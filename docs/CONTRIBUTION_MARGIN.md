# Sprint 46 — Contribution Margin

## Why contribution margin matters

GMV growth can coexist with worsening economics.

Baytna therefore separates:

```text
GMV
Cash Collected
Variable Cost
Contribution
Fixed Cost
Operational Profit
```

## Formula

```text
Contribution Margin %
=
(Net Collected - Verified Variable Costs)
/
Net Collected
```

## Per-order contribution

```text
Contribution / Delivered Order
```

is also reported.

## Evaluation rule

Contribution is not accepted as a scale signal when:
- delivered revenue is incomplete,
- cost coverage is incomplete,
- unverified costs exist,
- net collected is not positive.

## Expansion threshold

Each candidate expansion zone stores its own minimum acceptable:

```text
min_contribution_margin_pct
```

Default creation threshold can come from:

```text
BAYTNA_ECONOMICS_DEFAULT_MIN_CONTRIBUTION_MARGIN_PCT
```

Default in Sprint 46:

```text
15%
```

The threshold is an operational policy, not a claim that 15% is universally correct for every future Baytna stage.
