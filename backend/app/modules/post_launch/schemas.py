from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExpansionReviewResponse(BaseModel):
    id: UUID
    zone_id: UUID
    session_id: UUID | None
    review_date: date
    window_start: date
    window_end: date
    status: str
    recommendation: str
    monitoring_snapshots: int
    red_snapshots: int
    amber_snapshots: int
    auto_pause_events: int
    required_closes: int
    closed_closes: int
    overdue_closes: int
    blocked_closes: int
    latest_forecast_risk: str | None
    blockers_json: list
    evidence_json: dict
    generated_by: str
    generated_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PostLaunchSummary(BaseModel):
    zones_reviewed: int
    healthy: int
    watch: int
    blocked: int
    continue_count: int
    hold_count: int
    pause_count: int
    reviews: list[ExpansionReviewResponse]
