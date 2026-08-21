from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required = [
    "backend/alembic/versions/0025_sprint50_post_launch_stabilization.py",
    "backend/app/modules/post_launch/schemas.py",
    "backend/app/modules/post_launch/service.py",
    "backend/app/modules/post_launch/router.py",
    "backend/tests/test_sprint50_post_launch_stabilization.py",
    "apps/admin_dashboard/src/pages/PostLaunch.tsx",
    "scripts/pilot_post_launch_stabilization_evidence.py",
    "scripts/expansion_review_gate.py",
]
missing = [path for path in required if not (ROOT / path).exists()]
if missing:
    raise SystemExit("Sprint 50 missing files: " + ", ".join(missing))

config = (ROOT / "backend/app/core/config.py").read_text(encoding="utf-8")
models = (ROOT / "backend/app/core/db_models.py").read_text(encoding="utf-8")
traffic = (ROOT / "backend/app/modules/launch_governance/service.py").read_text(encoding="utf-8")
financial = (ROOT / "backend/app/modules/financial_automation/service.py").read_text(encoding="utf-8")
command = (ROOT / "backend/app/modules/launch_command/service.py").read_text(encoding="utf-8")
post_launch = (ROOT / "backend/app/modules/post_launch/service.py").read_text(encoding="utf-8")
jobs = (ROOT / "backend/app/modules/reliability/jobs.py").read_text(encoding="utf-8")
main = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
health = (ROOT / "backend/app/modules/health/router.py").read_text(encoding="utf-8")
pilot = (ROOT / ".env.pilot.example").read_text(encoding="utf-8")
prod = (ROOT / ".env.production.example").read_text(encoding="utf-8")

for cls in [
    "ExpansionCapacityForecastEntity",
    "ExpansionReviewEntity",
]:
    assert f"class {cls}" in models

for token in [
    "slo_auto_pause_enabled",
    "slo_consecutive_red_snapshots",
    "prepared_by_system",
    "cadence_due_at",
    "retention_class",
    "retain_until",
    "trigger_source",
    "trigger_reason",
]:
    assert token in models

for token in [
    "capacity_forecast_for_snapshot",
    "_consecutive_red_streak",
    "_evaluate_slo_auto_pause",
]:
    assert token in traffic

assert "auto_pause_rollout" in financial
for token in [
    "prepare_due_financial_closes",
    "prune_expired_working_evidence",
    "monitor_overdue_financial_closes",
]:
    assert token in command

for token in [
    "refresh_review",
    "refresh_due_reviews",
    "recommendation",
]:
    assert token in post_launch

# Sprint 50 reuses the existing jobs instead of adding another high-frequency loop.
assert '("expansion.monitor", {})' in jobs
assert '("launch.command.maintain", {})' in jobs
assert 'version="0.50.0"' in main
assert '"sprint": "50"' in main
assert '"migration_head": "0025_sprint50"' in health
assert "post_launch_router" in main

for line in [
    "BAYTNA_SLO_AUTO_PAUSE_DEFAULT_ENABLED must be true",
    "BAYTNA_LAUNCH_DAILY_CLOSE_CADENCE_ENABLED must be true",
]:
    assert line in config

for env_text in [pilot, prod]:
    for required_line in [
        "BAYTNA_SLO_AUTO_PAUSE_DEFAULT_ENABLED=true",
        "BAYTNA_SLO_CONSECUTIVE_RED_SNAPSHOTS=2",
        "BAYTNA_LAUNCH_DAILY_CLOSE_CADENCE_ENABLED=true",
    ]:
        assert required_line in env_text

app = (ROOT / "apps/admin_dashboard/src/App.tsx").read_text(encoding="utf-8")
nav = (ROOT / "apps/admin_dashboard/src/components/AppShell.tsx").read_text(encoding="utf-8")
traffic_ui = (ROOT / "apps/admin_dashboard/src/pages/TrafficGovernance.tsx").read_text(encoding="utf-8")
post_ui = (ROOT / "apps/admin_dashboard/src/pages/PostLaunch.tsx").read_text(encoding="utf-8")
assert "/post-launch" in app
assert "/post-launch" in nav
assert "slo_auto_pause_enabled" in traffic_ui
assert "capacity" in traffic_ui.lower()
assert "auto" in post_ui.lower() and "resume" in post_ui.lower()

print("Sprint 50 static verification passed.")
