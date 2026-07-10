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


import os
import sys

from trackma import utils
from trackma.ui.qt.mainwindow import MainWindow


def main():
    print("Trackma-qt v{}".format(utils.VERSION))

    debug = False

    if '-h' in sys.argv:
        print("Usage: trackma-qt [options]")
        print()
        print('Options:')
        print(' -d  Shows debugging information')
        print(' -h  Shows this help')
        sys.exit(0)
    if '-d' in sys.argv:
        print('Showing debug information.')
        debug = True

    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        from PyQt6.QtCore import QLockFile, QDir
        from PyQt6.QtNetwork import QLocalSocket
    except ImportError:
        print("Couldn't import Qt6 dependencies. "
              "Make sure you installed the PyQt6 package.")

    try:
        from PIL import Image
        os.environ['imaging_available'] = "1"
    except ImportError:
        print("Warning: PIL or Pillow isn't available. "
              "Preview images will be disabled.")

    app = QApplication(sys.argv)
    # Import stylesheet and apply
    from trackma.ui.qt.styles import QSS_STYLESHEET
    app.setStyleSheet(QSS_STYLESHEET)
    app.setApplicationName("trackma")
    app.setDesktopFileName("trackma-qt")

    # Single instance check and reopening
    socket = QLocalSocket()
    socket.connectToServer("trackma-qt")
    if socket.waitForConnected(500):
        socket.write(b"show")
        socket.waitForBytesWritten(500)
        print("Trackma-qt is already running, reopening existing instance.")
        sys.exit(0)

    # Fallback to lock file if server is not responding but lock exists
    lock_file = QLockFile(QDir.tempPath() + "/trackma-qt.lock")
    if not lock_file.tryLock(100):
        print("Trackma-qt is already running (locked).")
        sys.exit(1)

    if os.name == "nt":
        import ctypes
        myappid = 'trackma' + utils.VERSION
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    try:
        # keep the variable around to prevent it from being gc'ed
        main_window = MainWindow(debug)
        sys.exit(app.exec())
    except utils.TrackmaFatal as e:
        QMessageBox.critical(None, 'Fatal Error', "{0}".format(e), QMessageBox.StandardButton.Ok)
