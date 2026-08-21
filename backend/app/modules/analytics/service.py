from __future__ import annotations
from datetime import date, datetime, time, timedelta, timezone
from collections import Counter, defaultdict
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db_models import OrderEntity, OrderStatusEventEntity, PaymentEntity, RefundEntity
from app.core.errors import ApiError
from app.modules.analytics.schemas import DailyMetric, FunnelResponse, RetentionAnalytics


def _bounds(days:int):
    if days<1 or days>90: raise ApiError(422,"analytics_days_invalid","عدد الأيام يجب أن يكون بين 1 و90.")
    end=datetime.now(timezone.utc).date(); start=end-timedelta(days=days-1)
    return start,end,datetime.combine(start,time.min,tzinfo=timezone.utc),datetime.combine(end+timedelta(days=1),time.min,tzinfo=timezone.utc)

class AnalyticsService:
    def __init__(self,db:Session): self.db=db

    def daily(self,days:int):
        start,end,start_dt,end_dt=_bounds(days)
        orders=list(self.db.scalars(select(OrderEntity).where(OrderEntity.created_at>=start_dt,OrderEntity.created_at<end_dt)).all())
        payments=list(self.db.scalars(select(PaymentEntity).where(PaymentEntity.created_at>=start_dt,PaymentEntity.created_at<end_dt)).all())
        refunds=list(self.db.scalars(select(RefundEntity).where(RefundEntity.created_at>=start_dt,RefundEntity.created_at<end_dt)).all())
        data={start+timedelta(days=i):{"orders":0,"delivered":0,"cancelled":0,"gmv":0,"captured":0,"refunds":0} for i in range(days)}
        for x in orders:
            d=x.created_at.date();
            if d in data:
                data[d]["orders"]+=1
                if x.status=="delivered": data[d]["delivered"]+=1; data[d]["gmv"]+=x.total_minor
                if x.status in {"cancelled","expired"}: data[d]["cancelled"]+=1
        for x in payments:
            if x.status=="succeeded" and x.succeeded_at and x.succeeded_at.date() in data: data[x.succeeded_at.date()]["captured"]+=x.amount_minor
        for x in refunds:
            if x.status=="succeeded" and x.completed_at and x.completed_at.date() in data: data[x.completed_at.date()]["refunds"]+=x.amount_minor
        return [DailyMetric(day=d,orders_created=v["orders"],delivered_orders=v["delivered"],cancelled_orders=v["cancelled"],gmv_minor=v["gmv"],captured_minor=v["captured"],refunds_minor=v["refunds"]) for d,v in data.items()]

    def funnel(self,days:int):
        _,_,start_dt,end_dt=_bounds(days)
        orders=list(self.db.scalars(select(OrderEntity).where(OrderEntity.created_at>=start_dt,OrderEntity.created_at<end_dt)).all())
        ids={x.id for x in orders}; reached=defaultdict(set)
        if ids:
            events=list(self.db.scalars(select(OrderStatusEventEntity).where(OrderStatusEventEntity.order_id.in_(ids))).all())
            for e in events: reached[e.to_status].add(e.order_id)
        # Current status is also a valid reached stage for direct/imported orders.
        stages=["confirmed","accepted_by_chef","ready_for_pickup","assigned_to_driver","picked_up","out_for_delivery","delivered"]
        stage_order={s:i for i,s in enumerate(["pending_payment"]+stages)}
        for o in orders:
            if o.status in stage_order:
                oi=stage_order[o.status]
                for s in stages:
                    if stage_order[s]<=oi: reached[s].add(o.id)
        return FunnelResponse(orders_created=len(orders),reached_confirmed=len(reached["confirmed"]),reached_accepted_by_chef=len(reached["accepted_by_chef"]),reached_ready_for_pickup=len(reached["ready_for_pickup"]),reached_assigned_to_driver=len(reached["assigned_to_driver"]),reached_picked_up=len(reached["picked_up"]),reached_out_for_delivery=len(reached["out_for_delivery"]),reached_delivered=len(reached["delivered"]))

    def retention(self,days:int):
        _,_,start_dt,end_dt=_bounds(days)
        orders=list(self.db.scalars(select(OrderEntity).where(OrderEntity.created_at>=start_dt,OrderEntity.created_at<end_dt,OrderEntity.status=="delivered")).all())
        counts=Counter(x.customer_id for x in orders); unique=len(counts); repeat=sum(v>=2 for v in counts.values())
        return RetentionAnalytics(delivered_orders=len(orders),unique_customers=unique,repeat_customers=repeat,repeat_customer_rate_pct=round(repeat/unique*100,2) if unique else 0.0,average_delivered_orders_per_customer=round(len(orders)/unique,2) if unique else 0.0)
