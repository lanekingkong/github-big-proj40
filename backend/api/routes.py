"""
API Routes Aggregation
======================
Central router that aggregates all API sub-routers for the AgentForge backend.

All routes are mounted under the main FastAPI app with appropriate prefixes
and tags for OpenAPI documentation grouping.
"""

from __future__ import annotations

from fastapi import APIRouter

from api.agents import router as agents_router
from api.projects import router as projects_router
from api.websocket import router as websocket_router

__all__ = ["register_routes"]


def register_routes() -> APIRouter:
    """
    Create and return the master API router with all sub-routers registered.

    Route structure:
        /api/v1/agents       → Agent management
        /api/v1/projects     → Project management
        /api/v1/ws           → WebSocket endpoints

    Returns:
        APIRouter: Master router with all sub-routes mounted.
    """
    master_router = APIRouter(prefix="/api/v1")

    # Agent management routes
    master_router.include_router(
        agents_router,
        prefix="/agents",
        tags=["Agents"],
    )

    # Project management routes
    master_router.include_router(
        projects_router,
        prefix="/projects",
        tags=["Projects"],
    )

    # WebSocket routes (mounted at root level in main.py)
    # Included here for documentation, actually mounted in main.py
    # due to WebSocket requiring different middleware handling
    master_router.include_router(
        websocket_router,
        prefix="/ws",
        tags=["WebSocket"],
    )

    return master_router
