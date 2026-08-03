import { BridgeError, type AppBridge, type BridgeEvent } from './bridge';
import type {
  Account,
  Bootstrap,
  CatalogMetadata,
  DiscoverItem,
  LibrarySnapshot,
  MediaShow,
  Service,
  SessionSnapshot,
} from './types';


const services: Service[] = [
  { api: 'anilist', name: 'AniList', loginMode: 'oauth', requiresExternalAuth: true },
  { api: 'kitsu', name: 'Kitsu', loginMode: 'password', requiresExternalAuth: false },
  { api: 'mal', name: 'MyAnimeList', loginMode: 'oauthPkce', requiresExternalAuth: true },
];

const catalog: MediaShow[] = [
  {
    id: 131681,
    title: 'Demon Slayer: Entertainment District Arc',
    url: 'https://anilist.co/anime/131681/',
    image: 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx131681-s1L0v8D6q5pE.png',
    type: 'TV',
    total: 11,
    my_progress: 11,
    my_status: 'CURRENT',
    my_score: 9.2,
    availableEpisodes: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    airedEpisodes: 11,
  },
  {
    id: 140960,
    title: 'Spy x Family',
    url: 'https://anilist.co/anime/140960/',
    image: 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx140960-Yl5GLVvAMjtM.png',
    type: 'TV',
    total: 25,
    my_progress: 22,
    my_status: 'CURRENT',
    my_score: 8.8,
    availableEpisodes: Array.from({ length: 25 }, (_, index) => index + 1),
    airedEpisodes: 25,
  },
  {
    id: 104578,
    title: 'Attack on Titan: The Final Season',
    url: 'https://anilist.co/anime/104578/',
    image: 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx104578-LaZYFwmh9bQj.png',
    type: 'TV',
    total: 28,
    my_progress: 28,
    my_status: 'COMPLETED',
    my_score: 8.8,
    availableEpisodes: Array.from({ length: 28 }, (_, index) => index + 1),
    airedEpisodes: 28,
  },
  {
    id: 113415,
    title: 'Jujutsu Kaisen',
    url: 'https://anilist.co/anime/113415/',
    image: 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx113415-bbBWj4pEFseh.jpg',
    type: 'TV',
    total: 24,
    my_progress: 16,
    my_status: 'PAUSED',
    my_score: 9.2,
    availableEpisodes: Array.from({ length: 24 }, (_, index) => index + 1),
    airedEpisodes: 24,
  },
  {
    id: 127230,
    title: 'Chainsaw Man',
    url: 'https://anilist.co/anime/127230/',
    image: 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx127230-NuFDGkUAgFvG.png',
    type: 'TV',
    total: 12,
    my_progress: 8,
    my_status: 'CURRENT',
    my_score: 8.8,
    availableEpisodes: Array.from({ length: 12 }, (_, index) => index + 1),
    airedEpisodes: 12,
  },
  {
    id: 151807,
    title: 'Solo Leveling',
    url: 'https://anilist.co/anime/151807/',
    image: 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx151807-m1gX3iqITqoY.png',
    type: 'TV',
    total: 12,
    my_progress: 12,
    my_status: 'COMPLETED',
    my_score: 8.8,
    availableEpisodes: Array.from({ length: 12 }, (_, index) => index + 1),
    airedEpisodes: 12,
  },
];

const browseCatalog: MediaShow[] = [
  {
    id: 154587,
    title: 'Frieren: Beyond Journey’s End',
    url: 'https://anilist.co/anime/154587/',
    image: 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx154587-n1fmjRv4JQUd.jpg',
    type: 'TV',
    status: 'Finished',
    total: 28,
    my_progress: 0,
    my_status: 'PLANNING',
    my_score: 0,
  },
  {
    id: 166770,
    title: 'Delicious in Dungeon',
    url: 'https://anilist.co/anime/166770/',
    image: 'https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx166770-d4OtJg2I7H6T.jpg',
    type: 'TV',
    status: 'Finished',
    total: 24,
    my_progress: 0,
    my_status: 'PLANNING',
    my_score: 0,
  },
  ...catalog,
];

