from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.db_models import (
    ChefProfileEntity,
    DeliveryTaskEntity,
    DriverProfileEntity,
    OrderDeliveryAddressEntity,
    OrderEntity,
)


ACTIVE_MISSION_STATUSES = {
    "to_pickup",
    "at_pickup",
    "picked_up",
    "to_customer",
    "delivery_issue",
}


class DeliveryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def driver_profile(self, driver_id: UUID) -> DriverProfileEntity | None:
        return self.db.get(DriverProfileEntity, driver_id)

    def order(self, order_id: UUID) -> OrderEntity | None:
        return self.db.get(OrderEntity, order_id)

    def task(self, task_id: UUID) -> DeliveryTaskEntity | None:
        return self.db.get(DeliveryTaskEntity, task_id)

    def task_for_order(self, order_id: UUID) -> DeliveryTaskEntity | None:
        return self.db.scalar(
            select(DeliveryTaskEntity).where(
                DeliveryTaskEntity.order_id == order_id
            )
        )

    def delivery_address(
        self,
        order_id: UUID,
    ) -> OrderDeliveryAddressEntity | None:
        return self.db.get(OrderDeliveryAddressEntity, order_id)

    def chef(self, chef_id: UUID) -> ChefProfileEntity | None:
        return self.db.get(ChefProfileEntity, chef_id)

    def available_tasks(self) -> list[DeliveryTaskEntity]:
        return list(
            self.db.scalars(
                select(DeliveryTaskEntity)
                .where(
                    DeliveryTaskEntity.status == "unassigned",
                    DeliveryTaskEntity.driver_id.is_(None),
                )
                .order_by(DeliveryTaskEntity.created_at.asc())
            ).all()
        )

    def active_task_for_driver(
        self,
        driver_id: UUID,
    ) -> DeliveryTaskEntity | None:
        return self.db.scalar(
            select(DeliveryTaskEntity)
            .where(
                DeliveryTaskEntity.driver_id == driver_id,
                DeliveryTaskEntity.status.in_(ACTIVE_MISSION_STATUSES),
            )
            .order_by(DeliveryTaskEntity.updated_at.desc())
            .limit(1)
        )

    def history_for_driver(
        self,
        driver_id: UUID,
    ) -> list[DeliveryTaskEntity]:
        return list(
            self.db.scalars(
                select(DeliveryTaskEntity)
                .where(
                    DeliveryTaskEntity.driver_id == driver_id,
                    DeliveryTaskEntity.status.in_(["delivered", "cancelled"]),
                )
                .order_by(DeliveryTaskEntity.updated_at.desc())
            ).all()
        )

    def claim_task(
        self,
        *,
        task_id: UUID,
        driver_id: UUID,
    ) -> bool:
        result = self.db.execute(
            update(DeliveryTaskEntity)
            .where(
                DeliveryTaskEntity.id == task_id,
                DeliveryTaskEntity.status == "unassigned",
                DeliveryTaskEntity.driver_id.is_(None),
            )
            .values(
                driver_id=driver_id,
                status="to_pickup",
            )
        )
        self.db.flush()
        return result.rowcount == 1

    def transition_task(
        self,
        *,
        task_id: UUID,
        driver_id: UUID,
        expected_status: str,
        new_status: str,
    ) -> bool:
        result = self.db.execute(
            update(DeliveryTaskEntity)
            .where(
                DeliveryTaskEntity.id == task_id,
                DeliveryTaskEntity.driver_id == driver_id,
                DeliveryTaskEntity.status == expected_status,
            )
            .values(status=new_status)
        )
        self.db.flush()
        return result.rowcount == 1

    def transition_order(
        self,
        *,
        order_id: UUID,
        expected_status: str,
        new_status: str,
    ) -> bool:
        result = self.db.execute(
            update(OrderEntity)
            .where(
                OrderEntity.id == order_id,
                OrderEntity.status == expected_status,
            )
            .values(status=new_status)
        )
        self.db.flush()
        return result.rowcount == 1
