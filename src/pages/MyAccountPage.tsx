import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { FileText, Star, LogOut, Shield } from 'lucide-react';
import { useAuth } from '../lib/auth';
import { initialsFromName } from '../lib/useUserProfile';
import { queryClient } from '../api/queryClient';

/**
 * Account page — shows authenticated user info.
 * Replaces the old DashboardPage.
 */
export function MyAccountPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const displayName = user?.full_name || 'Usuario';
  const initials = initialsFromName(displayName);
  const [imgError, setImgError] = useState(false);

  const handleSignOut = async () => {
    await logout();
    queryClient.clear();
    navigate('/');
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-extrabold text-base-content">Mi cuenta</h1>
        <p className="mt-1 text-sm text-base-content/60">
          Gestioná tu información y accedé a tus secciones.
        </p>
      </div>

      {/* Profile card */}
      <div className="max-w-2xl rounded-[2rem] border border-base-300/70 bg-base-200/50 p-6 shadow-sm sm:p-8">
        <div className="flex items-center gap-5">
          {user?.picture && !imgError ? (
            <img
              key={user.picture}
              src={user.picture}
              alt={displayName}
              className="h-16 w-16 rounded-full object-cover"
              onError={() => setImgError(true)}
            />
          ) : (
            <span className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-xl font-bold text-primary-content">
              {initials}
            </span>
          )}
          <div className="flex flex-col gap-1">
            <span className="text-xl font-bold text-base-content">
              {displayName}
            </span>
            {user?.email && (
              <span className="text-sm text-base-content/60">{user.email}</span>
            )}
            <div className="mt-1 flex flex-wrap gap-2">
              {user?.auth_provider && (
                <span className="badge badge-sm rounded-full border-0 bg-primary/10 text-primary">
                  {user.auth_provider === 'google' ? 'Google' : user.auth_provider}
                </span>
              )}
              {user?.email_verified && (
                <span className="badge badge-sm rounded-full border-0 bg-success/10 text-success">
                  Email verificado
                </span>
              )}
              {user?.roles?.includes('admin') && (
                <span className="badge badge-sm rounded-full border-0 bg-warning/10 text-warning">
                  <Shield className="mr-1 h-3 w-3" /> Admin
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid max-w-2xl gap-4 sm:grid-cols-2">
        <Link
          to="/mi-perfil"
          className="flex items-center gap-4 rounded-[1.5rem] border border-base-300/70 bg-base-100 p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          <div>
            <span className="font-bold text-base-content">Mi perfil</span>
            <p className="text-xs text-base-content/60">
              Creá o editá tu perfil profesional
            </p>
          </div>
        </Link>

        <Link
          to="/mis-reviews"
          className="flex items-center gap-4 rounded-[1.5rem] border border-base-300/70 bg-base-100 p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Star className="h-6 w-6 text-primary" />
          </div>
          <div>
            <span className="font-bold text-base-content">Mis reseñas</span>
            <p className="text-xs text-base-content/60">
              Reseñas que escribiste
            </p>
          </div>
        </Link>
      </div>

      {/* Sign out */}
      <div className="max-w-2xl">
        <button
          onClick={handleSignOut}
          className="btn btn-error btn-sm rounded-full text-primary-content"
        >
          <LogOut className="h-4 w-4" />
          Cerrar sesión
        </button>
      </div>
    </div>
  );
}
