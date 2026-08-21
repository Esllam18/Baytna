from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.db_models import (
    AuditLogEntity,
    AuthSessionEntity,
    CustomerProfileEntity,
    OtpChallengeEntity,
    UserEntity,
)


def test_otp_is_persisted_hashed(client):
    response = client.post(
        "/api/v1/auth/send-otp",
        json={"phone": "01012345678"},
    )
    assert response.status_code == 200
    otp = response.json()["development_otp"]

    with SessionLocal() as db:
        challenge = db.scalar(select(OtpChallengeEntity))
        assert challenge is not None
        assert challenge.code_hash != otp
        assert len(challenge.code_hash) == 64


def test_verify_otp_creates_persistent_customer(client):
    sent = client.post("/api/v1/auth/send-otp", json={"phone": "01012345678"})
    otp = sent.json()["development_otp"]

    verified = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": "01012345678", "code": otp},
    )
    assert verified.status_code == 200
    body = verified.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["role"] == "customer"

    with SessionLocal() as db:
        user = db.scalar(
            select(UserEntity).where(UserEntity.phone == "+201012345678")
        )
        assert user is not None
        assert db.get(CustomerProfileEntity, user.id) is not None
        assert db.scalar(select(func.count(AuthSessionEntity.id))) == 1


def test_wrong_otp_increments_attempt(client):
    client.post("/api/v1/auth/send-otp", json={"phone": "01012345678"})
    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone": "01012345678", "code": "999999"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "otp_invalid"

    with SessionLocal() as db:
        challenge = db.scalar(select(OtpChallengeEntity))
        assert challenge.attempts == 1


def test_access_token_reads_me(login):
    response = login["client"].get(
        "/api/v1/me",
        headers=login["headers"],
    )
    assert response.status_code == 200
    assert response.json()["role"] == "customer"


def test_refresh_rotates_refresh_token(login):
    client = login["client"]

    first = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["refresh_token"] != login["refresh_token"]

    replay = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "refresh_revoked"

    second = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_body["refresh_token"]},
    )
    assert second.status_code == 200


def test_logout_revokes_refresh_token(login):
    client = login["client"]

    logout = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": login["refresh_token"]},
    )
    assert logout.status_code == 204

    refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert refresh.status_code == 401
    assert refresh.json()["error"]["code"] == "refresh_revoked"


def test_auth_writes_audit_log(login):
    with SessionLocal() as db:
        count = db.scalar(select(func.count(AuditLogEntity.id)))
        assert count >= 2
