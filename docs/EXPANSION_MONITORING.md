# Sprint 48 — Expansion Monitoring

## Snapshot metrics

Each persisted snapshot contains:

```text
Zone rollout stage / percent
daily orders / cap / utilization
hourly orders / cap / utilization
admission attempts / rejections / rate
open chefs in Zone area
available drivers
top Chef orders / cap / utilization
health
blockers
```

## Health

Policy thresholds default to:

```text
warning utilization = 80%
critical utilization = 95%
rejection spike = 30%
```

A paused Zone is Red.

A live Zone with no open Chef for the current day is Red.

A Zone with actual order demand and zero available driver pool becomes at least Amber.

## Worker

```text
expansion.monitor
```

persists snapshots for live/paused Expansion Zones.

## Control Room

Latest Amber/Red snapshots create a single deduplicated Operations incident per Zone.

When the condition disappears, the existing Operations auto-resolution logic can resolve the incident.
