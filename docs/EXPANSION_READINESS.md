# Sprint 46 — Expansion Readiness

## Source proof vs target zone

A candidate zone does not need historical orders before launch.

Its readiness is based on the proven source operating model.

Example:

```text
Source Pilot: 6 October
Target Zone: Sheikh Zayed
```

## Assessment

The system persists:
- pilot period,
- delivered orders,
- net collected,
- variable costs,
- contribution,
- contribution margin,
- fixed costs,
- operational profit,
- cost/revenue coverage,
- unverified cost count,
- stability result,
- post-pilot result,
- final blockers.

## Gate

A zone is `ready` only when all configured conditions pass.

Typical blockers:

```text
source_pilot_not_completed
economics_cost_coverage_below_100_pct
economics_unverified_cost_entries_present
operational_profit_not_positive
contribution_margin_below_zone_target
delivered_orders_*_below_*
eight_week_stability_gate_not_met
post_pilot_*
```

## Approval

Readiness does not automatically approve expansion.

An Admin explicitly approves the zone.

## Launch

Launch re-runs assessment.

This is important because:
- new costs may arrive,
- profit may deteriorate,
- a reconciliation issue may open,
- post-pilot readiness may change.

An old green assessment cannot force a current unsafe launch.

## Pause

A live zone can be paused.

Sprint 46 does not remove or rewrite historical assessment records.
