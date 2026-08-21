from __future__ import annotations
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db_models import (
    AdminOrderNoteEntity, AuditLogEntity, ChefProfileEntity, CustomerProfileEntity,
    DeliveryTaskEntity, DishEntity, DriverProfileEntity, OrderDeliveryAddressEntity,
    OrderEntity, OrderItemEntity, OrderPricingAdjustmentEntity, OrderStatusEventEntity,
    PaymentEntity, RefundEntity, ReviewEntity, SupportTicketEntity, UserEntity,
)
from app.core.errors import ApiError
from app.core.repositories import AuditRepository
from app.core.security import utc_now
from app.modules.admin_ops.schemas import (
    AdminChefDetail, AdminChefListItem, AdminDashboardOverview, AdminDriverDetail,
    AdminDriverListItem, AdminOrderDetail, AdminOrderListItem, AdminOrderNoteResponse,
    AuditItem, FinanceSummary, OperationsReport, SupportWorkloadSummary,
)

ACTIVE_ORDER_STATUSES = {
    "confirmed", "accepted_by_chef", "preparing", "ready_for_pickup",
    "assigned_to_driver", "picked_up", "out_for_delivery",
}
OPEN_SUPPORT = {"new","assigned","investigating","awaiting_customer","awaiting_internal"}


def _range(date_from: date | None, date_to: date | None, default_days: int = 7):
    today = datetime.now(timezone.utc).date()
    end = date_to or today
    start = date_from or (end - timedelta(days=default_days - 1))
    if end < start:
        raise ApiError(422, "date_range_invalid", "تاريخ النهاية يجب ألا يسبق تاريخ البداية.")
    if (end - start).days > 366:
        raise ApiError(422, "date_range_too_large", "الحد الأقصى للفترة هو 367 يومًا.")
    start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return start, end, start_dt, end_dt


def _masked_phone(phone: str) -> str:
    if len(phone) <= 4: return "****"
    return "*" * max(4, len(phone)-4) + phone[-4:]


