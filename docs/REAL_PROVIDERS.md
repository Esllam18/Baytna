# Sprint 31 — Real Provider Adapters

## FCM

Provider:
`FCMPushProvider`

Protocol:
```text
POST https://fcm.googleapis.com/v1/projects/{project_id}/messages:send
Authorization: Bearer <OAuth2 access token>
```

Credentials:
1. `BAYTNA_FCM_CREDENTIALS_FILE`, or
2. Google Application Default Credentials / workload identity.

The provider sends:
- registration token
- notification title/body
- string-normalized data payload

### Invalid tokens
FCM `UNREGISTERED` is classified as permanent.

Result:
- notification delivery → dead_letter
- push device → inactive

That prevents endless retry loops for dead app installations.

## Twilio

Provider:
`TwilioSmsProvider`

Protocol:
```text
POST /2010-04-01/Accounts/{AccountSid}/Messages.json
```

Uses:
- To
- Body
- From OR MessagingServiceSid
- StatusCallback

## Twilio callback
Endpoint:
`POST /api/v1/notifications/vendor-webhooks/twilio/status`

Twilio sends `application/x-www-form-urlencoded`.

Validation uses:
- exact configured callback URL
- all callback parameters
- `X-Twilio-Signature`
- Twilio Auth Token

The callback is translated into Sprint 30's normalized provider-event ledger.

## Provider state
`notification_deliveries` now records:
- provider_status
- provider_error_code
- provider_updated_at

This makes admin/reconciliation output useful with real vendors.
