from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    ChefOrderFulfillmentEntity,
    DeliveryTaskEntity,
    OrderStatusEventEntity,
    SpecialOrderRequestEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import ensure_utc, utc_now
from app.modules.fulfillment.repository import FulfillmentRepository
from app.modules.fulfillment.schemas import (
    AcceptOrderRequest,
    ChefNoteRequest,
    ChefOrderDetailResponse,
    ChefOrderItemResponse,
    ChefOrderListItemResponse,
    CustomerTrackingResponse,
    RejectOrderRequest,
)
from app.modules.orders.repository import OrderRepository
from app.modules.notifications.service import NotificationService
from app.modules.reliability.outbox import OutboxService
from app.modules.payments.schemas import RefundCreateRequest
from app.modules.payments.service import PaymentService


CUSTOMER_STATUS = {
    "pending_payment": ("في انتظار الدفع", "أكمل الدفع لتأكيد الطلب."),
    "confirmed": ("تم تأكيد طلبك", "في انتظار تأكيد الشيف."),
    "accepted_by_chef": ("الشيف بدأت تجهيز أكلك", "تم قبول الطلب من الشيف."),
    "preparing": ("جاري الطبخ", "الشيف بتجهز طلبك دلوقتي."),
    "ready_for_pickup": ("أكلك جاهز", "في انتظار استلام المندوب."),
    "assigned_to_driver": ("المندوب في طريقه للشيف", "تم تعيين مندوب لاستلام الطلب."),
    "picked_up": ("المندوب استلم الطلب", "تم استلام الطلب من الشيف."),
    "out_for_delivery": ("طلبك في الطريق", "المندوب متجه إلى عنوان التوصيل."),
    "delivered": ("تم توصيل طلبك", "تم تسليم الطلب بنجاح."),
    "cancelled": ("تم إلغاء الطلب", None),
    "expired": ("انتهت مهلة الطلب", None),
}


