import base64
import io
import json
import urllib.error
import urllib.parse
from uuid import UUID, uuid4

import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    NotificationDeliveryEntity,
    NotificationEntity,
    PushDeviceEntity,
    UserEntity,
)
from app.core.models import UserRole
from app.core.security import create_access_token
from app.modules.notification_delivery.providers import (
    FCMPushProvider,
    ProviderError,
    TwilioSmsProvider,
)
from app.modules.notification_delivery.service import NotificationDeliveryService
from app.modules.notification_delivery.twilio_webhook import (
    compute_twilio_signature,
    normalize_twilio_status,
)
from scripts.pilot_preflight import validate_pilot


class FakeResponse:
    def __init__(self, payload: dict, status: int = 200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def admin_headers():
    settings = get_settings()
    with SessionLocal() as db:
        user = UserEntity(
            id=uuid4(),
            phone=f"+20105{uuid4().int % 100000000:08d}",
            role="admin",
            is_active=True,
        )
        db.add(user)
        db.commit()
        token, _ = create_access_token(
            user_id=user.id,
            role=UserRole.ADMIN,
            settings=settings,
        )
        return {"Authorization": f"Bearer {token}"}


def test_fcm_http_v1_payload_and_message_id(monkeypatch):
    settings = Settings(
        fcm_project_id="baytna-pilot",
        notification_push_provider="fcm",
    )
    provider = FCMPushProvider(settings)
    monkeypatch.setattr(provider, "_access_token", lambda: "oauth-token")

    seen = {}

    def fake_urlopen(request, timeout=10):
        seen["url"] = request.full_url
        seen["headers"] = dict(request.header_items())
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {
                "name": (
                    "projects/baytna-pilot/messages/"
                    "0:123456789%abcdef"
                )
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = provider.send(
        token="fcm-device-token",
        title="جاهز",
        body="طلبك جاهز",
        data={"order_id": "123", "count": 2},
    )

    assert seen["url"].endswith(
        "/v1/projects/baytna-pilot/messages:send"
    )
    assert seen["headers"]["Authorization"] == "Bearer oauth-token"
    assert seen["payload"]["message"]["token"] == "fcm-device-token"
    assert seen["payload"]["message"]["data"]["count"] == "2"
    assert result.provider_message_id.startswith("projects/baytna-pilot/messages/")
    assert result.provider_status == "accepted"


def test_fcm_unregistered_token_is_permanent(monkeypatch):
    settings = Settings(
        fcm_project_id="baytna-pilot",
        notification_push_provider="fcm",
    )
    provider = FCMPushProvider(settings)
    monkeypatch.setattr(provider, "_access_token", lambda: "oauth-token")

    body = json.dumps(
        {
            "error": {
                "status": "NOT_FOUND",
                "message": "Requested entity was not found.",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.firebase.fcm.v1.FcmError",
                        "errorCode": "UNREGISTERED",
                    }
                ],
            }
        }
    ).encode("utf-8")

    def fake_urlopen(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://fcm.googleapis.com",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=io.BytesIO(body),
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(ProviderError) as exc:
        provider.send(
            token="dead-token",
            title="x",
            body="y",
            data={},
        )
    assert exc.value.code == "FCM_UNREGISTERED"
    assert exc.value.permanent is True
    assert exc.value.deactivate_target is True


def test_twilio_send_uses_rest_message_resource(monkeypatch):
    settings = Settings(
        notification_sms_provider="twilio",
        twilio_account_sid="AC12345678901234567890123456789012",
        twilio_auth_token="super-secret-token",
        twilio_from_number="+15005550006",
        twilio_status_callback_url="https://pilot.example/api/v1/notifications/vendor-webhooks/twilio/status",
    )
    provider = TwilioSmsProvider(settings)
    seen = {}

    def fake_urlopen(request, timeout=10):
        seen["url"] = request.full_url
        seen["headers"] = dict(request.header_items())
        seen["form"] = urllib.parse.parse_qs(
            request.data.decode("utf-8")
        )
        return FakeResponse(
            {
                "sid": "SM12345678901234567890123456789012",
                "status": "queued",
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = provider.send(phone="+201001234567", body="اختبار")

    assert "/Accounts/AC12345678901234567890123456789012/Messages.json" in seen["url"]
    assert seen["form"]["To"] == ["+201001234567"]
    assert seen["form"]["From"] == ["+15005550006"]
    assert "StatusCallback" in seen["form"]
    assert seen["headers"]["Authorization"].startswith("Basic ")
    decoded = base64.b64decode(
        seen["headers"]["Authorization"].split(" ", 1)[1]
    ).decode("utf-8")
    assert decoded.startswith("AC1234567890")
    assert result.provider_status == "queued"


def test_twilio_status_normalization():
    assert normalize_twilio_status("queued") == "accepted"
    assert normalize_twilio_status("sent") == "accepted"
    assert normalize_twilio_status("delivered") == "delivered"
    assert normalize_twilio_status("undelivered") == "bounced"
    assert normalize_twilio_status("failed") == "failed"


def test_twilio_vendor_webhook_updates_delivery(client, login):
    settings = get_settings()
    old_provider = settings.notification_sms_provider
    old_sid = settings.twilio_account_sid
    old_token = settings.twilio_auth_token
    old_from = settings.twilio_from_number
    old_callback = settings.twilio_status_callback_url

    settings.notification_sms_provider = "logging"
    settings.twilio_account_sid = "AC12345678901234567890123456789012"
    settings.twilio_auth_token = "twilio-test-auth-token"
    settings.twilio_from_number = "+15005550006"
    settings.twilio_status_callback_url = (
        "https://pilot.example/api/v1/notifications/vendor-webhooks/twilio/status"
    )
    try:
        user_id = UUID(login["body"]["user"]["id"])
        with SessionLocal() as db:
            service = NotificationDeliveryService(db, settings)
            pref = service._preference_row(user_id=user_id)
            pref.sms_enabled = True
            pref.push_enabled = False
            notification = NotificationEntity(
                user_id=user_id,
                kind="order_delivered",
                title="وصل",
                body="تم توصيل الطلب",
                data_json={},
                dedupe_key=f"twilio-webhook-{uuid4()}",
            )
            db.add(notification)
            db.flush()
            delivery = service._ensure_delivery(
                notification=notification,
                channel="sms",
                target_ref="user_phone",
                provider="twilio",
            )
            delivery.status = "succeeded"
            delivery.provider_message_id = (
                "SM12345678901234567890123456789012"
            )
            delivery.provider_status = "queued"
            db.commit()
            delivery_id = delivery.id

        params = {
            "AccountSid": settings.twilio_account_sid,
            "MessageSid": "SM12345678901234567890123456789012",
            "MessageStatus": "delivered",
            "ErrorCode": "",
        }
        signature = compute_twilio_signature(
            url=settings.twilio_status_callback_url,
            params={k: [v] for k, v in params.items()},
            auth_token=settings.twilio_auth_token,
        )

        response = client.post(
            "/api/v1/notifications/vendor-webhooks/twilio/status",
            content=urllib.parse.urlencode(params),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Twilio-Signature": signature,
            },
        )
        assert response.status_code == 200
        assert response.json()["matched"] is True

        with SessionLocal() as db:
            row = db.get(NotificationDeliveryEntity, delivery_id)
            assert row.provider_status == "delivered"
            assert row.status == "succeeded"
            assert row.provider_updated_at is not None
    finally:
        settings.notification_sms_provider = old_provider
        settings.twilio_account_sid = old_sid
        settings.twilio_auth_token = old_token
        settings.twilio_from_number = old_from
        settings.twilio_status_callback_url = old_callback


def test_twilio_vendor_webhook_rejects_bad_signature(client):
    settings = get_settings()
    old_token = settings.twilio_auth_token
    old_callback = settings.twilio_status_callback_url
    settings.twilio_auth_token = "twilio-test-auth-token"
    settings.twilio_status_callback_url = (
        "https://pilot.example/api/v1/notifications/vendor-webhooks/twilio/status"
    )
    try:
        response = client.post(
            "/api/v1/notifications/vendor-webhooks/twilio/status",
            content=urllib.parse.urlencode(
                {
                    "MessageSid": "SM123",
                    "MessageStatus": "delivered",
                }
            ),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Twilio-Signature": "bad",
            },
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "twilio_signature_invalid"
    finally:
        settings.twilio_auth_token = old_token
        settings.twilio_status_callback_url = old_callback


def test_permanent_provider_error_deactivates_push_device(login, monkeypatch):
    settings = get_settings()
    user_id = UUID(login["body"]["user"]["id"])

    with SessionLocal() as db:
        service = NotificationDeliveryService(db, settings)
        device = PushDeviceEntity(
            user_id=user_id,
            platform="android",
            token_hash="a" * 64,
            token_ciphertext=service.crypto.encrypt("dead-device-token"),
            is_active=True,
        )
        db.add(device)
        notification = NotificationEntity(
            user_id=user_id,
            kind="order_ready",
            title="جاهز",
            body="جاهز",
            data_json={},
            dedupe_key=f"permanent-provider-error-{uuid4()}",
        )
        db.add(notification)
        db.flush()
        delivery = service._ensure_delivery(
            notification=notification,
            channel="push",
            target_ref=str(device.id),
            provider="fcm",
        )
        db.commit()

        class BrokenProvider:
            def send(self, **kwargs):
                raise ProviderError(
                    "unregistered",
                    code="FCM_UNREGISTERED",
                    permanent=True,
                    deactivate_target=True,
                )

        monkeypatch.setattr(
            "app.modules.notification_delivery.service.build_push_provider",
            lambda settings: BrokenProvider(),
        )
        result = service.dispatch_specific(
            delivery_ids=[delivery.id],
            worker_id="test",
        )
        assert result[0].status == "dead_letter"
        assert result[0].provider_error_code == "FCM_UNREGISTERED"

        db.refresh(device)
        assert device.is_active is False


def test_admin_integration_status_requires_admin(login):
    response = login["client"].get(
        "/api/v1/admin/integrations/status",
        headers=login["headers"],
    )
    assert response.status_code == 403


def test_admin_integration_status_is_secret_safe(client):
    response = client.get(
        "/api/v1/admin/integrations/status",
        headers=admin_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    rendered = json.dumps(body)
    assert "auth_token" not in rendered
    assert "bearer_token" not in rendered
    assert "secret" not in rendered.lower()


def test_admin_test_notification_dispatches_logging_push(client):
    customer = None
    sent = client.post("/api/v1/auth/send-otp", json={"phone": "01043111111"})
    otp = sent.json()["development_otp"]
    verified = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": "01043111111", "code": otp},
    ).json()
    customer = {
        "headers": {"Authorization": f"Bearer {verified['access_token']}"},
        "id": verified["user"]["id"],
    }

    device = client.post(
        "/api/v1/customer/notifications/devices",
        headers=customer["headers"],
        json={
            "platform": "android",
            "token": "pilot-test-token-1234567890",
        },
    )
    assert device.status_code == 201

    response = client.post(
        "/api/v1/admin/integrations/test-notification",
        headers=admin_headers(),
        json={
            "user_id": customer["id"],
            "channels": ["push"],
            "dispatch_now": True,
        },
    )
    assert response.status_code == 200
    assert len(response.json()["deliveries"]) == 1
    assert response.json()["deliveries"][0]["status"] == "succeeded"
    assert response.json()["deliveries"][0]["provider_status"] == "accepted"


def test_pilot_preflight_shape_accepts_real_notification_profile():
    settings = Settings(
        env="staging",
        database_url="postgresql+psycopg://baytna:x@db:5432/baytna",
        dev_return_otp=False,
        seed_demo_data=False,
        payment_provider="paymob",
        paymob_secret_key="paymob-secret-key-for-pilot-tests",
        paymob_public_key="paymob-public-key",
        paymob_hmac_secret="paymob-hmac-secret-for-pilot-tests",
        paymob_payment_methods="12345",
        paymob_notification_url="https://pilot.example/api/v1/payments/webhooks/paymob/transaction",
        paymob_redirection_url="https://pilot.example/payment/result",
        storage_provider="s3",
        storage_bucket="baytna-pilot",
        notification_push_provider="fcm",
        fcm_project_id="baytna-pilot",
        notification_sms_provider="twilio",
        twilio_account_sid="AC12345678901234567890123456789012",
        twilio_auth_token="twilio-auth-token",
        twilio_from_number="+15005550006",
        twilio_status_callback_url="https://pilot.example/api/v1/notifications/vendor-webhooks/twilio/status",
        pilot_public_base_url="https://pilot.example",
    )
    assert validate_pilot(settings) == []


def test_pilot_preflight_rejects_mock_notification_profile():
    settings = Settings(
        env="staging",
        database_url="sqlite+pysqlite:///:memory:",
        notification_push_provider="logging",
        notification_sms_provider="logging",
    )
    problems = validate_pilot(settings)
    assert any("PostgreSQL" in x for x in problems)
    assert any("fcm" in x for x in problems)
    assert any("twilio" in x for x in problems)


def test_production_accepts_fcm_twilio_provider_configuration():
    settings = Settings(
        env="production",
        database_url="postgresql+psycopg://baytna:strong@db:5432/baytna",
        cors_origins="https://app.baytna.example",
        allowed_hosts="api.baytna.example",
        security_hsts_enabled=True,
        expansion_rollout_required=True,
        traffic_require_delivery_address_for_checkout=True,
        vendor_accounting_require_dual_control=True,
        vendor_accounting_require_closed_settlements_for_rollout=True,
        launch_command_required=True,
        launch_command_require_dual_control=True,
        slo_auto_pause_default_enabled=True,
        launch_daily_close_cadence_enabled=True,
        dev_return_otp=False,
        seed_demo_data=False,
        payment_provider="real_provider",
        jwt_secret="J" * 48,
        otp_pepper="O" * 48,
        refresh_token_pepper="R" * 48,
        payment_webhook_secret="P" * 48,
        storage_provider="s3",
        storage_bucket="baytna-production",
        media_signing_secret="M" * 48,
        integration_encryption_secret="I" * 48,
        notification_provider_webhook_secret="W" * 48,
        notification_push_provider="fcm",
        fcm_project_id="baytna-production",
        notification_sms_provider="twilio",
        twilio_account_sid="AC12345678901234567890123456789012",
        twilio_auth_token="T" * 48,
        twilio_from_number="+15005550006",
        twilio_status_callback_url="https://api.baytna.example/api/v1/notifications/vendor-webhooks/twilio/status",
    )
    assert settings.notification_push_provider == "fcm"
    assert settings.notification_sms_provider == "twilio"
