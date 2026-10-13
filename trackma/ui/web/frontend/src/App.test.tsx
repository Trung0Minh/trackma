import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

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
    expect(screen.queryByText('Engine connected')).not.toBeInTheDocument();
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

  it('stacks watched episodes per show and sends every episode in order', async () => {
    const user = userEvent.setup();
    const bridge = new MockBridge();
    const call = vi.spyOn(bridge, 'call');
    render(<App bridge={bridge} />);
    await screen.findByRole('heading', { name: 'My library' });

    act(() => {
      bridge.emit('prompt_for_update', [{ id: 140960, title: 'Spy x Family' }, 23]);
      bridge.emit('prompt_for_update', [{ id: 140960, title: 'Spy x Family' }, 24]);
      bridge.emit('prompt_for_update', [{ id: 127230, title: 'Chainsaw Man' }, 9]);
      bridge.emit('prompt_for_update', [{ id: 140960, title: 'Spy x Family' }, 23]);
    });
    expect(screen.getAllByRole('dialog')).toHaveLength(1);
    expect(screen.getByText('Mark Spy x Family episodes 23–24 as watched?')).toBeInTheDocument();
    expect(screen.getByText('Set Chainsaw Man to episode 9?')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Update progress' }));

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(call.mock.calls.filter(([method]) => method === 'tracker.update')).toEqual([
      ['tracker.update', { showId: 140960, episode: 23 }],
      ['tracker.update', { showId: 140960, episode: 24 }],
      ['tracker.update', { showId: 127230, episode: 9 }],
    ]);
  });

  it('keeps newer episodes received while an update is being saved', async () => {
    const user = userEvent.setup();
    const bridge = new MockBridge();
    render(<App bridge={bridge} />);
    await screen.findByRole('heading', { name: 'My library' });
    let finishSave!: (value: unknown) => void;
    const save = new Promise<unknown>((resolve) => { finishSave = resolve; });
    vi.spyOn(bridge, 'call').mockImplementationOnce(() => save);
    act(() => bridge.emit('prompt_for_update', [{ id: 140960, title: 'Spy x Family' }, 23]));
    await user.click(screen.getByRole('button', { name: 'Update progress' }));
    act(() => bridge.emit('prompt_for_update', [{ id: 140960, title: 'Spy x Family' }, 24]));
    await act(async () => finishSave({}));
    expect(screen.getByText('Set Spy x Family to episode 24?')).toBeInTheDocument();
  });

  it('keeps a failed update available to retry', async () => {
    const user = userEvent.setup();
    const bridge = new MockBridge();
    render(<App bridge={bridge} />);
    await screen.findByRole('heading', { name: 'My library' });
    vi.spyOn(bridge, 'call').mockRejectedValueOnce(new Error('Save failed'));
    act(() => bridge.emit('prompt_for_update', [{ id: 140960, title: 'Spy x Family' }, 23]));
    await user.click(screen.getByRole('button', { name: 'Update progress' }));
    expect(await screen.findByText('Save failed')).toBeInTheDocument();
    expect(screen.getByText('Set Spy x Family to episode 23?')).toBeInTheDocument();
  });

  it('retries only the remaining episodes after a partially successful batch', async () => {
    const user = userEvent.setup();
    const bridge = new MockBridge();
    render(<App bridge={bridge} />);
    await screen.findByRole('heading', { name: 'My library' });
    const originalCall = bridge.call.bind(bridge);
    let fail = true;
    const call = vi.spyOn(bridge, 'call').mockImplementation((command, payload) => {
      if (command === 'tracker.update' && payload?.episode === 24 && fail) {
        return Promise.reject(new Error('Send failed'));
      }
      return originalCall(command, payload);
    });
    act(() => {
      for (const episode of [23, 24, 25]) {
        bridge.emit('prompt_for_update', [{ id: 140960, title: 'Spy x Family' }, episode]);
      }
    });
    await user.click(screen.getByRole('button', { name: 'Update progress' }));
    expect(await screen.findByText('Send failed')).toBeInTheDocument();
    expect(screen.getByText('Mark Spy x Family episodes 24–25 as watched?')).toBeInTheDocument();
    fail = false;
    await user.click(screen.getByRole('button', { name: 'Update progress' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(call.mock.calls.filter(([command]) => command === 'tracker.update').map(([, payload]) => payload?.episode)).toEqual([23, 24, 24, 25]);
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
