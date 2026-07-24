import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { LogIn, ArrowLeft, User, FileText } from 'lucide-react';
import { useAuth } from '../lib/auth';
import { Navbar } from '../components/landing/Navbar';
import { Footer } from '../components/landing/Footer';

/**
 * `/login` page.
 *
 * Shows a polished login panel. Reads `next` query param to preserve
 * the intended destination after login. OAuth only starts when the
 * user explicitly clicks "Continuar con Google".
 *
 * If the user is already authenticated, shows navigation options
 * instead of the login button.
 */
export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, isAuthenticated, loading } = useAuth();
  const next = searchParams.get('next') || '/';

  // If already authenticated, show options instead of login
  if (!loading && isAuthenticated) {
    return (
      <div className="flex min-h-screen flex-col bg-base-100">
        <Navbar />
        <main className="flex flex-1 items-center justify-center px-4 py-12">
          <div className="w-full max-w-md rounded-[2rem] border border-base-300/70 bg-base-200/50 p-8 text-center shadow-sm sm:p-10">
            <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-success/10">
              <LogIn className="h-8 w-8 text-success" />
            </div>

            <h1 className="text-2xl font-extrabold text-base-content">
              Ya iniciaste sesión
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-base-content/70">
              Tu sesión ya está activa en Quien.uy.
            </p>

            <div className="mt-8 flex flex-col gap-3">
              <button
                onClick={() => navigate(next)}
                className="btn btn-primary w-full rounded-full"
              >
                Continuar
              </button>
              <button
                onClick={() => navigate('/mi-cuenta')}
                className="btn btn-outline w-full rounded-full border-base-300 text-base-content"
              >
                <User className="h-4 w-4" />
                Ir a mi cuenta
              </button>
              <button
                onClick={() => navigate('/mi-perfil')}
                className="btn btn-ghost w-full rounded-full text-base-content/70"
              >
                <FileText className="h-4 w-4" />
                Ir a mi perfil
              </button>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  // Login form — OAuth starts only on explicit click
  const handleGoogleLogin = () => {
    login();
  };

  return (
    <div className="flex min-h-screen flex-col bg-base-100">
      <Navbar />
      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-md rounded-[2rem] border border-base-300/70 bg-base-200/50 p-8 text-center shadow-sm sm:p-10">
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <LogIn className="h-8 w-8 text-primary" />
          </div>

          <h1 className="text-2xl font-extrabold text-base-content">
            Ingresá a Quien.uy
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-base-content/70">
            Accedé con tu cuenta de Google para empezar a encontrar
            personas con las habilidades que necesitás.
          </p>

          <div className="mt-8 flex flex-col gap-3">
            <button
              onClick={handleGoogleLogin}
              type="button"
              className="btn btn-primary w-full rounded-full"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"/>
              </svg>
              Continuar con Google
            </button>
            <Link
              to="/"
              className="btn btn-ghost w-full rounded-full text-base-content/70"
            >
              <ArrowLeft className="h-4 w-4" />
              Volver al inicio
            </Link>
          </div>

          <p className="mt-6 text-xs text-base-content/50">
            Al continuar aceptás los términos de servicio y la política de
            privacidad de Quien.uy.
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
