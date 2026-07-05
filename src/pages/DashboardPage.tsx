import { useNavigate } from 'react-router-dom';
import { queryClient } from '../api/queryClient';
import { useAuth } from '../lib/auth';
import { useUserProfile, initialsFromName } from '../lib/useUserProfile';

export function DashboardPage() {
  const navigate = useNavigate();
  const { logout, refresh } = useAuth();
  const profile = useUserProfile();

  const handleSignOut = async () => {
    await logout();
    queryClient.clear();
    navigate('/auth');
  };

  const handleRefresh = () => {
    void refresh();
  };

  const fallbackName: string = profile.data?.full_name || 'Usuario';

  return (
    <div className="flex flex-col gap-5">
      <div className="mb-2">
        <h1 className="text-2xl font-extrabold text-quien-charcoal">
          Panel de autenticación
        </h1>
      </div>

      {/* Profile card */}
      <div className="max-w-2xl rounded-3xl border border-quien-border bg-white p-6 shadow-card">
        <div className="flex items-center gap-4">
          {profile.data?.picture ? (
            <img
              src={profile.data.picture}
              alt={fallbackName}
              className="h-14 w-14 rounded-full object-cover"
            />
          ) : (
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-quien-green text-lg font-bold text-white">
              {initialsFromName(fallbackName)}
            </span>
          )}
          <div className="flex flex-col gap-1">
            {profile.isLoading && !profile.data ? (
              <span className="text-sm text-quien-charcoal/60">Cargando perfil…</span>
            ) : (
              <>
                <span className="text-xl font-bold text-quien-charcoal">
                  {profile.data?.full_name ?? fallbackName}
                </span>
                {profile.data?.email && (
                  <span className="flex items-center gap-1.5 text-sm text-quien-charcoal/60">
                    ✉ {profile.data.email}
                  </span>
                )}
                <div className="mt-1 flex flex-wrap gap-2">
                  <span className="badge badge-sm rounded-full border-0 bg-quien-green/10 text-quien-green">
                    FusionAuth
                  </span>
                  {profile.data?.email_verified && (
                    <span className="badge badge-sm rounded-full border-0 bg-quien-green/10 text-quien-green">
                      ✓ Email verificado
                    </span>
                  )}
                  {profile.data?.picture && (
                    <span className="badge badge-sm rounded-full border-0 bg-quien-blue/10 text-quien-blue">
                      Con foto
                    </span>
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        {profile.isError && !profile.data && (
          <div className="mt-4 rounded-xl border border-quien-yellow/30 bg-quien-yellow/10 p-3 text-sm text-quien-charcoal/70">
            No se pudo cargar el perfil del backend. Reintentá o volvé a iniciar
            sesión.
          </div>
        )}

        <div className="mt-4 flex gap-2">
          <button
            onClick={handleRefresh}
            className="btn btn-sm rounded-full border-quien-border bg-white text-quien-charcoal hover:border-quien-green hover:text-quien-green"
          >
            Refrescar
          </button>
          <button
            onClick={handleSignOut}
            className="btn btn-sm rounded-full border-0 bg-quien-coral text-white hover:bg-quien-coral/90"
          >
            Cerrar sesión
          </button>
        </div>
      </div>

      {/* Debug info */}
      <div className="max-w-2xl rounded-3xl border border-quien-border bg-white p-6 shadow-card">
        <h2 className="mb-3 text-lg font-bold text-quien-charcoal">
          Información de sesión
        </h2>
        <pre className="overflow-x-auto rounded-xl bg-quien-cream p-4 text-xs text-quien-charcoal/60">
          {JSON.stringify(profile.data, null, 2)}
        </pre>
      </div>
    </div>
  );
}
