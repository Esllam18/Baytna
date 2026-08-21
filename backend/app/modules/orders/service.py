from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    AddressEntity,
    CartItemEntity,
    OrderDeliveryAddressEntity,
    InventoryReservationEntity,
    OrderItemEntity,
    OrderStatusEventEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import ensure_utc, utc_now
from app.modules.orders.repository import OrderRepository
from app.modules.delivery_timing.service import DeliveryTimingService
from app.modules.launch_governance.service import LaunchTrafficGovernanceService
from app.modules.pricing.service import PricingService
from app.modules.orders.schemas import (
    AddCartItemRequest,
    CartLineResponse,
    CartResponse,
    CreateOrderRequest,
    OrderLineResponse,
    OrderListItemResponse,
    OrderPricingAdjustmentResponse,
    OrderResponse,
    OrderStatusEventResponse,
    UpdateCartItemRequest,
)


class OrderService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repo = OrderRepository(db)
        self.audit = AuditRepository(db)

    # ----------------------------------------------------------------
    # Inventory housekeeping
    # ----------------------------------------------------------------
    def release_expired_holds(self) -> int:
        now = utc_now()
        reservations = self.repo.expired_active_reservations(now)
        if not reservations:
            return 0

        released = 0
        touched_orders = set()

        for reservation in reservations:
            self.repo.release_inventory(
                daily_menu_item_id=reservation.daily_menu_item_id,
                quantity=reservation.quantity,
            )
            reservation.status = "expired"
            reservation.released_at = now
            touched_orders.add(reservation.order_id)
            released += 1

        for order_id in touched_orders:
            order = self.repo.order(order_id)
            if order is not None and order.status == "pending_payment":
                old_status = order.status
                order.status = "expired"
                order.inventory_hold_expires_at = None
                self.db.add(
                    OrderStatusEventEntity(
                        order_id=order.id,
                        from_status=old_status,
                        to_status="expired",
                        reason="inventory_hold_expired",
                    )
                )
                PricingService(self.db, self.settings).release_for_unpaid_order(
                    order_id=order.id,
                    reason="inventory_hold_expired",
                    request_id=None,
                )

        self.db.commit()
        return released

    # ----------------------------------------------------------------
    # Cart validation helpers
    # ----------------------------------------------------------------
    def _validated_menu_context(self, daily_menu_item_id: UUID):
        item = self.repo.daily_menu_item(daily_menu_item_id)
        if item is None:
            raise ApiError(
                404,
                "daily_menu_item_not_found",
                "الصنف غير موجود في مطبخ اليوم.",
            )

        workday = self.repo.workday(item.workday_id)
        if workday is None or workday.status != "open":
            raise ApiError(
                409,
                "kitchen_closed",
                "مطبخ الشيف غير مفتوح لهذا اليوم.",
            )

        if workday.cutoff_at is not None and ensure_utc(workday.cutoff_at) <= utc_now():
            raise ApiError(
                409,
                "kitchen_cutoff_passed",
                "انتهى وقت استقبال طلبات هذا اليوم.",
            )

        dish = self.repo.dish(item.dish_id)
        if dish is None or not dish.is_active:
            raise ApiError(
                409,
                "dish_unavailable",
                "الطبق غير متاح حاليًا.",
            )

        if item.status == "hidden":
            raise ApiError(
                409,
                "item_hidden",
                "الصنف غير متاح للطلب.",
            )

        return item, workday, dish

    def _validate_requested_quantity(self, *, item, quantity: int) -> None:
        if quantity > item.max_per_order:
            raise ApiError(
                422,
                "quantity_above_max_per_order",
                "الكمية تتجاوز الحد الأقصى المسموح لهذا الصنف.",
                {"max_per_order": item.max_per_order},
            )

        if item.status == "sold_out" or item.quantity_available <= 0:
            raise ApiError(
                409,
                "item_sold_out",
                "نفدت الكمية اليوم.",
            )

        if quantity > item.quantity_available:
            raise ApiError(
                409,
                "insufficient_inventory",
                "الكمية المطلوبة غير متاحة.",
                {"available": item.quantity_available},
            )

    # ----------------------------------------------------------------
    # Cart
    # ----------------------------------------------------------------
    def get_cart(self, *, customer_id: UUID) -> CartResponse:
        self.release_expired_holds()

        cart = self.repo.active_cart(customer_id)
        if cart is None:
            cart = self.repo.create_cart(customer_id)
            self.db.commit()

        return self._cart_response(cart)

    def add_cart_item(
        self,
        *,
        customer_id: UUID,
        payload: AddCartItemRequest,
        request_id: str | None,
    ) -> CartResponse:
        self.release_expired_holds()
        item, workday, dish = self._validated_menu_context(
            payload.daily_menu_item_id
        )

        cart = self.repo.active_cart(customer_id)
        if cart is None:
            cart = self.repo.create_cart(customer_id)

        if cart.chef_id is not None and cart.chef_id != workday.chef_id:
            raise ApiError(
                409,
                "cart_multiple_chefs_not_allowed",
                "يمكن أن يحتوي الطلب الواحد على أكلات من شيف واحد فقط.",
            )

        if cart.service_date is not None and cart.service_date != workday.service_date:
            raise ApiError(
                409,
                "cart_multiple_service_dates_not_allowed",
                "يمكن أن يحتوي الطلب الواحد على يوم توصيل واحد فقط.",
            )

        existing = self.repo.cart_item_by_menu_item(
            cart.id,
            payload.daily_menu_item_id,
        )
        final_quantity = payload.quantity + (existing.quantity if existing else 0)
        self._validate_requested_quantity(item=item, quantity=final_quantity)

        cart.chef_id = workday.chef_id
        cart.service_date = workday.service_date
        cart.updated_at = utc_now()

        if existing:
            existing.quantity = final_quantity
            existing.unit_price_minor = item.price_minor
        else:
            self.db.add(
                CartItemEntity(
                    cart_id=cart.id,
                    daily_menu_item_id=item.id,
                    quantity=payload.quantity,
                    unit_price_minor=item.price_minor,
                )
            )

        self.audit.add(
            action="customer.cart.item_added",
            actor_user_id=customer_id,
            entity_type="cart",
            entity_id=str(cart.id),
            request_id=request_id,
            metadata={
                "daily_menu_item_id": str(item.id),
                "quantity": payload.quantity,
            },
        )
        self.db.commit()
        return self._cart_response(cart)

    def update_cart_item(
        self,
        *,
        customer_id: UUID,
        cart_item_id: UUID,
        payload: UpdateCartItemRequest,
        request_id: str | None,
    ) -> CartResponse:
        self.release_expired_holds()
        cart = self.repo.active_cart(customer_id)
        if cart is None:
            raise ApiError(404, "cart_not_found", "السلة غير موجودة.")

        cart_item = self.repo.cart_item(cart_item_id)
        if cart_item is None or cart_item.cart_id != cart.id:
            raise ApiError(404, "cart_item_not_found", "الصنف غير موجود في السلة.")

        item, workday, _ = self._validated_menu_context(
            cart_item.daily_menu_item_id
        )
        self._validate_requested_quantity(
            item=item,
            quantity=payload.quantity,
        )

        if workday.chef_id != cart.chef_id or workday.service_date != cart.service_date:
            raise ApiError(409, "cart_context_changed", "بيانات السلة لم تعد صالحة.")

        cart_item.quantity = payload.quantity
        cart_item.unit_price_minor = item.price_minor
        cart.updated_at = utc_now()

        self.audit.add(
            action="customer.cart.item_updated",
            actor_user_id=customer_id,
            entity_type="cart_item",
            entity_id=str(cart_item.id),
            request_id=request_id,
            metadata={"quantity": payload.quantity},
        )
        self.db.commit()
        return self._cart_response(cart)

    def remove_cart_item(
        self,
        *,
        customer_id: UUID,
        cart_item_id: UUID,
        request_id: str | None,
    ) -> CartResponse:
        cart = self.repo.active_cart(customer_id)
        if cart is None:
            raise ApiError(404, "cart_not_found", "السلة غير موجودة.")

        cart_item = self.repo.cart_item(cart_item_id)
        if cart_item is None or cart_item.cart_id != cart.id:
            raise ApiError(404, "cart_item_not_found", "الصنف غير موجود في السلة.")

        self.db.delete(cart_item)
        self.db.flush()

        remaining = self.repo.cart_items(cart.id)
        if not remaining:
            cart.chef_id = None
            cart.service_date = None

        self.audit.add(
            action="customer.cart.item_removed",
            actor_user_id=customer_id,
            entity_type="cart_item",
            entity_id=str(cart_item_id),
            request_id=request_id,
        )
        self.db.commit()
        return self._cart_response(cart)

    def clear_cart(
        self,
        *,
        customer_id: UUID,
        request_id: str | None,
    ) -> CartResponse:
        cart = self.repo.active_cart(customer_id)
        if cart is None:
            cart = self.repo.create_cart(customer_id)
        else:
            self.db.execute(
                delete(CartItemEntity).where(CartItemEntity.cart_id == cart.id)
            )
            cart.chef_id = None
            cart.service_date = None
            cart.updated_at = utc_now()

        self.audit.add(
            action="customer.cart.cleared",
            actor_user_id=customer_id,
            entity_type="cart",
            entity_id=str(cart.id),
            request_id=request_id,
        )
        self.db.commit()
        return self._cart_response(cart)

    def _cart_response(self, cart) -> CartResponse:
        lines = []
        subtotal = 0

        for cart_item in self.repo.cart_items(cart.id):
            menu_item = self.repo.daily_menu_item(cart_item.daily_menu_item_id)
            if menu_item is None:
                continue
            dish = self.repo.dish(menu_item.dish_id)
            workday = self.repo.workday(menu_item.workday_id)
            if dish is None or workday is None:
                continue

            current_price = menu_item.price_minor
            line_total = current_price * cart_item.quantity
            subtotal += line_total
            label = (
                "نفدت الكمية اليوم"
                if menu_item.status == "sold_out" or menu_item.quantity_available == 0
                else ("غير متاح" if menu_item.status == "hidden" else "متاح اليوم")
            )

            lines.append(
                CartLineResponse(
                    id=cart_item.id,
                    daily_menu_item_id=menu_item.id,
                    dish_id=dish.id,
                    dish_name=dish.name,
                    chef_id=workday.chef_id,
                    unit_price_minor=current_price,
                    quantity=cart_item.quantity,
                    line_total_minor=line_total,
                    max_per_order=menu_item.max_per_order,
                    availability_label=label,
                )
            )

        return CartResponse(
            id=cart.id,
            customer_id=cart.customer_id,
            chef_id=cart.chef_id,
            service_date=cart.service_date,
            status=cart.status,
            subtotal_minor=subtotal,
            items=lines,
        )

    # ----------------------------------------------------------------
    # Order aggregate + inventory hold
    # ----------------------------------------------------------------
    def create_pending_order(
        self,
        *,
        customer_id: UUID,
        payload: CreateOrderRequest,
        request_id: str | None,
    ) -> OrderResponse:
        self.release_expired_holds()

        cart = self.repo.cart(payload.cart_id)
        if (
            cart is None
            or cart.customer_id != customer_id
            or cart.status != "active"
        ):
            raise ApiError(404, "cart_not_found", "السلة غير موجودة أو غير صالحة.")

        cart_items = self.repo.cart_items(cart.id)
        if not cart_items:
            raise ApiError(409, "cart_empty", "لا يمكن إنشاء طلب من سلة فارغة.")

        if cart.chef_id is None or cart.service_date is None:
            raise ApiError(409, "cart_invalid", "بيانات السلة غير مكتملة.")

        default_address = (
            self.db.scalar(
                select(AddressEntity).where(
                    AddressEntity.id == payload.delivery_address_id,
                    AddressEntity.user_id == customer_id,
                )
            )
            if payload.delivery_address_id is not None
            else self.db.scalar(
                select(AddressEntity)
                .where(
                    AddressEntity.user_id == customer_id,
                    AddressEntity.is_default.is_(True),
                )
                .limit(1)
            )
        )
        if payload.delivery_address_id is not None and default_address is None:
            raise ApiError(
                404,
                "delivery_address_not_found",
                "عنوان التوصيل المحدد غير موجود.",
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

        traffic_reservation = (
            LaunchTrafficGovernanceService(
                self.db,
                self.settings,
            ).admit_or_raise(
                customer_id=customer_id,
                chef_id=cart.chef_id,
                service_date=cart.service_date,
                area=default_address.area if default_address else None,
                request_id=request_id,
            )
            if default_address is not None
            else None
        )

        validated = []
        subtotal = 0

        # Revalidate every line immediately before taking inventory.
        for cart_item in cart_items:
            item, workday, dish = self._validated_menu_context(
                cart_item.daily_menu_item_id
            )
            if workday.chef_id != cart.chef_id:
                raise ApiError(
                    409,
                    "cart_multiple_chefs_not_allowed",
                    "يمكن أن يحتوي الطلب الواحد على شيف واحد فقط.",
                )
            if workday.service_date != cart.service_date:
                raise ApiError(
                    409,
                    "cart_multiple_service_dates_not_allowed",
                    "يمكن أن يحتوي الطلب الواحد على يوم توصيل واحد فقط.",
                )

            self._validate_requested_quantity(
                item=item,
                quantity=cart_item.quantity,
            )

            # Snapshot must match the current Today’s Kitchen price.
            cart_item.unit_price_minor = item.price_minor
            line_total = item.price_minor * cart_item.quantity
            subtotal += line_total
            validated.append((cart_item, item, dish))

        pricing = PricingService(self.db, self.settings)
        quote = pricing.quote_cart(
            customer_id=customer_id,
            cart_id=cart.id,
            coupon_code=payload.coupon_code,
            loyalty_points_to_redeem=payload.loyalty_points_to_redeem,
        )
        # Quote is the canonical pricing result. Subtotal was independently revalidated above.
        if quote.subtotal_minor != subtotal:
            raise ApiError(409, "pricing_cart_changed", "تغيرت أسعار السلة أثناء تأكيد الطلب.")
        delivery_fee_minor = quote.delivery_fee_minor
        discount_minor = quote.total_discount_minor
        total_minor = quote.total_minor
        hold_expires = utc_now() + timedelta(
            minutes=self.settings.inventory_hold_ttl_minutes
        )

        promise_workday = self.repo.workday(validated[0][1].workday_id)
        delivery_promise = DeliveryTimingService(self.settings).snapshot(
            service_date=cart.service_date,
            window_start=(
                promise_workday.delivery_window_start
                if promise_workday is not None
                else None
            ),
            window_end=(
                promise_workday.delivery_window_end
                if promise_workday is not None
                else None
            ),
            source="today_kitchen",
        )



        order = self.repo.create_order(
            customer_id=customer_id,
            chef_id=cart.chef_id,
            source_cart_id=cart.id,
            service_date=cart.service_date,
            subtotal_minor=subtotal,
            delivery_fee_minor=delivery_fee_minor,
            discount_minor=discount_minor,
            total_minor=total_minor,
            inventory_hold_expires_at=hold_expires,
        )
        DeliveryTimingService(self.settings).apply(
            order,
            delivery_promise,
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

        try:
            pricing.reserve_for_order(order=order, quote=quote, request_id=request_id)
            for cart_item, item, dish in validated:
                if not self.repo.reserve_inventory(
                    daily_menu_item_id=item.id,
                    quantity=cart_item.quantity,
                ):
                    raise ApiError(
                        409,
                        "inventory_changed",
                        "تغيرت الكمية المتاحة أثناء تأكيد الطلب. راجع السلة.",
                    )

                line_total = item.price_minor * cart_item.quantity
                self.db.add(
                    OrderItemEntity(
                        order_id=order.id,
                        daily_menu_item_id=item.id,
                        dish_id=dish.id,
                        dish_name=dish.name,
                        unit_price_minor=item.price_minor,
                        quantity=cart_item.quantity,
                        line_total_minor=line_total,
                    )
                )
                self.db.add(
                    InventoryReservationEntity(
                        order_id=order.id,
                        daily_menu_item_id=item.id,
                        quantity=cart_item.quantity,
                        status="active",
                        expires_at=hold_expires,
                    )
                )

            LaunchTrafficGovernanceService(
                self.db,
                self.settings,
            ).attach_admitted_order(
                reservation=traffic_reservation,
                order_id=order.id,
                request_id=request_id,
            )

            self.db.add(
                OrderStatusEventEntity(
                    order_id=order.id,
                    from_status=None,
                    to_status="pending_payment",
                    actor_user_id=customer_id,
                    reason="checkout_started",
                )
            )

            cart.status = "converted"
            cart.updated_at = utc_now()

            self.audit.add(
                action="customer.order.pending_payment_created",
                actor_user_id=customer_id,
                entity_type="order",
                entity_id=str(order.id),
                request_id=request_id,
                metadata={
                    "cart_id": str(cart.id),
                    "hold_expires_at": hold_expires.isoformat(),
                    "subtotal_minor": subtotal,
                    "discount_minor": discount_minor,
                    "total_minor": total_minor,
                    "coupon_code": quote.coupon.code if quote.coupon else None,
                    "loyalty_points_to_redeem": quote.loyalty_points_to_redeem,
                    "promised_delivery_window_start_at": (
                        order.promised_delivery_window_start_at.isoformat()
                        if order.promised_delivery_window_start_at
                        else None
                    ),
                    "promised_delivery_window_end_at": (
                        order.promised_delivery_window_end_at.isoformat()
                        if order.promised_delivery_window_end_at
                        else None
                    ),
                    "promised_delivery_timezone": order.promised_delivery_timezone,
                },
            )
            self.db.commit()
        except ApiError:
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise

        # New empty active cart will be created lazily on next GET /cart.
        return self.order_detail(
            customer_id=customer_id,
            order_id=order.id,
        )

    def order_detail(
        self,
        *,
        customer_id: UUID,
        order_id: UUID,
    ) -> OrderResponse:
        self.release_expired_holds()
        order = self.repo.order(order_id)

        if order is None or order.customer_id != customer_id:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        items = [
            OrderLineResponse(
                id=x.id,
                daily_menu_item_id=x.daily_menu_item_id,
                dish_id=x.dish_id,
                dish_name=x.dish_name,
                unit_price_minor=x.unit_price_minor,
                quantity=x.quantity,
                line_total_minor=x.line_total_minor,
            )
            for x in self.repo.order_items(order.id)
        ]

        timeline = [
            OrderStatusEventResponse(
                from_status=x.from_status,
                to_status=x.to_status,
                reason=x.reason,
                created_at=x.created_at,
            )
            for x in self.repo.order_events(order.id)
        ]

        pricing_adjustments = [
            OrderPricingAdjustmentResponse(
                adjustment_type=x.adjustment_type,
                reference_code=x.reference_code,
                amount_minor=x.amount_minor,
                metadata_json=x.metadata_json,
            )
            for x in PricingService(self.db, self.settings).adjustments_for_order(order_id=order.id)
        ]

        return OrderResponse(
            id=order.id,
            order_type=order.order_type,
            customer_id=order.customer_id,
            chef_id=order.chef_id,
            service_date=order.service_date,
            status=order.status,
            subtotal_minor=order.subtotal_minor,
            delivery_fee_minor=order.delivery_fee_minor,
            discount_minor=order.discount_minor,
            total_minor=order.total_minor,
            currency=order.currency,
            inventory_hold_expires_at=order.inventory_hold_expires_at,
            promised_delivery_window_start_at=(ensure_utc(order.promised_delivery_window_start_at) if order.promised_delivery_window_start_at else None),
            promised_delivery_window_end_at=(ensure_utc(order.promised_delivery_window_end_at) if order.promised_delivery_window_end_at else None),
            promised_delivery_timezone=order.promised_delivery_timezone,
            delivery_promise_source=order.delivery_promise_source,
            items=items,
            timeline=timeline,
            pricing_adjustments=pricing_adjustments,
            created_at=order.created_at,
        )

    def list_orders(
        self,
        *,
        customer_id: UUID,
    ) -> list[OrderListItemResponse]:
        self.release_expired_holds()
        return [
            OrderListItemResponse(
                id=x.id,
                order_type=x.order_type,
                chef_id=x.chef_id,
                service_date=x.service_date,
                status=x.status,
                total_minor=x.total_minor,
                currency=x.currency,
                promised_delivery_window_start_at=(ensure_utc(x.promised_delivery_window_start_at) if x.promised_delivery_window_start_at else None),
                promised_delivery_window_end_at=(ensure_utc(x.promised_delivery_window_end_at) if x.promised_delivery_window_end_at else None),
                promised_delivery_timezone=x.promised_delivery_timezone,
                created_at=x.created_at,
            )
            for x in self.repo.orders_for_customer(customer_id)
        ]

    def cancel_pending_order(
        self,
        *,
        customer_id: UUID,
        order_id: UUID,
        request_id: str | None,
    ) -> OrderResponse:
        self.release_expired_holds()
        order = self.repo.order(order_id)

        if order is None or order.customer_id != customer_id:
            raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        if order.status != "pending_payment":
            raise ApiError(
                409,
                "order_cannot_cancel",
                "يمكن إلغاء الطلب من هذه الخطوة قبل إتمام الدفع فقط.",
            )

        now = utc_now()
        for reservation in self.repo.active_reservations_for_order(order.id):
            self.repo.release_inventory(
                daily_menu_item_id=reservation.daily_menu_item_id,
                quantity=reservation.quantity,
            )
            reservation.status = "released"
            reservation.released_at = now

        old_status = order.status
        order.status = "cancelled"
        order.inventory_hold_expires_at = None

        if order.order_type == "special":
            from app.core.db_models import SpecialOrderEventEntity, SpecialOrderRequestEntity
            special = self.db.scalar(
                select(SpecialOrderRequestEntity).where(
                    SpecialOrderRequestEntity.order_id == order.id
                )
            )
            if special is not None and special.status in {"awaiting_payment", "counter_offer"}:
                previous_special_status = special.status
                special.status = "cancelled"
                special.cancelled_at = now
                self.db.add(
                    SpecialOrderEventEntity(
                        special_order_id=special.id,
                        from_status=previous_special_status,
                        to_status="cancelled",
                        actor_user_id=customer_id,
                        reason="customer_cancelled_before_payment",
                    )
                )
        self.db.add(
            OrderStatusEventEntity(
                order_id=order.id,
                from_status=old_status,
                to_status="cancelled",
                actor_user_id=customer_id,
                reason="customer_cancelled_before_payment",
            )
        )

        PricingService(self.db, self.settings).release_for_unpaid_order(
            order_id=order.id,
            reason="customer_cancelled_before_payment",
            request_id=request_id,
        )

        self.audit.add(
            action="customer.order.cancelled_before_payment",
            actor_user_id=customer_id,
            entity_type="order",
            entity_id=str(order.id),
            request_id=request_id,
        )
        self.db.commit()

        return self.order_detail(
            customer_id=customer_id,
            order_id=order.id,
        )
