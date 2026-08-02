import { useCallback, useEffect, useMemo, useState } from 'react';
import DOMPurify from 'dompurify';
import { ChevronLeft, ChevronRight, Download, Info, Search, X } from 'lucide-react';
import { marked } from 'marked';

import type { AppBridge } from '../bridge';


export interface TorrentResult {
  id: string;
  title: string;
  link: string;
  size: string;
  seeders: string;
  leechers: string;
  completed?: string;
  published?: string;
}

interface TorrentSearchPage {
  results: TorrentResult[];
  hasNext: boolean;
}

interface TorrentDialogProps {
  bridge: AppBridge;
  title: string;
  onClose(): void;
  onDownloaded(): Promise<void>;
  onMessage(message: string): void;
}


const categories = [
  ['1_0', 'All Anime'],
  ['1_2', 'Sub (English)'],
  ['1_4', 'Raw'],
  ['1_3', 'Non-English'],
] as const;


export function TorrentDialog({ bridge, title, onClose, onDownloaded, onMessage }: TorrentDialogProps) {
  const [query, setQuery] = useState(title);
  const [category, setCategory] = useState('1_2');
  const [page, setPage] = useState(1);
  const [results, setResults] = useState<TorrentResult[]>([]);
  const [hasNext, setHasNext] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [information, setInformation] = useState<{ title: string; content: string } | null>(null);
  const selected = useMemo(
    () => results.find((torrent) => torrent.id === selectedId) ?? null,
    [results, selectedId],
  );

  const search = useCallback(async (nextQuery: string, nextCategory: string, nextPage: number) => {
    const normalized = nextQuery.trim();
    if (!normalized) return;
    setBusy(true);
    setError(null);
    setSelectedId(null);
    try {
      const response = await bridge.call<TorrentSearchPage>('torrents.search', {
        query: normalized,
        category: nextCategory,
        page: nextPage,
      });
      setResults(response.results);
      setHasNext(response.hasNext);
    } catch (caught) {
      setResults([]);
      setHasNext(false);
      setError(caught instanceof Error ? caught.message : 'Could not search Nyaa');
    } finally {
      setBusy(false);
    }
  }, [bridge]);

  useEffect(() => {
    void search(title, '1_2', 1);
  }, [search, title]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setPage(1);
    await search(query, category, 1);
  }

  async function changeCategory(nextCategory: string) {
    setCategory(nextCategory);
    setPage(1);
    await search(query, nextCategory, 1);
  }

  async function changePage(nextPage: number) {
    setPage(nextPage);
    await search(query, category, nextPage);
  }

  async function showInformation(torrent: TorrentResult) {
    setBusy(true);
    setError(null);
    try {
      const content = await bridge.call<string>('torrents.details', { url: torrent.id });
      setInformation({ title: torrent.title, content });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load torrent information');
    } finally {
      setBusy(false);
    }
  }

  async function download(torrent: TorrentResult) {
    setBusy(true);
    setError(null);
    try {
      const result = await bridge.call<{ downloaded: boolean }>('torrents.download', { magnet: torrent.link });
      if (!result.downloaded) throw new Error('qBittorrent did not accept the torrent');
      await bridge.call('library.scan', { rescan: false });
      await onDownloaded();
      onMessage('Torrent added to qBittorrent');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not add the torrent');
    } finally {
      setBusy(false);
    }
  }

  async function downloadSelected() {
    if (selected) await download(selected);
  }

  return (
    <div className="modal-layer torrent-layer">
      <button className="modal-scrim" aria-label="Close torrent search" onClick={onClose} />
      <section className="torrent-dialog" role="dialog" aria-modal="true" aria-labelledby="torrent-dialog-title">
        <header className="torrent-dialog-header">
          <div>
            <h2 id="torrent-dialog-title">Find a release</h2>
            <p>Search releases and send the selected magnet link to qBittorrent.</p>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close torrent search"><X aria-hidden="true" /></button>
        </header>

        <form className="torrent-search-bar" onSubmit={submit}>
          <label className="torrent-query">Query
            <span className="search-field"><Search aria-hidden="true" /><input value={query} onChange={(event) => setQuery(event.target.value)} required /></span>
          </label>
          <label>Category
            <select aria-label="Category" value={category} onChange={(event) => void changeCategory(event.target.value)}>
              {categories.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <button className="primary-button" disabled={busy}><Search aria-hidden="true" /> {busy ? 'Searching' : 'Search'}</button>
        </form>

        {error && <div className="torrent-error" role="alert">{error}</div>}

        <div className="torrent-table-shell">
          <table className="torrent-table">
            <thead><tr><th>Title</th><th>Size</th><th title="Seeders">S</th><th title="Leechers">L</th><th>Done</th><th>Published</th><th><span className="sr-only">Information</span></th></tr></thead>
            <tbody>
              {results.map((torrent) => (
                <tr
                  key={torrent.id}
                  aria-selected={selectedId === torrent.id}
                  className={selectedId === torrent.id ? 'selected' : ''}
                  tabIndex={0}
                  onClick={() => setSelectedId(torrent.id)}
                  onDoubleClick={() => { setSelectedId(torrent.id); void download(torrent); }}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      setSelectedId(torrent.id);
                    }
                  }}
                >
                  <td title={torrent.title}>{torrent.title}</td>
                  <td>{torrent.size}</td>
                  <td className="seeders">{torrent.seeders}</td>
                  <td className="leechers">{torrent.leechers}</td>
                  <td>{torrent.completed ?? '—'}</td>
                  <td>{torrent.published ?? '—'}</td>
                  <td><button className="icon-button compact" onClick={(event) => { event.stopPropagation(); void showInformation(torrent); }} aria-label={`Torrent information for ${torrent.title}`}><Info aria-hidden="true" /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!busy && results.length === 0 && <div className="torrent-empty" role="status">No releases found.</div>}
        </div>

        <footer className="torrent-dialog-footer">
          <div className="torrent-pagination">
            <button className="secondary-button" disabled={busy || page === 1} onClick={() => void changePage(page - 1)}><ChevronLeft aria-hidden="true" /> Previous</button>
            <span>Page {page} · {results.length} results</span>
            <button className="secondary-button" title={hasNext ? 'Open the next results page' : 'No more results'} disabled={busy || !hasNext} onClick={() => void changePage(page + 1)}>Next <ChevronRight aria-hidden="true" /></button>
          </div>
          <div>
            <button className="secondary-button" onClick={onClose}>Close</button>
            <button className="primary-button" aria-label="Download selected torrent" disabled={busy || !selected} onClick={() => void downloadSelected()}><Download aria-hidden="true" /> Download selected</button>
          </div>
        </footer>
      </section>

      {information && <div className="torrent-info-layer">
        <button className="modal-scrim" aria-label="Dismiss torrent information" onClick={() => setInformation(null)} />
        <section className="torrent-info-dialog" role="dialog" aria-modal="true" aria-labelledby="torrent-info-title">
          <header><h3 id="torrent-info-title">{information.title}</h3><button className="icon-button" onClick={() => setInformation(null)} aria-label="Close torrent information"><X aria-hidden="true" /></button></header>
          <div
            className="torrent-info-content"
            onClick={(event) => {
              const link = (event.target as HTMLElement).closest('a');
              if (!link?.href) return;
              event.preventDefault();
              void bridge.call('native.openExternal', { url: link.href });
            }}
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(marked.parse(information.content, { async: false }) as string),
            }}
          />
        </section>
      </div>}
    </div>
  );
}
