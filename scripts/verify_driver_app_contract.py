from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=json.loads((ROOT/"contracts/openapi.json").read_text(encoding="utf-8"))
paths=spec.get("paths",{})

required={
    "/api/v1/auth/send-otp":{"post"},
    "/api/v1/auth/verify-otp":{"post"},
    "/api/v1/auth/refresh":{"post"},
    "/api/v1/auth/logout":{"post"},
    "/api/v1/driver/profile":{"get"},
    "/api/v1/driver/app-dashboard":{"get"},
    "/api/v1/driver/status":{"get"},
    "/api/v1/driver/availability":{"put"},
    "/api/v1/driver/missions/available":{"get"},
    "/api/v1/driver/missions/available/{task_id}":{"get"},
    "/api/v1/driver/missions/current":{"get"},
    "/api/v1/driver/missions/history":{"get"},
    "/api/v1/driver/missions/{task_id}":{"get"},
    "/api/v1/driver/missions/{task_id}/accept":{"post"},
    "/api/v1/driver/missions/{task_id}/arrive-pickup":{"post"},
    "/api/v1/driver/missions/{task_id}/confirm-pickup":{"post"},
    "/api/v1/driver/missions/{task_id}/start-delivery":{"post"},
    "/api/v1/driver/missions/{task_id}/deliver":{"post"},
    "/api/v1/driver/missions/{task_id}/issue":{"post"},
    "/api/v1/driver/missions/{task_id}/resume":{"post"},
    "/api/v1/media/uploads":{"post"},
    "/api/v1/media/{asset_id}/complete":{"post"},
}

missing=[]
for path,methods in required.items():
    actual={m.lower() for m in paths.get(path,{}) if m.lower() in {"get","post","put","patch","delete"}}
    if not methods.issubset(actual):
        missing.append(f"{path}: expected {sorted(methods)}, got {sorted(actual)}")

if missing:
    raise SystemExit("Sprint 39 Driver App contract failed:\n- "+"\n- ".join(missing))

print(f"Sprint 39 Driver App contract verified against {len(paths)} OpenAPI paths.")
