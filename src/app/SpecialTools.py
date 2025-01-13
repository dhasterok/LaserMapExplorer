import numpy as np
import pandas as pd
import scipy.odr as odr

from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import ( 
        QMessageBox, QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QScrollArea, QToolButton,
        QTableWidget, QTableWidgetItem, QSpacerItem, QFrame, QSizePolicy, QHeaderView, QTabWidget,
        QFormLayout, QComboBox, QLabel, QCheckBox, QGridLayout, QPushButton
    )
from src.common.CustomWidgets import CustomLineEdit


class SpecialPage(QWidget):
    def __init__(self, page_index, parent=None):
        super().__init__(parent)

        if parent is None:
            return

        self.parent = parent

        font = QFont()
        font.setPointSize(11)
        font.setStyleStrategy(QFont.PreferDefault)

        self.setGeometry(QRect(0, 0, 300, 321))
        self.setObjectName("PTtPage")
        self.verticalLayout_69 = QVBoxLayout(self)
        self.verticalLayout_69.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_69.setObjectName("verticalLayout_69")
        self.scrollAreaSpecial = QScrollArea(self)
        self.scrollAreaSpecial.setFont(font)
        self.scrollAreaSpecial.setFrameShape(QFrame.NoFrame)
        self.scrollAreaSpecial.setFrameShadow(QFrame.Plain)
        self.scrollAreaSpecial.setWidgetResizable(True)
        self.scrollAreaSpecial.setObjectName("scrollAreaSpecial")
        self.scrollAreaWidgetContentsSpecial = QWidget()
        self.scrollAreaWidgetContentsSpecial.setGeometry(QRect(0, 0, 300, 321))
        self.scrollAreaWidgetContentsSpecial.setObjectName("scrollAreaWidgetContentsSpecial")
        self.verticalLayout_64 = QVBoxLayout(self.scrollAreaWidgetContentsSpecial)
        self.verticalLayout_64.setContentsMargins(6, 6, 6, 6)
        self.verticalLayout_64.setObjectName("verticalLayout_64")

        self.tabWidgetSpecialFcn = QTabWidget(self.scrollAreaWidgetContentsSpecial)
        self.tabWidgetSpecialFcn.setMaximumSize(QSize(300, 16777215))
        self.tabWidgetSpecialFcn.setFont(font)
        self.tabWidgetSpecialFcn.setObjectName("tabWidgetSpecialFcn")
        self.tabThermometry = QWidget()
        self.tabThermometry.setObjectName("tabThermometry")
        self.formLayout_16 = QFormLayout(self.tabThermometry)
        self.formLayout_16.setContentsMargins(6, 6, 6, 6)
        self.formLayout_16.setObjectName("formLayout_16")
        self.labelThermometryMethod = QLabel(self.tabThermometry)
        self.labelThermometryMethod.setObjectName("labelThermometryMethod")
        self.formLayout_16.setWidget(0, QFormLayout.LabelRole, self.labelThermometryMethod)
        self.ComboBoxThermometryMethod = QComboBox(self.tabThermometry)
        self.ComboBoxThermometryMethod.setMaximumSize(QSize(200, 16777215))
        self.ComboBoxThermometryMethod.setObjectName("ComboBoxThermometryMethod")
        self.formLayout_16.setWidget(0, QFormLayout.FieldRole, self.ComboBoxThermometryMethod)
        self.tabWidgetSpecialFcn.addTab(self.tabThermometry, "")
        self.tabBarometry = QWidget()
        self.tabBarometry.setObjectName("tabBarometry")
        self.verticalLayout_67 = QVBoxLayout(self.tabBarometry)
        self.verticalLayout_67.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_67.setObjectName("verticalLayout_67")
        self.scrollAreaBarometry = QScrollArea(self.tabBarometry)
        self.scrollAreaBarometry.setFrameShape(QFrame.NoFrame)
        self.scrollAreaBarometry.setFrameShadow(QFrame.Plain)
        self.scrollAreaBarometry.setWidgetResizable(True)
        self.scrollAreaBarometry.setObjectName("scrollAreaBarometry")
        self.scrollAreaWidgetContentsBarometry = QWidget()
        self.scrollAreaWidgetContentsBarometry.setGeometry(QRect(0, 0, 151, 38))
        self.scrollAreaWidgetContentsBarometry.setObjectName("scrollAreaWidgetContentsBarometry")
        self.formLayout_17 = QFormLayout(self.scrollAreaWidgetContentsBarometry)
        self.formLayout_17.setContentsMargins(6, 6, 6, 6)
        self.formLayout_17.setObjectName("formLayout_17")
        self.labelBarometryMethod = QLabel(self.scrollAreaWidgetContentsBarometry)
        self.labelBarometryMethod.setObjectName("labelBarometryMethod")
        self.formLayout_17.setWidget(0, QFormLayout.LabelRole, self.labelBarometryMethod)
        self.ComboBoxBarometryMethod = QComboBox(self.scrollAreaWidgetContentsBarometry)
        self.ComboBoxBarometryMethod.setMaximumSize(QSize(200, 16777215))
        self.ComboBoxBarometryMethod.setObjectName("ComboBoxBarometryMethod")
        self.formLayout_17.setWidget(0, QFormLayout.FieldRole, self.ComboBoxBarometryMethod)
        self.scrollAreaBarometry.setWidget(self.scrollAreaWidgetContentsBarometry)
        self.verticalLayout_67.addWidget(self.scrollAreaBarometry)
        self.tabWidgetSpecialFcn.addTab(self.tabBarometry, "")
        self.tabDating = QWidget()
        self.tabDating.setObjectName("tabDating")
        self.verticalLayout_68 = QVBoxLayout(self.tabDating)
        self.verticalLayout_68.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_68.setObjectName("verticalLayout_68")
        self.scrollAreaDating = QScrollArea(self.tabDating)
        self.scrollAreaDating.setWidgetResizable(True)
        self.scrollAreaDating.setObjectName("scrollAreaDating")
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 260, 303))
        self.scrollAreaWidgetContents_2.setObjectName("scrollAreaWidgetContents_2")
        self.verticalLayout_58 = QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout_58.setContentsMargins(6, 6, 6, 6)
        self.verticalLayout_58.setObjectName("verticalLayout_58")
        self.verticalLayoutDatingParams = QVBoxLayout()
        self.verticalLayoutDatingParams.setObjectName("verticalLayoutDatingParams")
        self.formLayoutDatingMethod = QFormLayout()
        self.formLayoutDatingMethod.setObjectName("formLayoutDatingMethod")
        self.labelDatingMethod = QLabel(self.scrollAreaWidgetContents_2)
        self.labelDatingMethod.setObjectName("labelDatingMethod")
        self.formLayoutDatingMethod.setWidget(0, QFormLayout.LabelRole, self.labelDatingMethod)
        self.comboBoxDatingMethod = QComboBox(self.scrollAreaWidgetContents_2)
        self.comboBoxDatingMethod.setMaximumSize(QSize(200, 16777215))
        self.comboBoxDatingMethod.setObjectName("comboBoxDatingMethod")
        self.comboBoxDatingMethod.addItem("")
        self.comboBoxDatingMethod.addItem("")
        self.formLayoutDatingMethod.setWidget(0, QFormLayout.FieldRole, self.comboBoxDatingMethod)
        self.labelComputeRatios = QLabel(self.scrollAreaWidgetContents_2)
        self.labelComputeRatios.setObjectName("labelComputeRatios")
        self.formLayoutDatingMethod.setWidget(1, QFormLayout.LabelRole, self.labelComputeRatios)
        self.checkBoxComputeRatios = QCheckBox(self.scrollAreaWidgetContents_2)
        self.checkBoxComputeRatios.setChecked(True)
        self.checkBoxComputeRatios.setObjectName("checkBoxComputeRatios")
        self.formLayoutDatingMethod.setWidget(1, QFormLayout.FieldRole, self.checkBoxComputeRatios)
        self.verticalLayoutDatingParams.addLayout(self.formLayoutDatingMethod)
        self.gridLayoutDatingParams = QGridLayout()
        self.gridLayoutDatingParams.setObjectName("gridLayoutDatingParams")
        self.comboBoxIsotopeAgeFieldType3 = QComboBox(self.scrollAreaWidgetContents_2)
        self.comboBoxIsotopeAgeFieldType3.setMaximumSize(QSize(125, 16777215))
        self.comboBoxIsotopeAgeFieldType3.setFont(font)
        self.comboBoxIsotopeAgeFieldType3.setObjectName("comboBoxIsotopeAgeFieldType3")
        self.comboBoxIsotopeAgeFieldType3.addItem("")
        self.comboBoxIsotopeAgeFieldType3.addItem("")
        self.gridLayoutDatingParams.addWidget(self.comboBoxIsotopeAgeFieldType3, 2, 1, 1, 1)

        self.comboBoxIsotopeAgeField2 = QComboBox(self.scrollAreaWidgetContents_2)
        self.comboBoxIsotopeAgeField2.setFont(font)
        self.comboBoxIsotopeAgeField2.setCurrentText("")
        self.comboBoxIsotopeAgeField2.setObjectName("comboBoxIsotopeAgeField2")
        self.gridLayoutDatingParams.addWidget(self.comboBoxIsotopeAgeField2, 1, 2, 1, 1)

        self.comboBoxIsotopeAgeField3 = QComboBox(self.scrollAreaWidgetContents_2)
        self.comboBoxIsotopeAgeField3.setFont(font)
        self.comboBoxIsotopeAgeField3.setCurrentText("")
        self.comboBoxIsotopeAgeField3.setObjectName("comboBoxIsotopeAgeField3")
        self.gridLayoutDatingParams.addWidget(self.comboBoxIsotopeAgeField3, 2, 2, 1, 1)

        self.comboBoxIsotopeAgeFieldType2 = QComboBox(self.scrollAreaWidgetContents_2)
        self.comboBoxIsotopeAgeFieldType2.setMaximumSize(QSize(125, 16777215))
        self.comboBoxIsotopeAgeFieldType2.setFont(font)
        self.comboBoxIsotopeAgeFieldType2.setObjectName("comboBoxIsotopeAgeFieldType2")
        self.comboBoxIsotopeAgeFieldType2.addItem("")
        self.comboBoxIsotopeAgeFieldType2.addItem("")
        self.gridLayoutDatingParams.addWidget(self.comboBoxIsotopeAgeFieldType2, 1, 1, 1, 1)

        self.comboBoxIsotopeAgeField1 = QComboBox(self.scrollAreaWidgetContents_2)
        self.comboBoxIsotopeAgeField1.setFont(font)
        self.comboBoxIsotopeAgeField1.setCurrentText("")
        self.comboBoxIsotopeAgeField1.setObjectName("comboBoxIsotopeAgeField1")
        self.gridLayoutDatingParams.addWidget(self.comboBoxIsotopeAgeField1, 0, 2, 1, 1)
        self.labelIsotope2 = QLabel(self.scrollAreaWidgetContents_2)
        self.labelIsotope2.setObjectName("labelIsotope2")
        self.gridLayoutDatingParams.addWidget(self.labelIsotope2, 1, 0, 1, 1)
        self.labelIsotope1 = QLabel(self.scrollAreaWidgetContents_2)
        self.labelIsotope1.setObjectName("labelIsotope1")
        self.gridLayoutDatingParams.addWidget(self.labelIsotope1, 0, 0, 1, 1)

        self.comboBoxIsotopeAgeFieldType1 = QComboBox(self.scrollAreaWidgetContents_2)
        self.comboBoxIsotopeAgeFieldType1.setMaximumSize(QSize(125, 16777215))
        self.comboBoxIsotopeAgeFieldType1.setFont(font)
        self.comboBoxIsotopeAgeFieldType1.setObjectName("comboBoxIsotopeAgeFieldType1")
        self.comboBoxIsotopeAgeFieldType1.addItem("")
        self.comboBoxIsotopeAgeFieldType1.addItem("")
        self.gridLayoutDatingParams.addWidget(self.comboBoxIsotopeAgeFieldType1, 0, 1, 1, 1)
        self.labelDecayConstant = QLabel(self.scrollAreaWidgetContents_2)
        self.labelDecayConstant.setWordWrap(True)
        self.labelDecayConstant.setObjectName("labelDecayConstant")
        self.gridLayoutDatingParams.addWidget(self.labelDecayConstant, 3, 0, 1, 1)
        self.lineEditDecayConstant = CustomLineEdit(self.scrollAreaWidgetContents_2)
        self.lineEditDecayConstant.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.lineEditDecayConstant.setObjectName("lineEditDecayConstant")
        self.gridLayoutDatingParams.addWidget(self.lineEditDecayConstant, 3, 1, 1, 1)
        self.labelIsotope3 = QLabel(self.scrollAreaWidgetContents_2)
        self.labelIsotope3.setObjectName("labelIsotope3")
        self.gridLayoutDatingParams.addWidget(self.labelIsotope3, 2, 0, 1, 1)
        self.lineEditDecayConstantUncertainty = CustomLineEdit(self.scrollAreaWidgetContents_2)
        self.lineEditDecayConstantUncertainty.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)
        self.lineEditDecayConstantUncertainty.setObjectName("lineEditDecayConstantUncertainty")
        self.gridLayoutDatingParams.addWidget(self.lineEditDecayConstantUncertainty, 3, 2, 1, 1)
        self.verticalLayoutDatingParams.addLayout(self.gridLayoutDatingParams)
        self.pushButtonComputeAge = QPushButton(self.scrollAreaWidgetContents_2)
        self.pushButtonComputeAge.setObjectName("pushButtonComputeAge")
        self.verticalLayoutDatingParams.addWidget(self.pushButtonComputeAge)
        self.verticalLayout_58.addLayout(self.verticalLayoutDatingParams)
        spacerItem15 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout_58.addItem(spacerItem15)
        self.scrollAreaDating.setWidget(self.scrollAreaWidgetContents_2)
        self.verticalLayout_68.addWidget(self.scrollAreaDating)
        self.tabWidgetSpecialFcn.addTab(self.tabDating, "")
        self.tabDiffusion = QWidget()
        self.tabDiffusion.setObjectName("tabDiffusion")
        self.verticalLayout_66 = QVBoxLayout(self.tabDiffusion)
        self.verticalLayout_66.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_66.setObjectName("verticalLayout_66")
        self.scrollAreaDiffusion = QScrollArea(self.tabDiffusion)
        self.scrollAreaDiffusion.setFrameShape(QFrame.NoFrame)
        self.scrollAreaDiffusion.setFrameShadow(QFrame.Plain)
        self.scrollAreaDiffusion.setWidgetResizable(True)
        self.scrollAreaDiffusion.setObjectName("scrollAreaDiffusion")
        self.scrollAreaWidgetContentsDiffusion = QWidget()
        self.scrollAreaWidgetContentsDiffusion.setGeometry(QRect(0, 0, 236, 234))
        self.scrollAreaWidgetContentsDiffusion.setObjectName("scrollAreaWidgetContentsDiffusion")
        self.verticalLayout_65 = QVBoxLayout(self.scrollAreaWidgetContentsDiffusion)
        self.verticalLayout_65.setContentsMargins(6, 6, 6, 6)
        self.verticalLayout_65.setObjectName("verticalLayout_65")
        self.formLayoutDiffusion = QFormLayout()
        self.formLayoutDiffusion.setObjectName("formLayoutDiffusion")
        self.labelDimensionality = QLabel(self.scrollAreaWidgetContentsDiffusion)
        self.labelDimensionality.setObjectName("labelDimensionality")
        self.formLayoutDiffusion.setWidget(2, QFormLayout.LabelRole, self.labelDimensionality)
        self.comboBoxDimensionality = QComboBox(self.scrollAreaWidgetContentsDiffusion)
        self.comboBoxDimensionality.setMaximumSize(QSize(200, 16777215))
        self.comboBoxDimensionality.setObjectName("comboBoxDimensionality")
        self.comboBoxDimensionality.addItem("")
        self.comboBoxDimensionality.addItem("")
        self.formLayoutDiffusion.setWidget(2, QFormLayout.FieldRole, self.comboBoxDimensionality)
        self.labelDatingDiffusionMethod = QLabel(self.scrollAreaWidgetContentsDiffusion)
        self.labelDatingDiffusionMethod.setObjectName("labelDatingDiffusionMethod")
        self.formLayoutDiffusion.setWidget(3, QFormLayout.LabelRole, self.labelDatingDiffusionMethod)
        self.ComboBoxDiffusionMethod = QComboBox(self.scrollAreaWidgetContentsDiffusion)
        self.ComboBoxDiffusionMethod.setMaximumSize(QSize(200, 16777215))
        self.ComboBoxDiffusionMethod.setObjectName("ComboBoxDiffusionMethod")
        self.formLayoutDiffusion.setWidget(3, QFormLayout.FieldRole, self.ComboBoxDiffusionMethod)
        self.labelRegion = QLabel(self.scrollAreaWidgetContentsDiffusion)
        self.labelRegion.setObjectName("labelRegion")
        self.formLayoutDiffusion.setWidget(0, QFormLayout.LabelRole, self.labelRegion)
        self.comboBoxRegion = QComboBox(self.scrollAreaWidgetContentsDiffusion)
        self.comboBoxRegion.setMaximumSize(QSize(200, 16777215))
        self.comboBoxRegion.setObjectName("comboBoxRegion")
        self.formLayoutDiffusion.setWidget(0, QFormLayout.FieldRole, self.comboBoxRegion)
        self.labelDiffusionProfile = QLabel(self.scrollAreaWidgetContentsDiffusion)
        self.labelDiffusionProfile.setObjectName("labelDiffusionProfile")
        self.formLayoutDiffusion.setWidget(1, QFormLayout.LabelRole, self.labelDiffusionProfile)
        self.comboBoxDiffusionProfile = QComboBox(self.scrollAreaWidgetContentsDiffusion)
        self.comboBoxDiffusionProfile.setMaximumSize(QSize(200, 16777215))
        self.comboBoxDiffusionProfile.setObjectName("comboBoxDiffusionProfile")
        self.formLayoutDiffusion.setWidget(1, QFormLayout.FieldRole, self.comboBoxDiffusionProfile)
        self.verticalLayout_65.addLayout(self.formLayoutDiffusion)
        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.tableWidgetDiffusionConstants = QTableWidget(self.scrollAreaWidgetContentsDiffusion)
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

        self.toolButtonDiffusionLoad = QToolButton(self.scrollAreaWidgetContentsDiffusion)
        self.toolButtonDiffusionLoad.setMinimumSize(QSize(32, 32))
        self.toolButtonDiffusionLoad.setMaximumSize(QSize(32, 32))
        self.toolButtonDiffusionLoad.setFont(font)
        diffusion_icon = QIcon(":resources/icons/icon-zoning-64.svg")
        self.toolButtonDiffusionLoad.setIcon(diffusion_icon)
        self.toolButtonDiffusionLoad.setIconSize(QSize(24, 24))
        self.toolButtonDiffusionLoad.setObjectName("toolButtonDiffusionLoad")
        self.verticalLayout_10.addWidget(self.toolButtonDiffusionLoad)

        spacerItem16 = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.verticalLayout_10.addItem(spacerItem16)

        self.horizontalLayout_8.addLayout(self.verticalLayout_10)
        self.verticalLayout_65.addLayout(self.horizontalLayout_8)
        self.scrollAreaDiffusion.setWidget(self.scrollAreaWidgetContentsDiffusion)
        self.verticalLayout_66.addWidget(self.scrollAreaDiffusion)
        self.tabWidgetSpecialFcn.addTab(self.tabDiffusion, "")
        self.verticalLayout_64.addWidget(self.tabWidgetSpecialFcn)
        self.scrollAreaSpecial.setWidget(self.scrollAreaWidgetContentsSpecial)
        self.verticalLayout_69.addWidget(self.scrollAreaSpecial)
        page_icon = QIcon(":/resources/icons/icon-zoning-64.svg")

        self.parent.toolBox.insertItem(page_index+1, self, page_icon, "P-T-t Functions")

        specfun = SpecialFunctions(self.parent)

        # Dating
        self.comboBoxIsotopeAgeFieldType1.activated.connect(lambda: self.parent.update_field_combobox(self.comboBoxIsotopeAgeFieldType1, self.comboBoxIsotopeAgeField1))
        self.comboBoxIsotopeAgeFieldType2.activated.connect(lambda: self.parent.update_field_combobox(self.comboBoxIsotopeAgeFieldType2, self.comboBoxIsotopeAgeField2))
        self.comboBoxIsotopeAgeFieldType3.activated.connect(lambda: self.parent.update_field_combobox(self.comboBoxIsotopeAgeFieldType3, self.comboBoxIsotopeAgeField3))

        self.comboBoxDatingMethod.activated.connect(specfun.callback_dating_method)
        self.checkBoxComputeRatios.stateChanged.connect(specfun.callback_dating_ratios)
        self.pushButtonComputeAge.clicked.connect(specfun.compute_date_map)


