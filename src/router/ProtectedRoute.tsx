import { Navigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from '../lib/auth';

/**
 * Wrap a set of protected routes with `<ProtectedRoute>`.
 *
 * Uses the FusionAuth-based `useAuth` hook to check if the user is
 * authenticated. While the auth state is loading, renders a polished
 * skeleton. If unauthenticated, redirects to `/login`
 * preserving the original URL in the `next` query param.
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const location = useLocation();
  const { loading, isAuthenticated } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col bg-base-100">
        <div className="h-[72px] border-b border-base-300/60 bg-base-100/80" />
        <div className="flex flex-1 items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <span className="loading loading-spinner loading-lg text-primary" />
            <p className="text-sm text-base-content/60">Verificando sesión…</p>
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    const next = location.pathname + location.search;
    return (
      <Navigate
        to={`/login?next=${encodeURIComponent(next)}`}
        replace
      />
    );
  }

  return <>{children}</>;
}
