import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { customerApi, tokenStore } from "../api";
import { queryClient } from "../query/queryClient";

type AuthStatus = "loading" | "guest" | "authenticated";
interface AuthContextValue {
  status: AuthStatus;
  reload(): Promise<void>;
  signedIn(): void;
  signOut(): Promise<void>;
}
const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");

  const reload = useCallback(async () => {
    const tokens = await tokenStore.get();
    setStatus(tokens ? "authenticated" : "guest");
  }, []);

  useEffect(() => {
    void reload();
    return tokenStore.subscribe(() => void reload());
  }, [reload]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      reload,
      signedIn: () => {
        queryClient.clear();
        setStatus("authenticated");
      },
      signOut: async () => {
        await customerApi.logout();
        queryClient.clear();
        setStatus("guest");
      },
    }),
    [status, reload],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be inside AuthProvider");
  return value;
}
