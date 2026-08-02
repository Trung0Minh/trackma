import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { LibraryPage } from './LibraryPage';
import type { SessionSnapshot } from '../types';


const session: SessionSnapshot = {
  account: { id: 1, username: 'mina', api: 'anilist', serviceName: 'AniList' },
  api: {
    name: 'AniList',
    shortname: 'anilist',
    mediatype: 'anime',
    supported_mediatypes: ['anime'],
  },
  media: {
    statusOptions: [
      { value: 'CURRENT', label: 'Watching' },
      { value: 'COMPLETED', label: 'Completed' },
    ],
    searchMethods: ['keyword'],
    score_max: 10,
    score_step: 1,
    can_play: true,
  },
  library: {
    queueCount: 1,
    tracker: { state: 2, timer: 42, show: [{ title: 'Frieren' }, 13] },
    alternateTitles: {},
    shows: [
      {
        id: 1,
        title: 'Frieren',
        url: 'https://anilist.co/anime/154587/Frieren-Beyond-Journeys-End/',
        total: 28,
        my_progress: 12,
        my_score: 9,
        my_status: 'CURRENT',
        airedEpisodes: 20,
        availableEpisodes: [1, 15],
      },
      {
        id: 2,
        title: 'Pluto',
        total: 8,
        my_progress: 8,
        my_score: 8,
        my_status: 'COMPLETED',
      },
    ],
  },
};


describe('LibraryPage', () => {
  it('filters by service-derived status and title search', async () => {
    const user = userEvent.setup();
    render(
      <LibraryPage
        session={session}
        viewMode="grid"
        onViewModeChange={vi.fn()}
        onSelect={vi.fn()}
        onCommand={vi.fn()}
      />,
    );

    expect(screen.getByRole('tab', { name: 'Watching 1' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('Update prompt in 42s')).toBeInTheDocument();
    expect(screen.getByText('Frieren')).toBeInTheDocument();
    expect(screen.queryByText('Pluto')).not.toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'Completed 1' }));
    expect(screen.queryByText('Frieren')).not.toBeInTheDocument();
    expect(screen.getByText('Pluto')).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'All 2' }));
    await user.type(screen.getByRole('searchbox', { name: 'Search library' }), 'fri');
    expect(screen.getByText('Frieren')).toBeInTheDocument();
    expect(screen.queryByText('Pluto')).not.toBeInTheDocument();
  });

  it('opens the show AniList page from the card action', async () => {
    const user = userEvent.setup();
    const onCommand = vi.fn();
    render(
      <LibraryPage
        session={session}
        viewMode="grid"
        onViewModeChange={vi.fn()}
        onSelect={vi.fn()}
        onCommand={onCommand}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Open Frieren on AniList' }));

    expect(onCommand).toHaveBeenCalledWith('openExternal', session.library.shows[0]);
  });

  it('shows the numeric backend no-video state without treating a null timer as active', () => {
    render(
      <LibraryPage
        session={{ ...session, library: { ...session.library, tracker: { state: 1, timer: null } } }}
        viewMode="grid"
        onViewModeChange={vi.fn()}
        onSelect={vi.fn()}
        onCommand={vi.fn()}
      />,
    );

    expect(screen.getByText('No video detected')).toBeInTheDocument();
  });

  it('shows watched, aired, and downloaded episodes on one progress bar', () => {
    render(
      <LibraryPage
        session={session}
        viewMode="grid"
        onViewModeChange={vi.fn()}
        onSelect={vi.fn()}
        onCommand={vi.fn()}
      />,
    );

    const progress = screen.getByLabelText('Frieren episode progress: 12 watched, 20 aired, 2 downloaded, 28 total');
    expect(progress.querySelector('.aired-progress')).toHaveStyle({ width: '71.42857142857143%' });
    expect(progress.querySelector('.watched-progress')).toHaveStyle({ width: '42.857142857142854%' });
    expect(progress.querySelectorAll('.local-episode-progress')).toHaveLength(2);
  });
});
