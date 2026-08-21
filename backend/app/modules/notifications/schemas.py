from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: UUID
    kind: str
    title: str
    body: str
    action_url: str | None
    data_json: dict
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationSummaryResponse(BaseModel):
    unread_count: int
    latest: list[NotificationResponse]
