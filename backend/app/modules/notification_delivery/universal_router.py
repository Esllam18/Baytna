from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.modules.notification_delivery.schemas import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    PushDeviceRegisterRequest,
    PushDeviceResponse,
)
from app.modules.notification_delivery.service import NotificationDeliveryService

router = APIRouter(
    prefix="/notifications",
    tags=["notification-integrations"],
)


@router.post(
    "/devices",
    response_model=PushDeviceResponse,
    status_code=201,
)
def register_device(
    payload: PushDeviceRegisterRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PushDeviceResponse:
    return NotificationDeliveryService(db, settings).register_device(
        user_id=user.id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.get("/devices", response_model=list[PushDeviceResponse])
def list_devices(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[PushDeviceResponse]:
    return NotificationDeliveryService(db, settings).list_devices(
        user_id=user.id
    )


@router.delete("/devices/{device_id}", status_code=204)
def deactivate_device(
    device_id: UUID,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    NotificationDeliveryService(db, settings).deactivate_device(
        user_id=user.id,
        device_id=device_id,
        request_id=request.state.request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/preferences",
    response_model=NotificationPreferenceResponse,
)
def preferences(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> NotificationPreferenceResponse:
    return NotificationDeliveryService(db, settings).preferences(
        user_id=user.id
    )


@router.put(
    "/preferences",
    response_model=NotificationPreferenceResponse,
)
def update_preferences(
    payload: NotificationPreferenceUpdateRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> NotificationPreferenceResponse:
    return NotificationDeliveryService(db, settings).update_preferences(
        user_id=user.id,
        payload=payload,
        request_id=request.state.request_id,
    )
