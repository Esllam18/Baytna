from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class PilotProgramCreate(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    area: str | None = Field(default=None, max_length=120)
    start_date: date
    end_date: date | None = None
    required_stability_weeks: int = Field(default=8, ge=8, le=26)
    rating_target: float = Field(default=4.7, ge=1, le=5)
    repeat_customer_target_pct: float = Field(default=40.0, ge=0, le=100)
    on_time_target_pct: float = Field(default=95.0, ge=0, le=100)
    cancellation_max_pct: float = Field(default=5.0, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class PilotProgramResponse(BaseModel):
    id: UUID
    name: str
    area: str | None
    start_date: date
    end_date: date | None
    status: str
    required_stability_weeks: int
    rating_target: float
    repeat_customer_target_pct: float
    on_time_target_pct: float
    cancellation_max_pct: float
    notes: str | None
    created_by_admin_id: UUID | None
    activated_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PilotWeeklySnapshotResponse(BaseModel):
    id: UUID
    program_id: UUID
    week_index: int
    week_start: date
    week_end: date
    is_full_week: bool
    is_complete: bool
    orders_created: int
    delivered_orders: int
    cancelled_orders: int
    cancellation_rate_pct: float
    unique_customers: int
    repeat_customers: int
    repeat_customer_rate_pct: float
    average_chef_rating: float | None
    reviews_count: int
    on_time_delivery_rate_pct: float | None
    on_time_measurable_deliveries: int
    late_deliveries: int
    delivery_promise_coverage_pct: float
    gmv_minor: int
    captured_minor: int
    refunded_minor: int
    net_collected_minor: int
    support_tickets: int
    refund_count: int
    refund_rate_pct: float
    rating_met: bool | None
    repeat_met: bool | None
    on_time_met: bool | None
    cancellation_met: bool | None
    week_evaluable: bool
    week_passed: bool | None
    generated_at: datetime

    model_config = {"from_attributes": True}


class PilotStabilityReport(BaseModel):
    program: PilotProgramResponse
    required_weeks: int
    complete_full_weeks: int
    evaluable_weeks: int
    passed_weeks: int
    current_consecutive_passed_weeks: int
    max_consecutive_passed_weeks: int
    stability_gate_met: bool
    blockers: list[str]
    weeks: list[PilotWeeklySnapshotResponse]


class CohortRetentionCell(BaseModel):
    week_offset: int
    active_customers: int
    retention_pct: float


class PilotCohortRow(BaseModel):
    cohort_week: int
    cohort_start: date
    cohort_end: date
    cohort_size: int
    retention: list[CohortRetentionCell]


class PilotCohortReport(BaseModel):
    program_id: UUID
    max_weeks: int
    acquired_customers: int
    cohorts: list[PilotCohortRow]


class PilotQaEvidenceUpsert(BaseModel):
    status: str = Field(pattern=r"^(pending|passed|failed|not_applicable)$")
    reference: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=4000)
    observed_at: datetime | None = None

    @model_validator(mode="after")
    def passed_requires_reference(self):
        if self.status == "passed" and not (self.reference or "").strip():
            raise ValueError("passed evidence requires a reference")
        return self


class PilotQaEvidenceResponse(BaseModel):
    id: UUID
    program_id: UUID
    evidence_type: str
    status: str
    reference: str | None
    notes: str | None
    observed_at: datetime | None
    verified_by_admin_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PilotPostPilotReport(BaseModel):
    program: PilotProgramResponse
    generated_at: datetime
    duration_days: int
    orders_created: int
    delivered_orders: int
    cancelled_orders: int
    cancellation_rate_pct: float
    gmv_minor: int
    captured_minor: int
    refunded_minor: int
    net_collected_minor: int
    average_order_value_minor: int
    unique_delivered_customers: int
    repeat_customer_rate_pct: float
    average_chef_rating: float | None
    reviews_count: int
    on_time_delivery_rate_pct: float | None
    delivery_promise_coverage_pct: float
    support_tickets: int
    support_tickets_per_100_orders: float
    refunds_count: int
    refund_rate_pct: float
    active_critical_incidents: int
    open_payment_reconciliation_issues: int
    acquired_customer_cohorts: int
    weighted_w1_retention_pct: float | None
    weighted_w4_retention_pct: float | None
    stability_gate_met: bool
    current_consecutive_passed_weeks: int
    required_stability_weeks: int
    profitability_calculated_from_backend: bool
    operational_profit_evidence_status: str
    qa_exit_evidence_status: str
    operations_signoff_status: str
    scale_ready: bool
    scale_blockers: list[str]
