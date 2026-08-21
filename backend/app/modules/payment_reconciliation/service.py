from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    PaymentEntity,
    PaymentProviderTransactionEntity,
    PaymentReconciliationIssueEntity,
    PaymentWebhookEventEntity,
    RefundEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import utc_now
from app.modules.payments.paymob import PaymobTransaction
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.schemas import (
    PaymentProviderTransactionResponse,
    PaymentReconciliationIssueResponse,
    ReconciliationRunResponse,
)


class PaymentReconciliationService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repo = PaymentRepository(db)
        self.audit = AuditRepository(db)

    # ------------------------------------------------------------------
    # Callback transaction snapshot
    # ------------------------------------------------------------------
    def ingest_paymob_transaction(
        self,
        *,
        transaction: PaymobTransaction,
        payload_hash: str,
        request_id: str | None,
    ) -> dict:
        existing = self.repo.provider_transaction(
            provider="paymob",
            provider_transaction_id=transaction.transaction_id,
        )
        duplicate = existing is not None

        if existing is None:
            row = PaymentProviderTransactionEntity(
                provider="paymob",
                provider_transaction_id=transaction.transaction_id,
                provider_order_reference=transaction.provider_order_reference,
                parent_provider_transaction_id=transaction.parent_transaction_id,
                transaction_type=transaction.transaction_type,
                amount_minor=transaction.amount_minor,
                currency=transaction.currency,
                success=transaction.success,
                pending=transaction.pending,
                is_refunded=transaction.is_refunded,
                refunded_minor=transaction.refunded_minor,
                payload_hash=payload_hash,
                payload_json=transaction.raw_obj,
                observed_at=utc_now(),
            )
            self.db.add(row)
            self.db.flush()
        else:
            row = existing
            # Same provider transaction may be redelivered. Refresh the latest
            # provider snapshot while preserving the first observed_at.
            row.provider_order_reference = transaction.provider_order_reference
            row.parent_provider_transaction_id = transaction.parent_transaction_id
            row.transaction_type = transaction.transaction_type
            row.amount_minor = transaction.amount_minor
            row.currency = transaction.currency
            row.success = transaction.success
            row.pending = transaction.pending
            row.is_refunded = transaction.is_refunded
            row.refunded_minor = transaction.refunded_minor
            row.payload_hash = payload_hash
            row.payload_json = transaction.raw_obj

        payment = self._resolve_payment(
            transaction=transaction,
            existing_payment_id=row.payment_id,
        )
        if payment is not None:
            row.payment_id = payment.id
            payment.provider_last_seen_at = utc_now()
            payment.provider_status = transaction.provider_status

            if transaction.transaction_type == "payment":
                payment.provider_transaction_reference = transaction.transaction_id
                if (
                    transaction.provider_order_reference
                    and not payment.provider_order_reference
                ):
                    payment.provider_order_reference = (
                        transaction.provider_order_reference
                    )

        self.db.flush()

        issues = 0
        event_status = "received"

        if payment is None:
            self._upsert_issue(
                payment_id=None,
                provider_transaction_id=row.provider_transaction_id,
                issue_type="unmatched_provider_transaction",
                expected={},
                actual={
                    "provider": row.provider,
                    "provider_order_reference": row.provider_order_reference,
                    "transaction_type": row.transaction_type,
                    "amount_minor": row.amount_minor,
                    "currency": row.currency,
                },
            )
            issues = 1
        elif transaction.transaction_type in {"refund", "void"}:
            # Apply a matched financial reversal first, then compare the local
            # post-state to the provider snapshot. Otherwise every legitimate
            # refund would appear as a mismatch before its local ledger updates.
            event_status = self._apply_business_state(
                payment=payment,
                transaction=transaction,
                request_id=request_id,
            )
            issues = self._detect_transaction_issues(
                transaction_row=row,
                payment=payment,
            )
        else:
            issues = self._detect_transaction_issues(
                transaction_row=row,
                payment=payment,
            )
            if issues == 0:
                event_status = self._apply_business_state(
                    payment=payment,
                    transaction=transaction,
                    request_id=request_id,
                )

        self._record_webhook_ledger(
            transaction=transaction,
            payload_hash=payload_hash,
            processing_status=event_status,
        )

        self.audit.add(
            action="payment.paymob.transaction_observed",
            entity_type="payment_provider_transaction",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "payment_id": str(payment.id) if payment else None,
                "provider_transaction_id": row.provider_transaction_id,
                "transaction_type": row.transaction_type,
                "success": row.success,
                "pending": row.pending,
                "issues_detected": issues,
            },
        )
        self.db.commit()

        return {
            "status": event_status,
            "duplicate": duplicate,
            "matched": payment is not None,
            "payment_id": str(payment.id) if payment else None,
            "provider_transaction_id": transaction.transaction_id,
            "issues_detected": issues,
        }

    def _resolve_payment(
        self,
        *,
        transaction: PaymobTransaction,
        existing_payment_id: UUID | None,
    ) -> PaymentEntity | None:
        if existing_payment_id is not None:
            payment = self.repo.payment(existing_payment_id)
            if payment is not None:
                return payment

        if transaction.transaction_type in {"refund", "void"}:
            parent = transaction.parent_transaction_id
            if parent:
                payment = self.repo.payment_by_provider_transaction_reference(
                    "paymob",
                    parent,
                )
                if payment is not None:
                    return payment

        payment = self.repo.payment_by_provider_transaction_reference(
            "paymob",
            transaction.transaction_id,
        )
        if payment is not None:
            return payment

        if transaction.provider_order_reference:
            payment = self.repo.payment_by_provider_order_reference(
                "paymob",
                transaction.provider_order_reference,
            )
            if payment is not None:
                return payment

        if transaction.special_reference:
            try:
                payment_id = UUID(transaction.special_reference)
            except (TypeError, ValueError):
                payment_id = None
            if payment_id is not None:
                payment = self.repo.payment(payment_id)
                if payment is not None and payment.provider == "paymob":
                    return payment

            # Some integrations echo the Intention identifier or other merchant
            # reference in this location.
            payment = self.repo.payment_by_reference(
                "paymob",
                transaction.special_reference,
            )
            if payment is not None:
                return payment

        return None

    def _detect_transaction_issues(
        self,
        *,
        transaction_row: PaymentProviderTransactionEntity,
        payment: PaymentEntity | None,
    ) -> int:
        if payment is None:
            return 0

        count = 0
        if (
            transaction_row.transaction_type == "payment"
            and transaction_row.amount_minor != payment.amount_minor
        ):
            self._upsert_issue(
                payment_id=payment.id,
                provider_transaction_id=transaction_row.provider_transaction_id,
                issue_type="amount_mismatch",
                expected={"amount_minor": payment.amount_minor},
                actual={"amount_minor": transaction_row.amount_minor},
            )
            count += 1

        if transaction_row.currency.upper() != payment.currency.upper():
            self._upsert_issue(
                payment_id=payment.id,
                provider_transaction_id=transaction_row.provider_transaction_id,
                issue_type="currency_mismatch",
                expected={"currency": payment.currency.upper()},
                actual={"currency": transaction_row.currency.upper()},
            )
            count += 1

        if transaction_row.transaction_type == "payment":
            provider_success = (
                transaction_row.success and not transaction_row.pending
            )
            if payment.status == "succeeded" and not provider_success:
                self._upsert_issue(
                    payment_id=payment.id,
                    provider_transaction_id=transaction_row.provider_transaction_id,
                    issue_type="status_mismatch",
                    expected={"payment_status": "succeeded"},
                    actual={
                        "provider_success": transaction_row.success,
                        "provider_pending": transaction_row.pending,
                    },
                )
                count += 1

        if transaction_row.transaction_type == "refund":
            local_refunded = payment.refunded_minor
            provider_refunded = max(
                transaction_row.amount_minor if transaction_row.success else 0,
                transaction_row.refunded_minor,
            )
            if (
                transaction_row.success
                and provider_refunded > 0
                and local_refunded < provider_refunded
            ):
                self._upsert_issue(
                    payment_id=payment.id,
                    provider_transaction_id=transaction_row.provider_transaction_id,
                    issue_type="refund_mismatch",
                    expected={"local_refunded_minor": local_refunded},
                    actual={"provider_refunded_minor": provider_refunded},
                )
                count += 1

        return count

    def _apply_business_state(
        self,
        *,
        payment: PaymentEntity,
        transaction: PaymobTransaction,
        request_id: str | None,
    ) -> str:
        # Import late to keep the reconciliation persistence layer independent.
        from app.modules.payments.service import PaymentService

        payment_service = PaymentService(self.db, self.settings)

        if transaction.transaction_type == "payment":
            if transaction.pending:
                return "ignored"
            if transaction.success:
                payment_service._apply_payment_success(
                    payment,
                    request_id=request_id,
                )
                return "processed"

            payment_service._apply_payment_failure(
                payment,
                cancelled=False,
                request_id=request_id,
            )
            return "processed"

        if transaction.transaction_type == "refund":
            self._apply_refund_snapshot(
                payment=payment,
                transaction=transaction,
                request_id=request_id,
            )
            return "processed" if transaction.success else "ignored"

        if transaction.transaction_type == "void":
            # A successful void means the original authorization/payment should
            # not remain a confirmed usable payment.
            if transaction.success and payment.status != "succeeded":
                payment_service._apply_payment_failure(
                    payment,
                    cancelled=True,
                    request_id=request_id,
                )
                return "processed"
            return "ignored"

        return "ignored"

    def _apply_refund_snapshot(
        self,
        *,
        payment: PaymentEntity,
        transaction: PaymobTransaction,
        request_id: str | None,
    ) -> None:
        refund = self.db.scalar(
            select(RefundEntity)
            .where(
                RefundEntity.payment_id == payment.id,
                RefundEntity.provider_reference == transaction.transaction_id,
            )
            .limit(1)
        )

        if refund is None and transaction.success:
            # Match the oldest pending refund with the same amount. This handles
            # provider callback arrival after a synchronous refund submission.
            refund = self.db.scalar(
                select(RefundEntity)
                .where(
                    RefundEntity.payment_id == payment.id,
                    RefundEntity.status == "pending",
                    RefundEntity.amount_minor == transaction.amount_minor,
                )
                .order_by(RefundEntity.created_at.asc())
                .limit(1)
            )

        if refund is None:
            return

        refund.provider_reference = transaction.transaction_id
        refund.provider_status = transaction.provider_status

        if transaction.success and refund.status != "succeeded":
            refund.status = "succeeded"
            refund.completed_at = utc_now()
            refund.failed_at = None
            refund.provider_error = None
            payment.refunded_minor = min(
                payment.amount_minor,
                max(
                    payment.refunded_minor + refund.amount_minor,
                    transaction.refunded_minor,
                ),
            )
            self.audit.add(
                action="refund.paymob.confirmed",
                entity_type="refund",
                entity_id=str(refund.id),
                request_id=request_id,
                metadata={
                    "payment_id": str(payment.id),
                    "provider_transaction_id": transaction.transaction_id,
                },
            )
        elif not transaction.success and not transaction.pending:
            refund.status = "failed"
            refund.failed_at = utc_now()
            refund.provider_error = "paymob_refund_failed"

    def _record_webhook_ledger(
        self,
        *,
        transaction: PaymobTransaction,
        payload_hash: str,
        processing_status: str,
    ) -> None:
        event_id = (
            f"tx:{transaction.transaction_id}:"
            f"{transaction.transaction_type}:"
            f"{transaction.provider_status}"
        )
        existing = self.repo.webhook_event("paymob", event_id)
        if existing is not None:
            existing.processing_status = processing_status
            existing.processed_at = utc_now()
            return

        event = PaymentWebhookEventEntity(
            provider="paymob",
            provider_event_id=event_id,
            event_type=(
                f"payment.{transaction.provider_status}"
                if transaction.transaction_type == "payment"
                else f"{transaction.transaction_type}.{transaction.provider_status}"
            ),
            provider_reference=transaction.transaction_id,
            payload_hash=payload_hash,
            payload_json=transaction.raw_obj,
            processing_status=processing_status,
            processed_at=utc_now(),
        )
        self.db.add(event)

    # ------------------------------------------------------------------
    # Issue lifecycle
    # ------------------------------------------------------------------
    def _issue_fingerprint(
        self,
        *,
        payment_id: UUID | None,
        provider_transaction_id: str | None,
        issue_type: str,
    ) -> str:
        material = (
            f"{payment_id or 'none'}|"
            f"{provider_transaction_id or 'none'}|{issue_type}"
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def _upsert_issue(
        self,
        *,
        payment_id: UUID | None,
        provider_transaction_id: str | None,
        issue_type: str,
        expected: dict,
        actual: dict,
    ) -> PaymentReconciliationIssueEntity:
        fingerprint = self._issue_fingerprint(
            payment_id=payment_id,
            provider_transaction_id=provider_transaction_id,
            issue_type=issue_type,
        )
        row = self.repo.reconciliation_issue_by_fingerprint(fingerprint)
        now = utc_now()
        if row is None:
            row = PaymentReconciliationIssueEntity(
                fingerprint=fingerprint,
                payment_id=payment_id,
                provider_transaction_id=provider_transaction_id,
                issue_type=issue_type,
                status="open",
                expected_json=expected,
                actual_json=actual,
                detected_at=now,
                last_detected_at=now,
            )
            self.db.add(row)
        else:
            row.payment_id = payment_id
            row.provider_transaction_id = provider_transaction_id
            row.expected_json = expected
            row.actual_json = actual
            row.last_detected_at = now
            # Recurring discrepancy re-opens an issue that was manually resolved.
            if row.status == "resolved":
                row.status = "open"
                row.resolved_at = None
                row.resolved_by_user_id = None
                row.resolution_note = None
        self.db.flush()
        return row

    # ------------------------------------------------------------------
    # Batch reconciliation
    # ------------------------------------------------------------------
    def run(self) -> ReconciliationRunResponse:
        transactions = list(
            self.db.scalars(
                select(PaymentProviderTransactionEntity)
                .where(PaymentProviderTransactionEntity.provider == "paymob")
                .order_by(PaymentProviderTransactionEntity.observed_at.desc())
                .limit(self.settings.paymob_reconciliation_batch_size)
            ).all()
        )

        refreshed = 0
        touched_payments: set[UUID] = set()
        for tx in transactions:
            payment = (
                self.repo.payment(tx.payment_id)
                if tx.payment_id is not None
                else None
            )
            before = int(
                self.db.scalar(
                    select(func.count(PaymentReconciliationIssueEntity.id)).where(
                        PaymentReconciliationIssueEntity.status == "open"
                    )
                )
                or 0
            )
            count = self._detect_transaction_issues(
                transaction_row=tx,
                payment=payment,
            )
            refreshed += count
            if payment is not None:
                touched_payments.add(payment.id)

        # Local succeeded payments with a known Paymob transaction should agree
        # with the latest provider snapshot.
        payments = list(
            self.db.scalars(
                select(PaymentEntity)
                .where(PaymentEntity.provider == "paymob")
                .order_by(PaymentEntity.created_at.desc())
                .limit(self.settings.paymob_reconciliation_batch_size)
            ).all()
        )
        for payment in payments:
            if (
                payment.status == "succeeded"
                and payment.provider_transaction_reference
            ):
                tx = self.repo.provider_transaction(
                    provider="paymob",
                    provider_transaction_id=payment.provider_transaction_reference,
                )
                if tx is not None and not tx.success:
                    self._upsert_issue(
                        payment_id=payment.id,
                        provider_transaction_id=tx.provider_transaction_id,
                        issue_type="status_mismatch",
                        expected={"payment_status": "succeeded"},
                        actual={
                            "provider_success": tx.success,
                            "provider_pending": tx.pending,
                        },
                    )
                    refreshed += 1

        self.db.commit()
        open_issues = int(
            self.db.scalar(
                select(func.count(PaymentReconciliationIssueEntity.id)).where(
                    PaymentReconciliationIssueEntity.status == "open"
                )
            )
            or 0
        )
        return ReconciliationRunResponse(
            scanned_payments=len(payments),
            scanned_transactions=len(transactions),
            open_issues=open_issues,
            new_or_refreshed_issues=refreshed,
        )

    def list_issues(
        self,
        *,
        status: str | None,
        issue_type: str | None,
        limit: int,
    ) -> list[PaymentReconciliationIssueResponse]:
        stmt = select(PaymentReconciliationIssueEntity)
        if status:
            stmt = stmt.where(PaymentReconciliationIssueEntity.status == status)
        if issue_type:
            stmt = stmt.where(
                PaymentReconciliationIssueEntity.issue_type == issue_type
            )
        stmt = stmt.order_by(
            PaymentReconciliationIssueEntity.last_detected_at.desc()
        ).limit(limit)
        return [
            PaymentReconciliationIssueResponse.model_validate(x)
            for x in self.db.scalars(stmt).all()
        ]

    def summary(self) -> dict:
        grouped = self.db.execute(
            select(
                PaymentReconciliationIssueEntity.status,
                PaymentReconciliationIssueEntity.issue_type,
                func.count(PaymentReconciliationIssueEntity.id),
            ).group_by(
                PaymentReconciliationIssueEntity.status,
                PaymentReconciliationIssueEntity.issue_type,
            )
        ).all()
        by_status: dict[str, int] = {"open": 0, "resolved": 0}
        by_type: dict[str, int] = {}
        for status, issue_type, count in grouped:
            by_status[status] = by_status.get(status, 0) + int(count)
            by_type[issue_type] = by_type.get(issue_type, 0) + int(count)

        return {
            "issues_by_status": by_status,
            "issues_by_type": by_type,
            "provider_transactions": int(
                self.db.scalar(
                    select(func.count(PaymentProviderTransactionEntity.id))
                )
                or 0
            ),
            "paymob_payments": int(
                self.db.scalar(
                    select(func.count(PaymentEntity.id)).where(
                        PaymentEntity.provider == "paymob"
                    )
                )
                or 0
            ),
        }

    def resolve_issue(
        self,
        *,
        issue_id: UUID,
        admin_user_id: UUID,
        note: str,
        request_id: str | None,
    ) -> PaymentReconciliationIssueResponse:
        row = self.repo.reconciliation_issue(issue_id)
        if row is None:
            raise ApiError(
                404,
                "payment_reconciliation_issue_not_found",
                "مشكلة المطابقة المالية غير موجودة.",
            )
        if row.status != "resolved":
            row.status = "resolved"
            row.resolved_at = utc_now()
            row.resolved_by_user_id = admin_user_id
            row.resolution_note = note
            self.audit.add(
                action="payment.reconciliation.issue_resolved",
                actor_user_id=admin_user_id,
                entity_type="payment_reconciliation_issue",
                entity_id=str(row.id),
                request_id=request_id,
                metadata={"issue_type": row.issue_type},
            )
            self.db.commit()
            self.db.refresh(row)
        return PaymentReconciliationIssueResponse.model_validate(row)

    def provider_transactions(
        self,
        *,
        payment_id: UUID,
    ) -> list[PaymentProviderTransactionResponse]:
        if self.repo.payment(payment_id) is None:
            raise ApiError(404, "payment_not_found", "عملية الدفع غير موجودة.")
        return [
            PaymentProviderTransactionResponse.model_validate(x)
            for x in self.repo.provider_transactions_for_payment(payment_id)
        ]
