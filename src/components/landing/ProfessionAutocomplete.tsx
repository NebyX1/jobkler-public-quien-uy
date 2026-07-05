import { useEffect, useMemo, useRef, useState } from 'react';
import { Briefcase, Loader2, X } from 'lucide-react';
import { normalizeText } from '../../utils/normalizeText';
import {
  PROFESSION_AUTOCOMPLETE_MAX_RESULTS,
  PROFESSION_AUTOCOMPLETE_MIN_CHARS,
  buildProfessionSuggestions,
  createProfessionSearchIndex,
  getProfessionPredictions,
  type ProfessionPrediction,
  type ProfessionSuggestion,
  type SuggestionFilters,
} from '../../utils/professionSuggestions';
import type { Profile } from '../../types/profile';

interface ProfessionAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  onSelect?: (suggestion: ProfessionSuggestion) => void;
  profiles: Profile[];
  isLoadingProfiles: boolean;
  filters: SuggestionFilters;
  inputId: string;
  fieldClasses: string;
  labelClasses: string;
  placeholder?: string;
}

const SUGGESTION_LIST_ID = 'profession-suggestions-list';

/**
 * Accessible combobox (ARIA listbox pattern) that suggests professions
 * from the live profile set. Predictions only appear after the user
 * has typed 3+ characters, and they are guaranteed to exist in the
 * database (no hardcoded list).
 */
