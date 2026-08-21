from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.modules.delivery.schemas import DeliveryTrackingResponse
from app.modules.delivery.service import DeliveryService

router = APIRouter(prefix="/customer/orders", tags=["delivery-tracking"])


@router.get(
    "/{order_id}/delivery-tracking",
    response_model=DeliveryTrackingResponse,
)
def delivery_tracking(
    order_id: UUID,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryTrackingResponse:
    return DeliveryService(db, settings).customer_tracking(
        customer_id=user.id,
        order_id=order_id,
    )
