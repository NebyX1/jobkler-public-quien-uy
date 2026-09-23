import { useState } from 'react';
import { Star, Send } from 'lucide-react';

interface ReviewFormValues {
  rating: number;
  comment: string;
}

interface ReviewFormProps {
  onSubmit: (values: ReviewFormValues) => Promise<void>;
}

/**
 * Review form with star rating, comment, and no-edit policy checkbox.
 *
 * Reviews are immutable after submission. The user must acknowledge
 * this before the submit button is enabled.
 *
 * Frontend guard for reviews. The Flask backend also enforces
 * ownership, uniqueness, and immutability rules in production.
 */
export function ReviewForm({ onSubmit }: ReviewFormProps) {
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [comment, setComment] = useState('');
  const [acceptedNoEditPolicy, setAcceptedNoEditPolicy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const canSubmit =
    rating >= 1 &&
    rating <= 5 &&
    comment.trim().length >= 10 &&
    comment.trim().length <= 500 &&
    acceptedNoEditPolicy &&
    !submitting;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (rating < 1 || rating > 5) {
      setError('Elegí una calificación.');
      return;
    }
    if (comment.trim().length < 10) {
      setError('Escribí un comentario de al menos 10 caracteres.');
      return;
    }
    if (comment.trim().length > 500) {
      setError('La reseña no puede superar los 500 caracteres.');
      return;
    }
    if (!acceptedNoEditPolicy) {
      setError('Tenés que aceptar que la reseña no podrá modificarse después.');
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit({ rating, comment: comment.trim() });
      setRating(0);
      setComment('');
      setAcceptedNoEditPolicy(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al enviar la reseña.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="rounded-2xl border border-base-300/70 bg-base-200/50 p-5 shadow-sm">
      <h3 className="font-bold text-base-content">Dejar una reseña</h3>

      {/* Star rating */}
      <div className="mt-4">
        <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-base-content/60">
          Calificación
        </label>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((value) => {
            const filled = value <= (hoverRating || rating);
            return (
              <button
                key={value}
                type="button"
                onClick={() => setRating(value)}
                onMouseEnter={() => setHoverRating(value)}
                onMouseLeave={() => setHoverRating(0)}
                className="p-0.5 transition-transform hover:scale-110"
                aria-label={`${value} estrella${value > 1 ? 's' : ''}`}
              >
                <Star
                  className={`h-7 w-7 ${
                    filled
                      ? 'fill-warning text-warning'
                      : 'text-base-content/20 hover:text-warning/50'
                  }`}
                />
              </button>
            );
          })}
        </div>
      </div>

      {/* Comment */}
      <div className="mt-4">
        <label
          htmlFor="review-comment"
          className="mb-2 block text-xs font-semibold uppercase tracking-wide text-base-content/60"
        >
          Comentario
        </label>
        <textarea
          id="review-comment"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={4}
          maxLength={500}
          placeholder="Contá tu experiencia con este profesional…"
          className="w-full rounded-2xl border border-base-300/70 bg-base-100 px-4 py-3 text-sm text-base-content placeholder:text-base-content/40 transition focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/35"
        />
        <p className="mt-1 text-right text-xs text-base-content/40">
          {comment.length}/500
        </p>
      </div>

      {/* No-edit policy checkbox */}
      <div className="mt-4 rounded-2xl border border-base-300/70 bg-base-100/60 p-4">
        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            checked={acceptedNoEditPolicy}
            onChange={(e) => setAcceptedNoEditPolicy(e.target.checked)}
            className="checkbox checkbox-primary checkbox-sm mt-0.5"
          />
          <span className="text-sm text-base-content">
            Entiendo que una vez enviada, la reseña no se podrá modificar.
            <span className="mt-0.5 block text-xs text-base-content/60">
              Revisá bien tu comentario antes de enviarlo.
            </span>
          </span>
        </label>
      </div>

      {error && (
        <p className="mt-2 text-sm text-error">{error}</p>
      )}

      {/* Submit */}
      <div className="mt-4">
        <button
          type="submit"
          disabled={!canSubmit}
          className="btn btn-primary btn-sm rounded-full"
        >
          {submitting ? (
            <span className="loading loading-spinner loading-xs" />
          ) : (
            <Send className="h-4 w-4" />
          )}
          Enviar reseña
        </button>
      </div>
    </form>
  );
}
