# Sprint 36 — Account & Retention UI

## Account dashboard

The account home combines multiple backend domains without duplicating their source of truth:

```text
Customer Profile
    +
Addresses
    +
Favorites
    +
Notification Summary
    +
Loyalty
    +
Support
```

Counts are query-backed and refresh independently.

## Profile

Editable:
- display name
- preferred language

Read-only:
- phone number

Phone remains read-only because authentication currently uses phone OTP identity. A phone-change flow requires re-verification and is intentionally not simulated as a normal profile edit.

## Addresses

Lifecycle:
```text
create
→ edit
→ set default
→ use in checkout
→ optional delete
```

Order delivery addresses are snapshots, so deleting a saved address does not mutate the historical address already copied into an order.

Default behavior:
- first saved address becomes default.
- explicitly choosing default clears previous default.
- deleting the default promotes the oldest remaining saved address.

## Favorites

The mobile app uses backend idempotent favorite APIs.

Chef and Dish screens include a reusable FavoriteButton.

Query invalidation updates:
- account favorite count
- favorite chef list
- favorite dish list
- detail heart state

## Notifications

The notification center uses durable in-app notification records.

It supports:
- all/unread view
- mark one read
- mark all read
- action URL routing

Notification preferences are separate from notification history.

## Loyalty

The client only displays server-calculated loyalty state.

It never calculates or awards points locally.

## Subscription

Sprint 36 displays:
- active subscription
- plan list
- expiry
- cancellation

It does not invent a self-service recurring billing purchase flow.
