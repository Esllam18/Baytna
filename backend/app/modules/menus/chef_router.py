from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.menus.schemas import (
    ChefDashboardResponse,
    DailyMenuItemResponse,
    DailyMenuReplaceRequest,
    DishCreateRequest,
    DishMediaRequest,
    DishResponse,
    DishUpdateRequest,
    OpenKitchenRequest,
    QuantityUpdateRequest,
    TodayMenuResponse,
    WorkdayResponse,
)
from app.modules.menus.service import MenuService

router = APIRouter(prefix="/chef", tags=["chef"])


def chef_user(
    user: UserEntity = Depends(require_roles(UserRole.CHEF)),
) -> UserEntity:
    return user


@router.get("/dashboard", response_model=ChefDashboardResponse)
def dashboard(
    service_date: date = Query(default_factory=date.today, alias="date"),
    user: UserEntity = Depends(chef_user),
    db: Session = Depends(get_db),
) -> ChefDashboardResponse:
    return MenuService(db).dashboard(
        chef_id=user.id,
        service_date=service_date,
    )


@router.get("/signature-menu", response_model=list[DishResponse])
def owner_signature_menu(
    include_inactive: bool = False,
    user: UserEntity = Depends(chef_user),
    db: Session = Depends(get_db),
) -> list[DishResponse]:
    return MenuService(db).list_signature(
        chef_id=user.id,
        include_inactive=include_inactive,
        owner_view=True,
    )


@router.post("/signature-menu", response_model=DishResponse, status_code=201)
def create_signature_dish(
    payload: DishCreateRequest,
    request: Request,
    user: UserEntity = Depends(chef_user),
    db: Session = Depends(get_db),
) -> DishResponse:
    return MenuService(db).create_dish(
        chef_id=user.id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.patch("/signature-menu/{dish_id}", response_model=DishResponse)
def update_signature_dish(
    dish_id: UUID,
    payload: DishUpdateRequest,
    request: Request,
    user: UserEntity = Depends(chef_user),
    db: Session = Depends(get_db),
) -> DishResponse:
    return MenuService(db).update_dish(
        chef_id=user.id,
        dish_id=dish_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.put("/signature-menu/{dish_id}/media", response_model=DishResponse)
def set_signature_dish_media(
    dish_id: UUID, payload: DishMediaRequest, request: Request,
    user: UserEntity = Depends(chef_user), db: Session = Depends(get_db),
) -> DishResponse:
    return MenuService(db).set_dish_media(chef_id=user.id, dish_id=dish_id, payload=payload, request_id=request.state.request_id)


@router.post("/workdays/open", response_model=WorkdayResponse)
def open_kitchen(
    payload: OpenKitchenRequest,
    request: Request,
    user: UserEntity = Depends(chef_user),
    db: Session = Depends(get_db),
) -> WorkdayResponse:
    return MenuService(db).open_kitchen(
        chef_id=user.id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.post("/workdays/{service_date}/close", response_model=WorkdayResponse)
def close_kitchen(
    service_date: date,
    request: Request,
    user: UserEntity = Depends(chef_user),
    db: Session = Depends(get_db),
) -> WorkdayResponse:
    return MenuService(db).close_kitchen(
        chef_id=user.id,
        service_date=service_date,
        request_id=request.state.request_id,
    )


@router.put("/today-menu", response_model=TodayMenuResponse)
def replace_today_menu(
    payload: DailyMenuReplaceRequest,
    request: Request,
    user: UserEntity = Depends(chef_user),
    db: Session = Depends(get_db),
) -> TodayMenuResponse:
    return MenuService(db).replace_today_menu(
        chef_id=user.id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.get("/today-menu", response_model=TodayMenuResponse)
def owner_today_menu(
    service_date: date = Query(default_factory=date.today, alias="date"),
    user: UserEntity = Depends(chef_user),
    db: Session = Depends(get_db),
) -> TodayMenuResponse:
    return MenuService(db).today_menu(
        chef_id=user.id,
        service_date=service_date,
        owner_view=True,
    )


@router.patch(
    "/today-menu/{item_id}/quantity",
    response_model=DailyMenuItemResponse,
)
def update_available_quantity(
    item_id: UUID,
    payload: QuantityUpdateRequest,
    request: Request,
    user: UserEntity = Depends(chef_user),
    db: Session = Depends(get_db),
) -> DailyMenuItemResponse:
    return MenuService(db).update_quantity(
        chef_id=user.id,
        item_id=item_id,
        payload=payload,
        request_id=request.state.request_id,
    )
