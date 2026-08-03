# This file is part of Trackma.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import datetime
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

from trackma import utils
from trackma.lib.lib import lib


class libanilist(lib):
    """
    API class to communicate with Anilist

    Website: https://anilist.co

    messenger: Messenger object to send useful messages to
    """
    name = 'libanilist'
    msg = None
    logged_in = False

    api_info = {'name': 'Anilist', 'shortname': 'anilist',
                'version': '2.1', 'merge': False}
    mediatypes = dict()
    mediatypes['anime'] = {
        'has_progress': True,
        'can_add': True,
        'can_delete': True,
        'can_score': True,
        'can_status': True,
        'can_update': True,
        'can_play': True,
        'can_date': True,
        'date_next_ep': True,
        'statuses_start': ['CURRENT', 'REPEATING'],
        'statuses_finish': ['COMPLETED'],
        'statuses_library': ['CURRENT', 'REPEATING', 'PAUSED', 'PLANNING'],
        'statuses':  ['CURRENT', 'COMPLETED', 'REPEATING', 'PAUSED', 'DROPPED', 'PLANNING'],
        'statuses_dict': {
            'CURRENT': 'Watching',
            'COMPLETED': 'Completed',
            'REPEATING': 'Rewatching',
            'PAUSED': 'Paused',
            'DROPPED': 'Dropped',
            'PLANNING': 'Plan to Watch'
        },
        'score_max': 100,
        'score_step': 1,
        'search_methods': [utils.SearchMethod.KW, utils.SearchMethod.SEASON],
    }
    mediatypes['manga'] = {
        'has_progress': True,
        'can_add': True,
        'can_delete': True,
        'can_score': True,
        'can_status': True,
        'can_update': True,
        'can_play': False,
        'can_date': True,
        'statuses_start': ['CURRENT', 'REPEATING'],
        'statuses_finish': ['COMPLETED'],
        'statuses':  ['CURRENT', 'COMPLETED', 'REPEATING', 'PAUSED', 'DROPPED', 'PLANNING'],
        'statuses_dict': {
            'CURRENT': 'Reading',
            'COMPLETED': 'Completed',
            'REPEATING': 'Rereading',
            'PAUSED': 'Paused',
            'DROPPED': 'Dropped',
            'PLANNING': 'Plan to Read'
        },
        'score_max': 100,
        'score_step': 1,
        'search_methods': [utils.SearchMethod.KW],
    }
    default_mediatype = 'anime'

    score_types = {
        'POINT_100': (100, 1),
        'POINT_10_DECIMAL': (10, 0.1),
        'POINT_10': (10, 1),
        'POINT_5': (5, 1),
        'POINT_3': (3, 1),
    }

    type_translate = {
        None: utils.Type.UNKNOWN,
        'TV': utils.Type.TV,
        'TV_SHORT': utils.Type.TV_SHORT,
        'MOVIE': utils.Type.MOVIE,
        'SPECIAL': utils.Type.SP,
        'OVA': utils.Type.OVA,
        'ONA': utils.Type.ONA,
        'MUSIC': utils.Type.OTHER,
        'MANGA': utils.Type.OTHER,
        'NOVEL': utils.Type.OTHER,
        'ONE_SHOT': utils.Type.OTHER,
    }

    status_translate = {
        None: utils.Status.UNKNOWN,
        'RELEASING': utils.Status.AIRING,
        'FINISHED': utils.Status.FINISHED,
        'NOT_YET_RELEASED': utils.Status.NOTYET,
        'CANCELLED': utils.Status.CANCELLED,
    }

    season_translate = {
        utils.Season.WINTER: 'WINTER',
        utils.Season.SPRING: 'SPRING',
        utils.Season.SUMMER: 'SUMMER',
        utils.Season.FALL: 'FALL',
    }
    rev_season_translate = {v: k for k, v in season_translate.items()}

    # Supported signals for the data handler
    signals = {'show_info_changed': None, }

    auth_url = "https://anilist.co/api/v2/"
    query_url = "https://graphql.anilist.co"
    client_id = "537"
    _client_secret = "9Hl31gyz2q9xMhhJwLKRA8DAn0pXl9sOHFf6I1YO"
    user_agent = 'Trackma/{}'.format(utils.VERSION)

    discover_sorts = {
        'relevance': 'SEARCH_MATCH',
        'popularity': 'POPULARITY_DESC',
        'trending': 'TRENDING_DESC',
        'score': 'SCORE_DESC',
        'favorites': 'FAVOURITES_DESC',
        'newest': 'START_DATE_DESC',
        'oldest': 'START_DATE',
        'title': 'TITLE_ROMAJI',
    }

    discover_media_fields = '''
      id
      title { userPreferred romaji english native }
      coverImage { large extraLarge color }
      format
      averageScore
      meanScore
      popularity
      favourites
      chapters
      episodes
      duration
      status
      source
      countryOfOrigin
      startDate { year month day }
      endDate { year month day }
      siteUrl
      description
      genres
      synonyms
      studios(sort: NAME, isMain: true) { nodes { name } }
      seasonYear
      season
      nextAiringEpisode { episode airingAt timeUntilAiring }
      tags { name rank isMediaSpoiler }
      externalLinks { site url type }
    '''

    def __init__(self, messenger, account, userconfig):
        """Initializes the API"""
        super(libanilist, self).__init__(messenger, account, userconfig)

        self.pin = account['password'].strip()
        self.userid = self._get_userconfig('userid')

        if self.mediatype == 'manga':
            self.total_str = "chapters"
            self.watched_str = "chapters_read"
        else:
            self.total_str = "episodes"
            self.watched_str = "episodes_watched"

        # If we already know the scoreFormat of the cached list, apply it now
        self.scoreformat = self._get_userconfig(
            'scoreformat_' + self.mediatype)
        if self.scoreformat:
            self._apply_scoreformat(self.scoreformat)

        self.opener = urllib.request.build_opener()
        self.opener.addheaders = [('User-agent', self.user_agent)]
        self._discover_options_cache = {}

    def _raw_request(self, method, url, get=None, post=None, jsonpost=None, auth=False):
        if get:
            url = "{}?{}".format(url, urllib.parse.urlencode(get))
        if post:
            post = urllib.parse.urlencode(post).encode('utf-8')
        if jsonpost:
            post = json.dumps(jsonpost, ensure_ascii=False).encode('utf-8')

        request = urllib.request.Request(url, post)
        request.get_method = lambda: method

        request.add_header('Content-Type', 'application/json')
        request.add_header('Accept', 'application/json')

        if auth:
            request.add_header('Authorization', 'Bearer {}'.format(
                self.pin,
            ))

        try:
            response = self.opener.open(request, timeout=20)
            return json.loads(utils.read_response_limited(response).decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 400:
                raise utils.APIError("Invalid HTTP request: %s" % e.read())
            else:
                raise utils.APIError("HTTP error status: %s" % e.read())
        except urllib.error.URLError as e:
            raise utils.APIError("HTTP connection error: %s" % e.reason)
        except socket.timeout:
            raise utils.APIError("Connection timed out.")
        except ValueError as e:
            raise utils.APIError(str(e))

    def _request(self, query, variables=None):
        if variables:
            data = {'query': query, 'variables': variables}
        else:
            data = {'query': query}

        return self._raw_request('POST', self.query_url, jsonpost=data, auth=True)

    def check_credentials(self):
        if len(self.pin) == 40:  # Old pins were 40 digits, new ones seem to be 654 digits
            raise utils.APIFatal("This appears to be a V1 API PIN. You need a V2 API PIN to continue using AniList."
                                 " Please re-authorize or re-create your AniList account.")

        if not self.userid:
            self._refresh_user_info()

        return True

    def _refresh_user_info(self):
        self.msg.info('Refreshing user details...')
        query = '{Viewer{ id name avatar{large} options{titleLanguage displayAdultContent} mediaListOptions{scoreFormat} }}'
        data = self._request(query)['data']['Viewer']

        self._set_userconfig('userid', data['id'])
        self._set_userconfig('username', data['name'])
        self._emit_signal('userconfig_changed')

        self.userid = data['id']

    def fetch_list(self):
        self.check_credentials()
        self.msg.info('Downloading list...')

        query = '''query ($id: Int!, $listType: MediaType) {
  MediaListCollection (userId: $id, type: $listType) {
    lists {
      name
      isCustomList
      status
      entries {
        ... mediaListEntry
      }
    }
    user {
      mediaListOptions {
        scoreFormat
      }
    }
  }
}

fragment mediaListEntry on MediaList {
  id
  score
  progress
  repeat
  notes
  startedAt { year month day }
  updatedAt
  completedAt { year month day }
  media {
    id
    title { userPreferred romaji english native }
    synonyms
    coverImage { extraLarge large }
    format
    status
    chapters episodes
    nextAiringEpisode { airingAt episode }
    startDate { year month day }
    endDate { year month day }
    siteUrl
  }
}'''
        variables = {'id': self.userid, 'listType': self.mediatype.upper()}
        data = self._request(query, variables)['data']['MediaListCollection']

        showlist = {}

        if not data['lists']:
            # No lists returned so no need to continue
            return showlist

        # Handle different score formats provided by Anilist
        self.scoreformat = data['user']['mediaListOptions']['scoreFormat']
        self._apply_scoreformat(self.scoreformat)

        self._set_userconfig('scoreformat_' + self.mediatype, self.scoreformat)
        self._emit_signal('userconfig_changed')

        for remotelist in data['lists']:
            my_status = remotelist['status']

            if my_status not in self.media_info()['statuses']:
                continue
            if remotelist['isCustomList']:
                continue  # Maybe do something with this later
            for item in remotelist['entries']:
                show = utils.show()
                media = item['media']
                showid = media['id']
                showdata = {
                    'my_id': item['id'],
                    'id': showid,
                    'title': media['title']['userPreferred'],
                    'aliases': self._get_aliases(media),
                    'type': self._translate_type(media['format']),
                    'status': self._translate_status(media['status']),
                    'my_progress': self._c(item['progress']),
                    'my_status': my_status,
                    'my_score': self._c(item['score']),
                    'my_rewatches': self._c(item['repeat']),
                    'my_notes': item['notes'] or '',
                    'total': self._c(media[self.total_str]),
                    'image': media['coverImage']['extraLarge'],
                    'image_thumb': media['coverImage']['large'],
                    'url': media['siteUrl'],
                    'start_date': self._dict2date(media['startDate']),
                    'end_date': self._dict2date(media['endDate']),
                    'my_start_date': self._dict2date(item['startedAt']),
                    'my_finish_date': self._dict2date(item['completedAt']),
                    'my_last_update': self._int2datetime(item['updatedAt']),
                }
                if media['nextAiringEpisode']:
                    showdata['next_ep_number'] = media['nextAiringEpisode']['episode']
                    showdata['next_ep_time'] = self._int2date(
                        media['nextAiringEpisode']['airingAt'])
                show.update({k: v for k, v in showdata.items() if v})
                showlist[showid] = show
        return showlist

    args_SaveMediaListEntry = {
        'id': 'Int',                         # The list entry id, required for updating
        'mediaId': 'Int',                    # The id of the media the entry is of
        'status': 'MediaListStatus',         # The watching/reading status
        'scoreRaw': 'Int',                   # The score of the media in 100 point
        # The amount of episodes/chapters consumed by the user
        'progress': 'Int',
        'repeat': 'Int',                     # The amount of times the user has rewatched the media
        'notes': 'String',                   # Personal notes about the media
        'startedAt': 'FuzzyDateInput',       # When the entry was started by the user
        'completedAt': 'FuzzyDateInput',     # When the entry was completed by the user
    }

    def _update_entry(self, item):
        """
        New entries will lack a list entry id, while updates will include one.
        In the case of a new entry, we want to record the new id. In the case of an update, we want to record the new updated date.
        """
        values = {'mediaId': item['id']}
        if 'my_id' in item and item['my_id']:
            values['id'] = item['my_id']
        if 'my_progress' in item:
            values['progress'] = item['my_progress']
        if 'my_status' in item:
            values['status'] = item['my_status']
        if 'my_score' in item:
            values['scoreRaw'] = self._score2raw(item['my_score'])
        if 'my_rewatches' in item:
            values['repeat'] = item['my_rewatches']
        if 'my_notes' in item:
            values['notes'] = item['my_notes']
        if 'my_start_date' in item:
            values['startedAt'] = self._date2dict(item['my_start_date'])
        if 'my_finish_date' in item:
            values['completedAt'] = self._date2dict(item['my_finish_date'])

        vars_defn = ', '.join(
            ['${}: {}'.format(k, self.args_SaveMediaListEntry[k]) for k in values.keys()])
        subs_defn = ', '.join(['{0}: ${0}'.format(k) for k in values.keys()])
        query = 'mutation ({0}) {{ SaveMediaListEntry({1}) {{id updatedAt}} }}'.format(
            vars_defn, subs_defn)

        data = self._request(query, values)['data']
        return data['SaveMediaListEntry']

    def add_show(self, item):
        self.check_credentials()
        self.msg.info("Adding item %s..." % item['title'])
        return self._update_entry(item)['id']

    def update_show(self, item):
        self.check_credentials()
        self.msg.info("Updating item %s..." % item['title'])
        return self._int2datetime(self._update_entry(item)['updatedAt'])

    def delete_show(self, item):
        self.check_credentials()
        self.msg.info("Deleting item %s..." % item['title'])
        query = 'mutation ($id: Int) {DeleteMediaListEntry(id: $id){deleted} }'
        variables = {'id': item['my_id']}
        self._request(query, variables)

    @staticmethod
    def _season_for_date(value):
        if value.month <= 3:
            return 'WINTER', value.year
        if value.month <= 6:
            return 'SPRING', value.year
        if value.month <= 9:
            return 'SUMMER', value.year
        return 'FALL', value.year

    @classmethod
    def _next_season(cls, season, year):
        seasons = ['WINTER', 'SPRING', 'SUMMER', 'FALL']
        index = seasons.index(season)
        if index == len(seasons) - 1:
            return seasons[0], year + 1
        return seasons[index + 1], year

    def _discover_capabilities(self):
        if self.mediatype == 'anime':
            filters = [
                'search', 'genres', 'tags', 'year', 'season', 'formats',
                'statuses', 'country', 'source', 'streaming', 'sort',
            ]
        else:
            filters = [
                'search', 'genres', 'tags', 'year', 'formats', 'statuses',
                'country', 'source', 'sort',
            ]
        return {
            'mode': 'full',
            'filters': filters,
            'supportsHome': True,
            'supportsAdvanced': True,
            'supportsPagination': True,
        }

    def _parse_catalog_media(self, item, rank=None):
        show = self._parse_info(item)
        show['_catalog'] = {
            'titles': item.get('title') or {},
            'description': item.get('description'),
            'genres': item.get('genres') or [],
            'tags': [
                {'name': tag['name'], 'rank': tag.get('rank')}
                for tag in item.get('tags') or []
                if not tag.get('isMediaSpoiler')
            ],
            'studios': [studio['name'] for studio in item.get('studios', {}).get('nodes', [])],
            'format': item.get('format'),
            'status': item.get('status'),
            'averageScore': item.get('averageScore'),
            'meanScore': item.get('meanScore'),
            'popularity': item.get('popularity'),
            'favourites': item.get('favourites'),
            'duration': item.get('duration'),
            'season': item.get('season'),
            'seasonYear': item.get('seasonYear'),
            'source': item.get('source'),
            'countryOfOrigin': item.get('countryOfOrigin'),
            'nextAiringEpisode': item.get('nextAiringEpisode'),
            'externalLinks': item.get('externalLinks') or [],
            'coverColor': item.get('coverImage', {}).get('color'),
        }
        if rank is not None:
            show['_catalog']['rank'] = rank
        return show

    def discover_home(self):
        self.check_credentials()
        current_season, current_year = self._season_for_date(datetime.date.today())
        next_season, next_year = self._next_season(current_season, current_year)
        variables = {
            'type': self.mediatype.upper(),
            'currentSeason': current_season,
            'currentYear': current_year,
            'nextSeason': next_season,
            'nextYear': next_year,
        }
        if self.mediatype == 'anime':
            pages = '''
  trending: Page(page: 1, perPage: 6) { media(type: $type, sort: TRENDING_DESC) { %s } }
  popularSeason: Page(page: 1, perPage: 6) { media(type: $type, season: $currentSeason, seasonYear: $currentYear, sort: POPULARITY_DESC) { %s } }
  upcomingSeason: Page(page: 1, perPage: 6) { media(type: $type, season: $nextSeason, seasonYear: $nextYear, sort: POPULARITY_DESC) { %s } }
  popular: Page(page: 1, perPage: 6) { media(type: $type, sort: POPULARITY_DESC) { %s } }
  top: Page(page: 1, perPage: 10) { media(type: $type, sort: SCORE_DESC) { %s } }
''' % ((self.discover_media_fields,) * 5)
            definitions = '$type: MediaType, $currentSeason: MediaSeason, $currentYear: Int, $nextSeason: MediaSeason, $nextYear: Int'
            section_specs = [
                ('trending', 'Trending now', 'trending', {'sort': 'trending'}),
                ('popular-season', 'Popular this season', 'popularSeason', {'season': current_season, 'year': current_year, 'sort': 'popularity'}),
                ('upcoming-season', 'Upcoming next season', 'upcomingSeason', {'season': next_season, 'year': next_year, 'sort': 'popularity'}),
                ('popular', 'All time popular', 'popular', {'sort': 'popularity'}),
                ('top', 'Top 100 anime', 'top', {'sort': 'score'}),
            ]
        else:
            pages = '''
  trending: Page(page: 1, perPage: 6) { media(type: $type, sort: TRENDING_DESC) { %s } }
  popular: Page(page: 1, perPage: 6) { media(type: $type, sort: POPULARITY_DESC) { %s } }
  popularManhwa: Page(page: 1, perPage: 6) { media(type: $type, countryOfOrigin: "KR", sort: POPULARITY_DESC) { %s } }
  top: Page(page: 1, perPage: 10) { media(type: $type, sort: SCORE_DESC) { %s } }
''' % ((self.discover_media_fields,) * 4)
            definitions = '$type: MediaType'
            variables = {'type': self.mediatype.upper()}
            section_specs = [
                ('trending', 'Trending now', 'trending', {'sort': 'trending'}),
                ('popular', 'All time popular', 'popular', {'sort': 'popularity'}),
                ('popular-manhwa', 'Popular manhwa', 'popularManhwa', {'country': 'KR', 'sort': 'popularity'}),
                ('top', 'Top 100 manga', 'top', {'sort': 'score'}),
            ]
        data = self._request('query (%s) {%s}' % (definitions, pages), variables)['data']
        sections = []
        for section_id, title, alias, preset in section_specs:
            media = data.get(alias, {}).get('media', [])
            sections.append({
                'id': section_id,
                'title': title,
                'preset': preset,
                'items': [
                    self._parse_catalog_media(item, index if section_id == 'top' else None)
                    for index, item in enumerate(media, start=1)
                ],
            })
        return {'capabilities': self._discover_capabilities(), 'sections': sections}

    def discover_options(self):
        cached = self._discover_options_cache.get(self.mediatype)
        if cached:
            return cached
        self.check_credentials()
        query = '{ GenreCollection MediaTagCollection { name category isAdult } }'
        data = self._request(query)['data']
        formats = (
            ['TV', 'TV_SHORT', 'MOVIE', 'SPECIAL', 'OVA', 'ONA', 'MUSIC']
            if self.mediatype == 'anime'
            else ['MANGA', 'NOVEL', 'ONE_SHOT']
        )
        statuses = (
            ['RELEASING', 'FINISHED', 'NOT_YET_RELEASED', 'CANCELLED']
            if self.mediatype == 'anime'
            else ['RELEASING', 'FINISHED', 'NOT_YET_RELEASED', 'CANCELLED', 'HIATUS']
        )
        label = lambda value: value.replace('_', ' ').title()
        result = {
            'genres': [{'value': value, 'label': value} for value in data.get('GenreCollection', [])],
            'tags': [
                {'value': item['name'], 'label': item['name'], 'group': item.get('category') or 'Other'}
                for item in data.get('MediaTagCollection', [])
                if not item.get('isAdult')
            ],
            'formats': [{'value': value, 'label': label(value)} for value in formats],
            'statuses': [{'value': value, 'label': label(value)} for value in statuses],
            'countries': [
                {'value': 'JP', 'label': 'Japan'},
                {'value': 'KR', 'label': 'South Korea'},
                {'value': 'CN', 'label': 'China'},
                {'value': 'TW', 'label': 'Taiwan'},
            ],
            'sources': [
                {'value': value, 'label': label(value)}
                for value in ['ORIGINAL', 'MANGA', 'LIGHT_NOVEL', 'VISUAL_NOVEL', 'VIDEO_GAME', 'NOVEL', 'DOUJINSHI', 'ANIME', 'WEB_NOVEL', 'LIVE_ACTION', 'GAME', 'OTHER']
            ],
            'streaming': [
                {'value': 'Crunchyroll', 'label': 'Crunchyroll'},
                {'value': 'Netflix', 'label': 'Netflix'},
                {'value': 'Hulu', 'label': 'Hulu'},
                {'value': 'HIDIVE', 'label': 'HIDIVE'},
                {'value': 'Amazon', 'label': 'Amazon Prime Video'},
                {'value': 'Disney Plus', 'label': 'Disney+'},
                {'value': 'YouTube', 'label': 'YouTube'},
            ] if self.mediatype == 'anime' else [],
            'sorts': [
                {'value': 'relevance', 'label': 'Relevance'},
                {'value': 'popularity', 'label': 'Popularity'},
                {'value': 'trending', 'label': 'Trending'},
                {'value': 'score', 'label': 'Average score'},
                {'value': 'favorites', 'label': 'Favorites'},
                {'value': 'newest', 'label': 'Newest'},
                {'value': 'oldest', 'label': 'Oldest'},
                {'value': 'title', 'label': 'Title A-Z'},
            ],
        }
        self._discover_options_cache[self.mediatype] = result
        return result

    def discover_browse(self, filters, page=1, per_page=24):
        self.check_credentials()
        definitions = ['$page: Int', '$perPage: Int', '$type: MediaType']
        arguments = ['type: $type']
        variables = {'page': page, 'perPage': per_page, 'type': self.mediatype.upper()}
        specs = [
            ('search', 'String', 'search: $search', lambda value: str(value).strip()),
            ('genres', '[String]', 'genre_in: $genres', list),
            ('tags', '[String]', 'tag_in: $tags', list),
            ('year', 'String', 'startDate_like: $startDate', lambda value: '%s%%' % int(value), 'startDate'),
            ('season', 'MediaSeason', 'season: $season', str),
            ('formats', '[MediaFormat]', 'format_in: $formats', list),
            ('statuses', '[MediaStatus]', 'status_in: $statuses', list),
            ('country', 'CountryCode', 'countryOfOrigin: $country', str),
            ('source', '[MediaSource]', 'source_in: $sources', lambda value: [str(value)], 'sources'),
            ('streaming', '[String]', 'licensedBy_in: $licensedBy', lambda value: [str(value)], 'licensedBy'),
        ]
        for spec in specs:
            filter_name, graphql_type, argument, convert, *variable_override = spec
            value = filters.get(filter_name)
            if value in (None, '', []):
                continue
            variable_name = variable_override[0] if variable_override else filter_name
            definitions.append('$%s: %s' % (variable_name, graphql_type))
            arguments.append(argument)
            variables[variable_name] = convert(value)
        sort_name = str(filters.get('sort') or ('relevance' if variables.get('search') else 'popularity'))
        if sort_name == 'relevance' and not variables.get('search'):
            sort_name = 'popularity'
        variables['sort'] = [self.discover_sorts.get(sort_name, 'POPULARITY_DESC')]
        definitions.append('$sort: [MediaSort]')
        arguments.append('sort: $sort')
        query = '''query (%s) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { currentPage lastPage total hasNextPage }
    media(%s) { %s }
  }
}''' % (', '.join(definitions), ', '.join(arguments), self.discover_media_fields)
        page_data = self._request(query, variables)['data']['Page']
        return {
            'items': [self._parse_catalog_media(item) for item in page_data.get('media', [])],
            'pageInfo': page_data.get('pageInfo') or {
                'currentPage': page,
                'lastPage': page,
                'total': 0,
                'hasNextPage': False,
            },
        }

    def search(self, criteria, method):
        self.check_credentials()
        self.msg.info("Searching for {}...".format(criteria))

        if method == utils.SearchMethod.KW:
            query = "query ($query: String, $type: MediaType) { Page { media(search: $query, type: $type) {"
            variables = {'query': urllib.parse.quote_plus(criteria)}
        elif method == utils.SearchMethod.SEASON:
            season, seasonYear = criteria

            query = "query ($season: MediaSeason, $seasonYear: Int, $type: MediaType) { Page { media(season: $season, seasonYear: $seasonYear, type: $type) {"
            variables = {
                'season': self.season_translate[season], 'seasonYear': seasonYear}

        query += '''
      id
      title { userPreferred romaji english native }
      coverImage { large extraLarge }
      format
      averageScore
      meanScore
      chapters episodes
      status
      startDate { year month day }
      endDate { year month day }
      siteUrl
      description
      genres
      synonyms
      studios(sort: NAME, isMain: true) { nodes { name } }
      seasonYear
      season
    }
  }
}'''
        variables['type'] = self.mediatype.upper()
        data = self._request(query, variables)['data']['Page']['media']

        infolist = []
        for media in data:
            infolist.append(self._parse_info(media))

        self._emit_signal('show_info_changed', infolist)
        return infolist

    def request_info(self, itemlist):
        self.check_credentials()
        infolist = []

        query = '''query ($id: Int!, $type: MediaType) {
  Media(id: $id, type: $type) {
%s
  }
}''' % self.discover_media_fields

        for show in itemlist:
            variables = {'id': show['id'], 'type': self.mediatype.upper()}
            data = self._request(query, variables)['data']['Media']
            infolist.append(self._parse_catalog_media(data))

        self._emit_signal('show_info_changed', infolist)
        return infolist

    def media_info(self):
        """Return information about the currently selected mediatype."""
        return self.mediatypes[self.mediatype]

    def _parse_info(self, item):
        info = utils.show()
        showid = item['id']
        type_ = self._translate_type(item['format'])
        status = self._translate_status(item['status'])
        season = self.rev_season_translate.get(item.get('season'))
        if season and 'seasonYear' in item:
            season_and_year = f"{season!s} {item['seasonYear']}"
        elif 'seasonYear' in item:
            season_and_year = item['seasonYear']
        else:
            season_and_year = None

        info.update({
            'id': showid,
            'title': item['title']['userPreferred'],
            'total': self._c(item[self.total_str]),
            'aliases': self._get_aliases(item),
            'type': type_,
            'status': status,
            'image': item['coverImage']['extraLarge'],
            'image_thumb': item['coverImage']['large'],
            'url': item['siteUrl'],
            'start_date': self._dict2date(item.get('startDate')),
            'end_date': self._dict2date(item.get('endDate')),
            'extra': [
                ('English',         item['title'].get('english')),
                ('Romaji',          item['title'].get('romaji')),
                ('Japanese',        item['title'].get('native')),
                ('Synonyms',        item.get('synonyms')),
                ('Season',          season_and_year),
                ('Genres',          item.get('genres')),
                ('Studios',         [s['name'] for s in item['studios']['nodes']]),
                ('Synopsis',        item.get('description')),
                ('Type',            type_),
                ('Average score',   item.get('averageScore')),
                ('Mean score',      item.get('meanScore')),
                ('Status',          status),
            ]
        })
        return info

    def _apply_scoreformat(self, fmt):
        media = self.media_info()
        (media['score_max'], media['score_step']) = self.score_types[fmt]

    def _get_aliases(self, item):
        aliases = [a for a in (item['title']['romaji'], item['title']
                               ['english'], item['title']['native']) if a] + item['synonyms']

        return aliases

    def _translate_type(self, orig_type):
        return self.type_translate.get(orig_type, utils.Type.UNKNOWN)

    def _translate_status(self, orig_status):
        return self.status_translate.get(orig_status, utils.Status.UNKNOWN)

    def _dict2date(self, item):
        if not item:
            return None
        try:
            return datetime.datetime(item['year'], item['month'], item['day'])
        except (TypeError, ValueError):
            return None

    def _date2dict(self, date):
        if not date:
            return {}
        try:
            return {'year': date.year, 'month': date.month, 'day': date.day}
        except (TypeError, ValueError):
            return {}

    def _score2raw(self, score):
        if score == 0:
            return 0

        if self.scoreformat in ['POINT_10', 'POINT_10_DECIMAL']:
            return int(score*10)
        elif self.scoreformat == 'POINT_5':
            return int(score*20)
        elif self.scoreformat == 'POINT_3':
            return int(score*25)
        else:
            return score

    def _int2date(self, item):
        if not item:
            return None
        try:
            return datetime.datetime.utcfromtimestamp(item)
        except ValueError:
            return None

    def _int2datetime(self, item):
        if not item:
            return None
        try:
            return datetime.datetime.fromtimestamp(item, tz=datetime.timezone.utc)
        except ValueError:
            return None

    def _c(self, s):
        if s is None:
            return 0
        else:
            return s
