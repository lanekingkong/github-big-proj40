"""
Project Service
===============
Business logic layer for project management in the AgentForge platform.

Handles:
- Project lifecycle (create, read, update, delete)
- Execution orchestration (trigger task pipelines, manage state transitions)
- Status tracking and log aggregation across multi-agent workflows
"""

from __future__ import annotations

import asyncio
import datetime
import uuid
from typing import Any

from core.orchestrator import Orchestrator
from core.pipeline import Pipeline
from core.task_scheduler import TaskScheduler
from models.project import Project, ProjectStatus
from models.task import Task, TaskStatus
from utils.logger import get_logger

__all__ = ["ProjectService"]

logger = get_logger(__name__)


class ProjectService:
    """
    Service for managing project CRUD operations and execution lifecycle.

    Coordinates between the database, orchestrator, pipeline engine,
    and task scheduler to provide a unified API for project management.
    """

    def __init__(self) -> None:
        """Initialize the project service with orchestrator and scheduler instances."""
        self._orchestrator = Orchestrator()
        self._pipeline = Pipeline()
        self._scheduler = TaskScheduler()
        # In-memory store for demo; production uses database session
        self._projects: dict[uuid.UUID, Project] = {}
        self._execution_locks: dict[uuid.UUID, asyncio.Lock] = {}

    # ------------------------------------------------------------------
    # CRUD Operations
    # ------------------------------------------------------------------

    async def list_projects(
        self,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Project]:
        """
        List projects with optional filtering and pagination.

        Args:
            status: Filter by project status value.
            search: Filter by name/description substring (case-insensitive).
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of matching Project model instances.
        """
        projects = list(self._projects.values())

        if status:
            projects = [p for p in projects if p.status.value == status]

        if search:
            search_lower = search.lower()
            projects = [
                p for p in projects
                if search_lower in p.name.lower()
                or (p.description and search_lower in p.description.lower())
            ]

        return projects[offset : offset + limit]

    async def count_projects(
        self,
        status: str | None = None,
        search: str | None = None,
    ) -> int:
        """
        Count projects matching the given filters.

        Args:
            status: Filter by project status.
            search: Filter by name/description substring.

        Returns:
            Total count of matching projects.
        """
        projects = await self.list_projects(status=status, search=search, limit=999999)
        return len(projects)

    async def create_project(
        self,
        payload: Any,  # ProjectCreateRequest in production
    ) -> Project | None:
        """
        Create a new project from the request payload.

        Args:
            payload: Project creation request with name, description, agent configs,
                     and task definitions.

        Returns:
            The created Project instance, or None if validation fails.
        """
        try:
            project = Project(
                id=uuid.uuid4(),
                name=payload.name,
                description=getattr(payload, "description", None),
                status=ProjectStatus.DRAFT,
                agent_team=getattr(payload, "agent_team", []),
                pipeline_config=getattr(payload, "pipeline_config", None),
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            )
            self._projects[project.id] = project
            logger.info(f"Project created: {project.id} ({project.name})")
            return project
        except Exception as exc:
            logger.error(f"Failed to create project: {exc}")
            return None

    async def get_project(self, project_id: uuid.UUID) -> Project | None:
        """
        Retrieve a project by its unique identifier.

        Args:
            project_id: The project's UUID.

        Returns:
            The Project instance or None if not found.
        """
        return self._projects.get(project_id)

    async def update_project(
        self,
        project_id: uuid.UUID,
        payload: Any,  # ProjectUpdateRequest in production
    ) -> Project | None:
        """
        Update an existing project's configuration.

        Args:
            project_id: The project's UUID.
            payload: Fields to update.

        Returns:
            The updated Project instance or None if not found.
        """
        project = self._projects.get(project_id)
        if project is None:
            return None

        if hasattr(payload, "name") and payload.name is not None:
            project.name = payload.name
        if hasattr(payload, "description") and payload.description is not None:
            project.description = payload.description
        if hasattr(payload, "agent_team") and payload.agent_team is not None:
            project.agent_team = payload.agent_team
        if hasattr(payload, "pipeline_config") and payload.pipeline_config is not None:
            project.pipeline_config = payload.pipeline_config

        project.updated_at = datetime.datetime.utcnow()
        logger.info(f"Project updated: {project_id}")
        return project

    async def delete_project(self, project_id: uuid.UUID) -> bool:
        """
        Delete a project and all its associated resources.

        Args:
            project_id: The project's UUID.

        Returns:
            True if deleted, False if not found.
        """
        if project_id not in self._projects:
            return False
        del self._projects[project_id]
        self._execution_locks.pop(project_id, None)
        logger.info(f"Project deleted: {project_id}")
        return True

    # ------------------------------------------------------------------
    # Execution Orchestration
    # ------------------------------------------------------------------

    async def execute_project(
        self,
        project_id: uuid.UUID,
    ) -> Any | None:  # ProjectExecuteResponse in production
        """
        Trigger execution of a project's task pipeline.

        Validates that the project is in an executable state, creates
        an execution lock to prevent concurrent runs, and delegates
        to the Orchestrator for actual execution.

        Args:
            project_id: The project's UUID.

        Returns:
            Execution response with run ID and initial status, or None
            if the project cannot be executed.
        """
        project = self._projects.get(project_id)
        if project is None:
            return None

        if project.status not in (ProjectStatus.DRAFT, ProjectStatus.PENDING, ProjectStatus.FAILED):
            logger.warning(f"Project {project_id} is not executable (status={project.status})")
            return None

        # Create or reuse execution lock
        if project_id not in self._execution_locks:
            self._execution_locks[project_id] = asyncio.Lock()

        lock = self._execution_locks[project_id]
        if lock.locked():
            logger.warning(f"Project {project_id} is already executing")
            return None

        async with lock:
            # Transition to running state
            project.status = ProjectStatus.RUNNING
            project.updated_at = datetime.datetime.utcnow()

            run_id = uuid.uuid4()
            logger.info(f"Project execution started: {project_id}, run_id={run_id}")

            try:
                # Execute via orchestrator (non-blocking in production,
                # fire-and-forget with status polling)
                await self._orchestrator.execute_project(
                    project=project,
                    run_id=run_id,
                )
            except Exception as exc:
                logger.error(f"Project execution failed: {project_id}, error={exc}")
                project.status = ProjectStatus.FAILED
                project.updated_at = datetime.datetime.utcnow()
                return None

        # Return execution metadata
        return type(
            "ExecuteResponse",
            (),
            {
                "run_id": run_id,
                "project_id": project_id,
                "status": "running",
                "started_at": datetime.datetime.utcnow().isoformat(),
            },
        )()

    async def get_project_status(
        self,
        project_id: uuid.UUID,
    ) -> Any | None:  # ProjectStatusResponse in production
        """
        Query the current execution status and progress of a project.

        Args:
            project_id: The project's UUID.

        Returns:
            Status response with progress percentage, current task, and timestamps,
            or None if the project is not found.
        """
        project = self._projects.get(project_id)
        if project is None:
            return None

        return type(
            "StatusResponse",
            (),
            {
                "project_id": project_id,
                "name": project.name,
                "status": project.status.value,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
            },
        )()

    async def get_project_logs(
        self,
        project_id: uuid.UUID,
        tail: int = 200,
        level: str | None = None,
    ) -> Any | None:  # ProjectLogResponse in production
        """
        Retrieve execution logs for a project.

        Args:
            project_id: The project's UUID.
            tail: Number of most recent log lines to return.
            level: Filter by log level (DEBUG, INFO, WARNING, ERROR).

        Returns:
            Log response with log entries, or None if project not found.
        """
        project = self._projects.get(project_id)
        if project is None:
            return None

        # In production, fetch from log storage
        return type(
            "LogResponse",
            (),
            {
                "project_id": project_id,
                "entries": [],
                "total": 0,
                "tail": tail,
            },
        )()
