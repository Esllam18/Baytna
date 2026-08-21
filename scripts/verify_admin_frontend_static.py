from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
    "apps/admin_dashboard/package.json",
    "apps/admin_dashboard/index.html",
    "apps/admin_dashboard/src/App.tsx",
    "apps/admin_dashboard/src/main.tsx",
    "apps/admin_dashboard/src/styles.css",
    "apps/admin_dashboard/src/pages/Login.tsx",
    "apps/admin_dashboard/src/pages/Dashboard.tsx",
    "apps/admin_dashboard/src/pages/Orders.tsx",
    "apps/admin_dashboard/src/pages/OrderDetail.tsx",
    "apps/admin_dashboard/src/pages/Chefs.tsx",
    "apps/admin_dashboard/src/pages/ChefDetail.tsx",
    "apps/admin_dashboard/src/pages/Drivers.tsx",
    "apps/admin_dashboard/src/pages/DriverDetail.tsx",
    "apps/admin_dashboard/src/pages/Support.tsx",
    "apps/admin_dashboard/src/pages/TicketDetail.tsx",
    "apps/admin_dashboard/src/pages/Finance.tsx",
    "apps/admin_dashboard/src/pages/Audit.tsx",
    "apps/admin_dashboard/src/api/admin.ts",
    "apps/admin_dashboard/src/auth/AuthProvider.tsx",
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing:
    raise SystemExit("Missing Sprint 40 Admin files: "+", ".join(missing))

api=(ROOT/"apps/admin_dashboard/src/api/admin.ts").read_text(encoding="utf-8")
app=(ROOT/"apps/admin_dashboard/src/App.tsx").read_text(encoding="utf-8")
order=(ROOT/"apps/admin_dashboard/src/pages/OrderDetail.tsx").read_text(encoding="utf-8")
support=(ROOT/"apps/admin_dashboard/src/pages/TicketDetail.tsx").read_text(encoding="utf-8")
finance=(ROOT/"apps/admin_dashboard/src/pages/Finance.tsx").read_text(encoding="utf-8")

for symbol in [
    "profile","overview","orders","order","addOrderNote","createRefund",
    "chefs","chef","updateChefStatus","drivers","driver",
    "supportSummary","tickets","ticket","assignTicket","messageTicket",
    "updateTicketStatus","finance","daily","funnel","retention","audit",
]:
    assert symbol in api

assert 'r.user.role!=="admin"' in api
for route in ["/orders", "/chefs", "/drivers", "/support", "/finance", "/audit"]:
    assert route in app
assert "createRefund" in order
assert "addOrderNote" in order
assert "messageTicket" in support and "updateTicketStatus" in support
assert "funnel" in finance and "retention" in finance

print("Sprint 40 Admin frontend static verification passed.")
