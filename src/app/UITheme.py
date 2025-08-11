import darkdetect
from pathlib import Path
from PyQt6.QtGui import QIcon, QFont, QFontDatabase, QIcon, QAction
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QSettings, QSize, QTimer
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QSlider,
    QHBoxLayout, QPushButton, QFormLayout, QSizePolicy,
    QFrame, QToolButton, QWidget, QApplication, QStyle, QGridLayout
)
from src.app.config import ICONPATH, STYLE_PATH, load_stylesheet

def default_font():
    # set default font for application
    font = QFont()
    font.setPointSize(11)
    font.setStyleStrategy(QFont.StyleStrategy.PreferDefault)

    return font

def apply_font_to_children(widget, font: QFont):
    widget.setFont(font)
    for child in widget.findChildren(QWidget):
        child.setFont(font)

class PreferencesManager(QObject):
    scaleChanged = pyqtSignal(float)
    fontFamilyChanged = pyqtSignal(str)
    settingsChanged = pyqtSignal()

    SETTINGS_GROUP = "ui"
    KEY_SCALE = "scale"
    KEY_FONT_FAMILY = "font_family"

    DEFAULT_FONT_SIZE = 11
    TOOLBAR_FONT_SIZE = 10
    MIN_FONT = 6
    MAX_FONT = 24

    TOOLBAR_ICON_SIZE = 24

    TOOLBUTTON_ICON_SIZE = 21
    TOOLBUTTON_SIZE = 28

    RESET_BUTTON_ICON_SIZE = 12
    RESET_BUTTON_SIZE = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("Adelaide University", "LaME")
        self._load()

    def _load(self):
        self.settings.beginGroup(self.SETTINGS_GROUP)
        self._scale = self.settings.value(self.KEY_SCALE, 1.0, type=float)
        self._font_family = self.settings.value(self.KEY_FONT_FAMILY, "Segoe UI", type=str)
        self.settings.endGroup()

    def save(self):
        self.settings.beginGroup(self.SETTINGS_GROUP)
        self.settings.setValue(self.KEY_SCALE, self._scale)
        self.settings.setValue(self.KEY_FONT_FAMILY, self._font_family)
        self.settings.endGroup()

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, v: float):
        v = max(self.MIN_FONT / self.DEFAULT_FONT_SIZE, min(self.MAX_FONT / self.DEFAULT_FONT_SIZE, v))
        if abs(self._scale - v) < 1e-6:
            return
        self._scale = v
        self.save()

    @property
    def font_family(self):
        return self._font_family

    @font_family.setter
    def font_family(self, fam: str):
        if self._font_family == fam:
            return
        self._font_family = fam
        self.save()

    def default_font_size(self):
        # base 11 scaled, clamped
        size = round(self.DEFAULT_FONT_SIZE * self._scale)
        return max(self.MIN_FONT, min(self.MAX_FONT, size))

    def toolbar_font_size(self):
        size = round(self.TOOLBAR_FONT_SIZE * self._scale)
        return max(self.MIN_FONT, min(self.MAX_FONT, size))

    def scale_size(self, base: int) -> int:
        return int(round(base * self._scale))

    def property(self):
        return {
            "font": QFont(self._font_family, self.default_font_size()),
            "toolbar_font": QFont(self._font_family, self.toolbar_font_size()),
            "toolbar_icon_size": QSize(self.scale_size(self.TOOLBAR_ICON_SIZE), self.scale_size(self.TOOLBAR_ICON_SIZE)),
            "toolbutton_icon_size": QSize(self.scale_size(self.TOOLBUTTON_ICON_SIZE),self.scale_size(self.TOOLBUTTON_ICON_SIZE)),
            "toolbutton_size": QSize(self.scale_size(self.TOOLBUTTON_SIZE),self.scale_size(self.TOOLBUTTON_SIZE)),
            "reset_button_icon_size": QSize(self.scale_size(self.RESET_BUTTON_ICON_SIZE),self.scale_size(self.RESET_BUTTON_ICON_SIZE)),
            "reset_button_size": QSize(self.scale_size(self.RESET_BUTTON_SIZE),self.scale_size(self.RESET_BUTTON_SIZE)),
        }

    @staticmethod
    def available_font_families():
        families = QFontDatabase.families()

        # def is_sans_serif(family: str) -> bool:
        #     # crude heuristic: reject overly decorative by excluding known serif or script
        #     info = QFontDatabase.font(family, "", 12)
        #     # Accept if it's not identified as a serif in its style hints
        #     return True  # could refine if needed

        # def is_monospace(family: str) -> bool:
        #     return QFontDatabase.isFixedPitch(family)

        # # Build whitelist: all monospaced plus families containing common sans keywords
        # result = set()
        # for f in families:
        #     if is_sans_serif(f) or is_monospace(f):
        #         result.add(f)
        # Common generic sans serif families to include explicitly if present
        result = set()
        for candidate in (".AppleSystemUIFont", "Avenir", "Futura", "Candara", "Myriad Pro" ,"Myriad", "Segoe UI", "Arial", "Helvetica", "Ubuntu", "Calibri", "DejaVu Sans", "Verdana", "Tahoma", "Aptos"):
            if candidate in families:
                result.add(candidate)
        return sorted(result)
    
