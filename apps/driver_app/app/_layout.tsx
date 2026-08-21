import "../src/observability/sentry";
import React from "react";
import { Stack } from "expo-router";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "../src/query/queryClient";
import { AuthProvider } from "../src/auth/AuthProvider";
import { PushBootstrap } from "../src/notifications/PushBootstrap";

export default function Layout(){
  return <QueryClientProvider client={queryClient}>
    <AuthProvider><PushBootstrap /><Stack screenOptions={{headerShown:false}}/></AuthProvider>
  </QueryClientProvider>;
}
