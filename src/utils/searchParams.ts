/**
 * URL search-param helpers shared between the SearchPanel and the
 * results page. The Spanish market uses accented query keys
 * (`departamento`, `localidad`) and a free-text `q` for profession.
 *
 * Empty values are dropped, whitespace is trimmed.
 */

export interface SearchParamInput {
  q?: string;
  profession?: string;
  department?: string;
  locality?: string;
  category?: string;
  page?: number | string;
}

const clean = (value: string | number | undefined): string => {
  if (value === undefined || value === null) return '';
  return String(value).trim();
};

/**
 * Build a URLSearchParams instance with the canonical keys
 * used by /buscar routes.
 *
 * Falls back to `profession` when `q` is empty so callers can
 * pass either form.
 */
export function buildSearchParams(input: SearchParamInput = {}): URLSearchParams {
  const params = new URLSearchParams();

  const text = clean(input.q || input.profession);
  if (text) params.set('q', text);

  const department = clean(input.department);
  if (department) params.set('departamento', department);

  const locality = clean(input.locality);
  if (locality) params.set('localidad', locality);

  const category = clean(input.category);
  if (category) params.set('category', category);

  const page = clean(input.page);
  if (page) params.set('page', page);

  return params;
}

/**
 * String variant — convenient when the caller just wants
 * `?q=...&departamento=...` for `useNavigate`.
 */
export function buildSearchParamsString(input: SearchParamInput = {}): string {
  return buildSearchParams(input).toString();
}
