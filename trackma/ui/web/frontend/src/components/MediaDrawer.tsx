import { useEffect, useState } from 'react';
import {
  Download,
  ExternalLink,
  FolderOpen,
  Minus,
  Play,
  Plus,
  Save,
  Trash2,
  X,
} from 'lucide-react';

import type { AppBridge } from '../bridge';
import type { MediaShow, SessionSnapshot, ShowDetails, StatusValue } from '../types';
import { TorrentDialog } from './TorrentDialog';

interface MediaDrawerProps {
  bridge: AppBridge;
  session: SessionSnapshot;
  show: MediaShow;
  onClose(): void;
  onChanged(): Promise<void>;
  onMessage(message: string): void;
}

function dateInputValue(value: unknown) {
  if (!value) return '';
  const normalized = String(value);
  return /^\d{4}-\d{2}-\d{2}/.test(normalized) ? normalized.slice(0, 10) : '';
}

function sameValue(left: unknown, right: unknown) {
  return String(left ?? '') === String(right ?? '');
}

export function MediaDrawer({ bridge, session, show, onClose, onChanged, onMessage }: MediaDrawerProps) {
  const [draft, setDraft] = useState(show);
  const [alternateTitle, setAlternateTitle] = useState(session.library.alternateTitles[String(show.id)] ?? '');
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [torrentOpen, setTorrentOpen] = useState(false);

  useEffect(() => {
    setDraft(show);
    setAlternateTitle(session.library.alternateTitles[String(show.id)] ?? '');
    setConfirmDelete(false);
    bridge.call<ShowDetails>('show.details', { showId: show.id }).then((result) => {
      setDraft(result.show);
    });
  }, [bridge, session.library.alternateTitles, show]);

  async function save() {
    setBusy(true);
    try {
      const patch: Record<string, unknown> = {};
      if (Number(draft.my_progress) !== Number(show.my_progress)) patch.progress = Number(draft.my_progress);
      if (Number(draft.my_score) !== Number(show.my_score)) patch.score = Number(draft.my_score);
      if (!sameValue(draft.my_status, show.my_status)) patch.status = draft.my_status;
      if (Number(draft.my_rewatches ?? 0) !== Number(show.my_rewatches ?? 0)) patch.rewatches = Number(draft.my_rewatches ?? 0);
      if (!sameValue(draft.my_notes, show.my_notes)) patch.notes = draft.my_notes ?? '';
      if (!sameValue(draft.my_tags, show.my_tags)) patch.tags = draft.my_tags ?? '';
      if (session.media.can_date) {
        const draftStartDate = dateInputValue(draft.my_start_date);
        const showStartDate = dateInputValue(show.my_start_date);
        const draftFinishDate = dateInputValue(draft.my_finish_date);
        const showFinishDate = dateInputValue(show.my_finish_date);
        if (draftStartDate !== showStartDate) patch.startDate = draftStartDate || null;
        if (draftFinishDate !== showFinishDate) patch.finishDate = draftFinishDate || null;
      }

      if (Object.keys(patch).length > 0) {
        await bridge.call('show.update', { showId: show.id, patch });
      }
      if (alternateTitle !== (session.library.alternateTitles[String(show.id)] ?? '')) {
        await bridge.call('show.setAltTitle', { showId: show.id, title: alternateTitle });
      }
      await bridge.call('sync.upload');
      await onChanged();
      onMessage(`${show.title} saved to ${session.account.serviceName}`);
    } finally {
      setBusy(false);
    }
  }

  async function changeProgress(amount: number) {
    const progress = Math.max(0, Math.min(draft.total || 10000, draft.my_progress + amount));
    setDraft((current) => ({ ...current, my_progress: progress }));
    await bridge.call('show.update', { showId: show.id, patch: { progress } });
    await onChanged();
  }

  async function remove() {
    setBusy(true);
    try {
      await bridge.call('show.delete', { showId: show.id });
      await onChanged();
      onMessage(`${show.title} removed`);
      onClose();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="drawer-layer" role="presentation">
      <button className="drawer-scrim" aria-label="Close title details" onClick={onClose} />
      <aside className="media-drawer" aria-labelledby="drawer-title">
        <header className="drawer-header">
          <h2 id="drawer-title">{show.title}</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close"><X aria-hidden="true" /></button>
        </header>

        <div className="drawer-hero">
          <div className="drawer-poster-stack">
            {show.image || show.image_thumb ? <img src={show.image || show.image_thumb} alt={`Cover for ${show.title}`} /> : <div className="poster-placeholder">{show.title.slice(0, 2)}</div>}
          </div>
          <div>
            <p>{show.type || session.api.mediatype}</p>
            <strong>{show.my_progress} / {show.total || '?'} complete</strong>
            <div className="drawer-quick-actions" aria-label="Title shortcuts">
              {session.account.api === 'anilist' && show.url && (
                <button
                  className="icon-button compact"
                  onClick={() => bridge.call('native.openExternal', { url: show.url })}
                  aria-label={`Open ${show.title} on AniList`}
                  title="Open on AniList"
                >
                  <ExternalLink aria-hidden="true" />
                </button>
              )}
              {session.media.can_delete !== false && (
                <button
                  className="icon-button compact danger-icon"
                  onClick={() => setConfirmDelete(true)}
                  aria-label={`Remove ${show.title}`}
                  title="Remove"
                >
                  <Trash2 aria-hidden="true" />
                </button>
              )}
            </div>
            <div className="drawer-actions">
              {session.media.can_play && <button className="primary-button" onClick={() => bridge.call('show.play', { showId: show.id, episode: 0 })}><Play aria-hidden="true" /> Play next</button>}
              <button className="secondary-button" onClick={() => bridge.call('show.openFolder', { showId: show.id })}><FolderOpen aria-hidden="true" /> Folder</button>
              <button className="secondary-button" onClick={() => setTorrentOpen(true)}><Download aria-hidden="true" /> Torrent</button>
            </div>
          </div>
        </div>

        {confirmDelete && (
          <section className="drawer-remove-confirm" aria-label="Confirm removal">
            <p>Remove this title and queue the deletion?</p>
            <div>
              <button className="danger-button" onClick={remove} disabled={busy}>Remove title</button>
              <button className="text-button" onClick={() => setConfirmDelete(false)}>Cancel</button>
            </div>
          </section>
        )}

        <div className="drawer-form">
          <div className="field-pair">
            <label>Progress
              <span className="stepper"><button onClick={() => changeProgress(-1)} aria-label="Decrease progress"><Minus /></button><input type="number" value={draft.my_progress} min={0} max={draft.total || undefined} onChange={(event) => setDraft({ ...draft, my_progress: Number(event.target.value) })} /><button onClick={() => changeProgress(1)} aria-label="Increase progress"><Plus /></button></span>
            </label>
            <label>Score
              <input type="number" value={draft.my_score} min={0} max={session.media.score_max} step={session.media.score_step} onChange={(event) => setDraft({ ...draft, my_score: Number(event.target.value) })} />
            </label>
          </div>
          <div className="field-pair">
            <label>Status
              <select value={String(draft.my_status)} onChange={(event) => setDraft({ ...draft, my_status: session.media.statusOptions.find((item) => String(item.value) === event.target.value)?.value as StatusValue })}>
                {session.media.statusOptions.map((item) => <option key={String(item.value)} value={String(item.value)}>{item.label}</option>)}
              </select>
            </label>
            <label>Rewatches
              <input type="number" min={0} value={draft.my_rewatches ?? 0} onChange={(event) => setDraft({ ...draft, my_rewatches: Number(event.target.value) })} />
            </label>
          </div>
          {session.media.can_date && <div className="field-pair">
            <label>Start date
              <input type="date" value={dateInputValue(draft.my_start_date)} onChange={(event) => setDraft({ ...draft, my_start_date: event.target.value || null })} />
            </label>
            <label>Finish date
              <input type="date" value={dateInputValue(draft.my_finish_date)} onChange={(event) => setDraft({ ...draft, my_finish_date: event.target.value || null })} />
            </label>
          </div>}
          <label>Alternative title<input value={alternateTitle} onChange={(event) => setAlternateTitle(event.target.value)} placeholder="Name used for local matching" /></label>
          <label>Tags<input value={draft.my_tags ?? ''} onChange={(event) => setDraft({ ...draft, my_tags: event.target.value })} placeholder="Comma separated" /></label>
          <label>Notes<textarea value={draft.my_notes ?? ''} onChange={(event) => setDraft({ ...draft, my_notes: event.target.value })} rows={4} /></label>
          <button className="primary-button drawer-save" onClick={save} disabled={busy}><Save aria-hidden="true" /> Save changes</button>
        </div>

      </aside>
      {torrentOpen && <TorrentDialog bridge={bridge} title={show.title} onClose={() => setTorrentOpen(false)} onDownloaded={onChanged} onMessage={onMessage} />}
    </div>
  );
}
