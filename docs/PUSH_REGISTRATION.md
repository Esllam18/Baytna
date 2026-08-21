# Sprint 41 — Push Registration

## Backend Contract

Role-neutral authenticated routes:

```text
/api/v1/notifications/devices
/api/v1/notifications/preferences
```

These sit alongside the older customer-namespaced compatibility routes.

## Android Mobile Flow

```text
Authenticated App
  ↓
Physical Android device?
  ↓ yes
Notification permission
  ↓ granted
Android notification channel
  ↓
getDevicePushTokenAsync()
  ↓
POST /notifications/devices
```

Stored metadata:
- platform
- encrypted token
- device name
- app version
- active state
- last seen time

## Notification Tap

When a push notification payload includes:

```json
{
  "route": "/orders/..."
}
```

the app can route the authenticated user to that in-app location.

The backend still controls which notification content/event is generated.

## Failure Behavior

Push registration is best effort.

A token/permission/network failure:
- does not log the user out,
- does not block app startup,
- can retry on a later authenticated application start.

## iOS

The current backend FCM adapter expects an FCM registration token.

Sprint 41 does not pretend that an APNs device token is the same thing.

iOS production support requires the Firebase Messaging native registration path to be configured and validated before launch.
