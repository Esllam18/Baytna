from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = json.loads((ROOT / "contracts/openapi.json").read_text(encoding="utf-8"))
paths = spec.get("paths", {})

required = {
    "/health/live": {"get"},
    "/health/ready": {"get"},
    "/health/reliability": {"get"},
    "/health/release": {"get"},
    "/api/v1/notifications/devices": {"get", "post"},
    "/api/v1/notifications/preferences": {"get", "put"},
    "/api/v1/customer/orders/{order_id}/tracking": {"get"},
    "/api/v1/chef/orders/{order_id}/ready-for-pickup": {"post"},
    "/api/v1/driver/missions/{task_id}/deliver": {"post"},
    "/api/v1/admin/orders/{order_id}": {"get"},
    "/api/v1/admin/integrations/status": {"get"},
    "/api/v1/admin/payments/reconciliation/summary": {"get"},
}

missing = []
for path, methods in required.items():
    actual = {
        m.lower()
        for m in paths.get(path, {})
        if m.lower() in {"get", "post", "put", "patch", "delete"}
    }
    if not methods.issubset(actual):
        missing.append(
            f"{path}: expected {sorted(methods)}, got {sorted(actual)}"
        )

if missing:
    raise SystemExit(
        "Sprint 42 release contract failed:\n- " + "\n- ".join(missing)
    )

print(
    f"Sprint 42 release contract verified against {len(paths)} OpenAPI paths."
)
