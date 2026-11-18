import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowRight, ArrowUp, CircleAlert, LocateFixed, MapPin, Plus, RotateCcw,
  Snowflake, Sparkles, Wrench,
} from 'lucide-react';
import { authApi } from '../api/auth';
import { Navbar } from '../components/landing/Navbar';
import { ProfileAvatar } from '../components/ProfileAvatar';
import { SearchProgress } from '../components/search/SearchProgress';
import { useAuth } from '../lib/auth';
import {
  AdvancedSearchRequestError, searchAdvanced, type AdvancedSearchInput,
  type AdvancedSearchResponse, type AdvancedSearchResult, type SearchClarificationOption,
  type SearchProgressStage,
} from '../services/advancedSearchService';
import './AdvancedSearchPage.css';

const examples = [
  { text: 'Quiero un mecánico en Minas', Icon: Wrench },
  { text: '¿Quién instala aire acondicionado en Pando?', Icon: Snowflake },
  { text: 'Busco alguien que haga muebles a medida', Icon: Sparkles },
];

type Outcome =
  | { kind: 'pending'; stage?: SearchProgressStage }
  | { kind: 'result'; response: AdvancedSearchResponse }
  | { kind: 'error'; message: string; status?: number };

type ChatTurn = {
  id: number;
  input: AdvancedSearchInput;
  message: string;
  outcome: Outcome;
};

type TurnRequest = Pick<ChatTurn, 'input' | 'message'>;

function placeLabel(locality?: string | null, department?: string | null) {
  return locality && department && locality !== department ? `${locality}, ${department}` : locality || department || '';
}

function words(text: string) {
  return [...text.matchAll(/[\p{L}\p{M}\p{N}]+/gu)];
}

