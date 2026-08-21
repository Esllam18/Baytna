from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = json.loads((ROOT / "contracts/openapi.json").read_text(encoding="utf-8"))
paths = spec.get("paths", {})
schemas = spec.get("components", {}).get("schemas", {})

required_paths = {
    "/api/v1/admin/traffic/zones/{zone_id}/capacity-forecasts": {"get"},
    "/api/v1/admin/post-launch/reviews": {"get"},
    "/api/v1/admin/post-launch/zones/{zone_id}/review": {"post"},
    "/api/v1/admin/post-launch/summary": {"get"},
}

missing: list[str] = []
for path, methods in required_paths.items():
    actual = {
        method.lower()
        for method in paths.get(path, {})
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    }
    if not methods.issubset(actual):
        missing.append(f"{path}: expected {sorted(methods)}, got {sorted(actual)}")

required_schema_fields = {
    "TrafficPolicyResponse": {
        "slo_auto_pause_enabled",
        "slo_consecutive_red_snapshots",
    },
    "CapacityForecastResponse": {
        "monitoring_snapshot_id",
        "horizon_minutes",
        "sample_count",
        "projected_orders_next_hour",
        "projected_hourly_utilization_pct",
        "daily_headroom_orders",
        "projected_minutes_to_daily_cap",
        "risk",
        "reasons_json",
    },
    "DailyFinancialCloseResponse": {
        "prepared_by_system",
        "cadence_due_at",
        "overdue_notified_at",
    },
    "EvidencePackResponse": {
        "retention_class",
        "retain_until",
    },
    "ExpansionReviewResponse": {
        "zone_id",
        "review_date",
        "window_start",
        "window_end",
        "status",
        "recommendation",
        "monitoring_snapshots",
        "red_snapshots",
        "amber_snapshots",
        "auto_pause_events",
        "required_closes",
        "closed_closes",
        "overdue_closes",
        "blocked_closes",
        "latest_forecast_risk",
        "blockers_json",
        "evidence_json",
    },
    "PostLaunchSummary": {
        "zones_reviewed",
        "healthy",
        "watch",
        "blocked",
        "continue_count",
        "hold_count",
        "pause_count",
        "reviews",
    },
}

for schema, fields in required_schema_fields.items():
    props = set(schemas.get(schema, {}).get("properties", {}))
    absent = fields - props
    if absent:
        missing.append(f"{schema}: missing {sorted(absent)}")

if missing:
    raise SystemExit("Sprint 50 contract failed:\n- " + "\n- ".join(missing))

print(f"Sprint 50 contract verified against {len(paths)} OpenAPI paths.")
