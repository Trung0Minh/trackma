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
    expect(header).not.toContainElement(screen.getByText('Engine connected'));
    expect(screen.getByRole('status')).toHaveTextContent('Engine connected');
    expect(screen.queryByText('Home')).not.toBeInTheDocument();
    expect(screen.queryByText('Progress')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Discover' }));
    expect(await screen.findByRole('heading', { name: 'Browse anime' })).toBeInTheDocument();
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

  it('shows live tracker countdown state', async () => {
    const bridge = new MockBridge();
    render(<App bridge={bridge} />);
    await screen.findByRole('heading', { name: 'My library' });

    act(() => bridge.emit('tracker_state', { state: 'Playing', timer: 37, show: [{ title: 'Spy x Family' }, 23] }));

    const countdown = screen.getByRole('status', { name: 'Playback update countdown' });
    expect(countdown).toHaveTextContent('Spy x Family · Episode 23');
    expect(countdown).toHaveTextContent('Update prompt in 37s');
  });

  it('shows warning messages as danger toasts', async () => {
    const bridge = new MockBridge();
    render(<App bridge={bridge} />);
    await screen.findByRole('heading', { name: 'My library' });

    act(() => bridge.emit('message', { level: 5, message: 'Episode not found' }));

    const toast = screen.getByRole('alert');
    expect(toast).toHaveTextContent('Episode not found');
    expect(toast).toHaveClass('danger');
  });
});
