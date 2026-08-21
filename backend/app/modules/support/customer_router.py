from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.modules.support.schemas import (
    SupportMessageCreateRequest,
    SupportTicketCreateRequest,
    SupportTicketResponse,
)
from app.modules.support.service import SupportService

router = APIRouter(prefix="/customer/support", tags=["support"])


@router.post("/tickets", response_model=SupportTicketResponse, status_code=201)
def create_ticket(
    payload: SupportTicketCreateRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SupportTicketResponse:
    return SupportService(db, settings).create_ticket(
        customer_id=user.id,
        payload=payload,
        request_id=request.state.request_id,
    )


@router.get("/tickets", response_model=list[SupportTicketResponse])
def list_tickets(
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[SupportTicketResponse]:
    return SupportService(db, settings).customer_list(customer_id=user.id)


@router.get(
    "/tickets/{ticket_id}",
    response_model=SupportTicketResponse,
)
def ticket_detail(
    ticket_id: UUID,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SupportTicketResponse:
    return SupportService(db, settings).customer_detail(
        customer_id=user.id,
        ticket_id=ticket_id,
    )


@router.post(
    "/tickets/{ticket_id}/messages",
    response_model=SupportTicketResponse,
)
def add_message(
    ticket_id: UUID,
    payload: SupportMessageCreateRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SupportTicketResponse:
    return SupportService(db, settings).customer_message(
        customer_id=user.id,
        ticket_id=ticket_id,
        payload=payload,
        request_id=request.state.request_id,
    )
