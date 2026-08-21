from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.modules.special_orders.schemas import AvailabilityDayResponse
from app.modules.special_orders.service import SpecialOrderService

router = APIRouter(tags=["special-order-availability"])


@router.get(
    "/chefs/{chef_id}/availability",
    response_model=list[AvailabilityDayResponse],
)
def chef_availability(
    chef_id: UUID,
    start_date: date = Query(default_factory=date.today),
    days: int = Query(default=14, ge=1, le=60),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[AvailabilityDayResponse]:
    return SpecialOrderService(db, settings).availability(
        chef_id=chef_id,
        start_date=start_date,
        days=days,
    )
