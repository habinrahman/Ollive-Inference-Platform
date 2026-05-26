# Ingestion Flow

## Event Contract

The SDK emits a normalized telemetry event with:

- Provider and model.
- Request and response timestamps.
- Latency in milliseconds.
- Status and error metadata.
- Token accounting.
- Conversation and session identifiers.
- Request and response previews.
- Provider metadata.
- Request, trace, and correlation identifiers.

This event is provider-neutral so analytics do not depend on Gemini- or OpenAI-specific response shapes.

## Processing Path

1. `InferenceClient` creates a telemetry event after success or failure.
2. `FireAndForgetTelemetryEmitter` schedules delivery without blocking the chat response path.
3. `HttpTelemetryEmitter` posts to `/v1/ingest/events` with a short timeout and bounded retries.
4. The ingestion API validates the payload with Pydantic and returns `202 Accepted`.
5. A background task writes an `ingestion_events` row with the raw payload.
6. The row moves from `accepted` to `processing`, incrementing `retry_count`.
7. The processor normalizes fields into `inference_logs`.
8. The ingestion row is marked `processed` or `failed`.

## Idempotency

Each event carries an `event_id`. `ingestion_events.event_id` and `inference_logs.event_id` are unique. Duplicate events are ignored after the first successful insert, which allows retrying delivery without double-counting metrics.

## Failure Isolation

Telemetry failures are logged but do not raise back into the chat API once provider output has been produced. This protects user-facing inference from observability outages.

In the current local implementation, FastAPI background tasks provide async isolation. In production, this should move to a durable queue or outbox worker so events survive process restarts.

Redaction happens before telemetry previews are emitted. The system masks emails, phone numbers, and common secret-like tokens in request and response previews so operational dashboards do not become a casual PII surface.

## Tradeoffs

FastAPI background tasks are simple and keep `docker compose up` lightweight, but they are not a durable processing system.

HTTP loopback emission keeps the SDK decoupled from database code, but a production service mesh would usually route this through an internal ingestion service or queue.

Streaming token usage is approximated locally by word count. Non-streaming calls use provider-reported token usage when available. A production implementation should reconcile provider stream usage when available.
