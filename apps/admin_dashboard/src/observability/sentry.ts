import * as Sentry from "@sentry/react";

const dsn = import.meta.env.VITE_SENTRY_DSN?.trim() ?? "";
const environment = import.meta.env.VITE_BAYTNA_ENV ?? "development";
const release = import.meta.env.VITE_BAYTNA_RELEASE ?? "0.50.0";

const parsedRate = Number(
  import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? "0.02",
);
const tracesSampleRate =
  Number.isFinite(parsedRate) && parsedRate >= 0 && parsedRate <= 1
    ? parsedRate
    : 0.02;

if (dsn) {
  Sentry.init({
    dsn,
    environment,
    release: `baytna-admin@${release}`,
    tracesSampleRate,
    sendDefaultPii: false,
  });
  Sentry.setTag("baytna.app", "admin");
  Sentry.setTag("baytna.release", release);
}

export const sentryEnabled = Boolean(dsn);

export function captureAdminError(
  error: unknown,
  context?: Record<string, string | number | boolean | null>,
) {
  if (!dsn) return;
  Sentry.withScope((scope) => {
    if (context) scope.setContext("baytna", context);
    Sentry.captureException(error);
  });
}

export { Sentry };
