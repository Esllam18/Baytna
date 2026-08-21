from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.modules.favorites.service import FavoriteService
from app.modules.loyalty.service import LoyaltyService
from app.modules.notifications.service import NotificationService

router = APIRouter(prefix="/customer/retention", tags=["retention"])


@router.get("/summary")
def retention_summary(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    favorites = FavoriteService(db).summary(customer_id=user.id)
    loyalty = LoyaltyService(db, settings).response(customer_id=user.id)
    notifications = NotificationService(db).summary(user_id=user.id)

    return {
        "favorites": favorites.model_dump(mode="json"),
        "loyalty": {
            "balance_points": loyalty.balance_points,
            "lifetime_earned_points": loyalty.lifetime_earned_points,
        },
        "notifications": {
            "unread_count": notifications.unread_count,
        },
    }
