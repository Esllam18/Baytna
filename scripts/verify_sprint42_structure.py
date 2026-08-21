from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required = [
    "backend/tests/test_sprint42_release_hardening.py",
    "scripts/release_source_preflight.py",
    "scripts/live_release_probe.py",
    "scripts/go_live_gate.py",
    "scripts/verify_crash_reporting_static.py",
    "deployment/pilot/release-evidence.example.json",
    "docs/CRASH_REPORTING.md",
    "docs/REAL_DEVICE_BUILD_RUNBOOK.md",
    "docs/LIVE_STAGING_RUNBOOK.md",
    "docs/ROLLBACK_RUNBOOK.md",
    "docs/GO_LIVE_CHECKLIST.md",
    ".github/workflows/pilot-release-gates.yml",
    ".github/workflows/pilot-mobile-builds.yml",
]

missing = [x for x in required if not (ROOT / x).exists()]
if missing:
    raise SystemExit(
        "Missing Sprint 42 files: " + ", ".join(missing)
    )

print("Sprint 42 structure verified.")
