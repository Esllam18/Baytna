from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.notification_delivery.schemas import NotificationDeliveryResponse
from app.modules.notification_delivery.service import NotificationDeliveryService

router = APIRouter(
    prefix="/admin/notification-deliveries",
    tags=["admin-notification-deliveries"],
)


@router.get("", response_model=list[NotificationDeliveryResponse])
def list_deliveries(
    status: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: UserEntity = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[NotificationDeliveryResponse]:
    return NotificationDeliveryService(db, settings).list_deliveries(
        status=status,
        channel=channel,
        limit=limit,
    )


@router.post(
    "/{delivery_id}/retry",
    response_model=NotificationDeliveryResponse,
)
def retry_delivery(
    delivery_id: UUID,
    _: UserEntity = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> NotificationDeliveryResponse:
    return NotificationDeliveryService(db, settings).retry(
        delivery_id=delivery_id
    )


@router.post("/reconcile")
def reconcile(_: UserEntity = Depends(require_roles(UserRole.ADMIN)), db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> dict:
    return NotificationDeliveryService(db, settings).reconcile()
