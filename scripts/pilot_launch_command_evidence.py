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
    parser.add_argument("--session-id",required=True)
    parser.add_argument("--output",default="")
    args=parser.parse_args()

    if not args.api.startswith("https://"):
        raise SystemExit("Launch Command evidence must come from HTTPS.")

    failures=[]

    release=get_json(args.api,None,"/health/release")
    if release.get("version")!="0.50.0":
        failures.append("release_version_not_0.50.0")
    if release.get("migration_head")!="0025_sprint50":
        failures.append("migration_head_not_0025_sprint50")
    if release.get("commit") in {"",None,"unknown"}:
        failures.append("release_commit_not_stamped")

    overview=get_json(
        args.api,args.admin_token,
        f"/api/v1/admin/launch-command/sessions/{args.session_id}",
    )
    session=overview.get("session") or {}
    if session.get("status") not in {"active","paused","completed"}:
        failures.append("launch_session_not_operational")
    if not session.get("finance_admin_id"):
        failures.append("finance_admin_missing")
    if not session.get("operations_admin_id"):
        failures.append("operations_admin_missing")

    runbook=get_json(
        args.api,args.admin_token,
        f"/api/v1/admin/launch-command/sessions/{args.session_id}/runbook",
    )
    required_not_passed=[
        x.get("step_key")
        for x in runbook
        if x.get("is_required") and x.get("status")!="passed"
    ]
    if required_not_passed:
        failures.append("required_runbook_steps_not_passed")

    overrides=get_json(
        args.api,args.admin_token,
        f"/api/v1/admin/launch-command/sessions/{args.session_id}/traffic-overrides",
    )
    active_overrides=[x for x in overrides if x.get("status")=="active"]
    if active_overrides:
        failures.append("active_traffic_overrides_present")

    closes=get_json(
        args.api,args.admin_token,
        f"/api/v1/admin/launch-command/sessions/{args.session_id}/financial-closes",
    )
    launch_close=next(
        (
            x for x in closes
            if x.get("close_date")==session.get("launch_date")
            and x.get("status")=="closed"
            and x.get("checksum_sha256")
        ),
        None,
    )
    if launch_close is None:
        failures.append("launch_day_financial_close_not_closed")

    drills=get_json(
        args.api,args.admin_token,
        f"/api/v1/admin/launch-command/sessions/{args.session_id}/rollback-drills",
    )
    passed_drills=[
        x for x in drills
        if x.get("status")=="passed"
        and x.get("evidence_reference")
        and x.get("recovery_seconds") is not None
        and x.get("target_recovery_seconds") is not None
        and x.get("recovery_seconds")<=x.get("target_recovery_seconds")
    ]
    if not passed_drills:
        failures.append("rollback_drill_not_verified")

    packs=get_json(
        args.api,args.admin_token,
        f"/api/v1/admin/launch-command/sessions/{args.session_id}/evidence-packs",
    )
    complete_packs=[
        x for x in packs
        if x.get("status")=="complete"
        and not x.get("blockers_json")
        and x.get("release_version")=="0.50.0"
        and x.get("migration_head")=="0025_sprint50"
        and x.get("checksum_sha256")
    ]
    if not complete_packs:
        failures.append("complete_launch_evidence_pack_missing")

    evidence={
        "release":release,
        "session":session,
        "overview":{
            "zone_status":overview.get("zone_status"),
            "rollout_stage":overview.get("rollout_stage"),
            "rollout_percent":overview.get("rollout_percent"),
            "runbook_total":overview.get("runbook_total"),
            "runbook_passed":overview.get("runbook_passed"),
            "runbook_blocking":overview.get("runbook_blocking"),
            "active_overrides":overview.get("active_overrides"),
        },
        "runbook":{
            "required_not_passed":required_not_passed,
            "steps":runbook,
        },
        "active_overrides":active_overrides,
        "launch_day_financial_close":launch_close,
        "rollback_drill":passed_drills[0] if passed_drills else None,
        "evidence_pack":complete_packs[0] if complete_packs else None,
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
