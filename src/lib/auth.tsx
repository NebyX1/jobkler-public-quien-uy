/**
 * FusionAuth-based authentication context for the Quien.uy frontend.
 *
 * Architecture:
 *   - The frontend does NOT talk to Google directly.
 *   - The frontend does NOT store OAuth tokens in localStorage.
 *   - Login is handled by navigating to the backend `/api/auth/login`
 *     endpoint, which redirects to FusionAuth.
 *   - After FusionAuth redirects back to the backend callback, the
 *     backend creates an HTTP-only session cookie and redirects to
 *     the frontend.
 *   - The frontend calls `/api/auth/me` to know the current user.
 *   - Logout calls `POST /api/auth/logout` to clear the session cookie.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import { authApi } from '../api/auth';
import { queryClient } from '../api/queryClient';

// ── Types ───────────────────────────────────────────────────────────

export interface AuthUser {
  id: string;
  fusionauth_user_id: string;
  email: string | null;
  email_verified: boolean;
  full_name: string;
  first_name: string | null;
  last_name: string | null;
  picture: string | null;
  roles: string[];
  auth_provider: string;
  has_profile: boolean;
  is_demo: boolean;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: () => void;
  logout: () => Promise<void>;
  loginDemo: (key: string) => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ── Provider ────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    try {
      setUser(await authApi.me());
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const request = window.setTimeout(() => void fetchMe(), 0);
    return () => window.clearTimeout(request);
  }, [fetchMe]);

  const login = useCallback(() => {
    window.location.assign('/api/auth/login/google');
  }, []);

  const loginDemo = useCallback(async (key: string) => {
    queryClient.clear();
    const nextUser = await authApi.loginDemo(key);
    setUser(nextUser);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // ignore — the cookie may already be gone
    }
    setUser(null);
    queryClient.clear();
  }, []);

  const refresh = useCallback(async () => {
    await fetchMe();
  }, [fetchMe]);

  const value: AuthContextValue = {
    user,
    loading,
    isAuthenticated: user !== null,
    login,
    logout,
    loginDemo,
    refresh,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ── Hook ────────────────────────────────────────────────────────────

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
