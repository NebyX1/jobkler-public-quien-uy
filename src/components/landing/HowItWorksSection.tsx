import { Search, MapPinned, MessageCircle } from 'lucide-react';
import { STEPS } from '../../pages/landing/landingData';

const STEP_ICONS = [Search, MapPinned, MessageCircle];

export function HowItWorksSection() {
  return (
    <section id="como-funciona" className="bg-base-100 py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto mb-14 max-w-2xl text-center md:mb-20">
          <h2 className="text-3xl font-extrabold tracking-tight text-base-content md:text-5xl">
            Resolver algo debería ser simple.
          </h2>
          <p className="mt-4 text-lg text-base-content/60">
            Tres pasos, cero vueltas.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-3 md:gap-8">
          {STEPS.map((step, i) => {
            const Icon = STEP_ICONS[i];
            return (
              <div
                key={step.step}
                className="relative flex min-h-[260px] flex-col items-center rounded-[2rem] border border-base-300/70 bg-base-100 p-8 text-center shadow-md transition-all duration-300 hover:-translate-y-1 hover:shadow-xl md:p-10"
              >
                {/* Connector line on desktop */}
                {i < STEPS.length - 1 && (
                  <div className="absolute left-[calc(100%+1.5rem)] top-14 hidden h-px w-8 bg-base-300 md:block lg:w-12" />
                )}

                <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <Icon className="h-7 w-7" aria-hidden="true" />
                </span>
                <span className="mt-4 text-sm font-bold uppercase tracking-wider text-primary/70">
                  Paso {step.step}
                </span>
                <h3 className="mt-2 text-xl font-bold text-base-content">
                  {step.title}
                </h3>
                <p className="mt-2 max-w-xs text-base-content/60">
                  {step.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}