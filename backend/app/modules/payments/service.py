from __future__ import annotations

import json
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    ChefOrderFulfillmentEntity,
    CustomerProfileEntity,
    OrderDeliveryAddressEntity,
    OrderItemEntity,
    OrderStatusEventEntity,
    PaymentEntity,
    UserEntity,
    PaymentWebhookEventEntity,
    RefundEntity,
    SpecialOrderEventEntity,
    SpecialOrderRequestEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import ensure_utc, utc_now
from app.modules.orders.repository import OrderRepository
from app.modules.notifications.service import NotificationService
from app.modules.reliability.outbox import OutboxService
from app.modules.pricing.service import PricingService
from app.modules.payments.provider import (
    PaymentProvider,
    ProviderBillingData,
    ProviderLineItem,
    ProviderPaymentContext,
    get_provider,
)
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.schemas import (
    CreatePaymentIntentRequest,
    PaymentResponse,
    PaymentWebhookRequest,
    RefundCreateRequest,
    RefundResponse,
)


class PaymentService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.provider: PaymentProvider = get_provider(
            settings.payment_provider,
            settings,
        )
        self.repo = PaymentRepository(db)
        self.orders = OrderRepository(db)
        self.audit = AuditRepository(db)

    def create_payment_intent(
        self,
        *,
        customer_id: UUID,
        order_id: UUID,
        payload: CreatePaymentIntentRequest,
        request_id: str | None,
    ) -> PaymentResponse:
        order = self.orders.order(order_id)

        if order is None or order.customer_id != customer_id:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        if order.status != "pending_payment":
            raise ApiError(
                409,
                "order_not_pending_payment",
                "لا يمكن إنشاء عملية دفع لهذا الطلب في حالته الحالية.",
            )

        if order.order_type == "special":
            special = self.db.scalar(
                select(SpecialOrderRequestEntity).where(
                    SpecialOrderRequestEntity.order_id == order.id
                )
            )
            if special is None or special.status != "awaiting_payment":
                raise ApiError(
                    409,
                    "special_order_not_awaiting_payment",
                    "الطلب الخاص غير جاهز للدفع.",
                )
            if (
                special.offer_expires_at is None
                or ensure_utc(special.offer_expires_at) <= utc_now()
            ):
                raise ApiError(
                    409,
                    "special_order_offer_expired",
                    "انتهت مهلة دفع العرض.",
                )
            payment_deadline = ensure_utc(special.offer_expires_at)
        else:
            if order.inventory_hold_expires_at is None:
                raise ApiError(
                    409,
                    "inventory_hold_missing",
                    "حجز المخزون غير موجود لهذا الطلب.",
                )
            if ensure_utc(order.inventory_hold_expires_at) <= utc_now():
                raise ApiError(
                    409,
                    "inventory_hold_expired",
                    "انتهت مهلة حجز المخزون.",
                )
            payment_deadline = ensure_utc(order.inventory_hold_expires_at)

        existing = self.repo.payment_by_idempotency_key(payload.idempotency_key)
        if existing is not None:
            if existing.order_id != order.id or existing.customer_id != customer_id:
                raise ApiError(
                    409,
                    "payment_idempotency_conflict",
                    "مفتاح العملية مستخدم لطلب آخر.",
                )
            return PaymentResponse.model_validate(existing)

        payment = PaymentEntity(
            order_id=order.id,
            customer_id=customer_id,
            provider=self.provider.name,
            idempotency_key=payload.idempotency_key,
            amount_minor=order.total_minor,
            refunded_minor=0,
            currency=order.currency,
            status="pending",
            expires_at=min(
                payment_deadline,
                utc_now()
                + timedelta(minutes=self.settings.payment_intent_ttl_minutes),
            ),
        )
        self.db.add(payment)
        self.db.flush()

        provider_intent = self.provider.create_intent(
            payment_id=payment.id,
            amount_minor=payment.amount_minor,
            currency=payment.currency,
            idempotency_key=payload.idempotency_key,
            context=self._provider_payment_context(
                order=order,
                payment=payment,
            ),
        )
        payment.provider_reference = provider_intent.reference
        payment.provider_order_reference = provider_intent.provider_order_reference
        payment.provider_status = provider_intent.provider_status
        payment.provider_last_seen_at = utc_now()
        payment.checkout_url = provider_intent.checkout_url

        # Local-device development convenience:
        # The mock provider's checkout URL (mock-payments.local) is intentionally
        # non-routable. When this development machine explicitly exposes the API
        # to a LAN host (for example an iPhone on 192.168.x.x), complete mock
        # payments inside the backend so the end-to-end mobile flow can be tested.
        # Tests/default localhost development and all staging/production providers
        # keep the original webhook-driven behavior.
        allowed_hosts = {
            host.strip().lower()
            for host in self.settings.allowed_hosts.split(",")
            if host.strip()
        }
        has_lan_host = any(
            host not in {"localhost", "127.0.0.1", "testserver", "::1"}
            for host in allowed_hosts
        )
        if (
            self.provider.name == "mock"
            and self.settings.env.strip().lower() == "development"
            and has_lan_host
        ):
            payment.checkout_url = None
            self._apply_payment_success(
                payment,
                request_id=request_id,
            )

        self.audit.add(
            action="payment.intent.created",
            actor_user_id=customer_id,
            entity_type="payment",
            entity_id=str(payment.id),
            request_id=request_id,
            metadata={
                "order_id": str(order.id),
                "provider": payment.provider,
                "amount_minor": payment.amount_minor,
            },
        )
        self.db.commit()
        self.db.refresh(payment)
        return PaymentResponse.model_validate(payment)


    def _provider_payment_context(
        self,
        *,
        order,
        payment: PaymentEntity,
    ) -> ProviderPaymentContext:
        user = self.db.get(UserEntity, payment.customer_id)
        profile = self.db.get(CustomerProfileEntity, payment.customer_id)
        address = self.db.get(OrderDeliveryAddressEntity, order.id)
        order_items = list(
            self.db.scalars(
                select(OrderItemEntity)
                .where(OrderItemEntity.order_id == order.id)
                .order_by(OrderItemEntity.id.asc())
            ).all()
        )

        display_name = (
            profile.display_name.strip()
            if profile is not None and profile.display_name
            else "Baytna Customer"
        )
        parts = [x for x in display_name.split(" ") if x]
        first_name = parts[0] if parts else "Baytna"
        last_name = " ".join(parts[1:]) if len(parts) > 1 else "Customer"

        phone = user.phone if user is not None else "+200000000000"
        # User email is not a persisted field yet. Paymob requires a billing
        # email, so use a non-deliverable merchant-domain placeholder rather
        # than inventing customer personal data.
        email = f"customer-{payment.customer_id}@payments.baytna.invalid"

        billing = ProviderBillingData(
            first_name=first_name[:120],
            last_name=last_name[:120],
            phone_number=phone,
            email=email,
            country="EG",
            city=(address.area if address else "6 October") or "6 October",
            street=(address.street if address else None) or "N/A",
            building=(address.building if address else None) or "N/A",
            floor=(address.floor if address else None) or "N/A",
            apartment=(address.apartment if address else None) or "N/A",
            state="Giza",
        )

        items = [
            ProviderLineItem(
                name=item.dish_name,
                description=f"Baytna order item {item.id}",
                amount_minor=item.unit_price_minor,
                quantity=item.quantity,
            )
            for item in order_items
        ]

        return ProviderPaymentContext(
            order_id=order.id,
            customer_id=payment.customer_id,
            billing_data=billing,
            items=items,
            notification_url=self.settings.paymob_notification_url,
            redirection_url=self.settings.paymob_redirection_url,
        )

    def payment_for_order(
        self,
        *,
        customer_id: UUID,
        order_id: UUID,
    ) -> PaymentResponse:
        order = self.orders.order(order_id)
        if order is None or order.customer_id != customer_id:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        payment = self.repo.latest_payment_for_order(order.id)
        if payment is None:
            raise ApiError(404, "payment_not_found", "لا توجد عملية دفع لهذا الطلب.")

        return PaymentResponse.model_validate(payment)

    def process_webhook(
        self,
        *,
        provider: str,
        payload: PaymentWebhookRequest,
        payload_dict: dict,
        payload_hash: str,
        request_id: str | None,
    ) -> dict:
        if provider != self.provider.name:
            raise ApiError(404, "payment_provider_unknown", "مزود الدفع غير معروف.")

        existing_event = self.repo.webhook_event(provider, payload.event_id)
        if existing_event is not None:
            return {
                "status": existing_event.processing_status,
                "duplicate": True,
            }

        event = PaymentWebhookEventEntity(
            provider=provider,
            provider_event_id=payload.event_id,
            event_type=payload.event_type,
            provider_reference=payload.payment_reference,
            payload_hash=payload_hash,
            payload_json=payload_dict,
            processing_status="received",
        )
        self.db.add(event)
        self.db.flush()

        payment = self.repo.payment_by_reference(provider, payload.payment_reference)
        if payment is None:
            event.processing_status = "ignored"
            event.processed_at = utc_now()
            self.audit.add(
                action="payment.webhook.ignored",
                entity_type="payment_webhook_event",
                entity_id=str(event.id),
                request_id=request_id,
                metadata={"reason": "payment_reference_not_found"},
            )
            self.db.commit()
            return {"status": "ignored", "duplicate": False}

        if payload.amount_minor is not None and payload.amount_minor != payment.amount_minor:
            event.processing_status = "failed"
            event.processed_at = utc_now()
            self.db.commit()
            raise ApiError(
                400,
                "payment_amount_mismatch",
                "قيمة الدفع لا تطابق قيمة الطلب.",
            )

        if payload.currency is not None and payload.currency.upper() != payment.currency:
            event.processing_status = "failed"
            event.processed_at = utc_now()
            self.db.commit()
            raise ApiError(
                400,
                "payment_currency_mismatch",
                "عملة الدفع لا تطابق عملة الطلب.",
            )

        if payload.event_type == "payment.succeeded":
            self._apply_payment_success(payment, request_id=request_id)
            event.processing_status = "processed"

        elif payload.event_type in {"payment.failed", "payment.cancelled"}:
            self._apply_payment_failure(
                payment,
                cancelled=payload.event_type == "payment.cancelled",
                request_id=request_id,
            )
            event.processing_status = "processed"

        else:
            event.processing_status = "ignored"

        event.processed_at = utc_now()
        self.db.commit()

        return {
            "status": event.processing_status,
            "duplicate": False,
        }

    def _apply_payment_success(
        self,
        payment: PaymentEntity,
        *,
        request_id: str | None,
    ) -> None:
        if payment.status == "succeeded":
            return

        order = self.orders.order(payment.order_id)
        if order is None:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        if order.status != "pending_payment":
            raise ApiError(
                409,
                "order_not_pending_payment",
                "الطلب لم يعد في حالة انتظار الدفع.",
            )

        now = utc_now()
        if order.order_type == "special":
            special = self.db.scalar(
                select(SpecialOrderRequestEntity).where(
                    SpecialOrderRequestEntity.order_id == order.id
                )
            )
            if special is None or special.status != "awaiting_payment":
                raise ApiError(
                    409,
                    "special_order_not_awaiting_payment",
                    "الطلب الخاص لم يعد في انتظار الدفع.",
                )
            if (
                special.offer_expires_at is None
                or ensure_utc(special.offer_expires_at) <= now
            ):
                raise ApiError(
                    409,
                    "special_order_offer_expired",
                    "انتهت مهلة دفع العرض.",
                )
            active = []
        else:
            reservations = self.repo.reservations_for_order(order.id)
            active = [x for x in reservations if x.status == "active"]

            if not active:
                raise ApiError(
                    409,
                    "inventory_hold_not_active",
                    "حجز المخزون لم يعد فعالًا.",
                )

            for reservation in active:
                if ensure_utc(reservation.expires_at) <= now:
                    raise ApiError(
                        409,
                        "inventory_hold_expired",
                        "انتهت مهلة حجز المخزون قبل تأكيد الدفع.",
                    )

            PricingService(self.db, self.settings).apply_for_paid_order(
                order_id=order.id,
                request_id=request_id,
            )

        payment.status = "succeeded"
        payment.succeeded_at = now

        for reservation in active:
            reservation.status = "converted"
            reservation.converted_at = now

        old_status = order.status
        if order.order_type == "special":
            order.status = "accepted_by_chef"
            target_status = "accepted_by_chef"
            event_reason = "special_order_payment_succeeded"
            special.status = "scheduled"
            special.scheduled_at = now
            self.db.add(
                SpecialOrderEventEntity(
                    special_order_id=special.id,
                    from_status="awaiting_payment",
                    to_status="scheduled",
                    actor_user_id=payment.customer_id,
                    reason="payment_succeeded",
                )
            )
            fulfillment = self.db.get(ChefOrderFulfillmentEntity, order.id)
            if fulfillment is None:
                self.db.add(
                    ChefOrderFulfillmentEntity(
                        order_id=order.id,
                        chef_id=order.chef_id,
                        stage="accepted",
                        acceptance_deadline_at=None,
                        accepted_at=now,
                    )
                )
        else:
            order.status = "confirmed"
            target_status = "confirmed"
            event_reason = "payment_succeeded"
            order.inventory_hold_expires_at = None

        self.db.add(
            OrderStatusEventEntity(
                order_id=order.id,
                from_status=old_status,
                to_status=target_status,
                reason=event_reason,
            )
        )

        self.audit.add(
            action="payment.succeeded",
            actor_user_id=payment.customer_id,
            entity_type="payment",
            entity_id=str(payment.id),
            request_id=request_id,
            metadata={"order_id": str(order.id)},
        )
        OutboxService(self.db, self.settings).enqueue(
            event_type="payment.succeeded",
            aggregate_type="payment",
            aggregate_id=payment.id,
            dedupe_key=f"payment.succeeded:{payment.id}",
            payload={
                "payment_id": str(payment.id),
                "order_id": str(order.id),
                "customer_id": str(payment.customer_id),
                "amount_minor": payment.amount_minor,
                "currency": payment.currency,
                "order_type": order.order_type,
            },
        )
        OutboxService(self.db, self.settings).enqueue(
            event_type=(
                "special_order.scheduled"
                if order.order_type == "special"
                else "order.confirmed"
            ),
            aggregate_type="order",
            aggregate_id=order.id,
            dedupe_key=(
                f"special_order.scheduled:{order.id}"
                if order.order_type == "special"
                else f"order.confirmed:{order.id}"
            ),
            payload={
                "order_id": str(order.id),
                "customer_id": str(order.customer_id),
                "chef_id": str(order.chef_id),
                "service_date": order.service_date.isoformat(),
            },
        )
        if order.order_type == "special":
            NotificationService(self.db, self.settings).emit(
                user_id=payment.customer_id,
                kind="special_order_scheduled",
                title="تم جدولة طلبك الخاص",
                body="تم الدفع وتأكيد الطلب الخاص في الموعد المتفق عليه.",
                dedupe_key=f"special-order-scheduled:{order.id}",
                action_url=f"/orders/{order.id}",
                data_json={"order_id": str(order.id)},
            )
        else:
            NotificationService(self.db, self.settings).emit(
                user_id=payment.customer_id,
                kind="order_confirmed",
                title="تم تأكيد طلبك",
                body="تم الدفع بنجاح وطلبك دلوقتي في انتظار تأكيد الشيف.",
                dedupe_key=f"order-confirmed:{order.id}",
                action_url=f"/orders/{order.id}",
                data_json={"order_id": str(order.id)},
            )

    def _apply_payment_failure(
        self,
        payment: PaymentEntity,
        *,
        cancelled: bool,
        request_id: str | None,
    ) -> None:
        if payment.status in {"failed", "cancelled"}:
            return
        if payment.status == "succeeded":
            # Never downgrade a succeeded payment.
            return

        order = self.orders.order(payment.order_id)
        if order is None:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        payment.status = "cancelled" if cancelled else "failed"
        payment.failed_at = utc_now()

        if order.status == "pending_payment" and order.order_type != "special":
            for reservation in self.orders.active_reservations_for_order(order.id):
                self.orders.release_inventory(
                    daily_menu_item_id=reservation.daily_menu_item_id,
                    quantity=reservation.quantity,
                )
                reservation.status = "released"
                reservation.released_at = utc_now()

            PricingService(self.db, self.settings).release_for_unpaid_order(
                order_id=order.id,
                reason="payment_cancelled" if cancelled else "payment_failed",
                request_id=request_id,
            )

            old_status = order.status
            order.status = "expired"
            order.inventory_hold_expires_at = None
            self.db.add(
                OrderStatusEventEntity(
                    order_id=order.id,
                    from_status=old_status,
                    to_status="expired",
                    reason="payment_cancelled" if cancelled else "payment_failed",
                )
            )

        self.audit.add(
            action="payment.cancelled" if cancelled else "payment.failed",
            actor_user_id=payment.customer_id,
            entity_type="payment",
            entity_id=str(payment.id),
            request_id=request_id,
            metadata={"order_id": str(order.id)},
        )

    def create_refund(
        self,
        *,
        admin_user_id: UUID,
        order_id: UUID,
        payload: RefundCreateRequest,
        request_id: str | None,
        commit: bool = True,
    ) -> RefundResponse:
        order = self.orders.order(order_id)
        if order is None:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        if order.status != "confirmed":
            raise ApiError(
                409,
                "refund_order_not_confirmed",
                "لا يمكن تنفيذ استرداد إلا لطلب مؤكد.",
            )

        payment = self.repo.succeeded_payment_for_order(order.id)
        if payment is None:
            raise ApiError(
                409,
                "refund_payment_not_found",
                "لا توجد عملية دفع ناجحة لهذا الطلب.",
            )

        existing = self.repo.refund_by_idempotency(
            payment.id,
            payload.idempotency_key,
        )
        if existing is not None:
            return RefundResponse.model_validate(existing)

        remaining = payment.amount_minor - payment.refunded_minor
        if payload.amount_minor > remaining:
            raise ApiError(
                422,
                "refund_exceeds_remaining",
                "قيمة الاسترداد تتجاوز المبلغ المتبقي القابل للاسترداد.",
                {"remaining_refundable_minor": remaining},
            )

        refund = RefundEntity(
            order_id=order.id,
            payment_id=payment.id,
            requested_by_user_id=admin_user_id,
            amount_minor=payload.amount_minor,
            reason=payload.reason,
            idempotency_key=payload.idempotency_key,
            status="pending",
        )
        self.db.add(refund)
        self.db.flush()

        provider_payment_reference = (
            payment.provider_transaction_reference
            if payment.provider == "paymob"
            else payment.provider_reference
        )
        provider_refund = self.provider.refund(
            payment_reference=provider_payment_reference or "",
            amount_minor=payload.amount_minor,
            idempotency_key=payload.idempotency_key,
        )

        refund.provider_reference = provider_refund.reference or None
        refund.provider_status = provider_refund.provider_status
        refund.provider_error = provider_refund.error

        if provider_refund.succeeded:
            refund.status = "succeeded"
            refund.completed_at = utc_now()
            payment.refunded_minor += payload.amount_minor
        else:
            refund.status = "failed"
            refund.failed_at = utc_now()

        self.audit.add(
            action="refund.succeeded" if refund.status == "succeeded" else "refund.failed",
            actor_user_id=admin_user_id,
            entity_type="refund",
            entity_id=str(refund.id),
            request_id=request_id,
            metadata={
                "order_id": str(order.id),
                "payment_id": str(payment.id),
                "amount_minor": payload.amount_minor,
            },
        )
        if commit:
            self.db.commit()
            self.db.refresh(refund)
        else:
            self.db.flush()
        return RefundResponse.model_validate(refund)

    def refunds_for_order(self, *, order_id: UUID) -> list[RefundResponse]:
        order = self.orders.order(order_id)
        if order is None:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        payment = self.repo.succeeded_payment_for_order(order.id)
        if payment is None:
            return []

        return [
            RefundResponse.model_validate(x)
            for x in self.repo.refunds_for_payment(payment.id)
        ]
