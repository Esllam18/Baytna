# Sprint 36 — Definition of Done

- [x] Account bottom-nav destination.
- [x] Account dashboard.
- [x] Customer profile API.
- [x] Customer profile edit UI.
- [x] Full address management API.
- [x] Address list/new/edit/default/delete UI.
- [x] Favorite chefs UI.
- [x] Favorite dishes UI.
- [x] Chef favorite control.
- [x] Dish favorite control.
- [x] Notification list UI.
- [x] Unread filter.
- [x] Mark read.
- [x] Mark all read.
- [x] Notification preference UI.
- [x] Loyalty balance UI.
- [x] Loyalty history.
- [x] Support ticket list.
- [x] Create support ticket.
- [x] Support conversation.
- [x] Support conversation polling.
- [x] Subscription visibility.
- [x] Cancel active subscription.
- [x] Logout wiring.
- [x] OpenAPI customer account contract guard.
- [x] Backend regression suite.
- [x] TypeScript syntax/transpile verification.
- [x] Worker smoke.
- [x] Existing migration chain verification.

## No schema migration
Sprint 36 uses existing:
- customer_profiles
- addresses
- favorites
- notifications
- notification_preferences
- loyalty
- support
- subscriptions

Backend changes are service/router additions only.

## Out of Scope
- Customer account deletion workflow.
- Payment-method vault UI.
- Media picker for support attachments.
- Recurring subscription purchase/billing.
- Native push token acquisition flow from Expo/FCM.
- App-store/native build.

Next: Sprint 37.
