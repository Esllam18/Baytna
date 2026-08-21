# Sprint 30 — Definition of Done
- [x] Dish managed-media binding.
- [x] Support attachments.
- [x] Delivery photo proof media binding.
- [x] Notification template persistence.
- [x] Safe fallback rendering.
- [x] Admin template management.
- [x] Provider webhook HMAC verification.
- [x] Provider-event idempotency.
- [x] Delivery receipt matching.
- [x] Failure receipt retry/dead-letter mapping.
- [x] Late-event reconciliation.
- [x] Broken succeeded-delivery repair.
- [x] Worker reconciliation job.
- [x] Admin manual reconcile.
- [x] Alembic migration.
- [x] Regression tests.

## External boundary
Real FCM/APNs/SMS provider receipt payloads vary by vendor. Sprint 30 implements the normalized Baytna receipt contract and generic signed webhook boundary; vendor-specific translators belong in Sprint 31.
