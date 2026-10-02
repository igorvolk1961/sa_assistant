import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routers import (
    actors,
    admin,
    auth,
    comments,
    meetings,
    notifications,
    projects,
    reference,
    requirements,
    tasks,
)
from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.bootstrap import bootstrap

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await bootstrap()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SA Assistant API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(reference.router)
    app.include_router(projects.router)
    app.include_router(actors.router)
    app.include_router(meetings.router)
    app.include_router(requirements.router)
    app.include_router(tasks.router)
    app.include_router(comments.router)
    app.include_router(notifications.router)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        try:
            async with SessionFactory() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001
            logger.error("Healthcheck failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="database unavailable",
            ) from exc
        return {"status": "ok"}

    return app


app = create_app()
