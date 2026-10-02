import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, clearTokens, getAccessToken, setTokens } from "../api/client";
import type { User } from "../api/types";

interface AuthValue {
  user: User | null;
  loading: boolean;
  login: (login: string, password: string) => Promise<void>;
  register: (payload: {
    login: string;
    password: string;
    last_name: string;
    first_name: string;
    middle_name?: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getAccessToken()) {
      setLoading(false);
      return;
    }
    api
      .get<User>("/auth/me")
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (loginName: string, password: string) => {
    const tokens = await api.post<TokenPair>("/auth/login", {
      login: loginName,
      password,
    });
    setTokens(tokens.access_token, tokens.refresh_token);
    setUser(await api.get<User>("/auth/me"));
  }, []);

  const register = useCallback<AuthValue["register"]>(async (payload) => {
    await api.post("/auth/register", payload);
    const tokens = await api.post<TokenPair>("/auth/login", {
      login: payload.login,
      password: payload.password,
    });
    setTokens(tokens.access_token, tokens.refresh_token);
    setUser(await api.get<User>("/auth/me"));
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
