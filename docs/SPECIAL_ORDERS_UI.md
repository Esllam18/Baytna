# Sprint 37 — Special Orders Mobile UI

## Entry point

The product rule remains:
Customer chooses a chef, then a dish from Signature Menu.

If:
```text
dish.is_special_order_available == true
```

the customer can open:
```text
/special-orders/new?chefId=...&dishId=...
```

## Availability

The mobile app consumes:
```text
GET /api/v1/chefs/{chef_id}/availability?days=30
```

Only `is_available=true` dates are offered.

Displayed capacity comes from backend:
```text
capacity_total
capacity_used
capacity_remaining
```

The client does not calculate chef capacity.

## Create

Request contains:
```text
dish_id
request_type
quantity
requested_service_date
requested_window_start
requested_window_end
customer_note
```

Price displayed before chef response is explicitly described as preliminary.

## Lifecycle

```text
chef_review
     ↓
awaiting_payment
     ↓
scheduled
```

or:

```text
chef_review
     ↓
counter_offer
     ↓ customer accepts
awaiting_payment
     ↓
scheduled
```

terminal pre-schedule states:
```text
rejected
cancelled
expired
```

## Payment

The app never creates a separate mobile-only order.

Checkout:
```text
POST /customer/special-orders/{id}/checkout
```

returns:
- SpecialOrder
- canonical Order
- Payment

The canonical order then goes through the same payment-result and order-tracking experience as normal orders.

## Customer cancellation

The UI only offers cancellation in:
- chef_review
- counter_offer
- awaiting_payment

Once scheduled, customer self-cancel is hidden because backend rules require a different operational resolution path.

## Timeline

The customer sees the durable SpecialOrder event history, not reconstructed client-side state transitions.
