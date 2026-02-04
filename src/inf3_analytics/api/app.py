"""FastAPI application factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from inf3_analytics.api.config import get_settings
from inf3_analytics.api.queue import TaskQueue
from inf3_analytics.api.registry import RunRegistry
from inf3_analytics.api.routes import artifacts, decomposition, events, pipeline, runs, upload, video

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Ensure directories exist on startup and detect orphaned processes."""
    settings = get_settings()
    settings.inf3_registry_path.parent.mkdir(parents=True, exist_ok=True)

    # Check for orphaned pipeline steps from previous server crash
    registry = RunRegistry(settings.inf3_registry_path)
    orphaned = registry.mark_orphaned_steps()
    if orphaned > 0:
        logger.warning(
            f"Marked {orphaned} orphaned pipeline step(s) as failed on startup"
        )

    # Recover stale tasks from the queue (tasks stuck in processing)
    queue = TaskQueue()
    recovered = queue.recover_stale()
    if recovered > 0:
        logger.warning(
            f"Recovered {recovered} stale task(s) from queue on startup"
        )

    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title="inf3-analytics API",
        description="Infrastructure inspection video analytics pipeline API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.inf3_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    application.include_router(runs.router)
    application.include_router(artifacts.router)
    application.include_router(video.router)
    application.include_router(upload.router)
    application.include_router(pipeline.router)
    application.include_router(decomposition.router)
    application.include_router(events.router)

    return application


app = create_app()
