import { useMemo } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { SearchPanel } from '../components/landing/SearchPanel';
import { Navbar } from '../components/landing/Navbar';
import { Footer } from '../components/landing/Footer';
import { ProfileCard } from '../components/landing/ProfileCard';
import { getProfiles } from '../services/profileService';
import { normalizeText } from '../utils/textSearch';

function hasAnyQueryValue(values: Array<string | null | undefined>) {
  return values.some((value) => Boolean(value && value.trim()));
}

function buildTitle({
  q,
  department,
  locality,
  category,
}: {
  q: string;
  department: string;
  locality: string;
  category: string;
}) {
  const term = q || category;

  if (term && locality && department) {
    return `Resultados para ${term} en ${locality}, ${department}`;
  }

  if (term && department) {
    return `Resultados para ${term} en ${department}`;
  }

  if (department && locality) {
    return `Servicios en ${locality}, ${department}`;
  }

  if (department) {
    return `Servicios en ${department}`;
  }

  if (term) {
    return `Resultados para ${term}`;
  }

  return 'Resultados de búsqueda';
}

function SkeletonCard() {
  return (
    <div className="rounded-[2rem] border border-base-300/70 bg-base-100 p-5 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="skeleton h-16 w-16 rounded-full" />
        <div className="flex-1 space-y-3">
          <div className="skeleton h-5 w-2/3 rounded-full" />
          <div className="skeleton h-4 w-full rounded-full" />
          <div className="skeleton h-4 w-5/6 rounded-full" />
        </div>
      </div>
      <div className="mt-4 space-y-3">
        <div className="skeleton h-16 w-full rounded-2xl" />
        <div className="skeleton h-10 w-full rounded-full" />
      </div>
    </div>
  );
}

