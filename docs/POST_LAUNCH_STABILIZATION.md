# Sprint 50 — Post-Launch Stabilization

## Daily Close cadence

`launch.command.maintain` creates a system-prepared Daily Financial Close for each completed service day during the configured stabilization window.

Preparation time:

```text
next UTC service-day boundary
```

Operational close deadline:

```text
next UTC service-day boundary + launch_financial_close_grace_hours
```

System preparation never closes the ledger. Existing completeness checks and maker-checker remain authoritative.

## Evidence retention

Canonical complete evidence is permanent unless an explicit future archival policy says otherwise.
Automatic cleanup is limited to expired, superseded, incomplete working packs.

This prevents cleanup from deleting the proof used for launch authorization.

## Expansion Review

One durable review is generated per Zone/day.
It summarizes a configurable trailing window and produces an advisory recommendation.

Hard blockers include:

- missing/current RED monitoring,
- open Critical Zone incident,
- overdue Daily Close,
- blocked Daily Close,
- incomplete expected cadence.

Watch signals include:

- Amber monitoring,
- recent SLO Auto-Pause,
- Amber/Red forecast,
- Amber snapshots in the review window.

The review does not mutate rollout state.
