import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';

const NAV_LINKS = [
  { label: 'Buscar', href: '#buscar' },
  { label: 'Categorías', href: '#categorias' },
  { label: 'Cómo funciona', href: '#como-funciona' },
  { label: 'Sumá tu perfil', href: '#sumar-perfil' },
];

export function Navbar() {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-base-300/60 bg-base-100/80 backdrop-blur-xl">
      <nav className="mx-auto grid h-[72px] max-w-7xl grid-cols-2 items-center gap-4 px-4 sm:px-6 lg:grid-cols-[auto_1fr_auto] lg:px-8">
        {/* Logo */}
        <a href="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-sm font-extrabold text-primary-content shadow-sm">
            Q
          </span>
          <span className="text-lg font-extrabold tracking-tight text-base-content">
            Quien<span className="text-primary">.uy</span>
          </span>
        </a>

        {/* Desktop links — centered */}
        <div className="hidden items-center justify-center gap-8 lg:flex">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-semibold text-base-content/70 transition-colors hover:text-primary"
            >
              {link.label}
            </a>
          ))}
        </div>

        {/* Desktop actions */}
        <div className="hidden items-center justify-end gap-2 lg:flex">
          <ThemeToggle />
          <a
            href="/cerca-de-mi"
            className="btn btn-ghost btn-sm rounded-full text-sm font-semibold text-base-content/70 hover:bg-base-200 hover:text-primary"
          >
            Cerca de vos
          </a>
          <a
            href="/auth"
            className="btn btn-ghost btn-sm rounded-full text-sm font-semibold text-base-content/70 hover:bg-base-200 hover:text-primary"
          >
            Ingresar
          </a>
          <a
            href="#sumar-perfil"
            className="btn btn-primary btn-sm rounded-full px-5 text-sm font-semibold shadow-sm shadow-primary/30"
          >
            Publicar mi perfil
          </a>
        </div>

        {/* Mobile actions */}
        <div className="flex items-center justify-end gap-1 lg:hidden">
              <ThemeToggle />
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
              {NAV_LINKS.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className="rounded-xl px-3 py-3 text-sm font-semibold text-base-content/70 transition-colors hover:bg-base-200 hover:text-primary"
                  onClick={() => setDrawerOpen(false)}
                >
                  {link.label}
                </a>
              ))}
            </div>
            <div className="mt-3 flex flex-col gap-2 border-t border-base-300/60 pt-3">
              <a
                href="/cerca-de-mi"
                className="btn btn-ghost btn-sm rounded-full text-base-content/70"
                onClick={() => setDrawerOpen(false)}
              >
                Cerca de vos
              </a>
              <a
                href="/auth"
                className="btn btn-outline btn-sm rounded-full border-base-300 text-base-content"
                onClick={() => setDrawerOpen(false)}
              >
                Ingresar
              </a>
              <a
                href="#sumar-perfil"
                className="btn btn-primary btn-sm rounded-full shadow-sm shadow-primary/30"
                onClick={() => setDrawerOpen(false)}
              >
                Publicar mi perfil
              </a>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
