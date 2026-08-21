from __future__ import annotations

import argparse
import json
import ssl
import urllib.request
from pathlib import Path


def request_json(*, base_url: str, bearer: str, path: str):
    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        headers={
            "Authorization": f"Bearer {bearer}",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(
        req,
        timeout=30,
        context=ssl.create_default_context(),
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--admin-token", required=True)
    parser.add_argument("--program-id", required=True)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    if not args.api.startswith("https://"):
        raise SystemExit("Pilot scale evidence must come from HTTPS.")

    release = request_json(
        base_url=args.api,
        bearer=args.admin_token,
        path="/health/release",
    )
    program = request_json(
        base_url=args.api,
        bearer=args.admin_token,
        path=f"/api/v1/admin/pilot/programs/{args.program_id}",
    )
    stability = request_json(
        base_url=args.api,
        bearer=args.admin_token,
        path=f"/api/v1/admin/pilot/programs/{args.program_id}/stability",
    )
    cohorts = request_json(
        base_url=args.api,
        bearer=args.admin_token,
        path=f"/api/v1/admin/pilot/programs/{args.program_id}/cohorts?weeks=8",
    )
    evidence = request_json(
        base_url=args.api,
        bearer=args.admin_token,
        path=f"/api/v1/admin/pilot/programs/{args.program_id}/evidence",
    )
    post = request_json(
        base_url=args.api,
        bearer=args.admin_token,
        path=f"/api/v1/admin/pilot/programs/{args.program_id}/post-pilot",
    )
    economics = request_json(
        base_url=args.api,
        bearer=args.admin_token,
        path=f"/api/v1/admin/economics/programs/{args.program_id}/report",
    )

    payload = {
        "release": release,
        "program": program,
        "stability": stability,
        "cohorts": cohorts,
        "evidence": evidence,
        "post_pilot": post,
        "economics": economics,
        "scale_ready": bool(post.get("scale_ready")),
        "scale_blockers": post.get("scale_blockers") or [],
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return 0 if payload["scale_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
