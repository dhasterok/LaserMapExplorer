#!/usr/bin/env python3
"""
Color Picker

Created on Sat Aug 16 2025

@author: Derrick Hasterok
"""

from __future__ import annotations
import sys
import numpy as np
from typing import Tuple, List
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSpinBox,
    QFileDialog, QScrollArea, QLineEdit, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt6.QtGui import (
    QPixmap, QImage, QColor, QMouseEvent, QKeyEvent, QClipboard, QAction, QCursor, QPainter,
    QPen, QGuiApplication, QWheelEvent
)
from PyQt6.QtCore import Qt, QPoint, QRect, QSize, pyqtSignal
from src.common.ColorManager import convert_color, convert_color_list

from PIL import Image
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.pyplot as plt
import colorsys

# Configuration defaults
DEFAULT_ZOOM = 8         # magnification factor
GRID_SIZE = 15           # sample grid (odd preferred)
MAG_PREVIEW_SIZE = 180   # preview widget size in pixels (square)
MIN_ZOOM = 0.1
MAX_ZOOM = 10.0

def sort_by_hue(colors):
    """
    Sort a list of RGB colors by their hue.

    Parameters
    ----------
    colors : list of tuple
        List of colors, each as a 3-tuple (R, G, B) with values in [0, 1] or [0, 255].

    Returns
    -------
    list of tuple
        List of colors sorted by their hue in HSV space.
    """
    return sorted(colors, key=lambda c: colorsys.rgb_to_hsv(*c)[0])

class Magnifier(QWidget):
    def __init__(self, parent=None, grid_size:int=GRID_SIZE, zoom:int=DEFAULT_ZOOM, size:int=MAG_PREVIEW_SIZE):
        """
        Floating magnifier widget showing a zoomed region around a point in an image.

        The magnifier is DPI-aware and expects (image, image_pos_x, image_pos_y) where
        image is a QImage in device pixel coordinates.

        Attributes
        ----------
        grid_size : int
            Number of pixels in the magnifier grid (default GRID_SIZE).
        zoom : int
            Magnification factor for the preview (default DEFAULT_ZOOM).
        preview_size : int
            Size of the magnifier preview in pixels (default MAG_PREVIEW_SIZE).
        pixel_size : int
            Size of each magnified pixel in the preview.
        _image : QImage
            Image being magnified.
        _img_x : int
            X-coordinate of the center pixel in the image.
        _img_y : int
            Y-coordinate of the center pixel in the image.
        _center_color : QColor
            Color of the center pixel.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        grid_size : int
            Number of pixels in the magnifier grid.
        zoom : int
            Magnification factor.
        size : int
            Preview window size.

        Methods
        -------
        set_image_and_pos(image, img_x, img_y)
            Set the image and center position for magnification.
        paintEvent(event)
            Paint the magnifier preview, showing the zoomed region, grid lines, and center color.
        """
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
        """
        Set the image and center position for magnification.

        Set the image and center position (in image pixel coordinates) image must be a QImage in device pixels (not scaled).

        Parameters
        ----------
        image : QImage
            Source image in device pixels (not scaled).
        img_x : int
            X-coordinate of the center pixel in image coordinates.
        img_y : int
            Y-coordinate of the center pixel in image coordinates.
        """
        self._image = image
        self._img_x = int(img_x)
        self._img_y = int(img_y)
        if 0 <= self._img_x < image.width() and 0 <= self._img_y < image.height():
            self._center_color = image.pixelColor(self._img_x, self._img_y)
        self.update()

    def paintEvent(self, event):
        """
        Paint the magnifier preview.

        Draws the zoomed region with grid lines, highlights the center pixel,
        and displays a color swatch with RGB and hex values below the grid.

        Parameters
        ----------
        event : QPaintEvent
            The paint event from Qt.
        """
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

        hex_text = convert_color(self._center_color, "qcolor", "hex")
        rgb_color = convert_color(self._center_color, "qcolor", "rgb", norm_out=False)
        if rgb_color:
            rgb_text = f"RGB: {rgb_color[0]},{rgb_color[1]},{rgb_color[2]}"
        else:
            rgb_text = f"RGB:"
        painter.drawText(sw_left + sw_w + 6, sw_top + 10, hex_text)
        painter.drawText(sw_left + sw_w + 6, sw_top + 25, rgb_text)


