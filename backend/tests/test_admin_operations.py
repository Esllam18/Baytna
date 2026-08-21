from datetime import date, timedelta
from uuid import UUID, uuid4
from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    CartEntity, CouponEntity, DeliveryTaskEntity, OrderEntity, OrderPricingAdjustmentEntity,
    PaymentEntity, RefundEntity, SupportTicketEntity, UserEntity,
)
from app.core.models import UserRole
from app.core.security import create_access_token, utc_now

CHEF_ID=UUID("10000000-0000-0000-0000-000000000001")
DRIVER_ID=UUID("30000000-0000-0000-0000-000000000001")

def login_phone(client,phone):
    sent=client.post('/api/v1/auth/send-otp',json={'phone':phone}); otp=sent.json()['development_otp']
    body=client.post('/api/v1/auth/verify-otp',json={'phone':phone,'code':otp}).json()
    return {'headers':{'Authorization':f"Bearer {body['access_token']}"},'id':UUID(body['user']['id'])}

def admin_headers():
    settings=get_settings()
    with SessionLocal() as db:
        user=UserEntity(id=uuid4(),phone=f"+2012{uuid4().int%100000000:08d}",role='admin',is_active=True); db.add(user); db.commit(); db.refresh(user)
        token,_=create_access_token(user_id=user.id,role=UserRole.ADMIN,settings=settings)
        return {'Authorization':f'Bearer {token}'},user.id

def make_order(client,status='delivered',total=30000,with_payment=True):
    c=login_phone(client,f"010{uuid4().int%100000000:08d}")
    with SessionLocal() as db:
        cart=CartEntity(customer_id=c['id'],chef_id=CHEF_ID,service_date=date.today(),status='converted'); db.add(cart); db.flush()
        order=OrderEntity(customer_id=c['id'],chef_id=CHEF_ID,source_cart_id=cart.id,service_date=date.today(),status=status,subtotal_minor=total,delivery_fee_minor=0,discount_minor=0,total_minor=total,currency='EGP'); db.add(order); db.flush()
        if with_payment:
            pay=PaymentEntity(order_id=order.id,customer_id=c['id'],provider='mock',provider_reference=f'p-{order.id}',idempotency_key=f'i-{order.id}',amount_minor=total,refunded_minor=0,currency='EGP',status='succeeded',expires_at=utc_now()+timedelta(hours=1),succeeded_at=utc_now()); db.add(pay)
        db.commit(); return order.id,c['id']

def test_customer_cannot_access_admin_dashboard(login):
    r=login['client'].get('/api/v1/admin/dashboard/overview',headers=login['headers']); assert r.status_code==403

def test_admin_dashboard_overview_counts_orders(client):
    make_order(client,'delivered',30000); make_order(client,'cancelled',20000,False)
    h,_=admin_headers(); r=client.get('/api/v1/admin/dashboard/overview',headers=h); assert r.status_code==200
    b=r.json(); assert b['orders_total']>=2; assert b['delivered_orders']>=1; assert b['captured_payments_minor']>=30000

def test_admin_order_list_filters_status(client):
    delivered,_=make_order(client,'delivered'); make_order(client,'cancelled',with_payment=False); h,_=admin_headers()
    r=client.get('/api/v1/admin/orders',params={'status':'delivered'},headers=h); assert r.status_code==200
    assert delivered.hex in ''.join(x['id'].replace('-','') for x in r.json())
    assert all(x['status']=='delivered' for x in r.json())

def test_admin_order_detail_and_internal_notes(client):
    order_id,_=make_order(client,'delivered'); h,admin_id=admin_headers()
    n=client.post(f'/api/v1/admin/orders/{order_id}/notes',headers=h,json={'note':'راجعنا الطلب مع التشغيل.'}); assert n.status_code==201
    d=client.get(f'/api/v1/admin/orders/{order_id}',headers=h); assert d.status_code==200
    assert d.json()['notes'][0]['note']=='راجعنا الطلب مع التشغيل.'
    assert d.json()['order']['customer_phone_masked'].startswith('*')

def test_admin_note_creates_audit_event(client):
    order_id,_=make_order(client); h,_=admin_headers(); client.post(f'/api/v1/admin/orders/{order_id}/notes',headers=h,json={'note':'ملاحظة تشغيلية'})
    a=client.get('/api/v1/admin/audit',params={'action':'admin.order.note_added'},headers=h); assert a.status_code==200; assert len(a.json())>=1

def test_admin_chefs_list_and_detail(client):
    h,_=admin_headers(); r=client.get('/api/v1/admin/chefs',headers=h); assert r.status_code==200; assert any(x['id']==str(CHEF_ID) for x in r.json())
    d=client.get(f'/api/v1/admin/chefs/{CHEF_ID}',headers=h); assert d.status_code==200; assert d.json()['display_name']

