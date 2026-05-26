# Demo Notes

1. Start the API with `.\infrastructure\scripts\run_api.ps1 -Port 5500`.
2. Open the chat app at `http://localhost:3000`.
3. Send a few messages using Gemini, then switch to OpenAI in the chat header and send another message. Keep `ALLOW_MOCK_PROVIDER=true` for deterministic demos.
4. Open the dashboard at `http://localhost:3001`.
5. Verify request volume, latency, token usage, error rate, and provider distribution update from ingested telemetry.
6. Use API docs at `http://localhost:5500/docs` to inspect chat, ingestion, and analytics endpoints.
7. For Kubernetes review, open `infrastructure/kubernetes/README.md` and show the API/frontend/dashboard/Postgres manifests plus the Supabase overlay.

Suggested screenshots:

- Chat stream in progress with the provider selector visible.
- Conversation resume view.
- Dashboard throughput and latency charts.
- Dashboard provider health and recent inference timeline.
- Dashboard ingestion processing state.
- Supabase `inference_logs` with `trace_id` and `request_id`.
- Supabase `ingestion_events` with `processed` status.
- API logs showing `inference_completed`.
- API docs showing ingestion and analytics endpoints.
- Kubernetes manifests showing Deployments, Services, Ingress, and optional PostgreSQL StatefulSet.