function catalogMetadata(show: MediaShow, rank?: number): CatalogMetadata {
  const finished = String(show.status ?? '').toLocaleLowerCase().includes('finished');
  return {
    titles: { userPreferred: show.title, romaji: show.title, english: show.title },
    description: show.title === 'Delicious in Dungeon'
      ? 'A stranded adventuring party cooks its way through a dangerous dungeon.'
      : 'A character-led journey through memory, friendship, and changing worlds.',
    genres: show.title === 'Delicious in Dungeon'
      ? ['Adventure', 'Comedy', 'Fantasy']
      : ['Adventure', 'Drama', 'Fantasy'],
    tags: [{ name: 'Found Family', rank: 86 }, { name: 'Travel', rank: 78 }],
    studios: ['Madhouse'],
    format: show.type ?? 'TV',
    status: finished ? 'FINISHED' : 'RELEASING',
    averageScore: show.my_score ? Math.round(show.my_score * 10) : 84,
    popularity: 175000,
    favourites: 21000,
    duration: 24,
    season: 'SUMMER',
    seasonYear: 2026,
    source: 'MANGA',
    countryOfOrigin: 'JP',
    nextAiringEpisode: finished ? null : { episode: Math.max(1, show.my_progress + 1), timeUntilAiring: 32000 },
    externalLinks: [{ site: 'Crunchyroll', url: 'https://www.crunchyroll.com/', type: 'STREAMING' }],
    coverColor: '#4ba7d8',
    rank,
  };
}


export class MockBridge implements AppBridge {
  private listeners = new Set<(event: BridgeEvent) => void>();
  private accounts: Account[] = [
    { id: 1, username: 'minh', api: 'anilist', serviceName: 'AniList' },
  ];
  private shows = catalog.map((show) => ({ ...show }));
  private engineSettings: Record<string, unknown> = {
    tracker_enabled: true,
    tracker_type: 'auto',
    tracker_interval: 10,
    tracker_update_wait_s: 120,
    tracker_update_prompt: false,
    tracker_not_found_prompt: false,
    tracker_ignore_not_next: true,
    player: 'mpv',
    searchdir: ['~/Videos'],
    library_autoscan: true,
    scan_whole_list: false,
    library_full_path: false,
    autoretrieve: 'days',
    autoretrieve_days: 3,
    autosend: 'always',
    autosend_minutes: 60,
    autosend_size: 5,
    autosend_at_exit: true,
    auto_status_change: true,
    auto_status_change_if_scored: true,
    auto_date_change: true,
    qbittorrent_enabled: false,
    qbittorrent_host: 'localhost',
    qbittorrent_port: 8080,
    qbittorrent_user: 'admin',
    qbittorrent_pass: '',
    nyaa_category: '1_0',
    nyaa_filter: '0',
  };
  private windowSettings: Record<string, unknown> = {
    show_tray: true,
    close_to_tray: true,
    start_in_tray: false,
    notifications: true,
    remember_geometry: true,
    theme_mode: 'dark',
    view_mode: 'grid',
  };

