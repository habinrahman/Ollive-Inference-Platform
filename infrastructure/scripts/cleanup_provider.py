from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db.ssl import build_ssl_context
from app.models.inference import InferenceLog, IngestionEvent


async def main() -> None:
    parser = argparse.ArgumentParser(description="Remove historical telemetry for a provider.")
    parser.add_argument("--provider", required=True, help="Provider name to remove from historical logs.")
    parser.add_argument("--yes", action="store_true", help="Confirm destructive cleanup.")
    args = parser.parse_args()

    if not args.yes:
        raise SystemExit("Refusing to delete without --yes.")

    settings = get_settings()
    connect_args = {
        "prepared_statement_cache_size": settings.database_prepared_statement_cache_size,
    }
    if settings.database_ssl:
        connect_args["ssl"] = build_ssl_context(
            enabled=settings.database_ssl,
            mode=settings.database_ssl_mode,
        )

    engine = create_async_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
    async with engine.begin() as conn:
        event_ids = (
            await conn.execute(
                select(InferenceLog.event_id).where(InferenceLog.provider == args.provider)
            )
        ).scalars().all()

        deleted_logs = (
            await conn.execute(delete(InferenceLog).where(InferenceLog.provider == args.provider))
        ).rowcount

        deleted_events = 0
        if event_ids:
            deleted_events = (
                await conn.execute(delete(IngestionEvent).where(IngestionEvent.event_id.in_(event_ids)))
            ).rowcount

    await engine.dispose()
    print(f"Deleted inference_logs={deleted_logs or 0} ingestion_events={deleted_events or 0} for provider={args.provider}")


if __name__ == "__main__":
    asyncio.run(main())