function normalize(word: string) {
  return word.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

function replacePhrase(text: string, phrase: string, replacement = '') {
  const source = words(text);
  const target = words(phrase).map(([word]) => normalize(word));
  if (!target.length) return text;

  let result = '';
  let cursor = 0;
  for (let i = 0; i <= source.length - target.length; i += 1) {
    if (!target.every((word, offset) => normalize(source[i + offset][0]) === word)) continue;
    const start = source[i].index;
    const end = source[i + target.length - 1];
    result += text.slice(cursor, start) + replacement;
    cursor = end.index + end[0].length;
    i += target.length - 1;
  }
  return result + text.slice(cursor);
}

function ResultCard({ result, suggestionReason }: { result: AdvancedSearchResult; suggestionReason?: string }) {
  const { profile, evidence, locationLabel } = result;
  const name = profile.displayName || profile.name;
  const matchLabel = suggestionReason !== undefined
    ? 'Sugerencia relacionada'
    : evidence.matchType === 'direct' ? 'Coincidencia directa' : 'Experiencia relacionada';

  return (
    <article className="flex min-w-0 flex-col rounded-2xl border border-base-300 bg-base-100 p-4">
      <div className="flex items-center gap-3">
        <ProfileAvatar src={profile.photoUrl} fallbackSrc={profile.avatarFallback} name={name} size={38} />
        <div className="min-w-0">
          <h3 className="break-words text-sm font-extrabold">{name}</h3>
          <p className="break-words text-xs text-base-content/70">{profile.profession}</p>
        </div>
      </div>
      <p className="mt-3 flex items-start gap-1.5 text-xs font-semibold text-secondary">
        <MapPin aria-hidden="true" size={14} className="mt-px shrink-0" /> {locationLabel}
      </p>
      <blockquote className="my-3 line-clamp-4 border-l-2 border-primary/45 pl-3 text-sm leading-relaxed text-base-content/80">
        “{evidence.text}”
      </blockquote>
      {suggestionReason && (
        <p className="mb-3 text-xs leading-relaxed text-base-content/75">{suggestionReason}</p>
      )}
      <div className="mt-auto flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="text-base-content/65">{matchLabel}{profile.isFictionalDemo ? ' · Perfil ficticio' : ''}</span>
        <Link to={`/perfil/${profile.slug}`} aria-label={`Ver perfil de ${name}`} className="inline-flex items-center gap-1 font-extrabold text-secondary hover:underline">
          Ver perfil <ArrowRight aria-hidden="true" size={14} />
        </Link>
      </div>
    </article>
  );
}

function SearchReply({
  response, disabled, onClarify, onBroaden, onEdit,
}: {
  response: AdvancedSearchResponse;
  disabled: boolean;
  onClarify: (option: SearchClarificationOption) => void;
  onBroaden?: () => void;
  onEdit: () => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const filters = response.applied_filters;
  const area = placeLabel(filters?.locality, filters?.department) || (filters?.locationSource === 'national' ? 'Todo Uruguay' : '');
  const count = response.results.length;
  const suggestions = response.suggestions ?? [];
  const showingFallback = suggestions.length > 0 && !response.results.some((result) => result.evidence.matchType === 'direct');
  const needsClarification = response.status === 'ambiguous';
  const options = response.clarification?.options ?? [];
  let title = response.message;
  if (showingFallback) {
    title = 'No encontré una coincidencia exacta. Estos perfiles podrían ayudarte.';
  } else if (count) {
    title = `Encontré ${count} ${count === 1 ? 'perfil' : 'perfiles'}`;
  } else if (['ok', 'empty', 'degraded'].includes(response.status)) {
    title = 'No encontré coincidencias suficientes';
  }

  const resultCards = count > 0 && (
    <div className="grid gap-2.5 sm:grid-cols-2">
      {(showAll ? response.results : response.results.slice(0, 4)).map((result) => (
        <ResultCard key={result.profile.id} result={result} />
      ))}
    </div>
  );

  return (
    <div className="min-w-0 flex-1 space-y-3">
      <div className="w-fit max-w-full rounded-2xl rounded-tl-md border border-base-300 bg-base-100 px-4 py-3 text-sm sm:px-5">
        <p className="font-bold" role="status">{title}</p>
        {needsClarification && !options.length && (
          <button type="button" className="btn btn-ghost btn-xs mt-2 px-0 font-bold text-secondary" onClick={onEdit} disabled={disabled}>
            Editar mensaje
          </button>
        )}
        {area && (
          <div className="mt-2.5 flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/12 px-2.5 py-1 text-xs font-extrabold text-secondary">
              <MapPin aria-hidden="true" size={14} /> {area}
            </span>
            <span className="text-xs text-base-content/70">
              {filters?.locationSource === 'query' ? 'Ubicación detectada en tu mensaje' : 'Zona de búsqueda'}
            </span>
          </div>
        )}
        {response.degradation?.length ? (
          <div className="mt-3 flex items-start gap-2 border-t border-base-300 pt-2.5 text-xs leading-relaxed text-base-content/75">
            <CircleAlert aria-hidden="true" size={15} className="shrink-0 text-error" />
            <span>{response.degradation.join(' ')}</span>
          </div>
        ) : null}
      </div>

      {!showingFallback && resultCards}
      {suggestions.length > 0 && (
        <section className="space-y-2" aria-label="Sugerencias relacionadas">
          {!showingFallback && <h2 className="text-sm font-bold">Sugerencias relacionadas</h2>}
          <div className="grid gap-2.5 sm:grid-cols-2">
            {suggestions.map((suggestion) => (
              <ResultCard key={suggestion.profile.id} result={suggestion} suggestionReason={suggestion.reason} />
            ))}
          </div>
        </section>
      )}
      {showingFallback && resultCards}
      {(options.length > 0 || onBroaden || count > 4) && (
        <div className="flex flex-wrap gap-2">
          {options.map((option) => (
            <button type="button" key={`${option.kind}-${option.id ?? option.name}`} className="btn btn-outline btn-sm h-auto min-h-8 rounded-full whitespace-normal text-left" onClick={() => onClarify(option)} disabled={disabled}>
              {option.kind === 'profession' ? option.name : placeLabel(option.kind === 'locality' ? option.name : undefined, option.kind === 'department' ? option.name : option.department)}
            </button>
          ))}
          {count > 4 && (
            <button type="button" className="btn btn-outline btn-sm rounded-full" onClick={() => setShowAll(!showAll)} aria-expanded={showAll}>
              {showAll ? 'Ver menos' : `Ver ${count - 4} perfiles más`}
            </button>
          )}
          {onBroaden && (
            <button type="button" className="btn btn-ghost btn-sm gap-1.5 rounded-full font-bold text-secondary" onClick={onBroaden} disabled={disabled}>
              <LocateFixed aria-hidden="true" size={15} /> Buscar en todo Uruguay
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export function AdvancedSearchPage() {
  const { user, loading } = useAuth();
  return (
    <div className="flex min-h-dvh flex-col bg-base-100">
      <Navbar />
      <SearchChat key={user?.id ?? 'guest'} isAuthenticated={Boolean(user)} authLoading={loading} />
    </div>
  );
}

function SearchChat({ isAuthenticated, authLoading }: { isAuthenticated: boolean; authLoading: boolean }) {
  const [draft, setDraft] = useState('');
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const activeRequest = useRef<AbortController | null>(null);
  const nextId = useRef(0);
  const thread = useRef<HTMLDivElement>(null);
  const latestTurn = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const authConfig = useQuery({ queryKey: ['auth-config'], queryFn: authApi.config, staleTime: 60_000 });
  const ready = isAuthenticated && !authLoading && !authConfig.isPending && authConfig.data?.aiSearchEnabled !== false;
  const lastTurn = turns.at(-1);
  const latestOutcome = lastTurn?.outcome;
  const pending = latestOutcome?.kind === 'pending';
  const hasProgress = latestOutcome?.kind === 'pending' && Boolean(latestOutcome.stage);

  useEffect(() => () => activeRequest.current?.abort(), []);

  useEffect(() => {
    const container = thread.current;
    const row = latestTurn.current;
    if (container && row) {
      const top = row.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop;
      container.scrollTo({ top: Math.max(0, top - 16), behavior: 'instant' });
    }
  }, [lastTurn?.id, latestOutcome?.kind, hasProgress]);

  const updateTurn = (id: number, outcome: Outcome) => {
    setTurns((current) => current.map((turn) => turn.id === id ? { ...turn, outcome } : turn));
  };

  async function run(request: TurnRequest, retryId?: number) {
    if (!ready || activeRequest.current || request.input.query.trim().length < 2) return;
    const controller = new AbortController();
    activeRequest.current = controller;
    const id = retryId ?? ++nextId.current;
    const outcome: Outcome = { kind: 'pending' };
    if (retryId === undefined) setTurns((current) => [...current, { id, ...request, outcome }]);
    else updateTurn(id, outcome);

    try {
      const response = await searchAdvanced(request.input, controller.signal, (stage) => {
        if (!controller.signal.aborted) updateTurn(id, { kind: 'pending', stage });
      });
      if (!controller.signal.aborted) updateTurn(id, { kind: 'result', response });
    } catch (error) {
      if (controller.signal.aborted) return;
      const serverError = error instanceof AdvancedSearchRequestError;
      updateTurn(id, {
        kind: 'error',
        message: serverError ? error.message : 'La búsqueda se interrumpió. Probá de nuevo.',
        status: serverError ? error.status : undefined,
      });
    } finally {
      if (activeRequest.current === controller) activeRequest.current = null;
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = draft.trim();
    if (!ready || activeRequest.current || query.length < 2) return;
    setDraft('');
    void run({ input: { query }, message: query });
  }

  function edit(query: string) {
    setDraft(query.slice(0, 500));
    composer.current?.focus();
  }

  function clarify(turn: ChatTurn, response: AdvancedSearchResponse, option: SearchClarificationOption) {
    const query = turn.input.query;
    if (option.kind === 'profession') {
      const requested = response.clarification?.requestedText;
      const corrected = requested ? replacePhrase(query, requested, option.name) : query;
      if (corrected === query || corrected.length > 500) edit(corrected === query ? `${option.name} ${query}` : corrected);
      else void run({ input: { ...turn.input, query: corrected }, message: corrected });
    } else {
      const area = placeLabel(option.kind === 'locality' ? option.name : undefined, option.kind === 'department' ? option.name : option.department);
      void run({
        input: { query, departmentId: option.departmentId || undefined, localityId: option.localityId || undefined },
        message: `Buscar en ${area}`,
      });
    }
  }

  function reset() {
    activeRequest.current?.abort();
    activeRequest.current = null;
    setTurns([]);
    setDraft('');
    composer.current?.focus();
  }

  return (
    <main className="search-chat flex flex-1 flex-col items-center px-2.5 py-3 sm:px-6 sm:py-6">
      <section className="search-chat__frame flex w-full max-w-5xl flex-col overflow-hidden rounded-[1.35rem] border border-base-300 bg-base-100 shadow-soft sm:rounded-3xl" aria-label="Asistente de búsqueda avanzada">
        <header className="flex shrink-0 items-center gap-3 border-b border-base-300/80 px-4 py-3 sm:px-6">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary/15 text-secondary">
            <Sparkles aria-hidden="true" size={20} />
          </span>
          <div className="min-w-0 flex-1">
            <h1 className="text-base font-extrabold tracking-tight sm:text-lg">Asistente de búsqueda</h1>
            <p className="text-xs text-base-content/65">Encontrá servicios en Uruguay</p>
          </div>
          {ready && (turns.length > 0 || draft) && (
            <button type="button" className="btn btn-ghost btn-sm gap-1.5 rounded-full px-2.5" aria-label="Nuevo chat" onClick={reset}>
              <Plus aria-hidden="true" size={17} /><span className="hidden sm:inline">Nuevo chat</span>
            </button>
          )}
        </header>

        <div ref={thread} className="search-chat__thread min-h-0 flex-1 overflow-y-auto overscroll-contain" role="region" aria-label="Conversación" tabIndex={0}>
          {!ready ? (
            <div className="grid min-h-full place-items-center px-5 py-8 text-center">
              <div>
                {authLoading || (isAuthenticated && authConfig.isPending) ? (
                  <p role="status" className="text-sm text-base-content/75">Preparando el asistente…</p>
                ) : (
                  <>
                    <h2 className="text-xl font-extrabold">{isAuthenticated ? 'Búsqueda avanzada desactivada' : 'Ingresá para usar el asistente'}</h2>
                    <div className="mt-4 flex flex-wrap justify-center gap-2">
                      {!isAuthenticated && <Link to="/login?next=%2Fbuscar%2Favanzada" className="btn btn-primary btn-sm rounded-full">Ingresar</Link>}
                      <Link to="/buscar" className="btn btn-outline btn-sm rounded-full">Búsqueda común</Link>
                    </div>
                  </>
                )}
              </div>
            </div>
          ) : turns.length === 0 ? (
            <div className="search-chat__welcome flex min-h-full flex-col items-center justify-center px-4 py-6 text-center sm:px-8 sm:py-12">
              <span className="search-chat__mark grid size-16 place-items-center rounded-[1.35rem] border border-primary/25 bg-primary/12 text-secondary">
                <Sparkles aria-hidden="true" size={32} strokeWidth={1.7} />
              </span>
              <h2 className="mt-5 text-3xl font-extrabold tracking-tight sm:text-4xl">¿Qué servicio necesitás?</h2>
              <p className="mt-3 max-w-md text-sm leading-relaxed text-base-content/75 sm:text-base">
                Contame qué buscás y dónde. Voy a usar la ubicación de tu mensaje para filtrar los perfiles.
              </p>
              <div className="mt-5 flex max-w-2xl flex-wrap justify-center gap-2 sm:mt-7">
                {examples.map(({ text, Icon }) => (
                  <button key={text} type="button" onClick={() => edit(text)} className="inline-flex items-center gap-2 rounded-xl border border-base-300 bg-base-100 px-3 py-2 text-left text-xs font-bold transition-colors hover:border-primary/55 hover:bg-primary/8 sm:text-sm">
                    <Icon aria-hidden="true" size={15} className="shrink-0 text-secondary" /> {text}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-4xl space-y-7 px-3 py-5 sm:px-8 sm:py-7">
              {turns.map((turn) => {
                const isLast = turn.id === lastTurn?.id;
                const outcome = turn.outcome;
                const response = outcome.kind === 'result' ? outcome.response : undefined;
                const filters = response?.applied_filters;
                const canBroaden = isLast && Boolean(filters?.locality || filters?.department) && response?.status !== 'ambiguous';
                return (
                  <div key={turn.id} ref={isLast ? latestTurn : undefined} className="search-chat__turn space-y-4">
                    <div className="flex justify-end">
                      <p className="max-w-[87%] whitespace-pre-wrap break-words rounded-2xl rounded-tr-md border border-primary/20 bg-primary/13 px-4 py-2.5 text-sm font-semibold sm:max-w-[76%]">
                        <span className="sr-only">Tu mensaje: </span>{turn.message}
                      </p>
                    </div>
                    <div className="flex items-start gap-2.5 sm:gap-3">
                      <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg border border-primary/20 bg-primary/10 text-secondary sm:size-9">
                        <Sparkles aria-hidden="true" size={17} />
                      </span>
                      {outcome.kind === 'pending' && (outcome.stage
                        ? <SearchProgress stage={outcome.stage} />
                        : <p role="status" className="rounded-2xl rounded-tl-md border border-base-300 bg-base-100 px-4 py-2.5 text-sm text-base-content/75">Enviando tu mensaje…</p>)}
                      {outcome.kind === 'error' && (
                        <div className="rounded-2xl rounded-tl-md border border-base-300 bg-base-100 px-4 py-3 text-sm" role="alert">
                          <p>{outcome.message}</p>
                          {outcome.status === 401 ? (
                            <Link to="/login?next=%2Fbuscar%2Favanzada" className="btn btn-ghost btn-sm mt-1 px-0 text-secondary">Ingresar</Link>
                          ) : isLast && (
                            <button type="button" className="btn btn-ghost btn-sm mt-1 gap-1.5 px-0 text-secondary" onClick={() => void run(turn, turn.id)}>
                              <RotateCcw aria-hidden="true" size={14} /> Reintentar
                            </button>
                          )}
                        </div>
                      )}
                      {response && (
                        <SearchReply
                          response={response}
                          disabled={pending}
                          onClarify={(option) => clarify(turn, response, option)}
                          onEdit={() => edit(turn.input.query)}
                          onBroaden={canBroaden ? () => void run({ input: { query: turn.input.query, locationScope: 'national' }, message: 'Buscar en todo Uruguay' }) : undefined}
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {ready && (
          <form onSubmit={submit} className="shrink-0 border-t border-base-300/80 bg-base-100 px-3 py-3 sm:px-6 sm:py-4">
            <div className="mx-auto flex max-w-4xl items-end gap-2 rounded-2xl border border-base-300 bg-base-200/45 p-1.5 transition-colors focus-within:border-primary/65">
              <label htmlFor="chat-query" className="sr-only">Tu mensaje</label>
              <textarea
                ref={composer}
                id="chat-query"
                rows={1}
                value={draft}
                maxLength={500}
                placeholder="Escribí qué servicio necesitás…"
                className="search-chat__input min-w-0 flex-1 resize-none rounded-xl bg-transparent px-3 py-2.5 text-base leading-6 placeholder:text-base-content/55 focus-visible:outline-none"
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                aria-describedby="chat-input-help"
              />
              <button type="submit" className="grid size-11 shrink-0 place-items-center rounded-xl bg-primary text-primary-content transition-opacity hover:opacity-85 disabled:cursor-not-allowed disabled:opacity-40" aria-label="Enviar mensaje" disabled={pending || draft.trim().length < 2}>
                <ArrowUp aria-hidden="true" size={22} strokeWidth={2.5} />
              </button>
            </div>
            <p id="chat-input-help" className="mx-auto mt-1.5 max-w-4xl text-center text-xs text-base-content/60">
              {draft.length === 500 ? 'Llegaste al límite de 500 caracteres.' : <><span className="hidden sm:inline">Enter para enviar · Mayús + Enter para una nueva línea</span><span className="sm:hidden">Buscá por oficio, servicio o localidad</span></>}
            </p>
          </form>
        )}
      </section>
    </main>
  );
}
