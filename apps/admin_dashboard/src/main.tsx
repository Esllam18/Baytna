import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./query";
import { AuthProvider } from "./auth/AuthProvider";
import { App } from "./App";
import { Sentry, sentryEnabled } from "./observability/sentry";
import "./styles.css";

const container = document.getElementById("root");
if (!container) throw new Error("Baytna admin root element is missing.");

const root = sentryEnabled
  ? createRoot(container, {
      onUncaughtError: Sentry.reactErrorHandler(),
      onCaughtError: Sentry.reactErrorHandler(),
      onRecoverableError: Sentry.reactErrorHandler(),
    })
  : createRoot(container);

root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
