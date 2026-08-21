from __future__ import annotations

from collections import Counter
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.db_models import ChefProfileEntity
from app.core.errors import ApiError
from app.core.config import Settings
from app.modules.chef_app.schemas import (
    ChefAppDashboardResponse,
    ChefSelfProfileResponse,
)
from app.modules.fulfillment.service import FulfillmentService
from app.modules.menus.service import MenuService
from app.modules.special_orders.service import SpecialOrderService


class ChefAppService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def profile(self, *, chef_id: UUID) -> ChefSelfProfileResponse:
        chef = self.db.get(ChefProfileEntity, chef_id)
        if chef is None:
            raise ApiError(404, "chef_profile_not_found", "ملف الشيف غير موجود.")
        return ChefSelfProfileResponse(
            id=chef.user_id,
            display_name=chef.display_name,
            specialty=chef.specialty,
            area=chef.area,
            status=chef.status,
            rating=chef.rating,
            is_verified=chef.is_verified,
            is_open_today=chef.is_open_today,
        )

    def dashboard(
        self,
        *,
        chef_id: UUID,
        service_date: date,
    ) -> ChefAppDashboardResponse:
        chef = self.profile(chef_id=chef_id)

        menu = MenuService(self.db).dashboard(
            chef_id=chef_id,
            service_date=service_date,
        )
        order_rows = FulfillmentService(
            self.db,
            self.settings,
        ).queue(
            chef_id=chef_id,
            stage=None,
        )
        special_rows = SpecialOrderService(
            self.db,
            self.settings,
        ).chef_queue(
            chef_id=chef_id,
            status=None,
        )

        order_counts = Counter(row.fulfillment_stage for row in order_rows)
        special_counts = Counter(row.status for row in special_rows)

        return ChefAppDashboardResponse(
            chef=chef,
            service_date=service_date,
            kitchen_status=menu.kitchen_status,
            signature_dishes=menu.signature_dishes,
            today_items=menu.today_items,
            sold_out_items=menu.sold_out_items,
            available_quantity=menu.available_quantity,
            orders_new=order_counts["new"],
            orders_accepted=order_counts["accepted"],
            orders_preparing=order_counts["preparing"],
            orders_packaging=order_counts["packaging"],
            orders_ready=order_counts["ready"],
            special_review=special_counts["chef_review"],
            special_counter_offer=special_counts["counter_offer"],
            special_awaiting_payment=special_counts["awaiting_payment"],
            special_scheduled=special_counts["scheduled"],
        )
