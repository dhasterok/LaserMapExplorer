import os, re, copy, pickle
from PyQt6.QtWidgets import (
    QColorDialog, QTableWidgetItem, QMessageBox, QInputDialog, QSizePolicy, QComboBox, QLabel,
    QToolButton, QCheckBox, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QFrame, QSpacerItem, QLayout, QLineEdit, QDoubleSpinBox, QFontComboBox, QSpinBox, QMainWindow
)
from PyQt6.QtGui import ( QDoubleValidator, QFont, QFontDatabase, QIcon )
from PyQt6.QtCore import Qt, QSize, QRect
from src.common.CustomWidgets import (
    CustomDockWidget, CustomToolButton, CustomSlider, CustomLineEdit, CustomPage, CustomComboBox, ColorButton, CustomToolBox 
)
from pyqtgraph import colormap
import src.common.format as fmt
import numpy as np
import pandas as pd
import src.common.csvdict as csvdict
from src.common.colorfunc import get_hex_color, get_rgb_color
from src.app.config import BASEDIR, ICONPATH
from src.common.Logger import auto_log_methods, log
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .MainWindow import MainWindow

class AxesPage(CustomPage):
    def __init__(self, parent=None):
        super().__init__(obj_name="StyleAxes", parent=parent)

        self.setupUI(parent)

    def setupUI(self, parent):
        self.setGeometry(QRect(0, 0, 323, 807))

        form_layout = QFormLayout()

        self.lineEditXLabel = QLineEdit(parent=self)
        self.lineEditXLabel.setObjectName("lineEditXLabel")

        self.widgetXLimLabel = QWidget(parent=self)
        x_lim_label_layout = QHBoxLayout()
        x_lim_label_layout.setContentsMargins(0, 0, 0, 0)
        self.widgetXLimLabel.setLayout(x_lim_label_layout)

        x_lim_label = QLabel(parent=self)
        x_lim_label.setText("X Limits")

        self.toolButtonXAxisReset = CustomToolButton(
            text="Reset",
            light_icon_unchecked="icon-reset-64.svg",
            dark_icon_unchecked="icon-reset-dark-64.svg",
            parent=self)
        self.toolButtonXAxisReset.setObjectName("toolButtonXAxisReset")
        self.toolButtonXAxisReset.setFixedSize(QSize(20,20))
        self.toolButtonXAxisReset.setIconSize(QSize(14, 14))

        x_lim_label_layout.addWidget(x_lim_label)
        x_lim_label_layout.addWidget(self.toolButtonXAxisReset)

        self.widgetXLim = QWidget(parent=self)
        x_lim_layout = QHBoxLayout()
        x_lim_layout.setContentsMargins(0, 0, 0, 0)
        self.widgetXLim.setLayout(x_lim_layout)

        self.lineEditXLB = CustomLineEdit(parent=self)
        self.lineEditXLB.setObjectName("lineEditXLB")

        self.lineEditXUB = CustomLineEdit(parent=self)
        self.lineEditXUB.setObjectName("lineEditXUB")

        x_lim_layout.addWidget(self.lineEditXLB)
        x_lim_layout.addWidget(self.lineEditXUB)

        self.comboBoxXScale = QComboBox(parent=self)
        self.comboBoxXScale.setObjectName("comboBoxXScale")

        line_x = QFrame(parent=self)
        line_x.setFrameShape(QFrame.Shape.HLine)
        line_x.setFrameShadow(QFrame.Shadow.Sunken)

        form_layout.addRow("X Label", self.lineEditXLabel)
        form_layout.addRow(self.widgetXLimLabel, self.widgetXLim)
        form_layout.addRow("X Scale", self.comboBoxXScale)
        form_layout.addRow("", line_x)

        self.lineEditYLabel = QLineEdit(parent=self)
        self.lineEditYLabel.setObjectName("lineEditYLabel")

        self.widgetYLimLabel = QWidget(parent=self)
        y_lim_label_layout = QHBoxLayout()
        self.widgetYLimLabel.setLayout(y_lim_label_layout)

        y_lim_label = QLabel(parent=self)
        y_lim_label.setText("Y Limits")

        self.toolButtonYAxisReset = CustomToolButton(
            text="Reset",
            light_icon_unchecked="icon-reset-64.svg",
            dark_icon_unchecked="icon-reset-dark-64.svg",
            parent=self)
        self.toolButtonYAxisReset.setObjectName("toolButtonYAxisReset")
        self.toolButtonYAxisReset.setFixedSize(QSize(20,20))
        self.toolButtonYAxisReset.setIconSize(QSize(14, 14))

        y_lim_label_layout.addWidget(y_lim_label)
        y_lim_label_layout.setContentsMargins(0, 0, 0, 0)
        y_lim_label_layout.addWidget(self.toolButtonYAxisReset)

        self.widgetYLim = QWidget(parent=self)
        y_lim_layout = QHBoxLayout()
        self.widgetYLim.setLayout(y_lim_layout)

        self.lineEditYLB = CustomLineEdit(parent=self)
        self.lineEditYLB.setObjectName("lineEditYLB")

        self.lineEditYUB = CustomLineEdit(parent=self)
        self.lineEditYUB.setObjectName("lineEditYUB")

        y_lim_layout.addWidget(self.lineEditYLB)
        y_lim_layout.setContentsMargins(0, 0, 0, 0)
        y_lim_layout.addWidget(self.lineEditYUB)

        self.comboBoxYScale = QComboBox(parent=self)
        self.comboBoxYScale.setObjectName("comboBoxYScale")

        line_y = QFrame(parent=self)
        line_y.setFrameShape(QFrame.Shape.HLine)
        line_y.setFrameShadow(QFrame.Shadow.Sunken)

        form_layout.addRow("Y Label", self.lineEditYLabel)
        form_layout.addRow(self.widgetYLimLabel, self.widgetYLim)
        form_layout.addRow("Y Scale", self.comboBoxYScale)
        form_layout.addRow("", line_y)


        self.lineEditZLabel = QLineEdit(parent=self)
        self.lineEditZLabel.setObjectName("lineEditZLabel")

        self.widgetZLimLabel = QWidget(parent=self)
        z_lim_label_layout = QHBoxLayout()
        self.widgetZLimLabel.setLayout(z_lim_label_layout)

        z_lim_label = QLabel(parent=self)
        z_lim_label.setText("Z Limits")

        self.toolButtonZAxisReset = CustomToolButton(
            text="Reset",
            light_icon_unchecked="icon-reset-64.svg",
            dark_icon_unchecked="icon-reset-dark-64.svg",
            parent=self)
        self.toolButtonZAxisReset.setObjectName("toolButtonZAxisReset")
        self.toolButtonZAxisReset.setFixedSize(QSize(20,20))
        self.toolButtonZAxisReset.setIconSize(QSize(14, 14))

        z_lim_label_layout.addWidget(z_lim_label)
        z_lim_label_layout.setContentsMargins(0, 0, 0, 0)
        z_lim_label_layout.addWidget(self.toolButtonZAxisReset)

        self.widgetZLim = QWidget(parent=self)
        z_lim_layout = QHBoxLayout()
        z_lim_layout.setContentsMargins(0, 0, 0, 0)
        self.widgetZLim.setLayout(z_lim_layout)

        self.lineEditZLB = CustomLineEdit(parent=self)
        self.lineEditZLB.setObjectName("lineEditZLB")

        self.lineEditZUB = CustomLineEdit(parent=self)
        self.lineEditZUB.setObjectName("lineEditZUB")

        z_lim_layout.addWidget(self.lineEditZLB)
        z_lim_layout.addWidget(self.lineEditZUB)

        self.comboBoxZScale = QComboBox(parent=self)
        self.comboBoxZScale.setObjectName("comboBoxZScale")

        line_z = QFrame(parent=self)
        line_z.setFrameShape(QFrame.Shape.HLine)
        line_z.setFrameShadow(QFrame.Shadow.Sunken)

        form_layout.addRow("Z Label", self.lineEditZLabel)
        form_layout.addRow(self.widgetZLimLabel, self.widgetZLim)
        form_layout.addRow("Z Scale", self.comboBoxZScale)
        form_layout.addRow("", line_z)

        self.lineEditAspectRatio = CustomLineEdit(parent=self)
        self.lineEditAspectRatio.setObjectName("lineEditAspectRatio")

        self.comboBoxTickDirection = QComboBox(parent=self)
        self.comboBoxTickDirection.setObjectName("comboBoxTickDirection")

        form_layout.addRow("Aspect ratio", self.lineEditAspectRatio)
        form_layout.addRow("Tick direction", self.comboBoxTickDirection)

        scatter_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.addLayout(form_layout)
        self.addItem(scatter_spacer)

        # add the page to the toolbox
        light_icon = ICONPATH / "icon-axes-64.svg"
        page_name = "Axes"
        parent.toolbox.addItem(self, QIcon(str(light_icon)),  page_name)

        parent.toolbox.set_page_icons(
            page_name,
            light_icon = light_icon,
            dark_icon = ICONPATH / "icon-axes-dark-64.svg"
        ) 

class AnnotationsPage(CustomPage):
    def __init__(self, parent=None):
        super().__init__(obj_name="StyleAnnotations", parent=parent)

        self.setupUI(parent)

    def setupUI(self, parent):
        self.setGeometry(QRect(0, 0, 295, 807))

        form_layout = QFormLayout()
        form_layout.setObjectName("formLayoutStyleMaps")

        self.comboBoxScaleDirection = QComboBox(parent=self)
        self.comboBoxScaleDirection.setObjectName("comboBoxScaleDirection")

        self.comboBoxScaleLocation = QComboBox(parent=self)
        self.comboBoxScaleLocation.setObjectName("comboBoxScaleLocation")

        self.colorButtonOverlayColor = ColorButton(
            ui=self.parent,
            parent=self
        )
        self.colorButtonOverlayColor.setObjectName("colorButtonOverlayColor")

        self.lineEditScaleLength = CustomLineEdit(parent=self)
        self.lineEditScaleLength.setObjectName("lineEditScaleLength")

        form_layout.addRow("Scale direction", self.comboBoxScaleDirection)
        form_layout.addRow("Scale location", self.comboBoxScaleLocation)
        form_layout.addRow("Scale length", self.lineEditScaleLength)
        form_layout.addRow("Overlay color", self.colorButtonOverlayColor)

        line = QFrame(parent=self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        form_layout.addRow("", line)

        self.fontComboBox = QFontComboBox(parent=self)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fontComboBox.sizePolicy().hasHeightForWidth())
        self.fontComboBox.setSizePolicy(sizePolicy)
        #self.fontComboBox.setMinimumSize(QSize(100, 0))
        #self.fontComboBox.setMaximumSize(QSize(200, 16777215))
        self.fontComboBox.setObjectName("fontComboBox")

        self.doubleSpinBoxFontSize = QDoubleSpinBox(parent=self)
        self.doubleSpinBoxFontSize.setDecimals(1)
        self.doubleSpinBoxFontSize.setMinimum(6.0)
        self.doubleSpinBoxFontSize.setMaximum(24.0)
        self.doubleSpinBoxFontSize.setSingleStep(0.5)
        self.doubleSpinBoxFontSize.setValue(11.0)
        self.doubleSpinBoxFontSize.setObjectName("doubleSpinBoxFontSize")

        self.checkBoxShowMass = QCheckBox(parent=self)
        self.checkBoxShowMass.setObjectName("checkBoxShowMass")
        self.checkBoxShowMass.setChecked(True)

        form_layout.addRow("Font family", self.fontComboBox)
        form_layout.addRow("Font size", self.doubleSpinBoxFontSize)
        form_layout.addRow("Show mass", self.checkBoxShowMass)

        self.addLayout(form_layout)

        scatter_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.addItem(scatter_spacer)

        # add the page to the toolbox
        light_icon = ICONPATH / "icon-text-and-scales-64.svg"
        page_name = "Text and Scales"
        parent.toolbox.addItem(self, QIcon(str(light_icon)),  page_name)

        parent.toolbox.set_page_icons(
            page_name,
            light_icon = light_icon,
            dark_icon = ICONPATH / "icon-text-and-scales-dark-64.svg"
        ) 

