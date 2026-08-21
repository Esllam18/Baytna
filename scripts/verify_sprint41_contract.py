from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=json.loads((ROOT/"contracts/openapi.json").read_text(encoding="utf-8"))
paths=spec.get("paths",{})

required={
    "/api/v1/notifications/devices":{"get","post"},
    "/api/v1/notifications/devices/{device_id}":{"delete"},
    "/api/v1/notifications/preferences":{"get","put"},
    "/api/v1/media/uploads":{"post"},
    "/api/v1/media/{asset_id}/complete":{"post"},
    "/api/v1/chef/signature-menu/{dish_id}/media":{"put"},
    "/api/v1/customer/support/tickets":{"post"},
    "/api/v1/customer/support/tickets/{ticket_id}/messages":{"post"},
    "/api/v1/chef/orders":{"get"},
    "/api/v1/driver/missions/available":{"get"},
    "/api/v1/admin/orders/{order_id}":{"get"},
}

missing=[]
for path,methods in required.items():
    actual={m.lower() for m in paths.get(path,{}) if m.lower() in {"get","post","put","patch","delete"}}
    if not methods.issubset(actual):
        missing.append(f"{path}: expected {sorted(methods)}, got {sorted(actual)}")

if missing:
    raise SystemExit("Sprint 41 contract failed:\n- "+"\n- ".join(missing))

print(f"Sprint 41 cross-app contract verified against {len(paths)} OpenAPI paths.")
