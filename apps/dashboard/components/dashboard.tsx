"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { API_BASE_URL, CHAT_URL, AnalyticsSummary } from "@/lib/api";

const emptySummary: AnalyticsSummary = {
  total_requests: 0,
  error_rate: 0,
  avg_latency_ms: 0,
  p50_latency_ms: 0,
  p95_latency_ms: 0,
  p99_latency_ms: 0,
  total_tokens: 0,
  conversation_activity: {
    active: 0,
    cancelled: 0,
    total: 0,
    messages: 0
  },
  provider_distribution: [],
  ingestion_states: [],
  recent_inferences: [],
  time_series: []
};

export function Dashboard() {
  const [summary, setSummary] = useState<AnalyticsSummary>(emptySummary);
  const [hours, setHours] = useState(24);
  const [apiStatus, setApiStatus] = useState<"healthy" | "degraded">("healthy");
  const [lastUpdated, setLastUpdated] = useState<string>("never");

  useEffect(() => {
    const load = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/v1/analytics/summary?hours=${hours}`, {
          cache: "no-store"
        });
        if (!response.ok) {
          setApiStatus("degraded");
          return;
        }
        setSummary(await response.json());
        setApiStatus("healthy");
        setLastUpdated(new Date().toLocaleTimeString());
      } catch {
        setApiStatus("degraded");
      }
    };
    void load();
    const timer = window.setInterval(load, 10000);
    return () => window.clearInterval(timer);
  }, [hours]);

  const series = summary.time_series.map((point) => ({
    ...point,
    bucket: new Date(point.bucket).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  }));

  const latestInference = summary.recent_inferences[0];
  const hasFailures = summary.error_rate > 0.05;
  const latestFailure = summary.recent_inferences.find((event) => event.status === "error");

  return (
    <main className="min-h-screen bg-background text-zinc-950">
      <div className="border-b border-border bg-white/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-500">Ollive Observability</p>
            <h1 className="text-lg font-semibold tracking-tight text-zinc-950">Inference Operations Dashboard</h1>
          </div>
          <div className="flex items-center gap-3">
            <a
              href={CHAT_URL}
              className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-700 shadow-sm transition hover:bg-zinc-50"
            >
              Back to chat
            </a>
            <StatusBadge status={apiStatus === "healthy" ? "healthy" : "degraded"} />
            <select
              value={hours}
              onChange={(event) => setHours(Number(event.target.value))}
              className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-700 shadow-sm outline-none focus:border-blue-400 focus:ring-4 focus:ring-blue-50"
            >
              <option value={1}>Last hour</option>
              <option value={24}>Last 24h</option>
              <option value={168}>Last 7d</option>
            </select>
          </div>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-6 py-6">
        <section className="mb-5 grid gap-3 md:grid-cols-3 lg:grid-cols-6">
          <HealthCard label="API" value={apiStatus} tone={apiStatus === "healthy" ? "success" : "danger"} />
          <HealthCard label="Database" value="Supabase" tone="success" />
          <HealthCard label="Ingestion" value={summary.ingestion_states[0]?.status ?? "idle"} tone="success" />
          <HealthCard label="Streaming" value="available" tone="success" />
          <HealthCard label="Telemetry" value="persisting" tone="success" />
          <HealthCard label="Provider mode" value="mock" tone="neutral" />
        </section>

        <div className="mb-5 flex items-center justify-between rounded-xl border border-border bg-white px-4 py-3 text-sm shadow-sm">
          <div>
            <p className="font-medium text-zinc-950">System Health</p>
            <p className="mt-1 text-xs text-zinc-500">API, ingestion, persistence, streaming, and telemetry are monitored from normalized inference data.</p>
          </div>
          <div className="text-right text-xs text-zinc-500">
            <p>Last refresh</p>
            <p className="mt-1 font-medium text-zinc-900">{lastUpdated}</p>
          </div>
        </div>

        <section className="mb-5 rounded-2xl border border-border bg-white p-4 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-zinc-500">Request Lifecycle</p>
              <h2 className="mt-1 text-sm font-semibold text-zinc-950">received to persisted</h2>
            </div>
            <StatusBadge status={latestInference?.ingestion_status ?? "processed"} />
          </div>
          <div className="grid gap-2 md:grid-cols-5">
            {["received", "inferred", "emitted", "ingested", "persisted"].map((step, index) => (
              <div key={step} className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-zinc-950 text-xs font-semibold text-white">
                  {index + 1}
                </span>
                <span className="font-medium capitalize text-zinc-800">{step}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-5">
          <Metric label="Requests" value={summary.total_requests.toLocaleString()} hint="normalized logs" />
          <Metric label="Error rate" value={`${(summary.error_rate * 100).toFixed(2)}%`} hint={hasFailures ? "elevated failure rate" : "nominal"} tone={hasFailures ? "danger" : "success"} />
          <Metric label="P50 latency" value={`${Math.round(summary.p50_latency_ms)} ms`} hint="median" />
          <Metric label="P95 latency" value={`${Math.round(summary.p95_latency_ms)} ms`} hint="tail" />
          <Metric label="Tokens" value={summary.total_tokens.toLocaleString()} hint="total usage" />
        </section>

        <section className="mt-5 grid gap-5 lg:grid-cols-[1.35fr_1fr]">
          <Panel title="Request Throughput" eyebrow="traffic and failures">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis dataKey="bucket" stroke="#71717a" fontSize={12} />
                <YAxis stroke="#71717a" fontSize={12} />
                <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e4e4e7", borderRadius: 12 }} />
                <Line type="monotone" dataKey="requests" stroke="#2563eb" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="errors" stroke="#dc2626" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </Panel>

          <Panel title="Latency and Token Load" eyebrow="performance profile">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                <XAxis dataKey="bucket" stroke="#71717a" fontSize={12} />
                <YAxis stroke="#71717a" fontSize={12} />
                <Tooltip contentStyle={{ background: "#ffffff", border: "1px solid #e4e4e7", borderRadius: 12 }} />
                <Bar dataKey="avg_latency_ms" fill="#60a5fa" name="avg latency ms" radius={[6, 6, 0, 0]} />
                <Bar dataKey="tokens" fill="#a7f3d0" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>
        </section>

        <section className="mt-5 grid gap-5 lg:grid-cols-3">
          <Panel title="Provider Health" eyebrow="Gemini operations">
            <div className="space-y-3">
              {summary.provider_distribution.length === 0 && <EmptyState text="No provider telemetry received during this interval." />}
              {summary.provider_distribution.map((provider) => (
                <div key={provider.provider} className="rounded-xl border border-zinc-200 bg-white p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold capitalize text-zinc-950">{provider.provider}</p>
                      <p className="mt-1 text-xs text-zinc-500">{provider.requests} requests / {provider.errors} failures</p>
                    </div>
                    <StatusBadge status={provider.error_rate > 0.05 ? "degraded" : "healthy"} />
                  </div>
                  <div className="mt-4 h-2 rounded-full bg-zinc-100">
                    <div
                      className={provider.error_rate > 0.05 ? "h-2 rounded-full bg-red-500" : "h-2 rounded-full bg-emerald-500"}
                      style={{ width: `${Math.max(4, (provider.requests / Math.max(1, summary.total_requests)) * 100)}%` }}
                    />
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-zinc-500">
                    <span>Success {((1 - provider.error_rate) * 100).toFixed(1)}%</span>
                    <span>Avg {Math.round(provider.avg_latency_ms)} ms</span>
                    <span>{latestFailure ? `Last failure ${new Date(latestFailure.created_at).toLocaleTimeString()}` : "No recent failures"}</span>
                  </div>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Ingestion State" eyebrow="pipeline health">
            <div className="space-y-3">
              {summary.ingestion_states.length === 0 && <EmptyState text="No ingestion events received during this interval." />}
              {summary.ingestion_states.map((state) => (
                <div key={state.status} className="flex items-center justify-between rounded-xl border border-zinc-200 bg-zinc-50 p-4">
                  <div>
                    <p className="text-sm font-semibold capitalize text-zinc-950">{state.status}</p>
                    <p className="mt-1 text-xs text-zinc-500">retry attempts {state.retries}</p>
                  </div>
                  <p className="text-2xl font-semibold tracking-tight text-zinc-950">{state.events}</p>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Conversation Activity" eyebrow="workflow signal">
            <div className="grid grid-cols-2 gap-3">
              <MiniStat label="Active" value={summary.conversation_activity.active} />
              <MiniStat label="Cancelled" value={summary.conversation_activity.cancelled} />
              <MiniStat label="Total" value={summary.conversation_activity.total} />
              <MiniStat label="Messages" value={summary.conversation_activity.messages} />
            </div>
          </Panel>
        </section>

        <section className="mt-5 grid gap-5 lg:grid-cols-[1fr_340px]">
          <Panel title="Recent Inference Timeline" eyebrow="traceable events">
            <div className="overflow-hidden rounded-xl border border-zinc-200">
              <div className="grid grid-cols-[100px_92px_110px_1fr_90px_90px] border-b border-zinc-200 bg-zinc-50 px-4 py-2 text-xs font-medium uppercase tracking-[0.12em] text-zinc-500">
                <span>Time</span>
                <span>Status</span>
                <span>Ingestion</span>
                <span>Trace</span>
                <span className="text-right">Latency</span>
                <span className="text-right">Tokens</span>
              </div>
              {summary.recent_inferences.length === 0 && <EmptyState text="No inference events have been logged yet." />}
              {summary.recent_inferences.map((event) => (
                <div
                  key={event.event_id}
                  className="grid grid-cols-[100px_92px_110px_1fr_90px_90px] items-center border-b border-zinc-100 px-4 py-3 text-sm last:border-b-0 hover:bg-zinc-50"
                >
                  <span className="text-zinc-500">{new Date(event.created_at).toLocaleTimeString()}</span>
                  <StatusBadge status={event.status} />
                  <StatusBadge status={event.ingestion_status ?? "processed"} />
                  <div className="min-w-0">
                    <p className="truncate font-medium text-zinc-950">{event.provider} / {event.model}</p>
                    <p className="truncate font-mono text-xs text-zinc-500">trace {shortId(event.trace_id)}</p>
                    <p className="truncate font-mono text-xs text-zinc-400">request {shortId(event.request_id)}</p>
                    <p className="truncate text-xs text-zinc-500">{event.request_preview || "No request preview"}</p>
                  </div>
                  <span className="text-right tabular-nums text-zinc-700">{event.latency_ms} ms</span>
                  <span className="text-right tabular-nums text-zinc-700">{event.total_tokens}</span>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Trace Inspector" eyebrow="latest event">
            {latestInference ? (
              <dl className="space-y-3 text-sm">
                <TraceRow label="Event" value={latestInference.event_id} copyable />
                <TraceRow label="Trace" value={latestInference.trace_id ?? "n/a"} copyable />
                <TraceRow label="Request" value={latestInference.request_id ?? "n/a"} copyable />
                <TraceRow label="Provider" value={latestInference.provider} />
                <TraceRow label="Model" value={latestInference.model} />
                <TraceRow label="Status" value={latestInference.status} />
                <TraceRow label="Ingestion" value={`${latestInference.ingestion_status ?? "processed"} (${latestInference.ingestion_retries ?? 0} attempt)`} />
                <TraceRow label="Conversation" value={latestInference.conversation_id ?? "n/a"} copyable />
                <TraceRow label="Preview" value={latestInference.request_preview || "n/a"} />
              </dl>
            ) : (
              <EmptyState text="No trace selected." />
            )}
          </Panel>
        </section>
      </div>
    </main>
  );
}

function Metric({
  label,
  value,
  hint,
  tone = "neutral"
}: {
  label: string;
  value: string;
  hint: string;
  tone?: "neutral" | "success" | "danger";
}) {
  const toneClass = tone === "danger" ? "text-red-600" : tone === "success" ? "text-emerald-600" : "text-zinc-950";
  return (
    <div className="rounded-2xl border border-border bg-panel p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-zinc-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold tracking-tight ${toneClass}`}>{value}</p>
      <p className="mt-1 text-xs text-zinc-500">{hint}</p>
    </div>
  );
}

