from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
 "apps/chef_app/package.json","apps/chef_app/app.json",
 "apps/chef_app/app/auth/login.tsx","apps/chef_app/app/auth/verify.tsx",
 "apps/chef_app/app/home.tsx","apps/chef_app/app/kitchen.tsx",
 "apps/chef_app/app/signature-menu.tsx",
 "apps/chef_app/app/orders/index.tsx","apps/chef_app/app/orders/[orderId].tsx",
 "apps/chef_app/app/special-orders/index.tsx","apps/chef_app/app/special-orders/[specialOrderId].tsx",
 "apps/chef_app/app/schedule.tsx",
 "apps/chef_app/src/api/chef.ts","apps/chef_app/src/api/http.ts",
 "apps/chef_app/src/auth/AuthProvider.tsx","apps/chef_app/src/hooks/useChefOps.ts",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing: raise SystemExit("Missing Sprint 38 Chef App files: "+", ".join(missing))

api=(ROOT/"apps/chef_app/src/api/chef.ts").read_text(encoding="utf-8")
home=(ROOT/"apps/chef_app/app/home.tsx").read_text(encoding="utf-8")
kitchen=(ROOT/"apps/chef_app/app/kitchen.tsx").read_text(encoding="utf-8")
order=(ROOT/"apps/chef_app/app/orders/[orderId].tsx").read_text(encoding="utf-8")
special=(ROOT/"apps/chef_app/app/special-orders/[specialOrderId].tsx").read_text(encoding="utf-8")
auth=(ROOT/"apps/chef_app/src/api/chef.ts").read_text(encoding="utf-8")

for symbol in [
 "dashboard","signatureMenu","replaceTodayMenu","openKitchen","closeKitchen",
 "orders","acceptOrder","rejectOrder","startPreparing","startPackaging","readyForPickup",
 "specialOrders","acceptSpecialOrder","counterSpecialOrder","rejectSpecialOrder",
 "weeklySchedule","saveWeeklySchedule"
]:
    assert symbol in api

assert 'response.user.role !== "chef"' in auth
assert 'router.push("/kitchen")' in home
assert "replaceTodayMenu" in kitchen and "openKitchen" in kitchen
assert "startPreparing" in order and "startPackaging" in order and "readyForPickup" in order
assert "acceptSpecialOrder" in special and "counterSpecialOrder" in special and "rejectSpecialOrder" in special

print("Sprint 38 Chef frontend static verification passed.")
