from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
    "backend/app/modules/notification_delivery/universal_router.py",
    "backend/tests/test_sprint41_cross_app_pilot.py",
    "apps/customer_app/src/notifications/PushBootstrap.tsx",
    "apps/customer_app/src/media/uploadSupportAttachment.ts",
    "apps/chef_app/src/notifications/PushBootstrap.tsx",
    "apps/chef_app/src/media/uploadDishImage.ts",
    "apps/driver_app/src/notifications/PushBootstrap.tsx",
    "apps/admin_dashboard/Dockerfile",
    "scripts/staging_cross_app_e2e.py",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    raise SystemExit("Missing Sprint 41 files: "+", ".join(missing))
print("Sprint 41 structure verified.")
