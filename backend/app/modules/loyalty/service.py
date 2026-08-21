from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    LoyaltyAccountEntity,
    LoyaltyTransactionEntity,
    OrderEntity,
    OrderPricingAdjustmentEntity,
)
from app.core.repositories import AuditRepository
from app.modules.loyalty.schemas import (
    LoyaltyAccountResponse,
    LoyaltyTransactionResponse,
)


class LoyaltyService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.audit = AuditRepository(db)

    def account(self, *, customer_id: UUID) -> LoyaltyAccountEntity:
        row = self.db.get(LoyaltyAccountEntity, customer_id)
        if row is None:
            row = LoyaltyAccountEntity(customer_id=customer_id)
            self.db.add(row)
            self.db.flush()
        return row

    def award_for_delivered_order(
        self,
        *,
        order: OrderEntity,
        request_id: str | None,
        commit: bool = False,
    ) -> LoyaltyTransactionEntity | None:
        base_points = order.total_minor // self.settings.loyalty_minor_per_point
        multiplier_bps = 10000
        subscription_adjustment = self.db.scalar(
            select(OrderPricingAdjustmentEntity).where(
                OrderPricingAdjustmentEntity.order_id == order.id,
                OrderPricingAdjustmentEntity.adjustment_type == "subscription",
            )
        )
        if subscription_adjustment is not None:
            multiplier_bps = int(subscription_adjustment.metadata_json.get("loyalty_multiplier_bps", 10000))
        points = base_points * multiplier_bps // 10000
        if points <= 0:
            return None

        idempotency_key = f"order-delivered:{order.id}"
        existing = self.db.scalar(
            select(LoyaltyTransactionEntity).where(
                LoyaltyTransactionEntity.idempotency_key == idempotency_key
            )
        )
        if existing is not None:
            return existing

        account = self.account(customer_id=order.customer_id)
        tx = LoyaltyTransactionEntity(
            customer_id=order.customer_id,
            transaction_type="earn_order",
            points=points,
            source_order_id=order.id,
            idempotency_key=idempotency_key,
            description="نقاط من طلب مكتمل",
        )
        self.db.add(tx)

        account.balance_points += points
        account.lifetime_earned_points += points

        self.audit.add(
            action="loyalty.points.earned",
            actor_user_id=order.customer_id,
            entity_type="order",
            entity_id=str(order.id),
            request_id=request_id,
            metadata={"points": points},
        )
        self.db.flush()

        if commit:
            self.db.commit()
            self.db.refresh(tx)
        return tx

    def response(self, *, customer_id: UUID) -> LoyaltyAccountResponse:
        account = self.account(customer_id=customer_id)
        self.db.commit()
        txs = list(
            self.db.scalars(
                select(LoyaltyTransactionEntity)
                .where(LoyaltyTransactionEntity.customer_id == customer_id)
                .order_by(LoyaltyTransactionEntity.created_at.desc())
                .limit(100)
            ).all()
        )
        return LoyaltyAccountResponse(
            customer_id=customer_id,
            balance_points=account.balance_points,
            lifetime_earned_points=account.lifetime_earned_points,
            lifetime_redeemed_points=account.lifetime_redeemed_points,
            transactions=[
                LoyaltyTransactionResponse.model_validate(x)
                for x in txs
            ],
        )
