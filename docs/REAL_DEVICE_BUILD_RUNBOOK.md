# Sprint 42 — Real Device Build Runbook

## Applications

Three independent Android pilot applications:

```text
apps/customer_app
apps/chef_app
apps/driver_app
```

## Required EAS preview environment

Per project configure:

```text
EXPO_PUBLIC_BAYTNA_API_BASE_URL
EXPO_PUBLIC_BAYTNA_ENV=staging
EXPO_PUBLIC_BAYTNA_RELEASE=0.42.0
EXPO_PUBLIC_SENTRY_DSN
GOOGLE_SERVICES_JSON
SENTRY_AUTH_TOKEN
SENTRY_ORG
SENTRY_PROJECT
```

`GOOGLE_SERVICES_JSON` should be an EAS file environment variable.

Do not put the Firebase file in the repository.

## Build normal pilot APK

```bash
cd apps/customer_app
eas build --profile pilot --platform android

cd ../chef_app
eas build --profile pilot --platform android

cd ../driver_app
eas build --profile pilot --platform android
```

## Build diagnostic APK

```bash
eas build --profile pilot-diagnostics --platform android
```

Use diagnostic APKs only to verify:
- push token registration,
- Sentry event ingestion,
- controlled crash reporting,
- source-map symbolication.

## Physical device smoke

For every app:

1. Fresh install.
2. OTP login with correct role.
3. Close/reopen app and confirm session behavior.
4. Verify HTTPS API communication.
5. Accept notification permission.
6. Verify real FCM token registration.
7. Send a test push from Admin integration tooling.
8. Confirm notification receipt.
9. Tap notification and verify route behavior.
10. Run diagnostic Sentry event/crash.
11. Reinstall normal pilot APK after verification.

## Evidence

Store only references, not credentials:

- build URL
- build ID
- device model
- Android version
- timestamp
- tester
- Sentry event/release reference
- push test result

Add these to the live release evidence record.
