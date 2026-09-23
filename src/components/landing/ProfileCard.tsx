import { BadgeCheck, MessageCircle, Star } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ProfileAvatar } from '../ProfileAvatar';

export interface ProfileCardProfile {
  id: string;
  slug: string;
  name: string;
  displayName?: string;
  category: string;
  profession: string;
  professionNormalized?: string;
  department: string;
  locality: string;
  shortDescription: string;
  description: string;
  photoUrl?: string;
  avatarFallback?: string;
  whatsapp?: string;
  availability?: string;
  verified?: boolean;
  rating?: number;
  reviewsCount?: number;
  tags?: string[];
  isFictionalDemo?: boolean;
}

interface ProfileCardProps {
  profile: ProfileCardProfile;
  compact?: boolean;
}

/**
 * Rich profile card used across featured profiles and search results.
 */
export function ProfileCard({ profile, compact = false }: ProfileCardProps) {
  const profileName = profile.displayName || profile.name;
  const areaLabel = `${profile.locality}, ${profile.department}`;
  const whatsappHref = profile.whatsapp ? `https://wa.me/${profile.whatsapp}` : null;
  const hasReviews = Boolean(profile.reviewsCount && profile.reviewsCount > 0);

  return (
    <article className="flex h-full flex-col justify-between rounded-[2rem] border border-base-300/70 bg-base-100 p-5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl sm:p-6">
      <div className="flex items-start gap-3">
        <ProfileAvatar
          src={profile.photoUrl}
          fallbackSrc={profile.avatarFallback}
          name={profileName}
          size={compact ? 52 : 64}
          className="shrink-0"
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="truncate text-lg font-bold text-base-content">{profileName}</h3>
              <p className="truncate text-sm text-base-content/60">
                {profile.profession} · {areaLabel}
              </p>
            </div>
            {profile.verified ? (
              <span className="badge badge-sm gap-1 rounded-full border-0 bg-primary/10 text-primary">
                <BadgeCheck className="h-3.5 w-3.5" />
                Verificado
              </span>
            ) : null}
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="badge badge-sm rounded-full border-0 bg-base-200 text-base-content/70">
              {profile.category}
            </span>
            {profile.availability ? (
              <span className="badge badge-sm rounded-full border-0 bg-primary/10 text-primary">
                {profile.availability}
              </span>
            ) : null}
          </div>
        </div>
      </div>

      <p className="mt-4 text-sm leading-relaxed text-base-content/70">
        {profile.shortDescription}
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {(profile.tags || []).slice(0, 3).map((tag) => (
          <span key={tag} className="rounded-full border border-base-300/70 bg-base-200/70 px-3 py-1 text-xs font-medium text-base-content/70">
            {tag}
          </span>
        ))}
      </div>

      <div className="mt-4 flex items-center gap-2 text-sm text-base-content/60">
        {hasReviews ? <>
          <Star className="h-4 w-4 text-warning" />
          <span className="font-semibold text-base-content">{profile.rating?.toFixed(1) ?? '—'}</span>
          <span>({profile.reviewsCount} reseñas)</span>
        </> : <span>Sin reseñas publicadas</span>}
      </div>

      <div className="mt-auto flex flex-col gap-2 pt-5 sm:flex-row">
        <Link to={`/perfil/${profile.slug}`} className="btn btn-primary btn-sm flex-1 rounded-full">
          Ver perfil
        </Link>
        {whatsappHref ? (
          <a
            href={whatsappHref}
            target="_blank"
            rel="noreferrer"
            className="btn btn-outline btn-sm gap-1.5 rounded-full border-base-300 text-base-content hover:border-primary hover:bg-primary/10 hover:text-primary"
          >
            <MessageCircle className="h-4 w-4" aria-hidden="true" />
            WhatsApp
          </a>
        ) : null}
      </div>
    </article>
  );
}
