from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_TRUE = [
    "postgresql_staging_ready",
    "migrations_applied",
    "api_https_ready",
    "admin_https_ready",
    "customer_android_build_installed",
    "chef_android_build_installed",
    "driver_android_build_installed",
    "customer_fcm_received",
    "chef_fcm_received",
    "driver_fcm_received",
    "sentry_customer_event_verified",
    "sentry_chef_event_verified",
    "sentry_driver_event_verified",
    "sentry_admin_event_verified",
    "paymob_real_pilot_payment_verified",
    "paymob_webhook_verified",
    "s3_upload_download_verified",
    "twilio_sms_verified",
    "cross_app_live_journey_verified",
    "delivery_promise_live_order_verified",
    "on_time_kpi_measurable",
    "ops_auto_escalation_verified",
    "ops_incident_notification_verified",
    "backend_economics_evaluable",
    "backend_operational_profit_positive",
    "economics_cost_coverage_complete",
    "expansion_canary_rollout_verified",
    "expansion_budget_ready",
    "paymob_settlement_reconciled",
    "provider_cost_import_verified",
    "expansion_monitoring_verified",
    "settlement_operations_closed",
    "vendor_accounting_dual_control_verified",
    "capacity_admission_verified",
    "traffic_governance_policy_verified",
    "launch_evidence_pack_complete",
    "rollback_drill_verified",
    "daily_financial_close_closed",
    "canary_runbook_complete",
    "launch_command_session_verified",
    "rollback_rehearsed",
    "operations_owner_signed_off",
]

REQUIRED_ARTIFACTS = [
    "api_release_url",
    "admin_dashboard_url",
    "customer_build_url",
    "chef_build_url",
    "driver_build_url",
    "sentry_release",
    "cross_app_run_id",
    "migration_head",
    "delivery_timing_evidence_file",
    "ops_incident_evidence_id",
    "economics_evidence_file",
    "expansion_rollout_event_id",
    "settlement_batch_reference",
    "financial_automation_evidence_file",
    "vendor_accounting_evidence_file",
    "monitoring_snapshot_id",
    "launch_governance_evidence_file",
    "launch_evidence_pack_checksum",
    "launch_evidence_pack_id",
    "rollback_drill_id",
    "daily_financial_close_id",
    "launch_command_session_id",
    "launch_command_evidence_file",
]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence")
    parser.add_argument("--expected-release", default="0.50.0")
    args = parser.parse_args()

    path = Path(args.evidence)
    payload = json.loads(path.read_text(encoding="utf-8"))

    failures: list[str] = []

    if payload.get("release") != args.expected_release:
        failures.append(
            f"release mismatch: expected {args.expected_release}, got {payload.get('release')}"
        )

    commit = str(payload.get("commit") or "").strip()
    if len(commit) < 7:
        failures.append("commit evidence is missing")

    evidence = payload.get("evidence") or {}
    for key in REQUIRED_TRUE:
        if evidence.get(key) is not True:
            failures.append(f"gate not proven: {key}")

    artifacts = payload.get("artifacts") or {}
    for key in REQUIRED_ARTIFACTS:
        if not str(artifacts.get(key) or "").strip():
            failures.append(f"artifact evidence missing: {key}")

    if artifacts.get("migration_head") != "0025_sprint50":
        failures.append(
            "migration head evidence mismatch: expected 0025_sprint50"
        )

    if failures:
        print("GO-LIVE: BLOCKED")
        for item in failures:
            print(f"- {item}")
        return 2

    print("GO-LIVE: PASS")
    print(f"release={payload['release']} commit={commit}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
