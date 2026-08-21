from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
    "backend/alembic/versions/0024_sprint49_launch_command_center.py",
    "backend/app/modules/launch_command/schemas.py",
    "backend/app/modules/launch_command/service.py",
    "backend/app/modules/launch_command/router.py",
    "backend/tests/test_sprint49_launch_command_center.py",
    "apps/admin_dashboard/src/pages/LaunchCommand.tsx",
    "scripts/pilot_launch_command_evidence.py",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    raise SystemExit("Sprint 49 missing files: "+", ".join(missing))

config=(ROOT/"backend/app/core/config.py").read_text(encoding="utf-8")
models=(ROOT/"backend/app/core/db_models.py").read_text(encoding="utf-8")
service=(ROOT/"backend/app/modules/launch_command/service.py").read_text(encoding="utf-8")
jobs=(ROOT/"backend/app/modules/reliability/jobs.py").read_text(encoding="utf-8")
financial=(ROOT/"backend/app/modules/financial_automation/service.py").read_text(encoding="utf-8")
main=(ROOT/"backend/app/main.py").read_text(encoding="utf-8")
pilot=(ROOT/".env.pilot.example").read_text(encoding="utf-8")
prod=(ROOT/".env.production.example").read_text(encoding="utf-8")

for cls in [
    "LaunchCommandSessionEntity",
    "LaunchRunbookStepEntity",
    "LaunchCommandEventEntity",
    "LaunchTrafficOverrideEntity",
    "DailyFinancialCloseEntity",
    "LaunchRollbackDrillEntity",
    "LaunchEvidencePackEntity",
]:
    assert f"class {cls}" in models

for token in [
    "RUNBOOK_TEMPLATE",
    "create_override",
    "expire_overrides",
    "prepare_financial_close",
    "close_financial_day",
    "start_rollback_drill",
    "complete_rollback_drill",
    "generate_evidence_pack",
    "maintain",
]:
    assert token in service

assert '("launch.command.maintain", {})' in jobs
assert "launch_command_session_required" in financial
assert "launch_command_router" in main
assert 'version="0.50.0"' in main

for line in [
    "BAYTNA_LAUNCH_COMMAND_REQUIRED must be true",
    "BAYTNA_LAUNCH_COMMAND_REQUIRE_DUAL_CONTROL must be true",
]:
    assert line in config

for env_text in [pilot,prod]:
    assert "BAYTNA_LAUNCH_COMMAND_REQUIRED=true" in env_text
    assert "BAYTNA_LAUNCH_COMMAND_REQUIRE_DUAL_CONTROL=true" in env_text
    assert "BAYTNA_LAUNCH_EVIDENCE_REQUIRE_NO_ACTIVE_OVERRIDES=true" in env_text

admin=(ROOT/"apps/admin_dashboard/src/App.tsx").read_text(encoding="utf-8")
nav=(ROOT/"apps/admin_dashboard/src/components/AppShell.tsx").read_text(encoding="utf-8")
assert "/launch-command" in admin
assert "/launch-command" in nav

print("Sprint 49 static verification passed.")
