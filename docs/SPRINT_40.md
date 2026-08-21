# Sprint 40 — Definition of Done

## Backend
- [x] Admin self-profile endpoint.
- [x] Admin role isolation.
- [x] No new schema migration.
- [x] Existing admin operations APIs reused as sources of truth.

## Admin Web Foundation
- [x] Dedicated React/Vite app.
- [x] TypeScript.
- [x] Admin OTP login.
- [x] Admin role enforcement.
- [x] Session-scoped token storage.
- [x] Refresh token flow.
- [x] Logout/revocation.
- [x] Protected routing.
- [x] RTL responsive shell.
- [x] Desktop and compact/mobile layout.

## Operations Dashboard
- [x] Orders metrics.
- [x] GMV.
- [x] Net collected.
- [x] Support workload.
- [x] Chef counts.
- [x] Driver counts.
- [x] Daily order trend.
- [x] Operational alert shortcuts.

## Orders
- [x] Order list.
- [x] Status filter.
- [x] Order detail.
- [x] Masked customer phone.
- [x] Items.
- [x] Pricing adjustments.
- [x] Payment status.
- [x] Delivery status.
- [x] Delivery address.
- [x] Timeline.
- [x] Internal admin notes.
- [x] Refund action.
- [x] Linked support tickets.

## Chefs
- [x] List.
- [x] Status filter.
- [x] Detail.
- [x] Rating/orders/dishes/reviews/support metrics.
- [x] Pause.
- [x] Activate.
- [x] Suspend with reason.
- [x] Reject with reason.

## Drivers
- [x] List.
- [x] Status filter.
- [x] Detail.
- [x] Rating.
- [x] Mission counts.
- [x] Issue counts.
- [x] Current mission.

## Support
- [x] Workload summary.
- [x] Ticket filtering.
- [x] Ticket detail.
- [x] Assign to current admin.
- [x] Customer-visible reply.
- [x] Internal note.
- [x] Status transition.
- [x] Resolution fields.
- [x] Closed state.

## Finance & Analytics
- [x] Captured cash.
- [x] Refunds.
- [x] Net collected.
- [x] Failed/pending payments.
- [x] Pricing discounts.
- [x] Daily metrics.
- [x] Funnel.
- [x] Retention.

## Audit
- [x] Audit log table.
- [x] Actor/entity/request trace.

## Verification
- [x] 296 backend tests.
- [x] Python compile.
- [x] OpenAPI 166 paths.
- [x] Admin contract guard.
- [x] Admin frontend static verification.
- [x] 24 TypeScript files / 0 syntax diagnostics.
- [x] Structure verification.
- [x] Alembic chain.
- [x] Worker smoke 8/8.

## Out of Scope
- Production Vite bundle/deployment.
- Browser E2E with Playwright.
- Admin user/role management UI.
- Content-management UI.
- Coupon/subscription-plan management UI.
- Manual driver reassignment override.
- Finance commission/VAT/profit ledger not present in source-of-truth backend.
