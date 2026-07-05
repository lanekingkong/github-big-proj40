"""
Agent Registry
==============
Agent registration center for AgentForge.

Manages the lifecycle of agent instances, supports dynamic discovery,
and maintains a canonical registry of available agent configurations.
Provides CRUD operations backed by persistence via models.AgentConfig.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.base_adapter import (
    BaseAgentAdapter,
    HealthCheckResult,
    AgentStatus,
)
from config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Registry Entry
# =============================================================================

@dataclass
class RegistryEntry:
    """An entry in the agent registry."""
    agent_id: str
    name: str
    cli_name: str
    role: str
    model_name: str
    cli_path: Optional[str] = None
    api_key: Optional[str] = None
    enabled: bool = True
    metadata: Dict[str, Any] = None
    registered_at: Optional[datetime] = None
    last_health_check: Optional[HealthCheckResult] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.registered_at is None:
            self.registered_at = datetime.now(timezone.utc)

    @property
    def is_healthy(self) -> bool:
        return self.last_health_check is not None and self.last_health_check.is_healthy


# =============================================================================
# Adapter Factory
# =============================================================================

class AdapterFactory:
    """
    Factory for creating adapter instances from registry entries.

    Maps CLI names to concrete adapter classes and handles dynamic
    imports for custom adapters.
    """

    _ADAPTER_MAP: Dict[str, str] = {
        "claude": "adapters.claude_code.ClaudeCodeAdapter",
        "codex": "adapters.codex.CodexAdapter",
        "opencode": "adapters.opencode.OpenCodeAdapter",
        "gemini": "adapters.gemini_cli.GeminiCLIAdapter",
        "custom": "adapters.custom_adapter.CustomAgentAdapter",
    }

    @classmethod
    def get_adapter_class(cls, cli_name: str) -> Optional[Type[BaseAgentAdapter]]:
        """Get the adapter class for a given CLI name."""
        import_path = cls._ADAPTER_MAP.get(cli_name)
        if not import_path:
            logger.warning("No adapter registered for CLI: %s", cli_name)
            return None

        try:
            parts = import_path.rsplit(".", 1)
            module = __import__(parts[0], fromlist=[parts[1]])
            return getattr(module, parts[1])
        except (ImportError, AttributeError) as e:
            logger.error("Failed to load adapter '%s': %s", import_path, e)
            return None

    @classmethod
    def register_custom_adapter(
        cls,
        cli_name: str,
        import_path: str,
    ) -> None:
        """Register a custom adapter import path."""
        cls._ADAPTER_MAP[cli_name] = import_path
        logger.info("Registered custom adapter '%s' → %s", cli_name, import_path)

    @classmethod
    def list_supported_cli_names(cls) -> List[str]:
        """Return all supported CLI names."""
        return list(cls._ADAPTER_MAP.keys())

    @classmethod
    async def create_adapter(
        cls,
        entry: RegistryEntry,
    ) -> Optional[BaseAgentAdapter]:
        """
        Create an adapter instance from a registry entry.

        Args:
            entry: The registry entry with agent configuration.

        Returns:
            An initialized adapter instance, or None if creation fails.
        """
        adapter_cls = cls.get_adapter_class(entry.cli_name)
        if not adapter_cls:
            return None

        try:
            adapter = adapter_cls(
                name=entry.name,
                cli_name=entry.cli_name,
                role=entry.role,
                model_name=entry.model_name,
                cli_path=Path(entry.cli_path) if entry.cli_path else None,
                api_key=entry.api_key,
                config=entry.metadata,
            )
            return adapter
        except Exception as e:
            logger.error("Failed to create adapter '%s': %s", entry.name, e)
            return None


# =============================================================================
# Agent Registry
# =============================================================================

class AgentRegistry:
    """
    Central registry for managing agent instances.

    Supports:
    - Registration and unregistration of agents
    - Dynamic discovery of available agents
    - Health monitoring for all registered agents
    - Persistence via database models
    - Event hooks for lifecycle management
    """

    def __init__(self, db_session_factory=None):
        self._entries: Dict[str, RegistryEntry] = {}  # agent_id → entry
        self._instances: Dict[str, BaseAgentAdapter] = {}  # agent_id → adapter
        self._db_session_factory = db_session_factory
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._on_register_hooks: List[callable] = []
        self._on_unregister_hooks: List[callable] = []

        logger.info("AgentRegistry initialized")

    # ===== Registration =====

    async def register(
        self,
        agent_id: str,
        name: str,
        cli_name: str,
        role: str,
        model_name: str,
        cli_path: Optional[str] = None,
        api_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        persist: bool = True,
    ) -> RegistryEntry:
        """Register a new agent.

        Args:
            agent_id: Unique agent identifier.
            name: Human-readable name.
            cli_name: CLI tool name (claude, codex, gemini, etc.).
            role: Agent role (developer, reviewer, fixer, etc.).
            model_name: AI model identifier.
            cli_path: Optional custom path to CLI binary.
            api_key: Optional API key.
            metadata: Optional custom metadata.
            persist: Whether to persist to database.

        Returns:
            The created RegistryEntry.

        Raises:
            ValueError: If agent_id is already registered.
        """
        if agent_id in self._entries:
            raise ValueError(f"Agent '{agent_id}' is already registered")

        entry = RegistryEntry(
            agent_id=agent_id,
            name=name,
            cli_name=cli_name,
            role=role,
            model_name=model_name,
            cli_path=cli_path,
            api_key=api_key,
            metadata=metadata or {},
        )
        self._entries[agent_id] = entry

        # Create adapter instance
        adapter = await AdapterFactory.create_adapter(entry)
        if adapter:
            self._instances[agent_id] = adapter

        # Persist to database
        if persist and self._db_session_factory:
            await self._persist_entry(entry)

        # Fire hooks
        for hook in self._on_register_hooks:
            try:
                await hook(entry)
            except Exception as e:
                logger.exception("Register hook failed: %s", e)

        logger.info("Registered agent '%s' (id=%s, cli=%s, role=%s)", name, agent_id, cli_name, role)
        return entry

    async def unregister(self, agent_id: str) -> Optional[RegistryEntry]:
        """Remove an agent from the registry.

        Args:
            agent_id: The agent to remove.

        Returns:
            The removed entry, or None if not found.
        """
        entry = self._entries.pop(agent_id, None)
        if not entry:
            return None

        adapter = self._instances.pop(agent_id, None)
        if adapter:
            await adapter.cleanup()

        for hook in self._on_unregister_hooks:
            try:
                await hook(entry)
            except Exception as e:
                logger.exception("Unregister hook failed: %s", e)

        logger.info("Unregistered agent '%s' (id=%s)", entry.name, agent_id)
        return entry

    # ===== Discovery =====

    def get(self, agent_id: str) -> Optional[RegistryEntry]:
        """Get a registry entry by ID."""
        return self._entries.get(agent_id)

    def get_adapter(self, agent_id: str) -> Optional[BaseAgentAdapter]:
        """Get an active adapter instance by agent ID."""
        return self._instances.get(agent_id)

    def get_by_role(self, role: str) -> List[RegistryEntry]:
        """Find all agents with a given role."""
        return [e for e in self._entries.values() if e.role == role]

    def get_by_cli(self, cli_name: str) -> List[RegistryEntry]:
        """Find all agents using a given CLI."""
        return [e for e in self._entries.values() if e.cli_name == cli_name]

    def get_enabled(self) -> List[RegistryEntry]:
        """Get all enabled agents."""
        return [e for e in self._entries.values() if e.enabled]

    def list_all(self) -> List[RegistryEntry]:
        """List all registered agents."""
        return list(self._entries.values())

    def list_roles(self) -> List[str]:
        """List all unique roles across registered agents."""
        return list({e.role for e in self._entries.values()})

    def count(self) -> int:
        """Return the total number of registered agents."""
        return len(self._entries)

    # ===== Updates =====

    async def update(
        self,
        agent_id: str,
        **kwargs,
    ) -> Optional[RegistryEntry]:
        """Update an agent's configuration.

        Args:
            agent_id: The agent to update.
            **kwargs: Fields to update (name, cli_path, api_key, enabled, metadata, model_name).

        Returns:
            The updated entry, or None if not found.
        """
        entry = self._entries.get(agent_id)
        if not entry:
            return None

        updatable = {"name", "cli_path", "api_key", "enabled", "metadata", "model_name"}
        for key, value in kwargs.items():
            if key in updatable and hasattr(entry, key):
                setattr(entry, key, value)

        # Recreate adapter if cli_path or api_key changed
        if "cli_path" in kwargs or "api_key" in kwargs:
            old_adapter = self._instances.pop(agent_id, None)
            if old_adapter:
                await old_adapter.cleanup()
            new_adapter = await AdapterFactory.create_adapter(entry)
            if new_adapter:
                self._instances[agent_id] = new_adapter

        logger.info("Updated agent '%s' (id=%s)", entry.name, agent_id)
        return entry

    async def set_enabled(self, agent_id: str, enabled: bool) -> bool:
        """Enable or disable an agent."""
        entry = self._entries.get(agent_id)
        if not entry:
            return False
        entry.enabled = enabled
        logger.info("Agent '%s' %s", entry.name, "enabled" if enabled else "disabled")
        return True

    # ===== Health Monitoring =====

    async def check_health(
        self,
        agent_id: Optional[str] = None,
    ) -> Dict[str, HealthCheckResult]:
        """Run health checks on agents.

        Args:
            agent_id: If provided, check only this agent. Otherwise check all.

        Returns:
            Dict mapping agent_id → HealthCheckResult.
        """
        target_ids = [agent_id] if agent_id else list(self._instances.keys())
        results: Dict[str, HealthCheckResult] = {}

        async def check_one(aid: str) -> Tuple[str, HealthCheckResult]:
            adapter = self._instances.get(aid)
            if not adapter:
                return aid, HealthCheckResult(
                    status=AgentStatus.NOT_FOUND,
                    cli_name="unknown",
                    error_message=f"No adapter instance for {aid}",
                )
            result = await adapter.check_health()
            # Update cached health status
            if aid in self._entries:
                self._entries[aid].last_health_check = result
            return aid, result

        tasks = [check_one(aid) for aid in target_ids]
        gathered = await asyncio.gather(*tasks, return_exceptions=True)

        for item in gathered:
            if isinstance(item, Exception):
                logger.error("Health check error: %s", item)
                continue
            aid, result = item
            results[aid] = result

        return results

    def start_health_monitoring(self, interval_seconds: float = 60.0) -> None:
        """Start periodic health monitoring for all agents.

        Args:
            interval_seconds: How often to check health.
        """
        async def monitor_loop():
            while True:
                try:
                    await asyncio.sleep(interval_seconds)
                    await self.check_health()
                    unhealthy = [
                        aid for aid, e in self._entries.items()
                        if e.last_health_check and not e.last_health_check.is_healthy
                    ]
                    if unhealthy:
                        logger.warning("Unhealthy agents: %s", unhealthy)
                except asyncio.CancelledError:
                    break
                except Exception:
                    logger.exception("Health monitor error")

        if self._health_monitor_task and not self._health_monitor_task.done():
            self._health_monitor_task.cancel()

        self._health_monitor_task = asyncio.create_task(monitor_loop())
        logger.info("Health monitoring started (interval=%.1fs)", interval_seconds)

    def stop_health_monitoring(self) -> None:
        """Stop periodic health monitoring."""
        if self._health_monitor_task and not self._health_monitor_task.done():
            self._health_monitor_task.cancel()
            logger.info("Health monitoring stopped")

    # ===== Lifecycle Hooks =====

    def on_register(self, hook: callable) -> callable:
        """Register a callback invoked when an agent is registered."""
        self._on_register_hooks.append(hook)
        return hook

    def on_unregister(self, hook: callable) -> callable:
        """Register a callback invoked when an agent is unregistered."""
        self._on_unregister_hooks.append(hook)
        return hook

    # ===== Persistence =====

    async def _persist_entry(self, entry: RegistryEntry) -> None:
        """Persist a registry entry to the database."""
        if not self._db_session_factory:
            return
        try:
            from models.agent import AgentConfig
            async with self._db_session_factory() as session:
                session: AsyncSession
                config = AgentConfig(
                    agent_id=entry.agent_id,
                    name=entry.name,
                    role=entry.role,
                    cli_name=entry.cli_name,
                    model_name=entry.model_name,
                    cli_path=entry.cli_path,
                    enabled=entry.enabled,
                    metadata=entry.metadata,
                )
                session.add(config)
                await session.commit()
        except Exception as e:
            logger.error("Failed to persist agent '%s': %s", entry.agent_id, e)

    async def load_from_db(self) -> int:
        """Load agent configurations from the database.

        Returns:
            Number of agents loaded.
        """
        if not self._db_session_factory:
            logger.warning("No DB session factory configured, skipping load")
            return 0

        try:
            from models.agent import AgentConfig
            async with self._db_session_factory() as session:
                session: AsyncSession
                result = await session.execute(select(AgentConfig).where(AgentConfig.enabled == True))
                configs: List[AgentConfig] = result.scalars().all()

            loaded = 0
            for cfg in configs:
                try:
                    await self.register(
                        agent_id=cfg.agent_id,
                        name=cfg.name,
                        cli_name=cfg.cli_name,
                        role=cfg.role,
                        model_name=cfg.model_name,
                        cli_path=cfg.cli_path,
                        metadata=cfg.metadata or {},
                        persist=False,  # Already persisted
                    )
                    loaded += 1
                except ValueError:
                    logger.debug("Agent '%s' already registered, skipping", cfg.agent_id)
                except Exception as e:
                    logger.error("Failed to load agent '%s': %s", cfg.agent_id, e)

            logger.info("Loaded %d agents from database", loaded)
            return loaded
        except Exception as e:
            logger.exception("Failed to load agents from DB: %s", e)
            return 0

    # ===== Bulk Operations =====

    async def initialize_defaults(self) -> List[RegistryEntry]:
        """Register default agent configurations from settings."""
        defaults = getattr(settings, "DEFAULT_AGENTS", [])
        entries: List[RegistryEntry] = []

        for agent_cfg in defaults:
            try:
                entry = await self.register(
                    agent_id=agent_cfg.get("agent_id", f"default_{agent_cfg.get('cli_name', 'unknown')}"),
                    name=agent_cfg.get("name", agent_cfg.get("cli_name", "Unnamed")),
                    cli_name=agent_cfg.get("cli_name", "custom"),
                    role=agent_cfg.get("role", "developer"),
                    model_name=agent_cfg.get("model_name", "default"),
                    cli_path=agent_cfg.get("cli_path"),
                    api_key=agent_cfg.get("api_key"),
                    metadata=agent_cfg.get("metadata"),
                )
                entries.append(entry)
            except ValueError:
                logger.debug("Default agent '%s' already registered", agent_cfg.get("name", "unknown"))
            except Exception as e:
                logger.error("Failed to register default agent: %s", e)

        logger.info("Initialized %d default agents", len(entries))
        return entries

    async def shutdown(self) -> None:
        """Cleanup all agents and stop background tasks."""
        self.stop_health_monitoring()
        for agent_id, adapter in list(self._instances.items()):
            try:
                await adapter.cleanup()
            except Exception as e:
                logger.error("Cleanup failed for '%s': %s", agent_id, e)
        self._instances.clear()
        self._entries.clear()
        logger.info("AgentRegistry shutdown complete")