export function ProfessionAutocomplete({
  value,
  onChange,
  onSelect,
  profiles,
  isLoadingProfiles,
  filters,
  inputId,
  fieldClasses,
  labelClasses,
  placeholder = 'Electricista, psicóloga, albañil…',
}: ProfessionAutocompleteProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState<number>(-1);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Build the suggestion list filtered by dept/locality, then the
  // MiniSearch index on top of it. Both are memoized.
  const suggestions = useMemo<ProfessionSuggestion[]>(
    () => buildProfessionSuggestions(profiles, filters),
    [profiles, filters.department, filters.locality],
  );

  const index = useMemo(() => createProfessionSearchIndex(suggestions), [suggestions]);

  const predictions = useMemo<ProfessionPrediction[]>(() => {
    if (normalizeText(value).length < PROFESSION_AUTOCOMPLETE_MIN_CHARS) return [];
    return getProfessionPredictions(value, suggestions, index);
  }, [value, suggestions, index]);

  // Re-clamp the highlighted index when the prediction list changes.
  useEffect(() => {
    if (!isOpen) {
      setHighlightedIndex(-1);
      return;
    }
    if (predictions.length === 0) {
      setHighlightedIndex(-1);
    } else if (highlightedIndex >= predictions.length) {
      setHighlightedIndex(predictions.length - 1);
    }
  }, [predictions, isOpen, highlightedIndex]);

  // Close the panel when clicking outside the combobox.
  useEffect(() => {
    if (!isOpen) return;
    const onPointerDown = (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node | null;
      if (containerRef.current && target && !containerRef.current.contains(target)) {
        setIsOpen(false);
        setHighlightedIndex(-1);
      }
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('touchstart', onPointerDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('touchstart', onPointerDown);
    };
  }, [isOpen]);

  const openPanelIfNeeded = () => {
    if (normalizeText(value).length >= PROFESSION_AUTOCOMPLETE_MIN_CHARS) {
      setIsOpen(true);
    }
  };

  const handleInputChange = (next: string) => {
    onChange(next);
    if (normalizeText(next).length >= PROFESSION_AUTOCOMPLETE_MIN_CHARS) {
      setIsOpen(true);
    } else {
      setIsOpen(false);
      setHighlightedIndex(-1);
    }
  };

  const commitPrediction = (prediction: ProfessionPrediction) => {
    onChange(prediction.label);
    onSelect?.(prediction);
    setIsOpen(false);
    setHighlightedIndex(-1);
  };

  const clearValue = () => {
    onChange('');
    setIsOpen(false);
    setHighlightedIndex(-1);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      if (predictions.length === 0) return;
      event.preventDefault();
      setIsOpen(true);
      setHighlightedIndex((index) =>
        index < predictions.length - 1 ? index + 1 : 0,
      );
      return;
    }
    if (event.key === 'ArrowUp') {
      if (predictions.length === 0) return;
      event.preventDefault();
      setIsOpen(true);
      setHighlightedIndex((index) =>
        index > 0 ? index - 1 : predictions.length - 1,
      );
      return;
    }
    if (event.key === 'Escape') {
      if (isOpen) {
        event.preventDefault();
        setIsOpen(false);
        setHighlightedIndex(-1);
      }
      return;
    }
    if (event.key === 'Enter') {
      if (isOpen && highlightedIndex >= 0 && predictions[highlightedIndex]) {
        event.preventDefault();
        commitPrediction(predictions[highlightedIndex]);
      }
      return;
    }
  };

  const showPanel = isOpen && normalizeText(value).length >= PROFESSION_AUTOCOMPLETE_MIN_CHARS;
  const showLoadingHint = showPanel && isLoadingProfiles && predictions.length === 0;
  const showEmptyHint = showPanel && !isLoadingProfiles && predictions.length === 0;
  const activeDescendantId =
    showPanel && highlightedIndex >= 0 && predictions[highlightedIndex]
      ? `${SUGGESTION_LIST_ID}-option-${highlightedIndex}`
      : undefined;

  return (
    <div ref={containerRef} className="relative">
      <label htmlFor={inputId} className={labelClasses}>
        Profesión / oficio
      </label>
      <div className="relative">
        <Briefcase
          className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-base-content/45"
          aria-hidden="true"
        />
        <input
          id={inputId}
          type="text"
          value={value}
          onChange={(event) => handleInputChange(event.target.value)}
          onFocus={openPanelIfNeeded}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoComplete="off"
          spellCheck={false}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={showPanel}
          aria-controls={SUGGESTION_LIST_ID}
          aria-activedescendant={activeDescendantId}
          className={`${fieldClasses} pl-11 pr-11`}
        />
        {value ? (
          <button
            type="button"
            onClick={clearValue}
            className="absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full text-base-content/50 transition hover:bg-base-200 hover:text-base-content focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            aria-label="Borrar profesión"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : null}
      </div>

      {showPanel ? (
        <div className="absolute left-0 right-0 top-full z-50 mt-2 overflow-hidden rounded-2xl border border-base-300/70 bg-base-100/95 shadow-2xl backdrop-blur-xl">
          {showLoadingHint ? (
            <div className="flex items-center gap-2 px-4 py-3 text-sm text-base-content/70">
              <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden="true" />
              Cargando profesiones…
            </div>
          ) : null}

          {showEmptyHint ? (
            <div className="px-4 py-3 text-sm text-base-content/60">
              No hay profesiones disponibles con ese texto.
            </div>
          ) : null}

          {predictions.length > 0 ? (
            <ul
              id={SUGGESTION_LIST_ID}
              role="listbox"
              aria-label="Sugerencias de profesión"
              className="max-h-80 overflow-y-auto py-1"
            >
              {predictions.map((prediction, index) => {
                const isHighlighted = index === highlightedIndex;
                const locationNote = filters.locality
                  ? `en ${filters.locality}`
                  : filters.department
                    ? `en ${filters.department}`
                    : null;
                return (
                  <li
                    key={prediction.id}
                    id={`${SUGGESTION_LIST_ID}-option-${index}`}
                    role="option"
                    aria-selected={isHighlighted}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    onMouseDown={(event) => {
                      // Keep focus on the input (mousedown, not click).
                      event.preventDefault();
                    }}
                    onClick={() => commitPrediction(prediction)}
                    className={`flex cursor-pointer items-center justify-between gap-3 px-4 py-3 transition ${
                      isHighlighted
                        ? 'bg-primary/15 text-base-content'
                        : 'text-base-content hover:bg-base-200'
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">{prediction.label}</p>
                      <p className="truncate text-xs text-base-content/60">
                        {prediction.category || 'Profesión'}
                        {locationNote ? <> · en {locationNote}</> : null}
                      </p>
                    </div>
                    <span
                      className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                        isHighlighted
                          ? 'bg-primary text-primary-content'
                          : 'bg-base-200 text-base-content/70'
                      }`}
                    >
                      {prediction.count} {prediction.count === 1 ? 'perfil' : 'perfiles'}
                    </span>
                  </li>
                );
              })}
            </ul>
          ) : null}

          {predictions.length > 0 ? (
            <div className="border-t border-base-300/60 px-4 py-2 text-[11px] text-base-content/50">
              {PROFESSION_AUTOCOMPLETE_MAX_RESULTS} resultados máx. — enter para seleccionar, esc para cerrar
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
