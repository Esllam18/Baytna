from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SecurityEventResponse(BaseModel):
    id: UUID
    event_type: str
    severity: str
    request_id: str | None
    actor_user_id: UUID | None
    ip_hash: str | None
    path: str | None
    metadata_json: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class RateLimitBucketResponse(BaseModel):
    id: UUID
    scope: str
    key_hash: str
    window_start: datetime
    window_seconds: int
    request_count: int
    expires_at: datetime

    model_config = {"from_attributes": True}
