# Sprint 35 — Checkout & Payment UI

## Checkout invariant
The UI must quote and order with the same pricing inputs:

```text
cart_id
coupon_code
loyalty_points_to_redeem
```

Flow:

```text
Cart
  ↓
Pricing Quote
  ↓
Select/Create Delivery Address
  ↓
Create Order
  ↓
Set Order Delivery Address
  ↓
Create Paymob Payment Intent
  ↓
Store pending order ID in SecureStore
  ↓
Open hosted checkout_url
```

## Partial failure
The risky boundary is after `createOrder` because the cart is converted and inventory is reserved.

Sprint 35 therefore stores `createdOrderId` in screen state.

If payment intent/opening fails after order creation:
- checkout button is disabled for creating another order;
- user is routed to the existing order;
- order detail exposes `كمّل الدفع` for `pending_payment`.

## Provider return
Pending order ID is also stored in SecureStore so the payment result route can recover context even when the deep-link callback does not include `orderId`.

## Payment truth
The return screen polls backend payment/order state.

It does not trust:
- redirect query values;
- provider success text in a browser page;
- local app assumptions.

Only the Baytna backend payment state is shown as success.
