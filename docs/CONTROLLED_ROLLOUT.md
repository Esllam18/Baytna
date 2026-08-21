# Sprint 47 — Controlled Expansion Rollout

## Policy

A new zone should not jump from Approved directly to 100% traffic.

Default stages:

```text
Canary  10%
Limited 50%
Full   100%
```

## Start gate

Before Canary:
- Zone approved,
- current Expansion Assessment ready,
- source pilot economics/stability still pass,
- required launch budgets ready,
- no open Payment Reconciliation Issue,
- no blocked Provider Settlement Batch for the source program.

## Advance gate

The same checks run again before:
- Canary → Limited,
- Limited → Full.

An earlier approval cannot override later deterioration.

## Pause

Any live stage can be paused.

## Resume

Resume returns to the stage that was active before pause, after rechecking the financial/readiness gates.

## Evidence

Each stage transition persists:
- from/to stage,
- percentage,
- daily cap,
- assessment,
- full budget snapshot,
- Admin actor,
- timestamp.

This is the evidence used by Sprint 47's live financial automation collector.
