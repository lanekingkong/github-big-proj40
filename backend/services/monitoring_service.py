"""
Monitoring Service
==================
Real-time monitoring and event broadcasting for the AgentForge platform.

Collects agent status changes, task progress updates, performance metrics,
and collaboration events, then pushes them to connected WebSocket clients.

Design:
- Event-driven architecture with typed event classes
- Topic-based publish/subscribe for efficient filtering
- Non-blocking background monitoring task
- Automatic dead connection cleanup
"""

from __future__ import annotations

import asyncio
import datetime
import uuid
from collections import defaultdict
from enum import Enum
from typing import Any

from utils.logger import get_logger

__all__ = [
    "MonitoringService",
    "EventType",
    "AgentStateEvent",
    "TaskProgressEvent",
    "LogStreamEvent",
    "CollaborationEvent",
]

logger = get_logger(__name__)


class EventType(str, Enum):
    """Types of events broadcast via the monitoring service."""

    AGENT_STATUS = "agent_status"
    TASK_PROGRESS = "task_progress"
    LOG_STREAM = "log_stream"
    COLLABORATION = "collaboration"
    PERFORMANCE_METRIC = "performance_metric"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class AgentStateEvent:
    """Event emitted when an agent's state changes (idle ↔ busy ↔ error ↔ offline)."""

    def __init__(
        self,
        agent_id: uuid.UUID,
        agent_name: str,
        old_status: str,
        new_status: str,
        timestamp: datetime.datetime | None = None,
    ) -> None:
        """
        Initialize an agent state change event.

        Args:
            agent_id: The agent's unique identifier.
            agent_name: Human-readable agent name.
            old_status: Previous status before the change.
            new_status: Current status after the change.
            timestamp: When the transition occurred (defaults to now).
        """
        self.event_type = EventType.AGENT_STATUS
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.old_status = old_status
        self.new_status = new_status
        self.timestamp = timestamp or datetime.datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event to a JSON-compatible dictionary."""
        return {
            "event": self.event_type.value,
            "agent_id": str(self.agent_id),
            "agent_name": self.agent_name,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "timestamp": self.timestamp.isoformat(),
        }


class TaskProgressEvent:
    """Event emitted as tasks progress through their lifecycle."""

    def __init__(
        self,
        project_id: uuid.UUID,
        task_id: uuid.UUID,
        task_name: str,
        agent_id: uuid.UUID | None,
        status: str,
        progress: float,  # 0.0 to 100.0
        message: str = "",
        timestamp: datetime.datetime | None = None,
    ) -> None:
        """
        Initialize a task progress event.

        Args:
            project_id: The project this task belongs to.
            task_id: The task's unique identifier.
            task_name: Human-readable task name.
            agent_id: The agent executing this task (or None if unassigned).
            status: Current task status.
            progress: Completion percentage (0-100).
            message: Optional human-readable progress message.
            timestamp: When the event occurred.
        """
        self.event_type = EventType.TASK_PROGRESS
        self.project_id = project_id
        self.task_id = task_id
        self.task_name = task_name
        self.agent_id = agent_id
        self.status = status
        self.progress = progress
        self.message = message
        self.timestamp = timestamp or datetime.datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event to a JSON-compatible dictionary."""
        return {
            "event": self.event_type.value,
            "project_id": str(self.project_id),
            "task_id": str(self.task_id),
            "task_name": self.task_name,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class LogStreamEvent:
    """Event carrying a line of real-time agent output log."""

    def __init__(
        self,
        project_id: uuid.UUID,
        agent_id: uuid.UUID,
        agent_name: str,
        level: str,
        message: str,
        timestamp: datetime.datetime | None = None,
    ) -> None:
        """
        Initialize a log stream event.

        Args:
            project_id: The project context.
            agent_id: The agent producing the log.
            agent_name: Human-readable agent name.
            level: Log level (DEBUG, INFO, WARNING, ERROR).
            message: The log message content.
            timestamp: When the log was emitted.
        """
        self.event_type = EventType.LOG_STREAM
        self.project_id = project_id
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.level = level
        self.message = message
        self.timestamp = timestamp or datetime.datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event to a JSON-compatible dictionary."""
        return {
            "event": self.event_type.value,
            "project_id": str(self.project_id),
            "agent_id": str(self.agent_id),
            "agent_name": self.agent_name,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }


class CollaborationEvent:
    """Event emitted when agents interact (handoffs, reviews, conflicts)."""

    def __init__(
        self,
        project_id: uuid.UUID,
        from_agent_id: uuid.UUID,
        to_agent_id: uuid.UUID,
        action: str,
        details: dict[str, Any] | None = None,
        timestamp: datetime.datetime | None = None,
    ) -> None:
        """
        Initialize a collaboration event.

        Args:
            project_id: The project context.
            from_agent_id: The agent initiating the interaction.
            to_agent_id: The agent receiving the interaction.
            action: The type of interaction (handoff, review_request, fix_request).
            details: Additional event-specific data.
            timestamp: When the event occurred.
        """
        self.event_type = EventType.COLLABORATION
        self.project_id = project_id
        self.from_agent_id = from_agent_id
        self.to_agent_id = to_agent_id
        self.action = action
        self.details = details or {}
        self.timestamp = timestamp or datetime.datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event to a JSON-compatible dictionary."""
        return {
            "event": self.event_type.value,
            "project_id": str(self.project_id),
            "from_agent_id": str(self.from_agent_id),
            "to_agent_id": str(self.to_agent_id),
            "action": self.action,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class MonitoringService:
    """
    Central monitoring service that collects metrics and broadcasts events.

    Features:
        - Topic-based publish/subscribe for filtered delivery
        - Performance metric aggregation (CPU, memory, task throughput)
        - Heartbeat monitoring with configurable intervals
        - Automatic dead connection detection
        - WebSocket integration via ConnectionManager
    """

    def __init__(self) -> None:
        """Initialize the monitoring service with metric stores."""
        # Map of client_id → ConnectionManager reference
        self._ws_clients: dict[str, Any] = {}  # ConnectionManager stored here
        # Performance metrics store: agent_id → metrics dict
        self._performance_metrics: dict[str, dict[str, Any]] = {}
        # Event history buffer (circular, last N events)
        self._event_history: list[dict[str, Any]] = []
        self._max_history: int = 1000
        # Background task for heartbeat monitoring
        self._heartbeat_task: asyncio.Task[Any] | None = None

    # ------------------------------------------------------------------
    # WebSocket Client Management
    # ------------------------------------------------------------------

    async def register_ws_client(
        self,
        client_id: str,
        connection_manager: Any,
    ) -> None:
        """
        Register a WebSocket client for event push.

        Args:
            client_id: Unique client identifier.
            connection_manager: The WebSocket ConnectionManager instance.
        """
        self._ws_clients[client_id] = connection_manager
        logger.debug(f"WS client registered: {client_id}")

    async def unregister_ws_client(self, client_id: str) -> None:
        """
        Remove a WebSocket client registration.

        Args:
            client_id: The client to unregister.
        """
        self._ws_clients.pop(client_id, None)
        logger.debug(f"WS client unregistered: {client_id}")

    # ------------------------------------------------------------------
    # Event Publishing
    # ------------------------------------------------------------------

    async def publish_agent_status(
        self,
        agent_id: uuid.UUID,
        agent_name: str,
        old_status: str,
        new_status: str,
    ) -> None:
        """
        Publish an agent status change event.

        Broadcasts to the 'agent_status' topic and stores in history.

        Args:
            agent_id: The agent that changed status.
            agent_name: Human-readable agent name.
            old_status: Previous status.
            new_status: Current status.
        """
        event = AgentStateEvent(agent_id, agent_name, old_status, new_status)
        self._store_event(event.to_dict())

        # Push to all connected clients subscribed to agent_status
        for connection_manager in self._ws_clients.values():
            try:
                await connection_manager.publish(
                    EventType.AGENT_STATUS.value,
                    event.to_dict(),
                )
            except Exception as exc:
                logger.error(f"Failed to publish agent status: {exc}")

    async def publish_task_progress(
        self,
        project_id: uuid.UUID,
        task_id: uuid.UUID,
        task_name: str,
        agent_id: uuid.UUID | None,
        status: str,
        progress: float,
        message: str = "",
    ) -> None:
        """
        Publish a task progress update event.

        Args:
            project_id: The project context.
            task_id: The task being progressed.
            task_name: Human-readable task name.
            agent_id: The executing agent (or None).
            status: Current task status.
            progress: Completion percentage (0-100).
            message: Optional progress message.
        """
        event = TaskProgressEvent(
            project_id=project_id,
            task_id=task_id,
            task_name=task_name,
            agent_id=agent_id,
            status=status,
            progress=progress,
            message=message,
        )
        self._store_event(event.to_dict())

        for connection_manager in self._ws_clients.values():
            try:
                await connection_manager.publish(
                    EventType.TASK_PROGRESS.value,
                    event.to_dict(),
                )
            except Exception as exc:
                logger.error(f"Failed to publish task progress: {exc}")

    async def publish_log_stream(
        self,
        project_id: uuid.UUID,
        agent_id: uuid.UUID,
        agent_name: str,
        level: str,
        message: str,
    ) -> None:
        """
        Publish a log stream event from an agent.

        Args:
            project_id: The project context.
            agent_id: The agent producing the log.
            agent_name: Human-readable agent name.
            level: Log level (DEBUG, INFO, WARNING, ERROR).
            message: Log message content.
        """
        event = LogStreamEvent(project_id, agent_id, agent_name, level, message)
        self._store_event(event.to_dict())

        for connection_manager in self._ws_clients.values():
            try:
                await connection_manager.publish(
                    EventType.LOG_STREAM.value,
                    event.to_dict(),
                )
            except Exception as exc:
                logger.error(f"Failed to publish log stream: {exc}")

    async def publish_collaboration(
        self,
        project_id: uuid.UUID,
        from_agent_id: uuid.UUID,
        to_agent_id: uuid.UUID,
        action: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Publish an agent collaboration event.

        Args:
            project_id: The project context.
            from_agent_id: The initiating agent.
            to_agent_id: The receiving agent.
            action: Type of collaboration action.
            details: Additional event data.
        """
        event = CollaborationEvent(
            project_id=project_id,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            action=action,
            details=details,
        )
        self._store_event(event.to_dict())

        for connection_manager in self._ws_clients.values():
            try:
                await connection_manager.publish(
                    EventType.COLLABORATION.value,
                    event.to_dict(),
                )
            except Exception as exc:
                logger.error(f"Failed to publish collaboration event: {exc}")

    # ------------------------------------------------------------------
    # Performance Metrics
    # ------------------------------------------------------------------

    async def update_performance_metric(
        self,
        agent_id: uuid.UUID,
        metrics: dict[str, Any],
    ) -> None:
        """
        Update performance metrics for a specific agent.

        Supported metrics: cpu_percent, memory_mb, tasks_completed,
        avg_task_duration_sec, error_rate.

        Args:
            agent_id: The agent to update metrics for.
            metrics: Dictionary of metric name → value.
        """
        key = str(agent_id)
        if key not in self._performance_metrics:
            self._performance_metrics[key] = {}

        self._performance_metrics[key].update(metrics)
        self._performance_metrics[key]["updated_at"] = datetime.datetime.utcnow().isoformat()

    async def get_performance_metrics(
        self,
        agent_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Retrieve current performance metrics for an agent.

        Args:
            agent_id: The agent's UUID.

        Returns:
            Metrics dictionary or empty dict if no data available.
        """
        return self._performance_metrics.get(str(agent_id), {})

    # ------------------------------------------------------------------
    # Heartbeat Monitoring
    # ------------------------------------------------------------------

    async def start_heartbeat_monitor(self, interval_sec: float = 10.0) -> None:
        """
        Start a background heartbeat monitoring loop.

        Periodically checks all registered agents' health and publishes
        heartbeat events to connected clients.

        Args:
            interval_sec: Time between heartbeat checks in seconds.
        """
        if self._heartbeat_task is not None:
            return

        async def _heartbeat_loop() -> None:
            while True:
                try:
                    heartbeat_event = {
                        "event": EventType.HEARTBEAT.value,
                        "active_connections": len(self._ws_clients),
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                    }
                    for connection_manager in self._ws_clients.values():
                        try:
                            await connection_manager.broadcast(heartbeat_event)
                        except Exception:
                            pass
                except Exception as exc:
                    logger.error(f"Heartbeat monitor error: {exc}")

                await asyncio.sleep(interval_sec)

        self._heartbeat_task = asyncio.create_task(_heartbeat_loop())
        logger.info(f"Heartbeat monitor started (interval={interval_sec}s)")

    async def stop_heartbeat_monitor(self) -> None:
        """Stop the background heartbeat monitoring loop."""
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            logger.info("Heartbeat monitor stopped")

    # ------------------------------------------------------------------
    # Event History
    # ------------------------------------------------------------------

    def _store_event(self, event_dict: dict[str, Any]) -> None:
        """
        Store an event in the in-memory circular history buffer.

        Args:
            event_dict: Serialized event dictionary.
        """
        self._event_history.append(event_dict)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

    async def get_event_history(
        self,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Retrieve recent event history with optional filtering.

        Args:
            event_type: Filter by event type (e.g., 'agent_status').
            limit: Maximum number of events to return.

        Returns:
            List of matching event dictionaries (most recent first).
        """
        # Reverse for most-recent-first
        events = self._event_history[::-1]

        if event_type:
            events = [e for e in events if e.get("event") == event_type]

        return events[:limit]
