# Pricing Domain — Sprint 24

## Canonical Rule
There is one Pricing Engine for:
- quote preview
- order creation
- coupon validation
- subscription benefits
- loyalty redemption

The Order stores the final aggregated `discount_minor` and immutable pricing adjustments.

## Coupon Lifecycle
```text
valid
  ↓ order created
reserved
  ↓ payment success
applied
```

Failure path:
```text
reserved
  ↓ order cancel / payment fail / inventory-hold expiry
released
```

Coupon counters:
- `reserved_count`
- `redeemed_count`

Total usage limit counts both reserved and redeemed uses so pending checkouts cannot overbook the campaign cap.

## Coupon Types
### fixed
`discount_value` is minor currency units.

### percent
`discount_value` is basis points:
- 1000 = 10%
- 2500 = 25%
- 10000 = 100%

Optional `max_discount_minor` caps percentage campaigns.

## Loyalty Redemption
At order creation:
1. Validate requested points <= customer balance.
2. Convert points to money using redemption config.
3. Enforce minimum payable amount.
4. Atomically decrement available balance.
5. Store `loyalty_redemptions(status=reserved)`.

At payment success:
- reservation → applied
- `lifetime_redeemed_points` increments
- immutable negative ledger transaction is added

At unpaid failure:
- reservation → released
- points return to available balance

## Subscription Pricing
An active subscription can define:
- `order_discount_bps`
- `max_order_discount_minor`
- `loyalty_multiplier_bps`

The active plan is snapshotted into `order_pricing_adjustments`, so later plan edits do not change a historical order.

## Stacking
Coupon field:
`stack_with_subscription`

If false:
- coupon remains
- subscription order discount is removed for that checkout

Loyalty may still be redeemed after promotional discounts.

## Minimum Payable
By default the checkout must leave at least 100 minor units (1 EGP) payable.

This prevents a zero-value Order from entering the existing Payment domain, where a Payment amount must be positive.

## Pricing Snapshot
`order_pricing_adjustments` stores one row per type:
- coupon
- subscription
- loyalty

Each contains amount + immutable metadata/reference.
