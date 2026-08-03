import datetime
import json
import os
import subprocess
import sys

import pytest
from PyQt6 import QtTest, QtWidgets

from trackma import utils
from trackma.ui.web.contract import (
    CommandError,
    error_response,
    normalize_json,
    public_account,
    success_response,
)
from trackma.ui.web.controller import BackendController
from trackma.ui.web.bridge import WebBridge


QT_APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["trackma-web-tests"])


class FakeAccountManager:
    def __init__(self):
        self.accounts = {
            "default": 2,
            "next": 3,
            "accounts": {
                2: {
                    "username": "mina",
                    "password": "secret",
                    "api": "anilist",
                    "extra": {},
                }
            },
        }

    def get_accounts(self):
        return self.accounts["accounts"].items()

    def get_account(self, account_id):
        return self.accounts["accounts"][account_id]

    def set_default(self, account_id):
        self.accounts["default"] = account_id


class FakeEngine:
    def __init__(self, account, message_handler=None):
        self.account = account
        self.message_handler = message_handler
        self.loaded = False
        self.api_info = {
            "name": "AniList",
            "shortname": "anilist",
            "mediatype": "anime",
            "supported_mediatypes": ["anime", "manga"],
        }
        self.mediainfo = {
            "statuses": [1, 2],
            "statuses_dict": {1: "Watching", 2: "Completed"},
            "score_max": 10,
            "score_step": 1,
            "can_play": True,
            "can_add": True,
        }
        self.signals = {}
        self.dates = None
        self.catalog_details_requested = None

    def connect_signal(self, name, callback):
        self.signals[name] = callback

    def start(self):
        self.loaded = True

    def get_list(self):
        return {
            10: {
                "id": 10,
                "title": "Frieren",
                "status": utils.Status.AIRING,
                "next_ep_number": 14,
                "my_status": 1,
                "my_progress": 12,
                "total": 28,
                "my_score": 9,
            }
        }.values()

    def library(self):
        return {10: {1: "/shows/frieren-01.mkv"}}

    def altnames(self):
        return {10: "Sousou no Frieren"}

    def get_queue(self):
        return [{"id": 10, "my_progress": 12}]

    def tracker_status(self):
        return {"state": "wait", "timer": 0}

    def get_userconfig(self, key):
        return {"username": "mina"}[key]

    def get_show_info(self, show_id):
        return next(show for show in self.get_list() if show["id"] == show_id)

    def set_dates(self, show_id, start_date, finish_date):
        self.dates = (show_id, start_date, finish_date)

    def set_episode(self, *_args):
        pass

    set_score = set_episode
    set_status = set_episode
    set_rewatches = set_episode
    set_notes = set_episode
    set_tags = set_episode

    def download_torrent(self, _magnet):
        return False

    def search_torrents_manual(self, _query, category='1_0', page=1, include_page_info=False):
        assert category == '1_2'
        assert page == 1
        assert include_page_info is True
        return {'results': [{'id': 'release-1'}], 'has_next': True}

    def discover_home(self):
        return {
            "capabilities": {
                "mode": "full",
                "filters": ["search", "genres", "year"],
                "supportsHome": True,
            },
            "sections": [
                {
                    "id": "trending",
                    "title": "Trending now",
                    "preset": {"sort": "trending"},
                    "items": [
                        {
                            "id": 11,
                            "title": "Delicious in Dungeon",
                            "total": 24,
                            "_catalog": {"genres": ["Adventure"], "averageScore": 82},
                        }
                    ],
                }
            ],
        }

    def discover_options(self):
        return {
            "genres": [{"value": "Adventure", "label": "Adventure"}],
            "tags": [],
            "formats": [],
            "statuses": [],
            "countries": [],
            "sources": [],
            "streaming": [],
            "sorts": [],
        }

    def discover_browse(self, filters, page=1, per_page=24):
        assert filters == {"search": "dungeon"}
        assert page == 2
        assert per_page == 24
        return {
            "items": [
                {
                    "id": 11,
                    "title": "Delicious in Dungeon",
                    "total": 24,
                    "_catalog": {"genres": ["Adventure"]},
                }
            ],
            "pageInfo": {"currentPage": 2, "lastPage": 4, "total": 80, "hasNextPage": True},
        }

    def get_show_details(self, show):
        self.catalog_details_requested = show
        return {
            **show,
            "_catalog": {
                "description": "A party returns to a dangerous dungeon.",
                "genres": ["Adventure", "Fantasy"],
            },
        }


