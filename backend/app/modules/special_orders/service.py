from __future__ import annotations

from datetime import date, timedelta
from math import ceil
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    AddressEntity,
    ChefProfileEntity,
    ChefScheduleOverrideEntity,
    ChefWeeklyScheduleEntity,
    DishEntity,
    OrderDeliveryAddressEntity,
    OrderEntity,
    OrderItemEntity,
    OrderStatusEventEntity,
    SpecialOrderEventEntity,
    SpecialOrderRequestEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import ensure_utc, utc_now
from app.modules.notifications.service import NotificationService
from app.modules.orders.service import OrderService
from app.modules.payments.schemas import CreatePaymentIntentRequest
from app.modules.payments.service import PaymentService
from app.modules.delivery_timing.service import DeliveryTimingService
from app.modules.launch_governance.service import LaunchTrafficGovernanceService
from app.modules.special_orders.schemas import (
    AvailabilityDayResponse,
    ChefAcceptSpecialOrderRequest,
    ChefCounterOfferRequest,
    ChefRejectSpecialOrderRequest,
    ScheduleOverrideRequest,
    ScheduleOverrideResponse,
    SpecialOrderCheckoutRequest,
    SpecialOrderCheckoutResponse,
    SpecialOrderCreateRequest,
    SpecialOrderEventResponse,
    SpecialOrderResponse,
    WeeklyScheduleDayResponse,
    WeeklyScheduleUpsertRequest,
)


ACTIVE_CAPACITY_STATUSES = {
    "chef_review",
    "counter_offer",
    "awaiting_payment",
    "scheduled",
}


