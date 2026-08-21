# Sprint 49 — Daily Financial Close

## Scope

A Daily Close is calculated from backend truth for a Launch Session and service date.

## Revenue

```text
Succeeded Payment capture
-
Succeeded Refunds
=
Net Collected
```

## Costs

Only verified Economics Cost Entries count.

The close calculates:

```text
Variable Cost
Fixed Cost
Contribution
Operational Profit
```

## Completeness gates

Required:

```text
Revenue Coverage = 100%
Cost Coverage = 100%
No unverified cost
No pending provider import for the day
No unclosed provider settlement for the day
No open payment reconciliation issue
```

A loss-making day may still close if the ledger is complete.

## Dual control

Pilot/Production requires a different Admin to Close than the Admin who Prepared.

## Checksum

On Close, the canonical summary receives SHA-256.

Reopen invalidates that checksum and requires a new Close.
