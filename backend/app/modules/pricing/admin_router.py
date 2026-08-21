from datetime import timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.auth import require_roles
from app.core.database import get_db
from app.core.db_models import CouponEntity, CustomerSubscriptionEntity, SubscriptionPlanEntity, UserEntity
from app.core.errors import ApiError
from app.core.models import UserRole
from app.core.repositories import AuditRepository
from app.core.security import utc_now
from app.modules.pricing.schemas import CouponCreateRequest, CouponResponse, CouponUpdateRequest, CustomerSubscriptionResponse, GrantSubscriptionRequest, SubscriptionPlanCreateRequest, SubscriptionPlanResponse

router = APIRouter(prefix="/admin/pricing", tags=["admin-pricing"])

def admin_user(user: UserEntity = Depends(require_roles(UserRole.ADMIN))) -> UserEntity: return user

@router.post("/coupons", response_model=CouponResponse, status_code=201)
def create_coupon(payload: CouponCreateRequest, request: Request, admin: UserEntity = Depends(admin_user), db: Session = Depends(get_db)):
    if payload.discount_type == "percent" and payload.discount_value > 10000:
        raise ApiError(422, "coupon_percent_invalid", "نسبة الخصم لا يمكن أن تتجاوز 100%.")
    if payload.starts_at and payload.ends_at and payload.ends_at <= payload.starts_at:
        raise ApiError(422, "coupon_dates_invalid", "تاريخ نهاية الكوبون يجب أن يكون بعد البداية.")
    if db.scalar(select(CouponEntity).where(CouponEntity.code == payload.code)):
        raise ApiError(409, "coupon_code_exists", "كود الكوبون مستخدم بالفعل.")
    row=CouponEntity(**payload.model_dump()); db.add(row); db.flush(); AuditRepository(db).add(action="admin.coupon.created", actor_user_id=admin.id, entity_type="coupon", entity_id=str(row.id), request_id=request.state.request_id); db.commit(); db.refresh(row); return row

@router.get("/coupons", response_model=list[CouponResponse])
def list_coupons(_: UserEntity = Depends(admin_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(CouponEntity).order_by(CouponEntity.created_at.desc())).all())

@router.patch("/coupons/{coupon_id}", response_model=CouponResponse)
def update_coupon(coupon_id: UUID, payload: CouponUpdateRequest, request: Request, admin: UserEntity = Depends(admin_user), db: Session = Depends(get_db)):
    row=db.get(CouponEntity,coupon_id)
    if row is None: raise ApiError(404,"coupon_not_found","الكوبون غير موجود.")
    for k,v in payload.model_dump(exclude_unset=True).items(): setattr(row,k,v)
    if row.starts_at and row.ends_at and row.ends_at <= row.starts_at: raise ApiError(422,"coupon_dates_invalid","تاريخ نهاية الكوبون يجب أن يكون بعد البداية.")
    AuditRepository(db).add(action="admin.coupon.updated",actor_user_id=admin.id,entity_type="coupon",entity_id=str(row.id),request_id=request.state.request_id); db.commit(); db.refresh(row); return row

@router.post("/subscription-plans", response_model=SubscriptionPlanResponse, status_code=201)
def create_plan(payload: SubscriptionPlanCreateRequest, request: Request, admin: UserEntity = Depends(admin_user), db: Session = Depends(get_db)):
    if db.scalar(select(SubscriptionPlanEntity).where(SubscriptionPlanEntity.code == payload.code)): raise ApiError(409,"subscription_plan_code_exists","كود الخطة مستخدم بالفعل.")
    row=SubscriptionPlanEntity(**payload.model_dump()); db.add(row); db.flush(); AuditRepository(db).add(action="admin.subscription_plan.created",actor_user_id=admin.id,entity_type="subscription_plan",entity_id=str(row.id),request_id=request.state.request_id); db.commit(); db.refresh(row); return row

@router.post("/subscription-plans/{plan_id}/grant", response_model=CustomerSubscriptionResponse, status_code=201)
def grant_subscription(plan_id: UUID, payload: GrantSubscriptionRequest, request: Request, admin: UserEntity = Depends(admin_user), db: Session = Depends(get_db)):
    plan=db.get(SubscriptionPlanEntity,plan_id)
    if plan is None or not plan.is_active: raise ApiError(404,"subscription_plan_not_found","خطة الاشتراك غير موجودة.")
    customer=db.get(UserEntity,payload.customer_id)
    if customer is None: raise ApiError(404,"customer_not_found","العميل غير موجود.")
    now=utc_now()
    for old in db.scalars(select(CustomerSubscriptionEntity).where(CustomerSubscriptionEntity.customer_id==payload.customer_id,CustomerSubscriptionEntity.status=="active")).all():
        old.status="cancelled"; old.cancelled_at=now
    row=CustomerSubscriptionEntity(customer_id=payload.customer_id,plan_id=plan.id,status="active",source=payload.source,starts_at=now,ends_at=now+timedelta(days=plan.duration_days)); db.add(row); db.flush(); AuditRepository(db).add(action="admin.subscription.granted",actor_user_id=admin.id,entity_type="customer_subscription",entity_id=str(row.id),request_id=request.state.request_id,metadata={"customer_id":str(payload.customer_id),"plan_id":str(plan.id)}); db.commit(); db.refresh(row)
    return CustomerSubscriptionResponse(id=row.id,customer_id=row.customer_id,plan_id=plan.id,plan_code=plan.code,plan_name=plan.name,status=row.status,source=row.source,starts_at=row.starts_at,ends_at=row.ends_at,cancelled_at=row.cancelled_at)
