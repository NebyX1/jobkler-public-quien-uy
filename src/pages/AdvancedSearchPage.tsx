import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertTriangle, ArrowRight, LoaderCircle, Search, Sparkles } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Navbar } from '../components/landing/Navbar';
import { Footer } from '../components/landing/Footer';
import { ProfileCard } from '../components/landing/ProfileCard';
import { authApi } from '../api/auth';
import { useAuth } from '../lib/auth';
import { getCatalog } from '../services/locationService';
import { searchAdvanced, type AdvancedSearchResponse, type SearchClarificationOption } from '../services/advancedSearchService';

const EXAMPLES = [
  '¿Hay alguien que arregle termofones en Minas?',
  'Necesito reparar una puerta de madera',
  'Busco alguien que coloque muebles a medida en Lavalleja',
];

function removeLocationFromQuery(query: string, values: Array<string | null | undefined>) {
  let result = query;
  for (const value of values.filter((item): item is string => Boolean(item))) {
    const escaped = value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    result = result.replace(new RegExp(`\\b${escaped}\\b`, 'gi'), ' ');
  }
  return result
    .replace(/\b(?:en|dentro de|de)\s*(?=[,.;!?]|$)/gi, ' ')
    .replace(/\s+/g, ' ')
    .replace(/\s+([,.;!?])/g, '$1')
    .trim();
}

function sourceFieldLabel(value: string) {
  const labels: Record<string, string> = {
    profession: 'Oficio',
    category: 'Categoría',
    short_description: 'Descripción breve',
    description: 'Descripción del perfil',
    tags: 'Etiquetas del perfil',
  };
  return labels[value] || 'Perfil';
}

