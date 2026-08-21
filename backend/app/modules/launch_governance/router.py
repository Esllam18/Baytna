from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.launch_governance.schemas import (
    AdmissionEventResponse,
    CapacityForecastResponse,
    MonitoringSnapshotResponse,
    TrafficPolicyResponse,
    TrafficCapsResponse,
    TrafficCapsUpdate,
    TrafficPolicyUpdate,
    TrafficZoneOverview,
)
from app.modules.launch_governance.service import (
    LaunchTrafficGovernanceService,
)

router = APIRouter(
    prefix="/admin/traffic",
    tags=["admin-launch-traffic"],
)


def admin_user(
    user: UserEntity = Depends(require_roles(UserRole.ADMIN)),
) -> UserEntity:
    return user


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LaunchTrafficGovernanceService:
    return LaunchTrafficGovernanceService(db, settings)


@router.get("/zones", response_model=list[TrafficZoneOverview])
def zones(
    _: UserEntity = Depends(admin_user),
    svc: LaunchTrafficGovernanceService = Depends(service),
) -> list[TrafficZoneOverview]:
    return svc.zone_overviews()


@router.get(
    "/zones/{zone_id}/policy",
    response_model=TrafficPolicyResponse,
)
def policy(
    zone_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: LaunchTrafficGovernanceService = Depends(service),
) -> TrafficPolicyResponse:
    return svc.policy_response(zone_id)


@router.put(
    "/zones/{zone_id}/policy",
    response_model=TrafficPolicyResponse,
)
def update_policy(
    zone_id: UUID,
    payload: TrafficPolicyUpdate,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchTrafficGovernanceService = Depends(service),
) -> TrafficPolicyResponse:
    return svc.update_policy(
        zone_id=zone_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.patch(
    "/zones/{zone_id}/caps",
    response_model=TrafficCapsResponse,
)
def update_caps(
    zone_id: UUID,
    payload: TrafficCapsUpdate,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchTrafficGovernanceService = Depends(service),
) -> TrafficCapsResponse:
    return svc.update_caps(
        zone_id=zone_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/zones/{zone_id}/monitoring/refresh",
    response_model=MonitoringSnapshotResponse,
)
def refresh_monitoring(
    zone_id: UUID,
    service_date: date | None = Query(default=None),
    _: UserEntity = Depends(admin_user),
    svc: LaunchTrafficGovernanceService = Depends(service),
) -> MonitoringSnapshotResponse:
    return svc.refresh_monitoring(
        zone_id=zone_id,
        service_date=service_date,
        generated_by="admin",
    )


@router.get(
    "/zones/{zone_id}/monitoring",
    response_model=list[MonitoringSnapshotResponse],
)
def monitoring(
    zone_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    _: UserEntity = Depends(admin_user),
    svc: LaunchTrafficGovernanceService = Depends(service),
) -> list[MonitoringSnapshotResponse]:
    return svc.monitoring_history(zone_id=zone_id, limit=limit)


@router.get(
    "/zones/{zone_id}/capacity-forecasts",
    response_model=list[CapacityForecastResponse],
)
def capacity_forecasts(
    zone_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    _: UserEntity = Depends(admin_user),
    svc: LaunchTrafficGovernanceService = Depends(service),
) -> list[CapacityForecastResponse]:
    return svc.capacity_forecasts(zone_id=zone_id, limit=limit)


@router.get(
    "/zones/{zone_id}/admissions",
    response_model=list[AdmissionEventResponse],
)
def admissions(
    zone_id: UUID,
    decision: str | None = Query(default=None),
    reason: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    _: UserEntity = Depends(admin_user),
    svc: LaunchTrafficGovernanceService = Depends(service),
) -> list[AdmissionEventResponse]:
    return svc.admissions(
        zone_id=zone_id,
        decision=decision,
        reason=reason,
        limit=limit,
    )
