# Sprint 48 — Definition of Done

## Traffic Governance
- [x] Durable Zone Traffic Policy.
- [x] Daily Zone order cap.
- [x] Hourly Zone intake cap.
- [x] Chef/day cap.
- [x] Stable Customer rollout bucket.
- [x] Canary/Limited/Full audience enforcement.
- [x] Paused Zone rejection.
- [x] Non-live rollout rejection.
- [x] Durable accepted admission event.
- [x] Durable rejected admission event.
- [x] Rejection reason.
- [x] Cap utilization-before snapshot.
- [x] Admin policy APIs.
- [x] Admin cap PATCH API.
- [x] PostgreSQL-targeted policy row lock.

## Checkout
- [x] `delivery_address_id` on CreateOrderRequest.
- [x] Selected address validated as customer-owned.
- [x] Address used by admission before Order materialization.
- [x] Address snapshotted atomically into Order.
- [x] Customer app sends selected address in POST /orders.
- [x] Old two-step address patch removed from checkout.
- [x] Clear `expansion_capacity_unavailable` UI.
- [x] Delivery address required in Pilot/Production policy.

## Bypass Protection
- [x] Existing Order address change rechecks Zone admission.
- [x] Existing Order excluded from own Chef-cap count.
- [x] Special Order checkout rechecks Zone admission.
- [x] No address-switch bypass.

## Expansion Monitoring
- [x] Durable monitoring snapshots.
- [x] Daily utilization.
- [x] Hourly utilization.
- [x] Last-hour attempt/rejection rate.
- [x] Zone-area open Chef count.
- [x] Available driver count.
- [x] Top-Chef utilization.
- [x] Green/Amber/Red health.
- [x] Explicit blockers.
- [x] `expansion.monitor` worker job.
- [x] Worker maintenance total = 12.
- [x] Control Room traffic incident.
- [x] Red → Critical.
- [x] Amber → High.

## Vendor Import Review
- [x] Pending/Assigned/Approved/Rejected states.
- [x] Reviewer assignment.
- [x] Review note.
- [x] Risk flags.
- [x] Foreign-currency flag.
- [x] Unscoped Pilot flag.
- [x] Unscoped Area flag.
- [x] High-value flag.
- [x] Fixed-operations flag.
- [x] Provider-adjustment flag.
- [x] Unallocated variable-cost flag.
- [x] Pilot/Production maker-checker.
- [x] Creator cannot approve own import.
- [x] Strict Apply requires approved review.

## Settlement Operations
- [x] Open/Review/Closed/Reopened states.
- [x] Assignment.
- [x] Reconciled → Review.
- [x] Blocked → Open.
- [x] Close only after all rows matched.
- [x] Close blocks open Payment Reconciliation Issues.
- [x] Maker-checker close.
- [x] Close note.
- [x] Reopen with audit note.
- [x] Strict rollout can require all source settlements Closed.

## Production Safety
- [x] Expansion rollout required.
- [x] Delivery address required at checkout.
- [x] Vendor accounting dual control required.
- [x] Closed settlements required for rollout.
- [x] Production Settings validation enforces all four.
- [x] Pilot env example enforces all four.
- [x] Production env example enforces all four.

## Admin
- [x] `/traffic-governance`.
- [x] Zone tabs.
- [x] Traffic cap editor.
- [x] Rollout policy editor.
- [x] Monitoring refresh/history.
- [x] Admission ledger.
- [x] `/vendor-accounting`.
- [x] Import review queue.
- [x] Risk flags.
- [x] Approve/Reject.
- [x] Settlement close/reopen queue.

## Evidence / Release
- [x] Live launch-governance evidence script.
- [x] Release `0.48.0`.
- [x] Migration `0023_sprint48`.
- [x] New Go-Live booleans.
- [x] New Go-Live artifact references.
- [x] Incomplete evidence remains fail-closed.

## Verification
- [x] 359 backend tests.
- [x] Sprint 48 module: 16 tests.
- [x] Python compile.
- [x] OpenAPI: 228 paths.
- [x] TS route registry: 228.
- [x] Sprint 48 contract guard.
- [x] Sprint 48 static guard.
- [x] Sprint 48 structure guard.
- [x] Release source preflight.
- [x] Frontend preflight.
- [x] Crash reporting guard.
- [x] 169 TypeScript files / 0 syntax diagnostics.
- [x] Alembic full chain.
- [x] Worker 12/12.
- [x] Existing profitability Scale Gate.
- [x] Go-Live example blocked / exit 2.

## Not Claimed
- [ ] Live PostgreSQL concurrency.
- [ ] Live Zone-cap rejection.
- [ ] Live Canary traffic.
- [ ] Real maker-checker finance approval.
- [ ] Real settlement close.
- [ ] Final Go-Live PASS.
