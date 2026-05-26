# Self-Hosted Kubernetes Deployment

This directory contains Kubernetes manifests for running the Ollive inference platform on a small self-hosted cluster such as k3s, MicroK8s, kind, or a single-node homelab cluster.

The default deployment is self-contained: API, chat frontend, dashboard, and in-cluster PostgreSQL. The `overlays/supabase` overlay removes the in-cluster PostgreSQL StatefulSet and configures the API for a Supabase/Postgres pooler connection.

## Components

- `ollive-api`: FastAPI chat, ingestion, analytics, and schema startup.
- `ollive-frontend`: Next.js chat console with SSE rendering.
- `ollive-dashboard`: Next.js observability dashboard.
- `ollive-postgres`: optional in-cluster PostgreSQL StatefulSet with a persistent volume.
- `ollive-ingress`: host-based ingress for API, chat, and dashboard.

## Build Images

Build the API image:

```powershell
docker build -f infrastructure/docker/api.Dockerfile -t ollive-api:latest .
```

Build the chat and dashboard images. `NEXT_PUBLIC_API_BASE_URL` must be set at build time because Next.js bakes public environment variables into the client bundle.

```powershell
docker build -f infrastructure/docker/next.Dockerfile `
  --build-arg APP_NAME=frontend `
  --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.ollive.local `
  --build-arg NEXT_PUBLIC_DASHBOARD_URL=https://dashboard.ollive.local `
  -t ollive-frontend:latest .

docker build -f infrastructure/docker/next.Dockerfile `
  --build-arg APP_NAME=dashboard `
  --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.ollive.local `
  --build-arg NEXT_PUBLIC_CHAT_URL=https://chat.ollive.local `
  -t ollive-dashboard:latest .
```

For kind:

```powershell
kind load docker-image ollive-api:latest
kind load docker-image ollive-frontend:latest
kind load docker-image ollive-dashboard:latest
```

For a remote self-hosted cluster, push the images to a registry and update image names:

```powershell
kubectl kustomize infrastructure/kubernetes
kubectl kustomize infrastructure/kubernetes | kubectl apply -f -
```

If you need registry image names, edit `kustomization.yaml`:

```yaml
images:
  - name: ollive-api
    newName: registry.example.com/ollive-api
    newTag: v0.1.0
```

## Create Secrets

Create the namespace first:

```powershell
kubectl apply -f infrastructure/kubernetes/namespace.yaml
```

For the default in-cluster PostgreSQL deployment:

```powershell
kubectl -n ollive create secret generic ollive-postgres-secret `
  --from-literal=POSTGRES_USER=postgres `
  --from-literal=POSTGRES_PASSWORD=postgres `
  --from-literal=POSTGRES_DB=ollive

kubectl -n ollive create secret generic ollive-secrets `
  --from-literal=DATABASE_URL="postgresql+asyncpg://postgres:postgres@ollive-postgres:5432/ollive" `
  --from-literal=GEMINI_API_KEY="" `
  --from-literal=OPENAI_API_KEY=""
```

For real providers, set `GEMINI_API_KEY` and/or `OPENAI_API_KEY`, then set `ALLOW_MOCK_PROVIDER` to `false` in `configmap.yaml`.

For Supabase instead of in-cluster PostgreSQL, create only `ollive-secrets` with the Supabase async SQLAlchemy URL:

```powershell
kubectl -n ollive create secret generic ollive-secrets `
  --from-literal=DATABASE_URL="postgresql+asyncpg://postgres.<project-ref>:<password>@<pooler-host>:5432/postgres" `
  --from-literal=GEMINI_API_KEY="" `
  --from-literal=OPENAI_API_KEY=""
```

## Deploy

Default self-contained deployment:

```powershell
kubectl apply -k infrastructure/kubernetes
```

Supabase-backed deployment:

```powershell
kubectl apply -k infrastructure/kubernetes/overlays/supabase
```

Check rollout status:

```powershell
kubectl -n ollive rollout status deployment/ollive-api
kubectl -n ollive rollout status deployment/ollive-frontend
kubectl -n ollive rollout status deployment/ollive-dashboard
kubectl -n ollive get pods
```

## Access

The ingress uses these hosts:

- `api.ollive.local`
- `chat.ollive.local`
- `dashboard.ollive.local`

On a local cluster, map them to your ingress controller address in your hosts file. For a quick port-forward smoke test:

```powershell
kubectl -n ollive port-forward service/ollive-api 8000:8000
kubectl -n ollive port-forward service/ollive-frontend 3000:3000
kubectl -n ollive port-forward service/ollive-dashboard 3001:3000
```

Then open:

- API health: `http://localhost:8000/health`
- Chat app: `http://localhost:3000`
- Dashboard: `http://localhost:3001`

## Operational Notes

The API starts by creating the prototype schema with SQLAlchemy `create_all`. That is fine for a take-home and local Kubernetes demo, but production should use Alembic migrations run as a separate Job.

The in-cluster PostgreSQL manifest is intentionally lightweight. It is useful for a self-contained demo, not a highly available database. For production-like persistence, use managed Postgres, a dedicated Postgres operator, or the Supabase overlay.

Ingress disables proxy buffering and extends read/send timeouts so SSE streaming responses are not cut short by the ingress controller.

The API deployment runs one replica by default. Scaling the API horizontally is straightforward once schema migrations are externalized and provider/API quotas are accounted for.
