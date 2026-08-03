"""Synchronous Trackma backend commands executed by the web bridge worker."""

from __future__ import annotations

import datetime
import uuid
from collections.abc import Callable
from typing import Any, cast

from trackma import utils
from trackma.accounts import AccountManager
from trackma.engine import Engine

from .contract import CommandError, normalize_json, public_account


EventCallback = Callable[[str, Any], None]
EngineFactory = Callable[..., Engine]


class BackendController:
    """Own the active engine and expose a small, explicit command surface."""

    ENGINE_SIGNALS = (
        "episode_changed",
        "score_changed",
        "show_changed",
        "status_changed",
        "playing",
        "show_added",
        "show_deleted",
        "show_synced",
        "queue_changed",
        "prompt_for_update",
        "prompt_for_add",
        "tracker_state",
        "library_updated",
        "sync_complete",
    )

    def __init__(
        self,
        account_manager: AccountManager | None = None,
        engine_factory: EngineFactory = Engine,
        event_callback: EventCallback | None = None,
        process_launcher: Callable[[list[str]], Any] = utils.spawn_process,
    ) -> None:
        self.account_manager = account_manager or AccountManager()
        self.engine_factory = engine_factory
        self.event_callback = event_callback or (lambda _name, _payload: None)
        self.process_launcher = process_launcher
        self.engine: Engine | None = None
        self.active_account_id: int | None = None
        self._auth_sessions: dict[str, dict[str, Any]] = {}

        self._commands: dict[str, Callable[[dict[str, Any]], Any]] = {
            "app.bootstrap": self._bootstrap,
            "app.shutdown": self._shutdown,
            "accounts.beginAuth": self._begin_auth,
            "accounts.save": self._save_account,
            "accounts.delete": self._delete_account,
            "accounts.purge": self._purge_account,
            "session.open": self._open_session,
            "session.switchMediaType": self._switch_media_type,
            "library.snapshot": self._library_snapshot,
            "library.scan": self._scan_library,
            "sync.download": self._sync_download,
            "sync.upload": self._sync_upload,
            "show.details": self._show_details,
            "show.update": self._update_show,
            "show.delete": self._delete_show,
            "show.setAltTitle": self._set_alt_title,
            "show.play": self._play_show,
            "show.playRandom": self._play_random,
            "show.openFolder": self._open_folder,
            "discover.home": self._discover_home,
            "discover.options": self._discover_options,
            "discover.browse": self._discover_browse,
            "discover.details": self._discover_details,
            "discover.search": self._discover_search,
            "discover.add": self._discover_add,
            "torrents.search": self._torrent_search,
            "torrents.details": self._torrent_details,
            "torrents.download": self._torrent_download,
            "settings.get": self._settings_get,
            "settings.save": self._settings_save,
        }

    def handle(self, command: str, payload: dict[str, Any] | None) -> Any:
        handler = self._commands.get(command)
        if handler is None:
            raise CommandError(
                "INVALID_COMMAND",
                "Unsupported command",
                {"command": command},
            )
        try:
            return normalize_json(handler(payload or {}))
        except CommandError:
            raise
        except (utils.TrackmaError, utils.AccountError) as error:
            raise CommandError("TRACKMA_ERROR", str(error)) from error
        except KeyError as error:
            raise CommandError("NOT_FOUND", "The requested item was not found") from error
        except (TypeError, ValueError) as error:
            raise CommandError("INVALID_INPUT", str(error)) from error

    def _service_name(self, api: str) -> str:
        service = utils.available_libs.get(api)
        return str(service[0]) if service else api

    def _accounts(self) -> list[dict[str, Any]]:
        return [
            public_account(account_id, account, self._service_name(account["api"]))
            for account_id, account in self.account_manager.get_accounts()
        ]

    def _services(self) -> list[dict[str, Any]]:
        login_modes = {
            utils.Login.PASSWD: "password",
            utils.Login.OAUTH: "oauth",
            utils.Login.OAUTH_PKCE: "oauthPkce",
        }
        return [
            {
                "api": api,
                "name": service[0],
                "loginMode": login_modes[cast(utils.Login, service[2])],
                "requiresExternalAuth": cast(utils.Login, service[2]) is not utils.Login.PASSWD,
            }
            for api, service in sorted(utils.available_libs.items())
        ]

    def _bootstrap(self, _payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "version": utils.VERSION,
            "accounts": self._accounts(),
            "services": self._services(),
            "defaultAccountId": self.account_manager.accounts.get("default"),
            "activeAccountId": self.active_account_id,
        }

    def _begin_auth(self, payload: dict[str, Any]) -> dict[str, Any]:
        api = str(payload.get("api", ""))
        if api not in utils.available_libs:
            raise CommandError("INVALID_INPUT", "Unknown service")
        service = utils.available_libs[api]
        if service[2] is utils.Login.PASSWD:
            return {"authSessionId": None, "url": None}

        extra: dict[str, Any] = {}
        auth_url = str(service[3])
        if service[2] is utils.Login.OAUTH_PKCE:
            extra["code_verifier"] = utils.oauth_generate_pkce()
            auth_url %= extra["code_verifier"]

        session_id = uuid.uuid4().hex
        self._auth_sessions[session_id] = {"api": api, "extra": extra}
        return {"authSessionId": session_id, "url": auth_url}

    def _save_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        account_id = payload.get("accountId")
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("secret", ""))
        api = str(payload.get("api", ""))
        extra: dict[str, Any] = {}
        auth_session_id = payload.get("authSessionId")
        if auth_session_id:
            session = self._auth_sessions.pop(str(auth_session_id), None)
            if not session or session["api"] != api:
                raise CommandError("INVALID_AUTH_SESSION", "Authorization session expired")
            extra = session["extra"]

        if account_id is None:
            self.account_manager.add_account(username, password, api, extra)
        else:
            self.account_manager.edit_account(int(account_id), username, password, api, extra)
        return self._bootstrap({})

    def _delete_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        account_id = int(payload["accountId"])
        if account_id == self.active_account_id:
            self._shutdown({})
        self.account_manager.delete_account(account_id)
        return self._bootstrap({})

    def _purge_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.account_manager.purge_account(int(payload["accountId"]))
        return {"purged": True}

    def _connect_engine_signals(self) -> None:
        if self.engine is None:
            raise CommandError("NO_ACTIVE_SESSION", "Select an account first")
        engine = self.engine
        for signal_name in self.ENGINE_SIGNALS:
            engine.connect_signal(
                signal_name,
                lambda *args, name=signal_name: self.event_callback(name, normalize_json(args)),
            )

    def _message_handler(self, classname: str, msgtype: int, message: str) -> None:
        self.event_callback(
            "message",
            {"source": classname, "level": msgtype, "message": message},
        )

    def _open_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        account_id = int(payload["accountId"])
        if self.engine and self.engine.loaded:
            self.engine.unload()
        account = self.account_manager.get_account(account_id)
        self.engine = self.engine_factory(account, self._message_handler)
        self.active_account_id = account_id
        self._connect_engine_signals()
        self.engine.start()
        if payload.get("remember"):
            self.account_manager.set_default(account_id)
        elif payload.get("remember") is False:
            self.account_manager.set_default(None)
        return self._session_snapshot()

    def _switch_media_type(self, payload: dict[str, Any]) -> dict[str, Any]:
        engine = self._require_engine()
        media_type = str(payload["mediaType"])
        if media_type not in engine.api_info.get("supported_mediatypes", []):
            raise CommandError("INVALID_INPUT", "Unsupported media type")
        engine.reload(mediatype=media_type)
        self._connect_engine_signals()
        return self._session_snapshot()

    def _session_snapshot(self) -> dict[str, Any]:
        engine = self._require_engine()
        account_id = self.active_account_id
        if account_id is None:
            raise CommandError("NO_ACTIVE_SESSION", "Select an account first")
        account = self.account_manager.get_account(account_id)
        return {
            "account": public_account(
                account_id,
                account,
                self._service_name(account["api"]),
            ),
            "api": engine.api_info,
            "media": self._media_info(),
            "library": self._library_snapshot({}),
        }

    def _media_info(self) -> dict[str, Any]:
        media = self._require_engine().mediainfo
        search_names = {
            utils.SearchMethod.KW: "keyword",
            utils.SearchMethod.SEASON: "season",
        }
        return {
            **media,
            "statusOptions": [
                {"value": status, "label": media["statuses_dict"][status]}
                for status in media.get("statuses", [])
            ],
            "searchMethods": [
                search_names[method]
                for method in media.get("search_methods", [utils.SearchMethod.KW])
            ],
        }

    def _library_snapshot(self, _payload: dict[str, Any]) -> dict[str, Any]:
        engine = self._require_engine()
        local_library = engine.library() or {}
        shows = []
        for show in engine.get_list() or []:
            item = dict(show)
            episodes = local_library.get(show["id"], {})
            item["availableEpisodes"] = sorted(int(episode) for episode in episodes)
            item["airedEpisodes"] = (
                utils.estimate_aired_episodes(show)
                if engine.api_info.get("mediatype") == "anime"
                else 0
            )
            shows.append(item)
        shows.sort(key=lambda item: str(item.get("title", "")).casefold())
        return {
            "shows": shows,
            "alternateTitles": engine.altnames() or {},
            "queueCount": len(engine.get_queue() or []),
            "tracker": engine.tracker_status(),
        }

    def _require_engine(self) -> Engine:
        if self.engine is None or not self.engine.loaded:
            raise CommandError("NO_ACTIVE_SESSION", "Select an account first")
        return self.engine

    def _shutdown(self, _payload: dict[str, Any]) -> dict[str, Any]:
        if self.engine and self.engine.loaded:
            self.engine.unload()
        self.engine = None
        self.active_account_id = None
        return {"closed": True}

    def _scan_library(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_engine().scan_library(rescan=bool(payload.get("rescan")))
        return self._library_snapshot({})

    def _sync_download(self, _payload: dict[str, Any]) -> dict[str, Any]:
        self._require_engine().list_download()
        return self._library_snapshot({})

    def _sync_upload(self, _payload: dict[str, Any]) -> dict[str, Any]:
        self._require_engine().list_upload()
        return self._library_snapshot({})

    def _show_details(self, payload: dict[str, Any]) -> dict[str, Any]:
        engine = self._require_engine()
        show = engine.get_show_info(payload["showId"])
        return {"show": show, "details": engine.get_show_details(show)}

    def _update_show(self, payload: dict[str, Any]) -> dict[str, Any]:
        engine = self._require_engine()
        show_id = payload["showId"]
        patch = payload.get("patch") or {}
        setters = {
            "progress": engine.set_episode,
            "score": engine.set_score,
            "status": engine.set_status,
            "rewatches": engine.set_rewatches,
            "notes": engine.set_notes,
            "tags": engine.set_tags,
        }
        unknown = set(patch) - set(setters) - {"startDate", "finishDate"}
        if unknown:
            raise CommandError("INVALID_INPUT", "Unsupported media fields", sorted(unknown))
        for field, setter in setters.items():
            if field in patch:
                setter(show_id, patch[field])
        if "startDate" in patch or "finishDate" in patch:
            try:
                start_date = datetime.date.fromisoformat(patch["startDate"]) if patch.get("startDate") else None
                finish_date = datetime.date.fromisoformat(patch["finishDate"]) if patch.get("finishDate") else None
            except (TypeError, ValueError) as exc:
                raise CommandError("INVALID_INPUT", "Dates must use YYYY-MM-DD format") from exc
            engine.set_dates(show_id, start_date, finish_date)
        return engine.get_show_info(show_id)

    def _delete_show(self, payload: dict[str, Any]) -> dict[str, Any]:
        engine = self._require_engine()
        engine.delete_show(engine.get_show_info(payload["showId"]))
        return self._library_snapshot({})

    def _set_alt_title(self, payload: dict[str, Any]) -> dict[str, Any]:
        engine = self._require_engine()
        engine.altname(payload["showId"], str(payload.get("title", "")))
        return self._library_snapshot({})

    def _play_show(self, payload: dict[str, Any]) -> dict[str, Any]:
        engine = self._require_engine()
        show = engine.get_show_info(payload["showId"])
        command = engine.play_episode(show, int(payload.get("episode", 0)))
        if command:
            self.process_launcher(list(command))
        return {"launched": bool(command)}

    def _play_random(self, _payload: dict[str, Any]) -> dict[str, Any]:
        command = self._require_engine().play_random()
        if command:
            self.process_launcher(list(command))
        return {"launched": bool(command)}

    def _open_folder(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_engine().open_show_folder(payload["showId"])
        return {"opened": True}

    def _discover_search(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        method_name = str(payload.get("method", "keyword"))
        methods = {"keyword": utils.SearchMethod.KW, "season": utils.SearchMethod.SEASON}
        if method_name not in methods:
            raise CommandError("INVALID_INPUT", "Unsupported search method")
        criteria: Any
        if method_name == "season":
            criteria = (utils.Season.find(payload.get("season")), int(payload["year"]))
        else:
            criteria = str(payload.get("query", "")).strip()
            if not criteria:
                raise CommandError("INVALID_INPUT", "Enter a search term")
        return self._require_engine().search(criteria, methods[method_name]) or []

    def _catalog_item(
        self,
        raw_show: dict[str, Any],
        library_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        show = dict(raw_show)
        metadata = dict(show.pop("_catalog", {}) or {})
        extra = show.get("extra") or []
        if isinstance(extra, list):
            extra_map = {
                str(key).casefold(): value
                for entry in extra
                if isinstance(entry, (list, tuple)) and len(entry) == 2
                for key, value in [entry]
            }
            if extra_map:
                metadata.setdefault("description", extra_map.get("synopsis"))
                metadata.setdefault("genres", extra_map.get("genres") or [])
                metadata.setdefault("studios", extra_map.get("studios") or [])
                metadata.setdefault("averageScore", extra_map.get("average score"))
                metadata.setdefault("meanScore", extra_map.get("mean score"))
        if library_ids is None:
            library_ids = {
                str(item["id"])
                for item in self._require_engine().get_list() or []
            }
        return {
            "show": show,
            "metadata": metadata,
            "inLibrary": str(show.get("id")) in library_ids,
        }

    def _discover_home(self, _payload: dict[str, Any]) -> dict[str, Any]:
        result = self._require_engine().discover_home()
        library_ids = {
            str(item["id"])
            for item in self._require_engine().get_list() or []
        }
        return {
            "capabilities": result.get("capabilities", {}),
            "sections": [
                {
                    **section,
                    "items": [
                        self._catalog_item(item, library_ids)
                        for item in section.get("items", [])
                    ],
                }
                for section in result.get("sections", [])
            ],
        }

    def _discover_options(self, _payload: dict[str, Any]) -> dict[str, Any]:
        return self._require_engine().discover_options()

    def _discover_browse(self, payload: dict[str, Any]) -> dict[str, Any]:
        filters = payload.get("filters") or {}
        if not isinstance(filters, dict):
            raise CommandError("INVALID_INPUT", "Discover filters must be an object")
        page = max(1, int(payload.get("page", 1)))
        per_page = min(50, max(1, int(payload.get("perPage", 24))))
        result = self._require_engine().discover_browse(filters, page=page, per_page=per_page)
        library_ids = {
            str(item["id"])
            for item in self._require_engine().get_list() or []
        }
        return {
            "items": [
                self._catalog_item(item, library_ids)
                for item in result.get("items", [])
            ],
            "pageInfo": result.get("pageInfo", {}),
        }

    def _discover_details(self, payload: dict[str, Any]) -> dict[str, Any]:
        show = payload.get("show")
        if not isinstance(show, dict) or "id" not in show:
            raise CommandError("INVALID_INPUT", "A catalog show is required")
        details = self._require_engine().get_show_details(show)
        item = self._catalog_item(details)
        browse_metadata = payload.get("metadata")
        if isinstance(browse_metadata, dict):
            item["metadata"] = {**browse_metadata, **item["metadata"]}
        return item

    def _discover_add(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_engine().add_show(payload["show"], payload.get("status"))
        return self._library_snapshot({})

    def _torrent_search(self, payload: dict[str, Any]) -> Any:
        result = self._require_engine().search_torrents_manual(
            str(payload.get("query", "")),
            category=str(payload.get("category", "1_0")),
            page=int(payload.get("page", 1)),
            include_page_info=True,
        )
        return {
            "results": result.get("results", []),
            "hasNext": bool(result.get("has_next")),
        }

    def _torrent_details(self, payload: dict[str, Any]) -> Any:
        return self._require_engine().get_torrent_description(str(payload["url"]))

    def _torrent_download(self, payload: dict[str, Any]) -> dict[str, Any]:
        downloaded = self._require_engine().download_torrent(str(payload["magnet"]))
        return {"downloaded": bool(downloaded)}

    def _settings_get(self, _payload: dict[str, Any]) -> dict[str, Any]:
        engine = self._require_engine()
        return {key: engine.get_config(key) for key in utils.config_defaults}

    def _settings_save(self, payload: dict[str, Any]) -> dict[str, Any]:
        engine = self._require_engine()
        settings = payload.get("settings") or {}
        unknown = set(settings) - set(utils.config_defaults)
        if unknown:
            raise CommandError("INVALID_INPUT", "Unsupported settings", sorted(unknown))
        for key, value in settings.items():
            engine.set_config(key, value)
        engine.save_config()
        engine.apply_config()
        return self._settings_get({})