def test_admin_can_pause_and_reactivate_chef(client):
    h,_=admin_headers(); paused=client.patch(f'/api/v1/admin/chefs/{CHEF_ID}/status',headers=h,json={'status':'paused'}); assert paused.status_code==200; assert paused.json()['status']=='paused'
    active=client.patch(f'/api/v1/admin/chefs/{CHEF_ID}/status',headers=h,json={'status':'active'}); assert active.status_code==200; assert active.json()['status']=='active'

def test_suspend_chef_requires_reason(client):
    h,_=admin_headers(); r=client.patch(f'/api/v1/admin/chefs/{CHEF_ID}/status',headers=h,json={'status':'suspended'}); assert r.status_code==422; assert r.json()['error']['code']=='chef_status_reason_required'

def test_admin_drivers_list_and_detail(client):
    h,_=admin_headers(); r=client.get('/api/v1/admin/drivers',headers=h); assert r.status_code==200; assert any(x['id']==str(DRIVER_ID) for x in r.json())
    d=client.get(f'/api/v1/admin/drivers/{DRIVER_ID}',headers=h); assert d.status_code==200; assert d.json()['status'] in {'offline','available','on_mission'}

def test_support_workload_summary(client):
    customer=login_phone(client,'01033334444')
    with SessionLocal() as db:
        db.add(SupportTicketEntity(customer_id=customer['id'],category='other',subject='Urgent',description='help',priority='urgent',status='new')); db.commit()
    h,_=admin_headers(); r=client.get('/api/v1/admin/support/workload-summary',headers=h); assert r.status_code==200; assert r.json()['urgent_open']>=1; assert r.json()['unassigned_open']>=1

def test_finance_summary_includes_refunds_and_discounts(client):
    order_id,customer_id=make_order(client,'delivered',50000)
    with SessionLocal() as db:
        pay=db.scalar(select(PaymentEntity).where(PaymentEntity.order_id==order_id)); pay.refunded_minor=5000
        db.add(RefundEntity(order_id=order_id,payment_id=pay.id,requested_by_user_id=None,amount_minor=5000,reason='test',idempotency_key=f'r-{order_id}',status='succeeded',provider_reference='rf',completed_at=utc_now()))
        db.add(OrderPricingAdjustmentEntity(order_id=order_id,adjustment_type='coupon',reference_code='X',amount_minor=2000,metadata_json={}))
        db.commit()
    h,_=admin_headers(); r=client.get('/api/v1/admin/finance/summary',headers=h); assert r.status_code==200
    b=r.json(); assert b['captured_minor']>=50000; assert b['refunded_minor']>=5000; assert b['coupon_discount_minor']>=2000

def test_invalid_dashboard_date_range_rejected(client):
    h,_=admin_headers(); r=client.get('/api/v1/admin/dashboard/overview',params={'date_from':'2026-08-10','date_to':'2026-08-01'},headers=h); assert r.status_code==422; assert r.json()['error']['code']=='date_range_invalid'

def test_daily_analytics_returns_requested_days(client):
    make_order(client,'delivered'); h,_=admin_headers(); r=client.get('/api/v1/admin/analytics/daily',params={'days':7},headers=h); assert r.status_code==200; assert len(r.json())==7

def test_funnel_counts_current_delivered_order(client):
    make_order(client,'delivered'); h,_=admin_headers(); r=client.get('/api/v1/admin/analytics/funnel',params={'days':7},headers=h); assert r.status_code==200; assert r.json()['reached_delivered']>=1; assert r.json()['reached_confirmed']>=1

def test_retention_analytics_detects_repeat_customer(client):
    c=login_phone(client,'01044556677')
    with SessionLocal() as db:
        for i in range(2):
            cart=CartEntity(customer_id=c['id'],chef_id=CHEF_ID,service_date=date.today(),status='converted'); db.add(cart); db.flush(); db.add(OrderEntity(customer_id=c['id'],chef_id=CHEF_ID,source_cart_id=cart.id,service_date=date.today(),status='delivered',subtotal_minor=10000,total_minor=10000,currency='EGP'))
        db.commit()
    h,_=admin_headers(); r=client.get('/api/v1/admin/analytics/retention',params={'days':7},headers=h); assert r.status_code==200; assert r.json()['repeat_customers']>=1; assert r.json()['repeat_customer_rate_pct']>0

def test_operations_report_combines_sections(client):
    make_order(client,'delivered'); h,_=admin_headers(); r=client.get('/api/v1/admin/reports/operations',headers=h); assert r.status_code==200
    b=r.json(); assert 'overview' in b and 'finance' in b and 'support' in b and 'top_chefs' in b

def test_admin_order_not_found(client):
    h,_=admin_headers(); r=client.get('/api/v1/admin/orders/ffffffff-ffff-ffff-ffff-ffffffffffff',headers=h); assert r.status_code==404
