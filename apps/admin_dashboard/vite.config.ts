import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { sentryVitePlugin } from "@sentry/vite-plugin";

const sentryReady = Boolean(
  process.env.SENTRY_AUTH_TOKEN &&
    process.env.SENTRY_ORG &&
    process.env.SENTRY_PROJECT,
);

export default defineConfig({
  plugins: [
    react(),
    ...(sentryReady
      ? [
          sentryVitePlugin({
            org: process.env.SENTRY_ORG,
            project: process.env.SENTRY_PROJECT,
            authToken: process.env.SENTRY_AUTH_TOKEN,
            release: {
              name:
                process.env.SENTRY_RELEASE ??
                `baytna-admin@${process.env.VITE_BAYTNA_RELEASE ?? "0.50.0"}`,
            },
            sourcemaps: {
              filesToDeleteAfterUpload: ["./dist/**/*.map"],
            },
          }),
        ]
      : []),
  ],
  build: {
    sourcemap: sentryReady ? "hidden" : false,
  },
});
