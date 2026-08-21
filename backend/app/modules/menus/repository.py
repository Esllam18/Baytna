from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.db_models import (
    ChefProfileEntity,
    ChefWorkdayEntity,
    DailyMenuItemEntity,
    DishEntity,
)


class MenuRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def chef(self, chef_id: UUID) -> ChefProfileEntity | None:
        return self.db.get(ChefProfileEntity, chef_id)

    def create_dish(self, *, chef_id: UUID, values: dict) -> DishEntity:
        dish = DishEntity(chef_id=chef_id, **values)
        self.db.add(dish)
        self.db.flush()
        return dish

    def dish(self, dish_id: UUID) -> DishEntity | None:
        return self.db.get(DishEntity, dish_id)

    def list_signature(
        self,
        chef_id: UUID,
        *,
        include_inactive: bool = False,
    ) -> list[DishEntity]:
        stmt = select(DishEntity).where(DishEntity.chef_id == chef_id)
        if not include_inactive:
            stmt = stmt.where(DishEntity.is_active.is_(True))
        stmt = stmt.order_by(DishEntity.display_order.asc(), DishEntity.name.asc())
        return list(self.db.scalars(stmt).all())

    def workday(
        self,
        chef_id: UUID,
        service_date: date,
    ) -> ChefWorkdayEntity | None:
        return self.db.scalar(
            select(ChefWorkdayEntity).where(
                ChefWorkdayEntity.chef_id == chef_id,
                ChefWorkdayEntity.service_date == service_date,
            )
        )

    def create_workday(self, *, chef_id: UUID, values: dict) -> ChefWorkdayEntity:
        row = ChefWorkdayEntity(chef_id=chef_id, **values)
        self.db.add(row)
        self.db.flush()
        return row

    def daily_item(self, item_id: UUID) -> DailyMenuItemEntity | None:
        return self.db.get(DailyMenuItemEntity, item_id)

    def list_daily_items(
        self,
        workday_id: UUID,
        *,
        include_hidden: bool = False,
    ) -> list[DailyMenuItemEntity]:
        stmt = select(DailyMenuItemEntity).where(
            DailyMenuItemEntity.workday_id == workday_id
        )
        if not include_hidden:
            stmt = stmt.where(DailyMenuItemEntity.status != "hidden")
        stmt = stmt.order_by(DailyMenuItemEntity.created_at.asc())
        return list(self.db.scalars(stmt).all())

    def remove_daily_items(self, workday_id: UUID) -> None:
        self.db.execute(
            delete(DailyMenuItemEntity).where(
                DailyMenuItemEntity.workday_id == workday_id
            )
        )
        self.db.flush()

    def create_daily_item(
        self,
        *,
        workday_id: UUID,
        dish_id: UUID,
        price_minor: int,
        quantity_total: int,
        max_per_order: int,
        status: str,
    ) -> DailyMenuItemEntity:
        row = DailyMenuItemEntity(
            workday_id=workday_id,
            dish_id=dish_id,
            price_minor=price_minor,
            quantity_total=quantity_total,
            quantity_available=quantity_total,
            max_per_order=max_per_order,
            status=status,
        )
        self.db.add(row)
        self.db.flush()
        return row
