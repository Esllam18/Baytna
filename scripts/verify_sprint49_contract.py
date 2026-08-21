from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=json.loads((ROOT/"contracts/openapi.json").read_text(encoding="utf-8"))
paths=spec.get("paths",{})
schemas=spec.get("components",{}).get("schemas",{})

required={
    "/api/v1/admin/launch-command/sessions":{"get","post"},
    "/api/v1/admin/launch-command/sessions/{session_id}":{"get"},
    "/api/v1/admin/launch-command/sessions/{session_id}/start":{"post"},
    "/api/v1/admin/launch-command/sessions/{session_id}/pause":{"post"},
    "/api/v1/admin/launch-command/sessions/{session_id}/resume":{"post"},
    "/api/v1/admin/launch-command/sessions/{session_id}/abort":{"post"},
    "/api/v1/admin/launch-command/sessions/{session_id}/complete":{"post"},
    "/api/v1/admin/launch-command/sessions/{session_id}/runbook":{"get"},
    "/api/v1/admin/launch-command/sessions/{session_id}/runbook/{step_key}":{"post"},
    "/api/v1/admin/launch-command/sessions/{session_id}/events":{"get"},
    "/api/v1/admin/launch-command/sessions/{session_id}/traffic-overrides":{"get","post"},
    "/api/v1/admin/launch-command/traffic-overrides/{override_id}/revert":{"post"},
    "/api/v1/admin/launch-command/sessions/{session_id}/financial-closes/prepare":{"post"},
    "/api/v1/admin/launch-command/sessions/{session_id}/financial-closes":{"get"},
    "/api/v1/admin/launch-command/financial-closes/{close_id}/close":{"post"},
    "/api/v1/admin/launch-command/financial-closes/{close_id}/reopen":{"post"},
    "/api/v1/admin/launch-command/sessions/{session_id}/rollback-drills":{"get","post"},
    "/api/v1/admin/launch-command/rollback-drills/{drill_id}/complete":{"post"},
    "/api/v1/admin/launch-command/sessions/{session_id}/evidence-packs":{"get","post"},
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
    "LaunchSessionResponse":{
        "id","pilot_program_id","zone_id","launch_date","status",
        "incident_commander_admin_id","finance_admin_id","operations_admin_id",
    },
    "LaunchRunbookStepResponse":{
        "step_key","sequence","category","title","is_required","status","evidence_reference",
    },
    "TrafficOverrideResponse":{
        "override_type","previous_value_json","override_value_json","status","expires_at",
    },
    "DailyFinancialCloseResponse":{
        "close_date","status","net_collected_minor","verified_cost_minor",
        "operational_profit_minor","revenue_coverage_pct","cost_coverage_pct",
        "blockers_json","checksum_sha256",
    },
    "RollbackDrillResponse":{
        "mode","status","target_recovery_seconds","recovery_seconds",
        "pre_state_json","result_json","evidence_reference",
    },
    "EvidencePackResponse":{
        "status","release_version","migration_head","evidence_json",
        "blockers_json","checksum_sha256",
    },
}
for schema,required_fields in fields.items():
    props=set(schemas.get(schema,{}).get("properties",{}))
    absent=required_fields-props
    if absent:
        missing.append(f"{schema}: missing {sorted(absent)}")

if missing:
    raise SystemExit(
        "Sprint 49 contract failed:\n- "+"\n- ".join(missing)
    )
print(f"Sprint 49 contract verified against {len(paths)} OpenAPI paths.")
