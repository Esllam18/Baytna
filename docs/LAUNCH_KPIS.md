# Sprint 43 — Launch KPI Integrity

## Original Baytna launch gates

```text
Rating       ≥ 4.7
Repeat       ≥ 40%
On-time      ≥ 95%
Cancellation < 5%
```

## Measurable now

### Rating

Source:
`reviews.chef_overall`

### Repeat

Source:
delivered orders grouped by customer.

### Cancellation

Source:
orders in `cancelled` or `expired`.

## Operational but not the same as On-Time

Sprint 43 calculates:

```text
delivery_success_rate_pct
```

as:

```text
delivered / (delivered + cancelled)
```

This is useful operationally.

It is **not** the on-time KPI.

## Why On-Time is null

The current model contains timestamps such as:
- delivery task creation,
- pickup,
- route start,
- delivered time.

But it does not have one canonical:

```text
promised_delivery_deadline_at
```

for every standard order.

Without that value, any "95% on-time" number would be invented.

Therefore Sprint 43 returns:

```text
on_time_delivery_rate_pct = null
launch_target_on_time_met = null
```

The Admin UI shows:

```text
غير قابل للقياس حاليًا
```

## Required future model

A future sprint should introduce:
- promised delivery window/deadline,
- immutable order promise snapshot,
- actual delivered timestamp comparison,
- late reason taxonomy,
- on-time SLA aggregation.

Only then should the 95% launch gate be machine-evaluated.
