from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from collections import Counter

from database import get_db
from auth import require_admin
import models, schemas

router = APIRouter(prefix="/analytics", tags=["analytics"])


def time_period(hour: int) -> str:
    if 5  <= hour < 12: return "Morning"
    if 12 <= hour < 17: return "Afternoon"
    if 17 <= hour < 21: return "Evening"
    return "Night"


@router.get("/", response_model=schemas.AnalyticsSummary)
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    _:  models.User  = Depends(require_admin),
):
    # Totals
    total    = await db.scalar(select(func.count()).select_from(models.Report))
    pending  = await db.scalar(
        select(func.count()).select_from(models.Report)
        .where(models.Report.status == models.IssueStatus.pending)
    )
    resolved = await db.scalar(
        select(func.count()).select_from(models.Report)
        .where(models.Report.status == models.IssueStatus.resolved)
    )

    # Area distribution
    area_rows = await db.execute(
        select(models.Report.area_zone, func.count().label("n"))
        .group_by(models.Report.area_zone)
        .order_by(func.count().desc())
    )
    top_areas = {row.area_zone: row.n for row in area_rows}

    # Issue type distribution
    issue_rows = await db.execute(
        select(models.Detection.issue_type, func.count().label("n"))
        .group_by(models.Detection.issue_type)
        .order_by(func.count().desc())
    )
    top_issues = {row.issue_type: row.n for row in issue_rows}

    # Time-of-day distribution
    report_times = await db.execute(select(models.Report.created_at))
    time_counts: Counter = Counter()
    for (ts,) in report_times:
        if ts:
            time_counts[time_period(ts.hour)] += 1

    return schemas.AnalyticsSummary(
        total_reports=total or 0,
        pending_count=pending or 0,
        resolved_count=resolved or 0,
        top_areas=top_areas,
        top_issues_globally=top_issues,
        time_of_day_distribution=dict(time_counts),
    )
