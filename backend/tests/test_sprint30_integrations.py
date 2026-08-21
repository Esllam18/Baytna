import hashlib, json
from uuid import UUID, uuid4
from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.db_models import MediaAssetEntity, NotificationDeliveryEntity, NotificationEntity, PushDeviceEntity, SupportMessageAttachmentEntity, UserEntity
from app.core.models import UserRole
from app.core.security import create_access_token
from app.modules.notification_delivery.service import NotificationDeliveryService
from app.modules.notification_delivery.webhook_security import sign_payload
from app.modules.notifications.service import NotificationService
from app.modules.reliability.jobs import BackgroundJobService

def admin_headers():
    s=get_settings()
    with SessionLocal() as db:
        u=UserEntity(id=uuid4(), phone=f"+20105{uuid4().int%100000000:08d}", role="admin", is_active=True); db.add(u); db.commit(); token,_=create_access_token(user_id=u.id, role=UserRole.ADMIN, settings=s); return {"Authorization":f"Bearer {token}"}

def login_phone(client, phone):
    x=client.post('/api/v1/auth/send-otp',json={'phone':phone}); otp=x.json()['development_otp']; y=client.post('/api/v1/auth/verify-otp',json={'phone':phone,'code':otp}).json(); return {'headers':{'Authorization':f"Bearer {y['access_token']}"},'body':y}

def make_ready_media(client, login, tmp_path, purpose, visibility='private', content=b'abc123'):
    s=get_settings(); old=s.storage_local_root; s.storage_local_root=str(tmp_path)
    created=client.post('/api/v1/media/uploads',headers=login['headers'],json={'purpose':purpose,'visibility':visibility,'mime_type':'image/jpeg','size_bytes':len(content)}).json(); client.put(created['upload_url'],content=content); done=client.post(f"/api/v1/media/{created['asset']['id']}/complete",headers=login['headers']); assert done.status_code==200; return created['asset']['id'],old

def test_chef_can_bind_ready_public_dish_media(client,tmp_path):
    chef=login_phone(client,'+201000000001'); s=get_settings(); asset,old=make_ready_media(client,chef,tmp_path,'dish_image','public')
    try:
        dish=client.get('/api/v1/chef/signature-menu',headers=chef['headers']).json()[0]
        r=client.put(f"/api/v1/chef/signature-menu/{dish['id']}/media",headers=chef['headers'],json={'media_asset_id':asset}); assert r.status_code==200; assert r.json()['media_asset_id']==asset; assert asset in r.json()['image_url']
    finally: s.storage_local_root=old

def test_chef_cannot_bind_private_or_wrong_purpose_media(client,tmp_path):
    chef=login_phone(client,'+201000000001'); s=get_settings(); asset,old=make_ready_media(client,chef,tmp_path,'support_attachment','private')
    try:
        dish=client.get('/api/v1/chef/signature-menu',headers=chef['headers']).json()[0]
        r=client.put(f"/api/v1/chef/signature-menu/{dish['id']}/media",headers=chef['headers'],json={'media_asset_id':asset}); assert r.status_code==409
    finally: s.storage_local_root=old

def test_support_ticket_accepts_owned_attachment(login,tmp_path):
    c=login['client']; s=get_settings(); asset,old=make_ready_media(c,login,tmp_path,'support_attachment')
    try:
        r=c.post('/api/v1/customer/support/tickets',headers=login['headers'],json={'category':'other','subject':'مرفق','description':'راجع المرفق','attachment_ids':[asset]}); assert r.status_code==201; msg=r.json()['messages'][0]; assert msg['attachments'][0]['media_asset_id']==asset
        with SessionLocal() as db: assert db.scalar(select(SupportMessageAttachmentEntity)) is not None
    finally: s.storage_local_root=old

def test_support_rejects_other_customer_attachment(client,tmp_path):
    a=login_phone(client,'01050100001'); b=login_phone(client,'01050100002'); s=get_settings(); asset,old=make_ready_media(client,a,tmp_path,'support_attachment')
    try:
        r=client.post('/api/v1/customer/support/tickets',headers=b['headers'],json={'category':'other','subject':'مرفق','description':'محاولة','attachment_ids':[asset]}); assert r.status_code==404
    finally: s.storage_local_root=old

def test_notification_template_overrides_runtime_copy(login):
    c=login['client']; ah=admin_headers(); u=c.put('/api/v1/admin/notification-templates/order_ready',headers=ah,json={'title_template':'طلب {order_id} جاهز','body_template':'جهزنا طلبك رقم {order_id}','is_enabled':True}); assert u.status_code==200
    user_id=UUID(login['body']['user']['id'])
    with SessionLocal() as db:
        n=NotificationService(db,get_settings()).emit(user_id=user_id,kind='order_ready',title='fallback',body='fallback',data_json={'order_id':'ABC'},dedupe_key=f'tpl-{uuid4()}',commit=True); assert n.title=='طلب ABC جاهز'; assert n.body=='جهزنا طلبك رقم ABC'

