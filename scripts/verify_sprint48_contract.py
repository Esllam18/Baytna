from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=json.loads((ROOT/"contracts/openapi.json").read_text(encoding="utf-8"))
paths=spec.get("paths",{})
schemas=spec.get("components",{}).get("schemas",{})

required={
    "/api/v1/customer/orders":{"post"},
    "/api/v1/admin/traffic/zones":{"get"},
    "/api/v1/admin/traffic/zones/{zone_id}/policy":{"get","put"},
    "/api/v1/admin/traffic/zones/{zone_id}/caps":{"patch"},
    "/api/v1/admin/traffic/zones/{zone_id}/monitoring/refresh":{"post"},
    "/api/v1/admin/traffic/zones/{zone_id}/monitoring":{"get"},
    "/api/v1/admin/traffic/zones/{zone_id}/admissions":{"get"},
    "/api/v1/admin/vendor-accounting/summary":{"get"},
    "/api/v1/admin/vendor-accounting/import-reviews":{"get"},
    "/api/v1/admin/vendor-accounting/imports/{batch_id}/assign":{"post"},
    "/api/v1/admin/vendor-accounting/imports/{batch_id}/approve":{"post"},
    "/api/v1/admin/vendor-accounting/imports/{batch_id}/reject":{"post"},
    "/api/v1/admin/vendor-accounting/settlements":{"get"},
    "/api/v1/admin/vendor-accounting/settlements/{batch_id}/assign":{"post"},
    "/api/v1/admin/vendor-accounting/settlements/{batch_id}/close":{"post"},
    "/api/v1/admin/vendor-accounting/settlements/{batch_id}/reopen":{"post"},
}
missing=[]
for path,methods in required.items():
    actual={
        m.lower() for m in paths.get(path,{})
        if m.lower() in {"get","post","put","patch","delete"}
    }
    if not methods.issubset(actual):
        missing.append(f"{path}: expected {sorted(methods)}, got {sorted(actual)}")

fields={
    "CreateOrderRequest":{"cart_id","delivery_address_id"},
    "TrafficPolicyResponse":{
        "zone_id","is_enabled","hourly_order_cap","chef_daily_order_cap",
        "enforce_rollout_bucket","warning_utilization_pct",
        "critical_utilization_pct","rejection_spike_pct",
    },
    "MonitoringSnapshotResponse":{
        "zone_id","daily_utilization_pct","hourly_utilization_pct",
        "rejection_rate_pct","available_drivers","open_chefs",
        "health","blockers_json",
    },
    "AdmissionEventResponse":{
        "zone_id","order_id","decision","reason","rollout_bucket",
        "daily_cap","hourly_cap","chef_daily_cap",
    },
    "ImportReviewItem":{
        "review_status","risk_flags_json","created_by_admin_id",
        "reviewed_by_admin_id","reviewed_at",
    },
    "SettlementOperationsItem":{
        "status","operations_status","matched_lines","mismatched_lines",
        "closed_by_admin_id","closed_at",
    },
}
for schema,required_fields in fields.items():
    props=set(schemas.get(schema,{}).get("properties",{}))
    absent=required_fields-props
    if absent:
        missing.append(f"{schema}: missing {sorted(absent)}")

if missing:
    raise SystemExit(
        "Sprint 48 contract failed:\n- "+"\n- ".join(missing)
    )
print(f"Sprint 48 contract verified against {len(paths)} OpenAPI paths.")
