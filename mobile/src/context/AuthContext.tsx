import React, { createContext, useContext, useEffect, useState } from "react";
import { setAuthToken, authApi } from "../lib/api";
import { getItem, removeItem, setItem } from "../lib/storage";
import { initI18n } from "../i18n";

const ACCESS_KEY = "iaare_access";
const REFRESH_KEY = "iaare_refresh";

interface AuthCtx {
  user: any | null;
  booting: boolean;
  isAuthenticated: boolean;
  setSession: (access: string, refresh: string) => Promise<void>;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const Ctx = createContext<AuthCtx>({} as AuthCtx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<any | null>(null);
  const [booting, setBooting] = useState(true);

  async function loadUser() {
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      // try refresh once
      const rt = await getItem(REFRESH_KEY);
      if (rt) {
        try {
          const data = await authApi.refresh(rt);
          await setItem(ACCESS_KEY, data.access_token);
          setAuthToken(data.access_token);
          const me = await authApi.me();
          setUser(me);
          return;
        } catch {}
      }
      setUser(null);
      setAuthToken(null);
      await removeItem(ACCESS_KEY);
      await removeItem(REFRESH_KEY);
    }
  }

  useEffect(() => {
    (async () => {
      await initI18n();
      const token = await getItem(ACCESS_KEY);
      if (token) {
        setAuthToken(token);
        await loadUser();
      }
      setBooting(false);
    })();
  }, []);

  async function setSession(access: string, refresh: string) {
    await setItem(ACCESS_KEY, access);
    await setItem(REFRESH_KEY, refresh);
    setAuthToken(access);
    await loadUser();
  }

  async function logout() {
    await removeItem(ACCESS_KEY);
    await removeItem(REFRESH_KEY);
    setAuthToken(null);
    setUser(null);
  }

  return (
    <Ctx.Provider
      value={{ user, booting, isAuthenticated: !!user, setSession, refresh: loadUser, logout }}
    >
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
