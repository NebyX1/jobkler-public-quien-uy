import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Navbar } from '../components/landing/Navbar';
import { Footer } from '../components/landing/Footer';
import { ProfileCard } from '../components/landing/ProfileCard';
import { getProfilesByPredictedLocation } from '../services/profileService';
import { getPredictedLocation } from '../services/locationService';

export function NearMePage() {
  const [locationNote, setLocationNote] = useState('');
  const predictedLocation = useMemo(() => getPredictedLocation(), []);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['near-me', predictedLocation.department, predictedLocation.locality],
    queryFn: () => getProfilesByPredictedLocation(predictedLocation),
  });

  const handleUseLocation = () => {
    if (!navigator.geolocation) {
      setLocationNote('Tu navegador no permite geolocalización.');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      () => {
        setLocationNote('Ubicación detectada. Elegí el departamento/localidad para afinar resultados.');
      },
      () => {
        setLocationNote('No pudimos acceder a tu ubicación. Podés seguir buscando por zona.');
      },
      { enableHighAccuracy: false, timeout: 10000 },
    );
  };

  return (
    <div className="flex min-h-screen flex-col bg-base-100">
      <Navbar />
      <main className="flex-1">
        <section className="py-10 sm:py-12">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="rounded-[2.25rem] border border-base-300/70 bg-base-200/50 p-6 shadow-sm sm:p-8">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div className="max-w-2xl">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">
                    Cerca de vos
                  </p>
                  <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-base-content sm:text-4xl">
                    Resultados cerca de vos
                  </h1>
                  <p className="mt-3 text-base text-base-content/70">
                    Te mostramos perfiles sugeridos para {predictedLocation.locality}, {predictedLocation.department}.
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Link to="/buscar" className="btn btn-outline btn-sm rounded-full border-base-300 text-base-content">
                    Cambiar ubicación
                  </Link>
                  <button type="button" onClick={handleUseLocation} className="btn btn-primary btn-sm rounded-full">
                    Usar mi ubicación
                  </button>
                </div>
              </div>

              {locationNote ? (
                <div className="mt-4 rounded-2xl border border-base-300/70 bg-base-100 p-4 text-sm text-base-content/70">
                  {locationNote}
                </div>
              ) : null}
            </div>
          </div>
        </section>

        <section className="pb-12 sm:pb-16">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            {isError ? (
              <div className="rounded-[2rem] border border-error/20 bg-error/10 p-6 text-base-content">
                No pudimos conectar con el servidor de perfiles. Ejecutá `npm run dev:api`.
              </div>
            ) : isLoading ? (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 6 }).map((_, index) => (
                  <div key={index} className="rounded-[2rem] border border-base-300/70 bg-base-100 p-5">
                    <div className="skeleton h-16 w-16 rounded-full" />
                    <div className="mt-4 space-y-3">
                      <div className="skeleton h-5 w-2/3 rounded-full" />
                      <div className="skeleton h-4 w-full rounded-full" />
                      <div className="skeleton h-20 w-full rounded-2xl" />
                    </div>
                  </div>
                ))}
              </div>
            ) : data && data.length > 0 ? (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
                {data.map((profile) => (
                  <ProfileCard key={profile.id} profile={profile} compact />
                ))}
              </div>
            ) : (
              <div className="rounded-[2rem] border border-base-300/70 bg-base-100 p-8 text-center">
                <h2 className="text-2xl font-bold text-base-content">No encontramos perfiles cerca de vos.</h2>
                <p className="mt-2 text-base text-base-content/70">
                  Probá cambiar la ubicación o buscar en todo Uruguay.
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-3">
                  <Link to="/buscar" className="btn btn-primary rounded-full">
                    Buscar en todo Uruguay
                  </Link>
                  <Link to="/" className="btn btn-outline rounded-full border-base-300 text-base-content">
                    Ver inicio
                  </Link>
                </div>
              </div>
            )}
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
