import axios from 'axios';
import { apiClient } from '../api/client';
import type { PredictedLocation, Profile, ProfileFilters } from '../types/profile';

export interface ProfilesPage {
  items: Profile[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface HomeSummary {
  metrics: { profiles: number; categories: number; departments: number; reviews: number };
  featured: Profile[];
}

export async function getHomeSummary(): Promise<HomeSummary> {
  return (await apiClient.get<HomeSummary>('/home')).data;
}

export async function getProfilesPage(filters: ProfileFilters = {}): Promise<ProfilesPage> {
  const response = await apiClient.get<ProfilesPage>('/profiles', { params: filters });
  return response.data;
}

export async function getProfiles(filters: ProfileFilters = {}): Promise<Profile[]> {
  return (await getProfilesPage({ limit: 50, ...filters })).items;
}

export async function getProfileBySlug(slug: string): Promise<Profile | null> {
  try {
    const response = await apiClient.get<Profile>(`/profiles/${encodeURIComponent(slug)}`);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) return null;
    throw error;
  }
}

export const getProfileById = getProfileBySlug;

export async function getProfileByOwnerUserId(): Promise<Profile | null> {
  try {
    const response = await apiClient.get<Profile>('/profiles/me');
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) return null;
    throw error;
  }
}

function profileInput(input: Partial<Profile> | Record<string, unknown>) {
  const allowed = [
    'displayName', 'categoryId', 'category', 'profession', 'shortDescription', 'description',
    'photoUrl', 'phone', 'whatsapp', 'email', 'website', 'instagram', 'department',
    'departmentId', 'locality', 'localityId', 'address', 'serviceArea', 'tags',
    'availability', 'yearsExperience',
  ] as const;
  const data = input as Record<string, unknown>;
  return Object.fromEntries(allowed.filter((key) => key in data).map((key) => [key, data[key]]));
}

export async function createProfileForUser(
  input: Partial<Profile> | Record<string, unknown>,
): Promise<Profile> {
  const response = await apiClient.post<Profile>('/profiles', profileInput(input));
  return response.data;
}

export async function updateOwnedProfile(
  id: string,
  input: Partial<Profile> | Record<string, unknown>,
): Promise<Profile> {
  const response = await apiClient.patch<Profile>(`/profiles/${encodeURIComponent(id)}`, profileInput(input));
  return response.data;
}

export async function deleteOwnedProfile(id: string): Promise<void> {
  await apiClient.delete(`/profiles/${encodeURIComponent(id)}`);
}

export async function setOwnedProfileStatus(
  id: string,
  status: 'active' | 'inactive',
): Promise<Profile> {
  const response = await apiClient.post<Profile>(`/profiles/${encodeURIComponent(id)}/status`, { status });
  return response.data;
}

export function deactivateOwnedProfile(id: string): Promise<Profile> {
  return setOwnedProfileStatus(id, 'inactive');
}

export function reactivateOwnedProfile(id: string): Promise<Profile> {
  return setOwnedProfileStatus(id, 'active');
}

export async function getFeaturedProfiles(): Promise<Profile[]> {
  return getProfiles({ featured: true, limit: 6 });
}

export async function getFeaturedProfilesLimit(limit: number): Promise<Profile[]> {
  return getProfiles({ featured: true, limit });
}

export async function getProfilesByPredictedLocation(location: PredictedLocation): Promise<Profile[]> {
  if (location.locality || location.localityId) {
    return getProfiles({
      department: location.department || undefined,
      departmentId: location.departmentId || undefined,
      locality: location.locality || undefined,
      localityId: location.localityId || undefined,
      limit: 50,
    });
  }
  if (location.department || location.departmentId) {
    return getProfiles({
      department: location.department || undefined,
      departmentId: location.departmentId || undefined,
      limit: 50,
    });
  }
  return [];
}

export async function getProfessionSuggestions(q: string): Promise<string[]> {
  const response = await apiClient.get<{ suggestions: string[] }>('/suggestions', { params: { q } });
  return response.data.suggestions;
}

export function matchesSlugOrId(profile: Profile, value: string): boolean {
  const normalize = (input: string | undefined) => (input || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  return [profile.department, profile.departmentId, profile.locality, profile.localityId]
    .some((candidate) => normalize(candidate) === normalize(value));
}
