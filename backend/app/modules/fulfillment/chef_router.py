from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.fulfillment.schemas import (
    AcceptOrderRequest,
    ChefNoteRequest,
    ChefOrderDetailResponse,
    ChefOrderListItemResponse,
    RejectOrderRequest,
)
from app.modules.fulfillment.service import FulfillmentService

router = APIRouter(prefix="/chef/orders", tags=["chef-orders"])


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FulfillmentService:
    return FulfillmentService(db, settings)


def chef_user(
    user: UserEntity = Depends(require_roles(UserRole.CHEF)),
) -> UserEntity:
    return user


@router.get("", response_model=list[ChefOrderListItemResponse])
def queue(
    stage: str | None = Query(default=None),
    chef: UserEntity = Depends(chef_user),
    svc: FulfillmentService = Depends(service),
) -> list[ChefOrderListItemResponse]:
    return svc.queue(
        chef_id=chef.id,
        stage=stage,
    )


@router.get("/{order_id}", response_model=ChefOrderDetailResponse)
def detail(
    order_id: UUID,
    chef: UserEntity = Depends(chef_user),
    svc: FulfillmentService = Depends(service),
) -> ChefOrderDetailResponse:
    return svc.detail(
        chef_id=chef.id,
        order_id=order_id,
    )


@router.post("/{order_id}/accept", response_model=ChefOrderDetailResponse)
def accept(
    order_id: UUID,
    payload: AcceptOrderRequest,
    request: Request,
    chef: UserEntity = Depends(chef_user),
    svc: FulfillmentService = Depends(service),
) -> ChefOrderDetailResponse:
    return svc.accept(
        chef_id=chef.id,
        order_id=order_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.post("/{order_id}/reject", response_model=ChefOrderDetailResponse)
def reject(
    order_id: UUID,
    payload: RejectOrderRequest,
    request: Request,
    chef: UserEntity = Depends(chef_user),
    svc: FulfillmentService = Depends(service),
) -> ChefOrderDetailResponse:
    return svc.reject(
        chef_id=chef.id,
        order_id=order_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.post(
    "/{order_id}/start-preparing",
    response_model=ChefOrderDetailResponse,
)
def start_preparing(
    order_id: UUID,
    payload: ChefNoteRequest,
    request: Request,
    chef: UserEntity = Depends(chef_user),
    svc: FulfillmentService = Depends(service),
) -> ChefOrderDetailResponse:
    return svc.start_preparing(
        chef_id=chef.id,
        order_id=order_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.post(
    "/{order_id}/start-packaging",
    response_model=ChefOrderDetailResponse,
)
def start_packaging(
    order_id: UUID,
    payload: ChefNoteRequest,
    request: Request,
    chef: UserEntity = Depends(chef_user),
    svc: FulfillmentService = Depends(service),
) -> ChefOrderDetailResponse:
    return svc.start_packaging(
        chef_id=chef.id,
        order_id=order_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.post(
    "/{order_id}/ready-for-pickup",
    response_model=ChefOrderDetailResponse,
)
def ready_for_pickup(
    order_id: UUID,
    payload: ChefNoteRequest,
    request: Request,
    chef: UserEntity = Depends(chef_user),
    svc: FulfillmentService = Depends(service),
) -> ChefOrderDetailResponse:
    return svc.ready_for_pickup(
        chef_id=chef.id,
        order_id=order_id,
        payload=payload,
        request_id=request.state.request_id,
    )