class FulfillmentService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repo = FulfillmentRepository(db)
        self.orders = OrderRepository(db)
        self.audit = AuditRepository(db)

    # --------------------------------------------------------------
    # Fulfillment creation / synchronization
    # --------------------------------------------------------------
    def ensure_for_confirmed_order(
        self,
        *,
        order_id: UUID,
    ) -> ChefOrderFulfillmentEntity:
        order = self.repo.order(order_id)
        if order is None:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        existing = self.repo.fulfillment(order.id)
        if existing is not None:
            return existing

        if order.status not in {
            "confirmed",
            "accepted_by_chef",
            "preparing",
            "ready_for_pickup",
        }:
            raise ApiError(
                409,
                "fulfillment_not_available",
                "الطلب غير جاهز لمسار تجهيز الشيف.",
            )

        confirmed_event = None
        events = self.orders.order_events(order.id)
        for event in reversed(events):
            if event.to_status == "confirmed":
                confirmed_event = event
                break

        base = confirmed_event.created_at if confirmed_event else order.updated_at
        deadline = ensure_utc(base) + timedelta(
            minutes=self.settings.chef_acceptance_sla_minutes
        )

        stage = {
            "confirmed": "new",
            "accepted_by_chef": "accepted",
            "preparing": "preparing",
            "ready_for_pickup": "ready",
        }[order.status]

        row = self.repo.create_fulfillment(
            order_id=order.id,
            chef_id=order.chef_id,
            acceptance_deadline_at=deadline,
        )
        row.stage = stage
        self.db.flush()
        return row

    def sync_queue(self, *, chef_id: UUID) -> None:
        # Confirmed orders are the source of truth. Lazily backfill fulfillment rows.
        from app.core.db_models import OrderEntity
        from sqlalchemy import select

        orders = list(
            self.db.scalars(
                select(OrderEntity).where(
                    OrderEntity.chef_id == chef_id,
                    OrderEntity.status.in_(
                        [
                            "confirmed",
                            "accepted_by_chef",
                            "preparing",
                            "ready_for_pickup",
                        ]
                    ),
                )
            ).all()
        )

        created = False
        for order in orders:
            if self.repo.fulfillment(order.id) is None:
                self.ensure_for_confirmed_order(order_id=order.id)
                created = True

        if created:
            self.db.commit()

    # --------------------------------------------------------------
    # Read models
    # --------------------------------------------------------------
    def queue(
        self,
        *,
        chef_id: UUID,
        stage: str | None,
    ) -> list[ChefOrderListItemResponse]:
        self.sync_queue(chef_id=chef_id)
        rows = self.repo.queue(chef_id=chef_id, stage=stage)
        return [
            ChefOrderListItemResponse(
                order_id=order.id,
                customer_id=order.customer_id,
                service_date=order.service_date,
                order_status=order.status,
                fulfillment_stage=fulfillment.stage,
                total_minor=order.total_minor,
                currency=order.currency,
                acceptance_deadline_at=fulfillment.acceptance_deadline_at,
                estimated_ready_at=fulfillment.estimated_ready_at,
                created_at=order.created_at,
            )
            for order, fulfillment in rows
        ]

    def detail(
        self,
        *,
        chef_id: UUID,
        order_id: UUID,
    ) -> ChefOrderDetailResponse:
        order = self.repo.order_for_chef(
            order_id=order_id,
            chef_id=chef_id,
        )
        if order is None:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        fulfillment = self.repo.fulfillment(order.id)
        if fulfillment is None:
            fulfillment = self.ensure_for_confirmed_order(order_id=order.id)
            self.db.commit()

        return self._detail(order, fulfillment)

    def _detail(
        self,
        order,
        fulfillment: ChefOrderFulfillmentEntity,
    ) -> ChefOrderDetailResponse:
        items = [
            ChefOrderItemResponse(
                dish_id=x.dish_id,
                dish_name=x.dish_name,
                quantity=x.quantity,
                unit_price_minor=x.unit_price_minor,
                line_total_minor=x.line_total_minor,
            )
            for x in self.repo.items(order.id)
        ]
        return ChefOrderDetailResponse(
            order_id=order.id,
            customer_id=order.customer_id,
            chef_id=order.chef_id,
            service_date=order.service_date,
            order_status=order.status,
            fulfillment_stage=fulfillment.stage,
            subtotal_minor=order.subtotal_minor,
            total_minor=order.total_minor,
            currency=order.currency,
            acceptance_deadline_at=fulfillment.acceptance_deadline_at,
            estimated_ready_at=fulfillment.estimated_ready_at,
            accepted_at=fulfillment.accepted_at,
            preparation_started_at=fulfillment.preparation_started_at,
            packaging_started_at=fulfillment.packaging_started_at,
            ready_at=fulfillment.ready_at,
            rejected_at=fulfillment.rejected_at,
            rejection_reason=fulfillment.rejection_reason,
            chef_note=fulfillment.chef_note,
            items=items,
            created_at=order.created_at,
        )

    # --------------------------------------------------------------
    # State transitions
    # --------------------------------------------------------------
    def accept(
        self,
        *,
        chef_id: UUID,
        order_id: UUID,
        payload: AcceptOrderRequest,
        request_id: str | None,
    ) -> ChefOrderDetailResponse:
        order = self.repo.order_for_chef(order_id=order_id, chef_id=chef_id)
        if order is None:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        fulfillment = self.repo.fulfillment(order.id)
        if fulfillment is None:
            fulfillment = self.ensure_for_confirmed_order(order_id=order.id)

        if order.status == "accepted_by_chef" and fulfillment.stage == "accepted":
            return self._detail(order, fulfillment)

        if order.status != "confirmed" or fulfillment.stage != "new":
            raise ApiError(
                409,
                "order_cannot_accept",
                "لا يمكن قبول الطلب في حالته الحالية.",
            )

        if payload.estimated_ready_at is not None:
            if ensure_utc(payload.estimated_ready_at) <= utc_now():
                raise ApiError(
                    422,
                    "estimated_ready_must_be_future",
                    "وقت الجاهزية المتوقع يجب أن يكون في المستقبل.",
                )

        if not self.repo.transition_order(
            order_id=order.id,
            expected_status="confirmed",
            new_status="accepted_by_chef",
        ):
            self.db.rollback()
            raise ApiError(
                409,
                "order_state_changed",
                "تغيرت حالة الطلب، حدّث الصفحة وحاول مرة أخرى.",
            )

        fulfillment.stage = "accepted"
        fulfillment.accepted_at = utc_now()
        fulfillment.estimated_ready_at = payload.estimated_ready_at
        fulfillment.chef_note = payload.chef_note

        self.db.add(
            OrderStatusEventEntity(
                order_id=order.id,
                from_status="confirmed",
                to_status="accepted_by_chef",
                actor_user_id=chef_id,
                reason="chef_accepted",
            )
        )
        self.audit.add(
            action="chef.order.accepted",
            actor_user_id=chef_id,
            entity_type="order",
            entity_id=str(order.id),
            request_id=request_id,
            metadata={
                "estimated_ready_at": (
                    payload.estimated_ready_at.isoformat()
                    if payload.estimated_ready_at
                    else None
                ),
            },
        )
        NotificationService(self.db, self.settings).emit(
            user_id=order.customer_id,
            kind="chef_accepted",
            title="الشيف بدأت تجهيز أكلك",
            body="الشيف قبلت طلبك وبدأت التجهيز.",
            dedupe_key=f"chef-accepted:{order.id}",
            action_url=f"/orders/{order.id}/tracking",
            data_json={"order_id": str(order.id)},
        )
        self.db.commit()
        order = self.repo.order(order.id)
        self.db.refresh(fulfillment)
        return self._detail(order, fulfillment)

    def reject(
        self,
        *,
        chef_id: UUID,
        order_id: UUID,
        payload: RejectOrderRequest,
        request_id: str | None,
    ) -> ChefOrderDetailResponse:
        order = self.repo.order_for_chef(order_id=order_id, chef_id=chef_id)
        if order is None:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        fulfillment = self.repo.fulfillment(order.id)
        if fulfillment is None:
            fulfillment = self.ensure_for_confirmed_order(order_id=order.id)

        if order.status == "cancelled" and fulfillment.stage == "rejected":
            return self._detail(order, fulfillment)

        if order.status != "confirmed" or fulfillment.stage != "new":
            raise ApiError(
                409,
                "order_cannot_reject",
                "لا يمكن رفض الطلب بعد بدء التجهيز.",
            )

        # Paid confirmed orders are automatically fully refunded on chef rejection.
        payment_service = PaymentService(self.db, self.settings)
        payment = payment_service.repo.succeeded_payment_for_order(order.id)
        if payment is None:
            raise ApiError(
                409,
                "paid_order_payment_missing",
                "تعذر العثور على عملية الدفع الخاصة بالطلب.",
            )

        remaining = payment.amount_minor - payment.refunded_minor
        if remaining > 0:
            payment_service.create_refund(
                admin_user_id=chef_id,
                order_id=order.id,
                payload=RefundCreateRequest(
                    amount_minor=remaining,
                    reason=f"رفض الشيف: {payload.reason}",
                    idempotency_key=f"chef-reject-{order.id}",
                ),
                request_id=request_id,
                commit=False,
            )

        # Restore converted inventory because the paid order will not be fulfilled.
        for reservation in payment_service.repo.reservations_for_order(order.id):
            if reservation.status == "converted":
                self.orders.release_inventory(
                    daily_menu_item_id=reservation.daily_menu_item_id,
                    quantity=reservation.quantity,
                )
                reservation.status = "released"
                reservation.released_at = utc_now()

        if not self.repo.transition_order(
            order_id=order.id,
            expected_status="confirmed",
            new_status="cancelled",
        ):
            self.db.rollback()
            raise ApiError(
                409,
                "order_state_changed",
                "تغيرت حالة الطلب، حدّث الصفحة وحاول مرة أخرى.",
            )

        fulfillment.stage = "rejected"
        fulfillment.rejected_at = utc_now()
        fulfillment.rejection_reason = payload.reason

        self.db.add(
            OrderStatusEventEntity(
                order_id=order.id,
                from_status="confirmed",
                to_status="cancelled",
                actor_user_id=chef_id,
                reason="chef_rejected",
            )
        )
        self.audit.add(
            action="chef.order.rejected",
            actor_user_id=chef_id,
            entity_type="order",
            entity_id=str(order.id),
            request_id=request_id,
            metadata={
                "reason": payload.reason,
                "automatic_refund_minor": remaining,
            },
        )
        self.db.commit()

        order = self.repo.order(order.id)
        self.db.refresh(fulfillment)
        return self._detail(order, fulfillment)

    def start_preparing(
        self,
        *,
        chef_id: UUID,
        order_id: UUID,
        payload: ChefNoteRequest,
        request_id: str | None,
    ) -> ChefOrderDetailResponse:
        return self._progress(
            chef_id=chef_id,
            order_id=order_id,
            expected_order_status="accepted_by_chef",
            new_order_status="preparing",
            expected_stage="accepted",
            new_stage="preparing",
            timestamp_field="preparation_started_at",
            payload=payload,
            action="chef.order.preparing",
            reason="preparation_started",
            request_id=request_id,
        )

    def start_packaging(
        self,
        *,
        chef_id: UUID,
        order_id: UUID,
        payload: ChefNoteRequest,
        request_id: str | None,
    ) -> ChefOrderDetailResponse:
        order = self.repo.order_for_chef(order_id=order_id, chef_id=chef_id)
        if order is None:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")
        fulfillment = self.repo.fulfillment(order.id)

        if fulfillment is None:
            raise ApiError(409, "fulfillment_missing", "مسار التجهيز غير موجود.")

        if order.status != "preparing":
            raise ApiError(
                409,
                "order_not_preparing",
                "يجب أن يكون الطلب في مرحلة التحضير أولًا.",
            )

        if fulfillment.stage == "packaging":
            return self._detail(order, fulfillment)

        if fulfillment.stage != "preparing":
            raise ApiError(
                409,
                "order_cannot_package",
                "لا يمكن بدء التغليف في المرحلة الحالية.",
            )

        fulfillment.stage = "packaging"
        fulfillment.packaging_started_at = utc_now()
        if payload.chef_note is not None:
            fulfillment.chef_note = payload.chef_note

        self.db.add(
            OrderStatusEventEntity(
                order_id=order.id,
                from_status="preparing",
                to_status="preparing",
                actor_user_id=chef_id,
                reason="packaging_started",
            )
        )
        self.audit.add(
            action="chef.order.packaging",
            actor_user_id=chef_id,
            entity_type="order",
            entity_id=str(order.id),
            request_id=request_id,
        )
        self.db.commit()
        self.db.refresh(fulfillment)
        return self._detail(order, fulfillment)

    def ready_for_pickup(
        self,
        *,
        chef_id: UUID,
        order_id: UUID,
        payload: ChefNoteRequest,
        request_id: str | None,
    ) -> ChefOrderDetailResponse:
        order = self.repo.order_for_chef(order_id=order_id, chef_id=chef_id)
        if order is None:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")
        fulfillment = self.repo.fulfillment(order.id)

        if fulfillment is None:
            raise ApiError(409, "fulfillment_missing", "مسار التجهيز غير موجود.")

        if order.status == "ready_for_pickup" and fulfillment.stage == "ready":
            return self._detail(order, fulfillment)

        if order.status != "preparing" or fulfillment.stage not in {
            "preparing",
            "packaging",
        }:
            raise ApiError(
                409,
                "order_cannot_mark_ready",
                "لا يمكن اعتبار الطلب جاهزًا في المرحلة الحالية.",
            )

        if not self.repo.transition_order(
            order_id=order.id,
            expected_status="preparing",
            new_status="ready_for_pickup",
        ):
            self.db.rollback()
            raise ApiError(
                409,
                "order_state_changed",
                "تغيرت حالة الطلب، حدّث الصفحة وحاول مرة أخرى.",
            )

        fulfillment.stage = "ready"
        fulfillment.ready_at = utc_now()
        if payload.chef_note is not None:
            fulfillment.chef_note = payload.chef_note

        self.db.add(
            OrderStatusEventEntity(
                order_id=order.id,
                from_status="preparing",
                to_status="ready_for_pickup",
                actor_user_id=chef_id,
                reason="ready_for_pickup",
            )
        )
        self.audit.add(
            action="chef.order.ready_for_pickup",
            actor_user_id=chef_id,
            entity_type="order",
            entity_id=str(order.id),
            request_id=request_id,
        )
        NotificationService(self.db, self.settings).emit(
            user_id=order.customer_id,
            kind="order_ready",
            title="أكلك جاهز",
            body="الشيف خلصت تجهيز طلبك وفي انتظار استلام المندوب.",
            dedupe_key=f"order-ready:{order.id}",
            action_url=f"/orders/{order.id}/tracking",
            data_json={"order_id": str(order.id)},
        )
        OutboxService(self.db, self.settings).enqueue(
            event_type="order.ready_for_pickup",
            aggregate_type="order",
            aggregate_id=order.id,
            dedupe_key=f"order.ready_for_pickup:{order.id}",
            payload={
                "order_id": str(order.id),
                "customer_id": str(order.customer_id),
                "chef_id": str(order.chef_id),
            },
        )

        existing_delivery_task = self.db.scalar(
            select(DeliveryTaskEntity).where(
                DeliveryTaskEntity.order_id == order.id
            )
        )
        if existing_delivery_task is None:
            self.db.add(
                DeliveryTaskEntity(
                    order_id=order.id,
                    chef_id=order.chef_id,
                    status="unassigned",
                )
            )

        self.db.commit()
        order = self.repo.order(order.id)
        self.db.refresh(fulfillment)
        return self._detail(order, fulfillment)

    def _progress(
        self,
        *,
        chef_id: UUID,
        order_id: UUID,
        expected_order_status: str,
        new_order_status: str,
        expected_stage: str,
        new_stage: str,
        timestamp_field: str,
        payload: ChefNoteRequest,
        action: str,
        reason: str,
        request_id: str | None,
    ) -> ChefOrderDetailResponse:
        order = self.repo.order_for_chef(order_id=order_id, chef_id=chef_id)
        if order is None:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")
        fulfillment = self.repo.fulfillment(order.id)

        if fulfillment is None:
            raise ApiError(409, "fulfillment_missing", "مسار التجهيز غير موجود.")

        if order.status == new_order_status and fulfillment.stage == new_stage:
            return self._detail(order, fulfillment)

        if (
            order.status != expected_order_status
            or fulfillment.stage != expected_stage
        ):
            raise ApiError(
                409,
                "order_invalid_transition",
                "لا يمكن نقل الطلب إلى المرحلة المطلوبة من حالته الحالية.",
            )

        if not self.repo.transition_order(
            order_id=order.id,
            expected_status=expected_order_status,
            new_status=new_order_status,
        ):
            self.db.rollback()
            raise ApiError(
                409,
                "order_state_changed",
                "تغيرت حالة الطلب، حدّث الصفحة وحاول مرة أخرى.",
            )

        fulfillment.stage = new_stage
        setattr(fulfillment, timestamp_field, utc_now())
        if payload.chef_note is not None:
            fulfillment.chef_note = payload.chef_note

        self.db.add(
            OrderStatusEventEntity(
                order_id=order.id,
                from_status=expected_order_status,
                to_status=new_order_status,
                actor_user_id=chef_id,
                reason=reason,
            )
        )
        self.audit.add(
            action=action,
            actor_user_id=chef_id,
            entity_type="order",
            entity_id=str(order.id),
            request_id=request_id,
        )
        self.db.commit()
        order = self.repo.order(order.id)
        self.db.refresh(fulfillment)
        return self._detail(order, fulfillment)

    # --------------------------------------------------------------
    # Customer tracking
    # --------------------------------------------------------------
    def tracking(
        self,
        *,
        customer_id: UUID,
        order_id: UUID,
    ) -> CustomerTrackingResponse:
        order = self.repo.order(order_id)
        if order is None or order.customer_id != customer_id:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        fulfillment = self.repo.fulfillment(order.id)
        stage = fulfillment.stage if fulfillment else None

        special = None
        if order.order_type == "special":
            special = self.db.scalar(
                select(SpecialOrderRequestEntity).where(
                    SpecialOrderRequestEntity.order_id == order.id
                )
            )

        if (
            special is not None
            and special.status == "scheduled"
            and order.status == "accepted_by_chef"
        ):
            display = "تم جدولة طلبك الخاص"
            detail = "الشيف وافقت وتم تأكيد الموعد والدفع."
        elif order.status == "preparing" and stage == "packaging":
            display = "جاري التغليف"
            detail = "الشيف بتجهز الطلب للتسليم."
        else:
            display, detail = CUSTOMER_STATUS.get(
                order.status,
                ("جاري تحديث حالة الطلب", None),
            )

        updated_at = order.updated_at
        if fulfillment and ensure_utc(fulfillment.updated_at) > ensure_utc(updated_at):
            updated_at = fulfillment.updated_at

        return CustomerTrackingResponse(
            order_id=order.id,
            status=order.status,
            fulfillment_stage=stage,
            display_status=display,
            detail=detail,
            estimated_ready_at=(
                fulfillment.estimated_ready_at if fulfillment else None
            ),
            updated_at=updated_at,
        )
