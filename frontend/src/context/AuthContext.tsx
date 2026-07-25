import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, tokenStore } from "../lib/api";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    fullName?: string,
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore the session on first load if a token is present.
  useEffect(() => {
    async function bootstrap() {
      if (!tokenStore.access) {
        setLoading(false);
        return;
      }
      try {
        const { data } = await api.get<User>("/users/me");
        setUser(data);
      } catch {
        tokenStore.clear();
      } finally {
        setLoading(false);
      }
    }
    bootstrap();
  }, []);

  async function login(email: string, password: string) {
    // OAuth2 password flow -> form-encoded body.
    const form = new URLSearchParams({ username: email, password });
    const { data } = await api.post("/auth/login", form);
    tokenStore.set(data.access_token, data.refresh_token);
    const me = await api.get<User>("/users/me");
    setUser(me.data);
  }

  async function register(email: string, password: string, fullName?: string) {
    await api.post("/auth/register", {
      email,
      password,
      full_name: fullName || null,
    });
    await login(email, password);
  }

  function logout() {
    tokenStore.clear();
    setUser(null);
  }

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
