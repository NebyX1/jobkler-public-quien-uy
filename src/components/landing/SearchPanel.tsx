import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { uruguayLocations, departmentList } from '../../data/uruguayLocations';
import { saveLastLocation } from '../../services/locationService';
import { getProfiles } from '../../services/profileService';
import { ProfessionAutocomplete } from './ProfessionAutocomplete';

interface SearchPanelProps {
  className?: string;
  initialProfession?: string;
  initialDepartment?: string;
  initialLocality?: string;
  compact?: boolean;
  onSearch?: (params: { profession: string; department: string; locality: string }) => void;
}

/**
 * Build URL search params from the current field values.
 * Empty values are omitted.
 */
function buildSearchParams({
  profession,
  department,
  locality,
}: {
  profession: string;
  department: string;
  locality: string;
}): string {
  const params = new URLSearchParams();
  if (profession.trim()) params.set('q', profession.trim());
  if (department) params.set('departamento', department);
  if (locality) params.set('localidad', locality);
  return params.toString();
}

/**
 * Central search component for the Quien.uy hero.
 *
 * Three fields:
 *   1. Profesión / oficio (text input with database-driven autocomplete)
 *   2. Departamento (select)
 *   3. Localidad (select, depends on departamento)
 *
 * The locality select is disabled until a department is selected.
 * Changing department resets the locality.
 *
 * The profession field predicts suggestions from the live profile set
 * served by JSON Server. Suggestions are guaranteed to exist in the
 * database (no hardcoded list, no AI calls).
 *
 * On submit, navigates to /buscar?q=...&departamento=...&localidad=...
 * or calls onSearch if provided.
 */
export function SearchPanel({
  className = '',
  initialProfession = '',
  initialDepartment = '',
  initialLocality = '',
  compact = false,
  onSearch,
}: SearchPanelProps) {
  const navigate = useNavigate();
  const [profession, setProfession] = useState(initialProfession);
  const [department, setDepartment] = useState(initialDepartment);
  const [locality, setLocality] = useState(initialLocality);

  // Sync external profession changes (e.g. from quick chips)
  useEffect(() => {
    setProfession(initialProfession);
  }, [initialProfession]);

  useEffect(() => {
    setDepartment(initialDepartment);
  }, [initialDepartment]);

  useEffect(() => {
    setLocality(initialLocality);
  }, [initialLocality]);

  const localities = useMemo(
    () => (department ? uruguayLocations[department] ?? [] : []),
    [department],
  );

  // Load all profiles once. The autocomplete derives its prediction
  // list from this set, filtered by department / locality on the fly.
  // The component never fetches on every keystroke.
  const { data: profiles = [], isLoading: isLoadingProfiles } = useQuery({
    queryKey: ['profession-suggestion-profiles'],
    queryFn: () => getProfiles(),
    staleTime: 5 * 60 * 1000,
  });

  const suggestionFilters = useMemo(
    () => ({ department: department || undefined, locality: locality || undefined }),
    [department, locality],
  );

  const handleDepartmentChange = useCallback(
    (value: string) => {
      setDepartment(value);
      // Reset locality when department changes
      setLocality('');
    },
    [],
  );

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const params = { profession, department, locality };
      if (department || locality) {
        saveLastLocation({ department, locality, departmentId: '', localityId: '' });
      }
      if (onSearch) {
        onSearch(params);
        return;
      }
      const queryString = buildSearchParams(params);
      navigate(queryString ? `/buscar?${queryString}` : '/buscar');
    },
    [profession, department, locality, onSearch, navigate],
  );

  const fieldClasses =
    'h-14 w-full rounded-2xl border border-base-300/70 bg-base-200 px-4 text-base text-base-content placeholder:text-base-content/40 transition focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/35';
  const labelClasses =
    'mb-2 block text-xs font-semibold uppercase tracking-wide text-base-content/60';

  return (
    <div
      className={`${compact ? 'mt-0' : 'mt-10'} max-w-5xl rounded-[2.25rem] border border-base-300/70 bg-base-100/85 p-3 shadow-2xl backdrop-blur-xl sm:p-4 ${className}`}
    >
      <form
        className={`grid grid-cols-1 gap-3 ${compact ? 'md:grid-cols-2 lg:grid-cols-[1.2fr_0.9fr_0.9fr_auto]' : 'md:grid-cols-2 lg:grid-cols-[1.35fr_1fr_1fr_auto]'} lg:items-end`}
        onSubmit={handleSubmit}
      >
        {/* Profesión / oficio — autocomplete */}
        <ProfessionAutocomplete
          inputId="search-profession"
          fieldClasses={fieldClasses}
          labelClasses={labelClasses}
          value={profession}
          onChange={setProfession}
          profiles={profiles}
          isLoadingProfiles={isLoadingProfiles}
          filters={suggestionFilters}
        />

        {/* Departamento */}
        <div>
          <label htmlFor="search-department" className={labelClasses}>
            Departamento
          </label>
          <select
            id="search-department"
            value={department}
            onChange={(e) => handleDepartmentChange(e.target.value)}
            className={fieldClasses}
          >
            <option value="">Departamento</option>
            {departmentList.map((dep) => (
              <option key={dep} value={dep}>
                {dep}
              </option>
            ))}
          </select>
        </div>

        {/* Localidad */}
        <div>
          <label htmlFor="search-locality" className={labelClasses}>
            Localidad
          </label>
          <select
            id="search-locality"
            value={locality}
            onChange={(e) => setLocality(e.target.value)}
            disabled={!department}
            className={`${fieldClasses} disabled:cursor-not-allowed disabled:opacity-60`}
          >
            <option value="">
              {department ? 'Localidad' : 'Elegí departamento primero'}
            </option>
            {localities.map((loc) => (
              <option key={loc} value={loc}>
                {loc}
              </option>
            ))}
          </select>
        </div>

        {/* Buscar button */}
        <button
          type="submit"
          className="btn btn-primary h-14 w-full rounded-2xl px-8 text-base font-semibold shadow-lg shadow-primary/20 transition-all hover:-translate-y-0.5 lg:w-auto"
        >
          <Search className="h-5 w-5" aria-hidden="true" />
          Buscar
        </button>
      </form>
    </div>
  );
}
