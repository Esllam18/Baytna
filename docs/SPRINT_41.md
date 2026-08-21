# Sprint 41 — Definition of Done

## Cross-App Backend
- [x] Universal push device registration endpoint.
- [x] Universal device list.
- [x] Universal device deactivation.
- [x] Universal notification preferences.
- [x] Existing customer notification routes preserved.
- [x] No database migration required.

## Customer App
- [x] Sprint 41 version.
- [x] Android native push bootstrap.
- [x] Notification tap route handling.
- [x] Support image picker.
- [x] Signed support attachment upload.
- [x] Support ticket attachment IDs.
- [x] Support reply attachment IDs.
- [x] EAS pilot profile.

## Chef App
- [x] Sprint 41 version.
- [x] Android native push bootstrap.
- [x] Notification tap route handling.
- [x] Dish image picker.
- [x] Public dish-image media upload.
- [x] Dish media binding.
- [x] EAS pilot profile.

## Driver App
- [x] Sprint 41 version.
- [x] Android native push bootstrap.
- [x] Notification tap route handling.
- [x] Existing private delivery-proof image flow retained.
- [x] EAS pilot profile.

## Admin Dashboard
- [x] Docker multi-stage build.
- [x] Nginx SPA config.
- [x] Baseline static security headers.
- [x] Pilot frontend compose file.

## Pilot Journey
- [x] Automated Customer → Chef → Driver → Customer → Admin integration journey.
- [x] Universal push registration test for customer/chef/driver.
- [x] Customer support attachment backend test.
- [x] Chef dish image bind backend test.
- [x] Live staging cross-app validation script.
- [x] Live script refuses to fake real payment success.
- [x] Live delivery requires explicit proof reference.

## Deployment
- [x] Frontend deployment preflight.
- [x] GitHub frontend validation workflow.
- [x] Mobile internal Android build profiles.
- [x] Pilot deployment documentation.

## Verification
- [x] 300 backend tests.
- [x] Python compile.
- [x] OpenAPI 169 paths.
- [x] Cross-app contract guard.
- [x] Frontend/media/deployment static guard.
- [x] Structure guard.
- [x] Frontend preflight.
- [x] 155 frontend TypeScript files transpiled with 0 syntax diagnostics.
- [x] Alembic chain.
- [x] Worker smoke 8/8.

## Out of Scope / Live Boundaries
- [ ] Real physical Android FCM registration test.
- [ ] Real FCM delivery to Customer device.
- [ ] Real FCM delivery to Chef device.
- [ ] Real FCM delivery to Driver device.
- [ ] iOS Firebase Messaging registration.
- [ ] EAS cloud build.
- [ ] Real APK installation/device smoke.
- [ ] Deployed Admin Dashboard URL.
- [ ] Live paid Paymob end-to-end pilot transaction.
- [ ] Live staging cross-app script execution with production-like credentials.
