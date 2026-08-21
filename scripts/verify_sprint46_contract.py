from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=json.loads((ROOT/"contracts/openapi.json").read_text(encoding="utf-8"))
paths=spec.get("paths",{})
schemas=spec.get("components",{}).get("schemas",{})

required={
    "/health/release":{"get"},
    "/api/v1/admin/economics/costs":{"get","post"},
    "/api/v1/admin/economics/costs/{cost_id}/verify":{"post"},
    "/api/v1/admin/economics/programs/{program_id}/report":{"get"},
    "/api/v1/admin/economics/zones":{"get","post"},
    "/api/v1/admin/economics/zones/{zone_id}":{"get"},
    "/api/v1/admin/economics/zones/{zone_id}/assess":{"post"},
    "/api/v1/admin/economics/zones/{zone_id}/approve":{"post"},
    "/api/v1/admin/economics/zones/{zone_id}/launch":{"post"},
    "/api/v1/admin/economics/zones/{zone_id}/pause":{"post"},
    "/api/v1/admin/pilot/programs/{program_id}/post-pilot":{"get"},
}

errors=[]
for path,methods in required.items():
    actual={m.lower() for m in paths.get(path,{}) if m.lower() in {"get","post","put","patch","delete"}}
    if not methods.issubset(actual):
        errors.append(f"{path}: expected {sorted(methods)}, got {sorted(actual)}")

schema_fields={
    "EconomicsReport":{
        "net_collected_minor","variable_cost_minor","fixed_cost_minor",
        "contribution_minor","contribution_margin_pct",
        "operational_profit_minor","operational_profit_margin_pct",
        "cost_coverage_pct","revenue_coverage_pct",
        "economics_evaluable","operational_profit_positive",
    },
    "CostEntryResponse":{
        "cost_type","cost_scope","amount_minor","is_verified",
        "pilot_program_id","order_id",
    },
    "ExpansionAssessmentResponse":{
        "decision","blockers_json","economics_evaluable",
        "stability_gate_met","post_pilot_scale_ready",
        "contribution_margin_pct","operational_profit_minor",
    },
    "PilotPostPilotReport":{
        "profitability_calculated_from_backend",
        "operational_profit_evidence_status",
        "scale_ready","scale_blockers",
    },
}
for name,fields in schema_fields.items():
    props=set(schemas.get(name,{}).get("properties",{}))
    missing=fields-props
    if missing:
        errors.append(f"{name}: missing {sorted(missing)}")

if errors:
    raise SystemExit("Sprint 46 contract failed:\n- "+"\n- ".join(errors))
print(f"Sprint 46 Operational Economics contract verified against {len(paths)} OpenAPI paths.")
