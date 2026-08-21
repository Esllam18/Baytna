from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(StrEnum):
    CUSTOMER = "customer"
    CHEF = "chef"
    DRIVER = "driver"
    ADMIN = "admin"


class PublicUser(BaseModel):
    id: UUID
    phone: str
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ChefSummary(BaseModel):
    id: UUID
    display_name: str
    specialty: str
    area: str
    rating: float = Field(ge=0, le=5)
    is_verified: bool
    is_open_today: bool

    model_config = {"from_attributes": True}
