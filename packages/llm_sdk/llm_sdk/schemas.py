from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


MessageRole = Literal["system", "user", "assistant"]
InferenceStatus = Literal["success", "error", "cancelled"]


class ChatMessage(BaseModel):
    role: MessageRole
    content: str


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class InferenceResult(BaseModel):
    content: str
    provider: str
    model: str
    usage: Usage = Field(default_factory=Usage)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class TelemetryEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    provider: str
    model: str
    status: InferenceStatus
    request_timestamp: datetime
    response_timestamp: datetime
    latency_ms: int
    token_usage: Usage = Field(default_factory=Usage)
    conversation_id: str | None = None
    session_id: str | None = None
    request_preview: str = ""
    response_preview: str = ""
    error_type: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    emitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
