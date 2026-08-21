from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []

for app in ["customer_app", "chef_app", "driver_app"]:
    base = ROOT / "apps" / app

    package = json.loads((base / "package.json").read_text(encoding="utf-8"))
    if "@sentry/react-native" not in package.get("dependencies", {}):
        errors.append(f"{app}: @sentry/react-native missing")

    for rel in [
        "src/observability/sentry.ts",
        "metro.config.js",
        "app/diagnostics.tsx",
        "sentry.properties.example",
    ]:
        if not (base / rel).exists():
            errors.append(f"{app}: missing {rel}")

    layout = (base / "app/_layout.tsx").read_text(encoding="utf-8")
    if 'observability/sentry' not in layout:
        errors.append(f"{app}: Sentry is not initialized before root layout")

    app_json = json.loads((base / "app.json").read_text(encoding="utf-8"))
    plugins = app_json.get("expo", {}).get("plugins", [])
    if not any(
        x == "@sentry/react-native/expo"
        or (isinstance(x, list) and x and x[0] == "@sentry/react-native/expo")
        for x in plugins
    ):
        errors.append(f"{app}: Sentry Expo plugin missing")

    eas = json.loads((base / "eas.json").read_text(encoding="utf-8"))
    normal = eas.get("build", {}).get("pilot", {}).get("env", {})
    diag = eas.get("build", {}).get("pilot-diagnostics", {}).get("env", {})
    prod = eas.get("build", {}).get("production", {}).get("env", {})

    if normal.get("EXPO_PUBLIC_BAYTNA_ENABLE_DIAGNOSTICS") != "false":
        errors.append(f"{app}: normal pilot diagnostics must be disabled")
    if diag.get("EXPO_PUBLIC_BAYTNA_ENABLE_DIAGNOSTICS") != "true":
        errors.append(f"{app}: diagnostic build must enable diagnostics")
    if prod.get("EXPO_PUBLIC_BAYTNA_ENABLE_DIAGNOSTICS") != "false":
        errors.append(f"{app}: production diagnostics must be disabled")

admin = ROOT / "apps/admin_dashboard"
package = json.loads((admin / "package.json").read_text(encoding="utf-8"))
if "@sentry/react" not in package.get("dependencies", {}):
    errors.append("admin: @sentry/react missing")
if "@sentry/vite-plugin" not in package.get("devDependencies", {}):
    errors.append("admin: @sentry/vite-plugin missing")

for rel in [
    "src/observability/sentry.ts",
    "src/pages/Diagnostics.tsx",
    "vite.config.ts",
]:
    if not (admin / rel).exists():
        errors.append(f"admin: missing {rel}")

main = (admin / "src/main.tsx").read_text(encoding="utf-8")
if "reactErrorHandler" not in main:
    errors.append("admin: React 19 error hooks are not wired")

vite = (admin / "vite.config.ts").read_text(encoding="utf-8")
if "filesToDeleteAfterUpload" not in vite:
    errors.append("admin: source maps are not configured for post-upload removal")

if errors:
    raise SystemExit(
        "Crash reporting verification failed:\n- "
        + "\n- ".join(errors)
    )

print("Crash reporting static verification passed.")