def test_disabled_template_uses_fallback(login):
    c=login['client']; ah=admin_headers(); c.put('/api/v1/admin/notification-templates/order_ready',headers=ah,json={'title_template':'custom','body_template':'custom','is_enabled':False})
    with SessionLocal() as db:
        n=NotificationService(db,get_settings()).emit(user_id=UUID(login['body']['user']['id']),kind='order_ready',title='fallback title',body='fallback body',data_json={},dedupe_key=f'tpl2-{uuid4()}',commit=True); assert n.title=='fallback title'

def test_template_preview_keeps_unknown_placeholder(login):
    c=login['client']; ah=admin_headers(); c.put('/api/v1/admin/notification-templates/support_reply',headers=ah,json={'title_template':'أهلا {name}','body_template':'تذكرة {ticket_id}','is_enabled':True}); r=c.post('/api/v1/admin/notification-templates/support_reply/preview',headers=ah,json={'data':{'name':'محمد'}}); assert r.status_code==200; assert r.json()['title']=='أهلا محمد'; assert r.json()['body']=='تذكرة {ticket_id}'

def _planned_delivery(login):
    c=login['client']; c.post('/api/v1/customer/notifications/devices',headers=login['headers'],json={'platform':'ios','token':f'token-{uuid4()}-123456789'})
    with SessionLocal() as db:
        n=NotificationService(db,get_settings()).emit(user_id=UUID(login['body']['user']['id']),kind='order_ready',title='جاهز',body='جاهز',dedupe_key=f'wh-{uuid4()}',commit=True); svc=NotificationDeliveryService(db,get_settings()); result=svc.dispatch_due(worker_id='test',limit=10); assert result['succeeded']==1; d=db.scalar(select(NotificationDeliveryEntity).where(NotificationDeliveryEntity.notification_id==n.id)); return str(d.id), d.provider_message_id

def test_provider_webhook_requires_valid_signature(login):
    _,mid=_planned_delivery(login); payload={'event_id':'evt-1','message_id':mid,'status':'delivered'}; raw=json.dumps(payload,separators=(',',':')).encode(); r=login['client'].post('/api/v1/notifications/provider-webhooks/push/logging',content=raw,headers={'Content-Type':'application/json','X-Baytna-Signature':'bad'}); assert r.status_code==401

def test_provider_webhook_matches_delivery_idempotently(login):
    did,mid=_planned_delivery(login); payload={'event_id':'evt-2','message_id':mid,'status':'delivered'}; raw=json.dumps(payload,separators=(',',':')).encode(); sig=sign_payload(raw,get_settings().notification_provider_webhook_secret); c=login['client']; a=c.post('/api/v1/notifications/provider-webhooks/push/logging',content=raw,headers={'Content-Type':'application/json','X-Baytna-Signature':sig}); b=c.post('/api/v1/notifications/provider-webhooks/push/logging',content=raw,headers={'Content-Type':'application/json','X-Baytna-Signature':sig}); assert a.json()=={'duplicate':False,'matched':True}; assert b.json()=={'duplicate':True,'matched':True}

def test_failed_provider_receipt_moves_delivery_to_retry(login):
    did,mid=_planned_delivery(login)
    with SessionLocal() as db: d=db.get(NotificationDeliveryEntity,UUID(did)); d.attempts=1; db.commit()
    payload={'event_id':'evt-fail','message_id':mid,'status':'failed'}; raw=json.dumps(payload,separators=(',',':')).encode(); sig=sign_payload(raw,get_settings().notification_provider_webhook_secret); r=login['client'].post('/api/v1/notifications/provider-webhooks/push/logging',content=raw,headers={'Content-Type':'application/json','X-Baytna-Signature':sig}); assert r.status_code==200
    with SessionLocal() as db: assert db.get(NotificationDeliveryEntity,UUID(did)).status=='retry'

def test_reconciliation_matches_previously_unmatched_event(login):
    c=login['client']; payload={'event_id':'evt-late','message_id':'late-message-1','status':'delivered'}; raw=json.dumps(payload,separators=(',',':')).encode(); sig=sign_payload(raw,get_settings().notification_provider_webhook_secret); r=c.post('/api/v1/notifications/provider-webhooks/push/logging',content=raw,headers={'Content-Type':'application/json','X-Baytna-Signature':sig}); assert r.json()['matched'] is False
    c.post('/api/v1/customer/notifications/devices',headers=login['headers'],json={'platform':'ios','token':f'token-late-{uuid4()}-123456'})
    with SessionLocal() as db:
        n=NotificationService(db,get_settings()).emit(user_id=UUID(login['body']['user']['id']),kind='order_ready',title='x',body='x',dedupe_key=f'late-{uuid4()}',commit=True); d=db.scalar(select(NotificationDeliveryEntity).where(NotificationDeliveryEntity.notification_id==n.id)); d.status='succeeded'; d.provider_message_id='late-message-1'; db.commit()
    rr=c.post('/api/v1/admin/notification-deliveries/reconcile',headers=admin_headers()); assert rr.status_code==200; assert rr.json()['matched_events']>=1

def test_worker_schedules_reconciliation(login):
    with SessionLocal() as db: jobs=BackgroundJobService(db,get_settings()).schedule_maintenance(); assert any(j.job_type=='notifications.reconcile' for j in jobs)
