"""Generate the platform application icons from the source SVG.

PyInstaller needs a ``.icns`` on macOS and a ``.ico`` on Windows; it silently ignores
a plain PNG, which is why the original auto-generated spec produced an icon-less build.
Both are derived here from ``resources/icons/LaME-64.svg`` so there is one source of
truth for the app icon.

Run from the repository root::

    python packaging/make_icons.py

Writes ``packaging/LaME.icns`` (macOS only, requires ``iconutil``) and
``packaging/LaME.ico``.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QGuiApplication, QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'resources' / 'icons' / 'LaME-64.svg'
OUT_DIR = ROOT / 'packaging'

# .icns wants each size at 1x and 2x; .ico takes the common Windows sizes.
ICNS_SIZES = [16, 32, 128, 256, 512]
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def render(svg_path: Path, size: int, dest: Path) -> None:
    """Rasterise `svg_path` to a square `size`x`size` transparent PNG at `dest`."""
    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise SystemExit(f"cannot read SVG: {svg_path}")

    image = QImage(QSize(size, size), QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()

    if not image.save(str(dest), 'PNG'):
        raise SystemExit(f"failed to write {dest}")


def build_ico(tmp: Path) -> Path:
    """Build the Windows .ico from rendered PNGs."""
    largest = tmp / 'ico-256.png'
    render(SOURCE, 256, largest)
    dest = OUT_DIR / 'LaME.ico'
    Image.open(largest).save(dest, sizes=[(s, s) for s in ICO_SIZES])
    return dest


def build_icns(tmp: Path) -> Path | None:
    """Build the macOS .icns via `iconutil`; returns None on other platforms."""
    if sys.platform != 'darwin' or shutil.which('iconutil') is None:
        print('skipping .icns (needs macOS iconutil)')
        return None

    iconset = tmp / 'LaME.iconset'
    iconset.mkdir()
    for size in ICNS_SIZES:
        render(SOURCE, size, iconset / f'icon_{size}x{size}.png')
        render(SOURCE, size * 2, iconset / f'icon_{size}x{size}@2x.png')

    dest = OUT_DIR / 'LaME.icns'
    subprocess.run(
        ['iconutil', '-c', 'icns', str(iconset), '-o', str(dest)], check=True
    )
    return dest


def main() -> None:
    QGuiApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
    app = QGuiApplication(['make_icons', '-platform', 'offscreen'])  # noqa: F841

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for path in (build_ico(tmp), build_icns(tmp)):
            if path is not None:
                print(f'wrote {path.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
