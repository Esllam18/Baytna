# Sprint 38 — Chef Operational Flows

## Morning Kitchen Flow

```text
Login
  ↓
Dashboard
  ↓
Open Today’s Kitchen
  ↓
Select Signature Menu dishes
  ↓
Set quantities
  ↓
Publish
  ↓
Monitor sold-out / available stock
```

## Standard Order Flow

```text
payment succeeded
  ↓
new
  ↓ chef accepts
accepted
  ↓
preparing
  ↓
packaging
  ↓
ready
  ↓
driver pickup flow
```

Rejecting a confirmed order continues to use the backend refund/inventory recovery path already implemented.

## Special Order Flow

### Direct accept

```text
chef_review
  ↓ chef accepts
awaiting_payment
  ↓ customer pays
scheduled
  ↓
canonical fulfillment flow
```

### Counter offer

```text
chef_review
  ↓ chef proposes date/price/window
counter_offer
  ↓ customer accepts
awaiting_payment
  ↓ customer pays
scheduled
```

### Reject

```text
chef_review
  ↓
rejected
```

## Schedule Capacity

Weekly schedule determines which dates customers can request.

The app edits:
- weekday availability
- delivery window
- max special requests

The backend remains responsible for:
- actual capacity used,
- exclusions,
- booking horizon,
- prep notice,
- conflict validation.
