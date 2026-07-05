import { TRUST_ITEMS } from '../../pages/landing/landingData';

export function TrustSection() {
  return (
    <section className="bg-base-100 py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto mb-12 max-w-2xl text-center md:mb-16">
          <h2 className="text-3xl font-extrabold tracking-tight text-base-content md:text-5xl">
            Una red más ordenada y confiable.
          </h2>
          <p className="mt-4 text-lg text-base-content/60">
            Estamos construyendo una forma más clara de encontrar servicios
            locales, con perfiles revisados, datos útiles y contacto directo.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {TRUST_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.title}
                className="flex flex-col gap-3 rounded-[1.75rem] border border-base-300/70 bg-base-100 p-6 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-xl"
              >
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <Icon className="h-6 w-6" aria-hidden="true" />
                </span>
                <h3 className="font-bold text-base-content">{item.title}</h3>
                <p className="text-sm leading-relaxed text-base-content/60">
                  {item.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}