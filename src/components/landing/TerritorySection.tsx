import { LOCALITIES } from '../../pages/landing/landingData';

export function TerritorySection() {
  return (
    <section className="bg-base-100 py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
          {/* Left: text block */}
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-base-300/70 bg-base-100 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-primary">
              Identidad local
            </span>
            <h2 className="mt-4 text-3xl font-extrabold tracking-tight text-base-content md:text-5xl">
              De Minas al resto del país.
            </h2>
            <p className="mt-5 text-lg leading-relaxed text-base-content/70">
              Quien.uy nace para ordenar el talento local: personas que
              trabajan, resuelven, crean, arreglan, enseñan, cuidan y
              acompañan.
            </p>
          </div>

          {/* Right: locality bento cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {LOCALITIES.map((t) => {
              const isComingSoon = t.status === 'Próximamente';
              return (
                <div
                  key={t.name}
                  className={`flex flex-col items-center gap-2 rounded-[1.5rem] p-6 text-center transition-all duration-300 hover:-translate-y-1 ${
                    isComingSoon
                      ? 'border border-dashed border-base-300/70 bg-base-100/40'
                      : 'border border-base-300/70 bg-base-100 shadow-sm hover:shadow-xl'
                  }`}
                >
                  <p className="font-bold text-base-content">{t.name}</p>
                  <span
                    className={`badge badge-sm rounded-full border-0 ${
                      isComingSoon
                        ? 'bg-warning/20 text-base-content/60'
                        : 'bg-primary/10 text-primary'
                    }`}
                  >
                    {t.status}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}