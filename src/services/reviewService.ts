/**
 * Review service — manages reviews via JSON Server.
 *
 * Endpoints:
 *   GET    /reviews
 *   GET    /reviews?profileId=...
 *   GET    /reviews?authorUserId=...
 *   POST   /reviews
 *   PATCH  /reviews/:id
 *   DELETE /reviews/:id
 *
 * NOTE: JSON Server cannot enforce ownership or uniqueness constraints.
 * The frontend enforces:
 *   - A user cannot review their own profile.
 *   - A user cannot leave more than one review per profile.
 *   - Only authenticated users can create reviews.
 * These rules MUST be enforced by the real backend before production.
 */
import { API_BASE_URL } from '../config/api';
import type { Review } from '../types/profile';

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  if (response.status === 204) {
    return null as T;
  }
  return (await response.json()) as T;
}

export async function getReviewsByProfileId(profileId: string): Promise<Review[]> {
  const reviews = await fetchJson<Review[]>(
    `/reviews?profileId=${encodeURIComponent(profileId)}`,
  );
  return Array.isArray(reviews)
    ? reviews.filter((r) => r.status === 'published')
    : [];
}

export async function getReviewsByAuthorUserId(authorUserId: string): Promise<Review[]> {
  const reviews = await fetchJson<Review[]>(
    `/reviews?authorUserId=${encodeURIComponent(authorUserId)}`,
  );
  return Array.isArray(reviews) ? reviews : [];
}

export async function createReview(review: Omit<Review, 'id' | 'createdAt' | 'updatedAt'>): Promise<Review> {
  const now = new Date().toISOString();
  return fetchJson<Review>('/reviews', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...review,
      id: `review-${Date.now()}`,
      createdAt: now,
      updatedAt: now,
    }),
  });
}

export async function updateReview(
  id: string,
  partial: Partial<Pick<Review, 'rating' | 'comment' | 'status'>>,
): Promise<Review> {
  return fetchJson<Review>(`/reviews/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...partial,
      updatedAt: new Date().toISOString(),
    }),
  });
}

export async function deleteReview(id: string): Promise<unknown> {
  return fetchJson<unknown>(`/reviews/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

export async function userHasReviewedProfile(
  userId: string,
  profileId: string,
): Promise<Review | null> {
  const reviews = await fetchJson<Review[]>(
    `/reviews?authorUserId=${encodeURIComponent(userId)}&profileId=${encodeURIComponent(profileId)}`,
  );
  return Array.isArray(reviews) && reviews.length ? reviews[0] : null;
}

/**
 * Recalculate and update a profile's rating and reviewsCount
 * by aggregating all published reviews. This is mock behavior —
 * the real backend must handle this server-side.
 */
export async function recalculateProfileRating(profileId: string): Promise<void> {
  const reviews = await getReviewsByProfileId(profileId);
  if (reviews.length === 0) {
    await fetch(`${API_BASE_URL}/profiles/${encodeURIComponent(profileId)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rating: 0, reviewsCount: 0 }),
    });
    return;
  }

  const total = reviews.reduce((sum, r) => sum + r.rating, 0);
  const average = Math.round((total / reviews.length) * 10) / 10;

  await fetch(`${API_BASE_URL}/profiles/${encodeURIComponent(profileId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rating: average, reviewsCount: reviews.length }),
  });
}
