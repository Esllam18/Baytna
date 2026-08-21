# Integration Reconciliation — Sprint 30

## Why
External providers are not transactional with Baytna's DB. A provider can accept a message while the local process crashes, or a delivery receipt can arrive before/after local state catches up.

## Provider Event Ledger
`notification_provider_events` stores every signed receipt idempotently by `(provider, provider_event_id)`.

Normalized receipt:
```json
{"event_id":"...","message_id":"...","status":"accepted|delivered|failed|bounced"}
```

## Reconciliation
The reconciliation job:
1. replays unmatched provider events against known provider message IDs;
2. repairs `succeeded` deliveries that somehow have no provider message ID by moving them to retry;
3. preserves event history for audit/debugging.

## Security
Webhook body is authenticated with HMAC SHA-256 via `BAYTNA_NOTIFICATION_PROVIDER_WEBHOOK_SECRET`.