class PreferencesDialog(QDialog):
    def __init__(self, prefs: "PreferencesManager", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.prefs = prefs

        layout = QVBoxLayout(self)

        form = QFormLayout()
        # Font family selector
        self.font_combo = QComboBox()
        self.font_combo.addItems(self.prefs.available_font_families())
        current_index = self.font_combo.findText(self.prefs.font_family)
        if current_index >= 0:
            self.font_combo.setCurrentIndex(current_index)
        form.addRow("Font Family:", self.font_combo)

        # Scale slider
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(0, 100)
        self.scale_slider.setSingleStep(5)
        self.scale_slider.setTickInterval(10)
        min_s = self.prefs.MIN_FONT / self.prefs.DEFAULT_FONT_SIZE
        max_s = self.prefs.MAX_FONT / self.prefs.DEFAULT_FONT_SIZE
        slider_pos = int(round((self.prefs.scale - min_s) / (max_s - min_s) * 100))
        self.scale_slider.setValue(slider_pos)
        form.addRow("UI Scale:", self.scale_slider)

        layout.addLayout(form)

        # Preview label + box
        preview_label = QLabel("Preview:")
        preview_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(preview_label) 

        self.preview_widget = PreviewWidget(self.prefs)
        # align left: wrap in a horizontal layout to prevent expansion
        hl = QHBoxLayout()
        hl.addWidget(self.preview_widget)
        hl.addStretch()
        layout.addLayout(hl)

        # Buttons
        btns = QHBoxLayout()
        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_reset = QPushButton("Reset to Defaults")
        btns.addWidget(self.btn_reset)
        btns.addStretch()
        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_ok)
        layout.addLayout(btns)

        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_reset.clicked.connect(self._reset_defaults)
        self.font_combo.currentTextChanged.connect(self._on_change)
        self.scale_slider.valueChanged.connect(self._on_change)

        self._update_preview()

    def _on_change(self, *_):
        self._update_preview()

    def _update_preview(self):
        min_s = self.prefs.MIN_FONT / self.prefs.DEFAULT_FONT_SIZE
        max_s = self.prefs.MAX_FONT / self.prefs.DEFAULT_FONT_SIZE
        slider_pos = self.scale_slider.value()
        scale = (max_s - min_s) * (slider_pos / 100.0) + min_s
        font_family = self.font_combo.currentText()
        font_size = round(self.prefs.DEFAULT_FONT_SIZE * scale)
        font_size = max(self.prefs.MIN_FONT, min(self.prefs.MAX_FONT, font_size))

        # Update preview label for clarity
        self.preview_widget.prefs._scale = scale  # temporarily fudge for preview
        self.preview_widget.prefs._font_family = font_family
        self.preview_widget.update_preview()

    def _reset_defaults(self):
        # reset slider to scale = 1.0 and font to default
        min_s = self.prefs.MIN_FONT / self.prefs.DEFAULT_FONT_SIZE
        max_s = self.prefs.MAX_FONT / self.prefs.DEFAULT_FONT_SIZE
        default_slider = int(round((1.0 - min_s) / (max_s - min_s) * 100))
        self.scale_slider.setValue(default_slider)
        self.font_combo.setCurrentText(self.prefs.font_family)
        self._update_preview()

    def accept(self):
        slider_pos = self.scale_slider.value()
        min_s = self.prefs.MIN_FONT / self.prefs.DEFAULT_FONT_SIZE
        max_s = self.prefs.MAX_FONT / self.prefs.DEFAULT_FONT_SIZE
        new_scale = (max_s - min_s) * (slider_pos / 100.0) + min_s
        self.prefs.scale = new_scale
        self.prefs.font_family = self.font_combo.currentText()
        self.prefs.settingsChanged.emit()
        super().accept()


