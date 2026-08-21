from __future__ import annotations
from datetime import date
from pydantic import BaseModel

class DailyMetric(BaseModel):
    day: date
    orders_created: int
    delivered_orders: int
    cancelled_orders: int
    gmv_minor: int
    captured_minor: int
    refunds_minor: int

class FunnelResponse(BaseModel):
    orders_created: int
    reached_confirmed: int
    reached_accepted_by_chef: int
    reached_ready_for_pickup: int
    reached_assigned_to_driver: int
    reached_picked_up: int
    reached_out_for_delivery: int
    reached_delivered: int

class RetentionAnalytics(BaseModel):
    delivered_orders: int
    unique_customers: int
    repeat_customers: int
    repeat_customer_rate_pct: float
    average_delivered_orders_per_customer: float
