"""
Project Model
==============
SQLAlchemy model representing a user project in AgentForge.
A project is the top-level entity that ties together agents, tasks, and workflows.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text, DateTime, Enum as SAEnum, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from models.agent import AgentConfig
    from models.task import Task


class ProjectStatus:
    """Project lifecycle status constants."""
    CREATED = "created"
    CONFIGURING = "configuring"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class Project(Base):
    """
    Represents a user project managed by AgentForge.

    A project contains:
    - A git repository path where agent work happens
    - A description of what needs to be built
    - An assigned team of agents with specific roles
    - Associated tasks that represent work items
    - Workflow state tracking for the overall project lifecycle
    """

    __tablename__ = "projects"

    # ===== Primary Key =====
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )

    # ===== Core Fields =====
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Human-readable project name"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Project description / requirements specification"
    )
    repository_path: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        doc="Local filesystem path to the git repository"
    )
    repository_url: Mapped[Optional[str]] = mapped_column(
        String(2048),
        nullable=True,
        doc="Remote git repository URL (GitHub, GitLab, etc.)"
    )

    # ===== Status & Workflow =====
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ProjectStatus.CREATED,
        doc="Current project lifecycle status"
    )
    current_phase: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Current workflow phase (development/review/testing/deployment)"
    )
    iteration_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of review-fix-test iterations completed"
    )

    # ===== Configuration =====
    workflow_config: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON configuration for the project workflow pipeline"
    )
    agent_team_config: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON configuration mapping agent IDs to roles"
    )
    environment_vars: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON key-value pairs for project-specific environment variables"
    )

    # ===== Metadata =====
    language: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Primary programming language of the project"
    )
    framework: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Primary framework used (e.g., React, FastAPI, Django)"
    )
    tags: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Comma-separated tags for project categorization"
    )

    # ===== Timestamps =====
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="UTC timestamp when the project was created"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="UTC timestamp of last update"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="UTC timestamp when workflow execution started"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="UTC timestamp when project was completed or failed"
    )

    # ===== Relationships =====
    agents: Mapped[List["AgentConfig"]] = relationship(
        "AgentConfig",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"

    def to_dict(self) -> dict:
        """Convert project to a dictionary for API responses."""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "repository_path": self.repository_path,
            "repository_url": self.repository_url,
            "status": self.status,
            "current_phase": self.current_phase,
            "iteration_count": self.iteration_count,
            "language": self.language,
            "framework": self.framework,
            "tags": self.tags.split(",") if self.tags else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
