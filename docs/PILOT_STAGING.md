# Sprint 31 — Pilot / Staging Validation

## Goal
Make a staging deployment verifiable before the 6 October pilot without pretending external credentials exist inside the repository.

## Configuration
Copy:
`.env.pilot.example → .env.pilot`

Required real pilot integrations:
- PostgreSQL
- S3-compatible object storage
- Firebase Cloud Messaging
- Twilio SMS

Payment remains mock in Sprint 31 and is explicitly called out.

## Offline preflight
```bash
cd backend
python ../scripts/pilot_preflight.py
```

Validates configuration shape without contacting vendors.

## Live preflight
```bash
python ../scripts/pilot_preflight.py --live
```

Checks:
- PostgreSQL `SELECT 1`
- S3 `HeadBucket`
- FCM OAuth token refresh
- Twilio account API credentials

No SMS or Push message is sent by preflight.

## Staging E2E
Environment variables:
- `BAYTNA_STAGING_BASE_URL`
- `BAYTNA_STAGING_CUSTOMER_BEARER_TOKEN`
- `BAYTNA_STAGING_ADMIN_BEARER_TOKEN`
- optional `BAYTNA_STAGING_FCM_DEVICE_TOKEN`
- optional `BAYTNA_STAGING_TEST_SMS=true`

Run:
```bash
python scripts/staging_e2e.py
```

Flow:
1. readiness
2. authenticated customer
3. signed media upload + completion
4. device/preferences
5. admin integration status
6. optional real push/SMS dispatch

## CI
`.github/workflows/staging-validation.yml`

This workflow is manual and uses protected GitHub Environment secrets.

Real external delivery is only claimed after that staging workflow is run with valid provider credentials and real test targets.
