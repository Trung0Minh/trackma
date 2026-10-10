import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { AppBridge } from '../bridge';
import type { MediaShow, SessionSnapshot } from '../types';
import { MediaDrawer } from './MediaDrawer';


const show: MediaShow = {
  id: 154587,
  title: 'Frieren',
  url: 'https://anilist.co/anime/154587/Frieren-Beyond-Journeys-End/',
  total: 28,
  my_progress: 12,
  my_score: 9,
  my_status: 'CURRENT',
};

const session: SessionSnapshot = {
  account: { id: 1, username: 'mina', api: 'anilist', serviceName: 'AniList' },
  api: {
    name: 'AniList',
    shortname: 'anilist',
    mediatype: 'anime',
    supported_mediatypes: ['anime'],
  },
  media: {
    statusOptions: [{ value: 'CURRENT', label: 'Watching' }],
    searchMethods: ['keyword'],
    score_max: 10,
    score_step: 1,
    can_play: true,
    can_delete: true,
  },
  library: {
    queueCount: 0,
    tracker: null,
    alternateTitles: {},
    shows: [show],
  },
};


describe('MediaDrawer', () => {
  it('opens the exact Keyframe staff-list page next to the AniList shortcut', async () => {
    const user = userEvent.setup();
    const call = vi.fn(async (command: string, _payload?: Record<string, unknown>) => {
      if (command === 'show.details') return { show, details: {} };
      if (command === 'keyframe.staffList') {
        return { url: 'https://keyframe-staff-list.com/staff/sousou-no-frieren' };
      }
      return {};
    });
    const bridge: AppBridge = {
      call: <T,>(command: string, payload?: Record<string, unknown>) => call(command, payload) as Promise<T>,
      subscribe: () => () => undefined,
    };

    render(
      <MediaDrawer
        bridge={bridge}
        session={session}
        show={show}
        onClose={vi.fn()}
        onChanged={vi.fn(async () => undefined)}
        onMessage={vi.fn()}
      />,
    );

    const shortcuts = screen.getByLabelText('Title shortcuts');
    const aniListButton = screen.getByRole('button', { name: 'Open Frieren on AniList' });
    const keyframeButton = screen.getByRole('button', { name: 'Open Frieren on Keyframe Staff List' });
    expect(Array.from(shortcuts.querySelectorAll('button'))).toEqual([
      aniListButton,
      keyframeButton,
      screen.getByRole('button', { name: 'Remove Frieren' }),
    ]);

    await user.click(keyframeButton);

    await waitFor(() => {
      expect(call).toHaveBeenCalledWith('keyframe.staffList', { anilistId: 154587 });
      expect(call).toHaveBeenCalledWith('native.openExternal', {
        url: 'https://keyframe-staff-list.com/staff/sousou-no-frieren',
      });
    });
  });

  it('falls back to the Keyframe staff-list search when exact lookup fails', async () => {
    const user = userEvent.setup();
    const call = vi.fn(async (command: string, _payload?: Record<string, unknown>) => {
      if (command === 'show.details') return { show, details: {} };
      if (command === 'keyframe.staffList') throw new Error('Keyframe Staff List lookup failed');
      return {};
    });
    const bridge: AppBridge = {
      call: <T,>(command: string, payload?: Record<string, unknown>) => call(command, payload) as Promise<T>,
      subscribe: () => () => undefined,
    };
    const onMessage = vi.fn();

    render(
      <MediaDrawer
        bridge={bridge}
        session={session}
        show={show}
        onClose={vi.fn()}
        onChanged={vi.fn(async () => undefined)}
        onMessage={onMessage}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Open Frieren on Keyframe Staff List' }));

    await waitFor(() => {
      expect(call).toHaveBeenCalledWith('native.openExternal', {
        url: 'https://keyframe-staff-list.com/search?q=Frieren',
      });
    });
    expect(onMessage).not.toHaveBeenCalled();
  });
});
