from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any


# Paymob transaction callback HMAC field order.
TRANSACTION_HMAC_FIELDS = (
    "amount_cents",
    "created_at",
    "currency",
    "error_occured",
    "has_parent_transaction",
    "id",
    "integration_id",
    "is_3d_secure",
    "is_auth",
    "is_capture",
    "is_refunded",
    "is_standalone_payment",
    "is_voided",
    "order.id",
    "owner",
    "pending",
    "source_data.pan",
    "source_data.sub_type",
    "source_data.type",
    "success",
)


def _nested_get(payload: dict, dotted_key: str) -> Any:
    value: Any = payload
    for part in dotted_key.split("."):
        if not isinstance(value, dict):
            return ""
        value = value.get(part, "")
    return value


def _hmac_string_value(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return ""
    return str(value)


def paymob_transaction_hmac_material(transaction: dict) -> str:
    return "".join(
        _hmac_string_value(_nested_get(transaction, field))
        for field in TRANSACTION_HMAC_FIELDS
    )


def calculate_paymob_transaction_hmac(
    transaction: dict,
    secret: str,
) -> str:
    material = paymob_transaction_hmac_material(transaction)
    return hmac.new(
        secret.encode("utf-8"),
        material.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()


def verify_paymob_transaction_hmac(
    transaction: dict,
    *,
    provided_hmac: str | None,
    secret: str,
) -> bool:
    if not provided_hmac or not secret:
        return False
    expected = calculate_paymob_transaction_hmac(transaction, secret)
    return hmac.compare_digest(expected, provided_hmac.strip().lower())


def payload_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@dataclass(slots=True)
class PaymobTransaction:
    transaction_id: str
    provider_order_reference: str | None
    special_reference: str | None
    parent_transaction_id: str | None
    transaction_type: str
    amount_minor: int
    currency: str
    success: bool
    pending: bool
    is_refunded: bool
    refunded_minor: int
    provider_status: str
    raw_obj: dict


def parse_paymob_transaction(payload: dict) -> PaymobTransaction:
    obj = payload.get("obj") if isinstance(payload.get("obj"), dict) else payload
    if not isinstance(obj, dict):
        raise ValueError("Paymob callback obj must be an object")

    transaction_id = obj.get("id")
    if transaction_id is None:
        raise ValueError("Paymob transaction id is missing")

    order = obj.get("order")
    provider_order_reference = None
    special_reference = None
    if isinstance(order, dict):
        if order.get("id") is not None:
            provider_order_reference = str(order["id"])
        special_reference = (
            order.get("merchant_order_id")
            or order.get("special_reference")
        )
    elif order is not None:
        provider_order_reference = str(order)

    # Modern intention callbacks can expose the special reference in multiple
    # locations depending on integration/checkout path.
    special_reference = (
        special_reference
        or obj.get("special_reference")
        or (obj.get("data") or {}).get("special_reference")
        or (
            (obj.get("payment_key_claims") or {}).get("extra") or {}
        ).get("special_reference")
    )

    is_refund = bool(obj.get("is_refund"))
    is_void = bool(obj.get("is_void"))
    transaction_type = "refund" if is_refund else ("void" if is_void else "payment")

    success = bool(obj.get("success"))
    pending = bool(obj.get("pending"))
    amount = int(obj.get("amount_cents") or 0)
    refunded = int(obj.get("refunded_amount_cents") or 0)
    currency = str(obj.get("currency") or "EGP").upper()

    if success:
        provider_status = "succeeded"
    elif pending:
        provider_status = "pending"
    else:
        provider_status = "failed"

    parent = obj.get("parent_transaction")
    if isinstance(parent, dict):
        parent = parent.get("id")

    return PaymobTransaction(
        transaction_id=str(transaction_id),
        provider_order_reference=provider_order_reference,
        special_reference=str(special_reference) if special_reference else None,
        parent_transaction_id=str(parent) if parent else None,
        transaction_type=transaction_type,
        amount_minor=amount,
        currency=currency,
        success=success,
        pending=pending,
        is_refunded=bool(obj.get("is_refunded")),
        refunded_minor=refunded,
        provider_status=provider_status,
        raw_obj=obj,
    )