class AdminOperationsService:
    def __init__(self, db: Session) -> None:
        self.db=db; self.audit=AuditRepository(db)

    def overview(self, date_from: date | None, date_to: date | None) -> AdminDashboardOverview:
        start,end,start_dt,end_dt=_range(date_from,date_to)
        orders=list(self.db.scalars(select(OrderEntity).where(OrderEntity.created_at>=start_dt,OrderEntity.created_at<end_dt)).all())
        successful=list(self.db.scalars(select(PaymentEntity).where(PaymentEntity.status=="succeeded",PaymentEntity.succeeded_at>=start_dt,PaymentEntity.succeeded_at<end_dt)).all())
        refunds=list(self.db.scalars(select(RefundEntity).where(RefundEntity.status=="succeeded",RefundEntity.completed_at>=start_dt,RefundEntity.completed_at<end_dt)).all())
        delivered=sum(1 for x in orders if x.status=="delivered")
        cancelled=sum(1 for x in orders if x.status in {"cancelled","expired"})
        completed=delivered+cancelled
        gmv=sum(x.total_minor for x in orders if x.status=="delivered")
        captured=sum(x.amount_minor for x in successful)
        refunded=sum(x.amount_minor for x in refunds)
        open_support=int(self.db.scalar(select(func.count(SupportTicketEntity.id)).where(SupportTicketEntity.status.in_(OPEN_SUPPORT))) or 0)
        active_chefs=int(self.db.scalar(select(func.count(ChefProfileEntity.user_id)).where(ChefProfileEntity.status=="active")) or 0)
        verified_chefs=int(self.db.scalar(select(func.count(ChefProfileEntity.user_id)).where(ChefProfileEntity.is_verified.is_(True))) or 0)
        available_drivers=int(self.db.scalar(select(func.count(DriverProfileEntity.user_id)).where(DriverProfileEntity.status=="available")) or 0)
        mission_drivers=int(self.db.scalar(select(func.count(DriverProfileEntity.user_id)).where(DriverProfileEntity.status=="on_mission")) or 0)
        return AdminDashboardOverview(
            date_from=start,date_to=end,orders_total=len(orders),
            active_orders=sum(1 for x in orders if x.status in ACTIVE_ORDER_STATUSES),
            delivered_orders=delivered,cancelled_orders=cancelled,gmv_minor=gmv,
            captured_payments_minor=captured,refunds_minor=refunded,
            net_collected_minor=max(0,captured-refunded),
            average_order_value_minor=round(gmv/delivered) if delivered else 0,
            open_support_tickets=open_support,active_chefs=active_chefs,
            verified_chefs=verified_chefs,available_drivers=available_drivers,
            on_mission_drivers=mission_drivers,
            delivery_success_rate_pct=round(delivered/completed*100,2) if completed else 0.0,
        )

    def list_orders(self, *, status: str | None, chef_id: UUID | None, customer_id: UUID | None, date_from: date | None, date_to: date | None, limit: int, offset: int):
        stmt=select(OrderEntity)
        if status: stmt=stmt.where(OrderEntity.status==status)
        if chef_id: stmt=stmt.where(OrderEntity.chef_id==chef_id)
        if customer_id: stmt=stmt.where(OrderEntity.customer_id==customer_id)
        if date_from or date_to:
            _,_,start_dt,end_dt=_range(date_from,date_to,30); stmt=stmt.where(OrderEntity.created_at>=start_dt,OrderEntity.created_at<end_dt)
        rows=list(self.db.scalars(stmt.order_by(OrderEntity.created_at.desc()).offset(offset).limit(limit)).all())
        return [self._order_item(x) for x in rows]

    def _order_item(self, order: OrderEntity) -> AdminOrderListItem:
        user=self.db.get(UserEntity,order.customer_id); profile=self.db.get(CustomerProfileEntity,order.customer_id); chef=self.db.get(ChefProfileEntity,order.chef_id)
        payment=self.db.scalar(select(PaymentEntity).where(PaymentEntity.order_id==order.id).order_by(PaymentEntity.created_at.desc()).limit(1))
        delivery=self.db.scalar(select(DeliveryTaskEntity).where(DeliveryTaskEntity.order_id==order.id))
        return AdminOrderListItem(id=order.id,customer_id=order.customer_id,customer_name=profile.display_name if profile else None,customer_phone_masked=_masked_phone(user.phone if user else ""),chef_id=order.chef_id,chef_name=chef.display_name if chef else "",service_date=order.service_date,status=order.status,subtotal_minor=order.subtotal_minor,discount_minor=order.discount_minor,total_minor=order.total_minor,currency=order.currency,payment_status=payment.status if payment else None,delivery_status=delivery.status if delivery else None,promised_delivery_window_start_at=order.promised_delivery_window_start_at,promised_delivery_window_end_at=order.promised_delivery_window_end_at,promised_delivery_timezone=order.promised_delivery_timezone,created_at=order.created_at)

    def order_detail(self, order_id: UUID) -> AdminOrderDetail:
        order=self.db.get(OrderEntity,order_id)
        if order is None: raise ApiError(404,"order_not_found","الطلب غير موجود.")
        items=list(self.db.scalars(select(OrderItemEntity).where(OrderItemEntity.order_id==order.id)).all())
        adjustments=list(self.db.scalars(select(OrderPricingAdjustmentEntity).where(OrderPricingAdjustmentEntity.order_id==order.id)).all())
        payment=self.db.scalar(select(PaymentEntity).where(PaymentEntity.order_id==order.id).order_by(PaymentEntity.created_at.desc()).limit(1))
        refunds=list(self.db.scalars(select(RefundEntity).where(RefundEntity.order_id==order.id).order_by(RefundEntity.created_at.asc())).all())
        delivery=self.db.scalar(select(DeliveryTaskEntity).where(DeliveryTaskEntity.order_id==order.id)); address=self.db.get(OrderDeliveryAddressEntity,order.id)
        events=list(self.db.scalars(select(OrderStatusEventEntity).where(OrderStatusEventEntity.order_id==order.id).order_by(OrderStatusEventEntity.created_at.asc())).all())
        tickets=list(self.db.scalars(select(SupportTicketEntity).where(SupportTicketEntity.order_id==order.id).order_by(SupportTicketEntity.created_at.desc())).all())
        notes=list(self.db.scalars(select(AdminOrderNoteEntity).where(AdminOrderNoteEntity.order_id==order.id).order_by(AdminOrderNoteEntity.created_at.asc())).all())
        return AdminOrderDetail(
            order=self._order_item(order),
            items=[{"id":str(x.id),"dish_id":str(x.dish_id),"dish_name":x.dish_name,"quantity":x.quantity,"unit_price_minor":x.unit_price_minor,"line_total_minor":x.line_total_minor} for x in items],
            pricing_adjustments=[{"type":x.adjustment_type,"reference_code":x.reference_code,"amount_minor":x.amount_minor,"metadata":x.metadata_json} for x in adjustments],
            payment=({"id":str(payment.id),"status":payment.status,"amount_minor":payment.amount_minor,"refunded_minor":payment.refunded_minor,"provider":payment.provider,"provider_reference":payment.provider_reference} if payment else None),
            refunds=[{"id":str(x.id),"amount_minor":x.amount_minor,"status":x.status,"reason":x.reason,"created_at":x.created_at.isoformat()} for x in refunds],
            delivery=({"id":str(delivery.id),"driver_id":str(delivery.driver_id) if delivery.driver_id else None,"status":delivery.status,"issue_code":delivery.issue_code,"delivered_at":delivery.delivered_at.isoformat() if delivery.delivered_at else None,"delivery_timing_status":delivery.delivery_timing_status,"late_by_minutes":delivery.late_by_minutes} if delivery else None),
            delivery_address=({"area":address.area,"street":address.street,"building":address.building,"floor":address.floor,"apartment":address.apartment} if address else None),
            timeline=[{"from_status":x.from_status,"to_status":x.to_status,"reason":x.reason,"actor_user_id":str(x.actor_user_id) if x.actor_user_id else None,"created_at":x.created_at.isoformat()} for x in events],
            support_tickets=[{"id":str(x.id),"category":x.category,"priority":x.priority,"status":x.status,"subject":x.subject} for x in tickets],
            notes=[AdminOrderNoteResponse.model_validate(x) for x in notes],
        )

    def add_note(self, *, order_id: UUID, admin_id: UUID, note: str, request_id: str | None):
        if self.db.get(OrderEntity,order_id) is None: raise ApiError(404,"order_not_found","الطلب غير موجود.")
        row=AdminOrderNoteEntity(order_id=order_id,admin_user_id=admin_id,note=note); self.db.add(row); self.db.flush()
        self.audit.add(action="admin.order.note_added",actor_user_id=admin_id,entity_type="order",entity_id=str(order_id),request_id=request_id)
        self.db.commit(); self.db.refresh(row); return AdminOrderNoteResponse.model_validate(row)

    def notes(self, order_id: UUID):
        if self.db.get(OrderEntity,order_id) is None: raise ApiError(404,"order_not_found","الطلب غير موجود.")
        rows=self.db.scalars(select(AdminOrderNoteEntity).where(AdminOrderNoteEntity.order_id==order_id).order_by(AdminOrderNoteEntity.created_at.asc())).all()
        return [AdminOrderNoteResponse.model_validate(x) for x in rows]

    def chefs(self, *, status: str | None, area: str | None, verified: bool | None, limit: int, offset: int):
        stmt=select(ChefProfileEntity)
        if status: stmt=stmt.where(ChefProfileEntity.status==status)
        if area: stmt=stmt.where(ChefProfileEntity.area==area)
        if verified is not None: stmt=stmt.where(ChefProfileEntity.is_verified.is_(verified))
        rows=self.db.scalars(stmt.order_by(ChefProfileEntity.created_at.desc()).offset(offset).limit(limit)).all()
        return [self._chef_item(x) for x in rows]

    def _chef_item(self, chef: ChefProfileEntity):
        total=int(self.db.scalar(select(func.count(OrderEntity.id)).where(OrderEntity.chef_id==chef.user_id)) or 0)
        delivered=int(self.db.scalar(select(func.count(OrderEntity.id)).where(OrderEntity.chef_id==chef.user_id,OrderEntity.status=="delivered")) or 0)
        return AdminChefListItem(id=chef.user_id,display_name=chef.display_name,specialty=chef.specialty,area=chef.area,status=chef.status,rating=chef.rating,is_verified=chef.is_verified,is_open_today=chef.is_open_today,total_orders=total,delivered_orders=delivered,created_at=chef.created_at)

    def chef_detail(self, chef_id: UUID):
        chef=self.db.get(ChefProfileEntity,chef_id)
        if chef is None: raise ApiError(404,"chef_not_found","الشيف غير موجود.")
        base=self._chef_item(chef)
        active=int(self.db.scalar(select(func.count(OrderEntity.id)).where(OrderEntity.chef_id==chef_id,OrderEntity.status.in_(ACTIVE_ORDER_STATUSES))) or 0)
        dishes=int(self.db.scalar(select(func.count(DishEntity.id)).where(DishEntity.chef_id==chef_id, DishEntity.is_active.is_(True))) or 0)
        reviews=list(self.db.scalars(select(ReviewEntity).where(ReviewEntity.chef_id==chef_id,ReviewEntity.is_visible.is_(True))).all())
        open_support=int(self.db.scalar(select(func.count(SupportTicketEntity.id)).join(OrderEntity,OrderEntity.id==SupportTicketEntity.order_id).where(OrderEntity.chef_id==chef_id,SupportTicketEntity.status.in_(OPEN_SUPPORT))) or 0)
        return AdminChefDetail(**base.model_dump(),active_orders=active,dishes_count=dishes,reviews_count=len(reviews),avg_food_quality=round(sum(x.food_quality for x in reviews)/len(reviews),2) if reviews else 0.0,open_support_tickets=open_support)

    def update_chef_status(self, *, chef_id: UUID, status: str, reason: str | None, admin_id: UUID, request_id: str | None):
        chef=self.db.get(ChefProfileEntity,chef_id)
        if chef is None: raise ApiError(404,"chef_not_found","الشيف غير موجود.")
        if status in {"suspended","rejected"} and not reason:
            raise ApiError(422,"chef_status_reason_required","سبب التغيير مطلوب لهذه الحالة.")
        old=chef.status; chef.status=status
        if status != "active": chef.is_open_today=False
        self.audit.add(action="admin.chef.status_changed",actor_user_id=admin_id,entity_type="chef_profile",entity_id=str(chef_id),request_id=request_id,metadata={"from":old,"to":status,"reason":reason})
        self.db.commit(); return self.chef_detail(chef_id)

    def drivers(self, *, status: str | None, limit: int, offset: int):
        stmt=select(DriverProfileEntity)
        if status: stmt=stmt.where(DriverProfileEntity.status==status)
        rows=self.db.scalars(stmt.order_by(DriverProfileEntity.created_at.desc()).offset(offset).limit(limit)).all()
        return [self._driver_item(x) for x in rows]

    def _driver_item(self, driver: DriverProfileEntity):
        active=self.db.scalar(select(DeliveryTaskEntity).where(DeliveryTaskEntity.driver_id==driver.user_id,DeliveryTaskEntity.status.in_(["to_pickup","at_pickup","picked_up","to_customer","delivery_issue"])).order_by(DeliveryTaskEntity.updated_at.desc()).limit(1))
        delivered=int(self.db.scalar(select(func.count(DeliveryTaskEntity.id)).where(DeliveryTaskEntity.driver_id==driver.user_id,DeliveryTaskEntity.status=="delivered")) or 0)
        issues=int(self.db.scalar(select(func.count(DeliveryTaskEntity.id)).where(DeliveryTaskEntity.driver_id==driver.user_id,DeliveryTaskEntity.issue_code.is_not(None))) or 0)
        return AdminDriverListItem(id=driver.user_id,status=driver.status,rating=driver.rating,active_mission_id=active.id if active else None,delivered_missions=delivered,issue_missions=issues,created_at=driver.created_at)

    def driver_detail(self, driver_id: UUID):
        driver=self.db.get(DriverProfileEntity,driver_id)
        if driver is None: raise ApiError(404,"driver_not_found","المندوب غير موجود.")
        base=self._driver_item(driver)
        total=int(self.db.scalar(select(func.count(DeliveryTaskEntity.id)).where(DeliveryTaskEntity.driver_id==driver_id)) or 0)
        active=self.db.scalar(select(DeliveryTaskEntity).where(DeliveryTaskEntity.driver_id==driver_id,DeliveryTaskEntity.status.in_(["to_pickup","at_pickup","picked_up","to_customer","delivery_issue"])).order_by(DeliveryTaskEntity.updated_at.desc()).limit(1))
        current={"id":str(active.id),"order_id":str(active.order_id),"status":active.status,"issue_code":active.issue_code} if active else None
        return AdminDriverDetail(**base.model_dump(),total_missions=total,current_mission=current)

    def support_summary(self):
        rows=list(self.db.scalars(select(SupportTicketEntity)).all())
        open_rows=[x for x in rows if x.status in OPEN_SUPPORT]
        return SupportWorkloadSummary(total_open=len(open_rows),new=sum(x.status=="new" for x in open_rows),assigned=sum(x.status=="assigned" for x in open_rows),investigating=sum(x.status=="investigating" for x in open_rows),awaiting_customer=sum(x.status=="awaiting_customer" for x in open_rows),awaiting_internal=sum(x.status=="awaiting_internal" for x in open_rows),urgent_open=sum(x.priority=="urgent" for x in open_rows),unassigned_open=sum(x.assigned_admin_id is None for x in open_rows))

    def finance_summary(self, date_from: date | None, date_to: date | None):
        start,end,start_dt,end_dt=_range(date_from,date_to,30)
        payments=list(self.db.scalars(select(PaymentEntity).where(PaymentEntity.created_at>=start_dt,PaymentEntity.created_at<end_dt)).all())
        refunds=list(self.db.scalars(select(RefundEntity).where(RefundEntity.created_at>=start_dt,RefundEntity.created_at<end_dt)).all())
        adjustments=list(self.db.scalars(select(OrderPricingAdjustmentEntity).join(OrderEntity,OrderEntity.id==OrderPricingAdjustmentEntity.order_id).where(OrderEntity.created_at>=start_dt,OrderEntity.created_at<end_dt)).all())
        successful=[x for x in payments if x.status=="succeeded"]; succeeded_refunds=[x for x in refunds if x.status=="succeeded"]
        captured=sum(x.amount_minor for x in successful); refunded=sum(x.amount_minor for x in succeeded_refunds)
        sums={"coupon":0,"loyalty":0,"subscription":0}
        for x in adjustments: sums[x.adjustment_type]=sums.get(x.adjustment_type,0)+x.amount_minor
        return FinanceSummary(date_from=start,date_to=end,successful_payments_count=len(successful),captured_minor=captured,refunds_count=len(succeeded_refunds),refunded_minor=refunded,net_collected_minor=max(0,captured-refunded),pending_payments_count=sum(x.status=="pending" for x in payments),failed_payments_count=sum(x.status in {"failed","cancelled","expired"} for x in payments),coupon_discount_minor=sums["coupon"],loyalty_discount_minor=sums["loyalty"],subscription_discount_minor=sums["subscription"])

    def audit_logs(self, *, action: str | None, entity_type: str | None, actor_user_id: UUID | None, limit: int, offset: int):
        stmt=select(AuditLogEntity)
        if action: stmt=stmt.where(AuditLogEntity.action==action)
        if entity_type: stmt=stmt.where(AuditLogEntity.entity_type==entity_type)
        if actor_user_id: stmt=stmt.where(AuditLogEntity.actor_user_id==actor_user_id)
        rows=self.db.scalars(stmt.order_by(AuditLogEntity.created_at.desc()).offset(offset).limit(limit)).all()
        return [AuditItem.model_validate(x,from_attributes=True) for x in rows]

    def operations_report(self, date_from: date | None, date_to: date | None):
        chefs=self.chefs(status="active",area=None,verified=None,limit=100,offset=0)
        chefs=sorted(chefs,key=lambda x:(x.delivered_orders,x.rating),reverse=True)[:5]
        return OperationsReport(generated_at=utc_now(),overview=self.overview(date_from,date_to),finance=self.finance_summary(date_from,date_to),support=self.support_summary(),top_chefs=chefs)
