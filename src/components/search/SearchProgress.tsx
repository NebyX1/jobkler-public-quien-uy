import { Check, MapPin, MessageSquareText, Search } from 'lucide-react';
import type { SearchProgressStage } from '../../services/advancedSearchService';
import './SearchProgress.css';

export type { SearchProgressStage } from '../../services/advancedSearchService';

const stages = [
  { id: 'interpretation', label: 'Entender lo que necesitás', active: 'Interpretando tu consulta', Icon: MessageSquareText },
  { id: 'location', label: 'Definir la zona de búsqueda', active: 'Comprobando la ubicación', Icon: MapPin },
  { id: 'retrieval', label: 'Encontrar perfiles', active: 'Buscando perfiles que coincidan', Icon: Search },
] as const;

type SearchProgressProps = { stage: SearchProgressStage };

export function SearchProgress({ stage }: SearchProgressProps) {
  const currentIndex = stages.findIndex(({ id }) => id === stage);

  return (
    <section className="search-progress" aria-label="Progreso de la búsqueda">
      <div role="status" aria-atomic="true" className="sr-only">
        {stages[currentIndex]?.active}
      </div>

      <div className="search-progress__heading">
        <p>Búsqueda en curso</p>
        <span className="search-progress__dots" aria-hidden="true"><i /><i /><i /></span>
      </div>

      <ol className="search-progress__steps">
        {stages.map(({ id, label, active, Icon }, index) => {
          const state = index === currentIndex ? 'active' : index < currentIndex ? 'complete' : 'pending';

          return (
            <li key={id} data-state={state} aria-current={state === 'active' ? 'step' : undefined}>
              <span className="search-progress__icon" aria-hidden="true">
                {state === 'complete' ? <Check size={15} /> : <Icon size={15} />}
              </span>
              <span>
                {state === 'active' ? active : label}
                {state === 'complete' && <span className="sr-only"> (completado)</span>}
                {state === 'pending' && <span className="sr-only"> (pendiente)</span>}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
