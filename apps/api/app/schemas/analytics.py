from __future__ import annotations

from pydantic import BaseModel


class MetricPoint(BaseModel):
    bucket: str
    requests: int
    errors: int
    avg_latency_ms: float
    tokens: int


class ProviderMetric(BaseModel):
    provider: str
    requests: int
    errors: int
    error_rate: float
    avg_latency_ms: float


class IngestionStateMetric(BaseModel):
    status: str
    events: int
    retries: int


class ConversationActivity(BaseModel):
    active: int
    cancelled: int
    total: int
    messages: int


class RecentInference(BaseModel):
    event_id: str
    trace_id: str | None = None
    request_id: str | None = None
    conversation_id: str | None = None
    provider: str
    model: str
    status: str
    latency_ms: int
    total_tokens: int
    request_preview: str
    response_preview: str
    error_type: str | None = None
    ingestion_status: str | None = None
    ingestion_retries: int = 0
    created_at: str


class AnalyticsSummary(BaseModel):
    total_requests: int
    error_rate: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    total_tokens: int
    conversation_activity: ConversationActivity
    provider_distribution: list[ProviderMetric]
    ingestion_states: list[IngestionStateMetric]
    recent_inferences: list[RecentInference]
    time_series: list[MetricPoint]
