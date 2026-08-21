from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
    "backend/alembic/versions/0024_sprint49_launch_traffic_vendor_accounting.py",
    "backend/app/modules/launch_governance/schemas.py",
    "backend/app/modules/launch_governance/service.py",
    "backend/app/modules/launch_governance/router.py",
    "backend/app/modules/vendor_accounting/schemas.py",
    "backend/app/modules/vendor_accounting/service.py",
    "backend/app/modules/vendor_accounting/router.py",
    "backend/tests/test_sprint48_launch_traffic_vendor_accounting.py",
    "apps/admin_dashboard/src/pages/TrafficGovernance.tsx",
    "apps/admin_dashboard/src/pages/VendorAccounting.tsx",
    "scripts/pilot_launch_governance_evidence.py",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    raise SystemExit("Sprint 48 missing files: "+", ".join(missing))

models=(ROOT/"backend/app/core/db_models.py").read_text(encoding="utf-8")
orders=(ROOT/"backend/app/modules/orders/service.py").read_text(encoding="utf-8")
addresses=(ROOT/"backend/app/modules/addresses/service.py").read_text(encoding="utf-8")
special=(ROOT/"backend/app/modules/special_orders/service.py").read_text(encoding="utf-8")
traffic=(ROOT/"backend/app/modules/launch_governance/service.py").read_text(encoding="utf-8")
vendor=(ROOT/"backend/app/modules/vendor_accounting/service.py").read_text(encoding="utf-8")
financial=(ROOT/"backend/app/modules/financial_automation/service.py").read_text(encoding="utf-8")
jobs=(ROOT/"backend/app/modules/reliability/jobs.py").read_text(encoding="utf-8")
ops=(ROOT/"backend/app/modules/operations_control/service.py").read_text(encoding="utf-8")
main=(ROOT/"backend/app/main.py").read_text(encoding="utf-8")
config=(ROOT/"backend/app/core/config.py").read_text(encoding="utf-8")
pilot=(ROOT/".env.pilot.example").read_text(encoding="utf-8")
prod=(ROOT/".env.production.example").read_text(encoding="utf-8")

for cls in [
    "ZoneTrafficPolicyEntity",
    "ZoneAdmissionEventEntity",
    "ExpansionMonitoringSnapshotEntity",
]:
    assert f"class {cls}" in models

for token in [
    "admit_or_raise",
    "rollout_bucket",
    "zone_daily_cap_reached",
    "zone_hourly_cap_reached",
    "chef_daily_cap_reached",
    "outside_rollout_bucket",
    "refresh_monitoring",
]:
    assert token in traffic

assert "delivery_address_id" in (ROOT/"backend/app/modules/orders/schemas.py").read_text(encoding="utf-8")
assert "traffic_reservation" in orders
assert "address_change_traffic_reservation" in addresses
assert "special_traffic_reservation" in special
assert "vendor_accounting_dual_control_required" in vendor
assert "provider_import_review_required" in financial
assert "unclosed_provider_settlement_batches" in financial
assert '("expansion.monitor", {})' in jobs
assert "expansion_traffic_health:" in ops
assert "launch_governance_router" in main
assert "vendor_accounting_router" in main
assert 'version="0.50.0"' in main
assert "BAYTNA_EXPANSION_ROLLOUT_REQUIRED must be true" in config
assert "BAYTNA_TRAFFIC_REQUIRE_DELIVERY_ADDRESS_FOR_CHECKOUT must be true" in config
assert "BAYTNA_VENDOR_ACCOUNTING_REQUIRE_DUAL_CONTROL must be true" in config
assert "BAYTNA_VENDOR_ACCOUNTING_REQUIRE_CLOSED_SETTLEMENTS_FOR_ROLLOUT must be true" in config

for env_text in [pilot,prod]:
    assert "BAYTNA_TRAFFIC_REQUIRE_DELIVERY_ADDRESS_FOR_CHECKOUT=true" in env_text
    assert "BAYTNA_VENDOR_ACCOUNTING_REQUIRE_DUAL_CONTROL=true" in env_text
    assert "BAYTNA_VENDOR_ACCOUNTING_REQUIRE_CLOSED_SETTLEMENTS_FOR_ROLLOUT=true" in env_text

admin=(ROOT/"apps/admin_dashboard/src/App.tsx").read_text(encoding="utf-8")
assert "/traffic-governance" in admin
assert "/vendor-accounting" in admin

print("Sprint 48 static verification passed.")
