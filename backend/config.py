"""
AgentForge Backend Configuration
=================================
Centralized configuration management for the FastAPI backend.
Reads from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ===== Application =====
    APP_NAME: str = Field(default="AgentForge", description="Application name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Enable debug mode")

    # ===== Server =====
    API_HOST: str = Field(default="127.0.0.1", description="API server host")
    API_PORT: int = Field(default=8765, description="API server port")
    CORS_ORIGINS: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,app://.",
        description="Comma-separated list of allowed CORS origins"
    )

    # ===== Database =====
    DB_PATH: str = Field(
        default="",
        description="SQLite database file path. Defaults to <data_dir>/agentforge.db"
    )

    @property
    def database_url(self) -> str:
        """Get the full database URL."""
        db_path = self.DB_PATH or str(Path(self.data_dir) / "agentforge.db")
        return f"sqlite+aiosqlite:///{db_path}"

    # ===== Directories =====
    DATA_DIR: str = Field(
        default="",
        description="Data directory for database and logs. Defaults to <user_data>/agentforge"
    )
    AGENT_REGISTRY_PATH: str = Field(
        default="",
        description="Path to agent registry YAML file. Defaults to <data_dir>/agent_registry.yaml"
    )
    WORKSPACE_DIR: str = Field(
        default="",
        description="Workspace directory for agent projects. Defaults to <data_dir>/workspace"
    )

    @property
    def data_dir(self) -> str:
        """Get the resolved data directory."""
        if self.DATA_DIR:
            return self.DATA_DIR
        if os.name == 'nt':
            base = os.environ.get('APPDATA', str(Path.home() / 'AppData' / 'Roaming'))
        elif os.name == 'posix':
            if 'darwin' in os.uname().sysname.lower():
                base = str(Path.home() / 'Library' / 'Application Support')
            else:
                base = os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))
        else:
            base = str(Path.home())
        return str(Path(base) / 'agentforge')

    @property
    def agent_registry_path(self) -> str:
        """Get the resolved agent registry path."""
        return self.AGENT_REGISTRY_PATH or str(Path(self.data_dir) / 'agent_registry.yaml')

    @property
    def workspace_dir(self) -> str:
        """Get the resolved workspace directory."""
        return self.WORKSPACE_DIR or str(Path(self.data_dir) / 'workspace')

    # ===== Logging =====
    LOG_LEVEL: str = Field(default="INFO", description="Logging level (DEBUG|INFO|WARNING|ERROR)")
    LOG_FORMAT: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        description="Log format string"
    )
    LOG_FILE: str = Field(
        default="",
        description="Log file path. Defaults to <data_dir>/agentforge.log"
    )

    @property
    def log_file(self) -> str:
        """Get the resolved log file path."""
        return self.LOG_FILE or str(Path(self.data_dir) / 'agentforge.log')

    # ===== Agent Configuration =====
    AGENT_TIMEOUT_SECONDS: int = Field(
        default=600, description="Default timeout for agent operations (seconds)"
    )
    AGENT_MAX_RETRIES: int = Field(
        default=3, description="Maximum retries for failed agent operations"
    )
    AGENT_MAX_CONCURRENT: int = Field(
        default=5, description="Maximum concurrent agent operations"
    )

    # ===== Workflow Configuration =====
    WORKFLOW_MAX_ITERATIONS: int = Field(
        default=10, description="Maximum review-fix-test loop iterations"
    )
    WORKFLOW_AUTO_APPROVE: bool = Field(
        default=False, description="Auto-approve review suggestions without user input"
    )

    # ===== Git Configuration =====
    GIT_USER_NAME: str = Field(default="AgentForge Bot", description="Git commit author name")
    GIT_USER_EMAIL: str = Field(default="bot@agentforge.local", description="Git commit author email")

    # ===== MCP Protocol =====
    MCP_ENABLED: bool = Field(default=True, description="Enable Model Context Protocol")
    MCP_SERVER_PORT: int = Field(default=8766, description="MCP server port")

    model_config = {
        "env_prefix": "AGENTFORGE_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# Singleton settings instance
settings = Settings()


def ensure_directories() -> None:
    """Ensure all required directories exist."""
    dirs_to_create = [
        settings.data_dir,
        settings.workspace_dir,
        Path(settings.data_dir) / 'logs',
        Path(settings.data_dir) / 'models',
        Path(settings.data_dir) / 'cache',
    ]
    for d in dirs_to_create:
        Path(d).mkdir(parents=True, exist_ok=True)
