from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerProfileResponse(BaseModel):
    id: UUID
    phone: str
    display_name: str | None
    preferred_language: str
    role: str
    is_active: bool
    created_at: datetime


class CustomerProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    preferred_language: str = Field(default="ar", pattern=r"^(ar|en)$")
