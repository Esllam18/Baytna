# Sprint 47 — Settlement Reconciliation

## Source of truth model

Baytna already has a Paymob provider-transaction ledger from transaction callbacks.

Sprint 47 adds settlement evidence as a separate normalized input.

The settlement is compared to the transaction ledger; it does not replace it.

## Required normalized fields

```text
provider_transaction_id
gross_amount_minor
fee_minor
refund_minor
net_settlement_minor
currency
is_settled
settled_at
```

## Clean settlement

All lines must match.

Then:

```text
batch.status = reconciled
```

and each real Paymob fee can create:

```text
EconomicsCostEntry
cost_type = payment_processing
source = provider
is_verified = true
```

## Mismatch

Any unmatched/mismatch line causes:

```text
batch.status = blocked
```

No settlement fee costs are materialized.

This means a bad provider file cannot partially improve or distort the Profitability report.

## Double-counting

If a verified `payment_processing` cost already exists for the same order from a separate source, settlement reconciliation blocks that line.

An operator must reconcile the duplicate accounting source instead of silently counting both.

## Automation

The Worker re-runs Draft/Blocked settlement reconciliation.

This is useful when:
- settlement evidence arrived first,
- Paymob transaction callback/ledger arrived later.

## Control Room

A blocked settlement batch becomes a Critical payment incident.

Expansion rollout checks blocked source-program settlements directly as well.
