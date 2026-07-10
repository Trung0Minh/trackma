import sys
from PyQt6.QtWidgets import QApplication
from trackma.ui.qt.styles import QSS_STYLESHEET

def test_stylesheet():
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS_STYLESHEET)
    assert app.styleSheet() == QSS_STYLESHEET
    app.quit()

if __name__ == '__main__':
    test_stylesheet()
    print("Stylesheet check passed!")
