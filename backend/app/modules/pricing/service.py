from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    CouponEntity,
    CouponRedemptionEntity,
    CustomerSubscriptionEntity,
    LoyaltyAccountEntity,
    LoyaltyRedemptionEntity,
    LoyaltyTransactionEntity,
    OrderEntity,
    OrderPricingAdjustmentEntity,
    SubscriptionPlanEntity,
    UserEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import ensure_utc, utc_now
from app.modules.orders.repository import OrderRepository
from app.modules.pricing.schemas import PricingQuoteResponse


@dataclass(slots=True)
class QuoteData:
    cart_id: UUID
    subtotal_minor: int
    delivery_fee_minor: int
    coupon_discount_minor: int
    subscription_discount_minor: int
    loyalty_discount_minor: int
    total_discount_minor: int
    total_minor: int
    coupon: CouponEntity | None
    loyalty_points_to_redeem: int
    loyalty_balance_points: int
    subscription: CustomerSubscriptionEntity | None
    plan: SubscriptionPlanEntity | None


class PricingService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.orders = OrderRepository(db)
        self.audit = AuditRepository(db)

    def quote_cart(self, *, customer_id: UUID, cart_id: UUID, coupon_code: str | None, loyalty_points_to_redeem: int) -> QuoteData:
        cart = self.orders.cart(cart_id)
        if cart is None or cart.customer_id != customer_id or cart.status != "active":
            raise ApiError(404, "cart_not_found", "السلة غير موجودة أو غير صالحة.")
        items = self.orders.cart_items(cart.id)
        if not items:
            raise ApiError(409, "cart_empty", "لا يمكن تسعير سلة فارغة.")

        subtotal = 0
        for cart_item in items:
            menu_item = self.orders.daily_menu_item(cart_item.daily_menu_item_id)
            if menu_item is None or menu_item.status in {"hidden", "sold_out"}:
                raise ApiError(409, "cart_item_unavailable", "أحد أصناف السلة لم يعد متاحًا.")
            workday = self.orders.workday(menu_item.workday_id)
            if workday is None or workday.status != "open":
                raise ApiError(409, "kitchen_closed", "مطبخ الشيف غير مفتوح لهذا اليوم.")
            if workday.cutoff_at is not None and ensure_utc(workday.cutoff_at) <= utc_now():
                raise ApiError(409, "kitchen_cutoff_passed", "انتهى وقت استقبال طلبات هذا اليوم.")
            if cart_item.quantity > menu_item.quantity_available:
                raise ApiError(409, "insufficient_inventory", "الكمية المطلوبة لم تعد متاحة.", {"available": menu_item.quantity_available})
            subtotal += menu_item.price_minor * cart_item.quantity

        subscription, plan = self.active_subscription(customer_id=customer_id)
        subscription_discount = 0
        if plan is not None and plan.order_discount_bps > 0:
            subscription_discount = subtotal * plan.order_discount_bps // 10000
            if plan.max_order_discount_minor is not None:
                subscription_discount = min(subscription_discount, plan.max_order_discount_minor)

        coupon = None
        coupon_discount = 0
        normalized = coupon_code.strip().upper() if coupon_code else None
        if normalized:
            coupon = self._valid_coupon(customer_id=customer_id, code=normalized, subtotal_minor=subtotal)
            coupon_discount = self._coupon_discount(coupon, subtotal)
            if not coupon.stack_with_subscription:
                subscription_discount = 0

        promo_discount = coupon_discount + subscription_discount
        max_promo = max(0, subtotal - self.settings.minimum_payable_minor)
        promo_discount = min(promo_discount, max_promo)
        if coupon_discount + subscription_discount > promo_discount:
            # Preserve coupon first, trim subscription second.
            coupon_discount = min(coupon_discount, promo_discount)
            subscription_discount = max(0, promo_discount - coupon_discount)

        account = self.db.get(LoyaltyAccountEntity, customer_id)
        loyalty_balance = account.balance_points if account else 0
        if loyalty_points_to_redeem > loyalty_balance:
            raise ApiError(422, "loyalty_insufficient_points", "رصيد النقاط غير كافٍ.", {"available_points": loyalty_balance})

        loyalty_discount = loyalty_points_to_redeem * self.settings.loyalty_redemption_minor_per_point
        remaining_before_loyalty = subtotal - promo_discount
        max_loyalty_discount = max(0, remaining_before_loyalty - self.settings.minimum_payable_minor)
        if loyalty_discount > max_loyalty_discount:
            max_points = max_loyalty_discount // self.settings.loyalty_redemption_minor_per_point
            raise ApiError(422, "loyalty_redemption_too_high", "عدد النقاط أكبر من المسموح لهذا الطلب.", {"max_points": max_points})

        total_discount = promo_discount + loyalty_discount
        total = subtotal - total_discount
        return QuoteData(
            cart_id=cart.id,
            subtotal_minor=subtotal,
            delivery_fee_minor=0,
            coupon_discount_minor=coupon_discount,
            subscription_discount_minor=subscription_discount,
            loyalty_discount_minor=loyalty_discount,
            total_discount_minor=total_discount,
            total_minor=total,
            coupon=coupon,
            loyalty_points_to_redeem=loyalty_points_to_redeem,
            loyalty_balance_points=loyalty_balance,
            subscription=subscription,
            plan=plan,
        )

    def quote_response(self, quote: QuoteData) -> PricingQuoteResponse:
        return PricingQuoteResponse(
            cart_id=quote.cart_id,
            subtotal_minor=quote.subtotal_minor,
            delivery_fee_minor=quote.delivery_fee_minor,
            coupon_discount_minor=quote.coupon_discount_minor,
            subscription_discount_minor=quote.subscription_discount_minor,
            loyalty_discount_minor=quote.loyalty_discount_minor,
            total_discount_minor=quote.total_discount_minor,
            total_minor=quote.total_minor,
            coupon_code=quote.coupon.code if quote.coupon else None,
            loyalty_points_to_redeem=quote.loyalty_points_to_redeem,
            loyalty_balance_points=quote.loyalty_balance_points,
            subscription_plan_id=quote.plan.id if quote.plan else None,
            subscription_plan_name=quote.plan.name if quote.plan else None,
            minimum_payable_minor=self.settings.minimum_payable_minor,
        )

    def active_subscription(self, *, customer_id: UUID):
        now = utc_now()
        row = self.db.scalar(
            select(CustomerSubscriptionEntity)
            .where(
                CustomerSubscriptionEntity.customer_id == customer_id,
                CustomerSubscriptionEntity.status == "active",
                CustomerSubscriptionEntity.starts_at <= now,
                CustomerSubscriptionEntity.ends_at > now,
            )
            .order_by(CustomerSubscriptionEntity.ends_at.desc())
            .limit(1)
        )
        if row is None:
            return None, None
        plan = self.db.get(SubscriptionPlanEntity, row.plan_id)
        if plan is None or not plan.is_active:
            return None, None
        return row, plan

    def _valid_coupon(self, *, customer_id: UUID, code: str, subtotal_minor: int) -> CouponEntity:
        coupon = self.db.scalar(select(CouponEntity).where(CouponEntity.code == code))
        now = utc_now()
        if coupon is None or not coupon.is_active:
            raise ApiError(404, "coupon_invalid", "الكوبون غير صالح.")
        if coupon.starts_at and ensure_utc(coupon.starts_at) > now:
            raise ApiError(409, "coupon_not_started", "الكوبون لم يبدأ بعد.")
        if coupon.ends_at and ensure_utc(coupon.ends_at) <= now:
            raise ApiError(409, "coupon_expired", "انتهت صلاحية الكوبون.")
        if subtotal_minor < coupon.min_subtotal_minor:
            raise ApiError(422, "coupon_minimum_not_met", "قيمة السلة أقل من الحد الأدنى للكوبون.", {"minimum_subtotal_minor": coupon.min_subtotal_minor})
        if coupon.total_usage_limit is not None and coupon.reserved_count + coupon.redeemed_count >= coupon.total_usage_limit:
            raise ApiError(409, "coupon_usage_limit_reached", "تم استهلاك الحد الأقصى للكوبون.")
        customer_uses = int(self.db.scalar(select(func.count(CouponRedemptionEntity.id)).where(
            CouponRedemptionEntity.coupon_id == coupon.id,
            CouponRedemptionEntity.customer_id == customer_id,
            CouponRedemptionEntity.status.in_(["reserved", "applied"]),
        )) or 0)
        if customer_uses >= coupon.per_customer_usage_limit:
            raise ApiError(409, "coupon_customer_limit_reached", "تم استخدام الحد المسموح لهذا الكوبون.")
        return coupon

    def _coupon_discount(self, coupon: CouponEntity, subtotal: int) -> int:
        if coupon.discount_type == "fixed":
            amount = coupon.discount_value
        else:
            amount = subtotal * coupon.discount_value // 10000
        if coupon.max_discount_minor is not None:
            amount = min(amount, coupon.max_discount_minor)
        return min(amount, subtotal)

    def reserve_for_order(self, *, order: OrderEntity, quote: QuoteData, request_id: str | None) -> None:
        if quote.coupon and quote.coupon_discount_minor > 0:
            # Atomic total limit guard.
            stmt = update(CouponEntity).where(CouponEntity.id == quote.coupon.id)
            if quote.coupon.total_usage_limit is not None:
                stmt = stmt.where((CouponEntity.reserved_count + CouponEntity.redeemed_count) < CouponEntity.total_usage_limit)
            result = self.db.execute(stmt.values(reserved_count=CouponEntity.reserved_count + 1))
            if result.rowcount != 1:
                raise ApiError(409, "coupon_usage_limit_reached", "تم استهلاك الكوبون أثناء إتمام الطلب.")
            self.db.add(CouponRedemptionEntity(
                coupon_id=quote.coupon.id,
                customer_id=order.customer_id,
                order_id=order.id,
                discount_minor=quote.coupon_discount_minor,
                status="reserved",
            ))
            self.db.add(OrderPricingAdjustmentEntity(
                order_id=order.id,
                adjustment_type="coupon",
                reference_code=quote.coupon.code,
                amount_minor=quote.coupon_discount_minor,
                metadata_json={"coupon_id": str(quote.coupon.id)},
            ))

        if quote.subscription and quote.plan:
            self.db.add(OrderPricingAdjustmentEntity(
                order_id=order.id,
                adjustment_type="subscription",
                reference_code=quote.plan.code,
                amount_minor=quote.subscription_discount_minor,
                metadata_json={
                    "subscription_id": str(quote.subscription.id),
                    "plan_id": str(quote.plan.id),
                    "loyalty_multiplier_bps": quote.plan.loyalty_multiplier_bps,
                },
            ))

        if quote.loyalty_points_to_redeem > 0:
            account = self.db.get(LoyaltyAccountEntity, order.customer_id)
            if account is None:
                raise ApiError(422, "loyalty_insufficient_points", "رصيد النقاط غير كافٍ.")
            result = self.db.execute(
                update(LoyaltyAccountEntity)
                .where(
                    LoyaltyAccountEntity.customer_id == order.customer_id,
                    LoyaltyAccountEntity.balance_points >= quote.loyalty_points_to_redeem,
                )
                .values(balance_points=LoyaltyAccountEntity.balance_points - quote.loyalty_points_to_redeem)
            )
            if result.rowcount != 1:
                raise ApiError(409, "loyalty_balance_changed", "تغير رصيد النقاط أثناء إتمام الطلب.")
            self.db.add(LoyaltyRedemptionEntity(
                customer_id=order.customer_id,
                order_id=order.id,
                points=quote.loyalty_points_to_redeem,
                discount_minor=quote.loyalty_discount_minor,
                status="reserved",
            ))
            self.db.add(OrderPricingAdjustmentEntity(
                order_id=order.id,
                adjustment_type="loyalty",
                reference_code=None,
                amount_minor=quote.loyalty_discount_minor,
                metadata_json={"points": quote.loyalty_points_to_redeem},
            ))

        self.audit.add(
            action="pricing.benefits.reserved",
            actor_user_id=order.customer_id,
            entity_type="order",
            entity_id=str(order.id),
            request_id=request_id,
            metadata={"discount_minor": quote.total_discount_minor},
        )
        self.db.flush()

    def apply_for_paid_order(self, *, order_id: UUID, request_id: str | None) -> None:
        now = utc_now()
        coupon_redemption = self.db.scalar(select(CouponRedemptionEntity).where(CouponRedemptionEntity.order_id == order_id))
        if coupon_redemption and coupon_redemption.status == "reserved":
            coupon_redemption.status = "applied"
            coupon_redemption.applied_at = now
            coupon = self.db.get(CouponEntity, coupon_redemption.coupon_id)
            if coupon:
                coupon.reserved_count = max(0, coupon.reserved_count - 1)
                coupon.redeemed_count += 1

        loyalty = self.db.scalar(select(LoyaltyRedemptionEntity).where(LoyaltyRedemptionEntity.order_id == order_id))
        if loyalty and loyalty.status == "reserved":
            loyalty.status = "applied"
            loyalty.applied_at = now
            account = self.db.get(LoyaltyAccountEntity, loyalty.customer_id)
            if account:
                account.lifetime_redeemed_points += loyalty.points
            existing_tx = self.db.scalar(select(LoyaltyTransactionEntity).where(LoyaltyTransactionEntity.idempotency_key == f"order-redeem:{order_id}"))
            if existing_tx is None:
                self.db.add(LoyaltyTransactionEntity(
                    customer_id=loyalty.customer_id,
                    transaction_type="redeem",
                    points=-loyalty.points,
                    source_order_id=None,
                    idempotency_key=f"order-redeem:{order_id}",
                    description="استخدام نقاط في طلب",
                ))
        self.db.flush()

    def release_for_unpaid_order(self, *, order_id: UUID, reason: str, request_id: str | None) -> None:
        now = utc_now()
        coupon_redemption = self.db.scalar(select(CouponRedemptionEntity).where(CouponRedemptionEntity.order_id == order_id))
        if coupon_redemption and coupon_redemption.status == "reserved":
            coupon_redemption.status = "released"
            coupon_redemption.released_at = now
            coupon_redemption.release_reason = reason
            coupon = self.db.get(CouponEntity, coupon_redemption.coupon_id)
            if coupon:
                coupon.reserved_count = max(0, coupon.reserved_count - 1)

        loyalty = self.db.scalar(select(LoyaltyRedemptionEntity).where(LoyaltyRedemptionEntity.order_id == order_id))
        if loyalty and loyalty.status == "reserved":
            loyalty.status = "released"
            loyalty.released_at = now
            loyalty.release_reason = reason
            account = self.db.get(LoyaltyAccountEntity, loyalty.customer_id)
            if account:
                account.balance_points += loyalty.points
        self.db.flush()

    def adjustments_for_order(self, *, order_id: UUID):
        return list(self.db.scalars(select(OrderPricingAdjustmentEntity).where(OrderPricingAdjustmentEntity.order_id == order_id).order_by(OrderPricingAdjustmentEntity.created_at.asc())).all())
