import * as Sentry from "@sentry/react-native";

const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN?.trim() ?? "";
const environment = process.env.EXPO_PUBLIC_BAYTNA_ENV ?? "development";
const release =
  process.env.EXPO_PUBLIC_BAYTNA_RELEASE ?? "0.50.0";

const parsedRate = Number(
  process.env.EXPO_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? "0.05",
);
const tracesSampleRate =
  Number.isFinite(parsedRate) && parsedRate >= 0 && parsedRate <= 1
    ? parsedRate
    : 0.05;

if (dsn) {
  Sentry.init({
    dsn,
    environment,
    release: "baytna-chef@" + release,
    tracesSampleRate,
    sendDefaultPii: false,
    enableAutoSessionTracking: true,
  });

  Sentry.setTag("baytna.app", "chef");
  Sentry.setTag("baytna.release", release);
}

export function captureAppError(
  error: unknown,
  context?: Record<string, string | number | boolean | null>,
) {
  if (!dsn) return;
  Sentry.withScope((scope) => {
    if (context) {
      scope.setContext("baytna", context);
    }
    Sentry.captureException(error);
  });
}

export function setCrashUser(userId: string | null) {
  if (!dsn) return;
  Sentry.setUser(userId ? { id: userId } : null);
}

export function addOperationalBreadcrumb(
  message: string,
  data?: Record<string, string | number | boolean | null>,
) {
  if (!dsn) return;
  Sentry.addBreadcrumb({
    category: "baytna.operation",
    message,
    level: "info",
    data,
  });
}

export const crashReportingEnabled = Boolean(dsn);