class SpecialOrderService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.audit = AuditRepository(db)

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------
    def upsert_weekly_schedule(
        self,
        *,
        chef_id: UUID,
        payload: WeeklyScheduleUpsertRequest,
        request_id: str | None,
    ) -> list[WeeklyScheduleDayResponse]:
        self._active_chef(chef_id)

        for item in payload.days:
            row = self.db.scalar(
                select(ChefWeeklyScheduleEntity).where(
                    ChefWeeklyScheduleEntity.chef_id == chef_id,
                    ChefWeeklyScheduleEntity.weekday == item.weekday,
                )
            )
            if row is None:
                row = ChefWeeklyScheduleEntity(
                    chef_id=chef_id,
                    weekday=item.weekday,
                )
                self.db.add(row)

            row.is_available = item.is_available
            row.delivery_window_start = item.delivery_window_start
            row.delivery_window_end = item.delivery_window_end
            row.max_special_orders = item.max_special_orders

        self.audit.add(
            action="chef.schedule.weekly_updated",
            actor_user_id=chef_id,
            entity_type="chef_profile",
            entity_id=str(chef_id),
            request_id=request_id,
            metadata={"weekdays": sorted(x.weekday for x in payload.days)},
        )
        self.db.commit()
        return self.weekly_schedule(chef_id=chef_id)

    def weekly_schedule(
        self,
        *,
        chef_id: UUID,
    ) -> list[WeeklyScheduleDayResponse]:
        self._active_chef(chef_id)
        rows = list(
            self.db.scalars(
                select(ChefWeeklyScheduleEntity)
                .where(ChefWeeklyScheduleEntity.chef_id == chef_id)
                .order_by(ChefWeeklyScheduleEntity.weekday.asc())
            ).all()
        )
        return [
            WeeklyScheduleDayResponse(
                weekday=x.weekday,
                is_available=x.is_available,
                delivery_window_start=x.delivery_window_start,
                delivery_window_end=x.delivery_window_end,
                max_special_orders=x.max_special_orders,
            )
            for x in rows
        ]

    def upsert_override(
        self,
        *,
        chef_id: UUID,
        service_date: date,
        payload: ScheduleOverrideRequest,
        request_id: str | None,
    ) -> ScheduleOverrideResponse:
        self._active_chef(chef_id)

        row = self.db.scalar(
            select(ChefScheduleOverrideEntity).where(
                ChefScheduleOverrideEntity.chef_id == chef_id,
                ChefScheduleOverrideEntity.service_date == service_date,
            )
        )
        if row is None:
            row = ChefScheduleOverrideEntity(
                chef_id=chef_id,
                service_date=service_date,
                is_available=payload.is_available,
            )
            self.db.add(row)

        row.is_available = payload.is_available
        row.delivery_window_start = payload.delivery_window_start
        row.delivery_window_end = payload.delivery_window_end
        row.max_special_orders = payload.max_special_orders
        row.reason = payload.reason

        self.audit.add(
            action="chef.schedule.override_updated",
            actor_user_id=chef_id,
            entity_type="chef_schedule_override",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "service_date": service_date.isoformat(),
                "is_available": payload.is_available,
            },
        )
        self.db.commit()
        self.db.refresh(row)
        return ScheduleOverrideResponse.model_validate(row)

    def list_overrides(
        self,
        *,
        chef_id: UUID,
    ) -> list[ScheduleOverrideResponse]:
        self._active_chef(chef_id)
        rows = list(
            self.db.scalars(
                select(ChefScheduleOverrideEntity)
                .where(ChefScheduleOverrideEntity.chef_id == chef_id)
                .order_by(ChefScheduleOverrideEntity.service_date.asc())
            ).all()
        )
        return [ScheduleOverrideResponse.model_validate(x) for x in rows]

    def availability(
        self,
        *,
        chef_id: UUID,
        start_date: date,
        days: int,
    ) -> list[AvailabilityDayResponse]:
        self._active_chef(chef_id)
        return [
            self._availability_for_date(
                chef_id=chef_id,
                service_date=start_date + timedelta(days=offset),
            )
            for offset in range(days)
        ]

    def _schedule_rule(
        self,
        *,
        chef_id: UUID,
        service_date: date,
    ) -> tuple[bool, str, str | None, str | None, int]:
        weekly = self.db.scalar(
            select(ChefWeeklyScheduleEntity).where(
                ChefWeeklyScheduleEntity.chef_id == chef_id,
                ChefWeeklyScheduleEntity.weekday == service_date.weekday(),
            )
        )
        override = self.db.scalar(
            select(ChefScheduleOverrideEntity).where(
                ChefScheduleOverrideEntity.chef_id == chef_id,
                ChefScheduleOverrideEntity.service_date == service_date,
            )
        )

        if override is not None:
            start = (
                override.delivery_window_start
                if override.delivery_window_start is not None
                else (weekly.delivery_window_start if weekly else None)
            )
            end = (
                override.delivery_window_end
                if override.delivery_window_end is not None
                else (weekly.delivery_window_end if weekly else None)
            )
            capacity = (
                override.max_special_orders
                if override.max_special_orders is not None
                else (weekly.max_special_orders if weekly else 0)
            )
            return override.is_available, "override", start, end, capacity

        if weekly is not None:
            return (
                weekly.is_available,
                "weekly",
                weekly.delivery_window_start,
                weekly.delivery_window_end,
                weekly.max_special_orders,
            )

        return False, "unpublished", None, None, 0

    def _availability_for_date(
        self,
        *,
        chef_id: UUID,
        service_date: date,
        exclude_request_id: UUID | None = None,
    ) -> AvailabilityDayResponse:
        configured_available, source, start, end, capacity = self._schedule_rule(
            chef_id=chef_id,
            service_date=service_date,
        )
        used = self._capacity_used(
            chef_id=chef_id,
            service_date=service_date,
            exclude_request_id=exclude_request_id,
        )
        remaining = max(0, capacity - used)
        return AvailabilityDayResponse(
            service_date=service_date,
            weekday=service_date.weekday(),
            is_available=(
                configured_available and capacity > 0 and remaining > 0
            ),
            source=source,
            delivery_window_start=start,
            delivery_window_end=end,
            capacity_total=capacity,
            capacity_used=used,
            capacity_remaining=remaining,
        )

    def _capacity_used(
        self,
        *,
        chef_id: UUID,
        service_date: date,
        exclude_request_id: UUID | None = None,
    ) -> int:
        rows = list(
            self.db.scalars(
                select(SpecialOrderRequestEntity).where(
                    SpecialOrderRequestEntity.chef_id == chef_id,
                    SpecialOrderRequestEntity.status.in_(ACTIVE_CAPACITY_STATUSES),
                )
            ).all()
        )
        count = 0
        for row in rows:
            if exclude_request_id is not None and row.id == exclude_request_id:
                continue
            effective_date = (
                row.final_service_date
                or row.proposed_service_date
                or row.requested_service_date
            )
            if effective_date == service_date:
                count += 1
        return count

    # ------------------------------------------------------------------
    # Customer request lifecycle
    # ------------------------------------------------------------------
    def create_request(
        self,
        *,
        customer_id: UUID,
        payload: SpecialOrderCreateRequest,
        request_id: str | None,
    ) -> SpecialOrderResponse:
        dish = self.db.get(DishEntity, payload.dish_id)
        if dish is None or not dish.is_active:
            raise ApiError(404, "dish_not_found", "الطبق غير موجود.")
        if not dish.is_special_order_available:
            raise ApiError(
                409,
                "special_order_not_available",
                "هذا الطبق غير متاح للطلب الخاص.",
            )

        chef = self._active_chef(dish.chef_id)
        self._validate_notice(
            service_date=payload.requested_service_date,
            prep_notice_hours=dish.prep_notice_hours,
        )
        availability = self._ensure_schedulable(
            chef_id=chef.user_id,
            service_date=payload.requested_service_date,
            requested_start=payload.requested_window_start,
            requested_end=payload.requested_window_end,
        )

        row = SpecialOrderRequestEntity(
            customer_id=customer_id,
            chef_id=chef.user_id,
            dish_id=dish.id,
            request_type=payload.request_type,
            status="chef_review",
            quantity=payload.quantity,
            requested_service_date=payload.requested_service_date,
            requested_window_start=(
                payload.requested_window_start
                or availability.delivery_window_start
            ),
            requested_window_end=(
                payload.requested_window_end
                or availability.delivery_window_end
            ),
            requested_unit_price_minor=dish.base_price_minor,
            customer_note=payload.customer_note,
        )
        self.db.add(row)
        self.db.flush()
        self._event(
            row,
            from_status=None,
            to_status="chef_review",
            actor_user_id=customer_id,
            reason="customer_submitted",
            data={"request_type": payload.request_type},
        )
        self.audit.add(
            action="customer.special_order.created",
            actor_user_id=customer_id,
            entity_type="special_order_request",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "chef_id": str(row.chef_id),
                "dish_id": str(row.dish_id),
                "service_date": row.requested_service_date.isoformat(),
                "request_type": row.request_type,
            },
        )
        self.db.commit()
        return self._response(row)

    def customer_list(
        self,
        *,
        customer_id: UUID,
    ) -> list[SpecialOrderResponse]:
        self.expire_due_requests()
        rows = list(
            self.db.scalars(
                select(SpecialOrderRequestEntity)
                .where(SpecialOrderRequestEntity.customer_id == customer_id)
                .order_by(SpecialOrderRequestEntity.created_at.desc())
            ).all()
        )
        return [self._response(x) for x in rows]

    def customer_detail(
        self,
        *,
        customer_id: UUID,
        special_order_id: UUID,
    ) -> SpecialOrderResponse:
        self.expire_due_requests()
        row = self.db.get(SpecialOrderRequestEntity, special_order_id)
        if row is None or row.customer_id != customer_id:
            raise ApiError(
                404,
                "special_order_not_found",
                "الطلب الخاص غير موجود.",
            )
        return self._response(row)

    def accept_counter_offer(
        self,
        *,
        customer_id: UUID,
        special_order_id: UUID,
        request_id: str | None,
    ) -> SpecialOrderResponse:
        row = self._customer_request(
            customer_id=customer_id,
            special_order_id=special_order_id,
        )
        if row.status == "awaiting_payment":
            return self._response(row)
        if row.status != "counter_offer":
            raise ApiError(
                409,
                "special_order_not_counter_offer",
                "لا يوجد عرض بديل في انتظار موافقتك.",
            )
        if row.proposed_service_date is None or row.proposed_unit_price_minor is None:
            raise ApiError(409, "counter_offer_invalid", "العرض البديل غير مكتمل.")

        self._ensure_schedulable(
            chef_id=row.chef_id,
            service_date=row.proposed_service_date,
            requested_start=row.proposed_window_start,
            requested_end=row.proposed_window_end,
            exclude_request_id=row.id,
        )

        old = row.status
        row.status = "awaiting_payment"
        row.final_service_date = row.proposed_service_date
        row.final_window_start = row.proposed_window_start
        row.final_window_end = row.proposed_window_end
        row.final_unit_price_minor = row.proposed_unit_price_minor
        row.final_total_minor = row.proposed_unit_price_minor * row.quantity
        row.customer_accepted_at = utc_now()
        row.offer_expires_at = utc_now() + timedelta(
            minutes=self.settings.special_order_payment_window_minutes
        )
        self._event(
            row,
            from_status=old,
            to_status="awaiting_payment",
            actor_user_id=customer_id,
            reason="customer_accepted_counter_offer",
        )
        self.audit.add(
            action="customer.special_order.counter_accepted",
            actor_user_id=customer_id,
            entity_type="special_order_request",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()
        return self._response(row)

    def cancel(
        self,
        *,
        customer_id: UUID,
        special_order_id: UUID,
        request_id: str | None,
    ) -> SpecialOrderResponse:
        row = self._customer_request(
            customer_id=customer_id,
            special_order_id=special_order_id,
        )
        if row.status == "cancelled":
            return self._response(row)
        if row.status in {"scheduled", "rejected", "expired"}:
            raise ApiError(
                409,
                "special_order_cannot_cancel",
                "لا يمكن إلغاء الطلب الخاص من حالته الحالية.",
            )

        old = row.status
        row.status = "cancelled"
        row.cancelled_at = utc_now()

        if row.order_id is not None:
            order = self.db.get(OrderEntity, row.order_id)
            if order is not None and order.status == "pending_payment":
                order.status = "cancelled"
                self.db.add(
                    OrderStatusEventEntity(
                        order_id=order.id,
                        from_status="pending_payment",
                        to_status="cancelled",
                        actor_user_id=customer_id,
                        reason="special_order_cancelled_before_payment",
                    )
                )

        self._event(
            row,
            from_status=old,
            to_status="cancelled",
            actor_user_id=customer_id,
            reason="customer_cancelled",
        )
        self.audit.add(
            action="customer.special_order.cancelled",
            actor_user_id=customer_id,
            entity_type="special_order_request",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()
        return self._response(row)

    # ------------------------------------------------------------------
    # Chef actions
    # ------------------------------------------------------------------
    def chef_queue(
        self,
        *,
        chef_id: UUID,
        status: str | None,
    ) -> list[SpecialOrderResponse]:
        self._active_chef(chef_id)
        self.expire_due_requests()
        stmt = select(SpecialOrderRequestEntity).where(
            SpecialOrderRequestEntity.chef_id == chef_id
        )
        if status:
            stmt = stmt.where(SpecialOrderRequestEntity.status == status)
        stmt = stmt.order_by(
            SpecialOrderRequestEntity.requested_service_date.asc(),
            SpecialOrderRequestEntity.created_at.asc(),
        )
        return [self._response(x) for x in self.db.scalars(stmt).all()]

    def chef_detail(
        self,
        *,
        chef_id: UUID,
        special_order_id: UUID,
    ) -> SpecialOrderResponse:
        row = self._chef_request(
            chef_id=chef_id,
            special_order_id=special_order_id,
        )
        return self._response(row)

    def chef_accept(
        self,
        *,
        chef_id: UUID,
        special_order_id: UUID,
        payload: ChefAcceptSpecialOrderRequest,
        request_id: str | None,
    ) -> SpecialOrderResponse:
        row = self._chef_request(
            chef_id=chef_id,
            special_order_id=special_order_id,
        )
        if row.status == "awaiting_payment":
            return self._response(row)
        if row.status != "chef_review":
            raise ApiError(
                409,
                "special_order_cannot_accept",
                "لا يمكن قبول الطلب الخاص من حالته الحالية.",
            )

        availability = self._ensure_schedulable(
            chef_id=chef_id,
            service_date=row.requested_service_date,
            requested_start=(payload.delivery_window_start or row.requested_window_start),
            requested_end=(payload.delivery_window_end or row.requested_window_end),
            exclude_request_id=row.id,
        )
        price = payload.unit_price_minor or row.requested_unit_price_minor
        old = row.status
        row.status = "awaiting_payment"
        row.final_service_date = row.requested_service_date
        row.final_window_start = (
            payload.delivery_window_start
            or row.requested_window_start
            or availability.delivery_window_start
        )
        row.final_window_end = (
            payload.delivery_window_end
            or row.requested_window_end
            or availability.delivery_window_end
        )
        row.final_unit_price_minor = price
        row.final_total_minor = price * row.quantity
        row.chef_note = payload.chef_note
        row.chef_responded_at = utc_now()
        row.offer_expires_at = utc_now() + timedelta(
            minutes=self.settings.special_order_payment_window_minutes
        )

        self._event(
            row,
            from_status=old,
            to_status="awaiting_payment",
            actor_user_id=chef_id,
            reason="chef_accepted_quote",
            data={"unit_price_minor": price},
        )
        NotificationService(self.db, self.settings).emit(
            user_id=row.customer_id,
            kind="special_order_accepted",
            title="الشيف وافقت على طلبك الخاص",
            body="العرض جاهز للدفع وتأكيد الموعد.",
            dedupe_key=f"special-order-accepted:{row.id}",
            action_url=f"/special-orders/{row.id}",
            data_json={"special_order_id": str(row.id)},
        )
        self.audit.add(
            action="chef.special_order.accepted",
            actor_user_id=chef_id,
            entity_type="special_order_request",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()
        return self._response(row)

    def chef_counter_offer(
        self,
        *,
        chef_id: UUID,
        special_order_id: UUID,
        payload: ChefCounterOfferRequest,
        request_id: str | None,
    ) -> SpecialOrderResponse:
        row = self._chef_request(
            chef_id=chef_id,
            special_order_id=special_order_id,
        )
        if row.status != "chef_review":
            raise ApiError(
                409,
                "special_order_cannot_counter",
                "لا يمكن إرسال عرض بديل من الحالة الحالية.",
            )

        dish = self.db.get(DishEntity, row.dish_id)
        self._validate_notice(
            service_date=payload.proposed_service_date,
            prep_notice_hours=dish.prep_notice_hours,
        )
        self._ensure_schedulable(
            chef_id=chef_id,
            service_date=payload.proposed_service_date,
            requested_start=payload.proposed_window_start,
            requested_end=payload.proposed_window_end,
            exclude_request_id=row.id,
        )

        old = row.status
        row.status = "counter_offer"
        row.proposed_service_date = payload.proposed_service_date
        row.proposed_window_start = payload.proposed_window_start
        row.proposed_window_end = payload.proposed_window_end
        row.proposed_unit_price_minor = payload.proposed_unit_price_minor
        row.chef_note = payload.chef_note
        row.chef_responded_at = utc_now()

        self._event(
            row,
            from_status=old,
            to_status="counter_offer",
            actor_user_id=chef_id,
            reason="chef_counter_offer",
            data={
                "proposed_service_date": payload.proposed_service_date.isoformat(),
                "proposed_unit_price_minor": payload.proposed_unit_price_minor,
            },
        )
        NotificationService(self.db, self.settings).emit(
            user_id=row.customer_id,
            kind="special_order_counter_offer",
            title="الشيف اقترحت تعديل على طلبك",
            body="راجع الموعد والسعر المقترحين قبل التأكيد.",
            dedupe_key=f"special-order-counter:{row.id}:{row.chef_responded_at.isoformat()}",
            action_url=f"/special-orders/{row.id}",
            data_json={"special_order_id": str(row.id)},
        )
        self.audit.add(
            action="chef.special_order.counter_offered",
            actor_user_id=chef_id,
            entity_type="special_order_request",
            entity_id=str(row.id),
            request_id=request_id,
        )
        self.db.commit()
        return self._response(row)

    def chef_reject(
        self,
        *,
        chef_id: UUID,
        special_order_id: UUID,
        payload: ChefRejectSpecialOrderRequest,
        request_id: str | None,
    ) -> SpecialOrderResponse:
        row = self._chef_request(
            chef_id=chef_id,
            special_order_id=special_order_id,
        )
        if row.status == "rejected":
            return self._response(row)
        if row.status not in {"chef_review", "counter_offer"}:
            raise ApiError(
                409,
                "special_order_cannot_reject",
                "لا يمكن رفض الطلب الخاص من حالته الحالية.",
            )

        old = row.status
        row.status = "rejected"
        row.rejection_reason = payload.reason
        row.chef_responded_at = utc_now()
        self._event(
            row,
            from_status=old,
            to_status="rejected",
            actor_user_id=chef_id,
            reason=payload.reason,
        )
        NotificationService(self.db, self.settings).emit(
            user_id=row.customer_id,
            kind="special_order_rejected",
            title="تعذر تنفيذ الطلب الخاص",
            body="الشيف اعتذرت عن تنفيذ الطلب في الموعد المطلوب.",
            dedupe_key=f"special-order-rejected:{row.id}",
            action_url=f"/special-orders/{row.id}",
            data_json={"special_order_id": str(row.id)},
        )
        self.audit.add(
            action="chef.special_order.rejected",
            actor_user_id=chef_id,
            entity_type="special_order_request",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"reason": payload.reason},
        )
        self.db.commit()
        return self._response(row)

    # ------------------------------------------------------------------
    # Checkout bridge to core Order + Payment
    # ------------------------------------------------------------------
    def checkout(
        self,
        *,
        customer_id: UUID,
        special_order_id: UUID,
        payload: SpecialOrderCheckoutRequest,
        request_id: str | None,
    ) -> SpecialOrderCheckoutResponse:
        self.expire_due_requests()
        row = self._customer_request(
            customer_id=customer_id,
            special_order_id=special_order_id,
        )
        if row.status != "awaiting_payment":
            raise ApiError(
                409,
                "special_order_not_awaiting_payment",
                "الطلب الخاص غير جاهز للدفع.",
            )
        if row.offer_expires_at is None or ensure_utc(row.offer_expires_at) <= utc_now():
            self._expire_one(row)
            self.db.commit()
            raise ApiError(
                409,
                "special_order_offer_expired",
                "انتهت مهلة دفع العرض.",
            )
        if (
            row.final_service_date is None
            or row.final_unit_price_minor is None
            or row.final_total_minor is None
        ):
            raise ApiError(409, "special_order_quote_invalid", "العرض النهائي غير مكتمل.")

        order = self.db.get(OrderEntity, row.order_id) if row.order_id else None
        if order is None:
            default_address = self.db.scalar(
                select(AddressEntity)
                .where(
                    AddressEntity.user_id == customer_id,
                    AddressEntity.is_default.is_(True),
                )
                .limit(1)
            )
            if (
                default_address is None
                and self.settings.traffic_require_delivery_address_for_checkout
            ):
                raise ApiError(
                    409,
                    "delivery_address_required",
                    "يجب اختيار عنوان توصيل قبل تأكيد الطلب.",
                )
            special_traffic_reservation = (
                LaunchTrafficGovernanceService(
                    self.db,
                    self.settings,
                ).admit_or_raise(
                    customer_id=customer_id,
                    chef_id=row.chef_id,
                    service_date=row.final_service_date,
                    area=default_address.area if default_address else None,
                    request_id=request_id,
                )
                if default_address is not None
                else None
            )

            delivery_promise = DeliveryTimingService(self.settings).snapshot(
                service_date=row.final_service_date,
                window_start=row.final_window_start,
                window_end=row.final_window_end,
                source="special_order",
            )
            order = OrderEntity(
                customer_id=customer_id,
                chef_id=row.chef_id,
                source_cart_id=None,
                order_type="special",
                service_date=row.final_service_date,
                status="pending_payment",
                subtotal_minor=row.final_total_minor,
                delivery_fee_minor=0,
                discount_minor=0,
                total_minor=row.final_total_minor,
                currency="EGP",
                inventory_hold_expires_at=None,
            )
            self.db.add(order)
            self.db.flush()
            LaunchTrafficGovernanceService(
                self.db,
                self.settings,
            ).attach_admitted_order(
                reservation=special_traffic_reservation,
                order_id=order.id,
                request_id=request_id,
            )
            DeliveryTimingService(self.settings).apply(
                order,
                delivery_promise,
            )

            dish = self.db.get(DishEntity, row.dish_id)
            self.db.add(
                OrderItemEntity(
                    order_id=order.id,
                    daily_menu_item_id=None,
                    dish_id=row.dish_id,
                    dish_name=dish.name,
                    unit_price_minor=row.final_unit_price_minor,
                    quantity=row.quantity,
                    line_total_minor=row.final_total_minor,
                )
            )
            self.db.add(
                OrderStatusEventEntity(
                    order_id=order.id,
                    from_status=None,
                    to_status="pending_payment",
                    actor_user_id=customer_id,
                    reason="special_order_checkout_started",
                )
            )

            if default_address is not None:
                self.db.add(
                    OrderDeliveryAddressEntity(
                        order_id=order.id,
                        source_address_id=default_address.id,
                        label=default_address.label,
                        area=default_address.area,
                        street=default_address.street,
                        building=default_address.building,
                        floor=default_address.floor,
                        apartment=default_address.apartment,
                        latitude=default_address.latitude,
                        longitude=default_address.longitude,
                    )
                )

            row.order_id = order.id
            self.audit.add(
                action="customer.special_order.checkout_created",
                actor_user_id=customer_id,
                entity_type="order",
                entity_id=str(order.id),
                request_id=request_id,
                metadata={"special_order_id": str(row.id)},
            )
            self.db.commit()

        payment = PaymentService(self.db, self.settings).create_payment_intent(
            customer_id=customer_id,
            order_id=order.id,
            payload=CreatePaymentIntentRequest(
                idempotency_key=payload.idempotency_key
            ),
            request_id=request_id,
        )
        order_response = OrderService(self.db, self.settings).order_detail(
            customer_id=customer_id,
            order_id=order.id,
        )
        row = self.db.get(SpecialOrderRequestEntity, row.id)
        return SpecialOrderCheckoutResponse(
            special_order=self._response(row),
            order=order_response,
            payment=payment,
        )

    # ------------------------------------------------------------------
    # Expiry / helpers
    # ------------------------------------------------------------------
    def expire_due_requests(self) -> int:
        now = utc_now()
        rows = list(
            self.db.scalars(
                select(SpecialOrderRequestEntity).where(
                    SpecialOrderRequestEntity.status == "awaiting_payment",
                    SpecialOrderRequestEntity.offer_expires_at.is_not(None),
                    SpecialOrderRequestEntity.offer_expires_at <= now,
                )
            ).all()
        )
        if not rows:
            return 0
        for row in rows:
            self._expire_one(row)
        self.db.commit()
        return len(rows)

    def _expire_one(self, row: SpecialOrderRequestEntity) -> None:
        old = row.status
        row.status = "expired"
        if row.order_id is not None:
            order = self.db.get(OrderEntity, row.order_id)
            if order is not None and order.status == "pending_payment":
                order.status = "expired"
                self.db.add(
                    OrderStatusEventEntity(
                        order_id=order.id,
                        from_status="pending_payment",
                        to_status="expired",
                        reason="special_order_offer_expired",
                    )
                )
        self._event(
            row,
            from_status=old,
            to_status="expired",
            actor_user_id=None,
            reason="offer_expired",
        )

    def _validate_notice(
        self,
        *,
        service_date: date,
        prep_notice_hours: int,
    ) -> None:
        if service_date < date.today():
            raise ApiError(
                422,
                "special_order_date_in_past",
                "موعد الطلب الخاص يجب أن يكون في المستقبل.",
            )

        min_days = ceil(prep_notice_hours / 24) if prep_notice_hours else 0
        minimum_date = date.today() + timedelta(days=min_days)
        if service_date < minimum_date:
            raise ApiError(
                422,
                "special_order_prep_notice",
                "الموعد المطلوب لا يحقق مدة التحضير المطلوبة للطبق.",
                {
                    "prep_notice_hours": prep_notice_hours,
                    "earliest_service_date": minimum_date.isoformat(),
                },
            )

        maximum_date = date.today() + timedelta(
            days=self.settings.special_order_max_days_ahead
        )
        if service_date > maximum_date:
            raise ApiError(
                422,
                "special_order_date_too_far",
                "الموعد أبعد من فترة الحجز المسموحة حاليًا.",
                {"latest_service_date": maximum_date.isoformat()},
            )

    def _ensure_schedulable(
        self,
        *,
        chef_id: UUID,
        service_date: date,
        requested_start: str | None,
        requested_end: str | None,
        exclude_request_id: UUID | None = None,
    ) -> AvailabilityDayResponse:
        availability = self._availability_for_date(
            chef_id=chef_id,
            service_date=service_date,
            exclude_request_id=exclude_request_id,
        )
        if not availability.is_available:
            raise ApiError(
                409,
                "chef_not_available_for_date",
                "الشيف غير متاحة لهذا الموعد أو السعة اكتملت.",
            )

        if requested_start and availability.delivery_window_start:
            if requested_start < availability.delivery_window_start:
                raise ApiError(
                    422,
                    "requested_window_outside_schedule",
                    "بداية نافذة التوصيل خارج مواعيد الشيف.",
                )
        if requested_end and availability.delivery_window_end:
            if requested_end > availability.delivery_window_end:
                raise ApiError(
                    422,
                    "requested_window_outside_schedule",
                    "نهاية نافذة التوصيل خارج مواعيد الشيف.",
                )
        return availability

    def _active_chef(self, chef_id: UUID) -> ChefProfileEntity:
        chef = self.db.get(ChefProfileEntity, chef_id)
        if chef is None or chef.status != "active" or not chef.is_verified:
            raise ApiError(404, "chef_not_found", "الشيف غير موجود.")
        return chef

    def _customer_request(
        self,
        *,
        customer_id: UUID,
        special_order_id: UUID,
    ) -> SpecialOrderRequestEntity:
        row = self.db.get(SpecialOrderRequestEntity, special_order_id)
        if row is None or row.customer_id != customer_id:
            raise ApiError(
                404,
                "special_order_not_found",
                "الطلب الخاص غير موجود.",
            )
        return row

    def _chef_request(
        self,
        *,
        chef_id: UUID,
        special_order_id: UUID,
    ) -> SpecialOrderRequestEntity:
        row = self.db.get(SpecialOrderRequestEntity, special_order_id)
        if row is None or row.chef_id != chef_id:
            raise ApiError(
                404,
                "special_order_not_found",
                "الطلب الخاص غير موجود.",
            )
        return row

    def _event(
        self,
        row: SpecialOrderRequestEntity,
        *,
        from_status: str | None,
        to_status: str,
        actor_user_id: UUID | None,
        reason: str | None,
        data: dict | None = None,
    ) -> None:
        self.db.add(
            SpecialOrderEventEntity(
                special_order_id=row.id,
                from_status=from_status,
                to_status=to_status,
                actor_user_id=actor_user_id,
                reason=reason,
                data_json=data or {},
            )
        )

    def _response(
        self,
        row: SpecialOrderRequestEntity,
    ) -> SpecialOrderResponse:
        dish = self.db.get(DishEntity, row.dish_id)
        events = list(
            self.db.scalars(
                select(SpecialOrderEventEntity)
                .where(SpecialOrderEventEntity.special_order_id == row.id)
                .order_by(SpecialOrderEventEntity.created_at.asc())
            ).all()
        )
        return SpecialOrderResponse(
            id=row.id,
            customer_id=row.customer_id,
            chef_id=row.chef_id,
            dish_id=row.dish_id,
            dish_name=dish.name if dish else "طبق",
            order_id=row.order_id,
            request_type=row.request_type,
            status=row.status,
            quantity=row.quantity,
            requested_service_date=row.requested_service_date,
            requested_window_start=row.requested_window_start,
            requested_window_end=row.requested_window_end,
            requested_unit_price_minor=row.requested_unit_price_minor,
            proposed_service_date=row.proposed_service_date,
            proposed_window_start=row.proposed_window_start,
            proposed_window_end=row.proposed_window_end,
            proposed_unit_price_minor=row.proposed_unit_price_minor,
            final_service_date=row.final_service_date,
            final_window_start=row.final_window_start,
            final_window_end=row.final_window_end,
            final_unit_price_minor=row.final_unit_price_minor,
            final_total_minor=row.final_total_minor,
            customer_note=row.customer_note,
            chef_note=row.chef_note,
            rejection_reason=row.rejection_reason,
            offer_expires_at=row.offer_expires_at,
            chef_responded_at=row.chef_responded_at,
            customer_accepted_at=row.customer_accepted_at,
            scheduled_at=row.scheduled_at,
            cancelled_at=row.cancelled_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            events=[
                SpecialOrderEventResponse(
                    from_status=x.from_status,
                    to_status=x.to_status,
                    reason=x.reason,
                    data_json=x.data_json,
                    created_at=x.created_at,
                )
                for x in events
            ],
        )
