import { useEffect, useState } from 'react';
import { CalendarDays, Check, Plus, Search, Sparkles } from 'lucide-react';

import type { MediaShow, SessionSnapshot, StatusValue } from '../types';


interface DiscoverPageProps {
  session: SessionSnapshot;
  busy: boolean;
  initialQuery?: string;
  trackerEpisode?: number;
  onSearch(payload: Record<string, unknown>): Promise<MediaShow[]>;
  onAdd(show: MediaShow, status: StatusValue): Promise<void>;
}


export function DiscoverPage({ session, busy, initialQuery, trackerEpisode, onSearch, onAdd }: DiscoverPageProps) {
  const [method, setMethod] = useState<'keyword' | 'season'>('keyword');
  const [query, setQuery] = useState('');
  const [season, setSeason] = useState('Summer');
  const [year, setYear] = useState(new Date().getFullYear());
  const [status, setStatus] = useState<StatusValue>(session.media.statusOptions[0]?.value ?? '');
  const [results, setResults] = useState<MediaShow[]>([]);
  const [added, setAdded] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (initialQuery) {
      setMethod('keyword');
      setQuery(initialQuery);
    }
  }, [initialQuery]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const payload = method === 'keyword'
      ? { method, query }
      : { method, season, year };
    setResults(await onSearch(payload));
  }

  async function add(show: MediaShow) {
    await onAdd(show, status);
    setAdded((current) => new Set(current).add(String(show.id)));
  }

  return (
    <section className="page discover-page" aria-labelledby="discover-title">
      <header className="page-header discover-heading">
        <div>
          <h1 id="discover-title">Find something worth your time</h1>
          <p className="page-description">Search {session.account.serviceName} and add a title without leaving Trackma.</p>
        </div>
        <Sparkles className="header-art" aria-hidden="true" />
      </header>

      <form className="discover-search" onSubmit={submit}>
        {trackerEpisode !== undefined && <p className="tracker-request" role="status">Tracker request: add the matching title, then set progress to episode {trackerEpisode}.</p>}
        {session.media.searchMethods.length > 1 && (
          <div className="method-switch" aria-label="Search method">
            <button type="button" aria-pressed={method === 'keyword'} onClick={() => setMethod('keyword')}>Keyword</button>
            <button type="button" aria-pressed={method === 'season'} onClick={() => setMethod('season')}>Season</button>
          </div>
        )}
        <div className="discover-fields">
          {method === 'keyword' ? (
            <label className="search-field discover-query">
              <Search aria-hidden="true" />
              <span className="sr-only">Search remote catalog</span>
              <input
                type="search"
                aria-label="Search remote catalog"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Title, alternate title, or keyword"
                required
              />
            </label>
          ) : (
            <div className="season-fields">
              <CalendarDays aria-hidden="true" />
              <label>Season
                <select value={season} onChange={(event) => setSeason(event.target.value)}>
                  {['Winter', 'Spring', 'Summer', 'Fall'].map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label>Year
                <input type="number" min="1900" max={new Date().getFullYear() + 1} value={year} onChange={(event) => setYear(Number(event.target.value))} />
              </label>
            </div>
          )}
          <label className="status-select">Add to
            <select
              value={String(status)}
              onChange={(event) => setStatus(
                session.media.statusOptions.find((item) => String(item.value) === event.target.value)?.value ?? event.target.value,
              )}
            >
              {session.media.statusOptions.map((item) => <option key={String(item.value)} value={String(item.value)}>{item.label}</option>)}
            </select>
          </label>
          <button className="primary-button discover-submit" disabled={busy}>
            <Search aria-hidden="true" /> {busy ? 'Searching' : 'Search'}
          </button>
        </div>
      </form>

      {results.length === 0 ? (
        <div className="discover-empty">
          <span className="orbit-mark" aria-hidden="true"><Search /></span>
          <h2>Search the connected catalog</h2>
          <p>Results will include the service’s current metadata and available cover art.</p>
        </div>
      ) : (
        <div className="discover-results" aria-live="polite">
          {results.map((show) => {
            const isAdded = added.has(String(show.id));
            return (
              <article className="discover-result" key={String(show.id)}>
                {show.image || show.image_thumb ? (
                  <img src={show.image || show.image_thumb} alt={`Cover for ${show.title}`} />
                ) : <div className="result-placeholder">{show.title.slice(0, 2).toUpperCase()}</div>}
                <div>
                  <h2>{show.title}</h2>
                  <p>{show.total || '?'} entries · {show.status || 'Status unavailable'}</p>
                </div>
                <button className={isAdded ? 'secondary-button success' : 'primary-button'} disabled={busy || isAdded} onClick={() => add(show)}>
                  {isAdded ? <Check aria-hidden="true" /> : <Plus aria-hidden="true" />}
                  {isAdded ? 'Added' : 'Add'}
                </button>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