def test_normalize_json_converts_dates_sets_and_dictionary_keys():
    value = {
        1: datetime.date(2026, 8, 2),
        "updated": datetime.datetime(2026, 8, 2, 12, 30, 45),
        "tags": {"anime", "finished"},
    }

    normalized = normalize_json(value)

    assert normalized["1"] == "2026-08-02"
    assert normalized["updated"] == "2026-08-02T12:30:45"
    assert sorted(normalized["tags"]) == ["anime", "finished"]
    json.dumps(normalized)


def test_library_snapshot_separates_aired_and_downloaded_episodes():
    controller = BackendController(
        account_manager=FakeAccountManager(),
        engine_factory=FakeEngine,
    )
    session = controller.handle("session.open", {"accountId": 2, "remember": True})

    show = session["library"]["shows"][0]

    assert show["airedEpisodes"] == 13
    assert show["availableEpisodes"] == [1]


def test_public_account_never_exposes_credentials_or_oauth_state():
    account = {
        "username": "mina",
        "password": "secret-pin",
        "api": "anilist",
        "extra": {"code_verifier": "private"},
    }

    result = public_account(7, account, service_name="AniList")

    assert result == {
        "id": 7,
        "username": "mina",
        "api": "anilist",
        "serviceName": "AniList",
    }
    assert "secret-pin" not in json.dumps(result)
    assert "private" not in json.dumps(result)


def test_response_envelopes_use_one_predictable_shape():
    assert success_response("req-1", {"ready": True}) == {
        "id": "req-1",
        "ok": True,
        "data": {"ready": True},
    }

    error = CommandError("INVALID_COMMAND", "Unsupported command", {"command": "bad"})
    assert error_response("req-2", error) == {
        "id": "req-2",
        "ok": False,
        "error": {
            "code": "INVALID_COMMAND",
            "message": "Unsupported command",
            "details": {"command": "bad"},
        },
    }


def test_command_error_rejects_empty_codes_and_messages():
    with pytest.raises(ValueError):
        CommandError("", "Missing code")
    with pytest.raises(ValueError):
        CommandError("INVALID", "")


def test_bootstrap_lists_accounts_without_credentials_and_marks_default():
    controller = BackendController(
        account_manager=FakeAccountManager(),
        engine_factory=FakeEngine,
    )

    result = controller.handle("app.bootstrap", {})

    assert result["defaultAccountId"] == 2
    assert result["accounts"] == [
        {"id": 2, "username": "mina", "api": "anilist", "serviceName": "Anilist"}
    ]
    assert "secret" not in json.dumps(result)


def test_open_session_returns_a_normalized_library_snapshot():
    controller = BackendController(
        account_manager=FakeAccountManager(),
        engine_factory=FakeEngine,
    )

    result = controller.handle("session.open", {"accountId": 2, "remember": True})

    assert result["account"]["username"] == "mina"
    assert result["media"]["statusOptions"] == [
        {"value": 1, "label": "Watching"},
        {"value": 2, "label": "Completed"},
    ]
    assert result["library"]["shows"][0]["title"] == "Frieren"
    assert result["library"]["shows"][0]["availableEpisodes"] == [1]
    assert result["library"]["queueCount"] == 1
    assert result["library"]["alternateTitles"] == {"10": "Sousou no Frieren"}


def test_unknown_controller_command_raises_structured_error():
    controller = BackendController(
        account_manager=FakeAccountManager(),
        engine_factory=FakeEngine,
    )

    with pytest.raises(CommandError) as caught:
        controller.handle("system.deleteEverything", {})

    assert caught.value.code == "INVALID_COMMAND"


def test_show_update_converts_iso_dates_before_calling_engine():
    controller = BackendController(
        account_manager=FakeAccountManager(),
        engine_factory=FakeEngine,
    )
    controller.handle("session.open", {"accountId": 2, "remember": True})

    controller.handle(
        "show.update",
        {"showId": 10, "patch": {"startDate": "2026-01-02", "finishDate": "2026-03-04"}},
    )

    assert controller.engine.dates == (
        10,
        datetime.date(2026, 1, 2),
        datetime.date(2026, 3, 4),
    )


