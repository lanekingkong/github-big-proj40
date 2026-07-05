"""
Base Agent Adapter
===================
Abstract base class defining the unified interface for all AI Agent CLI adapters.
All agent adapters (Claude Code, Codex, Gemini CLI, OpenCode, etc.) must implement
this interface to ensure consistent interaction with the orchestration engine.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# =============================================================================
# Data Types
# =============================================================================

class AgentStatus(Enum):
    """Health status of an agent adapter."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    CONFIG_ERROR = "config_error"
    TIMEOUT = "timeout"


class TaskResultStatus(Enum):
    """Outcome status of a task execution."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class HealthCheckResult:
    """Result of an agent health check."""
    status: AgentStatus
    cli_name: str
    cli_version: Optional[str] = None
    cli_path: Optional[str] = None
    model_name: Optional[str] = None
    error_message: Optional[str] = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_healthy(self) -> bool:
        return self.status == AgentStatus.HEALTHY


@dataclass
class ExecutionContext:
    """Context passed to agents for task execution."""
    project_path: Path
    workspace_path: Path
    task_id: str
    previous_results: List[Dict[str, Any]] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskInput:
    """Input specification for a task to be executed by an agent."""
    task_id: str
    title: str
    description: str
    task_type: str  # development, review, fix, test, deploy
    agent_role: str  # developer, reviewer, fixer, tester, deployer
    priority: int = 1
    files_to_modify: Optional[List[str]] = None
    context_documents: Optional[List[str]] = None
    timeout_seconds: int = 600
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Result of a task execution by an agent."""
    task_id: str
    status: TaskResultStatus
    agent_name: str
    agent_role: str
    output: Optional[str] = None
    summary: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time_seconds: Optional[float] = None
    token_usage: Optional[Dict[str, int]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_successful(self) -> bool:
        return self.status in (TaskResultStatus.SUCCESS, TaskResultStatus.PARTIAL_SUCCESS)


@dataclass
class ReviewComment:
    """A single review comment from a reviewer agent."""
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    severity: str = "info"  # info, warning, error, critical
    category: str = "style"  # style, bug, security, performance, architecture, docs
    message: str = ""
    suggestion: Optional[str] = None
    rule_id: Optional[str] = None


@dataclass
class ReviewResult:
    """Complete review result from a reviewer agent."""
    task_id: str
    agent_name: str
    overall_score: float = 0.0  # 0.0 - 10.0
    is_approved: bool = False
    comments: List[ReviewComment] = field(default_factory=list)
    summary: Optional[str] = None
    suggestion_for_fixer: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Abstract Base Class
# =============================================================================

class BaseAgentAdapter(ABC):
    """
    Abstract base class for all AI Agent adapters.

    Each concrete adapter wraps a specific AI coding CLI tool and provides
    a unified interface for the orchestration engine to interact with it.

    Subclassing Requirements:
        - Implement ALL abstract methods.
        - Handle CLI not found / not installed gracefully (return UNHEALTHY).
        - Handle authentication failures (return UNAUTHORIZED).
        - Implement timeout handling (return TIMEOUT).
        - Stream output asynchronously where applicable.

    Concurrency Note:
        All methods are designed to be async. Subprocess interaction should
        use asyncio subprocess rather than blocking calls.

    Attributes:
        name: Human-readable adapter name.
        cli_name: The CLI command name (e.g., "claude", "codex").
        cli_path: Optional custom path to the CLI binary.
        role: The agent role this instance is assigned to.
        model_name: The AI model identifier to use.
        config: Arbitrary configuration dict for adapter-specific settings.
    """

    def __init__(
        self,
        name: str,
        cli_name: str,
        role: str,
        model_name: str,
        cli_path: Optional[Path] = None,
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.cli_name = cli_name
        self.role = role
        self.model_name = model_name
        self.cli_path = cli_path
        self._api_key = api_key
        self.config = config or {}

        # Runtime state
        self._is_running: bool = False
        self._current_task_id: Optional[str] = None
        self._cancel_event: Optional[asyncio.Event] = None
        self._active_processes: Set[asyncio.subprocess.Process] = set()

        logger.info(
            "Initialized %s adapter (name=%s, role=%s, model=%s)",
            cli_name, name, role, model_name,
        )

    # ===== Abstract Methods =====

    @abstractmethod
    async def check_health(self) -> HealthCheckResult:
        """
        Verify that the agent CLI is installed, configured, and responsive.

        Should:
        1. Check that the CLI binary exists and is executable.
        2. Run a minimal smoke test (e.g., `--version` or a trivial prompt).
        3. Verify API key / authentication if applicable.

        Returns:
            HealthCheckResult with detailed status information.
        """
        ...

    @abstractmethod
    async def execute_task(
        self,
        task_input: TaskInput,
        context: ExecutionContext,
    ) -> TaskResult:
        """
        Execute a single task using the agent CLI.

        Args:
            task_input: The task specification (title, description, type, etc.).
            context: Execution context (workspace path, previous results, etc.).

        Returns:
            TaskResult with the agent's output, status, and metrics.

        Raises:
            AgentTimeoutError: If the task exceeds its timeout.
            AgentExecutionError: If the CLI process fails unexpectedly.
        """
        ...

    @abstractmethod
    async def review_code(
        self,
        task_input: TaskInput,
        context: ExecutionContext,
        review_rules: Optional[List[str]] = None,
    ) -> ReviewResult:
        """
        Review code changes and produce structured review feedback.

        Args:
            task_input: The review task specification.
            context: Execution context including the diff/files to review.
            review_rules: Optional list of review rule IDs to apply.

        Returns:
            ReviewResult with scored review, comments, and fixer suggestions.
        """
        ...

    @abstractmethod
    async def stream_output(
        self,
        task_id: str,
        context: ExecutionContext,
    ) -> AsyncIterator[str]:
        """
        Stream real-time output from a running task.

        Args:
            task_id: The task to stream output for.
            context: Execution context.

        Yields:
            Chunks of output text as they become available.
        """
        ...

    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """
        Request cancellation of a running task.

        Args:
            task_id: The task to cancel.

        Returns:
            True if cancellation was successful, False otherwise.
        """
        ...

    # ===== Concrete Helper Methods =====

    async def _run_subprocess(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: float = 600.0,
        capture_stderr: bool = True,
    ) -> tuple[int, str, str]:
        """
        Run a subprocess command asynchronously with timeout.

        Args:
            cmd: The command and arguments as a list.
            cwd: Working directory for the subprocess.
            env: Environment variables (merged with current env).
            timeout_seconds: Timeout for the subprocess.
            capture_stderr: Whether to capture stderr separately.

        Returns:
            Tuple of (return_code, stdout, stderr).

        Raises:
            asyncio.TimeoutError: If the subprocess exceeds timeout_seconds.
        """
        merged_env = {**__import__('os').environ, **(env or {})}
        if self._api_key:
            merged_env[self._get_api_key_env_var()] = self._api_key

        logger.debug("Running subprocess: %s (cwd=%s)", " ".join(cmd), cwd or ".")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE if capture_stderr else asyncio.subprocess.DEVNULL,
        )
        self._active_processes.add(process)

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds,
            )
            stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""
            return process.returncode or 0, stdout_str, stderr_str
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            logger.warning("Subprocess timed out after %.1fs: %s", timeout_seconds, " ".join(cmd))
            raise
        finally:
            self._active_processes.discard(process)

    async def _check_cli_installed(self) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Check if the CLI binary is installed and get its version.

        Returns:
            Tuple of (is_installed, version_string, error_message).
        """
        cli_cmd = str(self.cli_path) if self.cli_path else self.cli_name
        try:
            code, stdout, stderr = await self._run_subprocess(
                [cli_cmd, "--version"],
                timeout_seconds=10.0,
            )
            if code == 0 and stdout.strip():
                return True, stdout.strip().split("\n")[0], None
            return False, None, stderr.strip() or "Unknown error"
        except FileNotFoundError:
            return False, None, f"CLI '{self.cli_name}' not found in PATH"
        except asyncio.TimeoutError:
            return False, None, f"Version check timed out for CLI '{self.cli_name}'"

    async def _perform_smoke_test(self) -> tuple[bool, Optional[str]]:
        """
        Run a minimal smoke test to verify the agent is functional.

        Returns:
            Tuple of (passed, error_message).
        """
        try:
            result = await self.execute_task(
                TaskInput(
                    task_id="smoke_test",
                    title="Smoke Test",
                    description="Respond with 'OK'.",
                    task_type="development",
                    agent_role=self.role,
                    timeout_seconds=30,
                ),
                ExecutionContext(
                    project_path=Path("."),
                    workspace_path=Path("."),
                    task_id="smoke_test",
                ),
            )
            return result.is_successful, None if result.is_successful else result.errors[0] if result.errors else "No output"
        except Exception as e:
            return False, str(e)

    def _get_api_key_env_var(self) -> str:
        """Get the environment variable name for this adapter's API key."""
        cli_env_vars = {
            "claude": "ANTHROPIC_API_KEY",
            "codex": "OPENAI_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "trae": "TRAE_API_KEY",
            "openclaw": "OPENCLAW_API_KEY",
            "hermess": "HERMESS_API_KEY",
            "opencode": "OPENCODE_API_KEY",
        }
        return cli_env_vars.get(self.cli_name, f"{self.cli_name.upper()}_API_KEY")

    async def cleanup(self) -> None:
        """Cleanup resources: kill remaining subprocesses."""
        for process in list(self._active_processes):
            if process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
        self._active_processes.clear()
        logger.debug("Cleaned up %s adapter resources", self.name)


