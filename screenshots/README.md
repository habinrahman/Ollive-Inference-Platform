# Screenshots

Store final demo screenshots in this root-level `screenshots/` directory using these exact filenames.

## Required Captures

- `dashboard-overview.png` - full operations dashboard with request, latency, error, token, and health panels visible.
- `inference-timeline.png` - recent inference timeline showing provider/model, status, ingestion state, latency, tokens, trace ID, and request ID.
- `telemetry-inspector.png` - chat-side telemetry inspector showing latest event, ingestion status, latency, event ID, trace ID, and request ID.
- `chat-console.png` - chat console with conversation list, provider selector, persisted messages, and dashboard navigation.
- `streaming-response.png` - chat console while an assistant response is actively streaming.
- `provider-health.png` - dashboard provider health panel showing Gemini/OpenAI request counts, failures, latency, and status.
- `supabase-inference-logs.png` - Supabase table view for `inference_logs` with provider, model, status, latency, tokens, trace ID, and request ID.
- `supabase-ingestion-events.png` - Supabase table view for `ingestion_events` with event ID, status, retry count, raw payload, and processed timestamp.
- `kubernetes-manifests.png` - editor or terminal view showing Kubernetes Deployments, Services, Ingress, Postgres, and Supabase overlay.
- `docker-compose.png` - Docker Compose file or running stack showing API, frontend, dashboard, and Postgres services.
- `architecture-diagram.png` - rendered architecture diagram from `architecture/diagrams.md`.

## Additional Captures

- `supabase-chat-messages.png` - Supabase table view for persisted `chat_messages`.
- `supabase-conversations.png` - Supabase table view for persisted `conversations`.
- `kubernetes-kustomization.png` - Kubernetes base kustomization resources and image mapping.
- `kubernetes-api-deployment.png` - API Deployment, Service, probes, resources, ConfigMap, and Secret references.
- `kubernetes-ingress.png` - Ingress configuration with SSE-friendly NGINX annotations.
- `kubernetes-ingress-routes.png` - Ingress host routing for API, chat, and dashboard.
- `kubernetes-supabase-overlay.png` - Supabase Kustomize overlay that removes in-cluster PostgreSQL and patches database settings.
- `docker-compose-next-services.png` - Docker Compose frontend/dashboard build args and service wiring.
- `architecture-failure-flow.png` - failure isolation Mermaid source from `architecture/diagrams.md`.

## Expected Layout

```text
screenshots/
├── dashboard-overview.png
├── inference-timeline.png
├── telemetry-inspector.png
├── chat-console.png
├── streaming-response.png
├── provider-health.png
├── supabase-chat-messages.png
├── supabase-conversations.png
├── supabase-inference-logs.png
├── supabase-ingestion-events.png
├── kubernetes-manifests.png
├── kubernetes-kustomization.png
├── kubernetes-api-deployment.png
├── kubernetes-ingress.png
├── kubernetes-ingress-routes.png
├── kubernetes-supabase-overlay.png
├── docker-compose.png
├── docker-compose-next-services.png
├── architecture-diagram.png
└── architecture-failure-flow.png
```
