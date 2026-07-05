"""
A2A (Agent-to-Agent) Protocol Server
====================================
Server-side implementation of the A2A protocol for AgentForge.

The A2A protocol enables direct inter-agent communication and coordination
within the AgentForge ecosystem. This server:
- Advertises agent capabilities to other agents in the team
- Receives task delegation requests from peer agents
- Provides status updates on delegated tasks
- Supports artifact sharing between agents
- Manages peer-to-peer message routing

Based on the Google A2A protocol draft specification.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from utils.logger import get_logger

__all__ = [
    "A2AServer",
    "A2AAgentCard",
    "A2ATaskState",
    "A2AMessage",
    "A2AArtifact",
]

logger = get_logger(__name__)


class A2ATaskState(str, Enum):
    """Task states in the A2A protocol lifecycle."""

    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class A2AAgentCard:
    """
    Agent capability advertisement card.

    Published by each agent to describe its capabilities, skills,
    and supported interaction modes for peer agents.

    Attributes:
        name: Human-readable agent name.
        description: What this agent does.
        url: Endpoint URL for A2A communication.
        version: Agent version string.
        capabilities: Skills and features this agent supports.
        skills: Detailed skill descriptions with input/output specs.
        default_input_modes: Supported input formats (text, file, etc.).
        default_output_modes: Supported output formats.
        is_authorized_agent: Whether this is a verified AgentForge agent.
    """

    name: str
    description: str
    url: str
    version: str = "1.0.0"
    capabilities: dict[str, Any] = field(default_factory=dict)
    skills: list[dict[str, Any]] = field(default_factory=list)
    default_input_modes: list[str] = field(default_factory=lambda: ["text"])
    default_output_modes: list[str] = field(default_factory=lambda: ["text"])
    is_authorized_agent: bool = True


@dataclass
class A2AMessage:
    """
    A message exchanged between agents via the A2A protocol.

    Attributes:
        message_id: Unique message identifier.
        from_agent: Sender agent identifier.
        to_agent: Recipient agent identifier.
        content: Message body content.
        task_id: Associated task ID if this message is task-related.
        timestamp: When the message was sent.
    """

    message_id: uuid.UUID
    from_agent: str
    to_agent: str
    content: str
    task_id: uuid.UUID | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class A2AArtifact:
    """
    A shareable output artifact produced by an agent during task execution.

    Attributes:
        artifact_id: Unique artifact identifier.
        name: Human-readable artifact name.
        content_type: MIME type of the artifact.
        data: Binary or text data content.
        created_by: Agent that produced this artifact.
        task_id: The task that generated this artifact.
        timestamp: Creation timestamp.
    """

    artifact_id: uuid.UUID
    name: str
    content_type: str
    data: bytes
    created_by: str
    task_id: uuid.UUID
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class A2AServer:
    """
    Server for receiving and processing A2A protocol requests.

    Manages:
    - Agent card publishing (capability advertisement)
    - Task delegation reception and lifecycle management
    - Message routing between agents
    - Artifact storage and sharing
    - Task status tracking

    Usage:
        server = A2AServer(agent_card=my_card)
        await server.start(host="127.0.0.1", port=8100)
        # Handles incoming A2A requests automatically
    """

    def __init__(self, agent_card: A2AAgentCard) -> None:
        """
        Initialize the A2A server.

        Args:
            agent_card: The agent capability card for this agent.
        """
        self.agent_card = agent_card
        self._tasks: dict[uuid.UUID, dict[str, Any]] = {}
        self._messages: dict[uuid.UUID, A2AMessage] = {}
        self._artifacts: dict[uuid.UUID, A2AArtifact] = {}
        self._task_handlers: dict[str, Any] = {}
        self._message_queue: asyncio.Queue[A2AMessage] = asyncio.Queue()
        self._running: bool = False

    # ------------------------------------------------------------------
    # Agent Card
    # ------------------------------------------------------------------

    def get_agent_card(self) -> dict[str, Any]:
        """
        Return the agent card as a JSON-serializable dictionary.

        Returns:
            Agent card with all capabilities and skills listed.
        """
        return {
            "name": self.agent_card.name,
            "description": self.agent_card.description,
            "url": self.agent_card.url,
            "version": self.agent_card.version,
            "capabilities": self.agent_card.capabilities,
            "skills": self.agent_card.skills,
            "defaultInputModes": self.agent_card.default_input_modes,
            "defaultOutputModes": self.agent_card.default_output_modes,
            "is_authorized_agent": self.agent_card.is_authorized_agent,
        }

    # ------------------------------------------------------------------
    # Task Management
    # ------------------------------------------------------------------

    async def receive_task(
        self,
        task_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Receive a task delegation from a peer agent.

        Creates a new task record and returns an acknowledgment.

        Args:
            task_data: Task specification including id, description,
                       input parameters, and sender info.

        Returns:
            Task acknowledgment with assigned task ID and initial state.
        """
        task_id = uuid.UUID(task_data.get("id", str(uuid.uuid4())))
        task_record = {
            "task_id": task_id,
            "state": A2ATaskState.SUBMITTED.value,
            "description": task_data.get("description", ""),
            "from_agent": task_data.get("from_agent", "unknown"),
            "input": task_data.get("input", {}),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._tasks[task_id] = task_record
        logger.info(f"A2A task received: {task_id} from {task_record['from_agent']}")
        return {"task_id": str(task_id), "state": A2ATaskState.SUBMITTED.value}

    async def update_task_state(
        self,
        task_id: uuid.UUID,
        state: A2ATaskState,
        status_message: str | None = None,
    ) -> dict[str, Any]:
        """
        Update the state of a delegated task.

        Args:
            task_id: The task to update.
            state: New task state.
            status_message: Optional human-readable status message.

        Returns:
            Updated task record.

        Raises:
            ValueError: If the task is not found.
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task not found: {task_id}")

        self._tasks[task_id]["state"] = state.value
        self._tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        if status_message:
            self._tasks[task_id]["status_message"] = status_message

        logger.info(f"A2A task {task_id} → {state.value}")
        return self._tasks[task_id]

    async def get_task_status(
        self,
        task_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Query the current status of a delegated task.

        Args:
            task_id: The task to query.

        Returns:
            Task status record.

        Raises:
            ValueError: If the task is not found.
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task not found: {task_id}")
        return self._tasks[task_id]

    async def cancel_task(self, task_id: uuid.UUID) -> dict[str, Any]:
        """
        Cancel a delegated task.

        Args:
            task_id: The task to cancel.

        Returns:
            Updated task record.

        Raises:
            ValueError: If the task is not found or already completed.
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task not found: {task_id}")

        task = self._tasks[task_id]
        if task["state"] in (A2ATaskState.COMPLETED.value, A2ATaskState.FAILED.value):
            raise ValueError(f"Cannot cancel task in state: {task['state']}")

        return await self.update_task_state(task_id, A2ATaskState.CANCELLED)

    async def list_tasks(
        self,
        state: A2ATaskState | None = None,
    ) -> list[dict[str, Any]]:
        """
        List all delegated tasks, optionally filtered by state.

        Args:
            state: Filter by task state.

        Returns:
            List of matching task records.
        """
        tasks = list(self._tasks.values())
        if state:
            tasks = [t for t in tasks if t["state"] == state.value]
        return tasks

    # ------------------------------------------------------------------
    # Message Handling
    # ------------------------------------------------------------------

    async def send_message(
        self,
        to_agent: str,
        content: str,
        task_id: uuid.UUID | None = None,
    ) -> A2AMessage:
        """
        Send a message to a peer agent.

        Args:
            to_agent: Recipient agent identifier.
            content: Message body.
            task_id: Optional associated task ID.

        Returns:
            The created message record.
        """
        message = A2AMessage(
            message_id=uuid.uuid4(),
            from_agent=self.agent_card.name,
            to_agent=to_agent,
            content=content,
            task_id=task_id,
        )
        self._messages[message.message_id] = message
        await self._message_queue.put(message)
        logger.info(
            f"A2A message {message.message_id}: {self.agent_card.name} → {to_agent}"
        )
        return message

    async def receive_messages(
        self,
        timeout: float = 1.0,
    ) -> list[A2AMessage]:
        """
        Receive pending messages addressed to this agent.

        Args:
            timeout: Maximum time to wait for messages in seconds.

        Returns:
            List of received messages.
        """
        messages: list[A2AMessage] = []
        try:
            while True:
                msg = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=timeout,
                )
                messages.append(msg)
        except asyncio.TimeoutError:
            pass
        return messages

    # ------------------------------------------------------------------
    # Artifact Management
    # ------------------------------------------------------------------

    async def register_artifact(
        self,
        name: str,
        content_type: str,
        data: bytes,
        task_id: uuid.UUID,
    ) -> A2AArtifact:
        """
        Register a new artifact produced during task execution.

        Args:
            name: Human-readable artifact name.
            content_type: MIME type of the content.
            data: Binary content data.
            task_id: Associated task that produced this artifact.

        Returns:
            The registered artifact record.
        """
        artifact = A2AArtifact(
            artifact_id=uuid.uuid4(),
            name=name,
            content_type=content_type,
            data=data,
            created_by=self.agent_card.name,
            task_id=task_id,
        )
        self._artifacts[artifact.artifact_id] = artifact
        logger.info(f"A2A artifact registered: {name} ({artifact.artifact_id})")
        return artifact

    async def get_artifact(
        self,
        artifact_id: uuid.UUID,
    ) -> A2AArtifact:
        """
        Retrieve a registered artifact by ID.

        Args:
            artifact_id: The artifact's unique identifier.

        Returns:
            The artifact record.

        Raises:
            ValueError: If the artifact is not found.
        """
        if artifact_id not in self._artifacts:
            raise ValueError(f"Artifact not found: {artifact_id}")
        return self._artifacts[artifact_id]

    async def list_artifacts(
        self,
        task_id: uuid.UUID | None = None,
    ) -> list[A2AArtifact]:
        """
        List all artifacts, optionally filtered by task.

        Args:
            task_id: Filter by associated task.

        Returns:
            List of matching artifacts.
        """
        artifacts = list(self._artifacts.values())
        if task_id:
            artifacts = [a for a in artifacts if a.task_id == task_id]
        return artifacts

    # ------------------------------------------------------------------
    # Server Lifecycle
    # ------------------------------------------------------------------

    async def start(
        self,
        host: str = "127.0.0.1",
        port: int = 8100,
    ) -> None:
        """
        Start the A2A server to listen for incoming peer agent requests.

        Args:
            host: Bind address.
            port: Bind port.
        """
        self._running = True
        logger.info(f"A2A server starting on {host}:{port}")
        # Actual network server implementation depends on the FastAPI
        # integration layer. Placeholder for now.
        raise NotImplementedError(
            "A2A server transport requires FastAPI integration. "
            "Use the A2A client for direct agent-to-agent calls."
        )

    async def stop(self) -> None:
        """Stop the A2A server gracefully."""
        self._running = False
        logger.info("A2A server stopped")
