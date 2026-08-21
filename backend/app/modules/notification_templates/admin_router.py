from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.auth import require_roles
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.models import UserRole
from app.modules.notification_templates.schemas import NotificationTemplatePreviewRequest, NotificationTemplatePreviewResponse, NotificationTemplateResponse, NotificationTemplateUpsertRequest
from app.modules.notification_templates.service import NotificationTemplateService
router=APIRouter(prefix="/admin/notification-templates", tags=["admin-notification-templates"])
@router.get("", response_model=list[NotificationTemplateResponse])
def list_templates(_:UserEntity=Depends(require_roles(UserRole.ADMIN)), db:Session=Depends(get_db)): return NotificationTemplateService(db).list()
@router.put("/{kind}", response_model=NotificationTemplateResponse)
def upsert(kind:str,payload:NotificationTemplateUpsertRequest,admin:UserEntity=Depends(require_roles(UserRole.ADMIN)),db:Session=Depends(get_db)): return NotificationTemplateService(db).upsert(kind=kind,payload=payload,admin_id=admin.id)
@router.post("/{kind}/preview", response_model=NotificationTemplatePreviewResponse)
def preview(kind:str,payload:NotificationTemplatePreviewRequest,_:UserEntity=Depends(require_roles(UserRole.ADMIN)),db:Session=Depends(get_db)): return NotificationTemplateService(db).preview(kind=kind,data=payload.data)
