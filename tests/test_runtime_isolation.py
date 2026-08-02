import sys
import types

import pytest

from trackma import utils
from trackma.accounts import AccountManager
from trackma.data import Data
from trackma.engine import Engine
from trackma.lib.lib import lib
from trackma.messenger import Messenger
from trackma.tracker.tracker import TrackerBase


MESSENGER = Messenger(None, "RuntimeIsolationTest")


class FakeLib(lib):
    api_info = {'name': 'Fake', 'version': '1', 'merge': False}
    mediatypes = {'anime': {}}
    default_mediatype = 'anime'
    signals = {'show_info_changed': None}


class FakeTracker(TrackerBase):
    def observe(self, _config, _watch_dirs):
        while self.active:
            self._stop_event.wait(0.01)


def test_engine_runtime_state_and_signals_are_instance_local(monkeypatch):
    monkeypatch.setattr(Engine, '_load', lambda self, account: None)
    monkeypatch.setattr(Engine, '_init_data_handler', lambda self: None)

    first = Engine()
    second = Engine()
    first.hooks_available.append(object())
    first.connect_signal('show_added', lambda _show: None)

    assert second.hooks_available == []
    assert second.signals['show_added'] is None

    with pytest.raises(utils.EngineFatal):
        first.connect_signal('not-a-signal', lambda: None)

    def broken_callback(_show):
        raise AttributeError('callback bug')

    first.connect_signal('show_added', broken_callback)
    with pytest.raises(AttributeError, match='callback bug'):
        first._emit_signal('show_added', {})


def test_data_runtime_state_is_instance_local(monkeypatch):
    fake_module = types.ModuleType('trackma.lib.libfake')
    fake_module.libfake = FakeLib
    monkeypatch.setitem(sys.modules, 'trackma.lib.libfake', fake_module)
    monkeypatch.setattr(Data, '_load_userconfig',
                        lambda self: setattr(self, 'userconfig', {'mediatype': 'anime'}))
    monkeypatch.setattr(utils, 'to_data_path', lambda *parts: '/'.join(parts))

    account = {'username': 'user', 'api': 'fake'}
    first = Data(MESSENGER, {}, account, None)
    second = Data(MESSENGER, {}, account, None)
    first.queue.append({'id': 1})
    first.meta['library'][1] = {'episode': 1}
    first.connect_signal('queue_changed', lambda _queue: None)

    assert second.queue == []
    assert second.meta['library'] == {}
    assert second.signals['queue_changed'] is None
    assert first.api.signals['show_info_changed'] is not None
    assert first.api.signals['userconfig_changed'] is not None
    with pytest.raises(utils.DataFatal):
        first.connect_signal('not-a-signal', lambda: None)


def test_api_and_tracker_runtime_state_is_instance_local():
    first_api = FakeLib(MESSENGER, {}, {'mediatype': 'anime'})
    second_api = FakeLib(MESSENGER, {}, {'mediatype': 'anime'})
    first_api.api_info['custom'] = True
    first_api.connect_signal('show_info_changed', lambda _show: None)

    assert 'custom' not in second_api.api_info
    assert second_api.signals['show_info_changed'] is None
    with pytest.raises(utils.EngineFatal):
        first_api.connect_signal('not-a-signal', lambda: None)

    config = {'title_parser': 'aie'}
    first_tracker = FakeTracker(MESSENGER, ({}, {}), config, [])
    second_tracker = FakeTracker(MESSENGER, ({}, {}), config, [])
    assert first_tracker._thread is None
    first_tracker.connect_signal('state', lambda _state: None)
    assert second_tracker.signals['state'] is None
    with pytest.raises(utils.EngineFatal):
        first_tracker.connect_signal('not-a-signal', lambda: None)

    first_tracker.start()
    assert first_tracker._thread.is_alive()
    first_tracker.disable()
    assert not first_tracker._thread.is_alive()


def test_api_subclasses_keep_required_base_signals():
    api = FakeLib(MESSENGER, {}, {'mediatype': 'anime'})

    api.connect_signal('userconfig_changed', lambda: None)

    assert api.signals['userconfig_changed'] is not None
    with pytest.raises(utils.EngineFatal):
        api.connect_signal('not-a-signal', lambda: None)


def test_account_manager_defaults_are_instance_local(monkeypatch, tmp_path):
    monkeypatch.setattr(utils, 'to_config_path',
                        lambda *parts: str(tmp_path.joinpath(*parts)))
    first = AccountManager()
    second = AccountManager()
    first.accounts['accounts'][1] = {'username': 'first'}

    assert second.accounts['accounts'] == {}
