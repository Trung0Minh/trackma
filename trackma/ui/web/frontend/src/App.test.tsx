import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import App from './App';
import { MockBridge } from './mockBridge';


describe('App', () => {
  it('opens the remembered account and uses the simplified navigation', async () => {
    const user = userEvent.setup();
    render(<App bridge={new MockBridge()} />);

    expect(await screen.findByRole('heading', { name: 'My library' })).toBeInTheDocument();
    const header = screen.getByRole('banner', { name: 'Application header' });
    expect(header).toContainElement(screen.getByRole('navigation', { name: 'Primary navigation' }));
    expect(header).toContainElement(screen.getByRole('button', { name: 'Manage accounts' }));
    expect(header).toContainElement(screen.getByText('Engine connected'));
    expect(screen.queryByText('Home')).not.toBeInTheDocument();
    expect(screen.queryByText('Progress')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Discover' }));
    expect(await screen.findByRole('heading', { name: 'Find something worth your time' })).toBeInTheDocument();
  });

  it('allows an existing account to be edited from the account menu', async () => {
    const user = userEvent.setup();
    render(<App bridge={new MockBridge()} />);

    await screen.findByRole('heading', { name: 'My library' });
    await user.click(screen.getByRole('button', { name: 'Manage accounts' }));
    await user.click(screen.getByRole('button', { name: 'Edit minh' }));

    expect(screen.getByRole('heading', { name: 'Edit account' })).toBeInTheDocument();
    expect(screen.getByLabelText('Profile name')).toHaveValue('minh');
  });

  it('asks before applying a tracker progress update', async () => {
    const bridge = new MockBridge();
    render(<App bridge={bridge} />);
    await screen.findByRole('heading', { name: 'My library' });

    act(() => bridge.emit('prompt_for_update', [{ id: 140960, title: 'Spy x Family' }, 23]));

    expect(screen.getByRole('dialog', { name: 'Update progress?' })).toBeInTheDocument();
    expect(screen.getByText('Set Spy x Family to episode 23?')).toBeInTheDocument();
  });
});
