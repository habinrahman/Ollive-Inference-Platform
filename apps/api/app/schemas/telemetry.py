from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class TelemetryEventIn(BaseModel):
    event_id: str
    trace_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    provider: str
    model: str
    status: Literal["success", "error", "cancelled"]
    request_timestamp: datetime
    response_timestamp: datetime
    latency_ms: int = Field(ge=0)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    conversation_id: str | None = None
    session_id: str | None = None
    request_preview: str = ""
    response_preview: str = ""
    error_type: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    emitted_at: datetime


class TelemetryAccepted(BaseModel):
    accepted: bool
    event_id: str


class IngestionEventOut(BaseModel):
    event_id: str
    trace_id: str | None = None
    request_id: str | None = None
    status: str
    retry_count: int
    error_message: str | None = None
    created_at: datetime
    processed_at: datetime | None = None

    model_config = {"from_attributes": True}
