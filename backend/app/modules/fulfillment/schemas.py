from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChefOrderItemResponse(BaseModel):
    dish_id: UUID
    dish_name: str
    quantity: int
    unit_price_minor: int
    line_total_minor: int


class ChefOrderListItemResponse(BaseModel):
    order_id: UUID
    customer_id: UUID
    service_date: date
    order_status: str
    fulfillment_stage: str
    total_minor: int
    currency: str
    acceptance_deadline_at: datetime | None
    estimated_ready_at: datetime | None
    created_at: datetime


class ChefOrderDetailResponse(BaseModel):
    order_id: UUID
    customer_id: UUID
    chef_id: UUID
    service_date: date
    order_status: str
    fulfillment_stage: str
    subtotal_minor: int
    total_minor: int
    currency: str
    acceptance_deadline_at: datetime | None
    estimated_ready_at: datetime | None
    accepted_at: datetime | None
    preparation_started_at: datetime | None
    packaging_started_at: datetime | None
    ready_at: datetime | None
    rejected_at: datetime | None
    rejection_reason: str | None
    chef_note: str | None
    items: list[ChefOrderItemResponse]
    created_at: datetime


class AcceptOrderRequest(BaseModel):
    estimated_ready_at: datetime | None = None
    chef_note: str | None = Field(default=None, max_length=1000)


class ChefNoteRequest(BaseModel):
    chef_note: str | None = Field(default=None, max_length=1000)


class RejectOrderRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=240)


class CustomerTrackingResponse(BaseModel):
    order_id: UUID
    status: str
    fulfillment_stage: str | None
    display_status: str
    detail: str | None
    estimated_ready_at: datetime | None
    updated_at: datetime
