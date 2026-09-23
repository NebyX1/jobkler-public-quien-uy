import { apiClient } from '../api/client';
import type { Category, Department, Locality, PredictedLocation } from '../types/profile';

export interface CatalogResponse {
  categories: Array<Category & { count: number }>;
  departments: Department[];
  localities: Array<Locality & { departmentSlug: string; profileCount: number }>;
}

const LAST_DEPARTMENT_KEY = 'quien:lastDepartment';
const LAST_DEPARTMENT_ID_KEY = 'quien:lastDepartmentId';
const LAST_LOCALITY_KEY = 'quien:lastLocality';
const LAST_LOCALITY_ID_KEY = 'quien:lastLocalityId';

export async function getCatalog(): Promise<CatalogResponse> {
  return (await apiClient.get<CatalogResponse>('/catalog')).data;
}

export function saveLastLocation(input: PredictedLocation): void {
  if (typeof window === 'undefined') return;
  if (input.department) window.localStorage.setItem(LAST_DEPARTMENT_KEY, input.department);
  if (input.departmentId) window.localStorage.setItem(LAST_DEPARTMENT_ID_KEY, input.departmentId);
  if (input.locality) window.localStorage.setItem(LAST_LOCALITY_KEY, input.locality);
  if (input.localityId) window.localStorage.setItem(LAST_LOCALITY_ID_KEY, input.localityId);
}

export function getPredictedLocation(): PredictedLocation {
  if (typeof window === 'undefined') return { department: '', locality: '' };
  const params = new URLSearchParams(window.location.search);
  const queryDepartment = params.get('departamento') || params.get('department') || '';
  const queryLocality = params.get('localidad') || params.get('locality') || '';
  if (queryDepartment || queryLocality) {
    return {
      department: queryDepartment,
      locality: queryLocality,
      departmentId: params.get('departmentId') || undefined,
      localityId: params.get('localityId') || undefined,
    };
  }
  return {
    department: window.localStorage.getItem(LAST_DEPARTMENT_KEY) || '',
    departmentId: window.localStorage.getItem(LAST_DEPARTMENT_ID_KEY) || undefined,
    locality: window.localStorage.getItem(LAST_LOCALITY_KEY) || '',
    localityId: window.localStorage.getItem(LAST_LOCALITY_ID_KEY) || undefined,
  };
}

export async function getDepartments(): Promise<string[]> {
  const catalog = await getCatalog();
  return catalog.departments.map((item) => item.name);
}

export async function getLocalitiesByDepartment(departmentNameOrId: string): Promise<string[]> {
  const catalog = await getCatalog();
  const normalized = departmentNameOrId.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  return catalog.localities
    .filter((item) => [item.department, item.departmentId].some((value) =>
      value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase() === normalized))
    .map((item) => item.name);
}
