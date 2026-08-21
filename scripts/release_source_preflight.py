from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.50.0"

errors: list[str] = []

def require(path: str) -> Path:
    p = ROOT / path
    if not p.exists():
        errors.append(f"missing: {path}")
    return p

# Backend release alignment.
pyproject = require("backend/pyproject.toml")
main = require("backend/app/main.py")
health = require("backend/app/modules/health/router.py")

if pyproject.exists() and f'version = "{VERSION}"' not in pyproject.read_text(encoding="utf-8"):
    errors.append("backend pyproject version mismatch")
if main.exists() and f'version="{VERSION}"' not in main.read_text(encoding="utf-8"):
    errors.append("FastAPI version mismatch")
if health.exists() and '"/health/release"' not in health.read_text(encoding="utf-8"):
    errors.append("release health endpoint missing")

# Mobile release/build/crash config.
for app in ["customer_app", "chef_app", "driver_app"]:
    base = ROOT / "apps" / app
    for rel in [
        "package.json",
        "app.json",
        "app.config.js",
        "eas.json",
        "metro.config.js",
        "sentry.properties.example",
        "src/observability/sentry.ts",
    ]:
        require(f"apps/{app}/{rel}")

    package_path = base / "package.json"
    if package_path.exists():
        package = json.loads(package_path.read_text(encoding="utf-8"))
        if package.get("version") != VERSION:
            errors.append(f"{app}: package version mismatch")
        if "@sentry/react-native" not in package.get("dependencies", {}):
            errors.append(f"{app}: Sentry React Native dependency missing")

    eas_path = base / "eas.json"
    if eas_path.exists():
        eas = json.loads(eas_path.read_text(encoding="utf-8"))
        if eas.get("build", {}).get("pilot", {}).get("environment") != "preview":
            errors.append(f"{app}: pilot EAS environment must be preview")
        if eas.get("build", {}).get("production", {}).get("environment") != "production":
            errors.append(f"{app}: production EAS environment mismatch")

# Admin release/crash/deployment config.
for rel in [
    "apps/admin_dashboard/package.json",
    "apps/admin_dashboard/vite.config.ts",
    "apps/admin_dashboard/src/observability/sentry.ts",
    "apps/admin_dashboard/Dockerfile",
    "deployment/pilot/docker-compose.frontends.yml",
    "deployment/pilot/release-evidence.example.json",
]:
    require(rel)

admin_package = ROOT / "apps/admin_dashboard/package.json"
if admin_package.exists():
    package = json.loads(admin_package.read_text(encoding="utf-8"))
    if package.get("version") != VERSION:
        errors.append("admin dashboard version mismatch")
    if "@sentry/react" not in package.get("dependencies", {}):
        errors.append("admin Sentry dependency missing")
    if "@sentry/vite-plugin" not in package.get("devDependencies", {}):
        errors.append("admin Sentry Vite plugin missing")

# Prevent obvious real secrets/credentials from being committed into source files.
secret_patterns = [
    re.compile(r"(?i)(sentry_auth_token\s*=\s*)(?!REPLACE|$)(\S{20,})"),
    re.compile(r"(?i)(twilio_auth_token\s*=\s*)(?!REPLACE|$)(\S{20,})"),
    re.compile(r"(?i)(paymob_secret_key\s*=\s*)(?!REPLACE|$)(\S{20,})"),
]
for candidate in [
    ROOT / ".env.pilot.example",
    ROOT / "deployment/pilot/.env.frontends.example",
]:
    if not candidate.exists():
        continue
    text = candidate.read_text(encoding="utf-8", errors="ignore")
    for pattern in secret_patterns:
        if pattern.search(text):
            errors.append(f"possible committed secret in {candidate.relative_to(ROOT)}")


pilot_env = ROOT / ".env.pilot.example"
if pilot_env.exists():
    text = pilot_env.read_text(encoding="utf-8")
    if "BAYTNA_DELIVERY_PROMISE_REQUIRED=true" not in text:
        errors.append(
            "pilot env must require immutable promised delivery windows"
        )
    if "BAYTNA_DELIVERY_PROMISE_TIMEZONE=Africa/Cairo" not in text:
        errors.append("pilot delivery promise timezone is not configured")

if not (ROOT / "scripts/pilot_delivery_timing_evidence.py").exists():
    errors.append("pilot delivery timing evidence collector is missing")

if not (ROOT / "scripts/pilot_economics_evidence.py").exists():
    errors.append("pilot economics evidence collector is missing")

if pilot_env.exists():
    text = pilot_env.read_text(encoding="utf-8")
    if "BAYTNA_EXPANSION_ROLLOUT_REQUIRED=true" not in text:
        errors.append("pilot must require controlled expansion rollout")
    if "BAYTNA_EXPANSION_REQUIRED_BUDGET_CATEGORIES=" not in text:
        errors.append("pilot expansion budget categories are missing")

