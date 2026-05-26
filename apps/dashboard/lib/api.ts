export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
export const CHAT_URL = process.env.NEXT_PUBLIC_CHAT_URL ?? "http://localhost:3000";

export type AnalyticsSummary = {
  total_requests: number;
  error_rate: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  total_tokens: number;
  conversation_activity: {
    active: number;
    cancelled: number;
    total: number;
    messages: number;
  };
  provider_distribution: Array<{
    provider: string;
    requests: number;
    errors: number;
    error_rate: number;
    avg_latency_ms: number;
  }>;
  ingestion_states: Array<{
    status: string;
    events: number;
    retries: number;
  }>;
  recent_inferences: Array<{
    event_id: string;
    trace_id?: string | null;
    request_id?: string | null;
    conversation_id?: string | null;
    provider: string;
    model: string;
    status: string;
    latency_ms: number;
    total_tokens: number;
    request_preview: string;
    response_preview: string;
    error_type?: string | null;
    ingestion_status?: string | null;
    ingestion_retries: number;
    created_at: string;
  }>;
  time_series: Array<{
    bucket: string;
    requests: number;
    errors: number;
    avg_latency_ms: number;
    tokens: number;
  }>;
};
