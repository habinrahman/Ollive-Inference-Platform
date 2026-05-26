"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Activity, CircleCheck, Database, MessageSquare, RotateCcw, Server, XCircle } from "lucide-react";

import { API_BASE_URL, DASHBOARD_URL, ChatMessage, Conversation, ConversationDetail, RecentInference } from "@/lib/api";

const SESSION_ID = "demo-session";

export function ChatShell() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [provider, setProvider] = useState<"gemini" | "openai">("gemini");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [recentInference, setRecentInference] = useState<RecentInference | null>(null);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === conversationId),
    [conversations, conversationId]
  );
  const latestAssistantMessage = [...messages].reverse().find((message) => message.role === "assistant");
  const latestMessage = messages[messages.length - 1];

  useEffect(() => {
    void refreshConversations();
    void refreshTelemetry();
  }, []);

  async function refreshConversations() {
    const response = await fetch(`${API_BASE_URL}/v1/conversations?session_id=${SESSION_ID}`);
    if (response.ok) {
      setConversations(await response.json());
    }
  }

  async function refreshTelemetry() {
    const response = await fetch(`${API_BASE_URL}/v1/analytics/summary?hours=24`, { cache: "no-store" });
    if (!response.ok) return;
    const summary = await response.json();
    setRecentInference(summary.recent_inferences?.[0] ?? null);
  }

  async function openConversation(id: string) {
    const response = await fetch(`${API_BASE_URL}/v1/conversations/${id}`);
    if (!response.ok) return;
    const detail = (await response.json()) as ConversationDetail;
    setConversationId(detail.id);
    setMessages(detail.messages);
    setStreamingText("");
  }

  async function cancelConversation() {
    if (!conversationId) return;
    await fetch(`${API_BASE_URL}/v1/conversations/${conversationId}/cancel`, { method: "POST" });
    await refreshConversations();
  }

  async function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || isStreaming) return;

    setDraft("");
    setIsStreaming(true);
    setStreamingText("");
    setError(null);

    const response = await fetch(`${API_BASE_URL}/v1/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        conversation_id: conversationId,
        session_id: SESSION_ID,
        provider,
        message
      })
    });

    if (!response.ok || !response.body) {
      setError("The inference request failed before streaming started. Check provider configuration and API logs.");
      setIsStreaming(false);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";
      for (const eventBlock of events) {
        handleSseEvent(eventBlock);
      }
    }

    setIsStreaming(false);
    await refreshConversations();
    await refreshTelemetry();
    window.setTimeout(() => {
      void refreshTelemetry();
    }, 2000);
  }

  function handleSseEvent(block: string) {
    const event = block.match(/^event: (.+)$/m)?.[1];
    const data = block.match(/^data: (.+)$/m)?.[1];
    if (!event || !data) return;
    const payload = JSON.parse(data);

    if (event === "conversation") {
      setConversationId(payload.conversation.id);
      setMessages((current) => [...current, payload.user_message]);
    }
    if (event === "token") {
      setStreamingText((current) => current + payload.token);
    }
    if (event === "done") {
      setMessages((current) => [...current, payload.assistant_message]);
      setStreamingText("");
    }
    if (event === "error") {
      setError(payload.message ?? "The inference stream failed.");
    }
  }

  return (
    <main className="min-h-screen bg-background text-zinc-950">
      <div className="border-b border-border bg-white/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">Ollive</p>
            <h1 className="text-lg font-semibold tracking-tight text-zinc-950">Inference Operations Console</h1>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <a
              href={DASHBOARD_URL}
              className="rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs font-medium text-zinc-700 shadow-sm transition hover:bg-zinc-50"
            >
              Open dashboard
            </a>
            <StatusPill tone="success" label="API connected" />
            <StatusPill tone="neutral" label="Gemini + OpenAI" />
          </div>
        </div>
      </div>

      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-5 px-6 py-6 lg:grid-cols-[280px_1fr_320px]">
        <aside className="rounded-2xl border border-border bg-panel shadow-sm">
          <div className="border-b border-border p-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">Conversations</p>
              <h2 className="mt-1 text-sm font-semibold text-zinc-950">Session workspace</h2>
            </div>
          </div>
          <div className="p-3">
          <button
            className="mb-3 w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-800 shadow-sm transition hover:bg-zinc-50"
            onClick={() => {
              setConversationId(null);
              setMessages([]);
              setStreamingText("");
              setError(null);
            }}
          >
            New conversation
          </button>
          <div className="space-y-2">
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                onClick={() => openConversation(conversation.id)}
                className={`w-full rounded-lg border px-3 py-2 text-left text-sm ${
                  conversation.id === conversationId
                    ? "border-blue-200 bg-blue-50 text-blue-950"
                    : "border-transparent text-zinc-700 hover:border-zinc-200 hover:bg-zinc-50"
                }`}
              >
                <div className="truncate font-medium">{conversation.title}</div>
                <div className="mt-1 flex items-center justify-between text-xs text-zinc-500">
                  <span>{conversation.status}</span>
                  <span>{new Date(conversation.updated_at).toLocaleTimeString()}</span>
                </div>
              </button>
            ))}
            {conversations.length === 0 && (
              <div className="rounded-xl border border-dashed border-zinc-200 p-4 text-sm text-zinc-500">
                No conversations for this session.
              </div>
            )}
          </div>
          </div>
        </aside>

        <section className="flex min-h-[calc(100vh-8rem)] flex-col rounded-2xl border border-border bg-panel shadow-sm">
          <header className="flex items-center justify-between border-b border-border px-5 py-4">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">Chat console</p>
              <h2 className="mt-1 text-base font-semibold text-zinc-950">
                {activeConversation?.title ?? "New operational chat"}
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={provider}
                onChange={(event) => setProvider(event.target.value as "gemini" | "openai")}
                className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 outline-none"
              >
                <option value="gemini">Gemini</option>
                <option value="openai">OpenAI</option>
              </select>
              <button
                onClick={cancelConversation}
                disabled={!conversationId}
                className="rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-600 transition hover:bg-zinc-50 disabled:opacity-40"
              >
                <XCircle className="mr-2 inline h-4 w-4" />
                Cancel
              </button>
            </div>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto px-5 py-6">
            {messages.length === 0 && (
              <div className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50/70 p-8 text-center text-zinc-500">
                <MessageSquare className="mx-auto mb-3 h-8 w-8 text-zinc-400" />
                Start a multi-turn inference session. Every request emits telemetry into the ingestion pipeline.
              </div>
            )}
            {messages.map((message) => (
              <div
                key={message.id}
                className={`max-w-3xl rounded-2xl border px-4 py-3 shadow-sm ${
                  message.role === "user"
                    ? "ml-auto border-blue-200 bg-blue-50 text-blue-950"
                    : "border-zinc-200 bg-white text-zinc-800"
                }`}
              >
                <div className="mb-2 flex items-center justify-between gap-3 text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
                  <span>{message.role === "user" ? "User request" : `${message.provider ?? "Provider"} response`}</span>
                  <span>{new Date(message.created_at).toLocaleTimeString()}</span>
                </div>
                <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>
                {message.role === "assistant" && (
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-zinc-500">
                    <span className="rounded-full bg-zinc-100 px-2 py-1">{message.provider ?? "provider"}</span>
                    <span className="rounded-full bg-zinc-100 px-2 py-1">{message.model ?? "model"}</span>
                    <span className="rounded-full bg-zinc-100 px-2 py-1">{message.token_count ?? 0} tokens</span>
                  </div>
                )}
              </div>
            ))}
            {streamingText && (
              <div className="max-w-3xl rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm leading-6 text-emerald-950 shadow-sm">
                <div className="mb-2 flex items-center gap-2 text-xs font-medium text-emerald-700">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
                  Streaming response
                </div>
                {streamingText}
              </div>
            )}
            {error && (
              <div className="max-w-3xl rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-800">
                {error}
              </div>
            )}
          </div>

          <form onSubmit={submitMessage} className="border-t border-border p-4">
            <div className="flex gap-3">
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Ask something that should be logged, measured, and replayable..."
                className="min-h-24 flex-1 rounded-xl border border-zinc-200 bg-white p-3 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-blue-400 focus:ring-4 focus:ring-blue-50"
              />
              <button
                disabled={isStreaming}
                className="rounded-xl bg-zinc-950 px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800 disabled:opacity-50"
              >
                {isStreaming ? <RotateCcw className="h-5 w-5 animate-spin" /> : "Send"}
              </button>
            </div>
          </form>
        </section>

        <aside className="rounded-2xl border border-border bg-panel shadow-sm">
          <div className="border-b border-border p-4">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">Telemetry inspector</p>
            <h2 className="mt-1 text-sm font-semibold text-zinc-950">Current inference state</h2>
          </div>
          <div className="space-y-4 p-4">
            <HealthRow icon={<Server className="h-4 w-4" />} label="API connectivity" value="healthy" tone="success" />
            <HealthRow icon={<Database className="h-4 w-4" />} label="Persistence" value="Supabase" tone="neutral" />
            <HealthRow icon={<Activity className="h-4 w-4" />} label="Streaming" value={isStreaming ? "active" : "available"} tone="success" />
            <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">Latest message</p>
              <dl className="mt-3 space-y-3 text-sm">
                <MetaRow label="Role" value={latestMessage?.role ?? "none"} />
                <MetaRow label="Provider" value={latestAssistantMessage?.provider ?? provider} />
                <MetaRow label="Model" value={latestAssistantMessage?.model ?? (provider === "gemini" ? "gemini-2.0-flash" : "gpt-4o-mini")} />
                <MetaRow label="Tokens" value={`${latestAssistantMessage?.token_count ?? 0}`} />
                <MetaRow label="Updated" value={latestMessage ? new Date(latestMessage.created_at).toLocaleTimeString() : "n/a"} />
              </dl>
            </div>
            <div className="rounded-xl border border-zinc-200 bg-white p-4">
              <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-500">Trace context</p>
              <dl className="mt-3 space-y-3 text-sm">
                <MetaRow label="Status" value={recentInference?.status ?? "pending"} />
                <MetaRow label="Ingestion" value={recentInference?.ingestion_status ?? "processed"} />
                <MetaRow label="Retries" value={`${recentInference?.ingestion_retries ?? 0}`} />
                <MetaRow label="Latency" value={recentInference ? `${recentInference.latency_ms} ms` : "n/a"} />
                <MetaRow label="Event" value={recentInference?.event_id ?? "n/a"} mono copyable />
                <MetaRow label="Trace" value={recentInference?.trace_id ?? "n/a"} mono copyable />
                <MetaRow label="Request" value={recentInference?.request_id ?? "n/a"} mono copyable />
              </dl>
            </div>
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
              <div className="mb-2 flex items-center gap-2 font-medium">
                <CircleCheck className="h-4 w-4" />
                Telemetry enabled
              </div>
              Requests are persisted with provider, model, latency, token estimate, and trace metadata in the backend pipeline.
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}

function StatusPill({ label, tone }: { label: string; tone: "success" | "neutral" }) {
  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-medium ${
        tone === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-zinc-200 bg-zinc-50 text-zinc-600"
      }`}
    >
      {label}
    </span>
  );
}

function HealthRow({
  icon,
  label,
  value,
  tone
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone: "success" | "neutral";
}) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white p-3">
      <div className="flex items-center gap-2 text-sm text-zinc-600">
        <span className="text-zinc-400">{icon}</span>
        {label}
      </div>
      <span
        className={`rounded-full px-2 py-1 text-xs font-medium ${
          tone === "success" ? "bg-emerald-50 text-emerald-700" : "bg-zinc-100 text-zinc-700"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

function MetaRow({
  label,
  value,
  mono = false,
  copyable = false
}: {
  label: string;
  value: string;
  mono?: boolean;
  copyable?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="flex min-w-0 items-center gap-2">
        <span className={`truncate font-medium text-zinc-900 ${mono ? "max-w-32 font-mono text-xs" : ""}`}>{shortId(value)}</span>
        {copyable && value !== "n/a" && (
          <button
            className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-[11px] font-medium text-zinc-600 hover:bg-zinc-100"
            onClick={() => void navigator.clipboard.writeText(value)}
          >
            Copy
          </button>
        )}
      </dd>
    </div>
  );
}

function shortId(value: string) {
  if (value.length <= 18) return value;
  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}
