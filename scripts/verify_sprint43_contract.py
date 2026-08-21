from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=json.loads((ROOT/"contracts/openapi.json").read_text(encoding="utf-8"))
paths=spec.get("paths",{})

required={
    "/health/release":{"get"},
    "/api/v1/admin/control-room/incidents/refresh":{"post"},
    "/api/v1/admin/control-room/overview":{"get"},
    "/api/v1/admin/control-room/kpis":{"get"},
    "/api/v1/admin/control-room/daily-brief":{"get"},
    "/api/v1/admin/control-room/incidents":{"get"},
    "/api/v1/admin/control-room/incidents/{incident_id}/acknowledge":{"post"},
    "/api/v1/admin/control-room/incidents/{incident_id}/assign":{"post"},
    "/api/v1/admin/control-room/incidents/{incident_id}/escalate":{"post"},
    "/api/v1/admin/control-room/incidents/{incident_id}/resolve":{"post"},
    "/api/v1/admin/reliability/summary":{"get"},
    "/api/v1/admin/observability/summary":{"get"},
    "/api/v1/admin/finance/summary":{"get"},
    "/api/v1/admin/support/workload-summary":{"get"},
}

missing=[]
for path,methods in required.items():
    actual={m.lower() for m in paths.get(path,{}) if m.lower() in {"get","post","put","patch","delete"}}
    if not methods.issubset(actual):
        missing.append(f"{path}: expected {sorted(methods)}, got {sorted(actual)}")

if missing:
    raise SystemExit("Sprint 43 Control Room contract failed:\n- "+"\n- ".join(missing))

print(f"Sprint 43 Control Room contract verified against {len(paths)} OpenAPI paths.")
