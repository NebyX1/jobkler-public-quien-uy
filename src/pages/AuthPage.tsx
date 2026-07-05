import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { AuthCallbackLoading } from '../components/auth/AuthCallbackLoading';
import './AuthPage.css';

/**
 * True when the current URL belongs to the auth callback route
 * (`/auth/callback`). The backend redirects here after creating
 * the session cookie, and we show a loading state while the
 * frontend verifies the session via `/api/auth/me`.
 */
function isAuthCallbackPath(pathname: string): boolean {
  return /^\/auth\/callback(\/|$)/.test(pathname);
}

const FEATURE_CHIPS = [
  'Oficios y profesionales',
  'Cerca de tu ubicación',
  'Soluciones reales',
  'Rápido y simple',
];

/**
 * `/auth` page.
 *
 * Shows a login button that redirects to the backend
 * `/api/auth/login` endpoint, which starts the FusionAuth OAuth2
 * Authorization Code flow with PKCE.
 *
 * If the user is already signed in, redirects to the main page.
 * During `/auth/callback`, shows a loading state while the
 * session is verified.
 */
export function AuthPage() {
  const navigate = useNavigate();
  const { isAuthenticated, loading, login } = useAuth();
  const [searchParams] = useSearchParams();
  const error = searchParams.get('error');

  const isCallback = isAuthCallbackPath(window.location.pathname);

  useEffect(() => {
    // Detect an existing session and bounce signed-in users away
    // from the auth screen. On the callback route we keep the
    // loading card visible while the session is verified.
    if (!isCallback && isAuthenticated && !loading) {
      navigate('/', { replace: true });
    }
  }, [navigate, isCallback, isAuthenticated, loading]);

  if (isCallback) {
    return (
      <div className="auth-shell">
        <div className="auth-blob auth-blob--one" aria-hidden="true" />
        <div className="auth-blob auth-blob--two" aria-hidden="true" />
        <div className="auth-blob auth-blob--three" aria-hidden="true" />
        <div className="auth-container">
          <section className="auth-card" aria-labelledby="auth-card-title">
            <header className="auth-card__header">
              <h2 id="auth-card-title" className="auth-card__title">
                Iniciando sesión
              </h2>
            </header>
            <div className="auth-card__widget auth-card__widget--callback">
              <AuthCallbackLoading />
            </div>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-shell">
      {/* Decorative blurred shapes for the SaaS-style backdrop. */}
      <div className="auth-blob auth-blob--one" aria-hidden="true" />
      <div className="auth-blob auth-blob--two" aria-hidden="true" />
      <div className="auth-blob auth-blob--three" aria-hidden="true" />

      <div className="auth-container">
        {/* Left: branding / welcome panel. */}
        <section className="auth-brand" aria-labelledby="auth-brand-title">
          <span className="auth-brand__logo">
            <span className="auth-brand__logo-mark" aria-hidden="true">Q</span>
            <span>Quien.uy</span>
          </span>

          <h1 id="auth-brand-title" className="auth-brand__title">
            <span className="auth-brand__title-accent">
              Encontrá a la persona indicada, cerca tuyo.
            </span>
          </h1>

          <p className="auth-brand__subtitle">
            Quien.uy te conecta con personas, oficios y profesionales de tu
            zona para resolver lo que necesitás, de forma simple, rápida y
            segura.
          </p>

          <p className="auth-brand__supporting">
            Desde reparaciones y servicios técnicos hasta bienestar,
            asesoramiento y soluciones cotidianas, Quien.uy es el lugar
            donde encontrar habilidades reales para problemas reales.
          </p>

          <ul className="auth-features" aria-label="Características destacadas">
            {FEATURE_CHIPS.map((label) => (
              <li key={label} className="auth-chip">
                <span className="auth-chip__dot" aria-hidden="true" />
                {label}
              </li>
            ))}
          </ul>

          <p className="auth-brand__footnote">
            Buscá, encontrá y conectá con la solución que necesitás en tu
            zona.
          </p>
        </section>

        {/* Right: auth card with login button. */}
        <section className="auth-card" aria-labelledby="auth-card-title">
          <header className="auth-card__header">
            <h2 id="auth-card-title" className="auth-card__title">
              Ingresá a Quien.uy
            </h2>
            <p className="auth-card__hint">
              Accedé con tu cuenta de Google para empezar a encontrar
              personas con las habilidades que necesitás.
            </p>
          </header>

          <div className="auth-card__widget">
            {error ? (
              <div className="auth-error" role="alert">
                <p>
                  Hubo un problema al iniciar sesión. Intentá de nuevo.
                </p>
                <p className="auth-error__code">
                  Código de error: {error}
                </p>
              </div>
            ) : null}

            <button
              className="auth-login-btn"
              onClick={login}
              type="button"
            >
              <svg className="auth-login-btn__google-icon" viewBox="0 0 24 24" aria-hidden="true">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"/>
              </svg>
              <span>Continuar con Google</span>
            </button>

            <p className="auth-card__footer">
              Al continuar aceptás los términos de servicio y la
              política de privacidad de Quien.uy.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}

export default AuthPage;
