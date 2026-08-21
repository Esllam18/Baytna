# Sprint 44 — True On-Time KPI

## Definition

For each delivered order with an immutable promised window:

```text
On Time
if
delivered_at <= promised_delivery_window_end_at
```

Otherwise:

```text
Late
```

with:

```text
late_by_minutes
```

rounded upward to full minutes.

## Aggregation

```text
On-Time Rate
=
On-Time measurable deliveries
/
All measurable deliveries
```

## Coverage

```text
Promise Coverage
=
Measurable delivered orders
/
All delivered orders
```

## Launch gate

Baytna's launch target:

```text
On-Time ≥ 95%
```

Machine evaluation requires:

```text
Promise Coverage = 100%
```

If coverage is below 100%:

```text
launch_target_on_time_met = null
```

even if the measurable subset scores above 95%.

## Why

Without this rule, a mixed historical sample could hide late/unmeasurable deliveries and create an artificially strong launch KPI.

## Separate metric

```text
delivery_success_rate_pct
```

remains useful, but it means successful completion versus cancellation.

It is not the same as On-Time Delivery.
