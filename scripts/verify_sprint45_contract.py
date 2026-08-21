from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = json.loads((ROOT / "contracts/openapi.json").read_text(encoding="utf-8"))
paths = spec.get("paths", {})
schemas = spec.get("components", {}).get("schemas", {})

required_paths = {
    "/api/v1/admin/pilot/programs": {"get", "post"},
    "/api/v1/admin/pilot/programs/{program_id}": {"get"},
    "/api/v1/admin/pilot/programs/{program_id}/activate": {"post"},
    "/api/v1/admin/pilot/programs/{program_id}/complete": {"post"},
    "/api/v1/admin/pilot/programs/{program_id}/refresh": {"post"},
    "/api/v1/admin/pilot/programs/{program_id}/stability": {"get"},
    "/api/v1/admin/pilot/programs/{program_id}/cohorts": {"get"},
    "/api/v1/admin/pilot/programs/{program_id}/evidence": {"get"},
    "/api/v1/admin/pilot/programs/{program_id}/evidence/{evidence_type}": {"put"},
    "/api/v1/admin/pilot/programs/{program_id}/post-pilot": {"get"},
}

errors: list[str] = []
for path, expected in required_paths.items():
    actual = {
        x.lower()
        for x in paths.get(path, {})
        if x.lower() in {"get", "post", "put", "patch", "delete"}
    }
    if not expected.issubset(actual):
        errors.append(f"{path}: expected {sorted(expected)}, got {sorted(actual)}")

required_fields = {
    "PilotProgramResponse": {
        "required_stability_weeks",
        "rating_target",
        "repeat_customer_target_pct",
        "on_time_target_pct",
        "cancellation_max_pct",
        "status",
    },
    "PilotWeeklySnapshotResponse": {
        "week_index",
        "repeat_customer_rate_pct",
        "on_time_delivery_rate_pct",
        "delivery_promise_coverage_pct",
        "week_evaluable",
        "week_passed",
    },
    "PilotStabilityReport": {
        "required_weeks",
        "current_consecutive_passed_weeks",
        "max_consecutive_passed_weeks",
        "stability_gate_met",
        "weeks",
    },
    "PilotPostPilotReport": {
        "scale_ready",
        "scale_blockers",
        "operational_profit_evidence_status",
        "profitability_calculated_from_backend",
        "weighted_w1_retention_pct",
        "weighted_w4_retention_pct",
    },
}
for name, expected in required_fields.items():
    actual = set(schemas.get(name, {}).get("properties", {}))
    missing = expected - actual
    if missing:
        errors.append(f"{name}: missing {sorted(missing)}")

if errors:
    raise SystemExit("Sprint 45 contract failed:\n- " + "\n- ".join(errors))

print(f"Sprint 45 pilot stability contract verified against {len(paths)} OpenAPI paths.")
