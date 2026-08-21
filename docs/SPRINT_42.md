# Sprint 42 — Definition of Done

## Release Identity
- [x] Backend version `0.42.0`.
- [x] Customer version `0.42.0`.
- [x] Chef version `0.42.0`.
- [x] Driver version `0.42.0`.
- [x] Admin version `0.42.0`.
- [x] Release version setting.
- [x] Release commit setting.
- [x] Release slot setting.
- [x] Safe `/health/release`.
- [x] No new database migration.

## Crash Reporting — Mobile
- [x] `@sentry/react-native`.
- [x] Sentry Expo config plugin.
- [x] Sentry Metro wrapper.
- [x] Startup initialization.
- [x] Environment/release tags.
- [x] PII-default disabled.
- [x] Customer diagnostics route.
- [x] Chef diagnostics route.
- [x] Driver diagnostics route.
- [x] Normal pilot diagnostics disabled.
- [x] Production diagnostics disabled.
- [x] Dedicated diagnostic build profile.

## Crash Reporting — Admin
- [x] `@sentry/react`.
- [x] React 19 error hooks.
- [x] `@sentry/vite-plugin`.
- [x] Build-time source-map upload path.
- [x] Source-map deletion after upload.
- [x] Admin diagnostics route.
- [x] Diagnostics disabled by default.

## Build Security
- [x] No Sentry auth token committed.
- [x] No Firebase service file committed.
- [x] Dynamic `GOOGLE_SERVICES_JSON`.
- [x] EAS preview/production environments.
- [x] `sentry.properties.example` only.
- [x] Source release secret-pattern guard.

## Release Automation
- [x] Source release preflight.
- [x] Live API release probe.
- [x] Release evidence template.
- [x] Strict go-live gate.
- [x] PR/manual pilot release workflow.
- [x] Manual EAS build submission workflow.

## Operational Runbooks
- [x] Crash reporting.
- [x] Physical-device build.
- [x] Live staging.
- [x] Rollback.
- [x] Go-live checklist.

## Verification
- [x] 302 backend tests.
- [x] Python compile.
- [x] OpenAPI 170 paths.
- [x] Sprint 42 contract guard.
- [x] Release source preflight.
- [x] Crash-reporting static guard.
- [x] Structure guard.
- [x] Frontend deployment preflight.
- [x] 163 TypeScript files / 0 syntax diagnostics.
- [x] Alembic chain.
- [x] Worker smoke 8/8.
- [x] Incomplete evidence blocks go-live with exit code 2.

## External / Live Gates Not Claimed
- [ ] EAS cloud builds completed.
- [ ] Physical Android installs completed.
- [ ] Real FCM receipt completed.
- [ ] Real Sentry event/crash proof completed.
- [ ] Real Paymob pilot payment completed.
- [ ] Real S3 pilot storage completed.
- [ ] Real Twilio delivery completed.
- [ ] Deployed pilot domains completed.
- [ ] Full live cross-app staging journey completed.
- [ ] Operations sign-off completed.
- [ ] GO-LIVE: PASS.
