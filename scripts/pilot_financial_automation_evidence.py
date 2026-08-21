from __future__ import annotations

import argparse
import json
import ssl
import urllib.parse
import urllib.request
from pathlib import Path


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
    parser.add_argument("--program-id", required=True)
    parser.add_argument("--zone-id", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    if not args.api.startswith("https://"):
        raise SystemExit(
            "Financial automation evidence must come from HTTPS."
        )

    failures: list[str] = []

    release = get_json(args.api, None, "/health/release")
    if release.get("version") != "0.50.0":
        failures.append("release_version_not_0.50.0")
    if release.get("migration_head") != "0025_sprint50":
        failures.append("migration_head_not_0025_sprint50")
    if release.get("commit") in {"", None, "unknown"}:
        failures.append("release_commit_not_stamped")

    imports = get_json(
        args.api,
        args.admin_token,
        "/api/v1/admin/economics/imports?limit=500",
    )
    applied_imports = [
        item
        for item in imports
        if item.get("status") == "applied"
        and item.get("pilot_program_id") == args.program_id
        and int(item.get("applied_cost_entries") or 0) > 0
    ]
    if not applied_imports:
        failures.append("no_applied_provider_cost_import_for_program")

    settlements = get_json(
        args.api,
        args.admin_token,
        "/api/v1/admin/economics/settlements?limit=500",
    )
    program_settlements = [
        item
        for item in settlements
        if item.get("pilot_program_id") == args.program_id
    ]
    reconciled_paymob = [
        item
        for item in program_settlements
        if item.get("provider") == "paymob"
        and item.get("status") == "reconciled"
        and int(item.get("mismatched_lines") or 0) == 0
        and int(item.get("matched_lines") or 0)
        == int(item.get("rows_count") or 0)
    ]
    if not reconciled_paymob:
        failures.append("no_clean_paymob_settlement_for_program")
    if any(x.get("status") == "blocked" for x in program_settlements):
        failures.append("blocked_settlement_batch_for_program")

    budget = get_json(
        args.api,
        args.admin_token,
        f"/api/v1/admin/economics/zones/{args.zone_id}/budgets",
    )
    if budget.get("budget_ready") is not True:
        failures.append("expansion_budget_not_ready")
    if budget.get("missing_categories"):
        failures.append("expansion_budget_categories_missing")

    rollout = get_json(
        args.api,
        args.admin_token,
        f"/api/v1/admin/economics/zones/{args.zone_id}/rollout/history?limit=100",
    )
    launch_events = [
        item
        for item in rollout
        if item.get("to_stage") in {"canary", "limited", "full"}
    ]
    if not launch_events:
        failures.append("controlled_rollout_event_missing")

    zone_detail = get_json(
        args.api,
        args.admin_token,
        f"/api/v1/admin/economics/zones/{args.zone_id}",
    )
    zone = zone_detail.get("zone") or {}
    if zone.get("source_program_id") != args.program_id:
        failures.append("zone_source_program_mismatch")
    if zone.get("rollout_stage") not in {
        "canary",
        "limited",
        "full",
    }:
        failures.append("zone_not_in_active_rollout")

    evidence = {
        "release": release,
        "program_id": args.program_id,
        "zone_id": args.zone_id,
        "provider_cost_import": {
            "verified": bool(applied_imports),
            "applied_batches": [
                {
                    "id": x.get("id"),
                    "provider": x.get("provider"),
                    "external_reference": x.get("external_reference"),
                    "applied_cost_entries": x.get(
                        "applied_cost_entries"
                    ),
                }
                for x in applied_imports
            ],
        },
        "paymob_settlement": {
            "reconciled": bool(reconciled_paymob),
            "batches": [
                {
                    "id": x.get("id"),
                    "external_reference": x.get("external_reference"),
                    "rows_count": x.get("rows_count"),
                    "matched_lines": x.get("matched_lines"),
                    "fees_minor": x.get("fees_minor"),
                    "net_settlement_minor": x.get(
                        "net_settlement_minor"
                    ),
                }
                for x in reconciled_paymob
            ],
        },
        "budget": budget,
        "rollout": {
            "zone": {
                "status": zone.get("status"),
                "rollout_stage": zone.get("rollout_stage"),
                "rollout_percent": zone.get("rollout_percent"),
                "daily_order_cap": zone.get("daily_order_cap"),
            },
            "latest_event": launch_events[0] if launch_events else None,
        },
        "verified": not failures,
        "failures": failures,
    }

    rendered = json.dumps(
        evidence,
        ensure_ascii=False,
        indent=2,
    )
    print(rendered)

    if args.output:
        Path(args.output).write_text(
            rendered + "\n",
            encoding="utf-8",
        )

    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