# =============================================================================
# Custom Exceptions
# =============================================================================

class AgentAdapterError(Exception):
    """Base exception for agent adapter errors."""
    def __init__(self, message: str, adapter_name: str = ""):
        super().__init__(message)
        self.adapter_name = adapter_name


class AgentTimeoutError(AgentAdapterError):
    """Raised when an agent task exceeds its timeout."""
    def __init__(self, task_id: str, timeout_seconds: float, adapter_name: str = ""):
        super().__init__(
            f"Task '{task_id}' timed out after {timeout_seconds:.1f}s",
            adapter_name,
        )
        self.task_id = task_id
        self.timeout_seconds = timeout_seconds


class AgentExecutionError(AgentAdapterError):
    """Raised when an agent CLI process fails."""
    def __init__(self, task_id: str, exit_code: int, stderr: str, adapter_name: str = ""):
        super().__init__(
            f"Task '{task_id}' failed with exit code {exit_code}: {stderr[:500]}",
            adapter_name,
        )
        self.task_id = task_id
        self.exit_code = exit_code
        self.stderr = stderr


class AgentNotFoundError(AgentAdapterError):
    """Raised when an agent CLI is not found."""
    def __init__(self, cli_name: str, adapter_name: str = ""):
        super().__init__(f"Agent CLI '{cli_name}' not found", adapter_name)
        self.cli_name = cli_name


class AgentAuthenticationError(AgentAdapterError):
    """Raised when agent authentication fails."""
    def __init__(self, cli_name: str, adapter_name: str = ""):
        super().__init__(f"Authentication failed for '{cli_name}'", adapter_name)
        self.cli_name = cli_name
