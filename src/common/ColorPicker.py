from __future__ import annotations
import sys
from typing import Tuple, List
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QScrollArea, QLineEdit, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtGui import (
    QPixmap, QImage, QColor, QMouseEvent, QKeyEvent, QClipboard, QAction, QCursor, QPainter,
    QPen, QGuiApplication, QWheelEvent
)
from PyQt6.QtCore import Qt, QPoint, QRect, QSize, pyqtSignal
from src.common.ColorManager import color_to_hex, color_to_rgb, color_to_hsv

# Configuration defaults
DEFAULT_ZOOM = 8         # magnification factor
GRID_SIZE = 15           # sample grid (odd preferred)
MAG_PREVIEW_SIZE = 180   # preview widget size in pixels (square)
MIN_ZOOM = 0.1
MAX_ZOOM = 10.0

class Magnifier(QWidget):
    """Floating magnifier widget showing zoomed region around a point in an image.

    The magnifier is DPI-aware and expects (image, image_pos_x, image_pos_y) where
    image is a QImage in device pixel coordinates.
    """
    def __init__(self, parent=None, grid_size:int=GRID_SIZE, zoom:int=DEFAULT_ZOOM, size:int=MAG_PREVIEW_SIZE):
        super().__init__(parent, flags=Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.grid_size = grid_size
        self.zoom = int(zoom)
        self.preview_size = int(size)
        self.pixel_size = max(1, self.preview_size // self.grid_size)
        self.setFixedSize(self.pixel_size * self.grid_size + 10, self.pixel_size * self.grid_size + 40)
        self._image = None
        self._img_x = 0
        self._img_y = 0
        self._center_color = QColor(0,0,0)

    def set_image_and_pos(self, image: QImage, img_x: int, img_y: int):
        """Set the image and center position (in image pixel coordinates)
        image must be a QImage in device pixels (not scaled)
        """
        self._image = image
        self._img_x = int(img_x)
        self._img_y = int(img_y)
        if 0 <= self._img_x < image.width() and 0 <= self._img_y < image.height():
            self._center_color = image.pixelColor(self._img_x, self._img_y)
        self.update()

    def paintEvent(self, event):
        if self._image is None:
            return
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(240,240,240,220))

        half = self.grid_size // 2
        src_x = self._img_x - half
        src_y = self._img_y - half

        # Create a small region image (grid_size x grid_size) and fill with background
        region = QImage(self.grid_size, self.grid_size, QImage.Format.Format_RGB32)
        bg = QColor(200,200,200)
        region.fill(bg)

        for r in range(self.grid_size):
            for c in range(self.grid_size):
                sx = src_x + c
                sy = src_y + r
                if 0 <= sx < self._image.width() and 0 <= sy < self._image.height():
                    region.setPixel(c, r, self._image.pixel(sx, sy))

        # scale nearest-neighbor (FastTransformation) to preserve pixel blocks
        scaled = region.scaled(self.pixel_size * self.grid_size, self.pixel_size * self.grid_size,
                               Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)

        # draw area for scaled grid
        left = 5
        top = 5
        painter.drawImage(left, top, scaled)

        # draw grid lines
        pen = QPen(QColor(120,120,120,180))
        pen.setWidth(1)
        painter.setPen(pen)
        for i in range(self.grid_size + 1):
            x = left + i * self.pixel_size
            y = top + i * self.pixel_size
            painter.drawLine(x, top, x, top + self.pixel_size * self.grid_size)
            painter.drawLine(left, y, left + self.pixel_size * self.grid_size, y)

        # Draw highlight around center pixel
        cx = left + half * self.pixel_size
        cy = top + half * self.pixel_size
        highlight_pen = QPen(QColor(255,255,255), 2)
        painter.setPen(highlight_pen)
        painter.drawRect(cx - 1, cy - 1, self.pixel_size + 2, self.pixel_size + 2)
        highlight_pen = QPen(QColor(0,0,0), 1)
        painter.setPen(highlight_pen)
        painter.drawRect(cx, cy, self.pixel_size, self.pixel_size)

        # Draw color swatch and text below
        sw_left = left
        sw_top = top + self.pixel_size * self.grid_size + 6
        sw_w = 50
        sw_h = 24
        painter.fillRect(sw_left, sw_top, sw_w, sw_h, self._center_color)
        painter.setPen(QPen(QColor(0,0,0)))
        painter.drawRect(sw_left, sw_top, sw_w, sw_h)

        hex_text = color_to_hex(self._center_color)
        rgb_color = color_to_rgb(self._center_color)
        if rgb_color:
            rgb_text = f"RGB: {rgb_color[0]},{rgb_color[1]},{rgb_color[2]}"
        else:
            rgb_text = f"RGB:"
        painter.drawText(sw_left + sw_w + 6, sw_top + 10, hex_text)
        painter.drawText(sw_left + sw_w + 6, sw_top + 25, rgb_text)


class ImageColorPicker(QWidget):
    """Main widget that shows an image and the magnifier. Emits colorPicked(hex).

    Features:
    - Load image from file, drag & drop, or paste from clipboard
    - Hover updates magnifier (tool window)
    - Click picks color and adds to palette
    """
    colorPicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle('Image Color Picker')
        self.resize(900, 600)

        self.zoom = DEFAULT_ZOOM
        self.grid_size = GRID_SIZE
        self._zoom_factor = 1.0

        # UI
        self.open_btn = QPushButton('Open Image')
        self.open_btn.clicked.connect(self.open_image)
        self.paste_btn = QPushButton('Paste Image')
        self.paste_btn.clicked.connect(self.paste_image)

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.open_btn)
        top_bar.addWidget(self.paste_btn)
        top_bar.addStretch(1)

        # Image display
        self.image_label = QLabel()
        #self.image_label.setBackgroundRole(QLabel.ColorRole.Base)
        self.image_label.setScaledContents(False)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.image_label.setMouseTracking(True)
        self.image_label.installEventFilter(self)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.image_label)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_bar)
        main_layout.addWidget(self.scroll)

        self.setLayout(main_layout)

        # Internal state
        self._pixmap = None            # QPixmap as loaded
        self._image = None             # QImage in device pixels
        self._display_scale = 1.0      # displayed_pixmap_width / image.width()

        # Magnifier
        self.magnifier = Magnifier(self, grid_size=self.grid_size, zoom=self.zoom)
        self.magnifier.hide()

        # Drag & drop
        self.setAcceptDrops(True)

    # ----------------- image loading -----------------
    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open Image', '', 'Images (*.png *.jpg *.bmp *.gif)')
        if path:
            pm = QPixmap(path)
            if pm.isNull():
                QMessageBox.warning(self, 'Error', 'Failed to load image')
                return
            self.set_pixmap(pm)

    def paste_image(self):
        clipboard = QApplication.clipboard()
        img = clipboard.image()
        if not img.isNull():
            pm = QPixmap.fromImage(img)
            self.set_pixmap(pm)
        else:
            QMessageBox.information(self, 'Info', 'No image in clipboard')

    def set_pixmap(self, pixmap: QPixmap):
        # Ensure device pixel ratio handled
        dpr = pixmap.devicePixelRatio() or 1.0
        self._pixmap = pixmap
        # Convert to image in device pixels
        self._image = pixmap.toImage()

        # Display scaled-to-fit width if larger than scroll area viewport
        viewport = self.scroll.viewport().size()
        img_w = self._image.width()
        img_h = self._image.height()
        if img_w > viewport.width() or img_h > viewport.height():
            # scale to fit while preserving aspect
            scaled = pixmap.scaled(viewport, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled)
            self._display_scale = scaled.width() / img_w
        else:
            self.image_label.setPixmap(pixmap)
            self._display_scale = 1.0

        self.image_label.adjustSize()
        self.magnifier.hide()

    # ----------------- drag & drop -----------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasImage() or event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasImage():
            img = event.mimeData().imageData()
            pm = QPixmap.fromImage(img)
            self.set_pixmap(pm)
        elif event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            self.set_pixmap(QPixmap(url.toLocalFile()))

    # ----------------- event mapping -----------------
    def eventFilter(self, obj, event):
        # listen for mouse events on the image_label
        if obj is self.image_label:
            if event.type() == QMouseEvent.Type.MouseMove:
                me = event
                pos = me.position().toPoint()
                self.on_image_mouse_move(pos)
            elif event.type() == QMouseEvent.Type.MouseButtonPress:
                me = event
                pos = me.position().toPoint()
                if me.button() == Qt.MouseButton.LeftButton:
                    self.on_image_mouse_click(pos)
            elif event.type() == QMouseEvent.Type.Leave:
                self.magnifier.hide()
        return super().eventFilter(obj, event)

    def widget_to_image_coords(self, widget_pos: QPoint) -> Tuple[int, int]:
        """Map widget coordinates to image pixel coordinates, safely."""
        if self._image is None:
            return None  # nothing to map

        label_pixmap = self.image_label.pixmap()
        if label_pixmap is None or label_pixmap.isNull():
            return None

        # position relative to the label's top-left (widget coords)
        x = widget_pos.x()
        y = widget_pos.y()

        # account for scale between displayed pixmap and real image
        scale = self._display_scale if self._display_scale > 0 else 1.0
        img_x = int(x / scale)
        img_y = int(y / scale)

        # clamp to image bounds
        img_x = max(0, min(self._image.width() - 1, img_x))
        img_y = max(0, min(self._image.height() - 1, img_y))
        return (img_x, img_y)

    def on_image_mouse_move(self, widget_pos: QPoint):
        if self._image is None:
            return  # nothing loaded yet

        coords = self.widget_to_image_coords(widget_pos)
        if coords is None:
            return
        img_x, img_y = coords

        # magnifier positioning and preview
        global_cursor = QCursor.pos()
        screen = QGuiApplication.screenAt(global_cursor) or QGuiApplication.primaryScreen()
        mag_w, mag_h = self.magnifier.width(), self.magnifier.height()
        screen_geo = screen.availableGeometry()
        offset = QPoint(20, 20)

        mag_pos = global_cursor + offset
        if mag_pos.x() + mag_w > screen_geo.right():
            mag_pos.setX(global_cursor.x() - mag_w - 20)
        if mag_pos.y() + mag_h > screen_geo.bottom():
            mag_pos.setY(global_cursor.y() - mag_h - 20)

        self.magnifier.set_image_and_pos(self._image, img_x, img_y)
        self.magnifier.move(mag_pos)
        self.magnifier.show()

    def on_image_mouse_click(self, widget_pos: QPoint):
        if self._image is None:
            return  # ignore clicks until an image is loaded

        coords = self.widget_to_image_coords(widget_pos)
        if coords is None:
            return
        img_x, img_y = coords

        color = self._image.pixelColor(img_x, img_y)
        hex_code = color_to_hex(color)
        print(f"Picked color: {hex_code}")
        self.colorPicked.emit(hex_code)

    def wheelEvent(self, event: QWheelEvent):
        """Zoom in/out on scroll wheel."""
        if self._pixmap is None:
            return

        # zoom factors
        zoom_in_factor = 1.25
        zoom_out_factor = 0.8

        if event.angleDelta().y() > 0:   # scroll up
            factor = zoom_in_factor
        else:                            # scroll down
            factor = zoom_out_factor

        new_zoom = self._zoom_factor * factor

        # Clamp zoom
        if new_zoom < MIN_ZOOM or new_zoom > MAX_ZOOM:
            return

        self._zoom_factor = new_zoom

        # Rescale pixmap
        scaled = self._pixmap.scaled(
            self._pixmap.size() * self._zoom_factor,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        self.image_label.adjustSize()
        self._display_scale = scaled.width() / self._image.width()