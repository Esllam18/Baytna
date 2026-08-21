from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.launch_command.schemas import (
    DailyFinancialCloseResponse,
    EvidencePackResponse,
    FinancialCloseActionRequest,
    FinancialClosePrepareRequest,
    LaunchCommandEventResponse,
    LaunchCommandOverview,
    LaunchRunbookStepResponse,
    LaunchSessionCreate,
    LaunchSessionResponse,
    RollbackDrillComplete,
    RollbackDrillCreate,
    RollbackDrillResponse,
    RunbookStepDecision,
    TrafficOverrideCreate,
    TrafficOverrideResponse,
)
from app.modules.launch_command.service import LaunchCommandService

router = APIRouter(
    prefix="/admin/launch-command",
    tags=["admin-launch-command"],
)


def admin_user(
    user: UserEntity = Depends(require_roles(UserRole.ADMIN)),
) -> UserEntity:
    return user


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LaunchCommandService:
    return LaunchCommandService(db, settings)


@router.post("/sessions", response_model=LaunchSessionResponse, status_code=201)
def create_session(
    payload: LaunchSessionCreate,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> LaunchSessionResponse:
    return svc.create_session(
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get("/sessions", response_model=list[LaunchSessionResponse])
def sessions(
    limit: int = Query(default=100, ge=1, le=500),
    _: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> list[LaunchSessionResponse]:
    return svc.sessions(limit)


@router.get("/sessions/{session_id}", response_model=LaunchCommandOverview)
def overview(
    session_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> LaunchCommandOverview:
    return svc.overview(session_id)


@router.post("/sessions/{session_id}/start", response_model=LaunchSessionResponse)
def start_session(
    session_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> LaunchSessionResponse:
    return svc.start_session(session_id=session_id, admin_id=admin.id, request_id=request.state.request_id)


@router.post("/sessions/{session_id}/pause", response_model=LaunchSessionResponse)
def pause_session(
    session_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> LaunchSessionResponse:
    return svc.pause_session(session_id=session_id, admin_id=admin.id, request_id=request.state.request_id)


@router.post("/sessions/{session_id}/resume", response_model=LaunchSessionResponse)
def resume_session(
    session_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> LaunchSessionResponse:
    return svc.resume_session(session_id=session_id, admin_id=admin.id, request_id=request.state.request_id)


@router.post("/sessions/{session_id}/abort", response_model=LaunchSessionResponse)
def abort_session(
    session_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> LaunchSessionResponse:
    return svc.abort_session(session_id=session_id, admin_id=admin.id, request_id=request.state.request_id)


@router.post("/sessions/{session_id}/complete", response_model=LaunchSessionResponse)
def complete_session(
    session_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> LaunchSessionResponse:
    return svc.complete_session(session_id=session_id, admin_id=admin.id, request_id=request.state.request_id)


@router.get("/sessions/{session_id}/runbook", response_model=list[LaunchRunbookStepResponse])
def runbook(
    session_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> list[LaunchRunbookStepResponse]:
    return svc.runbook(session_id)


@router.post(
    "/sessions/{session_id}/runbook/{step_key}",
    response_model=LaunchRunbookStepResponse,
)
def decide_runbook_step(
    session_id: UUID,
    step_key: str,
    payload: RunbookStepDecision,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> LaunchRunbookStepResponse:
    return svc.decide_runbook_step(
        session_id=session_id,
        step_key=step_key,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get("/sessions/{session_id}/events", response_model=list[LaunchCommandEventResponse])
def events(
    session_id: UUID,
    limit: int = Query(default=500, ge=1, le=2000),
    _: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> list[LaunchCommandEventResponse]:
    return svc.events(session_id, limit)


@router.post(
    "/sessions/{session_id}/traffic-overrides",
    response_model=TrafficOverrideResponse,
    status_code=201,
)
def create_override(
    session_id: UUID,
    payload: TrafficOverrideCreate,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> TrafficOverrideResponse:
    return svc.create_override(
        session_id=session_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get(
    "/sessions/{session_id}/traffic-overrides",
    response_model=list[TrafficOverrideResponse],
)
def overrides(
    session_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> list[TrafficOverrideResponse]:
    return svc.overrides(session_id)


@router.post(
    "/traffic-overrides/{override_id}/revert",
    response_model=TrafficOverrideResponse,
)
def revert_override(
    override_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> TrafficOverrideResponse:
    return svc.revert_override(
        override_id=override_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/sessions/{session_id}/financial-closes/prepare",
    response_model=DailyFinancialCloseResponse,
)
def prepare_financial_close(
    session_id: UUID,
    payload: FinancialClosePrepareRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> DailyFinancialCloseResponse:
    return svc.prepare_financial_close(
        session_id=session_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get(
    "/sessions/{session_id}/financial-closes",
    response_model=list[DailyFinancialCloseResponse],
)
def financial_closes(
    session_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> list[DailyFinancialCloseResponse]:
    return svc.financial_closes(session_id)


@router.post(
    "/financial-closes/{close_id}/close",
    response_model=DailyFinancialCloseResponse,
)
def close_financial_day(
    close_id: UUID,
    payload: FinancialCloseActionRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> DailyFinancialCloseResponse:
    return svc.close_financial_day(
        close_id=close_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/financial-closes/{close_id}/reopen",
    response_model=DailyFinancialCloseResponse,
)
def reopen_financial_day(
    close_id: UUID,
    payload: FinancialCloseActionRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> DailyFinancialCloseResponse:
    return svc.reopen_financial_day(
        close_id=close_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/sessions/{session_id}/rollback-drills",
    response_model=RollbackDrillResponse,
    status_code=201,
)
def start_rollback_drill(
    session_id: UUID,
    payload: RollbackDrillCreate,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> RollbackDrillResponse:
    return svc.start_rollback_drill(
        session_id=session_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get(
    "/sessions/{session_id}/rollback-drills",
    response_model=list[RollbackDrillResponse],
)
def rollback_drills(
    session_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> list[RollbackDrillResponse]:
    return svc.rollback_drills(session_id)


@router.post(
    "/rollback-drills/{drill_id}/complete",
    response_model=RollbackDrillResponse,
)
def complete_rollback_drill(
    drill_id: UUID,
    payload: RollbackDrillComplete,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> RollbackDrillResponse:
    return svc.complete_rollback_drill(
        drill_id=drill_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/sessions/{session_id}/evidence-packs",
    response_model=EvidencePackResponse,
    status_code=201,
)
def generate_evidence_pack(
    session_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> EvidencePackResponse:
    return svc.generate_evidence_pack(
        session_id=session_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get(
    "/sessions/{session_id}/evidence-packs",
    response_model=list[EvidencePackResponse],
)
def evidence_packs(
    session_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: LaunchCommandService = Depends(service),
) -> list[EvidencePackResponse]:
    return svc.evidence_packs(session_id)
