import sys
import os
import json
import numpy as np
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QPointF, QEvent, QStandardPaths
from PyQt6.QtGui import QPainter, QImage, QPixmap, QColor, QPen, QLinearGradient, QPolygon
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QLabel, QSlider, QHBoxLayout, QPushButton,
    QVBoxLayout, QGridLayout, QLineEdit, QFrame, QSizePolicy, QFormLayout, QToolButton, QDialog
)
from src.common.ColorManager2 import convert_color

def fix_bounds(x):
    return max(0.0, min(1.0, float(x)))

# --------------------------- color patch widgets -----------------------------
class HueSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Vertical, parent)
        h = 280
        self.setFixedHeight(248)
        self.setMinimum(0)
        self.setMaximum(360)
        self.setSingleStep(1)
        self.setPageStep(10)
        self.setFixedWidth(24)  # slider bar width
        self.setValue(180)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)  # smoother edges
        rect = self.rect()

        # Draw hue gradient
        gradient = QLinearGradient(QPointF(rect.left(), rect.top()), QPointF(rect.left(), rect.bottom()))
        for i in range(0, 360, 10):
            gradient.setColorAt((360 - i) / 360, QColor.fromHsv(i % 360, 255, 255))
        p.setBrush(gradient)
        p.setPen(Qt.PenStyle.NoPen)

        p.setPen(QPen(QColor("#111111"), 2))
        p.drawRect(rect)

        p.setBrush(QColor("#111111"))  # fill color

        # Handle position
        handle_pos = self._value_to_pos(self.value())
        handle_size = 3

        # Left triangle
        left_triangle = QPolygon([
            QPoint(rect.left() + handle_size*2, handle_pos),
            QPoint(rect.left(), handle_pos - handle_size),
            QPoint(rect.left(), handle_pos + handle_size),
        ])
        p.drawPolygon(left_triangle)

        # Right triangle
        right_triangle = QPolygon([
            QPoint(1+rect.right() - handle_size*2, handle_pos),
            QPoint(1+rect.right(), handle_pos - handle_size),
            QPoint(1+rect.right(), handle_pos + handle_size),
        ])
        p.drawPolygon(right_triangle)
        p.end()

    def _value_to_pos(self, value):
        """Convert slider value to vertical pixel position (top=min, bottom=max)."""
        slider_height = self.height()
        return slider_height - int((value - self.minimum()) / (self.maximum() - self.minimum()) * slider_height)


