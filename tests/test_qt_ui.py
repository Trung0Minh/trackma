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
        'total': 28,
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

    # Test update_data with unknown total
    dummy_show_unknown = {
        'id': 123,
        'title': 'Frieren',
        'my_progress': 15,
        'image': None
    }
    widget.update_data(dummy_show_unknown)
    assert widget.progress_label.text() == 'Ep 15 / ?'


def test_shows_grid_view():
    app = QApplication.instance() or QApplication(sys.argv)
    from trackma.ui.qt.models import ShowListModel, ShowListProxy
    from trackma.ui.qt.widgets import ShowsGridView
    from trackma import utils
    from PyQt6.QtGui import QImage

    model = ShowListModel()
    proxy = ShowListProxy()
    proxy.setSourceModel(model)

    model.showlist = [
        {'id': 1, 'title': 'Frieren', 'total': 28, 'my_progress': 10, 'image': 'http://example.com/frieren.jpg', 'my_status': None},
        {'id': 2, 'title': 'Evangelion', 'total': 26, 'my_progress': 26, 'image': None, 'my_status': None}
    ]

    grid_view = ShowsGridView()
    api_info = {'shortname': 'test_api', 'mediatype': 'anime'}
    grid_view.set_api_info(api_info)
    grid_view.setModel(proxy)

    # 1. Verify cards are created
    assert 1 in grid_view.cards
    assert 2 in grid_view.cards
    assert grid_view.cards[1].show_data['title'] == 'Frieren'

    # 2. Verify selection sync (click updates state and emits signal)
    selection_emitted = []
    grid_view.selectionChanged.connect(selection_emitted.append)
    grid_view.cards[1].clicked.emit(1)
    assert grid_view.selected_show_id == 1
    assert grid_view.cards[1].selected is True
    assert grid_view.cards[2].selected is False
    assert selection_emitted == [1]

    # Test select_show helper
    grid_view.select_show(2)
    assert grid_view.selected_show_id == 2
    assert grid_view.cards[1].selected is False
    assert grid_view.cards[2].selected is True

    # 3. Verify itemFinished downloaded updates the card's poster image
    dummy_image = QImage(10, 10, QImage.Format.Format_RGB32)
    expected_path = utils.to_cache_path("test_api_anime_f_1.jpg")
    grid_view.on_thumb_downloaded("1", dummy_image)
    assert grid_view.cards[1].cached_image_path == expected_path

    # 4. Verify dataChanged updates the widget progress
    model.showlist[0]['my_progress'] = 12
    topLeft = proxy.index(0, 0)
    bottomRight = proxy.index(0, 0)
    proxy.dataChanged.emit(topLeft, bottomRight)
    assert grid_view.cards[1].progress_label.text() == 'Ep 12 / 28'

    # 5. Verify model reset/layoutChanged reloads grid
    model.showlist = [
        {'id': 3, 'title': 'One Piece', 'total': 1000, 'my_progress': 999, 'image': None, 'my_status': None}
    ]
    proxy.layoutChanged.emit()
    assert 1 not in grid_view.cards
    assert 3 in grid_view.cards
    assert grid_view.cards[3].show_data['title'] == 'One Piece'

    # 6. Verify layout column calculations
    grid_view.resize(350, 400)
    grid_view.rearrange_grid()
    # grid layout should have the widget
    assert grid_view.grid_layout.count() == 1


if __name__ == '__main__':
    test_stylesheet()
    test_show_card_widget()
    test_shows_grid_view()
    print("Stylesheet check passed!")
    print("ShowCardWidget tests passed!")
    print("ShowsGridView tests passed!")


