# Sprint 35 — Live Order Tracking UI

## Data sources
Two backend views are combined:

1. Fulfillment:
`GET /customer/orders/{order_id}/tracking`

2. Delivery:
`GET /customer/orders/{order_id}/delivery-tracking`

With the current backend, before driver dispatch the second endpoint returns `200` with `mission_status = null`.

The mobile API layer also defensively tolerates a 404 as `delivery: null` so a future deployment/race condition does not break the entire tracking screen. Other errors still propagate.

## Polling
Active orders refresh every 10 seconds.

Polling stops for terminal states:
- delivered
- cancelled
- expired

## Display journey
```text
confirmed
→ accepted_by_chef
→ preparing
→ ready_for_pickup
→ assigned_to_driver
→ picked_up
→ out_for_delivery
→ delivered
```

The current emotional status from backend remains primary display copy.
The visual journey is secondary context.

## No fake live GPS
Sprint 35 does not invent courier GPS/map tracking because the backend does not yet expose a real location feed/provider.

It displays operational status only.
