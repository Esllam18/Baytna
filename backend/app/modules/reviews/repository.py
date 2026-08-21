from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db_models import (
    DeliveryTaskEntity,
    DriverProfileEntity,
    OrderEntity,
    ReviewEntity,
)


class ReviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def order(self, order_id: UUID) -> OrderEntity | None:
        return self.db.get(OrderEntity, order_id)

    def review_for_order(self, order_id: UUID) -> ReviewEntity | None:
        return self.db.scalar(
            select(ReviewEntity).where(ReviewEntity.order_id == order_id)
        )

    def review(self, review_id: UUID) -> ReviewEntity | None:
        return self.db.get(ReviewEntity, review_id)

    def delivery_driver_for_order(self, order_id: UUID) -> UUID | None:
        task = self.db.scalar(
            select(DeliveryTaskEntity).where(
                DeliveryTaskEntity.order_id == order_id,
                DeliveryTaskEntity.status == "delivered",
            )
        )
        return task.driver_id if task else None

    def visible_for_chef(self, chef_id: UUID) -> list[ReviewEntity]:
        return list(
            self.db.scalars(
                select(ReviewEntity)
                .where(
                    ReviewEntity.chef_id == chef_id,
                    ReviewEntity.is_visible.is_(True),
                )
                .order_by(ReviewEntity.created_at.desc())
            ).all()
        )

    def customer_reviews(self, customer_id: UUID) -> list[ReviewEntity]:
        return list(
            self.db.scalars(
                select(ReviewEntity)
                .where(ReviewEntity.customer_id == customer_id)
                .order_by(ReviewEntity.created_at.desc())
            ).all()
        )

    def recalc_chef_rating(self, chef_id: UUID):
        rows = list(
            self.db.scalars(
                select(ReviewEntity).where(
                    ReviewEntity.chef_id == chef_id,
                    ReviewEntity.is_visible.is_(True),
                )
            ).all()
        )
        if not rows:
            return {
                "count": 0,
                "overall": 0.0,
                "food_quality": 0.0,
                "packaging": 0.0,
                "order_accuracy": 0.0,
                "value_for_money": 0.0,
            }

        count = len(rows)
        return {
            "count": count,
            "overall": sum(x.chef_overall for x in rows) / count,
            "food_quality": sum(x.food_quality for x in rows) / count,
            "packaging": sum(x.packaging for x in rows) / count,
            "order_accuracy": sum(x.order_accuracy for x in rows) / count,
            "value_for_money": sum(x.value_for_money for x in rows) / count,
        }

    def recalc_driver_rating(self, driver_id: UUID):
        rows = list(
            self.db.scalars(
                select(ReviewEntity).where(
                    ReviewEntity.driver_id == driver_id,
                    ReviewEntity.delivery_overall.is_not(None),
                    ReviewEntity.is_visible.is_(True),
                )
            ).all()
        )
        if not rows:
            return {"count": 0, "overall": 0.0}
        return {
            "count": len(rows),
            "overall": sum(x.delivery_overall for x in rows) / len(rows),
        }
