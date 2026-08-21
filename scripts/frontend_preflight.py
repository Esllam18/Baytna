from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MOBILE = {
    "customer_app": "com.baytna.customer",
    "chef_app": "com.baytna.chef",
    "driver_app": "com.baytna.driver",
}

errors: list[str] = []

for app, package_id in MOBILE.items():
    base = ROOT / "apps" / app
    for required in [
        "package.json",
        "app.json",
        "eas.json",
        ".env.example",
        "src/notifications/PushBootstrap.tsx",
    ]:
        if not (base / required).exists():
            errors.append(f"{app}: missing {required}")

    package = json.loads((base / "package.json").read_text(encoding="utf-8"))
    app_json = json.loads((base / "app.json").read_text(encoding="utf-8"))
    eas = json.loads((base / "eas.json").read_text(encoding="utf-8"))

    if package.get("version") != "0.50.0":
        errors.append(f"{app}: package version is not 0.50.0")
    if "expo-notifications" not in package.get("dependencies", {}):
        errors.append(f"{app}: expo-notifications missing")
    if app_json.get("expo", {}).get("android", {}).get("package") != package_id:
        errors.append(f"{app}: android package mismatch")
    if eas.get("build", {}).get("pilot", {}).get("distribution") != "internal":
        errors.append(f"{app}: pilot EAS build is not internal")

admin = ROOT / "apps" / "admin_dashboard"
for required in [
    "Dockerfile",
    "nginx.conf",
    "package.json",
    "src/App.tsx",
]:
    if not (admin / required).exists():
        errors.append(f"admin_dashboard: missing {required}")

for required in [
    "deployment/pilot/docker-compose.frontends.yml",
    "deployment/pilot/FRONTEND_DEPLOYMENT.md",
    ".github/workflows/frontend-validation.yml",
]:
    if not (ROOT / required).exists():
        errors.append(f"missing {required}")

if errors:
    raise SystemExit(
        "Sprint 41 frontend preflight failed:\n- " + "\n- ".join(errors)
    )

print("Frontend deployment preflight passed.")
