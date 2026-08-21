# Sprint 32 — Payment Reconciliation

## Purpose
Payment callbacks are external financial facts. They are stored separately from Baytna's operational payment row so inconsistencies can be discovered without overwriting evidence.

## Provider transaction ledger
Table:
`payment_provider_transactions`

Stores:
- provider transaction ID
- linked Baytna payment
- Paymob order reference
- parent transaction
- transaction type
- amount/currency
- success/pending/refund state
- callback payload hash
- raw provider snapshot
- observed timestamps

Unique key:
```text
(provider, provider_transaction_id)
```

This makes repeated provider callbacks idempotent.

## Matching strategy
A Paymob transaction is linked using the strongest available reference:

1. already-linked payment ID
2. parent provider transaction for refund/void
3. provider transaction reference
4. Paymob order reference
5. Baytna payment UUID echoed as `special_reference`
6. provider intention reference fallback

## Reconciliation issues
Table:
`payment_reconciliation_issues`

Types:
- `unmatched_provider_transaction`
- `amount_mismatch`
- `currency_mismatch`
- `status_mismatch`
- `refund_mismatch`

Issue fingerprints are deterministic, so repeatedly running reconciliation refreshes an existing discrepancy instead of flooding the table.

A discrepancy that reappears after manual resolution is reopened.

## Admin API

```text
GET  /api/v1/admin/payments/reconciliation/summary
GET  /api/v1/admin/payments/reconciliation/issues
POST /api/v1/admin/payments/reconciliation/run
POST /api/v1/admin/payments/reconciliation/issues/{id}/resolve
GET  /api/v1/admin/payments/reconciliation/payments/{payment_id}/provider-transactions
```

## Worker
Maintenance job:
`payments.reconcile`

This scans recent Paymob payment/provider snapshots and refreshes reconciliation issues.

## Refund reconciliation
Paymob refund callbacks are linked through the parent payment transaction.

For a matched successful refund:
- pending Baytna refund is completed
- provider refund transaction ID is captured
- local `refunded_minor` is updated
- then reconciliation compares post-state

Applying the legitimate callback before comparison avoids creating a false refund mismatch.
