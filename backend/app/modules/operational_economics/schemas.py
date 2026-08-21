from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


VARIABLE_COST_TYPES = {
    "chef_payout",
    "delivery_partner",
    "payment_processing",
    "packaging",
    "refund_fee",
    "customer_recovery",
    "other_variable",
    "communications_provider",
    "cloud_storage",
    "cloud_infrastructure",
    "provider_adjustment",
}


class CostEntryCreate(BaseModel):
    pilot_program_id: UUID | None = None
    order_id: UUID | None = None
    area: str | None = Field(default=None, max_length=120)
    incurred_on: date
    cost_type: str = Field(max_length=40)
    amount_minor: int = Field(gt=0)
    currency: str = Field(default="EGP", pattern=r"^EGP$")
    source: str = Field(default="manual", pattern=r"^(manual|provider|import)$")
    external_reference: str | None = Field(default=None, max_length=180)
    note: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_cost_type(self):
        allowed = VARIABLE_COST_TYPES | {"fixed_operations"}
        if self.cost_type not in allowed:
            raise ValueError("unsupported cost_type")
        if self.order_id is not None and self.cost_type == "fixed_operations":
            raise ValueError("fixed_operations cannot be order-scoped")
        return self


class CostEntryResponse(BaseModel):
    id: UUID
    pilot_program_id: UUID | None
    order_id: UUID | None
    area: str | None
    incurred_on: date
    cost_type: str
    cost_scope: str
    amount_minor: int
    currency: str
    source: str
    external_reference: str | None
    note: str | None
    is_verified: bool
    verified_by_admin_id: UUID | None
    verified_at: datetime | None
    created_by_admin_id: UUID | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class CostBreakdownItem(BaseModel):
    cost_type: str
    amount_minor: int


class EconomicsReport(BaseModel):
    program_id: UUID
    area: str | None
    period_start: date
    period_end: date
    delivered_orders: int
    delivered_gmv_minor: int
    succeeded_payment_orders: int
    captured_minor: int
    refunded_minor: int
    net_collected_minor: int
    revenue_coverage_pct: float
    variable_cost_minor: int
    fixed_cost_minor: int
    contribution_minor: int
    contribution_margin_pct: float | None
    contribution_per_delivered_order_minor: int | None
    operational_profit_minor: int
    operational_profit_margin_pct: float | None
    required_order_cost_types: list[str]
    fully_costed_delivered_orders: int
    cost_coverage_pct: float
    unverified_cost_entries: int
    cost_breakdown: list[CostBreakdownItem]
    economics_evaluable: bool
    operational_profit_positive: bool | None
    blockers: list[str]
    generated_at: datetime


class ExpansionZoneCreate(BaseModel):
    area: str = Field(min_length=2, max_length=120)
    source_program_id: UUID
    min_delivered_orders: int | None = Field(default=None, gt=0)
    min_contribution_margin_pct: float | None = Field(default=None, ge=-100, le=100)
    min_operational_profit_minor: int = Field(default=1)
    notes: str | None = Field(default=None, max_length=4000)


class ExpansionZoneResponse(BaseModel):
    id: UUID
    area: str
    source_program_id: UUID
    status: str
    min_delivered_orders: int
    min_contribution_margin_pct: float
    min_operational_profit_minor: int
    notes: str | None
    created_by_admin_id: UUID | None
    approved_by_admin_id: UUID | None
    approved_at: datetime | None
    launched_at: datetime | None
    paused_at: datetime | None
    rollout_stage: str
    rollout_percent: int
    daily_order_cap: int | None
    rollout_started_at: datetime | None
    rollout_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ExpansionAssessmentResponse(BaseModel):
    id: UUID
    zone_id: UUID
    program_id: UUID
    period_start: date
    period_end: date
    delivered_orders: int
    net_collected_minor: int
    variable_cost_minor: int
    contribution_minor: int
    contribution_margin_pct: float | None
    fixed_cost_minor: int
    operational_profit_minor: int
    cost_coverage_pct: float
    revenue_coverage_pct: float
    unverified_cost_entries: int
    economics_evaluable: bool
    stability_gate_met: bool
    post_pilot_scale_ready: bool
    decision: str
    blockers_json: list[str]
    generated_at: datetime
    generated_by_admin_id: UUID | None
    model_config = {"from_attributes": True}


class ExpansionZoneDetail(BaseModel):
    zone: ExpansionZoneResponse
    latest_assessment: ExpansionAssessmentResponse | None