for required in [
    "backend/alembic/versions/0022_sprint47_financial_reconciliation_rollout.py",
    "backend/app/modules/financial_automation/service.py",
    "scripts/pilot_financial_automation_evidence.py",
]:
    if not (ROOT / required).exists():
        errors.append(f"Sprint 47 financial automation file missing: {required}")

if pilot_env.exists():
    text = pilot_env.read_text(encoding="utf-8")
    for required_line in [
        "BAYTNA_TRAFFIC_REQUIRE_DELIVERY_ADDRESS_FOR_CHECKOUT=true",
        "BAYTNA_VENDOR_ACCOUNTING_REQUIRE_DUAL_CONTROL=true",
        "BAYTNA_VENDOR_ACCOUNTING_REQUIRE_CLOSED_SETTLEMENTS_FOR_ROLLOUT=true",
    ]:
        if required_line not in text:
            errors.append(f"pilot Sprint 48 policy missing: {required_line}")

for required in [
    "backend/alembic/versions/0023_sprint48_launch_traffic_vendor_accounting.py",
    "backend/app/modules/launch_governance/service.py",
    "backend/app/modules/vendor_accounting/service.py",
    "apps/admin_dashboard/src/pages/TrafficGovernance.tsx",
    "apps/admin_dashboard/src/pages/VendorAccounting.tsx",
    "scripts/pilot_launch_governance_evidence.py",
    "scripts/verify_sprint48_contract.py",
    "scripts/verify_sprint48_static.py",
]:
    if not (ROOT / required).exists():
        errors.append(f"Sprint 48 launch governance file missing: {required}")

if pilot_env.exists():
    text = pilot_env.read_text(encoding="utf-8")
    for required_line in [
        "BAYTNA_LAUNCH_COMMAND_REQUIRED=true",
        "BAYTNA_LAUNCH_COMMAND_REQUIRE_DUAL_CONTROL=true",
        "BAYTNA_LAUNCH_EVIDENCE_REQUIRE_NO_ACTIVE_OVERRIDES=true",
    ]:
        if required_line not in text:
            errors.append(f"pilot Sprint 49 policy missing: {required_line}")

for required in [
    "backend/alembic/versions/0024_sprint49_launch_command_center.py",
    "backend/app/modules/launch_command/service.py",
    "backend/app/modules/launch_command/router.py",
    "apps/admin_dashboard/src/pages/LaunchCommand.tsx",
]:
    if not (ROOT / required).exists():
        errors.append(f"Sprint 49 launch command file missing: {required}")

for required in [
    "scripts/pilot_launch_command_evidence.py",
    "scripts/verify_sprint49_contract.py",
    "scripts/verify_sprint49_static.py",
    "scripts/verify_sprint49_structure.py",
]:
    if not (ROOT / required).exists():
        errors.append(f"Sprint 49 command evidence file missing: {required}")


# Sprint 50 — SLO automation and post-launch stabilization.
if pilot_env.exists():
    text = pilot_env.read_text(encoding="utf-8")
    for required_line in [
        "BAYTNA_SLO_AUTO_PAUSE_DEFAULT_ENABLED=true",
        "BAYTNA_LAUNCH_DAILY_CLOSE_CADENCE_ENABLED=true",
    ]:
        if required_line not in text:
            errors.append(f"pilot Sprint 50 policy missing: {required_line}")

production_env = ROOT / ".env.production.example"
if production_env.exists():
    text = production_env.read_text(encoding="utf-8")
    for required_line in [
        "BAYTNA_SLO_AUTO_PAUSE_DEFAULT_ENABLED=true",
        "BAYTNA_LAUNCH_DAILY_CLOSE_CADENCE_ENABLED=true",
    ]:
        if required_line not in text:
            errors.append(f"production Sprint 50 policy missing: {required_line}")

for required in [
    "backend/alembic/versions/0025_sprint50_post_launch_stabilization.py",
    "backend/app/modules/post_launch/service.py",
    "backend/app/modules/post_launch/router.py",
    "apps/admin_dashboard/src/pages/PostLaunch.tsx",
    "scripts/pilot_post_launch_stabilization_evidence.py",
    "scripts/expansion_review_gate.py",
    "scripts/verify_sprint50_contract.py",
    "scripts/verify_sprint50_static.py",
    "scripts/verify_sprint50_structure.py",
]:
    if not (ROOT / required).exists():
        errors.append(f"Sprint 50 stabilization file missing: {required}")

for required in [
    "backend/alembic/versions/0020_sprint45_pilot_stability.py",
    "backend/app/modules/pilot_stability/service.py",
    "scripts/pilot_scale_evidence.py",
    "scripts/pilot_scale_gate.py",
]:
    if not (ROOT / required).exists():
        errors.append(f"Sprint 45 pilot stability file missing: {required}")

if errors:
    raise SystemExit("Release source preflight failed:\n- " + "\n- ".join(errors))

print("Release source preflight passed.")
