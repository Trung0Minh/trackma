export type MediaId = string | number;
export type StatusValue = string | number;

export interface Account {
  id: number;
  username: string;
  api: string;
  serviceName: string;
}

export interface Service {
  api: string;
  name: string;
  loginMode: 'password' | 'oauth' | 'oauthPkce';
  requiresExternalAuth: boolean;
}

export interface Bootstrap {
  version: string;
  accounts: Account[];
  services: Service[];
  defaultAccountId: number | null;
  activeAccountId: number | null;
}

export interface StatusOption {
  value: StatusValue;
  label: string;
}

export interface MediaInfo {
  statusOptions: StatusOption[];
  searchMethods: Array<'keyword' | 'season'>;
  score_max: number;
  score_step: number;
  can_play?: boolean;
  can_add?: boolean;
  can_delete?: boolean;
  can_score?: boolean;
  can_status?: boolean;
  can_date?: boolean;
  has_progress?: boolean;
  [key: string]: unknown;
}

export interface ApiInfo {
  name: string;
  shortname: string;
  mediatype: string;
  supported_mediatypes: string[];
}

export interface MediaShow {
  id: MediaId;
  title: string;
  image?: string;
  image_thumb?: string;
  url?: string;
  aliases?: string[];
  type?: string;
  status?: string;
  total: number;
  my_progress: number;
  my_status: StatusValue;
  my_score: number;
  my_rewatches?: number;
  my_notes?: string;
  my_tags?: string;
  start_date?: string | null;
  end_date?: string | null;
  my_start_date?: string | null;
  my_finish_date?: string | null;
  availableEpisodes?: number[];
  airedEpisodes?: number;
  queued?: boolean;
  [key: string]: unknown;
}

export interface LibrarySnapshot {
  shows: MediaShow[];
  alternateTitles: Record<string, string>;
  queueCount: number;
  tracker: Record<string, unknown> | null;
}

export interface SessionSnapshot {
  account: Account;
  api: ApiInfo;
  media: MediaInfo;
  library: LibrarySnapshot;
}

export interface ShowDetails {
  show: MediaShow;
  details: Record<string, unknown>;
}

export interface DiscoverOption {
  value: string;
  label: string;
  group?: string;
}

export interface CatalogTag {
  name: string;
  rank?: number;
}

export interface CatalogMetadata {
  titles?: Record<string, string | null>;
  description?: string | null;
  genres?: string[];
  tags?: CatalogTag[];
  studios?: string[];
  format?: string | null;
  status?: string | null;
  averageScore?: number | null;
  meanScore?: number | null;
  popularity?: number | null;
  favourites?: number | null;
  duration?: number | null;
  season?: string | null;
  seasonYear?: number | null;
  source?: string | null;
  countryOfOrigin?: string | null;
  nextAiringEpisode?: {
    episode?: number;
    airingAt?: number;
    timeUntilAiring?: number;
  } | null;
  externalLinks?: Array<{ site?: string; url?: string; type?: string }>;
  coverColor?: string | null;
  rank?: number;
}

export interface DiscoverItem {
  show: MediaShow;
  metadata: CatalogMetadata;
  inLibrary: boolean;
}

export interface DiscoverCapabilities {
  mode: 'full' | 'fallback';
  filters: string[];
  supportsHome: boolean;
  supportsAdvanced?: boolean;
  supportsPagination?: boolean;
}

export interface DiscoverSection {
  id: string;
  title: string;
  preset: DiscoverFilters;
  items: DiscoverItem[];
}

export interface DiscoverHome {
  capabilities: DiscoverCapabilities;
  sections: DiscoverSection[];
}

export interface DiscoverFilterOptions {
  genres: DiscoverOption[];
  tags: DiscoverOption[];
  formats: DiscoverOption[];
  statuses: DiscoverOption[];
  countries: DiscoverOption[];
  sources: DiscoverOption[];
  streaming: DiscoverOption[];
  sorts: DiscoverOption[];
}

export interface DiscoverFilters {
  search?: string;
  genres?: string[];
  tags?: string[];
  year?: number;
  season?: string;
  formats?: string[];
  statuses?: string[];
  country?: string;
  source?: string;
  streaming?: string;
  sort?: string;
}

export interface DiscoverPageInfo {
  currentPage: number;
  lastPage: number;
  total: number;
  hasNextPage: boolean;
}

export interface DiscoverResults {
  items: DiscoverItem[];
  pageInfo: DiscoverPageInfo;
}
