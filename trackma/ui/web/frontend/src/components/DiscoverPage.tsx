import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, Search } from 'lucide-react';
import { createPortal } from 'react-dom';

import type { AppBridge } from '../bridge';
import type {
  DiscoverFilterOptions,
  DiscoverFilters,
  DiscoverHome,
  DiscoverItem,
  DiscoverResults,
  MediaShow,
  SessionSnapshot,
  StatusValue,
} from '../types';
import { DiscoverCatalog, DiscoverCatalogSkeleton } from './DiscoverCatalog';
import { DiscoverDetailsDrawer } from './DiscoverDetailsDrawer';
import { DiscoverFiltersBar } from './DiscoverFilters';


const emptyOptions: DiscoverFilterOptions = {
  genres: [],
  tags: [],
  formats: [],
  statuses: [],
  countries: [],
  sources: [],
  streaming: [],
  sorts: [],
};

const defaultFilters: DiscoverFilters = { sort: 'popularity' };

interface DiscoverPageProps {
  bridge: AppBridge;
  session: SessionSnapshot;
  initialQuery?: string;
  trackerEpisode?: number;
  onAdd(show: MediaShow, status: StatusValue): Promise<void>;
}

function hasBrowseFilters(filters: DiscoverFilters) {
  return Object.entries(filters).some(([key, value]) => {
    if (key === 'sort') return value !== undefined && value !== 'popularity';
    return Array.isArray(value) ? value.length > 0 : value !== undefined && value !== '';
  });
}

export function DiscoverPage({ bridge, session, initialQuery, trackerEpisode, onAdd }: DiscoverPageProps) {
  const [home, setHome] = useState<DiscoverHome | null>(null);
  const [options, setOptions] = useState<DiscoverFilterOptions>(emptyOptions);
  const [filters, setFilters] = useState<DiscoverFilters>(defaultFilters);
  const [results, setResults] = useState<DiscoverResults | null>(null);
  const [browsing, setBrowsing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<DiscoverItem | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set());
  const requestSequence = useRef(0);
  const resultsTop = useRef<HTMLDivElement>(null);

  const loadHome = useCallback(async () => {
    const sequence = ++requestSequence.current;
    setLoading(true);
    setError(null);
    try {
      const [nextHome, nextOptions] = await Promise.all([
        bridge.call<DiscoverHome>('discover.home'),
        bridge.call<DiscoverFilterOptions>('discover.options'),
      ]);
      if (sequence !== requestSequence.current) return;
      setHome(nextHome);
      setOptions(nextOptions);
    } catch (caught) {
      if (sequence === requestSequence.current) {
        setError(caught instanceof Error ? caught.message : 'Could not load the catalog');
      }
    } finally {
      if (sequence === requestSequence.current) setLoading(false);
    }
  }, [bridge]);

  useEffect(() => {
    setFilters(defaultFilters);
    setResults(null);
    setBrowsing(false);
    setSelected(null);
    setAddedIds(new Set());
    void loadHome();
  }, [loadHome, session.account.id, session.api.mediatype]);

  useEffect(() => {
    if (!initialQuery) return;
    setFilters((current) => ({ ...current, search: initialQuery }));
    setBrowsing(true);
  }, [initialQuery]);

  const browse = useCallback(async (nextFilters: DiscoverFilters, page: number) => {
    const sequence = ++requestSequence.current;
    setLoading(true);
    setError(null);
    try {
      const next = await bridge.call<DiscoverResults>('discover.browse', {
        filters: nextFilters,
        page,
        perPage: 24,
      });
      if (sequence !== requestSequence.current) return;
      setResults(next);
    } catch (caught) {
      if (sequence === requestSequence.current) {
        setError(caught instanceof Error ? caught.message : 'Could not search the catalog');
      }
    } finally {
      if (sequence === requestSequence.current) setLoading(false);
    }
  }, [bridge]);

  useEffect(() => {
    if (!browsing) return;
    const timer = window.setTimeout(() => void browse(filters, 1), 350);
    return () => window.clearTimeout(timer);
  }, [browse, browsing, filters]);

  function updateFilters(next: DiscoverFilters) {
    setFilters(next);
    setBrowsing(hasBrowseFilters(next));
    if (!hasBrowseFilters(next)) setResults(null);
  }

  function viewAll(preset: DiscoverFilters) {
    setFilters({ ...defaultFilters, ...preset });
    setBrowsing(true);
    resultsTop.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function changePage(page: number) {
    await browse(filters, page);
    resultsTop.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function openDetails(item: DiscoverItem) {
    setSelected(item);
    setDetailsLoading(true);
    try {
      const details = await bridge.call<DiscoverItem>('discover.details', {
        show: item.show,
        metadata: item.metadata,
      });
      setSelected(details);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load title details');
    } finally {
      setDetailsLoading(false);
    }
  }

  async function add(item: DiscoverItem, status: StatusValue) {
    await onAdd(item.show, status);
    setAddedIds((current) => new Set(current).add(String(item.show.id)));
    setSelected((current) => current && String(current.show.id) === String(item.show.id)
      ? { ...current, inLibrary: true }
      : current);
  }

  const markAdded = (item: DiscoverItem): DiscoverItem => ({
    ...item,
    inLibrary: item.inLibrary || addedIds.has(String(item.show.id)),
  });

  return (
    <section className="page discover-page" aria-labelledby="discover-title">
      <h1 id="discover-title" className="sr-only">Browse {session.api.mediatype}</h1>

      {trackerEpisode !== undefined && (
        <p className="tracker-request" role="status">
          Add the matching title to set progress to episode {trackerEpisode}.
        </p>
      )}

      <DiscoverFiltersBar
        mediaType={session.api.mediatype}
        capabilities={home?.capabilities ?? null}
        options={options}
        filters={filters}
        onChange={updateFilters}
        onReset={() => updateFilters(defaultFilters)}
      />

      {error && (
        <div className="discover-inline-error" role="alert">
          <AlertTriangle aria-hidden="true" />
          <span>{error}</span>
          <button type="button" onClick={() => browsing ? void browse(filters, results?.pageInfo.currentPage ?? 1) : void loadHome()}>Retry</button>
        </div>
      )}

      <div ref={resultsTop} className="discover-content">
        {loading && !home && <DiscoverCatalogSkeleton />}
        {!loading && home && !browsing && home.sections.length > 0 && (
          <DiscoverCatalog
            sections={home.sections.map((section) => ({ ...section, items: section.items.map(markAdded) }))}
            statusOptions={session.media.statusOptions}
            onViewAll={viewAll}
            onDetails={(item) => void openDetails(item)}
            onAdd={add}
          />
        )}
        {!loading && home && !browsing && home.sections.length === 0 && (
          <div className="discover-fallback-empty">
            <Search aria-hidden="true" />
            <h2>Search {session.account.serviceName}</h2>
            <p>This service supports catalog search but does not provide AniList-style browse collections.</p>
          </div>
        )}
        {browsing && (
          <DiscoverCatalog
            title="Search results"
            items={(results?.items ?? []).map(markAdded)}
            pageInfo={results?.pageInfo}
            loading={loading}
            statusOptions={session.media.statusOptions}
            onPageChange={(page) => void changePage(page)}
            onDetails={(item) => void openDetails(item)}
            onAdd={add}
          />
        )}
      </div>

      {selected && createPortal(
        <DiscoverDetailsDrawer
          bridge={bridge}
          item={markAdded(selected)}
          loading={detailsLoading}
          statusOptions={session.media.statusOptions}
          onAdd={add}
          onClose={() => setSelected(null)}
        />,
        document.body,
      )}
    </section>
  );
}
