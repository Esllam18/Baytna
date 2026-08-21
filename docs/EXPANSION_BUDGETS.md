# Sprint 47 — Expansion Zone Budgets

## Why

"Economics is profitable" does not mean "we have approved cash to launch another zone."

Sprint 47 separates:
- source-pilot economics,
- expansion launch budget.

## Default required categories

```text
operations
chef_onboarding
delivery_supply
contingency
```

The list is configurable.

## Budget model

For every category:

```text
allocated
committed
spent
remaining
```

Formula:

```text
remaining = allocated - committed - spent
```

Database/service guards prevent used money from exceeding allocation.

## Movements

### Commit

Reserve budget against a purchase/order/contract.

### Release

Release a prior commitment.

### Spend

Record actual spend. Spend consumes available committed value first.

## Launch gate

A zone is Budget Ready only when:
- every required category exists,
- every required allocation is positive,
- total remaining is not negative.

Budget Ready is required before controlled rollout starts or resumes/advances.
