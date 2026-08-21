from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.pilot_stability.schemas import (
    PilotCohortReport,
    PilotPostPilotReport,
    PilotProgramCreate,
    PilotProgramResponse,
    PilotQaEvidenceResponse,
    PilotQaEvidenceUpsert,
    PilotStabilityReport,
    PilotWeeklySnapshotResponse,
)
from app.modules.pilot_stability.service import PilotStabilityService

router = APIRouter(
    prefix="/admin/pilot",
    tags=["admin-pilot-stability"],
)


def admin_user(
    user: UserEntity = Depends(require_roles(UserRole.ADMIN)),
) -> UserEntity:
    return user


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PilotStabilityService:
    return PilotStabilityService(db, settings)


@router.post(
    "/programs",
    response_model=PilotProgramResponse,
    status_code=201,
)
def create_program(
    payload: PilotProgramCreate,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: PilotStabilityService = Depends(service),
) -> PilotProgramResponse:
    return svc.create_program(
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get(
    "/programs",
    response_model=list[PilotProgramResponse],
)
def programs(
    _: UserEntity = Depends(admin_user),
    svc: PilotStabilityService = Depends(service),
) -> list[PilotProgramResponse]:
    return svc.programs()


@router.get(
    "/programs/{program_id}",
    response_model=PilotProgramResponse,
)
def program(
    program_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: PilotStabilityService = Depends(service),
) -> PilotProgramResponse:
    return PilotProgramResponse.model_validate(svc.program(program_id))


@router.post(
    "/programs/{program_id}/activate",
    response_model=PilotProgramResponse,
)
def activate(
    program_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: PilotStabilityService = Depends(service),
) -> PilotProgramResponse:
    return svc.activate(
        program_id=program_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/programs/{program_id}/complete",
    response_model=PilotProgramResponse,
)
def complete(
    program_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: PilotStabilityService = Depends(service),
) -> PilotProgramResponse:
    return svc.complete(
        program_id=program_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/programs/{program_id}/refresh",
    response_model=list[PilotWeeklySnapshotResponse],
)
def refresh(
    program_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: PilotStabilityService = Depends(service),
) -> list[PilotWeeklySnapshotResponse]:
    return svc.refresh_program(program_id)


@router.get(
    "/programs/{program_id}/stability",
    response_model=PilotStabilityReport,
)
def stability(
    program_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: PilotStabilityService = Depends(service),
) -> PilotStabilityReport:
    return svc.stability_report(program_id)


@router.get(
    "/programs/{program_id}/cohorts",
    response_model=PilotCohortReport,
)
def cohorts(
    program_id: UUID,
    weeks: int = Query(default=8, ge=1, le=26),
    _: UserEntity = Depends(admin_user),
    svc: PilotStabilityService = Depends(service),
) -> PilotCohortReport:
    return svc.cohort_report(program_id, max_weeks=weeks)


@router.get(
    "/programs/{program_id}/evidence",
    response_model=list[PilotQaEvidenceResponse],
)
def evidence(
    program_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: PilotStabilityService = Depends(service),
) -> list[PilotQaEvidenceResponse]:
    return svc.evidence(program_id)


@router.put(
    "/programs/{program_id}/evidence/{evidence_type}",
    response_model=PilotQaEvidenceResponse,
)
def upsert_evidence(
    program_id: UUID,
    evidence_type: str,
    payload: PilotQaEvidenceUpsert,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: PilotStabilityService = Depends(service),
) -> PilotQaEvidenceResponse:
    return svc.upsert_evidence(
        program_id=program_id,
        evidence_type=evidence_type,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get(
    "/programs/{program_id}/post-pilot",
    response_model=PilotPostPilotReport,
)
def post_pilot(
    program_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: PilotStabilityService = Depends(service),
) -> PilotPostPilotReport:
    return svc.post_pilot_report(program_id)
