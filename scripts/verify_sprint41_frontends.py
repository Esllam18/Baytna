from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
apps=["customer_app","chef_app","driver_app"]

for app in apps:
    base=ROOT/"apps"/app
    required=[
        "package.json",
        "app.json",
        "eas.json",
        "src/notifications/PushBootstrap.tsx",
    ]
    for rel in required:
        assert (base/rel).exists(), f"{app}: missing {rel}"

    package=json.loads((base/"package.json").read_text(encoding="utf-8"))
    assert package["version"]=="0.50.0"
    assert "expo-notifications" in package["dependencies"]
    assert "expo-device" in package["dependencies"]

customer=(ROOT/"apps/customer_app/app/account/support/new.tsx").read_text(encoding="utf-8")
reply=(ROOT/"apps/customer_app/app/account/support/[ticketId].tsx").read_text(encoding="utf-8")
chef=(ROOT/"apps/chef_app/app/signature-menu.tsx").read_text(encoding="utf-8")
driver=(ROOT/"apps/driver_app/app/missions/[missionId]/proof.tsx").read_text(encoding="utf-8")

assert "uploadSupportAttachment" in customer
assert "attachment_ids" in (ROOT/"apps/customer_app/src/api/customer.ts").read_text(encoding="utf-8")
assert "uploadSupportAttachment" in reply
assert "uploadDishImage" in chef
assert "setDishMedia" in (ROOT/"apps/chef_app/src/api/chef.ts").read_text(encoding="utf-8")
assert "uploadDeliveryProof" in driver

admin=ROOT/"apps/admin_dashboard"
for rel in ["Dockerfile","nginx.conf"]:
    assert (admin/rel).exists()

for rel in [
    "deployment/pilot/docker-compose.frontends.yml",
    "deployment/pilot/FRONTEND_DEPLOYMENT.md",
    "scripts/frontend_preflight.py",
    "scripts/staging_cross_app_e2e.py",
    ".github/workflows/frontend-validation.yml",
]:
    assert (ROOT/rel).exists(), rel

print("Sprint 41 frontend/media/deployment static verification passed.")
