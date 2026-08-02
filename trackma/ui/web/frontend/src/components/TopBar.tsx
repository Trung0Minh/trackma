import { Compass, Library, Play, Settings, UserRound } from 'lucide-react';

import type { Account } from '../types';


export type PageName = 'library' | 'discover' | 'settings';

interface TopBarProps {
  activePage: PageName;
  account: Account;
  mediaType: string;
  supportedMediaTypes: string[];
  queueCount: number;
  onNavigate(page: PageName): void;
  onAccounts(): void;
  onMediaTypeChange(mediaType: string): void;
}


export function TopBar({
  activePage,
  account,
  mediaType,
  supportedMediaTypes,
  queueCount,
  onNavigate,
  onAccounts,
  onMediaTypeChange,
}: TopBarProps) {
  return (
    <header className="topbar" aria-label="Application header">
      <div className="brand-lockup">
        <span className="brand-mark"><Play fill="currentColor" aria-hidden="true" /></span>
        <span>Trackma</span>
      </div>

      <nav aria-label="Primary navigation">
        <button
          className={activePage === 'library' ? 'nav-item active' : 'nav-item'}
          aria-label="Library"
          aria-current={activePage === 'library' ? 'page' : undefined}
          onClick={() => onNavigate('library')}
        >
          <Library aria-hidden="true" />
          <span>Library</span>
          {queueCount > 0 && <span className="nav-count" aria-label={`${queueCount} pending changes`}>{queueCount}</span>}
        </button>
        <button
          className={activePage === 'discover' ? 'nav-item active' : 'nav-item'}
          aria-label="Discover"
          aria-current={activePage === 'discover' ? 'page' : undefined}
          onClick={() => onNavigate('discover')}
        >
          <Compass aria-hidden="true" />
          <span>Discover</span>
        </button>
        <button
          className={activePage === 'settings' ? 'nav-item active' : 'nav-item'}
          aria-label="Settings"
          aria-current={activePage === 'settings' ? 'page' : undefined}
          onClick={() => onNavigate('settings')}
        >
          <Settings aria-hidden="true" />
          <span>Settings</span>
        </button>
      </nav>

      <div className="topbar-tools">
        {supportedMediaTypes.length > 1 && (
          <label className="media-switcher">
            <select aria-label="Media type" value={mediaType} onChange={(event) => onMediaTypeChange(event.target.value)}>
              {supportedMediaTypes.map((value) => <option key={value}>{value}</option>)}
            </select>
          </label>
        )}
        <button className="account-chip" aria-label="Manage accounts" onClick={onAccounts}>
          <span className="account-avatar"><UserRound aria-hidden="true" /></span>
          <span className="account-copy">
            <strong>{account.username}</strong>
            <small>{account.serviceName} · {mediaType}</small>
          </span>
          <span className="account-more" aria-hidden="true">•••</span>
        </button>
      </div>
    </header>
  );
}
