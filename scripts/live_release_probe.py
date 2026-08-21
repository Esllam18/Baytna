from __future__ import annotations

import argparse
import json
import ssl
import urllib.request


def get_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(
        req,
        timeout=20,
        context=ssl.create_default_context(),
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--expected-release", default="0.50.0")
    parser.add_argument("--expected-environment", default="staging")
    parser.add_argument("--expected-migration-head", default="0025_sprint50")
    args = parser.parse_args()

    base = args.api.rstrip("/")
    if not base.startswith("https://"):
        raise SystemExit("Pilot API must be HTTPS.")

    ready = get_json(base + "/health/ready")
    release = get_json(base + "/health/release")
    reliability = get_json(base + "/health/reliability")

    if ready.get("status") != "ready":
        raise SystemExit("API readiness failed.")
    if release.get("version") != args.expected_release:
        raise SystemExit(
            f"Release mismatch: {release.get('version')} != {args.expected_release}"
        )
    if release.get("environment") != args.expected_environment:
        raise SystemExit(
            "Environment mismatch: "
            f"{release.get('environment')} != {args.expected_environment}"
        )
    if release.get("commit") in {"", None, "unknown"}:
        raise SystemExit("Release commit is not stamped.")
    if release.get("migration_head") != args.expected_migration_head:
        raise SystemExit(
            "Migration head mismatch: "
            f"{release.get('migration_head')} != {args.expected_migration_head}"
        )
    if reliability.get("outbox_dead_letter") != "0":
        raise SystemExit("Outbox contains dead-letter events.")
    if reliability.get("jobs_dead_letter") != "0":
        raise SystemExit("Background jobs contain dead-letter items.")

    print("Live API release probe passed.")
    print(json.dumps(release, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
