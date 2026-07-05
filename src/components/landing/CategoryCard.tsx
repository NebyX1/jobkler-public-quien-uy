import { ArrowRight } from 'lucide-react';
import type { CategoryItem } from '../../pages/landing/landingData';

/**
 * Bento-style category card. Icon bubble + count badge sit in a
 * top row, followed by title, description and a small "Explorar"
 * CTA anchored to the bottom.
 */
export function CategoryCard({ item }: { item: CategoryItem }) {
  const Icon = item.icon;

  return (
    <a
      href="#buscar"
      className="group flex min-h-[230px] flex-col justify-between rounded-[2rem] border border-base-300/70 bg-base-100 p-6 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-xl"
    >
      <div className="flex items-center justify-between gap-3">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-content">
          <Icon className="h-6 w-6" />
        </span>
        <span className="badge badge-sm rounded-full border-0 bg-base-200 font-semibold text-base-content/60">
          {item.count}
        </span>
      </div>

      <h3 className="mt-4 text-lg font-bold leading-snug text-base-content">
        {item.name}
      </h3>
      <p className="mt-1.5 text-sm leading-relaxed text-base-content/60">
        {item.description}
      </p>

      <span className="mt-auto flex items-center gap-1.5 pt-4 text-sm font-semibold text-primary opacity-0 transition-opacity group-hover:opacity-100">
        Explorar
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </span>
    </a>
  );
}
