import { Check, ChevronLeft, ChevronRight, Plus } from 'lucide-react';
import { useState } from 'react';

import type {
  DiscoverFilters,
  DiscoverItem,
  DiscoverPageInfo,
  DiscoverSection,
  StatusOption,
  StatusValue,
} from '../types';


interface DiscoverCatalogProps {
  title?: string;
  items?: DiscoverItem[];
  sections?: DiscoverSection[];
  pageInfo?: DiscoverPageInfo;
  loading?: boolean;
  statusOptions: StatusOption[];
  onViewAll?(preset: DiscoverFilters): void;
  onPageChange?(page: number): void;
  onDetails(item: DiscoverItem): void;
  onAdd(item: DiscoverItem, status: StatusValue): Promise<void>;
}

function humanize(value?: string | null) {
  if (!value) return '';
  return value.replaceAll('_', ' ').toLocaleLowerCase().replace(/^./, (character) => character.toLocaleUpperCase());
}

function CatalogCard({ item, statusOptions, onDetails, onAdd }: {
  item: DiscoverItem;
  statusOptions: StatusOption[];
  onDetails(item: DiscoverItem): void;
  onAdd(item: DiscoverItem, status: StatusValue): Promise<void>;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const cover = item.show.image || item.show.image_thumb;
  const releasing = item.metadata.status === 'RELEASING';

  async function add(status: StatusValue) {
    setAdding(true);
    try {
      await onAdd(item, status);
      setMenuOpen(false);
    } finally {
      setAdding(false);
    }
  }

  return (
    <article className="discover-media-card">
      <div className="discover-cover-wrap">
        <button type="button" className="discover-card-hit" aria-label={`Open details for ${item.show.title}`} onClick={() => onDetails(item)} />
        {cover ? <img src={cover} alt={`Cover for ${item.show.title}`} loading="lazy" /> : <div className="discover-cover-placeholder">{item.show.title.slice(0, 2).toLocaleUpperCase()}</div>}
        {item.metadata.rank && <span className={`discover-rank rank-${Math.min(item.metadata.rank, 10)}`}>#{item.metadata.rank}</span>}
        <button
          type="button"
          className={item.inLibrary ? 'discover-add-button added' : 'discover-add-button'}
          aria-label={item.inLibrary ? `${item.show.title} is in list` : `Add ${item.show.title} to list`}
          disabled={item.inLibrary || adding}
          onClick={() => setMenuOpen((open) => !open)}
        >
          {item.inLibrary ? <Check aria-hidden="true" /> : <Plus aria-hidden="true" />}
        </button>
        {menuOpen && !item.inLibrary && (
          <div className="discover-add-menu" role="menu" aria-label={`Add ${item.show.title} as`}>
            {statusOptions.map((status) => (
              <button type="button" role="menuitem" key={String(status.value)} onClick={() => void add(status.value)}>{status.label}</button>
            ))}
          </div>
        )}
        <div className="discover-card-peek" aria-hidden="true">
          <strong>{item.metadata.averageScore ? `${item.metadata.averageScore}%` : humanize(item.metadata.format)}</strong>
          <span>{item.metadata.genres?.slice(0, 2).join(' · ')}</span>
        </div>
      </div>
      <button type="button" className="discover-card-title" onClick={() => onDetails(item)}>
        {releasing && <span className="airing-dot" aria-label="Currently airing" />}
        <span>{item.show.title}</span>
      </button>
    </article>
  );
}

function MediaGrid({ items, statusOptions, onDetails, onAdd }: {
  items: DiscoverItem[];
  statusOptions: StatusOption[];
  onDetails(item: DiscoverItem): void;
  onAdd(item: DiscoverItem, status: StatusValue): Promise<void>;
}) {
  return <div className="discover-media-grid">{items.map((item) => <CatalogCard key={String(item.show.id)} item={item} statusOptions={statusOptions} onDetails={onDetails} onAdd={onAdd} />)}</div>;
}

function pageNumbers(pageInfo: DiscoverPageInfo) {
  const start = Math.max(1, Math.min(pageInfo.currentPage - 2, pageInfo.lastPage - 4));
  const end = Math.min(pageInfo.lastPage, start + 4);
  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
}

export function DiscoverCatalog({ title, items = [], sections, pageInfo, loading, statusOptions, onViewAll, onPageChange, onDetails, onAdd }: DiscoverCatalogProps) {
  if (sections) {
    return <div className="discover-sections">{sections.map((section) => (
      <section className={section.id === 'top' ? 'discover-section ranked' : 'discover-section'} key={section.id} aria-labelledby={`discover-section-${section.id}`}>
        <header><h2 id={`discover-section-${section.id}`}>{section.title}</h2><button type="button" onClick={() => onViewAll?.(section.preset)}>View All</button></header>
        <MediaGrid items={section.items} statusOptions={statusOptions} onDetails={onDetails} onAdd={onAdd} />
      </section>
    ))}</div>;
  }

  return (
    <section className="discover-results-section" aria-labelledby="discover-results-title" aria-busy={loading}>
      <header><div><h2 id="discover-results-title">{title}</h2>{pageInfo && <p>{pageInfo.total} titles</p>}</div></header>
      {loading ? <DiscoverCatalogSkeleton compact /> : items.length > 0 ? <MediaGrid items={items} statusOptions={statusOptions} onDetails={onDetails} onAdd={onAdd} /> : <div className="discover-no-results"><h3>No titles found</h3><p>Try removing a filter or using a broader title search.</p></div>}
      {pageInfo && pageInfo.lastPage > 1 && (
        <nav className="discover-pagination" aria-label="Catalog pages">
          <button type="button" aria-label="Previous page" disabled={pageInfo.currentPage === 1} onClick={() => onPageChange?.(pageInfo.currentPage - 1)}><ChevronLeft aria-hidden="true" /></button>
          {pageNumbers(pageInfo).map((page) => <button type="button" key={page} aria-current={page === pageInfo.currentPage ? 'page' : undefined} onClick={() => onPageChange?.(page)}>{page}</button>)}
          <button type="button" aria-label="Next page" disabled={!pageInfo.hasNextPage} onClick={() => onPageChange?.(pageInfo.currentPage + 1)}><ChevronRight aria-hidden="true" /></button>
        </nav>
      )}
    </section>
  );
}

export function DiscoverCatalogSkeleton({ compact = false }: { compact?: boolean }) {
  return <div className={compact ? 'discover-skeleton-grid compact' : 'discover-skeleton-grid'} aria-label="Loading catalog" role="status">{Array.from({ length: compact ? 12 : 18 }, (_, index) => <div className="discover-card-skeleton" key={index}><span /><i /></div>)}</div>;
}
