from __future__ import annotations

import base64
import hashlib
import hmac
from urllib.parse import parse_qs


def compute_twilio_signature(
    *,
    url: str,
    params: dict[str, list[str] | str],
    auth_token: str,
) -> str:
    pieces = [url]
    for key in sorted(params):
        value = params[key]
        values = value if isinstance(value, list) else [value]
        for item in sorted(str(x) for x in values):
            pieces.append(key)
            pieces.append(item)
    digest = hmac.new(
        auth_token.encode("utf-8"),
        "".join(pieces).encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def verify_twilio_signature(
    *,
    url: str,
    params: dict[str, list[str] | str],
    provided_signature: str | None,
    auth_token: str,
) -> bool:
    if not provided_signature or not auth_token:
        return False
    expected = compute_twilio_signature(
        url=url,
        params=params,
        auth_token=auth_token,
    )
    return hmac.compare_digest(expected, provided_signature.strip())


def parse_twilio_form(raw: bytes) -> dict[str, list[str]]:
    return parse_qs(
        raw.decode("utf-8"),
        keep_blank_values=True,
        strict_parsing=False,
    )


def first(params: dict[str, list[str]], key: str) -> str:
    values = params.get(key) or []
    return str(values[0]) if values else ""


def normalize_twilio_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized in {
        "accepted",
        "scheduled",
        "queued",
        "sending",
        "sent",
    }:
        return "accepted"
    if normalized in {"delivered", "read"}:
        return "delivered"
    if normalized in {"failed", "canceled"}:
        return "failed"
    if normalized == "undelivered":
        return "bounced"
    return "accepted"


def deterministic_twilio_event_id(
    params: dict[str, list[str]],
) -> str:
    fields = [
        first(params, "MessageSid"),
        first(params, "MessageStatus"),
        first(params, "ErrorCode"),
        first(params, "RawDlrDoneDate"),
    ]
    material = "|".join(fields)
    return "twilio_" + hashlib.sha256(material.encode("utf-8")).hexdigest()
