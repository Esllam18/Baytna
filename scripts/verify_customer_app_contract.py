from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = json.loads((ROOT / "contracts/openapi.json").read_text(encoding="utf-8"))
paths = spec.get("paths", {})

required = {
    "/api/v1/auth/send-otp": {"post"},
    "/api/v1/auth/verify-otp": {"post"},
    "/api/v1/auth/refresh": {"post"},
    "/api/v1/auth/logout": {"post"},
    "/api/v1/customer/home": {"get"},
    "/api/v1/customer/profile": {"get", "patch"},
    "/api/v1/chefs": {"get"},
    "/api/v1/chefs/{chef_id}": {"get"},
    "/api/v1/chefs/{chef_id}/signature-menu": {"get"},
    "/api/v1/chefs/{chef_id}/today-menu": {"get"},
    "/api/v1/customer/cart": {"get", "delete"},
    "/api/v1/customer/cart/items": {"post"},
    "/api/v1/customer/cart/items/{cart_item_id}": {"patch", "delete"},
    "/api/v1/customer/pricing/quote": {"post"},
    "/api/v1/customer/addresses": {"get", "post"},
    "/api/v1/customer/addresses/{address_id}": {"patch", "delete"},
    "/api/v1/customer/addresses/{address_id}/default": {"post"},
    "/api/v1/customer/orders": {"get", "post"},
    "/api/v1/customer/orders/{order_id}": {"get"},
    "/api/v1/customer/orders/{order_id}/payment-intent": {"post"},
    "/api/v1/customer/orders/{order_id}/payment": {"get"},
    "/api/v1/customer/orders/{order_id}/tracking": {"get"},
    "/api/v1/customer/favorites/summary": {"get"},
    "/api/v1/customer/favorites/chefs": {"get"},
    "/api/v1/customer/favorites/chefs/{chef_id}": {"put", "delete"},
    "/api/v1/customer/favorites/dishes": {"get"},
    "/api/v1/customer/favorites/dishes/{dish_id}": {"put", "delete"},
    "/api/v1/customer/notifications": {"get"},
    "/api/v1/customer/notifications/summary": {"get"},
    "/api/v1/customer/notifications/{notification_id}/read": {"post"},
    "/api/v1/customer/notifications/read-all": {"post"},
    "/api/v1/customer/notifications/preferences": {"get", "put"},
    "/api/v1/customer/loyalty": {"get"},
    "/api/v1/customer/support/tickets": {"get", "post"},
    "/api/v1/customer/support/tickets/{ticket_id}": {"get"},
    "/api/v1/customer/support/tickets/{ticket_id}/messages": {"post"},
    "/api/v1/customer/subscriptions/plans": {"get"},
    "/api/v1/customer/subscriptions/current": {"get"},
    "/api/v1/customer/subscriptions/current/cancel": {"post"},
    "/api/v1/customer/orders/{order_id}/review-eligibility": {"get"},
    "/api/v1/customer/orders/{order_id}/review": {"get", "post"},
    "/api/v1/customer/reviews/{review_id}": {"patch"},
    "/api/v1/customer/reviews": {"get"},
    "/api/v1/chefs/{chef_id}/reviews": {"get"},
    "/api/v1/chefs/{chef_id}/rating-summary": {"get"},
    "/api/v1/chefs/{chef_id}/availability": {"get"},
    "/api/v1/customer/special-orders": {"get", "post"},
    "/api/v1/customer/special-orders/{special_order_id}": {"get"},
    "/api/v1/customer/special-orders/{special_order_id}/accept-counter-offer": {"post"},
    "/api/v1/customer/special-orders/{special_order_id}/cancel": {"post"},
    "/api/v1/customer/special-orders/{special_order_id}/checkout": {"post"},
}

missing = []
for path, methods in required.items():
    actual = {
        method.lower()
        for method in paths.get(path, {})
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    }
    if not methods.issubset(actual):
        missing.append(
            f"{path}: expected {sorted(methods)}, got {sorted(actual)}"
        )

if missing:
    raise SystemExit(
        "Sprint 37 customer post-order contract failed:\n- "
        + "\n- ".join(missing)
    )

print(
    f"Sprint 37 customer post-order contract verified against {len(paths)} OpenAPI paths."
)
