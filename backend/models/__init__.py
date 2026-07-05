"""
AgentForge Data Models Package
===============================
SQLAlchemy ORM models for the AgentForge platform.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# Import models to register them with Base.metadata
from models.project import Project  # noqa: F401, E402
from models.agent import AgentConfig  # noqa: F401, E402
from models.task import Task  # noqa: F401, E402

__all__ = ["Base", "Project", "AgentConfig", "Task"]
