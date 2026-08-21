from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db_models import (
    PaymentReconciliationIssueEntity,
    ProviderCostImportBatchEntity,
    ProviderSettlementBatchEntity,
    ProviderSettlementLineEntity,
    UserEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import utc_now
from app.modules.vendor_accounting.schemas import (
    ImportReviewItem,
    QueueAssignRequest,
    ReviewDecisionRequest,
    SettlementCloseRequest,
    SettlementOperationsItem,
    VendorAccountingSummary,
)


class VendorAccountingService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.audit = AuditRepository(db)

    def _admin(self, admin_id: UUID) -> UserEntity:
        row = self.db.get(UserEntity, admin_id)
        if row is None or row.role != "admin" or not row.is_active:
            raise ApiError(
                422,
                "vendor_accounting_admin_invalid",
                "المستخدم المحدد ليس مسؤول إدارة نشطًا.",
            )
        return row

    def _import(self, batch_id: UUID) -> ProviderCostImportBatchEntity:
        row = self.db.get(ProviderCostImportBatchEntity, batch_id)
        if row is None:
            raise ApiError(
                404,
                "provider_import_not_found",
                "دفعة الاستيراد غير موجودة.",
            )
        return row

    def _settlement(self, batch_id: UUID) -> ProviderSettlementBatchEntity:
        row = self.db.get(ProviderSettlementBatchEntity, batch_id)
        if row is None:
            raise ApiError(
                404,
                "settlement_not_found",
                "دفعة التسوية غير موجودة.",
            )
        return row

    # ------------------------------------------------------------------
    # Import review queue
    # ------------------------------------------------------------------
    def import_reviews(
        self,
        *,
        review_status: str | None,
        provider: str | None,
        limit: int,
    ) -> list[ImportReviewItem]:
        stmt = select(ProviderCostImportBatchEntity)
        if review_status:
            stmt = stmt.where(
                ProviderCostImportBatchEntity.review_status == review_status
            )
        if provider:
            stmt = stmt.where(
                ProviderCostImportBatchEntity.provider
                == provider.strip().lower()
            )
        rows = list(
            self.db.scalars(
                stmt.order_by(
                    ProviderCostImportBatchEntity.created_at.asc()
                ).limit(limit)
            ).all()
        )
        return [ImportReviewItem.model_validate(x) for x in rows]

    def assign_import(
        self,
        *,
        batch_id: UUID,
        payload: QueueAssignRequest,
        admin_id: UUID,
        request_id: str | None,
    ) -> ImportReviewItem:
        row = self._import(batch_id)
        if row.status == "applied":
            raise ApiError(
                409,
                "provider_import_already_applied",
                "لا يمكن إعادة تعيين مراجعة دفعة تم تطبيقها.",
            )

        if payload.admin_id is None:
            row.assigned_reviewer_id = None
            row.review_status = "pending"
        else:
            self._admin(payload.admin_id)
            row.assigned_reviewer_id = payload.admin_id
            row.review_status = "assigned"

        self.audit.add(
            action="vendor.import_review.assigned",
            actor_user_id=admin_id,
            entity_type="provider_cost_import_batch",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "assigned_reviewer_id": (
                    str(payload.admin_id)
                    if payload.admin_id
                    else None
                )
            },
        )
        self.db.commit()
        self.db.refresh(row)
        return ImportReviewItem.model_validate(row)

    def approve_import(
        self,
        *,
        batch_id: UUID,
        payload: ReviewDecisionRequest,
        admin_id: UUID,
        request_id: str | None,
    ) -> ImportReviewItem:
        row = self._import(batch_id)
        if row.status != "validated":
            raise ApiError(
                409,
                "provider_import_not_validated_for_review",
                "يجب أن تكون الدفعة Validated قبل اعتمادها محاسبيًا.",
            )
        if (
            self.settings.vendor_accounting_require_dual_control
            and row.created_by_admin_id == admin_id
        ):
            raise ApiError(
                409,
                "vendor_accounting_dual_control_required",
                "منشئ الدفعة لا يمكنه اعتمادها في وضع maker-checker.",
            )

        row.review_status = "approved"
        row.assigned_reviewer_id = admin_id
        row.reviewed_by_admin_id = admin_id
        row.review_note = payload.note.strip()
        row.reviewed_at = utc_now()
        self.audit.add(
            action="vendor.import_review.approved",
            actor_user_id=admin_id,
            entity_type="provider_cost_import_batch",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"risk_flags": row.risk_flags_json},
        )
        self.db.commit()
        self.db.refresh(row)
        return ImportReviewItem.model_validate(row)

    def reject_import(
        self,
        *,
        batch_id: UUID,
        payload: ReviewDecisionRequest,
        admin_id: UUID,
        request_id: str | None,
    ) -> ImportReviewItem:
        row = self._import(batch_id)
        if row.status == "applied":
            raise ApiError(
                409,
                "provider_import_already_applied",
                "لا يمكن رفض دفعة بعد تطبيقها على دفتر التكاليف.",
            )
        row.review_status = "rejected"
        row.assigned_reviewer_id = admin_id
        row.reviewed_by_admin_id = admin_id
        row.review_note = payload.note.strip()
        row.reviewed_at = utc_now()
        self.audit.add(
            action="vendor.import_review.rejected",
            actor_user_id=admin_id,
            entity_type="provider_cost_import_batch",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"note": row.review_note},
        )
        self.db.commit()
        self.db.refresh(row)
        return ImportReviewItem.model_validate(row)

    # ------------------------------------------------------------------
    # Settlement operations queue
    # ------------------------------------------------------------------
    def settlement_operations(
        self,
        *,
        operations_status: str | None,
        status: str | None,
        limit: int,
    ) -> list[SettlementOperationsItem]:
        stmt = select(ProviderSettlementBatchEntity)
        if operations_status:
            stmt = stmt.where(
                ProviderSettlementBatchEntity.operations_status
                == operations_status
            )
        if status:
            stmt = stmt.where(
                ProviderSettlementBatchEntity.status == status
            )
        rows = list(
            self.db.scalars(
                stmt.order_by(
                    ProviderSettlementBatchEntity.created_at.asc()
                ).limit(limit)
            ).all()
        )
        return [
            SettlementOperationsItem.model_validate(x)
            for x in rows
        ]

    def assign_settlement(
        self,
        *,
        batch_id: UUID,
        payload: QueueAssignRequest,
        admin_id: UUID,
        request_id: str | None,
    ) -> SettlementOperationsItem:
        row = self._settlement(batch_id)
        if payload.admin_id is not None:
            self._admin(payload.admin_id)
        row.assigned_admin_id = payload.admin_id
        self.audit.add(
            action="vendor.settlement.assigned",
            actor_user_id=admin_id,
            entity_type="provider_settlement_batch",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "assigned_admin_id": (
                    str(payload.admin_id)
                    if payload.admin_id
                    else None
                )
            },
        )
        self.db.commit()
        self.db.refresh(row)
        return SettlementOperationsItem.model_validate(row)

    def _open_payment_issues_for_settlement(
        self,
        batch_id: UUID,
    ) -> int:
        payment_ids = list(
            self.db.scalars(
                select(ProviderSettlementLineEntity.matched_payment_id).where(
                    ProviderSettlementLineEntity.batch_id == batch_id,
                    ProviderSettlementLineEntity.matched_payment_id.is_not(None),
                )
            ).all()
        )
        if not payment_ids:
            return 0
        return int(
            self.db.scalar(
                select(func.count(PaymentReconciliationIssueEntity.id)).where(
                    PaymentReconciliationIssueEntity.payment_id.in_(payment_ids),
                    PaymentReconciliationIssueEntity.status == "open",
                )
            )
            or 0
        )

    def close_settlement(
        self,
        *,
        batch_id: UUID,
        payload: SettlementCloseRequest,
        admin_id: UUID,
        request_id: str | None,
    ) -> SettlementOperationsItem:
        row = self._settlement(batch_id)
        if row.status != "reconciled":
            raise ApiError(
                409,
                "settlement_not_reconciled",
                "لا يمكن إغلاق تسوية لم تجتز المطابقة.",
            )
        if row.mismatched_lines != 0 or row.matched_lines != row.rows_count:
            raise ApiError(
                409,
                "settlement_not_fully_matched",
                "لا يمكن إغلاق تسوية بها سطور غير مطابقة.",
            )
        open_issues = self._open_payment_issues_for_settlement(row.id)
        if open_issues:
            raise ApiError(
                409,
                "settlement_payment_reconciliation_open",
                "لا يمكن إغلاق التسوية قبل غلق اختلافات المدفوعات.",
                {"open_issues": open_issues},
            )
        if (
            self.settings.vendor_accounting_require_dual_control
            and row.created_by_admin_id == admin_id
        ):
            raise ApiError(
                409,
                "vendor_accounting_dual_control_required",
                "منشئ التسوية لا يمكنه إغلاقها في وضع maker-checker.",
            )

        row.operations_status = "closed"
        row.assigned_admin_id = admin_id
        row.closed_by_admin_id = admin_id
        row.close_note = payload.note.strip()
        row.closed_at = utc_now()
        self.audit.add(
            action="vendor.settlement.closed",
            actor_user_id=admin_id,
            entity_type="provider_settlement_batch",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={
                "fees_minor": row.fees_minor,
                "net_settlement_minor": row.net_settlement_minor,
            },
        )
        self.db.commit()
        self.db.refresh(row)
        return SettlementOperationsItem.model_validate(row)

    def reopen_settlement(
        self,
        *,
        batch_id: UUID,
        payload: SettlementCloseRequest,
        admin_id: UUID,
        request_id: str | None,
    ) -> SettlementOperationsItem:
        row = self._settlement(batch_id)
        if row.operations_status != "closed":
            raise ApiError(
                409,
                "settlement_not_closed",
                "يمكن إعادة فتح تسوية مغلقة فقط.",
            )
        row.operations_status = "reopened"
        row.assigned_admin_id = admin_id
        row.closed_by_admin_id = None
        row.closed_at = None
        row.close_note = payload.note.strip()
        self.audit.add(
            action="vendor.settlement.reopened",
            actor_user_id=admin_id,
            entity_type="provider_settlement_batch",
            entity_id=str(row.id),
            request_id=request_id,
            metadata={"note": row.close_note},
        )
        self.db.commit()
        self.db.refresh(row)
        return SettlementOperationsItem.model_validate(row)

    def summary(self) -> VendorAccountingSummary:
        import_rows = self.db.execute(
            select(
                ProviderCostImportBatchEntity.review_status,
                func.count(ProviderCostImportBatchEntity.id),
            ).group_by(ProviderCostImportBatchEntity.review_status)
        ).all()
        import_counts = {k: int(v) for k, v in import_rows}

        high_risk_open = sum(
            1
            for row in self.db.scalars(
                select(ProviderCostImportBatchEntity).where(
                    ProviderCostImportBatchEntity.review_status.in_(
                        ["pending", "assigned"]
                    )
                )
            ).all()
            if row.risk_flags_json
        )

        settlement_rows = self.db.execute(
            select(
                ProviderSettlementBatchEntity.operations_status,
                func.count(ProviderSettlementBatchEntity.id),
            ).group_by(ProviderSettlementBatchEntity.operations_status)
        ).all()
        settlement_counts = {k: int(v) for k, v in settlement_rows}
        blocked = int(
            self.db.scalar(
                select(func.count(ProviderSettlementBatchEntity.id)).where(
                    ProviderSettlementBatchEntity.status == "blocked"
                )
            )
            or 0
        )

        return VendorAccountingSummary(
            imports_pending_review=import_counts.get("pending", 0),
            imports_assigned=import_counts.get("assigned", 0),
            imports_approved=import_counts.get("approved", 0),
            imports_rejected=import_counts.get("rejected", 0),
            imports_high_risk_open=high_risk_open,
            settlements_open=settlement_counts.get("open", 0),
            settlements_in_review=settlement_counts.get("review", 0),
            settlements_closed=settlement_counts.get("closed", 0),
            settlements_reopened=settlement_counts.get("reopened", 0),
            settlements_blocked=blocked,
        )
