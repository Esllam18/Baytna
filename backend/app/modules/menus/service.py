from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db_models import ChefProfileEntity, DailyMenuItemEntity, DishEntity, MediaAssetEntity
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import utc_now
from app.modules.menus.repository import MenuRepository
from app.modules.menus.schemas import (
    ChefDashboardResponse,
    DailyMenuItemResponse,
    DailyMenuReplaceRequest,
    DishCreateRequest,
    DishMediaRequest,
    DishResponse,
    DishUpdateRequest,
    OpenKitchenRequest,
    QuantityUpdateRequest,
    TodayMenuResponse,
    WorkdayResponse,
)


def _availability_label(item: DailyMenuItemEntity) -> str:
    if item.status == "hidden":
        return "غير متاح"
    if item.status == "sold_out" or item.quantity_available <= 0:
        return "نفدت الكمية اليوم"
    return "متاح اليوم"


class MenuService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MenuRepository(db)
        self.audit = AuditRepository(db)

    def _require_active_chef(self, chef_id: UUID) -> ChefProfileEntity:
        chef = self.repo.chef(chef_id)
        if chef is None:
            raise ApiError(404, "chef_not_found", "ملف الشيف غير موجود.")
        if chef.status != "active" or not chef.is_verified:
            raise ApiError(
                403,
                "chef_not_active",
                "يجب أن يكون حساب الشيف معتمدًا ونشطًا.",
            )
        return chef

    def _dish_owned_by_chef(
        self,
        *,
        chef_id: UUID,
        dish_id: UUID,
        require_active: bool = False,
    ) -> DishEntity:
        dish = self.repo.dish(dish_id)
        if dish is None or dish.chef_id != chef_id:
            raise ApiError(404, "dish_not_found", "الطبق غير موجود.")
        if require_active and not dish.is_active:
            raise ApiError(409, "dish_inactive", "الطبق غير نشط في قائمة التخصص.")
        return dish

    def create_dish(
        self,
        *,
        chef_id: UUID,
        payload: DishCreateRequest,
        request_id: str | None,
    ) -> DishResponse:
        self._require_active_chef(chef_id)

        try:
            dish = self.repo.create_dish(
                chef_id=chef_id,
                values=payload.model_dump(),
            )
            self.audit.add(
                action="chef.signature_menu.dish_created",
                actor_user_id=chef_id,
                entity_type="dish",
                entity_id=str(dish.id),
                request_id=request_id,
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ApiError(
                409,
                "dish_name_conflict",
                "يوجد طبق بنفس الاسم بالفعل في قائمة التخصص.",
            ) from exc

        self.db.refresh(dish)
        return DishResponse.model_validate(dish)

    def update_dish(
        self,
        *,
        chef_id: UUID,
        dish_id: UUID,
        payload: DishUpdateRequest,
        request_id: str | None,
    ) -> DishResponse:
        self._require_active_chef(chef_id)
        dish = self._dish_owned_by_chef(chef_id=chef_id, dish_id=dish_id)

        values = payload.model_dump(exclude_unset=True)
        for key, value in values.items():
            setattr(dish, key, value)

        try:
            self.audit.add(
                action="chef.signature_menu.dish_updated",
                actor_user_id=chef_id,
                entity_type="dish",
                entity_id=str(dish.id),
                request_id=request_id,
                metadata={"fields": sorted(values.keys())},
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ApiError(
                409,
                "dish_name_conflict",
                "يوجد طبق بنفس الاسم بالفعل في قائمة التخصص.",
            ) from exc

        self.db.refresh(dish)
        return DishResponse.model_validate(dish)

    def list_signature(
        self,
        *,
        chef_id: UUID,
        include_inactive: bool,
        owner_view: bool,
    ) -> list[DishResponse]:
        chef = self.repo.chef(chef_id)
        if chef is None:
            raise ApiError(404, "chef_not_found", "الشيف غير موجود.")

        if not owner_view and (chef.status != "active" or not chef.is_verified):
            raise ApiError(404, "chef_not_found", "الشيف غير موجود.")

        dishes = self.repo.list_signature(
            chef_id,
            include_inactive=include_inactive if owner_view else False,
        )
        return [DishResponse.model_validate(x) for x in dishes]


    def set_dish_media(self, *, chef_id: UUID, dish_id: UUID, payload: DishMediaRequest, request_id: str | None) -> DishResponse:
        self._require_active_chef(chef_id)
        dish = self._dish_owned_by_chef(chef_id=chef_id, dish_id=dish_id)
        if payload.media_asset_id is None:
            dish.media_asset_id = None
            dish.image_url = None
        else:
            asset = self.db.get(MediaAssetEntity, payload.media_asset_id)
            if asset is None or asset.owner_user_id != chef_id:
                raise ApiError(404, "media_not_found", "الصورة غير موجودة.")
            if asset.status != "ready" or asset.purpose != "dish_image" or asset.visibility != "public":
                raise ApiError(409, "dish_media_invalid", "الصورة يجب أن تكون جاهزة وعامة ومن نوع dish_image.")
            dish.media_asset_id = asset.id
            dish.image_url = f"/api/v1/media/public/{asset.id}"
        self.audit.add(action="chef.signature_menu.media_updated", actor_user_id=chef_id, entity_type="dish", entity_id=str(dish.id), request_id=request_id, metadata={"media_asset_id": str(payload.media_asset_id) if payload.media_asset_id else None})
        self.db.commit(); self.db.refresh(dish)
        return DishResponse.model_validate(dish)

    def open_kitchen(
        self,
        *,
        chef_id: UUID,
        payload: OpenKitchenRequest,
        request_id: str | None,
    ) -> WorkdayResponse:
        self._require_active_chef(chef_id)
        workday = self.repo.workday(chef_id, payload.service_date)

        if workday is None:
            workday = self.repo.create_workday(
                chef_id=chef_id,
                values={
                    "service_date": payload.service_date,
                    "status": "open",
                    "cutoff_at": payload.cutoff_at,
                    "delivery_window_start": payload.delivery_window_start,
                    "delivery_window_end": payload.delivery_window_end,
                },
            )
            action = "chef.kitchen.opened"
        else:
            workday.status = "open"
            workday.cutoff_at = payload.cutoff_at
            workday.delivery_window_start = payload.delivery_window_start
            workday.delivery_window_end = payload.delivery_window_end
            workday.opened_at = utc_now()
            workday.closed_at = None
            action = "chef.kitchen.reopened"

        self.audit.add(
            action=action,
            actor_user_id=chef_id,
            entity_type="chef_workday",
            entity_id=str(workday.id),
            request_id=request_id,
            metadata={"service_date": payload.service_date.isoformat()},
        )
        self.db.commit()
        self.db.refresh(workday)
        return WorkdayResponse.model_validate(workday)

    def close_kitchen(
        self,
        *,
        chef_id: UUID,
        service_date: date,
        request_id: str | None,
    ) -> WorkdayResponse:
        self._require_active_chef(chef_id)
        workday = self.repo.workday(chef_id, service_date)
        if workday is None:
            raise ApiError(404, "workday_not_found", "مطبخ اليوم غير مفتوح لهذا التاريخ.")

        workday.status = "closed"
        workday.closed_at = utc_now()

        self.audit.add(
            action="chef.kitchen.closed",
            actor_user_id=chef_id,
            entity_type="chef_workday",
            entity_id=str(workday.id),
            request_id=request_id,
            metadata={"service_date": service_date.isoformat()},
        )
        self.db.commit()
        self.db.refresh(workday)
        return WorkdayResponse.model_validate(workday)

    def replace_today_menu(
        self,
        *,
        chef_id: UUID,
        payload: DailyMenuReplaceRequest,
        request_id: str | None,
    ) -> TodayMenuResponse:
        self._require_active_chef(chef_id)
        workday = self.repo.workday(chef_id, payload.service_date)

        if workday is None or workday.status != "open":
            raise ApiError(
                409,
                "kitchen_not_open",
                "افتح مطبخ اليوم أولًا قبل إضافة الأصناف.",
            )

        prepared = []
        for item in payload.items:
            dish = self._dish_owned_by_chef(
                chef_id=chef_id,
                dish_id=item.dish_id,
                require_active=True,
            )
            price = item.price_minor or dish.base_price_minor
            status = (
                "hidden"
                if not item.is_visible
                else ("sold_out" if item.quantity_total == 0 else "available")
            )
            prepared.append((dish, item, price, status))

        self.repo.remove_daily_items(workday.id)
        for dish, item, price, status in prepared:
            self.repo.create_daily_item(
                workday_id=workday.id,
                dish_id=dish.id,
                price_minor=price,
                quantity_total=item.quantity_total,
                max_per_order=item.max_per_order,
                status=status,
            )

        self.audit.add(
            action="chef.today_menu.replaced",
            actor_user_id=chef_id,
            entity_type="chef_workday",
            entity_id=str(workday.id),
            request_id=request_id,
            metadata={
                "service_date": payload.service_date.isoformat(),
                "items_count": len(prepared),
            },
        )
        self.db.commit()
        return self.today_menu(
            chef_id=chef_id,
            service_date=payload.service_date,
            owner_view=True,
        )

    def update_quantity(
        self,
        *,
        chef_id: UUID,
        item_id: UUID,
        payload: QuantityUpdateRequest,
        request_id: str | None,
    ) -> DailyMenuItemResponse:
        self._require_active_chef(chef_id)
        item = self.repo.daily_item(item_id)
        if item is None:
            raise ApiError(404, "daily_menu_item_not_found", "الصنف غير موجود.")

        workday = None
        # Keep ownership validation explicit through the workday.
        from app.core.db_models import ChefWorkdayEntity
        workday = self.db.get(ChefWorkdayEntity, item.workday_id)
        if workday is None or workday.chef_id != chef_id:
            raise ApiError(404, "daily_menu_item_not_found", "الصنف غير موجود.")

        if payload.quantity_available > item.quantity_total:
            raise ApiError(
                422,
                "quantity_exceeds_total",
                "الكمية المتاحة لا يمكن أن تتجاوز كمية اليوم الأصلية.",
            )

        item.quantity_available = payload.quantity_available
        if item.status != "hidden":
            item.status = "sold_out" if payload.quantity_available == 0 else "available"

        self.audit.add(
            action="chef.today_menu.quantity_updated",
            actor_user_id=chef_id,
            entity_type="daily_menu_item",
            entity_id=str(item.id),
            request_id=request_id,
            metadata={"quantity_available": payload.quantity_available},
        )
        self.db.commit()
        self.db.refresh(item)

        dish = self.repo.dish(item.dish_id)
        return self._daily_response(item, dish)

    def _daily_response(
        self,
        item: DailyMenuItemEntity,
        dish: DishEntity,
    ) -> DailyMenuItemResponse:
        return DailyMenuItemResponse(
            id=item.id,
            dish_id=dish.id,
            name=dish.name,
            description=dish.description,
            category=dish.category,
            price_minor=item.price_minor,
            quantity_total=item.quantity_total,
            quantity_available=item.quantity_available,
            max_per_order=item.max_per_order,
            status=item.status,
            availability_label=_availability_label(item),
            image_url=dish.image_url,
        )

    def today_menu(
        self,
        *,
        chef_id: UUID,
        service_date: date,
        owner_view: bool = False,
    ) -> TodayMenuResponse:
        chef = self.repo.chef(chef_id)
        if chef is None:
            raise ApiError(404, "chef_not_found", "الشيف غير موجود.")

        if not owner_view and (chef.status != "active" or not chef.is_verified):
            raise ApiError(404, "chef_not_found", "الشيف غير موجود.")

        workday = self.repo.workday(chef_id, service_date)

        if workday is None:
            return TodayMenuResponse(
                chef_id=chef_id,
                service_date=service_date,
                kitchen_status="closed",
                cutoff_at=None,
                delivery_window_start=None,
                delivery_window_end=None,
                items=[],
            )

        if not owner_view and workday.status != "open":
            return TodayMenuResponse(
                chef_id=chef_id,
                service_date=service_date,
                kitchen_status="closed",
                cutoff_at=workday.cutoff_at,
                delivery_window_start=workday.delivery_window_start,
                delivery_window_end=workday.delivery_window_end,
                items=[],
            )

        items = self.repo.list_daily_items(
            workday.id,
            include_hidden=owner_view,
        )
        responses = []
        for item in items:
            dish = self.repo.dish(item.dish_id)
            if dish is None:
                continue
            if not owner_view and not dish.is_active:
                continue
            responses.append(self._daily_response(item, dish))

        return TodayMenuResponse(
            chef_id=chef_id,
            service_date=service_date,
            kitchen_status=workday.status,
            cutoff_at=workday.cutoff_at,
            delivery_window_start=workday.delivery_window_start,
            delivery_window_end=workday.delivery_window_end,
            items=responses,
        )

    def dashboard(
        self,
        *,
        chef_id: UUID,
        service_date: date,
    ) -> ChefDashboardResponse:
        self._require_active_chef(chef_id)
        all_dishes = self.repo.list_signature(chef_id, include_inactive=True)
        workday = self.repo.workday(chef_id, service_date)

        items = []
        if workday:
            items = self.repo.list_daily_items(
                workday.id,
                include_hidden=True,
            )

        return ChefDashboardResponse(
            chef_id=chef_id,
            service_date=service_date,
            kitchen_status=workday.status if workday else "closed",
            signature_dishes=len(all_dishes),
            active_signature_dishes=sum(1 for x in all_dishes if x.is_active),
            today_items=len(items),
            sold_out_items=sum(
                1
                for x in items
                if x.status == "sold_out" or x.quantity_available == 0
            ),
            total_quantity=sum(x.quantity_total for x in items),
            available_quantity=sum(x.quantity_available for x in items),
        )
