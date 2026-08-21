from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class LaunchSessionCreate(BaseModel):
    pilot_program_id: UUID
    zone_id: UUID
    launch_date: date
    incident_commander_admin_id: UUID
    finance_admin_id: UUID | None = None
    operations_admin_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=4000)


class LaunchSessionResponse(BaseModel):
    id: UUID
    pilot_program_id: UUID
    zone_id: UUID
    launch_date: date
    status: str
    incident_commander_admin_id: UUID
    finance_admin_id: UUID | None
    operations_admin_id: UUID | None
    notes: str | None
    created_by_admin_id: UUID
    started_at: datetime | None
    paused_at: datetime | None
    completed_at: datetime | None
    aborted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class LaunchRunbookStepResponse(BaseModel):
    id: UUID
    session_id: UUID
    step_key: str
    sequence: int
    category: str
    title: str
    is_required: bool
    status: str
    evidence_reference: str | None
    note: str | None
    completed_by_admin_id: UUID | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class RunbookStepDecision(BaseModel):
    status: str
    evidence_reference: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def validate_status(self):
        if self.status not in {"passed", "failed", "skipped", "pending"}:
            raise ValueError("Unsupported runbook step status")
        if self.status == "passed" and not (self.evidence_reference or "").strip():
            raise ValueError("Passed runbook steps require evidence_reference")
        return self


class LaunchCommandEventResponse(BaseModel):
    id: UUID
    session_id: UUID
    event_type: str
    severity: str
    title: str
    details_json: dict[str, Any]
    actor_admin_id: UUID | None
    created_at: datetime
    model_config = {"from_attributes": True}


class TrafficOverrideCreate(BaseModel):
    override_type: str
    value: int | bool
    duration_minutes: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=3000)


class TrafficOverrideResponse(BaseModel):
    id: UUID
    session_id: UUID
    zone_id: UUID
    override_type: str
    previous_value_json: dict
    override_value_json: dict
    reason: str
    status: str
    expires_at: datetime
    activated_by_admin_id: UUID
    reverted_by_admin_id: UUID | None
    activated_at: datetime
    reverted_at: datetime | None
    model_config = {"from_attributes": True}


class FinancialClosePrepareRequest(BaseModel):
    close_date: date
    note: str | None = Field(default=None, max_length=3000)


class FinancialCloseActionRequest(BaseModel):
    note: str = Field(min_length=3, max_length=3000)


class DailyFinancialCloseResponse(BaseModel):
    id: UUID
    session_id: UUID
    pilot_program_id: UUID
    close_date: date
    status: str
    delivered_orders: int
    succeeded_payment_orders: int
    captured_minor: int
    refunded_minor: int
    net_collected_minor: int
    verified_cost_minor: int
    contribution_minor: int
    operational_profit_minor: int
    revenue_coverage_pct: float
    cost_coverage_pct: float
    unverified_cost_entries: int
    pending_provider_imports: int
    unclosed_settlements: int
    open_payment_issues: int
    blockers_json: list[str]
    summary_json: dict
    checksum_sha256: str | None
    prepared_by_admin_id: UUID | None
    prepared_by_system: bool
    cadence_due_at: datetime | None
    overdue_notified_at: datetime | None
    closed_by_admin_id: UUID | None
    reopened_by_admin_id: UUID | None
    note: str | None
    prepared_at: datetime
    closed_at: datetime | None
    reopened_at: datetime | None
    updated_at: datetime
    model_config = {"from_attributes": True}


class RollbackDrillCreate(BaseModel):
    mode: str
    target_recovery_seconds: int | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=3000)

    @model_validator(mode="after")
    def validate_mode(self):
        if self.mode not in {"tabletop", "live_controlled"}:
            raise ValueError("Unsupported rollback drill mode")
        return self


class RollbackDrillComplete(BaseModel):
    passed: bool
    evidence_reference: str = Field(min_length=3, max_length=500)
    note: str | None = Field(default=None, max_length=3000)


class RollbackDrillResponse(BaseModel):
    id: UUID
    session_id: UUID
    zone_id: UUID
    mode: str
    status: str
    target_recovery_seconds: int
    recovery_seconds: int | None
    pre_state_json: dict
    result_json: dict
    evidence_reference: str | None
    note: str | None
    initiated_by_admin_id: UUID
    verified_by_admin_id: UUID | None
    started_at: datetime
    completed_at: datetime | None
    model_config = {"from_attributes": True}


class EvidencePackResponse(BaseModel):
    id: UUID
    session_id: UUID
    status: str
    release_version: str
    migration_head: str
    evidence_json: dict
    blockers_json: list[str]
    checksum_sha256: str
    retention_class: str
    retain_until: datetime | None
    generated_by_admin_id: UUID
    generated_at: datetime
    model_config = {"from_attributes": True}


class LaunchCommandOverview(BaseModel):
    session: LaunchSessionResponse
    zone_status: str
    rollout_stage: str
    rollout_percent: int
    runbook_total: int
    runbook_passed: int
    runbook_blocking: int
    active_overrides: int
    latest_financial_close: DailyFinancialCloseResponse | None
    latest_rollback_drill: RollbackDrillResponse | None
    latest_evidence_pack: EvidencePackResponse | None
