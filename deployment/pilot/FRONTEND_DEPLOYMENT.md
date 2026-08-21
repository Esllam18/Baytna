# Baytna Pilot Frontend Deployment

## Admin Dashboard

The Admin Dashboard is a static Vite build served by Nginx.

Required build-time value:

```text
VITE_BAYTNA_API_BASE_URL=https://pilot-api.example.com
```

Pilot compose:

```bash
cd deployment/pilot
cp .env.frontends.example .env.frontends
docker compose --env-file .env.frontends -f docker-compose.frontends.yml up --build
```

The pilot reverse proxy / TLS termination layer must expose the dashboard over HTTPS.

## Mobile Apps

Three separate Expo applications are prepared for internal Android pilot distribution:

```text
apps/customer_app
apps/chef_app
apps/driver_app
```

Each includes:

```text
eas.json
build.pilot.distribution = internal
android.buildType = apk
```

Before EAS build, configure:

```text
EXPO_PUBLIC_BAYTNA_API_BASE_URL=https://pilot-api.example.com
EXPO_PUBLIC_BAYTNA_ENV=staging
EXPO_PUBLIC_BAYTNA_ENABLE_NATIVE_PUSH=true
```

Build examples:

```bash
cd apps/customer_app
eas build --profile pilot --platform android

cd ../chef_app
eas build --profile pilot --platform android

cd ../driver_app
eas build --profile pilot --platform android
```

## Android Push

Sprint 41 registers the native Android device push token using `expo-notifications`.

The backend FCM provider expects a real FCM registration token.

Pilot requirements:
- physical Android device,
- configured Firebase Android application,
- correct `google-services.json` / Expo native credentials,
- FCM HTTP v1 server credentials on the backend.

The repository intentionally contains no real Firebase credential file.

## iOS Boundary

Sprint 41 does not claim iOS FCM registration.

Raw APNs device tokens are not sent to the FCM HTTP v1 adapter as if they were FCM registration tokens.

A production iOS build requires the chosen Firebase Messaging native registration path and Apple push credentials to be configured and verified separately.

## CORS

Backend staging CORS must include the public Admin Dashboard origin.

Example:

```text
BAYTNA_CORS_ORIGINS=https://pilot-admin.example.com
```