  async call<T = unknown>(command: string, payload: Record<string, unknown> = {}): Promise<T> {
    await new Promise((resolve) => window.setTimeout(resolve, 80));
    let result: unknown;
    switch (command) {
      case 'app.bootstrap':
        result = this.bootstrap();
        break;
      case 'session.open':
      case 'session.switchMediaType':
        result = this.session();
        break;
      case 'library.snapshot':
      case 'library.scan':
      case 'sync.download':
      case 'sync.upload':
        result = this.library();
        break;
      case 'show.details': {
        const show = this.show(payload.showId);
        result = {
          show,
          details: {
            synopsis: 'A quiet, character-led journey through memory, magic, and the passage of time.',
            genres: ['Adventure', 'Drama', 'Fantasy'],
            studios: ['Madhouse'],
          },
        };
        break;
      }
      case 'show.update': {
        const show = this.show(payload.showId);
        const patch = payload.patch as Record<string, unknown>;
        const fields: Record<string, keyof MediaShow> = {
          progress: 'my_progress',
          score: 'my_score',
          status: 'my_status',
          rewatches: 'my_rewatches',
          notes: 'my_notes',
          tags: 'my_tags',
          startDate: 'my_start_date',
          finishDate: 'my_finish_date',
        };
        Object.entries(patch).forEach(([key, value]) => {
          const field = fields[key];
          if (field) Object.assign(show, { [field]: value });
        });
        result = show;
        break;
      }
      case 'show.delete':
        this.shows = this.shows.filter((show) => String(show.id) !== String(payload.showId));
        result = this.library();
        break;
      case 'show.setAltTitle':
      case 'show.play':
      case 'show.playRandom':
      case 'show.openFolder':
        result = { launched: true, opened: true };
        break;
      case 'discover.search':
        result = catalog.filter((show) =>
          show.title.toLocaleLowerCase().includes(String(payload.query ?? '').toLocaleLowerCase()),
        );
        break;
      case 'discover.home': {
        const item = (show: MediaShow, rank?: number): DiscoverItem => ({
          show: { ...show },
          metadata: catalogMetadata(show, rank),
          inLibrary: this.shows.some((current) => String(current.id) === String(show.id)),
        });
        const six = browseCatalog.slice(0, 6);
        result = {
          capabilities: {
            mode: 'full',
            filters: ['search', 'genres', 'tags', 'year', 'season', 'formats', 'statuses', 'country', 'source', 'streaming', 'sort'],
            supportsHome: true,
            supportsAdvanced: true,
            supportsPagination: true,
          },
          sections: [
            { id: 'trending', title: 'Trending now', preset: { sort: 'trending' }, items: six.map((show) => item(show)) },
            { id: 'popular-season', title: 'Popular this season', preset: { season: 'SUMMER', year: 2026, sort: 'popularity' }, items: [...six].reverse().map((show) => item(show)) },
            { id: 'upcoming-season', title: 'Upcoming next season', preset: { season: 'FALL', year: 2026, sort: 'popularity' }, items: browseCatalog.slice(1, 7).map((show) => item(show)) },
            { id: 'popular', title: 'All time popular', preset: { sort: 'popularity' }, items: browseCatalog.slice(2, 8).map((show) => item(show)) },
            { id: 'top', title: 'Top 100 anime', preset: { sort: 'score' }, items: browseCatalog.slice(0, 8).map((show, index) => item(show, index + 1)) },
          ],
        };
        break;
      }
      case 'discover.options':
        result = {
          genres: ['Action', 'Adventure', 'Comedy', 'Drama', 'Fantasy', 'Romance', 'Sci-Fi'].map((value) => ({ value, label: value })),
          tags: ['Found Family', 'Travel', 'Magic', 'School', 'Female Protagonist'].map((value) => ({ value, label: value, group: 'Themes' })),
          formats: ['TV', 'TV_SHORT', 'MOVIE', 'SPECIAL', 'OVA', 'ONA'].map((value) => ({ value, label: value.replace('_', ' ') })),
          statuses: ['RELEASING', 'FINISHED', 'NOT_YET_RELEASED', 'CANCELLED'].map((value) => ({ value, label: value.replaceAll('_', ' ') })),
          countries: [{ value: 'JP', label: 'Japan' }, { value: 'KR', label: 'South Korea' }, { value: 'CN', label: 'China' }],
          sources: [{ value: 'ORIGINAL', label: 'Original' }, { value: 'MANGA', label: 'Manga' }, { value: 'LIGHT_NOVEL', label: 'Light novel' }],
          streaming: [{ value: 'Crunchyroll', label: 'Crunchyroll' }, { value: 'Netflix', label: 'Netflix' }, { value: 'HIDIVE', label: 'HIDIVE' }],
          sorts: [
            { value: 'relevance', label: 'Relevance' },
            { value: 'popularity', label: 'Popularity' },
            { value: 'trending', label: 'Trending' },
            { value: 'score', label: 'Average score' },
            { value: 'favorites', label: 'Favorites' },
            { value: 'newest', label: 'Newest' },
            { value: 'oldest', label: 'Oldest' },
            { value: 'title', label: 'Title A-Z' },
          ],
        };
        break;
      case 'discover.browse': {
        const filters = (payload.filters ?? {}) as Record<string, unknown>;
        const query = String(filters.search ?? '').toLocaleLowerCase();
        const page = Number(payload.page ?? 1);
        const perPage = Number(payload.perPage ?? 24);
        const filtered = browseCatalog.filter((show) => show.title.toLocaleLowerCase().includes(query));
        const start = (page - 1) * perPage;
        result = {
          items: filtered.slice(start, start + perPage).map((show) => ({
            show: { ...show },
            metadata: catalogMetadata(show),
            inLibrary: this.shows.some((current) => String(current.id) === String(show.id)),
          })),
          pageInfo: {
            currentPage: page,
            lastPage: Math.max(1, Math.ceil(filtered.length / perPage)),
            total: filtered.length,
            hasNextPage: start + perPage < filtered.length,
          },
        };
        break;
      }
      case 'discover.details': {
        const show = payload.show as MediaShow;
        result = {
          show: { ...show },
          metadata: catalogMetadata(show),
          inLibrary: this.shows.some((current) => String(current.id) === String(show.id)),
        };
        break;
      }
      case 'discover.add': {
        const status = typeof payload.status === 'string' || typeof payload.status === 'number'
          ? payload.status
          : 'PLANNING';
        const show: MediaShow = {
          ...(payload.show as MediaShow),
          my_status: status,
          my_start_date: this.engineSettings.auto_date_change && ['CURRENT', 'REPEATING'].includes(String(status))
            ? new Date().toISOString().slice(0, 10)
            : (payload.show as MediaShow).my_start_date,
        };
        if (!this.shows.some((item) => String(item.id) === String(show.id))) this.shows.push(show);
        result = this.library();
        break;
      }
      case 'settings.get':
        result = this.engineSettings;
        break;
      case 'settings.save':
        Object.assign(this.engineSettings, payload.settings);
        result = this.engineSettings;
        break;
      case 'native.getWindowConfig':
        result = this.windowSettings;
        break;
      case 'native.windowConfig':
        Object.assign(this.windowSettings, payload.settings);
        result = this.windowSettings;
        break;
      case 'native.pickPlayer':
        result = { path: '/usr/bin/mpv' };
        break;
      case 'native.pickDirectory':
        result = { path: '/home/minh/Videos' };
        break;
      case 'accounts.beginAuth':
        result = { authSessionId: 'mock-auth', url: 'https://example.com/authorize' };
        break;
      case 'accounts.save': {
        const service = services.find((item) => item.api === payload.api);
        const account: Account = {
          id: payload.accountId === undefined ? this.accounts.length + 1 : Number(payload.accountId),
          username: String(payload.username),
          api: String(payload.api),
          serviceName: service?.name ?? String(payload.api),
        };
        const existing = this.accounts.findIndex((item) => item.id === account.id);
        if (existing >= 0) this.accounts[existing] = account;
        else this.accounts.push(account);
        result = this.bootstrap();
        break;
      }
      case 'accounts.delete':
        this.accounts = this.accounts.filter((account) => account.id !== Number(payload.accountId));
        result = this.bootstrap();
        break;
      case 'accounts.purge':
        result = { purged: true };
        break;
      case 'native.openExternal':
        result = { opened: true };
        break;
      case 'torrents.search':
        result = {
          results: [{
            id: 'https://nyaa.si/view/mock-release',
            title: '[MockSubs] Spy x Family - 23 [1080p]',
            link: 'magnet:?xt=urn:btih:trackma-mock',
            size: '1.1 GiB',
            seeders: '142',
            leechers: '6',
            completed: '984',
            published: '2026-08-02',
          }],
          hasNext: false,
        };
        break;
      case 'torrents.details':
        result = '## Mock release information\n\n![Release preview](https://example.com/preview.jpg)\n\n**Video Resolution:** 1920x1080\n\n- Episode file\n- Subtitle file';
        break;
      case 'torrents.download':
        result = { downloaded: true };
        break;
      default:
        throw new BridgeError('INVALID_COMMAND', `Mock command not implemented: ${command}`);
    }
    return result as T;
  }

