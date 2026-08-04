import numpy as np
import pandas as pd

from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import (
        QMessageBox, QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QScrollArea, QToolButton,
        QTableWidget, QTableWidgetItem, QSpacerItem, QFrame, QSizePolicy, QHeaderView, QTabWidget,
        QFormLayout, QComboBox, QLabel, QCheckBox, QGridLayout, QPushButton, QPlainTextEdit
    )
from lame_core.CustomWidgets import CustomPage, CustomToolButton, CustomLineEdit
from lame_core.UITheme import default_font
from lame_core.config import ICONPATH
from src.app.FieldLogic import FieldLogicUI
from src.common.geochronology import Geochronology

class SpecialPage(CustomPage, FieldLogicUI):
    """P-T-t Functions toolbox page (Thermometry/Barometry/Dating/Diffusion tabs).

    Mixes in ``FieldLogicUI`` so ``DatingTab`` can use the standard
    ``update_field_type_combobox``/``update_field_combobox`` helpers (the
    same ones ``CalculatorDock`` uses) for its isotope field pickers.
    """
    def __init__(self, page_index, dock=None):
        if dock is None:
            return
        super().__init__(obj_name="PTtPage", parent=dock)

        self.dock = dock
        self.page_index = page_index

        # geochronology compute engine, shared by DatingTab
        self.geochron = Geochronology(self.dock.ui)

        # setupUI() constructs each sub-tab (ThermometryTab, BarmometryTab,
        # DatingTab, DiffusionTab), which each wire their own widgets in
        # their own __init__ -- SpecialPage itself has nothing further to connect.
        self.setupUI()

    @property
    def app_data(self):
        """Delegate to ui.app_data so FieldLogicUI methods work correctly."""
        return self.dock.ui.app_data

    @property
    def data(self):
        """Access current sample data without caching a reference -- this page
        is (re)created each time the Special Tools toolbar action is toggled,
        possibly before any sample is loaded, so a snapshot would go stale.

        Returns the SampleObj (not ``.processed``) -- ``FieldLogicUI.update_field_type_combobox``
        reads ``self.data.processed`` directly (matching ``InfoDock``'s convention),
        unlike ``update_field_combobox`` which only needs ``self.app_data``.
        """
        if hasattr(self.dock.ui, 'app_data'):
            return self.dock.ui.app_data.current_data
        return None

    @data.setter
    def data(self, value):
        """Ignored -- data is always derived from dock.ui.app_data.current_data."""
        pass

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
    """Lu-Hf (and, in future, other isotope-system) dating controls.

    Isotope ratio fields 1-4 are the four pre-reduced Lu-Hf ratio columns
    (176Hf/177Hf, 176Lu/177Hf, 177Hf/176Hf, 176Lu/176Hf) LaME's imported data
    already provides -- no ratio computation happens here, matching how the
    source data is actually delivered (unlike the older stub, which assumed
    raw isotope counts and a Hf178 denominator).
    """
    ISOTOPE_LABELS = ['176Hf/177Hf', '176Lu/177Hf', '177Hf/176Hf', '176Lu/176Hf']

    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent = parent

        self.setupUI()
        self.connect_widgets()

    def setupUI(self):
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

        self.labelDatingMethod = QLabel("Method", tab_scroll_area_contents)
        self.labelDatingMethod.setObjectName("labelDatingMethod")

        self.formLayoutDatingMethod.setWidget(0, QFormLayout.ItemRole.LabelRole, self.labelDatingMethod)

        self.comboBoxDatingMethod = QComboBox(tab_scroll_area_contents)
        self.comboBoxDatingMethod.setMaximumSize(QSize(200, 16777215))
        self.comboBoxDatingMethod.setObjectName("comboBoxDatingMethod")
        for method in Geochronology.DATING_METHODS:
            self.comboBoxDatingMethod.addItem(method)
            if method not in Geochronology.IMPLEMENTED_METHODS:
                idx = self.comboBoxDatingMethod.count() - 1
                self.comboBoxDatingMethod.setItemText(idx, f"{method} (not yet implemented)")

        self.formLayoutDatingMethod.setWidget(0, QFormLayout.ItemRole.FieldRole, self.comboBoxDatingMethod)

        self.verticalLayoutDatingParams.addLayout(self.formLayoutDatingMethod)

        # -- isotope ratio field pickers (4 rows: label | field type | field) --
        self.gridLayoutDatingParams = QGridLayout()
        self.gridLayoutDatingParams.setObjectName("gridLayoutDatingParams")

        self.labelIsotope = []
        self.comboBoxIsotopeAgeFieldType = []
        self.comboBoxIsotopeAgeField = []
        for i in range(1, 5):
            label = QLabel(self.ISOTOPE_LABELS[i - 1], tab_scroll_area_contents)
            label.setObjectName(f"labelIsotope{i}")
            self.gridLayoutDatingParams.addWidget(label, i - 1, 0, 1, 1)
            setattr(self, f"labelIsotope{i}", label)
            self.labelIsotope.append(label)

            type_box = QComboBox(tab_scroll_area_contents)
            type_box.setMaximumSize(QSize(125, 16777215))
            type_box.setObjectName(f"comboBoxIsotopeAgeFieldType{i}")
            self.gridLayoutDatingParams.addWidget(type_box, i - 1, 1, 1, 1)
            setattr(self, f"comboBoxIsotopeAgeFieldType{i}", type_box)
            self.comboBoxIsotopeAgeFieldType.append(type_box)

            field_box = QComboBox(tab_scroll_area_contents)
            field_box.setObjectName(f"comboBoxIsotopeAgeField{i}")
            self.gridLayoutDatingParams.addWidget(field_box, i - 1, 2, 1, 1)
            setattr(self, f"comboBoxIsotopeAgeField{i}", field_box)
            self.comboBoxIsotopeAgeField.append(field_box)

        self.labelDecayConstant = QLabel("λ ± unc. (Ma⁻¹)", tab_scroll_area_contents)
        self.labelDecayConstant.setWordWrap(True)
        self.labelDecayConstant.setObjectName("labelDecayConstant")
        self.gridLayoutDatingParams.addWidget(self.labelDecayConstant, 4, 0, 1, 1)

        self.lineEditDecayConstant = CustomLineEdit(parent=tab_scroll_area_contents, precision=8)
        self.lineEditDecayConstant.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditDecayConstant.setObjectName("lineEditDecayConstant")
        self.gridLayoutDatingParams.addWidget(self.lineEditDecayConstant, 4, 1, 1, 1)

        self.lineEditDecayConstantUncertainty = CustomLineEdit(parent=tab_scroll_area_contents, precision=8)
        self.lineEditDecayConstantUncertainty.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditDecayConstantUncertainty.setObjectName("lineEditDecayConstantUncertainty")
        self.gridLayoutDatingParams.addWidget(self.lineEditDecayConstantUncertainty, 4, 2, 1, 1)

        self.verticalLayoutDatingParams.addLayout(self.gridLayoutDatingParams)
        scroll_area_layout.addLayout(self.verticalLayoutDatingParams)

        # -- compute actions --
        compute_group = QGroupBox("Compute", tab_scroll_area_contents)
        compute_layout = QVBoxLayout(compute_group)

        self.pushButtonComputeAge = QPushButton("Single-pixel date map", tab_scroll_area_contents)
        self.pushButtonComputeAge.setObjectName("pushButtonComputeAge")
        self.pushButtonComputeAge.setToolTip("Compute a per-pixel forward and inverse date map from the selected ratio fields.")
        compute_layout.addWidget(self.pushButtonComputeAge)

        self.pushButtonComputeIsochron = QPushButton("Multi-pixel isochron", tab_scroll_area_contents)
        self.pushButtonComputeIsochron.setObjectName("pushButtonComputeIsochron")
        self.pushButtonComputeIsochron.setToolTip("Fit an isochron to each selected cluster (Cluster Filtering tab) and show the result as a new plot.")
        compute_layout.addWidget(self.pushButtonComputeIsochron)

        scroll_area_layout.addWidget(compute_group)

        # -- smoothing (noise reduction) --
        smooth_group = QGroupBox("Smooth Isotope Fields", tab_scroll_area_contents)
        smooth_layout = QFormLayout(smooth_group)

        self.lineEditSigmaSpatial = CustomLineEdit(value=2.0, precision=3, parent=tab_scroll_area_contents)
        smooth_layout.addRow("Spatial sigma", self.lineEditSigmaSpatial)

        self.lineEditSigmaIntensity = CustomLineEdit(value=0.1, precision=3, parent=tab_scroll_area_contents)
        smooth_layout.addRow("Intensity sigma", self.lineEditSigmaIntensity)

        self.pushButtonSmoothFields = QPushButton("Smooth selected isotope fields", tab_scroll_area_contents)
        self.pushButtonSmoothFields.setObjectName("pushButtonSmoothFields")
        self.pushButtonSmoothFields.setToolTip("Bilateral-filter (log-space, cluster-mean-preserving) the 4 selected ratio fields and save as new Calculated fields.")
        smooth_layout.addRow(self.pushButtonSmoothFields)

        scroll_area_layout.addWidget(smooth_group)

        # -- results --
        results_group = QGroupBox("Results", tab_scroll_area_contents)
        results_layout = QVBoxLayout(results_group)

        self.textEditDatingResults = QPlainTextEdit(tab_scroll_area_contents)
        self.textEditDatingResults.setObjectName("textEditDatingResults")
        self.textEditDatingResults.setReadOnly(True)
        self.textEditDatingResults.setMaximumHeight(160)
        results_layout.addWidget(self.textEditDatingResults)

        self.pushButtonCopyToNotes = QPushButton("Copy to Notes", tab_scroll_area_contents)
        self.pushButtonCopyToNotes.setObjectName("pushButtonCopyToNotes")
        results_layout.addWidget(self.pushButtonCopyToNotes)

        scroll_area_layout.addWidget(results_group)

        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        scroll_area_layout.addItem(spacer)

        tab_scroll_area.setWidget(tab_scroll_area_contents)
        tab_layout.addWidget(tab_scroll_area)

    def connect_widgets(self):
        for type_box, field_box in zip(self.comboBoxIsotopeAgeFieldType, self.comboBoxIsotopeAgeField):
            type_box.activated.connect(lambda _, t=type_box, f=field_box: self.parent.update_field_combobox(t, f))

        self.comboBoxDatingMethod.activated.connect(lambda: self.parent.geochron.callback_dating_method())
        self.pushButtonComputeAge.clicked.connect(lambda: self.parent.geochron.compute_date_map())
        self.pushButtonComputeIsochron.clicked.connect(lambda: self.parent.geochron.compute_multipixel_isochron())
        self.pushButtonSmoothFields.clicked.connect(lambda: self.parent.geochron.smooth_isotope_fields())
        self.pushButtonCopyToNotes.clicked.connect(lambda: self.parent.geochron.copy_results_to_notes())


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
