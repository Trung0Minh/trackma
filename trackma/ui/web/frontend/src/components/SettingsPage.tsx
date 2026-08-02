import { useEffect, useState } from 'react';
import {
  Bell,
  Download,
  Film,
  FolderOpen,
  MonitorCog,
  Palette,
  Radio,
  Save,
  Server,
} from 'lucide-react';

import type { AppBridge } from '../bridge';


type SettingsSection = 'media' | 'library' | 'sync' | 'torrents' | 'interface' | 'appearance';

interface SettingsPageProps {
  bridge: AppBridge;
  onSaved(message: string): void;
  onThemeChange(theme: string): void;
}


const sections = [
  { id: 'media', label: 'Media tracker', icon: Radio },
  { id: 'library', label: 'Local library', icon: FolderOpen },
  { id: 'sync', label: 'Synchronization', icon: Download },
  { id: 'torrents', label: 'Torrents', icon: Server },
  { id: 'interface', label: 'Interface', icon: MonitorCog },
  { id: 'appearance', label: 'Appearance', icon: Palette },
] as const;


export function SettingsPage({ bridge, onSaved, onThemeChange }: SettingsPageProps) {
  const [active, setActive] = useState<SettingsSection>('media');
  const [engine, setEngine] = useState<Record<string, unknown> | null>(null);
  const [windowSettings, setWindowSettings] = useState<Record<string, unknown> | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      bridge.call<Record<string, unknown>>('settings.get'),
      bridge.call<Record<string, unknown>>('native.getWindowConfig'),
    ]).then(([engineConfig, interfaceConfig]) => {
      setEngine(engineConfig);
      setWindowSettings(interfaceConfig);
    });
  }, [bridge]);

  function updateEngine(key: string, value: unknown) {
    setEngine((current) => ({ ...(current ?? {}), [key]: value }));
  }

  function updateWindow(key: string, value: unknown) {
    setWindowSettings((current) => ({ ...(current ?? {}), [key]: value }));
    if (key === 'theme_mode') onThemeChange(String(value));
  }

  async function choosePlayer() {
    const selected = await bridge.call<{ path: string | null }>('native.pickPlayer', {
      current: engine?.player,
    });
    if (selected.path) updateEngine('player', selected.path);
  }

  async function addDirectory() {
    const selected = await bridge.call<{ path: string | null }>('native.pickDirectory');
    if (!selected.path) return;
    const current = Array.isArray(engine?.searchdir) ? engine.searchdir : [];
    if (!current.includes(selected.path)) updateEngine('searchdir', [...current, selected.path]);
  }

  async function save() {
    if (!engine || !windowSettings) return;
    setSaving(true);
    try {
      await Promise.all([
        bridge.call('settings.save', { settings: engine }),
        bridge.call('native.windowConfig', { settings: windowSettings }),
      ]);
      onSaved('Settings saved');
    } finally {
      setSaving(false);
    }
  }

  if (!engine || !windowSettings) {
    return <div className="page-loading" role="status">Loading settings</div>;
  }

  return (
    <section className="page settings-page" aria-labelledby="settings-title">
      <header className="page-header">
        <div>
          <h1 id="settings-title">Settings</h1>
          <p className="page-description">Changes are applied to the active Trackma engine.</p>
        </div>
        <button className="primary-button" onClick={save} disabled={saving}>
          <Save aria-hidden="true" /> {saving ? 'Saving' : 'Save changes'}
        </button>
      </header>

      <div className="settings-layout">
        <nav className="settings-nav" aria-label="Settings categories">
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <button key={section.id} className={active === section.id ? 'active' : ''} onClick={() => setActive(section.id)}>
                <Icon aria-hidden="true" /> {section.label}
              </button>
            );
          })}
        </nav>

        <div className="settings-panel">
          {active === 'media' && (
            <SettingsGroup title="Media recognition" description="Control how Trackma detects and updates playing media." icon={Radio}>
              <Toggle label="Enable tracker" checked={Boolean(engine.tracker_enabled)} onChange={(value) => updateEngine('tracker_enabled', value)} />
              <SelectField label="Tracker type" value={String(engine.tracker_type)} onChange={(value) => updateEngine('tracker_type', value)} options={[
                ['auto', 'Auto-detect'], ['inotify_auto', 'inotify'], ['polling', 'Polling'], ['mpris', 'MPRIS'], ['plex', 'Plex'], ['jellyfin', 'Jellyfin'], ['kodi', 'Kodi'], ['win32', 'Win32'],
              ]} />
              <NumberField label="Polling interval" suffix="seconds" value={Number(engine.tracker_interval)} min={5} onChange={(value) => updateEngine('tracker_interval', value)} />
              <NumberField label="Update delay" suffix="seconds" value={Number(engine.tracker_update_wait_s)} min={0} onChange={(value) => updateEngine('tracker_update_wait_s', value)} />
              <Toggle label="Ask before updating progress" checked={Boolean(engine.tracker_update_prompt)} onChange={(value) => updateEngine('tracker_update_prompt', value)} />
              <Toggle label="Ask before adding unknown titles" checked={Boolean(engine.tracker_not_found_prompt)} onChange={(value) => updateEngine('tracker_not_found_prompt', value)} />
            </SettingsGroup>
          )}

          {active === 'library' && (
            <SettingsGroup title="Local media" description="Choose the player and directories Trackma scans." icon={Film}>
              <div className="setting-row">
                <div><strong>Media player</strong><small>Executable used for playback</small></div>
                <div className="input-action"><input value={String(engine.player)} onChange={(event) => updateEngine('player', event.target.value)} /><button className="secondary-button" onClick={choosePlayer}>Browse</button></div>
              </div>
              <div className="setting-row directory-setting">
                <div><strong>Media directories</strong><small>Folders included in library scans</small></div>
                <div className="directory-list">
                  {(engine.searchdir as string[]).map((path) => (
                    <div key={path}><code>{path}</code><button className="text-button danger" onClick={() => updateEngine('searchdir', (engine.searchdir as string[]).filter((item) => item !== path))}>Remove</button></div>
                  ))}
                  <button className="secondary-button" onClick={addDirectory}>Add directory</button>
                </div>
              </div>
              <Toggle label="Rescan library at startup" checked={Boolean(engine.library_autoscan)} onChange={(value) => updateEngine('library_autoscan', value)} />
              <Toggle label="Scan through the whole list" checked={Boolean(engine.scan_whole_list)} onChange={(value) => updateEngine('scan_whole_list', value)} />
              <Toggle label="Use subdirectory names when matching" checked={Boolean(engine.library_full_path)} onChange={(value) => updateEngine('library_full_path', value)} />
            </SettingsGroup>
          )}

          {active === 'sync' && (
            <SettingsGroup title="Synchronization" description="Set when Trackma retrieves and uploads list changes." icon={Download}>
              <SelectField label="Retrieve at startup" value={String(engine.autoretrieve)} onChange={(value) => updateEngine('autoretrieve', value)} options={[["off", "Disabled"], ["always", "Always"], ["days", "After a number of days"]]} />
              <NumberField label="Retrieve interval" suffix="days" value={Number(engine.autoretrieve_days)} min={1} onChange={(value) => updateEngine('autoretrieve_days', value)} />
              <SelectField label="Upload changes" value={String(engine.autosend)} onChange={(value) => updateEngine('autosend', value)} options={[["off", "Manually"], ["always", "After every change"], ["minutes", "After a delay"], ["size", "At queue size"]]} />
              <NumberField label="Upload delay" suffix="minutes" value={Number(engine.autosend_minutes)} min={1} onChange={(value) => updateEngine('autosend_minutes', value)} />
              <NumberField label="Queue threshold" suffix="items" value={Number(engine.autosend_size)} min={2} onChange={(value) => updateEngine('autosend_size', value)} />
              <Toggle label="Upload pending changes when quitting" checked={Boolean(engine.autosend_at_exit)} onChange={(value) => updateEngine('autosend_at_exit', value)} />
              <Toggle label="Change status automatically" checked={Boolean(engine.auto_status_change)} onChange={(value) => updateEngine('auto_status_change', value)} />
              <Toggle label="Set start and finish dates automatically" checked={Boolean(engine.auto_date_change)} onChange={(value) => updateEngine('auto_date_change', value)} />
            </SettingsGroup>
          )}

          {active === 'torrents' && (
            <SettingsGroup title="Torrent search" description="Connect Nyaa results to qBittorrent." icon={Server}>
              <Toggle label="Enable qBittorrent" checked={Boolean(engine.qbittorrent_enabled)} onChange={(value) => updateEngine('qbittorrent_enabled', value)} />
              <TextField label="Host" value={String(engine.qbittorrent_host)} onChange={(value) => updateEngine('qbittorrent_host', value)} />
              <NumberField label="Port" value={Number(engine.qbittorrent_port)} min={1} max={65535} onChange={(value) => updateEngine('qbittorrent_port', value)} />
              <TextField label="Username" value={String(engine.qbittorrent_user)} onChange={(value) => updateEngine('qbittorrent_user', value)} />
              <TextField label="Password" type="password" value={String(engine.qbittorrent_pass)} onChange={(value) => updateEngine('qbittorrent_pass', value)} />
              <TextField label="Default Nyaa category" value={String(engine.nyaa_category)} onChange={(value) => updateEngine('nyaa_category', value)} />
            </SettingsGroup>
          )}

          {active === 'interface' && (
            <SettingsGroup title="Desktop behavior" description="Control the native Trackma window and notifications." icon={Bell}>
              <Toggle label="Show tray icon" checked={Boolean(windowSettings.show_tray)} onChange={(value) => updateWindow('show_tray', value)} />
              <Toggle label="Close to tray" checked={Boolean(windowSettings.close_to_tray)} onChange={(value) => updateWindow('close_to_tray', value)} />
              <Toggle label="Start minimized to tray" checked={Boolean(windowSettings.start_in_tray)} onChange={(value) => updateWindow('start_in_tray', value)} />
              <Toggle label="Show tracker notifications" checked={Boolean(windowSettings.notifications)} onChange={(value) => updateWindow('notifications', value)} />
              <Toggle label="Remember window position and size" checked={Boolean(windowSettings.remember_geometry)} onChange={(value) => updateWindow('remember_geometry', value)} />
            </SettingsGroup>
          )}

          {active === 'appearance' && (
            <SettingsGroup title="Appearance" description="Use the mock's visual language in dark, light, or system mode." icon={Palette}>
              <SelectField label="Theme" value={String(windowSettings.theme_mode)} onChange={(value) => updateWindow('theme_mode', value)} options={[["system", "Follow system"], ["dark", "Dark"], ["light", "Light"]]} />
              <SelectField label="Default library view" value={String(windowSettings.view_mode)} onChange={(value) => updateWindow('view_mode', value)} options={[["grid", "Cover grid"], ["table", "Compact table"]]} />
            </SettingsGroup>
          )}
        </div>
      </div>
    </section>
  );
}


