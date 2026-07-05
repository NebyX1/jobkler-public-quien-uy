/**
 * Text utilities used by the search service.
 *
 * - `normalizeText` lowercases and strips diacritics so that
 *   "Minas" / "minás" / "MINAS" all match the same query.
 * - `matchesProfileSearch` does a single haystack search across
 *   the fields the directory exposes.
 */
import type { Profile } from '../types/profile';

export function normalizeText(value: unknown): string {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

export function matchesProfileSearch(profile: Profile, query: string): boolean {
  const normalizedQuery = normalizeText(query).trim();
  if (!normalizedQuery) return true;

  const haystack = [
    profile.name,
    profile.displayName,
    profile.profession,
    profile.professionNormalized,
    profile.category,
    profile.shortDescription,
    profile.description,
    profile.department,
    profile.locality,
    ...(Array.isArray(profile.tags) ? profile.tags : []),
    ...(Array.isArray(profile.serviceArea) ? profile.serviceArea : []),
  ]
    .map(normalizeText)
    .join(' ');

  return haystack.includes(normalizedQuery);
}
