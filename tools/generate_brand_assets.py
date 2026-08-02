"""Generate Trackma raster application icons from the SVG source mark."""

from pathlib import Path
import sys

from PIL import Image
from PyQt6 import QtCore, QtGui, QtSvg


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "trackma" / "data" / "brand" / "trackma-mark.svg"
DATA = ROOT / "trackma" / "data"


def render(size: int) -> Path:
    renderer = QtSvg.QSvgRenderer(str(SOURCE))
    image = QtGui.QImage(size, size, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()

    output = DATA / "brand" / f"trackma-{size}.png"
    image.save(str(output))
    return output


def main() -> int:
    paths = [render(size) for size in (16, 24, 32, 48, 64, 128, 256)]
    (DATA / "icon.png").write_bytes((DATA / "brand" / "trackma-256.png").read_bytes())
    images = [Image.open(path).convert("RGBA") for path in paths]
    images[-1].save(DATA / "icon.ico", format="ICO", append_images=images[:-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
