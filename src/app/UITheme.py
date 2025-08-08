import darkdetect
from pathlib import Path
from PyQt6.QtGui import QIcon, QFont, QFontDatabase, QIcon
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QSettings, QSize
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QSlider,
    QHBoxLayout, QPushButton, QFormLayout, QSizePolicy,
    QFrame, QToolButton, QWidget, QApplication, QStyle, QGridLayout
)
from src.app.config import ICONPATH, RESOURCE_PATH, load_stylesheet

def default_font():
    # set default font for application
    font = QFont()
    font.setPointSize(11)
    font.setStyleStrategy(QFont.StyleStrategy.PreferDefault)

    return font

class PreferencesManager(QObject):
    scaleChanged = pyqtSignal(float)
    fontFamilyChanged = pyqtSignal(str)

    SETTINGS_GROUP = "ui"
    KEY_SCALE = "scale"
    KEY_FONT_FAMILY = "font_family"

    BASE_FONT_SIZE = 11
    TOOLBAR_FONT_SIZE = 10
    MIN_FONT = 6
    MAX_FONT = 24

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("YourOrg", "YourApp")
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
        v = max(self.MIN_FONT / self.BASE_FONT_SIZE, min(self.MAX_FONT / self.BASE_FONT_SIZE, v))
        if abs(self._scale - v) < 1e-6:
            return
        self._scale = v
        self.scaleChanged.emit(v)
        self.save()

    @property
    def font_family(self):
        return self._font_family

    @font_family.setter
    def font_family(self, fam: str):
        if self._font_family == fam:
            return
        self._font_family = fam
        self.fontFamilyChanged.emit(fam)
        self.save()

    def effective_font_size(self):
        # base 11 scaled, clamped
        size = round(self.BASE_FONT_SIZE * self._scale)
        return max(self.MIN_FONT, min(self.MAX_FONT, size))

    def effective_toolbar_font_size(self):
        size = round(self.TOOLBAR_FONT_SIZE * self._scale)
        return max(self.MIN_FONT, min(self.MAX_FONT, size))

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
        min_s = self.prefs.MIN_FONT / self.prefs.BASE_FONT_SIZE
        max_s = self.prefs.MAX_FONT / self.prefs.BASE_FONT_SIZE
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
        min_s = self.prefs.MIN_FONT / self.prefs.BASE_FONT_SIZE
        max_s = self.prefs.MAX_FONT / self.prefs.BASE_FONT_SIZE
        slider_pos = self.scale_slider.value()
        scale = (max_s - min_s) * (slider_pos / 100.0) + min_s
        font_family = self.font_combo.currentText()
        font_size = round(self.prefs.BASE_FONT_SIZE * scale)
        font_size = max(self.prefs.MIN_FONT, min(self.prefs.MAX_FONT, font_size))

        # Update preview label for clarity
        self.preview_widget.prefs._scale = scale  # temporarily fudge for preview
        self.preview_widget.prefs._font_family = font_family
        self.preview_widget.update_preview()

    def _reset_defaults(self):
        # reset slider to scale = 1.0 and font to default
        min_s = self.prefs.MIN_FONT / self.prefs.BASE_FONT_SIZE
        max_s = self.prefs.MAX_FONT / self.prefs.BASE_FONT_SIZE
        default_slider = int(round((1.0 - min_s) / (max_s - min_s) * 100))
        self.scale_slider.setValue(default_slider)
        self.font_combo.setCurrentText(self.prefs.font_family)
        self._update_preview()

    def accept(self):
        slider_pos = self.scale_slider.value()
        min_s = self.prefs.MIN_FONT / self.prefs.BASE_FONT_SIZE
        max_s = self.prefs.MAX_FONT / self.prefs.BASE_FONT_SIZE
        new_scale = (max_s - min_s) * (slider_pos / 100.0) + min_s
        self.prefs.scale = new_scale
        self.prefs.font_family = self.font_combo.currentText()
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
        base_font_size = self.prefs.effective_font_size()
        toolbar_font_size = self.prefs.effective_toolbar_font_size()

        # Apply fonts
        normal_font = QFont(font_family, base_font_size)
        self.label_example.setFont(normal_font)

        toolbar_font = QFont(font_family, toolbar_font_size)
        self.toolbar_example.setFont(toolbar_font)

        self.normal_example.setFont(normal_font)
        self.reset_example.setFont(normal_font)

        self.pushbutton_example.setFont(normal_font)
        self.combobox_example.setFont(normal_font)

        # Icon/button sizing
        # Toolbar-style: icon 24x24 scaled
        tb_icon_dim = int(round(24 * scale))
        self.toolbar_example.setIconSize(QSize(tb_icon_dim, tb_icon_dim))
        # Toolbar-style button overall size auto-adjusts (text + icon)

        # Normal toolbutton: base 28x28, icon 20x20 scaled
        tb_size = int(round(28 * scale))
        tb_icon = int(round(20 * scale))
        self.normal_example.setFixedSize(tb_size, tb_size)
        self.normal_example.setIconSize(QSize(tb_icon, tb_icon))

        # Reset button: base 20x20, icon 14x14
        reset_size = int(round(16 * scale))
        reset_icon = int(round(12 * scale))
        self.reset_example.setFixedSize(reset_size, reset_size)
        self.reset_example.setIconSize(QSize(reset_icon, reset_icon))

