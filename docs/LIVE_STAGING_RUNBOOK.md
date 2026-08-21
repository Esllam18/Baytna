# Sprint 42 — Live Staging Runbook

## Phase 1 — Deploy

1. Deploy PostgreSQL.
2. Run Alembic through `0017_sprint32`.
3. Deploy API `0.42.0`.
4. Stamp `BAYTNA_RELEASE_COMMIT`.
5. Deploy worker from the same commit.
6. Deploy Admin Dashboard from the same release.
7. Configure S3 storage.
8. Configure FCM.
9. Configure Twilio.
10. Configure Paymob.

## Phase 2 — Probe

Run:

```bash
python scripts/live_release_probe.py \
  --api https://pilot-api.example.com \
  --expected-release 0.42.0 \
  --expected-environment staging
```

The probe blocks on:
- failed readiness,
- wrong release,
- wrong environment,
- missing commit stamp,
- outbox dead letters,
- worker job dead letters.

## Phase 3 — Device integrations

Verify Customer, Chef and Driver on physical Android devices:
- native FCM token registration,
- real push receipt,
- notification tap routing,
- Sentry diagnostic event,
- controlled crash + symbolication.

## Phase 4 — Payment

Create a real merchant-approved pilot/sandbox order.

Do not manually force Baytna payment state.

Verify:
1. Paymob intention.
2. Checkout.
3. Transaction callback.
4. HMAC validation.
5. Baytna payment success.
6. Order confirmed.
7. Reconciliation has no mismatch.

## Phase 5 — Cross-app journey

Run the cross-app live validator with protected role tokens and the paid order ID:

```bash
python scripts/staging_cross_app_e2e.py
```

The validator requires an explicit delivery proof reference before it may complete a real staging delivery.

## Phase 6 — Support and Admin

Verify:
- Customer support attachment upload,
- Admin sees linked ticket,
- Admin response,
- Customer sees response,
- audit trail exists,
- finance view sees captured payment.

## Phase 7 — Evidence and go-live gate

Create:

```text
deployment/pilot/release-evidence.json
```

from the example template.

Then run:

```bash
python scripts/go_live_gate.py \
  deployment/pilot/release-evidence.json
```

A failed or missing proof keeps the release blocked.
