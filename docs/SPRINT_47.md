# Sprint 47 — Definition of Done

## Provider Cost Imports
- [x] Durable import batches.
- [x] Durable import lines.
- [x] Provider/external-reference idempotency.
- [x] SHA-256 evidence checksum.
- [x] Explicit period.
- [x] Optional Pilot Program scope.
- [x] Optional Area scope.
- [x] Source currency.
- [x] Explicit FX to EGP.
- [x] FX reference required for foreign currency.
- [x] Duplicate line-key protection.
- [x] Validate stage.
- [x] Apply stage.
- [x] Applied costs are verified provider costs.
- [x] Audit events.
- [x] Max-line guard.

## Twilio Cost Adapter
- [x] Usage Records request path.
- [x] Date range.
- [x] Category.
- [x] TotalPrice-ready Admin flow.
- [x] Basic Auth from runtime credentials.
- [x] Provider price normalization.
- [x] Currency normalization.
- [x] No guessed FX.
- [x] Creates normal provider-import batch.
- [x] No live account result claimed.

## Paymob Settlement Reconciliation
- [x] Durable settlement batches.
- [x] Durable settlement lines.
- [x] Normalized settlement import.
- [x] Transaction-ledger matching.
- [x] Payment matching.
- [x] Amount match.
- [x] Currency match.
- [x] Refund snapshot match.
- [x] Net settlement arithmetic.
- [x] Final-settled check.
- [x] Pilot Program scope check.
- [x] Duplicate payment-processing cost protection.
- [x] Batch fail-closed.
- [x] Clean batch materializes verified provider fee.
- [x] Blocked batch materializes no fee cost.
- [x] Audit events.

## Automation
- [x] `finance.settlements.reconcile` worker job.
- [x] Rechecks draft settlement batches.
- [x] Rechecks blocked settlement batches.
- [x] Worker maintenance count = 11.
- [x] Blocked settlement → Critical Control Room incident.

## Expansion Budgets
- [x] Durable zone budgets.
- [x] Required category policy.
- [x] Allocate.
- [x] Commit.
- [x] Release.
- [x] Spend.
- [x] Prevent budget overspend.
- [x] Remaining balance.
- [x] Budget readiness summary.
- [x] Audit events.

## Controlled Rollout
- [x] `not_started`.
- [x] `canary`.
- [x] `limited`.
- [x] `full`.
- [x] `paused`.
- [x] Rollout percent.
- [x] Daily order cap.
- [x] Durable rollout events.
- [x] Budget snapshot at transition.
- [x] Readiness assessment at transition.
- [x] Start Canary.
- [x] Advance Canary → Limited.
- [x] Advance Limited → Full.
- [x] Pause.
- [x] Resume.
- [x] Rollout history endpoint.
- [x] Recheck economics/readiness before Start/Advance/Resume.
- [x] Open payment reconciliation blocks rollout.
- [x] Blocked source settlement blocks rollout.

## Pilot / Production Safety
- [x] Controlled rollout required in Pilot example.
- [x] Controlled rollout required in Production example.
- [x] Legacy direct launch blocked when required.
- [x] Development compatibility retained.

## Admin UI
- [x] `/finance-automation`.
- [x] Provider import form.
- [x] Import Validate/Apply.
- [x] Twilio Usage form.
- [x] Settlement form.
- [x] Settlement reconciliation cards.
- [x] Zone budgets.
- [x] Missing budget categories.
- [x] Rollout meter.
- [x] Start Canary.
- [x] Advance Rollout.
- [x] Pause Rollout.
- [x] Resume Rollout.
- [x] Legacy one-click launch removed from primary UI.

## Evidence
- [x] Live financial automation evidence collector.
- [x] Applied provider-import evidence.
- [x] Clean Paymob settlement evidence.
- [x] Budget-ready evidence.
- [x] Controlled rollout event evidence.
- [x] Main Go-Live gate requires Sprint 47 evidence.
- [x] Incomplete evidence fails closed.

## Verification
- [x] 343 backend tests.
- [x] Python compile.
- [x] OpenAPI 213 paths.
- [x] Generated TS routes 213.
- [x] Sprint 47 contract guard.
- [x] Sprint 47 static guard.
- [x] Sprint 47 structure guard.
- [x] Release preflight.
- [x] Frontend preflight.
- [x] Crash reporting guard.
- [x] Four frontend static guards.
- [x] 167 frontend TypeScript files / 0 syntax diagnostics.
- [x] Alembic through `0022_sprint47`.
- [x] Worker 11/11.
- [x] Scale gate.
- [x] Go-Live fail-closed / exit 2.

## Not Claimed
- [ ] Live Twilio Usage cost import.
- [ ] Live courier/chef invoice import.
- [ ] Live Paymob settlement import.
- [ ] Live provider fee accounting.
- [ ] Real zone canary launch.
- [ ] Final go-live authorization.
