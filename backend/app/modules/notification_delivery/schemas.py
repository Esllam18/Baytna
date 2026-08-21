from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PushDeviceRegisterRequest(BaseModel):
    platform: str = Field(pattern=r"^(ios|android|web)$")
    token: str = Field(min_length=12, max_length=4096)
    device_name: str | None = Field(default=None, max_length=120)
    app_version: str | None = Field(default=None, max_length=40)


class PushDeviceResponse(BaseModel):
    id: UUID
    platform: str
    device_name: str | None
    app_version: str | None
    is_active: bool
    last_seen_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationPreferenceUpdateRequest(BaseModel):
    push_enabled: bool
    sms_enabled: bool
    order_updates: bool
    support_updates: bool
    marketing_enabled: bool


class NotificationPreferenceResponse(BaseModel):
    user_id: UUID
    push_enabled: bool
    sms_enabled: bool
    order_updates: bool
    support_updates: bool
    marketing_enabled: bool

    model_config = {"from_attributes": True}


class NotificationDeliveryResponse(BaseModel):
    id: UUID
    notification_id: UUID
    user_id: UUID
    channel: str
    target_ref: str
    provider: str
    status: str
    attempts: int
    max_attempts: int
    available_at: datetime
    provider_message_id: str | None
    provider_status: str | None
    provider_error_code: str | None
    provider_updated_at: datetime | None
    last_error: str | None
    delivered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
