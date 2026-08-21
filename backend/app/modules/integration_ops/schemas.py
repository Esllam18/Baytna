from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.notification_delivery.schemas import NotificationDeliveryResponse


class IntegrationTestNotificationRequest(BaseModel):
    user_id: UUID
    channels: list[str] = Field(min_length=1, max_length=2)
    title: str = Field(default="Baytna integration test", min_length=2, max_length=180)
    body: str = Field(
        default="رسالة اختبار من بيئة بيتنا.",
        min_length=2,
        max_length=500,
    )
    dispatch_now: bool = False


class IntegrationTestNotificationResponse(BaseModel):
    notification_id: UUID
    delivery_ids: list[UUID]
    deliveries: list[NotificationDeliveryResponse] = []
