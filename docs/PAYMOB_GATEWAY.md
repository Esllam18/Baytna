# Sprint 32 — Paymob Gateway

## Payment flow

```text
Customer checkout
      ↓
Baytna Order = pending_payment
      ↓
POST /customer/orders/{order_id}/payment-intent
      ↓
Baytna creates Payment row
      ↓
Paymob Intention API
      ↓
client_secret + intention id
      ↓
Baytna returns hosted Unified Checkout URL
      ↓
Customer pays on Paymob
      ↓
Paymob backend Transaction Processed Callback
      ↓
HMAC verification
      ↓
Baytna confirms/fails payment
```

The browser/app redirect is UX only. Baytna does not confirm payment from redirect parameters.

## Configuration

```env
BAYTNA_PAYMENT_PROVIDER=paymob
BAYTNA_PAYMOB_BASE_URL=https://accept.paymob.com
BAYTNA_PAYMOB_SECRET_KEY=...
BAYTNA_PAYMOB_PUBLIC_KEY=...
BAYTNA_PAYMOB_HMAC_SECRET=...
BAYTNA_PAYMOB_PAYMENT_METHODS=12345,67890
BAYTNA_PAYMOB_NOTIFICATION_URL=https://api.example.com/api/v1/payments/webhooks/paymob/transaction
BAYTNA_PAYMOB_REDIRECTION_URL=https://app.example.com/payment/result
```

Payment-method identifiers must be enabled for the merchant account.

## Intention
Provider implementation sends:
- amount
- currency
- payment methods
- items
- billing data
- Baytna payment UUID as `special_reference`
- notification URL
- redirection URL

The response's Intention ID becomes `provider_reference`.

When returned, Paymob's order reference becomes `provider_order_reference`.

The Paymob `client_secret` is used to build the checkout URL and is not persisted as a separate internal credential.

## Billing data
Baytna currently persists customer phone/display name/address but no customer email field.

Paymob requires billing email, so Sprint 32 uses a merchant-domain non-deliverable placeholder:
`customer-{uuid}@payments.baytna.invalid`

This deliberately avoids inventing personal customer data. A verified customer-email field can replace it later.

## HMAC
Transaction callbacks are verified using Paymob HMAC SHA-512 over the documented transaction fields.

If HMAC verification fails:
- HTTP 401
- no payment state transition
- no order confirmation

## Callback mapping

```text
success=true, pending=false
  → payment succeeded

success=false, pending=false
  → payment failed

pending=true
  → provider snapshot stored, no final state transition
```

## Security
Baytna never receives or stores:
- PAN/card number
- CVV
- raw payment credentials

Hosted Paymob checkout handles sensitive payment entry.
