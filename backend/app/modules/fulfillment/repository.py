from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.db_models import (
    ChefOrderFulfillmentEntity,
    OrderEntity,
    OrderItemEntity,
)


class FulfillmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def order(self, order_id: UUID) -> OrderEntity | None:
        return self.db.get(OrderEntity, order_id)

    def order_for_chef(
        self,
        *,
        order_id: UUID,
        chef_id: UUID,
    ) -> OrderEntity | None:
        return self.db.scalar(
            select(OrderEntity).where(
                OrderEntity.id == order_id,
                OrderEntity.chef_id == chef_id,
            )
        )

    def items(self, order_id: UUID) -> list[OrderItemEntity]:
        return list(
            self.db.scalars(
                select(OrderItemEntity)
                .where(OrderItemEntity.order_id == order_id)
                .order_by(OrderItemEntity.id.asc())
            ).all()
        )

    def fulfillment(
        self,
        order_id: UUID,
    ) -> ChefOrderFulfillmentEntity | None:
        return self.db.get(ChefOrderFulfillmentEntity, order_id)

    def create_fulfillment(
        self,
        *,
        order_id: UUID,
        chef_id: UUID,
        acceptance_deadline_at: datetime | None,
    ) -> ChefOrderFulfillmentEntity:
        row = ChefOrderFulfillmentEntity(
            order_id=order_id,
            chef_id=chef_id,
            stage="new",
            acceptance_deadline_at=acceptance_deadline_at,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def queue(
        self,
        *,
        chef_id: UUID,
        stage: str | None = None,
    ) -> list[tuple[OrderEntity, ChefOrderFulfillmentEntity]]:
        stmt = (
            select(OrderEntity, ChefOrderFulfillmentEntity)
            .join(
                ChefOrderFulfillmentEntity,
                ChefOrderFulfillmentEntity.order_id == OrderEntity.id,
            )
            .where(OrderEntity.chef_id == chef_id)
        )

        if stage:
            stmt = stmt.where(ChefOrderFulfillmentEntity.stage == stage)

        stmt = stmt.order_by(
            ChefOrderFulfillmentEntity.acceptance_deadline_at.asc(),
            OrderEntity.created_at.asc(),
        )
        return list(self.db.execute(stmt).all())

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
