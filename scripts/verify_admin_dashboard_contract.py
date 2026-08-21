from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=json.loads((ROOT/"contracts/openapi.json").read_text(encoding="utf-8"))
paths=spec.get("paths",{})

required={
    "/api/v1/auth/send-otp":{"post"},
    "/api/v1/auth/verify-otp":{"post"},
    "/api/v1/auth/refresh":{"post"},
    "/api/v1/auth/logout":{"post"},
    "/api/v1/admin/profile":{"get"},
    "/api/v1/admin/dashboard/overview":{"get"},
    "/api/v1/admin/orders":{"get"},
    "/api/v1/admin/orders/{order_id}":{"get"},
    "/api/v1/admin/orders/{order_id}/notes":{"get","post"},
    "/api/v1/admin/orders/{order_id}/refunds":{"get","post"},
    "/api/v1/admin/chefs":{"get"},
    "/api/v1/admin/chefs/{chef_id}":{"get"},
    "/api/v1/admin/chefs/{chef_id}/status":{"patch"},
    "/api/v1/admin/drivers":{"get"},
    "/api/v1/admin/drivers/{driver_id}":{"get"},
    "/api/v1/admin/support/workload-summary":{"get"},
    "/api/v1/admin/support/tickets":{"get"},
    "/api/v1/admin/support/tickets/{ticket_id}":{"get"},
    "/api/v1/admin/support/tickets/{ticket_id}/assign":{"post"},
    "/api/v1/admin/support/tickets/{ticket_id}/messages":{"post"},
    "/api/v1/admin/support/tickets/{ticket_id}/status":{"patch"},
    "/api/v1/admin/finance/summary":{"get"},
    "/api/v1/admin/analytics/daily":{"get"},
    "/api/v1/admin/analytics/funnel":{"get"},
    "/api/v1/admin/analytics/retention":{"get"},
    "/api/v1/admin/audit":{"get"},
}

missing=[]
for path,methods in required.items():
    actual={m.lower() for m in paths.get(path,{}) if m.lower() in {"get","post","put","patch","delete"}}
    if not methods.issubset(actual):
        missing.append(f"{path}: expected {sorted(methods)}, got {sorted(actual)}")

if missing:
    raise SystemExit("Sprint 40 Admin Dashboard contract failed:\n- "+"\n- ".join(missing))

print(f"Sprint 40 Admin Dashboard contract verified against {len(paths)} OpenAPI paths.")
