import pytest

from trackma import utils
from trackma.messenger import Messenger
from trackma.tracker.tracker import TrackerBase


@pytest.fixture
def tracker(monkeypatch):
    clock = [100]
    monkeypatch.setattr('trackma.tracker.tracker.time.time', lambda: clock[0])
    show = {'id': 1, 'title': 'Test show', 'titles': ['Test show'], 'my_progress': 3, 'total': 12}
    tracker = TrackerBase(Messenger(None, 'Test'), ({1: show}, {}), dict(utils.config_defaults), [])
    tracker.config.update(tracker_update_prompt=True, tracker_update_wait_s=10,
                          tracker_ignore_not_next=True, tracker_update_close=False)
    updates = []
    tracker.connect_signal('update', lambda show, episode: updates.append((show['id'], episode)))
    return tracker, show, updates, clock


@pytest.mark.parametrize('update_close', [False, True])
def test_unanswered_prompt_allows_consecutive_episodes(tracker, update_close):
    tracker, show, updates, clock = tracker
    tracker.config['tracker_update_close'] = update_close
    for episode in (4, 5, 6):
        tracker.update_show_if_needed(utils.Tracker.PLAYING, (show, episode))
        clock[0] += 11
        tracker.update_show_if_needed(utils.Tracker.PLAYING, (show, episode))
    tracker.update_show_if_needed(utils.Tracker.NOVIDEO, None)

    assert updates == [(1, 4), (1, 5), (1, 6)]
    assert show['my_progress'] == 3
    assert tracker.pending_episodes == {1: 6}
    tracker.update_list(({1: {**show, 'my_progress': 6}}, {}))
    assert tracker.pending_episodes == {}


def test_pending_progress_does_not_allow_skipped_or_unfinished_episodes(tracker):
    tracker, show, updates, clock = tracker
    tracker.update_show_if_needed(utils.Tracker.PLAYING, (show, 4))
    tracker.update_show_if_needed(utils.Tracker.PLAYING, (show, 5))
    assert tracker.last_state == utils.Tracker.IGNORED
    assert updates == []

    tracker.update_show_if_needed(utils.Tracker.PLAYING, (show, 4))
    clock[0] += 11
    tracker.update_show_if_needed(utils.Tracker.PLAYING, (show, 4))
    tracker.update_show_if_needed(utils.Tracker.PLAYING, (show, 6))
    assert tracker.last_state == utils.Tracker.IGNORED
    assert updates == [(1, 4)]


def test_pending_progress_is_per_show_and_tracker_instance(tracker):
    tracker, show, updates, clock = tracker
    tracker.update_show_if_needed(utils.Tracker.PLAYING, (show, 4))
    clock[0] += 11
    tracker.update_show_if_needed(utils.Tracker.PLAYING, (show, 4))
    other_show = {**show, 'id': 2}
    tracker.update_show_if_needed(utils.Tracker.PLAYING, (other_show, 5))
    assert tracker.last_state == utils.Tracker.IGNORED
    other = TrackerBase(Messenger(None, 'Test'), ({1: show}, {}), tracker.config, [])
    assert other.pending_episodes == {}
    tracker.update_list(({}, {}))
    assert tracker.pending_episodes == {}


def test_automatic_updates_still_use_saved_progress(tracker):
    tracker, show, updates, clock = tracker
    tracker.config['tracker_update_prompt'] = False
    tracker.update_show_if_needed(utils.Tracker.PLAYING, (show, 4))
    clock[0] += 11
    tracker.update_show_if_needed(utils.Tracker.PLAYING, (show, 4))
    assert updates == [(1, 4)]
    assert tracker.pending_episodes == {}
    tracker.update_show_if_needed(utils.Tracker.PLAYING, (show, 5))
    assert tracker.last_state == utils.Tracker.IGNORED
