import { apiClient } from '../api/client';
import type { Profile } from '../types/profile';

export interface AdvancedSearchInput {
  query: string;
  departmentId?: string;
  localityId?: string;
  locationScope?: 'national';
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

export interface AdvancedSearchSuggestion extends AdvancedSearchResult {
  reason: string;
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
  suggestions?: AdvancedSearchSuggestion[];
}

export type SearchProgressStage = 'interpretation' | 'location' | 'retrieval';

const PROGRESS_MEDIA_TYPE = 'application/x-ndjson';

export class AdvancedSearchRequestError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'AdvancedSearchRequestError';
    this.status = status;
  }
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === 'object' ? value as Record<string, unknown> : undefined;
}

function readResult(value: unknown, status: number): AdvancedSearchResponse {
  const data = asRecord(value);
  if (status < 200 || status >= 300) {
    const message = typeof data?.error === 'string' ? data.error : asRecord(data?.error)?.message ?? data?.message;
    throw new AdvancedSearchRequestError(status, typeof message === 'string' && message.trim()
      ? message
      : 'No pude completar la búsqueda. Probá de nuevo.');
  }
  if (typeof data?.status !== 'string' || typeof data.message !== 'string' || !Array.isArray(data.results)
    || (data.suggestions !== undefined && !Array.isArray(data.suggestions))) {
    throw new Error('Recibí una respuesta incompleta. Probá de nuevo.');
  }
  return value as AdvancedSearchResponse;
}

async function* readEventLines(body: ReadableStream<Uint8Array>) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let pending = '';
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      pending += decoder.decode(value, { stream: true });
      const lines = pending.split('\n');
      pending = lines.pop() ?? '';
      yield* lines;
    }
    pending += decoder.decode();
    if (pending) yield pending;
  } finally {
    // A terminal event or cancellation can finish consumption before the stream closes.
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}

export async function searchAdvanced(
  input: AdvancedSearchInput,
  signal?: AbortSignal,
  onProgress?: (stage: SearchProgressStage) => void,
): Promise<AdvancedSearchResponse> {
  const response = await apiClient.post<ReadableStream<Uint8Array>>('/search/advanced', input, {
    signal,
    adapter: 'fetch',
    responseType: 'stream',
    headers: { Accept: PROGRESS_MEDIA_TYPE },
    validateStatus: () => true,
  });

  const mediaType = String(response.headers['content-type'] ?? '').split(';', 1)[0].trim().toLowerCase();
  if (mediaType !== PROGRESS_MEDIA_TYPE) {
    let data: unknown;
    try {
      data = await new Response(response.data).json();
    } catch {
      signal?.throwIfAborted();
    }
    signal?.throwIfAborted();
    return readResult(data, response.status);
  }

  for await (const line of readEventLines(response.data)) {
    if (!line.trim()) continue;
    signal?.throwIfAborted();
    let event: Record<string, unknown> | undefined;
    try {
      event = asRecord(JSON.parse(line));
    } catch {
      throw new Error('Recibí una respuesta inválida. Probá de nuevo.');
    }
    if (event?.type === 'result' && typeof event.status === 'number') {
      return readResult(event.result, event.status);
    }
    const stage = event?.stage;
    if (event?.type === 'stage' && (stage === 'interpretation' || stage === 'location' || stage === 'retrieval')) {
      onProgress?.(stage);
    }
  }

  signal?.throwIfAborted();
  throw new Error('La búsqueda se interrumpió. Probá de nuevo.');
}
