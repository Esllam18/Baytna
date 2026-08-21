from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.notification_delivery.service import NotificationDeliveryService
from app.modules.notification_delivery.twilio_webhook import (
    deterministic_twilio_event_id,
    first,
    normalize_twilio_status,
    parse_twilio_form,
    verify_twilio_signature,
)

router = APIRouter(
    prefix="/notifications/vendor-webhooks",
    tags=["notification-vendor-webhooks"],
)


@router.post("/twilio/status")
async def twilio_status_callback(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    raw = await request.body()
    params = parse_twilio_form(raw)

    callback_url = (
        settings.twilio_status_callback_url.strip()
        or str(request.url)
    )
    signature = request.headers.get("X-Twilio-Signature")

    if not verify_twilio_signature(
        url=callback_url,
        params=params,
        provided_signature=signature,
        auth_token=settings.twilio_auth_token,
    ):
        raise ApiError(
            403,
            "twilio_signature_invalid",
            "توقيع Twilio غير صالح.",
        )

    account_sid = first(params, "AccountSid")
    if (
        settings.twilio_account_sid
        and account_sid
        and account_sid != settings.twilio_account_sid
    ):
        raise ApiError(
            403,
            "twilio_account_mismatch",
            "معرّف حساب Twilio لا يطابق الإعدادات.",
        )

    message_sid = first(params, "MessageSid")
    message_status = first(params, "MessageStatus") or first(params, "SmsStatus")
    if not message_sid or not message_status:
        raise ApiError(
            422,
            "twilio_callback_invalid",
            "MessageSid و MessageStatus مطلوبان.",
        )

    normalized = normalize_twilio_status(message_status)
    payload = {
        key: values[0] if len(values) == 1 else values
        for key, values in params.items()
    }

    return NotificationDeliveryService(
        db,
        settings,
    ).ingest_provider_event(
        channel="sms",
        provider="twilio",
        event_id=deterministic_twilio_event_id(params),
        provider_message_id=message_sid,
        event_status=normalized,
        payload=payload,
        payload_hash=hashlib.sha256(raw).hexdigest(),
    )
