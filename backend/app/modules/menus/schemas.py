from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class DishCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="أطباق رئيسية", min_length=2, max_length=80)
    base_price_minor: int = Field(gt=0, le=2_000_000)
    prep_notice_hours: int = Field(default=24, ge=0, le=168)
    is_special_order_available: bool = True
    image_url: str | None = Field(default=None, max_length=500)
    display_order: int = Field(default=0, ge=0, le=10_000)


class DishUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=140)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    base_price_minor: int | None = Field(default=None, gt=0, le=2_000_000)
    prep_notice_hours: int | None = Field(default=None, ge=0, le=168)
    is_special_order_available: bool | None = None
    image_url: str | None = Field(default=None, max_length=500)
    display_order: int | None = Field(default=None, ge=0, le=10_000)
    is_active: bool | None = None

    @model_validator(mode="after")
    def ensure_has_change(self):
        if not self.model_fields_set:
            raise ValueError("يجب إرسال حقل واحد على الأقل للتعديل")
        return self


class DishMediaRequest(BaseModel):
    media_asset_id: UUID | None = None


class DishResponse(BaseModel):
    id: UUID
    chef_id: UUID
    name: str
    description: str
    category: str
    base_price_minor: int
    prep_notice_hours: int
    is_special_order_available: bool
    is_active: bool
    image_url: str | None
    media_asset_id: UUID | None
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OpenKitchenRequest(BaseModel):
    service_date: date
    cutoff_at: datetime | None = None
    delivery_window_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    delivery_window_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")

    @model_validator(mode="after")
    def validate_window(self):
        if bool(self.delivery_window_start) != bool(self.delivery_window_end):
            raise ValueError("يجب إرسال بداية ونهاية نافذة التوصيل معًا")
        if (
            self.delivery_window_start
            and self.delivery_window_end
            and self.delivery_window_start >= self.delivery_window_end
        ):
            raise ValueError("نهاية نافذة التوصيل يجب أن تكون بعد البداية")
        return self


class WorkdayResponse(BaseModel):
    id: UUID
    chef_id: UUID
    service_date: date
    status: str
    cutoff_at: datetime | None
    delivery_window_start: str | None
    delivery_window_end: str | None
    opened_at: datetime
    closed_at: datetime | None

    model_config = {"from_attributes": True}


class DailyMenuUpsertItem(BaseModel):
    dish_id: UUID
    price_minor: int | None = Field(default=None, gt=0, le=2_000_000)
    quantity_total: int = Field(ge=0, le=10_000)
    max_per_order: int = Field(default=10, gt=0, le=100)
    is_visible: bool = True


class DailyMenuReplaceRequest(BaseModel):
    service_date: date
    items: list[DailyMenuUpsertItem] = Field(min_length=1, max_length=25)

    @field_validator("items")
    @classmethod
    def unique_dishes(cls, items):
        ids = [x.dish_id for x in items]
        if len(ids) != len(set(ids)):
            raise ValueError("لا يمكن تكرار نفس الطبق في مطبخ اليوم")
        return items


class QuantityUpdateRequest(BaseModel):
    quantity_available: int = Field(ge=0, le=10_000)


class DailyMenuItemResponse(BaseModel):
    id: UUID
    dish_id: UUID
    name: str
    description: str
    category: str
    price_minor: int
    quantity_total: int
    quantity_available: int
    max_per_order: int
    status: str
    availability_label: str
    image_url: str | None


class TodayMenuResponse(BaseModel):
    chef_id: UUID
    service_date: date
    kitchen_status: str
    cutoff_at: datetime | None
    delivery_window_start: str | None
    delivery_window_end: str | None
    items: list[DailyMenuItemResponse]


class ChefDashboardResponse(BaseModel):
    chef_id: UUID
    service_date: date
    kitchen_status: str
    signature_dishes: int
    active_signature_dishes: int
    today_items: int
    sold_out_items: int
    total_quantity: int
    available_quantity: int
