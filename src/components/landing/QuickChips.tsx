import { QUICK_CHIPS } from '../../pages/landing/landingData';

interface QuickChipsProps {
  onSelect?: (value: string) => void;
}

/**
 * Horizontally scrollable row of quick-search pill buttons.
 * When onSelect is provided, clicking a chip sets the profession
 * field in the parent SearchPanel.
 */
export function QuickChips({ onSelect }: QuickChipsProps) {
  return (
    <div
      className="no-scrollbar mt-5 flex gap-2 overflow-x-auto px-1 py-1 lg:flex-wrap lg:overflow-visible"
      role="group"
      aria-label="Búsquedas rápidas"
    >
      {QUICK_CHIPS.map((chip) => (
        <button
          key={chip}
          type="button"
          onClick={() => onSelect?.(chip)}
          className="shrink-0 rounded-full border border-base-300/70 bg-base-100/80 px-4 py-2 text-sm font-semibold text-base-content/75 transition-colors hover:border-primary hover:bg-primary hover:text-primary-content"
        >
          {chip}
        </button>
      ))}
    </div>
  );
}
