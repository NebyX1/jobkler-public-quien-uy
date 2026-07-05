/**
 * Location service.
 *
 * `getPredictedLocation()` is read-only and is used by the
 * /cerca-de-mi page. It picks the location in this order:
 *   1. URL search params (`departamento` / `localidad`)
 *   2. localStorage (`quien:lastDepartment` / `quien:lastLocality`)
 *   3. Default: Lavalleja / Minas
 *
 * It NEVER asks for browser geolocation on page load. The user
 * has to click the "Usar mi ubicación" button for that.
 */
import { API_BASE_URL } from '../config/api';
import type { PredictedLocation } from '../types/profile';

const DEFAULT_LOCATION: PredictedLocation = {
  department: 'Lavalleja',
  locality: 'Minas',
  departmentId: 'lavalleja',
  localityId: 'minas',
};

const LAST_DEPARTMENT_KEY = 'quien:lastDepartment';
const LAST_DEPARTMENT_ID_KEY = 'quien:lastDepartmentId';
const LAST_LOCALITY_KEY = 'quien:lastLocality';
const LAST_LOCALITY_ID_KEY = 'quien:lastLocalityId';

function getQueryLocation(): Partial<PredictedLocation> {
  if (typeof window === 'undefined') return {};
  const params = new URLSearchParams(window.location.search);
  return {
    department: params.get('departamento') || params.get('department') || undefined,
    locality: params.get('localidad') || params.get('locality') || undefined,
    departmentId: params.get('departmentId') || undefined,
    localityId: params.get('localityId') || undefined,
  };
}

export function saveLastLocation(input: PredictedLocation): void {
  if (typeof window === 'undefined') return;
  if (input.department) window.localStorage.setItem(LAST_DEPARTMENT_KEY, input.department);
  if (input.departmentId) window.localStorage.setItem(LAST_DEPARTMENT_ID_KEY, input.departmentId);
  if (input.locality) window.localStorage.setItem(LAST_LOCALITY_KEY, input.locality);
  if (input.localityId) window.localStorage.setItem(LAST_LOCALITY_ID_KEY, input.localityId);
}

export function getPredictedLocation(): PredictedLocation {
  const fromQuery = getQueryLocation();
  if (fromQuery.department || fromQuery.locality) {
    return {
      department: fromQuery.department || DEFAULT_LOCATION.department,
      locality: fromQuery.locality || DEFAULT_LOCATION.locality,
      departmentId: fromQuery.departmentId || DEFAULT_LOCATION.departmentId,
      localityId: fromQuery.localityId || DEFAULT_LOCATION.localityId,
    };
  }

  if (typeof window !== 'undefined') {
    const department = window.localStorage.getItem(LAST_DEPARTMENT_KEY);
    const departmentId = window.localStorage.getItem(LAST_DEPARTMENT_ID_KEY);
    const locality = window.localStorage.getItem(LAST_LOCALITY_KEY);
    const localityId = window.localStorage.getItem(LAST_LOCALITY_ID_KEY);
    if (department || locality) {
      return {
        department: department || DEFAULT_LOCATION.department,
        locality: locality || DEFAULT_LOCATION.locality,
        departmentId: departmentId || DEFAULT_LOCATION.departmentId,
        localityId: localityId || DEFAULT_LOCATION.localityId,
      };
    }
  }

  return { ...DEFAULT_LOCATION };
}

export async function getDepartments(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/departments`);
  if (!response.ok) {
    throw new Error(`Failed to load departments (${response.status})`);
  }
  const data = (await response.json()) as { name: string }[];
  return data.map((item) => item.name).sort();
}

export async function getLocalitiesByDepartment(
  departmentNameOrId: string,
): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/localities`);
  if (!response.ok) {
    throw new Error(`Failed to load localities (${response.status})`);
  }
  const data = (await response.json()) as {
    name: string;
    department: string;
    departmentId: string;
  }[];
  return data
    .filter(
      (item) =>
        item.department === departmentNameOrId || item.departmentId === departmentNameOrId,
    )
    .map((item) => item.name)
    .sort();
}
