import { useState } from 'react';
import { Link, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { Menu, X, User, FileText, Star, LogOut } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { useAuth } from '../../lib/auth';
import { initialsFromName } from '../../lib/useUserProfile';
import { queryClient } from '../../api/queryClient';
import { useQuery } from '@tanstack/react-query';
import { authApi } from '../../api/auth';

const NAV_LINKS = [
  { label: 'Buscar', href: '/buscar' },
  { label: 'Búsqueda Avanzada', href: '/buscar/avanzada' },
  { label: 'Categorías', href: '#categorias' },
  { label: 'Cómo funciona', href: '#como-funciona' },
  { label: 'Cerca de vos', href: '/cerca-de-mi' },
];

export function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [imgError, setImgError] = useState(false);
  const { user, isAuthenticated, loading, logout } = useAuth();
  const { data: authConfig } = useQuery({ queryKey: ['auth-config'], queryFn: authApi.config, staleTime: 60_000 });

  const displayName = user?.full_name || 'Usuario';
  const picture = user?.picture || undefined;
  const initials = initialsFromName(displayName);

  const handleLogout = async () => {
    await logout();
    queryClient.clear();
    setDrawerOpen(false);
    navigate('/');
  };

  /**
   * Navigate to the login page. Never call login() or start OAuth
   * directly from the navbar. The login page will handle OAuth
   * only after an explicit user click.
   */
  const goToLogin = (nextPath?: string) => {
    const next = nextPath || `${location.pathname}${location.search}`;
    navigate(`/login?next=${encodeURIComponent(next)}`);
  };

  const handlePublishClick = () => {
    if (isAuthenticated) {
      navigate('/mi-perfil');
    } else {
      goToLogin('/mi-perfil');
    }
  };

  const handleAdvancedSearchClick = () => {
    const destination = '/buscar/avanzada';
    if (isAuthenticated) navigate(destination);
    else goToLogin(destination);
    setDrawerOpen(false);
  };

  return (
    <header className="sticky top-0 z-50 border-b border-base-300/60 bg-base-100/80 backdrop-blur-xl">
      {authConfig?.demoBanner ? (
        <div className="bg-warning/15 px-4 py-1.5 text-center text-xs font-semibold text-base-content">
          Demostración local · datos ficticios · los contactos de la semilla no inician comunicaciones reales
        </div>
      ) : null}
      <nav className="mx-auto grid h-[72px] max-w-7xl grid-cols-2 items-center gap-4 px-4 sm:px-6 lg:grid-cols-[auto_1fr_auto] lg:px-8">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-sm font-extrabold text-primary-content shadow-sm">
            Q
          </span>
          <span className="text-lg font-extrabold tracking-tight text-base-content">
            Quien<span className="text-primary">.uy</span>
          </span>
        </Link>

        {/* Desktop links — centered */}
        <div className="hidden items-center justify-center gap-8 lg:flex">
          {NAV_LINKS.map((link) =>
            link.href.startsWith('#') ? (
              <a
                key={link.href}
                href={link.href}
                className="text-sm font-semibold text-base-content/70 transition-colors hover:text-primary"
              >
                {link.label}
              </a>
            ) : link.href === '/buscar/avanzada' ? (
              <button
                key={link.href}
                type="button"
                onClick={handleAdvancedSearchClick}
                className="text-sm font-semibold text-base-content/70 transition-colors hover:text-primary"
              >
                {link.label}
              </button>
            ) : (
              <NavLink
                key={link.href}
                to={link.href}
                className="text-sm font-semibold text-base-content/70 transition-colors hover:text-primary"
              >
                {link.label}
              </NavLink>
            )
          )}
        </div>

        {/* Desktop actions */}
        <div className="hidden items-center justify-end gap-2 lg:flex">
          <ThemeToggle />
          {!loading && isAuthenticated ? (
            <div className="dropdown dropdown-end">
              <div
                tabIndex={0}
                role="button"
                className="btn btn-circle btn-ghost btn-sm"
                aria-label="Menú de usuario"
              >
                {picture && !imgError ? (
                  <img
                    key={picture}
                    src={picture}
                    alt={displayName}
                    className="h-8 w-8 rounded-full object-cover"
                    onError={() => setImgError(true)}
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
                    {user?.email && (
                      <span className="text-xs text-base-content/60">{user.email}</span>
                    )}
                  </span>
                </li>
                <div className="divider my-1" />
                <li>
                  <button
                    onClick={() => navigate('/mi-cuenta')}
                    className="rounded-xl text-base-content/70 hover:bg-base-200"
                  >
                    <User className="h-4 w-4" />
                    Mi cuenta
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => navigate('/mi-perfil')}
                    className="rounded-xl text-base-content/70 hover:bg-base-200"
                  >
                    <FileText className="h-4 w-4" />
                    Mi perfil
                  </button>
                </li>
                <li>
                  <button
                    onClick={() => navigate('/mis-reviews')}
                    className="rounded-xl text-base-content/70 hover:bg-base-200"
                  >
                    <Star className="h-4 w-4" />
                    Mis reseñas
                  </button>
                </li>
                <div className="divider my-1" />
                <li>
                  <button
                    onClick={handleLogout}
                    className="rounded-xl text-error hover:bg-error/10"
                  >
                    <LogOut className="h-4 w-4" />
                    Salir
                  </button>
                </li>
              </ul>
            </div>
          ) : !loading ? (
            <>
              <button
                onClick={() => goToLogin()}
                className="btn btn-ghost btn-sm rounded-full text-sm font-semibold text-base-content/70 hover:bg-base-200 hover:text-primary"
              >
                Ingresar
              </button>
              <button
                onClick={handlePublishClick}
                className="btn btn-primary btn-sm rounded-full px-5 text-sm font-semibold shadow-sm shadow-primary/30"
              >
                Publicar mi perfil
              </button>
            </>
          ) : null}
        </div>

        {/* Mobile actions */}
        <div className="flex items-center justify-end gap-1 lg:hidden">
          <ThemeToggle />
          {!loading && isAuthenticated && (
            <div className="dropdown dropdown-end">
              <div
                tabIndex={0}
                role="button"
                className="btn btn-circle btn-ghost btn-sm"
                aria-label="Menú de usuario"
              >
                {picture && !imgError ? (
                  <img
                    key={picture}
                    src={picture}
                    alt={displayName}
                    className="h-7 w-7 rounded-full object-cover"
                    onError={() => setImgError(true)}
                  />
                ) : (
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-content">
                    {initials}
                  </span>
                )}
              </div>
              <ul
                tabIndex={0}
                className="menu dropdown-content z-[60] mt-2 w-48 rounded-2xl border border-base-300 bg-base-100 p-2 shadow-soft"
              >
                <li>
                  <button onClick={() => navigate('/mi-cuenta')} className="rounded-xl">
                    <User className="h-4 w-4" /> Mi cuenta
                  </button>
                </li>
                <li>
                  <button onClick={() => navigate('/mi-perfil')} className="rounded-xl">
                    <FileText className="h-4 w-4" /> Mi perfil
                  </button>
                </li>
                <li>
                  <button onClick={() => navigate('/mis-reviews')} className="rounded-xl">
                    <Star className="h-4 w-4" /> Mis reseñas
                  </button>
                </li>
                <div className="divider my-1" />
                <li>
                  <button onClick={handleLogout} className="rounded-xl text-error">
                    <LogOut className="h-4 w-4" /> Salir
                  </button>
                </li>
              </ul>
            </div>
          )}
          <button
            className="btn btn-square btn-ghost btn-sm"
            aria-label={drawerOpen ? 'Cerrar menú' : 'Abrir menú'}
            aria-expanded={drawerOpen}
            onClick={() => setDrawerOpen((v) => !v)}
          >
            {drawerOpen ? (
              <X className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Menu className="h-5 w-5" aria-hidden="true" />
            )}
          </button>
        </div>
      </nav>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="border-t border-base-300/60 bg-base-100 shadow-lg lg:hidden">
          <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6">
            <div className="flex flex-col gap-1">
              {NAV_LINKS.map((link) =>
                link.href.startsWith('#') ? (
                  <a
                    key={link.href}
                    href={link.href}
                    className="rounded-xl px-3 py-3 text-sm font-semibold text-base-content/70 transition-colors hover:bg-base-200 hover:text-primary"
                    onClick={() => setDrawerOpen(false)}
                  >
                    {link.label}
                  </a>
                ) : link.href === '/buscar/avanzada' ? (
                  <button
                    key={link.href}
                    type="button"
                    onClick={handleAdvancedSearchClick}
                    className="rounded-xl px-3 py-3 text-left text-sm font-semibold text-base-content/70 transition-colors hover:bg-base-200 hover:text-primary"
                  >
                    {link.label}
                  </button>
                ) : (
                  <NavLink
                    key={link.href}
                    to={link.href}
                    className="rounded-xl px-3 py-3 text-sm font-semibold text-base-content/70 transition-colors hover:bg-base-200 hover:text-primary"
                    onClick={() => setDrawerOpen(false)}
                  >
                    {link.label}
                  </NavLink>
                )
              )}
            </div>
            <div className="mt-3 flex flex-col gap-2 border-t border-base-300/60 pt-3">
              {!loading && !isAuthenticated && (
                <>
                  <button
                    onClick={() => { goToLogin(); setDrawerOpen(false); }}
                    className="btn btn-outline btn-sm rounded-full border-base-300 text-base-content"
                  >
                    Ingresar
                  </button>
                  <button
                    onClick={() => { handlePublishClick(); setDrawerOpen(false); }}
                    className="btn btn-primary btn-sm rounded-full shadow-sm shadow-primary/30"
                  >
                    Publicar mi perfil
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
