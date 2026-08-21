from __future__ import annotations
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, Field


class AdminDashboardOverview(BaseModel):
    date_from: date
    date_to: date
    orders_total: int
    active_orders: int
    delivered_orders: int
    cancelled_orders: int
    gmv_minor: int
    captured_payments_minor: int
    refunds_minor: int
    net_collected_minor: int
    average_order_value_minor: int
    open_support_tickets: int
    active_chefs: int
    verified_chefs: int
    available_drivers: int
    on_mission_drivers: int
    delivery_success_rate_pct: float


class AdminOrderListItem(BaseModel):
    id: UUID
    customer_id: UUID
    customer_name: str | None
    customer_phone_masked: str
    chef_id: UUID
    chef_name: str
    service_date: date
    status: str
    subtotal_minor: int
    discount_minor: int
    total_minor: int
    currency: str
    payment_status: str | None
    delivery_status: str | None
    promised_delivery_window_start_at: datetime | None = None
    promised_delivery_window_end_at: datetime | None = None
    promised_delivery_timezone: str | None = None
    created_at: datetime


class AdminOrderNoteCreate(BaseModel):
    note: str = Field(min_length=2, max_length=4000)


class AdminOrderNoteResponse(BaseModel):
    id: UUID
    order_id: UUID
    admin_user_id: UUID | None
    note: str
    created_at: datetime
    model_config = {"from_attributes": True}


class AdminOrderDetail(BaseModel):
    order: AdminOrderListItem
    items: list[dict]
    pricing_adjustments: list[dict]
    payment: dict | None
    refunds: list[dict]
    delivery: dict | None
    delivery_address: dict | None
    timeline: list[dict]
    support_tickets: list[dict]
    notes: list[AdminOrderNoteResponse]


class ChefStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(active|paused|suspended|rejected)$")
    reason: str | None = Field(default=None, max_length=500)


class AdminChefListItem(BaseModel):
    id: UUID
    display_name: str
    specialty: str
    area: str
    status: str
    rating: float
    is_verified: bool
    is_open_today: bool
    total_orders: int
    delivered_orders: int
    created_at: datetime


class AdminChefDetail(AdminChefListItem):
    active_orders: int
    dishes_count: int
    reviews_count: int
    avg_food_quality: float
    open_support_tickets: int


class AdminDriverListItem(BaseModel):
    id: UUID
    status: str
    rating: float
    active_mission_id: UUID | None
    delivered_missions: int
    issue_missions: int
    created_at: datetime


class AdminDriverDetail(AdminDriverListItem):
    total_missions: int
    current_mission: dict | None


class SupportWorkloadSummary(BaseModel):
    total_open: int
    new: int
    assigned: int
    investigating: int
    awaiting_customer: int
    awaiting_internal: int
    urgent_open: int
    unassigned_open: int


class FinanceSummary(BaseModel):
    date_from: date
    date_to: date
    successful_payments_count: int
    captured_minor: int
    refunds_count: int
    refunded_minor: int
    net_collected_minor: int
    pending_payments_count: int
    failed_payments_count: int
    coupon_discount_minor: int
    loyalty_discount_minor: int
    subscription_discount_minor: int


class AuditItem(BaseModel):
    id: int
    actor_user_id: UUID | None
    action: str
    entity_type: str | None
    entity_id: str | None
    request_id: str | None
    metadata_json: dict
    created_at: datetime


class OperationsReport(BaseModel):
    generated_at: datetime
    overview: AdminDashboardOverview
    finance: FinanceSummary
    support: SupportWorkloadSummary
    top_chefs: list[AdminChefListItem]



class AdminSelfProfile(BaseModel):
    id: UUID
    phone: str
    role: str
    is_active: bool
