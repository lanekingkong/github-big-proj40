"""
Agent Service
=============
Business logic for AI Agent lifecycle management in the AgentForge platform.

Responsible for:
- Agent registration and deregistration
- Health monitoring and status tracking
- Automatic agent discovery via filesystem scanning
- Adapter lifecycle coordination
"""

from __future__ import annotations

import asyncio
import datetime
import uuid
from pathlib import Path
from typing import Any

from core.agent_registry import AgentRegistry
from models.agent import AgentConfig, AgentRole, AgentStatus
from utils.logger import get_logger

__all__ = ["AgentService"]

logger = get_logger(__name__)

# Known AI coding agent CLI names and their adapter mappings
_KNOWN_AGENTS: dict[str, dict[str, Any]] = {
    "claude": {
        "name": "Claude Code",
        "adapter": "claude_code",
        "role": AgentRole.DEVELOPER,
        "cli_names": ["claude", "claude-code"],
    },
    "codex": {
        "name": "OpenAI Codex",
        "adapter": "codex",
        "role": AgentRole.DEVELOPER,
        "cli_names": ["codex", "openai-codex"],
    },
    "opencode": {
        "name": "OpenCode",
        "adapter": "opencode",
        "role": AgentRole.DEVELOPER,
        "cli_names": ["opencode"],
    },
    "gemini": {
        "name": "Gemini CLI",
        "adapter": "gemini_cli",
        "role": AgentRole.DEVELOPER,
        "cli_names": ["gemini", "gemini-cli"],
    },
}


