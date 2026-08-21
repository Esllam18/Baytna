from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.modules.fulfillment.schemas import CustomerTrackingResponse
from app.modules.fulfillment.service import FulfillmentService

router = APIRouter(prefix="/customer/orders", tags=["order-tracking"])


@router.get(
    "/{order_id}/tracking",
    response_model=CustomerTrackingResponse,
)
def tracking(
    order_id: UUID,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CustomerTrackingResponse:
    return FulfillmentService(db, settings).tracking(
        customer_id=user.id,
        order_id=order_id,
    )
