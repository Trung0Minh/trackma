import { useEffect, useMemo, useState } from 'react';
import {
  ExternalLink,
  Grid2X2,
  List,
  Play,
  RefreshCw,
  ScanSearch,
  Search,
  Send,
} from 'lucide-react';

import type { MediaShow, SessionSnapshot, StatusValue } from '../types';


interface LibraryPageProps {
  session: SessionSnapshot;
  viewMode: 'grid' | 'table';
  onViewModeChange(mode: 'grid' | 'table'): void;
  onSelect(show: MediaShow): void;
  onCommand(command: string, show?: MediaShow): void;
}


function sameStatus(left: StatusValue | 'all', right: StatusValue) {
  return left === 'all' || String(left) === String(right);
}


function progressWidth(show: MediaShow) {
  if (!show.total) return 0;
  return Math.min(100, Math.max(0, (show.my_progress / show.total) * 100));
}


function episodeWidth(value: number, total: number) {
  if (!total) return 0;
  return Math.min(100, Math.max(0, (value / total) * 100));
}

function trackerSummary(tracker: Record<string, unknown> | null) {
  if (!tracker) return 'Not active';
  const state = String(tracker.state ?? '').toLocaleLowerCase();
  const stateNumber = typeof tracker.state === 'number' ? tracker.state : null;
  const timer = typeof tracker.timer === 'number' ? tracker.timer : Number.NaN;
  const show = tracker.show as [MediaShow, number] | null | undefined;
  const showTitle = Array.isArray(show) ? show[0]?.title : undefined;
  const episode = Array.isArray(show) ? show[1] : undefined;

  if (stateNumber === 5 || state.includes('ignored')) return 'Ignored current playback';
  if (stateNumber === 3 || state.includes('unrecognized')) return 'File name not recognized';
  if (stateNumber === 4 || state.includes('not found')) return 'Title not in list';
  if (stateNumber === 1 || state.includes('no video')) return 'No video detected';
  if (stateNumber === 2 || state.includes('playing') || Number.isFinite(timer)) {
    const subject = showTitle && episode ? `${showTitle} ep ${episode}` : 'detected title';
    if (tracker.paused) return `Paused: ${subject}`;
    if (Number.isFinite(timer) && timer > 0) return `Update prompt in ${timer}s`;
    return `Watching ${subject}`;
  }
  return 'Monitoring players';
}


