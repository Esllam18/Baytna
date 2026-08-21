from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

required=[
    "backend/app/modules/operations_control/service.py",
    "backend/app/modules/operations_control/router.py",
    "backend/app/modules/operations_control/schemas.py",
    "backend/alembic/versions/0018_sprint43_operations_control_room.py",
    "backend/tests/test_sprint43_operations_control_room.py",
    "apps/admin_dashboard/src/pages/ControlRoom.tsx",
    "scripts/verify_sprint43_contract.py",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    raise SystemExit("Missing Sprint 43 files: "+", ".join(missing))

service=(ROOT/"backend/app/modules/operations_control/service.py").read_text(encoding="utf-8")
jobs=(ROOT/"backend/app/modules/reliability/jobs.py").read_text(encoding="utf-8")
main=(ROOT/"backend/app/main.py").read_text(encoding="utf-8")
api=(ROOT/"apps/admin_dashboard/src/api/admin.ts").read_text(encoding="utf-8")
page=(ROOT/"apps/admin_dashboard/src/pages/ControlRoom.tsx").read_text(encoding="utf-8")
shell=(ROOT/"apps/admin_dashboard/src/components/AppShell.tsx").read_text(encoding="utf-8")

for detector in [
    "chef_acceptance:",
    "delivery_assignment:",
    "delivery_issue:",
    "support_sla:",
    "payment_reconciliation:",
    "outbox_dead:",
    "job_dead:",
    "worker_stale:",
    "notification_dead:",
]:
    assert detector in service

assert '("operations.scan", {})' in jobs
assert 'if job.job_type == "operations.scan":' in jobs
assert "operations_control_router" in main
assert '"0021_sprint46"' in (ROOT/"backend/app/modules/health/router.py").read_text(encoding="utf-8")

for symbol in [
    "refreshControlRoom",
    "controlRoomOverview",
    "controlRoomKpis",
    "dailyBrief",
    "incidents",
    "acknowledgeIncident",
    "assignIncident",
    "escalateIncident",
    "resolveIncident",
]:
    assert symbol in api

assert "/control-room" in shell
assert "Launch KPI Gates" in page
assert "On-time ≥ 95%" in page
assert "delivery_promise_coverage_pct" in page
assert "launch_target_on_time_met" in page
assert "launch_target_delivery_met" not in page

print("Inherited Control Room static verification passed under Sprint 44.")
