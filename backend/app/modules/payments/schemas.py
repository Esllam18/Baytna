from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreatePaymentIntentRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)


class PaymentResponse(BaseModel):
    id: UUID
    order_id: UUID
    provider: str
    provider_reference: str | None
    provider_order_reference: str | None
    provider_transaction_reference: str | None
    provider_status: str | None
    provider_last_seen_at: datetime | None
    amount_minor: int
    refunded_minor: int
    currency: str
    status: str
    checkout_url: str | None
    expires_at: datetime
    succeeded_at: datetime | None
    failed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentWebhookRequest(BaseModel):
    event_id: str = Field(min_length=4, max_length=180)
    event_type: str = Field(min_length=4, max_length=80)
    payment_reference: str = Field(min_length=4, max_length=160)
    amount_minor: int | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class RefundCreateRequest(BaseModel):
    amount_minor: int = Field(gt=0, le=100_000_000)
    reason: str = Field(min_length=3, max_length=240)
    idempotency_key: str = Field(min_length=8, max_length=120)


class RefundResponse(BaseModel):
    id: UUID
    order_id: UUID
    payment_id: UUID
    amount_minor: int
    reason: str
    status: str
    provider_reference: str | None
    provider_status: str | None
    provider_error: str | None
    created_at: datetime
    completed_at: datetime | None
    failed_at: datetime | None

    model_config = {"from_attributes": True}


class PaymentProviderTransactionResponse(BaseModel):
    id: UUID
    provider: str
    provider_transaction_id: str
    payment_id: UUID | None
    provider_order_reference: str | None
    parent_provider_transaction_id: str | None
    transaction_type: str
    amount_minor: int
    currency: str
    success: bool
    pending: bool
    is_refunded: bool
    refunded_minor: int
    observed_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentReconciliationIssueResponse(BaseModel):
    id: UUID
    fingerprint: str
    payment_id: UUID | None
    provider_transaction_id: str | None
    issue_type: str
    status: str
    expected_json: dict
    actual_json: dict
    detected_at: datetime
    last_detected_at: datetime
    resolved_at: datetime | None
    resolved_by_user_id: UUID | None
    resolution_note: str | None

    model_config = {"from_attributes": True}


class ReconciliationResolveRequest(BaseModel):
    note: str = Field(min_length=3, max_length=1000)


class ReconciliationRunResponse(BaseModel):
    scanned_payments: int
    scanned_transactions: int
    open_issues: int
    new_or_refreshed_issues: int
