# Sprint 46 — Operational Economics

## Revenue

```text
Captured Revenue
=
Successful Payments
```

```text
Net Collected
=
Successful Payments
-
Successful Refunds
```

Delivered order totals are shown as GMV but are not used as cash revenue.

## Variable Costs

Examples:
- chef settlement,
- courier partner settlement,
- payment processing,
- packaging,
- refund fee,
- recovery/compensation paid externally.

Only verified entries are included.

## Contribution

```text
Contribution = Net Collected - Variable Costs
```

```text
Contribution Margin = Contribution / Net Collected
```

## Fixed Operations

Examples:
- pilot operations staffing,
- fixed dispatch partner minimum,
- warehouse/office pilot expense,
- fixed operational software/support expense.

These must be entered as actual costs.

## Operational Profit

```text
Operational Profit
=
Contribution
-
Fixed Operations
```

## Coverage

Backend profitability is not evaluable unless:

```text
Revenue Coverage = 100%
Cost Coverage = 100%
Unverified Cost Entries = 0
```

## Required cost policy

Default:

```text
chef_payout
delivery_partner
payment_processing
```

This is configurable, but weakening the policy changes what "fully costed" means and should be treated as a finance/operations governance change.

## No discount double counting

A coupon reduces payment revenue.

It should not automatically become a second cost entry.

A separate cash reimbursement/subsidy may be recorded if it actually exists.
