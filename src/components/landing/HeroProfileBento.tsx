import { MapPin, SlidersHorizontal } from 'lucide-react';

/**
 * Controlled bento-style visual panel shown on the right side of
 * the hero. Contains a mini header, a decorative filter pill row
 * and a 2-column grid of profile mini-cards. Everything is
 * contained inside this panel — nothing floats outside it.
 */
export function HeroProfileBento() {
  return (
    <div className="relative mx-auto max-w-xl overflow-hidden rounded-[2.5rem] border border-base-300/70 bg-base-100/70 p-5 shadow-2xl backdrop-blur-xl sm:p-6 lg:mx-0 lg:p-7">
      {/* Decorative accent glow, contained within the panel */}
      <div
        className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-primary/15 blur-3xl"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute -bottom-20 -left-16 h-56 w-56 rounded-full bg-accent/10 blur-3xl"
        aria-hidden="true"
      />

      <div className="relative">
        {/* Mini header */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/15 text-primary">
              <MapPin className="h-4 w-4" aria-hidden="true" />
            </span>
            <div>
              <p className="text-sm font-bold text-base-content">Perfiles cerca de vos</p>
              <p className="text-xs text-base-content/55">Actualizado hoy</p>
            </div>
          </div>
          <span className="flex h-9 w-9 items-center justify-center rounded-full border border-base-300/70 bg-base-100 text-base-content/60">
            <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
          </span>
        </div>

        {/* Decorative filter pill row */}
        <div className="no-scrollbar mt-4 flex gap-2 overflow-x-auto">
          {['Todos', 'Disponibles', 'Online', 'Cerca de mí'].map((f, i) => (
            <span
              key={f}
              className={`shrink-0 rounded-full px-3.5 py-1.5 text-xs font-semibold ${
                i === 0
                  ? 'bg-primary text-primary-content'
                  : 'border border-base-300/70 bg-base-100 text-base-content/60'
              }`}
            >
              {f}
            </span>
          ))}
        </div>

        {/* Profile mini-cards */}
        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {[
            { title: 'Electricistas', location: 'Minas y alrededores', status: 'Disponibles hoy' },
            { title: 'Salud y bienestar', location: 'Lavalleja', status: 'Atención online' },
            { title: 'Oficios del hogar', location: 'Canelones', status: 'Responden rápido' },
            { title: 'Servicios rurales', location: 'Interior del país', status: 'Agenda flexible' },
          ].map((profile, i) => (
            <div
              key={profile.title}
              className={`rounded-3xl border border-base-300/70 bg-base-100 p-4 shadow-md transition-all duration-300 hover:-translate-y-1 hover:shadow-xl ${
                i % 2 === 1 ? 'sm:mt-6' : ''
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
                  <MapPin className="h-4 w-4" aria-hidden="true" />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-base-content">
                    {profile.title}
                  </p>
                  <p className="truncate text-xs text-base-content/60">{profile.location}</p>
                </div>
              </div>

              <div className="mt-3 flex items-center justify-between gap-2">
                <span className="badge badge-sm rounded-full border-0 bg-primary/10 text-[11px] font-semibold text-primary">
                  {profile.status}
                </span>
                <span className="text-xs font-semibold text-primary">Ver perfil</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
