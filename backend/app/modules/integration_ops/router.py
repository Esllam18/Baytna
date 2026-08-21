from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.db_models import UserEntity
from app.core.errors import ApiError
from app.core.models import UserRole
from app.modules.integration_ops.schemas import (
    IntegrationTestNotificationRequest,
    IntegrationTestNotificationResponse,
)
from app.modules.notification_delivery.service import NotificationDeliveryService

router = APIRouter(prefix="/admin/integrations", tags=["admin-integrations"])


def admin_user(
    user: UserEntity = Depends(require_roles(UserRole.ADMIN)),
) -> UserEntity:
    return user


@router.get("/status")
def integration_status(
    _: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return {
        "environment": settings.env,
        "storage_provider": settings.storage_provider,
        "payment_provider": settings.payment_provider,
        "payment": {
            "provider": settings.payment_provider,
            "paymob_configured": (
                settings.payment_provider.lower() == "paymob"
                and bool(settings.paymob_secret_key)
                and bool(settings.paymob_public_key)
                and bool(settings.paymob_hmac_secret)
                and bool(settings.paymob_payment_method_list)
            ),
            "paymob_payment_methods_count": (
                len(settings.paymob_payment_method_list)
                if settings.payment_provider.lower() == "paymob"
                else 0
            ),
            "paymob_notification_https": (
                settings.paymob_notification_url.startswith("https://")
                if settings.payment_provider.lower() == "paymob"
                else None
            ),
            "paymob_refund_enabled": (
                settings.paymob_refund_enabled
                if settings.payment_provider.lower() == "paymob"
                else None
            ),
        },
        "notifications": NotificationDeliveryService(
            db,
            settings,
        ).provider_configuration(),
        "pilot_public_base_url_configured": bool(
            settings.pilot_public_base_url
        ),
    }


@router.post(
    "/test-notification",
    response_model=IntegrationTestNotificationResponse,
)
def test_notification(
    payload: IntegrationTestNotificationRequest,
    _: UserEntity = Depends(admin_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IntegrationTestNotificationResponse:
    channels = {x.strip().lower() for x in payload.channels}
    if not channels or not channels.issubset({"push", "sms"}):
        raise ApiError(
            422,
            "integration_test_channels_invalid",
            "القنوات المدعومة للاختبار هي push و sms.",
        )

    service = NotificationDeliveryService(db, settings)
    result = service.enqueue_test_notification(
        user_id=payload.user_id,
        channels=channels,
        title=payload.title,
        body=payload.body,
    )
    delivery_ids = [UUID(x) for x in result["delivery_ids"]]
    deliveries = []
    if payload.dispatch_now:
        deliveries = service.dispatch_specific(
            delivery_ids=delivery_ids,
            worker_id="admin-integration-test",
        )

    return IntegrationTestNotificationResponse(
        notification_id=UUID(result["notification_id"]),
        delivery_ids=delivery_ids,
        deliveries=deliveries,
    )
