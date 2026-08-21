from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class TrafficPolicyUpdate(BaseModel):
    is_enabled: bool = True
    hourly_order_cap: int | None = Field(default=None, gt=0)
    chef_daily_order_cap: int | None = Field(default=None, gt=0)
    enforce_rollout_bucket: bool = True
    warning_utilization_pct: float = Field(default=80.0, gt=0, le=100)
    critical_utilization_pct: float = Field(default=95.0, gt=0, le=100)
    rejection_spike_pct: float = Field(default=30.0, gt=0, le=100)
    rejection_spike_min_attempts: int = Field(default=5, gt=0)
    slo_auto_pause_enabled: bool = False
    slo_consecutive_red_snapshots: int = Field(default=2, ge=2, le=20)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_threshold_order(self):
        if self.warning_utilization_pct > self.critical_utilization_pct:
            raise ValueError(
                "warning_utilization_pct cannot exceed critical_utilization_pct"
            )
        return self


class TrafficPolicyResponse(BaseModel):
    zone_id: UUID
    is_enabled: bool
    hourly_order_cap: int | None
    chef_daily_order_cap: int | None
    enforce_rollout_bucket: bool
    warning_utilization_pct: float
    critical_utilization_pct: float
    rejection_spike_pct: float
    rejection_spike_min_attempts: int
    slo_auto_pause_enabled: bool
    slo_consecutive_red_snapshots: int
    note: str | None
    created_by_admin_id: UUID | None
    updated_by_admin_id: UUID | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class AdmissionEventResponse(BaseModel):
    id: UUID
    zone_id: UUID
    order_id: UUID | None
    customer_id: UUID
    chef_id: UUID
    service_date: date
    area: str
    decision: str
    reason: str
    rollout_stage: str
    rollout_percent: int
    rollout_bucket: int | None
    daily_cap: int | None
    daily_usage_before: int
    hourly_cap: int | None
    hourly_usage_before: int
    chef_daily_cap: int | None
    chef_usage_before: int
    request_id: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class AdmissionDecision(BaseModel):
    governed: bool
    admitted: bool
    zone_id: UUID | None = None
    reason: str
    rollout_stage: str | None = None
    rollout_percent: int | None = None
    rollout_bucket: int | None = None
    daily_cap: int | None = None
    daily_usage_before: int = 0
    hourly_cap: int | None = None
    hourly_usage_before: int = 0
    chef_daily_cap: int | None = None
    chef_usage_before: int = 0
    event_id: UUID | None = None


class MonitoringSnapshotResponse(BaseModel):
    id: UUID
    zone_id: UUID
    service_date: date
    rollout_stage: str
    rollout_percent: int
    zone_daily_cap: int | None
    admitted_orders_today: int
    daily_utilization_pct: float
    hourly_cap: int | None
    admitted_orders_last_hour: int
    hourly_utilization_pct: float
    admission_attempts_last_hour: int
    admission_rejections_last_hour: int
    rejection_rate_pct: float
    available_drivers: int
    open_chefs: int
    top_chef_orders: int
    chef_daily_cap: int | None
    top_chef_utilization_pct: float
    health: str
    blockers_json: list[str]
    generated_by: str
    observed_at: datetime
    model_config = {"from_attributes": True}


class CapacityForecastResponse(BaseModel):
    id: UUID
    zone_id: UUID
    monitoring_snapshot_id: UUID
    service_date: date
    horizon_minutes: int
    sample_count: int
    current_orders_last_hour: int
    projected_orders_next_hour: float
    hourly_cap: int | None
    projected_hourly_utilization_pct: float
    current_daily_orders: int
    daily_cap: int | None
    daily_headroom_orders: int | None
    projected_minutes_to_daily_cap: int | None
    risk: str
    reasons_json: list[str]
    generated_at: datetime
    model_config = {"from_attributes": True}


class TrafficZoneOverview(BaseModel):
    zone_id: UUID
    area: str
    zone_status: str
    rollout_stage: str
    rollout_percent: int
    daily_order_cap: int | None
    policy: TrafficPolicyResponse
    latest_monitoring: MonitoringSnapshotResponse | None
    latest_forecast: CapacityForecastResponse | None = None



class TrafficCapsUpdate(BaseModel):
    daily_order_cap: int | None = Field(default=None, gt=0)
    hourly_order_cap: int | None = Field(default=None, gt=0)
    chef_daily_order_cap: int | None = Field(default=None, gt=0)


class TrafficCapsResponse(BaseModel):
    zone_id: UUID
    daily_order_cap: int | None
    hourly_order_cap: int | None
    chef_daily_order_cap: int | None
