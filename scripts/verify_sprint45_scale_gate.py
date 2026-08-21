from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "pilot_scale_gate.py"
EXAMPLE = ROOT / "deployment" / "pilot" / "scale-evidence.example.json"

blocked = subprocess.run(
    [sys.executable, str(GATE), str(EXAMPLE)],
    text=True,
    capture_output=True,
)
if blocked.returncode != 2 or "SCALE DECISION: BLOCKED" not in blocked.stdout:
    raise SystemExit("Scale gate did not fail closed for incomplete evidence.")

passing = {
    "release": {
        "version": "0.50.0",
        "migration_head": "0025_sprint50",
        "commit": "abcdef1234567890",
    },
    "program": {
        "id": "11111111-1111-1111-1111-111111111111",
        "status": "completed",
        "required_stability_weeks": 8,
    },
    "stability": {
        "stability_gate_met": True,
        "current_consecutive_passed_weeks": 8,
    },
    "economics": {
        "economics_evaluable": True,
        "revenue_coverage_pct": 100.0,
        "cost_coverage_pct": 100.0,
        "unverified_cost_entries": 0,
        "operational_profit_positive": True,
        "operational_profit_minor": 250000,
    },
    "evidence": [
        {
            "evidence_type": "pilot_qa_exit",
            "status": "passed",
            "reference": "qa://exit-approved",
        },
        {
            "evidence_type": "operations_signoff",
            "status": "passed",
            "reference": "ops://owner-approved",
        },
    ],
    "post_pilot": {
        "scale_ready": True,
        "profitability_calculated_from_backend": True,
        "operational_profit_evidence_status": "backend_passed",
    },
}

with tempfile.TemporaryDirectory() as td:
    path = Path(td) / "pass.json"
    path.write_text(json.dumps(passing), encoding="utf-8")
    passed = subprocess.run(
        [sys.executable, str(GATE), str(path)],
        text=True,
        capture_output=True,
    )

if passed.returncode != 0 or "SCALE DECISION: PASS" not in passed.stdout:
    raise SystemExit("Scale gate rejected a complete backend economics evidence set.")

print("Sprint 46 scale decision gate verified: fail-closed + backend-profit positive path passed.")
