from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.ssl import build_ssl_context

settings = get_settings()

connect_args = {
    "prepared_statement_cache_size": settings.database_prepared_statement_cache_size,
}
if settings.database_ssl:
    connect_args["ssl"] = build_ssl_context(
        enabled=settings.database_ssl,
        mode=settings.database_ssl_mode,
    )

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args=connect_args,
)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
