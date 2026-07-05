import { useQuery } from '@tanstack/react-query';
import { getFeaturedProfiles } from '../../services/profileService';
import { ProfileCard } from './ProfileCard';

export function FeaturedProfilesSection() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['featured-profiles'],
    queryFn: getFeaturedProfiles,
  });

  return (
    <section className="bg-base-200 py-24 md:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto mb-12 max-w-2xl text-center md:mb-16">
          <h2 className="text-3xl font-extrabold tracking-tight text-base-content md:text-5xl">
            Personas que ya podés encontrar
          </h2>
          <p className="mt-4 text-lg text-base-content/60">
            Perfiles claros, humanos y listos para contactar.
          </p>
        </div>

        {isError ? (
          <div className="rounded-[2rem] border border-base-300/70 bg-base-100 p-6 text-center text-base-content/70">
            No pudimos cargar los perfiles destacados. Verificá que JSON Server esté corriendo.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
            {isLoading
              ? Array.from({ length: 4 }).map((_, index) => (
                  <div
                    key={index}
                    className="rounded-[2rem] border border-base-300/70 bg-base-100 p-6"
                  >
                    <div className="skeleton h-14 w-14 rounded-full" />
                    <div className="mt-4 space-y-3">
                      <div className="skeleton h-5 w-2/3 rounded-full" />
                      <div className="skeleton h-4 w-full rounded-full" />
                      <div className="skeleton h-4 w-5/6 rounded-full" />
                      <div className="skeleton h-24 w-full rounded-2xl" />
                    </div>
                  </div>
                ))
              : data?.slice(0, 4).map((profile) => (
                  <ProfileCard key={profile.id} profile={profile} />
                ))}
          </div>
        )}
      </div>
    </section>
  );
}
