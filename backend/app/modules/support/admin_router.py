from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.support.schemas import (
    AdminSupportMessageCreateRequest,
    AssignTicketRequest,
    SupportTicketResponse,
    TicketStatusUpdateRequest,
)
from app.modules.support.service import SupportService

router = APIRouter(prefix="/admin/support", tags=["admin-support"])


def admin_user(
    user: UserEntity = Depends(require_roles(UserRole.ADMIN)),
) -> UserEntity:
    return user


@router.get("/tickets", response_model=list[SupportTicketResponse])
def list_tickets(
    status: str | None = Query(default=None),
    assigned_admin_id: UUID | None = Query(default=None),
    _: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[SupportTicketResponse]:
    return SupportService(db, settings).admin_list(
        status=status,
        assigned_admin_id=assigned_admin_id,
    )


@router.get(
    "/tickets/{ticket_id}",
    response_model=SupportTicketResponse,
)
def ticket_detail(
    ticket_id: UUID,
    _: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SupportTicketResponse:
    return SupportService(db, settings).admin_detail(ticket_id=ticket_id)


@router.post(
    "/tickets/{ticket_id}/assign",
    response_model=SupportTicketResponse,
)
def assign_ticket(
    ticket_id: UUID,
    payload: AssignTicketRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SupportTicketResponse:
    return SupportService(db, settings).assign(
        actor_admin_id=admin.id,
        ticket_id=ticket_id,
        target_admin_id=payload.admin_id,
        request_id=request.state.request_id,
    )


@router.post(
    "/tickets/{ticket_id}/messages",
    response_model=SupportTicketResponse,
)
def add_admin_message(
    ticket_id: UUID,
    payload: AdminSupportMessageCreateRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SupportTicketResponse:
    return SupportService(db, settings).admin_message(
        admin_id=admin.id,
        ticket_id=ticket_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.patch(
    "/tickets/{ticket_id}/status",
    response_model=SupportTicketResponse,
)
def update_ticket_status(
    ticket_id: UUID,
    payload: TicketStatusUpdateRequest,
    request: Request,
    admin: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SupportTicketResponse:
    return SupportService(db, settings).update_status(
        admin_id=admin.id,
        ticket_id=ticket_id,
        payload=payload,
        request_id=request.state.request_id,
    )
