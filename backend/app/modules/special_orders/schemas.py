from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.modules.orders.schemas import OrderResponse
from app.modules.payments.schemas import PaymentResponse


class WeeklyScheduleDayRequest(BaseModel):
    weekday: int = Field(ge=0, le=6)
    is_available: bool = True
    delivery_window_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    delivery_window_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    max_special_orders: int = Field(default=5, ge=0, le=100)

    @model_validator(mode="after")
    def validate_window(self):
        if bool(self.delivery_window_start) != bool(self.delivery_window_end):
            raise ValueError("يجب تحديد بداية ونهاية نافذة التوصيل معًا")
        if (
            self.delivery_window_start
            and self.delivery_window_end
            and self.delivery_window_start >= self.delivery_window_end
        ):
            raise ValueError("نهاية نافذة التوصيل يجب أن تكون بعد البداية")
        return self


class WeeklyScheduleUpsertRequest(BaseModel):
    days: list[WeeklyScheduleDayRequest] = Field(min_length=1, max_length=7)

    @model_validator(mode="after")
    def unique_days(self):
        values = [x.weekday for x in self.days]
        if len(values) != len(set(values)):
            raise ValueError("لا يمكن تكرار نفس يوم الأسبوع")
        return self


class WeeklyScheduleDayResponse(BaseModel):
    weekday: int
    is_available: bool
    delivery_window_start: str | None
    delivery_window_end: str | None
    max_special_orders: int


class ScheduleOverrideRequest(BaseModel):
    is_available: bool
    delivery_window_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    delivery_window_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    max_special_orders: int | None = Field(default=None, ge=0, le=100)
    reason: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def validate_window(self):
        if bool(self.delivery_window_start) != bool(self.delivery_window_end):
            raise ValueError("يجب تحديد بداية ونهاية نافذة التوصيل معًا")
        if (
            self.delivery_window_start
            and self.delivery_window_end
            and self.delivery_window_start >= self.delivery_window_end
        ):
            raise ValueError("نهاية نافذة التوصيل يجب أن تكون بعد البداية")
        return self


class ScheduleOverrideResponse(BaseModel):
    id: UUID
    service_date: date
    is_available: bool
    delivery_window_start: str | None
    delivery_window_end: str | None
    max_special_orders: int | None
    reason: str | None

    model_config = {"from_attributes": True}


class AvailabilityDayResponse(BaseModel):
    service_date: date
    weekday: int
    is_available: bool
    source: str
    delivery_window_start: str | None
    delivery_window_end: str | None
    capacity_total: int
    capacity_used: int
    capacity_remaining: int


class SpecialOrderCreateRequest(BaseModel):
    dish_id: UUID
    request_type: str = Field(default="special", pattern=r"^(special|preorder)$")
    quantity: int = Field(gt=0, le=100)
    requested_service_date: date
    requested_window_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    requested_window_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    customer_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_window(self):
        if bool(self.requested_window_start) != bool(self.requested_window_end):
            raise ValueError("يجب تحديد بداية ونهاية نافذة التوصيل معًا")
        if (
            self.requested_window_start
            and self.requested_window_end
            and self.requested_window_start >= self.requested_window_end
        ):
            raise ValueError("نهاية نافذة التوصيل يجب أن تكون بعد البداية")
        return self


class ChefAcceptSpecialOrderRequest(BaseModel):
    unit_price_minor: int | None = Field(default=None, gt=0, le=5_000_000)
    delivery_window_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    delivery_window_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    chef_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_window(self):
        if bool(self.delivery_window_start) != bool(self.delivery_window_end):
            raise ValueError("يجب تحديد بداية ونهاية نافذة التوصيل معًا")
        if (
            self.delivery_window_start
            and self.delivery_window_end
            and self.delivery_window_start >= self.delivery_window_end
        ):
            raise ValueError("نهاية نافذة التوصيل يجب أن تكون بعد البداية")
        return self


class ChefCounterOfferRequest(BaseModel):
    proposed_service_date: date
    proposed_unit_price_minor: int = Field(gt=0, le=5_000_000)
    proposed_window_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    proposed_window_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    chef_note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_window(self):
        if bool(self.proposed_window_start) != bool(self.proposed_window_end):
            raise ValueError("يجب تحديد بداية ونهاية نافذة التوصيل معًا")
        if (
            self.proposed_window_start
            and self.proposed_window_end
            and self.proposed_window_start >= self.proposed_window_end
        ):
            raise ValueError("نهاية نافذة التوصيل يجب أن تكون بعد البداية")
        return self


class ChefRejectSpecialOrderRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=240)


class SpecialOrderEventResponse(BaseModel):
    from_status: str | None
    to_status: str
    reason: str | None
    data_json: dict
    created_at: datetime


class SpecialOrderResponse(BaseModel):
    id: UUID
    customer_id: UUID
    chef_id: UUID
    dish_id: UUID
    dish_name: str
    order_id: UUID | None
    request_type: str
    status: str
    quantity: int
    requested_service_date: date
    requested_window_start: str | None
    requested_window_end: str | None
    requested_unit_price_minor: int
    proposed_service_date: date | None
    proposed_window_start: str | None
    proposed_window_end: str | None
    proposed_unit_price_minor: int | None
    final_service_date: date | None
    final_window_start: str | None
    final_window_end: str | None
    final_unit_price_minor: int | None
    final_total_minor: int | None
    customer_note: str | None
    chef_note: str | None
    rejection_reason: str | None
    offer_expires_at: datetime | None
    chef_responded_at: datetime | None
    customer_accepted_at: datetime | None
    scheduled_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    events: list[SpecialOrderEventResponse] = []


class SpecialOrderCheckoutRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=120)


class SpecialOrderCheckoutResponse(BaseModel):
    special_order: SpecialOrderResponse
    order: OrderResponse
    payment: PaymentResponse
