# Sprint 41 — Pilot Readiness

## Automated Gate

Passed locally:
- backend regression
- API compile
- OpenAPI contract
- cross-app integration journey
- media attachment flows
- universal push device routes
- frontend static integration
- frontend syntax/transpile
- deployment preflight
- migration chain
- worker smoke

## Live Pilot Gate — Still Required

Before real 6 October pilot traffic:

1. Deploy PostgreSQL staging.
2. Configure S3-compatible storage.
3. Configure Paymob test/live merchant credentials.
4. Configure Firebase Android apps.
5. Configure FCM HTTP v1 server credentials.
6. Build Customer APK.
7. Build Chef APK.
8. Build Driver APK.
9. Install APKs on physical pilot devices.
10. Register real FCM tokens from all three roles.
11. Verify push reception/tap routing.
12. Deploy Admin Dashboard over HTTPS.
13. Run `scripts/staging_cross_app_e2e.py`.
14. Execute a real Paymob sandbox/pilot payment manually.
15. Verify payment webhook source-of-truth transition.
16. Complete Chef fulfillment.
17. Complete Driver delivery with real proof.
18. Verify Customer tracking/review/support.
19. Verify Admin order/support/finance visibility.
20. Sign off go-live gates.

Sprint 41 supplies the software/runbook foundations but does not claim these external/live steps have occurred.
