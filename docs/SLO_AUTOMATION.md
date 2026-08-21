# Sprint 50 — SLO Automation & Capacity Forecasting

## Auto-Pause source of truth

Auto-Pause consumes persisted `expansion_monitoring_snapshots` only.
A mutable streak counter is deliberately not introduced.

Required policy:

```text
slo_auto_pause_enabled = true
slo_consecutive_red_snapshots >= 2
```

A Green or Amber observation breaks the RED streak.
Paused snapshots cannot recursively create another Pause transition.

## Auto-Pause action

The system calls the same canonical rollout Pause semantics used by controlled expansion.
It writes a durable rollout event with:

```text
trigger_source = system
trigger_reason = slo_auto_pause
trigger_evidence_json = {
  monitoring_snapshot_id,
  blockers,
  red_streak,
  required_red_streak,
  previous_stage,
  previous_percent
}
```

If a Launch Command Session is operational, a critical Command Timeline event is also persisted.

## No Auto-Resume

Recovery is never inferred from a later Green snapshot.
Resume remains an explicit guarded action and rechecks the current readiness, finance and command gates.

## Forecasting

Each monitoring snapshot has at most one `expansion_capacity_forecasts` row.
The one-hour projection is conservative: it never projects below the latest observed hourly rate and uses a rolling lookback as context.

Forecast risk may become Amber/Red, but forecast risk alone does not Pause a Zone.
This avoids a forecast model becoming an unreviewed traffic controller.
