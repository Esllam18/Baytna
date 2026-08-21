# Sprint 44 — Escalation Automation

## Promise-risk detector

An active order with a delivery promise enters the Control Room warning zone when:

```text
promised_delivery_window_end_at
<=
now + OPS_DELIVERY_PROMISE_WARNING_MINUTES
```

Default:

```text
20 minutes
```

### Before deadline

```text
severity = high
```

### After deadline

```text
severity = critical
```

Fingerprint:

```text
delivery_promise:<order_id>
```

## Automatic incident escalation

Unacknowledged incidents escalate after:

```text
OPS_INCIDENT_AUTO_ESCALATE_MINUTES
```

Default:

```text
15
```

Progression:

```text
info → warning → high → critical
```

The next escalation uses the previous auto-escalation timestamp, allowing multiple controlled escalation steps for a long-running unowned incident.

## Acknowledgement

Once an Admin acknowledges the incident:

```text
status = acknowledged
```

automatic escalation stops.

The source detector still refreshes the incident and may independently increase the detected severity, for example when a near-deadline delivery becomes actually late.

## Notification threshold

Default:

```text
OPS_NOTIFICATION_MIN_SEVERITY=high
```

At or above this threshold Baytna emits an Admin notification for important incident lifecycle events.

## Durable notification pipeline

```text
Operations Incident
↓
NotificationService
↓
notification
↓
notification_delivery
↓
existing provider worker
↓
FCM when configured
```

No provider credential is stored in the incident.

No live FCM result is claimed without a real Admin device.
