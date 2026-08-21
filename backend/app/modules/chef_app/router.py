from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.chef_app.schemas import (
    ChefAppDashboardResponse,
    ChefSelfProfileResponse,
)
from app.modules.chef_app.service import ChefAppService

router = APIRouter(prefix="/chef", tags=["chef-app"])


def chef_user(
    user: UserEntity = Depends(require_roles(UserRole.CHEF)),
) -> UserEntity:
    return user


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ChefAppService:
    return ChefAppService(db, settings)


@router.get("/profile", response_model=ChefSelfProfileResponse)
def profile(
    chef: UserEntity = Depends(chef_user),
    svc: ChefAppService = Depends(service),
) -> ChefSelfProfileResponse:
    return svc.profile(chef_id=chef.id)


@router.get("/app-dashboard", response_model=ChefAppDashboardResponse)
def app_dashboard(
    service_date: date = Query(default_factory=date.today, alias="date"),
    chef: UserEntity = Depends(chef_user),
    svc: ChefAppService = Depends(service),
) -> ChefAppDashboardResponse:
    return svc.dashboard(
        chef_id=chef.id,
        service_date=service_date,
    )
