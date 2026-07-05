"""
Task Model
===========
SQLAlchemy model representing an individual task within a project workflow.
Tasks flow through a state machine from pending through to completion or failure.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    String, Text, DateTime, Integer, Boolean, Float,
    ForeignKey, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from models.project import Project
    from models.agent import AgentConfig


# ===== Task State Machine =====
class TaskStatus:
    """
    Task lifecycle states.

    State Transitions:
        PENDING    → RUNNING
        RUNNING    → REVIEWING | FAILED
        REVIEWING  → FIXING | COMPLETED
        FIXING     → RUNNING | FAILED
        TESTING    → FIXING | COMPLETED | FAILED
        COMPLETED  → (terminal)
        FAILED     → PENDING (retry) | (terminal)
        CANCELLED  → (terminal)
    """
    PENDING = "pending"
    RUNNING = "running"
    REVIEWING = "reviewing"
    FIXING = "fixing"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    ALL_STATUSES = [PENDING, RUNNING, REVIEWING, FIXING, TESTING, COMPLETED, FAILED, CANCELLED]
    TERMINAL_STATUSES = [COMPLETED, FAILED, CANCELLED]
    ACTIVE_STATUSES = [PENDING, RUNNING, REVIEWING, FIXING, TESTING]

    # Valid transitions map
    TRANSITIONS = {
        PENDING: [RUNNING, CANCELLED],
        RUNNING: [REVIEWING, TESTING, FAILED, CANCELLED],
        REVIEWING: [FIXING, TESTING, COMPLETED, CANCELLED],
        FIXING: [RUNNING, TESTING, FAILED, CANCELLED],
        TESTING: [FIXING, COMPLETED, FAILED, CANCELLED],
        COMPLETED: [],  # Terminal
        FAILED: [PENDING, CANCELLED],  # Can retry or cancel
        CANCELLED: [],  # Terminal
    }

    @classmethod
    def is_valid_transition(cls, from_status: str, to_status: str) -> bool:
        """Check if a state transition is valid."""
        return to_status in cls.TRANSITIONS.get(from_status, [])

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """Check if a status is terminal."""
        return status in cls.TERMINAL_STATUSES

    @classmethod
    def is_active(cls, status: str) -> bool:
        """Check if a status represents an in-progress task."""
        return status in cls.ACTIVE_STATUSES

    @classmethod
    def get_color(cls, status: str) -> str:
        """Get display color for a status."""
        colors = {
            cls.PENDING: "#94A3B8",     # Gray
            cls.RUNNING: "#3B82F6",     # Blue
            cls.REVIEWING: "#8B5CF6",   # Purple
            cls.FIXING: "#F59E0B",      # Amber
            cls.TESTING: "#22C55E",     # Green
            cls.COMPLETED: "#10B981",   # Emerald
            cls.FAILED: "#EF4444",      # Red
            cls.CANCELLED: "#6B7280",   # Dark Gray
        }
        return colors.get(status, "#6B7280")

    @classmethod
    def get_label(cls, status: str) -> str:
        """Get human-readable label for a status."""
        labels = {
            cls.PENDING: "Pending",
            cls.RUNNING: "Running",
            cls.REVIEWING: "Under Review",
            cls.FIXING: "Fixing Issues",
            cls.TESTING: "Testing",
            cls.COMPLETED: "Completed",
            cls.FAILED: "Failed",
            cls.CANCELLED: "Cancelled",
        }
        return labels.get(status, status)


class TaskPriority:
    """Task priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

    @classmethod
    def get_label(cls, priority: int) -> str:
        labels = {0: "Low", 1: "Normal", 2: "High", 3: "Critical"}
        return labels.get(priority, "Unknown")


class Task(Base):
    """
    Represents an individual task in the AgentForge workflow.

    A task is a unit of work assigned to a specific agent role.
    Tasks flow through a state machine (pending → running → reviewing → ...)
    and carry their execution context, results, and error information.
    """

    __tablename__ = "tasks"

    # ===== Primary Key =====
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )

    # ===== Identity =====
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Short, descriptive task title"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed task description / instructions for the agent"
    )
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="development",
        doc="Task type: development|review|fix|test|deploy|documentation|refactor"
    )

    # ===== State =====
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TaskStatus.PENDING,
        doc="Current task status in the state machine"
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=TaskPriority.NORMAL,
        doc="Task priority (0=Low, 1=Normal, 2=High, 3=Critical)"
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of times this task has been retried"
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        doc="Maximum allowed retry attempts"
    )

    # ===== Execution Context =====
    agent_role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="The role required to execute this task (developer|reviewer|fixer|tester|deployer)"
    )
    context: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON execution context (file paths, related task IDs, environment info)"
    )

    # ===== Results =====
    result: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Task execution result / output (Markdown or plain text)"
    )
    result_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Brief summary of the task result"
    )
    result_artifacts: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON list of file paths generated or modified by this task"
    )
    metrics: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON metrics: lines changed, tests passed/failed, execution time, etc."
    )

    # ===== Review Data =====
    review_comments: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON array of review comments from the reviewer agent"
    )
    review_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Review score (0.0 - 10.0)"
    )

    # ===== Error Tracking =====
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if the task failed"
    )
    error_stacktrace: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Full error stacktrace for debugging"
    )
    error_category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Error category: syntax_error|runtime_error|test_failure|timeout|api_error|etc."
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
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When task execution started"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When task reached a terminal state"
    )
    duration_seconds: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Total execution duration in seconds"
    )
    deadline_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Optional deadline for the task"
    )

    # ===== Ordering =====
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Order within the parent project's task queue"
    )

    # ===== Foreign Keys =====
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key to the parent project",
    )
    agent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("agent_configs.agent_id", ondelete="SET NULL"),
        nullable=True,
        doc="Foreign key to the assigned agent (can be null if unassigned)",
    )
    parent_task_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("tasks.task_id", ondelete="SET NULL"),
        nullable=True,
        doc="Foreign key to parent task for subtask relationships",
    )

    # ===== Relationships =====
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="tasks",
    )
    assigned_agent: Mapped[Optional["AgentConfig"]] = relationship(
        "AgentConfig",
        back_populates="tasks",
        foreign_keys=[agent_id],
    )
    parent_task: Mapped[Optional["Task"]] = relationship(
        "Task",
        remote_side="Task.task_id",
        backref="subtasks",
        foreign_keys=[parent_task_id],
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title[:50]}', status='{self.status}')>"

    def to_dict(self) -> dict:
        """Convert task to a dictionary for API responses."""
        import json

        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "task_type": self.task_type,
            "status": self.status,
            "status_label": TaskStatus.get_label(self.status),
            "status_color": TaskStatus.get_color(self.status),
            "priority": self.priority,
            "priority_label": TaskPriority.get_label(self.priority),
            "agent_role": self.agent_role,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "result_summary": self.result_summary,
            "review_score": self.review_score,
            "error_message": self.error_message,
            "error_category": self.error_category,
            "duration_seconds": self.duration_seconds,
            "project_id": self.project_id,
            "agent_id": self.agent_id,
            "parent_task_id": self.parent_task_id,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
