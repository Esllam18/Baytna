from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=json.loads((ROOT/"contracts/openapi.json").read_text(encoding="utf-8"))
paths=spec.get("paths",{})
schemas=spec.get("components",{}).get("schemas",{})

required={
    "/health/release":{"get"},
    "/api/v1/admin/economics/imports":{"get","post"},
    "/api/v1/admin/economics/imports/{batch_id}":{"get"},
    "/api/v1/admin/economics/imports/{batch_id}/validate":{"post"},
    "/api/v1/admin/economics/imports/{batch_id}/apply":{"post"},
    "/api/v1/admin/economics/providers/twilio/sync":{"post"},
    "/api/v1/admin/economics/settlements":{"get","post"},
    "/api/v1/admin/economics/settlements/{batch_id}":{"get"},
    "/api/v1/admin/economics/settlements/{batch_id}/reconcile":{"post"},
    "/api/v1/admin/economics/zones/{zone_id}/budgets":{"get","put"},
    "/api/v1/admin/economics/budgets/{budget_id}/movement":{"post"},
    "/api/v1/admin/economics/zones/{zone_id}/rollout/history":{"get"},
    "/api/v1/admin/economics/zones/{zone_id}/rollout/start":{"post"},
    "/api/v1/admin/economics/zones/{zone_id}/rollout/advance":{"post"},
    "/api/v1/admin/economics/zones/{zone_id}/rollout/pause":{"post"},
    "/api/v1/admin/economics/zones/{zone_id}/rollout/resume":{"post"},
}

missing=[]
for path,methods in required.items():
    actual={
        m.lower() for m in paths.get(path,{})
        if m.lower() in {"get","post","put","patch","delete"}
    }
    if not methods.issubset(actual):
        missing.append(
            f"{path}: expected {sorted(methods)}, got {sorted(actual)}"
        )

required_schema_fields={
    "ProviderCostImportBatchResponse":{
        "provider","checksum_sha256","status","total_egp_minor",
        "applied_cost_entries","validation_errors_json",
    },
    "SettlementBatchResponse":{
        "provider","status","matched_lines","mismatched_lines",
        "fees_minor","net_settlement_minor","blockers_json",
    },
    "ZoneBudgetSummary":{
        "required_categories","missing_categories","allocated_minor",
        "remaining_minor","budget_ready","budgets",
    },
    "RolloutResponse":{
        "zone_status","rollout_stage","rollout_percent",
        "daily_order_cap","budget_ready","payment_reconciliation_open",
        "blocked_settlement_batches","event_id",
    },
    "ExpansionZoneResponse":{
        "rollout_stage","rollout_percent","daily_order_cap",
        "rollout_started_at","rollout_completed_at",
    },
}
for schema,fields in required_schema_fields.items():
    properties=set(schemas.get(schema,{}).get("properties",{}))
    absent=fields-properties
    if absent:
        missing.append(f"{schema}: missing {sorted(absent)}")

if missing:
    raise SystemExit(
        "Sprint 47 financial automation contract failed:\n- "
        + "\n- ".join(missing)
    )

print(f"Sprint 47 contract verified against {len(paths)} OpenAPI paths.")
