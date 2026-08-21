import "../src/observability/sentry";
import React from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { Stack } from "expo-router";
import { queryClient } from "../src/query/queryClient";
import { AuthProvider } from "../src/auth/AuthProvider";
import { PushBootstrap } from "../src/notifications/PushBootstrap";
import { RouteGuard } from "../src/auth/RouteGuard";

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <PushBootstrap />
        <RouteGuard>
          <Stack screenOptions={{ headerShown: false, animation: "slide_from_left" }} />
        </RouteGuard>
      </AuthProvider>
    </QueryClientProvider>
  );
}
