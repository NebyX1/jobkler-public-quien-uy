import { useMemo, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { BadgeCheck, Mail, Phone, Star, MessageCircle, LogIn, Pencil } from 'lucide-react';
import { Navbar } from '../components/landing/Navbar';
import { Footer } from '../components/landing/Footer';
import { ProfileAvatar } from '../components/ProfileAvatar';
import { ProfileCard } from '../components/landing/ProfileCard';
import { OwnerBanner } from '../components/profiles/OwnerBanner';
import { ReviewCard } from '../components/profiles/ReviewCard';
import { ReviewForm } from '../components/profiles/ReviewForm';
import { getProfileBySlug, getProfiles } from '../services/profileService';
import {
  getReviewsByProfileId,
  createReview,
  userHasReviewedProfile,
} from '../services/reviewService';
import { useAuth } from '../lib/auth';

function digitsOnly(value: string) {
  return String(value || '').replace(/\D/g, '');
}

export function ProfileDetailPage() {
  const { slug = '' } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();

  const [reviewError, setReviewError] = useState<string | null>(null);

  const { data: profile, isLoading, isError } = useQuery({
    queryKey: ['profile-detail', slug],
    queryFn: () => getProfileBySlug(slug),
    enabled: Boolean(slug),
  });

  const isOwner = Boolean(profile?.isOwner);

  const reviewsQuery = useQuery({
    queryKey: ['profile-reviews', profile?.id],
    queryFn: () => getReviewsByProfileId(profile!.id),
    enabled: Boolean(profile?.id),
  });

  const existingReviewQuery = useQuery({
    queryKey: ['user-review', user?.fusionauth_user_id, profile?.id],
    queryFn: () => userHasReviewedProfile(user!.fusionauth_user_id, profile!.id),
    enabled: isAuthenticated && Boolean(user?.fusionauth_user_id) && Boolean(profile?.id) && !isOwner,
  });

  const similarQuery = useQuery({
    queryKey: ['similar-profiles', profile?.id],
    queryFn: () => getProfiles({ department: profile?.department, category: profile?.category, limit: 4 }),
    enabled: Boolean(profile),
  });

  const similarProfiles = useMemo(() => {
    return (similarQuery.data || [])
      .filter((item) => item.id !== profile?.id)
      .slice(0, 3);
  }, [profile?.id, similarQuery.data]);

  const whatsappHref = profile?.whatsapp ? `https://wa.me/${digitsOnly(profile.whatsapp)}` : null;
  const phoneHref = profile?.phone ? `tel:${digitsOnly(profile.phone)}` : null;
  const emailHref = profile?.email ? `mailto:${profile.email}` : null;

  const serviceArea = profile?.serviceArea?.filter(Boolean) || [];
  const tags = profile?.tags?.filter(Boolean) || [];
  const reviews = reviewsQuery.data || [];
  const existingReview = existingReviewQuery.data;

  const handleSubmitReview = async (values: { rating: number; comment: string }) => {
    if (!user || !profile) return;
    setReviewError(null);

    if (isOwner) {
      setReviewError('No podés reseñar tu propio perfil.');
      return;
    }

    // Service-level guard: block if already reviewed
    if (existingReview) {
      setReviewError('Ya dejaste una reseña para este perfil.');
      return;
    }

    try {
      await createReview({
        profileId: profile.id,
        profileSlug: profile.slug,
        authorUserId: user.fusionauth_user_id,
        authorName: user.full_name,
        authorPicture: user.picture || '',
        rating: values.rating,
        comment: values.comment,
        status: 'published',
        editable: false,
        acceptedNoEditPolicy: true,
      });

      queryClient.invalidateQueries({ queryKey: ['profile-reviews'] });
      queryClient.invalidateQueries({ queryKey: ['user-review'] });
      queryClient.invalidateQueries({ queryKey: ['profile-detail'] });
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : 'Error al enviar la reseña.');
      throw err;
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-base-100">
      <Navbar />
      <main className="flex-1">
        <section className="py-10 sm:py-12">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            {isLoading ? (
              <div className="space-y-6">
                <div className="rounded-[2.25rem] border border-base-300/70 bg-base-200/50 p-6 sm:p-8">
                  <div className="flex items-start gap-4">
                    <div className="skeleton h-24 w-24 rounded-full" />
                    <div className="flex-1 space-y-3">
                      <div className="skeleton h-8 w-2/3 rounded-full" />
                      <div className="skeleton h-5 w-1/2 rounded-full" />
                      <div className="skeleton h-5 w-1/3 rounded-full" />
                    </div>
                  </div>
                </div>
                <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
                  <div className="space-y-6 rounded-[2rem] border border-base-300/70 bg-base-100 p-6">
                    <div className="skeleton h-5 w-1/3 rounded-full" />
                    <div className="skeleton h-32 w-full rounded-2xl" />
                    <div className="skeleton h-40 w-full rounded-2xl" />
                  </div>
                  <div className="skeleton h-80 rounded-[2rem] border border-base-300/70 bg-base-100" />
                </div>
              </div>
            ) : isError ? (
              <div className="rounded-[2rem] border border-error/20 bg-error/10 p-8 text-base-content">
                No pudimos cargar el perfil. Revisá que la API local esté iniciada con run.ps1 o run.sh.
              </div>
            ) : !profile ? (
              <div className="rounded-[2rem] border border-base-300/70 bg-base-100 p-8 text-center">
                <h1 className="text-3xl font-extrabold text-base-content">Perfil no encontrado</h1>
                <p className="mt-3 text-base text-base-content/70">
                  El perfil que buscás no existe o fue eliminado.
                </p>
                <Link to="/buscar" className="btn btn-primary mt-6 rounded-full">
                  Volver a buscar
                </Link>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Owner banner */}
                {isOwner && <OwnerBanner profileSlug={profile.slug} />}

                <section className="rounded-[2.25rem] border border-base-300/70 bg-base-200/50 p-6 shadow-sm sm:p-8">
                  <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                    <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
                      <ProfileAvatar
                        src={profile.photoUrl}
                        fallbackSrc={profile.avatarFallback}
                        name={profile.displayName || profile.name}
                        size={104}
                      />
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h1 className="text-3xl font-extrabold tracking-tight text-base-content sm:text-4xl">
                            {profile.displayName || profile.name}
                          </h1>
                          {profile.verified ? (
                            <span className="badge badge-lg gap-1 rounded-full border-0 bg-primary/10 text-primary">
                              <BadgeCheck className="h-4 w-4" />
                              Verificado
                            </span>
                          ) : null}
                        </div>
                        <p className="mt-2 text-lg text-base-content/70">
                          {profile.profession} · {profile.category}
                        </p>
                        <p className="mt-1 text-sm text-base-content/60">
                          {profile.locality}, {profile.department}
                        </p>

                        <div className="mt-4 flex flex-wrap items-center gap-2">
                          <span className="badge rounded-full border-0 bg-primary/10 text-primary">
                            {profile.availability || 'Disponible'}
                          </span>
                          <span className="badge rounded-full border-0 bg-base-100 text-base-content/70">
                            <Star className="mr-1 h-3.5 w-3.5 text-warning" />
                            {profile.rating?.toFixed(1) ?? '0.0'} · {profile.reviewsCount ?? 0} reseñas
                          </span>
                          {profile.yearsExperience ? (
                            <span className="badge rounded-full border-0 bg-base-100 text-base-content/70">
                              {profile.yearsExperience} años de experiencia
                            </span>
                          ) : null}
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col gap-2 sm:flex-row lg:flex-col xl:flex-row">
                      {whatsappHref ? (
                        <a href={whatsappHref} target="_blank" rel="noreferrer" className="btn btn-primary rounded-full">
                          <MessageCircle className="h-4 w-4" />
                          WhatsApp
                        </a>
                      ) : null}
                      {phoneHref ? (
                        <a href={phoneHref} className="btn btn-outline rounded-full border-base-300 text-base-content">
                          <Phone className="h-4 w-4" />
                          Llamar
                        </a>
                      ) : null}
                      {emailHref ? (
                        <a href={emailHref} className="btn btn-outline rounded-full border-base-300 text-base-content">
                          <Mail className="h-4 w-4" />
                          Email
                        </a>
                      ) : null}
                    </div>
                  </div>

                  {tags.length ? (
                    <div className="mt-5 flex flex-wrap gap-2">
                      {tags.map((tag) => (
                        <span key={tag} className="rounded-full border border-base-300/70 bg-base-100 px-3 py-1 text-xs font-medium text-base-content/70">
                          {tag}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </section>

                <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
                  <div className="space-y-6">
                    <section className="rounded-[2rem] border border-base-300/70 bg-base-100 p-6 shadow-sm">
                      <h2 className="text-xl font-bold text-base-content">Sobre {profile.displayName || profile.name}</h2>
                      <p className="mt-3 leading-relaxed text-base-content/70">{profile.description}</p>
                    </section>

                    <section className="rounded-[2rem] border border-base-300/70 bg-base-100 p-6 shadow-sm">
                      <h2 className="text-xl font-bold text-base-content">Servicios ofrecidos</h2>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {tags.length ? tags.map((tag) => (
                          <span key={tag} className="badge rounded-full border-0 bg-base-200 text-base-content/70">{tag}</span>
                        )) : <p className="text-base-content/70">Información disponible en el perfil.</p>}
                      </div>
                    </section>

                    <section className="rounded-[2rem] border border-base-300/70 bg-base-100 p-6 shadow-sm">
                      <h2 className="text-xl font-bold text-base-content">Zona de servicio</h2>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {serviceArea.map((area) => (
                          <span key={area} className="badge rounded-full border-0 bg-base-200 text-base-content/70">{area}</span>
                        ))}
                      </div>
                    </section>
                  </div>

                  <aside className="space-y-6">
                    <section className="rounded-[2rem] border border-base-300/70 bg-base-100 p-6 shadow-sm">
                      <h2 className="text-xl font-bold text-base-content">Contacto</h2>
                      <div className="mt-4 space-y-3 text-sm text-base-content/70">
                        {profile.phone ? <p><span className="font-semibold text-base-content">Tel:</span> {profile.phone}</p> : null}
                        {profile.whatsapp ? <p><span className="font-semibold text-base-content">WhatsApp:</span> {profile.whatsapp}</p> : null}
                        {profile.email ? <p><span className="font-semibold text-base-content">Email:</span> {profile.email}</p> : null}
                        {profile.website ? <p><span className="font-semibold text-base-content">Sitio:</span> <a className="link link-primary" href={profile.website} target="_blank" rel="noreferrer">{profile.website}</a></p> : null}
                        {profile.instagram ? <p><span className="font-semibold text-base-content">Instagram:</span> <a className="link link-primary" href={profile.instagram} target="_blank" rel="noreferrer">{profile.instagram}</a></p> : null}
                        {profile.address ? <p><span className="font-semibold text-base-content">Dirección:</span> {profile.address}</p> : null}
                      </div>
                    </section>

                    <section className="rounded-[2rem] border border-base-300/70 bg-base-100 p-6 shadow-sm">
                      <h2 className="text-xl font-bold text-base-content">Experiencia</h2>
                      <p className="mt-3 text-sm text-base-content/70">
                        {profile.yearsExperience ? `Más de ${profile.yearsExperience} años de experiencia.` : 'Experiencia profesional disponible en el perfil.'}
                      </p>
                    </section>
                  </aside>
                </div>

                {/* Reviews section */}
                <section className="rounded-[2rem] border border-base-300/70 bg-base-200/50 p-6 shadow-sm sm:p-7">
                  <div className="flex items-end justify-between gap-3">
                    <div>
                      <h2 className="text-xl font-bold text-base-content">Reseñas</h2>
                      <p className="mt-1 text-sm text-base-content/60">
                        {reviewsQuery.isLoading
                          ? 'Cargando reseñas…'
                          : reviewsQuery.isError
                            ? 'No pudimos cargar las reseñas.'
                            : reviews.length > 0
                          ? `${reviews.length} reseña${reviews.length > 1 ? 's' : ''} · Promedio ${profile.rating?.toFixed(1) ?? '0.0'}`
                          : 'Todavía no hay reseñas.'}
                      </p>
                    </div>
                  </div>

                  {reviewError && (
                    <div className="mt-4 rounded-2xl border border-error/20 bg-error/10 p-4 text-sm text-error">
                      {reviewError}
                      <button onClick={() => setReviewError(null)} className="ml-2 underline">Cerrar</button>
                    </div>
                  )}

                  <div className="mt-5 space-y-4">
                    {reviews.map((review) => (
                      <ReviewCard key={review.id} review={review} />
                    ))}
                  </div>

                  {/* Review CTA / Form */}
                  <div className="mt-6">
                    {!isAuthenticated ? (
                      <div className="rounded-2xl border border-base-300/70 bg-base-100 p-6 text-center">
                        <h3 className="text-lg font-bold text-base-content">¿Querés dejar una reseña?</h3>
                        <p className="mt-2 text-sm text-base-content/70">
                          Iniciá sesión para compartir tu experiencia con este profesional.
                        </p>
                        <button
                          onClick={() => navigate(`/login?next=${encodeURIComponent(`/perfil/${slug}`)}`)}
                          className="btn btn-primary btn-sm mt-4 rounded-full"
                        >
                          <LogIn className="h-4 w-4" />
                          Iniciar sesión
                        </button>
                      </div>
                    ) : isOwner ? (
                      <div className="rounded-[2rem] border border-base-300/70 bg-base-100 p-6 shadow-sm">
                        <div className="flex flex-col items-center text-center sm:items-start sm:text-left">
                          <h3 className="text-lg font-bold text-base-content">Este es tu perfil</h3>
                          <p className="mt-2 max-w-md text-sm text-base-content/70">
                            No podés dejar una reseña sobre tu propio servicio. Podés editar la información desde tu área privada.
                          </p>
                          <Link
                            to="/mi-perfil/editar"
                            className="btn btn-primary btn-sm mt-4 rounded-full"
                          >
                            <Pencil className="h-4 w-4" />
                            Editar mi perfil
                          </Link>
                        </div>
                      </div>
                    ) : existingReview ? (
                      <div className="space-y-3">
                        <div className="rounded-2xl border border-base-300/70 bg-base-100 p-4 text-center text-sm text-base-content/60">
                          Ya dejaste una reseña para este perfil.
                          <span className="mt-1 block text-xs text-base-content/40">
                            Las reseñas enviadas no se pueden modificar.
                          </span>
                        </div>
                        <ReviewCard review={existingReview} />
                      </div>
                    ) : (
                      <ReviewForm onSubmit={handleSubmitReview} />
                    )}
                  </div>
                </section>

                {/* Similar profiles */}
                <section className="rounded-[2rem] border border-base-300/70 bg-base-200/50 p-6 shadow-sm sm:p-7">
                  <div className="flex items-end justify-between gap-3">
                    <div>
                      <h2 className="text-xl font-bold text-base-content">Perfiles similares</h2>
                      <p className="mt-1 text-sm text-base-content/60">Otras opciones dentro de la misma zona o categoría.</p>
                    </div>
                  </div>

                  <div className="mt-5 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
                    {(similarProfiles.length ? similarProfiles : []).map((item) => (
                      <ProfileCard key={item.id} profile={item} compact />
                    ))}
                  </div>
                </section>
              </div>
            )}
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
