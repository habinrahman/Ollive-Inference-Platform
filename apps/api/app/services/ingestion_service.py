from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.inference_logs import InferenceLogRepository
from app.schemas.telemetry import TelemetryEventIn

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.logs = InferenceLogRepository(session)

    async def process(self, event: TelemetryEventIn) -> None:
        try:
            inserted = await self.logs.record_ingestion_event(event)
            if not inserted:
                await self.session.rollback()
                logger.info("duplicate_ingestion_event", extra={"event_id": event.event_id})
                return

            await self.logs.mark_processing(event.event_id)
            await self.logs.create_log(event)
            await self.logs.mark_processed(event.event_id, status="processed")
            await self.session.commit()
            logger.info(
                "ingestion_event_processed",
                extra={
                    "event_id": event.event_id,
                    "trace_id": event.trace_id,
                    "request_id": event.request_id,
                    "provider": event.provider,
                    "model": event.model,
                    "status": event.status,
                    "latency_ms": event.latency_ms,
                },
            )
        except IntegrityError as exc:
            await self.session.rollback()
            logger.info("ingestion_event_already_processed", extra={"event_id": event.event_id, "error": str(exc)})
        except Exception as exc:
            await self.session.rollback()
            try:
                await self.logs.mark_processed(event.event_id, status="failed", error_message=str(exc))
                await self.session.commit()
            except Exception:
                await self.session.rollback()
            logger.exception("ingestion_processing_failed", extra={"event_id": event.event_id})
