"""
WebSocket API Endpoints
=======================
Real-time bidirectional communication channel for the AgentForge platform.

Pushes live updates to connected clients including:
- Agent status changes (idle → busy → error → offline)
- Task progress updates (percent complete, current step)
- Log streaming (real-time agent output)
- Collaboration events (agent-to-agent handoffs, review requests)
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from services.monitoring_service import MonitoringService

__all__ = ["router"]

router = APIRouter()

# --- Connection Manager ---

class ConnectionManager:
    """
    Manages active WebSocket connections and message broadcasting.

    Supports:
        - Global broadcast to all connected clients
        - Targeted unicast to specific clients
        - Topic-based subscription for filtered event delivery
        - Automatic dead connection cleanup
    """

    def __init__(self) -> None:
        """Initialize the connection manager with an empty connection pool."""
        # Map of client_id → WebSocket connection
        self._connections: dict[str, WebSocket] = {}
        # Map of topic → set of client_ids subscribed
        self._subscriptions: dict[str, set[str]] = {}
        # Lock for thread-safe connection mutations
        self._lock: asyncio.Lock = asyncio.Lock()

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        """
        Accept and register a new WebSocket connection.

        Args:
            client_id: Unique identifier for this client connection.
            websocket: The accepted WebSocket connection instance.
        """
        await websocket.accept()
        async with self._lock:
            self._connections[client_id] = websocket

    async def disconnect(self, client_id: str) -> None:
        """
        Remove a client connection and clean up its subscriptions.

        Args:
            client_id: The client to disconnect.
        """
        async with self._lock:
            self._connections.pop(client_id, None)
            # Remove from all topic subscriptions
            for subscribers in self._subscriptions.values():
                subscribers.discard(client_id)

    async def subscribe(self, client_id: str, topic: str) -> None:
        """
        Subscribe a client to a specific event topic.

        Args:
            client_id: The subscribing client.
            topic: The topic name (e.g., 'agent_status', 'task_progress', 'logs').
        """
        async with self._lock:
            if topic not in self._subscriptions:
                self._subscriptions[topic] = set()
            self._subscriptions[topic].add(client_id)

    async def unsubscribe(self, client_id: str, topic: str) -> None:
        """
        Unsubscribe a client from a topic.

        Args:
            client_id: The client to unsubscribe.
            topic: The topic to leave.
        """
        async with self._lock:
            if topic in self._subscriptions:
                self._subscriptions[topic].discard(client_id)

    async def send_to_client(self, client_id: str, message: dict[str, Any]) -> bool:
        """
        Send a JSON message to a specific client.

        Args:
            client_id: Target client ID.
            message: JSON-serializable message payload.

        Returns:
            True if message was sent successfully, False if client not connected.
        """
        async with self._lock:
            websocket = self._connections.get(client_id)
        if websocket is None:
            return False
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            await self.disconnect(client_id)
            return False

    async def broadcast(self, message: dict[str, Any]) -> None:
        """
        Send a message to all connected clients.

        Args:
            message: JSON-serializable message payload.
        """
        async with self._lock:
            connections = dict(self._connections)
        for client_id, websocket in connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(client_id)

    async def publish(self, topic: str, message: dict[str, Any]) -> None:
        """
        Publish a message to all clients subscribed to a specific topic.

        Args:
            topic: The topic to publish to.
            message: JSON-serializable message payload.
        """
        message["topic"] = topic
        async with self._lock:
            subscribers = self._subscriptions.get(topic, set()).copy()
        for client_id in subscribers:
            await self.send_to_client(client_id, message)

    @property
    def active_connections(self) -> int:
        """Return the count of currently active WebSocket connections."""
        return len(self._connections)


# Global connection manager instance
manager = ConnectionManager()


# --- WebSocket Routes ---

@router.websocket("/events")
async def events_websocket(
    websocket: WebSocket,
    client_id: str = Query(
        ...,
        description="Unique client identifier for this connection",
    ),
) -> None:
    """
    Main WebSocket endpoint for receiving live event streams.

    After connecting, the client can:
    1. Send subscribe messages to filter events:
       → {"action": "subscribe", "topics": ["agent_status", "task_progress"]}
    2. Send unsubscribe messages:
       → {"action": "unsubscribe", "topics": ["logs"]}
    3. Receive event messages pushed from the server:
       ← {"event": "agent_status", "agent_id": "...", "status": "busy", "timestamp": "..."}

    Args:
        websocket: The WebSocket connection instance.
        client_id: Unique client identifier from query parameter.
    """
    await manager.connect(client_id, websocket)
    monitoring = MonitoringService()

    # Register this client with the monitoring service for automatic event push
    await monitoring.register_ws_client(client_id, manager)

    try:
        while True:
            data: dict[str, Any] = await websocket.receive_json()

            action = data.get("action")
            if action == "subscribe":
                topics: list[str] = data.get("topics", [])
                for topic in topics:
                    await manager.subscribe(client_id, topic)
                await websocket.send_json({
                    "event": "subscribed",
                    "topics": topics,
                    "client_id": client_id,
                })

            elif action == "unsubscribe":
                topics: list[str] = data.get("topics", [])
                for topic in topics:
                    await manager.unsubscribe(client_id, topic)
                await websocket.send_json({
                    "event": "unsubscribed",
                    "topics": topics,
                    "client_id": client_id,
                })

            elif action == "ping":
                await websocket.send_json({"event": "pong", "client_id": client_id})

            else:
                await websocket.send_json({
                    "event": "error",
                    "message": f"Unknown action: {action}",
                })

    except WebSocketDisconnect:
        pass
    finally:
        await monitoring.unregister_ws_client(client_id)
        await manager.disconnect(client_id)


@router.websocket("/agent/{agent_id}")
async def agent_stream_websocket(
    websocket: WebSocket,
    agent_id: str,
) -> None:
    """
    Dedicated WebSocket endpoint for a single agent's output stream.

    Clients connect to this endpoint to receive real-time output
    from a specific agent during task execution.

    Event types pushed:
        - agent_output: Raw stdout/stderr from the agent process
        - agent_status: Status changes for this specific agent
        - agent_progress: Task progress updates from this agent

    Args:
        websocket: The WebSocket connection instance.
        agent_id: The UUID of the agent to stream from.
    """
    client_id = f"agent_stream_{agent_id}_{uuid.uuid4().hex[:8]}"
    await manager.connect(client_id, websocket)

    # Auto-subscribe to agent-specific topics
    await manager.subscribe(client_id, f"agent:{agent_id}:output")
    await manager.subscribe(client_id, f"agent:{agent_id}:status")

    try:
        while True:
            data: dict[str, Any] = await websocket.receive_json()
            action = data.get("action")

            if action == "ping":
                await websocket.send_json({
                    "event": "pong",
                    "agent_id": agent_id,
                    "client_id": client_id,
                })
            elif action == "unsubscribe":
                break
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(client_id)
