from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import SpecialOrderRequestEntity, UserEntity
from app.core.models import UserRole
from app.modules.special_orders.schemas import SpecialOrderResponse
from app.modules.special_orders.service import SpecialOrderService

router = APIRouter(prefix="/admin/special-orders", tags=["admin-special-orders"])


@router.get("", response_model=list[SpecialOrderResponse])
def list_special_orders(
    status: str | None = Query(default=None),
    _: UserEntity = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[SpecialOrderResponse]:
    svc = SpecialOrderService(db, settings)
    svc.expire_due_requests()
    stmt = select(SpecialOrderRequestEntity)
    if status:
        stmt = stmt.where(SpecialOrderRequestEntity.status == status)
    stmt = stmt.order_by(SpecialOrderRequestEntity.created_at.desc())
    return [svc._response(x) for x in db.scalars(stmt).all()]
