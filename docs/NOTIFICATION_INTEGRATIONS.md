# Sprint 29 — Notification Delivery Providers

## Durable Notification vs External Delivery
`notifications` remains the in-app source of truth.

External delivery is separate:
`notification_deliveries`

One in-app notification may generate:
- zero external deliveries
- one SMS
- one or more pushes for active devices

## Push Devices
The raw provider token is never exposed by read APIs.

At rest:
- SHA-256 hash for uniqueness
- encrypted ciphertext for provider use

Encryption is derived from:
`BAYTNA_INTEGRATION_ENCRYPTION_SECRET`

## Preferences
Per user:
- push_enabled
- sms_enabled
- order_updates
- support_updates
- marketing_enabled

Defaults:
- push ON
- SMS OFF
- transactional order/support ON
- marketing OFF

## Planning
NotificationService creates durable external-delivery rows inside the same database transaction when a notification is emitted.

This means business events do not make external HTTP calls during checkout/delivery/support transactions.

## Worker Dispatch
Background job:
`notifications.dispatch`

Workflow:
```text
pending/retry
   ↓ claim
processing
   ↓ provider success
succeeded

provider error
   ↓
retry
   ↓ max attempts
dead_letter
```

PostgreSQL workers use `FOR UPDATE SKIP LOCKED` through the same worker pattern used elsewhere.

## Providers

Development:
- LoggingPushProvider
- LoggingSmsProvider

Production-capable generic adapters:
- HttpPushProvider
- HttpSmsProvider

The HTTP provider contract sends JSON to a configured external adapter/gateway.

This keeps Baytna vendor-neutral. An FCM/Twilio/Vodafone-specific adapter can later implement the same interface.

## SMS policy
SMS is intentionally limited to selected important kinds even when enabled, to control cost and avoid noisy UX.
