"""Dashboard aggregated statistics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core import telemetry
from app.schemas.run import DashboardStatsResponse, DashboardTimeseriesResponse
from app.services.persistence import get_dashboard_stats, get_dashboard_timeseries

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
def dashboard_stats(db: Session = Depends(get_db)) -> DashboardStatsResponse:
    """Return aggregated run counts and average confidence."""
    stats = get_dashboard_stats(db)
    telemetry.log_dashboard_stats(total_runs=stats.get("total_runs", 0))
    return DashboardStatsResponse(**stats)


@router.get("/stats/timeseries", response_model=DashboardTimeseriesResponse)
def dashboard_timeseries(
    db: Session = Depends(get_db),
    bucket: str = Query(default="day", pattern="^day$"),
    days: int = Query(default=14, ge=1, le=90),
) -> DashboardTimeseriesResponse:
    """Return daily run counts grouped by routing decision (trend chart)."""
    data = get_dashboard_timeseries(db, days=days)
    telemetry.log_dashboard_timeseries(days=days, point_count=len(data.get("points", [])))
    return DashboardTimeseriesResponse(**data)