export function LibraryPage({
  session,
  viewMode,
  onViewModeChange,
  onSelect,
  onCommand,
}: LibraryPageProps) {
  const defaultStatus = session.media.statusOptions[0]?.value ?? 'all';
  const [activeStatus, setActiveStatus] = useState<StatusValue | 'all'>(defaultStatus);
  const [query, setQuery] = useState('');

  useEffect(() => setActiveStatus(defaultStatus), [defaultStatus]);
  const statusCounts = useMemo(() => {
    const counts = new Map<string, number>();
    session.library.shows.forEach((show) => {
      const key = String(show.my_status);
      counts.set(key, (counts.get(key) ?? 0) + 1);
    });
    return counts;
  }, [session.library.shows]);
  const filtered = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return session.library.shows.filter((show) => {
      const matchesStatus = sameStatus(activeStatus, show.my_status);
      const alternate = session.library.alternateTitles[String(show.id)] ?? '';
      const matchesQuery =
        !normalized ||
        show.title.toLocaleLowerCase().includes(normalized) ||
        alternate.toLocaleLowerCase().includes(normalized);
      return matchesStatus && matchesQuery;
    });
  }, [activeStatus, query, session.library]);

  return (
    <>
    <section className="page library-page" aria-labelledby="library-title">
      <header className="page-header">
        <div>
          <h1 id="library-title">My library</h1>
          <p className="page-description">
            {session.library.shows.length} titles, {session.library.queueCount} waiting to sync
          </p>
        </div>
      </header>

      <div className="library-pulse" aria-label="Current library state">
        <div>
          <span className="pulse-label">Tracker</span>
          <strong>{trackerSummary(session.library.tracker)}</strong>
        </div>
        <div>
          <span className="pulse-label">Local media</span>
          <strong>
            {session.library.shows.reduce(
              (total, show) => total + (show.availableEpisodes?.length ?? 0),
              0,
            )}{' '}
            episodes indexed
          </strong>
        </div>
        <div>
          <span className="pulse-label">Remote queue</span>
          <strong>{session.library.queueCount || 'No'} pending changes</strong>
        </div>
      </div>

      <div className="library-controls">
        <div className="status-tabs" role="tablist" aria-label="Library status">
          <button
            role="tab"
            aria-selected={activeStatus === 'all'}
            className={activeStatus === 'all' ? 'active' : ''}
            onClick={() => setActiveStatus('all')}
          >
            All <span>{session.library.shows.length}</span>
          </button>
          {session.media.statusOptions.map((status) => (
            <button
              key={String(status.value)}
              role="tab"
              aria-selected={String(activeStatus) === String(status.value)}
              className={String(activeStatus) === String(status.value) ? 'active' : ''}
              onClick={() => setActiveStatus(status.value)}
            >
              {status.label} <span>{statusCounts.get(String(status.value)) ?? 0}</span>
            </button>
          ))}
        </div>
        <div className="control-cluster">
          <label className="search-field">
            <Search aria-hidden="true" />
            <span className="sr-only">Search library</span>
            <input
              type="search"
              aria-label="Search library"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search titles"
            />
          </label>
          <div className="segmented-control" aria-label="Library view">
            <button
              aria-label="Grid view"
              aria-pressed={viewMode === 'grid'}
              onClick={() => onViewModeChange('grid')}
            >
              <Grid2X2 aria-hidden="true" />
            </button>
            <button
              aria-label="Table view"
              aria-pressed={viewMode === 'table'}
              onClick={() => onViewModeChange('table')}
            >
              <List aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state" role="status">
          <Search aria-hidden="true" />
          <h2>No titles match</h2>
          <p>Try another status or search phrase.</p>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="media-grid">
          {filtered.map((show, index) => (
            <article
              className="media-card"
              key={String(show.id)}
              style={{ '--reveal-index': index } as React.CSSProperties}
            >
              <button className="card-hit-area" onClick={() => onSelect(show)}>
                <span className="sr-only">Open {show.title}</span>
              </button>
              <div className="poster-frame">
                {show.image || show.image_thumb ? (
                  <img src={show.image || show.image_thumb} alt={`Cover for ${show.title}`} />
                ) : (
                  <div className="poster-placeholder" aria-hidden="true">
                    {show.title.slice(0, 2).toUpperCase()}
                  </div>
                )}
                {show.queued && <span className="queued-flag">queued</span>}
              </div>
              <div className="card-copy">
                <h2 title={show.title}>{show.title}</h2>
                <p>{show.type || session.api.mediatype} · score {show.my_score || '—'}</p>
                <div className="card-footer">
                  <div className="progress-copy">
                    <span>{show.my_progress} / {show.total || '?'} {session.api.mediatype === 'manga' ? 'CH' : 'EP'}</span>
                    <div
                      className="progress-track"
                      role="img"
                      aria-label={`${show.title} episode progress: ${show.my_progress} watched, ${show.airedEpisodes ?? 0} aired, ${show.availableEpisodes?.length ?? 0} downloaded, ${show.total || 'unknown'} total`}
                      title={`Watched ${show.my_progress} · Aired ${show.airedEpisodes ?? 0} · Downloaded ${show.availableEpisodes?.length ?? 0} · Total ${show.total || '?'}`}
                    >
                      <span className="aired-progress" aria-hidden="true" style={{ width: `${episodeWidth(show.airedEpisodes ?? 0, show.total)}%` }} />
                      <span className="watched-progress" aria-hidden="true" style={{ width: `${progressWidth(show)}%` }} />
                      {show.total > 0 && [...new Set(show.availableEpisodes ?? [])].map((episode) => (
                        episode > 0 && episode <= show.total ? <span
                          aria-hidden="true"
                          className="local-episode-progress"
                          key={episode}
                          style={{
                            left: `${episodeWidth(episode - 1, show.total)}%`,
                            width: `${100 / show.total}%`,
                          }}
                        /> : null
                      ))}
                    </div>
                  </div>
                  {session.account.api === 'anilist' && show.url && (
                    <button
                      className="increment-button"
                      aria-label={`Open ${show.title} on AniList`}
                      title="Open on AniList"
                      onClick={() => onCommand('openExternal', show)}
                    >
                      <ExternalLink aria-hidden="true" />
                    </button>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="table-shell">
          <table>
            <thead>
              <tr><th>Title</th><th>Progress</th><th>Score</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr>
            </thead>
            <tbody>
              {filtered.map((show) => (
                <tr key={String(show.id)} onDoubleClick={() => onSelect(show)}>
                  <td><button className="text-button" onClick={() => onSelect(show)}>{show.title}</button></td>
                  <td>{show.my_progress} / {show.total || '?'}</td>
                  <td>{show.my_score || '—'}</td>
                  <td>{session.media.statusOptions.find((item) => String(item.value) === String(show.my_status))?.label}</td>
                  <td>
                    {session.media.can_play && (
                      <button className="icon-button compact" onClick={() => onCommand('play', show)} aria-label={`Play ${show.title}`}>
                        <Play aria-hidden="true" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
    <div className="floating-library-actions" role="toolbar" aria-label="Library actions">
      <button className="icon-button" onClick={() => onCommand('scan')} title="Scan library">
        <ScanSearch aria-hidden="true" />
        <span className="sr-only">Scan library</span>
      </button>
      <button className="icon-button" onClick={() => onCommand('download')} title="Retrieve list">
        <RefreshCw aria-hidden="true" />
        <span className="sr-only">Retrieve list</span>
      </button>
      <button className="primary-button" aria-label="Sync changes" title="Sync changes" onClick={() => onCommand('upload')}>
        <Send aria-hidden="true" />
      </button>
    </div>
    </>
  );
}
