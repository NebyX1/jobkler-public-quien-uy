/**
 * Profile service — fetches profiles from JSON Server and applies
 * the client-side filters the directory needs (Spanish text,
 * accents, slugs, category/department/locality, etc.).
 *
 * Endpoints:
 *   GET    /profiles
 *   GET    /profiles/:id
 *   GET    /profiles?slug=...
 *   POST   /profiles
 *   PATCH  /profiles/:id
 *   DELETE /profiles/:id
 */
import { API_BASE_URL } from '../config/api';
import { matchesProfileSearch, normalizeText } from '../utils/textSearch';
import type { PredictedLocation, Profile, ProfileFilters } from '../types/profile';

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

function paginate<T>(items: T[], page?: number | string, limit?: number): T[] {
  if (!limit) return items;
  const currentPage = Math.max(Number(page) || 1, 1);
  const pageSize = Math.max(Number(limit) || items.length, 1);
  const start = (currentPage - 1) * pageSize;
  return items.slice(start, start + pageSize);
}

function matchesSlugOrId(profile: Profile, value: string): boolean {
  const normalized = normalizeText(value).trim();
  if (!normalized) return true;
  return (
    normalizeText(profile.department) === normalized ||
    normalizeText(profile.departmentId) === normalized ||
    normalizeText(profile.locality) === normalized ||
    normalizeText(profile.localityId) === normalized
  );
}

export async function getProfiles(filters: ProfileFilters = {}): Promise<Profile[]> {
  const profiles = await fetchJson<Profile[]>('/profiles');
  const {
    q,
    department,
    departmentId,
    locality,
    localityId,
    category,
    categoryId,
    profession,
    featured,
    page,
    limit,
  } = filters;

  const normalizedDepartment = normalizeText(department).trim();
  const normalizedDepartmentId = normalizeText(departmentId).trim();
  const normalizedLocality = normalizeText(locality).trim();
  const normalizedLocalityId = normalizeText(localityId).trim();
  const normalizedCategory = normalizeText(category).trim();
  const normalizedCategoryId = normalizeText(categoryId).trim();
  const normalizedProfession = normalizeText(profession).trim();

  let filtered: Profile[] = Array.isArray(profiles) ? profiles.slice() : [];

  if (featured !== undefined && featured !== null) {
    const isFeatured = Boolean(featured);
    filtered = filtered.filter((profile) => Boolean(profile.featured) === isFeatured);
  }

  if (normalizedDepartment || normalizedDepartmentId) {
    filtered = filtered.filter((profile) => {
      if (normalizedDepartment && normalizeText(profile.department) === normalizedDepartment) {
        return true;
      }
      if (normalizedDepartmentId && profile.departmentId === normalizedDepartmentId) {
        return true;
      }
      return false;
    });
  }

  if (normalizedLocality || normalizedLocalityId) {
    filtered = filtered.filter((profile) => {
      if (normalizedLocality && normalizeText(profile.locality) === normalizedLocality) {
        return true;
      }
      if (normalizedLocalityId && profile.localityId === normalizedLocalityId) {
        return true;
      }
      return false;
    });
  }

  if (normalizedCategory || normalizedCategoryId) {
    filtered = filtered.filter((profile) => {
      if (normalizedCategory && normalizeText(profile.category) === normalizedCategory) {
        return true;
      }
      if (normalizedCategoryId && profile.categoryId === normalizedCategoryId) {
        return true;
      }
      return false;
    });
  }

  if (normalizedProfession) {
    filtered = filtered.filter((profile) => {
      const candidate = [profile.profession, profile.professionNormalized]
        .map(normalizeText)
        .join(' ');
      return candidate.includes(normalizedProfession);
    });
  }

  if (q) {
    filtered = filtered.filter((profile) => matchesProfileSearch(profile, q));
  }

  return paginate(filtered, page, limit);
}

export async function getProfileBySlug(slug: string): Promise<Profile | null> {
  const profiles = await fetchJson<Profile[]>(
    `/profiles?slug=${encodeURIComponent(slug)}`,
  );
  return Array.isArray(profiles) && profiles.length ? profiles[0] : null;
}

export async function getProfileById(id: string): Promise<Profile | null> {
  return fetchJson<Profile>(`/profiles/${encodeURIComponent(id)}`);
}

// Prepared for a future admin / profile management UI.
export async function createProfile(profile: Partial<Profile>): Promise<Profile> {
  return fetchJson<Profile>('/profiles', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  });
}

// Prepared for a future admin / profile management UI.
export async function updateProfile(
  id: string,
  profile: Partial<Profile>,
): Promise<Profile> {
  return fetchJson<Profile>(`/profiles/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  });
}

// Prepared for a future admin / profile management UI.
export async function deleteProfile(id: string): Promise<unknown> {
  return fetchJson<unknown>(`/profiles/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

export async function getFeaturedProfiles(): Promise<Profile[]> {
  return getProfiles({ featured: true });
}

export async function getFeaturedProfilesLimit(limit: number): Promise<Profile[]> {
  return getProfiles({ featured: true, limit });
}

/**
 * Used by the /cerca-de-mi page.
 *
 * Priority:
 *   1. Profiles in the predicted locality.
 *   2. Top up with profiles in the predicted department.
 *   3. Top up with featured profiles if we still don't have 6.
 */
export async function getProfilesByPredictedLocation(
  location: PredictedLocation,
): Promise<Profile[]> {
  const localityMatches = location.locality
    ? await getProfiles({ locality: location.locality, localityId: location.localityId })
    : [];

  if (localityMatches.length >= 6) {
    return localityMatches;
  }

  const departmentMatches = location.department
    ? await getProfiles({ department: location.department, departmentId: location.departmentId })
    : [];
  const featuredMatches = await getFeaturedProfiles();

  const merged = new Map<string, Profile>();
  [...localityMatches, ...departmentMatches, ...featuredMatches].forEach((profile) => {
    if (!merged.has(profile.id)) {
      merged.set(profile.id, profile);
    }
  });

  return Array.from(merged.values());
}

// Helper re-export so callers can compose route + query params without
// importing slug logic separately.
export { matchesSlugOrId };
