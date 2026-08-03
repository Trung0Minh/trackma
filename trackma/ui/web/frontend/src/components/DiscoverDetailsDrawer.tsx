import DOMPurify from 'dompurify';
import { Check, ExternalLink, Plus, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import type { AppBridge } from '../bridge';
import type { DiscoverItem, StatusOption, StatusValue } from '../types';


interface DiscoverDetailsDrawerProps {
  bridge: AppBridge;
  item: DiscoverItem;
  loading: boolean;
  statusOptions: StatusOption[];
  onAdd(item: DiscoverItem, status: StatusValue): Promise<void>;
  onClose(): void;
}

function humanize(value?: string | null) {
  return value ? value.replaceAll('_', ' ').toLocaleLowerCase().replace(/^./, (character) => character.toLocaleUpperCase()) : 'Unknown';
}

export function DiscoverDetailsDrawer({ bridge, item, loading, statusOptions, onAdd, onClose }: DiscoverDetailsDrawerProps) {
  const [status, setStatus] = useState<StatusValue>(statusOptions[0]?.value ?? '');
  const [adding, setAdding] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);
  const metadata = item.metadata;
  const cover = item.show.image || item.show.image_thumb;

  useEffect(() => {
    closeRef.current?.focus({ preventScroll: true });
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [onClose]);

  async function add() {
    setAdding(true);
    try {
      await onAdd(item, status);
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="discover-drawer-layer">
      <button type="button" className="discover-drawer-scrim" aria-label="Dismiss catalog details" onClick={onClose} />
      <aside className="discover-details-drawer" role="dialog" aria-modal="true" aria-labelledby="catalog-detail-title" aria-busy={loading}>
        <button ref={closeRef} type="button" className="discover-detail-close" aria-label="Close catalog details" onClick={onClose}><X aria-hidden="true" /></button>
        <div className="discover-detail-hero">
          {cover ? <img src={cover} alt={`Cover for ${item.show.title}`} /> : <div className="discover-cover-placeholder">{item.show.title.slice(0, 2)}</div>}
          <div>
            <p>{humanize(metadata.format)} · {humanize(metadata.status)}</p>
            <h2 id="catalog-detail-title">{item.show.title}</h2>
            <div className="discover-detail-score"><strong>{metadata.averageScore ? `${metadata.averageScore}%` : '—'}</strong><span>average score</span></div>
            <div className="discover-detail-actions">
              {item.inLibrary ? <span className="discover-in-list"><Check aria-hidden="true" /> In list</span> : <><select aria-label="Add status" value={String(status)} onChange={(event) => setStatus(statusOptions.find((option) => String(option.value) === event.target.value)?.value ?? event.target.value)}>{statusOptions.map((option) => <option key={String(option.value)} value={String(option.value)}>{option.label}</option>)}</select><button type="button" onClick={() => void add()} disabled={adding}><Plus aria-hidden="true" /> Add</button></>}
              {item.show.url && <button type="button" className="discover-external-link" onClick={() => void bridge.call('native.openExternal', { url: item.show.url })}><ExternalLink aria-hidden="true" /> Open on {item.show.url.includes('anilist') ? 'AniList' : 'service'}</button>}
            </div>
          </div>
        </div>

        <dl className="discover-detail-facts">
          <div><dt>Season</dt><dd>{metadata.seasonYear ? `${humanize(metadata.season)} ${metadata.seasonYear}` : 'Unknown'}</dd></div>
          <div><dt>Episodes</dt><dd>{item.show.total || '?'}</dd></div>
          <div><dt>Source</dt><dd>{humanize(metadata.source)}</dd></div>
          <div><dt>Studio</dt><dd>{metadata.studios?.join(', ') || 'Unknown'}</dd></div>
        </dl>

        {metadata.genres && <div className="discover-detail-chips" aria-label="Genres">{metadata.genres.map((genre) => <span key={genre}>{genre}</span>)}</div>}
        {metadata.description && <div className="discover-detail-description" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(metadata.description) }} />}
        {metadata.tags && metadata.tags.length > 0 && <section className="discover-detail-tags"><h3>Tags</h3><div>{metadata.tags.slice(0, 8).map((tag) => <span key={tag.name}>{tag.name}{tag.rank ? ` ${tag.rank}%` : ''}</span>)}</div></section>}
      </aside>
    </div>
  );
}
