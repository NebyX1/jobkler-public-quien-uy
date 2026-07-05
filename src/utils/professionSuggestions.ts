/**
 * Profession suggestions.
 *
 * Builds a derived list of unique professions from the profile set
 * and indexes it with MiniSearch so the search panel can autocomplete
 * the "Profesión / oficio" field with predictions that are
 * guaranteed to exist in the database.
 *
 * No hardcoded lists, no AI calls, no remote services.
 */
import MiniSearch, { type SearchResult } from 'minisearch';
import { normalizeText } from './normalizeText';
import type { Profile } from '../types/profile';

export interface ProfessionSuggestion {
  id: string;
  label: string;
  normalizedLabel: string;
  category: string;
  count: number;
  departments: string[];
  localities: string[];
  profileIds: string[];
}

export interface SuggestionFilters {
  department?: string;
  locality?: string;
}

export interface ProfessionPrediction extends ProfessionSuggestion {
  /** "exact" = starts with query, "fuzzy" = match was approximate. */
  matchKind: 'exact' | 'fuzzy';
}

const MAX_PREDICTIONS = 6;
const MIN_QUERY_LENGTH = 3;

/**
 * Build the unique profession suggestion list from a profile set,
 * optionally filtered by department / locality first.
 */
export function buildProfessionSuggestions(
  profiles: Profile[],
  filters: SuggestionFilters = {},
): ProfessionSuggestion[] {
  if (!Array.isArray(profiles) || profiles.length === 0) return [];

  const filtered = profiles.filter((profile) => {
    if (filters.department && profile.department !== filters.department) return false;
    if (filters.locality && profile.locality !== filters.locality) return false;
    return true;
  });

  const groups = new Map<string, ProfessionSuggestion>();

  for (const profile of filtered) {
    const label = String(profile.profession || '').trim();
    if (!label) continue;

    const normalized = normalizeText(label);
    if (!normalized) continue;

    const existing = groups.get(normalized);
    if (!existing) {
      groups.set(normalized, {
        id: normalized,
        label,
        normalizedLabel: normalized,
        category: profile.category || '',
        count: 1,
        departments: profile.department ? [profile.department] : [],
        localities: profile.locality ? [profile.locality] : [],
        profileIds: [profile.id],
      });
      continue;
    }

    existing.count += 1;
    if (profile.id) existing.profileIds.push(profile.id);
    if (profile.department && !existing.departments.includes(profile.department)) {
      existing.departments.push(profile.department);
    }
    if (profile.locality && !existing.localities.includes(profile.locality)) {
      existing.localities.push(profile.locality);
    }
  }

  return Array.from(groups.values()).sort((a, b) => {
    if (b.count !== a.count) return b.count - a.count;
    return a.label.localeCompare(b.label, 'es');
  });
}

/**
 * Build a MiniSearch index over the suggestion list.
 *
 * - Searches across `label` and `normalizedLabel`.
 * - `prefix: true` powers "ele" -> "Electricista".
 * - `fuzzy: 0.2` is conservative; the spec asked us to keep
 *   suggestions close to the query (no random matches).
 */
export function createProfessionSearchIndex(
  suggestions: ProfessionSuggestion[],
): MiniSearch<ProfessionSuggestion> {
  const index = new MiniSearch<ProfessionSuggestion>({
    idField: 'id',
    fields: ['label', 'normalizedLabel', 'category'],
    storeFields: ['id', 'label', 'normalizedLabel', 'category', 'count', 'profileIds'],
    searchOptions: {
      prefix: true,
      fuzzy: 0.2,
      boost: { label: 3, normalizedLabel: 3, category: 1 },
    },
  });

  if (suggestions.length > 0) {
    index.addAll(suggestions);
  }
  return index;
}

function sortExactFirst(
  results: SearchResult[],
  normalizedQuery: string,
): SearchResult[] {
  return results.slice().sort((a, b) => {
    const aExact = (a as { normalizedLabel?: string }).normalizedLabel
      ? String((a as { normalizedLabel?: string }).normalizedLabel).startsWith(normalizedQuery)
      : String(a.id).startsWith(normalizedQuery);
    const bExact = (b as { normalizedLabel?: string }).normalizedLabel
      ? String((b as { normalizedLabel?: string }).normalizedLabel).startsWith(normalizedQuery)
      : String(b.id).startsWith(normalizedQuery);
    if (aExact !== bExact) return aExact ? -1 : 1;
    const aScore = (a as { score?: number }).score ?? 0;
    const bScore = (b as { score?: number }).score ?? 0;
    if (aScore !== bScore) return bScore - aScore;
    return String(a.id).localeCompare(String(b.id), 'es');
  });
}

/**
 * Get up to 6 profession predictions for a query.
 *
 * - Returns `[]` if the query has fewer than 3 chars.
 * - Combines prefix matches (MiniSearch) with a normalized
 *   `startsWith` pass so that typos / accents still work even when
 *   MiniSearch's fuzzy threshold is not enough.
 * - Never returns a profession that is not in `suggestions`.
 */
export function getProfessionPredictions(
  query: string,
  suggestions: ProfessionSuggestion[],
  index: MiniSearch<ProfessionSuggestion>,
): ProfessionPrediction[] {
  const normalizedQuery = normalizeText(query);
  if (normalizedQuery.length < MIN_QUERY_LENGTH) return [];
  if (suggestions.length === 0) return [];

  const byId = new Map<string, ProfessionSuggestion>();
  suggestions.forEach((item) => byId.set(item.id, item));

  const seen = new Set<string>();
  const out: ProfessionPrediction[] = [];

  // Pass 1: MiniSearch (prefix + fuzzy).
  try {
    const results = index.search(normalizedQuery);
    const sorted = sortExactFirst(results, normalizedQuery);
    for (const hit of sorted) {
      const id = String(hit.id);
      const suggestion = byId.get(id);
      if (!suggestion || seen.has(id)) continue;
      seen.add(id);
      out.push({
        ...suggestion,
        matchKind: id.startsWith(normalizedQuery) ? 'exact' : 'fuzzy',
      });
      if (out.length >= MAX_PREDICTIONS) return out;
    }
  } catch {
    // MiniSearch can throw on empty indexes or odd inputs — fall
    // through to the manual pass below.
  }

  // Pass 2: normalized startsWith — guarantees we never miss
  // "Electricista" when typing "ele" even if MiniSearch's ranking
  // moved it down.
  for (const suggestion of suggestions) {
    if (seen.has(suggestion.id)) continue;
    if (suggestion.normalizedLabel.startsWith(normalizedQuery)) {
      out.push({ ...suggestion, matchKind: 'exact' });
      seen.add(suggestion.id);
      if (out.length >= MAX_PREDICTIONS) return out;
    }
  }

  // Pass 3: substring match (still strictly within the dataset).
  for (const suggestion of suggestions) {
    if (seen.has(suggestion.id)) continue;
    if (suggestion.normalizedLabel.includes(normalizedQuery)) {
      out.push({ ...suggestion, matchKind: 'exact' });
      seen.add(suggestion.id);
      if (out.length >= MAX_PREDICTIONS) return out;
    }
  }

  return out;
}

export const PROFESSION_AUTOCOMPLETE_MIN_CHARS = MIN_QUERY_LENGTH;
export const PROFESSION_AUTOCOMPLETE_MAX_RESULTS = MAX_PREDICTIONS;
