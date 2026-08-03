import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Info, LoaderCircle, RefreshCw, Timer, X, XCircle } from 'lucide-react';

import type { AppBridge, BridgeEvent } from './bridge';
import { AccountPanel } from './components/AccountPanel';
import { DiscoverPage } from './components/DiscoverPage';
import { LibraryPage } from './components/LibraryPage';
import { MediaDrawer } from './components/MediaDrawer';
import { SettingsPage } from './components/SettingsPage';
import { TopBar, type PageName } from './components/TopBar';
import type {
  Bootstrap,
  LibrarySnapshot,
  MediaShow,
  SessionSnapshot,
  StatusValue,
} from './types';


interface AppProps {
  bridge: AppBridge;
}

type ToastTone = 'success' | 'info' | 'danger';

interface ToastState {
  message: string;
  tone: ToastTone;
}

const refreshEvents = new Set([
  'episode_changed',
  'score_changed',
  'show_changed',
  'status_changed',
  'show_added',
  'show_deleted',
  'show_synced',
  'queue_changed',
  'library_updated',
]);


function playbackCountdown(tracker: Record<string, unknown> | null) {
  if (!tracker) return null;
  const state = String(tracker.state ?? '').toLocaleLowerCase();
  const playing = tracker.state === 2 || state.includes('playing');
  const timer = typeof tracker.timer === 'number' ? tracker.timer : Number.NaN;
  const show = tracker.show as [MediaShow, number] | null | undefined;
  if (!playing || !Number.isFinite(timer) || timer <= 0 || !Array.isArray(show)) return null;
  return { title: show[0]?.title ?? 'Detected title', episode: show[1], timer };
}

function toastToneFromMessageLevel(level: unknown): ToastTone {
  if (typeof level !== 'number') return 'info';
  return level >= 3 ? 'danger' : 'info';
}

function ToastIcon({ tone }: { tone: ToastTone }) {
  if (tone === 'danger') return <XCircle aria-hidden="true" />;
  if (tone === 'info') return <Info aria-hidden="true" />;
  return <CheckCircle2 aria-hidden="true" />;
}

