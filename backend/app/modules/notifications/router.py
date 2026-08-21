from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.modules.notifications.schemas import (
    NotificationResponse,
    NotificationSummaryResponse,
)
from app.modules.notifications.service import NotificationService

router = APIRouter(prefix="/customer/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[NotificationResponse]:
    return NotificationService(db, settings).list_for_user(
        user_id=user.id,
        unread_only=unread_only,
        limit=limit,
    )


@router.get("/summary", response_model=NotificationSummaryResponse)
def summary(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> NotificationSummaryResponse:
    return NotificationService(db, settings).summary(user_id=user.id)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_read(
    notification_id: UUID,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> NotificationResponse:
    return NotificationService(db, settings).mark_read(
        user_id=user.id,
        notification_id=notification_id,
    )


@router.post("/read-all")
def mark_all_read(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    count = NotificationService(db, settings).mark_all_read(user_id=user.id)
    return {"updated": count}
