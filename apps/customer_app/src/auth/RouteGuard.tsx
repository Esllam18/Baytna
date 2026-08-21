import React, { useEffect } from "react";
import { router, useSegments } from "expo-router";
import { useAuth } from "./AuthProvider";

export function RouteGuard({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const segments = useSegments();

  useEffect(() => {
    if (status === "loading") return;
    const inAuth = segments[0] === "auth";
    if (status === "guest" && !inAuth) {
      router.replace("/auth/phone");
    } else if (status === "authenticated" && inAuth) {
      router.replace("/home");
    }
  }, [status, segments]);

  return <>{children}</>;
}
