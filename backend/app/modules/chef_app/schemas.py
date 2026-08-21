from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class ChefSelfProfileResponse(BaseModel):
    id: UUID
    display_name: str
    specialty: str
    area: str
    status: str
    rating: float
    is_verified: bool
    is_open_today: bool


class ChefAppDashboardResponse(BaseModel):
    chef: ChefSelfProfileResponse
    service_date: date
    kitchen_status: str
    signature_dishes: int
    today_items: int
    sold_out_items: int
    available_quantity: int
    orders_new: int
    orders_accepted: int
    orders_preparing: int
    orders_packaging: int
    orders_ready: int
    special_review: int
    special_counter_offer: int
    special_awaiting_payment: int
    special_scheduled: int
