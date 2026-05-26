from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import analytics, chat, ingest
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401 - register SQLAlchemy models


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


settings = get_settings()

app = FastAPI(
    title="Ollive Inference Platform API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(ingest.router)
app.include_router(analytics.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "Ollive Inference Platform API",
        "health": "/health",
        "docs": "/docs",
        "analytics": "/v1/analytics/summary",
        "ingestion_events": "/v1/ingest/events",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
