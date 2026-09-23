import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Navbar } from '../components/landing/Navbar';
import { Footer } from '../components/landing/Footer';
import { ProfileCard } from '../components/landing/ProfileCard';
import { getProfilesByPredictedLocation } from '../services/profileService';
import { getCatalog, getPredictedLocation, saveLastLocation } from '../services/locationService';
import type { PredictedLocation } from '../types/profile';

export function NearMePage() {
  const [location, setLocation] = useState<PredictedLocation>(() => getPredictedLocation());
  const catalog = useQuery({ queryKey: ['catalog'], queryFn: getCatalog, staleTime: 5 * 60_000 });
  const department = catalog.data?.departments.find((item) =>
    item.id === location.departmentId || item.name === location.department,
  );
  const localities = catalog.data?.localities.filter((item) => item.departmentId === department?.id) || [];
  const selectedLocality = localities.find((item) =>
    item.id === location.localityId || item.name === location.locality,
  );
  const { data = [], isLoading, isError } = useQuery({
    queryKey: ['near-me', department?.id, selectedLocality?.id],
    queryFn: () => getProfilesByPredictedLocation({
      department: department?.name || '',
      departmentId: department?.id,
      locality: selectedLocality?.name || '',
      localityId: selectedLocality?.id,
    }),
    enabled: Boolean(department && selectedLocality),
  });

  const chooseDepartment = (id: string) => {
    const next = catalog.data?.departments.find((item) => item.id === id);
    setLocation({ department: next?.name || '', departmentId: next?.id, locality: '', localityId: undefined });
  };
  const chooseLocality = (id: string) => {
    const next = localities.find((item) => item.id === id);
    const current = {
      department: department?.name || '', departmentId: department?.id,
      locality: next?.name || '', localityId: next?.id,
    };
    setLocation(current);
    if (department && next) saveLastLocation(current);
  };

  return (
    <div className="flex min-h-screen flex-col bg-base-100">
      <Navbar />
      <main className="flex-1">
        <section className="py-10 sm:py-12">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="rounded-[2.25rem] border border-base-300/70 bg-base-200/50 p-6 shadow-sm sm:p-8">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">Cerca de vos</p>
              <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-base-content sm:text-4xl">Servicios por localidad</h1>
              <p className="mt-3 max-w-2xl text-base text-base-content/70">
                Elegí una zona para ver perfiles de esa localidad. Esta búsqueda no usa GPS ni estima distancias.
              </p>
              <div className="mt-6 grid gap-4 sm:max-w-2xl sm:grid-cols-2">
                <label className="text-sm font-semibold text-base-content">
                  Departamento
                  <select
                    value={department?.id || ''}
                    onChange={(event) => chooseDepartment(event.target.value)}
                    className="select select-bordered mt-2 w-full rounded-2xl bg-base-100"
                  >
                    <option value="">Seleccionar departamento</option>
                    {catalog.data?.departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                </label>
                <label className="text-sm font-semibold text-base-content">
                  Localidad
                  <select
                    value={selectedLocality?.id || ''}
                    onChange={(event) => chooseLocality(event.target.value)}
                    disabled={!department}
                    className="select select-bordered mt-2 w-full rounded-2xl bg-base-100 disabled:opacity-60"
                  >
                    <option value="">Seleccionar localidad</option>
                    {localities.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                </label>
              </div>
            </div>
          </div>
        </section>

        <section className="pb-12 sm:pb-16">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            {!department || !selectedLocality ? (
              <div className="rounded-[2rem] border border-base-300/70 bg-base-100 p-8 text-center">
                <p className="text-base-content/70">Seleccioná departamento y localidad para comenzar.</p>
              </div>
            ) : isError ? (
              <div role="alert" className="rounded-[2rem] border border-error/20 bg-error/10 p-6 text-base-content">No pudimos cargar los perfiles. Probá de nuevo en unos instantes.</div>
            ) : isLoading ? (
              <div className="rounded-[2rem] border border-base-300/70 bg-base-100 p-8 text-center text-base-content/70">Cargando perfiles…</div>
            ) : data.length ? (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
                {data.map((profile) => <ProfileCard key={profile.id} profile={profile} compact />)}
              </div>
            ) : (
              <div className="rounded-[2rem] border border-base-300/70 bg-base-100 p-8 text-center">
                <h2 className="text-2xl font-bold text-base-content">No encontramos perfiles en {selectedLocality.name}.</h2>
                <p className="mt-2 text-base text-base-content/70">Probá otra localidad o buscá en todo Uruguay.</p>
                <Link to="/buscar" className="btn btn-primary mt-6 rounded-full">Buscar profesionales</Link>
              </div>
            )}
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
