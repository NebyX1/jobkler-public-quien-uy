import { Star } from 'lucide-react';
import { ProfileAvatar } from '../ProfileAvatar';
import type { Review } from '../../types/profile';

interface ReviewCardProps {
  review: Review;
}

/**
 * Displays a single review with author info, rating, and comment.
 * Reviews are immutable after submission — no edit controls are shown.
 */
export function ReviewCard({ review }: ReviewCardProps) {
  const stars = Array.from({ length: 5 }, (_, i) => i < review.rating);

  return (
    <div className="rounded-2xl border border-base-300/70 bg-base-100 p-5 shadow-sm">
      <div className="flex items-start gap-3">
        <ProfileAvatar
          src={review.authorPicture}
          name={review.authorName}
          size={40}
          className="shrink-0"
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <span className="font-semibold text-base-content">{review.authorName}</span>
              <div className="mt-0.5 flex items-center gap-1">
                {stars.map((filled, i) => (
                  <Star
                    key={i}
                    className={`h-4 w-4 ${filled ? 'fill-warning text-warning' : 'text-base-content/20'}`}
                  />
                ))}
              </div>
            </div>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-base-content/70">
            {review.comment}
          </p>
          <p className="mt-2 text-xs text-base-content/40">
            {new Date(review.createdAt).toLocaleDateString('es-UY', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </p>
        </div>
      </div>
    </div>
  );
}
