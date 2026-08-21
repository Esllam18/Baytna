from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.database import get_db
from app.core.db_models import (
    RateLimitBucketEntity,
    SecurityEventEntity,
    UserEntity,
)
from app.core.models import UserRole
from app.modules.observability.metrics import metrics_registry
from app.modules.security_hardening.schemas import (
    RateLimitBucketResponse,
    SecurityEventResponse,
)

router = APIRouter(prefix="/admin/observability", tags=["admin-observability"])


def admin_user(
    user: UserEntity = Depends(require_roles(UserRole.ADMIN)),
) -> UserEntity:
    return user


@router.get("/summary")
def summary(
    _: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
) -> dict:
    security_events = int(
        db.scalar(select(func.count(SecurityEventEntity.id))) or 0
    )
    active_rate_buckets = int(
        db.scalar(select(func.count(RateLimitBucketEntity.id))) or 0
    )
    return {
        "http": metrics_registry.snapshot(),
        "security": {
            "events_total": security_events,
            "rate_limit_buckets_total": active_rate_buckets,
        },
    }


@router.get(
    "/security-events",
    response_model=list[SecurityEventResponse],
)
def security_events(
    event_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
) -> list[SecurityEventResponse]:
    stmt = select(SecurityEventEntity)
    if event_type:
        stmt = stmt.where(SecurityEventEntity.event_type == event_type)
    stmt = stmt.order_by(SecurityEventEntity.created_at.desc()).limit(limit)
    return [
        SecurityEventResponse.model_validate(x)
        for x in db.scalars(stmt).all()
    ]


@router.get(
    "/rate-limit-buckets",
    response_model=list[RateLimitBucketResponse],
)
def rate_limit_buckets(
    scope: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
) -> list[RateLimitBucketResponse]:
    stmt = select(RateLimitBucketEntity)
    if scope:
        stmt = stmt.where(RateLimitBucketEntity.scope == scope)
    stmt = stmt.order_by(RateLimitBucketEntity.updated_at.desc()).limit(limit)
    return [
        RateLimitBucketResponse.model_validate(x)
        for x in db.scalars(stmt).all()
    ]
