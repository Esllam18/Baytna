# Payment Domain — Sprint 19

## Separation of Concerns

Order lifecycle and financial lifecycle are separate.

### Order
- pending_payment
- confirmed
- cancelled
- expired

### Payment
- pending
- succeeded
- failed
- cancelled
- expired

### Refund
- pending
- succeeded
- failed

A confirmed order may have one or more refund records without rewriting the operational order status.

## Payment Intent
Payment Intent is created only when:
- customer owns the order
- order is `pending_payment`
- inventory hold still exists
- inventory hold has not expired

## Idempotency
Customer supplies:
`idempotency_key`

If the same key is retried for the same order, the same Payment is returned.

## Webhook Security
Webhook body is signed using HMAC SHA-256.

Header:
`X-Baytna-Signature`

Sprint 19 stores:
- provider
- provider event id
- event type
- payload hash
- payload body
- processing state

Duplicate provider event IDs are not processed twice.

## Payment Success
On `payment.succeeded`:
1. Verify payment reference.
2. Verify amount.
3. Verify currency.
4. Verify order still pending payment.
5. Verify reservation still active/not expired.
6. payment → succeeded.
7. inventory reservation → converted.
8. order → confirmed.
9. status event + audit log.

## Payment Failure / Cancellation
1. payment → failed/cancelled.
2. active inventory reservations released.
3. Today’s Kitchen quantity restored.
4. order → expired.
5. timeline/audit written.

## Refunds
Refund execution is admin-only in Sprint 19.

Rules:
- order must be confirmed
- successful payment must exist
- refund cannot exceed remaining refundable amount
- partial refunds allowed
- refund request uses an idempotency key

## Provider Adapter
Current provider:
`mock`

It is deliberately isolated behind `PaymentProvider`.

A real Egyptian or international provider can later implement:
- `create_intent`
- `refund`
- provider-specific webhook verification/parsing

without changing Order Domain rules.
