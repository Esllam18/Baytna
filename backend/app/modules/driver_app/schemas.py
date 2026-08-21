from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.modules.delivery.schemas import DeliveryMissionResponse


class DriverSelfProfileResponse(BaseModel):
    id: UUID
    phone: str
    status: str
    rating: float


class DriverAppDashboardResponse(BaseModel):
    driver: DriverSelfProfileResponse
    active_mission: DeliveryMissionResponse | None
    available_missions_count: int
    completed_missions_count: int
