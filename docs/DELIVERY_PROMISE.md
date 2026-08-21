# Sprint 44 — Delivery Promise Model

## Problem

A delivery system cannot truthfully calculate "On-Time Delivery" unless each order has an immutable promise to compare against.

Chef operating windows alone are not enough because they can change after an order is created.

## Order Snapshot

At order creation Baytna stores:

```text
promised_delivery_window_start_at
promised_delivery_window_end_at
promised_delivery_timezone
delivery_promise_source
delivery_promise_snapshot_at
```

That snapshot belongs to the Order.

The current Chef Workday may later change without rewriting that historical promise.

## Standard Order Source

```text
delivery_promise_source = today_kitchen
```

Source values:
- service date from Cart,
- delivery window from the matching Chef Workday.

## Special Order Source

```text
delivery_promise_source = special_order
```

Source values:
- approved/final service date,
- final negotiated delivery window.

## Timezone

Operational window input:

```text
HH:MM
```

Pilot timezone:

```text
Africa/Cairo
```

Snapshot timestamps are converted to UTC.

The original timezone name remains stored for accurate customer/driver presentation.

## Required Pilot Behavior

The pilot example configuration sets:

```text
BAYTNA_DELIVERY_PROMISE_REQUIRED=true
```

With this enabled, an order cannot be created without a complete valid delivery window.

This keeps new pilot orders measurable.

## Historical Compatibility

The database columns remain nullable.

Old/historical data without a promise remains valid and receives:

```text
delivery_timing_status = unmeasurable
```

rather than receiving an invented deadline.
