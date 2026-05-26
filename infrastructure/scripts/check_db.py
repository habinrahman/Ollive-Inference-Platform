from __future__ import annotations

import argparse
import asyncio
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db.base import Base
from app.db.ssl import build_ssl_context
from app import models  # noqa: F401 - register SQLAlchemy models


REQUIRED_TABLES = {
    "chat_messages",
    "conversations",
    "inference_logs",
    "ingestion_events",
}


def mask_database_url(url: str) -> str:
    parsed = urlparse(url)
    username = parsed.username or ""
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    database = parsed.path or ""
    return f"{parsed.scheme}://{username}:***@{host}{port}{database}"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Check Ollive database connectivity and schema.")
    parser.add_argument(
        "--create-schema",
        action="store_true",
        help="Create missing SQLAlchemy tables. Intended for local demos, not managed migrations.",
    )
    args = parser.parse_args()

    settings = get_settings()
    connect_args = {
        "prepared_statement_cache_size": settings.database_prepared_statement_cache_size,
    }
    if settings.database_ssl:
        connect_args["ssl"] = build_ssl_context(
            enabled=settings.database_ssl,
            mode=settings.database_ssl_mode,
        )

    print(f"Checking database: {mask_database_url(settings.database_url)}")
    engine = create_async_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)

    try:
        async with engine.begin() as conn:
            if args.create_schema:
                await conn.run_sync(Base.metadata.create_all)

            info = (
                await conn.execute(
                    text(
                        """
                        select
                          current_database() as database_name,
                          current_user as user_name,
                          version() as postgres_version
                        """
                    )
                )
            ).mappings().one()

            rows = (
                await conn.execute(
                    text(
                        """
                        select table_name
                        from information_schema.tables
                        where table_schema = 'public'
                          and table_name = any(:table_names)
                        order by table_name
                        """
                    ),
                    {"table_names": list(REQUIRED_TABLES)},
                )
            ).scalars().all()

        existing = set(rows)
        missing = REQUIRED_TABLES - existing

        print("Connection: OK")
        print(f"Database: {info['database_name']}")
        print(f"User: {info['user_name']}")
        print(f"Postgres: {info['postgres_version'].split(',')[0]}")
        print(f"Required tables present: {', '.join(sorted(existing)) or 'none'}")

        if missing:
            print(f"Missing tables: {', '.join(sorted(missing))}")
            print("Run the API once or rerun this script with --create-schema for the prototype schema.")
            raise SystemExit(2)

        print("Schema: OK")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
