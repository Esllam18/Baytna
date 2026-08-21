from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


PROVIDER_COST_TYPES = {
    "chef_payout",
    "delivery_partner",
    "payment_processing",
    "packaging",
    "refund_fee",
    "customer_recovery",
    "other_variable",
    "fixed_operations",
    "communications_provider",
    "cloud_storage",
    "cloud_infrastructure",
    "provider_adjustment",
}

BUDGET_CATEGORIES = {
    "operations",
    "marketing",
    "chef_onboarding",
    "delivery_supply",
    "contingency",
    "support",
    "technology",
}


class ProviderCostLineInput(BaseModel):
    line_key: str = Field(min_length=1, max_length=180)
    order_id: UUID | None = None
    incurred_on: date
    cost_type: str = Field(max_length=40)
    source_amount_minor: int = Field(gt=0)
    external_reference: str | None = Field(default=None, max_length=220)
    description: str | None = Field(default=None, max_length=2000)
    raw_json: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_cost_type(self):
        if self.cost_type not in PROVIDER_COST_TYPES:
            raise ValueError("unsupported provider cost_type")
        return self


class ProviderCostImportCreate(BaseModel):
    provider: str = Field(min_length=2, max_length=40)
    pilot_program_id: UUID | None = None
    area: str | None = Field(default=None, max_length=120)
    period_start: date
    period_end: date
    source_currency: str = Field(min_length=3, max_length=3)
    fx_rate_to_egp: float | None = Field(default=None, gt=0)
    fx_reference: str | None = Field(default=None, max_length=240)
    external_reference: str = Field(min_length=2, max_length=180)
    lines: list[ProviderCostLineInput]

    @model_validator(mode="after")
    def validate_period_and_fx(self):
        self.provider = self.provider.strip().lower()
        self.source_currency = self.source_currency.upper()
        if self.period_end < self.period_start:
            raise ValueError("period_end before period_start")
        if self.source_currency != "EGP":
            if self.fx_rate_to_egp is None:
                raise ValueError("fx_rate_to_egp required for non-EGP import")
            if not (self.fx_reference or "").strip():
                raise ValueError("fx_reference required for non-EGP import")
        return self


class ProviderCostImportBatchResponse(BaseModel):
    id: UUID
    provider: str
    pilot_program_id: UUID | None
    area: str | None
    period_start: date
    period_end: date
    source_currency: str
    fx_rate_to_egp: float | None
    fx_reference: str | None
    external_reference: str
    checksum_sha256: str
    status: str
    rows_count: int
    total_source_minor: int
    total_egp_minor: int
    applied_cost_entries: int
    validation_errors_json: list
    review_status: str
    assigned_reviewer_id: UUID | None
    reviewed_by_admin_id: UUID | None
    review_note: str | None
    risk_flags_json: list
    reviewed_at: datetime | None
    created_by_admin_id: UUID | None
    validated_by_admin_id: UUID | None
    applied_by_admin_id: UUID | None
    validated_at: datetime | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ProviderCostImportLineResponse(BaseModel):
    id: UUID
    batch_id: UUID
    line_key: str
    order_id: UUID | None
    incurred_on: date
    cost_type: str
    source_amount_minor: int
    source_currency: str
    egp_amount_minor: int
    external_reference: str | None
    description: str | None
    raw_json: dict
    applied_cost_entry_id: UUID | None
    created_at: datetime
    model_config = {"from_attributes": True}


class ProviderCostImportDetail(BaseModel):
    batch: ProviderCostImportBatchResponse
    lines: list[ProviderCostImportLineResponse]


class TwilioUsageSyncRequest(BaseModel):
    pilot_program_id: UUID | None = None
    area: str | None = Field(default=None, max_length=120)
    period_start: date
    period_end: date
    category: str = Field(default="totalprice", min_length=2, max_length=120)
    fx_rate_to_egp: float | None = Field(default=None, gt=0)
    fx_reference: str | None = Field(default=None, max_length=240)
    external_reference: str = Field(min_length=2, max_length=180)


class SettlementLineInput(BaseModel):
    provider_transaction_id: str = Field(min_length=1, max_length=180)
    settlement_reference: str | None = Field(default=None, max_length=180)
    gross_amount_minor: int = Field(ge=0)
    fee_minor: int = Field(default=0, ge=0)
    refund_minor: int = Field(default=0, ge=0)
    net_settlement_minor: int = Field(ge=0)
    is_settled: bool
    settled_at: datetime | None = None
    raw_json: dict = Field(default_factory=dict)


