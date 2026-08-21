from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QueueAssignRequest(BaseModel):
    admin_id: UUID | None = None


class ReviewDecisionRequest(BaseModel):
    note: str = Field(min_length=2, max_length=3000)


class SettlementCloseRequest(BaseModel):
    note: str = Field(min_length=2, max_length=3000)


class ImportReviewItem(BaseModel):
    id: UUID
    provider: str
    pilot_program_id: UUID | None
    area: str | None
    period_start: date
    period_end: date
    source_currency: str
    external_reference: str
    status: str
    review_status: str
    rows_count: int
    total_egp_minor: int
    applied_cost_entries: int
    validation_errors_json: list
    risk_flags_json: list[str]
    created_by_admin_id: UUID | None
    assigned_reviewer_id: UUID | None
    reviewed_by_admin_id: UUID | None
    review_note: str | None
    validated_at: datetime | None
    reviewed_at: datetime | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class SettlementOperationsItem(BaseModel):
    id: UUID
    provider: str
    pilot_program_id: UUID | None
    period_start: date
    period_end: date
    external_reference: str
    status: str
    operations_status: str
    rows_count: int
    matched_lines: int
    mismatched_lines: int
    gross_minor: int
    fees_minor: int
    refunds_minor: int
    net_settlement_minor: int
    blockers_json: list[str]
    created_by_admin_id: UUID | None
    assigned_admin_id: UUID | None
    reconciled_by_admin_id: UUID | None
    closed_by_admin_id: UUID | None
    close_note: str | None
    reconciled_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class VendorAccountingSummary(BaseModel):
    imports_pending_review: int
    imports_assigned: int
    imports_approved: int
    imports_rejected: int
    imports_high_risk_open: int
    settlements_open: int
    settlements_in_review: int
    settlements_closed: int
    settlements_reopened: int
    settlements_blocked: int
