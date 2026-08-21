from datetime import date

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.database import get_db
from app.core.db_models import ChefProfileEntity, UserEntity
from app.core.repositories import ChefRepository
from app.modules.menus.service import MenuService
from app.modules.users.customer_schemas import (
    CustomerProfileResponse,
    CustomerProfileUpdateRequest,
)
from app.modules.users.customer_service import CustomerAccountService

router = APIRouter(prefix="/customer", tags=["customer"])




@router.get("/profile", response_model=CustomerProfileResponse)
def customer_profile(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> CustomerProfileResponse:
    return CustomerAccountService(db).profile(user_id=user.id)


@router.patch("/profile", response_model=CustomerProfileResponse)
def update_customer_profile(
    payload: CustomerProfileUpdateRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> CustomerProfileResponse:
    return CustomerAccountService(db).update_profile(
        user_id=user.id,
        payload=payload,
        request_id=request.state.request_id,
    )

@router.get("/home")
def customer_home(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    chefs = ChefRepository(db).list(
        area="6 أكتوبر",
        open_today=True,
    )

    today_items = []
    service = MenuService(db)
    today = date.today()

    for chef in chefs:
        menu = service.today_menu(
            chef_id=chef.user_id,
            service_date=today,
            owner_view=False,
        )
        for item in menu.items:
            if item.status == "hidden":
                continue
            today_items.append(
                {
                    **item.model_dump(mode="json"),
                    "chef_id": str(chef.user_id),
                    "chef_name": chef.display_name,
                }
            )

    return {
        "customer": {"id": str(user.id), "phone": user.phone},
        "area": "6 أكتوبر",
        "featured_chefs": [
            {
                "id": str(chef.user_id),
                "display_name": chef.display_name,
                "specialty": chef.specialty,
                "area": chef.area,
                "rating": chef.rating,
                "is_verified": chef.is_verified,
                "is_open_today": chef.is_open_today,
            }
            for chef in chefs[:5]
        ],
        "today": {
            "title": "مطبخ اليوم",
            "service_date": today.isoformat(),
            "items": today_items[:20],
        },
    }