class SettlementBatchCreate(BaseModel):
    provider: str = Field(default="paymob", min_length=2, max_length=40)
    pilot_program_id: UUID | None = None
    period_start: date
    period_end: date
    currency: str = Field(default="EGP", min_length=3, max_length=3)
    external_reference: str = Field(min_length=2, max_length=180)
    lines: list[SettlementLineInput]

    @model_validator(mode="after")
    def validate_batch(self):
        self.provider = self.provider.strip().lower()
        self.currency = self.currency.upper()
        if self.period_end < self.period_start:
            raise ValueError("period_end before period_start")
        if self.provider != "paymob":
            raise ValueError("Sprint 47 settlement reconciliation supports paymob")
        if self.currency != "EGP":
            raise ValueError("Paymob settlement import must be EGP")
        return self


class SettlementBatchResponse(BaseModel):
    id: UUID
    provider: str
    pilot_program_id: UUID | None
    period_start: date
    period_end: date
    currency: str
    external_reference: str
    checksum_sha256: str
    status: str
    rows_count: int
    matched_lines: int
    mismatched_lines: int
    gross_minor: int
    fees_minor: int
    refunds_minor: int
    net_settlement_minor: int
    blockers_json: list
    operations_status: str
    assigned_admin_id: UUID | None
    closed_by_admin_id: UUID | None
    close_note: str | None
    closed_at: datetime | None
    created_by_admin_id: UUID | None
    reconciled_by_admin_id: UUID | None
    reconciled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class SettlementLineResponse(BaseModel):
    id: UUID
    batch_id: UUID
    provider_transaction_id: str
    settlement_reference: str | None
    gross_amount_minor: int
    fee_minor: int
    refund_minor: int
    net_settlement_minor: int
    currency: str
    is_settled: bool
    settled_at: datetime | None
    matched_payment_id: UUID | None
    reconciliation_status: str
    issues_json: list
    applied_cost_entry_id: UUID | None
    raw_json: dict
    created_at: datetime
    model_config = {"from_attributes": True}


class SettlementBatchDetail(BaseModel):
    batch: SettlementBatchResponse
    lines: list[SettlementLineResponse]


class ZoneBudgetUpsert(BaseModel):
    category: str = Field(min_length=2, max_length=40)
    allocated_minor: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_category(self):
        self.category = self.category.strip().lower()
        if self.category not in BUDGET_CATEGORIES:
            raise ValueError("unsupported budget category")
        return self


class ZoneBudgetMovement(BaseModel):
    action: str = Field(pattern=r"^(commit|release|spend)$")
    amount_minor: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=2000)


class ZoneBudgetResponse(BaseModel):
    id: UUID
    zone_id: UUID
    category: str
    allocated_minor: int
    committed_minor: int
    spent_minor: int
    currency: str
    note: str | None
    created_by_admin_id: UUID | None
    updated_by_admin_id: UUID | None
    created_at: datetime
    updated_at: datetime
    remaining_minor: int = 0
    model_config = {"from_attributes": True}


class ZoneBudgetSummary(BaseModel):
    zone_id: UUID
    required_categories: list[str]
    present_categories: list[str]
    missing_categories: list[str]
    allocated_minor: int
    committed_minor: int
    spent_minor: int
    remaining_minor: int
    budget_ready: bool
    budgets: list[ZoneBudgetResponse]


class RolloutRequest(BaseModel):
    daily_order_cap: int | None = Field(default=None, gt=0)


class RolloutResponse(BaseModel):
    zone_id: UUID
    zone_status: str
    rollout_stage: str
    rollout_percent: int
    daily_order_cap: int | None
    assessment_id: UUID | None
    budget_ready: bool
    payment_reconciliation_open: int
    blocked_settlement_batches: int
    blockers: list[str]
    event_id: UUID | None = None


class RolloutEventResponse(BaseModel):
    id: UUID
    zone_id: UUID
    from_stage: str
    to_stage: str
    rollout_percent: int
    daily_order_cap: int | None
    assessment_id: UUID | None
    budget_snapshot_json: dict
    triggered_by_admin_id: UUID | None
    trigger_source: str
    trigger_reason: str | None
    trigger_evidence_json: dict
    created_at: datetime
    model_config = {"from_attributes": True}
