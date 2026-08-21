# Sprint 49 — Definition of Done

## Launch Command Session
- [x] Durable sessions.
- [x] Pilot Program binding.
- [x] Expansion Zone binding.
- [x] Launch Date.
- [x] Incident Commander.
- [x] Finance Admin.
- [x] Operations Admin.
- [x] Planned.
- [x] Active.
- [x] Paused.
- [x] Completed.
- [x] Aborted.
- [x] One open session per Zone.
- [x] Durable command timeline.

## Runbook
- [x] 12 default required steps.
- [x] Ordered sequence.
- [x] Categories.
- [x] Pending.
- [x] Passed.
- [x] Failed.
- [x] Skipped.
- [x] Evidence reference required for Pass.
- [x] Admin actor/time.

## Rollout integration
- [x] Strict Start requires active Command Session.
- [x] Strict Advance requires active Command Session.
- [x] Strict Resume requires active Command Session.
- [x] Emergency Pause remains available.
- [x] Development compatibility retained.

## Traffic Overrides
- [x] Daily cap override.
- [x] Hourly cap override.
- [x] Chef/day cap override.
- [x] Admission stop override.
- [x] Cannot increase traffic.
- [x] Finite expiry.
- [x] Maximum duration.
- [x] Mandatory reason.
- [x] Exact previous-state snapshot.
- [x] Manual Revert.
- [x] Automatic Expiry.
- [x] Exact state restoration.
- [x] One active override/type/Zone.

## Daily Financial Close
- [x] Durable close.
- [x] Service-date scope.
- [x] Delivered Orders.
- [x] Succeeded Payments.
- [x] Refunds.
- [x] Net Collected.
- [x] Verified variable/fixed cost.
- [x] Contribution.
- [x] Operational Profit.
- [x] Revenue Coverage.
- [x] Cost Coverage.
- [x] Unverified-cost blocker.
- [x] Pending-import blocker.
- [x] Unclosed-settlement blocker.
- [x] Payment-reconciliation blocker.
- [x] Ready / Blocked.
- [x] Independent Close.
- [x] SHA-256 close checksum.
- [x] Reopen.
- [x] Overdue monitoring event.

## Rollback Drill
- [x] Tabletop.
- [x] Live controlled.
- [x] Pre-state snapshot.
- [x] Admission disable.
- [x] Recovery timer.
- [x] Exact admission restore.
- [x] Recovery target.
- [x] Independent verifier.
- [x] Evidence reference.
- [x] Passed / Failed.
- [x] Auto-recovery on timeout.
- [x] Aborted auto-recovered drill evidence.

## Evidence Pack
- [x] Durable pack.
- [x] Release identity.
- [x] Migration head.
- [x] Runbook state.
- [x] Traffic state.
- [x] Monitoring state.
- [x] Financial Close.
- [x] Rollback Drill.
- [x] Provider imports.
- [x] Settlement close.
- [x] Critical incidents.
- [x] Active overrides.
- [x] Launch roles.
- [x] Complete / Incomplete.
- [x] Explicit blockers.
- [x] SHA-256 checksum.
- [x] Session Complete requires Complete pack.

## Worker
- [x] `launch.command.maintain`.
- [x] Override expiry.
- [x] Drill auto-recovery.
- [x] Overdue Financial Close event.
- [x] Maintenance count = 13.

## Production
- [x] `BAYTNA_LAUNCH_COMMAND_REQUIRED=true`.
- [x] `BAYTNA_LAUNCH_COMMAND_REQUIRE_DUAL_CONTROL=true`.
- [x] Production Settings fail closed without both.
- [x] Pilot example configured.
- [x] Production example configured.
- [x] No active overrides required for evidence in examples.

## Admin
- [x] `/launch-command`.
- [x] Session creator.
- [x] Session actions.
- [x] Command summary.
- [x] Runbook controls.
- [x] Traffic Override controls.
- [x] Daily Financial Close.
- [x] Rollback Drill.
- [x] Evidence Pack history.
- [x] Command Timeline.

## Live evidence
- [x] HTTPS evidence collector.
- [x] `0.49.0`.
- [x] `0024_sprint49`.
- [x] Go-Live booleans.
- [x] Go-Live artifact references.
- [x] Fail-closed example.

## Verification
- [x] 373 backend tests.
- [x] Sprint 49: 14 tests.
- [x] Python compile.
- [x] Alembic full chain.
- [x] OpenAPI 247.
- [x] Generated TS routes 247.
- [x] Contract guard.
- [x] Static guard.
- [x] Structure guard.
- [x] Release preflight.
- [x] Frontend preflight.
- [x] Crash guard.
- [x] Four frontend static guards.
- [x] 170 TypeScript files / 0 syntax errors.
- [x] Worker 13/13.
- [x] Scale Gate.
- [x] Go-Live blocked / exit 2.

## Not Claimed
- [ ] Real launch session.
- [ ] Real live emergency override.
- [ ] Real Daily Close.
- [ ] Real rollback drill.
- [ ] Real Evidence Pack.
- [ ] Final Go-Live authorization.
