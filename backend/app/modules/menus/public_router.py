from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.menus.schemas import DishResponse, TodayMenuResponse
from app.modules.menus.service import MenuService

router = APIRouter(tags=["menus"])


@router.get(
    "/chefs/{chef_id}/signature-menu",
    response_model=list[DishResponse],
)
def signature_menu(
    chef_id: UUID,
    db: Session = Depends(get_db),
) -> list[DishResponse]:
    return MenuService(db).list_signature(
        chef_id=chef_id,
        include_inactive=False,
        owner_view=False,
    )


@router.get(
    "/chefs/{chef_id}/today-menu",
    response_model=TodayMenuResponse,
)
def today_menu(
    chef_id: UUID,
    service_date: date = Query(default_factory=date.today, alias="date"),
    db: Session = Depends(get_db),
) -> TodayMenuResponse:
    return MenuService(db).today_menu(
        chef_id=chef_id,
        service_date=service_date,
        owner_view=False,
    )
