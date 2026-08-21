from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.modules.payment_reconciliation.service import (
    PaymentReconciliationService,
)
from app.modules.payments.paymob import (
    parse_paymob_transaction,
    payload_sha256,
    verify_paymob_transaction_hmac,
)
from app.modules.security_hardening.service import SecurityService, client_ip

router = APIRouter(
    prefix="/payments/webhooks/paymob",
    tags=["paymob-webhooks"],
)


@router.post("/transaction")
async def paymob_transaction_callback(
    request: Request,
    hmac: str | None = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    SecurityService(db, settings).enforce(
        request=request,
        scope="payments.webhook.paymob.ip",
        raw_key=client_ip(request, settings),
        limit=settings.rate_limit_payment_webhook_ip,
    )

    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8"))
        transaction = parse_paymob_transaction(payload)
    except Exception as exc:
        raise ApiError(
            400,
            "paymob_webhook_payload_invalid",
            "بيانات Paymob callback غير صالحة.",
        ) from exc

    obj = payload.get("obj") if isinstance(payload.get("obj"), dict) else payload
    if not verify_paymob_transaction_hmac(
        obj,
        provided_hmac=hmac,
        secret=settings.paymob_hmac_secret,
    ):
        raise ApiError(
            401,
            "paymob_webhook_hmac_invalid",
            "توقيع Paymob HMAC غير صالح.",
        )

    return PaymentReconciliationService(
        db,
        settings,
    ).ingest_paymob_transaction(
        transaction=transaction,
        payload_hash=payload_sha256(raw),
        request_id=request.state.request_id,
    )
