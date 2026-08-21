from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AddCartItemRequest(BaseModel):
    daily_menu_item_id: UUID
    quantity: int = Field(gt=0, le=100)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(gt=0, le=100)


class CartLineResponse(BaseModel):
    id: UUID
    daily_menu_item_id: UUID | None
    dish_id: UUID
    dish_name: str
    chef_id: UUID
    unit_price_minor: int
    quantity: int
    line_total_minor: int
    max_per_order: int
    availability_label: str


class CartResponse(BaseModel):
    id: UUID
    customer_id: UUID
    chef_id: UUID | None
    service_date: date | None
    status: str
    subtotal_minor: int
    currency: str = "EGP"
    items: list[CartLineResponse]


class CreateOrderRequest(BaseModel):
    cart_id: UUID
    delivery_address_id: UUID | None = None
    coupon_code: str | None = Field(default=None, max_length=40)
    loyalty_points_to_redeem: int = Field(default=0, ge=0, le=1_000_000)


class OrderLineResponse(BaseModel):
    id: UUID
    daily_menu_item_id: UUID | None
    dish_id: UUID
    dish_name: str
    unit_price_minor: int
    quantity: int
    line_total_minor: int


class OrderStatusEventResponse(BaseModel):
    from_status: str | None
    to_status: str
    reason: str | None
    created_at: datetime


class OrderPricingAdjustmentResponse(BaseModel):
    adjustment_type: str
    reference_code: str | None
    amount_minor: int
    metadata_json: dict


class OrderResponse(BaseModel):
    id: UUID
    order_type: str
    customer_id: UUID
    chef_id: UUID
    service_date: date
    status: str
    subtotal_minor: int
    delivery_fee_minor: int
    discount_minor: int
    total_minor: int
    currency: str
    inventory_hold_expires_at: datetime | None
    promised_delivery_window_start_at: datetime | None = None
    promised_delivery_window_end_at: datetime | None = None
    promised_delivery_timezone: str | None = None
    delivery_promise_source: str | None = None
    items: list[OrderLineResponse]
    timeline: list[OrderStatusEventResponse]
    pricing_adjustments: list[OrderPricingAdjustmentResponse] = Field(default_factory=list)
    created_at: datetime


class OrderListItemResponse(BaseModel):
    id: UUID
    order_type: str
    chef_id: UUID
    service_date: date
    status: str
    total_minor: int
    currency: str
    promised_delivery_window_start_at: datetime | None = None
    promised_delivery_window_end_at: datetime | None = None
    promised_delivery_timezone: str | None = None
    created_at: datetime
