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

from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import (QAbstractItemView, QFrame, QGridLayout, QHeaderView, QLabel, QListView,
                             QProgressBar, QScrollArea, QSizePolicy, QSplitter, QTableView, QVBoxLayout, QWidget)

from trackma import utils
from trackma.ui.qt.delegates import AddListDelegate, ShowsTableDelegate
from trackma.ui.qt.models import AddListModel, AddListProxy, AddTableModel, ShowListModel, ShowListProxy
from trackma.ui.qt.workers import ImageWorker


class DetailsWidget(QWidget):
    current_image_file = None

    def __init__(self, parent, worker):
        self.worker = worker

        QWidget.__init__(self, parent)

        # Build layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.show_title = QLabel()
        show_title_font = QtGui.QFont()
        show_title_font.setBold(True)
        show_title_font.setPointSize(12)
        self.show_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.show_title.setFont(show_title_font)

        info_area = QWidget()
        info_layout = QGridLayout()

        self.show_image = QLabel()
        self.show_image.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.show_info = QLabel()
        self.show_info.setWordWrap(True)
        self.show_info.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.show_description = QLabel()
        self.show_description.setWordWrap(True)
        self.show_description.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        info_layout.addWidget(self.show_image,        0, 0, 1, 1)
        info_layout.addWidget(self.show_info,         1, 0, 1, 1)
        info_layout.addWidget(self.show_description,  0, 1, 2, 1)

        info_area.setLayout(info_layout)

        scroll_area = QScrollArea()
        scroll_area.setBackgroundRole(QtGui.QPalette.ColorRole.Light)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(info_area)

        main_layout.addWidget(self.show_title)
        main_layout.addWidget(scroll_area)

        self.setLayout(main_layout)

    def worker_call(self, function, ret_function, *args, **kwargs):
        # Run worker in a thread
        self.worker.set_function(function, ret_function, *args, **kwargs)
        self.worker.start()

    def resizeEvent(self, event):
        self._update_image()
        super().resizeEvent(event)

    def load(self, show):
        metrics = QtGui.QFontMetrics(self.show_title.font())
        title = metrics.elidedText(
            show['title'], QtCore.Qt.TextElideMode.ElideRight, self.show_title.width())

        self.show_title.setText("<a href=\"%s\">%s</a>" % (show['url'], title))
        self.show_title.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.show_title.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        self.show_title.setOpenExternalLinks(True)

        # Load show info
        self.show_info.setText('Wait...')
        self.worker_call('get_show_details', self.r_details_loaded, show)
        api_info = self.worker.engine.api_info

        # Load show image
        if show.get('image'):
            utils.make_dir(utils.to_cache_path())
            filename = utils.to_cache_path("%s_%s_xl_%s.jpg" % (
                api_info['shortname'], api_info['mediatype'], show['id']))

            if os.path.isfile(filename):
                self.s_show_image(filename)
            else:
                self.show_image.setText('Downloading...')
                self.image_worker = ImageWorker(
                    show['image'], filename)
                self.image_worker.finished.connect(self.s_show_image)
                self.image_worker.start()
        else:
            self.show_image.setText('No image')
            self.current_image_file = None

    def s_show_image(self, filename):
        self.current_image_file = filename
        self._update_image()

    def _update_image(self):
        if not self.current_image_file or not os.path.isfile(self.current_image_file):
            return

        pixmap = QtGui.QPixmap(self.current_image_file)
        if not pixmap.isNull():
            dpr = self.show_image.devicePixelRatioF()
            # In details widget, we use a fixed target size for the sidebar-like feel
            w = int(200 * dpr)
            h = int(280 * dpr)
            pixmap = pixmap.scaled(w, h,
                                   QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                   QtCore.Qt.TransformationMode.SmoothTransformation)
            pixmap.setDevicePixelRatio(dpr)
            self.show_image.setPixmap(pixmap)

    def r_details_loaded(self, result):
        if result['success']:
            details = result['result']

            info_strings = []
            description_strings = []
            # This might come down to personal preference
            description_keys = {'Synopsis', 'English', 'Japanese',  'Romaji', 'Synonyms'}

            for key, value in details['extra']:
                if not key or not value:
                    continue
                str_value = ', '.join(value) if isinstance(value, list) else str(value)
                if key in description_keys or len(str_value) >= 17:
                    # Avoid short tidbits taking up too much vertical space
                    html = f"<h3>{key}</h3><p>{str_value}</p>"
                else:
                    html = f"<p><b>{key}:</b> {str_value}</p>"

                if key in description_keys:
                    description_strings.append(html)
                else:
                    info_strings.append(html)

            info_string = ''.join(info_strings)
            self.show_info.setText(info_string)
            description_string = ''.join(description_strings)
            self.show_description.setText(description_string)
        else:
            self.show_info.setText('There was an error while getting details.')


class ShowsTableView(QTableView):
    """
    Regular table widget with context menu for show actions.

    """
    middleClicked = QtCore.pyqtSignal()

    def __init__(self, parent=None, palette=None):
        QTableView.__init__(self, parent)

        model = ShowListModel(palette=palette)
        proxymodel = ShowListProxy()
        proxymodel.setSourceModel(model)
        proxymodel.setFilterKeyColumn(-1)
        self.setModel(proxymodel)

        self.setItemDelegate(ShowsTableDelegate(self, palette=palette))
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.verticalHeader().hide()
        self.setGridStyle(QtCore.Qt.PenStyle.NoPen)

    def contextMenuEvent(self, event):
        action = self.context_menu.exec(event.globalPos())

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.middleClicked.emit()


