import { apiClient } from '../api/client';
import type { Review } from '../types/profile';

export async function getReviewsByProfileId(profileId: string): Promise<Review[]> {
  const response = await apiClient.get<Review[]>('/reviews', { params: { profileId } });
  return response.data;
}

export async function getReviewsByAuthorUserId(authorUserId: string): Promise<Review[]> {
  const response = await apiClient.get<Review[]>('/reviews', { params: { authorUserId } });
  return response.data;
}

export async function createReview(review: Partial<Review> & { profileId: string; rating: number; comment: string }): Promise<Review> {
  const response = await apiClient.post<Review>('/reviews', {
    profileId: review.profileId,
    rating: review.rating,
    comment: review.comment,
    acceptedNoEditPolicy: review.acceptedNoEditPolicy === true,
  });
  return response.data;
}

export async function updateReview(): Promise<never> {
  throw new Error('Las reseñas publicadas no se pueden editar.');
}

export async function deleteReview(): Promise<never> {
  throw new Error('Las reseñas publicadas no se pueden eliminar desde esta cuenta.');
}

export async function userHasReviewedProfile(userId: string, profileId: string): Promise<Review | null> {
  const reviews = await getReviewsByAuthorUserId(userId);
  return reviews.find((review) => review.profileId === profileId) ?? null;
}
