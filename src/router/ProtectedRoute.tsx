import { Navigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from '../lib/auth';

/**
 * Wrap a set of protected routes with `<ProtectedRoute>`.
 *
 * Uses the FusionAuth-based `useAuth` hook to check if the user is
 * authenticated. While the auth state is loading, renders nothing
 * to avoid a flash of protected UI. If unauthenticated, redirects
 * to `/auth` (the login page), preserving the original URL in
 * `history.state` so we could send users back after sign-in.
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const location = useLocation();
  const { loading, isAuthenticated } = useAuth();

  if (loading) {
    // Auth check is in-flight; render nothing to avoid a flash.
    return null;
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/auth"
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  return <>{children}</>;
}