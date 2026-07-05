import { CATEGORIES } from '../../pages/landing/landingData';
import { CategoryCard } from './CategoryCard';

export function CategorySection() {
  return (
    <section id="categorias" className="bg-base-200 py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto mb-12 max-w-2xl text-center md:mb-16">
          <span className="inline-flex items-center gap-2 rounded-full border border-base-300/70 bg-base-100 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-primary">
            Categorías
          </span>
          <h2 className="mt-4 text-3xl font-extrabold tracking-tight text-base-content md:text-5xl">
            Buscá por categoría
          </h2>
          <p className="mt-4 text-lg text-base-content/60">
            Ordenamos los servicios para que encuentres más rápido a la persona
            adecuada.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 md:gap-6">
          {CATEGORIES.map((cat) => (
            <CategoryCard key={cat.name} item={cat} />
          ))}
        </div>
      </div>
    </section>
  );
}