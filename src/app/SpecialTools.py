import numpy as np
import pandas as pd
import scipy.odr as odr

from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import ( 
        QMessageBox, QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QScrollArea, QToolButton,
        QTableWidget, QTableWidgetItem, QSpacerItem, QFrame, QSizePolicy, QHeaderView, QTabWidget,
        QFormLayout, QComboBox, QLabel, QCheckBox, QGridLayout, QPushButton
    )
from src.common.CustomWidgets import CustomPage, CustomToolButton, CustomLineEdit
from src.app.config import ICONPATH
#from src.common.geochronology import 

class SpecialPage(CustomPage):
    def __init__(self, page_index, dock=None):
        if dock is None:
            return
        super().__init__(dock)

        self.dock = dock
        self.page_index = page_index

        self.setupUI()
        self.connect_widgets()

        specfun = SpecialFunctions(self.dock)

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

        self.dating = DatingTab(parent=self)
        self.special_fcns.addTab(self.dating, "Dating")

        self.diffusion = DiffusionTab(parent=self)
        self.special_fcns.addTab(self.diffusion, "Diffusion")

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

class DatingTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent = parent

        self.setupUI()
        self.connect_widgets()

    def setupUI(self):
        self.setObjectName("tabDating")

        self.setObjectName("tabDating")

        tab_layout = QVBoxLayout(self)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        tab_scroll_area = QScrollArea(self)
        tab_scroll_area.setWidgetResizable(True)

        tab_scroll_area_contents = QWidget()
        tab_scroll_area_contents.setGeometry(QRect(0, 0, 260, 303))

        scroll_area_layout = QVBoxLayout(tab_scroll_area_contents)
        scroll_area_layout.setContentsMargins(6, 6, 6, 6)
        scroll_area_layout.setObjectName("verticalLayout_58")

        self.verticalLayoutDatingParams = QVBoxLayout()
        self.verticalLayoutDatingParams.setObjectName("verticalLayoutDatingParams")

        self.formLayoutDatingMethod = QFormLayout()
        self.formLayoutDatingMethod.setObjectName("formLayoutDatingMethod")

        self.labelDatingMethod = QLabel(tab_scroll_area_contents)
        self.labelDatingMethod.setObjectName("labelDatingMethod")

        self.formLayoutDatingMethod.setWidget(0, QFormLayout.ItemRole.LabelRole, self.labelDatingMethod)

        self.comboBoxDatingMethod = QComboBox(tab_scroll_area_contents)
        self.comboBoxDatingMethod.setMaximumSize(QSize(200, 16777215))
        self.comboBoxDatingMethod.setObjectName("comboBoxDatingMethod")

        self.formLayoutDatingMethod.setWidget(0, QFormLayout.ItemRole.FieldRole, self.comboBoxDatingMethod)

        self.labelComputeRatios = QLabel(tab_scroll_area_contents)
        self.labelComputeRatios.setObjectName("labelComputeRatios")

        self.formLayoutDatingMethod.setWidget(1, QFormLayout.ItemRole.LabelRole, self.labelComputeRatios)

        self.checkBoxComputeRatios = QCheckBox(tab_scroll_area_contents)
        self.checkBoxComputeRatios.setChecked(True)
        self.checkBoxComputeRatios.setObjectName("checkBoxComputeRatios")

        self.formLayoutDatingMethod.setWidget(1, QFormLayout.ItemRole.FieldRole, self.checkBoxComputeRatios)

        self.verticalLayoutDatingParams.addLayout(self.formLayoutDatingMethod)

        self.gridLayoutDatingParams = QGridLayout()
        self.gridLayoutDatingParams.setObjectName("gridLayoutDatingParams")

        self.comboBoxIsotopeAgeFieldType3 = QComboBox(tab_scroll_area_contents)
        self.comboBoxIsotopeAgeFieldType3.setMaximumSize(QSize(125, 16777215))
        self.comboBoxIsotopeAgeFieldType3.setObjectName("comboBoxIsotopeAgeFieldType3")

        self.gridLayoutDatingParams.addWidget(self.comboBoxIsotopeAgeFieldType3, 2, 1, 1, 1)

        self.comboBoxIsotopeAgeField2 = QComboBox(tab_scroll_area_contents)
        self.comboBoxIsotopeAgeField2.setObjectName("comboBoxIsotopeAgeField2")

        self.gridLayoutDatingParams.addWidget(self.comboBoxIsotopeAgeField2, 1, 2, 1, 1)

        self.comboBoxIsotopeAgeField3 = QComboBox(tab_scroll_area_contents)
        self.comboBoxIsotopeAgeField3.setObjectName("comboBoxIsotopeAgeField3")
        self.gridLayoutDatingParams.addWidget(self.comboBoxIsotopeAgeField3, 2, 2, 1, 1)

        self.comboBoxIsotopeAgeFieldType2 = QComboBox(tab_scroll_area_contents)
        self.comboBoxIsotopeAgeFieldType2.setMaximumSize(QSize(125, 16777215))
        self.comboBoxIsotopeAgeFieldType2.setObjectName("comboBoxIsotopeAgeFieldType2")

        self.gridLayoutDatingParams.addWidget(self.comboBoxIsotopeAgeFieldType2, 1, 1, 1, 1)

        self.comboBoxIsotopeAgeField1 = QComboBox(tab_scroll_area_contents)
        self.comboBoxIsotopeAgeField1.setObjectName("comboBoxIsotopeAgeField1")

        self.gridLayoutDatingParams.addWidget(self.comboBoxIsotopeAgeField1, 0, 2, 1, 1)

        self.labelIsotope2 = QLabel(tab_scroll_area_contents)
        self.labelIsotope2.setObjectName("labelIsotope2")

        self.gridLayoutDatingParams.addWidget(self.labelIsotope2, 1, 0, 1, 1)

        self.labelIsotope1 = QLabel(tab_scroll_area_contents)
        self.labelIsotope1.setObjectName("labelIsotope1")

        self.gridLayoutDatingParams.addWidget(self.labelIsotope1, 0, 0, 1, 1)

        self.comboBoxIsotopeAgeFieldType1 = QComboBox(tab_scroll_area_contents)
        self.comboBoxIsotopeAgeFieldType1.setMaximumSize(QSize(125, 16777215))
        self.comboBoxIsotopeAgeFieldType1.setFont(font)
        self.comboBoxIsotopeAgeFieldType1.setObjectName("comboBoxIsotopeAgeFieldType1")

        self.gridLayoutDatingParams.addWidget(self.comboBoxIsotopeAgeFieldType1, 0, 1, 1, 1)

        self.labelDecayConstant = QLabel(tab_scroll_area_contents)
        self.labelDecayConstant.setWordWrap(True)
        self.labelDecayConstant.setObjectName("labelDecayConstant")

        self.gridLayoutDatingParams.addWidget(self.labelDecayConstant, 3, 0, 1, 1)

        self.lineEditDecayConstant = CustomLineEdit(tab_scroll_area_contents)
        self.lineEditDecayConstant.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditDecayConstant.setObjectName("lineEditDecayConstant")

        self.gridLayoutDatingParams.addWidget(self.lineEditDecayConstant, 3, 1, 1, 1)

        self.labelIsotope3 = QLabel(tab_scroll_area_contents)
        self.labelIsotope3.setObjectName("labelIsotope3")

        self.gridLayoutDatingParams.addWidget(self.labelIsotope3, 2, 0, 1, 1)

        self.lineEditDecayConstantUncertainty = CustomLineEdit(tab_scroll_area_contents)
        self.lineEditDecayConstantUncertainty.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditDecayConstantUncertainty.setObjectName("lineEditDecayConstantUncertainty")

        self.gridLayoutDatingParams.addWidget(self.lineEditDecayConstantUncertainty, 3, 2, 1, 1)
        self.verticalLayoutDatingParams.addLayout(self.gridLayoutDatingParams)

        self.pushButtonComputeAge = QPushButton(tab_scroll_area_contents)
        self.pushButtonComputeAge.setObjectName("pushButtonComputeAge")

        self.verticalLayoutDatingParams.addWidget(self.pushButtonComputeAge)
        scroll_area_layout.addLayout(self.verticalLayoutDatingParams)

        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        scroll_area_layout.addItem(spacer)

        tab_scroll_area.setWidget(tab_scroll_area_contents)
        tab_layout.addWidget(tab_scroll_area)

    def connect_widgets(self):
        # Dating
        self.comboBoxIsotopeAgeFieldType1.activated.connect(lambda: self.parent.update_field_combobox(self.comboBoxIsotopeAgeFieldType1, self.comboBoxIsotopeAgeField1))
        self.comboBoxIsotopeAgeFieldType2.activated.connect(lambda: self.parent.update_field_combobox(self.comboBoxIsotopeAgeFieldType2, self.comboBoxIsotopeAgeField2))
        self.comboBoxIsotopeAgeFieldType3.activated.connect(lambda: self.parent.update_field_combobox(self.comboBoxIsotopeAgeFieldType3, self.comboBoxIsotopeAgeField3))

        self.comboBoxDatingMethod.activated.connect(specfun.callback_dating_method)
        self.checkBoxComputeRatios.stateChanged.connect(specfun.callback_dating_ratios)
        self.pushButtonComputeAge.clicked.connect(specfun.compute_date_map)



class DiffusionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent = parent

        self.setupUI()

    def setupUI(self):
        self.setObjectName("tabDiffusion")

        self.setObjectName("tabDiffusion")
        tab_layout = QVBoxLayout(self)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        tab_scroll_area = QScrollArea(self)
        tab_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        tab_scroll_area.setFrameShadow(QFrame.Shadow.Plain)
        tab_scroll_area.setWidgetResizable(True)
        tab_scroll_area.setObjectName("scrollAreaDiffusion")

        tab_scroll_area_contents = QWidget()
        tab_scroll_area_contents.setGeometry(QRect(0, 0, 236, 234))
        tab_scroll_area_contents.setObjectName("scrollAreaWidgetContentsDiffusion")

        self.verticalLayout_65 = QVBoxLayout(tab_scroll_area_contents)
        self.verticalLayout_65.setContentsMargins(6, 6, 6, 6)
        self.verticalLayout_65.setObjectName("verticalLayout_65")
        self.formLayoutDiffusion = QFormLayout()
        self.formLayoutDiffusion.setObjectName("formLayoutDiffusion")
        self.labelDimensionality = QLabel(tab_scroll_area_contents)
        self.labelDimensionality.setObjectName("labelDimensionality")
        self.formLayoutDiffusion.setWidget(2, QFormLayout.ItemRole.LabelRole, self.labelDimensionality)
        self.comboBoxDimensionality = QComboBox(tab_scroll_area_contents)
        self.comboBoxDimensionality.setMaximumSize(QSize(200, 16777215))
        self.comboBoxDimensionality.setObjectName("comboBoxDimensionality")
        self.comboBoxDimensionality.addItem("")
        self.comboBoxDimensionality.addItem("")
        self.formLayoutDiffusion.setWidget(2, QFormLayout.ItemRole.FieldRole, self.comboBoxDimensionality)
        self.labelDatingDiffusionMethod = QLabel(tab_scroll_area_contents)
        self.labelDatingDiffusionMethod.setObjectName("labelDatingDiffusionMethod")
        self.formLayoutDiffusion.setWidget(3, QFormLayout.ItemRole.LabelRole, self.labelDatingDiffusionMethod)
        self.ComboBoxDiffusionMethod = QComboBox(tab_scroll_area_contents)
        self.ComboBoxDiffusionMethod.setMaximumSize(QSize(200, 16777215))
        self.ComboBoxDiffusionMethod.setObjectName("ComboBoxDiffusionMethod")
        self.formLayoutDiffusion.setWidget(3, QFormLayout.ItemRole.FieldRole, self.ComboBoxDiffusionMethod)
        self.labelRegion = QLabel(tab_scroll_area_contents)
        self.labelRegion.setObjectName("labelRegion")
        self.formLayoutDiffusion.setWidget(0, QFormLayout.ItemRole.LabelRole, self.labelRegion)
        self.comboBoxRegion = QComboBox(tab_scroll_area_contents)
        self.comboBoxRegion.setMaximumSize(QSize(200, 16777215))
        self.comboBoxRegion.setObjectName("comboBoxRegion")
        self.formLayoutDiffusion.setWidget(0, QFormLayout.ItemRole.FieldRole, self.comboBoxRegion)
        self.labelDiffusionProfile = QLabel(tab_scroll_area_contents)
        self.labelDiffusionProfile.setObjectName("labelDiffusionProfile")
        self.formLayoutDiffusion.setWidget(1, QFormLayout.ItemRole.LabelRole, self.labelDiffusionProfile)
        self.comboBoxDiffusionProfile = QComboBox(tab_scroll_area_contents)
        self.comboBoxDiffusionProfile.setMaximumSize(QSize(200, 16777215))
        self.comboBoxDiffusionProfile.setObjectName("comboBoxDiffusionProfile")
        self.formLayoutDiffusion.setWidget(1, QFormLayout.ItemRole.FieldRole, self.comboBoxDiffusionProfile)
        self.verticalLayout_65.addLayout(self.formLayoutDiffusion)
        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.tableWidgetDiffusionConstants = QTableWidget(tab_scroll_area_contents)
        self.tableWidgetDiffusionConstants.setObjectName("tableWidgetDiffusionConstants")
        self.tableWidgetDiffusionConstants.setColumnCount(3)
        self.tableWidgetDiffusionConstants.setRowCount(0)
        item = QTableWidgetItem()
        self.tableWidgetDiffusionConstants.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem()
        self.tableWidgetDiffusionConstants.setHorizontalHeaderItem(1, item)
        item = QTableWidgetItem()
        self.tableWidgetDiffusionConstants.setHorizontalHeaderItem(2, item)
        self.tableWidgetDiffusionConstants.horizontalHeader().setDefaultSectionSize(79)
        self.horizontalLayout_8.addWidget(self.tableWidgetDiffusionConstants)
        self.verticalLayout_10 = QVBoxLayout()
        self.verticalLayout_10.setObjectName("verticalLayout_10")

        self.toolButtonDiffusionLoad = CustomToolButton(
            text="",
            light_icon_unchecked="icon-zoning-64.svg",
            parent=tab_scroll_area_contents,
        )
        self.toolButtonDiffusionLoad.setObjectName("toolButtonDiffusionLoad")
        self.verticalLayout_10.addWidget(self.toolButtonDiffusionLoad)

        spacerItem16 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.verticalLayout_10.addItem(spacerItem16)

        self.horizontalLayout_8.addLayout(self.verticalLayout_10)
        self.verticalLayout_65.addLayout(self.horizontalLayout_8)
        tab_scroll_area.setWidget(tab_scroll_area_contents)
        tab_layout.addWidget(tab_scroll_area)
