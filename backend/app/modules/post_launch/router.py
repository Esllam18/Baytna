from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.post_launch.schemas import ExpansionReviewResponse, PostLaunchSummary
from app.modules.post_launch.service import PostLaunchStabilizationService


router = APIRouter(prefix="/admin/post-launch", tags=["admin-post-launch"])


def admin_user(user: UserEntity = Depends(require_roles(UserRole.ADMIN))) -> UserEntity:
    return user


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PostLaunchStabilizationService:
    return PostLaunchStabilizationService(db, settings)


@router.get("/reviews", response_model=list[ExpansionReviewResponse])
def reviews(
    zone_id: UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    _: UserEntity = Depends(admin_user),
    svc: PostLaunchStabilizationService = Depends(service),
) -> list[ExpansionReviewResponse]:
    return svc.reviews(zone_id=zone_id, limit=limit)


@router.post("/zones/{zone_id}/review", response_model=ExpansionReviewResponse)
def refresh_review(
    zone_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: PostLaunchStabilizationService = Depends(service),
) -> ExpansionReviewResponse:
    return svc.refresh_review(zone_id=zone_id, generated_by="admin")


@router.get("/summary", response_model=PostLaunchSummary)
def summary(
    _: UserEntity = Depends(admin_user),
    svc: PostLaunchStabilizationService = Depends(service),
) -> PostLaunchSummary:
    return svc.summary()
