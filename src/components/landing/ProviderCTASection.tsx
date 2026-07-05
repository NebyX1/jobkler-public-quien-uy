import { Check } from 'lucide-react';
import { PROVIDER_BENEFITS } from '../../pages/landing/landingData';

export function ProviderCTASection() {
  return (
    <section id="sumar-perfil" className="bg-base-200 py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-[2.5rem] bg-gradient-to-br from-primary to-secondary p-8 shadow-2xl sm:p-12 lg:p-16">
          {/* Decorative shapes, fully contained */}
          <div
            className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-warning/20 blur-3xl"
            aria-hidden="true"
          />
          <div
            className="pointer-events-none absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-accent/20 blur-3xl"
            aria-hidden="true"
          />
          <div className="pointer-events-none absolute inset-0 bg-grid-soft text-primary-content/[0.06]" aria-hidden="true" />

          <div className="relative grid gap-10 lg:grid-cols-2 lg:items-center">
            <div className="flex flex-col gap-5">
              <h2 className="text-3xl font-extrabold tracking-tight text-primary-content md:text-5xl">
                ¿Querés que te encuentren?
              </h2>
              <p className="text-lg text-primary-content/85">
                Creá tu perfil, contá qué hacés, dónde trabajás y cómo pueden
                contactarte.
              </p>
              <div>
                <a
                  href="/auth"
                  className="btn h-14 rounded-2xl border-0 bg-base-100 px-8 text-base font-bold text-primary shadow-lg transition-transform hover:-translate-y-0.5 hover:bg-base-200"
                >
                  Sumar mi perfil
                </a>
              </div>
            </div>

            <ul className="flex flex-col gap-3">
              {PROVIDER_BENEFITS.map((benefit) => (
                <li key={benefit} className="flex items-center gap-3 text-primary-content/95">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-content/20">
                    <Check className="h-3.5 w-3.5" aria-hidden="true" />
                  </span>
                  <span className="text-sm font-medium">{benefit}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}