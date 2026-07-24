import { Navigate, useSearchParams } from 'react-router-dom';

/**
 * Login required page — legacy redirect.
 *
 * Now redirects to `/login` with the same `next` query param.
 * Kept for backwards compatibility in case any external links
 * point to `/login-required`.
 */
export function LoginRequiredPage() {
  const [searchParams] = useSearchParams();
  const next = searchParams.get('next') || '/';
  return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />;
}
