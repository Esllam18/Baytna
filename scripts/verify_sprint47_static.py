from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

required=[
    "backend/alembic/versions/0022_sprint47_financial_reconciliation_rollout.py",
    "backend/app/modules/financial_automation/schemas.py",
    "backend/app/modules/financial_automation/service.py",
    "backend/app/modules/financial_automation/router.py",
    "backend/tests/test_sprint47_financial_automation.py",
    "apps/admin_dashboard/src/pages/FinancialAutomation.tsx",
    "apps/admin_dashboard/src/pages/Economics.tsx",
    "scripts/pilot_financial_automation_evidence.py",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    raise SystemExit("Sprint 47 missing files: "+", ".join(missing))

models=(ROOT/"backend/app/core/db_models.py").read_text(encoding="utf-8")
service=(ROOT/"backend/app/modules/financial_automation/service.py").read_text(encoding="utf-8")
jobs=(ROOT/"backend/app/modules/reliability/jobs.py").read_text(encoding="utf-8")
ops=(ROOT/"backend/app/modules/operations_control/service.py").read_text(encoding="utf-8")
main=(ROOT/"backend/app/main.py").read_text(encoding="utf-8")
economics=(ROOT/"apps/admin_dashboard/src/pages/Economics.tsx").read_text(encoding="utf-8")
automation=(ROOT/"apps/admin_dashboard/src/pages/FinancialAutomation.tsx").read_text(encoding="utf-8")
shell=(ROOT/"apps/admin_dashboard/src/components/AppShell.tsx").read_text(encoding="utf-8")
pilot=(ROOT/".env.pilot.example").read_text(encoding="utf-8")
production=(ROOT/".env.production.example").read_text(encoding="utf-8")
gate=(ROOT/"scripts/go_live_gate.py").read_text(encoding="utf-8")

for cls in [
    "ProviderCostImportBatchEntity",
    "ProviderCostImportLineEntity",
    "ProviderSettlementBatchEntity",
    "ProviderSettlementLineEntity",
    "ExpansionZoneBudgetEntity",
    "ExpansionRolloutEventEntity",
]:
    assert f"class {cls}" in models

for feature in [
    "sync_twilio_usage",
    "create_settlement",
    "reconcile_settlement",
    "budget_summary",
    "start_rollout",
    "advance_rollout",
    "pause_rollout",
    "resume_rollout",
]:
    assert f"def {feature}" in service

assert '("finance.settlements.reconcile", {})' in jobs
assert 'job.job_type == "finance.settlements.reconcile"' in jobs
assert "provider_settlement_blocked:" in ops
assert "financial_automation_router" in main
assert 'version="0.47.0"' in main

assert "Start Canary" in economics
assert "Advance Rollout" in economics
assert "Launch Budget" in economics
assert "communications_provider" in economics
assert "Provider Cost Import" in automation
assert "Twilio Usage Sync" in automation
assert "Paymob Settlement Import" in automation
assert "/finance-automation" in shell

for env_text in [pilot,production]:
    assert "BAYTNA_EXPANSION_ROLLOUT_REQUIRED=true" in env_text
    assert "BAYTNA_EXPANSION_REQUIRED_BUDGET_CATEGORIES=" in env_text

assert "provider_cost_import_verified" in gate
assert "paymob_settlement_reconciled" in gate
assert "expansion_budget_ready" in gate
assert "expansion_canary_rollout_verified" in gate

health=(ROOT/"backend/app/modules/health/router.py").read_text(encoding="utf-8")
assert '"0022_sprint47"' in health

print("Sprint 47 financial automation/static verification passed.")
