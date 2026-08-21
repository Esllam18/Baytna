from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class IncidentResponse(BaseModel):
    id: UUID
    fingerprint: str
    category: str
    severity: str
    status: str
    source_type: str
    source_id: str | None
    title: str
    message: str
    details_json: dict
    owner_admin_id: UUID | None
    detected_at: datetime
    last_detected_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by_admin_id: UUID | None
    resolved_at: datetime | None
    resolved_by_admin_id: UUID | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncidentAssignRequest(BaseModel):
    admin_id: UUID | None = None


class IncidentEscalateRequest(BaseModel):
    note: str | None = Field(default=None, max_length=1000)


class IncidentResolveRequest(BaseModel):
    note: str = Field(min_length=2, max_length=2000)


class IncidentRefreshResponse(BaseModel):
    detected: int
    created: int
    updated: int
    auto_resolved: int
    auto_escalated: int = 0
    admin_notifications_planned: int = 0
    active_incidents: int


class LaunchKpis(BaseModel):
    days: int
    orders_created: int
    delivered_orders: int
    cancelled_orders: int
    cancellation_rate_pct: float
    delivery_success_rate_pct: float
    gmv_minor: int
    repeat_customer_rate_pct: float
    average_chef_rating: float
    reviews_count: int
    chef_acceptance_sla_breaches: int
    support_sla_breaches: int
    payment_reconciliation_open: int
    notification_dead_letters: int
    outbox_dead_letters: int
    background_job_dead_letters: int
    stale_workers: int
    launch_target_rating_met: bool
    launch_target_repeat_met: bool
    on_time_delivery_rate_pct: float | None
    on_time_measurable_deliveries: int
    late_deliveries: int
    delivery_promise_coverage_pct: float
    launch_target_on_time_met: bool | None
    launch_target_cancellation_met: bool


class ControlRoomOverview(BaseModel):
    generated_at: datetime
    health: str
    active_incidents: int
    critical_incidents: int
    high_incidents: int
    unacknowledged_incidents: int
    urgent_support_open: int
    open_payment_reconciliation: int
    worker_status: str
    kpis: LaunchKpis
    top_incidents: list[IncidentResponse]


class DailyActionItem(BaseModel):
    priority: str
    title: str
    detail: str
    route: str | None = None


class DailyBrief(BaseModel):
    day: date
    generated_at: datetime
    health: str
    opening_orders: int
    delivered_orders: int
    cancelled_orders: int
    gmv_minor: int
    active_incidents: int
    critical_incidents: int
    urgent_support_open: int
    available_drivers: int
    open_chefs: int
    actions: list[DailyActionItem]