export function SearchResultsPage() {
  const [searchParams] = useSearchParams();
  const params = useParams<{ department?: string; locality?: string }>();

  const resolvedFilters = useMemo(() => {
    const queryValues = {
      q: searchParams.get('q') || '',
      department: searchParams.get('departamento') || '',
      locality: searchParams.get('localidad') || '',
      category: searchParams.get('category') || '',
      profession: searchParams.get('profession') || '',
    };

    const hasQuery = hasAnyQueryValue(Object.values(queryValues));

    return {
      q: queryValues.q,
      department: hasQuery ? queryValues.department : params.department || '',
      locality: hasQuery ? queryValues.locality : params.locality || '',
      category: queryValues.category,
      profession: queryValues.profession,
    };
  }, [params.department, params.locality, searchParams]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['search-results', resolvedFilters],
    queryFn: () => getProfiles(resolvedFilters),
  });

  const title = buildTitle(resolvedFilters);
  const subtitle = `${data?.length ?? 0} perfiles disponibles.`;
  const compactSearchClassName = 'mx-auto w-full max-w-6xl';

  return (
    <div className="flex min-h-screen flex-col bg-base-100">
      <Navbar />
      <main className="flex-1">
        <section className="border-b border-base-300/60 bg-base-200/40 py-8 sm:py-10">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="rounded-[2.25rem] border border-base-300/70 bg-base-100/90 p-5 shadow-sm backdrop-blur-xl sm:p-6 lg:p-7">
              <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
                <div className="max-w-2xl">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">
                    Búsqueda
                  </p>
                  <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-base-content sm:text-4xl">
                    {title}
                  </h1>
                  <p className="mt-3 text-base text-base-content/70">{subtitle}</p>
                </div>

                <div className="flex flex-wrap gap-2 text-sm text-base-content/60">
                  {resolvedFilters.q ? <span className="badge rounded-full border-0 bg-base-200">{normalizeText(resolvedFilters.q)}</span> : null}
                  {resolvedFilters.department ? <span className="badge rounded-full border-0 bg-base-200">{resolvedFilters.department}</span> : null}
                  {resolvedFilters.locality ? <span className="badge rounded-full border-0 bg-base-200">{resolvedFilters.locality}</span> : null}
                  {resolvedFilters.category ? <span className="badge rounded-full border-0 bg-base-200">{resolvedFilters.category}</span> : null}
                </div>
              </div>

              <div className="mt-6">
                <SearchPanel
                  compact
                  className={compactSearchClassName}
                  initialProfession={resolvedFilters.q}
                  initialDepartment={resolvedFilters.department}
                  initialLocality={resolvedFilters.locality}
                />
              </div>
            </div>
          </div>
        </section>

        <section className="py-10 sm:py-12">
          <div className="mx-auto grid max-w-7xl gap-8 px-4 sm:px-6 lg:grid-cols-[280px_minmax(0,1fr)] lg:px-8">
            <aside className="hidden lg:block">
              <div className="sticky top-24 rounded-[2rem] border border-base-300/70 bg-base-200/70 p-5 shadow-sm">
                <h2 className="text-lg font-bold text-base-content">Filtros activos</h2>
                <div className="mt-4 flex flex-col gap-3 text-sm text-base-content/70">
                  <div className="flex items-center justify-between gap-3">
                    <span>Profesión</span>
                    <span className="font-semibold text-base-content">{resolvedFilters.q || 'Todas'}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span>Departamento</span>
                    <span className="font-semibold text-base-content">{resolvedFilters.department || 'Todos'}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span>Localidad</span>
                    <span className="font-semibold text-base-content">{resolvedFilters.locality || 'Todas'}</span>
                  </div>
                </div>

                <div className="mt-5 flex flex-col gap-2">
                  <Link to="/buscar" className="btn btn-primary btn-sm rounded-full">
                    Limpiar búsqueda
                  </Link>
                  <Link to="/" className="btn btn-outline btn-sm rounded-full border-base-300 text-base-content">
                    Ver perfiles destacados
                  </Link>
                  <Link to="/buscar" className="btn btn-ghost btn-sm rounded-full">
                    Buscar en todo Uruguay
                  </Link>
                </div>
              </div>
            </aside>

            <div>
              <details className="lg:hidden rounded-[2rem] border border-base-300/70 bg-base-200/70 p-4">
                <summary className="cursor-pointer font-semibold text-base-content">Filtros</summary>
                <div className="mt-4 grid gap-3 text-sm text-base-content/70 sm:grid-cols-3">
                  <div className="rounded-2xl border border-base-300/70 bg-base-100 p-3">
                    <p className="text-xs uppercase tracking-wide text-base-content/50">Profesión</p>
                    <p className="mt-1 font-semibold text-base-content">{resolvedFilters.q || 'Todas'}</p>
                  </div>
                  <div className="rounded-2xl border border-base-300/70 bg-base-100 p-3">
                    <p className="text-xs uppercase tracking-wide text-base-content/50">Departamento</p>
                    <p className="mt-1 font-semibold text-base-content">{resolvedFilters.department || 'Todos'}</p>
                  </div>
                  <div className="rounded-2xl border border-base-300/70 bg-base-100 p-3">
                    <p className="text-xs uppercase tracking-wide text-base-content/50">Localidad</p>
                    <p className="mt-1 font-semibold text-base-content">{resolvedFilters.locality || 'Todas'}</p>
                  </div>
                </div>
              </details>

              {isError ? (
                <div className="rounded-[2rem] border border-error/20 bg-error/10 p-6 text-base-content">
                  <h2 className="text-lg font-bold">No pudimos cargar los perfiles</h2>
                  <p className="mt-2 text-sm text-base-content/70">
                    Verificá que JSON Server esté corriendo en el puerto 3001.
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Link to="/" className="btn btn-primary btn-sm rounded-full">
                      Volver al inicio
                    </Link>
                    <Link to="/buscar" className="btn btn-outline btn-sm rounded-full border-base-300 text-base-content">
                      Reintentar búsqueda
                    </Link>
                  </div>
                </div>
              ) : isLoading ? (
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
                  {Array.from({ length: 6 }).map((_, index) => (
                    <SkeletonCard key={index} />
                  ))}
                </div>
              ) : data && data.length > 0 ? (
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
                  {data.map((profile) => (
                    <ProfileCard key={profile.id} profile={profile} compact />
                  ))}
                </div>
              ) : (
                <div className="rounded-[2rem] border border-base-300/70 bg-base-100 p-8 text-center shadow-sm">
                  <h2 className="text-2xl font-bold text-base-content">No encontramos perfiles con esos filtros.</h2>
                  <p className="mt-2 text-base text-base-content/70">
                    Probá limpiar la búsqueda o explorar perfiles destacados.
                  </p>
                  <div className="mt-6 flex flex-wrap justify-center gap-3">
                    <Link to="/buscar" className="btn btn-primary rounded-full">
                      Limpiar búsqueda
                    </Link>
                    <Link to="/" className="btn btn-outline rounded-full border-base-300 text-base-content">
                      Ver perfiles destacados
                    </Link>
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
