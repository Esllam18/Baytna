# Sprint 43 — SLA & Incident Rules

## Chef Acceptance

Source:

```text
chef_order_fulfillments.acceptance_deadline_at
```

Condition:

```text
stage = new
AND acceptance_deadline_at < now
```

Severity:
- initial breach: high
- larger breach: critical

## Driver Assignment

Source:

```text
delivery_tasks
```

Condition:

```text
status = unassigned
AND age > OPS_DELIVERY_ASSIGNMENT_SLA
```

Default:

```text
10 minutes
```

Severity:
- first SLA window: high
- two SLA windows or more: critical

## Delivery Issue

Condition:

```text
delivery_tasks.status = delivery_issue
```

Severity:

```text
high
```

## Support

Defaults:

```text
urgent = 15 minutes
high   = 60 minutes
normal = 240 minutes
```

Severity:
- urgent → critical
- high → high
- normal → warning

## Financial Reconciliation

Any open:

```text
payment_reconciliation_issues
```

becomes critical.

Reason: financial state should not be silently treated as trustworthy while provider/Baytna reconciliation is unresolved.

## Reliability

Critical:
- Outbox dead letter
- Background Job dead letter
- stale worker

High:
- Notification Delivery dead letter

## Fingerprints

Each incident has a stable fingerprint, for example:

```text
chef_acceptance:<order_id>
delivery_assignment:<task_id>
support_sla:<ticket_id>
outbox_dead:<event_id>
```

This avoids duplicate incidents every minute.

## Sensitive Data

Incident JSON may contain:
- internal IDs,
- status,
- SLA timings,
- provider transaction references where operationally required.

It must not contain:
- card data,
- OTP,
- access token,
- refresh token,
- provider secret,
- raw notification token,
- raw customer phone.
