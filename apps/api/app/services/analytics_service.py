from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import (
    AnalyticsSummary,
    ConversationActivity,
    IngestionStateMetric,
    MetricPoint,
    ProviderMetric,
    RecentInference,
)


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self, *, hours: int = 24) -> AnalyticsSummary:
        totals = (
            await self.session.execute(
                text(
                    """
                    select
                      count(*)::int as total_requests,
                      coalesce(avg(latency_ms), 0)::float as avg_latency_ms,
                      coalesce(percentile_cont(0.50) within group (order by latency_ms), 0)::float as p50_latency_ms,
                      coalesce(percentile_cont(0.95) within group (order by latency_ms), 0)::float as p95_latency_ms,
                      coalesce(percentile_cont(0.99) within group (order by latency_ms), 0)::float as p99_latency_ms,
                      coalesce(sum(total_tokens), 0)::int as total_tokens,
                      coalesce(sum(case when status = 'error' then 1 else 0 end), 0)::int as errors
                    from inference_logs
                    where request_timestamp >= now() - (:hours * interval '1 hour')
                    """
                ),
                {"hours": hours},
            )
        ).mappings().one()

        providers = (
            await self.session.execute(
                text(
                    """
                    select
                      provider,
                      count(*)::int as requests,
                      coalesce(sum(case when status = 'error' then 1 else 0 end), 0)::int as errors,
                      coalesce(avg(latency_ms), 0)::float as avg_latency_ms
                    from inference_logs
                    where request_timestamp >= now() - (:hours * interval '1 hour')
                    group by provider
                    order by requests desc
                    """
                ),
                {"hours": hours},
            )
        ).mappings().all()

        series = (
            await self.session.execute(
                text(
                    """
                    select
                      date_trunc('hour', request_timestamp) as bucket,
                      count(*)::int as requests,
                      coalesce(sum(case when status = 'error' then 1 else 0 end), 0)::int as errors,
                      coalesce(avg(latency_ms), 0)::float as avg_latency_ms,
                      coalesce(sum(total_tokens), 0)::int as tokens
                    from inference_logs
                    where request_timestamp >= now() - (:hours * interval '1 hour')
                    group by bucket
                    order by bucket asc
                    """
                ),
                {"hours": hours},
            )
        ).mappings().all()

        ingestion_states = (
            await self.session.execute(
                text(
                    """
                    select
                      status,
                      count(*)::int as events,
                      coalesce(sum(retry_count), 0)::int as retries
                    from ingestion_events
                    where created_at >= now() - (:hours * interval '1 hour')
                    group by status
                    order by events desc
                    """
                ),
                {"hours": hours},
            )
        ).mappings().all()

        conversation_activity = (
            await self.session.execute(
                text(
                    """
                    with recent_conversations as (
                      select id, status
                      from conversations
                      where created_at >= now() - (:hours * interval '1 hour')
                    ),
                    message_counts as (
                      select count(*)::int as messages
                      from chat_messages
                      where conversation_id in (select id from recent_conversations)
                    )
                    select
                      coalesce(sum(case when rc.status = 'active' then 1 else 0 end), 0)::int as active,
                      coalesce(sum(case when rc.status = 'cancelled' then 1 else 0 end), 0)::int as cancelled,
                      count(rc.id)::int as total,
                      (select messages from message_counts)::int as messages
                    from recent_conversations rc
                    """
                ),
                {"hours": hours},
            )
        ).mappings().one()

        recent_inferences = (
            await self.session.execute(
                text(
                    """
                    select
                      l.event_id,
                      l.trace_id,
                      l.request_id,
                      l.conversation_id::text as conversation_id,
                      l.provider,
                      l.model,
                      l.status,
                      l.latency_ms,
                      l.total_tokens,
                      l.request_preview,
                      l.response_preview,
                      l.error_type,
                      e.status as ingestion_status,
                      coalesce(e.retry_count, 0)::int as ingestion_retries,
                      l.created_at
                    from inference_logs l
                    left join ingestion_events e on e.event_id = l.event_id
                    order by l.created_at desc
                    limit 12
                    """
                )
            )
        ).mappings().all()

        total_requests = totals["total_requests"]
        errors = totals["errors"]
        return AnalyticsSummary(
            total_requests=total_requests,
            error_rate=(errors / total_requests) if total_requests else 0,
            avg_latency_ms=totals["avg_latency_ms"],
            p50_latency_ms=totals["p50_latency_ms"],
            p95_latency_ms=totals["p95_latency_ms"],
            p99_latency_ms=totals["p99_latency_ms"],
            total_tokens=totals["total_tokens"],
            conversation_activity=ConversationActivity(**conversation_activity),
            provider_distribution=[
                ProviderMetric(
                    provider=row["provider"],
                    requests=row["requests"],
                    errors=row["errors"],
                    error_rate=(row["errors"] / row["requests"]) if row["requests"] else 0,
                    avg_latency_ms=row["avg_latency_ms"],
                )
                for row in providers
            ],
            ingestion_states=[IngestionStateMetric(**row) for row in ingestion_states],
            recent_inferences=[
                RecentInference(
                    event_id=row["event_id"],
                    trace_id=row["trace_id"],
                    request_id=row["request_id"],
                    conversation_id=row["conversation_id"],
                    provider=row["provider"],
                    model=row["model"],
                    status=row["status"],
                    latency_ms=row["latency_ms"],
                    total_tokens=row["total_tokens"],
                    request_preview=row["request_preview"],
                    response_preview=row["response_preview"],
                    error_type=row["error_type"],
                    ingestion_status=row["ingestion_status"],
                    ingestion_retries=row["ingestion_retries"],
                    created_at=row["created_at"].isoformat(),
                )
                for row in recent_inferences
            ],
            time_series=[
                MetricPoint(
                    bucket=row["bucket"].isoformat(),
                    requests=row["requests"],
                    errors=row["errors"],
                    avg_latency_ms=row["avg_latency_ms"],
                    tokens=row["tokens"],
                )
                for row in series
            ],
        )
