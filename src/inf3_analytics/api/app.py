"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from inf3_analytics.api.config import get_settings
from inf3_analytics.api.routes import artifacts, pipeline, runs, upload, video


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Ensure directories exist on startup."""
    settings = get_settings()
    settings.inf3_registry_path.parent.mkdir(parents=True, exist_ok=True)
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

    return application


app = create_app()