class AddCardView(QListView):
    changed = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None, api_info=None):
        super().__init__(parent)

        m = AddListModel(api_info=api_info)
        proxy = AddListProxy()
        proxy.setSourceModel(m)
        proxy.sort(0, QtCore.Qt.SortOrder.AscendingOrder)

        self.setItemDelegate(AddListDelegate())
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setModel(proxy)

        self.selectionModel().currentRowChanged.connect(self.s_show_selected)

    def s_show_selected(self, new, old=None):
        if not new:
            return

        index = self.model().mapToSource(new).row()
        selected_show = self.getModel().results[index]

        self.changed.emit(selected_show)

    def setResults(self, results):
        self.getModel().setResults(results)

    def getModel(self):
        return self.model().sourceModel()


class AddTableDetailsView(QSplitter):
    """ This is a splitter widget that contains a table and
    a details widget. Used in the Add Show dialog. """

    changed = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None, worker=None):
        super().__init__(parent)

        self.table = QTableView()
        m = AddTableModel()
        proxy = QtCore.QSortFilterProxyModel()
        proxy.setSourceModel(m)

        self.table.setGridStyle(QtCore.Qt.PenStyle.NoPen)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setModel(proxy)

        # Allow sorting but don't sort by default
        self.table.horizontalHeader().setSortIndicator(-1, QtCore.Qt.SortOrder.AscendingOrder)
        self.table.setSortingEnabled(True)

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        self.table.selectionModel().currentRowChanged.connect(self.s_show_selected)
        self.addWidget(self.table)

        self.details = DetailsWidget(parent, worker)
        self.addWidget(self.details)

        self.setSizes([1, 1])

    def s_show_selected(self, new, old=None):
        if not new:
            return

        index = self.table.model().mapToSource(new).row()
        selected_show = self.getModel().results[index]
        self.details.load(selected_show)

        self.changed.emit(selected_show)

    def setResults(self, results):
        self.getModel().setResults(results)

    def getModel(self):
        return self.table.model().sourceModel()

    def clearSelection(self):
        return self.table.clearSelection()


class ShowCardWidget(QFrame):
    clicked = QtCore.pyqtSignal(int)
    play_clicked = QtCore.pyqtSignal(int)

    def __init__(self, show_data, parent=None):
        super().__init__(parent)
        self.show_data = show_data
        self.show_id = show_data['id']
        self.selected = False
        self.setObjectName("ShowCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self.setStyleSheet("""
            QFrame#ShowCard {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            QFrame#ShowCard[selected="true"] {
                border: 2px solid #a855f7;
            }
        """)

        # Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Poster Image
        self.poster_label = QLabel(self)
        self.poster_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.poster_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.main_layout.addWidget(self.poster_label)

        # Metadata Overlay Box
        self.info_panel = QFrame(self)
        self.info_panel.setStyleSheet("""
            QFrame {
                background: rgba(15, 23, 42, 0.95);
                border-top: 1px solid #334155;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)
        info_layout = QVBoxLayout(self.info_panel)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(4)

        self.title_label = QLabel(self.info_panel)
        self.title_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 11px;")
        info_layout.addWidget(self.title_label)

        self.progress_label = QLabel(self.info_panel)
        self.progress_label.setStyleSheet("color: #9ca3af; font-size: 9px;")
        info_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar(self.info_panel)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #334155;
                border-radius: 2px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #a855f7);
                border-radius: 2px;
            }
        """)
        info_layout.addWidget(self.progress_bar)

        self.main_layout.addWidget(self.info_panel)
        self.update_data(show_data)

    def update_data(self, show_data):
        self.show_data = show_data
        metrics = QtGui.QFontMetrics(self.title_label.font())
        elided_title = metrics.elidedText(show_data['title'], QtCore.Qt.TextElideMode.ElideRight, 120)
        self.title_label.setText(elided_title)

        total_eps = show_data.get('total_episodes') or show_data.get('episodes') or 0
        my_progress = show_data.get('my_progress', 0)

        if total_eps > 0:
            self.progress_label.setText(f"Ep {my_progress} / {total_eps}")
            self.progress_bar.setMaximum(total_eps)
            self.progress_bar.setValue(my_progress)
            self.progress_bar.show()
        else:
            self.progress_label.setText(f"Ep {my_progress} / ?")
            self.progress_bar.hide()

        self.load_poster()

    def load_poster(self):
        # Resolve image path via local thumbnail managers or caching
        image_path = self.show_data.get('image')
        if image_path and os.path.isfile(image_path):
            pixmap = QtGui.QPixmap(image_path)
            if not pixmap.isNull():
                dpr = self.devicePixelRatioF()
                w = int(140 * dpr)
                h = int(210 * dpr)
                pixmap = pixmap.scaled(w, h,
                                       QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                       QtCore.Qt.TransformationMode.SmoothTransformation)
                pixmap.setDevicePixelRatio(dpr)
                self.poster_label.setPixmap(pixmap)
                return

        # Fallback linear gradient styled label
        self.poster_label.setText(self.show_data['title'][:2].upper())
        self.poster_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e1b4b, stop:1 #311042);
                color: #a5b4fc;
                font-size: 24px;
                font-weight: bold;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)

    def set_selected(self, selected):
        self.selected = selected
        self.setProperty("selected", "true" if selected else "false")
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit(self.show_id)
        super().mousePressEvent(event)

