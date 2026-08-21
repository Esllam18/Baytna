# Reliability Domain — Sprint 27

## 1. Why Transactional Outbox?
A domain transaction must not do this:

```text
commit order
→ try to publish external event
→ process crashes
```

because the order can be committed while the event is lost.

Sprint 27 writes the Outbox row **inside the same SQL transaction** as the domain change:

```text
Domain rows + Outbox row → COMMIT
```

A separate worker publishes later.

## 2. Outbox state machine

```text
pending
  ↓ claim
processing
  ├─ success → published
  └─ failure → retry
                  ↓ max attempts
              dead_letter
```

Stale `processing` locks are returned to `retry`.

## 3. Concurrency
PostgreSQL claim path uses:

```sql
SELECT ... FOR UPDATE SKIP LOCKED
```

This allows multiple worker processes without the same pending event/job being claimed normally by two workers.

SQLite tests use a safe single-process fallback; they do not prove PostgreSQL locking behavior.

## 4. Background jobs
Durable jobs include:
- expired inventory holds
- expired special-order quotes
- expired pending payment intents
- expired OTP/auth-session cleanup

Every minute-bucket scheduling call uses an idempotency key, preventing duplicate maintenance jobs for the same job type/minute.

## 5. Retry policy
Both jobs and outbox events use bounded exponential backoff:

```text
base * 2^(attempt-1)
```

with a one-hour cap.

After `max_attempts`, the item becomes `dead_letter` and requires an explicit operational retry after investigation.

## 6. Worker heartbeat
Each worker records:
- status
- started time
- last seen time
- processed jobs
- published events
- last error

This supports operational dashboards and stale-worker detection later.

## 7. Publisher boundary
Current publisher is `logging` only.

That is intentional. Reliability is implemented at the database boundary now, without hard-coding a broker decision.

Future adapters can implement:
- SQS
- Kafka
- RabbitMQ
- provider webhook fanout

## 8. API transaction safety
`get_db()` now rolls back the SQLAlchemy session if the request path raises an exception before closing the session.

## 9. Operational APIs
Admin-only:
- reliability summary
- outbox inspection
- background-job inspection
- dead-letter retry
- manual worker tick

These are operational controls, not customer-facing APIs.
