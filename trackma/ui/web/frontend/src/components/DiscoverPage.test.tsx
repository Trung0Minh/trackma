import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { MockBridge } from '../mockBridge';
import type { MediaShow, SessionSnapshot, StatusValue } from '../types';
import { DiscoverPage } from './DiscoverPage';


const session: SessionSnapshot = {
  account: { id: 1, username: 'mina', api: 'anilist', serviceName: 'AniList' },
  api: {
    name: 'AniList',
    shortname: 'anilist',
    mediatype: 'anime',
    supported_mediatypes: ['anime', 'manga'],
  },
  media: {
    statusOptions: [
      { value: 'CURRENT', label: 'Watching' },
      { value: 'PLANNING', label: 'Plan to watch' },
    ],
    searchMethods: ['keyword', 'season'],
    score_max: 100,
    score_step: 1,
    can_add: true,
  },
  library: {
    queueCount: 0,
    tracker: null,
    alternateTitles: {},
    shows: [],
  },
};


function renderDiscover(onAdd = vi.fn(async (_show: MediaShow, _status: StatusValue) => undefined)) {
  render(
    <DiscoverPage
      bridge={new MockBridge()}
      session={session}
      onAdd={onAdd}
    />,
  );
  return onAdd;
}


describe('DiscoverPage', () => {
  it('loads AniList-style filters and browse collections', async () => {
    renderDiscover();

    expect(await screen.findByRole('heading', { name: 'Trending now' })).toBeInTheDocument();
    expect(screen.getByRole('searchbox', { name: 'Search catalog' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Genres & Tags' })).toBeInTheDocument();
    expect(screen.getByLabelText('Year')).toBeInTheDocument();
    expect(screen.getByLabelText('Season')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Popular this season' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Top 100 anime' })).toBeInTheDocument();
  });

  it('switches to search results after a debounced query', async () => {
    const user = userEvent.setup();
    renderDiscover();
    await screen.findByRole('heading', { name: 'Trending now' });

    await user.type(screen.getByRole('searchbox', { name: 'Search catalog' }), 'Spy');

    expect(await screen.findByRole('heading', { name: 'Search results' })).toBeInTheDocument();
    expect(await screen.findByText('Spy x Family')).toBeInTheDocument();
  });

  it('opens details and adds a title with a selected status', async () => {
    const user = userEvent.setup();
    const onAdd = renderDiscover();
    await screen.findByRole('heading', { name: 'Trending now' });

    await user.click(screen.getAllByRole('button', { name: /Open details for/ })[0]);
    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('Adventure');
    expect(dialog.closest('.discover-page')).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Close catalog details' }));

    const addButton = screen.getAllByRole('button', { name: /Add .* to list/ })[0];
    await user.click(addButton);
    await user.click(screen.getByRole('menuitem', { name: 'Plan to watch' }));

    await waitFor(() => expect(onAdd).toHaveBeenCalled());
    expect(screen.getAllByRole('button', { name: /is in list/ })[0]).toBeDisabled();
  });

  it('opens advanced filters and resets active selections', async () => {
    const user = userEvent.setup();
    renderDiscover();
    await screen.findByRole('heading', { name: 'Trending now' });

    await user.click(screen.getByRole('button', { name: 'More filters' }));
    expect(screen.getByRole('region', { name: 'Advanced filters' })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Sort'), 'score');
    await user.click(screen.getByRole('button', { name: 'Reset all filters' }));

    expect(screen.getByLabelText('Sort')).toHaveValue('popularity');
  });
});
