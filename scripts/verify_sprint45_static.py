from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "backend/alembic/versions/0021_sprint46_pilot_stability.py",
    "backend/app/modules/pilot_stability/schemas.py",
    "backend/app/modules/pilot_stability/service.py",
    "backend/app/modules/pilot_stability/router.py",
    "backend/tests/test_sprint45_pilot_stability.py",
    "apps/admin_dashboard/src/pages/Pilot.tsx",
    "scripts/pilot_scale_evidence.py",
    "scripts/pilot_scale_gate.py",
]
missing = [x for x in required if not (ROOT / x).exists()]
if missing:
    raise SystemExit("Missing Sprint 45 files: " + ", ".join(missing))

models = (ROOT / "backend/app/core/db_models.py").read_text(encoding="utf-8")
service = (ROOT / "backend/app/modules/pilot_stability/service.py").read_text(encoding="utf-8")
jobs = (ROOT / "backend/app/modules/reliability/jobs.py").read_text(encoding="utf-8")
main = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
page = (ROOT / "apps/admin_dashboard/src/pages/Pilot.tsx").read_text(encoding="utf-8")
shell = (ROOT / "apps/admin_dashboard/src/components/AppShell.tsx").read_text(encoding="utf-8")
scale_gate = (ROOT / "scripts/pilot_scale_gate.py").read_text(encoding="utf-8")

for cls in ["PilotProgramEntity", "PilotWeeklySnapshotEntity", "PilotQaEvidenceEntity"]:
    assert f"class {cls}" in models
assert "required_stability_weeks BETWEEN 8 AND 26" in models
assert "current_consecutive_passed_weeks" in service
assert "delivery_promise_coverage_pct" in service
assert "operational_profit_positive" in service
assert "profitability_calculated_from_backend=False" in service
assert 'job_type="pilot.snapshot"' in jobs
assert 'if job.job_type == "pilot.snapshot":' in jobs
assert "pilot_stability_router" in main
assert '"0021_sprint46"' in (ROOT / "backend/app/modules/health/router.py").read_text(encoding="utf-8")
assert "/pilot" in shell
assert "8-WEEK STABILITY GATE" in page
assert "Customer Cohorts" in page
assert "QA & Scale Evidence" in page
assert "Post-Pilot Analytics & Scale Decision" in page
assert "required_weeks < 8" in scale_gate
assert "profitability must come from reviewed external evidence" in scale_gate

print("Sprint 45 pilot execution/stability static verification passed.")