class ImageColorPicker(QWidget):
    colorPicked = pyqtSignal(str)
    paletteCreated = pyqtSignal(list)

    def __init__(self, parent=None):
        """
        Main widget that shows an image and a magnifier. Emits signals for picked colors.

        Features
        --------
        - Load image from file, drag & drop, or paste from clipboard.
        - Hover updates the magnifier preview (tool window).
        - Click picks color and emits a signal.

        Signals
        -------
        colorPicked : pyqtSignal(str)
            Emitted when a color is picked. Argument is the color hex code.
        paletteCreated : pyqtSignal(list)
            Emitted when a palette is created. Argument is a list of color hex codes.

        Methods
        -------
        open_image()
            Open an image from a file dialog and display it.
        paste_image()
            Paste an image from the system clipboard and display it.
        set_pixmap(pixmap)
            Set the displayed pixmap and convert it to QImage for processing.
        dragEnterEvent(event)
            Accept drag events containing images or file URLs.
        dropEvent(event)
            Handle drop events. Accepts images or file URLs.
        eventFilter(obj, event)
            Filter mouse events on the image label (hover, click, leave).
        widget_to_image_coords(widget_pos)
            Convert widget coordinates to image pixel coordinates.
        on_image_mouse_move(widget_pos)
            Update magnifier based on mouse move over the image.
        on_image_mouse_click(widget_pos)
            Pick color at the mouse position and emit colorPicked signal.
        wheelEvent(event)
            Zoom the displayed image on mouse wheel scroll.
        qpixmap_to_pil()
            Convert the current QPixmap to a PIL Image in RGB format.
        region_based_palette_qpixmap()
            Generate a palette from the image using region-based K-means clustering.
        """
        super().__init__()
        self.setWindowTitle('Image Color Picker')
        self.resize(900, 600)

        self.zoom = DEFAULT_ZOOM
        self.grid_size = GRID_SIZE
        self._zoom_factor = 1.0
        self._n_colors = 6

        # UI
        self.open_btn = QPushButton('Open Image')
        self.open_btn.clicked.connect(self.open_image)
        self.paste_btn = QPushButton('Paste Image')
        self.paste_btn.clicked.connect(self.paste_image)

        self.region_btn = QPushButton('Auto: Palette')
        self.region_btn.clicked.connect(self.region_based_palette_qpixmap)

        self.n_colors_spinbox = QSpinBox()
        self.n_colors_spinbox.setRange(2, 20)
        self.n_colors_spinbox.setSingleStep(1)
        self.n_colors_spinbox.setValue(self._n_colors)
        self.n_colors_spinbox.valueChanged.connect(lambda value: setattr(self, "_n_colors", value))

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.open_btn)
        top_bar.addWidget(self.paste_btn)
        top_bar.addStretch(1)
        top_bar.addWidget(self.region_btn)
        top_bar.addWidget(QLabel("No. colors:"))
        top_bar.addWidget(self.n_colors_spinbox)

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
        """
        Open an image from a file dialog and display it.
        """
        path, _ = QFileDialog.getOpenFileName(self, 'Open Image', '', 'Images (*.png *.jpg *.bmp *.gif)')
        if path:
            pm = QPixmap(path)
            if pm.isNull():
                QMessageBox.warning(self, 'Error', 'Failed to load image')
                return
            self.set_pixmap(pm)

    def paste_image(self):
        """
        Paste an image from the system clipboard and display it.
        """
        clipboard = QApplication.clipboard()
        img = clipboard.image()
        if not img.isNull():
            pm = QPixmap.fromImage(img)
            self.set_pixmap(pm)
        else:
            QMessageBox.information(self, 'Info', 'No image in clipboard')

    def set_pixmap(self, pixmap: QPixmap):
        """
        Set the displayed pixmap and convert to QImage for processing.

        Handles device pixel ratio and scales to fit the viewport if necessary.

        Parameters
        ----------
        pixmap : QPixmap
            Pixmap to display and process.
        """
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
        """
        Accept drag events containing images or file URLs.

        Parameters
        ----------
        event : QDragEnterEvent
            Drag event.
        """
        if event.mimeData().hasImage() or event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """
        Handle drop events. Accepts images or file URLs.

        Parameters
        ----------
        event : QDropEvent
            Drop event.
        """
        if event.mimeData().hasImage():
            img = event.mimeData().imageData()
            pm = QPixmap.fromImage(img)
            self.set_pixmap(pm)
        elif event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            self.set_pixmap(QPixmap(url.toLocalFile()))

    # ----------------- event mapping -----------------
    def eventFilter(self, obj, event):
        """
        Filter mouse events on the image label.

        Handles mouse move (update magnifier), click (pick color), and leave (hide magnifier).

        Parameters
        ----------
        obj : QObject
            Object that received the event.
        event : QEvent
            The event object.

        Returns
        -------
        bool
            True if the event was handled, otherwise False.
        """
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
        """
        Convert widget coordinates to image pixel coordinates.

        Parameters
        ----------
        widget_pos : QPoint
            Position in widget coordinates.

        Returns
        -------
        tuple of int or None
            Corresponding (x, y) pixel coordinates in the image, or None if mapping is impossible.
        """
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
        """
        Update magnifier based on mouse move over the image.

        Parameters
        ----------
        widget_pos : QPoint
            Mouse position in widget coordinates.
        """
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
        """
        Pick color at the mouse position and emit colorPicked signal.

        Parameters
        ----------
        widget_pos : QPoint
            Mouse click position in widget coordinates.
        """
        if self._image is None:
            return  # ignore clicks until an image is loaded

        coords = self.widget_to_image_coords(widget_pos)
        if coords is None:
            return
        img_x, img_y = coords

        color = self._image.pixelColor(img_x, img_y)
        hex_code = convert_color(color, "qcolor", "hex")
        print(f"Picked color: {hex_code}")
        self.colorPicked.emit(hex_code)

    def wheelEvent(self, event: QWheelEvent):
        """
        Zoom the displayed image on mouse wheel scroll.

        Parameters
        ----------
        event : QWheelEvent
            Mouse wheel event.
        """
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

    def qpixmap_to_pil(self) -> Image.Image:
        """
        Convert the current QPixmap to a PIL Image in RGB format.

        Returns
        -------
        PIL.Image.Image
            The converted PIL image.
        """
        qimg = self._pixmap.toImage().convertToFormat(QImage.Format.Format_RGB32)
        width, height = qimg.width(), qimg.height()

        ptr = qimg.bits()
        ptr.setsize(height * width * 4)

        arr = np.array(ptr, dtype=np.uint8).reshape((height, width, 4))

        # Qt RGB32 is stored as BGRA on little-endian
        b, g, r, a = arr[...,0], arr[...,1], arr[...,2], arr[...,3]
        rgb = np.dstack([r, g, b])

        return Image.fromarray(rgb, "RGB")    

    def region_based_palette_qpixmap(self):
        """
        Generate a palette from the image using region-based K-means clustering.

        Downsamples the image, clusters colors, sorts by hue, and emits paletteCreated signal.
        """
        grid_size = int(50)
        # Convert to PIL, downsample to emphasize regions
        pil_img = self.qpixmap_to_pil().convert("RGB")
        print("Image mode after conversion:", pil_img.mode)

        # plt.imshow(pil_img)
        # plt.axis("off")
        # plt.show()
        print("Image mode before resize:", pil_img.mode)
        small = pil_img.convert("RGB").resize((grid_size, grid_size), Image.Resampling.LANCZOS)
        pixels = np.array(small).reshape(-1, 3).astype(float) / 255.0

        print("Sample pixels:", pixels[:10])

        # K-means clustering on reduced set
        kmeans = KMeans(n_clusters=self._n_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)
        colors = kmeans.cluster_centers_
        colors = sort_by_hue(colors=colors)

        # Example visualization
        self.paletteCreated.emit(convert_color_list(colors, 'rgb', 'hex'))