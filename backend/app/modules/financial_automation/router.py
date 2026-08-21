from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.financial_automation.schemas import (
    ProviderCostImportBatchResponse,
    ProviderCostImportCreate,
    ProviderCostImportDetail,
    RolloutRequest,
    RolloutEventResponse,
    RolloutResponse,
    SettlementBatchCreate,
    SettlementBatchDetail,
    SettlementBatchResponse,
    TwilioUsageSyncRequest,
    ZoneBudgetMovement,
    ZoneBudgetResponse,
    ZoneBudgetSummary,
    ZoneBudgetUpsert,
)
from app.modules.financial_automation.service import FinancialAutomationService

router = APIRouter(
    prefix="/admin/economics",
    tags=["admin-financial-automation"],
)


def admin_user(
    user: UserEntity = Depends(require_roles(UserRole.ADMIN)),
) -> UserEntity:
    return user


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FinancialAutomationService:
    return FinancialAutomationService(db, settings)


@router.post(
    "/imports",
    response_model=ProviderCostImportDetail,
    status_code=201,
)
def create_import(
    payload: ProviderCostImportCreate,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> ProviderCostImportDetail:
    return svc.create_cost_import(
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get(
    "/imports",
    response_model=list[ProviderCostImportBatchResponse],
)
def imports(
    provider: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> list[ProviderCostImportBatchResponse]:
    return svc.cost_imports(
        provider=provider,
        status=status,
        limit=limit,
    )


@router.get(
    "/imports/{batch_id}",
    response_model=ProviderCostImportDetail,
)
def import_detail(
    batch_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> ProviderCostImportDetail:
    return svc.cost_import_detail(batch_id)


@router.post(
    "/imports/{batch_id}/validate",
    response_model=ProviderCostImportDetail,
)
def validate_import(
    batch_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> ProviderCostImportDetail:
    return svc.validate_cost_import(
        batch_id=batch_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/imports/{batch_id}/apply",
    response_model=ProviderCostImportDetail,
)
def apply_import(
    batch_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> ProviderCostImportDetail:
    return svc.apply_cost_import(
        batch_id=batch_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/providers/twilio/sync",
    response_model=ProviderCostImportDetail,
    status_code=201,
)
def sync_twilio(
    payload: TwilioUsageSyncRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> ProviderCostImportDetail:
    return svc.sync_twilio_usage(
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/settlements",
    response_model=SettlementBatchDetail,
    status_code=201,
)
def create_settlement(
    payload: SettlementBatchCreate,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> SettlementBatchDetail:
    return svc.create_settlement(
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get(
    "/settlements",
    response_model=list[SettlementBatchResponse],
)
def settlements(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> list[SettlementBatchResponse]:
    return svc.settlements(status=status, limit=limit)


@router.get(
    "/settlements/{batch_id}",
    response_model=SettlementBatchDetail,
)
def settlement(
    batch_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> SettlementBatchDetail:
    return svc.settlement_detail(batch_id)


@router.post(
    "/settlements/{batch_id}/reconcile",
    response_model=SettlementBatchDetail,
)
def reconcile_settlement(
    batch_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> SettlementBatchDetail:
    return svc.reconcile_settlement(
        batch_id=batch_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.put(
    "/zones/{zone_id}/budgets",
    response_model=ZoneBudgetResponse,
)
def upsert_zone_budget(
    zone_id: UUID,
    payload: ZoneBudgetUpsert,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> ZoneBudgetResponse:
    return svc.upsert_budget(
        zone_id=zone_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get(
    "/zones/{zone_id}/budgets",
    response_model=ZoneBudgetSummary,
)
def zone_budgets(
    zone_id: UUID,
    _: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> ZoneBudgetSummary:
    return svc.budget_summary(zone_id)


@router.post(
    "/budgets/{budget_id}/movement",
    response_model=ZoneBudgetResponse,
)
def budget_movement(
    budget_id: UUID,
    payload: ZoneBudgetMovement,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> ZoneBudgetResponse:
    return svc.move_budget(
        budget_id=budget_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.get(
    "/zones/{zone_id}/rollout/history",
    response_model=list[RolloutEventResponse],
)
def rollout_history(
    zone_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    _: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> list[RolloutEventResponse]:
    return svc.rollout_history(zone_id=zone_id, limit=limit)


@router.post(
    "/zones/{zone_id}/rollout/start",
    response_model=RolloutResponse,
)
def start_rollout(
    zone_id: UUID,
    payload: RolloutRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> RolloutResponse:
    return svc.start_rollout(
        zone_id=zone_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/zones/{zone_id}/rollout/advance",
    response_model=RolloutResponse,
)
def advance_rollout(
    zone_id: UUID,
    payload: RolloutRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> RolloutResponse:
    return svc.advance_rollout(
        zone_id=zone_id,
        payload=payload,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/zones/{zone_id}/rollout/pause",
    response_model=RolloutResponse,
)
def pause_rollout(
    zone_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> RolloutResponse:
    return svc.pause_rollout(
        zone_id=zone_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )


@router.post(
    "/zones/{zone_id}/rollout/resume",
    response_model=RolloutResponse,
)
def resume_rollout(
    zone_id: UUID,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    svc: FinancialAutomationService = Depends(service),
) -> RolloutResponse:
    return svc.resume_rollout(
        zone_id=zone_id,
        admin_id=admin.id,
        request_id=request.state.request_id,
    )
