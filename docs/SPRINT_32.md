# Sprint 32 — Definition of Done

- [x] Paymob payment provider.
- [x] Paymob Intention request.
- [x] Unified Checkout URL.
- [x] Secret/Public Key configuration.
- [x] Payment methods configuration.
- [x] Billing/item mapping.
- [x] Baytna payment reference mapping.
- [x] Paymob Transaction callback.
- [x] HMAC SHA-512 verification.
- [x] Callback idempotency.
- [x] Provider transaction persistence.
- [x] Success → Baytna payment/order success lifecycle.
- [x] Failure → Baytna payment/order failure lifecycle.
- [x] Amount/currency mismatch protection.
- [x] Refund callback reconciliation.
- [x] Provider status/reference fields.
- [x] Reconciliation issue ledger.
- [x] Admin reconciliation APIs.
- [x] Manual issue resolution.
- [x] Payment reconciliation worker job.
- [x] Pilot profile requires Paymob.
- [x] Staging E2E Paymob-intention gate.
- [x] Production settings validation.
- [x] Alembic migration `0017_sprint32`.
- [x] Full regression suite.

## External boundary
Live Paymob charge/refund verification requires real merchant credentials/payment methods and is not claimed in the local execution environment.

The live refund endpoint remains config-disabled by default until merchant API enablement is confirmed.
