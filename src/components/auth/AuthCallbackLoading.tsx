import './AuthCallbackLoading.css';

/**
 * Loading card shown while the backend is processing the
 * FusionAuth OAuth callback (e.g. `/auth/callback`).
 *
 * Renders a centered card with:
 *   - an animated gradient ring
 *   - the primary message `Iniciando sesión` followed by a CSS
 *     animated ellipsis (`.` / `..` / `...`) so the user always
 *     sees motion even before the session is verified
 *   - a smaller helper line in Spanish explaining what is happening
 *
 * The component is intentionally framework-free (no Fluent UI,
 * no Framer Motion) so it can render on the very first paint
 * without waiting for chunk hydration.
 */
export function AuthCallbackLoading() {
  return (
    <div className="auth-callback-loading" role="status" aria-live="polite">
      <div className="auth-callback-loading__ring" aria-hidden="true">
        <span className="auth-callback-loading__ring-spin" />
        <span className="auth-callback-loading__ring-mark" aria-hidden="true">Q</span>
      </div>

      <h3 className="auth-callback-loading__title">
        <span>Iniciando sesi&oacute;n</span>
        <span className="auth-callback-loading__dots" aria-hidden="true" />
      </h3>

      <p className="auth-callback-loading__hint">
        Estamos verificando tu cuenta de Google.
      </p>
    </div>
  );
}

export default AuthCallbackLoading;
