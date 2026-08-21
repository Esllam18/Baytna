from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class PricingQuoteRequest(BaseModel):
    cart_id: UUID
    coupon_code: str | None = Field(default=None, max_length=40)
    loyalty_points_to_redeem: int = Field(default=0, ge=0, le=1_000_000)

    @field_validator("coupon_code")
    @classmethod
    def normalize_coupon(cls, value: str | None):
        return value.strip().upper() if value and value.strip() else None


class PricingAdjustmentResponse(BaseModel):
    adjustment_type: str
    reference_code: str | None
    amount_minor: int
    metadata_json: dict = Field(default_factory=dict)


class PricingQuoteResponse(BaseModel):
    cart_id: UUID
    subtotal_minor: int
    delivery_fee_minor: int
    coupon_discount_minor: int
    subscription_discount_minor: int
    loyalty_discount_minor: int
    total_discount_minor: int
    total_minor: int
    currency: str = "EGP"
    coupon_code: str | None
    loyalty_points_to_redeem: int
    loyalty_balance_points: int
    subscription_plan_id: UUID | None
    subscription_plan_name: str | None
    minimum_payable_minor: int


class CouponCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    discount_type: str = Field(pattern=r"^(fixed|percent)$")
    discount_value: int = Field(gt=0)
    min_subtotal_minor: int = Field(default=0, ge=0)
    max_discount_minor: int | None = Field(default=None, gt=0)
    total_usage_limit: int | None = Field(default=None, gt=0)
    per_customer_usage_limit: int = Field(default=1, gt=0)
    stack_with_subscription: bool = True
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str):
        return value.strip().upper()


class CouponUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    min_subtotal_minor: int | None = Field(default=None, ge=0)
    max_discount_minor: int | None = Field(default=None, gt=0)
    total_usage_limit: int | None = Field(default=None, gt=0)
    per_customer_usage_limit: int | None = Field(default=None, gt=0)
    stack_with_subscription: bool | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool | None = None


class CouponResponse(BaseModel):
    id: UUID
    code: str
    name: str
    discount_type: str
    discount_value: int
    min_subtotal_minor: int
    max_discount_minor: int | None
    total_usage_limit: int | None
    per_customer_usage_limit: int
    reserved_count: int
    redeemed_count: int
    stack_with_subscription: bool
    starts_at: datetime | None
    ends_at: datetime | None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class SubscriptionPlanCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price_minor: int = Field(default=0, ge=0)
    duration_days: int = Field(default=30, gt=0, le=3650)
    order_discount_bps: int = Field(default=0, ge=0, le=10000)
    max_order_discount_minor: int | None = Field(default=None, gt=0)
    loyalty_multiplier_bps: int = Field(default=10000, ge=10000, le=50000)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str):
        return value.strip().upper()


class SubscriptionPlanResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    price_minor: int
    duration_days: int
    order_discount_bps: int
    max_order_discount_minor: int | None
    loyalty_multiplier_bps: int
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class GrantSubscriptionRequest(BaseModel):
    customer_id: UUID
    source: str = Field(default="manual", pattern=r"^(manual|promo|billing)$")


class CustomerSubscriptionResponse(BaseModel):
    id: UUID
    customer_id: UUID
    plan_id: UUID
    plan_code: str
    plan_name: str
    status: str
    source: str
    starts_at: datetime
    ends_at: datetime
    cancelled_at: datetime | None
