# Sprint 43 — Daily Operations

## Opening routine

1. Open `/control-room`.
2. Confirm worker status.
3. Run/observe incident refresh.
4. Check RED incidents.
5. Assign owners.
6. Check AMBER incidents.
7. Check urgent support.
8. Check available drivers.
9. Check open kitchens.
10. Review launch KPI sample health.

## During operations

Every minute the worker schedules:

```text
operations.scan
```

Recommended staff behavior:

### Critical
- acknowledge immediately,
- assign owner,
- investigate source,
- resolve source condition,
- add meaningful resolution note.

### High
- assign during active shift,
- prevent SLA becoming critical.

### Warning
- monitor and clear before volume increases.

## Daily Brief

The daily brief provides:
- created orders,
- delivered,
- cancelled,
- GMV,
- incidents,
- urgent support,
- available drivers,
- open chefs,
- prioritized actions.

## End-of-day routine

1. No unexplained critical incidents.
2. Review all manually resolved incidents.
3. Review auto-resolved incidents for recurring patterns.
4. Review payment reconciliation.
5. Review Outbox/Job dead letters.
6. Review notification dead letters.
7. Review support SLA breaches.
8. Export/record operational decisions where required.
9. Compare launch KPI trends.
10. Record unresolved operational risks for next shift.
