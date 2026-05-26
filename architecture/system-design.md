# System Design

## Goals

Ollive is an internal AI platform prototype for observing LLM inference workloads. The chat app is intentionally thin: it exercises the inference path while the platform captures operational data for debugging, reliability, and capacity planning.

The core architectural constraint is separation between chat execution and telemetry persistence. Provider calls are wrapped by `packages/llm_sdk`, while ingestion and analytics live in `apps/api`.

## Request Lifecycle

1. The browser posts a user message to `POST /v1/chat/stream`.
2. Request middleware assigns or accepts `x-request-id` and `x-trace-id`.
3. `ChatService` creates or loads a conversation and persists the user turn.
4. `ChatService` builds short conversational memory from the latest messages.
5. `InferenceClient` selects a provider adapter and starts timing.
6. The provider adapter calls Gemini, OpenAI, or a provider-compatible mock.
7. Streaming chunks are returned to the browser as SSE tokens.
8. `InferenceClient` creates a normalized telemetry event with trace metadata and redacted previews.
9. The telemetry emitter posts to `/v1/ingest/events` in the background.
10. The ingestion route validates the payload and schedules processing.
11. The processor writes raw and normalized records to PostgreSQL.
12. The dashboard queries aggregate metrics through `/v1/analytics/summary`.

## Module Boundaries

`apps/frontend` never calls provider APIs. It only talks to the FastAPI chat API.

`apps/api` owns application state, persistence, ingestion endpoints, and analytics.

`packages/llm_sdk` owns provider abstraction, timing, retry boundaries, response normalization, and telemetry event construction.

Provider adapters implement `BaseProvider`; Gemini and OpenAI are active adapters behind the same SDK contract. Gemini remains the default demo path, while OpenAI can be selected per request without changing chat, ingestion, or analytics code.

## Database Model

`conversations` stores lifecycle state such as `active` or `cancelled`.

`chat_messages` stores replayable conversation turns.

`ingestion_events` stores raw accepted telemetry payloads and processing state. This supports idempotency, replay, and debugging malformed events.

`inference_logs` stores normalized facts optimized for analytics and operational triage.

The production database target is Supabase Postgres. Local development can still run a disposable Postgres container, but the same SQLAlchemy models and analytics queries are designed to run against Supabase with SSL enabled. When using the Supabase pooler, prepared statement caching is disabled for compatibility.

## Operational Assumptions

Telemetry delivery is best effort in this prototype. Inference should not fail just because telemetry storage fails.

Streaming is treated as a non-retryable provider operation after bytes are sent to the user. Non-streaming calls can retry once within the SDK.

Conversation memory is intentionally short to keep latency and prompt cost bounded. Full conversation replay remains available from PostgreSQL.

Request IDs and trace IDs are treated as first-class operational metadata. They are returned as response headers, added to structured logs, stored with raw ingestion events, and copied into normalized inference logs.

Telemetry previews are redacted before persistence. Full chat messages remain in `chat_messages` for replay; production deployments should add tenant-level retention policies and optional message redaction depending on data classification.
