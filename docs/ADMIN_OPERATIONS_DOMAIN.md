# Admin Operations & Analytics Domain — Sprint 25

## Source-of-truth rules
- Order operational KPIs come from `orders`.
- Captured cash comes from successful `payments`.
- Refund totals come from successful `refunds`.
- Promotion cost comes from `order_pricing_adjustments`.
- Support workload comes from open `support_tickets`.
- Delivery operations come from `delivery_tasks`.
- Audit activity comes from append-only `audit_logs`.

## Order 360
The admin order detail aggregates order items, pricing adjustments, payment/refunds, delivery, address snapshot, state timeline, support tickets and internal notes without duplicating those domains.

## Admin notes
`admin_order_notes` is intentionally internal and audited. It stores operational context that does not belong in the customer-visible support conversation.

## Chef status actions
Allowed admin target states:
- active
- paused
- suspended
- rejected

Suspended/rejected require a reason. Non-active chefs are forced closed for Today’s Kitchen.

## Privacy
Order lists mask customer phone. More sensitive identity data should only be exposed by a future explicitly permissioned support/contact workflow.

## Analytics
Daily metrics are computed from transactional tables for a bounded 1–90 day range. This is appropriate for MVP. A warehouse/materialized reporting layer can replace it later without changing API contracts.

## Funnel caveat
The funnel uses immutable `order_status_events` plus the current Order state. It answers “reached stage”, not exact conversion timestamp attribution by marketing channel.
