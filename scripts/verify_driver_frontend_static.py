from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
    "apps/driver_app/package.json",
    "apps/driver_app/app.json",
    "apps/driver_app/app/auth/login.tsx",
    "apps/driver_app/app/auth/verify.tsx",
    "apps/driver_app/app/home.tsx",
    "apps/driver_app/app/missions/index.tsx",
    "apps/driver_app/app/missions/[missionId].tsx",
    "apps/driver_app/app/missions/[missionId]/proof.tsx",
    "apps/driver_app/app/history.tsx",
    "apps/driver_app/src/api/driver.ts",
    "apps/driver_app/src/api/http.ts",
    "apps/driver_app/src/auth/AuthProvider.tsx",
    "apps/driver_app/src/hooks/useDriverOps.ts",
    "apps/driver_app/src/media/uploadDeliveryProof.ts",
    "apps/driver_app/src/navigation/maps.ts",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    raise SystemExit("Missing Sprint 39 Driver App files: "+", ".join(missing))

api=(ROOT/"apps/driver_app/src/api/driver.ts").read_text(encoding="utf-8")
home=(ROOT/"apps/driver_app/app/home.tsx").read_text(encoding="utf-8")
missions=(ROOT/"apps/driver_app/app/missions/[missionId].tsx").read_text(encoding="utf-8")
proof=(ROOT/"apps/driver_app/app/missions/[missionId]/proof.tsx").read_text(encoding="utf-8")
upload=(ROOT/"apps/driver_app/src/media/uploadDeliveryProof.ts").read_text(encoding="utf-8")

for symbol in [
    "setAvailability",
    "availableMissions",
    "availableMission",
    "acceptMission",
    "arrivePickup",
    "confirmPickup",
    "startDelivery",
    "deliver",
    "reportIssue",
    "resumeMission",
    "createMediaUpload",
    "completeMedia",
]:
    assert symbol in api

assert 'response.user.role !== "driver"' in api
assert "setAvailability" in home
assert "navigateToPickup" in missions
assert "navigateToDropoff" in missions
assert "arrivePickup" in missions
assert "confirmPickup" in missions
assert "startDelivery" in missions
assert "reportIssue" in missions
assert "resumeMission" in missions
assert "expo-image-picker" in proof
assert "uploadDeliveryProof" in proof
assert 'purpose:"delivery_proof"' in upload
assert 'visibility:"private"' in upload

print("Sprint 39 Driver frontend static verification passed.")
