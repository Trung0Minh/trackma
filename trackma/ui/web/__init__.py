"""Trackma React desktop interface."""

from __future__ import annotations

import argparse
import os
import sys
from types import SimpleNamespace

from trackma import utils


def _load_desktop_qt() -> SimpleNamespace:
    """Load WebEngine before QApplication, as required by Qt."""
    from PyQt6 import (
        QtCore,
        QtNetwork,
        QtWebChannel,
        QtWebEngineCore,
        QtWebEngineWidgets,
        QtWidgets,
    )

    return SimpleNamespace(
        QtCore=QtCore,
        QtNetwork=QtNetwork,
        QtWebChannel=QtWebChannel,
        QtWebEngineCore=QtWebEngineCore,
        QtWebEngineWidgets=QtWebEngineWidgets,
        QtWidgets=QtWidgets,
    )


def _arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="trackma")
    parser.add_argument("-d", "--debug", action="store_true", help="show debugging information")
    parser.add_argument("--dev-url", help="load a running Vite development server")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _arguments(list(sys.argv[1:] if argv is None else argv))
    try:
        qt = _load_desktop_qt()
    except ImportError:
        print("Trackma's desktop UI requires PyQt6 and PyQt6-WebEngine.")
        return 1

    QtCore = qt.QtCore
    QtNetwork = qt.QtNetwork
    QtWidgets = qt.QtWidgets

    if os.name == "nt":
        import ctypes

        getattr(ctypes, "windll").shell32.SetCurrentProcessExplicitAppUserModelID(
            "trackma" + utils.VERSION
        )

    app = QtWidgets.QApplication([sys.argv[0], *(argv or sys.argv[1:])])
    app.setApplicationName("trackma")
    app.setApplicationDisplayName("Trackma")
    app.setDesktopFileName("trackma")
    app.setWindowIcon(QtWidgets.QApplication.windowIcon())

    socket = QtNetwork.QLocalSocket()
    socket.connectToServer("trackma-web")
    if socket.waitForConnected(500):
        socket.write(b"show")
        socket.waitForBytesWritten(500)
        return 0

    lock_file = QtCore.QLockFile(QtCore.QDir.tempPath() + "/trackma-web.lock")
    if not lock_file.tryLock(100):
        print("Trackma is already running.")
        return 1

    try:
        from .window import WebMainWindow

        window = WebMainWindow(debug=args.debug, dev_url=args.dev_url)
    except RuntimeError as error:
        QtWidgets.QMessageBox.critical(None, "Trackma", str(error))
        return 1

    server = QtNetwork.QLocalServer(app)
    QtNetwork.QLocalServer.removeServer("trackma-web")
    server.listen("trackma-web")

    def show_existing_window() -> None:
        connection = server.nextPendingConnection()
        if connection is None:
            return
        connection.waitForReadyRead(250)
        if bytes(connection.readAll()) == b"show":
            window.show_and_raise()
        connection.disconnectFromServer()

    server.newConnection.connect(show_existing_window)
    app.main_window = window
    app.single_instance_server = server
    app.single_instance_lock = lock_file
    window.show()
    return app.exec()


__all__ = ["main"]
