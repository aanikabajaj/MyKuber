import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { REFRESH_KEY, TOKEN_KEY, userApi, UserProfile } from "@/lib/api";

interface AuthCtx {
  user: UserProfile | null;
  loading: boolean;
  isAuthenticated: boolean;
  setSession: (access: string, refresh: string) => Promise<void>;
  refresh: () => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>({} as AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadUser() {
    if (!localStorage.getItem(TOKEN_KEY)) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await userApi.me();
      setUser(me);
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_KEY);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUser();
  }, []);

  async function setSession(access: string, refresh: string) {
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
    setLoading(true);
    await loadUser();
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setUser(null);
  }

  return (
    <Ctx.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        setSession,
        refresh: loadUser,
        logout,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);
