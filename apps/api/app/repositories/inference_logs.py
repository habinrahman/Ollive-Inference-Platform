from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inference import InferenceLog, IngestionEvent
from app.schemas.telemetry import TelemetryEventIn


class InferenceLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_ingestion_event(self, event: TelemetryEventIn) -> bool:
        stmt = (
            insert(IngestionEvent)
            .values(
                event_id=event.event_id,
                trace_id=event.trace_id,
                request_id=event.request_id,
                status="accepted",
                retry_count=0,
                raw_payload=event.model_dump(mode="json"),
            )
            .on_conflict_do_nothing(index_elements=["event_id"])
        )
        result = await self.session.execute(stmt)
        return result.rowcount == 1

    async def mark_processed(self, event_id: str, *, status: str, error_message: str | None = None) -> None:
        ingestion_event = await self.session.scalar(
            select(IngestionEvent).where(IngestionEvent.event_id == event_id)
        )
        if ingestion_event:
            ingestion_event.status = status
            ingestion_event.error_message = error_message
            ingestion_event.processed_at = datetime.now(UTC)

    async def mark_processing(self, event_id: str) -> None:
        ingestion_event = await self.session.scalar(
            select(IngestionEvent).where(IngestionEvent.event_id == event_id)
        )
        if ingestion_event:
            ingestion_event.status = "processing"
            ingestion_event.retry_count += 1

    async def create_log(self, event: TelemetryEventIn) -> InferenceLog:
        conversation_id = UUID(event.conversation_id) if event.conversation_id else None
        log = InferenceLog(
            event_id=event.event_id,
            trace_id=event.trace_id,
            request_id=event.request_id,
            correlation_id=event.correlation_id,
            conversation_id=conversation_id,
            session_id=event.session_id,
            provider=event.provider,
            model=event.model,
            status=event.status,
            request_timestamp=event.request_timestamp,
            response_timestamp=event.response_timestamp,
            latency_ms=event.latency_ms,
            prompt_tokens=event.token_usage.prompt_tokens,
            completion_tokens=event.token_usage.completion_tokens,
            total_tokens=event.token_usage.total_tokens,
            request_preview=event.request_preview,
            response_preview=event.response_preview,
            error_type=event.error_type,
            error_message=event.error_message,
            meta=event.metadata,
        )
        self.session.add(log)
        await self.session.flush()
        return log
