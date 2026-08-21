# Sprint 40 — Admin Operations Flows

## Order Investigation

```text
Orders
  ↓ filter
Order Detail
  ├── items
  ├── pricing
  ├── payment
  ├── delivery
  ├── timeline
  ├── support tickets
  └── admin notes
```

If financial remediation is required:

```text
Order Detail
  ↓
Refund
  ↓
Existing Payment Provider
  ↓
Refund record / provider status
```

## Chef Control

```text
Chef Detail
  ↓
active / paused / suspended / rejected
```

Suspended and rejected states require a reason.

The backend audit event remains the source of the change record.

## Support

```text
New Ticket
  ↓
Assign
  ↓
Investigating
  ↓
Awaiting Customer / Awaiting Internal
  ↓
Resolved
  ↓
Closed
```

Internal notes:
- staff-only
- visually distinct
- never intentionally sent as customer-visible replies

## Finance

The dashboard shows:
```text
Captured
− Successful Refunds
= Net Collected
```

This is cash collection reporting, not accounting profit.

Commission, tax and net-profit calculations are intentionally not fabricated.
