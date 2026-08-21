# Sprint 42 — Crash Reporting

## Scope

Sprint 42 adds Sentry crash/error reporting foundations to:

- Customer App
- Chef App
- Driver App
- Admin Dashboard

Release identifier:

```text
0.42.0
```

## Mobile

Dependency:

```text
@sentry/react-native
```

Each mobile app initializes Sentry at startup only when:

```text
EXPO_PUBLIC_SENTRY_DSN
```

is configured.

Events are tagged with:
- Baytna app role
- environment
- release

Default PII sending is disabled.

Metro is wrapped with Sentry's React Native Metro integration so release builds can produce Sentry-compatible source-map metadata.

### Controlled diagnostics

Each mobile app has a hidden diagnostics route:

```text
/diagnostics
```

The route is useful only when:

```text
EXPO_PUBLIC_BAYTNA_ENABLE_DIAGNOSTICS=true
```

Normal pilot and production profiles set it to false.

A separate EAS profile is provided:

```text
pilot-diagnostics
```

That profile exists only for controlled internal verification.

The diagnostics screen can:
- send a non-fatal event,
- trigger a deliberate JS crash.

Never distribute the diagnostic profile to normal pilot users.

## Admin Dashboard

Dependencies:
- `@sentry/react`
- `@sentry/vite-plugin`

React 19 root error hooks are connected to Sentry when a DSN is configured.

Vite source maps are generated only when the Sentry build credentials are present.

After successful source-map upload, map files are removed from the built artifact.

## Build Credentials

Do not commit:
- `SENTRY_AUTH_TOKEN`
- Firebase credential files
- provider secrets

For EAS, `SENTRY_AUTH_TOKEN` should live in the protected build environment.

For the Admin Dashboard CI build, provide:
- `SENTRY_AUTH_TOKEN`
- `SENTRY_ORG`
- `SENTRY_PROJECT`

as CI secrets/environment values.

The client DSN is not treated as a server secret, but it should still be environment-specific.

## Required live proof

For each app before go-live:

1. Create a diagnostic build.
2. Install it on a pilot device/browser environment.
3. Send the non-fatal test event.
4. Trigger the controlled crash.
5. Confirm the event appears under release `0.42.0`.
6. Confirm the stack trace is symbolicated.
7. Record evidence in `release-evidence.json`.
8. Return to the normal non-diagnostics build profile.

No live Sentry event is claimed by Sprint 42 until those external steps are completed.
