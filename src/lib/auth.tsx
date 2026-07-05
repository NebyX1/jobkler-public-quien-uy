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
import { apiClient } from '../api/client';

// ── Types ───────────────────────────────────────────────────────────

export interface AuthUser {
  fusionauth_user_id: string;
  email: string | null;
  email_verified: boolean;
  full_name: string;
  first_name: string | null;
  last_name: string | null;
  picture: string | null;
  roles: string[];
  auth_provider: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: () => void;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// ── Provider ────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    try {
      const res = await apiClient.get<AuthUser>('/api/auth/me');
      setUser(res.data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchMe();
  }, [fetchMe]);

  const login = useCallback(() => {
    // Clear only app-owned auth/user/session cache before starting
    // a fresh Google login. We do NOT clear unrelated user data.
    const authKeyPatterns = [
      'auth',
      'user',
      'session',
      'token',
      'profile',
      'supertokens',
      'fusionauth',
    ];
    const isAuthKey = (key: string) =>
      authKeyPatterns.some((p) => key.toLowerCase().includes(p));

    try {
      for (let i = localStorage.length - 1; i >= 0; i--) {
        const key = localStorage.key(i);
        if (key && isAuthKey(key)) localStorage.removeItem(key);
      }
      for (let i = sessionStorage.length - 1; i >= 0; i--) {
        const key = sessionStorage.key(i);
        if (key && isAuthKey(key)) sessionStorage.removeItem(key);
      }
    } catch {
      // Storage may be unavailable (incognito, etc.) — ignore.
    }

    // Build the backend Google login URL. The forced Google flow must
    // start on Flask so the backend can create state + PKCE and redirect
    // to FusionAuth; do not send the browser to Vite's `/api` origin.
    //
    // The backend endpoint redirects the browser to FusionAuth's
    // `/oauth2/authorize` with `idp_hint=google` and `prompt=login`,
    // forcing a fresh Google login and preventing silent session
    // reuse.
    const apiDomain =
      import.meta.env.VITE_API_BASE_URL ||
      import.meta.env.VITE_AUTH_API_DOMAIN ||
      'http://localhost:5000';
    const base = apiDomain ? apiDomain.replace(/\/$/, '') : '';
    window.location.href = `${base}/api/auth/login/google?force=1`;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.post('/api/auth/logout');
    } catch {
      // ignore — the cookie may already be gone
    }
    setUser(null);
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
    refresh,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ── Hook ────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}