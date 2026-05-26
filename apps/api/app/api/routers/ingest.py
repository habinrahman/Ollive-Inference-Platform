from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session, get_session
from app.models.inference import IngestionEvent
from app.schemas.telemetry import IngestionEventOut, TelemetryAccepted, TelemetryEventIn
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/v1/ingest", tags=["ingestion"])


@router.post("/events", response_model=TelemetryAccepted, status_code=202)
async def ingest_event(event: TelemetryEventIn, background_tasks: BackgroundTasks) -> TelemetryAccepted:
    background_tasks.add_task(_process_event, event)
    return TelemetryAccepted(accepted=True, event_id=event.event_id)


@router.get("/events", response_model=list[IngestionEventOut])
async def list_ingestion_events(
    limit: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
) -> list[IngestionEventOut]:
    stmt = select(IngestionEvent).order_by(IngestionEvent.created_at.desc()).limit(limit)
    events = list((await db.scalars(stmt)).all())
    return [IngestionEventOut.model_validate(event) for event in events]


async def _process_event(event: TelemetryEventIn) -> None:
    async with async_session() as session:
        service = IngestionService(session)
        await service.process(event)
