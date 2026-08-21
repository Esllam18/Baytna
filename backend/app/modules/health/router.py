from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.core.db_models import OutboxEventEntity, BackgroundJobEntity

router = APIRouter(tags=["health"])


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok", "service": "baytna-api"}


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise ApiError(
            503,
            "database_unavailable",
            "قاعدة البيانات غير متاحة.",
        ) from exc

    return {
        "status": "ready",
        "database": "connected",
        "persistence": "sqlalchemy",
    }


@router.get("/health/reliability")
def reliability(db: Session = Depends(get_db)) -> dict[str, str]:
    outbox_dead = int(
        db.scalar(
            select(func.count(OutboxEventEntity.id)).where(
                OutboxEventEntity.status == "dead_letter"
            )
        )
        or 0
    )
    jobs_dead = int(
        db.scalar(
            select(func.count(BackgroundJobEntity.id)).where(
                BackgroundJobEntity.status == "dead_letter"
            )
        )
        or 0
    )
    return {
        "status": "ok",
        "outbox_dead_letter": str(outbox_dead),
        "jobs_dead_letter": str(jobs_dead),
    }



@router.get("/health/release")
def release(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "service": "baytna-api",
        "version": settings.release_version,
        "environment": settings.env,
        "slot": settings.release_slot,
        "commit": settings.release_commit or "unknown",
        "migration_head": "0025_sprint50",
    }
