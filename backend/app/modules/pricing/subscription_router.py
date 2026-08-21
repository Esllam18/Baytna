from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.auth import current_user
from app.core.database import get_db
from app.core.db_models import CustomerSubscriptionEntity, SubscriptionPlanEntity, UserEntity
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import utc_now
from app.modules.pricing.schemas import CustomerSubscriptionResponse, SubscriptionPlanResponse

router=APIRouter(prefix="/customer/subscriptions", tags=["subscriptions"])

@router.get("/plans", response_model=list[SubscriptionPlanResponse])
def plans(user: UserEntity=Depends(current_user), db: Session=Depends(get_db)):
    return list(db.scalars(select(SubscriptionPlanEntity).where(SubscriptionPlanEntity.is_active.is_(True)).order_by(SubscriptionPlanEntity.price_minor.asc())).all())

@router.get("/current", response_model=CustomerSubscriptionResponse | None)
def current(user: UserEntity=Depends(current_user), db: Session=Depends(get_db)):
    now=utc_now(); row=db.scalar(select(CustomerSubscriptionEntity).where(CustomerSubscriptionEntity.customer_id==user.id,CustomerSubscriptionEntity.status=="active",CustomerSubscriptionEntity.ends_at>now).order_by(CustomerSubscriptionEntity.ends_at.desc()).limit(1))
    if row is None: return None
    plan=db.get(SubscriptionPlanEntity,row.plan_id)
    return CustomerSubscriptionResponse(id=row.id,customer_id=row.customer_id,plan_id=row.plan_id,plan_code=plan.code,plan_name=plan.name,status=row.status,source=row.source,starts_at=row.starts_at,ends_at=row.ends_at,cancelled_at=row.cancelled_at)

@router.post("/current/cancel", response_model=CustomerSubscriptionResponse)
def cancel(request: Request, user: UserEntity=Depends(current_user), db: Session=Depends(get_db)):
    now=utc_now(); row=db.scalar(select(CustomerSubscriptionEntity).where(CustomerSubscriptionEntity.customer_id==user.id,CustomerSubscriptionEntity.status=="active",CustomerSubscriptionEntity.ends_at>now).order_by(CustomerSubscriptionEntity.ends_at.desc()).limit(1))
    if row is None: raise ApiError(404,"active_subscription_not_found","لا يوجد اشتراك نشط.")
    row.status="cancelled"; row.cancelled_at=now; plan=db.get(SubscriptionPlanEntity,row.plan_id); AuditRepository(db).add(action="customer.subscription.cancelled",actor_user_id=user.id,entity_type="customer_subscription",entity_id=str(row.id),request_id=request.state.request_id); db.commit(); db.refresh(row)
    return CustomerSubscriptionResponse(id=row.id,customer_id=row.customer_id,plan_id=row.plan_id,plan_code=plan.code,plan_name=plan.name,status=row.status,source=row.source,starts_at=row.starts_at,ends_at=row.ends_at,cancelled_at=row.cancelled_at)
