from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db_models import (
    SupportMessageEntity,
    SupportTicketEntity,
    UserEntity,
)


class SupportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ticket(self, ticket_id: UUID) -> SupportTicketEntity | None:
        return self.db.get(SupportTicketEntity, ticket_id)

    def customer_tickets(self, customer_id: UUID) -> list[SupportTicketEntity]:
        return list(
            self.db.scalars(
                select(SupportTicketEntity)
                .where(SupportTicketEntity.customer_id == customer_id)
                .order_by(SupportTicketEntity.created_at.desc())
            ).all()
        )

    def admin_tickets(
        self,
        *,
        status: str | None = None,
        assigned_admin_id: UUID | None = None,
    ) -> list[SupportTicketEntity]:
        stmt = select(SupportTicketEntity)
        if status:
            stmt = stmt.where(SupportTicketEntity.status == status)
        if assigned_admin_id:
            stmt = stmt.where(
                SupportTicketEntity.assigned_admin_id == assigned_admin_id
            )
        stmt = stmt.order_by(
            SupportTicketEntity.priority.desc(),
            SupportTicketEntity.created_at.asc(),
        )
        return list(self.db.scalars(stmt).all())

    def messages(
        self,
        ticket_id: UUID,
        *,
        include_internal: bool,
    ) -> list[SupportMessageEntity]:
        stmt = select(SupportMessageEntity).where(
            SupportMessageEntity.ticket_id == ticket_id
        )
        if not include_internal:
            stmt = stmt.where(SupportMessageEntity.is_internal.is_(False))
        stmt = stmt.order_by(SupportMessageEntity.created_at.asc())
        return list(self.db.scalars(stmt).all())

    def admin_user(self, admin_id: UUID) -> UserEntity | None:
        user = self.db.get(UserEntity, admin_id)
        if user is None or user.role != "admin" or not user.is_active:
            return None
        return user
