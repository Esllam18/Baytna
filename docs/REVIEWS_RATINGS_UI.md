# Sprint 37 — Reviews & Ratings UI

## Eligibility

Endpoint:
```text
GET /api/v1/customer/orders/{order_id}/review-eligibility
```

Responses represent three main states:

```text
order_not_delivered
  can_review = false

ready_for_review
  can_review = true
  review = null

review_exists
  can_review = true
  review = existing review
```

The client no longer needs to use "GET review → 404" as normal UI state.

## Rating dimensions

```text
food_quality
packaging
order_accuracy
value_for_money
chef_overall
delivery_overall (optional)
```

All required dimensions use 1–5 stars.

## Public privacy

The public chef page never needs operational identities.

Public response contains:
- review ID
- food quality
- packaging
- order accuracy
- value for money
- chef overall
- comment
- created timestamp

It does not expose:
- customer ID
- order ID
- driver ID
- moderation state

## Customer history

`/account/reviews`

Customers can inspect and edit their own rating history.

Editing continues to use the existing backend aggregate recalculation logic, so updated ratings propagate to the chef/driver aggregate rather than being client-calculated.
