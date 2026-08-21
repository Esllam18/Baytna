from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import UserEntity
from app.core.errors import ApiError
from app.modules.delivery.service import DeliveryService
from app.modules.driver_app.schemas import (
    DriverAppDashboardResponse,
    DriverSelfProfileResponse,
)


class DriverAppService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.delivery = DeliveryService(db, settings)

    def profile(self, *, driver_id: UUID) -> DriverSelfProfileResponse:
        user = self.db.get(UserEntity, driver_id)
        if user is None:
            raise ApiError(404, "driver_user_not_found", "حساب المندوب غير موجود.")

        status = self.delivery.status(driver_id=driver_id)
        return DriverSelfProfileResponse(
            id=driver_id,
            phone=user.phone,
            status=status.status,
            rating=status.rating,
        )

    def dashboard(self, *, driver_id: UUID) -> DriverAppDashboardResponse:
        driver = self.profile(driver_id=driver_id)

        self.delivery.sync_ready_orders()

        active_row = self.delivery.repo.active_task_for_driver(driver_id)
        active = (
            self.delivery._mission_response(active_row)
            if active_row is not None
            else None
        )

        if active is None and driver.status == "available":
            available_count = len(self.delivery.repo.available_tasks())
        else:
            available_count = 0

        completed_count = len(
            self.delivery.repo.history_for_driver(driver_id)
        )

        return DriverAppDashboardResponse(
            driver=driver,
            active_mission=active,
            available_missions_count=available_count,
            completed_missions_count=completed_count,
        )
