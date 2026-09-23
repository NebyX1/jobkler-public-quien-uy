import { useEffect, useMemo, useRef, useState } from 'react';
import { Briefcase, Loader2, X } from 'lucide-react';

interface ProfessionAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  suggestions: string[];
  isLoading: boolean;
  inputId: string;
  fieldClasses: string;
  labelClasses: string;
  placeholder?: string;
}

const SUGGESTION_LIST_ID = 'profession-suggestions-list';

export function ProfessionAutocomplete({
  value,
  onChange,
  suggestions,
  isLoading,
  inputId,
  fieldClasses,
  labelClasses,
  placeholder = 'Electricista, sanitaria, albañilería…',
}: ProfessionAutocompleteProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const predictions = useMemo(() => suggestions.slice(0, 10), [suggestions]);

  const activeIndex = isOpen && predictions.length
    ? Math.min(highlightedIndex, predictions.length - 1)
    : -1;

  useEffect(() => {
    if (!isOpen) return;
    const closeOutside = (event: MouseEvent | TouchEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setIsOpen(false);
    };
    document.addEventListener('mousedown', closeOutside);
    document.addEventListener('touchstart', closeOutside);
    return () => {
      document.removeEventListener('mousedown', closeOutside);
      document.removeEventListener('touchstart', closeOutside);
    };
  }, [isOpen]);

  const choose = (prediction: string) => {
    onChange(prediction);
    setIsOpen(false);
    setHighlightedIndex(-1);
  };
  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown' && predictions.length) {
      event.preventDefault();
      setIsOpen(true);
      setHighlightedIndex((index) => (index + 1) % predictions.length);
    } else if (event.key === 'ArrowUp' && predictions.length) {
      event.preventDefault();
      setIsOpen(true);
      setHighlightedIndex((index) => (index <= 0 ? predictions.length - 1 : index - 1));
    } else if (event.key === 'Escape') {
      setIsOpen(false);
      setHighlightedIndex(-1);
    } else if (event.key === 'Enter' && isOpen && highlightedIndex >= 0) {
      event.preventDefault();
      choose(predictions[highlightedIndex]!);
    }
  };
  const showPanel = isOpen && value.trim().length >= 2;

  return (
    <div ref={containerRef} className="relative">
      <label htmlFor={inputId} className={labelClasses}>Profesión / oficio</label>
      <div className="relative">
        <Briefcase className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-base-content/45" aria-hidden="true" />
        <input
          id={inputId}
          type="text"
          value={value}
          onChange={(event) => { onChange(event.target.value); setIsOpen(event.target.value.trim().length >= 2); }}
          onFocus={() => setIsOpen(value.trim().length >= 2)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoComplete="off"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={showPanel}
          aria-controls={SUGGESTION_LIST_ID}
          aria-activedescendant={activeIndex >= 0 ? `${SUGGESTION_LIST_ID}-option-${activeIndex}` : undefined}
          className={`${fieldClasses} pl-11 pr-11`}
        />
        {value ? (
          <button type="button" onClick={() => { onChange(''); setIsOpen(false); }} className="absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full text-base-content/50 hover:bg-base-200" aria-label="Borrar profesión">
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : null}
      </div>
      {showPanel ? (
        <div className="absolute left-0 right-0 top-full z-50 mt-2 overflow-hidden rounded-2xl border border-base-300/70 bg-base-100/95 shadow-2xl backdrop-blur-xl">
          {isLoading ? (
            <div className="flex items-center gap-2 px-4 py-3 text-sm text-base-content/70"><Loader2 className="h-4 w-4 animate-spin text-primary" /> Cargando sugerencias…</div>
          ) : predictions.length ? (
            <ul id={SUGGESTION_LIST_ID} role="listbox" aria-label="Sugerencias de profesión" className="max-h-80 overflow-y-auto py-1">
              {predictions.map((prediction, index) => (
                <li
                  key={prediction}
                  id={`${SUGGESTION_LIST_ID}-option-${index}`}
                  role="option"
                  aria-selected={index === activeIndex}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => choose(prediction)}
                  className={`cursor-pointer px-4 py-3 text-sm font-semibold ${index === activeIndex ? 'bg-primary/15 text-base-content' : 'text-base-content hover:bg-base-200'}`}
                >
                  {prediction}
                </li>
              ))}
            </ul>
          ) : (
            <div className="px-4 py-3 text-sm text-base-content/60">No hay profesiones disponibles con ese texto.</div>
          )}
        </div>
      ) : null}
    </div>
  );
}
