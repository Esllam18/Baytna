from pathlib import Path
from uuid import UUID, uuid4

import pytest
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
from app.modules.notification_delivery.crypto import IntegrationSecretBox
from app.modules.notification_delivery.service import NotificationDeliveryService
from app.modules.notifications.service import NotificationService
from app.modules.reliability.jobs import BackgroundJobService


def login_phone(client, phone: str):
    sent = client.post("/api/v1/auth/send-otp", json={"phone": phone})
    assert sent.status_code == 200
    otp = sent.json()["development_otp"]
    verified = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": phone, "code": otp},
    )
    assert verified.status_code == 200
    body = verified.json()
    return {
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "body": body,
    }


def admin_headers():
    settings = get_settings()
    with SessionLocal() as db:
        user = UserEntity(
            id=uuid4(),
            phone=f"+20106{uuid4().int % 100000000:08d}",
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


def test_local_media_upload_complete_and_download(login, tmp_path):
    client = login["client"]
    settings = get_settings()
    old_root = settings.storage_local_root
    settings.storage_local_root = str(tmp_path)
    try:
        content = b"fake-jpeg-bytes-12345"
        created = client.post(
            "/api/v1/media/uploads",
            headers=login["headers"],
            json={
                "purpose": "customer_attachment",
                "visibility": "private",
                "filename": "receipt.jpg",
                "mime_type": "image/jpeg",
                "size_bytes": len(content),
            },
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["asset"]["status"] == "pending"
        assert body["asset"]["storage_provider"] == "local"

        uploaded = client.put(
            body["upload_url"],
            content=content,
            headers={"Content-Type": "image/jpeg"},
        )
        assert uploaded.status_code == 200
        assert uploaded.json()["size_bytes"] == len(content)

        completed = client.post(
            f"/api/v1/media/{body['asset']['id']}/complete",
            headers=login["headers"],
        )
        assert completed.status_code == 200
        assert completed.json()["asset"]["status"] == "ready"
        assert completed.json()["asset"]["actual_size_bytes"] == len(content)
        assert len(completed.json()["asset"]["checksum_sha256"]) == 64

        signed = client.get(
            f"/api/v1/media/{body['asset']['id']}/download-url",
            headers=login["headers"],
        )
        assert signed.status_code == 200
        downloaded = client.get(signed.json()["download_url"])
        assert downloaded.status_code == 200
        assert downloaded.content == content
    finally:
        settings.storage_local_root = old_root


def test_media_complete_rejects_size_mismatch(login, tmp_path):
    client = login["client"]
    settings = get_settings()
    old_root = settings.storage_local_root
    settings.storage_local_root = str(tmp_path)
    try:
        created = client.post(
            "/api/v1/media/uploads",
            headers=login["headers"],
            json={
                "purpose": "support_attachment",
                "mime_type": "application/pdf",
                "size_bytes": 100,
            },
        ).json()

        client.put(
            created["upload_url"],
            content=b"tiny-pdf",
            headers={"Content-Type": "application/pdf"},
        )
        completed = client.post(
            f"/api/v1/media/{created['asset']['id']}/complete",
            headers=login["headers"],
        )
        assert completed.status_code == 409
        assert completed.json()["error"]["code"] == "media_size_mismatch"
    finally:
        settings.storage_local_root = old_root


def test_private_media_is_owner_isolated(client, tmp_path):
    settings = get_settings()
    old_root = settings.storage_local_root
    settings.storage_local_root = str(tmp_path)
    try:
        a = login_phone(client, "01041000001")
        b = login_phone(client, "01041000002")
        content = b"private-file"

        created = client.post(
            "/api/v1/media/uploads",
            headers=a["headers"],
            json={
                "purpose": "support_attachment",
                "mime_type": "image/png",
                "size_bytes": len(content),
            },
        ).json()
        client.put(created["upload_url"], content=content)
        client.post(
            f"/api/v1/media/{created['asset']['id']}/complete",
            headers=a["headers"],
        )

        blocked = client.get(
            f"/api/v1/media/{created['asset']['id']}/download-url",
            headers=b["headers"],
        )
        assert blocked.status_code == 404
    finally:
        settings.storage_local_root = old_root


def test_public_media_requires_public_purpose(login):
    response = login["client"].post(
        "/api/v1/media/uploads",
        headers=login["headers"],
        json={
            "purpose": "support_attachment",
            "visibility": "public",
            "mime_type": "image/jpeg",
            "size_bytes": 10,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "media_public_purpose_not_allowed"


def test_public_dish_image_can_be_downloaded_without_auth(login, tmp_path):
    client = login["client"]
    settings = get_settings()
    old_root = settings.storage_local_root
    settings.storage_local_root = str(tmp_path)
    try:
        content = b"public-image"
        created = client.post(
            "/api/v1/media/uploads",
            headers=login["headers"],
            json={
                "purpose": "dish_image",
                "visibility": "public",
                "mime_type": "image/webp",
                "size_bytes": len(content),
            },
        ).json()
        client.put(created["upload_url"], content=content)
        client.post(
            f"/api/v1/media/{created['asset']['id']}/complete",
            headers=login["headers"],
        )

        public = client.get(
            f"/api/v1/media/public/{created['asset']['id']}"
        )
        assert public.status_code == 200
        downloaded = client.get(public.json()["download_url"])
        assert downloaded.content == content
    finally:
        settings.storage_local_root = old_root


def test_media_delete_is_idempotent(login, tmp_path):
    client = login["client"]
    settings = get_settings()
    old_root = settings.storage_local_root
    settings.storage_local_root = str(tmp_path)
    try:
        content = b"delete-me"
        created = client.post(
            "/api/v1/media/uploads",
            headers=login["headers"],
            json={
                "purpose": "other",
                "mime_type": "image/png",
                "size_bytes": len(content),
            },
        ).json()
        client.put(created["upload_url"], content=content)
        client.post(
            f"/api/v1/media/{created['asset']['id']}/complete",
            headers=login["headers"],
        )

        first = client.delete(
            f"/api/v1/media/{created['asset']['id']}",
            headers=login["headers"],
        )
        second = client.delete(
            f"/api/v1/media/{created['asset']['id']}",
            headers=login["headers"],
        )
        assert first.status_code == 204
        assert second.status_code == 204
    finally:
        settings.storage_local_root = old_root


def test_push_device_token_is_encrypted_at_rest(login):
    client = login["client"]
    token = "device-token-super-secret-123456789"
    response = client.post(
        "/api/v1/customer/notifications/devices",
        headers=login["headers"],
        json={
            "platform": "ios",
            "token": token,
            "device_name": "iPhone",
            "app_version": "1.0.0",
        },
    )
    assert response.status_code == 201

    with SessionLocal() as db:
        row = db.get(PushDeviceEntity, UUID(response.json()["id"]))
        assert row.token_ciphertext != token
        assert token not in row.token_ciphertext
        assert len(row.token_hash) == 64
        assert IntegrationSecretBox(get_settings()).decrypt(row.token_ciphertext) == token


def test_register_same_device_is_idempotent_and_moves_to_current_user(client):
    a = login_phone(client, "01042000001")
    b = login_phone(client, "01042000002")
    token = "shared-device-token-1234567890"

    first = client.post(
        "/api/v1/customer/notifications/devices",
        headers=a["headers"],
        json={"platform": "android", "token": token},
    )
    second = client.post(
        "/api/v1/customer/notifications/devices",
        headers=b["headers"],
        json={"platform": "android", "token": token},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    a_devices = client.get(
        "/api/v1/customer/notifications/devices",
        headers=a["headers"],
    )
    b_devices = client.get(
        "/api/v1/customer/notifications/devices",
        headers=b["headers"],
    )
    assert a_devices.json() == []
    assert len(b_devices.json()) == 1


def test_notification_preferences_default_push_on_sms_off(login):
    response = login["client"].get(
        "/api/v1/customer/notifications/preferences",
        headers=login["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["push_enabled"] is True
    assert body["sms_enabled"] is False
    assert body["marketing_enabled"] is False


def test_notification_with_registered_device_plans_push_delivery(login):
    client = login["client"]
    client.post(
        "/api/v1/customer/notifications/devices",
        headers=login["headers"],
        json={
            "platform": "ios",
            "token": "push-token-plan-1234567890",
        },
    )

    with SessionLocal() as db:
        user_id = UUID(login["body"]["user"]["id"])
        notification = NotificationService(db, get_settings()).emit(
            user_id=user_id,
            kind="order_ready",
            title="جاهز",
            body="طلبك جاهز",
            dedupe_key=f"test-plan-{uuid4()}",
            commit=True,
        )
        deliveries = list(
            db.scalars(
                select(NotificationDeliveryEntity).where(
                    NotificationDeliveryEntity.notification_id == notification.id
                )
            ).all()
        )
        assert len(deliveries) == 1
        assert deliveries[0].channel == "push"
        assert deliveries[0].status == "pending"


def test_notification_dispatch_logging_provider_succeeds(login):
    client = login["client"]
    client.post(
        "/api/v1/customer/notifications/devices",
        headers=login["headers"],
        json={
            "platform": "android",
            "token": "push-token-dispatch-1234567890",
        },
    )

    with SessionLocal() as db:
        user_id = UUID(login["body"]["user"]["id"])
        notification = NotificationService(db, get_settings()).emit(
            user_id=user_id,
            kind="order_delivered",
            title="وصل",
            body="تم توصيل طلبك",
            dedupe_key=f"test-dispatch-{uuid4()}",
            commit=True,
        )
        result = NotificationDeliveryService(
            db,
            get_settings(),
        ).dispatch_due(
            worker_id="test-worker",
            limit=10,
        )
        assert result["succeeded"] == 1

        delivery = db.scalar(
            select(NotificationDeliveryEntity).where(
                NotificationDeliveryEntity.notification_id == notification.id
            )
        )
        assert delivery.status == "succeeded"
        assert delivery.provider_message_id.startswith("log-push-")


def test_sms_delivery_only_when_enabled_and_kind_is_eligible(login):
    client = login["client"]
    pref = client.put(
        "/api/v1/customer/notifications/preferences",
        headers=login["headers"],
        json={
            "push_enabled": False,
            "sms_enabled": True,
            "order_updates": True,
            "support_updates": True,
            "marketing_enabled": False,
        },
    )
    assert pref.status_code == 200

    with SessionLocal() as db:
        user_id = UUID(login["body"]["user"]["id"])
        eligible = NotificationService(db, get_settings()).emit(
            user_id=user_id,
            kind="order_delivered",
            title="وصل",
            body="وصل طلبك",
            dedupe_key=f"sms-eligible-{uuid4()}",
            commit=True,
        )
        ineligible = NotificationService(db, get_settings()).emit(
            user_id=user_id,
            kind="chef_accepted",
            title="الشيف وافقت",
            body="بدأ التجهيز",
            dedupe_key=f"sms-ineligible-{uuid4()}",
            commit=True,
        )

        eligible_rows = list(
            db.scalars(
                select(NotificationDeliveryEntity).where(
                    NotificationDeliveryEntity.notification_id == eligible.id
                )
            ).all()
        )
        ineligible_rows = list(
            db.scalars(
                select(NotificationDeliveryEntity).where(
                    NotificationDeliveryEntity.notification_id == ineligible.id
                )
            ).all()
        )
        assert len(eligible_rows) == 1
        assert eligible_rows[0].channel == "sms"
        assert ineligible_rows == []


def test_disabled_order_updates_prevents_external_delivery(login):
    client = login["client"]
    client.post(
        "/api/v1/customer/notifications/devices",
        headers=login["headers"],
        json={
            "platform": "ios",
            "token": "push-token-pref-1234567890",
        },
    )
    client.put(
        "/api/v1/customer/notifications/preferences",
        headers=login["headers"],
        json={
            "push_enabled": True,
            "sms_enabled": True,
            "order_updates": False,
            "support_updates": True,
            "marketing_enabled": False,
        },
    )

    with SessionLocal() as db:
        user_id = UUID(login["body"]["user"]["id"])
        notification = NotificationService(db, get_settings()).emit(
            user_id=user_id,
            kind="order_ready",
            title="جاهز",
            body="جاهز",
            dedupe_key=f"disabled-order-{uuid4()}",
            commit=True,
        )
        rows = list(
            db.scalars(
                select(NotificationDeliveryEntity).where(
                    NotificationDeliveryEntity.notification_id == notification.id
                )
            ).all()
        )
        assert rows == []


def test_deactivated_device_is_not_planned(login):
    client = login["client"]
    registered = client.post(
        "/api/v1/customer/notifications/devices",
        headers=login["headers"],
        json={
            "platform": "web",
            "token": "push-token-deactivate-1234567890",
        },
    ).json()
    response = client.delete(
        f"/api/v1/customer/notifications/devices/{registered['id']}",
        headers=login["headers"],
    )
    assert response.status_code == 204

    with SessionLocal() as db:
        user_id = UUID(login["body"]["user"]["id"])
        notification = NotificationService(db, get_settings()).emit(
            user_id=user_id,
            kind="order_ready",
            title="جاهز",
            body="جاهز",
            dedupe_key=f"inactive-device-{uuid4()}",
            commit=True,
        )
        rows = list(
            db.scalars(
                select(NotificationDeliveryEntity).where(
                    NotificationDeliveryEntity.notification_id == notification.id
                )
            ).all()
        )
        assert rows == []


def test_admin_notification_delivery_api_requires_admin(login):
    response = login["client"].get(
        "/api/v1/admin/notification-deliveries",
        headers=login["headers"],
    )
    assert response.status_code == 403


def test_admin_can_list_notification_deliveries(login):
    client = login["client"]
    client.post(
        "/api/v1/customer/notifications/devices",
        headers=login["headers"],
        json={
            "platform": "ios",
            "token": "push-token-admin-list-1234567890",
        },
    )
    with SessionLocal() as db:
        user_id = UUID(login["body"]["user"]["id"])
        NotificationService(db, get_settings()).emit(
            user_id=user_id,
            kind="order_ready",
            title="جاهز",
            body="جاهز",
            dedupe_key=f"admin-list-{uuid4()}",
            commit=True,
        )

    response = client.get(
        "/api/v1/admin/notification-deliveries",
        headers=admin_headers(),
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_worker_schedules_notification_dispatch(login):
    with SessionLocal() as db:
        jobs = BackgroundJobService(db, get_settings()).schedule_maintenance()
        assert any(x.job_type == "notifications.dispatch" for x in jobs)


def test_production_rejects_local_storage_and_logging_integrations():
    with pytest.raises(ValueError) as exc:
        Settings(
            env="production",
            database_url="postgresql+psycopg://baytna:strong@db:5432/baytna",
            cors_origins="https://app.baytna.example",
            allowed_hosts="api.baytna.example",
            security_hsts_enabled=True,
            dev_return_otp=False,
            seed_demo_data=False,
            payment_provider="real_provider",
            jwt_secret="J" * 48,
            otp_pepper="O" * 48,
            refresh_token_pepper="R" * 48,
            payment_webhook_secret="P" * 48,
            media_signing_secret="M" * 48,
            integration_encryption_secret="I" * 48,
        )
    text = str(exc.value)
    assert "BAYTNA_STORAGE_PROVIDER must be s3" in text
    assert "BAYTNA_NOTIFICATION_PUSH_PROVIDER cannot be logging" in text


def test_production_accepts_s3_http_provider_configuration():
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
        notification_push_provider="http",
        notification_push_endpoint="https://push.example.com/send",
        notification_sms_provider="http",
        notification_sms_endpoint="https://sms.example.com/send",
        notification_provider_webhook_secret="W" * 48,
    )
    assert settings.storage_provider == "s3"
    assert settings.notification_push_provider == "http"
