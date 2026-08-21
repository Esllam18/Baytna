from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.modules.loyalty.schemas import LoyaltyAccountResponse
from app.modules.loyalty.service import LoyaltyService

router = APIRouter(prefix="/customer/loyalty", tags=["loyalty"])


@router.get("", response_model=LoyaltyAccountResponse)
def loyalty_account(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LoyaltyAccountResponse:
    return LoyaltyService(db, settings).response(customer_id=user.id)
