import { useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { useUserProfile, initialsFromName } from '../lib/useUserProfile';
import { queryClient } from '../api/queryClient';

/**
 * Navbar for the authenticated app layout.
 * Uses Tailwind/DaisyUI classes instead of Fluent UI.
 */
export function Navbar() {
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuth();
  const profile = useUserProfile();

  const displayName =
    profile.data?.full_name || (isAuthenticated ? 'Usuario' : 'Invitado');
  const email = profile.data?.email || '';
  const picture = profile.data?.picture || undefined;
  const initials = initialsFromName(displayName);

  const handleLogout = async () => {
    await logout();
    queryClient.clear();
    navigate('/auth');
  };

  return (
    <header className="sticky top-0 z-50 border-b border-base-300/60 bg-base-100/80 backdrop-blur-lg">
      <nav className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <a href="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary font-extrabold text-primary-content shadow-sm">
            Q
          </span>
          <span className="text-lg font-extrabold tracking-tight text-base-content">
            Quien<span className="text-primary">.uy</span>
          </span>
        </a>

        {/* User section */}
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <div className="hidden flex-col items-end sm:flex">
              <span className="max-w-[220px] truncate text-sm font-semibold text-base-content">
                {displayName}
              </span>
              {email && (
                <span className="max-w-[220px] truncate text-xs text-base-content/60">
                  {email}
                </span>
              )}
            </div>
          ) : (
            <span className="text-sm text-base-content/70">Invitado</span>
          )}

          {/* Avatar dropdown */}
          <div className="dropdown dropdown-end">
            <div
              tabIndex={0}
              role="button"
              className="btn btn-circle btn-ghost btn-sm"
              aria-label="Menú de usuario"
            >
              {picture ? (
                <img
                  src={picture}
                  alt={displayName}
                  className="h-8 w-8 rounded-full object-cover"
                />
              ) : (
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-content">
                  {initials}
                </span>
              )}
            </div>
            <ul
              tabIndex={0}
              className="menu dropdown-content z-[60] mt-2 w-56 rounded-2xl border border-base-300 bg-base-100 p-2 shadow-soft"
            >
              <li className="pointer-events-none">
                <span className="flex flex-col gap-0">
                  <span className="font-semibold text-base-content">{displayName}</span>
                  {email && (
                    <span className="text-xs text-base-content/60">{email}</span>
                  )}
                </span>
              </li>
              <li>
                <button
                  onClick={handleLogout}
                  className="rounded-xl text-error hover:bg-error/10"
                >
                  Cerrar sesión
                </button>
              </li>
            </ul>
          </div>
        </div>
      </nav>
    </header>
  );
}
