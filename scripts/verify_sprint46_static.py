from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
    "backend/alembic/versions/0021_sprint46_operational_economics.py",
    "backend/app/modules/operational_economics/service.py",
    "backend/app/modules/operational_economics/router.py",
    "backend/app/modules/operational_economics/schemas.py",
    "backend/tests/test_sprint46_operational_economics.py",
    "apps/admin_dashboard/src/pages/Economics.tsx",
    "scripts/verify_sprint46_contract.py",
    "scripts/pilot_economics_evidence.py",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    raise SystemExit("Missing Sprint 46 files: "+", ".join(missing))

service=(ROOT/"backend/app/modules/operational_economics/service.py").read_text(encoding="utf-8")
pilot=(ROOT/"backend/app/modules/pilot_stability/service.py").read_text(encoding="utf-8")
main=(ROOT/"backend/app/main.py").read_text(encoding="utf-8")
health=(ROOT/"backend/app/modules/health/router.py").read_text(encoding="utf-8")
admin_api=(ROOT/"apps/admin_dashboard/src/api/admin.ts").read_text(encoding="utf-8")
page=(ROOT/"apps/admin_dashboard/src/pages/Economics.tsx").read_text(encoding="utf-8")
pilot_page=(ROOT/"apps/admin_dashboard/src/pages/Pilot.tsx").read_text(encoding="utf-8")

for token in [
    "contribution_margin_pct","operational_profit_minor",
    "cost_coverage_pct","revenue_coverage_pct",
    "economics_evaluable","operational_profit_positive",
    "assess_zone","approve_zone","launch_zone","pause_zone",
]:
    assert token in service

config=(ROOT/"backend/app/core/config.py").read_text(encoding="utf-8")
for token in ["chef_payout","delivery_partner","payment_processing"]:
    assert token in config

assert "profitability_calculated_from_backend=True" in pilot
assert "backend_operational_profit_not_positive" in pilot
assert '"operational_profit_positive"' not in pilot.split("MANDATORY_SCALE_EVIDENCE",1)[1].split(")",1)[0]
assert "operational_economics_router" in main
assert '"0021_sprint46"' in health

for symbol in [
    "economicsReport","economicsCosts","createEconomicsCost",
    "verifyEconomicsCost","expansionZones","createExpansionZone",
    "assessExpansionZone","approveExpansionZone",
    "launchExpansionZone","pauseExpansionZone",
]:
    assert symbol in admin_api

assert "BACKEND PROFITABILITY" in page
assert "Contribution margin" in page
assert "Expansion Readiness" in page
assert "operational_profit_positive" not in pilot_page

print("Sprint 46 Operational Economics static verification passed.")
