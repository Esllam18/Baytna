# Sprint 37 — Definition of Done

## Reviews
- [x] Review eligibility endpoint.
- [x] Existing-review return in eligibility.
- [x] Customer isolation.
- [x] Multi-dimensional review screen.
- [x] Create review.
- [x] Edit review.
- [x] My Reviews screen.
- [x] Delivered-order review CTA.
- [x] Linked post-order support CTA.
- [x] Same-chef post-order navigation.
- [x] Chef rating summary UI.
- [x] Public chef review list UI.
- [x] Public review privacy hardening.

## Special Orders
- [x] Dish special-order CTA.
- [x] Chef availability API integration.
- [x] Capacity-aware date selection.
- [x] Quantity selector.
- [x] Customer note.
- [x] Special vs preorder selection.
- [x] Customer special-order list.
- [x] Customer special-order detail.
- [x] Counter-offer display.
- [x] Accept counter offer.
- [x] Offer expiry display.
- [x] Cancel before scheduling.
- [x] Checkout from awaiting payment.
- [x] Hosted payment bridge.
- [x] Scheduled order → canonical order navigation.
- [x] Rejection display.
- [x] Event timeline.

## Verification
- [x] 279 backend tests.
- [x] Python compile.
- [x] OpenAPI export.
- [x] 160 OpenAPI paths.
- [x] Customer contract guard.
- [x] Frontend static verification.
- [x] 69 TypeScript files transpiled without syntax diagnostics.
- [x] Existing Alembic chain.
- [x] Worker smoke 8/8.

## Database
No new database migration.

Migration head remains:
`0017_sprint32`

## Out of Scope
- App-store/native build.
- Photo/video attachments inside review UI.
- Public reviewer identity/avatar.
- Special-order custom multi-dish bundles.
- Customer negotiation beyond accepting/rejecting the chef counter offer.
- Direct in-app chat with chef.
