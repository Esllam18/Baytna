from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.delivery.schemas import (
    DeliveryIssueRequest,
    DeliveryMissionResponse,
    DeliveryProofRequest,
    DriverAvailabilityRequest,
    DriverStatusResponse,
)
from app.modules.delivery.service import DeliveryService

router = APIRouter(prefix="/driver", tags=["driver"])


def driver_user(
    user: UserEntity = Depends(require_roles(UserRole.DRIVER)),
) -> UserEntity:
    return user


@router.get("/status", response_model=DriverStatusResponse)
def status(
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DriverStatusResponse:
    return DeliveryService(db, settings).status(driver_id=driver.id)


@router.put("/availability", response_model=DriverStatusResponse)
def availability(
    payload: DriverAvailabilityRequest,
    request: Request,
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DriverStatusResponse:
    return DeliveryService(db, settings).set_availability(
        driver_id=driver.id,
        available=payload.available,
        request_id=request.state.request_id,
    )


@router.get(
    "/missions/available",
    response_model=list[DeliveryMissionResponse],
)
def available_missions(
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[DeliveryMissionResponse]:
    return DeliveryService(db, settings).available_missions(driver_id=driver.id)


@router.get(
    "/missions/available/{task_id}",
    response_model=DeliveryMissionResponse,
)
def available_mission_detail(
    task_id: UUID,
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryMissionResponse:
    return DeliveryService(db, settings).available_mission_detail(
        driver_id=driver.id,
        task_id=task_id,
    )


@router.get("/missions/current", response_model=DeliveryMissionResponse)
def current_mission(
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryMissionResponse:
    return DeliveryService(db, settings).current_mission(driver_id=driver.id)


@router.get(
    "/missions/history",
    response_model=list[DeliveryMissionResponse],
)
def history(
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[DeliveryMissionResponse]:
    return DeliveryService(db, settings).history(driver_id=driver.id)


@router.get(
    "/missions/{task_id}",
    response_model=DeliveryMissionResponse,
)
def mission_detail(
    task_id: UUID,
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryMissionResponse:
    return DeliveryService(db, settings).mission_detail(
        driver_id=driver.id,
        task_id=task_id,
    )


@router.post(
    "/missions/{task_id}/accept",
    response_model=DeliveryMissionResponse,
)
def accept(
    task_id: UUID,
    request: Request,
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryMissionResponse:
    return DeliveryService(db, settings).accept_mission(
        driver_id=driver.id,
        task_id=task_id,
        request_id=request.state.request_id,
    )


@router.post(
    "/missions/{task_id}/arrive-pickup",
    response_model=DeliveryMissionResponse,
)
def arrive_pickup(
    task_id: UUID,
    request: Request,
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryMissionResponse:
    return DeliveryService(db, settings).arrive_pickup(
        driver_id=driver.id,
        task_id=task_id,
        request_id=request.state.request_id,
    )


@router.post(
    "/missions/{task_id}/confirm-pickup",
    response_model=DeliveryMissionResponse,
)
def confirm_pickup(
    task_id: UUID,
    request: Request,
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryMissionResponse:
    return DeliveryService(db, settings).confirm_pickup(
        driver_id=driver.id,
        task_id=task_id,
        request_id=request.state.request_id,
    )


@router.post(
    "/missions/{task_id}/start-delivery",
    response_model=DeliveryMissionResponse,
)
def start_delivery(
    task_id: UUID,
    request: Request,
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryMissionResponse:
    return DeliveryService(db, settings).start_delivery(
        driver_id=driver.id,
        task_id=task_id,
        request_id=request.state.request_id,
    )


@router.post(
    "/missions/{task_id}/deliver",
    response_model=DeliveryMissionResponse,
)
def deliver(
    task_id: UUID,
    payload: DeliveryProofRequest,
    request: Request,
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryMissionResponse:
    return DeliveryService(db, settings).mark_delivered(
        driver_id=driver.id,
        task_id=task_id,
        proof=payload,
        request_id=request.state.request_id,
    )


@router.post(
    "/missions/{task_id}/issue",
    response_model=DeliveryMissionResponse,
)
def report_issue(
    task_id: UUID,
    payload: DeliveryIssueRequest,
    request: Request,
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryMissionResponse:
    return DeliveryService(db, settings).report_issue(
        driver_id=driver.id,
        task_id=task_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.post(
    "/missions/{task_id}/resume",
    response_model=DeliveryMissionResponse,
)
def resume(
    task_id: UUID,
    request: Request,
    driver: UserEntity = Depends(driver_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DeliveryMissionResponse:
    return DeliveryService(db, settings).resume_after_issue(
        driver_id=driver.id,
        task_id=task_id,
        request_id=request.state.request_id,
    )
