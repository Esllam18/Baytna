from __future__ import annotations

import hashlib
import hmac


def payload_hash(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


def sign_webhook(raw_body: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()


def verify_webhook_signature(
    *,
    raw_body: bytes,
    provided_signature: str | None,
    secret: str,
) -> bool:
    if not provided_signature:
        return False
    expected = sign_webhook(raw_body, secret)
    return hmac.compare_digest(expected, provided_signature.strip())
