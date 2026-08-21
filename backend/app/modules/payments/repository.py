from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db_models import (
    InventoryReservationEntity,
    PaymentEntity,
    PaymentProviderTransactionEntity,
    PaymentReconciliationIssueEntity,
    PaymentWebhookEventEntity,
    RefundEntity,
)


class PaymentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def payment(self, payment_id: UUID) -> PaymentEntity | None:
        return self.db.get(PaymentEntity, payment_id)

    def payment_by_reference(
        self,
        provider: str,
        reference: str,
    ) -> PaymentEntity | None:
        return self.db.scalar(
            select(PaymentEntity).where(
                PaymentEntity.provider == provider,
                PaymentEntity.provider_reference == reference,
            )
        )

    def payment_by_provider_order_reference(
        self,
        provider: str,
        reference: str,
    ) -> PaymentEntity | None:
        return self.db.scalar(
            select(PaymentEntity).where(
                PaymentEntity.provider == provider,
                PaymentEntity.provider_order_reference == reference,
            )
        )

    def payment_by_provider_transaction_reference(
        self,
        provider: str,
        reference: str,
    ) -> PaymentEntity | None:
        return self.db.scalar(
            select(PaymentEntity).where(
                PaymentEntity.provider == provider,
                PaymentEntity.provider_transaction_reference == reference,
            )
        )

    def payment_by_idempotency_key(self, key: str) -> PaymentEntity | None:
        return self.db.scalar(
            select(PaymentEntity).where(PaymentEntity.idempotency_key == key)
        )

    def latest_payment_for_order(self, order_id: UUID) -> PaymentEntity | None:
        return self.db.scalar(
            select(PaymentEntity)
            .where(PaymentEntity.order_id == order_id)
            .order_by(PaymentEntity.created_at.desc())
            .limit(1)
        )

    def succeeded_payment_for_order(self, order_id: UUID) -> PaymentEntity | None:
        return self.db.scalar(
            select(PaymentEntity)
            .where(
                PaymentEntity.order_id == order_id,
                PaymentEntity.status == "succeeded",
            )
            .order_by(PaymentEntity.created_at.desc())
            .limit(1)
        )

    def webhook_event(
        self,
        provider: str,
        provider_event_id: str,
    ) -> PaymentWebhookEventEntity | None:
        return self.db.scalar(
            select(PaymentWebhookEventEntity).where(
                PaymentWebhookEventEntity.provider == provider,
                PaymentWebhookEventEntity.provider_event_id == provider_event_id,
            )
        )

    def reservations_for_order(
        self,
        order_id: UUID,
    ) -> list[InventoryReservationEntity]:
        return list(
            self.db.scalars(
                select(InventoryReservationEntity).where(
                    InventoryReservationEntity.order_id == order_id
                )
            ).all()
        )

    def refunds_for_payment(self, payment_id: UUID) -> list[RefundEntity]:
        return list(
            self.db.scalars(
                select(RefundEntity)
                .where(RefundEntity.payment_id == payment_id)
                .order_by(RefundEntity.created_at.asc())
            ).all()
        )

    def refund_by_idempotency(
        self,
        payment_id: UUID,
        idempotency_key: str,
    ) -> RefundEntity | None:
        return self.db.scalar(
            select(RefundEntity).where(
                RefundEntity.payment_id == payment_id,
                RefundEntity.idempotency_key == idempotency_key,
            )
        )

    # --------------------------------------------------------------
    # Sprint 32 provider transaction / reconciliation persistence
    # --------------------------------------------------------------
    def provider_transaction(
        self,
        *,
        provider: str,
        provider_transaction_id: str,
    ) -> PaymentProviderTransactionEntity | None:
        return self.db.scalar(
            select(PaymentProviderTransactionEntity).where(
                PaymentProviderTransactionEntity.provider == provider,
                PaymentProviderTransactionEntity.provider_transaction_id
                == provider_transaction_id,
            )
        )

    def provider_transactions_for_payment(
        self,
        payment_id: UUID,
    ) -> list[PaymentProviderTransactionEntity]:
        return list(
            self.db.scalars(
                select(PaymentProviderTransactionEntity)
                .where(PaymentProviderTransactionEntity.payment_id == payment_id)
                .order_by(PaymentProviderTransactionEntity.observed_at.asc())
            ).all()
        )

    def reconciliation_issue_by_fingerprint(
        self,
        fingerprint: str,
    ) -> PaymentReconciliationIssueEntity | None:
        return self.db.scalar(
            select(PaymentReconciliationIssueEntity).where(
                PaymentReconciliationIssueEntity.fingerprint == fingerprint
            )
        )

    def reconciliation_issue(
        self,
        issue_id: UUID,
    ) -> PaymentReconciliationIssueEntity | None:
        return self.db.get(PaymentReconciliationIssueEntity, issue_id)
