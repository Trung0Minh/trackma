import os
import stat

import pytest

from trackma import utils
from trackma.data import Data
from trackma.engine import Engine
from trackma.ui.web.contract import CommandError
from trackma.ui.web.controller import BackendController


class MessageSink:
    def debug(self, *_args):
        pass

    def info(self, *_args):
        pass

    def warn(self, *_args):
        pass


class QueueAPI:
    def __init__(self):
        self.logged_out = False

    def update_show(self, item):
        if item['id'] == 2:
            raise utils.APIError('temporary failure')
        return 123

    def logout(self):
        self.logged_out = True


def make_data(tmp_path):
    handler = object.__new__(Data)
    handler.msg = MessageSink()
    handler.api = QueueAPI()
    handler.showlist = {
        1: {'id': 1, 'title': 'One', 'queued': True},
        2: {'id': 2, 'title': 'Two', 'queued': True},
        3: {'id': 3, 'title': 'Three', 'queued': True},
    }
    handler.queue = [
        {'id': 1, 'title': 'One', 'action': 'update'},
        {'id': 2, 'title': 'Two', 'action': 'update'},
        {'id': 3, 'title': 'Three', 'action': 'mystery'},
    ]
    handler.meta = {'lastsend': 0}
    handler.cache_file = str(tmp_path / 'shows.list')
    handler.queue_file = str(tmp_path / 'shows.queue')
    handler.signals = {
        'show_synced': None,
        'sync_complete': None,
        'queue_changed': None,
        'list_updated': None,
    }
    return handler


def test_process_queue_removes_only_successful_items(tmp_path):
    handler = make_data(tmp_path)

    handler.process_queue()

    assert [item['id'] for item in handler.queue] == [2, 3]
    assert handler.showlist[1]['queued'] is False
    assert handler.showlist[2]['queued'] is True
    assert handler.showlist[3]['queued'] is True
    assert [item['id'] for item in utils.load_data(handler.queue_file)] == [2, 3]
    assert handler.api.logged_out is True


def test_uploading_show_without_queued_changes_leaves_queue_untouched(tmp_path):
    handler = make_data(tmp_path)
    original = list(handler.queue)
    handler.process_queue(show_id=99)
    assert handler.queue == original
    assert handler.meta['lastsend'] == 0
    assert handler.api.logged_out is False


@pytest.fixture
def tracker_confirmation(tmp_path):
    handler = make_data(tmp_path)
    handler.config = {'autosend': 'off'}
    handler.showlist[1].update(my_id=1, my_progress=2, total=12, my_status=1)
    handler.queue = [{'id': 2, 'title': 'Two', 'action': 'update', 'my_progress': 7}]
    sent = []
    fail = [False]

    def update_show(item):
        if fail[0]:
            raise utils.APIError('temporary failure')
        sent.append(dict(item))
        return 123

    handler.api.update_show = update_show
    engine = object.__new__(Engine)
    engine.loaded = True
    engine.data_handler = handler
    engine.msg = handler.msg
    engine.config = {'auto_status_change': False, 'auto_date_change': False}
    engine.mediainfo = {'can_update': True}
    engine._update_tracker = lambda: None
    engine._emit_signal = lambda *_args: None
    controller = BackendController(account_manager=object())
    controller.engine = engine
    return controller, handler, sent, fail


def test_tracker_confirmation_sends_each_episode_without_syncing_other_shows(tracker_confirmation):
    controller, handler, sent, _ = tracker_confirmation
    for episode in (3, 4):
        controller.handle('tracker.update', {'showId': 1, 'episode': episode})

    assert [item['my_progress'] for item in sent] == [3, 4]
    assert handler.showlist[1]['my_progress'] == 4
    assert [item['id'] for item in handler.queue] == [2]
    assert utils.load_data(handler.queue_file) == handler.queue


def test_tracker_confirmation_retries_failed_episode_before_advancing(tracker_confirmation):
    controller, handler, sent, fail = tracker_confirmation
    fail[0] = True
    with pytest.raises(CommandError, match='could not be sent'):
        controller.handle('tracker.update', {'showId': 1, 'episode': 3})
    with pytest.raises(CommandError, match='could not be sent'):
        controller.handle('tracker.update', {'showId': 1, 'episode': 4})
    assert handler.showlist[1]['my_progress'] == 3
    assert handler.queue[-1]['my_progress'] == 3

    fail[0] = False
    controller.handle('tracker.update', {'showId': 1, 'episode': 3})
    controller.handle('tracker.update', {'showId': 1, 'episode': 4})
    controller.handle('tracker.update', {'showId': 1, 'episode': 3})
    assert [item['my_progress'] for item in sent] == [3, 4]


@pytest.mark.parametrize('episode', [0, -1, 13, 'invalid'])
def test_tracker_confirmation_rejects_invalid_episodes(tracker_confirmation, episode):
    controller, handler, sent, _ = tracker_confirmation
    with pytest.raises(CommandError):
        controller.handle('tracker.update', {'showId': 1, 'episode': episode})
    assert sent == []
    assert handler.showlist[1]['my_progress'] == 2


def test_queue_clear_resets_flags_and_persists_cache(tmp_path):
    handler = make_data(tmp_path)

    handler.queue_clear()

    assert handler.queue == []
    assert all(not show['queued'] for show in handler.showlist.values())
    assert utils.load_data(handler.queue_file) == []
    assert all(not show['queued'] for show in utils.load_data(handler.cache_file).values())


def test_private_atomic_writes_preserve_existing_formats(tmp_path):
    config_file = tmp_path / 'config.json'
    data_file = tmp_path / 'cache.pickle'

    utils.save_config({'token': 'secret'}, str(config_file))
    utils.save_data({'value': 1}, str(data_file))

    assert utils.parse_config(str(config_file), {}) == {'token': 'secret'}
    assert utils.load_data(str(data_file)) == {'value': 1}
    assert stat.S_IMODE(config_file.stat().st_mode) == 0o600
    assert stat.S_IMODE(data_file.stat().st_mode) == 0o600
    assert not list(tmp_path.glob('.trackma-*'))


def test_account_storage_component_rejects_path_traversal():
    assert utils.account_data_dirname('user@example.com', 'mal') == 'user@example.com.mal'
    with pytest.raises(utils.TrackmaFatal):
        utils.account_data_dirname('../escape', 'mal')
    with pytest.raises(utils.TrackmaFatal):
        utils.account_data_dirname('user', '..\\escape')


def test_database_lock_creation_is_atomic(tmp_path):
    first = object.__new__(Data)
    first.config = {'debug_disable_lock': False}
    first.lock_file = str(tmp_path / 'lock')
    first._lock_acquired = False
    second = object.__new__(Data)
    second.config = {'debug_disable_lock': False}
    second.lock_file = first.lock_file
    second._lock_acquired = False

    first._lock()
    try:
        assert os.path.exists(first.lock_file)
        with pytest.raises(utils.DataFatal):
            second._lock()
    finally:
        first._unlock()
    assert not os.path.exists(first.lock_file)
