from __future__ import annotations
import hashlib
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.notification_delivery.service import NotificationDeliveryService
from app.modules.notification_delivery.webhook_security import verify_payload
router=APIRouter(prefix="/notifications/provider-webhooks", tags=["notification-provider-webhooks"])
@router.post("/{channel}/{provider}")
async def provider_webhook(channel:str, provider:str, request:Request, db:Session=Depends(get_db), settings:Settings=Depends(get_settings)):
    if channel not in {"push","sms"}: raise ApiError(404,"notification_channel_not_found","القناة غير مدعومة.")
    raw=await request.body(); sig=request.headers.get("X-Baytna-Signature")
    if not verify_payload(raw,sig,settings.notification_provider_webhook_secret): raise ApiError(401,"notification_webhook_signature_invalid","توقيع webhook غير صالح.")
    try: payload=__import__('json').loads(raw.decode('utf-8'))
    except Exception: raise ApiError(400,"notification_webhook_invalid_json","Webhook غير صالح.")
    for field in ("event_id","message_id","status"):
        if not payload.get(field): raise ApiError(422,"notification_webhook_field_missing",f"الحقل {field} مطلوب.")
    if payload["status"] not in {"accepted","delivered","failed","bounced"}: raise ApiError(422,"notification_webhook_status_invalid","حالة webhook غير مدعومة.")
    return NotificationDeliveryService(db,settings).ingest_provider_event(channel=channel,provider=provider,event_id=str(payload['event_id']),provider_message_id=str(payload['message_id']),event_status=str(payload['status']),payload=payload,payload_hash=hashlib.sha256(raw).hexdigest())
