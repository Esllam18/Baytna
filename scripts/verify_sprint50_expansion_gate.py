from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
gate = ROOT / "scripts" / "expansion_review_gate.py"

base = {
    "release": {"version": "0.50.0", "migration_head": "0025_sprint50", "commit": "abc123"},
    "zone_id": "00000000-0000-0000-0000-000000000050",
    "slo_auto_pause_policy_verified": True,
    "capacity_forecast_verified": True,
    "daily_close_cadence_verified": True,
    "evidence_retention_verified": True,
    "expansion_review_verified": True,
    "latest_review": {"status": "healthy", "recommendation": "continue", "blockers_json": []},
    "cadence": {"closed_system_rows": 1, "overdue_open_rows": 0},
}

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "evidence.json"
    path.write_text(json.dumps(base), encoding="utf-8")
    passed = subprocess.run([sys.executable, str(gate), str(path)], capture_output=True, text=True)
    if passed.returncode != 0 or "STABILIZATION DECISION: PASS" not in passed.stdout:
        raise SystemExit("Sprint 50 positive stabilization gate failed")

    blocked_payload = dict(base)
    blocked_payload["capacity_forecast_verified"] = False
    blocked_payload["latest_review"] = {"status": "blocked", "recommendation": "pause", "blockers_json": ["latest_monitoring_red"]}
    path.write_text(json.dumps(blocked_payload), encoding="utf-8")
    blocked = subprocess.run([sys.executable, str(gate), str(path)], capture_output=True, text=True)
    if blocked.returncode != 2 or "STABILIZATION DECISION: BLOCKED" not in blocked.stdout:
        raise SystemExit("Sprint 50 fail-closed stabilization gate failed")

print("Sprint 50 stabilization gate verified (PASS + fail-closed paths).")
