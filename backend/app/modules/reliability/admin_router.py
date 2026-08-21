from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import BackgroundJobEntity, OutboxEventEntity, UserEntity, WorkerHeartbeatEntity
from app.core.models import UserRole
from app.core.security import utc_now
from app.modules.reliability.jobs import BackgroundJobService
from app.modules.reliability.outbox import OutboxService
from app.modules.reliability.schemas import BackgroundJobResponse, OutboxEventResponse, WorkerHeartbeatResponse
from app.modules.reliability.worker import WorkerService

router = APIRouter(prefix="/admin/reliability", tags=["admin-reliability"])


def admin_user(user: UserEntity = Depends(require_roles(UserRole.ADMIN))) -> UserEntity:
    return user


@router.get("/summary")
def summary(
    _: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    heartbeats = list(db.scalars(select(WorkerHeartbeatEntity).order_by(WorkerHeartbeatEntity.last_seen_at.desc())).all())
    return {
        "outbox": OutboxService(db, settings).counts(),
        "jobs": BackgroundJobService(db, settings).counts(),
        "workers": [WorkerHeartbeatResponse.model_validate(x).model_dump(mode="json") for x in heartbeats],
    }


@router.get("/outbox", response_model=list[OutboxEventResponse])
def list_outbox(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
) -> list[OutboxEventResponse]:
    stmt = select(OutboxEventEntity)
    if status:
        stmt = stmt.where(OutboxEventEntity.status == status)
    rows = db.scalars(stmt.order_by(OutboxEventEntity.created_at.desc()).limit(limit)).all()
    return [OutboxEventResponse.model_validate(x) for x in rows]


@router.post("/outbox/{event_id}/retry", response_model=OutboxEventResponse)
def retry_outbox(
    event_id: UUID,
    _: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
) -> OutboxEventResponse:
    row = db.get(OutboxEventEntity, event_id)
    if row is None:
        from app.core.errors import ApiError
        raise ApiError(404, "outbox_event_not_found", "حدث الـ Outbox غير موجود.")
    row.status = "pending"
    row.attempts = 0
    row.available_at = utc_now()
    row.locked_at = None
    row.locked_by = None
    row.last_error = None
    db.commit()
    db.refresh(row)
    return OutboxEventResponse.model_validate(row)


@router.get("/jobs", response_model=list[BackgroundJobResponse])
def list_jobs(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
) -> list[BackgroundJobResponse]:
    stmt = select(BackgroundJobEntity)
    if status:
        stmt = stmt.where(BackgroundJobEntity.status == status)
    rows = db.scalars(stmt.order_by(BackgroundJobEntity.created_at.desc()).limit(limit)).all()
    return [BackgroundJobResponse.model_validate(x) for x in rows]


@router.post("/jobs/{job_id}/retry", response_model=BackgroundJobResponse)
def retry_job(
    job_id: UUID,
    _: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
) -> BackgroundJobResponse:
    row = db.get(BackgroundJobEntity, job_id)
    if row is None:
        from app.core.errors import ApiError
        raise ApiError(404, "background_job_not_found", "المهمة الخلفية غير موجودة.")
    row.status = "queued"
    row.attempts = 0
    row.available_at = utc_now()
    row.locked_at = None
    row.locked_by = None
    row.finished_at = None
    row.last_error = None
    db.commit()
    db.refresh(row)
    return BackgroundJobResponse.model_validate(row)


@router.post("/run-once")
def run_once(
    _: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return WorkerService(db, settings).run_once(worker_id="admin-manual-worker")
