import datetime
from types import SimpleNamespace

from trackma import utils
from trackma.engine import Engine


def make_engine(auto_date_change=True):
    queued = []
    engine = object.__new__(Engine)
    engine.config = {"auto_date_change": auto_date_change}
    engine.mediainfo = {
        "can_add": True,
        "can_date": True,
        "statuses": ["CURRENT", "COMPLETED", "PLANNING"],
        "statuses_start": ["CURRENT"],
    }
    engine.data_handler = SimpleNamespace(queue_add=queued.append)
    engine._update_tracker = lambda: None
    engine._emit_signal = lambda *_args: None
    return engine, queued


def test_add_show_sets_today_as_start_date_for_active_status():
    engine, queued = make_engine()
    show = utils.show()

    engine.add_show(show, "CURRENT")

    assert queued[0]["my_start_date"] == datetime.date.today()


def test_add_show_leaves_start_date_empty_for_planning_status():
    engine, queued = make_engine()
    show = utils.show()

    engine.add_show(show, "PLANNING")

    assert queued[0]["my_start_date"] is None


def test_add_show_respects_disabled_automatic_dates():
    engine, queued = make_engine(auto_date_change=False)
    show = utils.show()

    engine.add_show(show, "CURRENT")

    assert queued[0]["my_start_date"] is None
