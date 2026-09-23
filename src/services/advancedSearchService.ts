import { apiClient } from '../api/client';
import type { Profile } from '../types/profile';

export interface AdvancedSearchInput {
  query: string;
  departmentId?: string;
  localityId?: string;
  limit?: number;
}

export interface SearchEvidence {
  sourceField: string;
  text: string;
  matchType: 'direct' | 'related';
  cosine: number | null;
}

export interface AdvancedSearchResult {
  profile: Profile;
  evidence: SearchEvidence;
  locationLabel: string;
}

export interface SearchClarificationOption {
  kind: 'department' | 'locality' | 'profession';
  id?: string;
  name: string;
  department?: string;
  departmentId?: string | null;
  localityId?: string | null;
}

export interface AdvancedSearchResponse {
  request_id: string;
  status: 'ok' | 'degraded' | 'ambiguous' | 'unsupported' | 'empty' | 'busy' | 'error';
  message: string;
  applied_filters?: {
    department?: string | null;
    departmentId?: string | null;
    locality?: string | null;
    localityId?: string | null;
    locationSource?: 'selected' | 'query' | 'national';
    profession?: string | null;
  };
  clarification?: {
    code?: string;
    requestedText?: string;
    options?: SearchClarificationOption[];
  };
  degradation?: string[];
  results: AdvancedSearchResult[];
}

export async function searchAdvanced(input: AdvancedSearchInput, signal?: AbortSignal): Promise<AdvancedSearchResponse> {
  return (await apiClient.post<AdvancedSearchResponse>('/search/advanced', input, { signal })).data;
}
