from __future__ import annotations

import argparse
import json
import ssl
import urllib.request
from pathlib import Path


def get_json(base: str, token: str, path: str):
    req=urllib.request.Request(
        base.rstrip("/") + path,
        headers={"Authorization":f"Bearer {token}","Accept":"application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req,timeout=30,context=ssl.create_default_context()) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--api",required=True)
    parser.add_argument("--admin-token",required=True)
    parser.add_argument("--program-id",required=True)
    parser.add_argument("--min-contribution-margin-pct",type=float,default=0.0)
    parser.add_argument("--output",default="")
    args=parser.parse_args()

    if not args.api.startswith("https://"):
        raise SystemExit("Economics evidence must come from HTTPS.")

    release=get_json(args.api,args.admin_token,"/health/release")
    economics=get_json(
        args.api,args.admin_token,
        f"/api/v1/admin/economics/programs/{args.program_id}/report",
    )
    failures=[]
    if release.get("version")!="0.50.0":
        failures.append("release_version_mismatch")
    if release.get("migration_head")!="0025_sprint50":
        failures.append("migration_head_mismatch")
    if economics.get("economics_evaluable") is not True:
        failures.append("economics_not_evaluable")
    if economics.get("revenue_coverage_pct") != 100.0:
        failures.append("revenue_coverage_not_100")
    if economics.get("cost_coverage_pct") != 100.0:
        failures.append("cost_coverage_not_100")
    if economics.get("unverified_cost_entries") != 0:
        failures.append("unverified_cost_entries_present")
    if economics.get("operational_profit_positive") is not True:
        failures.append("operational_profit_not_positive")
    margin=economics.get("contribution_margin_pct")
    if margin is None or float(margin)<args.min_contribution_margin_pct:
        failures.append("contribution_margin_below_requested_threshold")

    payload={
        "release":release,
        "program_id":args.program_id,
        "economics":economics,
        "verified":not failures,
        "failures":failures,
    }
    rendered=json.dumps(payload,ensure_ascii=False,indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered+"\\n",encoding="utf-8")
    return 0 if not failures else 2


if __name__=="__main__":
    raise SystemExit(main())
