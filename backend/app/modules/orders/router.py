from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.modules.orders.schemas import (
    AddCartItemRequest,
    CartResponse,
    CreateOrderRequest,
    OrderListItemResponse,
    OrderResponse,
    UpdateCartItemRequest,
)
from app.modules.orders.service import OrderService

router = APIRouter(prefix="/customer", tags=["customer-orders"])


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderService:
    return OrderService(db, settings)


@router.get("/cart", response_model=CartResponse)
def get_cart(
    user: UserEntity = Depends(current_user),
    svc: OrderService = Depends(service),
) -> CartResponse:
    return svc.get_cart(customer_id=user.id)


@router.post("/cart/items", response_model=CartResponse, status_code=201)
def add_cart_item(
    payload: AddCartItemRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    svc: OrderService = Depends(service),
) -> CartResponse:
    return svc.add_cart_item(
        customer_id=user.id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.patch("/cart/items/{cart_item_id}", response_model=CartResponse)
def update_cart_item(
    cart_item_id: UUID,
    payload: UpdateCartItemRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    svc: OrderService = Depends(service),
) -> CartResponse:
    return svc.update_cart_item(
        customer_id=user.id,
        cart_item_id=cart_item_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.delete("/cart/items/{cart_item_id}", response_model=CartResponse)
def remove_cart_item(
    cart_item_id: UUID,
    request: Request,
    user: UserEntity = Depends(current_user),
    svc: OrderService = Depends(service),
) -> CartResponse:
    return svc.remove_cart_item(
        customer_id=user.id,
        cart_item_id=cart_item_id,
        request_id=request.state.request_id,
    )


@router.delete("/cart", response_model=CartResponse)
def clear_cart(
    request: Request,
    user: UserEntity = Depends(current_user),
    svc: OrderService = Depends(service),
) -> CartResponse:
    return svc.clear_cart(
        customer_id=user.id,
        request_id=request.state.request_id,
    )


@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    payload: CreateOrderRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    svc: OrderService = Depends(service),
) -> OrderResponse:
    return svc.create_pending_order(
        customer_id=user.id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.get("/orders", response_model=list[OrderListItemResponse])
def list_orders(
    user: UserEntity = Depends(current_user),
    svc: OrderService = Depends(service),
) -> list[OrderListItemResponse]:
    return svc.list_orders(customer_id=user.id)


@router.get("/orders/{order_id}", response_model=OrderResponse)
def order_detail(
    order_id: UUID,
    user: UserEntity = Depends(current_user),
    svc: OrderService = Depends(service),
) -> OrderResponse:
    return svc.order_detail(
        customer_id=user.id,
        order_id=order_id,
    )


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: UUID,
    request: Request,
    user: UserEntity = Depends(current_user),
    svc: OrderService = Depends(service),
) -> OrderResponse:
    return svc.cancel_pending_order(
        customer_id=user.id,
        order_id=order_id,
        request_id=request.state.request_id,
    )