class SpecialFunctions():
    def __init__(self, parent=None):

        if parent is None:
            return
        self.parent = parent



    def callback_dating_ratios(self):
        self.callback_dating_method()

    def callback_dating_method(self):
        """Updates isotopes and decay constants when dating method changes.

        Default decay constants are as follows:
        * Lu-Hf : :math:`1.867 \pm 0.008 \times 10^{-5}` Ma (Sonderlund et al., EPSL, 2004, https://doi.org/10.1016/S0012-821X(04)00012-3)
        * Re-Os : :math:`1.666 \pm 0.005 \times 10^{-5}` Ma (Selby et al., GCA, 2007, https://doi.org/10.1016/j.gca.2007.01.008)
        """
        data = self.parent.data[self.parent.sample_id].processed_data

        match self.parent.comboBoxDatingMethod.currentText():
            case "Lu-Hf":
                if self.parent.checkBoxComputeRatios.isChecked():
                    # get list of analytes
                    analyte_list = data.get_attribute('data_type','analyte')

                    self.parent.labelIsotope1.setText("Lu175")
                    self.parent.comboBoxIsotopeAgeFieldType1.setCurrentText("Analyte")
                    if ("Lu175" in analyte_list) and (self.parent.parent.comboBoxIsotopeAgeFieldType1.currentText() == "Analyte"):
                        self.parent.comboBoxIsotopeAgeField1.setCurrentText("Lu175")

                    self.parent.labelIsotope2.setText("Hf176")
                    self.parent.comboBoxIsotopeAgeFieldType2.setCurrentText("Analyte")
                    if ("Hf176" in analyte_list) and (self.parent.comboBoxIsotopeAgeFieldType2.currentText() == "Analyte"):
                        self.parent.comboBoxIsotopeAgeField2.setCurrentText("Hf176")

                    self.parent.labelIsotope3.setEnabled(True)
                    self.parent.comboBoxIsotopeAgeField3.setEnabled(True)
                    self.parent.labelIsotope3.setText("Hf178")
                    self.parent.comboBoxIsotopeAgeFieldType3.setCurrentText("Analyte")
                    if ("Hf178" in analyte_list) and (self.parent.comboBoxIsotopeAgeFieldType3.currentText() == "Analyte"):
                        self.parent.comboBoxIsotopeAgeField3.setCurrentText("Hf178")
                else:
                    # get list of ratios
                    ratio_list = data.get_attribute('data_type','ratio')

                    self.parent.labelIsotope1.setText("Hf176/Hf178")
                    self.parent.comboBoxIsotopeAgeFieldType1.setCurrentText("Ratio")
                    if ("Hf176/Hf178" in ratio_list) and (self.parent.comboBoxIsotopeAgeFieldType1.currentText() == "Ratio"):
                        self.parent.comboBoxIsotopeAgeField1.setCurrentText("Hf176/Hf178")

                    self.parent.labelIsotope2.setText("Lu175/Hf178")
                    self.parent.comboBoxIsotopeAgeFieldType2.currentText("Ratio")
                    if ("Lu175/Hf178" in ratio_list) and (self.parent.comboBoxIsotopeAgeFieldType2.currentText() == "Ratio"):
                        self.parent.comboBoxIsotopeAgeField2.setCurrentText("Lu175/Hf178")

                    self.parent.labelIsotope3.setText("")
                    self.parent.comboBoxIsotopeAgeFieldType3.currentText("Ratio")
                    self.parent.labelIsotope3.setEnabled(False)
                    self.parent.comboBoxIsotopeAgeFieldType3.setEnabled(False)
                    self.parent.comboBoxIsotopeAgeField3.setEnabled(False)
                    

                # Sonderlund et al., EPSL, 2004, https://doi.org/10.1016/S0012-821X(04)00012-3
                self.parent.lineEditDecayConstant.value = 1.867e-5 # Ma
                self.parent.lineEditDecayConstantUncertainty.value = 0.008e-5 # Ma
            case "Re-Os":
                self.parent.labelIsotope1.setText("Re187")
                if "Re187" in self.parent.analyte_list and self.parent.comboBoxIsotopeAgeFieldType1.currentText() == "Analyte":
                    self.parent.comboBoxIsotopeAgeField1.setCurrentText("Re187")
                self.parent.labelIsotope2.setText("Os187")
                if "Os187" in self.parent.analyte_list and self.parent.comboBoxIsotopeAgeFieldType2.currentText() == "Analyte":
                    self.parent.comboBoxIsotopeAgeField2.setCurrentText("Os187")
                self.parent.labelIsotope3.setText("Os188")
                if "Os188" in self.parent.analyte_list and self.parent.comboBoxIsotopeAgeFieldType3.currentText() == "Analyte":
                    self.parent.comboBoxIsotopeAgeField3.setCurrentText("Os188")

                # Selby et al., GCA, 2007, https://doi.org/10.1016/j.gca.2007.01.008
                self.parent.lineEditDecayConstant.value = 1.666e-5 # Ma
                self.parent.lineEditDecayConstantUncertainty.value = 0.005e-5 # Ma
            case "Sm-Nd":
                pass
            case "Rb-Sr":
                pass
            case "U-Pb":
                pass
            case "Th-Pb":
                pass
            case "Pb-Pb":
                pass

    def scatter_date(self, x, y, y0):

        def slope_only(b):
            def model(A,x):
                return A[0]*x + b
            return model

        linear = odr.Model(slope_only(y0))
        data = odr.RealData(x,y)
        myodr = odr.ODR(data, linear, beta0=[1])
        myoutput = myodr.run()
        myoutput.pprint()


    def compute_date_map(self):
        """Compute one of several date maps"""
        decay_constant = self.parent.lineEditDecayConstant.value
        method = self.parent.comboBoxDatingMethod.currentText()
        match method:
            case "Lu-Hf":
                if self.parent.checkBoxComputeRatios.isChecked():
                    try:
                        Lu175 = self.parent.get_map_data(self.parent.sample_id, self.parent.comboBoxIsotopeAgeField1.currentText(), self.parent.comboBoxIsotopeAgeFieldType1.currentText())
                        Hf176 = self.parent.get_map_data(self.parent.sample_id, self.parent.comboBoxIsotopeAgeField2.currentText(), self.parent.comboBoxIsotopeAgeFieldType2.currentText())
                        Hf178 = self.parent.get_map_data(self.parent.sample_id, self.parent.comboBoxIsotopeAgeField3.currentText(), self.parent.comboBoxIsotopeAgeFieldType3.currentText())

                        Hf176_Hf178 = Hf176['array'].values / Hf178['array'].values
                        Lu175_Hf178 = Lu175['array'].values / Hf178['array'].values
                    except:
                        QMessageBox.warning(self.parent,'Warning','Could not compute ratios, check selected fields.')
                        return
                else:
                    try:
                        Hf176_Hf178 = self.parent.get_map_data(self.parent.sample_id, self.parent.comboBoxIsotopeAgeField1.currentText(), self.parent.comboBoxIsotopeAgeFieldType1.currentText())
                        Lu175_Hf178 = self.parent.get_map_data(self.parent.sample_id, self.parent.comboBoxIsotopeAgeField2.currentText(), self.parent.comboBoxIsotopeAgeFieldType2.currentText())
                    except:
                        QMessageBox.warning(self.parent,'Warning','Could not locate ratios, check selected fields.')
                        return

                if self.parent.data[self.parent.sample_id]['computed_data']['Calculated'].empty:
                    self.parent.data[self.parent.sample_id]['computed_data']['Calculated'][['X','Y']] = self.parent.data[self.parent.sample_id]['cropped_raw_data'][['X','Y']]

                try:
                    date_map = np.log((Hf176_Hf178 - 3.55)/Lu175_Hf178 + 1) / decay_constant 
                except:
                    QMessageBox.warning(self.parent,'Error','Something went wrong. Could not compute date map.')

            case "Re-Os":
                pass

        # save date_map to Calculated dataframe
        self.parent.data[self.parent.sample_id]['computed_data']['Calculated'].loc[self.parent.data[self.parent.sample_id]['mask'],method] = date_map
        
        # update styles and plot
        self.parent.comboBoxColorByField.setCurrentText('Calculated')
        self.parent.color_by_field_callback()
        self.parent.comboBoxColorField.setCurrentText(method)
        self.parent.color_field_callback()
        #self.set_style_widgets(plot_type='analyte map')

        #self.update_SV()

    def add_ree(self, sample_df):
        """Adds predefined sums of rare earth elements to calculated fields

        Computes four separate sums, LREE, MREE, HREE, and REE.  Elements not analyzed are igorned by the sum.

        * ``lree = ['la', 'ce', 'pr', 'nd', 'sm', 'eu', 'gd']``
        * ``mree = ['sm', 'eu', 'gd']``
        * ``hree = ['tb', 'dy', 'ho', 'er', 'tm', 'yb', 'lu']``

        Parameters
        ----------
        sample_df : pandas.DataFrame
            Sample data
        
        Returns
        -------
        pandas.DataFrame
            REE dataframe
        """

        lree = ['la', 'ce', 'pr', 'nd', 'sm', 'eu', 'gd']
        mree = ['sm', 'eu', 'gd']
        hree = ['tb', 'dy', 'ho', 'er', 'tm', 'yb', 'lu']

        # Convert column names to lowercase and filter based on lree, hree, etc. lists
        lree_cols = [col for col in sample_df.columns if any([col.lower().startswith(iso) for iso in lree])]
        hree_cols = [col for col in sample_df.columns if any([col.lower().startswith(iso) for iso in hree])]
        mree_cols = [col for col in sample_df.columns if any([col.lower().startswith(iso) for iso in mree])]
        ree_cols = lree_cols + hree_cols

        # Sum up the values for each row
        ree_df = pd.DataFrame(index=sample_df.index)
        ree_df['LREE'] = sample_df[lree_cols].sum(axis=1)
        ree_df['HREE'] = sample_df[hree_cols].sum(axis=1)
        ree_df['MREE'] = sample_df[mree_cols].sum(axis=1)
        ree_df['REE'] = sample_df[ree_cols].sum(axis=1)

        return ree_df