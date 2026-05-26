# Scaling Notes

## API Scaling

The chat API is stateless apart from PostgreSQL and provider credentials, so it can scale horizontally behind a load balancer. Sessions are represented by client-supplied `session_id` and persisted conversation IDs rather than process memory.

Connection pools should be tuned separately for chat traffic and ingestion workers. Provider timeouts should be shorter than upstream gateway timeouts so failures surface predictably.

The Kubernetes manifests in `infrastructure/kubernetes` model this by running the API as a Deployment behind a ClusterIP Service, with external access handled by ingress. The default replica count is intentionally one for a small self-hosted demo; increasing replicas is safe once schema migrations are moved out of API startup and into an explicit migration Job.

## Ingestion Scaling

The prototype uses background tasks, but the intended production model is:

```text
SDK emitter -> ingestion API -> durable queue -> worker pool -> PostgreSQL/warehouse
```

A queue introduces backpressure, retry visibility, dead-letter queues, and deployment independence between inference services and telemetry processors.

## Storage Scaling

PostgreSQL is sufficient for early-stage operational analytics. As volume grows:

- Keep raw events in append-only storage for replay.
- Partition `inference_logs` by time.
- Add rollup tables for dashboard windows.
- Export high-volume events to OLAP storage for long retention.
- Keep hot debugging windows in Postgres.

For self-hosted demos, the Kubernetes base includes a single-replica PostgreSQL StatefulSet with a persistent volume. For a more production-like deployment, use the Supabase overlay, a managed Postgres instance, or a Postgres operator with backup and restore policies.

## Observability Strategy

The platform already captures latency, status, provider, model, tokens, previews, and conversation/session links. Production hardening should add trace IDs propagated through frontend, API, SDK, provider request, ingestion event, and dashboard drilldowns.

Structured logs should include `conversation_id`, `session_id`, `event_id`, `provider`, and `model` when available.

This implementation already propagates request and trace identifiers across API middleware, SDK telemetry, raw ingestion events, and normalized inference logs. A production version would bridge those IDs into OpenTelemetry spans and provider request metadata where supported.

## Reliability Decisions

Non-streaming inference can retry before responding to the user. Streaming inference avoids retrying after partial output because it risks duplicated tokens and confusing UX.

Telemetry emission has short timeouts and bounded retries. The user response path should remain available during ingestion brownouts.

`event_id` uniqueness supports at-least-once delivery from emitters while preserving exactly-once analytical counting.

PII redaction is applied to telemetry previews before they are stored in observability tables. This keeps dashboards useful for debugging while reducing the risk of leaking user data into operational surfaces.
