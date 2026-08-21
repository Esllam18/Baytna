from __future__ import annotations

import argparse
import json
import ssl
import urllib.request
from pathlib import Path


def get_json(base: str, token: str | None, path: str):
    headers={"Accept":"application/json"}
    if token:
        headers["Authorization"]=f"Bearer {token}"
    req=urllib.request.Request(
        base.rstrip("/")+path,
        headers=headers,
        method="GET",
    )
    with urllib.request.urlopen(
        req,
        timeout=30,
        context=ssl.create_default_context(),
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--api",required=True)
    parser.add_argument("--admin-token",required=True)
    parser.add_argument("--program-id",required=True)
    parser.add_argument("--zone-id",required=True)
    parser.add_argument("--output",default="")
    args=parser.parse_args()

    if not args.api.startswith("https://"):
        raise SystemExit("Launch-governance evidence must come from HTTPS.")

    failures=[]

    release=get_json(args.api,None,"/health/release")
    if release.get("version")!="0.50.0":
        failures.append("release_version_not_0.50.0")
    if release.get("migration_head")!="0025_sprint50":
        failures.append("migration_head_not_0025_sprint50")
    if release.get("commit") in {"",None,"unknown"}:
        failures.append("release_commit_not_stamped")

    zones=get_json(
        args.api,args.admin_token,
        "/api/v1/admin/traffic/zones",
    )
    zone=next(
        (x for x in zones if x.get("zone_id")==args.zone_id),
        None,
    )
    if zone is None:
        failures.append("traffic_zone_not_found")
        zone={}
    policy=zone.get("policy") or {}
    if policy.get("is_enabled") is not True:
        failures.append("traffic_policy_not_enabled")
    if policy.get("enforce_rollout_bucket") is not True:
        failures.append("rollout_bucket_not_enforced")
    if not policy.get("hourly_order_cap"):
        failures.append("hourly_order_cap_missing")
    if not policy.get("chef_daily_order_cap"):
        failures.append("chef_daily_order_cap_missing")
    if not zone.get("daily_order_cap"):
        failures.append("zone_daily_order_cap_missing")
    if zone.get("rollout_stage") not in {"canary","limited","full"}:
        failures.append("zone_not_in_active_rollout")

    monitoring=get_json(
        args.api,args.admin_token,
        f"/api/v1/admin/traffic/zones/{args.zone_id}/monitoring?limit=20",
    )
    latest=monitoring[0] if monitoring else None
    if latest is None:
        failures.append("expansion_monitoring_missing")
    elif latest.get("health")=="red":
        failures.append("expansion_monitoring_red")

    admissions=get_json(
        args.api,args.admin_token,
        f"/api/v1/admin/traffic/zones/{args.zone_id}/admissions?limit=500",
    )
    admitted=[
        x for x in admissions
        if x.get("decision")=="admitted"
        and x.get("order_id")
    ]
    if not admitted:
        failures.append("real_order_admission_evidence_missing")

    imports=get_json(
        args.api,args.admin_token,
        "/api/v1/admin/vendor-accounting/import-reviews?limit=1000",
    )
    approved_imports=[
        x for x in imports
        if x.get("pilot_program_id")==args.program_id
        and x.get("status")=="applied"
        and x.get("review_status")=="approved"
        and x.get("reviewed_by_admin_id")
        and x.get("created_by_admin_id")
        and x.get("reviewed_by_admin_id")!=x.get("created_by_admin_id")
    ]
    if not approved_imports:
        failures.append("independent_provider_import_review_missing")

    settlements=get_json(
        args.api,args.admin_token,
        "/api/v1/admin/vendor-accounting/settlements?limit=1000",
    )
    closed_settlements=[
        x for x in settlements
        if x.get("pilot_program_id")==args.program_id
        and x.get("status")=="reconciled"
        and x.get("operations_status")=="closed"
        and int(x.get("mismatched_lines") or 0)==0
        and int(x.get("matched_lines") or 0)==int(x.get("rows_count") or 0)
        and x.get("closed_by_admin_id")
    ]
    if not closed_settlements:
        failures.append("closed_provider_settlement_missing")

    evidence={
        "release":release,
        "program_id":args.program_id,
        "zone_id":args.zone_id,
        "traffic_policy":policy,
        "zone":{
            "area":zone.get("area"),
            "status":zone.get("zone_status"),
            "rollout_stage":zone.get("rollout_stage"),
            "rollout_percent":zone.get("rollout_percent"),
            "daily_order_cap":zone.get("daily_order_cap"),
        },
        "latest_monitoring":latest,
        "admission_evidence":admitted[0] if admitted else None,
        "vendor_import_review":{
            "verified":bool(approved_imports),
            "sample":approved_imports[0] if approved_imports else None,
        },
        "settlement_operations":{
            "verified":bool(closed_settlements),
            "sample":closed_settlements[0] if closed_settlements else None,
        },
        "verified":not failures,
        "failures":failures,
    }

    rendered=json.dumps(evidence,ensure_ascii=False,indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered+"\n",encoding="utf-8")
    return 0 if not failures else 2


if __name__=="__main__":
    raise SystemExit(main())
