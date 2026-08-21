# Post-Pilot Scale Decision

## Automated inputs

Baytna calculates:

- 8-week stability,
- order volume,
- cancellation,
- true On-Time,
- promise coverage,
- ratings,
- repeat rate,
- cohorts,
- support rate,
- refund rate,
- GMV/cash collection,
- active Critical incidents,
- Payment Reconciliation state.

## Reviewed inputs

Baytna requires reviewed evidence for:

- positive operational profit,
- QA exit,
- operations sign-off.

## Scale readiness

`scale_ready` is true only when:

```text
program completed
AND current consecutive stable weeks >= 8
AND operational_profit_positive passed
AND pilot_qa_exit passed
AND operations_signoff passed
AND active critical incidents = 0
AND open payment reconciliation issues = 0
```

## Why Net Collected is not profit

```text
Net Collected = captured payments - successful refunds
```

It does not represent:

- outsourced delivery cost,
- packaging subsidies,
- support labor,
- payment-provider cost,
- promotions funded by Baytna,
- platform/cloud cost,
- operating payroll,
- other overhead.

Sprint 45 therefore returns:

```text
profitability_calculated_from_backend = false
```

A future operational-cost ledger can automate that evidence safely.
