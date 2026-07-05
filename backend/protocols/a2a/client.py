"""
A2A (Agent-to-Agent) Protocol Client
====================================
Client for communicating with peer agents via the A2A protocol.

Enables agents within the AgentForge team to:
- Discover peer agent capabilities via agent cards
- Send task delegation requests to other agents
- Query task status from delegated agents
- Share artifacts between agents
- Exchange direct messages for coordination

Based on the Google A2A protocol draft specification.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from utils.logger import get_logger

__all__ = ["A2AClient", "A2APeerInfo"]

logger = get_logger(__name__)


@dataclass
class A2APeerInfo:
    """
    Information about a peer agent discovered on the network.

    Attributes:
        name: Agent name from its agent card.
        description: Agent description.
        url: A2A endpoint URL.
        capabilities: Advertised capabilities.
        skills: Available skills with input/output specs.
    """

    name: str
    description: str
    url: str
    capabilities: dict[str, Any]
    skills: list[dict[str, Any]]

    def supports_skill(self, skill_name: str) -> bool:
        """
        Check if this peer supports a specific skill.

        Args:
            skill_name: The skill name to check.

        Returns:
            True if the skill is listed in the agent's capabilities.
        """
        for skill in self.skills:
            if skill.get("name") == skill_name:
                return True
        return False


class A2AClient:
    """
    Client for communicating with peer agents via the A2A protocol.

    Handles:
    - Peer agent discovery
    - Task delegation (send task requests to peer agents)
    - Task status polling
    - Direct message exchange
    - Artifact retrieval from peer agents

    Usage:
        client = A2AClient()
        peer = await client.discover_agent("http://localhost:8100")
        task = await client.send_task(
            peer_url=peer.url,
            description="Review the generated code for security issues",
            input_artifacts=["artifact-id-1"],
        )
        status = await client.get_task_status(peer.url, task["task_id"])
    """

    def __init__(self) -> None:
        """Initialize the A2A client with an empty peer registry."""
        self._peers: dict[str, A2APeerInfo] = {}
        self._pending_tasks: dict[uuid.UUID, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Peer Discovery
    # ------------------------------------------------------------------

    async def discover_agent(self, peer_url: str) -> A2APeerInfo:
        """
        Discover a peer agent by fetching its agent card.

        Performs an HTTP GET to `{peer_url}/.well-known/agent.json`
        to retrieve the agent's capability advertisement.

        Args:
            peer_url: The base URL of the peer agent's A2A endpoint.

        Returns:
            Parsed peer agent information.

        Raises:
            ConnectionError: If the peer agent is unreachable.
            ValueError: If the agent card response is malformed.
        """
        logger.info(f"Discovering A2A peer agent at {peer_url}")

        # In production, make HTTP request to peer_url/.well-known/agent.json
        # Simulated discovery response for now
        agent_card: dict[str, Any] = await self._fetch_agent_card(peer_url)

        peer_info = A2APeerInfo(
            name=agent_card.get("name", "unknown"),
            description=agent_card.get("description", ""),
            url=peer_url,
            capabilities=agent_card.get("capabilities", {}),
            skills=agent_card.get("skills", []),
        )
        self._peers[peer_url] = peer_info
        logger.info(f"Discovered A2A peer: {peer_info.name}")
        return peer_info

    async def _fetch_agent_card(self, peer_url: str) -> dict[str, Any]:
        """
        Fetch the agent card from a peer's well-known endpoint.

        Args:
            peer_url: The peer agent's base URL.

        Returns:
            Parsed agent card JSON.

        Raises:
            NotImplementedError: In this stub; requires HTTP client integration.
        """
        # Placeholder: in production, use httpx or aiohttp
        raise NotImplementedError(
            "Agent card fetching requires HTTP client integration. "
            "Use discover_agent with a manually configured peer for testing."
        )

    async def list_known_peers(self) -> list[A2APeerInfo]:
        """
        List all currently known peer agents.

        Returns:
            List of discovered peer agent information.
        """
        return list(self._peers.values())

    async def forget_peer(self, peer_url: str) -> bool:
        """
        Remove a peer from the known peers registry.

        Args:
            peer_url: The peer's URL to forget.

        Returns:
            True if removed, False if not found.
        """
        if peer_url in self._peers:
            del self._peers[peer_url]
            logger.info(f"A2A peer forgotten: {peer_url}")
            return True
        return False

    # ------------------------------------------------------------------
    # Task Delegation
    # ------------------------------------------------------------------

    async def send_task(
        self,
        peer_url: str,
        description: str,
        input_data: dict[str, Any] | None = None,
        input_artifacts: list[str] | None = None,
        from_agent: str = "agentforge",
    ) -> dict[str, Any]:
        """
        Send a task delegation request to a peer agent.

        Args:
            peer_url: The peer agent's A2A endpoint.
            description: Task description for the peer agent.
            input_data: Input parameters for the task.
            input_artifacts: IDs of artifacts to pass as input.
            from_agent: Sender agent identifier.

        Returns:
            Task acknowledgment with assigned task_id and initial state.

        Raises:
            ConnectionError: If the peer agent is unreachable.
        """
        task_id = uuid.uuid4()
        task_payload = {
            "id": str(task_id),
            "description": description,
            "input": input_data or {},
            "input_artifacts": input_artifacts or [],
            "from_agent": from_agent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Sending A2A task to {peer_url}: {task_id}")

        # In production: POST {peer_url}/tasks
        # Simulated response for now
        response = await self._post_task(peer_url, task_payload)

        task_record = {
            "task_id": task_id,
            "peer_url": peer_url,
            "state": response.get("state", "submitted"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._pending_tasks[task_id] = task_record
        return task_record

    async def _post_task(
        self,
        peer_url: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        POST a task to a peer agent.

        Args:
            peer_url: The peer's endpoint.
            payload: Task creation payload.

        Returns:
            Response from the peer agent.

        Raises:
            NotImplementedError: In this stub.
        """
        raise NotImplementedError(
            "Task posting requires HTTP client integration."
        )

    # ------------------------------------------------------------------
    # Task Status
    # ------------------------------------------------------------------

    async def get_task_status(
        self,
        peer_url: str,
        task_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Query the status of a delegated task on a peer agent.

        Args:
            peer_url: The peer agent's endpoint.
            task_id: The task to query.

        Returns:
            Task status from the peer agent.
        """
        logger.info(f"Querying A2A task status: {task_id} on {peer_url}")

        # In production: GET {peer_url}/tasks/{task_id}
        status = await self._fetch_task_status(peer_url, task_id)

        if task_id in self._pending_tasks:
            self._pending_tasks[task_id]["state"] = status.get("state", "unknown")

        return status

    async def _fetch_task_status(
        self,
        peer_url: str,
        task_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Fetch task status from a peer agent.

        Args:
            peer_url: The peer's endpoint.
            task_id: The task ID.

        Returns:
            Task status response.

        Raises:
            NotImplementedError: In this stub.
        """
        raise NotImplementedError(
            "Task status fetching requires HTTP client integration."
        )

    async def cancel_task(
        self,
        peer_url: str,
        task_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Cancel a delegated task on a peer agent.

        Args:
            peer_url: The peer agent's endpoint.
            task_id: The task to cancel.

        Returns:
            Cancellation confirmation from the peer.
        """
        logger.info(f"Cancelling A2A task: {task_id} on {peer_url}")
        # In production: DELETE {peer_url}/tasks/{task_id}
        raise NotImplementedError(
            "Task cancellation requires HTTP client integration."
        )

    # ------------------------------------------------------------------
    # Artifact Retrieval
    # ------------------------------------------------------------------

    async def get_artifact(
        self,
        peer_url: str,
        artifact_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Retrieve an artifact from a peer agent.

        Args:
            peer_url: The peer agent's endpoint.
            artifact_id: The artifact to retrieve.

        Returns:
            Artifact metadata and data.
        """
        logger.info(f"Retrieving A2A artifact {artifact_id} from {peer_url}")
        # In production: GET {peer_url}/artifacts/{artifact_id}
        raise NotImplementedError(
            "Artifact retrieval requires HTTP client integration."
        )

    async def list_task_artifacts(
        self,
        peer_url: str,
        task_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """
        List all artifacts produced by a specific task on a peer agent.

        Args:
            peer_url: The peer agent's endpoint.
            task_id: The task to list artifacts for.

        Returns:
            List of artifact descriptors.
        """
        logger.info(f"Listing A2A artifacts for task {task_id} on {peer_url}")
        raise NotImplementedError(
            "Artifact listing requires HTTP client integration."
        )

    # ------------------------------------------------------------------
    # Direct Messaging
    # ------------------------------------------------------------------

    async def send_message(
        self,
        peer_url: str,
        to_agent: str,
        content: str,
        task_id: uuid.UUID | None = None,
    ) -> None:
        """
        Send a direct message to a peer agent.

        Args:
            peer_url: The peer agent's endpoint.
            to_agent: Recipient agent name.
            content: Message content.
            task_id: Optional associated task.
        """
        message = {
            "message_id": str(uuid.uuid4()),
            "from_agent": "agentforge",
            "to_agent": to_agent,
            "content": content,
            "task_id": str(task_id) if task_id else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Sending A2A message to {to_agent} at {peer_url}")
        # In production: POST {peer_url}/messages
        raise NotImplementedError(
            "Direct messaging requires HTTP client integration."
        )

    # ------------------------------------------------------------------
    # Pending Tasks
    # ------------------------------------------------------------------

    async def list_pending_tasks(self) -> list[dict[str, Any]]:
        """
        List all tasks that have been delegated to peer agents
        and are still pending completion.

        Returns:
            List of pending task records.
        """
        return [
            t for t in self._pending_tasks.values()
            if t["state"] not in ("completed", "failed", "cancelled")
        ]

    async def get_pending_task(
        self,
        task_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """
        Retrieve a specific pending task record.

        Args:
            task_id: The task to look up.

        Returns:
            Task record or None if not found.
        """
        return self._pending_tasks.get(task_id)