class MarkersPage(CustomPage):
    def __init__(self, parent=None):
        super().__init__(obj_name="StyleMarkers", parent=parent)

        self.setupUI(parent)

    def setupUI(self, parent):
        self.setGeometry(QRect(0, 0, 244, 807))

        form_layout = QFormLayout()
        form_layout.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        form_layout.setObjectName("formLayoutMarkers")

        self.comboBoxMarker = QComboBox(parent=self)
        self.comboBoxMarker.setMaximumSize(QSize(125, 16777215))
        self.comboBoxMarker.setObjectName("comboBoxMarker")

        self.doubleSpinBoxMarkerSize = QDoubleSpinBox(parent=self)
        self.doubleSpinBoxMarkerSize.setMaximumSize(QSize(125, 16777215))
        self.doubleSpinBoxMarkerSize.setKeyboardTracking(False)
        self.doubleSpinBoxMarkerSize.setMinimum(1.0)
        self.doubleSpinBoxMarkerSize.setMaximum(64.0)
        self.doubleSpinBoxMarkerSize.setSingleStep(1.0)
        self.doubleSpinBoxMarkerSize.setProperty("value", 6.0)
        self.doubleSpinBoxMarkerSize.setObjectName("doubleSpinBoxMarkerSize")

        self.colorButtonMarkerColor = ColorButton(
            ui=self.parent,
            parent=self
        )
        self.colorButtonMarkerColor.setObjectName("colorButtonMarkerColor")

        self.sliderTransparency = CustomSlider(
            initial_value = 100,
            parent=self,
        )
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        self.sliderTransparency.setObjectName("sliderTransparency")

        form_layout.addRow("Marker", self.comboBoxMarker)
        form_layout.addRow("Marker size", self.doubleSpinBoxMarkerSize)
        form_layout.addRow("Marker color", self.colorButtonMarkerColor)
        form_layout.addRow("Transparency", self.sliderTransparency)

        line = QFrame(parent=self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        form_layout.addRow("", line)

        self.doubleSpinBoxLineWidth = QDoubleSpinBox(parent=self)
        self.doubleSpinBoxLineWidth.setMaximum(10.0)
        self.doubleSpinBoxLineWidth.setSingleStep(0.5)
        self.doubleSpinBoxLineWidth.setObjectName("doubleSpinBoxLineWidth")

        self.colorButtonLineColor = ColorButton(
            ui=self.parent,
            parent=self
        )
        self.colorButtonLineColor.setObjectName("colorButtonLineColor")
        self.lineEditLengthMultiplier = CustomLineEdit(parent=self)
        self.lineEditLengthMultiplier.setMinimumSize(QSize(30, 0))
        self.lineEditLengthMultiplier.setMaximumSize(QSize(75, 16777215))
        self.lineEditLengthMultiplier.setObjectName("lineEditLengthMultiplier")

        form_layout.addRow("Line width", self.doubleSpinBoxLineWidth)
        form_layout.addRow("Line color", self.colorButtonLineColor)
        form_layout.addRow("Line multiplier", self.lineEditLengthMultiplier)

        self.addLayout(form_layout)

        scatter_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.addItem(scatter_spacer)

        # add the page to the toolbox
        light_icon = ICONPATH / "icon-marker-and-lines-64.svg"
        page_name = "Markers and Lines"
        parent.toolbox.addItem(self, QIcon(str(light_icon)),  page_name)

        parent.toolbox.set_page_icons(
            page_name,
            light_icon = light_icon,
            dark_icon = ICONPATH / "icon-marker-and-lines-dark-64.svg"
        )

class ColorsPage(CustomPage):
    def __init__(self, parent=None):
        super().__init__(obj_name="StyleColors", parent=parent)

        self.setupUI(parent)

    def setupUI(self, parent):
        self.setGeometry(QRect(0, 0, 326, 807))

        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.lineEditCLabel = QLineEdit(parent=self)
        self.lineEditCLabel.setObjectName("lineEditCLabel")

        self.widgetCLimLabel = QWidget(parent=self)
        c_lim_label_layout = QHBoxLayout()
        c_lim_label_layout.setContentsMargins(0, 0, 0, 0)
        self.widgetCLimLabel.setLayout(c_lim_label_layout)

        c_lim_label = QLabel(parent=self)
        c_lim_label.setText("C Limits")

        self.toolButtonCAxisReset = CustomToolButton(
            text="Reset",
            light_icon_unchecked="icon-reset-64.svg",
            dark_icon_unchecked="icon-reset-dark-64.svg",
            parent=self)
        self.toolButtonCAxisReset.setObjectName("toolButtonCAxisReset")

        c_lim_label_layout.addWidget(c_lim_label)
        c_lim_label_layout.addWidget(self.toolButtonCAxisReset)

        self.widgetCLim = QWidget(parent=self)
        c_lim_layout = QHBoxLayout()
        c_lim_layout.setContentsMargins(0, 0, 0, 0)
        self.widgetCLim.setLayout(c_lim_layout)

        self.lineEditCLB = CustomLineEdit(parent=self)
        self.lineEditCLB.setObjectName("lineEditCLB")

        self.lineEditCUB = CustomLineEdit(parent=self)
        self.lineEditCUB.setObjectName("lineEditCUB")

        c_lim_layout.addWidget(self.lineEditCLB)
        c_lim_layout.addWidget(self.lineEditCUB)

        self.comboBoxCScale = QComboBox(parent=self)
        self.comboBoxCScale.setObjectName("comboBoxCScale")

        line_c = QFrame(parent=self)
        line_c.setFrameShape(QFrame.Shape.HLine)
        line_c.setFrameShadow(QFrame.Shadow.Sunken)

        form_layout.addRow("C Label", self.lineEditCLabel)
        form_layout.addRow(self.widgetCLimLabel, self.widgetCLim)
        form_layout.addRow("C Scale", self.comboBoxCScale)
        form_layout.addRow("", line_c)

        self.comboBoxFieldColormap = CustomComboBox(parent=self)
        self.comboBoxFieldColormap.setMaximumSize(QSize(155, 16777215))
        self.comboBoxFieldColormap.setObjectName("comboBoxFieldColormap")
        form_layout.addRow("Colormap", self.comboBoxFieldColormap)

        self.comboBoxCbarDirection = QComboBox(parent=self)
        self.comboBoxCbarDirection.setMaximumSize(QSize(16777215, 16777215))
        self.comboBoxCbarDirection.setObjectName("comboBoxCbarDirection")
        form_layout.addRow("Cbar direction", self.comboBoxCbarDirection)

        self.checkBoxReverseColormap = QCheckBox(parent=self)
        self.checkBoxReverseColormap.setText("")
        self.checkBoxReverseColormap.setObjectName("checkBoxReverseColormap")
        form_layout.addRow("Reverse", self.checkBoxReverseColormap)

        line_m = QFrame(parent=self)
        line_m.setFrameShape(QFrame.Shape.HLine)
        line_m.setFrameShadow(QFrame.Shadow.Sunken)
        form_layout.addRow("", line_m)

        self.spinBoxHeatmapResolution = QSpinBox(parent=self)
        self.spinBoxHeatmapResolution.setEnabled(True)
        self.spinBoxHeatmapResolution.setMinimum(1)
        self.spinBoxHeatmapResolution.setMaximum(100)
        self.spinBoxHeatmapResolution.setValue(10)
        self.spinBoxHeatmapResolution.setObjectName("spinBoxHeatmapResolution")
        form_layout.addRow("Resolution", self.spinBoxHeatmapResolution)

        self.addLayout(form_layout)

        scatter_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.addItem(scatter_spacer)

        # add the page to the toolbox
        light_icon = ICONPATH / "icon-rgb-64.svg"
        page_name = "Colors"
        parent.toolbox.addItem(self, QIcon(str(light_icon)),  page_name)

        parent.toolbox.set_page_icons(
            page_name,
            light_icon = light_icon,
            dark_icon = ICONPATH / "icon-rgb-dark-64.svg"
        )

@auto_log_methods(logger_key='Style')
class StylingDock(CustomDockWidget):
    def __init__(self, ui: "MainWindow"):
        if not isinstance(ui, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")
        super().__init__(parent=ui)
        self.logger_key = 'Style'
        self.ui = ui

        # create UI for StylingDock
        self.setWindowTitle("Styling Toolbox")
        self.setupUI()
        self.reindex_tab_dict()

        self.axis_widget_dict = {
            'x': {
                'scalebox': self.axes.comboBoxXScale,
                'axis_label': self.axes.lineEditXLabel,
                'lbound': self.axes.lineEditXLB,
                'ubound': self.axes.lineEditXUB,
                'reset_btn': self.axes.toolButtonXAxisReset,
            },
            'y': {'scalebox': self.axes.comboBoxYScale,
                'axis_label': self.axes.lineEditYLabel,
                'lbound': self.axes.lineEditYLB,
                'ubound': self.axes.lineEditYUB,
                'reset_btn': self.axes.toolButtonYAxisReset,
            },
            'z': {
                'scalebox': self.axes.comboBoxZScale,
                'axis_label': self.axes.lineEditZLabel,
                'lbound': self.axes.lineEditZLB,
                'ubound': self.axes.lineEditZUB,
                'reset_btn': self.axes.toolButtonZAxisReset,
            },
            'c': {'scalebox': self.caxes.comboBoxCScale,
                'axis_label': self.caxes.lineEditCLabel,
                'lbound': self.caxes.lineEditCLB,
                'ubound': self.caxes.lineEditCUB,
                'reset_btn': self.caxes.toolButtonCAxisReset,
            },
        }

        # toggles signals from widgets, if false, blocks widgets from sending signals
        self._signal_state = True

        # initial plot type
        self._plot_type = "field map"

        # initialize style themes and associated widgets
        self.comboBoxStyleTheme.clear()
        self.comboBoxStyleTheme.addItems(self.ui.style_data.load_theme_names())
        self.comboBoxStyleTheme.setCurrentIndex(0)
        
        self.comboBoxStyleTheme.activated.connect(lambda: setattr(self, "style_dict", self.ui.style_data.read_theme(self.comboBoxStyleTheme.currentText())))
        self.toolButtonSaveTheme.clicked.connect(self.save_style_theme)

        self.ui.control_dock.comboBoxFieldX.currentTextChanged.connect(lambda text: self.axis_variable_changed(text, 'x'))
        self.ui.control_dock.comboBoxFieldY.currentTextChanged.connect(lambda text: self.axis_variable_changed(text, 'y'))
        self.ui.control_dock.comboBoxFieldZ.currentTextChanged.connect(lambda text: self.axis_variable_changed(text, 'z'))
        self.ui.control_dock.comboBoxFieldC.currentTextChanged.connect(lambda text: self.axis_variable_changed(text, 'c'))

        self.connect_widgets()
        self.connect_observer()
        self.connect_logger()

        self._signal_state = False

        self.set_style_widgets()

    def setupUI(self):
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable|QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea|Qt.DockWidgetArea.RightDockWidgetArea)
        self.setObjectName("dockWidgetStyling")

        dock_contents = QWidget()
        dock_layout = QVBoxLayout(dock_contents)
        dock_layout.setContentsMargins(3, 3, 3, 3)

        # Style theme selection
        theme_layout = QHBoxLayout()

        theme_label = QLabel(parent=dock_contents)
        theme_label.setText("Theme")

        self.comboBoxStyleTheme = QComboBox(parent=dock_contents)
        self.comboBoxStyleTheme.setObjectName("comboBoxStyleTheme")

        self.toolButtonSaveTheme = CustomToolButton(
            text="Save\nTheme",
            light_icon_unchecked="icon-save-file-64.svg",
            parent=dock_contents,
        )
        self.toolButtonSaveTheme.setObjectName("toolButtonSaveTheme")
        self.toolButtonSaveTheme.setToolTip("Save plot theme")

        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.comboBoxStyleTheme)
        theme_layout.addWidget(self.toolButtonSaveTheme)
        

        dock_layout.addLayout(theme_layout)

        # Style toolbox
        self.toolbox = CustomToolBox(parent=dock_contents)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.toolbox.sizePolicy().hasHeightForWidth())
        self.toolbox.setSizePolicy(sizePolicy)
        self.toolbox.setObjectName("toolBoxStyle")

        # Axes page
        self.axes = AxesPage(self)
        # Annotations and Scale Page
        self.annotations = AnnotationsPage(self)
        # Markers and Lines Page
        self.elements = MarkersPage(self)
        # Colors Page
        self.caxes = ColorsPage(self)

        dock_layout.addWidget(self.toolbox)
        self.setWidget(dock_contents)

    def reindex_tab_dict(self):
        self.tab_dict = {}
        for tid in range(self.toolbox.count()):
            match self.toolbox.itemText(tid).lower():
                case 'axes and labels':
                    self.tab_dict.update({'axes': tid})
                case 'annotations and scale':
                    self.tab_dict.update({'text': tid})
                case 'markers and lines':
                    self.tab_dict.update({'markers': tid})
                case 'coloring':
                    self.tab_dict.update({'colors': tid})
                case 'regression':
                    self.tab_dict.update({'regression': tid})

    def connect_widgets(self):
        # axes
        # ---
        self.axes.lineEditXLabel.editingFinished.connect(lambda _: self.update_axis_label('x'))
        self.axes.lineEditYLabel.editingFinished.connect(lambda _: self.update_axis_label('y'))
        self.axes.lineEditZLabel.editingFinished.connect(lambda _: self.update_axis_label('z'))
        self.caxes.lineEditCLabel.editingFinished.connect(lambda _: self.update_axis_label('c'))

        self.axes.comboBoxXScale.activated.connect(lambda _: self.update_axis_scale('x'))
        self.axes.comboBoxYScale.activated.connect(lambda _: self.update_axis_scale('y'))
        self.axes.comboBoxZScale.activated.connect(lambda _: self.update_axis_scale('y'))
        self.caxes.comboBoxCScale.activated.connect(lambda _: self.update_axis_scale('c'))

        self.axes.lineEditXLB.setValidator(QDoubleValidator())
        self.axes.lineEditXLB.precision = 3
        self.axes.lineEditXLB.toward = 0
        self.axes.lineEditXUB.setValidator(QDoubleValidator())
        self.axes.lineEditXUB.precision = 3
        self.axes.lineEditXUB.toward = 1
        self.axes.lineEditYLB.setValidator(QDoubleValidator())
        self.axes.lineEditYLB.precision = 3
        self.axes.lineEditYLB.toward = 0
        self.axes.lineEditYUB.setValidator(QDoubleValidator())
        self.axes.lineEditYUB.precision = 3
        self.axes.lineEditYUB.toward = 1
        self.axes.lineEditZLB.setValidator(QDoubleValidator())
        self.axes.lineEditZLB.precision = 3
        self.axes.lineEditZLB.toward = 0
        self.axes.lineEditZUB.setValidator(QDoubleValidator())
        self.axes.lineEditZUB.precision = 3
        self.axes.lineEditZUB.toward = 1
        self.caxes.lineEditCLB.setValidator(QDoubleValidator())
        self.caxes.lineEditCLB.precision = 3
        self.caxes.lineEditCLB.toward = 0
        self.caxes.lineEditCUB.setValidator(QDoubleValidator())
        self.caxes.lineEditCUB.precision = 3
        self.caxes.lineEditCUB.toward = 1
        self.axes.lineEditAspectRatio.setValidator(QDoubleValidator())
        self.axes.lineEditAspectRatio.precision = 3
        self.axes.lineEditAspectRatio.toward = 1
        self.axes.lineEditAspectRatio.set_bounds(0.0,None)

        self.axes.lineEditXLB.editingFinished.connect(lambda _: self.update_axis_limits('x'))
        self.axes.lineEditXUB.editingFinished.connect(lambda _: self.update_axis_limits('x'))
        self.axes.lineEditYLB.editingFinished.connect(lambda _: self.update_axis_limits('y'))
        self.axes.lineEditYUB.editingFinished.connect(lambda _: self.update_axis_limits('y'))
        self.axes.lineEditZLB.editingFinished.connect(lambda _: self.update_axis_limits('z'))
        self.axes.lineEditZUB.editingFinished.connect(lambda _: self.update_axis_limits('z'))
        self.caxes.lineEditCLB.editingFinished.connect(lambda _: self.update_axis_limits('c'))
        self.caxes.lineEditCUB.editingFinished.connect(lambda _: self.update_axis_limits('c'))

        self.axes.toolButtonXAxisReset.clicked.connect(lambda: self.axis_reset_callback('x'))
        self.axes.toolButtonYAxisReset.clicked.connect(lambda: self.axis_reset_callback('y'))
        self.axes.toolButtonZAxisReset.clicked.connect(lambda: self.axis_reset_callback('z'))
        self.caxes.toolButtonCAxisReset.clicked.connect(lambda: self.axis_reset_callback('c'))

        self.axes.lineEditAspectRatio.editingFinished.connect(lambda _:self.update_aspect_ratio)
        self.axes.comboBoxTickDirection.activated.connect(lambda _: self.update_tick_dir())
        self.axes.comboBoxTickDirection.clear()
        self.axes.comboBoxTickDirection.addItems(self.ui.style_data.tick_dir_options)

        # annotations and scales
        # ---
        self.annotations.lineEditScaleLength.setValidator(QDoubleValidator())
        self.annotations.lineEditScaleLength.precision = 3
        self.annotations.lineEditScaleLength.toward = 1
        self.annotations.lineEditScaleLength.set_bounds(0.0,None)

        self.elements.lineEditLengthMultiplier.setValidator(QDoubleValidator())
        self.elements.lineEditLengthMultiplier.precision = 3
        self.elements.lineEditLengthMultiplier.toward = 1
        self.elements.lineEditLengthMultiplier.set_bounds(0.0,100)

        #overlay color
        self.annotations.comboBoxScaleDirection.activated.connect(lambda _: self.update_scale_direction())
        self.annotations.comboBoxScaleLocation.activated.connect(lambda _: self.update_scale_location())
        self.annotations.lineEditScaleLength.setValidator(QDoubleValidator())
        self.annotations.lineEditScaleLength.editingFinished.connect(lambda _: self.update_scale_length())

        #self.annotations.fontComboBox.setCurrentFont(QFont(self.ui.style_data.style_dict['Font'], 11))
        self.annotations.fontComboBox.activated.connect(lambda _: self.update_font_family())
        self.annotations.doubleSpinBoxFontSize.valueChanged.connect(lambda _: self.update_font_size())

        # overlay and annotation properties
        self.annotations.checkBoxShowMass.stateChanged.connect(lambda _: self.update_show_mass())
        self.annotations.colorButtonOverlayColor.clicked.connect(lambda _: self.update_overlay_color())
        self.annotations.colorButtonOverlayColor.setStyleSheet("background-color: white;")

        # add list of colormaps to comboBoxFieldColormap and set callbacks
        self.caxes.comboBoxFieldColormap.clear()
        self.caxes.comboBoxFieldColormap.addItems(list(self.ui.style_data.custom_color_dict.keys())+self.ui.style_data.mpl_colormaps)
        self.caxes.comboBoxFieldColormap.activated.connect(lambda _: self.update_field_colormap())
        self.caxes.checkBoxReverseColormap.stateChanged.connect(lambda _: self.update_cbar_direction())


        # markers and lines
        # ---
        self.elements.comboBoxMarker.clear()
        self.elements.comboBoxMarker.addItems(self.ui.style_data.marker_dict.keys())
        self.elements.comboBoxMarker.setCurrentIndex(0)
        self.elements.comboBoxMarker.activated.connect(lambda _: self.update_marker_symbol())
        self.elements.doubleSpinBoxMarkerSize.valueChanged.connect(lambda _: self.update_marker_size())
        self.elements.sliderTransparency.sliderReleased.connect(lambda: self.update_marker_transparency())
        self.elements.colorButtonMarkerColor.setStyleSheet("background-color: white;")
        self.elements.colorButtonMarkerColor.clicked.connect(lambda _: self.update_marker_color())

        self.elements.doubleSpinBoxLineWidth.valueChanged.connect(lambda _: self.update_line_width())
        self.elements.lineEditLengthMultiplier.editingFinished.connect(lambda _: self.update_length_multiplier())
        self.elements.colorButtonLineColor.setStyleSheet("background-color: white;")
        self.elements.colorButtonLineColor.clicked.connect(lambda _: self.update_line_color())
        # marker color

        # colors
        self.caxes.comboBoxFieldColormap.activated.connect(lambda _: self.update_field_colormap())
        self.caxes.comboBoxCbarDirection.clear()
        self.caxes.comboBoxCbarDirection.addItems(self.ui.style_data.cbar_dir_options)
        self.caxes.comboBoxCbarDirection.activated.connect(lambda _: self.update_cbar_direction())
        # resolution
        self.caxes.spinBoxHeatmapResolution.valueChanged.connect(lambda _: self.update_resolution())

        # ternary colormaps
        # ---
        self._ternary_colormap = ""
        self._ternary_color_x = ""
        self._ternary_color_y = ""
        self._ternary_color_z = ""
        self._ternary_color_m = ""
        
    def connect_observer(self):
        """Connects properties to observer functions."""
        self.ui.style_data.plotTypeChanged.connect(lambda new_plot_type: self.update_plot_type(new_plot_type))

        # these are commented out because they should now be handled by updates
        # to plot data from the control dock, which should force updates
        self.ui.style_data.axisLimChanged.connect(lambda ax, new_lim: self.update_axis_limits(ax, new_lim))
        self.ui.style_data.axisLabelChanged.connect(lambda ax, new_text: self.update_axis_label(ax, new_text))
        self.ui.style_data.axisScaleChanged.connect(lambda ax, new_text: self.update_axis_scale(ax, new_text))
        self.ui.style_data.aspectRatioChanged.connect(lambda value: self.update_aspect_ratio(value))
        self.ui.style_data.tickDirChanged.connect(lambda direction: self.update_tick_dir(direction))
        self.ui.style_data.fontFamilyChanged.connect(lambda new_font: self.update_font_family(new_font))
        self.ui.style_data.fontSizeChanged.connect(lambda value: self.update_font_size(value))
        self.ui.style_data.scaleDirChanged.connect(lambda direction: self.update_scale_direction(direction))
        self.ui.style_data.scaleLocationChanged.connect(lambda location: self.update_scale_location(location))
        self.ui.style_data.scaleLengthChanged.connect(lambda value: self.update_scale_length(value))
        self.ui.style_data.overlayColorChanged.connect(lambda new_color: self.update_overlay_color(new_color))
        self.ui.style_data.showMassChanged.connect(lambda state: self.update_show_mass(state))
        self.ui.style_data.markerChanged.connect(lambda new_text: self.update_marker_symbol(new_text))
        self.ui.style_data.markerSizeChanged.connect(lambda value: self.update_marker_size(value))
        self.ui.style_data.markerColorChanged.connect(lambda new_color: self.update_marker_color(new_color))
        self.ui.style_data.markerAlphaChanged.connect(lambda value: self.update_marker_transparency(value))
        self.ui.style_data.lineWidthChanged.connect(lambda value: self.update_line_width(value))
        self.ui.style_data.lengthMultiplierChanged.connect(lambda value: self.update_length_multiplier(value))
        self.ui.style_data.lineColorChanged.connect(lambda new_color: self.update_line_color(new_color))
        self.ui.style_data.colormapChanged.connect(lambda cmap: self.update_field_colormap(cmap))
        self.ui.style_data.cbarReverseChanged.connect(lambda state: self.update_cbar_reverse(state))
        self.ui.style_data.cbarDirChanged.connect(lambda direction: self.update_cbar_direction(direction))
        self.ui.style_data.heatmapResolutionChanged.connect(lambda value: self.update_resolution(value))

    def connect_logger(self):
        """Connects widgets to logger."""
        self.comboBoxStyleTheme.activated.connect(lambda: log(f"comboBoxStyleTheme value=[{self.comboBoxStyleTheme.currentText()}]", prefix="UI"))
        self.toolButtonSaveTheme.clicked.connect(lambda: log("toolButtonTheme", prefix="UI"))

        # axes and labels
        self.axes.lineEditXLabel.editingFinished.connect(lambda: log(f"lineEditXLabel value=[{self.axes.lineEditXLabel.text()}]", prefix="UI"))
        self.axes.lineEditXLB.editingFinished.connect(lambda: log(f"lineEditXLB value=[{self.axes.lineEditXLB.value}]", prefix="UI"))
        self.axes.lineEditXUB.editingFinished.connect(lambda: log(f"lineEditXUB value=[{self.axes.lineEditXUB.value}]", prefix="UI"))
        self.axes.toolButtonXAxisReset.clicked.connect(lambda: log("toolButtonXAxisReset", prefix="UI"))
        self.axes.comboBoxXScale.activated.connect(lambda: log(f"comboBoxXScale value=[{self.axes.comboBoxXScale.currentText()}]", prefix="UI"))
        self.axes.lineEditYLabel.editingFinished.connect(lambda: log(f"lineEditYLabel value=[{self.axes.lineEditYLabel.text()}]", prefix="UI"))
        self.axes.lineEditYLB.editingFinished.connect(lambda: log(f"lineEditYLB value=[{self.axes.lineEditYLB.value}]", prefix="UI"))
        self.axes.lineEditYUB.editingFinished.connect(lambda: log(f"lineEditYUB value=[{self.axes.lineEditYUB.value}]", prefix="UI"))
        self.axes.toolButtonYAxisReset.clicked.connect(lambda: log("toolButtonYAxisReset", prefix="UI"))
        self.axes.comboBoxYScale.activated.connect(lambda: log(f"comboBoxYScale value=[{self.axes.comboBoxYScale.currentText()}]", prefix="UI"))
        self.axes.lineEditZLabel.editingFinished.connect(lambda: log(f"lineEditZLabel value=[{self.axes.lineEditZLabel.text()}]", prefix="UI"))
        self.axes.lineEditZLB.editingFinished.connect(lambda: log(f"lineEditZLB value=[{self.axes.lineEditZLB.value}]", prefix="UI"))
        self.axes.lineEditZUB.editingFinished.connect(lambda: log(f"lineEditZUB value=[{self.axes.lineEditZUB.value}]", prefix="UI"))
        self.axes.toolButtonZAxisReset.clicked.connect(lambda: log("toolButtonZAxisReset", prefix="UI"))
        self.axes.comboBoxZScale.activated.connect(lambda: log(f"comboBoxZScale value=[{self.axes.comboBoxZScale.currentText()}]", prefix="UI"))
        self.axes.lineEditAspectRatio.editingFinished.connect(lambda: log(f"lineEditAspectRatio value=[{self.axes.lineEditAspectRatio.text()}]", prefix="UI"))
        self.axes.comboBoxTickDirection.activated.connect(lambda: log(f"comboBoxTickDirection value=[{self.axes.comboBoxTickDirection.currentText()}]", prefix="UI"))

        # annotations and scale
        self.annotations.comboBoxScaleDirection.activated.connect(lambda: log(f"comboBoxScaleDirection value=[{self.annotations.comboBoxScaleDirection.currentText()}]", prefix="UI"))
        self.annotations.comboBoxScaleLocation.activated.connect(lambda: log(f"comboBoxScaleLocation value=[{self.annotations.comboBoxScaleLocation.currentText()}]", prefix="UI"))
        self.annotations.lineEditScaleLength.editingFinished.connect(lambda: log(f"lineEditScaleLength value=[{self.annotations.lineEditScaleLength.value}]", prefix="UI"))
        self.annotations.colorButtonOverlayColor.clicked.connect(lambda: log("colorButtonOverlayColor", prefix="UI"))
        self.annotations.fontComboBox.activated.connect(lambda: log(f"fontComboBox value=[{self.annotations.fontComboBox.currentText()}]", prefix="UI"))
        self.annotations.doubleSpinBoxFontSize.valueChanged.connect(lambda: log(f"doubleSpinBoxFontSize value=[{self.annotations.doubleSpinBoxFontSize.value()}]", prefix="UI"))
        self.annotations.checkBoxShowMass.checkStateChanged.connect(lambda: log(f"checkBoxShowMass value=[{self.annotations.checkBoxShowMass.isChecked()}]", prefix="UI"))

        # markers and lines
        self.elements.comboBoxMarker.activated.connect(lambda: log(f"comboBoxMarker value=[{self.elements.comboBoxMarker.currentText()}]", prefix="UI"))
        self.elements.doubleSpinBoxMarkerSize.valueChanged.connect(lambda: log(f"doubleSpinBoxMarkerSize value=[{self.elements.doubleSpinBoxMarkerSize.value()}]", prefix="UI"))
        self.elements.colorButtonMarkerColor.clicked.connect(lambda: log("colorButtonMarkerColor", prefix="UI"))
        self.elements.sliderTransparency.valueChanged.connect(lambda: log(f"sliderTransparency value=[{self.elements.sliderTransparency.value()}]", prefix="UI"))
        self.elements.doubleSpinBoxLineWidth.valueChanged.connect(lambda: log(f"doubleSpinBoxLineWidth value=[{self.elements.doubleSpinBoxLineWidth.value()}]", prefix="UI"))
        self.elements.colorButtonLineColor.clicked.connect(lambda: log("colorButtonLineColor", prefix="UI"))
        self.elements.lineEditLengthMultiplier.editingFinished.connect(lambda: log(f"lineEditLengthMultiplier value=[{self.elements.lineEditLengthMultiplier.value}]", prefix="UI"))

        # coloring
        self.caxes.lineEditCLabel.editingFinished.connect(lambda: log(f"lineEditCLabel value=[{self.caxes.lineEditCLabel.text()}]", prefix="UI"))
        self.caxes.lineEditCLB.editingFinished.connect(lambda: log(f"lineEditCLB value=[{self.caxes.lineEditCLB.value}]", prefix="UI"))
        self.caxes.lineEditCUB.editingFinished.connect(lambda: log(f"lineEditCUB value=[{self.caxes.lineEditCUB.value}]", prefix="UI"))
        self.caxes.toolButtonCAxisReset.clicked.connect(lambda: log("toolButtonCAxisReset", prefix="UI"))
        self.caxes.comboBoxCScale.activated.connect(lambda: log(f"comboBoxCScale value=[{self.caxes.comboBoxCScale.currentText()}]", prefix="UI"))
        self.caxes.comboBoxFieldColormap.activated.connect(lambda: log(f"comboBoxFieldColormap value=[{self.caxes.comboBoxFieldColormap.currentText()}]", prefix="UI"))
        self.caxes.comboBoxCbarDirection.activated.connect(lambda: log(f"comboBoxCbarDirection value=[{self.caxes.comboBoxCbarDirection.currentText()}]", prefix="UI"))
        self.caxes.checkBoxReverseColormap.checkStateChanged.connect(lambda: log(f"checkBoxReverseColormap value=[{self.caxes.checkBoxReverseColormap.isChecked()}]", prefix="UI"))
        self.caxes.spinBoxHeatmapResolution.valueChanged.connect(lambda: log(f"spinBoxHeatmapResolution value=[{self.caxes.spinBoxHeatmapResolution.value()}]", prefix="UI"))

    @property
    def signal_state(self):
        """
        Signal state for styling related widgets.
        
        When ``signal_state == False``, signals from widgets are blocked.
        """
        return self._signal_state
    
    @signal_state.setter
    def signal_state(self, state):
        if not isinstance(state, bool):
            raise TypeError("signal_state must be a bool")
        
        self._signal_state = state
        self.toggle_signals()

    def save_style_theme(self):
        """Saves a style dictionary to a theme.
        
        The theme is added to ``MainWindow.comboBoxStyleTheme`` and the style widget
        settings for each plot type (``MainWindow.styles``) are saved as a
        dictionary into the theme name with a ``.sty`` extension."""
        name = self.ui.style_data.input_theme_name_dlg(self.ui.style_data.style_dict)
        self.comboBoxStyleTheme.addItem(name)

    def toggle_signals(self):
        """Toggles signals from all style widgets.  Useful when updating many widgets."""        
        self.ui.control_dock.comboBoxPlotType.blockSignals(self._signal_state)

       # x-axis widgets
        self.axes.lineEditXLB.blockSignals(self._signal_state)
        self.axes.lineEditXUB.blockSignals(self._signal_state)
        self.axes.comboBoxXScale.blockSignals(self._signal_state)
        self.axes.lineEditXLabel.blockSignals(self._signal_state)

        # y-axis widgets
        self.axes.lineEditYLB.blockSignals(self._signal_state)
        self.axes.lineEditYUB.blockSignals(self._signal_state)
        self.axes.comboBoxYScale.blockSignals(self._signal_state)
        self.axes.lineEditYLabel.blockSignals(self._signal_state)

        # z-axis widgets
        self.axes.lineEditZLB.blockSignals(self._signal_state)
        self.axes.lineEditZUB.blockSignals(self._signal_state)
        self.axes.comboBoxZScale.blockSignals(self._signal_state)
        self.axes.lineEditZLabel.blockSignals(self._signal_state)

        # other axis properties
        self.axes.lineEditAspectRatio.blockSignals(self._signal_state)
        self.axes.comboBoxTickDirection.blockSignals(self._signal_state)

        # annotations
        self.annotations.fontComboBox.blockSignals(self._signal_state)
        self.annotations.doubleSpinBoxFontSize.blockSignals(self._signal_state)
        self.annotations.checkBoxShowMass.blockSignals(self._signal_state)

        # scale
        self.annotations.comboBoxScaleDirection.blockSignals(self._signal_state)
        self.annotations.comboBoxScaleLocation.blockSignals(self._signal_state)
        self.annotations.lineEditScaleLength.blockSignals(self._signal_state)
        self.annotations.colorButtonOverlayColor.blockSignals(self._signal_state)

        # markers and lines
        self.elements.comboBoxMarker.blockSignals(self._signal_state)
        self.elements.doubleSpinBoxMarkerSize.blockSignals(self._signal_state)
        self.elements.colorButtonMarkerColor.blockSignals(self._signal_state)
        self.elements.sliderTransparency.blockSignals(self._signal_state)
        self.elements.doubleSpinBoxLineWidth.blockSignals(self._signal_state)
        self.elements.colorButtonLineColor.blockSignals(self._signal_state)
        self.elements.lineEditLengthMultiplier.blockSignals(self._signal_state)

        # coloring
        self.ui.control_dock.comboBoxFieldTypeC.blockSignals(self._signal_state)
        self.ui.control_dock.comboBoxFieldC.blockSignals(self._signal_state)
        self.caxes.spinBoxHeatmapResolution.blockSignals(self._signal_state)
        self.caxes.comboBoxFieldColormap.blockSignals(self._signal_state)
        self.caxes.checkBoxReverseColormap.blockSignals(self._signal_state)
        self.caxes.lineEditCLB.blockSignals(self._signal_state)
        self.caxes.lineEditCUB.blockSignals(self._signal_state)
        self.caxes.comboBoxCScale.blockSignals(self._signal_state)
        self.caxes.lineEditCLabel.blockSignals(self._signal_state)
        self.caxes.comboBoxCbarDirection.blockSignals(self._signal_state)

    # ------------------------------------------------------------------
    # updates from plot type, field type and field
    # ------------------------------------------------------------------
    def update_plot_type(self, new_plot_type=None, force=False):
        """Updates styles when plot type is changed

        Executes on change of ``ControlDock.comboBoxPlotType``.  Updates ``PlotData.plot_type[0]`` to the current index of the 
        combobox, then updates the style widgets to match the dictionary entries and updates the plot.
        """
        # update all plot widgets
        self.ui.plot_flag = False
        self.set_style_widgets()
        self.ui.plot_flag = True

        if self.ui.style_data.plot_type != '':
            self.ui.schedule_update()

    # ------------------------------------------------------------------
    # Axes
    # ------------------------------------------------------------------
    def update_axis_limits(self, ax: str, new_lim: tuple|None=None):

        if ax == 'c':
            lower = getattr(self.caxes, f"lineEdit{ax.upper()}LB")
            upper = getattr(self.caxes, f"lineEdit{ax.upper()}UB")
        else:
            lower = getattr(self.axes, f"lineEdit{ax.upper()}LB")
            upper = getattr(self.axes, f"lineEdit{ax.upper()}UB")

        ui_lim = [lower.value, upper.value]

        if new_lim is None:
            self.ui.style_data.blockSignals(True)
            setattr(self, f"{ax}lim", ui_lim)
            self.ui.style_data.blockSignals(False)
        else:
            if list(new_lim) == ui_lim:
                return
            lower.blockSignals(True)
            upper.blockSignals(True)
            lower.value = new_lim[0]
            upper.value = new_lim[1]
            lower.blockSignals(False)
            lower.blockSignals(False)

        self.ui.schedule_update()

    def update_axis_label(self, ax: str, new_text: str|None=None):
        
        if ax == 'c':
            ui_label = getattr(self.caxes, f"lineEdit{ax.upper()}Label")
        else:
            ui_label = getattr(self.axes, f"lineEdit{ax.upper()}Label")

        if new_text is None:
            self.ui.style_data.blockSignals(True)
            setattr(self, f"{ax}label", ui_label.text())
            self.ui.style_data.blockSignals(False)
        else:
            if new_text == ui_label.text():
                return
            ui_label.blockSignals(True)
            ui_label.setText(new_text)
            ui_label.blockSignals(False)

        self.ui.schedule_update()

    def update_axis_scale(self, ax: str, new_text: str|None=None):
        """Update axis scale combobox and triggers plot update.

        If `new_text` is None, it uses the current value of the combobox to set `self.[ax]scale`.
        If `new_text` is provided, it updates the `ui.comboBox[ax]Scale` state accordingly.

        Parameters
        ----------
        ax : str
            Axis to update, `x`, `y`, `z`, or `c`
        new_text : str, optional
            New axis scale for combobox, by default None
        """
        if ax == 'c':
            scale_combo = getattr(self.caxes, f"comboBox{ax.upper()}Scale")
        else:
            scale_combo = getattr(self.axes, f"comboBox{ax.upper()}Scale")

        if  new_text is None:
            self.ui.style_data.blockSignals(True)
            setattr(self, f"{ax}_scale", scale_combo.currentText())
            self.ui.style_data.blockSignals(False)
        else:
            if new_text == scale_combo.currentText():
                return
            if new_text == 'discrete':
                scale_combo.clear()
                scale_combo.addItems(new_text)
                
            scale_combo.blockSignals(True)
            scale_combo.setCurrentText(new_text)
            scale_combo.blockSignals(False)

        self.ui.schedule_update()

    # ------------------------------------------------------------------
    # Aspect ratio & tick direction
    # ------------------------------------------------------------------
    def update_aspect_ratio(self, new_value=None):
        """
        Updates aspect ratio line edit and triggers plot update.

        If `new_value` is None, it uses the current value of the line edit to set `self.aspect_ratio`.
        If `new_value` is provided, it updates the `self.axes.lineEditAspectRation` state accordingly.

        Parameters
        ----------
        new_value : float, optional
            New value for the line edit, by default None
        """
        if new_value is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.aspect_ratio = self.axes.lineEditAspectRatio.value
            self.ui.style_data.blockSignals(False)
        else:
            if new_value == self.axes.lineEditAspectRatio.value:
                return

            self.axes.lineEditAspectRatio.blockSignals(True)
            self.axes.lineEditAspectRatio.value = new_value
            self.axes.lineEditAspectRatio.blockSignals(False)

        self.ui.schedule_update()

    def update_tick_dir(self, new_dir=None):
        """
        Updates tick direction combobox and triggers plot update.

        If `new_dir` is None, it uses the current text of the combobox to set `self.tick_dir`.
        If `new_dir` is provided, it updates the `ui.comboBoxTickDirection` state accordingly.

        Parameters
        ----------
        new_dir : float, optional
            New direction for the combobox, by default None
        """
        if new_dir is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.tick_dir = self.axes.comboBoxTickDirection.currentText()
            self.ui.style_data.blockSignals(False)
        else:
            if new_dir == self.axes.comboBoxTickDirection.currentText():
                return

            self.axes.comboBoxTickDirection.blockSignals(True)
            self.axes.comboBoxTickDirection.setCurrentText(new_dir)
            self.axes.comboBoxTickDirection.blockSignals(False)

        self.ui.schedule_update()

    # ------------------------------------------------------------------
    # Scale‑bar
    # ------------------------------------------------------------------
    def update_scale_direction(self, new_text=None):
        """
        Updates scale direction combobox and triggers plot update.

        If `new_text` is None, it uses the current text of the combobox to set `self.scale_dir`.
        If `new_text` is provided, it updates the `self.annotations.comboBoxScaleDirection` state accordingly.

        Parameters
        ----------
        new_text : float, optional
            New direction for the combobox, by default None
        """
        if new_text is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.scale_dir = self.annotations.comboBoxScaleDirection.currentText()
            self.ui.style_data.blockSignals(False)
        else:
            if new_text == self.annotations.comboBoxScaleDirection.currentText():
                return

            self.annotations.comboBoxScaleDirection.blockSignals(True)
            self.annotations.comboBoxScaleDirection.setCurrentText(new_text)
            self.annotations.comboBoxScaleDirection.blockSignals(False)

        self.ui.schedule_update()

    def update_scale_location(self, new_text=None):
        """
        Updates scale location combobox and triggers plot update.

        If `new_text` is None, it uses the current text of the combobox to set `self.scale_location`.
        If `new_text` is provided, it updates the `self.annotations.comboBoxScaleLocation` state accordingly.

        Parameters
        ----------
        new_text : float, optional
            New location for the combobox, by default None
        """
        if new_text is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.scale_location = self.annotations.comboBoxScaleLocation.currentText()
            self.ui.style_data.blockSignals(False)
        else:
            if new_text == self.annotations.comboBoxScaleLocation.currentText():
                return

            self.annotations.comboBoxScaleLocation.blockSignals(True)
            self.annotations.comboBoxScaleLocation.setCurrentText(new_text)
            self.annotations.comboBoxScaleLocation.blockSignals(False)
            self.toggle_scale_widgets()

        self.ui.schedule_update()

    def update_scale_length(self, new_value=None):
        """
        Updates scale length line edit and triggers plot update.

        If `new_value` is None, it uses the current text of the line edit to set `self.scale_location`.
        If `new_value` is provided, it updates the `self.annotations.comboBoxScaleLocation` state accordingly.

        Parameters
        ----------
        new_value : float, optional
            New location for the combobox, by default None
        """
        if not new_value:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.scale_length = self.annotations.lineEditScaleLength.value
            self.ui.style_data.blockSignals(False)
        else:
            if new_value == self.annotations.lineEditScaleLength.value:
                return

            self.annotations.lineEditScaleLength.blockSignals(True)
            self.annotations.lineEditScaleLength.value = new_value
            self.annotations.lineEditScaleLength.blockSignals(False)

        self.ui.schedule_update()

    def update_overlay_color(self, new_color=None):
        self.ui.style_data.overlay_color = new_color
        self.annotations.colorButtonOverlayColor.color = new_color
        self.ui.schedule_update()

    def update_show_mass(self, new_state=None):
        """
        Updates show mass checkbox and triggers plot update.

        If `new_state` is None, it uses the current state of the checkbox to set `self.checkBoxShowMass`.
        If `new_state` is provided, it updates the `annotations.checkBoxShowMass` state accordingly.

        Parameters
        ----------
        new_state : bool, optional
            New state for the checkbox, by default None
        """
        if new_state is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.show_mass = self.annotations.checkBoxShowMass.isChecked()
            self.ui.style_data.blockSignals(False)
        else:
            if new_state == self.annotations.checkBoxShowMass.isChecked():
                return

            self.annotations.checkBoxShowMass.blockSignals(True)
            self.annotations.checkBoxShowMass.setChecked(new_state)
            self.annotations.checkBoxShowMass.blockSignals(False)

        self.ui.schedule_update()

    # ------------------------------------------------------------------
    # Marker
    # ------------------------------------------------------------------
    def update_marker_symbol(self, new_marker=None):
        """
        Updates marker symbol combobox and triggers plot update.

        If `new_marker` is None, it uses the current text of the combobox to set `self.marker`.
        If `new_marker` is provided, it updates the `ui.comboBoxMarker` state accordingly.

        Parameters
        ----------
        new_marker : str, optional
            New marker for the combobox, by default None
        """
        if new_marker is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.marker = self.elements.comboBoxMarker.currentText()
            self.ui.style_data.blockSignals(False)
        else:
            if new_marker == self.elements.comboBoxMarker.currentText():
                return
            
            self.elements.comboBoxMarker.blockSignals(True)
            self.elements.comboBoxMarker.setCurrentText(new_marker)
            self.elements.comboBoxMarker.blockSignals(False)

        self.ui.schedule_update()

    def update_marker_size(self, new_value=None):
        """
        Updates marker size double spinbox and triggers plot update.

        If `new_value` is None, it uses the current value of the spinbox to set `self.marker_size`.
        If `new_value` is provided, it updates the `ui.doubleSpinBoxMarkerSize` state accordingly.

        Parameters
        ----------
        new_value : float, optional
            New size for the spinbox, by default None
        """
        if new_value is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.marker_size = self.elements.doubleSpinBoxMarkerSize.value()
            self.ui.style_data.blockSignals(False)
        else:
            if new_value == self.elements.doubleSpinBoxMarkerSize.value():
                return
            self.elements.doubleSpinBoxMarkerSize.blockSignals(True)
            self.elements.doubleSpinBoxMarkerSize.setValue(new_value)
            self.elements.doubleSpinBoxMarkerSize.blockSignals(False)

        self.ui.schedule_update()

    def update_marker_color(self, new_color=None):
        if new_color is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.marker_color = new_color
            self.ui.style_data.blockSignals(False)
        else:
            if new_color == self.elements.colorButtonMarkerColor.color:
                return

            self.elements.colorButtonMarkerColor.blockSignals(True)
            self.elements.colorButtonMarkerColor.color = new_color
            self.elements.colorButtonMarkerColor.blockSignals(False)

        self.ui.schedule_update()

    def update_marker_transparency(self, new_value=None):
        """
        Updates marker transparency (alpha) slider and triggers plot update.

        If `new_value` is None, it uses the current value of the slider to set `self.marker_alpha`.
        If `new_value` is provided, it updates the `ui.sliderTransparencyAlpha` state accordingly.

        Parameters
        ----------
        new_value : float, optional
            New transparency for the slider, by default None
        """
        if new_value is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.marker_alpha = self.elements.sliderTransparency.value()
            self.ui.style_data.blockSignals(False)
        else:
            if new_value == self.elements.sliderTransparency.value():
                return

            self.elements.sliderTransparency.blockSignals(True)
            self.elements.sliderTransparency.setValue(new_value)
            self.elements.sliderTransparency.blockSignals(False)

        self.ui.schedule_update()

    # ------------------------------------------------------------------
    # Line
    # ------------------------------------------------------------------
    def update_line_width(self, new_value=None):
        """
        Updates line width double spinbox and triggers plot update.

        If `new_value` is None, it uses the current value of the spinbox to set `self.line_width`.
        If `new_value` is provided, it updates the `ui.doubleSpinBoxLineWidth` state accordingly.

        Parameters
        ----------
        new_value : float, optional
            New width for the spinbox, by default None
        """
        if new_value is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.line_width = self.elements.doubleSpinBoxLineWidth.value()
            self.ui.style_data.blockSignals(False)
        else:
            if new_value == self.elements.doubleSpinBoxLineWidth.value():
                return

            self.elements.doubleSpinBoxLineWidth.blockSignals(True)
            self.elements.doubleSpinBoxLineWidth.setValue(new_value)
            self.elements.doubleSpinBoxLineWidth.blockSignals(False)

        self.ui.schedule_update()

    def update_length_multiplier(self, new_value=None):
        """
        Updates line multiplier line edit and triggers plot update.

        If `new_value` is None, it uses the current value of the line edit to set `self.length_multiplier`.
        If `new_value` is provided, it updates the `ui.lineEditLengthMultiplier` state accordingly.

        Parameters
        ----------
        new_value : float, optional
            New mulitiplier for the line edit, by default None
        """
        if new_value is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.length_multiplier = self.elements.lineEditLengthMultiplier.value
            self.ui.style_data.blockSignals(False)
        else:
            if new_value == self.elements.lineEditLengthMultiplier.value:
                return

            self.elements.lineEditLengthMultiplier.blockSignals(True)
            self.elements.lineEditLengthMultiplier.value = new_value
            self.elements.lineEditLengthMultiplier.blockSignals(False)

        self.ui.schedule_update()

    def update_line_color(self, new_color=None):
        if new_color is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.line_color = new_color
            self.ui.style_data.blockSignals(False)
        else:
            if new_color == self.elements.colorButtonLineColor.color:
                self.elements.colorButtonLineColor.blockSignals(True)
                self.elements.colorButtonLineColor.color = new_color
                self.elements.colorButtonLineColor.blockSignals(False)

        self.ui.schedule_update()

    # ------------------------------------------------------------------
    # Font
    # ------------------------------------------------------------------
    def update_font_family(self, new_font=None):
        """
        Updates font family combobox and triggers plot update.

        If `new_text` is None, it uses the current text of the combobox to set `self.font`.
        If `new_text` is provided, it updates the `ui.fontComboBox` state accordingly.

        Parameters
        ----------
        new_font : str, optional
            New font family for the combobox, by default None
        """
        if new_font is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.font = self.annotations.fontComboBox.currentText()
            self.ui.style_data.blockSignals(False)
        else:
            if new_font == self.annotations.fontComboBox.currentText():
                return

            self.annotations.fontComboBox.blockSignals(True)
            self.annotations.fontComboBox.setCurrentText(new_font)
            self.annotations.fontComboBox.blockSignals(False)

        self.ui.schedule_update()

    def update_font_size(self, new_value=None):
        """
        Updates font size spinbox and triggers plot update.

        If `new_value` is None, it uses the current value of the spinbox to set `self.font_size`.
        If `new_value` is provided, it updates the `ui.doubleSpinBoxFontSize` state accordingly.

        Parameters
        ----------
        new_value : float, optional
            New font size for the spinbox, by default None
        """
        if new_value is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.font_size = self.annotations.doubleSpinBoxFontSize.value()
            self.ui.style_data.blockSignals(False)
        else:
            if new_value == self.annotations.doubleSpinBoxFontSize.value():
                return

            self.annotations.doubleSpinBoxFontSize.blockSignals(True)
            self.annotations.doubleSpinBoxFontSize.setValue(new_value)
            self.annotations.doubleSpinBoxFontSize.blockSignals(False)

        self.ui.schedule_update()

    # ------------------------------------------------------------------
    # Colormap / colour‑bar
    # ------------------------------------------------------------------
    def update_field_colormap(self, new_text=None):
        """
        Updates colormap combobox, usually associated with fields, and triggers plot update.

        If `new_text` is None, it uses the current text of the combobox to set `self.cmap`.
        If `new_text` is provided, it updates the `ui.comboBoxFieldColormap` state accordingly.

        Parameters
        ----------
        new_text : str, optional
            New colormap for the combobox, by default None
        """
        if new_text is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.cmap = self.caxes.comboBoxFieldColormap.currentText()
            self.ui.style_data.blockSignals(False)
        else:
            if new_text == self.caxes.comboBoxFieldColormap.currentText():
                return

            self.caxes.comboBoxFieldColormap.blockSignals(True)
            self.caxes.comboBoxFieldColormap.setCurrentText(new_text)
            self.caxes.comboBoxFieldColormap.blockSignals(False)

        self.toggle_style_widgets()
        self.ui.style_data.style_dict[self.ui.control_dock.comboBoxPlotType.currentText()]['Colormap'] = self.caxes.comboBoxFieldColormap.currentText()

        self.ui.schedule_update()

    def update_cbar_reverse(self, new_value):
        if new_value is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.cbar_reverse = self.caxes.checkBoxReverseColormap.isChecked()
            self.ui.style_data.blockSignals(False)
        else:
            if new_value == self.caxes.checkBoxReverseColormap.isChecked():
                return

            self.caxes.checkBoxReverseColormap.blockSignals(True)
            self.caxes.checkBoxReverseColormap.setChecked(new_value)
            self.caxes.checkBoxReverseColormap.blockSignals(False)

        self.ui.schedule_update()

    def update_cbar_direction(self, new_text=None):
        """
        Updates colormap direction combobox and triggers plot update.

        If `new_text` is None, it uses the current text of the combobox to set `self.cbar_dir`.
        If `new_text` is provided, it updates the `ui.comboBoxCbarDirection` state accordingly.

        Parameters
        ----------
        new_text : str, optional
            New colormap direction for the combobox, by default None
        """
        if new_text is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.cbar_dir = self.caxes.comboBoxCbarDirection.currentText()
            self.ui.style_data.blockSignals(False)
        else:
            if new_text == self.caxes.comboBoxCbarDirection.currentText():
                return

            self.caxes.comboBoxCbarDirection.blockSignals(True)
            self.caxes.comboBoxCbarDirection.setCurrentText(new_text)
            self.caxes.comboBoxCbarDirection.blockSignals(False)

        self.ui.schedule_update()

    # ------------------------------------------------------------------
    # Heat‑map resolution
    # ------------------------------------------------------------------
    def update_resolution(self, new_value=None):

        if new_value is None:
            self.ui.style_data.blockSignals(True)
            self.ui.style_data.resolution = self.caxes.spinBoxHeatmapResolution.value()
            self.ui.style_data.blockSignals(False)
        else:
            if new_value == self.caxes.spinBoxHeatmapResolution.value():
                return
            
            self.caxes.spinBoxHeatmapResolution.blockSignals(True)
            self.caxes.spinBoxHeatmapResolution.setValue(new_value)
            self.caxes.spinBoxHeatmapResolution.blockSignals(False)

        if self.ui.style_data.plot_type.lower() == "heatmap" and self.ui.control_dock.toolbox:
            self.ui.schedule_update()


    # general style functions
    # -------------------------------------
    def disable_style_widgets(self):
        """Disables all style related widgets."""        

        # x-axis widgets
        self.axes.lineEditXLB.setEnabled(False)
        self.axes.lineEditXUB.setEnabled(False)
        self.axes.comboBoxXScale.setEnabled(False)
        self.axes.lineEditXLabel.setEnabled(False)

        # y-axis widgets
        self.axes.lineEditYLB.setEnabled(False)
        self.axes.lineEditYUB.setEnabled(False)
        self.axes.comboBoxYScale.setEnabled(False)
        self.axes.lineEditYLabel.setEnabled(False)

        # z-axis widgets
        self.axes.lineEditZLB.setEnabled(False)
        self.axes.lineEditZUB.setEnabled(False)
        self.axes.comboBoxZScale.setEnabled(False)
        self.axes.lineEditZLabel.setEnabled(False)

        # other axis properties
        self.axes.lineEditAspectRatio.setEnabled(False)
        self.axes.comboBoxTickDirection.setEnabled(False)

        # annotations
        self.annotations.fontComboBox.setEnabled(False)
        self.annotations.doubleSpinBoxFontSize.setEnabled(False)
        self.annotations.checkBoxShowMass.setEnabled(False)

        # scale
        self.annotations.comboBoxScaleDirection.setEnabled(False)
        self.annotations.comboBoxScaleLocation.setEnabled(False)
        self.annotations.lineEditScaleLength.setEnabled(False)
        self.annotations.colorButtonOverlayColor.setEnabled(False)

        # markers and lines
        self.elements.comboBoxMarker.setEnabled(False)
        self.elements.doubleSpinBoxMarkerSize.setEnabled(False)
        self.elements.colorButtonMarkerColor.setEnabled(False)
        self.elements.sliderTransparency.setEnabled(False)
        self.elements.doubleSpinBoxLineWidth.setEnabled(False)
        self.elements.colorButtonLineColor.setEnabled(False)
        self.elements.lineEditLengthMultiplier.setEnabled(False)

        # coloring
        self.caxes.spinBoxHeatmapResolution.setEnabled(False)
        self.caxes.comboBoxFieldColormap.setEnabled(False)
        self.caxes.checkBoxReverseColormap.setEnabled(False)
        self.caxes.lineEditCLB.setEnabled(False)
        self.caxes.lineEditCUB.setEnabled(False)
        self.caxes.comboBoxCScale.setEnabled(False)
        self.caxes.lineEditCLabel.setEnabled(False)
        self.caxes.comboBoxCbarDirection.setEnabled(False)

    def toggle_style_widgets(self):
        """Enables/disables all style widgets

        Toggling of enabled states are based on ``MainWindow.toolBox`` page and the current plot type
        selected in ``MainWindow.comboBoxPlotType."""
        ui = self.ui

        #print('toggle_style_widgets')
        plot_type = self.ui.style_data.plot_type.lower()

        self.disable_style_widgets()

        # annotation properties
        self.annotations.fontComboBox.setEnabled(True)
        self.annotations.doubleSpinBoxFontSize.setEnabled(True)
        match plot_type.lower():
            case 'field map' | 'gradient map':
                # axes properties
                self.axes.lineEditXLB.setEnabled(True)
                self.axes.lineEditXUB.setEnabled(True)

                self.axes.lineEditYLB.setEnabled(True)
                self.axes.lineEditYUB.setEnabled(True)

                # scalebar properties
                self.annotations.comboBoxScaleDirection.setEnabled(True)
                self.annotations.comboBoxScaleLocation.setEnabled(True)
                self.annotations.lineEditScaleLength.setEnabled(True)
                self.annotations.colorButtonOverlayColor.setEnabled(True)

                self.annotations.checkBoxShowMass.setEnabled(True)

                # marker properties
                if ui.app_data.sample_id != '' and len(ui.data[ui.app_data.sample_id].spotdata) != 0:
                    self.elements.comboBoxMarker.setEnabled(True)
                    self.elements.doubleSpinBoxMarkerSize.setEnabled(True)
                    self.elements.sliderTransparency.setEnabled(True)

                    self.elements.colorButtonMarkerColor.setEnabled(True)

                # line properties
                self.elements.doubleSpinBoxLineWidth.setEnabled(True)
                self.elements.colorButtonLineColor.setEnabled(True)

                # color properties
                self.caxes.comboBoxFieldColormap.setEnabled(True)
                self.caxes.lineEditCLB.setEnabled(True)
                self.caxes.lineEditCUB.setEnabled(True)
                self.caxes.comboBoxCScale.setEnabled(True)
                self.caxes.comboBoxCbarDirection.setEnabled(True)
                self.caxes.lineEditCLabel.setEnabled(True)

            case 'correlation' | 'basis vectors':
                # axes properties
                self.axes.comboBoxTickDirection.setEnabled(True)

                self.annotations.checkBoxShowMass.setEnabled(True)

                # color properties
                self.caxes.comboBoxFieldColormap.setEnabled(True)
                self.caxes.lineEditCLB.setEnabled(True)
                self.caxes.lineEditCUB.setEnabled(True)
                self.caxes.comboBoxCbarDirection.setEnabled(True)

            case 'histogram':
                # axes properties
                self.axes.lineEditXLB.setEnabled(True)
                self.axes.lineEditXUB.setEnabled(True)
                self.axes.comboBoxXScale.setEnabled(True)
                self.axes.lineEditYLB.setEnabled(True)
                self.axes.lineEditYUB.setEnabled(True)
                self.axes.lineEditXLabel.setEnabled(True)
                self.axes.lineEditYLabel.setEnabled(True)
                self.axes.lineEditAspectRatio.setEnabled(True)
                self.axes.comboBoxTickDirection.setEnabled(True)

                self.annotations.checkBoxShowMass.setEnabled(True)

                # marker properties
                self.elements.sliderTransparency.setEnabled(True)

                # line properties
                self.elements.doubleSpinBoxLineWidth.setEnabled(True)
                self.elements.colorButtonLineColor.setEnabled(True)

                # color properties
                # if color by field is set to clusters, then colormap fields are on,
                # field is set by cluster table
                if self.ui.control_dock.comboBoxFieldTypeC.currentText().lower() == 'none':
                    self.elements.colorButtonMarkerColor.setEnabled(True)
                else:
                    self.caxes.comboBoxCbarDirection.setEnabled(True)

            case 'scatter' | 'PCA scatter':
                # axes properties
                if (self.ui.control_dock.toolbox.currentIndex() != self.ui.control_dock.tab_dict['scatter']) or (self.ui.control_dock.comboBoxFieldZ.currentText() == ''):
                    self.axes.lineEditXLB.setEnabled(True)
                    self.axes.lineEditXUB.setEnabled(True)
                    self.axes.comboBoxXScale.setEnabled(True)
                    self.axes.lineEditYLB.setEnabled(True)
                    self.axes.lineEditYUB.setEnabled(True)
                    self.axes.comboBoxYScale.setEnabled(True)

                self.axes.lineEditXLabel.setEnabled(True)
                self.axes.lineEditYLabel.setEnabled(True)
                if self.ui.control_dock.comboBoxFieldZ.currentText() != '':
                    self.axes.lineEditZLB.setEnabled(True)
                    self.axes.lineEditZUB.setEnabled(True)
                    self.axes.comboBoxZScale.setEnabled(True)
                    self.axes.lineEditZLabel.setEnabled(True)
                self.axes.lineEditAspectRatio.setEnabled(True)
                self.axes.comboBoxTickDirection.setEnabled(True)

                self.annotations.checkBoxShowMass.setEnabled(True)

                # marker properties
                self.elements.comboBoxMarker.setEnabled(True)
                self.elements.doubleSpinBoxMarkerSize.setEnabled(True)
                self.elements.sliderTransparency.setEnabled(True)

                # line properties
                if self.ui.control_dock.comboBoxFieldZ.currentText() == '':
                    self.elements.doubleSpinBoxLineWidth.setEnabled(True)
                    self.elements.colorButtonLineColor.setEnabled(True)

                if plot_type == 'PCA scatter':
                    self.elements.lineEditLengthMultiplier.setEnabled(True)

                # color properties
                # if color by field is none, then use marker color,
                # otherwise turn off marker color and turn all field and colormap properties to on
                if self.ui.control_dock.comboBoxFieldTypeC.currentText().lower() == 'none':
                    self.elements.colorButtonMarkerColor.setEnabled(True)

                elif self.ui.control_dock.comboBoxFieldTypeC.currentText() == 'cluster':

                    self.caxes.comboBoxCbarDirection.setEnabled(True)

                    self.caxes.comboBoxFieldColormap.setEnabled(True)
                    self.caxes.lineEditCLB.setEnabled(True)
                    self.caxes.lineEditCUB.setEnabled(True)
                    self.caxes.comboBoxCScale.setEnabled(True)
                    self.caxes.comboBoxCbarDirection.setEnabled(True)
                    self.caxes.lineEditCLabel.setEnabled(True)

            case 'heatmap' | 'PCA heatmap':
                # axes properties
                if (self.ui.control_dock.toolbox.currentIndex() != self.ui.control_dock.tab_dict['scatter']) or (self.ui.control_dock.comboBoxFieldZ.currentText() == ''):
                    self.axes.lineEditXLB.setEnabled(True)
                    self.axes.lineEditXUB.setEnabled(True)
                    self.axes.comboBoxXScale.setEnabled(True)
                    self.axes.lineEditYLB.setEnabled(True)
                    self.axes.lineEditYUB.setEnabled(True)
                    self.axes.comboBoxYScale.setEnabled(True)

                self.axes.lineEditXLabel.setEnabled(True)
                self.axes.lineEditYLabel.setEnabled(True)
                if (self.ui.control_dock.toolbox.currentIndex() == self.ui.control_dock.tab_dict['scatter']) and (self.ui.control_dock.comboBoxFieldZ.currentText() == ''):
                    self.axes.lineEditZLB.setEnabled(True)
                    self.axes.lineEditZUB.setEnabled(True)
                    self.axes.comboBoxZScale.setEnabled(True)
                    self.axes.lineEditZLabel.setEnabled(True)
                self.axes.lineEditAspectRatio.setEnabled(True)
                self.axes.comboBoxTickDirection.setEnabled(True)

                self.annotations.checkBoxShowMass.setEnabled(True)

                # line properties
                if self.ui.control_dock.comboBoxFieldZ.currentText() == '':
                    self.elements.doubleSpinBoxLineWidth.setEnabled(True)
                    self.elements.colorButtonLineColor.setEnabled(True)

                if plot_type == 'PCA heatmap':
                    self.elements.lineEditLengthMultiplier.setEnabled(True)

                # color properties
                self.caxes.comboBoxFieldColormap.setEnabled(True)
                self.caxes.lineEditCLB.setEnabled(True)
                self.caxes.lineEditCUB.setEnabled(True)
                self.caxes.comboBoxCScale.setEnabled(True)
                self.caxes.comboBoxCbarDirection.setEnabled(True)
                self.caxes.lineEditCLabel.setEnabled(True)

                self.caxes.spinBoxHeatmapResolution.setEnabled(True)
            case 'ternary map':
                # axes properties
                self.axes.lineEditXLB.setEnabled(True)
                self.axes.lineEditXUB.setEnabled(True)
                self.axes.comboBoxXScale.setEnabled(True)
                self.axes.lineEditYLB.setEnabled(True)
                self.axes.lineEditYUB.setEnabled(True)
                self.axes.comboBoxYScale.setEnabled(True)
                self.axes.lineEditZLB.setEnabled(True)
                self.axes.lineEditZUB.setEnabled(True)
                self.axes.comboBoxZScale.setEnabled(True)
                self.axes.lineEditYLabel.setEnabled(True)
                self.axes.lineEditYLabel.setEnabled(True)
                self.axes.lineEditZLabel.setEnabled(True)

                self.annotations.checkBoxShowMass.setEnabled(True)

                # scalebar properties
                self.annotations.comboBoxScaleDirection.setEnabled(True)
                self.annotations.comboBoxScaleLocation.setEnabled(True)
                self.annotations.lineEditScaleLength.setEnabled(True)
                self.annotations.colorButtonOverlayColor.setEnabled(True)

                # marker properties
                if not self.ui.app_data.current_data.spotdata.empty:
                    self.elements.comboBoxMarker.setEnabled(True)
                    self.elements.doubleSpinBoxMarkerSize.setEnabled(True)
                    self.elements.sliderTransparency.setEnabled(True)

                    self.elements.colorButtonMarkerColor.setEnabled(True)

            case 'tec' | 'radar':
                # axes properties
                if plot_type == 'tec':
                    self.axes.lineEditYLB.setEnabled(True)
                    self.axes.lineEditYUB.setEnabled(True)
                    self.axes.lineEditYLabel.setEnabled(True)
                self.axes.lineEditAspectRatio.setEnabled(True)
                self.axes.comboBoxTickDirection.setEnabled(True)

                self.annotations.checkBoxShowMass.setEnabled(True)

                # scalebar properties
                self.annotations.lineEditScaleLength.setEnabled(True)

                # marker properties
                self.elements.sliderTransparency.setEnabled(True)

                # line properties
                self.elements.doubleSpinBoxLineWidth.setEnabled(True)
                self.elements.colorButtonLineColor.setEnabled(True)

                # color properties
                if self.ui.control_dock.comboBoxFieldTypeC.currentText().lower() == 'none':
                    self.elements.colorButtonMarkerColor.setEnabled(True)
                elif self.ui.control_dock.comboBoxFieldTypeC.currentText().lower() == 'cluster':
                    self.caxes.comboBoxCbarDirection.setEnabled(True)

            case 'variance' | 'cluster performance':
                # axes properties
                self.axes.lineEditAspectRatio.setEnabled(True)
                self.axes.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.annotations.lineEditScaleLength.setEnabled(True)
                self.annotations.colorButtonOverlayColor.setEnabled(True)

                self.annotations.checkBoxShowMass.setEnabled(False)

                # marker properties
                self.elements.comboBoxMarker.setEnabled(True)
                self.elements.doubleSpinBoxMarkerSize.setEnabled(True)

                # line properties
                self.elements.doubleSpinBoxLineWidth.setEnabled(True)
                self.elements.colorButtonLineColor.setEnabled(True)

                # color properties
                self.elements.colorButtonMarkerColor.setEnabled(True)

            case 'pca score' | 'cluster score' | 'cluster map':
                # axes properties
                self.axes.lineEditXLB.setEnabled(True)
                self.axes.lineEditXUB.setEnabled(True)
                self.axes.lineEditYLB.setEnabled(True)
                self.axes.lineEditYUB.setEnabled(True)

                # scalebar properties
                self.annotations.comboBoxScaleDirection.setEnabled(True)
                self.annotations.comboBoxScaleLocation.setEnabled(True)
                self.annotations.lineEditScaleLength.setEnabled(True)
                self.annotations.colorButtonOverlayColor.setEnabled(True)

                self.annotations.checkBoxShowMass.setEnabled(False)

                # marker properties
                # if len(ui.spotdata) != 0:
                #     ui.comboBoxMarker.setEnabled(True)
                #     ui.doubleSpinBoxMarkerSize.setEnabled(True)
                #     ui.sliderTransparencyAlpha.setEnabled(True)
                #     ui.labelMarkerAlpha.setEnabled(True)
                #     ui.colorButtonMarkerColor.setEnabled(True)

                # line properties
                self.elements.doubleSpinBoxLineWidth.setEnabled(True)
                self.elements.colorButtonLineColor.setEnabled(True)

                # color properties
                if plot_type != 'clusters':
                    self.caxes.comboBoxFieldColormap.setEnabled(True)
                    self.caxes.lineEditCLB.setEnabled(True)
                    self.caxes.lineEditCUB.setEnabled(True)
                    self.caxes.comboBoxCScale.setEnabled(True)
                    self.caxes.comboBoxCbarDirection.setEnabled(True)
                    self.caxes.lineEditCLabel.setEnabled(True)
            case 'profile':
                # axes properties
                self.axes.lineEditXLB.setEnabled(True)
                self.axes.lineEditXUB.setEnabled(True)
                self.axes.lineEditAspectRatio.setEnabled(True)
                self.axes.comboBoxTickDirection.setEnabled(True)

                self.annotations.checkBoxShowMass.setEnabled(True)

                # scalebar properties
                self.annotations.lineEditScaleLength.setEnabled(True)

                # marker properties
                self.elements.comboBoxMarker.setEnabled(True)
                self.elements.doubleSpinBoxMarkerSize.setEnabled(True)

                # line properties
                self.elements.doubleSpinBoxLineWidth.setEnabled(True)
                self.elements.colorButtonLineColor.setEnabled(True)

                # color properties
                self.elements.colorButtonMarkerColor.setEnabled(True)
                self.caxes.comboBoxFieldColormap.setEnabled(True)
        
        # enable/disable labels
        #self.toggle_style_labels()

    def toggle_style_labels(self):
        """Toggles style labels based on enabled/disabled style widgets."""        
        ui = self.ui

        # axes properties - only toggle widgets that actually exist
        self.axes.toolButtonXAxisReset.setEnabled(self.axes.lineEditXLB.isEnabled())
        self.axes.toolButtonYAxisReset.setEnabled(self.axes.lineEditYLB.isEnabled())
        self.axes.toolButtonZAxisReset.setEnabled(self.axes.lineEditZLB.isEnabled())

        # color properties
        self.caxes.toolButtonCAxisReset.setEnabled(self.caxes.lineEditCLB.isEnabled())
        self.caxes.checkBoxReverseColormap.setEnabled(self.caxes.comboBoxFieldColormap.isEnabled())
        
        # scalebar properties - update overlay color styling
        if hasattr(self, 'annotations') and self.annotations.colorButtonOverlayColor.isEnabled():
            self.annotations.colorButtonOverlayColor.setStyleSheet("background-color: %s;" % self.ui.style_data.style_dict[self.ui.style_data.plot_type]['OverlayColor'])
        elif hasattr(self, 'annotations'):
            self.annotations.colorButtonOverlayColor.setStyleSheet("background-color: %s;" % '#e6e6e6')

    def set_style_widgets(self):
        """Sets values in right toolbox style page

        Parameters
        ----------
        plot_type : str, optional
            Dictionary key into ``MainWindow.styles``, Defaults to ``None``
        style : dict, optional
            Style dictionary for the current plot type. Defaults to ``None``
        """
        if self.ui.app_data.sample_id == '' or self.ui.style_data.plot_type =='':
            return

        data = self.ui.app_data.current_data

        self.signal_state = True

        style = self.ui.style_data

        # toggle actionSwapAxes
        match style.plot_type:
            case 'field map' | 'gradient map'| 'scatter' | 'heatmap':
                self.ui.lame_action.SwapAxes.setEnabled(True)
            case _:
                self.ui.lame_action.SwapAxes.setEnabled(False)

        if (style.scale_length is None) and (style.plot_type.lower() in style.map_plot_types):
            style.scale_length = style.default_scale_length()

        # axes properties
        # set style dictionary values for Axes
        for ax in ['x', 'y', 'z', 'c']:
            axes_obj = self.caxes if ax == 'c' else self.axes

            # Get axis-specific widgets
            lb = getattr(axes_obj, f"lineEdit{ax.upper()}LB")
            ub = getattr(axes_obj, f"lineEdit{ax.upper()}UB")
            if style.plot_type in style.map_plot_types and ax in ['x', 'y']:
                # do not round axes limits for coordinates
                lb.precision = None
                ub.precision = None
            else:
                # limit precision for non coordinates
                lb.precision = 3
                ub.precision = 3
            label = getattr(axes_obj, f"lineEdit{ax.upper()}Label")
            scale = getattr(axes_obj, f"comboBox{ax.upper()}Scale")

            # Set axis limits, label, and scale
            lb.value = getattr(style, f"{ax}lim")[0]
            ub.value = getattr(style, f"{ax}lim")[1]
            label.setText(getattr(style, f"{ax}label"))
            # scale probably needs to get fixed to clear and add correct list
            # of options each time.
            scale.setCurrentText(getattr(style, f"{ax}scale"))

            # Get and set field type and field in control dock
            field_type = getattr(self.ui.control_dock, f"comboBoxFieldType{ax.upper()}")
            field = getattr(self.ui.control_dock, f"comboBoxField{ax.upper()}")

            field_type.setCurrentText(getattr(self.ui.app_data, f"{ax}_field_type"))
            field.setCurrentText(getattr(self.ui.app_data, f"{ax}_field"))

            # color properties
            self.ui.control_dock.update_field_type_combobox_options(
                field_type,
                field,
                ax=ax
            )
            if getattr(self.ui.app_data, f"{ax}_field_type") is None or getattr(self.ui.app_data, f"{ax}_field_type") == '':
                field_type.setCurrentIndex(0)
                setattr(self.ui.app_data, f"{ax}_field_type", field_type.currentText())
            else:
                #field.setCurrentText(getattr(self.ui.style_data, f"{c}_field_type")
                pass

            if getattr(self.ui.app_data, f"{ax}_field_type") == '':
                field.clear()
            else:
                self.ui.control_dock.update_field_combobox_options(field, field_type)
                self.ui.control_dock.spinBoxFieldC.setMinimum(0)
                self.ui.control_dock.spinBoxFieldC.setMaximum(field.count() - 1)

            if getattr(self.ui.app_data, f"{ax}_field") in field.allItems():
                field.setCurrentText(self.ui.app_data.c_field)
                #self.ui.c_field_spinbox_changed()
            else:
                #self.ui.style_data.c_field = self.ui.control_dock.comboBoxFieldC.currentText()
                pass

        # for map plots
        if style.plot_type.lower() in style.map_plot_types:
            style.aspect_ratio = data.aspect_ratio
            
            if style.scale_length is None:
                style.scale_length = style.default_scale_length()
        else:
            self.scale_length = None

        self.axes.lineEditAspectRatio.value = style.aspect_ratio
        self.axes.comboBoxTickDirection.setCurrentText(style.tick_dir)

        # annotation properties
        # Font
        if isinstance(style.font, str):
            self.annotations.fontComboBox.setCurrentFont(QFont(style.font))
        else:
            self.annotations.fontComboBox.setCurrentFont(style.font)
        self.annotations.doubleSpinBoxFontSize.setValue(style.font_size)

        # scalebar properties
        self.annotations.comboBoxScaleDirection.setCurrentText(style.scale_dir)
        self.annotations.comboBoxScaleLocation.setCurrentText(style.scale_location)
        self.annotations.colorButtonOverlayColor.color = style.overlay_color

        # Marker
        self.elements.comboBoxMarker.setCurrentText(style.marker)
        self.elements.doubleSpinBoxMarkerSize.setValue(style.marker_size)
        self.elements.colorButtonMarkerColor.color = style.marker_color
        self.elements.sliderTransparency.setValue(style.marker_alpha)

        # Line
        self.elements.doubleSpinBoxLineWidth.setValue(style.line_width)
        self.elements.colorButtonLineColor.color = style.line_color
        self.elements.lineEditLengthMultiplier.value = style.length_multiplier


        self.caxes.comboBoxFieldColormap.setCurrentText(style.cmap)
        self.caxes.checkBoxReverseColormap.setChecked(style.cbar_reverse)
        
        field = self.ui.app_data.c_field
        if field in list(data.processed.column_attributes.keys()):
            self.ui.style_data.clim = [data.processed.get_attribute(field,'plot_min'), data.processed.get_attribute(field,'plot_max')]
            self.ui.style_data.clabel = data.processed.get_attribute(field,'label')
        else:
            self.ui.style_data.clim = style['CLim']
            self.ui.style_data.clabel = style['CLabel']
        
        if self.ui.app_data.c_field_type == 'cluster':
            # set color field to active cluster method
            self.ui.control_dock.comboBoxFieldC.setCurrentText(self.ui.cluster_dict['active method'])

            # set color scale to discrete
            self.caxes.comboBoxCScale.clear()
            self.caxes.comboBoxCScale.addItem('discrete')
            self.caxes.comboBoxCScale.setCurrentText('discrete')

            self.ui.style_data.cscale = 'discrete'
        else:
            # set color scale options to linear/log
            self.caxes.comboBoxCScale.clear()
            self.caxes.comboBoxCScale.addItems(data.scale_options(plot_type=self.ui.style_data.plot_type, ax='c', field_type=self.ui.app_data.c_field_type, field=self.ui.app_data.c_field))
            self.ui.style_data.cscale = 'linear'
            self.caxes.comboBoxCScale.setCurrentText(self.ui.style_data.cscale)
            
        self.caxes.comboBoxCbarDirection.setCurrentText(style.cbar_dir)
        self.caxes.spinBoxHeatmapResolution.setValue(style.resolution)

        # turn properties on/off based on plot type and style settings
        self.toggle_style_widgets()

        self.signal_state = False


    # style widget callbacks
    # -------------------------------------
    # axes
    # -------------------------------------
    def axis_variable_changed(self, field, ax):
        """Updates axis variables when the field is changed.

        Parameters
        ----------
        field_type : str
            field type
        field : str
            field
        ax : str, optional
            axis for plotting, by default "None"
        """
        ui = self.ui

        scalebox = self.axis_widget_dict[ax]['scalebox']
        lbound = self.axis_widget_dict[ax]['lbound']
        ubound = self.axis_widget_dict[ax]['ubound']
        axis_label = self.axis_widget_dict[ax]['axis_label']
        reset_btn = self.axis_widget_dict[ax]['reset_btn']

        if field == '' or field.lower() == 'none':
            for w in (lbound, ubound, axis_label):
                w.setEnabled(False)
                w.setText('')
            scalebox.setEnabled(False)
            scalebox.setText('')
            reset_btn.setEnabled(False)
            
            return

        amin, amax, scale, label = self.ui.style_data.get_axis_values(self.ui.app_data.current_data, field)

        plot_type = self.ui.style_data.plot_type

        self.ui.style_data.set_axis_lim(ax, [amin, amax])
        self.ui.style_data.set_axis_scale(ax, scale)
        self.ui.style_data.set_axis_label(ax, label)

        for w in (lbound, ubound, axis_label, scalebox, reset_btn):
            w.setEnabled(True)
        lbound.value = amin
        ubound.value = amax
        scalebox.setCurrentText(scale)
        axis_label.setText(label)

        self.ui.schedule_update()

    def axis_label_edit_callback(self, ax, new_label):
        """Updates axis label in dictionaries from widget

        Parameters
        ----------
        ax : str
            Axis that has changed, options include ``x``, ``y``, ``z``, and ``c``.
        new_label : str
            New label for bound set by user.
        """
        data = self.ui.app_data.current_data

        if ax == 'c':
            old_label = self.ui.style_data.style_dict[self.ui.style_data.plot_type][ax.upper()+'Label']
        else:
            old_label = self.ui.style_data.style_dict[self.ui.style_data.plot_type][ax.upper()+'Label']

        # if label has not changed return
        if old_label == new_label:
            return

        # change label in dictionary
        field = self.ui.control_dock.get_axis_field(ax)
        data.processed.set_attribute(field,'label', new_label)
        if ax == 'c':
            self.ui.style_data.style_dict[self.ui.style_data.plot_type][ax.upper()+'Label'] = new_label
        else:
            self.ui.style_data.style_dict[self.ui.style_data.plot_type][ax.upper()+'Label'] = new_label

        # update plot
        self.ui.schedule_update()

    def axis_limit_edit_callback(self, ax, bound, new_value,field= None, ui_update= True):
        """Updates axis limit in dictionaries from widget

        Parameters
        ----------
        ax : str
            Axis that has changed, options include ``x``, ``y``, ``z``, and ``c``.
        bound : int
            Indicates whether the bound to set is a lower (``0``) or upper (``1``).
        new_value : float
            New value for bound set by user.
        """
        data = self.ui.app_data.current_data

        if ui_update:
            plot_type = self.ui.control_dock.comboBoxPlotType.currentText()
        else:
            plot_type = self.ui.style_data.plot_type

        if ax == 'c':
            old_value = self.ui.style_data.style_dict[plot_type]['CLim'][bound]
        else:
            old_value = self.ui.style_data.style_dict[plot_type][ax.upper()+'Lim'][bound]

        # if label has not changed return
        if old_value == new_value:
            return

        if ui_update:
            if ax == 'c' and plot_type in ['heatmap', 'correlation']:
                self.ui.schedule_update()
                return
        if not field:
            # change label in dictionary
            field = self.ui.control_dock.get_axis_field(ax)
        if bound:
            if plot_type == 'histogram' and ax == 'y':
                data.processed.set_attribute(field,'p_max', new_value)
                
            else:
                data.processed.set_attribute(field,'plot_max', new_value)
                
        else:
            if plot_type == 'histogram' and ax == 'y':
                data.processed.set_attribute(field,'p_min', new_value)
            else:
                data.processed.set_attribute(field,'plot_min', new_value)

        if ax == 'c':
            self.ui.style_data.style_dict[plot_type][f'{ax.upper()}Lim'][bound] = new_value
        else:
            self.ui.style_data.style_dict[plot_type][f'{ax.upper()}Lim'][bound] = new_value

        # update plot
        self.ui.schedule_update()

    def axis_scale_callback(self, comboBox, ax):
        """Updates axis scale when a scale comboBox has changed.

        Parameters
        ----------
        comboBox : QComboBox
            Widget whos scale has changed.
        ax : str
            Axis whos scale been set from comboBox, options include ``x``, ``y``, ``z``, and ``c``.
        """        
        data = self.ui.app_data.current_data

        styles = self.ui.style_data.style_dict[self._plot_type]

        new_value = comboBox.currentText()
        if ax == 'c':
            if styles['CLim'] == new_value:
                return
        elif styles[ax.upper()+'norm'] == new_value:
            return

        field = self.ui.control_dock.get_axis_field(ax)

        if self._plot_type != 'heatmap':
            data.processed.set_attribute(field,'norm',new_value)

        if ax == 'c':
            styles['CScale'] = new_value
        else:
            styles[ax.upper()+'norm'] = new_value

        # update plot
        self.ui.schedule_update()

    def set_color_axis_widgets(self):
        """Sets the color axis limits, label, and related widgets."""
        data = self.ui.app_data.current_data

        field = self.ui.control_dock.comboBoxFieldC.currentText()
        if field == '':
            return
        
        # Update color axis bounds and scale
        if data and data.processed:
            self.caxes.lineEditCLB.value = data.processed.get_attribute(field,'plot_min')
            self.caxes.lineEditCUB.value = data.processed.get_attribute(field,'plot_max')
            self.caxes.comboBoxCScale.setCurrentText(data.processed.get_attribute(field,'norm'))
            
            # Update color axis label
            label = data.processed.get_attribute(field,'label')
            self.caxes.lineEditCLabel.setText(label)
            
            # Update style data
            self.ui.style_data.clabel = label


    def axis_reset_callback(self, ax):
        """Resets axes widgets and plot axes to auto values

        Resets the axis limits and scales to auto values, and updates the style dictionary.     

        Parameters
        ----------
        ax : str
            axis to reset values, can be `x`, `y`, `z` and `c`

        """
        data = self.ui.app_data.current_data

        if ax == 'c':
            if self.ui.control_dock.comboBoxPlotType.currentText() == 'basis vectors':
                self.ui.style_data.style_dict['basis vectors']['CLim'] = [np.amin(self.ui.pca_results.components_), np.amax(self.ui.pca_results.components_)]
            elif not (self.ui.control_dock.comboBoxFieldTypeC.currentText() in ['none','cluster']):
                field_type = self.ui.control_dock.comboBoxFieldTypeC.currentText()
                field = self.ui.control_dock.comboBoxFieldC.currentText()
                if field == '':
                    return
                data.processed.prep_data(field)

            self.set_color_axis_widgets()
        else:
            match self.ui.control_dock.comboBoxPlotType.currentText().lower():
                case 'field map' | 'cluster map' | 'cluster score map' | 'pca score':
                    field = ax.upper()
                    data.processed.prep_data(field)
                    self.set_axis_widgets(ax, field)
                case 'histogram':
                    field = self.ui.control_dock.comboBoxFieldC.currentText()
                    if ax == 'x':
                        field_type = self.ui.control_dock.comboBoxFieldTypeC.currentText()
                        data.processed.prep_data(field)
                        self.set_axis_widgets(ax, field)
                    else:
                        data.processed.set_attribute(field, 'p_min', None)
                        data.processed.set_attribute(field, 'p_max', None)

                case 'scatter' | 'heatmap':
                    match ax:
                        case 'x':
                            field_type = self.ui.control_dock.comboBoxFieldTypeX.currentText()
                            field = self.ui.control_dock.comboBoxFieldX.currentText()
                        case 'y':
                            field_type = self.ui.control_dock.comboBoxFieldTypeY.currentText()
                            field = self.ui.control_dock.comboBoxFieldY.currentText()
                        case 'z':
                            field_type = self.ui.control_dock.comboBoxFieldTypeZ.currentText()
                            field = self.ui.control_dock.comboBoxFieldZ.currentText()
                    if (field_type == '') | (field == ''):
                        return
                    data.processed.prep_data(field)
                    self.set_axis_widgets(ax, field)

                case 'PCA scatter' | 'PCA heatmap':
                    field_type = 'PCA score'
                    if ax == 'x':
                        field = self.ui.spinBoxPCX.currentText()
                    else:
                        field = self.ui.spinBoxPCY.currentText()
                    data.processed.prep_data(field)
                    self.set_axis_widgets(ax, field)

                case _:
                    return

        self.set_style_widgets()
        self.ui.schedule_update()



    # text and annotations
    # -------------------------------------
    

    # scales
    # -------------------------------------

    def toggle_scale_widgets(self):
        """Toggles state of scale widgets.
         
        Enables/disables widgets based on ``self.scale_dir``, including the scale location and scale length."""
        if self.scale_dir == 'none':
            self.annotations.comboBoxScaleLocation.setEnabled(False)
            self.annotations.lineEditScaleLength.setEnabled(False)
            self.annotations.lineEditScaleLength.value = None
        else:
            self.annotations.comboBoxScaleLocation.setEnabled(True)
            self.annotations.lineEditScaleLength.setEnabled(True)
            # set scalebar length if plot is a map type
            if self.ui.style_data.plot_type not in self.ui.style_data.map_plot_types:
                self.scale_length = None
            else:
                self.scale_length = self.ui.style_data.default_scale_length()



    def scale_length_callback(self):
        """Updates length of scalebar on map-type plots
        
        Executes on change of ``MainWindow.lineEditScaleLength``, updates length if within bounds set by plot dimensions, then updates plot.
        """ 
        if self._plot_type in self.ui.style_data.map_plot_types:
            # make sure user input is within bounds, do not change
            if ((self.annotations.comboBoxScaleDirection.currentText() == 'horizontal') and (scale_length > data.x_range)) or (scale_length <= 0):
                scale_length = self.ui.style_data.style_dict[self._plot_type]['ScaleLength']
                self.annotations.lineEditScaleLength.value = scale_length
                return
            elif ((self.annotations.comboBoxScaleDirection.currentText() == 'vertical') and (scale_length > data.y_range)) or (scale_length <= 0):
                scale_length = self.ui.style_data.style_dict[self._plot_type]['ScaleLength']
                self.annotations.lineEditScaleLength.value = scale_length
                return
        else:
            if self.ui.style_data.style_dict[self._plot_type]['ScaleLength'] is not None:
                self.scale_length = None
                return

        # update plot
        self.ui.schedule_update()

    def overlay_color_callback(self):
        """Updates color of overlay markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.colorButtonOverlayColor`` color.
        """
        plot_type = self.ui.control_dock.comboBoxPlotType.currentText()
        # change color
        self.annotations.colorButtonOverlayColor.select_color()

        color = get_hex_color(self.annotations.colorButtonOverlayColor.palette().button().color())
        # update style
        if self.ui.style_data.style_dict[plot_type]['OverlayColor'] == color:
            return

        self.ui.style_data.style_dict[plot_type]['OverlayColor'] = color
        # update plot
        self.ui.schedule_update()

    # lines
    # -------------------------------------
    def line_color_callback(self):
        """Updates color of plot markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.colorButtonLineColor`` color.
        """
        # change color
        self.elements.colorButtonLineColor.select_color()
        color = get_hex_color(self.elements.colorButtonLineColor.palette().button().color())
        if self.line_color == color:
            return

        # update style
        self.line_color = color

        # update plot
        self.ui.schedule_update()

    # colors
    # -------------------------------------
    def marker_color_callback(self):
        """Updates color of plot markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.colorButtonMarkerColor`` color.
        """
        # change color
        self.button_color_select(self.elements.colorButtonMarkerColor)
        color = get_hex_color(self.elements.colorButtonMarkerColor.palette().button().color())
        if self.marker_color == color:
            return

        # update style
        self.marker_color = color

        # update plot
        self.ui.schedule_update()
