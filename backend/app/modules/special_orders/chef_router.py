from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.special_orders.schemas import (
    ChefAcceptSpecialOrderRequest,
    ChefCounterOfferRequest,
    ChefRejectSpecialOrderRequest,
    ScheduleOverrideRequest,
    ScheduleOverrideResponse,
    SpecialOrderResponse,
    WeeklyScheduleDayResponse,
    WeeklyScheduleUpsertRequest,
)
from app.modules.special_orders.service import SpecialOrderService

router = APIRouter(prefix="/chef", tags=["chef-special-orders"])


def chef_user(
    user: UserEntity = Depends(require_roles(UserRole.CHEF)),
) -> UserEntity:
    return user


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SpecialOrderService:
    return SpecialOrderService(db, settings)


@router.put("/schedule/weekly", response_model=list[WeeklyScheduleDayResponse])
def upsert_weekly_schedule(
    payload: WeeklyScheduleUpsertRequest,
    request: Request,
    chef: UserEntity = Depends(chef_user),
    svc: SpecialOrderService = Depends(service),
) -> list[WeeklyScheduleDayResponse]:
    return svc.upsert_weekly_schedule(
        chef_id=chef.id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.get("/schedule/weekly", response_model=list[WeeklyScheduleDayResponse])
def weekly_schedule(
    chef: UserEntity = Depends(chef_user),
    svc: SpecialOrderService = Depends(service),
) -> list[WeeklyScheduleDayResponse]:
    return svc.weekly_schedule(chef_id=chef.id)


@router.put(
    "/schedule/overrides/{service_date}",
    response_model=ScheduleOverrideResponse,
)
def upsert_override(
    service_date: date,
    payload: ScheduleOverrideRequest,
    request: Request,
    chef: UserEntity = Depends(chef_user),
    svc: SpecialOrderService = Depends(service),
) -> ScheduleOverrideResponse:
    return svc.upsert_override(
        chef_id=chef.id,
        service_date=service_date,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.get(
    "/schedule/overrides",
    response_model=list[ScheduleOverrideResponse],
)
def list_overrides(
    chef: UserEntity = Depends(chef_user),
    svc: SpecialOrderService = Depends(service),
) -> list[ScheduleOverrideResponse]:
    return svc.list_overrides(chef_id=chef.id)


@router.get("/special-orders", response_model=list[SpecialOrderResponse])
def special_order_queue(
    status: str | None = Query(default=None),
    chef: UserEntity = Depends(chef_user),
    svc: SpecialOrderService = Depends(service),
) -> list[SpecialOrderResponse]:
    return svc.chef_queue(chef_id=chef.id, status=status)


@router.get(
    "/special-orders/{special_order_id}",
    response_model=SpecialOrderResponse,
)
def special_order_detail(
    special_order_id: UUID,
    chef: UserEntity = Depends(chef_user),
    svc: SpecialOrderService = Depends(service),
) -> SpecialOrderResponse:
    return svc.chef_detail(
        chef_id=chef.id,
        special_order_id=special_order_id,
    )


@router.post(
    "/special-orders/{special_order_id}/accept",
    response_model=SpecialOrderResponse,
)
def accept_special_order(
    special_order_id: UUID,
    payload: ChefAcceptSpecialOrderRequest,
    request: Request,
    chef: UserEntity = Depends(chef_user),
    svc: SpecialOrderService = Depends(service),
) -> SpecialOrderResponse:
    return svc.chef_accept(
        chef_id=chef.id,
        special_order_id=special_order_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.post(
    "/special-orders/{special_order_id}/counter-offer",
    response_model=SpecialOrderResponse,
)
def counter_offer(
    special_order_id: UUID,
    payload: ChefCounterOfferRequest,
    request: Request,
    chef: UserEntity = Depends(chef_user),
    svc: SpecialOrderService = Depends(service),
) -> SpecialOrderResponse:
    return svc.chef_counter_offer(
        chef_id=chef.id,
        special_order_id=special_order_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.post(
    "/special-orders/{special_order_id}/reject",
    response_model=SpecialOrderResponse,
)
def reject_special_order(
    special_order_id: UUID,
    payload: ChefRejectSpecialOrderRequest,
    request: Request,
    chef: UserEntity = Depends(chef_user),
    svc: SpecialOrderService = Depends(service),
) -> SpecialOrderResponse:
    return svc.chef_reject(
        chef_id=chef.id,
        special_order_id=special_order_id,
        payload=payload,
        request_id=request.state.request_id,
    )
