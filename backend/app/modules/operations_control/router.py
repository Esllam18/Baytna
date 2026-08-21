from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.operations_control.schemas import (
    ControlRoomOverview,
    DailyBrief,
    IncidentAssignRequest,
    IncidentEscalateRequest,
    IncidentRefreshResponse,
    IncidentResolveRequest,
    IncidentResponse,
    LaunchKpis,
)
from app.modules.operations_control.service import OperationsControlService

router = APIRouter(
    prefix="/admin/control-room",
    tags=["admin-control-room"],
)


def admin_user(
    user: UserEntity = Depends(require_roles(UserRole.ADMIN)),
) -> UserEntity:
    return user


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OperationsControlService:
    return OperationsControlService(db, settings)


@router.post(
    "/incidents/refresh",
    response_model=IncidentRefreshResponse,
)
def refresh_incidents(
    _: UserEntity = Depends(admin_user),
    svc: OperationsControlService = Depends(service),
) -> IncidentRefreshResponse:
    return svc.refresh_incidents()


@router.get(
    "/overview",
    response_model=ControlRoomOverview,
)
def overview(
    _: UserEntity = Depends(admin_user),
    svc: OperationsControlService = Depends(service),
) -> ControlRoomOverview:
    return svc.overview()


@router.get(
    "/kpis",
    response_model=LaunchKpis,
)
def kpis(
    days: int = Query(default=7, ge=1, le=90),
    _: UserEntity = Depends(admin_user),
    svc: OperationsControlService = Depends(service),
) -> LaunchKpis:
    return svc.launch_kpis(days)


@router.get(
    "/daily-brief",
    response_model=DailyBrief,
)
def daily_brief(
    day: date | None = Query(default=None),
    _: UserEntity = Depends(admin_user),
    svc: OperationsControlService = Depends(service),
) -> DailyBrief:
    return svc.daily_brief(day)


@router.get(
    "/incidents",
    response_model=list[IncidentResponse],
)
def incidents(
    status: str | None = Query(
        default=None,
        pattern=r"^(open|acknowledged|resolved)$",
    ),
    severity: str | None = Query(
        default=None,
        pattern=r"^(info|warning|high|critical)$",
    ),
    category: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    _: UserEntity = Depends(admin_user),
    svc: OperationsControlService = Depends(service),
) -> list[IncidentResponse]:
    return svc.list_incidents(
        status=status,
        severity=severity,
        category=category,
        limit=limit,
    )


@router.post(
    "/incidents/{incident_id}/acknowledge",
    response_model=IncidentResponse,
)
def acknowledge(
    incident_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: OperationsControlService = Depends(service),
) -> IncidentResponse:
    return svc.acknowledge(
        incident_id=incident_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/incidents/{incident_id}/assign",
    response_model=IncidentResponse,
)
def assign(
    incident_id: UUID,
    payload: IncidentAssignRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: OperationsControlService = Depends(service),
) -> IncidentResponse:
    return svc.assign(
        incident_id=incident_id,
        owner_admin_id=payload.admin_id or admin.id,
        actor_admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/incidents/{incident_id}/escalate",
    response_model=IncidentResponse,
)
def escalate(
    incident_id: UUID,
    payload: IncidentEscalateRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: OperationsControlService = Depends(service),
) -> IncidentResponse:
    return svc.escalate(
        incident_id=incident_id,
        admin_id=admin.id,
        note=payload.note,
        request_id=request.state.request_id,
    )


@router.post(
    "/incidents/{incident_id}/resolve",
    response_model=IncidentResponse,
)
def resolve(
    incident_id: UUID,
    payload: IncidentResolveRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: OperationsControlService = Depends(service),
) -> IncidentResponse:
    return svc.resolve(
        incident_id=incident_id,
        admin_id=admin.id,
        note=payload.note,
        request_id=request.state.request_id,
    )
