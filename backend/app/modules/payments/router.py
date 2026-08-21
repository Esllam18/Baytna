import json
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.errors import ApiError
from app.modules.payments.schemas import (
    CreatePaymentIntentRequest,
    PaymentResponse,
    PaymentWebhookRequest,
)
from app.modules.payments.security import (
    payload_hash,
    verify_webhook_signature,
)
from app.modules.payments.service import PaymentService
from app.modules.security_hardening.service import SecurityService, client_ip

customer_router = APIRouter(
    prefix="/customer/orders",
    tags=["payments"],
)

webhook_router = APIRouter(
    prefix="/payments/webhooks",
    tags=["payment-webhooks"],
)


def service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PaymentService:
    return PaymentService(db, settings)


@customer_router.post(
    "/{order_id}/payment-intent",
    response_model=PaymentResponse,
    status_code=201,
)
def create_payment_intent(
    order_id: UUID,
    payload: CreatePaymentIntentRequest,
    request: Request,
    user: UserEntity = Depends(current_user),
    svc: PaymentService = Depends(service),
) -> PaymentResponse:
    return svc.create_payment_intent(
        customer_id=user.id,
        order_id=order_id,
        payload=payload,
        request_id=request.state.request_id,
    )


@customer_router.get(
    "/{order_id}/payment",
    response_model=PaymentResponse,
)
def payment_for_order(
    order_id: UUID,
    user: UserEntity = Depends(current_user),
    svc: PaymentService = Depends(service),
) -> PaymentResponse:
    return svc.payment_for_order(
        customer_id=user.id,
        order_id=order_id,
    )


@webhook_router.post("/{provider}")
async def payment_webhook(
    provider: str,
    request: Request,
    x_baytna_signature: str | None = Header(
        default=None,
        alias="X-Baytna-Signature",
    ),
    svc: PaymentService = Depends(service),
    settings: Settings = Depends(get_settings),
) -> dict:
    SecurityService(svc.db, settings).enforce(
        request=request,
        scope=f"payments.webhook.{provider}.ip",
        raw_key=client_ip(request, settings),
        limit=settings.rate_limit_payment_webhook_ip,
    )

    raw = await request.body()

    if not verify_webhook_signature(
        raw_body=raw,
        provided_signature=x_baytna_signature,
        secret=settings.payment_webhook_secret,
    ):
        raise ApiError(
            401,
            "payment_webhook_signature_invalid",
            "توقيع إشعار الدفع غير صالح.",
        )

    try:
        payload_dict = json.loads(raw.decode("utf-8"))
        payload = PaymentWebhookRequest.model_validate(payload_dict)
    except Exception as exc:
        raise ApiError(
            400,
            "payment_webhook_payload_invalid",
            "بيانات إشعار الدفع غير صالحة.",
        ) from exc

    return svc.process_webhook(
        provider=provider,
        payload=payload,
        payload_dict=payload_dict,
        payload_hash=payload_hash(raw),
        request_id=request.state.request_id,
    )
