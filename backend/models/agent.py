"""
Agent Configuration Model
==========================
SQLAlchemy model representing an AI agent configuration within the AgentForge platform.
Each agent has a defined role, underlying CLI runtime, tool permissions, and model settings.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from models.project import Project
    from models.task import Task


# ===== Agent Role Definitions =====
class AgentRole:
    """
    Standard agent roles in the AgentForge collaboration workflow.

    Each role represents a distinct phase in the development pipeline:
    - DEVELOPER: Generates and writes code
    - REVIEWER: Inspects code for bugs, style, and architecture issues
    - FIXER: Resolves issues flagged by the reviewer
    - TESTER: Runs test suites and validates functionality
    - DEPLOYER: Packages and deploys the project
    """
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    FIXER = "fixer"
    TESTER = "tester"
    DEPLOYER = "deployer"

    ALL_ROLES = [DEVELOPER, REVIEWER, FIXER, TESTER, DEPLOYER]

    # Role descriptions for UI display
    DESCRIPTIONS = {
        DEVELOPER: "Generates and writes source code based on requirements and review feedback",
        REVIEWER: "Inspects code changes for bugs, style violations, security issues, and architectural problems",
        FIXER: "Resolves bugs and issues identified by the reviewer agent",
        TESTER: "Runs test suites, generates new tests, and validates functionality",
        DEPLOYER: "Packages the application and deploys to target environments",
    }

    # Role-to-CLI compatibility matrix
    # Maps each supported CLI to its best-suited roles
    CLI_ROLE_MATRIX = {
        "claude": [DEVELOPER, REVIEWER, FIXER],
        "codex": [DEVELOPER, FIXER],
        "trae": [DEVELOPER, TESTER],
        "openclaw": [REVIEWER, FIXER],
        "hermess": [DEVELOPER, DEPLOYER],
        "opencode": [DEVELOPER, FIXER],
        "gemini": [REVIEWER, TESTER],
    }

    @classmethod
    def get_supported_roles(cls, cli_name: str) -> List[str]:
        """Get the list of roles supported by a given CLI."""
        return cls.CLI_ROLE_MATRIX.get(cli_name, [])

    @classmethod
    def get_cli_for_role(cls, role: str) -> List[str]:
        """Get all CLIs that support a given role."""
        return [cli for cli, roles in cls.CLI_ROLE_MATRIX.items() if role in roles]

    @classmethod
    def get_color(cls, role: str) -> str:
        """Get the display color for a role."""
        colors = {
            cls.DEVELOPER: "#3B82F6",  # Blue
            cls.REVIEWER: "#8B5CF6",   # Purple
            cls.FIXER: "#F59E0B",      # Amber
            cls.TESTER: "#22C55E",     # Green
            cls.DEPLOYER: "#06B6D4",   # Cyan
        }
        return colors.get(role, "#6B7280")


class AgentConfig(Base):
    """
    Configuration for an individual AI agent within a project.

    Each AgentConfig binds:
    - A specific CLI runtime (claude, codex, gemini, etc.)
    - A role assignment (developer, reviewer, fixer, tester, deployer)
    - Tool access permissions
    - Model and API configuration
    """

    __tablename__ = "agent_configs"

    # ===== Primary Key =====
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )

    # ===== Identity =====
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Human-readable agent display name"
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Agent role: developer|reviewer|fixer|tester|deployer"
    )

    # ===== CLI Runtime =====
    cli_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Underlying CLI runtime: claude|codex|trae|openclaw|hermess|opencode|gemini"
    )
    cli_path: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        doc="Filesystem path to the CLI executable (auto-detected if not specified)"
    )

    # ===== Model Configuration =====
    model_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="AI model identifier (e.g., claude-sonnet-4-20250514, gemini-2.5-pro)"
    )
    max_context_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=200000,
        doc="Maximum context window size in tokens"
    )
    temperature: Mapped[float] = mapped_column(
        Integer,  # We store as integer but conceptual value is float for DB compat
        nullable=False,
        default=0,
        doc="Model temperature (0-1, stored as integer x100 for SQLite compat)"
    )  # Note: In production, use proper Decimal type; integer placeholder for MVP

    # ===== Authentication =====
    api_key_env_var: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Environment variable name containing the API key"
    )
    api_base_url: Mapped[Optional[str]] = mapped_column(
        String(2048),
        nullable=True,
        doc="Custom API base URL for self-hosted or proxy setups"
    )

    # ===== Tool Access =====
    allowed_tools: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON array of tool names this agent is permitted to use"
    )
    denied_tools: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON array of explicitly denied tool names"
    )

    # ===== Review Configuration (Reviewer role only) =====
    review_rules: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON array of review rule identifiers (security_check, style_lint, etc.)"
    )
    review_severity_threshold: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        doc="Minimum severity to flag: info|warning|error|critical"
    )

    # ===== Test Configuration (Tester role only) =====
    test_framework: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Test framework to use: pytest|jest|junit|vitest|etc."
    )
    test_command: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        doc="Custom command to execute test suite"
    )
    auto_generate_tests: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether the tester should auto-generate missing tests"
    )

    # ===== Deploy Configuration (Deployer role only) =====
    deploy_target: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Deployment target: docker|kubernetes|heroku|vercel|aws|gcp|azure|custom"
    )
    deploy_config: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON deployment configuration (Dockerfile path, k8s manifests, etc.)"
    )

    # ===== State =====
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether this agent is active in the project"
    )
    is_healthy: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Agent health status (checked on startup and periodically)"
    )
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last successful heartbeat timestamp"
    )

    # ===== Timestamps =====
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ===== Foreign Keys =====
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key to the parent project",
    )

    # ===== Relationships =====
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="agents",
    )
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="assigned_agent",
        foreign_keys="Task.agent_id",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<AgentConfig(id={self.id}, name='{self.name}', role='{self.role}', cli='{self.cli_name}')>"

    def to_dict(self) -> dict:
        """Convert agent config to a dictionary for API responses."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "role_description": AgentRole.DESCRIPTIONS.get(self.role, ""),
            "role_color": AgentRole.get_color(self.role),
            "cli_name": self.cli_name,
            "model_name": self.model_name,
            "max_context_tokens": self.max_context_tokens,
            "is_active": self.is_active,
            "is_healthy": self.is_healthy,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