class AgentService:
    """
    Service for managing agent registration, health, and discovery.

    Coordinates with AgentRegistry for persistence and health checks,
    and provides auto-discovery for detecting installed AI agents.
    """

    def __init__(self) -> None:
        """Initialize the agent service with registry and in-memory store."""
        self._registry = AgentRegistry()
        self._agents: dict[uuid.UUID, AgentConfig] = {}
        self._health_cache: dict[uuid.UUID, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------

    async def list_agents(
        self,
        role: str | None = None,
        status: str | None = None,
        adapter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AgentConfig]:
        """
        List registered agents with optional filtering.

        Args:
            role: Filter by agent role (Developer, Reviewer, etc.).
            status: Filter by agent status (idle, busy, error, offline).
            adapter: Filter by adapter type.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of matching AgentConfig instances.
        """
        agents = list(self._agents.values())

        if role:
            agents = [a for a in agents if a.role.value == role]
        if status:
            agents = [a for a in agents if a.status.value == status]
        if adapter:
            agents = [a for a in agents if a.adapter == adapter]

        return agents[offset : offset + limit]

    async def count_agents(
        self,
        role: str | None = None,
        status: str | None = None,
        adapter: str | None = None,
    ) -> int:
        """
        Count agents matching the given filters.

        Args:
            role: Filter by agent role.
            status: Filter by agent status.
            adapter: Filter by adapter type.

        Returns:
            Total count of matching agents.
        """
        agents = await self.list_agents(role=role, status=status, adapter=adapter, limit=999999)
        return len(agents)

    async def register_agent(self, payload: Any) -> AgentConfig | None:
        """
        Register a new agent with its adapter configuration.

        Args:
            payload: Agent creation request with name, role, adapter, and CLI path.

        Returns:
            The registered AgentConfig, or None if a conflict exists.
        """
        try:
            # Check for duplicate name or path
            for existing in self._agents.values():
                if existing.name == payload.name:
                    logger.warning(f"Agent name conflict: {payload.name}")
                    return None
                if (getattr(payload, "cli_path", None)
                        and existing.cli_path == payload.cli_path):
                    logger.warning(f"Agent CLI path conflict: {payload.cli_path}")
                    return None

            agent = AgentConfig(
                id=uuid.uuid4(),
                name=payload.name,
                role=getattr(payload, "role", AgentRole.DEVELOPER),
                adapter=getattr(payload, "adapter", "custom"),
                cli_path=getattr(payload, "cli_path", ""),
                cli_args=getattr(payload, "cli_args", []),
                env_vars=getattr(payload, "env_vars", {}),
                status=AgentStatus.IDLE,
                created_at=datetime.datetime.utcnow(),
            )
            self._agents[agent.id] = agent
            self._registry.register(agent)
            logger.info(f"Agent registered: {agent.id} ({agent.name})")
            return agent
        except Exception as exc:
            logger.error(f"Failed to register agent: {exc}")
            return None

    async def get_agent(self, agent_id: uuid.UUID) -> AgentConfig | None:
        """
        Retrieve an agent by its unique identifier.

        Args:
            agent_id: The agent's UUID.

        Returns:
            The AgentConfig instance or None if not found.
        """
        return self._agents.get(agent_id)

    async def update_agent(
        self,
        agent_id: uuid.UUID,
        payload: Any,
    ) -> AgentConfig | None:
        """
        Update an existing agent's configuration.

        Args:
            agent_id: The agent's UUID.
            payload: Fields to update (name, role, adapter, cli_args, env_vars).

        Returns:
            The updated AgentConfig or None if not found.
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            return None

        if hasattr(payload, "name") and payload.name is not None:
            agent.name = payload.name
        if hasattr(payload, "role") and payload.role is not None:
            agent.role = payload.role
        if hasattr(payload, "adapter") and payload.adapter is not None:
            agent.adapter = payload.adapter
        if hasattr(payload, "cli_args") and payload.cli_args is not None:
            agent.cli_args = payload.cli_args
        if hasattr(payload, "env_vars") and payload.env_vars is not None:
            agent.env_vars = payload.env_vars

        agent.updated_at = datetime.datetime.utcnow()
        logger.info(f"Agent updated: {agent_id}")
        return agent

    async def deregister_agent(self, agent_id: uuid.UUID) -> bool:
        """
        Remove an agent from the registry.

        Args:
            agent_id: The agent's UUID.

        Returns:
            True if removed, False if not found.
        """
        if agent_id not in self._agents:
            return False
        self._registry.deregister(agent_id)
        del self._agents[agent_id]
        self._health_cache.pop(agent_id, None)
        logger.info(f"Agent deregistered: {agent_id}")
        return True

    # ------------------------------------------------------------------
    # Health & Status
    # ------------------------------------------------------------------

    async def get_agent_status(self, agent_id: uuid.UUID) -> dict[str, Any] | None:
        """
        Retrieve the current health status of an agent.

        Performs an active health check and caches the result.

        Args:
            agent_id: The agent's UUID.

        Returns:
            Status dict with keys: agent_id, status, last_heartbeat, uptime, pid,
            or None if agent not found.
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            return None

        # Perform health check via registry
        health = await self._registry.check_health(agent_id)
        self._health_cache[agent_id] = {
            "agent_id": str(agent_id),
            "name": agent.name,
            "status": health.status.value if health else "unknown",
            "last_heartbeat": (
                health.last_heartbeat.isoformat() if health and health.last_heartbeat else None
            ),
            "uptime": health.uptime if health else 0,
            "pid": health.pid if health else None,
            "checked_at": datetime.datetime.utcnow().isoformat(),
        }
        return self._health_cache[agent_id]

    # ------------------------------------------------------------------
    # Auto-Discovery
    # ------------------------------------------------------------------

    async def discover_agents(
        self,
        scan_paths: list[str] | None = None,
    ) -> list[AgentConfig]:
        """
        Scan the system for installed AI coding agents and auto-register them.

        Searches common installation directories and system PATH for known
        agent CLIs. Already-registered agents are skipped.

        Args:
            scan_paths: Additional directories to search beyond defaults.

        Returns:
            List of newly discovered and registered AgentConfig instances.
        """
        discovered: list[AgentConfig] = []
        search_paths = self._build_search_paths(scan_paths)
        known_names = {a.name for a in self._agents.values()}

        for search_dir in search_paths:
            for agent_key, agent_info in _KNOWN_AGENTS.items():
                if agent_info["name"] in known_names:
                    continue

                found_path = self._find_executable(search_dir, agent_info["cli_names"])
                if found_path is None:
                    continue

                agent = await self.register_agent(
                    type(
                        "DiscoverRequest",
                        (),
                        {
                            "name": agent_info["name"],
                            "role": agent_info["role"],
                            "adapter": agent_info["adapter"],
                            "cli_path": str(found_path),
                            "cli_args": [],
                            "env_vars": {},
                        },
                    )()
                )
                if agent is not None:
                    discovered.append(agent)
                    known_names.add(agent.name)
                    logger.info(
                        f"Auto-discovered agent: {agent_info['name']} at {found_path}"
                    )

        return discovered

    def _build_search_paths(self, extra_paths: list[str] | None) -> list[Path]:
        """
        Build the list of directories to scan for agent executables.

        Includes system PATH entries, common installation directories,
        and user-specified extra paths.

        Args:
            extra_paths: Additional directories to include.

        Returns:
            List of Path objects to search.
        """
        paths: list[Path] = []

        # System PATH
        import os
        path_env = os.environ.get("PATH", "")
        for entry in path_env.split(";"):
            entry = entry.strip()
            if entry and Path(entry).exists():
                paths.append(Path(entry))

        # Common install locations on Windows
        common = [
            Path.home() / "AppData" / "Roaming" / "npm",
            Path.home() / "AppData" / "Local" / "Programs",
            Path("C:/") / "Program Files" / "nodejs",
        ]
        for p in common:
            if p.exists() and p not in paths:
                paths.append(p)

        # User-specified paths
        if extra_paths:
            for ep in extra_paths:
                ep_path = Path(ep)
                if ep_path.exists() and ep_path not in paths:
                    paths.append(ep_path)

        return paths

    @staticmethod
    def _find_executable(
        directory: Path,
        names: list[str],
    ) -> Path | None:
        """
        Search for an executable file by name in a directory.

        Tries both the raw name and common extensions (.exe, .cmd, .bat).

        Args:
            directory: The directory to search in.
            names: Base names of the executable to find.

        Returns:
            Path to the found executable or None if not found.
        """
        extensions = ["", ".exe", ".cmd", ".bat", ".ps1"]
        for name in names:
            for ext in extensions:
                candidate = directory / f"{name}{ext}"
                if candidate.is_file():
                    return candidate
        return None
