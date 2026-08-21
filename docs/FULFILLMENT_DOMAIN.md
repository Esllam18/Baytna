# Fulfillment Domain — Sprint 20

## Why a separate Fulfillment record?
Order status is the public operational state.

Chef Fulfillment stores kitchen-specific details:
- acceptance deadline
- estimated ready time
- chef notes
- preparation timestamps
- packaging timestamp
- rejection reason

This avoids stuffing kitchen operational metadata into the core Order aggregate.

## Stages

### new
Order is paid/confirmed and waiting for chef response.

### accepted
Chef accepted the order.

### preparing
Cooking started.

### packaging
Internal stage while Order remains `preparing`.

### ready
Order is `ready_for_pickup`.

### rejected
Chef rejected before acceptance.

## State Rules

Allowed:
- confirmed → accepted_by_chef
- accepted_by_chef → preparing
- preparing → ready_for_pickup
- confirmed → cancelled (chef rejection only)

Internal fulfillment:
- preparing → packaging → ready

Not allowed:
- preparing before accept
- reject after accept
- another chef touching the order
- customer calling chef transitions

## Chef Rejection & Money
A confirmed order has already been paid.

Chef rejection therefore:
1. Calculates remaining refundable payment.
2. Creates a full refund using the Payment Provider adapter.
3. Restores converted inventory.
4. Marks fulfillment rejected.
5. Moves order to cancelled.
6. Writes timeline + audit.

Refund idempotency key:
`chef-reject-{order_id}`

## Customer Status Language

| Order / Fulfillment | Customer label |
|---|---|
| confirmed | تم تأكيد طلبك |
| accepted_by_chef | الشيف بدأت تجهيز أكلك |
| preparing | جاري الطبخ |
| preparing + packaging | جاري التغليف |
| ready_for_pickup | أكلك جاهز |
| cancelled | تم إلغاء الطلب |

## Concurrency
Order status transitions use an atomic:
`UPDATE orders ... WHERE status = expected_status`

This prevents two simultaneous transition requests from both succeeding.
