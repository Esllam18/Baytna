from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db_models import (
    ChefProfileEntity,
    DishEntity,
    FavoriteChefEntity,
    FavoriteDishEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.modules.favorites.schemas import (
    FavoriteChefResponse,
    FavoriteDishResponse,
    FavoritesSummaryResponse,
)


class FavoriteService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditRepository(db)

    def add_chef(
        self,
        *,
        customer_id: UUID,
        chef_id: UUID,
        request_id: str | None,
    ) -> FavoriteChefResponse:
        chef = self.db.get(ChefProfileEntity, chef_id)
        if chef is None or chef.status != "active" or not chef.is_verified:
            raise ApiError(404, "chef_not_found", "الشيف غير موجود.")

        existing = self.db.scalar(
            select(FavoriteChefEntity).where(
                FavoriteChefEntity.customer_id == customer_id,
                FavoriteChefEntity.chef_id == chef_id,
            )
        )
        if existing is None:
            row = FavoriteChefEntity(
                customer_id=customer_id,
                chef_id=chef_id,
            )
            self.db.add(row)
            self.db.flush()
            self.audit.add(
                action="customer.favorite_chef.added",
                actor_user_id=customer_id,
                entity_type="chef_profile",
                entity_id=str(chef_id),
                request_id=request_id,
            )
            self.db.commit()
            self.db.refresh(row)
        else:
            row = existing

        return self._chef_response(row, chef)

    def remove_chef(
        self,
        *,
        customer_id: UUID,
        chef_id: UUID,
        request_id: str | None,
    ) -> None:
        row = self.db.scalar(
            select(FavoriteChefEntity).where(
                FavoriteChefEntity.customer_id == customer_id,
                FavoriteChefEntity.chef_id == chef_id,
            )
        )
        if row is None:
            return
        self.db.delete(row)
        self.audit.add(
            action="customer.favorite_chef.removed",
            actor_user_id=customer_id,
            entity_type="chef_profile",
            entity_id=str(chef_id),
            request_id=request_id,
        )
        self.db.commit()

    def list_chefs(
        self,
        *,
        customer_id: UUID,
    ) -> list[FavoriteChefResponse]:
        rows = list(
            self.db.execute(
                select(FavoriteChefEntity, ChefProfileEntity)
                .join(
                    ChefProfileEntity,
                    ChefProfileEntity.user_id == FavoriteChefEntity.chef_id,
                )
                .where(FavoriteChefEntity.customer_id == customer_id)
                .order_by(FavoriteChefEntity.created_at.desc())
            ).all()
        )
        return [self._chef_response(fav, chef) for fav, chef in rows]

    def add_dish(
        self,
        *,
        customer_id: UUID,
        dish_id: UUID,
        request_id: str | None,
    ) -> FavoriteDishResponse:
        dish = self.db.get(DishEntity, dish_id)
        if dish is None or not dish.is_active:
            raise ApiError(404, "dish_not_found", "الطبق غير موجود.")

        chef = self.db.get(ChefProfileEntity, dish.chef_id)
        if chef is None or chef.status != "active" or not chef.is_verified:
            raise ApiError(404, "dish_not_found", "الطبق غير موجود.")

        existing = self.db.scalar(
            select(FavoriteDishEntity).where(
                FavoriteDishEntity.customer_id == customer_id,
                FavoriteDishEntity.dish_id == dish_id,
            )
        )
        if existing is None:
            row = FavoriteDishEntity(
                customer_id=customer_id,
                dish_id=dish_id,
            )
            self.db.add(row)
            self.db.flush()
            self.audit.add(
                action="customer.favorite_dish.added",
                actor_user_id=customer_id,
                entity_type="dish",
                entity_id=str(dish_id),
                request_id=request_id,
            )
            self.db.commit()
            self.db.refresh(row)
        else:
            row = existing

        return self._dish_response(row, dish)

    def remove_dish(
        self,
        *,
        customer_id: UUID,
        dish_id: UUID,
        request_id: str | None,
    ) -> None:
        row = self.db.scalar(
            select(FavoriteDishEntity).where(
                FavoriteDishEntity.customer_id == customer_id,
                FavoriteDishEntity.dish_id == dish_id,
            )
        )
        if row is None:
            return
        self.db.delete(row)
        self.audit.add(
            action="customer.favorite_dish.removed",
            actor_user_id=customer_id,
            entity_type="dish",
            entity_id=str(dish_id),
            request_id=request_id,
        )
        self.db.commit()

    def list_dishes(
        self,
        *,
        customer_id: UUID,
    ) -> list[FavoriteDishResponse]:
        rows = list(
            self.db.execute(
                select(FavoriteDishEntity, DishEntity)
                .join(
                    DishEntity,
                    DishEntity.id == FavoriteDishEntity.dish_id,
                )
                .where(FavoriteDishEntity.customer_id == customer_id)
                .order_by(FavoriteDishEntity.created_at.desc())
            ).all()
        )
        return [self._dish_response(fav, dish) for fav, dish in rows]

    def summary(self, *, customer_id: UUID) -> FavoritesSummaryResponse:
        chefs = int(
            self.db.scalar(
                select(func.count(FavoriteChefEntity.id)).where(
                    FavoriteChefEntity.customer_id == customer_id
                )
            )
            or 0
        )
        dishes = int(
            self.db.scalar(
                select(func.count(FavoriteDishEntity.id)).where(
                    FavoriteDishEntity.customer_id == customer_id
                )
            )
            or 0
        )
        return FavoritesSummaryResponse(
            chefs_count=chefs,
            dishes_count=dishes,
        )

    def _chef_response(
        self,
        fav: FavoriteChefEntity,
        chef: ChefProfileEntity,
    ) -> FavoriteChefResponse:
        return FavoriteChefResponse(
            favorite_id=fav.id,
            chef_id=chef.user_id,
            display_name=chef.display_name,
            specialty=chef.specialty,
            area=chef.area,
            rating=chef.rating,
            is_verified=chef.is_verified,
            is_open_today=chef.is_open_today,
            created_at=fav.created_at,
        )

    def _dish_response(
        self,
        fav: FavoriteDishEntity,
        dish: DishEntity,
    ) -> FavoriteDishResponse:
        return FavoriteDishResponse(
            favorite_id=fav.id,
            dish_id=dish.id,
            chef_id=dish.chef_id,
            name=dish.name,
            category=dish.category,
            base_price_minor=dish.base_price_minor,
            image_url=dish.image_url,
            is_active=dish.is_active,
            created_at=fav.created_at,
        )
