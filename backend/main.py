"""
AgentForge Backend - FastAPI Application Entry Point
=====================================================
Main application server for the AgentForge multi-agent orchestration platform.
Provides REST API, WebSocket endpoints, and agent workflow engine.
"""

import os
import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).parent))

from config import settings, ensure_directories

# ===== Logging Setup =====
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format=settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.log_file, encoding='utf-8'),
    ],
)
logger = logging.getLogger("agentforge")

# ===== Application Lifespan =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")
    logger.info(f"Data directory: {settings.data_dir}")

    ensure_directories()

    # Initialize database (deferred to first request or explicit init)
    from models import Base
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine(settings.database_url, echo=settings.DEBUG)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Store engine in app state for dependency injection
    app.state.engine = engine
    app.state.SessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    logger.info("Database initialized successfully")
    logger.info(f"API server listening on {settings.API_HOST}:{settings.API_PORT}")

    yield

    # Shutdown
    logger.info("Shutting down AgentForge server...")
    await engine.dispose()
    logger.info("Server shutdown complete")


# ===== FastAPI Application =====
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multi-Agent Collaborative Orchestration Platform API",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ===== CORS Middleware =====
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Agent-Forge-Version"],
)

# ===== Custom Middleware =====
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID and timing headers."""
    import uuid
    import time

    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    start_time = time.time()

    response = await call_next(request)

    elapsed = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{elapsed:.3f}s"
    response.headers["X-Agent-Forge-Version"] = settings.APP_VERSION

    return response


# ===== Health Check =====
@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }


# ===== System Info =====
@app.get("/api/info", tags=["System"])
async def system_info():
    """Get system and application information."""
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "data_dir": settings.data_dir,
        "database_url": str(settings.database_url).replace(
            settings.data_dir, "<data_dir>"
        ),
        "agent_registry_path": settings.agent_registry_path,
        "workspace_dir": settings.workspace_dir,
        "mcp_enabled": settings.MCP_ENABLED,
        "python_version": sys.version,
        "platform": sys.platform,
        "max_concurrent_agents": settings.AGENT_MAX_CONCURRENT,
    }


# ===== Route Registration =====
# Routes will be registered here as modules are developed:
# from routers import projects, agents, tasks, workflows, websocket
# app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
# app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
# app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
# app.include_router(workflows.router, prefix="/api/workflows", tags=["Workflows"])
# app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


# ===== Error Handlers =====
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors with proper API response."""
    logger.warning(f"ValueError: {exc}")
    return JSONResponse(
        status_code=400,
        content={"error": "Bad Request", "detail": str(exc)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
        },
    )


# ===== Direct Run Support =====
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.DEBUG,
    )
