"""
Agent Management API
====================
REST endpoints for managing AI Agents in the AgentForge platform.

Supports CRUD operations, status monitoring, and automatic agent discovery
through filesystem scanning and CLI compatibility checks.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from schemas.agent import (
    AgentCreateRequest,
    AgentListResponse,
    AgentResponse,
    AgentStatusResponse,
    AgentUpdateRequest,
)
from services.agent_service import AgentService

__all__ = ["router"]

router = APIRouter()


def get_agent_service() -> AgentService:
    """
    Dependency that provides the AgentService singleton.

    Returns:
        AgentService: The application-wide agent service instance.
    """
    return AgentService()  # In production, use DI container


@router.get(
    "/",
    response_model=AgentListResponse,
    summary="List all registered agents",
    description="Returns a paginated list of all agents with optional filtering by role, status, and adapter type.",
)
async def list_agents(
    role: str | None = Query(
        None,
        description="Filter by agent role: Developer, Reviewer, Fixer, Tester, Deployer",
    ),
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by agent status: idle, busy, error, offline",
    ),
    adapter: str | None = Query(
        None,
        description="Filter by adapter type: claude_code, codex, opencode, gemini_cli, custom",
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of agents to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: AgentService = Depends(get_agent_service),
) -> AgentListResponse:
    """Retrieve a filtered, paginated list of agents."""
    agents = await service.list_agents(
        role=role,
        status=status_filter,
        adapter=adapter,
        limit=limit,
        offset=offset,
    )
    total = await service.count_agents(
        role=role,
        status=status_filter,
        adapter=adapter,
    )
    return AgentListResponse(
        total=total,
        items=agents,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new agent",
    description="Register a new AI agent with its adapter configuration and capabilities.",
)
async def register_agent(
    payload: AgentCreateRequest,
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """Register a new agent in the system."""
    agent = await service.register_agent(payload)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent with the same name or adapter path already exists",
        )
    return agent


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent details",
    description="Retrieve detailed information about a specific agent.",
)
async def get_agent(
    agent_id: uuid.UUID,
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """Fetch a single agent by ID."""
    agent = await service.get_agent(agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id '{agent_id}' not found",
        )
    return agent


@router.patch(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Update agent configuration",
    description="Update an existing agent's configuration and parameters.",
)
async def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdateRequest,
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    """Modify an existing agent's config."""
    agent = await service.update_agent(agent_id, payload)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id '{agent_id}' not found",
        )
    return agent


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deregister an agent",
    description="Remove an agent from the registry. Active tasks assigned to this agent will be reassigned.",
)
async def deregister_agent(
    agent_id: uuid.UUID,
    service: AgentService = Depends(get_agent_service),
) -> None:
    """Remove an agent from the system."""
    success = await service.deregister_agent(agent_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id '{agent_id}' not found",
        )


@router.get(
    "/{agent_id}/status",
    response_model=AgentStatusResponse,
    summary="Get agent health status",
    description="Query the current health status, uptime, and performance metrics of a specific agent.",
)
async def get_agent_status(
    agent_id: uuid.UUID,
    service: AgentService = Depends(get_agent_service),
) -> AgentStatusResponse:
    """Retrieve the live status of an agent."""
    status_info = await service.get_agent_status(agent_id)
    if status_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with id '{agent_id}' not found",
        )
    return status_info


@router.post(
    "/discover",
    response_model=AgentListResponse,
    summary="Auto-discover agents",
    description="Scan the filesystem and system PATH for installed AI coding agents (Claude Code, Codex, OpenCode, Gemini CLI) and register them automatically.",
)
async def discover_agents(
    scan_paths: list[str] | None = Query(
        None,
        description="Additional directories to scan for agent executables",
    ),
    service: AgentService = Depends(get_agent_service),
) -> AgentListResponse:
    """Auto-discover and register available AI agents on the system."""
    discovered = await service.discover_agents(scan_paths=scan_paths)
    return AgentListResponse(
        total=len(discovered),
        items=discovered,
        limit=len(discovered),
        offset=0,
    )