def test_torrent_download_reports_qbittorrent_result():
    controller = BackendController(
        account_manager=FakeAccountManager(),
        engine_factory=FakeEngine,
    )
    controller.handle("session.open", {"accountId": 2, "remember": True})

    result = controller.handle("torrents.download", {"magnet": "magnet:?xt=test"})

    assert result == {"downloaded": False}


def test_torrent_search_exposes_page_availability():
    controller = BackendController(
        account_manager=FakeAccountManager(),
        engine_factory=FakeEngine,
    )
    controller.handle("session.open", {"accountId": 2, "remember": True})

    result = controller.handle(
        "torrents.search",
        {"query": "Frieren", "category": "1_2", "page": 1},
    )

    assert result == {"results": [{"id": "release-1"}], "hasNext": True}


def test_discover_home_normalizes_catalog_items_and_marks_library_membership():
    controller = BackendController(
        account_manager=FakeAccountManager(),
        engine_factory=FakeEngine,
    )
    controller.handle("session.open", {"accountId": 2, "remember": True})

    result = controller.handle("discover.home", {})

    item = result["sections"][0]["items"][0]
    assert result["capabilities"]["mode"] == "full"
    assert item["show"]["title"] == "Delicious in Dungeon"
    assert "_catalog" not in item["show"]
    assert item["metadata"] == {"genres": ["Adventure"], "averageScore": 82}
    assert item["inLibrary"] is False


def test_discover_browse_returns_numbered_page_metadata():
    controller = BackendController(
        account_manager=FakeAccountManager(),
        engine_factory=FakeEngine,
    )
    controller.handle("session.open", {"accountId": 2, "remember": True})

    result = controller.handle(
        "discover.browse",
        {"filters": {"search": "dungeon"}, "page": 2, "perPage": 24},
    )

    assert result["pageInfo"] == {
        "currentPage": 2,
        "lastPage": 4,
        "total": 80,
        "hasNextPage": True,
    }
    assert result["items"][0]["metadata"]["genres"] == ["Adventure"]


def test_discover_details_accepts_a_catalog_show_that_is_not_in_the_library():
    controller = BackendController(
        account_manager=FakeAccountManager(),
        engine_factory=FakeEngine,
    )
    controller.handle("session.open", {"accountId": 2, "remember": True})
    catalog_show = {"id": 11, "title": "Delicious in Dungeon", "total": 24}

    result = controller.handle(
        "discover.details",
        {
            "show": catalog_show,
            "metadata": {"season": "FALL", "seasonYear": 2023, "source": "MANGA"},
        },
    )

    assert controller.engine.catalog_details_requested == catalog_show
    assert result["show"] == catalog_show
    assert result["metadata"]["genres"] == ["Adventure", "Fantasy"]
    assert result["metadata"]["season"] == "FALL"
    assert result["metadata"]["seasonYear"] == 2023
    assert result["metadata"]["source"] == "MANGA"


def _bridge_response(bridge, request_id, command, payload):
    spy = QtTest.QSignalSpy(bridge.response)
    bridge.request(request_id, command, payload)
    if not spy:
        assert spy.wait(2000), "Bridge response timed out"
    return json.loads(spy[0][0])


def test_web_bridge_emits_async_success_responses():
    controller = BackendController(
        account_manager=FakeAccountManager(),
        engine_factory=FakeEngine,
    )
    bridge = WebBridge(controller)

    response = _bridge_response(bridge, "request-1", "app.bootstrap", "{}")
    assert response["id"] == "request-1"
    assert response["ok"] is True
    assert response["data"]["defaultAccountId"] == 2
    bridge.close()


def test_web_bridge_returns_structured_errors_for_bad_json():
    controller = BackendController(
        account_manager=FakeAccountManager(),
        engine_factory=FakeEngine,
    )
    bridge = WebBridge(controller)

    response = _bridge_response(bridge, "request-2", "app.bootstrap", "not-json")
    assert response == {
        "id": "request-2",
        "ok": False,
        "error": {
            "code": "INVALID_PAYLOAD",
            "message": "Command payload must be a JSON object",
        },
    }
    bridge.close()


def test_webengine_is_loaded_before_qapplication_is_created():
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from trackma.ui.web import _load_desktop_qt; "
                "qt = _load_desktop_qt(); "
                "app = qt.QtWidgets.QApplication(['trackma-order-test']); "
                "print(qt.QtWebEngineWidgets.QWebEngineView.__name__)"
            ),
        ],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "QWebEngineView"
