# Sprint 46 — Definition of Done

## Persistence
- [x] `economics_cost_entries`.
- [x] `expansion_zones`.
- [x] `expansion_assessments`.
- [x] Migration `0021_sprint46`.
- [x] Cost-entry program index.
- [x] Cost-entry order/type index.
- [x] Durable expansion assessment history.

## Cost Ledger
- [x] Chef payout.
- [x] Delivery partner cost.
- [x] Payment processing cost.
- [x] Packaging.
- [x] Refund fee.
- [x] Customer recovery.
- [x] Other variable cost.
- [x] Fixed operations.
- [x] Manual/provider/import source.
- [x] External reference.
- [x] Verification workflow.
- [x] Audit trail.
- [x] Duplicate external-reference protection.

## Economics Integrity
- [x] Successful-payment revenue source.
- [x] Successful-refund subtraction.
- [x] Revenue coverage.
- [x] Required order-cost policy.
- [x] Cost coverage.
- [x] Unverified costs block evaluation.
- [x] Net Collected must be positive.
- [x] Missing costs are not treated as zero.
- [x] Discounts are not double-counted automatically.

## Contribution / Profitability
- [x] Variable cost total.
- [x] Fixed cost total.
- [x] Contribution.
- [x] Contribution margin.
- [x] Contribution/order.
- [x] Operational profit.
- [x] Operational profit margin.
- [x] Backend profitability pass/fail/unevaluable.

## Pilot Scale Gate
- [x] Removed manual operational-profit evidence dependency.
- [x] `profitability_calculated_from_backend = true`.
- [x] QA Exit remains required.
- [x] Operations Sign-off remains required.
- [x] Negative backend profit blocks scale.
- [x] Incomplete economics blocks scale.

## Expansion Zones
- [x] Candidate zone.
- [x] Source pilot.
- [x] Minimum delivered-order target.
- [x] Contribution-margin target.
- [x] Operational-profit target.
- [x] Persisted assessment.
- [x] Ready/blocked decision.
- [x] Approve.
- [x] Launch readiness re-check.
- [x] Live.
- [x] Pause.
- [x] Audit history.

## Admin UI
- [x] `/economics`.
- [x] Backend profitability banner.
- [x] Coverage metrics.
- [x] Contribution metrics.
- [x] Operational profit.
- [x] Cost ledger.
- [x] Verify cost.
- [x] Cost breakdown.
- [x] Expansion candidate form.
- [x] Assessment.
- [x] Approve/Launch/Pause.
- [x] Pilot UI no longer requests manual profit evidence.

## Release Evidence
- [x] `pilot_scale_evidence.py` includes economics.
- [x] `pilot_scale_gate.py` requires backend economics.
- [x] Live `pilot_economics_evidence.py`.
- [x] Main go-live gate requires economics evidence.
- [x] Fail-closed test.

## Verification
- [x] 331 backend tests.
- [x] Python compile.
- [x] OpenAPI 198 paths.
- [x] Generated TS routes 198.
- [x] Contract guard.
- [x] Static guard.
- [x] Structure guard.
- [x] Release preflight.
- [x] Frontend preflight.
- [x] Crash-reporting guard.
- [x] 166 frontend TypeScript files / 0 syntax diagnostics.
- [x] Alembic chain through 0021.
- [x] Worker 10/10.
- [x] Scale gate backend-profit positive path.
- [x] Incomplete main go-live evidence blocks with exit code 2.

## Not Claimed
- [ ] Live accounting imports.
- [ ] Live courier settlement imports.
- [ ] Live Paymob fee settlement import.
- [ ] Real positive pilot operational profit.
- [ ] Real expansion zone approval.
- [ ] Final go-live authorization.
