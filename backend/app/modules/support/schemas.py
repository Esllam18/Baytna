from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SupportTicketCreateRequest(BaseModel):
    order_id: UUID | None = None
    category: str = Field(
        pattern=r"^(food_quality|missing_item|wrong_item|late_delivery|delivery_issue|refund|payment|app_issue|other)$"
    )
    subject: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=3, max_length=4000)
    priority: str = Field(default="normal", pattern=r"^(normal|high|urgent)$")
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=5)


class SupportMessageCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=5)


class AdminSupportMessageCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    is_internal: bool = False
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=5)


class SupportAttachmentResponse(BaseModel):
    media_asset_id: UUID
    mime_type: str
    filename: str | None


class SupportMessageResponse(BaseModel):
    id: UUID
    sender_role: str
    body: str
    is_internal: bool
    created_at: datetime
    attachments: list[SupportAttachmentResponse] = []

    model_config = {"from_attributes": True}


class SupportTicketResponse(BaseModel):
    id: UUID
    customer_id: UUID
    order_id: UUID | None
    assigned_admin_id: UUID | None
    category: str
    subject: str
    description: str
    priority: str
    status: str
    resolution_code: str | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None
    messages: list[SupportMessageResponse] = []


class AssignTicketRequest(BaseModel):
    admin_id: UUID | None = None


class TicketStatusUpdateRequest(BaseModel):
    status: str = Field(
        pattern=r"^(assigned|investigating|awaiting_customer|awaiting_internal|resolved|closed)$"
    )
    resolution_code: str | None = Field(default=None, max_length=80)
    resolution_note: str | None = Field(default=None, max_length=4000)