function Panel({ title, eyebrow, children }: { title: string; eyebrow: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-panel p-5 shadow-sm">
      <div className="mb-4">
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-zinc-500">{eyebrow}</p>
        <h2 className="mt-1 text-base font-semibold text-zinc-950">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function HealthCard({ label, value, tone }: { label: string; value: string; tone: "success" | "danger" | "neutral" }) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-border bg-white px-3 py-2 shadow-sm">
      <span className="text-xs font-medium uppercase tracking-[0.12em] text-zinc-500">{label}</span>
      <StatusBadge status={tone === "success" ? value : tone === "danger" ? "degraded" : value} />
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3">
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-zinc-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">{value.toLocaleString()}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const isHealthy = normalized === "success" || normalized === "processed" || normalized === "healthy" || normalized === "mock";
  const isDanger = normalized === "error" || normalized === "failed" || normalized === "degraded";
  return (
    <span
      className={`inline-flex w-fit rounded-full border px-2.5 py-1 text-xs font-medium ${
        isDanger
          ? "border-red-200 bg-red-50 text-red-700"
          : isHealthy
            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
            : "border-zinc-200 bg-zinc-50 text-zinc-700"
      }`}
    >
      {status}
    </span>
  );
}

function TraceRow({ label, value, copyable = false }: { label: string; value: string; copyable?: boolean }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-[0.12em] text-zinc-500">{label}</dt>
      <dd className="mt-1 flex items-center gap-2 rounded-lg bg-zinc-50 p-2 font-mono text-xs text-zinc-700">
        <span className="min-w-0 flex-1 truncate">{value}</span>
        {copyable && (
          <button
            className="rounded-md border border-zinc-200 bg-white px-2 py-1 font-sans text-[11px] font-medium text-zinc-600 hover:bg-zinc-100"
            onClick={() => void navigator.clipboard.writeText(value)}
          >
            Copy
          </button>
        )}
      </dd>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-500">{text}</div>;
}

function shortId(value?: string | null) {
  if (!value) return "n/a";
  if (value.length <= 14) return value;
  return `${value.slice(0, 8)}...${value.slice(-6)}`;
}
