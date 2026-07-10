import sys
from PyQt6.QtWidgets import QApplication
from trackma.ui.qt.styles import QSS_STYLESHEET
from trackma.ui.qt.widgets import ShowCardWidget

def test_stylesheet():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(QSS_STYLESHEET)
    assert app.styleSheet() == QSS_STYLESHEET

def test_show_card_widget():
    app = QApplication.instance() or QApplication(sys.argv)
    dummy_show = {
        'id': 123,
        'title': 'Frieren',
        'total_episodes': 28,
        'my_progress': 10,
        'image': None
    }
    widget = ShowCardWidget(dummy_show)
    assert widget.show_id == 123
    assert widget.selected is False
    assert widget.title_label.text() == 'Frieren'
    assert widget.progress_label.text() == 'Ep 10 / 28'

    widget.set_selected(True)
    assert widget.selected is True

    # Test update_data
    dummy_show_unknown = {
        'id': 123,
        'title': 'Frieren',
        'my_progress': 15,
        'image': None
    }
    widget.update_data(dummy_show_unknown)
    assert widget.progress_label.text() == 'Ep 15 / ?'

if __name__ == '__main__':
    test_stylesheet()
    test_show_card_widget()
    print("Stylesheet check passed!")
    print("ShowCardWidget tests passed!")

