# Sprint 45 — Definition of Done

## Persistence
- [x] `pilot_programs`.
- [x] `pilot_weekly_snapshots`.
- [x] `pilot_qa_evidence`.
- [x] Migration `0020_sprint45`.
- [x] Program status constraints.
- [x] Minimum stability requirement cannot be below 8 weeks.
- [x] Unique program/week snapshot.
- [x] Unique program/evidence type.

## Pilot lifecycle
- [x] Create program.
- [x] List/read programs.
- [x] Activate program.
- [x] Only one active pilot.
- [x] Complete program.
- [x] Audit create/activate/complete.

## Weekly stability
- [x] Seven-day sequential pilot weeks.
- [x] Partial final week does not count toward stability.
- [x] Orders/delivered/cancelled.
- [x] Cancellation rate.
- [x] Unique customers.
- [x] Repeat-customer rate.
- [x] Rating/review count.
- [x] True On-Time rate.
- [x] Promise coverage.
- [x] Late deliveries.
- [x] GMV.
- [x] Captured/refunded/net collected.
- [x] Support count.
- [x] Refund rate.
- [x] Per-KPI gates.
- [x] Week evaluability.
- [x] Weekly PASS/FAIL.
- [x] Current consecutive streak.
- [x] Maximum historical streak.
- [x] Strict 8-week stability gate.

## Cohorts
- [x] First delivered order defines acquisition.
- [x] Existing customers excluded from acquired cohort.
- [x] W0..W7 retention matrix.
- [x] Weighted W1 retention.
- [x] Weighted W4 retention.

## QA evidence
- [x] Arbitrary evidence key support.
- [x] Pending/passed/failed/not-applicable.
- [x] Passed evidence requires reference.
- [x] Admin verifier identity.
- [x] Observed timestamp.
- [x] Audit trail.
- [x] Mandatory scale evidence: operational profit.
- [x] Mandatory scale evidence: QA exit.
- [x] Mandatory scale evidence: operations sign-off.

## Post-pilot report
- [x] Orders/delivery/cancellation.
- [x] GMV/cash/refunds/AOV.
- [x] Repeat rate.
- [x] Rating.
- [x] True On-Time + promise coverage.
- [x] Support per 100 orders.
- [x] Refund rate.
- [x] Cohort retention.
- [x] Stability result.
- [x] Evidence status.
- [x] Active Critical Incident blocker.
- [x] Open Payment Reconciliation blocker.
- [x] Scale blockers.
- [x] `scale_ready`.
- [x] Backend explicitly does not calculate operational profit.

## Worker
- [x] Daily `pilot.snapshot` maintenance job.
- [x] Daily idempotency key.
- [x] Active pilot refresh.
- [x] Existing 9 maintenance jobs preserved.

## Admin Dashboard
- [x] `/pilot` route.
- [x] Sidebar navigation.
- [x] Pilot creation.
- [x] Lifecycle controls.
- [x] Weekly stability table.
- [x] 8-week stability banner.
- [x] Cohort matrix.
- [x] QA evidence controls.
- [x] Post-pilot analytics.
- [x] Scale blockers.
- [x] Responsive layout.

## Scale evidence
- [x] Live HTTPS evidence collector.
- [x] Strict post-pilot scale gate.
- [x] Scale gate cannot accept stability below 8 weeks.
- [x] Evidence references mandatory.
- [x] Fail-closed example verified.
- [x] Synthetic positive gate path verified.
- [x] Separate from pre-pilot Go-Live gate.

## Verification
- [x] 324 collected backend tests passed across 4 isolated batches.
- [x] Python compile.
- [x] OpenAPI 189 paths.
- [x] generated TS route registry 189.
- [x] Sprint 45 API contract guard.
- [x] Sprint 45 static guard.
- [x] Sprint 45 structure guard.
- [x] Customer/Chef/Driver/Admin inherited contracts.
- [x] Release source preflight.
- [x] Frontend preflight.
- [x] Crash reporting static guard.
- [x] 165 TypeScript files / 0 syntax diagnostics.
- [x] Alembic chain to `0020_sprint45`.
- [x] Worker 10/10 on clean first tick.
- [x] Go-Live incomplete evidence blocks.
- [x] Scale incomplete evidence blocks.
- [x] Scale positive-path gate fixture passes.

## Not claimed
- [ ] Real 8-week pilot stability.
- [ ] Real positive operational profit.
- [ ] Real scale authorization.
- [ ] Live provider/device evidence not already independently proven.
