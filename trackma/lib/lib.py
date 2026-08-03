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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from typing import Optional

from trackma import utils


class lib:
    """
    Base interface for creating API implementations for Trackma.

    messenger: Messenger object to send useful messages to
    mediatype: String containing the media type to be used
    """
    name = 'lib'
    version = 'dummy'
    msg = None

    api_info = {'name': 'BaseAPI', 'version': 'undefined', 'merge': False}
    """
    api_info is a dictionary containing useful information about the API itself
    name: API name
    version: API version
    """

    mediatypes = dict()
    """
    mediatypes is a dictionary containing the possible mediatypes for the current API.
    An example mediatype should look like this:
    ::

        mediatypes['anime'] = {
            'has_progress': True,
            'can_add': True,
            'can_delete': True,
            'can_score': True,
            'can_status': True,
            'can_update': True,
            'can_play': True,
            'statuses_start': [1],
            'statuses_finish': [2],
            'statuses':  [1, 2, 3, 4, 6],
            'statuses_dict': { 1: 'Watching', 2: 'Completed', 3: 'On Hold', 4: 'Dropped', 6: 'Plan to Watch' },
        }

    """

    default_mediatype: Optional[str] = None

    # Supported signals for the data handler
    signals = {
        'show_info_changed': None,
        'userconfig_changed': None,
    }

    def __init__(self, messenger, account, userconfig):
        """Initializes the API"""
        self.userconfig = userconfig
        self.api_info = dict(self.api_info)
        supported_signals = {**lib.signals, **type(self).signals}
        self.signals = {name: None for name in supported_signals}
        self.msg = messenger.with_classname(self.name)
        self.msg.info('Initializing...')

        if not userconfig.get('mediatype'):
            userconfig['mediatype'] = self.default_mediatype

        if userconfig['mediatype'] in self.mediatypes:
            self.mediatype = userconfig['mediatype']
        else:
            raise utils.APIFatal('Unsupported mediatype %s.' %
                                 userconfig['mediatype'])

        self.api_info['mediatype'] = self.mediatype
        self.api_info['supported_mediatypes'] = list(self.mediatypes.keys())

    def _emit_signal(self, signal, *args):
        try:
            if self.signals[signal]:
                self.signals[signal](*args)
        except KeyError:
            raise Exception("Call to undefined signal.")

    def _get_userconfig(self, key):
        return self.userconfig.get(key)

    def _set_userconfig(self, key, value):
        self.userconfig[key] = value

    def connect_signal(self, signal, callback):
        if signal not in self.signals:
            raise utils.EngineFatal("Invalid signal.")
        self.signals[signal] = callback

    def check_credentials(self):
        """Checks if credentials are correct; returns True or False."""
        raise NotImplementedError

    def fetch_list(self):
        """
        Fetches the remote list and returns a dictionary of show dictionaries.

        It should return a dictionary with the show ID as the key and a show dictionary as its value.
        You can create an empty show dictionary with the :func:`utils.show` function.
        """
        raise NotImplementedError

    def add_show(self, item):
        """
        Adds the **item** in the remote server list. The **item** is a show dictionary passed by the Data Handler.
        """
        raise NotImplementedError

    def update_show(self, item):
        """
        Sends the updates of a show to the remote site.

        This function gets called every time a show should be updated remotely,
        and in a queue it may be called many times consecutively, so you should
        use a boolean (or other method) to login only once.

        """
        raise NotImplementedError

    def delete_show(self, item):
        """
        Deletes the **item** in the remote server list. The **item** is a show dictionary passed by the Data Handler.
        """
        raise NotImplementedError

    def search(self, criteria, method):
        """
        Called when the data handler needs a detailed list of shows from the remote server.
        It should return a list of show dictionaries with the additional 'extra' key (which is a list of tuples)
        containing any additional detailed information about the show.
        """
        raise NotImplementedError

    def discover_home(self):
        """Return browse previews when the provider exposes a catalog feed."""
        methods = self.media_info().get('search_methods', [utils.SearchMethod.KW])
        filters = ['search']
        if utils.SearchMethod.SEASON in methods:
            filters.extend(['year', 'season'])
        return {
            'capabilities': {
                'mode': 'fallback',
                'filters': filters,
                'supportsHome': False,
                'supportsAdvanced': False,
                'supportsPagination': False,
            },
            'sections': [],
        }

    def discover_options(self):
        """Return an empty option set for providers without browse metadata."""
        return {
            'genres': [],
            'tags': [],
            'formats': [],
            'statuses': [],
            'countries': [],
            'sources': [],
            'streaming': [],
            'sorts': [],
        }

    def discover_browse(self, filters, page=1, per_page=24):
        """Adapt the existing keyword/season search to the browse contract."""
        del page, per_page
        query = str(filters.get('search', '')).strip()
        season = filters.get('season')
        year = filters.get('year')
        if query:
            items = self.search(query, utils.SearchMethod.KW)
        elif season and year and utils.SearchMethod.SEASON in self.media_info().get('search_methods', []):
            items = self.search((utils.Season.find(season), int(year)), utils.SearchMethod.SEASON)
        else:
            items = []
        return {
            'items': items or [],
            'pageInfo': {
                'currentPage': 1,
                'lastPage': 1,
                'total': len(items or []),
                'hasNextPage': False,
            },
        }

    def request_info(self, items):
        # Request detailed information for requested shows
        raise NotImplementedError

    def logout(self):
        # This is called whenever the API won't be required
        # for a good while
        pass

    def media_info(self):
        """Return information about the currently selected mediatype."""
        return self.mediatypes[self.mediatype]

    def set_message_handler(self, message_handler):
        self.msg = message_handler.with_classname(self.name)
