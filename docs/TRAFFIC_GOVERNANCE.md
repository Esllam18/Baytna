# Sprint 48 — Launch Traffic Governance

## Admission order

For a customer whose selected delivery address belongs to an Expansion Zone:

```text
resolve Zone
↓
lock Zone Traffic Policy
↓
check policy enabled
↓
check Zone live/not paused
↓
check stable rollout bucket
↓
check Zone daily cap
↓
check Zone hourly cap
↓
check Chef daily cap
↓
admit / reject
```

## Stable rollout bucket

```text
bucket = sha256(zone_id : customer_id) % 100
```

This avoids random audience churn between requests.

## Daily cap

Daily cap uses the Order service date and the Zone's delivery-area snapshots.

Cancelled/expired Orders do not consume active capacity.

## Hourly cap

Hourly cap protects launch intake by counting active Orders created for the Zone during the last hour.

## Chef cap

Chef/day protects a single kitchen from becoming the bottleneck while Zone traffic grows.

## Concurrency

The policy row is locked with `FOR UPDATE` on databases that support it.

Production target is PostgreSQL.

SQLite tests verify logic and migrations, not true concurrent lock behavior.

## Audit

Rejected admission has a durable event even without an Order.

Accepted admission is linked to the successful Order.

This makes traffic decisions measurable instead of inferred from HTTP logs.
