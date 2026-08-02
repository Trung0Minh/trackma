import { useState } from 'react';
import { DatabaseZap, ExternalLink, LogIn, Pencil, Plus, Trash2, UserRound, X } from 'lucide-react';

import type { AppBridge } from '../bridge';
import type { Account, Bootstrap, Service } from '../types';


interface AccountPanelProps {
  bridge: AppBridge;
  bootstrap: Bootstrap;
  modal?: boolean;
  onClose?(): void;
  onSelect(accountId: number, remember: boolean): Promise<void>;
  onBootstrap(value: Bootstrap): void;
  onMessage(message: string): void;
}


export function AccountPanel({ bridge, bootstrap, modal, onClose, onSelect, onBootstrap, onMessage }: AccountPanelProps) {
  const [adding, setAdding] = useState(bootstrap.accounts.length === 0);
  const [remember, setRemember] = useState(bootstrap.defaultAccountId !== null);
  const [service, setService] = useState<Service>(bootstrap.services[0]);
  const [username, setUsername] = useState('');
  const [secret, setSecret] = useState('');
  const [authSessionId, setAuthSessionId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [confirmAction, setConfirmAction] = useState<{ accountId: number; type: 'delete' | 'purge' } | null>(null);

  function closeForm() {
    setAdding(false);
    setEditing(null);
    setUsername('');
    setSecret('');
    setAuthSessionId(null);
  }

  function editAccount(account: Account) {
    setEditing(account);
    setService(bootstrap.services.find((item) => item.api === account.api) ?? bootstrap.services[0]);
    setUsername(account.username);
    setSecret('');
    setAuthSessionId(null);
    setAdding(true);
  }

  async function beginAuth() {
    const auth = await bridge.call<{ authSessionId: string | null; url: string | null }>('accounts.beginAuth', { api: service.api });
    setAuthSessionId(auth.authSessionId);
    if (auth.url) await bridge.call('native.openExternal', { url: auth.url });
  }

  async function saveAccount(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const result = await bridge.call<Bootstrap>('accounts.save', {
        accountId: editing?.id,
        username,
        secret,
        api: service.api,
        authSessionId,
      });
      onBootstrap(result);
      closeForm();
      onMessage(editing ? 'Account updated' : 'Account added');
    } finally {
      setBusy(false);
    }
  }

  async function removeAccount(accountId: number) {
    const result = await bridge.call<Bootstrap>('accounts.delete', { accountId });
    onBootstrap(result);
    setConfirmAction(null);
    onMessage('Account removed');
  }

  async function purgeAccount(accountId: number) {
    await bridge.call('accounts.purge', { accountId });
    setConfirmAction(null);
    onMessage('Local account data cleared');
  }

  const body = (
    <section className={modal ? 'account-panel modal-panel' : 'account-panel account-gate'} aria-labelledby="account-title">
      <header>
        <div><h1 id="account-title">Choose an account</h1><p>Trackma keeps each service and media library separate.</p></div>
        {modal && <button className="icon-button" onClick={onClose} aria-label="Close accounts"><X /></button>}
      </header>

      {!adding && <div className="account-list">
        {bootstrap.accounts.map((account) => (
          <article key={account.id} className="account-card">
            <span className="account-avatar large"><UserRound /></span>
            <div className="account-card-copy"><strong>{account.username}</strong><small>{account.serviceName}</small></div>
            <button className="primary-button" onClick={() => onSelect(account.id, remember)} disabled={busy}><LogIn /> Open</button>
            {confirmAction?.accountId === account.id ? (
              <div className="account-delete-confirm">
                <button className="danger-button" onClick={() => confirmAction.type === 'delete' ? removeAccount(account.id) : purgeAccount(account.id)}>Confirm {confirmAction.type}</button>
                <button className="text-button" onClick={() => setConfirmAction(null)}>Cancel</button>
              </div>
            ) : (
              <div className="account-actions">
                <button className="icon-button compact" onClick={() => editAccount(account)} aria-label={`Edit ${account.username}`}><Pencil /></button>
                <button className="icon-button compact" onClick={() => setConfirmAction({ accountId: account.id, type: 'purge' })} aria-label={`Clear local data for ${account.username}`}><DatabaseZap /></button>
                <button className="icon-button compact danger" onClick={() => setConfirmAction({ accountId: account.id, type: 'delete' })} aria-label={`Delete ${account.username}`}><Trash2 /></button>
              </div>
            )}
          </article>
        ))}
        <label className="remember-account"><input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} /> Remember the selected account</label>
        <button className="secondary-button add-account-button" onClick={() => setAdding(true)}><Plus /> Connect another service</button>
      </div>}

      {adding && <form className="account-form" onSubmit={saveAccount}>
        {editing && <h2>Edit account</h2>}
        <label>Service<select value={service.api} onChange={(event) => setService(bootstrap.services.find((item) => item.api === event.target.value) ?? bootstrap.services[0])}>{bootstrap.services.map((item) => <option key={item.api} value={item.api}>{item.name}</option>)}</select></label>
        <label>{service.requiresExternalAuth ? 'Profile name' : 'Username'}<input value={username} onChange={(event) => setUsername(event.target.value)} required /></label>
        {service.requiresExternalAuth && <button type="button" className="secondary-button auth-button" onClick={beginAuth}><ExternalLink /> Open authorization page</button>}
        <label>{service.requiresExternalAuth ? 'PIN or authorization code' : 'Password'}<input type={service.requiresExternalAuth ? 'text' : 'password'} value={secret} onChange={(event) => setSecret(event.target.value)} required /></label>
        <div className="form-actions"><button className="primary-button" disabled={busy}>{busy ? 'Saving' : editing ? 'Update account' : 'Save account'}</button>{bootstrap.accounts.length > 0 && <button type="button" className="text-button" onClick={closeForm}>Cancel</button>}</div>
      </form>}
    </section>
  );

  return modal ? <div className="modal-layer"><button className="modal-scrim" aria-label="Close accounts" onClick={onClose} />{body}</div> : <main className="account-screen"><div className="account-atmosphere" />{body}</main>;
}
