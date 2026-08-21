from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class NotificationTemplateUpsertRequest(BaseModel):
    title_template: str = Field(min_length=1, max_length=180)
    body_template: str = Field(min_length=1, max_length=4000)
    is_enabled: bool = True

class NotificationTemplatePreviewRequest(BaseModel):
    data: dict = {}

class NotificationTemplateResponse(BaseModel):
    id: UUID
    kind: str
    title_template: str
    body_template: str
    is_enabled: bool
    updated_by_admin_id: UUID | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class NotificationTemplatePreviewResponse(BaseModel):
    title: str
    body: str
