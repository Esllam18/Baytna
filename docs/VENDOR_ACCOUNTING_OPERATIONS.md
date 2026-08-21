# Sprint 48 — Vendor Accounting Operations

## Provider Import Review

Sprint 47:

```text
Draft → Validate → Apply
```

Sprint 48:

```text
Draft → Validate → Independent Review → Apply
```

Pilot/Production requires maker-checker.

### Risk flags

Risk flags do not automatically reject an import. They make the review queue explicit and auditable.

Examples:

```text
foreign_currency
high_value_import
provider_adjustment
unallocated_variable_cost
```

## Settlement operations

Reconciliation answers:

```text
Does provider settlement evidence match Baytna's transaction ledger?
```

Operational close answers:

```text
Has Finance reviewed and closed the matched settlement?
```

They are intentionally different states.

A settlement cannot Close when:
- it is not reconciled,
- any line is mismatched,
- line counts do not match,
- a matched Payment still has an open reconciliation issue.

## Rollout dependency

Pilot/Production can require source-Pilot settlements to be operationally Closed before Start/Advance/Resume of Expansion rollout.
