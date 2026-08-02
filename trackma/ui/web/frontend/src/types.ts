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
