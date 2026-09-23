import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { ArrowLeft, LogIn } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../lib/auth';
import { authApi } from '../api/auth';
import { Navbar } from '../components/landing/Navbar';
import { Footer } from '../components/landing/Footer';

function safeNext(value: string | null) {
  return value && value.startsWith('/') && !value.startsWith('//') ? value : '/';
}

export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, loginDemo, isAuthenticated, loading } = useAuth();
  const [loginError, setLoginError] = useState('');
  const [pendingKey, setPendingKey] = useState('');
  const next = safeNext(searchParams.get('next'));
  const config = useQuery({ queryKey: ['auth-config'], queryFn: authApi.config, staleTime: 60_000 });
  const accounts = useQuery({
    queryKey: ['demo-accounts'],
    queryFn: authApi.demoAccounts,
    enabled: config.data?.demoEnabled === true,
  });

  const handleDemoLogin = async (key: string) => {
    setLoginError('');
    setPendingKey(key);
    try {
      await loginDemo(key);
      navigate(next, { replace: true });
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'No se pudo iniciar sesión.');
    } finally {
      setPendingKey('');
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-base-100">
      <Navbar />
      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-xl rounded-[2rem] border border-base-300/70 bg-base-200/50 p-8 shadow-sm sm:p-10">
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <LogIn className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-center text-2xl font-extrabold text-base-content">Ingresá a Quien.uy</h1>

          {config.data?.demoEnabled ? (
            <div className="mt-5 rounded-2xl border border-warning/30 bg-warning/10 p-4 text-sm text-base-content">
              <strong>Demostración local.</strong> Las cuentas y perfiles de esta instalación son ficticios.
            </div>
          ) : null}

          {isAuthenticated && !loading ? (
            <div className="mt-6 text-center">
              <p className="text-sm text-base-content/70">Tu sesión ya está activa.</p>
              <button onClick={() => navigate(next)} className="btn btn-primary mt-5 w-full rounded-full">Continuar</button>
            </div>
          ) : config.isLoading ? (
            <p className="mt-6 text-center text-sm text-base-content/60">Consultando opciones de acceso…</p>
          ) : config.data?.demoEnabled ? (
            <div className="mt-6 space-y-3">
              {accounts.isLoading ? <p className="text-sm text-base-content/60">Cargando cuentas de prueba…</p> : null}
              {accounts.data?.map((account) => (
                <button
                  key={account.key}
                  type="button"
                  disabled={Boolean(pendingKey)}
                  onClick={() => void handleDemoLogin(account.key)}
                  className="flex w-full flex-col items-start rounded-2xl border border-base-300/70 bg-base-100 p-4 text-left transition hover:border-primary/50 hover:bg-primary/5 disabled:opacity-60"
                >
                  <span className="font-bold text-base-content">{pendingKey === account.key ? 'Iniciando sesión…' : account.name}</span>
                  <span className="mt-1 text-sm text-base-content/60">{account.description}</span>
                </button>
              ))}
            </div>
          ) : config.data?.mode === 'fusionauth' && config.data.configured ? (
            <div className="mt-6">
              <p className="text-center text-sm leading-relaxed text-base-content/70">Accedé con tu cuenta de FusionAuth.</p>
              <button onClick={login} type="button" className="btn btn-primary mt-5 w-full rounded-full">
                Continuar con Google
              </button>
            </div>
          ) : (
            <div className="mt-6 rounded-2xl border border-base-300 bg-base-100 p-4 text-sm text-base-content/70">
              El acceso con FusionAuth no está configurado. No se activará una cuenta demo automáticamente.
            </div>
          )}

          {loginError ? <p role="alert" className="mt-4 text-sm text-error">{loginError}</p> : null}
          <Link to="/" className="btn btn-ghost mt-6 w-full rounded-full text-base-content/70">
            <ArrowLeft className="h-4 w-4" /> Volver al inicio
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}