function SettingsGroup({ title, description, icon: Icon, children }: { title: string; description: string; icon: typeof Radio; children: React.ReactNode }) {
  return <section className="settings-group"><header><span><Icon aria-hidden="true" /></span><div><h2>{title}</h2><p>{description}</p></div></header><div className="settings-rows">{children}</div></section>;
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange(value: boolean): void }) {
  return <label className="setting-row toggle-row"><span><strong>{label}</strong></span><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} /></label>;
}

function TextField({ label, value, onChange, type = 'text' }: { label: string; value: string; onChange(value: string): void; type?: string }) {
  return <label className="setting-row"><span><strong>{label}</strong></span><input type={type} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function NumberField({ label, value, onChange, min, max, suffix }: { label: string; value: number; onChange(value: number): void; min?: number; max?: number; suffix?: string }) {
  return <label className="setting-row"><span><strong>{label}</strong></span><span className="number-input"><input type="number" value={value} min={min} max={max} onChange={(event) => onChange(Number(event.target.value))} />{suffix && <small>{suffix}</small>}</span></label>;
}

function SelectField({ label, value, onChange, options }: { label: string; value: string; onChange(value: string): void; options: string[][] }) {
  return <label className="setting-row"><span><strong>{label}</strong></span><select value={value} onChange={(event) => onChange(event.target.value)}>{options.map(([optionValue, text]) => <option key={optionValue} value={optionValue}>{text}</option>)}</select></label>;
}
