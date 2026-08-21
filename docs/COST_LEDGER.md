# Sprint 46 — Cost Ledger

## Entry lifecycle

```text
Create
  ↓
Unverified
  ↓ Admin review
Verified
```

Unverified costs are excluded from totals but block economics evaluation.

## Order-level costs

For direct unit economics, attach the cost to:

```text
order_id
```

Examples:
- chef payout,
- courier partner charge,
- Paymob processing fee.

## Program-level costs

Fixed operational costs should be attached to:

```text
pilot_program_id
```

without an `order_id`.

## External references

When importing settlements or provider invoices:

```text
source = provider / import
external_reference = provider settlement/invoice ID
```

Sprint 46 rejects duplicate `source + external_reference`.

## Currency

Sprint 46 currently accepts:

```text
EGP
```

only.

There is no hidden FX conversion.

## Verification

Verification records:
- Admin ID,
- verification timestamp,
- Audit event.

## Deletion

Sprint 46 intentionally does not add a casual delete button.

Financial correction should be handled through a reviewed correction/import policy in a later reconciliation sprint rather than silently erasing audited cost history.
