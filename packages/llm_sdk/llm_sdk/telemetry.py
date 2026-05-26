from __future__ import annotations

import asyncio
import logging

import httpx

from llm_sdk.schemas import TelemetryEvent

logger = logging.getLogger(__name__)


class HttpTelemetryEmitter:
    def __init__(
        self,
        *,
        endpoint: str,
        timeout_seconds: float = 1.5,
        max_retries: int = 2,
    ) -> None:
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def emit(self, event: TelemetryEvent) -> None:
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(self.endpoint, json=event.model_dump(mode="json"))
                    response.raise_for_status()
                    return
            except Exception as exc:  # pragma: no cover - deliberately best-effort
                if attempt >= self.max_retries:
                    logger.warning("telemetry_emit_failed", extra={"event_id": event.event_id, "error": str(exc)})
                    return
                await asyncio.sleep(0.1 * (2**attempt))


class FireAndForgetTelemetryEmitter:
    def __init__(self, emitter: HttpTelemetryEmitter) -> None:
        self.emitter = emitter

    def emit(self, event: TelemetryEvent) -> None:
        task = asyncio.create_task(self.emitter.emit(event))
        task.add_done_callback(self._log_unhandled_exception)

    @staticmethod
    def _log_unhandled_exception(task: asyncio.Task[None]) -> None:
        try:
            task.result()
        except Exception as exc:  # pragma: no cover - defensive guard for background tasks
            logger.warning("telemetry_background_task_failed", extra={"error": str(exc)})
