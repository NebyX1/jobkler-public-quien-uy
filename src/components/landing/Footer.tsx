import { Link } from 'react-router-dom';

const FOOTER_LINKS = [
  { label: 'Buscar', href: '#buscar' },
  { label: 'Categorías', href: '#categorias' },
  { label: 'Publicar perfil', href: '#sumar-perfil' },
  { label: 'Contacto', href: '#' },
];

const LEGAL_LINKS = [
  { label: 'Términos', href: '#' },
  { label: 'Privacidad', href: '#' },
];

export function Footer() {
  return (
    <footer className="border-t border-base-300 bg-base-100">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid gap-10 md:grid-cols-3">
          {/* Brand */}
          <div className="flex flex-col gap-3">
            <Link to="/" className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary font-extrabold text-primary-content">
                Q
              </span>
              <span className="text-lg font-extrabold tracking-tight text-base-content">
                Quien<span className="text-primary">.uy</span>
              </span>
            </Link>
            <p className="max-w-xs text-sm leading-relaxed text-base-content/60">
              Directorio local de profesionales, oficios y servicios en Uruguay.
              Encontrá quién puede hacerlo.
            </p>
          </div>

          {/* Links */}
          <div className="grid grid-cols-2 gap-8 md:justify-self-center">
            <div>
              <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-base-content/50">
                Enlaces
              </h3>
              <ul className="flex flex-col gap-2">
                {FOOTER_LINKS.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-sm text-base-content/70 transition-colors hover:text-primary"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-base-content/50">
                Legal
              </h3>
              <ul className="flex flex-col gap-2">
                {LEGAL_LINKS.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-sm text-base-content/70 transition-colors hover:text-primary"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Social */}
          <div className="flex flex-col gap-3 md:items-end">
            <h3 className="text-sm font-bold uppercase tracking-wider text-base-content/50">
              Seguinos
            </h3>
            <div className="flex gap-3">
              {['Instagram', 'Facebook', 'WhatsApp'].map((social) => (
                <a
                  key={social}
                  href="#"
                  className="flex h-10 w-10 items-center justify-center rounded-full border border-base-300 bg-base-100 text-sm font-semibold text-base-content/60 transition-all hover:border-primary hover:text-primary"
                  aria-label={social}
                >
                  {social.charAt(0)}
                </a>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom line */}
        <div className="mt-12 border-t border-base-300 pt-6 text-center">
          <p className="text-sm font-medium text-base-content/60">
            Hecho en Uruguay. 🇺🇾
          </p>
        </div>
      </div>
    </footer>
  );
}