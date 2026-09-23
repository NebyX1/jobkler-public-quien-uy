import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getCatalog } from '../../services/locationService';

export function TerritorySection() {
  const { data: catalog } = useQuery({ queryKey: ['catalog'], queryFn: getCatalog, staleTime: 5 * 60_000 });
  const localities = (catalog?.localities || []).filter((locality) => locality.profileCount > 0).slice(0, 6);

  return (
    <section className="bg-base-100 py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-base-300/70 bg-base-100 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-primary">Identidad local</span>
            <h2 className="mt-4 text-3xl font-extrabold tracking-tight text-base-content md:text-5xl">De Minas al resto del país.</h2>
            <p className="mt-5 text-lg leading-relaxed text-base-content/70">
              Explorá profesionales y servicios por localidad, con la zona indicada en cada perfil.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {localities.map((item) => (
              <Link
                key={item.id}
                to={`/buscar/${item.departmentSlug}/${item.slug}`}
                className="flex flex-col items-center gap-2 rounded-[1.5rem] border border-base-300/70 bg-base-100 p-6 text-center shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
              >
                <span className="font-bold text-base-content">{item.name}</span>
                <span className="badge badge-sm rounded-full border-0 bg-primary/10 text-primary">
                  {item.profileCount} {item.profileCount === 1 ? 'perfil' : 'perfiles'}
                </span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
