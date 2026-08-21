import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { queryClient } from "../query/queryClient";
import { chefApi, tokenStore } from "../api";
import { ApiClientError } from "../api/http";

type AuthContextValue = {
  ready: boolean;
  authenticated: boolean;
  reload(): Promise<void>;
  signOut(): Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);

  const reload = useCallback(async () => {
    try {
      const pair = await tokenStore.get();
      if (!pair) {
        setAuthenticated(false);
        return;
      }

      try {
        await chefApi.profile();
        setAuthenticated(true);
      } catch (error) {
        if (
          error instanceof ApiClientError &&
          (error.status === 401 || error.status === 403)
        ) {
          await tokenStore.clear();
          setAuthenticated(false);
        } else {
          // Keep the local session during a temporary LAN/backend outage.
          setAuthenticated(true);
        }
      }
    } catch {
      setAuthenticated(false);
    } finally {
      setReady(true);
    }
  }, []);

  const signOut = useCallback(async () => {
    await chefApi.logout();
    queryClient.clear();
    setAuthenticated(false);
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const value = useMemo<AuthContextValue>(
    () => ({ ready, authenticated, reload, signOut }),
    [ready, authenticated, reload, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider missing");
  return value;
}
