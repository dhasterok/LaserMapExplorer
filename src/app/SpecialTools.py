import numpy as np
import pandas as pd

from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import (
        QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QToolButton,
        QTableWidget, QTableWidgetItem, QSpacerItem, QFrame, QSizePolicy, QHeaderView, QTabWidget,
        QFormLayout, QComboBox, QLabel, QCheckBox
    )
from lame_core.CustomWidgets import CustomPage, CustomToolButton
from lame_core.UITheme import default_font
from lame_core.config import ICONPATH

class SpecialPage(CustomPage):
    """P-T-t Functions toolbox page (Thermometry/Barometry tabs).

    Lu-Hf/geochronology dating tools live in their own dock (``GeochronDock``,
    ``src/common/geochronology.py``), toggled from Tools > Geochronology.
    Diffusion modeling tools likewise live in their own dock (``DiffusionDock``,
    ``src/common/diffusion.py``), toggled from Tools > Diffusion.
    """
    def __init__(self, page_index, dock=None):
        if dock is None:
            return
        super().__init__(obj_name="PTtPage", parent=dock)

        self.dock = dock
        self.page_index = page_index

        # setupUI() constructs each sub-tab (ThermometryTab, BarmometryTab),
        # which each wire their own widgets in their own __init__ --
        # SpecialPage itself has nothing further to connect.
        self.setupUI()

    def setupUI(self):
        self.setGeometry(QRect(0, 0, 300, 321))
        self.setObjectName("PTtPage")

        self.special_fcns = QTabWidget(self)
        self.special_fcns.setMaximumSize(QSize(300, 16777215))
        self.special_fcns.setObjectName("special_fcns")

        self.thermometry = ThermometryTab(parent=self)
        self.special_fcns.addTab(self.thermometry, "Thermometry")

        self.barometry = BarmometryTab(parent=self)
        self.special_fcns.addTab(self.barometry, "Barmometry")

        self.addWidget(self.special_fcns)

        page_icon = QIcon(":/resources/icons/icon-zoning-64.svg")
        page_name = "P-T-t Functions"
        if not self.page_index:
            self.dock.toolbox.addItem(self, page_icon, page_name)
        else:
            self.dock.toolbox.insertItem(self.page_index+1, self, page_icon, page_name)

        self.dock.toolbox.set_page_icons(
            page_name,
            light_icon = ICONPATH / "icon-zoning-64.svg",
            dark_icon = ICONPATH / "icon-zoning-64.svg"
        )

class ThermometryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent = parent

        self.setupUI()
        self.connect_widgets()

    def setupUI(self):
        self.setObjectName("tabThermometry")

        form_layout = QFormLayout(self)
        form_layout.setContentsMargins(6, 6, 6, 6)
        form_layout.setObjectName("formLayout_16")

        self.comboBoxThermometryMethod = QComboBox(self)
        self.comboBoxThermometryMethod.setMaximumSize(QSize(200, 16777215))
        self.comboBoxThermometryMethod.setObjectName("ComboBoxThermometryMethod")

        form_layout.addRow("Method", self.comboBoxThermometryMethod)

    def connect_widgets(self):
        pass

class BarmometryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent = parent

        self.setupUI()
        self.connect_widgets()

    def setupUI(self):
        self.setObjectName("tabBarometry")

        tab_layout = QVBoxLayout(self)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setObjectName("verticalLayout_67")

        tab_scroll_area = QScrollArea(self)
        tab_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        tab_scroll_area.setFrameShadow(QFrame.Shadow.Plain)
        tab_scroll_area.setWidgetResizable(True)
        tab_scroll_area.setObjectName("scrollAreaBarometry")

        tab_scroll_area_contents = QWidget()
        tab_scroll_area_contents.setGeometry(QRect(0, 0, 151, 38))
        tab_scroll_area_contents.setObjectName("scrollAreaWidgetContentsBarometry")

        form_layout = QFormLayout(tab_scroll_area_contents)
        form_layout.setContentsMargins(6, 6, 6, 6)
        form_layout.setObjectName("formLayout_17")

        self.comboBoxBarometryMethod = QComboBox(tab_scroll_area_contents)
        self.comboBoxBarometryMethod.setMaximumSize(QSize(200, 16777215))
        self.comboBoxBarometryMethod.setObjectName("ComboBoxBarometryMethod")

        form_layout.addRow("Method", self.comboBoxBarometryMethod)

        tab_scroll_area.setWidget(tab_scroll_area_contents)
        tab_layout.addWidget(tab_scroll_area)

    def connect_widgets(self):
        pass
