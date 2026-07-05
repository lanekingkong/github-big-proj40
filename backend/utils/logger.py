"""
Structured Logging Utility
==========================
Provides a structured JSON logger with dual output: file rotation and colored
console output. Designed for the AgentForge multi-agent platform where log
traceability across agents, tasks, and projects is critical.

Features:
- JSON-structured log output for machine parsing
- Colorized console output for human readability
- Automatic log file rotation (size-based)
- Context binding (project_id, agent_id, task_id) for traceability
- Configurable log levels per component
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ------------------------------------------------------------------
# Colored Console Formatter
# ------------------------------------------------------------------

class ColoredConsoleFormatter(logging.Formatter):
    """
    Colorized log formatter for terminal output.

    Color mapping:
        DEBUG   → Blue
        INFO    → Green
        WARNING → Yellow
        ERROR   → Red
        CRITICAL → Bold Red + White background
    """

    # ANSI color codes
    COLORS: dict[str, str] = {
        "DEBUG": "\033[36m",       # Cyan instead of blue for readability
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[1;37;41m",  # Bold White on Red
    }
    RESET: str = "\033[0m"
    DIM: str = "\033[2m"

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record with colorized output.

        Args:
            record: The log record to format.

        Returns:
            Colorized string representation.
        """
        color = self.COLORS.get(record.levelname, self.RESET)

        # Build prefix with timestamp and level
        timestamp = datetime.fromtimestamp(
            record.created, tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S")

        log_line = (
            f"{self.DIM}{timestamp}{self.RESET} "
            f"{color}{record.levelname:<8}{self.RESET} "
            f"{record.getMessage()}"
        )

        # Append exception info if present
        if record.exc_info:
            log_line += "\n" + self.DIM
            log_line += traceback.format_exc()
            log_line += self.RESET

        return log_line


# ------------------------------------------------------------------
# JSON Structured Formatter
# ------------------------------------------------------------------

class JSONLogFormatter(logging.Formatter):
    """
    Emits log records as JSON objects for machine consumption.

    Each log line is a valid JSON object with the following structure:
    {
        "timestamp": "ISO-8601",
        "level": "INFO",
        "logger": "module.name",
        "message": "Human-readable message",
        "context": { ... extra fields ... },
        "exception": "traceback if present"
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A single-line JSON string.
        """
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include extra context if available
        if hasattr(record, "context"):
            log_entry["context"] = record.context  # type: ignore[attr-defined]

        # Include exception traceback
        if record.exc_info:
            log_entry["exception"] = traceback.format_exc()

        return json.dumps(log_entry, ensure_ascii=False, default=str)


# ------------------------------------------------------------------
# Context-Aware Logger Adapter
# ------------------------------------------------------------------

class ContextLogger(logging.LoggerAdapter):
    """
    Logger adapter that supports binding structured context.

    Context fields (project_id, agent_id, task_id) are automatically
    included in JSON log output when using the JSON formatter.

    Usage:
        logger = get_logger(__name__)
        ctx_logger = logger.bind(project_id="abc-123", agent_id="xyz-456")
        ctx_logger.info("Agent started processing task")
    """

    def __init__(
        self,
        logger: logging.Logger,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the context logger.

        Args:
            logger: The underlying logger instance.
            extra: Initial context dictionary.
        """
        super().__init__(logger, extra or {})

    def process(
        self,
        msg: Any,
        kwargs: dict[str, Any],
    ) -> tuple[Any, dict[str, Any]]:
        """
        Inject extra context into the log record before emission.

        Args:
            msg: The log message.
            kwargs: Keyword arguments for the log call.

        Returns:
            Tuple of (message, kwargs) with context injected.
        """
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        kwargs["extra"].update(self.extra)
        return msg, kwargs

    def bind(self, **context: Any) -> ContextLogger:
        """
        Create a new ContextLogger with additional bound context.

        Args:
            **context: Key-value pairs to add to the context.

        Returns:
            A new ContextLogger with merged context.
        """
        new_extra = {**self.extra, **context}
        return ContextLogger(self.logger, new_extra)


# ------------------------------------------------------------------
# Logger Factory
# ------------------------------------------------------------------

# Cache of created loggers to avoid duplicate handler registrations
_logger_cache: dict[str, logging.Logger] = {}

# Default configuration
_DEFAULT_LOG_DIR: Path = Path(os.environ.get(
    "AGENTFORGE_LOG_DIR",
    str(Path.home() / ".agentforge" / "logs"),
))
_DEFAULT_LOG_LEVEL: int = logging.INFO
_DEFAULT_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB per log file
_DEFAULT_BACKUP_COUNT: int = 5


def configure_logging(
    log_dir: str | Path | None = None,
    level: int | str = _DEFAULT_LOG_LEVEL,
    console_enabled: bool = True,
    file_enabled: bool = True,
) -> None:
    """
    Configure global logging settings for all AgentForge loggers.

    Args:
        log_dir: Directory for log files. Defaults to ~/.agentforge/logs.
        level: Default log level (int or string name).
        console_enabled: Whether to enable colored console output.
        file_enabled: Whether to enable JSON file output with rotation.
    """
    global _DEFAULT_LOG_DIR, _DEFAULT_LOG_LEVEL
    if log_dir:
        _DEFAULT_LOG_DIR = Path(log_dir)
    if isinstance(level, str):
        _DEFAULT_LOG_LEVEL = getattr(logging, level.upper(), logging.INFO)
    else:
        _DEFAULT_LOG_LEVEL = level

    _DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger("agentforge")
    root_logger.setLevel(_DEFAULT_LOG_LEVEL)
    root_logger.handlers.clear()

    # Console handler (colored)
    if console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(_DEFAULT_LOG_LEVEL)
        console_handler.setFormatter(ColoredConsoleFormatter())
        root_logger.addHandler(console_handler)

    # File handler (JSON, rotating)
    if file_enabled:
        file_path = _DEFAULT_LOG_DIR / "agentforge.log"
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(file_path),
            maxBytes=_DEFAULT_MAX_BYTES,
            backupCount=_DEFAULT_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(_DEFAULT_LOG_LEVEL)
        file_handler.setFormatter(JSONLogFormatter())
        root_logger.addHandler(file_handler)


def get_logger(
    name: str,
    log_dir: str | Path | None = None,
) -> ContextLogger:
    """
    Get or create a structured context-aware logger.

    Automatically inherits global configuration. The returned logger
    supports .bind() for attaching structured context.

    Args:
        name: Logger name, typically __name__ of the calling module.
        log_dir: Optional override for log directory.

    Returns:
        A ContextLogger instance ready for structured logging.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Service started")
        >>> ctx = logger.bind(project_id="p1", agent_id="a1")
        >>> ctx.info("Agent assigned to task")
    """
    if name not in _logger_cache:
        # Ensure root is configured on first call
        root = logging.getLogger("agentforge")
        if not root.handlers:
            configure_logging(log_dir=log_dir)

        # Create module-specific logger
        module_logger = logging.getLogger(f"agentforge.{name}")
        module_logger.setLevel(_DEFAULT_LOG_LEVEL)
        module_logger.propagate = False  # Avoid duplicate output

        # Add handlers if none present (inherits root's config)
        if not module_logger.handlers:
            # Console
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(_DEFAULT_LOG_LEVEL)
            console_handler.setFormatter(ColoredConsoleFormatter())
            module_logger.addHandler(console_handler)

            # File
            file_path = _DEFAULT_LOG_DIR / "agentforge.log"
            file_handler = logging.handlers.RotatingFileHandler(
                filename=str(file_path),
                maxBytes=_DEFAULT_MAX_BYTES,
                backupCount=_DEFAULT_BACKUP_COUNT,
                encoding="utf-8",
            )
            file_handler.setLevel(_DEFAULT_LOG_LEVEL)
            file_handler.setFormatter(JSONLogFormatter())
            module_logger.addHandler(file_handler)

        _logger_cache[name] = module_logger

    return ContextLogger(_logger_cache[name])


# ------------------------------------------------------------------
# Convenience Functions
# ------------------------------------------------------------------

def log_exception(
    logger: ContextLogger,
    exc: Exception,
    message: str = "An error occurred",
) -> None:
    """
    Log an exception with full traceback at ERROR level.

    Args:
        logger: The logger to use.
        exc: The exception instance.
        message: Prefix message for the error.
    """
    logger.error(f"{message}: {exc}", exc_info=True)


def log_agent_event(
    logger: ContextLogger,
    agent_id: str,
    event: str,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Log an agent lifecycle event with structured details.

    Args:
        logger: The logger to use.
        agent_id: The agent's identifier.
        event: Event name (e.g., 'registered', 'health_check_failed').
        details: Additional event data.
    """
    ctx_logger = logger.bind(agent_id=agent_id)
    ctx_logger.info(
        f"Agent event: {event}",
        extra={
            "event_type": "agent_event",
            "event_name": event,
            "details": details or {},
        },
    )
