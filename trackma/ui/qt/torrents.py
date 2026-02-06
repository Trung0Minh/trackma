from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
                             QTableView, QHeaderView, QAbstractItemView, QDialogButtonBox, 
                             QMessageBox, QLabel, QComboBox)

class TorrentTableModel(QtCore.QAbstractTableModel):
    columns = ["Cat", "Title", "Size", "S", "L", "Done", "Published"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.results = []

    def setResults(self, results):
        self.beginResetModel()
        self.results = results if results else []
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.results)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.columns)

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.ItemDataRole.DisplayRole and orientation == QtCore.Qt.Orientation.Horizontal:
            return self.columns[section]

    def data(self, index, role):
        if not index.isValid():
            return None
        
        row, col = index.row(), index.column()
        item = self.results[row]

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            if col == 0: return item.get('category', '?')
            if col == 1: return item.get('title')
            if col == 2: return item.get('size')
            if col == 3: return item.get('seeders')
            if col == 4: return item.get('leechers')
            if col == 5: return item.get('completed')
            if col == 6: return item.get('published')
        
        if role == QtCore.Qt.ItemDataRole.ForegroundRole:
            if col == 3: return QtGui.QColor("green")
            if col == 4: return QtGui.QColor("red")
            if col == 5: return QtGui.QColor("deepskyblue")

        return None

class TorrentDialog(QDialog):
    def __init__(self, parent, worker, default_query=""):
        super().__init__(parent)
        self.worker = worker
        self.current_page = 1
        self.setWindowTitle("Nyaa Torrent Search")
        self.resize(1100, 600)

        layout = QVBoxLayout(self)

        # Search Bar
        search_layout = QHBoxLayout()
        
        self.search_txt = QLineEdit()
        self.search_txt.setText(default_query)
        self.search_txt.setPlaceholderText("Search torrents on Nyaa...")
        self.search_txt.returnPressed.connect(self.s_new_search)
        
        self.cat_combo = QComboBox()
        self.cat_combo.addItem("All Anime", "1_0")
        self.cat_combo.addItem("Sub (English)", "1_2")
        self.cat_combo.addItem("Raw", "1_4")
        self.cat_combo.addItem("Non-English", "1_3")
        # Default to Sub if it's an anime search, or keep "All"
        self.cat_combo.setCurrentIndex(1) 
        self.cat_combo.currentIndexChanged.connect(self.s_new_search)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.s_new_search)
        
        search_layout.addWidget(QLabel("Query:"))
        search_layout.addWidget(self.search_txt, 4)
        search_layout.addWidget(QLabel("Category:"))
        search_layout.addWidget(self.cat_combo, 1)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)

        # Results Table
        self.table = QTableView()
        self.model = TorrentTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self.s_download)
        layout.addWidget(self.table)

        # Pagination and Download Row
        bottom_row = QHBoxLayout()
        
        # Pagination
        self.prev_btn = QPushButton("< Prev")
        self.prev_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self.s_prev_page)
        self.next_btn = QPushButton("Next >")
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self.s_next_page)
        self.page_label = QLabel("Page 1")
        
        pagination_layout = QHBoxLayout()
        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addWidget(self.next_btn)
        
        bottom_row.addLayout(pagination_layout)
        bottom_row.addStretch(1)

        # Download Buttons
        self.download_btn = QPushButton("Download")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.s_download)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        
        bottom_row.addWidget(self.download_btn)
        bottom_row.addWidget(self.close_btn)
        layout.addLayout(bottom_row)

        self.table.selectionModel().currentRowChanged.connect(self.s_selected)

        if default_query:
            self.s_new_search()

    def s_new_search(self):
        self.current_page = 1
        self.s_search()

    def s_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.s_search()

    def s_next_page(self):
        self.current_page += 1
        self.s_search()

    def s_search(self):
        query = self.search_txt.text().strip()
        if not query: return
        
        category = self.cat_combo.currentData()
        
        self.search_btn.setEnabled(False)
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.page_label.setText(f"Page {self.current_page} (loading...)")
        
        # Use custom category from dropdown instead of config default
        self.worker.set_function('search_torrents_manual', self.r_searched, query, category=category, page=self.current_page)
        self.worker.start()

    def r_searched(self, result):
        self.search_btn.setEnabled(True)
        if result['success']:
            results = result['result']
            self.model.setResults(results)
            self.page_label.setText(f"Page {self.current_page}")
            self.prev_btn.setEnabled(self.current_page > 1)
            self.next_btn.setEnabled(len(results) >= 75)
        else:
            self.model.setResults([])
            self.page_label.setText(f"Page {self.current_page} (Error)")

    def s_selected(self, current, previous):
        self.download_btn.setEnabled(current.isValid())

    def s_download(self):
        index = self.table.currentIndex()
        if not index.isValid(): return
        
        item = self.model.results[index.row()]
        magnet = item.get('link')
        
        self.download_btn.setEnabled(False)
        self.worker.set_function('download_torrent', self.r_downloaded, magnet)
        self.worker.start()

    def r_downloaded(self, result):
        self.download_btn.setEnabled(True)
        if result['success']:
            if result['result']:
                QMessageBox.information(self, "Success", "Torrent added to qBittorrent!")
                # Trigger a scan to detect the newly created file
                self.worker.set_function('scan_library', None)
                self.worker.start()
            else:
                QMessageBox.warning(self, "Error", "Failed to add torrent to qBittorrent.")
        else:
            QMessageBox.critical(self, "Error", "Communication error with engine.")
