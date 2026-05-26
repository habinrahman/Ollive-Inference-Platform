export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
export const DASHBOARD_URL = process.env.NEXT_PUBLIC_DASHBOARD_URL ?? "http://localhost:3001";

export type Conversation = {
  id: string;
  session_id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  provider?: string | null;
  model?: string | null;
  token_count?: number | null;
  created_at: string;
};

export type ConversationDetail = Conversation & {
  messages: ChatMessage[];
};

export type RecentInference = {
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
};
