import os
import stat

import pytest

from trackma import utils
from trackma.data import Data


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
