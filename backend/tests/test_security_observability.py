from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.db_models import (
    RateLimitBucketEntity,
    SecurityEventEntity,
    UserEntity,
)
from app.core.models import UserRole
from app.core.security import create_access_token, utc_now
from app.modules.observability.metrics import metrics_registry
from app.modules.reliability.jobs import BackgroundJobService
from app.modules.security_hardening.service import SecurityService


def admin_headers():
    settings = get_settings()
    with SessionLocal() as db:
        user = UserEntity(
            id=uuid4(),
            phone=f"+20107{uuid4().int % 100000000:08d}",
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


def test_security_headers_are_present(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors" in response.headers["content-security-policy"]
    assert "camera=()" in response.headers["permissions-policy"]


def test_process_time_header_is_present(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert float(response.headers["x-process-time-ms"]) >= 0


def test_valid_request_id_is_preserved(client):
    response = client.get(
        "/health/live",
        headers={"X-Request-ID": "mobile.checkout-123"},
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "mobile.checkout-123"


def test_malformed_request_id_is_replaced(client):
    response = client.get(
        "/health/live",
        headers={"X-Request-ID": "bad request id !!!"},
    )
    assert response.status_code == 200
    generated = response.headers["x-request-id"]
    assert generated != "bad request id !!!"
    assert len(generated) == 32


def test_request_body_limit_rejects_large_payload(client):
    settings = get_settings()
    original = settings.max_request_body_bytes
    settings.max_request_body_bytes = 64
    try:
        response = client.post(
            "/api/v1/auth/send-otp",
            content=b'{"phone":"' + (b"1" * 500) + b'"}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "request_body_too_large"
    finally:
        settings.max_request_body_bytes = original


def test_send_otp_phone_rate_limit_returns_retry_headers(client):
    settings = get_settings()
    original_phone = settings.rate_limit_otp_send_phone
    original_ip = settings.rate_limit_otp_send_ip
    settings.rate_limit_otp_send_phone = 2
    settings.rate_limit_otp_send_ip = 100
    try:
        phone = "01012345678"
        assert client.post("/api/v1/auth/send-otp", json={"phone": phone}).status_code == 200
        assert client.post("/api/v1/auth/send-otp", json={"phone": phone}).status_code == 200
        blocked = client.post("/api/v1/auth/send-otp", json={"phone": phone})
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "rate_limit_exceeded"
        assert int(blocked.headers["retry-after"]) >= 1
        assert blocked.headers["x-ratelimit-limit"] == "2"
        assert blocked.headers["x-ratelimit-remaining"] == "0"
    finally:
        settings.rate_limit_otp_send_phone = original_phone
        settings.rate_limit_otp_send_ip = original_ip


def test_rate_limit_bucket_hashes_sensitive_key(client):
    settings = get_settings()
    original_phone = settings.rate_limit_otp_send_phone
    settings.rate_limit_otp_send_phone = 1
    try:
        phone = "01033334444"
        client.post("/api/v1/auth/send-otp", json={"phone": phone})
        client.post("/api/v1/auth/send-otp", json={"phone": phone})

        with SessionLocal() as db:
            rows = list(
                db.scalars(
                    select(RateLimitBucketEntity).where(
                        RateLimitBucketEntity.scope == "auth.send_otp.phone"
                    )
                ).all()
            )
            assert rows
            assert all(row.key_hash != phone for row in rows)
            assert all(len(row.key_hash) == 64 for row in rows)
    finally:
        settings.rate_limit_otp_send_phone = original_phone


def test_rate_limit_block_persists_security_event(client):
    settings = get_settings()
    original = settings.rate_limit_otp_send_phone
    settings.rate_limit_otp_send_phone = 1
    try:
        phone = "01055556666"
        client.post("/api/v1/auth/send-otp", json={"phone": phone})
        blocked = client.post("/api/v1/auth/send-otp", json={"phone": phone})
        assert blocked.status_code == 429

        with SessionLocal() as db:
            event = db.scalar(
                select(SecurityEventEntity)
                .where(SecurityEventEntity.event_type == "rate_limit.blocked")
                .order_by(SecurityEventEntity.created_at.desc())
            )
            assert event is not None
            assert event.severity == "warning"
            assert event.ip_hash is not None
            assert event.metadata_json["scope"] == "auth.send_otp.phone"
    finally:
        settings.rate_limit_otp_send_phone = original


def test_verify_otp_has_independent_rate_limit(client):
    settings = get_settings()
    original = settings.rate_limit_otp_verify_phone
    settings.rate_limit_otp_verify_phone = 2
    try:
        phone = "01077778888"
        sent = client.post("/api/v1/auth/send-otp", json={"phone": phone})
        otp = sent.json()["development_otp"]

        bad1 = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone": phone, "code": "111111"},
        )
        bad2 = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone": phone, "code": "222222"},
        )
        blocked = client.post(
            "/api/v1/auth/verify-otp",
            json={"phone": phone, "code": otp},
        )

        assert bad1.status_code == 400
        assert bad2.status_code == 400
        assert blocked.status_code == 429
    finally:
        settings.rate_limit_otp_verify_phone = original


def test_prometheus_metrics_endpoint_exposes_safe_aggregates(client):
    metrics_registry.reset_for_tests()
    client.get("/health/live")
    client.get("/health/ready")

    response = client.get("/metrics")
    assert response.status_code == 200
    text = response.text
    assert "baytna_http_requests_total" in text
    assert "baytna_http_errors_total" in text
    assert "baytna_http_request_duration_milliseconds_average" in text
    assert "phone" not in text.lower()


def test_observability_health(client):
    response = client.get("/health/observability")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "requests_total" in response.json()
    assert "average_duration_ms" in response.json()


def test_admin_observability_requires_admin(login):
    response = login["client"].get(
        "/api/v1/admin/observability/summary",
        headers=login["headers"],
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_admin_can_inspect_security_events(client):
    settings = get_settings()
    original = settings.rate_limit_otp_send_phone
    settings.rate_limit_otp_send_phone = 1
    try:
        phone = "01099990000"
        client.post("/api/v1/auth/send-otp", json={"phone": phone})
        client.post("/api/v1/auth/send-otp", json={"phone": phone})

        response = client.get(
            "/api/v1/admin/observability/security-events",
            headers=admin_headers(),
        )
        assert response.status_code == 200
        assert any(x["event_type"] == "rate_limit.blocked" for x in response.json())
    finally:
        settings.rate_limit_otp_send_phone = original


def test_admin_can_inspect_rate_limit_buckets(client):
    client.post("/api/v1/auth/send-otp", json={"phone": "01011112222"})
    response = client.get(
        "/api/v1/admin/observability/rate-limit-buckets",
        headers=admin_headers(),
    )
    assert response.status_code == 200
    assert len(response.json()) >= 2
    assert all(len(x["key_hash"]) == 64 for x in response.json())


def test_security_cleanup_job_deletes_old_rows(client):
    settings = get_settings()
    with SessionLocal() as db:
        service = SecurityService(db, settings)
        service.consume(
            scope="cleanup.test",
            raw_key="old-key",
            limit=100,
            window_seconds=1,
        )
        event = service.record_event(
            event_type="cleanup.old",
            severity="info",
            ip="127.0.0.1",
        )
        db.commit()

        bucket = db.scalar(
            select(RateLimitBucketEntity).where(
                RateLimitBucketEntity.scope == "cleanup.test"
            )
        )
        bucket.expires_at = utc_now() - timedelta(days=1)
        event.created_at = utc_now() - timedelta(
            days=settings.security_event_retention_days + 1
        )
        db.commit()

        result = SecurityService(db, settings).cleanup()
        assert result["deleted_rate_limit_buckets"] == 1
        assert result["deleted_security_events"] == 1


def test_worker_schedules_security_cleanup(client):
    settings = get_settings()
    with SessionLocal() as db:
        jobs = BackgroundJobService(db, settings).schedule_maintenance()
        assert any(x.job_type == "maintenance.cleanup_security" for x in jobs)


def test_production_settings_reject_unsafe_defaults():
    with pytest.raises(ValueError) as exc:
        Settings(env="production")
    text = str(exc.value)
    assert "Unsafe production configuration" in text


def test_production_settings_accept_strong_configuration():
    settings = Settings(
        env="production",
        database_url="postgresql+psycopg://baytna:strong@db:5432/baytna",
        cors_origins="https://app.baytna.example,https://admin.baytna.example",
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
    assert settings.env == "production"
    assert settings.allowed_host_list == ["api.baytna.example"]


def test_trusted_host_blocks_unknown_host(client):
    response = client.get(
        "/health/live",
        headers={"Host": "evil.example"},
    )
    assert response.status_code == 400
