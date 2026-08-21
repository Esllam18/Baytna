from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_EVIDENCE = {
    "pilot_qa_exit",
    "operations_signoff",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_json")
    parser.add_argument("--expected-release", default="0.50.0")
    parser.add_argument("--expected-migration-head", default="0025_sprint50")
    args = parser.parse_args()

    payload = json.loads(Path(args.evidence_json).read_text(encoding="utf-8"))
    failures: list[str] = []

    release = payload.get("release") or {}
    if release.get("version") != args.expected_release:
        failures.append("release version mismatch")
    if release.get("migration_head") != args.expected_migration_head:
        failures.append("migration head mismatch")
    if release.get("commit") in {None, "", "unknown"}:
        failures.append("release commit is not stamped")

    program = payload.get("program") or {}
    if program.get("status") != "completed":
        failures.append("pilot program is not completed")
    required_weeks = int(program.get("required_stability_weeks") or 0)
    if required_weeks < 8:
        failures.append("stability requirement was weakened below 8 weeks")

    stability = payload.get("stability") or {}
    if stability.get("stability_gate_met") is not True:
        failures.append("8-week stability gate not met")
    if int(stability.get("current_consecutive_passed_weeks") or 0) < 8:
        failures.append("fewer than 8 consecutive passed weeks")

    economics = payload.get("economics") or {}
    if economics.get("economics_evaluable") is not True:
        failures.append("backend economics is not evaluable")
    if float(economics.get("revenue_coverage_pct") or 0) != 100.0:
        failures.append("revenue coverage is not 100%")
    if float(economics.get("cost_coverage_pct") or 0) != 100.0:
        failures.append("cost coverage is not 100%")
    if int(economics.get("unverified_cost_entries") or 0) != 0:
        failures.append("unverified cost entries remain")
    if economics.get("operational_profit_positive") is not True:
        failures.append("backend operational profit is not positive")

    post = payload.get("post_pilot") or {}
    if post.get("scale_ready") is not True:
        failures.append("post-pilot scale readiness is blocked")
    if post.get("profitability_calculated_from_backend") is not True:
        failures.append("profitability is not calculated from backend ledger")
    if post.get("operational_profit_evidence_status") != "backend_passed":
        failures.append("backend profitability status is not passed")

    evidence_rows = {
        row.get("evidence_type"): row
        for row in payload.get("evidence") or []
    }
    for key in REQUIRED_EVIDENCE:
        row = evidence_rows.get(key) or {}
        if row.get("status") != "passed":
            failures.append(f"mandatory evidence not passed: {key}")
        if not str(row.get("reference") or "").strip():
            failures.append(f"mandatory evidence reference missing: {key}")

    if failures:
        print("SCALE DECISION: BLOCKED")
        for item in failures:
            print(f"- {item}")
        return 2

    print("SCALE DECISION: PASS")
    print(
        f"release={release.get('version')} "
        f"program={program.get('id')} "
        f"streak={stability.get('current_consecutive_passed_weeks')} "
        f"profit_minor={economics.get('operational_profit_minor')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
