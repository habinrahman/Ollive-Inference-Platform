from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from llm_sdk.providers.base import BaseProvider
from llm_sdk.redaction import redact_text
from llm_sdk.schemas import ChatMessage, InferenceResult, TelemetryEvent, Usage
from llm_sdk.telemetry import FireAndForgetTelemetryEmitter


class InferenceClient:
    def __init__(
        self,
        *,
        providers: dict[str, BaseProvider],
        telemetry: FireAndForgetTelemetryEmitter,
        default_provider: str = "gemini",
        default_model: str = "gemini-2.0-flash",
        default_models: dict[str, str] | None = None,
        max_retries: int = 1,
    ) -> None:
        self.providers = providers
        self.telemetry = telemetry
        self.default_provider = default_provider
        self.default_model = default_model
        self.default_models = default_models or {}
        self.max_retries = max_retries

    async def complete(
        self,
        *,
        messages: list[ChatMessage],
        provider_name: str | None = None,
        model: str | None = None,
        conversation_id: str | None = None,
        session_id: str | None = None,
        trace_id: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> InferenceResult:
        provider_key, selected_model = self.resolve(provider_name=provider_name, model=model)
        provider = self._provider(provider_key)
        started_at = datetime.now(UTC)
        start = perf_counter()
        request_preview = self._preview(messages[-1].content if messages else "")

        for attempt in range(self.max_retries + 1):
            try:
                result = await provider.complete(messages=messages, model=selected_model)
                latency_ms = int((perf_counter() - start) * 1000)
                self.telemetry.emit(
                    TelemetryEvent(
                        provider=result.provider,
                        model=result.model,
                        trace_id=trace_id,
                        request_id=request_id,
                        correlation_id=correlation_id,
                        status="success",
                        request_timestamp=started_at,
                        response_timestamp=datetime.now(UTC),
                        latency_ms=latency_ms,
                        token_usage=result.usage,
                        conversation_id=conversation_id,
                        session_id=session_id,
                        request_preview=request_preview,
                        response_preview=self._preview(result.content),
                        metadata={"attempt": attempt, **(metadata or {})},
                    )
                )
                return result
            except Exception as exc:
                if attempt < self.max_retries:
                    continue
                latency_ms = int((perf_counter() - start) * 1000)
                self.telemetry.emit(
                    TelemetryEvent(
                        provider=provider_key,
                        model=selected_model,
                        trace_id=trace_id,
                        request_id=request_id,
                        correlation_id=correlation_id,
                        status="error",
                        request_timestamp=started_at,
                        response_timestamp=datetime.now(UTC),
                        latency_ms=latency_ms,
                        token_usage=Usage(),
                        conversation_id=conversation_id,
                        session_id=session_id,
                        request_preview=request_preview,
                        error_type=exc.__class__.__name__,
                        error_message=str(exc),
                        metadata={"attempt": attempt, **(metadata or {})},
                    )
                )
                raise

        raise RuntimeError("unreachable inference retry state")

    async def stream(
        self,
        *,
        messages: list[ChatMessage],
        provider_name: str | None = None,
        model: str | None = None,
        conversation_id: str | None = None,
        session_id: str | None = None,
        trace_id: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        provider_key, selected_model = self.resolve(provider_name=provider_name, model=model)
        provider = self._provider(provider_key)
        started_at = datetime.now(UTC)
        start = perf_counter()
        chunks: list[str] = []
        request_preview = self._preview(messages[-1].content if messages else "")

        try:
            async for chunk in provider.stream(messages=messages, model=selected_model):
                chunks.append(chunk)
                yield chunk
            content = "".join(chunks)
            prompt_tokens = sum(len(message.content.split()) for message in messages)
            completion_tokens = len(content.split())
            usage = Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
            self.telemetry.emit(
                TelemetryEvent(
                    provider=provider.name,
                    model=selected_model,
                    trace_id=trace_id,
                    request_id=request_id,
                    correlation_id=correlation_id,
                    status="success",
                    request_timestamp=started_at,
                    response_timestamp=datetime.now(UTC),
                    latency_ms=int((perf_counter() - start) * 1000),
                    token_usage=usage,
                    conversation_id=conversation_id,
                    session_id=session_id,
                    request_preview=request_preview,
                    response_preview=self._preview(content),
                    metadata={"streamed": True, **(metadata or {})},
                )
            )
        except Exception as exc:
            self.telemetry.emit(
                TelemetryEvent(
                    provider=provider_key,
                    model=selected_model,
                    trace_id=trace_id,
                    request_id=request_id,
                    correlation_id=correlation_id,
                    status="error",
                    request_timestamp=started_at,
                    response_timestamp=datetime.now(UTC),
                    latency_ms=int((perf_counter() - start) * 1000),
                    token_usage=Usage(),
                    conversation_id=conversation_id,
                    session_id=session_id,
                    request_preview=request_preview,
                    response_preview=self._preview("".join(chunks)),
                    error_type=exc.__class__.__name__,
                    error_message=str(exc),
                    metadata={"streamed": True, **(metadata or {})},
                )
            )
            raise

    def resolve(self, *, provider_name: str | None = None, model: str | None = None) -> tuple[str, str]:
        provider_key = provider_name or self.default_provider
        selected_model = model or self.default_models.get(provider_key) or self.default_model
        return provider_key, selected_model

    def _provider(self, provider_name: str) -> BaseProvider:
        try:
            return self.providers[provider_name]
        except KeyError as exc:
            raise ValueError(f"Unsupported provider: {provider_name}") from exc

    @staticmethod
    def _preview(value: str, limit: int = 500) -> str:
        return redact_text(value[:limit])
