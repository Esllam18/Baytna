from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings

from app.core.db_models import (
    MediaAssetEntity,
    OrderEntity,
    SupportMessageAttachmentEntity,
    SupportMessageEntity,
    SupportTicketEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import utc_now
from app.modules.support.repository import SupportRepository
from app.modules.notifications.service import NotificationService
from app.modules.reliability.outbox import OutboxService
from app.modules.support.schemas import (
    AdminSupportMessageCreateRequest,
    SupportAttachmentResponse,
    SupportMessageCreateRequest,
    SupportMessageResponse,
    SupportTicketCreateRequest,
    SupportTicketResponse,
    TicketStatusUpdateRequest,
)


class SupportService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings
        self.repo = SupportRepository(db)
        self.audit = AuditRepository(db)

    def create_ticket(
        self,
        *,
        customer_id: UUID,
        payload: SupportTicketCreateRequest,
        request_id: str | None,
    ) -> SupportTicketResponse:
        if payload.order_id is not None:
            order = self.db.get(OrderEntity, payload.order_id)
            if order is None or order.customer_id != customer_id:
                raise ApiError(404, "order_not_found", "الطلب غير موجود.")

        ticket = SupportTicketEntity(
            customer_id=customer_id,
            order_id=payload.order_id,
            category=payload.category,
            subject=payload.subject,
            description=payload.description,
            priority=payload.priority,
            status="new",
        )
        self.db.add(ticket)
        self.db.flush()

        initial_message = SupportMessageEntity(ticket_id=ticket.id, sender_user_id=customer_id, sender_role="customer", body=payload.description, is_internal=False)
        self.db.add(initial_message); self.db.flush()
        self._attach_media(message=initial_message, actor_user_id=customer_id, attachment_ids=payload.attachment_ids)

        self.audit.add(
            action="support.ticket.created",
            actor_user_id=customer_id,
            entity_type="support_ticket",
            entity_id=str(ticket.id),
            request_id=request_id,
            metadata={
                "category": payload.category,
                "priority": payload.priority,
                "order_id": str(payload.order_id) if payload.order_id else None,
            },
        )
        OutboxService(self.db).enqueue(
            event_type="support.ticket.created",
            aggregate_type="support_ticket",
            aggregate_id=ticket.id,
            dedupe_key=f"support.ticket.created:{ticket.id}",
            payload={
                "ticket_id": str(ticket.id),
                "customer_id": str(customer_id),
                "order_id": str(payload.order_id) if payload.order_id else None,
                "category": payload.category,
                "priority": payload.priority,
            },
        )
        self.db.commit()
        self.db.refresh(ticket)
        return self._ticket_response(ticket, include_internal=False)

    def customer_list(self, *, customer_id: UUID) -> list[SupportTicketResponse]:
        return [
            self._ticket_response(x, include_internal=False)
            for x in self.repo.customer_tickets(customer_id)
        ]

    def customer_detail(
        self,
        *,
        customer_id: UUID,
        ticket_id: UUID,
    ) -> SupportTicketResponse:
        ticket = self.repo.ticket(ticket_id)
        if ticket is None or ticket.customer_id != customer_id:
            raise ApiError(404, "support_ticket_not_found", "طلب الدعم غير موجود.")
        return self._ticket_response(ticket, include_internal=False)

    def customer_message(
        self,
        *,
        customer_id: UUID,
        ticket_id: UUID,
        payload: SupportMessageCreateRequest,
        request_id: str | None,
    ) -> SupportTicketResponse:
        ticket = self.repo.ticket(ticket_id)
        if ticket is None or ticket.customer_id != customer_id:
            raise ApiError(404, "support_ticket_not_found", "طلب الدعم غير موجود.")

        if ticket.status == "closed":
            raise ApiError(
                409,
                "support_ticket_closed",
                "لا يمكن إضافة رسالة إلى طلب دعم مغلق.",
            )

        message = SupportMessageEntity(ticket_id=ticket.id, sender_user_id=customer_id, sender_role="customer", body=payload.body, is_internal=False)
        self.db.add(message); self.db.flush()
        self._attach_media(message=message, actor_user_id=customer_id, attachment_ids=payload.attachment_ids)

        if ticket.status == "awaiting_customer":
            ticket.status = "investigating"

        self.audit.add(
            action="support.customer_message.added",
            actor_user_id=customer_id,
            entity_type="support_ticket",
            entity_id=str(ticket.id),
            request_id=request_id,
        )
        self.db.commit()
        return self._ticket_response(ticket, include_internal=False)

    def admin_list(
        self,
        *,
        status: str | None,
        assigned_admin_id: UUID | None,
    ) -> list[SupportTicketResponse]:
        return [
            self._ticket_response(x, include_internal=True)
            for x in self.repo.admin_tickets(
                status=status,
                assigned_admin_id=assigned_admin_id,
            )
        ]

    def admin_detail(
        self,
        *,
        ticket_id: UUID,
    ) -> SupportTicketResponse:
        ticket = self.repo.ticket(ticket_id)
        if ticket is None:
            raise ApiError(404, "support_ticket_not_found", "طلب الدعم غير موجود.")
        return self._ticket_response(ticket, include_internal=True)

    def assign(
        self,
        *,
        actor_admin_id: UUID,
        ticket_id: UUID,
        target_admin_id: UUID | None,
        request_id: str | None,
    ) -> SupportTicketResponse:
        ticket = self.repo.ticket(ticket_id)
        if ticket is None:
            raise ApiError(404, "support_ticket_not_found", "طلب الدعم غير موجود.")

        assignee_id = target_admin_id or actor_admin_id
        if self.repo.admin_user(assignee_id) is None:
            raise ApiError(404, "admin_not_found", "الموظف الإداري غير موجود.")

        ticket.assigned_admin_id = assignee_id
        if ticket.status == "new":
            ticket.status = "assigned"

        self.audit.add(
            action="support.ticket.assigned",
            actor_user_id=actor_admin_id,
            entity_type="support_ticket",
            entity_id=str(ticket.id),
            request_id=request_id,
            metadata={"assigned_admin_id": str(assignee_id)},
        )
        self.db.commit()
        return self._ticket_response(ticket, include_internal=True)

    def admin_message(
        self,
        *,
        admin_id: UUID,
        ticket_id: UUID,
        payload: AdminSupportMessageCreateRequest,
        request_id: str | None,
    ) -> SupportTicketResponse:
        ticket = self.repo.ticket(ticket_id)
        if ticket is None:
            raise ApiError(404, "support_ticket_not_found", "طلب الدعم غير موجود.")

        if ticket.status == "closed":
            raise ApiError(
                409,
                "support_ticket_closed",
                "لا يمكن إضافة رسالة إلى طلب دعم مغلق.",
            )

        message = SupportMessageEntity(ticket_id=ticket.id, sender_user_id=admin_id, sender_role="admin", body=payload.body, is_internal=payload.is_internal)
        self.db.add(message); self.db.flush()
        self._attach_media(message=message, actor_user_id=admin_id, attachment_ids=payload.attachment_ids, admin=True)

        if ticket.assigned_admin_id is None:
            ticket.assigned_admin_id = admin_id
        if ticket.status in {"new", "assigned"}:
            ticket.status = "investigating"

        self.audit.add(
            action="support.admin_message.added",
            actor_user_id=admin_id,
            entity_type="support_ticket",
            entity_id=str(ticket.id),
            request_id=request_id,
            metadata={"is_internal": payload.is_internal},
        )
        if not payload.is_internal:
            NotificationService(self.db, self.settings).emit(
                user_id=ticket.customer_id,
                kind="support_reply",
                title="رد جديد من دعم بيتنا",
                body="فريق الدعم رد على طلب المساعدة بتاعك.",
                dedupe_key=f"support-reply:{ticket.id}:{self.repo.messages(ticket.id, include_internal=True)[-1].id}",
                action_url=f"/support/tickets/{ticket.id}",
                data_json={"ticket_id": str(ticket.id)},
            )
        self.db.commit()
        return self._ticket_response(ticket, include_internal=True)

    def update_status(
        self,
        *,
        admin_id: UUID,
        ticket_id: UUID,
        payload: TicketStatusUpdateRequest,
        request_id: str | None,
    ) -> SupportTicketResponse:
        ticket = self.repo.ticket(ticket_id)
        if ticket is None:
            raise ApiError(404, "support_ticket_not_found", "طلب الدعم غير موجود.")

        allowed = {
            "new": {"assigned", "investigating", "closed"},
            "assigned": {"investigating", "awaiting_customer", "awaiting_internal", "resolved", "closed"},
            "investigating": {"awaiting_customer", "awaiting_internal", "resolved", "closed"},
            "awaiting_customer": {"investigating", "resolved", "closed"},
            "awaiting_internal": {"investigating", "resolved", "closed"},
            "resolved": {"closed", "investigating"},
            "closed": set(),
        }

        if payload.status == ticket.status:
            return self._ticket_response(ticket, include_internal=True)

        if payload.status not in allowed[ticket.status]:
            raise ApiError(
                409,
                "support_invalid_transition",
                "لا يمكن نقل طلب الدعم إلى الحالة المطلوبة.",
            )

        if payload.status == "resolved":
            if not payload.resolution_code or not payload.resolution_note:
                raise ApiError(
                    422,
                    "support_resolution_required",
                    "كود وملاحظة الحل مطلوبان عند إغلاق المشكلة كـ resolved.",
                )
            ticket.resolution_code = payload.resolution_code
            ticket.resolution_note = payload.resolution_note
            ticket.resolved_at = utc_now()

        if payload.status == "closed":
            ticket.closed_at = utc_now()

        ticket.status = payload.status
        if ticket.assigned_admin_id is None:
            ticket.assigned_admin_id = admin_id

        self.audit.add(
            action="support.ticket.status_changed",
            actor_user_id=admin_id,
            entity_type="support_ticket",
            entity_id=str(ticket.id),
            request_id=request_id,
            metadata={"status": payload.status},
        )
        if payload.status in {"resolved", "closed"}:
            NotificationService(self.db, self.settings).emit(
                user_id=ticket.customer_id,
                kind="support_status",
                title="تم تحديث طلب الدعم",
                body=(
                    "تم حل طلب الدعم الخاص بك."
                    if payload.status == "resolved"
                    else "تم إغلاق طلب الدعم الخاص بك."
                ),
                dedupe_key=f"support-status:{ticket.id}:{payload.status}",
                action_url=f"/support/tickets/{ticket.id}",
                data_json={"ticket_id": str(ticket.id), "status": payload.status},
            )
        self.db.commit()
        return self._ticket_response(ticket, include_internal=True)

    def _attach_media(self, *, message: SupportMessageEntity, actor_user_id: UUID, attachment_ids: list[UUID], admin: bool = False) -> None:
        for asset_id in dict.fromkeys(attachment_ids):
            asset = self.db.get(MediaAssetEntity, asset_id)
            if asset is None or asset.status != "ready" or asset.purpose not in {"support_attachment", "customer_attachment"}:
                raise ApiError(404, "support_attachment_not_found", "المرفق غير موجود أو غير جاهز.")
            if not admin and asset.owner_user_id != actor_user_id:
                raise ApiError(404, "support_attachment_not_found", "المرفق غير موجود أو غير جاهز.")
            if admin and asset.owner_user_id != actor_user_id:
                raise ApiError(404, "support_attachment_not_found", "المرفق الإداري يجب أن يكون مملوكًا للموظف الحالي.")
            self.db.add(SupportMessageAttachmentEntity(message_id=message.id, media_asset_id=asset.id))

    def _message_response(self, message: SupportMessageEntity) -> SupportMessageResponse:
        rows = self.db.execute(
            select(SupportMessageAttachmentEntity, MediaAssetEntity)
            .join(MediaAssetEntity, MediaAssetEntity.id == SupportMessageAttachmentEntity.media_asset_id)
            .where(SupportMessageAttachmentEntity.message_id == message.id)
            .order_by(SupportMessageAttachmentEntity.created_at.asc())
        ).all()
        return SupportMessageResponse(
            id=message.id, sender_role=message.sender_role, body=message.body, is_internal=message.is_internal, created_at=message.created_at,
            attachments=[SupportAttachmentResponse(media_asset_id=asset.id, mime_type=asset.mime_type, filename=asset.original_filename) for _, asset in rows],
        )

    def _ticket_response(
        self,
        ticket: SupportTicketEntity,
        *,
        include_internal: bool,
    ) -> SupportTicketResponse:
        messages = self.repo.messages(
            ticket.id,
            include_internal=include_internal,
        )
        return SupportTicketResponse(
            id=ticket.id,
            customer_id=ticket.customer_id,
            order_id=ticket.order_id,
            assigned_admin_id=ticket.assigned_admin_id,
            category=ticket.category,
            subject=ticket.subject,
            description=ticket.description,
            priority=ticket.priority,
            status=ticket.status,
            resolution_code=ticket.resolution_code,
            resolution_note=ticket.resolution_note,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            resolved_at=ticket.resolved_at,
            closed_at=ticket.closed_at,
            messages=[
                self._message_response(x)
                for x in messages
            ],
        )
