# Special Order Domain — Sprint 26

## Signature Menu vs Today’s Kitchen

### Today’s Kitchen
Immediate inventory:
- quantity exists now
- cart holds inventory at checkout
- standard order

### Special Order / Preorder
Future commitment:
- comes from Signature Menu
- does not require a Today’s Kitchen inventory row
- chef must approve the commercial request first
- customer pays the approved quote
- order is then scheduled

## Schedule Resolution
For a requested date:

1. Date-specific override wins.
2. Otherwise weekly weekday rule is used.
3. If neither exists, the date is unavailable.
4. Capacity counts active special-order requests.
5. Dish `prep_notice_hours` is enforced.
6. Maximum booking horizon is configurable.

## Special Order State Machine
```text
chef_review
  ├─ chef reject → rejected
  ├─ chef counter → counter_offer
  │                   ↓ customer accept
  └─ chef accept ─→ awaiting_payment
                         ↓ payment
                      scheduled
```

Terminal before payment:
- rejected
- cancelled
- expired

## Quote
The final quote contains:
- final service date
- delivery window
- final unit price
- quantity
- final total
- payment expiry

The quote is fixed in Sprint 26:
- no coupon stacking
- no loyalty redemption
- no subscription order-discount stacking

## Payment Bridge
Special-order checkout creates a normal `orders` row with:
```text
order_type = special
source_cart_id = NULL
```

`order_items.daily_menu_item_id` is nullable for Special Orders.

Payment validation uses `offer_expires_at` instead of a Today’s Kitchen inventory hold.

## Payment Success
Because the chef already approved the custom quote before payment:
```text
Order: pending_payment → accepted_by_chef
Special Order: awaiting_payment → scheduled
Fulfillment: accepted
```

This prevents approving the same custom request twice.

## Payment Failure
A failed provider attempt:
- marks that Payment failed
- does not cancel the Special Order
- keeps Order `pending_payment`
- customer can retry with a new Payment Intent while the quote remains valid

## Capacity
Active states that consume schedule capacity:
- chef_review
- counter_offer
- awaiting_payment
- scheduled

Rejected / cancelled / expired requests are excluded from capacity.