export default function App({ bridge }: AppProps) {
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [session, setSession] = useState<SessionSnapshot | null>(null);
  const [page, setPage] = useState<PageName>('library');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [theme, setTheme] = useState('dark');
  const [selected, setSelected] = useState<MediaShow | null>(null);
  const [accountsOpen, setAccountsOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [syncConflict, setSyncConflict] = useState(false);
  const [trackerUpdate, setTrackerUpdate] = useState<{ show: MediaShow; episode: number } | null>(null);
  const [trackerAdd, setTrackerAdd] = useState<{ show: MediaShow; episode: number } | null>(null);

  const showMessage = useCallback((message: string, tone: ToastTone = 'success') => {
    setToast({ message, tone });
    window.setTimeout(() => setToast(null), 3200);
  }, []);

  const openSession = useCallback(async (accountId: number, remember: boolean) => {
    setBusy(true);
    setError(null);
    try {
      const next = await bridge.call<SessionSnapshot>('session.open', { accountId, remember });
      setSession(next);
      setAccountsOpen(false);
      setPage('library');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not open the account');
    } finally {
      setBusy(false);
    }
  }, [bridge]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      bridge.call<Bootstrap>('app.bootstrap'),
      bridge.call<Record<string, unknown>>('native.getWindowConfig').catch(() => ({} as Record<string, unknown>)),
    ]).then(async ([initial, interfaceSettings]) => {
      if (cancelled) return;
      setBootstrap(initial);
      const initialTheme = String(interfaceSettings.theme_mode ?? 'dark');
      setTheme(initialTheme);
      setViewMode(interfaceSettings.view_mode === 'table' ? 'table' : 'grid');
      if (initial.defaultAccountId !== null) {
        await openSession(initial.defaultAccountId, true);
      }
    }).catch((caught) => {
      if (!cancelled) setError(caught instanceof Error ? caught.message : 'Trackma could not start');
    });
    return () => { cancelled = true; };
  }, [bridge, openSession]);

  const refreshLibrary = useCallback(async () => {
    if (!session) return;
    const library = await bridge.call<LibrarySnapshot>('library.snapshot');
    setSession((current) => current ? { ...current, library } : current);
    setSelected((current) => current ? library.shows.find((show) => String(show.id) === String(current.id)) ?? null : null);
  }, [bridge, session]);

  useEffect(() => bridge.subscribe((event: BridgeEvent) => {
    if (refreshEvents.has(event.name)) void refreshLibrary();
    if (event.name === 'tracker_state') {
      setSession((current) => current ? {
        ...current,
        library: { ...current.library, tracker: event.payload as Record<string, unknown> | null },
      } : current);
    }
    if (event.name === 'message') {
      const payload = event.payload as { level?: unknown; message?: string };
      if (payload.message) showMessage(payload.message, toastToneFromMessageLevel(payload.level));
    }
    if (event.name === 'prompt_for_update') {
      const [show, episode] = event.payload as [MediaShow, number];
      setTrackerUpdate({ show, episode });
    }
    if (event.name === 'prompt_for_add') {
      const [show, episode] = event.payload as [MediaShow, number];
      setTrackerAdd({ show, episode });
      setPage('discover');
      showMessage(`Find the catalog match for ${show.title}`);
    }
  }), [bridge, refreshLibrary, showMessage]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme === 'light' ? 'light' : 'dark';
  }, [theme]);

  async function run(action: () => Promise<unknown>, message?: string) {
    setBusy(true);
    setError(null);
    try {
      await action();
      if (message) showMessage(message);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The operation failed');
    } finally {
      setBusy(false);
    }
  }

  async function libraryCommand(command: string, show?: MediaShow) {
    if (!session) return;
    if (command === 'download' && session.library.queueCount > 0) {
      setSyncConflict(true);
      return;
    }
    const actions: Record<string, () => Promise<unknown>> = {
      scan: async () => setSession({ ...session, library: await bridge.call('library.scan', { rescan: false }) }),
      download: async () => setSession({ ...session, library: await bridge.call('sync.download') }),
      upload: async () => setSession({ ...session, library: await bridge.call('sync.upload') }),
      increment: async () => {
        if (!show) return;
        await bridge.call('show.update', { showId: show.id, patch: { progress: show.my_progress + 1 } });
        await refreshLibrary();
      },
      play: async () => { if (show) await bridge.call('show.play', { showId: show.id, episode: 0 }); },
      openExternal: async () => {
        if (show?.url) await bridge.call('native.openExternal', { url: show.url });
      },
    };
    const action = actions[command];
    if (action) await run(action, command === 'upload' ? 'Changes synchronized' : undefined);
  }

  async function resolveSyncConflict(choice: 'send' | 'discard') {
    setSyncConflict(false);
    await run(async () => {
      if (choice === 'send') await bridge.call('sync.upload');
      const library = await bridge.call<LibrarySnapshot>('sync.download');
      setSession((current) => current ? { ...current, library } : current);
    }, 'Remote list retrieved');
  }

  async function switchMediaType(mediaType: string) {
    await run(async () => {
      const next = await bridge.call<SessionSnapshot>('session.switchMediaType', { mediaType });
      setSession(next);
      setSelected(null);
    });
  }

  async function searchDiscover(payload: Record<string, unknown>) {
    setBusy(true);
    try {
      return await bridge.call<MediaShow[]>('discover.search', payload);
    } finally {
      setBusy(false);
    }
  }

  async function addDiscovered(show: MediaShow, status: StatusValue) {
    await run(async () => {
      const library = await bridge.call<LibrarySnapshot>('discover.add', { show, status });
      if (trackerAdd) {
        await bridge.call('show.update', { showId: show.id, patch: { progress: trackerAdd.episode } });
        setTrackerAdd(null);
      }
      setSession((current) => current ? { ...current, library } : current);
    }, `${show.title} added`);
  }

  async function applyTrackerUpdate() {
    if (!trackerUpdate) return;
    const request = trackerUpdate;
    setTrackerUpdate(null);
    await run(async () => {
      await bridge.call('show.update', { showId: request.show.id, patch: { progress: request.episode } });
      await refreshLibrary();
    }, `${request.show.title} updated to episode ${request.episode}`);
  }

  function changeViewMode(mode: 'grid' | 'table') {
    setViewMode(mode);
    void bridge.call('native.windowConfig', { settings: { view_mode: mode } });
  }

  if (!bootstrap) {
    return <main className="boot-screen" role="status"><span className="boot-mark"><LoaderCircle /></span><h1>Starting Trackma</h1><p>Loading accounts and local library data.</p>{error && <p className="boot-error">{error}</p>}</main>;
  }

  if (!session) {
    return <AccountPanel bridge={bridge} bootstrap={bootstrap} onSelect={openSession} onBootstrap={setBootstrap} onMessage={showMessage} />;
  }

  const countdown = playbackCountdown(session.library.tracker);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <TopBar
        activePage={page}
        account={session.account}
        mediaType={session.api.mediatype}
        supportedMediaTypes={session.api.supported_mediatypes}
        queueCount={session.library.queueCount}
        onNavigate={setPage}
        onAccounts={() => setAccountsOpen(true)}
        onMediaTypeChange={(mediaType) => void switchMediaType(mediaType)}
      />
      <main id="main-content" className="main-content">
        {error && <div className="error-banner" role="alert"><AlertTriangle /><span>{error}</span><button onClick={() => setError(null)} aria-label="Dismiss error"><X /></button></div>}
        {page === 'library' && <LibraryPage session={session} viewMode={viewMode} onViewModeChange={changeViewMode} onSelect={setSelected} onCommand={libraryCommand} />}
        {page === 'discover' && <DiscoverPage session={session} busy={busy} initialQuery={trackerAdd?.show.title} trackerEpisode={trackerAdd?.episode} onSearch={searchDiscover} onAdd={addDiscovered} />}
        {page === 'settings' && <SettingsPage bridge={bridge} onSaved={showMessage} onThemeChange={setTheme} />}
      </main>

      <div className="connection-state" role="status"><span aria-hidden="true" /><span>Engine connected</span></div>
      {countdown && (
        <div className="tracker-countdown" role="status" aria-label="Playback update countdown" aria-live="polite" aria-atomic="true">
          <span className="tracker-countdown-icon" aria-hidden="true"><Timer /></span>
          <span className="tracker-countdown-copy">
            <small>{countdown.title} · Episode {countdown.episode}</small>
            <strong>Update prompt in {countdown.timer}s</strong>
          </span>
        </div>
      )}
      {busy && <div className="busy-indicator" role="status"><RefreshCw /> Working</div>}
      {toast && <div className={`toast ${toast.tone}`} role={toast.tone === 'danger' ? 'alert' : 'status'}><ToastIcon tone={toast.tone} /> {toast.message}</div>}
      {selected && <MediaDrawer bridge={bridge} session={session} show={selected} onClose={() => setSelected(null)} onChanged={refreshLibrary} onMessage={showMessage} />}
      {accountsOpen && <AccountPanel bridge={bridge} bootstrap={bootstrap} modal onClose={() => setAccountsOpen(false)} onSelect={openSession} onBootstrap={setBootstrap} onMessage={showMessage} />}
      {syncConflict && <div className="modal-layer"><button className="modal-scrim" aria-label="Cancel retrieve" onClick={() => setSyncConflict(false)} /><section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="sync-conflict-title"><AlertTriangle /><h2 id="sync-conflict-title">Unsynced changes</h2><p>Send the current queue before retrieving, or discard it and replace the local list.</p><div><button className="primary-button" onClick={() => resolveSyncConflict('send')}>Send, then retrieve</button><button className="danger-button" onClick={() => resolveSyncConflict('discard')}>Discard and retrieve</button><button className="text-button" onClick={() => setSyncConflict(false)}>Cancel</button></div></section></div>}
      {trackerUpdate && <div className="modal-layer"><button className="modal-scrim" aria-label="Decline tracker update" onClick={() => setTrackerUpdate(null)} /><section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="tracker-update-title"><RefreshCw /><h2 id="tracker-update-title">Update progress?</h2><p>Set {trackerUpdate.show.title} to episode {trackerUpdate.episode}?</p><div><button className="primary-button" onClick={applyTrackerUpdate}>Update progress</button><button className="text-button" onClick={() => setTrackerUpdate(null)}>Not now</button></div></section></div>}
    </div>
  );
}
