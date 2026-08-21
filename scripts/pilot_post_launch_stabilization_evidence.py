from __future__ import annotations

import argparse
import json
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

EXPECTED_RELEASE = "0.50.0"
EXPECTED_MIGRATION = "0025_sprint50"


def get_json(base: str, token: str | None, path: str):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        base.rstrip("/") + path,
        headers=headers,
        method="GET",
    )
    with urllib.request.urlopen(
        request,
        timeout=30,
        context=ssl.create_default_context(),
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--admin-token", required=True)
    parser.add_argument("--zone-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    if not args.api.startswith("https://"):
        raise SystemExit("Post-launch evidence must come from HTTPS.")

    failures: list[str] = []
    release = get_json(args.api, None, "/health/release")
    if release.get("version") != EXPECTED_RELEASE:
        failures.append(f"release_version_not_{EXPECTED_RELEASE}")
    if release.get("migration_head") != EXPECTED_MIGRATION:
        failures.append(f"migration_head_not_{EXPECTED_MIGRATION}")
    if release.get("commit") in {None, "", "unknown"}:
        failures.append("release_commit_not_stamped")

    policy = get_json(
        args.api,
        args.admin_token,
        f"/api/v1/admin/traffic/zones/{args.zone_id}/policy",
    )
    auto_pause_verified = (
        policy.get("slo_auto_pause_enabled") is True
        and int(policy.get("slo_consecutive_red_snapshots") or 0) >= 2
    )
    if not auto_pause_verified:
        failures.append("slo_auto_pause_policy_not_safe")

    forecasts = get_json(
        args.api,
        args.admin_token,
        f"/api/v1/admin/traffic/zones/{args.zone_id}/capacity-forecasts?limit=50",
    )
    forecast_verified = bool(
        forecasts
        and forecasts[0].get("monitoring_snapshot_id")
        and forecasts[0].get("risk") in {"green", "amber", "red"}
    )
    if not forecast_verified:
        failures.append("capacity_forecast_missing")

    reviews = get_json(
        args.api,
        args.admin_token,
        "/api/v1/admin/post-launch/reviews?"
        + urllib.parse.urlencode({"zone_id": args.zone_id, "limit": 50}),
    )
    latest_review = reviews[0] if reviews else None
    review_verified = bool(
        latest_review
        and latest_review.get("status") == "healthy"
        and latest_review.get("recommendation") == "continue"
        and not latest_review.get("blockers_json")
    )
    if not review_verified:
        failures.append("expansion_review_not_healthy")

    closes = get_json(
        args.api,
        args.admin_token,
        f"/api/v1/admin/launch-command/sessions/{args.session_id}/financial-closes",
    )
    cadence_rows = [x for x in closes if x.get("cadence_due_at")]
    cadence_closed = [
        x
        for x in cadence_rows
        if x.get("prepared_by_system") is True and x.get("status") == "closed"
    ]
    overdue = [x for x in cadence_rows if x.get("overdue_notified_at") and x.get("status") != "closed"]
    cadence_verified = bool(cadence_closed) and not overdue
    if not cadence_verified:
        failures.append("daily_close_cadence_not_verified")

    packs = get_json(
        args.api,
        args.admin_token,
        f"/api/v1/admin/launch-command/sessions/{args.session_id}/evidence-packs",
    )
    complete_packs = [x for x in packs if x.get("status") == "complete"]
    malformed_complete = [x for x in complete_packs if x.get("retention_class") != "final" or x.get("retain_until") is not None]
    malformed_working = [
        x
        for x in packs
        if x.get("status") != "complete"
        and (x.get("retention_class") != "working" or not x.get("retain_until"))
    ]
    retention_verified = bool(complete_packs) and not malformed_complete and not malformed_working
    if not retention_verified:
        failures.append("evidence_retention_policy_not_verified")

    evidence = {
        "release": release,
        "zone_id": args.zone_id,
        "session_id": args.session_id,
        "slo_auto_pause_policy_verified": auto_pause_verified,
        "capacity_forecast_verified": forecast_verified,
        "daily_close_cadence_verified": cadence_verified,
        "evidence_retention_verified": retention_verified,
        "expansion_review_verified": review_verified,
        "policy": policy,
        "latest_forecast": forecasts[0] if forecasts else None,
        "latest_review": latest_review,
        "cadence": {
            "rows": cadence_rows,
            "closed_system_rows": len(cadence_closed),
            "overdue_open_rows": len(overdue),
        },
        "evidence_retention": {
            "pack_count": len(packs),
            "complete_final_count": len(complete_packs),
            "malformed_complete": len(malformed_complete),
            "malformed_working": len(malformed_working),
        },
        "verified": not failures,
        "failures": failures,
    }

    rendered = json.dumps(evidence, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