class DualPatch(QWidget):
    """Shows two color patches: left = selected, right = under-mouse."""
    def __init__(self):
        super().__init__()
        self.sel = (1.0, 1.0, 1.0)
        self.hover = (1.0, 1.0, 1.0)
        self.setMinimumHeight(60)
        self.setMinimumWidth(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_selected(self, rgb):
        self.sel = rgb
        self.update()

    def set_hover(self, rgb):
        self.hover = rgb
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        w = self.width()
        h = self.height()

        # top half: selected
        sr, sg, sb = self.sel
        p.fillRect(QRect(0, h//2, w, h//2), QColor(int(sr*255), int(sg*255), int(sb*255)))

        # right half: hover
        hr, hg, hb = self.hover
        p.fillRect(QRect(0, 0, w, h//2), QColor(int(hr*255), int(hg*255), int(hb*255)))

        # box around it all
        p.setPen(QPen(QColor("#111111"), 2))
        p.drawRect(0, 0, w, h)

        p.end()

# ----------------------------- ternary widget --------------------------------

class TernaryHVWidget(QWidget):
    """
    Ternary with vertices: Black (bottom-left), White (bottom-right), Pure Hue (top).
    A saturation multiplier slider can globally reduce S after picking from triangle.
    """

    # Signals emit RGB as three floats in 0..1
    hoverColor = pyqtSignal(tuple)
    pickColor  = pyqtSignal(tuple)
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        h = 280
        w = int(h/0.866)
        self.setFixedSize(w, h)
        self.margin = 16
        self.hue = 0.5  # default cyan (0.0-1.0 range)
        self.sat_scale = 1.0  # global saturation multiplier (0..1)
        self._img = None  # cached QImage
        self.hover_pos = None
        self.pick_pos = None
        self.pick_rgb = (1.0, 1.0, 1.0)
        self.hover_rgb = (1.0, 1.0, 1.0)

    # --------------------------- geometry helpers ---------------------------
    def triangle_vertices(self):
        w, h = self.width(), self.height()
        m = self.margin
        # Equilateral triangle inscribed in widget rect
        base_y = h - m
        left = QPoint(m, base_y)
        right = QPoint(w - m, base_y)
        top = QPoint((w)//2, m)
        return left, right, top

    def _barycentric(self, x, y):
        """Return (t1,t2,t3) for point against triangle (left,right,top)."""
        left, right, top = self.triangle_vertices()
        x1, y1 = left.x(), left.y()
        x2, y2 = right.x(), right.y()
        x3, y3 = top.x(), top.y()
        denom = ( (y2 - y3)*(x1 - x3) + (x3 - x2)*(y1 - y3) )
        if denom == 0:
            return None
        t1 = ( (y2 - y3)*(x - x3) + (x3 - x2)*(y - y3) ) / denom  # left (black)
        t2 = ( (y3 - y1)*(x - x3) + (x1 - x3)*(y - y3) ) / denom  # right (white)
        t3 = 1.0 - t1 - t2                                        # top (pure hue)
        return (t1, t2, t3)

    def _inside(self, l):
        t1, t2, t3 = l
        eps = -1e-6
        return (t1 >= eps) and (t2 >= eps) and (t3 >= eps)

    # ----------------------------- color logic ------------------------------
    def pure_hue_rgb(self):
        """Convert hue (0-1) to RGB tuple using HSV with full saturation and value"""
        hsv = (self.hue, 1.0, 1.0)
        return convert_color(hsv, "hsv", "rgb", norm_in=True, norm_out=True)

    def mix_color(self, t):
        """RGB from barycentric weights with vertices B(0,0,0), W(1,1,1), H(pure hue)."""
        t1, t2, t3 = t
        H = np.array(self.pure_hue_rgb(), dtype=np.float32)
        rgb = t2 * np.array([1.0, 1.0, 1.0], dtype=np.float32) + t3 * H  # black contributes nothing
        # apply saturation multiplier (preserve V)
        hsv = convert_color(tuple(rgb), "rgb", "hsv", norm_in=True, norm_out=True)
        h, s, v = hsv
        s = fix_bounds(s * self.sat_scale)
        rgb2 = convert_color((h, s, v), "hsv", "rgb", norm_in=True, norm_out=True)
        return rgb2

    # ------------------------------ rendering ------------------------------
    def _render_triangle(self):
        w, h = self.width(), self.height()
        if w <= 2*self.margin or h <= 2*self.margin:
            self._img = None
            return
        left, right, top = self.triangle_vertices()
        # Prepare grid
        xs = np.arange(w, dtype=np.float32)
        ys = np.arange(h, dtype=np.float32)
        X, Y = np.meshgrid(xs, ys)
        x1, y1 = left.x(), left.y()
        x2, y2 = right.x(), right.y()
        x3, y3 = top.x(), top.y()
        denom = ( (y2 - y3)*(x1 - x3) + (x3 - x2)*(y1 - y3) )
        # Barycentric across grid
        T1 = ( (y2 - y3)*(X - x3) + (x3 - x2)*(Y - y3) ) / denom
        T2 = ( (y3 - y1)*(X - x3) + (x1 - x3)*(Y - y3) ) / denom
        T3 = 1.0 - T1 - T2
        mask = (T1 >= 0) & (T2 >= 0) & (T3 >= 0)

        # Colors
        Hrgb = np.array(self.pure_hue_rgb(), dtype=np.float32)
        # Ensure Hrgb is 1D array with 3 elements
        if Hrgb.ndim == 0:
            Hrgb = np.array([Hrgb, Hrgb, Hrgb], dtype=np.float32)
        elif len(Hrgb) != 3:
            raise ValueError(f"Expected RGB tuple with 3 elements, got {len(Hrgb)}")
            
        rgb = np.zeros((h, w, 3), dtype=np.float32)
        # mixture: l2*white + l3*H
        for c in range(3):
            rgb[..., c] = T2 * 1.0 + T3 * Hrgb[c]

        # apply saturation multiplier on masked region
        # convert to HSV and scale S
        # (vectorized conversion using colorsys is tricky; do channel-wise formula)
        R, G, B = rgb[...,0], rgb[...,1], rgb[...,2]
        M = np.maximum.reduce([R, G, B])
        m = np.minimum.reduce([R, G, B])
        C = M - m
        V = M
        # Saturation in HSV: S = 0 if V == 0 else C/V
        S = np.zeros_like(V)
        nz = V > 1e-8
        S[nz] = C[nz] / V[nz]
        S *= self.sat_scale
        # Recompute RGB from H (keep hue from original rgb, but simpler: blend toward gray at same V)
        # Gray at same V: (V,V,V). Interpolate by S' across chroma
        # Find original fully-desaturated color at same V, then mix by S/S0.
        # When original S0 is zero, nothing to do.
        S0 = np.zeros_like(V)
        S0[nz] = (C[nz] / V[nz])
        scale = np.ones_like(S)
        with np.errstate(divide='ignore', invalid='ignore'):
            scale[nz & (S0>0)] = S[nz & (S0>0)] / S0[nz & (S0>0)]
        # move each channel toward V by factor (1-scale)
        for c in range(3):
            rgb[...,c] = V + (rgb[...,c] - V) * scale

        # Compose RGBA image
        img = np.zeros((h, w, 4), dtype=np.uint8)
        img[..., :3] = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
        img[..., 3] = np.where(mask, 255, 0).astype(np.uint8)
        self._img = QImage(img.data, w, h, QImage.Format.Format_RGBA8888)
        # Keep a deep copy so backing array can be freed
        self._img = self._img.copy()

    def set_hue(self, h):
        """Set hue value (expects 0.0-1.0 range)"""
        self.hue = fix_bounds(h)
        self._render_triangle()
        self.update()

    def set_saturation_scale(self, s):
        self.sat_scale = fix_bounds(s)
        self._render_triangle()
        self.update()

    def sizeHint(self):
        return self.minimumSize()

    # ------------------------------ events ---------------------------------
    def resizeEvent(self, event):
        self._render_triangle()
        super().resizeEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        if self._img is None:
            self._render_triangle()
        if self._img is not None:
            p.drawImage(0, 0, self._img)
        # draw triangle border
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(Qt.GlobalColor.black, 1.5))
        left, right, top = self.triangle_vertices()
        p.drawPolygon(left, right, top)
        # draw cursor circle at saved position
        if self.pick_pos is not None:
            p.setPen(QPen(Qt.GlobalColor.white, 1))
            p.drawEllipse(self.pick_pos, 4, 4)
        # draw cursor circle at hover
        if self.hover_pos is not None and self._color_at_point(self.hover_pos) is not None:
            self.setCursor(Qt.CursorShape.BlankCursor)
            p.setPen(QPen(Qt.GlobalColor.white, 1))
            p.drawEllipse(self.hover_pos, 7, 7)
            p.setPen(QPen(Qt.GlobalColor.black, 1))
            p.drawEllipse(self.hover_pos, 6, 6)
            p.setPen(QPen(Qt.GlobalColor.white, 1))
            p.drawEllipse(self.hover_pos, 5, 5)
        elif self.hover_pos is not None and self._color_at_point(self.hover_pos) is None:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        p.end()

    def _color_at_point(self, pos):
        t = self._barycentric(pos.x(), pos.y())
        if t is None:
            return None
        if not self._inside(t):
            return None
        return self.mix_color(t)

    def mouseMoveEvent(self, event):
        self.hover_pos = event.position().toPoint()
        c = self._color_at_point(self.hover_pos)
        if c is not None:
            self.hover_rgb = c
            self.hoverColor.emit(c)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            c = self._color_at_point(pos)
            if c is not None:
                self.pick_pos = pos
                self.pick_rgb = c
                self.pickColor.emit(c)
                self.update()

# ------------------------------- dialog --------------------------------

class ColorSelectorDialog(QDialog):
    """Color selector as a dialog that can return a color or None"""
    
    def __init__(self, initial_color=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Color Selector")
        self.setModal(True)
        self.selected_color = None  # Will be set to hex string if OK is pressed
        
        # Set initial color or default to white
        if initial_color:
            try:
                self.current_color = convert_color(initial_color, "hex", "rgb", norm_out=True)
            except:
                self.current_color = (0.0, 1.0, 1.0)
        else:
            self.current_color = (0.0, 1.0, 1.0)

        self.setupUI()
        self.load_color_history()
        
        # Initialize display with starting color
        self.on_pick_color(self.current_color)
        
        # Set hue slider to match initial color
        hsv = convert_color(self.current_color, "rgb", "hsv", norm_in=True, norm_out=True)
        self.hue_slider.setValue(int(hsv[0] * 360))  # Convert from 0-1 to 0-360

    def setupUI(self):
        font = self.font()
        font.setPixelSize(11)
        self.setFont(font)

        self.ternary = TernaryHVWidget()

        # Controls: Hue slider (0..360)
        self.hue_slider = HueSlider()
        self.hue_slider.valueChanged.connect(self._on_hue_changed)

        # Text edits for HSV
        self.text_H = QLineEdit()
        self.text_S = QLineEdit()
        self.text_V = QLineEdit()

        # strip units when editing
        self.text_H.installEventFilter(self)
        self.text_S.installEventFilter(self)
        self.text_V.installEventFilter(self)

        # update HSV on edit
        self.text_H.editingFinished.connect(self.on_text_H_finished)
        self.text_S.editingFinished.connect(lambda: self.on_text_SV_finished(self.text_S))
        self.text_V.editingFinished.connect(lambda: self.on_text_SV_finished(self.text_V))

        # Text edits for RGB
        self.text_R = QLineEdit()
        self.text_G = QLineEdit()
        self.text_B = QLineEdit()

        # update RGB on edit
        self.text_R.editingFinished.connect(lambda: self.on_text_RGB_finished(self.text_R))
        self.text_G.editingFinished.connect(lambda: self.on_text_RGB_finished(self.text_G))
        self.text_B.editingFinished.connect(lambda: self.on_text_RGB_finished(self.text_B))

        self.text_hex = QLineEdit()

        # Dual color patch
        self.patches = DualPatch()

        display_widget = QWidget()
        display_widget.setMaximumWidth(100)
        display_layout = QVBoxLayout()
        display_layout.setContentsMargins(3, 3, 3, 0)
        display_widget.setLayout(display_layout)

        display_layout.addWidget(self.patches)

        form_layout = QFormLayout()
        form_layout.setSpacing(5)
        form_layout.setContentsMargins(3, 3, 3, 0)

        # --- Text boxes with color data ---
        form_layout.addRow(QLabel("H:"), self.text_H)
        form_layout.addRow(QLabel("S:"), self.text_S)
        form_layout.addRow(QLabel("V:"), self.text_V)
        form_layout.addRow(QLabel("R:"), self.text_R)
        form_layout.addRow(QLabel("G:"), self.text_G)
        form_layout.addRow(QLabel("B:"), self.text_B)
        form_layout.addRow(QLabel("HEX:"), self.text_hex)

        display_layout.addLayout(form_layout)

        # --- Color history (2 rows of 8) ---
        self.color_history = [None] * 16
        history_widget = QWidget()
        history_layout = QGridLayout(history_widget)
        history_layout.setSpacing(4)
        self.history_buttons = []
        for row in range(2):
            for col in range(8):
                btn = QToolButton()
                btn.setFixedSize(40, 25)
                btn.setStyleSheet("background-color: none; border: 1px solid #111111; border-radius: 4px;")
                btn.clicked.connect(lambda checked, b=btn: self.restore_color(b))
                history_layout.addWidget(btn, row, col)
                self.history_buttons.append(btn)

        # --- Buttons ---
        button_widget = QWidget()
        button_layout = QVBoxLayout(button_widget)
        self.btn_save = QPushButton("Save")
        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")
        button_layout.addWidget(self.btn_save)
        button_layout.addWidget(self.btn_ok)
        button_layout.addWidget(self.btn_cancel)

        # Connect buttons
        self.btn_save.clicked.connect(self.save_color)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        picker_layout = QHBoxLayout()
        picker_layout.addWidget(self.ternary)
        picker_layout.addWidget(self.hue_slider)
        picker_layout.addWidget(display_widget)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(history_widget)
        bottom_layout.addWidget(button_widget)

        main_layout = QVBoxLayout()
        main_layout.addLayout(picker_layout)
        main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)

        # Initialize readouts
        self.ternary.hoverColor.connect(self.on_hover_color)
        self.ternary.pickColor.connect(self.on_pick_color)

    def get_config_path(self):
        """Get path for storing color history"""
        config_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "color_history.json")

    def load_color_history(self):
        """Load color history from file"""
        try:
            config_path = self.get_config_path()
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    self.color_history = data.get('history', [None] * 16)
                    # Ensure we have exactly 16 entries
                    while len(self.color_history) < 16:
                        self.color_history.append(None)
                    self.color_history = self.color_history[:16]
                    
                    # Update button displays
                    for btn, color in zip(self.history_buttons, self.color_history):
                        if color is not None:
                            btn.setStyleSheet(f"background-color: {color}; border: 1px solid #111111; border-radius: 4px;")
                            btn.setToolTip(color)
        except Exception as e:
            print(f"Error loading color history: {e}")
            self.color_history = [None] * 16

    def save_color_history(self):
        """Save color history to file"""
        try:
            config_path = self.get_config_path()
            data = {'history': self.color_history}
            with open(config_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving color history: {e}")

    # -------------------------- slots / callbacks ---------------------------
    def eventFilter(self, source, event):
        """Event filter: remove units when editing starts"""
        if source is self.text_H:
            if event.type() == QEvent.Type.FocusIn:
                txt = self.text_H.text().replace("°", "").strip()
                self.text_H.setText(txt)
        elif source in [self.text_S, self.text_V]:
            if event.type() == QEvent.Type.FocusIn:
                txt = source.text().replace("%", "").strip()
                source.setText(txt)
        return super().eventFilter(source, event)

    def on_text_H_finished(self):
        """Handle hue editing finished: validate + update color"""
        text = self.text_H.text().strip().replace("°", "")
        try:
            val = int(text)
            if not (0 <= val <= 359):
                raise ValueError("Hue must be between 0 and 360")
        except ValueError:
            # restore previous value
            if self.current_color is not None:
                hsv = convert_color(self.current_color, "rgb", "hsv", norm_in=True, norm_out=True)
                self.text_H.setText(f"{int(hsv[0]*360)}°")
                return
            else:
                self.text_H.setText("0°")
                return

        # Update HSV
        hsv = convert_color(self.current_color, "rgb", "hsv", norm_in=True, norm_out=True)
        hsv = (val / 360.0, hsv[1], hsv[2])  # Convert to 0-1 range
        
        # Convert to RGB and update everything else
        rgb = convert_color(hsv, "hsv", "rgb", norm_in=True, norm_out=True)
        self.on_pick_color(rgb)
        self.hue_slider.setValue(val)

    def on_text_SV_finished(self, source):
        """Handle saturation or value editing finished: validate + update color"""
        text = source.text().strip().replace("%", "")
        idx = 1 if source is self.text_S else 2

        try:
            val = int(text)
            if not (0 <= val <= 100):
                raise ValueError("Saturation and Value must be between 0 and 100")
        except ValueError:
            # restore previous value
            if self.current_color is not None:
                hsv = convert_color(self.current_color, "rgb", "hsv", norm_in=True, norm_out=True)
                source.setText(f"{int(hsv[idx]*100)}%")
                return
            else:
                source.setText("100%")
                return

        # Update HSV
        hsv = convert_color(self.current_color, "rgb", "hsv", norm_in=True, norm_out=True)
        val = val / 100.0  # Convert to 0-1 range
        hsv = (hsv[0], val, hsv[2]) if idx == 1 else (hsv[0], hsv[1], val)

        # Convert to RGB and update everything else
        rgb = convert_color(hsv, "hsv", "rgb", norm_in=True, norm_out=True)
        self.on_pick_color(rgb)

    def on_text_RGB_finished(self, source):
        """Handle RGB editing finished: validate + update color"""
        if source is self.text_R:
            idx = 0
        elif source is self.text_G:
            idx = 1
        else:  # self.text_B
            idx = 2

        text = source.text()
        try:
            val = int(text)
            if not (0 <= val <= 255):
                raise ValueError("RGB channels must be between 0 and 255")
        except ValueError:
            # restore previous value
            if self.current_color is not None:
                rgb = self.current_color
                source.setText(f"{int(rgb[idx]*255)}")
                return
            else:
                source.setText("255")
                return

        # Update RGB
        rgb = list(self.current_color)
        rgb[idx] = float(val) / 255.0  # Convert to 0-1 range
        rgb = tuple(rgb)

        # Update everything
        self.on_pick_color(rgb)

    def _on_hue_changed(self, val):
        """Convert hue slider value (0-360) to normalized value (0.0-1.0) for ternary widget"""
        normalized_hue = val / 360.0  # Convert from 0-360 to 0.0-1.0
        self.ternary.set_hue(normalized_hue)

    def on_pick_color(self, rgb):
        hsv = convert_color(rgb, "rgb", "hsv", norm_in=True, norm_out=True)
        # Format with proper units
        self.text_H.setText(f"{int(hsv[0]*360)}°")  # Convert from 0-1 to 0-360
        self.text_S.setText(f"{int(hsv[1]*100)}%")
        self.text_V.setText(f"{int(hsv[2]*100)}%")
        self.text_R.setText(f"{int(rgb[0]*255)}")
        self.text_G.setText(f"{int(rgb[1]*255)}")
        self.text_B.setText(f"{int(rgb[2]*255)}")
        self.text_hex.setText(convert_color(rgb, "rgb", "hex", norm_in=True))
        self.patches.set_selected(rgb)
        self.current_color = rgb

    def on_hover_color(self, rgb):
        self.patches.set_hover(rgb)

    def save_color(self):
        """Save current pick_color into history (button backgrounds)."""
        hex_color = convert_color(self.current_color, "rgb", "hex", norm_in=True)
        # Shift colors, insert new at front
        self.color_history = [hex_color] + self.color_history[:-1]
        for btn, color in zip(self.history_buttons, self.color_history):
            if color is not None:
                btn.setStyleSheet(f"background-color: {color}; border: 1px solid #111111; border-radius: 4px;")
                btn.setToolTip(color)

    def restore_color(self, button):
        """When a history button is clicked, use its color."""
        color = button.toolTip()
        if color:
            rgb = convert_color(color, "hex", "rgb", norm_out=True)
            self.on_pick_color(rgb)
            # Update hue slider
            hsv = convert_color(rgb, "rgb", "hsv", norm_in=True, norm_out=True)
            self.hue_slider.setValue(int(hsv[0] * 360))  # Convert from 0-1 to 0-360

    def accept(self):
        """Called when OK is pressed - save the selected color"""
        self.selected_color = convert_color(self.current_color, "rgb", "hex", norm_in=True)
        self.save_color_history()
        super().accept()

    def reject(self):
        """Called when Cancel is pressed or dialog is closed without OK"""
        self.selected_color = None
        super().reject()

    def closeEvent(self, event):
        """Handle window close button - same as cancel"""
        self.selected_color = None
        super().closeEvent(event)


# Legacy MainWindow class for standalone operation
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Color Selector")
        self.current_color = (1.0, 1.0, 1.0)
        self.setupUI()

    def setupUI(self):
        # Create the dialog content as central widget
        self.dialog = ColorSelectorDialog()
        self.setCentralWidget(self.dialog)
        
        # Override the dialog buttons for main window
        self.dialog.btn_ok.setText("Apply")
        self.dialog.btn_cancel.setText("Exit")
        
        # Connect buttons differently
        self.dialog.btn_ok.clicked.disconnect()
        self.dialog.btn_cancel.clicked.disconnect()
        self.dialog.btn_ok.clicked.connect(self.apply_color)
        self.dialog.btn_cancel.clicked.connect(self.close)

    def apply_color(self):
        """Handle Apply button in standalone mode"""
        print("Selected color:", convert_color(self.dialog.current_color, "rgb", "hex", norm_in=True))


# ----------------------------- Convenience Functions -------------------------

def select_color(initial_color=None, parent=None):
    """
    Show color selector dialog and return selected color.
    
    Args:
        initial_color: Initial color as hex string (e.g., "#FF0000") or None for white
        parent: Parent widget for the dialog
        
    Returns:
        Selected color as hex string (e.g., "#FF0000") or None if cancelled
    """
    dialog = ColorSelectorDialog(initial_color, parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.selected_color
    return None


# --------------------------------- app run -----------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Example of using as dialog
    if len(sys.argv) > 1 and sys.argv[1] == "--dialog":
        initial_color = "#FF5733" if len(sys.argv) > 2 else None
        result = select_color(initial_color)
        if result:
            print(f"Selected color: {result}")
        else:
            print("No color selected")
    else:
        # Run as standalone application
        w = MainWindow()
        w.show()
        sys.exit(app.exec())