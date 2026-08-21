from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt

from app.core.config import Settings
from app.core.errors import ApiError
from app.core.models import UserRole


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    # SQLite returns timezone-aware DateTime columns as naive values.
    # PostgreSQL/psycopg returns aware values. Normalize both paths.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def hash_secret(value: str, pepper: str) -> str:
    return hmac.new(
        pepper.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_secret(value: str, expected_hash: str, pepper: str) -> bool:
    candidate = hash_secret(value, pepper)
    return hmac.compare_digest(candidate, expected_hash)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def create_access_token(
    *,
    user_id: UUID,
    role: UserRole,
    settings: Settings,
) -> tuple[str, datetime]:
    now = utc_now()
    expires_at = now + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "typ": "access",
        "jti": uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_at


def decode_access_token(token: str, settings: Settings) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "typ", "exp", "iat", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ApiError(401, "auth_access_expired", "انتهت صلاحية جلسة الدخول.") from exc
    except jwt.InvalidTokenError as exc:
        raise ApiError(401, "auth_access_invalid", "رمز الدخول غير صالح.") from exc

    if payload.get("typ") != "access":
        raise ApiError(401, "auth_wrong_token_type", "نوع رمز الدخول غير صالح.")

    return payload
