from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ApiError
from app.core.models import ChefSummary
from app.core.repositories import ChefRepository

router = APIRouter(prefix="/chefs", tags=["chefs"])


def to_summary(chef) -> ChefSummary:
    return ChefSummary(
        id=chef.user_id,
        display_name=chef.display_name,
        specialty=chef.specialty,
        area=chef.area,
        rating=chef.rating,
        is_verified=chef.is_verified,
        is_open_today=chef.is_open_today,
    )


@router.get("", response_model=list[ChefSummary])
def list_chefs(
    area: str | None = None,
    open_today: bool | None = None,
    db: Session = Depends(get_db),
) -> list[ChefSummary]:
    chefs = ChefRepository(db).list(area=area, open_today=open_today)
    return [to_summary(x) for x in chefs]


@router.get("/{chef_id}", response_model=ChefSummary)
def get_chef(
    chef_id: UUID,
    db: Session = Depends(get_db),
) -> ChefSummary:
    chef = ChefRepository(db).get(chef_id)
    if chef is None:
        raise ApiError(404, "chef_not_found", "الشيف غير موجود.")
    return to_summary(chef)
