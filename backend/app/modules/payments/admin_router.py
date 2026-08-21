from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.payments.schemas import RefundCreateRequest, RefundResponse
from app.modules.payments.service import PaymentService

router = APIRouter(
    prefix="/admin/orders",
    tags=["admin-payments"],
)


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PaymentService:
    return PaymentService(db, settings)


@router.post(
    "/{order_id}/refunds",
    response_model=RefundResponse,
    status_code=201,
)
def create_refund(
    order_id: UUID,
    payload: RefundCreateRequest,
    request: Request,
    admin: UserEntity = Depends(require_roles(UserRole.ADMIN)),
    svc: PaymentService = Depends(service),
) -> RefundResponse:
    return svc.create_refund(
        admin_user_id=admin.id,
        order_id=order_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.get(
    "/{order_id}/refunds",
    response_model=list[RefundResponse],
)
def refunds_for_order(
    order_id: UUID,
    _: UserEntity = Depends(require_roles(UserRole.ADMIN)),
    svc: PaymentService = Depends(service),
) -> list[RefundResponse]:
    return svc.refunds_for_order(order_id=order_id)
