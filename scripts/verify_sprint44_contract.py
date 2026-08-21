from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = json.loads(
    (ROOT / "contracts/openapi.json").read_text(encoding="utf-8")
)
paths = spec.get("paths", {})
schemas = spec.get("components", {}).get("schemas", {})

required_paths = {
    "/health/release": {"get"},
    "/api/v1/customer/orders/{order_id}": {"get"},
    "/api/v1/customer/orders/{order_id}/delivery-tracking": {"get"},
    "/api/v1/driver/missions/{task_id}": {"get"},
    "/api/v1/driver/missions/{task_id}/deliver": {"post"},
    "/api/v1/admin/orders/{order_id}": {"get"},
    "/api/v1/admin/control-room/incidents/refresh": {"post"},
    "/api/v1/admin/control-room/kpis": {"get"},
}

missing = []
for path, methods in required_paths.items():
    actual = {
        method.lower()
        for method in paths.get(path, {})
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    }
    if not methods.issubset(actual):
        missing.append(
            f"{path}: expected {sorted(methods)}, got {sorted(actual)}"
        )

required_schema_fields = {
    "OrderResponse": {
        "promised_delivery_window_start_at",
        "promised_delivery_window_end_at",
        "promised_delivery_timezone",
        "delivery_promise_source",
    },
    "DeliveryTrackingResponse": {
        "promised_delivery_window_start_at",
        "promised_delivery_window_end_at",
        "promised_delivery_timezone",
        "delivery_timing_status",
        "late_by_minutes",
    },
    "DeliveryMissionResponse": {
        "promised_delivery_window_start_at",
        "promised_delivery_window_end_at",
        "promised_delivery_timezone",
        "delivery_timing_status",
        "late_by_minutes",
    },
    "LaunchKpis": {
        "on_time_delivery_rate_pct",
        "on_time_measurable_deliveries",
        "late_deliveries",
        "delivery_promise_coverage_pct",
        "launch_target_on_time_met",
    },
    "IncidentRefreshResponse": {
        "auto_escalated",
        "admin_notifications_planned",
    },
}

for schema_name, fields in required_schema_fields.items():
    properties = set(
        schemas.get(schema_name, {}).get("properties", {})
    )
    absent = fields - properties
    if absent:
        missing.append(
            f"{schema_name}: missing fields {sorted(absent)}"
        )

if missing:
    raise SystemExit(
        "Sprint 44 delivery timing contract failed:\n- "
        + "\n- ".join(missing)
    )

print(
    f"Sprint 44 contract verified against {len(paths)} OpenAPI paths."
)
