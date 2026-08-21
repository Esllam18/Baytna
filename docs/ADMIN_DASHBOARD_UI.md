# Sprint 40 — Admin Dashboard UI

## Information Architecture

```text
Admin
├── Dashboard
├── Orders
│   └── Order Detail
├── Chefs
│   └── Chef Detail
├── Drivers
│   └── Driver Detail
├── Support
│   └── Ticket Detail
├── Finance & Analytics
└── Audit Log
```

## Design Principle

The dashboard is operational, not decorative.

Every top-level screen answers a staff question:

### Dashboard
"What needs attention now?"

### Orders
"What exactly happened to this order?"

### Chefs
"Is this partner healthy and allowed to operate?"

### Drivers
"Who is available, in mission or repeatedly encountering issues?"

### Support
"Which customer problems are open, urgent or unassigned?"

### Finance
"What cash was captured/refunded and where is the order funnel leaking?"

### Audit
"Who changed what, and under which request?"

## Privacy

Order lists continue to use masked customer phone values from the backend.

The Admin Dashboard never attempts to derive or unmask hidden contact information.

## Sensitive Actions

High-impact actions are deliberately limited to existing backend contracts:
- chef suspension/rejection
- order refund
- support resolution
- internal operational note

No unsupported administrative override is simulated in the frontend.
