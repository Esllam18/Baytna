from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.driver_app.schemas import (
    DriverAppDashboardResponse,
    DriverSelfProfileResponse,
)
from app.modules.driver_app.service import DriverAppService

router = APIRouter(prefix="/driver", tags=["driver-app"])


def driver_user(
    user: UserEntity = Depends(require_roles(UserRole.DRIVER)),
) -> UserEntity:
    return user


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DriverAppService:
    return DriverAppService(db, settings)


@router.get("/profile", response_model=DriverSelfProfileResponse)
def profile(
    driver: UserEntity = Depends(driver_user),
    svc: DriverAppService = Depends(service),
) -> DriverSelfProfileResponse:
    return svc.profile(driver_id=driver.id)


@router.get("/app-dashboard", response_model=DriverAppDashboardResponse)
def app_dashboard(
    driver: UserEntity = Depends(driver_user),
    svc: DriverAppService = Depends(service),
) -> DriverAppDashboardResponse:
    return svc.dashboard(driver_id=driver.id)
