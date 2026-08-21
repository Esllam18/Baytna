# Retention Domain — Sprint 23

## 1. Notifications

Notification is a durable in-app record.

Fields:
- user
- kind
- title
- body
- action_url
- data_json
- dedupe_key
- read_at

### Dedupe
`(user_id, dedupe_key)` is unique.

This prevents duplicated UI notifications when an idempotent event endpoint is retried.

## 2. Favorites

Separate tables:
- favorite_chefs
- favorite_dishes

This preserves real foreign keys instead of a polymorphic `target_type + target_id` table.

Rules:
- favorite chef must exist, active, verified
- favorite dish must exist and be active
- add is idempotent
- remove is idempotent
- favorites are customer-isolated

## 3. Loyalty

Account:
- balance_points
- lifetime_earned_points
- lifetime_redeemed_points

Ledger:
- transaction type
- points
- source order
- idempotency key
- description

### Earn Rule
After Order becomes `delivered`:
```text
points = total_minor // loyalty_minor_per_point
```

Default:
```text
loyalty_minor_per_point = 1000
```

Each order can generate loyalty points only once.

Database protection:
- unique `source_order_id`
- unique `idempotency_key`

## 4. Delivery Integration

On successful delivery, in the same DB transaction:
1. order → delivered
2. delivery proof stored
3. notification created
4. loyalty transaction created
5. loyalty balance updated
6. commit

This avoids a delivered order with missing loyalty points under normal transaction success.

## 5. Retention Summary

One lightweight endpoint aggregates:
- favorites counts
- loyalty balance
- unread notifications

This is intended for the Customer Account/Home retention surfaces.

## Current Boundary

Points cannot yet be redeemed.

Why:
Discount application must be integrated with:
- checkout total calculation
- payment amount
- cancellation/refund
- loyalty rollback

That belongs together in Sprint 24 rather than being partially implemented.
