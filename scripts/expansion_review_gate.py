from __future__ import annotations

import argparse
import json
from pathlib import Path


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

    required_flags = [
        "slo_auto_pause_policy_verified",
        "capacity_forecast_verified",
        "daily_close_cadence_verified",
        "evidence_retention_verified",
        "expansion_review_verified",
    ]
    for flag in required_flags:
        if payload.get(flag) is not True:
            failures.append(f"missing or failed evidence: {flag}")

    review = payload.get("latest_review") or {}
    if review.get("status") != "healthy":
        failures.append("latest expansion review is not healthy")
    if review.get("recommendation") != "continue":
        failures.append("latest expansion review does not recommend continue")
    if review.get("blockers_json"):
        failures.append("latest expansion review has blockers")

    cadence = payload.get("cadence") or {}
    if int(cadence.get("overdue_open_rows") or 0) != 0:
        failures.append("overdue daily closes remain")
    if int(cadence.get("closed_system_rows") or 0) < 1:
        failures.append("no closed system-prepared cadence row")

    if failures:
        print("STABILIZATION DECISION: BLOCKED")
        for item in failures:
            print(f"- {item}")
        return 2

    print("STABILIZATION DECISION: PASS")
    print(
        f"release={release.get('version')} "
        f"zone={payload.get('zone_id')} "
        f"review={review.get('status')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
