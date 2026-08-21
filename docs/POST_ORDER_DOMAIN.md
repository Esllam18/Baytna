# Post-Order Domain — Sprint 22

## Review Trust Rule
A review can only be created when:
- order belongs to customer
- order status is `delivered`
- no previous review exists for order

This guarantees the review comes from a real Baytna transaction.

## Multi-Dimensional Review
Stored dimensions:
- food_quality
- packaging
- order_accuracy
- value_for_money
- chef_overall
- delivery_overall

`delivery_overall` is optional if no delivered driver context exists.

## Aggregates
Chef profile `rating` is recalculated from visible `chef_overall` reviews.

Driver profile `rating` is recalculated from visible `delivery_overall` reviews.

Admin moderation can hide abusive/fake content without deleting the historical review.

Hidden reviews:
- remain in customer history
- are excluded from public chef reviews
- are excluded from aggregate rating

## Support Ticket State Machine

```text
new
 ↓
assigned
 ↓
investigating
 ↙        ↘
awaiting_customer   awaiting_internal
       \             /
        investigating
             ↓
          resolved
             ↓
           closed
```

Direct closure is allowed operationally when appropriate.

## Customer Visibility
Customer sees:
- public customer messages
- public admin responses
- status/resolution

Customer does NOT see:
- internal admin notes

## Resolution
Moving to `resolved` requires:
- resolution_code
- resolution_note

This forces structured operational learning from support cases.

## Order-linked Support
Ticket may reference an order.

If an `order_id` is provided:
- order must exist
- order must belong to the same customer

This prevents cross-customer data leakage.
