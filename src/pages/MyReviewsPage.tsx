import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Star, ExternalLink } from 'lucide-react';
import { useAuth } from '../lib/auth';
import { getReviewsByAuthorUserId } from '../services/reviewService';
import { ReviewCard } from '../components/profiles/ReviewCard';

/**
 * My Reviews page — shows reviews written by the current user.
 * Reviews are immutable after submission.
 */
export function MyReviewsPage() {
  const { user } = useAuth();

  const {
    data: reviews = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['my-reviews', user?.fusionauth_user_id],
    queryFn: () => getReviewsByAuthorUserId(user!.fusionauth_user_id),
    enabled: Boolean(user?.fusionauth_user_id),
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-extrabold text-base-content">Mis reseñas</h1>
        <p className="mt-1 text-sm text-base-content/60">
          Reseñas que escribiste para otros profesionales.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-32 w-full rounded-2xl" />
          ))}
        </div>
      ) : isError ? (
        <div className="rounded-[2rem] border border-error/20 bg-error/10 p-8 text-center">
          <p className="text-base-content">Error al cargar tus reseñas.</p>
        </div>
      ) : reviews.length === 0 ? (
        <div className="rounded-[2rem] border border-base-300/70 bg-base-200/50 p-8 text-center shadow-sm sm:p-12">
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <Star className="h-8 w-8 text-primary" />
          </div>
          <h2 className="text-xl font-bold text-base-content">
            Todavía no escribiste reseñas
          </h2>
          <p className="mt-3 max-w-md mx-auto text-sm text-base-content/70">
            Cuando dejes una reseña en un perfil profesional, aparecerá acá.
          </p>
          <Link
            to="/buscar"
            className="btn btn-primary mt-6 rounded-full"
          >
            Buscar profesionales
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {reviews.map((review) => (
            <div key={review.id} className="space-y-2">
              <ReviewCard review={review} />
              <div className="flex items-center gap-2 pl-2">
                <Link
                  to={`/perfil/${review.profileSlug}`}
                  className="btn btn-ghost btn-xs rounded-full text-primary"
                >
                  <ExternalLink className="h-3 w-3" />
                  Ver perfil
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