# Assuming PreferencesManager from earlier is available as prefs

class PreviewWidget(QFrame):
    def __init__(self, prefs: "PreferencesManager", parent=None):
        super().__init__(parent)
        self.prefs = prefs
        self.setFrameShape(QFrame.Shape.Box)
        self.setFixedSize(350, 200)  # adjust as needed
        layout = QGridLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Toolbar-style button (icon + text)
        toolbar_label = QLabel()
        toolbar_label.setText("Toolbar action")
        toolbar_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.toolbar_example = QToolButton()
        self.toolbar_example.setText("Toolbar")
        self.toolbar_example.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.toolbar_example.setToolTip("Toolbar action (icon + text)")
        self.toolbar_example.setAutoRaise(True)
        self.toolbar_example.setIcon(QIcon(str(ICONPATH / "LaME-64.svg")))

        # Normal toolbutton (icon only)
        icon_label = QLabel()
        icon_label.setText("Normal icon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.normal_example = QToolButton()
        self.normal_example.setText("Icons")
        self.normal_example.setAutoRaise(True)
        self.normal_example.setToolTip("Normal toolbutton (icon only)")
        self.normal_example.setIcon(QIcon(str(ICONPATH / "icon-launch-64.svg")))

        # Reset-style toolbutton (smaller)
        reset_label = QLabel()
        reset_label.setText("Reset button")
        reset_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.reset_example = QToolButton()
        self.reset_example.setToolTip("Reset button (small)")
        self.reset_example.setAutoRaise(True)
        self.reset_example.setIcon(QIcon(str(ICONPATH / "icon-reset-64.svg")))

        self.label_example = QLabel()
        self.label_example.setText("This is an example of the text size.")

        self.pushbutton_example = QPushButton()
        self.pushbutton_example.setText("Click")

        self.combobox_example = QComboBox()
        self.combobox_example.addItems(["Item 1", "Item 2", "Item 3", "..."])

        layout.addWidget(self.label_example, 0, 0, 1, 3)
        layout.addWidget(toolbar_label, 1, 0, 1, 1)
        layout.addWidget(icon_label, 1, 1, 1, 1)
        layout.addWidget(reset_label, 1, 2, 1, 1)
        layout.addWidget(self.toolbar_example, 2, 0, 1, 1)
        layout.setAlignment(self.toolbar_example, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.normal_example, 2, 1, 1, 1)
        layout.setAlignment(self.normal_example, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.reset_example, 2, 2, 1, 1)
        layout.setAlignment(self.reset_example, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.pushbutton_example, 3, 0, 1, 1)
        layout.setAlignment(self.pushbutton_example, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.combobox_example, 3, 1, 1, 2)

        # Connect to preference changes
        prefs.scaleChanged.connect(self.update_preview)
        prefs.fontFamilyChanged.connect(self.update_preview)

        self.update_preview(prefs.scale)

    def update_preview(self, *args):
        scale = self.prefs.scale
        font_family = self.prefs.font_family

        # Base font sizes
        default_font_size = self.prefs.default_font_size()
        toolbar_font_size = self.prefs.toolbar_font_size()

        # Apply fonts
        normal_font = QFont(font_family, default_font_size)
        self.label_example.setFont(normal_font)

        toolbar_font = QFont(font_family, toolbar_font_size)
        self.toolbar_example.setFont(toolbar_font)

        self.normal_example.setFont(normal_font)
        self.reset_example.setFont(normal_font)

        self.pushbutton_example.setFont(normal_font)
        self.combobox_example.setFont(normal_font)

        # Icon/button sizing
        # Toolbar-style: icon 24x24 scaled
        tb_icon_dim = int(round(self.prefs.TOOLBAR_ICON_SIZE * scale))
        self.toolbar_example.setIconSize(QSize(tb_icon_dim, tb_icon_dim))
        # Toolbar-style button overall size auto-adjusts (text + icon)

        # Normal toolbutton: base 28x28, icon 20x20 scaled
        tb_size = int(round(self.prefs.TOOLBUTTON_SIZE * scale))
        tb_icon = int(round(self.prefs.TOOLBUTTON_ICON_SIZE * scale))
        self.normal_example.setFixedSize(tb_size, tb_size)
        self.normal_example.setIconSize(QSize(tb_icon, tb_icon))

        # Reset button: base 20x20, icon 14x14
        reset_size = int(round(self.prefs.RESET_BUTTON_SIZE * scale))
        reset_icon = int(round(self.prefs.RESET_BUTTON_ICON_SIZE * scale))
        self.reset_example.setFixedSize(reset_size, reset_size)
        self.reset_example.setIconSize(QSize(reset_icon, reset_icon))

class ThemeManager(QObject):
    """Manages application theme (light/dark/auto) and notifies listeners."""

    theme_changed = pyqtSignal(str)  # "light" or "dark"

    def __init__(self, initial="auto", parent=None):
        super().__init__(parent)
        self._mode = initial  # "auto", "dark", "light"
        self.view_mode = 0  # 0=auto, 1=dark, 2=light
        self._current_theme = None
        self._poll_timer = None
        self.parent = parent

        self.highlight_color_dark = '#696880'
        self.highlight_color_light = '#FFFFC8'

        if self._mode == "auto":
            self._start_auto_detection()
        else:
            self.set_theme(self._mode)

    @property
    def theme(self) -> str:
        return self._current_theme

    def set_mode(self, mode: str):
        """Set mode to 'light', 'dark', or 'auto'."""
        self._mode = mode
        if mode == "auto":
            self.view_mode = 0
            self._start_auto_detection()
        elif mode == "dark":
            self.view_mode = 1
            self._stop_auto_detection()
            self.set_theme("dark")
        elif mode == "light":
            self.view_mode = 2
            self._stop_auto_detection()
            self.set_theme("light")

        self._update_view_mode_action()

    def cycle_mode(self):
        """Cycle through Auto → Dark → Light → Auto."""
        self.view_mode = (self.view_mode + 1) % 3
        if self.view_mode == 0:
            self.set_mode("auto")
        elif self.view_mode == 1:
            self.set_mode("dark")
        elif self.view_mode == 2:
            self.set_mode("light")

    def _start_auto_detection(self):
        """Starts polling system theme."""
        if not self._poll_timer:
            self._poll_timer = QTimer(self)
            self._poll_timer.timeout.connect(self._check_system_theme)
            self._poll_timer.start(60000)  # every 60 seconds
        self._check_system_theme()

    def _stop_auto_detection(self):
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None

    def _check_system_theme(self):
        system_theme = "dark" if darkdetect.isDark() else "light"
        if system_theme != self._current_theme:
            self.set_theme(system_theme)

    def set_theme(self, theme: str):
        """Force set theme to 'light' or 'dark' and notify listeners."""
        if theme in ("light", "dark") and theme != self._current_theme:
            self._current_theme = theme
            self._apply_stylesheet(theme)
            self.theme_changed.emit(theme)

    def _apply_stylesheet(self, theme: str):
        """Apply the appropriate QSS stylesheet."""
        qss_file = STYLE_PATH / f'{theme}.qss'
        if qss_file.exists():
            with open(qss_file, 'r') as f:
                self.parent.app.setStyleSheet(f.read())
        else:
            print(f"Stylesheet not found: {qss_file}")

    def _update_view_mode_action(self):
        """Update icon and tooltip based on current view_mode."""
        if not self.parent.lame_action.ViewMode:
            return

        icons = {
            0: ('icon-sun-and-moon-64.svg', 'Theme:\nAuto'),
            1: ('icon-moon-64.svg', 'Theme:\nDark'),
            2: ('icon-sun-64.svg', 'Theme:\nLight')
        }

        icon_file, text = icons[self.view_mode]
        icon_path = ICONPATH / icon_file

        if isinstance(self.parent.lame_action.ViewMode, QAction):
            self.parent.lame_action.ViewMode.setIcon(QIcon(str(icon_path)))
            self.parent.lame_action.ViewMode.setText(text)
        else:  # QToolButton or similar
            self.parent.lame_action.ViewMode.setIcon(QIcon(str(icon_path)))
            self.parent.lame_action.ViewMode.setText(text)






