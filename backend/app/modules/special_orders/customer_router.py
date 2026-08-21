from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.modules.special_orders.schemas import (
    SpecialOrderCheckoutRequest,
    SpecialOrderCheckoutResponse,
    SpecialOrderCreateRequest,
    SpecialOrderResponse,
)
from app.modules.special_orders.service import SpecialOrderService

router = APIRouter(prefix="/customer/special-orders", tags=["special-orders"])


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SpecialOrderService:
    return SpecialOrderService(db, settings)


@router.post("", response_model=SpecialOrderResponse, status_code=201)
def create_special_order(
    payload: SpecialOrderCreateRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    svc: SpecialOrderService = Depends(service),
) -> SpecialOrderResponse:
    return svc.create_request(
        customer_id=user.id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.get("", response_model=list[SpecialOrderResponse])
def list_special_orders(
    user: UserEntity = Depends(current_user),
    svc: SpecialOrderService = Depends(service),
) -> list[SpecialOrderResponse]:
    return svc.customer_list(customer_id=user.id)


@router.get("/{special_order_id}", response_model=SpecialOrderResponse)
def special_order_detail(
    special_order_id: UUID,
    user: UserEntity = Depends(current_user),
    svc: SpecialOrderService = Depends(service),
) -> SpecialOrderResponse:
    return svc.customer_detail(
        customer_id=user.id,
        special_order_id=special_order_id,
    )


@router.post(
    "/{special_order_id}/accept-counter-offer",
    response_model=SpecialOrderResponse,
)
def accept_counter_offer(
    special_order_id: UUID,
    request: Request,
    user: UserEntity = Depends(current_user),
    svc: SpecialOrderService = Depends(service),
) -> SpecialOrderResponse:
    return svc.accept_counter_offer(
        customer_id=user.id,
        special_order_id=special_order_id,
        request_id=request.state.request_id,
    )


@router.post(
    "/{special_order_id}/cancel",
    response_model=SpecialOrderResponse,
)
def cancel_special_order(
    special_order_id: UUID,
    request: Request,
    user: UserEntity = Depends(current_user),
    svc: SpecialOrderService = Depends(service),
) -> SpecialOrderResponse:
    return svc.cancel(
        customer_id=user.id,
        special_order_id=special_order_id,
        request_id=request.state.request_id,
    )


@router.post(
    "/{special_order_id}/checkout",
    response_model=SpecialOrderCheckoutResponse,
    status_code=201,
)
def checkout_special_order(
    special_order_id: UUID,
    payload: SpecialOrderCheckoutRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    svc: SpecialOrderService = Depends(service),
) -> SpecialOrderCheckoutResponse:
    return svc.checkout(
        customer_id=user.id,
        special_order_id=special_order_id,
        payload=payload,
        request_id=request.state.request_id,
    )
