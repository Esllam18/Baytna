from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class DriverAvailabilityRequest(BaseModel):
    available: bool


class DriverStatusResponse(BaseModel):
    driver_id: UUID
    status: str
    rating: float
    active_mission_id: UUID | None


class DeliveryAddressResponse(BaseModel):
    label: str | None
    area: str
    street: str | None
    building: str | None
    floor: str | None
    apartment: str | None
    latitude: str | None
    longitude: str | None


class DeliveryMissionResponse(BaseModel):
    id: UUID
    order_id: UUID
    chef_id: UUID
    driver_id: UUID | None
    status: str
    order_status: str
    service_date: date
    total_minor: int
    currency: str
    pickup_name: str
    pickup_area: str
    dropoff: DeliveryAddressResponse | None
    navigation_ready: bool
    accepted_at: datetime | None
    arrived_pickup_at: datetime | None
    picked_up_at: datetime | None
    route_started_at: datetime | None
    delivered_at: datetime | None
    promised_delivery_window_start_at: datetime | None = None
    promised_delivery_window_end_at: datetime | None = None
    promised_delivery_timezone: str | None = None
    delivery_timing_status: str | None = None
    late_by_minutes: int | None = None
    delivery_proof_type: str | None
    delivery_proof_media_asset_id: UUID | None = None
    issue_code: str | None
    issue_note: str | None
    created_at: datetime


class DeliveryProofRequest(BaseModel):
    proof_type: str = Field(pattern=r"^(otp|photo|signature|manual)$")
    proof_reference: str | None = Field(default=None, min_length=3, max_length=500)
    media_asset_id: UUID | None = None

    @model_validator(mode="after")
    def validate_proof(self):
        if not self.proof_reference and self.media_asset_id is None:
            raise ValueError("يجب إرسال proof_reference أو media_asset_id")
        return self


class DeliveryIssueRequest(BaseModel):
    issue_code: str = Field(min_length=2, max_length=80)
    note: str = Field(min_length=3, max_length=1000)


class DeliveryTrackingResponse(BaseModel):
    order_id: UUID
    order_status: str
    mission_status: str | None
    display_status: str
    detail: str | None
    delivered_at: datetime | None
    promised_delivery_window_start_at: datetime | None = None
    promised_delivery_window_end_at: datetime | None = None
    promised_delivery_timezone: str | None = None
    delivery_timing_status: str | None = None
    late_by_minutes: int | None = None