  subscribe(listener: (event: BridgeEvent) => void) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  emit(name: string, payload: unknown) {
    this.listeners.forEach((listener) => listener({ name, payload }));
  }

  private bootstrap(): Bootstrap {
    return {
      version: '0.10.3',
      accounts: [...this.accounts],
      services,
      defaultAccountId: this.accounts[0]?.id ?? null,
      activeAccountId: this.accounts[0]?.id ?? null,
    };
  }

  private library(): LibrarySnapshot {
    return {
      shows: this.shows.map((show) => ({ ...show })),
      alternateTitles: {},
      queueCount: 2,
      tracker: { state: 'wait', timer: 0 },
    };
  }

  private session(): SessionSnapshot {
    return {
      account: this.accounts[0],
      api: {
        name: 'AniList',
        shortname: 'anilist',
        mediatype: 'anime',
        supported_mediatypes: ['anime', 'manga'],
      },
      media: {
        statusOptions: [
          { value: 'CURRENT', label: 'Watching' },
          { value: 'COMPLETED', label: 'Completed' },
          { value: 'PAUSED', label: 'Paused' },
          { value: 'DROPPED', label: 'Dropped' },
          { value: 'PLANNING', label: 'Plan to watch' },
        ],
        searchMethods: ['keyword', 'season'],
        score_max: 10,
        score_step: 0.1,
        has_progress: true,
        can_play: true,
        can_add: true,
        can_delete: true,
        can_score: true,
        can_status: true,
        can_date: true,
      },
      library: this.library(),
    };
  }

  private show(showId: unknown) {
    const show = this.shows.find((item) => String(item.id) === String(showId));
    if (!show) throw new BridgeError('NOT_FOUND', 'Title not found');
    return show;
  }
}
