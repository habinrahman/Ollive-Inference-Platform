from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.analytics import AnalyticsSummary
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(
    hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_session),
) -> AnalyticsSummary:
    return await AnalyticsService(db).summary(hours=hours)
