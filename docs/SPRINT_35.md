# Sprint 35 — Definition of Done

- [x] C13 Cart screen.
- [x] Cart quantity update.
- [x] Cart remove item.
- [x] Clear cart.
- [x] max-per-order UI guard.
- [x] C14 Checkout screen.
- [x] Saved address selection.
- [x] Create address inside checkout.
- [x] Pricing quote integration.
- [x] Coupon UI.
- [x] Loyalty points UI.
- [x] Full pricing summary.
- [x] Order creation.
- [x] Delivery-address snapshot selection.
- [x] Paymob payment-intent launch.
- [x] Pending order ID persisted securely for provider return.
- [x] Payment result screen.
- [x] Backend payment/order re-fetch after redirect.
- [x] Pending payment retry from order detail.
- [x] Prevent duplicate order after partial checkout failure.
- [x] Orders list.
- [x] Order detail.
- [x] Pending-payment cancellation action.
- [x] C15 live tracking.
- [x] Fulfillment + delivery tracking merge.
- [x] Pre-dispatch delivery tracking with null mission state.
- [x] Defensive 404 tolerance in mobile API layer.
- [x] 10-second tracking polling.
- [x] Bottom-nav Orders route.
- [x] Home quick-cart access.
- [x] Backend runtime contract tests.
- [x] OpenAPI contract guard.
- [x] Frontend static verification.
- [x] TypeScript syntax/transpile verification.

## Backend migration
No schema change required.

Migration head remains:
`0017_sprint32`

## External boundary
A real Paymob card payment is not executed by automated tests because merchant credentials and a user payment action are not available in this environment.

The app uses the real backend `checkout_url` contract and never assumes payment success from redirect alone.
