from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.operational_economics.schemas import (
    CostEntryCreate,
    CostEntryResponse,
    EconomicsReport,
    ExpansionAssessmentResponse,
    ExpansionZoneCreate,
    ExpansionZoneDetail,
    ExpansionZoneResponse,
)
from app.modules.operational_economics.service import OperationalEconomicsService

router = APIRouter(
    prefix="/admin/economics",
    tags=["admin-operational-economics"],
)


def admin_user(
    user: UserEntity = Depends(require_roles(UserRole.ADMIN)),
) -> UserEntity:
    return user


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OperationalEconomicsService:
    return OperationalEconomicsService(db, settings)


@router.post("/costs", response_model=CostEntryResponse, status_code=201)
def create_cost(
    payload: CostEntryCreate,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: OperationalEconomicsService = Depends(service),
) -> CostEntryResponse:
    return svc.create_cost(
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get("/costs", response_model=list[CostEntryResponse])
def costs(
    program_id: UUID | None = Query(default=None),
    order_id: UUID | None = Query(default=None),
    verified: bool | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    _: UserEntity = Depends(admin_user),
    svc: OperationalEconomicsService = Depends(service),
) -> list[CostEntryResponse]:
    return svc.costs(
        program_id=program_id,
        order_id=order_id,
        verified=verified,
        limit=limit,
    )


@router.post(
    "/costs/{cost_id}/verify",
    response_model=CostEntryResponse,
)
def verify_cost(
    cost_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: OperationalEconomicsService = Depends(service),
) -> CostEntryResponse:
    return svc.verify_cost(
        cost_id=cost_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get(
    "/programs/{program_id}/report",
    response_model=EconomicsReport,
)
def report(
    program_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: OperationalEconomicsService = Depends(service),
) -> EconomicsReport:
    return svc.report(program_id)


@router.post(
    "/zones",
    response_model=ExpansionZoneResponse,
    status_code=201,
)
def create_zone(
    payload: ExpansionZoneCreate,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: OperationalEconomicsService = Depends(service),
) -> ExpansionZoneResponse:
    return svc.create_zone(
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get("/zones", response_model=list[ExpansionZoneDetail])
def zones(
    _: UserEntity = Depends(admin_user),
    svc: OperationalEconomicsService = Depends(service),
) -> list[ExpansionZoneDetail]:
    return svc.zones()


@router.get(
    "/zones/{zone_id}",
    response_model=ExpansionZoneDetail,
)
def zone(
    zone_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: OperationalEconomicsService = Depends(service),
) -> ExpansionZoneDetail:
    return svc.zone_detail(zone_id)


@router.post(
    "/zones/{zone_id}/assess",
    response_model=ExpansionAssessmentResponse,
)
def assess(
    zone_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: OperationalEconomicsService = Depends(service),
) -> ExpansionAssessmentResponse:
    return svc.assess_zone(
        zone_id=zone_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/zones/{zone_id}/approve",
    response_model=ExpansionZoneResponse,
)
def approve(
    zone_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: OperationalEconomicsService = Depends(service),
) -> ExpansionZoneResponse:
    return svc.approve_zone(
        zone_id=zone_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/zones/{zone_id}/launch",
    response_model=ExpansionZoneResponse,
)
def launch(
    zone_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: OperationalEconomicsService = Depends(service),
) -> ExpansionZoneResponse:
    return svc.launch_zone(
        zone_id=zone_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/zones/{zone_id}/pause",
    response_model=ExpansionZoneResponse,
)
def pause(
    zone_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: OperationalEconomicsService = Depends(service),
) -> ExpansionZoneResponse:
    return svc.pause_zone(
        zone_id=zone_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )
