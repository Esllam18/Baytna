# Sprint 43 — Pilot Operations Control Room

## Health Model

```text
GREEN
No active incidents

AMBER
One or more active warning/high incidents

RED
One or more active critical incidents
```

The health color is based on durable active incidents, not browser-local state.

## Incident Sources

| Category | Condition |
|---|---|
| Chef SLA | Chef acceptance deadline exceeded |
| Delivery SLA | Delivery task unassigned too long |
| Delivery SLA | Active delivery issue |
| Support SLA | Open support ticket exceeded priority SLA |
| Payment | Open reconciliation issue |
| Reliability | Outbox dead letter |
| Reliability | Job dead letter |
| Reliability | Stale worker heartbeat |
| Notifications | Notification dead letter |

## Lifecycle

```text
detected
  ↓
open
  ↓ acknowledge
acknowledged
  ↓ resolve
resolved
```

Owner assignment can happen while an incident is open or acknowledged.

Escalation raises:

```text
info → warning → high → critical
```

Critical remains critical.

## Source Condition Wins

A manual resolution does not suppress an ongoing problem forever.

If the next scan still detects the condition:

```text
resolved → open
```

This is intentional.

## Automatic Resolution

If the source condition disappears:

```text
open / acknowledged
  ↓
resolved
resolution_note = auto_resolved_condition_cleared
```

## Control Room Refresh

The worker performs the authoritative scan every minute.

The Admin page also calls refresh as an operational convenience.

The UI is not the only path capable of creating incidents.
