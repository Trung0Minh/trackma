# trackma/ui/qt/styles.py

QSS_STYLESHEET = """
QMainWindow {
    background-color: #0b0f19;
}

QSplitter::handle {
    background-color: #1e293b;
}

QTabBar::tab {
    background: transparent;
    color: #9ca3af;
    padding: 8px 16px;
    font-weight: 600;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #a5b4fc;
    border-bottom: 2px solid #6366f1;
    background: rgba(99, 102, 241, 0.1);
}

QScrollArea, QTableView {
    background-color: #111827;
    border: 1px solid #1e293b;
    border-radius: 8px;
}

QHeaderView::section {
    background-color: #111827;
    color: #9ca3af;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #1e293b;
    font-weight: bold;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {
    background-color: #1e293b;
    color: #f3f4f6;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {
    border-color: #6366f1;
}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled, QPlainTextEdit:disabled {
    background-color: #0f172a;
    color: #64748b;
    border: 1px solid #1e293b;
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6366f1, stop:1 #a855f7);
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f46e5, stop:1 #9333ea);
}
QPushButton:disabled {
    background: #1e293b;
    color: #64748b;
    border: 1px solid #1e293b;
}

QToolButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px;
    color: #f3f4f6;
}
QToolButton:hover {
    border-color: #6366f1;
    background-color: rgba(99, 102, 241, 0.1);
}
QToolButton:disabled {
    background-color: #0f172a;
    border-color: #1e293b;
    color: #64748b;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 15px;
    border-left-width: 0px;
}
QComboBox QAbstractItemView {
    background-color: #111827;
    color: #f3f4f6;
    border: 1px solid #1e293b;
    selection-background-color: #6366f1;
}

QScrollBar:vertical {
    border: none;
    background: #111827;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #1e293b;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #6366f1;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #111827;
    height: 10px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #1e293b;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #6366f1;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
    width: 0px;
}

QMenu {
    background-color: #111827;
    color: #f3f4f6;
    border: 1px solid #1e293b;
    border-radius: 6px;
}
QMenu::item:selected {
    background-color: #6366f1;
}
"""
