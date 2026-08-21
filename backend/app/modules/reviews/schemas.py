from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    food_quality: int = Field(ge=1, le=5)
    packaging: int = Field(ge=1, le=5)
    order_accuracy: int = Field(ge=1, le=5)
    value_for_money: int = Field(ge=1, le=5)
    chef_overall: int = Field(ge=1, le=5)
    delivery_overall: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1500)


class ReviewUpdateRequest(BaseModel):
    food_quality: int | None = Field(default=None, ge=1, le=5)
    packaging: int | None = Field(default=None, ge=1, le=5)
    order_accuracy: int | None = Field(default=None, ge=1, le=5)
    value_for_money: int | None = Field(default=None, ge=1, le=5)
    chef_overall: int | None = Field(default=None, ge=1, le=5)
    delivery_overall: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1500)


class ReviewResponse(BaseModel):
    id: UUID
    order_id: UUID
    customer_id: UUID
    chef_id: UUID
    driver_id: UUID | None
    food_quality: int
    packaging: int
    order_accuracy: int
    value_for_money: int
    chef_overall: int
    delivery_overall: int | None
    comment: str | None
    is_visible: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChefRatingSummaryResponse(BaseModel):
    chef_id: UUID
    rating: float
    review_count: int
    food_quality: float
    packaging: float
    order_accuracy: float
    value_for_money: float


class DriverRatingSummaryResponse(BaseModel):
    driver_id: UUID
    rating: float
    review_count: int


class ModerationRequest(BaseModel):
    is_visible: bool
    moderation_note: str | None = Field(default=None, max_length=500)



class PublicReviewResponse(BaseModel):
    id: UUID
    food_quality: int
    packaging: int
    order_accuracy: int
    value_for_money: int
    chef_overall: int
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewEligibilityResponse(BaseModel):
    order_id: UUID
    order_status: str
    can_review: bool
    reason: str
    review: ReviewResponse | None = None