export function AdvancedSearchPage() {
  const navigate = useNavigate();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [query, setQuery] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [localityId, setLocalityId] = useState('');
  const [response, setResponse] = useState<AdvancedSearchResponse | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const sequence = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const authConfig = useQuery({ queryKey: ['auth-config'], queryFn: authApi.config, staleTime: 60_000 });
  const catalog = useQuery({ queryKey: ['jobkler-catalog'], queryFn: getCatalog, staleTime: 5 * 60_000 });

  useEffect(() => () => {
    sequence.current += 1;
    controller.current?.abort();
  }, []);

  const departments = catalog.data?.departments || [];
  const localities = catalog.data?.localities.filter((item) => !departmentId || item.departmentId === departmentId) || [];

  const runSearch = async (nextQuery = query, nextDepartment = departmentId, nextLocality = localityId) => {
    if (!isAuthenticated) {
      navigate(`/login?next=${encodeURIComponent('/buscar/avanzada')}`);
      return;
    }
    const cleanQuery = nextQuery.trim();
    if (cleanQuery.length < 2) {
      setError('Escribí al menos dos caracteres para buscar.');
      return;
    }
    if (cleanQuery.length > 500) {
      setError('La búsqueda puede tener hasta 500 caracteres.');
      return;
    }

    const requestSequence = ++sequence.current;
    controller.current?.abort();
    const nextController = new AbortController();
    controller.current = nextController;
    setQuery(nextQuery);
    setBusy(true);
    setError('');
    setResponse(null);
    try {
      const result = await searchAdvanced({
        query: cleanQuery,
        departmentId: nextDepartment || undefined,
        localityId: nextLocality || undefined,
        limit: 10,
      }, nextController.signal);
      if (sequence.current === requestSequence) setResponse(result);
    } catch (reason) {
      if (sequence.current !== requestSequence || (axios.isAxiosError(reason) && reason.code === 'ERR_CANCELED')) return;
      const data = axios.isAxiosError(reason) ? reason.response?.data : undefined;
      const message = axios.isAxiosError(reason)
        ? (typeof data?.error === 'string' ? data.error
          : typeof data?.error?.message === 'string' ? data.error.message
          : typeof data?.message === 'string' ? data.message : reason.message)
        : reason instanceof Error ? reason.message : 'No se pudo completar la búsqueda.';
      setError(message || 'No se pudo completar la búsqueda. Probá otra vez.');
    } finally {
      if (sequence.current === requestSequence) setBusy(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void runSearch();
  };

  const handleClarification = (option: SearchClarificationOption) => {
    if (option.kind === 'locality' && option.localityId) {
      setDepartmentId(option.departmentId || '');
      setLocalityId(option.localityId);
    } else if (option.kind === 'department' && option.departmentId) {
      setDepartmentId(option.departmentId);
      setLocalityId('');
    } else if (option.kind === 'profession') {
      const requested = response?.clarification?.requestedText;
      const next = requested
        ? query.replace(new RegExp(`\\b${requested.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i'), option.name)
        : `${option.name} ${query}`.trim();
      setQuery(next);
    }
    setResponse(null);
  };

  const broadenSearch = () => {
    const selectedDepartment = departments.find((item) => item.id === departmentId)?.name;
    const selectedLocality = catalog.data?.localities.find((item) => item.id === localityId)?.name;
    const queryWithoutPlace = removeLocationFromQuery(query, [selectedLocality, selectedDepartment]);
    if (localityId) {
      const nextQuery = queryWithoutPlace || query;
      setLocalityId('');
      void runSearch(nextQuery, departmentId, '');
      return;
    }
    if (departmentId) {
      setDepartmentId('');
      setLocalityId('');
      void runSearch(queryWithoutPlace || query, '', '');
      return;
    }
    const resultDepartment = response?.applied_filters?.department;
    const resultLocality = response?.applied_filters?.locality;
    const nextQuery = removeLocationFromQuery(query, [resultLocality, resultDepartment]);
    if (nextQuery && nextQuery !== query) void runSearch(nextQuery, '', '');
  };

  const hasLocationScope = Boolean(departmentId || localityId || response?.applied_filters?.department || response?.applied_filters?.locality);
  const canBroaden = Boolean(response && response.results.length === 0 && hasLocationScope);

  return (
    <div className="flex min-h-screen flex-col bg-base-100">
      <Navbar />
      <main className="flex-1">
        <section className="border-b border-base-300/60 bg-base-200/40 py-10 sm:py-14">
          <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
            <div className="rounded-[2.25rem] border border-base-300/70 bg-base-100/95 p-6 shadow-sm sm:p-9">
              <div className="flex items-start gap-4">
                <span className="mt-1 flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <Sparkles className="h-6 w-6" aria-hidden="true" />
                </span>
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-primary">Jobkler · búsqueda local</p>
                  <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-base-content sm:text-4xl">Búsqueda Avanzada</h1>
                  <p className="mt-3 max-w-3xl text-base leading-relaxed text-base-content/70">
                    Contá qué necesitás con tus palabras. Buscamos en los perfiles publicados y mostramos el fragmento que respalda cada coincidencia.
                  </p>
                </div>
              </div>

              {!authLoading && !isAuthenticated ? (
                <div className="mt-7 rounded-2xl border border-warning/30 bg-warning/10 p-5" role="status">
                  <h2 className="font-bold text-base-content">Iniciá sesión para buscar</h2>
                  <p className="mt-1 text-sm text-base-content/70">La búsqueda avanzada está disponible para cuentas autenticadas. El buscador común sigue abierto.</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Link to={`/login?next=${encodeURIComponent('/buscar/avanzada')}`} className="btn btn-primary btn-sm rounded-full">Ingresar</Link>
                    <Link to="/buscar" className="btn btn-outline btn-sm rounded-full">Usar búsqueda común</Link>
                  </div>
                </div>
              ) : authLoading ? (
                <p className="mt-7 text-sm text-base-content/60" role="status">Comprobando la sesión…</p>
              ) : authConfig.isLoading ? (
                <p className="mt-7 text-sm text-base-content/60" role="status">Comprobando la disponibilidad…</p>
              ) : authConfig.data?.aiSearchEnabled === false ? (
                <div className="mt-7 rounded-2xl border border-warning/30 bg-warning/10 p-5" role="status">
                  <p className="font-semibold text-base-content">La búsqueda avanzada está apagada en esta configuración.</p>
                  <Link to="/buscar" className="btn btn-outline btn-sm mt-4 rounded-full">Ir a búsqueda común</Link>
                </div>
              ) : (
                <>
                  <form className="mt-7 space-y-4" onSubmit={handleSubmit}>
                    <div>
                      <label htmlFor="advanced-query" className="mb-2 block text-sm font-semibold text-base-content">¿Qué servicio necesitás?</label>
                      <textarea
                        id="advanced-query"
                        value={query}
                        onChange={(event) => setQuery(event.target.value)}
                        maxLength={500}
                        rows={3}
                        placeholder="Ej.: ¿Hay alguien que arregle termofones en Minas?"
                        className="w-full resize-y rounded-2xl border border-base-300 bg-base-100 px-4 py-3 text-base text-base-content placeholder:text-base-content/40 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
                        aria-describedby="advanced-query-help"
                      />
                      <div className="mt-1 flex justify-between gap-4 text-xs text-base-content/55">
                        <span id="advanced-query-help">Cada envío es independiente; no se guarda una conversación.</span>
                        <span>{query.length}/500</span>
                      </div>
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <div>
                        <label htmlFor="advanced-department" className="mb-2 block text-sm font-semibold text-base-content">Departamento (opcional)</label>
                        <select
                          id="advanced-department"
                          value={departmentId}
                          onChange={(event) => { setDepartmentId(event.target.value); setLocalityId(''); }}
                          className="h-12 w-full rounded-xl border border-base-300 bg-base-100 px-3 text-base-content focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
                        >
                          <option value="">Todo Uruguay</option>
                          {departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                        </select>
                      </div>
                      <div>
                        <label htmlFor="advanced-locality" className="mb-2 block text-sm font-semibold text-base-content">Localidad (opcional)</label>
                        <select
                          id="advanced-locality"
                          value={localityId}
                          disabled={!departmentId}
                          onChange={(event) => setLocalityId(event.target.value)}
                          className="h-12 w-full rounded-xl border border-base-300 bg-base-100 px-3 text-base-content focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-55"
                        >
                          <option value="">Todas las localidades</option>
                          {localities.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                        </select>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                      <button type="submit" disabled={busy || !query.trim()} className="btn btn-primary rounded-full px-7">
                  {busy ? <LoaderCircle className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" /> : <Search className="h-4 w-4" aria-hidden="true" />}
                        {busy ? 'Buscando…' : 'Buscar'}
                      </button>
                      <span className="text-xs text-base-content/50">Hasta 10 resultados · texto y significado · sin ubicaciones por defecto</span>
                    </div>
                  </form>

                  {!response && !busy && !error ? (
                    <div className="mt-6">
                      <p className="text-xs font-semibold uppercase tracking-wide text-base-content/50">Podés probar</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {EXAMPLES.map((example) => (
                          <button key={example} type="button" onClick={() => setQuery(example)} className="rounded-full border border-base-300 bg-base-200/60 px-3 py-2 text-left text-sm text-base-content/75 transition hover:border-primary/40 hover:text-primary">
                            {example}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </>
              )}
            </div>
          </div>
        </section>

        {isAuthenticated ? (
          <section className="py-9 sm:py-12" aria-live="polite">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              {busy ? (
                <div className="flex items-center gap-3 rounded-2xl border border-base-300 bg-base-100 p-5 text-base-content/70" role="status">
                  <LoaderCircle className="h-5 w-5 animate-spin motion-reduce:animate-none text-primary" aria-hidden="true" />
                  <span>Buscando perfiles publicados…</span>
                </div>
              ) : error ? (
                <div className="rounded-2xl border border-error/25 bg-error/10 p-5" role="alert">
                  <div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-error" aria-hidden="true" /><div><h2 className="font-bold text-base-content">No se pudo completar la búsqueda</h2><p className="mt-1 text-sm text-base-content/75">{error}</p></div></div>
                  <button onClick={() => void runSearch()} className="btn btn-outline btn-sm mt-4 rounded-full" type="button">Reintentar</button>
                </div>
              ) : response ? (
                <div>
                  {response.status === 'degraded' ? (
                    <div className="mb-5 rounded-2xl border border-warning/30 bg-warning/10 p-4 text-sm text-base-content" role="status">
                      <p className="font-semibold">Búsqueda reducida</p>
                      {(response.degradation || []).map((item) => <p key={item} className="mt-1 text-base-content/75">{item}</p>)}
                    </div>
                  ) : null}

                  {response.status === 'ambiguous' ? (
                    <div className="rounded-2xl border border-warning/30 bg-warning/10 p-5" role="status">
                      <h2 className="font-bold text-base-content">Necesitamos una aclaración</h2>
                      <p className="mt-1 text-sm text-base-content/75">{response.message}</p>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {response.clarification?.options?.map((option) => (
                          <button key={`${option.kind}-${option.id || option.name}`} type="button" onClick={() => handleClarification(option)} className="btn btn-outline btn-sm rounded-full">
                            Usar {option.name}{option.department ? ` · ${option.department}` : ''}
                          </button>
                        ))}
                      </div>
                      {response.clarification?.options?.length ? <p className="mt-3 text-xs text-base-content/60">La opción solo cambia los filtros; volvé a presionar Buscar para enviar una búsqueda nueva.</p> : null}
                    </div>
                  ) : response.status === 'unsupported' ? (
                    <div className="rounded-2xl border border-base-300 bg-base-100 p-5" role="status"><h2 className="font-bold text-base-content">Escribí un servicio para buscar</h2><p className="mt-1 text-sm text-base-content/70">{response.message}</p></div>
                  ) : response.results.length ? (
                    <>
                      <div className="mb-6">
                        <p className="text-sm font-semibold uppercase tracking-[0.14em] text-primary">Resultados</p>
                        <h2 className="mt-2 text-2xl font-extrabold text-base-content">Sobre tu búsqueda, esto fue lo que pude encontrar</h2>
                        <p className="mt-2 text-sm text-base-content/65">{response.results.length} perfiles con evidencia en el contenido publicado.</p>
                      </div>
                      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
                        {response.results.map((item) => (
                          <div key={item.profile.id} className="flex flex-col gap-3">
                            <ProfileCard profile={item.profile} compact />
                            <article className="rounded-2xl border border-base-300/70 bg-base-200/50 p-4">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <span className={`badge rounded-full border-0 ${item.evidence.matchType === 'direct' ? 'bg-success/15 text-success' : 'bg-info/15 text-info'}`}>
                                  {item.evidence.matchType === 'direct' ? 'Coincidencia directa' : 'Experiencia relacionada'}
                                </span>
                                <span className="text-xs text-base-content/55">{sourceFieldLabel(item.evidence.sourceField)}</span>
                              </div>
                              <blockquote className="mt-3 border-l-2 border-primary/40 pl-3 text-sm leading-relaxed text-base-content/80">“{item.evidence.text}”</blockquote>
                              <p className="mt-3 text-xs font-semibold text-base-content/60">{item.locationLabel}</p>
                              {item.evidence.matchType === 'related' ? <p className="mt-2 text-xs text-base-content/55">Este fragmento está relacionado con la consulta; no confirma por sí solo el servicio exacto.</p> : null}
                              {item.profile.isFictionalDemo ? <p className="mt-2 text-xs font-semibold text-warning">Perfil ficticio de evaluación local.</p> : null}
                              <Link to={`/perfil/${item.profile.slug}`} className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline">Ver perfil completo <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" /></Link>
                            </article>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="rounded-2xl border border-base-300/70 bg-base-100 p-6" role="status">
                      <h2 className="text-xl font-bold text-base-content">No encontramos coincidencias suficientes</h2>
                      <p className="mt-2 text-sm text-base-content/70">{response.message}</p>
                      {canBroaden ? <button type="button" onClick={broadenSearch} className="btn btn-outline btn-sm mt-4 rounded-full">{localityId ? 'Ampliar al departamento' : 'Buscar sin filtro geográfico'}</button> : null}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </section>
        ) : null}
      </main>
      <Footer />
    </div>
  );
}
