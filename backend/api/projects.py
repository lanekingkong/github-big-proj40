"""
Project Management API
======================
REST endpoints for managing projects in the AgentForge platform.

Supports full CRUD operations, project execution orchestration,
status tracking, and log retrieval for transparency in multi-agent workflows.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from schemas.project import (
    ProjectCreateRequest,
    ProjectExecuteResponse,
    ProjectListResponse,
    ProjectLogResponse,
    ProjectResponse,
    ProjectStatusResponse,
    ProjectUpdateRequest,
)
from services.project_service import ProjectService

__all__ = ["router"]

router = APIRouter()


def get_project_service() -> ProjectService:
    """
    Dependency that provides the ProjectService singleton.

    Returns:
        ProjectService: The application-wide project service instance.
    """
    return ProjectService()


@router.get(
    "/",
    response_model=ProjectListResponse,
    summary="List all projects",
    description="Returns a paginated list of all projects with optional filtering by status and name search.",
)
async def list_projects(
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by project status: draft, pending, running, completed, failed, paused, cancelled",
    ),
    search: str | None = Query(
        None,
        description="Search projects by name or description (case-insensitive)",
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of projects to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    """Retrieve a filtered, paginated list of projects."""
    projects = await service.list_projects(
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    total = await service.count_projects(
        status=status_filter,
        search=search,
    )
    return ProjectListResponse(
        total=total,
        items=projects,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="Create a new project with specified name, description, agent team configuration, and task pipeline.",
)
async def create_project(
    payload: ProjectCreateRequest,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Create a new project."""
    project = await service.create_project(payload)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid project configuration",
        )
    return project


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details",
    description="Retrieve full project information, including agent assignments and task structure.",
)
async def get_project(
    project_id: uuid.UUID,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Fetch a single project by ID."""
    project = await service.get_project(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id '{project_id}' not found",
        )
    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project configuration",
    description="Modify an existing project's configuration, agent assignments, or task definitions.",
)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Update an existing project."""
    project = await service.update_project(project_id, payload)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id '{project_id}' not found",
        )
    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
    description="Permanently delete a project and all associated tasks and artifacts.",
)
async def delete_project(
    project_id: uuid.UUID,
    service: ProjectService = Depends(get_project_service),
) -> None:
    """Delete a project and its resources."""
    success = await service.delete_project(project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id '{project_id}' not found",
        )


@router.post(
    "/{project_id}/execute",
    response_model=ProjectExecuteResponse,
    summary="Execute a project",
    description="Trigger the execution of a project's task pipeline using the configured agent team.",
)
async def execute_project(
    project_id: uuid.UUID,
    service: ProjectService = Depends(get_project_service),
) -> ProjectExecuteResponse:
    """Start project execution."""
    result = await service.execute_project(project_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is already running or cannot be executed in its current state",
        )
    return result


@router.get(
    "/{project_id}/status",
    response_model=ProjectStatusResponse,
    summary="Get project execution status",
    description="Query the current execution status, progress percentage, and active tasks of a project.",
)
async def get_project_status(
    project_id: uuid.UUID,
    service: ProjectService = Depends(get_project_service),
) -> ProjectStatusResponse:
    """Retrieve live execution status of a project."""
    status_info = await service.get_project_status(project_id)
    if status_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id '{project_id}' not found",
        )
    return status_info


@router.get(
    "/{project_id}/logs",
    response_model=ProjectLogResponse,
    summary="Get project execution logs",
    description="Retrieve the complete execution log for a project, including agent outputs, errors, and timeline events.",
)
async def get_project_logs(
    project_id: uuid.UUID,
    tail: int = Query(
        200,
        ge=1,
        le=5000,
        description="Number of most recent log lines to return",
    ),
    level: str | None = Query(
        None,
        description="Filter by log level: DEBUG, INFO, WARNING, ERROR",
    ),
    service: ProjectService = Depends(get_project_service),
) -> ProjectLogResponse:
    """Retrieve execution logs for a project."""
    logs = await service.get_project_logs(
        project_id=project_id,
        tail=tail,
        level=level,
    )
    if logs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id '{project_id}' not found",
        )
    return logs
