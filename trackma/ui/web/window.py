"""Native Qt host for Trackma's React interface."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from PyQt6 import QtCore, QtGui, QtWidgets

from trackma import utils

from .bridge import WebBridge
from .contract import CommandError
from .controller import BackendController


WEB_DEFAULTS = {
    "show_tray": True,
    "close_to_tray": True,
    "start_in_tray": False,
    "notifications": True,
    "remember_geometry": True,
    "last_x": 80,
    "last_y": 80,
    "last_width": 1280,
    "last_height": 820,
    "theme_mode": "dark",
    "view_mode": "grid",
    "visible_columns": ["Title", "Progress", "Score", "Percent"],
}


def load_web_config() -> tuple[dict[str, Any], str]:
    configfile = utils.to_config_path("ui-web.json")
    if os.path.isfile(configfile):
        return utils.parse_config(configfile, WEB_DEFAULTS), configfile

    config = dict(WEB_DEFAULTS)
    legacy_file = utils.to_config_path("ui-qt.json")
    if os.path.isfile(legacy_file):
        legacy = utils.parse_config(legacy_file, utils.qt_defaults)
        for key in WEB_DEFAULTS:
            if key in legacy:
                config[key] = legacy[key]
    return config, configfile


def frontend_entrypoint() -> Path:
    return Path(__file__).resolve().parent / "assets" / "index.html"


class WebMainWindow(QtWidgets.QMainWindow):
    def __init__(self, debug: bool = False, dev_url: str | None = None) -> None:
        super().__init__()
        try:
            from PyQt6 import QtWebChannel, QtWebEngineCore, QtWebEngineWidgets
        except ImportError as error:
            raise RuntimeError(
                "PyQt6-WebEngine is required. Install Trackma with the 'ui' extra."
            ) from error

        self._webengine_core = QtWebEngineCore
        self._quitting = False
        self.debug = debug
        self.config, self.configfile = load_web_config()
        self.setWindowTitle("Trackma")
        self.setMinimumSize(760, 560)
        self.setWindowIcon(QtGui.QIcon(utils.DATADIR + "/icon.png"))

        if self.config.get("remember_geometry"):
            self.setGeometry(
                int(self.config["last_x"]),
                int(self.config["last_y"]),
                int(self.config["last_width"]),
                int(self.config["last_height"]),
            )
        else:
            self.resize(1280, 820)

        self.controller = BackendController()
        self.bridge = WebBridge(self.controller, self._native_command, self)
        self.bridge.event.connect(self._native_event)

        self.web_view = QtWebEngineWidgets.QWebEngineView(self)
        settings = self.web_view.settings()
        if settings is None:
            raise RuntimeError("Qt WebEngine settings are unavailable")
        settings.setAttribute(
            QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            True,
        )
        settings.setAttribute(
            QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            True,
        )
        page = self.web_view.page()
        if page is None:
            raise RuntimeError("Qt WebEngine page is unavailable")
        self.channel = QtWebChannel.QWebChannel(page)
        self.channel.registerObject("trackmaBridge", self.bridge)
        page.setWebChannel(self.channel)
        self.setCentralWidget(self.web_view)

        if dev_url:
            self.web_view.setUrl(QtCore.QUrl(dev_url))
        else:
            entrypoint = frontend_entrypoint()
            if not entrypoint.is_file():
                raise RuntimeError(
                    "The web frontend is not built. Run 'npm run build' in "
                    "trackma/ui/web/frontend."
                )
            self.web_view.setUrl(QtCore.QUrl.fromLocalFile(str(entrypoint)))

        self._build_tray()
        if self.config.get("start_in_tray") and self.tray.isVisible():
            QtCore.QTimer.singleShot(0, self.hide)

    def _build_tray(self) -> None:
        self.tray = QtWidgets.QSystemTrayIcon(self.windowIcon(), self)
        menu = QtWidgets.QMenu(self)
        show_action = QtGui.QAction("Show Trackma", menu)
        menu.addAction(show_action)
        show_action.triggered.connect(self.show_and_raise)
        menu.addSeparator()
        quit_action = QtGui.QAction("Quit", menu)
        menu.addAction(quit_action)
        quit_action.triggered.connect(self.quit_application)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        if self.config.get("show_tray") and QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def _tray_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            self.show_and_raise()

    def show_and_raise(self) -> None:
        self.show()
        if self.isMinimized():
            self.showNormal()
        self.activateWindow()
        self.raise_()

    def _native_command(self, command: str, payload: dict[str, Any]) -> Any:
        if command == "native.openExternal":
            url = QtCore.QUrl(str(payload.get("url", "")))
            if url.scheme() not in {"http", "https"} or not url.isValid():
                raise CommandError("INVALID_INPUT", "Only HTTP and HTTPS links can be opened")
            if not QtGui.QDesktopServices.openUrl(url):
                raise CommandError("NATIVE_ERROR", "The link could not be opened")
            return {"opened": True}
        if command == "native.pickPlayer":
            filename, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
                self, "Choose media player", str(payload.get("current", ""))
            )
            return {"path": filename or None}
        if command == "native.pickDirectory":
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                self, "Choose media directory", str(payload.get("current", ""))
            )
            return {"path": directory or None}
        if command == "native.windowConfig":
            allowed = {
                "show_tray",
                "close_to_tray",
                "start_in_tray",
                "notifications",
                "remember_geometry",
                "theme_mode",
                "view_mode",
                "visible_columns",
                "last_x",
                "last_y",
                "last_width",
                "last_height",
            }
            updates = payload.get("settings") or {}
            unknown = set(updates) - allowed
            if unknown:
                raise CommandError("INVALID_INPUT", "Unsupported interface settings", sorted(unknown))
            self.config.update(updates)
            utils.save_config(self.config, self.configfile)
            self.tray.setVisible(
                bool(self.config.get("show_tray"))
                and QtWidgets.QSystemTrayIcon.isSystemTrayAvailable()
            )
            return {key: self.config[key] for key in allowed}
        if command == "native.getWindowConfig":
            return dict(self.config)
        raise CommandError("INVALID_COMMAND", "Unsupported native command", {"command": command})

    @QtCore.pyqtSlot(str)
    def _native_event(self, event_json: str) -> None:
        if not self.config.get("notifications") or not self.tray.isVisible():
            return
        try:
            event = json.loads(event_json)
        except json.JSONDecodeError:
            return
        if event.get("name") != "playing":
            return
        payload = event.get("payload") or []
        if len(payload) >= 3 and payload[1]:
            show = payload[0] or {}
            self.tray.showMessage(
                "Trackma tracker",
                f"Playing {show.get('title', 'media')} episode {payload[2]}",
            )

    def closeEvent(self, event: QtGui.QCloseEvent | None) -> None:
        if event is None:
            return
        if (
            not self._quitting
            and self.config.get("show_tray")
            and self.config.get("close_to_tray")
            and self.tray.isVisible()
        ):
            event.ignore()
            self.hide()
            return
        event.accept()
        if not self._quitting:
            self.quit_application()

    @QtCore.pyqtSlot()
    def quit_application(self) -> None:
        if self._quitting:
            return
        self._quitting = True
        if self.config.get("remember_geometry"):
            geometry = self.normalGeometry()
            self.config.update(
                {
                    "last_x": geometry.x(),
                    "last_y": geometry.y(),
                    "last_width": geometry.width(),
                    "last_height": geometry.height(),
                }
            )
        utils.save_config(self.config, self.configfile)
        self.bridge.close()
        self.tray.hide()
        application = QtWidgets.QApplication.instance()
        if application is not None:
            application.quit()
