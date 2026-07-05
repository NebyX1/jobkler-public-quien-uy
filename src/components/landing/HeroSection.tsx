import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { TRUST_METRICS } from '../../pages/landing/landingData';
import { SearchPanel } from './SearchPanel';
import { QuickChips } from './QuickChips';

export function HeroSection() {
  const [profession, setProfession] = useState('');

  const handleChipSelect = useCallback((value: string) => {
    setProfession(value);
  }, []);

  return (
    <section id="buscar" className="relative overflow-hidden bg-base-100">
      {/* Layered warm decorative background, fully contained */}
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <div className="absolute inset-0 bg-grid-soft text-base-content/[0.035]" />
        <div className="absolute -left-24 top-0 h-96 w-96 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute -right-16 top-32 h-80 w-80 rounded-full bg-warning/10 blur-3xl" />
        <div className="absolute bottom-0 left-1/3 h-72 w-72 rounded-full bg-accent/10 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-7xl px-4 pb-24 pt-16 sm:px-6 md:pb-32 md:pt-24 lg:px-8 lg:pb-36 lg:pt-32">
        {/* Centered hero content — search is the centerpiece */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="mx-auto flex max-w-5xl flex-col items-center text-center"
        >
          {/* Eyebrow badge */}
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-base-300/70 bg-base-100 px-4 py-2 text-sm font-semibold text-base-content/70 shadow-sm">
            <span className="h-2 w-2 rounded-full bg-primary" />
            Directorio local de profesionales y servicios
          </span>

          {/* Headline */}
          <h1 className="mt-6 max-w-3xl text-5xl font-extrabold leading-[0.95] tracking-tight text-base-content sm:text-6xl lg:text-7xl">
            Encontrá quién puede{' '}
            <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              hacerlo.
            </span>
          </h1>

          {/* Subheadline */}
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-base-content/70 md:text-xl">
            Buscá por profesión, oficio, departamento o localidad y contactá
            directo.
          </p>

          {/* Search panel — the hero centerpiece */}
          <SearchPanel initialProfession={profession} />

          {/* Quick chips */}
          <QuickChips onSelect={handleChipSelect} />

          {/* Trust metrics */}
          <div className="mt-8 grid w-full max-w-2xl grid-cols-1 gap-3 sm:grid-cols-3">
            {TRUST_METRICS.map((metric) => (
              <div
                key={metric.label}
                className="rounded-2xl border border-base-300/60 bg-base-100/75 p-4 shadow-sm"
              >
                <p className="text-xl font-extrabold text-base-content sm:text-2xl">
                  {metric.value}
                </p>
                <p className="text-xs text-base-content/60 sm:text-sm">
                  {metric.label}
                </p>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}