class ThemeManager(QObject):
    themeChanged = pyqtSignal(str)  # 'dark' or 'light'

    def __init__(self, app):
        super().__init__()
        self.current_theme = 'light'

        self.app = app

    def set_theme(self, theme):
        if theme == self.current_theme:
            return
        self.current_theme = theme
        self.apply_theme()
        self.themeChanged.emit(theme)

    def apply_theme(self):
        if self.current_theme == 'dark':
            self.app.setStyleSheet(open(RESOURCE_PATH / 'styles' / 'dark.qss').read())
        else:
            self.app.setStyleSheet(open(RESOURCE_PATH / 'styles' / 'light.qss').read())

class UIThemes():
    def __init__(self, app, parent):

        self.app = app
        self.parent = parent

        # set theme
        self.view_mode = 0
        self.switch_view_mode(self.view_mode)
        parent.actions.ViewMode.triggered.connect(lambda: self.switch_view_mode(self.view_mode+1))

        self.highlight_color_dark = '#696880'
        self.highlight_color_light = '#FFFFC8'

    def switch_view_mode(self, view_mode):
        if view_mode > 2:
            view_mode = 0
        self.view_mode = view_mode

        match self.view_mode:
            case 0: # auto
                if darkdetect.isDark():
                    #self.set_dark_theme()
                    pass
                else:
                    #self.set_light_theme()
                    pass

                self.parent.actions.ViewMode.setIcon(QIcon(str(ICONPATH / 'icon-sun-and-moon-64.svg')))
                self.parent.actions.ViewMode.setIconText('Theme:\nAuto')
            case 1: # dark
                #self.set_dark_theme()
                pass
            case 2: # light
                #self.set_light_theme()
                pass

    def set_dark_theme(self):
        ss = load_stylesheet('dark.qss')
        self.app.setStyleSheet(ss)

        parent = self.parent

        parent.actions.ViewMode.setIcon(QIcon(str(ICONPATH / 'icon-moon-64.svg')))
        parent.actions.ViewMode.setIconText('Theme:\nDark')

        parent.actions.SelectAnalytes.setIcon(QIcon(str(ICONPATH / 'icon-atom-dark-64.svg')))
        parent.actions.OpenProject.setIcon(QIcon(str(ICONPATH / 'icon-open-session-dark-64.svg')))
        parent.actions.SaveProject.setIcon(QIcon(str(ICONPATH / 'icon-save-session-dark-64.svg')))
        parent.actions.FullMap.setIcon(QIcon(str(ICONPATH / 'icon-fit-to-width-dark-64.svg')))
        parent.actions.Crop.setIcon(QIcon(str(ICONPATH / 'icon-crop-dark-64.svg')))
        parent.actions.SwapAxes.setIcon(QIcon(str(ICONPATH / 'icon-swap-dark-64.svg')))
        # Reset Buttons
        parent.toolButtonXAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-dark-64.svg')))
        parent.toolButtonYAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-dark-64.svg')))
        parent.toolButtonZAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-dark-64.svg')))
        parent.toolButtonCAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-dark-64.svg')))
        #parent.toolButtonClusterColorReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-dark-64.svg')))
        parent.histogram.toolButtonHistogramReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-dark-64.svg')))
        # Samples
        parent.toolBox.setItemIcon(parent.ui.control_dock.tab_dict['sample'],QIcon(str(ICONPATH / 'icon-atom-dark-64.svg')))
        parent.toolBox.setItemIcon(parent.ui.control_dock.tab_dict['process'],QIcon(str(ICONPATH / 'icon-histogram-dark-64.svg')))
        parent.toolBox.setItemIcon(parent.ui.control_dock.tab_dict['dim_red'],QIcon(str(ICONPATH / 'icon-dimensional-analysis-dark-64.svg')))
        parent.toolBox.setItemIcon(parent.ui.control_dock.tab_dict['cluster'],QIcon(str(ICONPATH / 'icon-cluster-dark-64.svg')))
        parent.toolBox.setItemIcon(parent.ui.control_dock.tab_dict['scatter'],QIcon(str(ICONPATH / 'icon-ternary-dark-64.svg')))
        # Spot Data
        if hasattr(parent,"spot_tools"):
            parent.toolButtonSpotMove.setIcon(QIcon(str(ICONPATH / 'icon-move-point-dark-64.svg')))
            parent.toolButtonSpotToggle.setIcon(QIcon(str(ICONPATH / 'icon-show-hide-dark-64.svg')))
            parent.toolButtonSpotSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-dark-64.svg')))
            parent.toolButtonSpotAnalysis.setIcon(QIcon(str(ICONPATH / 'icon-analysis-dark-64.svg')))
            parent.toolButtonSpotRemove.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        #parent.toolButtonFilterSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-dark-64.svg')))
        #parent.toolButtonFilterUp.setIcon(QIcon(str(ICONPATH / 'icon-up-arrow-dark-64.svg')))
        #parent.toolButtonFilterDown.setIcon(QIcon(str(ICONPATH / 'icon-down-arrow-dark-64.svg')))
        #parent.toolButtonFilterRemove.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        # Polygons
        #parent.toolBox.setItemIcon(parent.ui.control_dock.tab_dict['polygons'],QIcon(str(ICONPATH / 'icon-polygon-new-dark-64.svg')))
        #parent.toolButtonPolyCreate.setIcon(QIcon(str(ICONPATH / 'icon-polygon-new-dark-64.svg')))
        #parent.toolButtonPolyAddPoint.setIcon(QIcon(str(ICONPATH / 'icon-add-point-dark-64.svg')))
        #parent.toolButtonPolyRemovePoint.setIcon(QIcon(str(ICONPATH / 'icon-remove-point-dark-64.svg')))
        #parent.toolButtonPolyMovePoint.setIcon(QIcon(str(ICONPATH / 'icon-move-point-dark-64.svg')))
        #parent.toolButtonPolyLink.setIcon(QIcon(str(ICONPATH / 'icon-link-dark-64.svg')))
        #parent.toolButtonPolyDelink.setIcon(QIcon(str(ICONPATH / 'icon-unlink-dark-64.svg')))
        #parent.toolButtonPolyDelete.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        # Profile
        #parent.toolBox.setItemIcon(parent.ui.control_dock.tab_dict['profile'],QIcon(str(ICONPATH / 'icon-profile-dark-64.svg')))
        #parent.toolButtonClearProfile.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        #parent.toolButtonPointDelete.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        #parent.toolButtonPointSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-dark-64.svg')))
        #parent.toolButtonPointMove.setIcon(QIcon(str(ICONPATH / 'icon-move-point-dark-64.svg')))
        #parent.toolButtonProfileInterpolate.setIcon(QIcon(str(ICONPATH / 'icon-interpolate-dark-64.svg')))
        #parent.toolButtonPlotProfile.setIcon(QIcon(str(ICONPATH / 'icon-profile-dark-64.svg')))
        #parent.toolButtonPointDown.setIcon(QIcon(str(ICONPATH / 'icon-down-arrow-dark-64.svg')))
        #parent.toolButtonPointUp.setIcon(QIcon(str(ICONPATH / 'icon-up-arrow-dark-64.svg')))
        # Group Box Plot Tools
        parent.toolButtonHome.setIcon(QIcon(str(ICONPATH / 'icon-home-dark-64.svg')))
        parent.toolButtonRemoveAllMVPlots.setIcon(QIcon(str(ICONPATH / 'icon-delete-dark-64.svg')))
        parent.toolButtonPopFigure.setIcon(QIcon(str(ICONPATH / 'icon-popout-dark-64.svg')))
        parent.toolButtonAnnotate.setIcon(QIcon(str(ICONPATH / 'icon-annotate-dark-64.svg')))
        parent.toolButtonPan.setIcon(QIcon(str(ICONPATH / 'icon-move-dark-64.svg')))
        parent.toolButtonZoom.setIcon(QIcon(str(ICONPATH / 'icon-zoom-dark-64.svg')))
        parent.toolButtonDistance.setIcon(QIcon(str(ICONPATH / 'icon-distance-dark-64.svg')))
        # Calculator
        # Style Toolbox
        parent.toolBoxStyle.setItemIcon(parent.style_tab['axes'],QIcon(str(ICONPATH / 'icon-axes-dark-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['text'],QIcon(str(ICONPATH / 'icon-text-and-scales-dark-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['markers'],QIcon(str(ICONPATH / 'icon-marker-and-lines-dark-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['colors'],QIcon(str(ICONPATH / 'icon-rgb-dark-64.svg')))
        # Cluster tab
        #parent.tabWidgetMask.setItemIcon(parent.mask_tab['cluster'],QIcon(str(ICONPATH / 'icon-cluster-dark-64.svg')))
        #parent.toolButtonClusterLink.setIcon(QIcon(str(ICONPATH / 'icon-link-dark-64.svg')))
        #parent.toolButtonClusterDelink.setIcon(QIcon(str(ICONPATH / 'icon-unlink-dark-64.svg')))

    def set_light_theme(self):
        ss = load_stylesheet('light.qss')
        self.app.setStyleSheet(ss)

        parent = self.parent

        parent.actions.ViewMode.setIcon(QIcon(str(ICONPATH / 'icon-sun-64.svg')))
        parent.actions.ViewMode.setIconText('Theme:\nLight')

        parent.actions.SelectAnalytes.setIcon(QIcon(str(ICONPATH / 'icon-atom-64.svg')))
        parent.actions.OpenProject.setIcon(QIcon(str(ICONPATH / 'icon-open-session-64.svg')))
        parent.actions.SaveProject.setIcon(QIcon(str(ICONPATH / 'icon-save-session-64.svg')))
        parent.actions.FullMap.setIcon(QIcon(str(ICONPATH / 'icon-fit-to-width-64.svg')))
        parent.actions.Crop.setIcon(QIcon(str(ICONPATH / 'icon-crop-64.svg')))
        parent.actions.SwapAxes.setIcon(QIcon(str(ICONPATH / 'icon-swap-64.svg')))
        # Reset Buttons
        parent.toolButtonXAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-64.svg')))
        parent.toolButtonYAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-64.svg')))
        parent.toolButtonZAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-64.svg')))
        parent.toolButtonCAxisReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-64.svg')))
        if hasattr(parent,"mask_dock"):
            parent.mask_dock.actionClusterColorReset.setIcon(QIcon(str(ICONPATH / 'icon-reset-64.svg')))
        # Samples
        parent.toolBox.setItemIcon(parent.ui.control_dock.tab_dict['sample'],QIcon(str(ICONPATH / 'icon-atom-64.svg')))
        parent.toolBox.setItemIcon(parent.ui.control_dock.tab_dict['process'],QIcon(str(ICONPATH / 'icon-histogram-64.svg')))
        parent.toolBox.setItemIcon(parent.ui.control_dock.tab_dict['dim_red'],QIcon(str(ICONPATH / 'icon-dimensional-analysis-64.svg')))
        parent.toolBox.setItemIcon(parent.ui.control_dock.tab_dict['cluster'],QIcon(str(ICONPATH / 'icon-cluster-64.svg')))
        parent.toolBox.setItemIcon(parent.ui.control_dock.tab_dict['scatter'],QIcon(str(ICONPATH / 'icon-ternary-64.svg')))
        # Spot Data
        if hasattr(parent,"spot_tools"):
            parent.toolButtonSpotMove.setIcon(QIcon(str(ICONPATH / 'icon-move-point-64.svg')))
            parent.toolButtonSpotToggle.setIcon(QIcon(str(ICONPATH / 'icon-show-hide-64.svg')))
            parent.toolButtonSpotSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-64.svg')))
            parent.toolButtonSpotAnalysis.setIcon(QIcon(str(ICONPATH / 'icon-analysis-64.svg')))
            parent.toolButtonSpotRemove.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
        # Filter
        if hasattr(parent,"mask_dock"):
            parent.actionFilterSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-64.svg')))
            parent.actionFilterUp.setIcon(QIcon(str(ICONPATH / 'icon-up-arrow-64.svg')))
            parent.actionFilterDown.setIcon(QIcon(str(ICONPATH / 'icon-down-arrow-64.svg')))
            parent.actionFilterRemove.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
            # Polygons
            parent.toolBox.setItemIcon(parent.mask_tab['polygon'],QIcon(str(ICONPATH / 'icon-polygon-new-64.svg')))
            parent.actionPolyCreate.setIcon(QIcon(str(ICONPATH / 'icon-polygon-new-64.svg')))
            parent.actionPolyAddPoint.setIcon(QIcon(str(ICONPATH / 'icon-add-point-64.svg')))
            parent.actionPolyRemovePoint.setIcon(QIcon(str(ICONPATH / 'icon-remove-point-64.svg')))
            parent.actionPolyMovePoint.setIcon(QIcon(str(ICONPATH / 'icon-move-point-64.svg')))
            parent.actionPolyLink.setIcon(QIcon(str(ICONPATH / 'icon-link-64.svg')))
            parent.actionPolyDelink.setIcon(QIcon(str(ICONPATH / 'icon-unlink-64.svg')))
            parent.actionPolyDelete.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
        # Profile
        #parent.toolBox.setItemIcon(parent.ui.control_dock.tab_dict['profile'],QIcon(str(ICONPATH / 'icon-profile-64.svg')))
        #parent.toolButtonClearProfile.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
        #parent.toolButtonPointDelete.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
        #parent.toolButtonPointSelectAll.setIcon(QIcon(str(ICONPATH / 'icon-select-all-64.svg')))
        #parent.toolButtonPointMove.setIcon(QIcon(str(ICONPATH / 'icon-move-point-64.svg')))
        #parent.toolButtonProfileInterpolate.setIcon(QIcon(str(ICONPATH / 'icon-interpolate-64.svg')))
        #parent.toolButtonPlotProfile.setIcon(QIcon(str(ICONPATH / 'icon-profile-64.svg')))
        #parent.toolButtonPointDown.setIcon(QIcon(str(ICONPATH / 'icon-down-arrow-64.svg')))
        #parent.toolButtonPointUp.setIcon(QIcon(str(ICONPATH / 'icon-up-arrow-64.svg')))
        # Group Box Plot Tools
        parent.toolButtonHome.setIcon(QIcon(str(ICONPATH / 'icon-home-64.svg')))
        parent.toolButtonRemoveAllMVPlots.setIcon(QIcon(str(ICONPATH / 'icon-delete-64.svg')))
        parent.toolButtonPopFigure.setIcon(QIcon(str(ICONPATH / 'icon-popout-64.svg')))
        parent.toolButtonAnnotate.setIcon(QIcon(str(ICONPATH / 'icon-annotate-64.svg')))
        parent.toolButtonPan.setIcon(QIcon(str(ICONPATH / 'icon-move-64.svg')))
        parent.toolButtonZoom.setIcon(QIcon(str(ICONPATH / 'icon-zoom-64.svg')))
        parent.toolButtonDistance.setIcon(QIcon(str(ICONPATH / 'icon-distance-64.svg')))
        # Calculator
        parent.actions.Calculator.setIcon(QIcon(str(ICONPATH / 'icon-calculator-64.svg')))
        # Style Toolbox
        parent.toolBoxStyle.setItemIcon(parent.style_tab['axes'],QIcon(str(ICONPATH / 'icon-axes-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['text'],QIcon(str(ICONPATH / 'icon-text-and-scales-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['markers'],QIcon(str(ICONPATH / 'icon-marker-and-lines-64.svg')))
        parent.toolBoxStyle.setItemIcon(parent.style_tab['colors'],QIcon(str(ICONPATH / 'icon-rgb-64.svg')))
        # Cluster tab
        if hasattr(parent, "mask_dock"):
            parent.mask_dock.cluster_tab.setTabIcon(parent.mask_tab['cluster'],QIcon(str(ICONPATH / 'icon-cluster-64.svg')))
            parent.actionClusterLink.setIcon(QIcon(str(ICONPATH / 'icon-link-64.svg')))
            parent.actionClusterDelink.setIcon(QIcon(str(ICONPATH / 'icon-unlink-64.svg')))


