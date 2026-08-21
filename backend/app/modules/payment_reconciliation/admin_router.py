from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.payment_reconciliation.service import PaymentReconciliationService
from app.modules.payments.schemas import (
    PaymentProviderTransactionResponse,
    PaymentReconciliationIssueResponse,
    ReconciliationResolveRequest,
    ReconciliationRunResponse,
)

router = APIRouter(
    prefix="/admin/payments/reconciliation",
    tags=["admin-payment-reconciliation"],
)


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PaymentReconciliationService:
    return PaymentReconciliationService(db, settings)


@router.get("/summary")
def summary(
    _: UserEntity = Depends(require_roles(UserRole.ADMIN)),
    svc: PaymentReconciliationService = Depends(service),
) -> dict:
    return svc.summary()


@router.get(
    "/issues",
    response_model=list[PaymentReconciliationIssueResponse],
)
def issues(
    status: str | None = Query(default=None),
    issue_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: UserEntity = Depends(require_roles(UserRole.ADMIN)),
    svc: PaymentReconciliationService = Depends(service),
) -> list[PaymentReconciliationIssueResponse]:
    return svc.list_issues(
        status=status,
        issue_type=issue_type,
        limit=limit,
    )


@router.post("/run", response_model=ReconciliationRunResponse)
def run_reconciliation(
    _: UserEntity = Depends(require_roles(UserRole.ADMIN)),
    svc: PaymentReconciliationService = Depends(service),
) -> ReconciliationRunResponse:
    return svc.run()


@router.post(
    "/issues/{issue_id}/resolve",
    response_model=PaymentReconciliationIssueResponse,
)
def resolve_issue(
    issue_id: UUID,
    payload: ReconciliationResolveRequest,
    request: Request,
    admin: UserEntity = Depends(require_roles(UserRole.ADMIN)),
    svc: PaymentReconciliationService = Depends(service),
) -> PaymentReconciliationIssueResponse:
    return svc.resolve_issue(
        issue_id=issue_id,
        admin_user_id=admin.id,
        note=payload.note,
        request_id=request.state.request_id,
    )


@router.get(
    "/payments/{payment_id}/provider-transactions",
    response_model=list[PaymentProviderTransactionResponse],
)
def provider_transactions(
    payment_id: UUID,
    _: UserEntity = Depends(require_roles(UserRole.ADMIN)),
    svc: PaymentReconciliationService = Depends(service),
) -> list[PaymentProviderTransactionResponse]:
    return svc.provider_transactions(payment_id=payment_id)
