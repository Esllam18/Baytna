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
    "/api/v1/chef/profile":{"get"},
    "/api/v1/chef/app-dashboard":{"get"},
    "/api/v1/chef/dashboard":{"get"},
    "/api/v1/chef/signature-menu":{"get","post"},
    "/api/v1/chef/signature-menu/{dish_id}":{"patch"},
    "/api/v1/chef/workdays/open":{"post"},
    "/api/v1/chef/workdays/{service_date}/close":{"post"},
    "/api/v1/chef/today-menu":{"get","put"},
    "/api/v1/chef/today-menu/{item_id}/quantity":{"patch"},
    "/api/v1/chef/orders":{"get"},
    "/api/v1/chef/orders/{order_id}":{"get"},
    "/api/v1/chef/orders/{order_id}/accept":{"post"},
    "/api/v1/chef/orders/{order_id}/reject":{"post"},
    "/api/v1/chef/orders/{order_id}/start-preparing":{"post"},
    "/api/v1/chef/orders/{order_id}/start-packaging":{"post"},
    "/api/v1/chef/orders/{order_id}/ready-for-pickup":{"post"},
    "/api/v1/chef/special-orders":{"get"},
    "/api/v1/chef/special-orders/{special_order_id}":{"get"},
    "/api/v1/chef/special-orders/{special_order_id}/accept":{"post"},
    "/api/v1/chef/special-orders/{special_order_id}/counter-offer":{"post"},
    "/api/v1/chef/special-orders/{special_order_id}/reject":{"post"},
    "/api/v1/chef/schedule/weekly":{"get","put"},
}

missing=[]
for path,methods in required.items():
    actual={m.lower() for m in paths.get(path,{}) if m.lower() in {"get","post","put","patch","delete"}}
    if not methods.issubset(actual):
        missing.append(f"{path}: expected {sorted(methods)}, got {sorted(actual)}")
if missing:
    raise SystemExit("Sprint 38 Chef App contract failed:\n- "+"\n- ".join(missing))
print(f"Sprint 38 Chef App contract verified against {len(paths)} OpenAPI paths.")
