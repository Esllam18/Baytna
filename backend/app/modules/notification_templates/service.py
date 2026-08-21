from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db_models import NotificationTemplateEntity
from app.core.errors import ApiError
from app.modules.notification_templates.schemas import NotificationTemplatePreviewResponse, NotificationTemplateResponse, NotificationTemplateUpsertRequest

class SafeMap(dict):
    def __missing__(self, key):
        return "{" + key + "}"

class NotificationTemplateService:
    def __init__(self, db: Session): self.db=db
    def render(self, *, kind: str, fallback_title: str, fallback_body: str, data: dict) -> tuple[str,str]:
        row=self.db.scalar(select(NotificationTemplateEntity).where(NotificationTemplateEntity.kind==kind))
        if row is None or not row.is_enabled: return fallback_title, fallback_body
        values=SafeMap({k:str(v) for k,v in (data or {}).items()})
        return row.title_template.format_map(values), row.body_template.format_map(values)
    def list(self):
        return [NotificationTemplateResponse.model_validate(x) for x in self.db.scalars(select(NotificationTemplateEntity).order_by(NotificationTemplateEntity.kind)).all()]
    def upsert(self, *, kind:str, payload:NotificationTemplateUpsertRequest, admin_id:UUID):
        row=self.db.scalar(select(NotificationTemplateEntity).where(NotificationTemplateEntity.kind==kind))
        if row is None: row=NotificationTemplateEntity(kind=kind); self.db.add(row)
        row.title_template=payload.title_template; row.body_template=payload.body_template; row.is_enabled=payload.is_enabled; row.updated_by_admin_id=admin_id
        self.db.commit(); self.db.refresh(row); return NotificationTemplateResponse.model_validate(row)
    def preview(self, *, kind:str, data:dict):
        row=self.db.scalar(select(NotificationTemplateEntity).where(NotificationTemplateEntity.kind==kind))
        if row is None: raise ApiError(404,"notification_template_not_found","قالب الإشعار غير موجود.")
        values=SafeMap({k:str(v) for k,v in (data or {}).items()})
        return NotificationTemplatePreviewResponse(title=row.title_template.format_map(values), body=row.body_template.format_map(values))
