"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from xspy import __version__
from xspy.core.config import load_settings
from xspy.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = load_settings()

    app = FastAPI(
        title="xspy",
        description="Novel-to-audiobook fully automated dubbing system",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.web.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from xspy.web.routes import characters, novels, scripts, tasks
    from xspy.web.ws import router as ws_router

    app.include_router(novels.router, prefix="/api/novels", tags=["novels"])
    app.include_router(characters.router, prefix="/api/characters", tags=["characters"])
    app.include_router(scripts.router, prefix="/api/scripts", tags=["scripts"])
    app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
    app.include_router(ws_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app
