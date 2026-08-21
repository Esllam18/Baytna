from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.vendor_accounting.schemas import (
    ImportReviewItem,
    QueueAssignRequest,
    ReviewDecisionRequest,
    SettlementCloseRequest,
    SettlementOperationsItem,
    VendorAccountingSummary,
)
from app.modules.vendor_accounting.service import VendorAccountingService

router = APIRouter(
    prefix="/admin/vendor-accounting",
    tags=["admin-vendor-accounting"],
)


def admin_user(
    user: UserEntity = Depends(require_roles(UserRole.ADMIN)),
) -> UserEntity:
    return user


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> VendorAccountingService:
    return VendorAccountingService(db, settings)


@router.get("/summary", response_model=VendorAccountingSummary)
def summary(
    _: UserEntity = Depends(admin_user),
    svc: VendorAccountingService = Depends(service),
) -> VendorAccountingSummary:
    return svc.summary()


@router.get(
    "/import-reviews",
    response_model=list[ImportReviewItem],
)
def import_reviews(
    review_status: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    _: UserEntity = Depends(admin_user),
    svc: VendorAccountingService = Depends(service),
) -> list[ImportReviewItem]:
    return svc.import_reviews(
        review_status=review_status,
        provider=provider,
        limit=limit,
    )


@router.post(
    "/imports/{batch_id}/assign",
    response_model=ImportReviewItem,
)
def assign_import(
    batch_id: UUID,
    payload: QueueAssignRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: VendorAccountingService = Depends(service),
) -> ImportReviewItem:
    return svc.assign_import(
        batch_id=batch_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/imports/{batch_id}/approve",
    response_model=ImportReviewItem,
)
def approve_import(
    batch_id: UUID,
    payload: ReviewDecisionRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: VendorAccountingService = Depends(service),
) -> ImportReviewItem:
    return svc.approve_import(
        batch_id=batch_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/imports/{batch_id}/reject",
    response_model=ImportReviewItem,
)
def reject_import(
    batch_id: UUID,
    payload: ReviewDecisionRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: VendorAccountingService = Depends(service),
) -> ImportReviewItem:
    return svc.reject_import(
        batch_id=batch_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get(
    "/settlements",
    response_model=list[SettlementOperationsItem],
)
def settlements(
    operations_status: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    _: UserEntity = Depends(admin_user),
    svc: VendorAccountingService = Depends(service),
) -> list[SettlementOperationsItem]:
    return svc.settlement_operations(
        operations_status=operations_status,
        status=status,
        limit=limit,
    )


@router.post(
    "/settlements/{batch_id}/assign",
    response_model=SettlementOperationsItem,
)
def assign_settlement(
    batch_id: UUID,
    payload: QueueAssignRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: VendorAccountingService = Depends(service),
) -> SettlementOperationsItem:
    return svc.assign_settlement(
        batch_id=batch_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/settlements/{batch_id}/close",
    response_model=SettlementOperationsItem,
)
def close_settlement(
    batch_id: UUID,
    payload: SettlementCloseRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: VendorAccountingService = Depends(service),
) -> SettlementOperationsItem:
    return svc.close_settlement(
        batch_id=batch_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/settlements/{batch_id}/reopen",
    response_model=SettlementOperationsItem,
)
def reopen_settlement(
    batch_id: UUID,
    payload: SettlementCloseRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: VendorAccountingService = Depends(service),
) -> SettlementOperationsItem:
    return svc.reopen_settlement(
        batch_id=batch_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )
