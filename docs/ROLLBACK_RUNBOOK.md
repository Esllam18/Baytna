# Sprint 42 — Rollback Runbook

## Principle

Rollback must restore application code without corrupting financial or order state.

Database rollback is not the default incident response.

## API / Worker rollback

1. Stop new deployment rollout.
2. Keep PostgreSQL running.
3. Record current release commit and incident timestamp.
4. Roll API and worker containers back together to the last verified compatible image.
5. Do not downgrade the database unless a reviewed migration-specific recovery plan requires it.
6. Run:
   - `/health/ready`
   - `/health/release`
   - `/health/reliability`
7. Check dead-letter queues.
8. Check payment reconciliation issues.
9. Resume traffic only after operational sign-off.

## Admin Dashboard rollback

Static frontend can roll back independently if its API contract remains compatible.

Verify:
- login,
- order list,
- support,
- finance,
- audit.

## Mobile rollback

For internal pilot:
- remove broken APK,
- install previous verified APK,
- keep the backend compatible with both current and previous pilot build during rollout.

For store release:
- follow store rollback/release controls.
- do not assume instant client rollback is possible.

## Payment incident

If payment callbacks are uncertain:
- stop payment-facing rollout,
- do not fabricate success,
- inspect provider ledger,
- run reconciliation,
- resolve unmatched/mismatched provider transactions through the existing financial reconciliation workflow.

## Push incident

Push failure must not block order state transitions.

If FCM is failing:
- keep core order APIs running,
- use Admin visibility/support as operational fallback,
- restore notification provider separately.

## Evidence

A rollback rehearsal is a mandatory Sprint 42 go-live gate.

The rehearsal must record:
- release rolled from/to,
- elapsed time,
- health probes,
- data integrity observations,
- operator,
- timestamp.
