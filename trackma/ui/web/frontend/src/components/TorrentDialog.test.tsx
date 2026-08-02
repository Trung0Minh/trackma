import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { AppBridge } from '../bridge';
import { TorrentDialog } from './TorrentDialog';


describe('TorrentDialog', () => {
  it('opens with English subtitles and supports filtering, information, and download', async () => {
    const user = userEvent.setup();
    const call = vi.fn(async (command: string, _payload?: Record<string, unknown>) => {
      if (command === 'torrents.search') {
        return {
          results: [{
            id: 'https://nyaa.si/view/1',
            title: '[Group] Frieren - 01 [1080p]',
            link: 'magnet:?xt=urn:btih:test',
            size: '1.2 GiB',
            seeders: '120',
            leechers: '4',
            completed: '900',
            published: '2026-08-02',
          }],
          hasNext: true,
        };
      }
      if (command === 'torrents.details') return '## Release notes\n\n![Release preview](https://example.com/preview.jpg)\n\n**Video Resolution:** 1920x1080\n\n```text\nRelease file.mkv\n```';
      if (command === 'torrents.download') return { downloaded: true };
      if (command === 'library.scan') return {};
      return {};
    });
    const bridge: AppBridge = {
      call: <T,>(command: string, payload?: Record<string, unknown>) => call(command, payload) as Promise<T>,
      subscribe: () => () => undefined,
    };
    const onDownloaded = vi.fn(async () => undefined);

    render(
      <TorrentDialog
        bridge={bridge}
        title="Frieren"
        onClose={vi.fn()}
        onDownloaded={onDownloaded}
        onMessage={vi.fn()}
      />,
    );

    expect(screen.getByRole('dialog', { name: 'Find a release' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Category' })).toHaveValue('1_2');
    expect(await screen.findByText('[Group] Frieren - 01 [1080p]')).toBeInTheDocument();
    expect(call).toHaveBeenCalledWith('torrents.search', { query: 'Frieren', category: '1_2', page: 1 });

    await user.selectOptions(screen.getByRole('combobox', { name: 'Category' }), '1_4');
    await waitFor(() => expect(call).toHaveBeenCalledWith('torrents.search', { query: 'Frieren', category: '1_4', page: 1 }));

    await user.click(screen.getByRole('button', { name: 'Torrent information for [Group] Frieren - 01 [1080p]' }));
    expect(await screen.findByRole('heading', { name: 'Release notes' })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Release preview' })).toBeInTheDocument();
    expect(screen.getByText('Video Resolution:').tagName).toBe('STRONG');
    expect(screen.getByText('Release file.mkv').tagName).toBe('CODE');
    await user.click(screen.getByRole('button', { name: 'Close torrent information' }));

    const next = screen.getByRole('button', { name: 'Next' });
    expect(next).toBeEnabled();
    await user.click(next);
    await waitFor(() => expect(call).toHaveBeenCalledWith('torrents.search', { query: 'Frieren', category: '1_4', page: 2 }));
    expect(screen.getByRole('button', { name: 'Previous' })).toBeEnabled();

    await user.click(screen.getByRole('row', { name: /Frieren - 01/ }));
    await user.click(screen.getByRole('button', { name: 'Download selected torrent' }));
    await waitFor(() => expect(call).toHaveBeenCalledWith('torrents.download', { magnet: 'magnet:?xt=urn:btih:test' }));
    expect(call).toHaveBeenCalledWith('library.scan', { rescan: false });
    expect(onDownloaded).toHaveBeenCalled();
  });
});
