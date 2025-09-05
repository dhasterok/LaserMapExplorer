import re
from dataclasses import dataclass, field
from PyQt6.QtCore import ( Qt, QSize, )
from PyQt6.QtWidgets import (
    QLabel, QComboBox, QVBoxLayout, QSizePolicy, QWidget, QGroupBox,
    QGridLayout, QSpinBox, QDockWidget, QSpacerItem,
)
from PyQt6.QtGui import ( QIcon )
from src.app.config import BASEDIR, ICONPATH, RESOURCE_PATH
from src.common.ExtendedDF import AttributeDataFrame
from src.common.CustomWidgets import CustomDockWidget, CustomPage, CustomComboBox, CustomToolBox
from src.app.Preprocessing import PreprocessingUI
from src.app.LamePlotUI import HistogramUI, CorrelationUI, ScatterUI, NDimUI
from src.app.ImageProcessing import ImageProcessingUI
from src.app.DataAnalysis import ClusterPage, DimensionalReductionPage
from src.app.SpotTools import SpotPage
from src.app.SpecialTools import SpecialPage
from src.common.Logger import LoggerConfig, auto_log_methods, log
from src.common.LamePlot import plot_clusters
from typing import List, Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from .MainWindow import MainWindow

@dataclass
class AxisSettings:
    """Axis-specific settings for plots.

    This class stores settings that control the state of a single plot axis,
    including its label, saved field type, saved field, and whether the axis
    allows a 'None' option.

    Attributes
    ----------
    label : str
        Label text associated with this axis (e.g., "X", "Y", "Z", "Color").
    saved_field_type : str or None
        The last selected field type for this axis. ``None`` if not yet set.
    saved_field : str or None
        The last selected field value for this axis. ``None`` if not yet set.
    add_none : bool
        Whether to include a 'None' option for this axis in the UI.
    """
    label: str = ''
    field_type: str | None = None
    field: str | None = None

@dataclass
class ControlSettings:
    saved_index: int = 0
    page_name: str = ''
    plot_list: List[str] = field(default_factory=list)
    axes: Dict[str, AxisSettings] = field(default_factory=dict)


class ControlDock(CustomDockWidget):
    def __init__(self, ui: "MainWindow"):
        super().__init__(parent=ui)
        self.setWindowTitle("Control Toolbox")

        self.ui = ui

        self.setupUI()

        self.tab_dict = {}
        self.field_control_settings = {}
        self.reindex_tab_dict()

        self.connect_widgets()
        self.connect_observers()
        self.connect_logger()

        # self.axis_widget_dict = {
        #     'label': [self.labelX, self.labelY, self.labelZ, self.labelC],
        #     'parentbox': [self.comboBoxFieldTypeX, self.comboBoxFieldTypeY, self.comboBoxFieldTypeZ, self.comboBoxFieldTypeC],
        #     'childbox': [self.comboBoxFieldX, self.comboBoxFieldY, self.comboBoxFieldZ, self.comboBoxFieldC],
        #     'spinbox': [self.spinBoxFieldX, self.spinBoxFieldY, self.spinBoxFieldZ, self.spinBoxFieldC],
        # }
        self.axis_widget_dict = {
            'x': {'label': self.labelX, 'parentbox': self.comboBoxFieldTypeX, 'childbox': self.comboBoxFieldX, 'spinbox': self.spinBoxFieldX},
            'y': {'label': self.labelY, 'parentbox': self.comboBoxFieldTypeY, 'childbox': self.comboBoxFieldY, 'spinbox': self.spinBoxFieldY},
            'z': {'label': self.labelZ, 'parentbox': self.comboBoxFieldTypeZ, 'childbox': self.comboBoxFieldZ, 'spinbox': self.spinBoxFieldZ},
            'c': {'label': self.labelC, 'parentbox': self.comboBoxFieldTypeC, 'childbox': self.comboBoxFieldC, 'spinbox': self.spinBoxFieldC},
        }

    def setupUI(self):
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QSize(306, 522))
        self.setMaximumSize(QSize(306, 524287))
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable|QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea|Qt.DockWidgetArea.RightDockWidgetArea)
        self.setObjectName("dockWidgetLeftToolbox")

        dock_container = QWidget()

        dock_layout = QVBoxLayout(dock_container)
        dock_layout.setContentsMargins(3, 3, 3, 3)

        self.groupBox = QGroupBox(parent=dock_container)
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setMaximumSize(QSize(300, 16777215))
        self.groupBox.setObjectName("groupBox")

        group_box_layout = QVBoxLayout(self.groupBox)
        group_box_layout.setContentsMargins(3, 3, 3, 3)

        grid_layout = QGridLayout()

        # Plot type
        self.labelPlotType = QLabel(parent=self.groupBox)
        self.labelPlotType.setObjectName("labelPlotType")
        self.labelPlotType.setText("Plot")

        self.comboBoxPlotType = CustomComboBox(parent=self.groupBox)
        self.comboBoxPlotType.setMaximumSize(QSize(190, 16777215))
        self.comboBoxPlotType.setObjectName("comboBoxPlotType")

        # X-Axis
        self.labelX = QLabel(parent=self.groupBox)
        self.labelX.setObjectName("labelX")
        self.labelX.setText("X")

        self.comboBoxFieldTypeX = CustomComboBox(parent=self.groupBox)
        self.comboBoxFieldTypeX.setObjectName("comboBoxFieldTypeX")

        self.comboBoxFieldX = CustomComboBox(parent=self.groupBox)
        self.comboBoxFieldX.setObjectName("comboBoxFieldX")

        self.spinBoxFieldX = QSpinBox(parent=self.groupBox)
        self.spinBoxFieldX.setObjectName("spinBoxFieldX")

        # Y-Axis
        self.labelY = QLabel(parent=self.groupBox)
        self.labelY.setObjectName("labelY")

        self.comboBoxFieldTypeY = CustomComboBox(parent=self.groupBox)
        self.comboBoxFieldTypeY.setObjectName("comboBoxFieldTypeY")

        self.comboBoxFieldY = CustomComboBox(parent=self.groupBox)
        self.comboBoxFieldY.setObjectName("comboBoxFieldY")

        self.spinBoxFieldY = QSpinBox(parent=self.groupBox)
        self.spinBoxFieldY.setObjectName("spinBoxFieldY")

        # Z-Axis
        self.labelZ = QLabel(parent=self.groupBox)
        self.labelZ.setObjectName("labelZ")
        self.labelZ.setText("Z")

        self.comboBoxFieldTypeZ = CustomComboBox(parent=self.groupBox)
        self.comboBoxFieldTypeZ.setObjectName("comboBoxFieldTypeZ")

        self.comboBoxFieldZ = CustomComboBox(parent=self.groupBox)
        self.comboBoxFieldZ.setObjectName("comboBoxFieldZ")

        self.spinBoxFieldZ = QSpinBox(parent=self.groupBox)
        self.spinBoxFieldZ.setObjectName("spinBoxFieldZ")

        # C-Axis
        self.labelC = QLabel(parent=self.groupBox)
        self.labelC.setObjectName("labelC")

        self.comboBoxFieldTypeC = CustomComboBox(parent=self.groupBox)
        self.comboBoxFieldTypeC.setObjectName("comboBoxFieldTypeC")

        self.comboBoxFieldC = CustomComboBox(parent=self.groupBox)
        self.comboBoxFieldC.setObjectName("comboBoxFieldC")

        self.spinBoxFieldC = QSpinBox(parent=self.groupBox)
        self.spinBoxFieldC.setReadOnly(False)
        self.spinBoxFieldC.setObjectName("spinBoxFieldC")
        # Normalization reference
        norm_label = QLabel(parent=self.groupBox)
        norm_label.setText("Ref.")
        norm_label.setObjectName("labelReferenceValue")

        self.comboBoxRefMaterial = QComboBox(parent=self.groupBox)
        self.comboBoxRefMaterial.setMaximumSize(QSize(190, 16777215))
        self.comboBoxRefMaterial.setObjectName("comboBoxRefMaterial")
        self.comboBoxRefMaterial.setPlaceholderText("Select reference...")
        self.comboBoxRefMaterial.setToolTip("Choose a reference for normalization")

        max_type_width = 125
        max_field_width = 100
        spinbox_width = 40

        for lbl in [self.labelPlotType, self.labelX, self.labelY, self.labelZ, self.labelC, norm_label]:
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight)

        for cb in [self.comboBoxFieldTypeX, self.comboBoxFieldTypeY, self.comboBoxFieldTypeZ, self.comboBoxFieldTypeC]:
            cb.setMaximumWidth(max_type_width)

        for cb in [self.comboBoxFieldX, self.comboBoxFieldY, self.comboBoxFieldZ, self.comboBoxFieldC]:
            cb.setMaximumWidth(max_field_width)

        for sb in [self.spinBoxFieldX, self.spinBoxFieldY, self.spinBoxFieldZ, self.spinBoxFieldC]:
            sb.setMinimumWidth(spinbox_width)
            sb.setMaximumWidth(spinbox_width)
            sb.setAlignment(Qt.AlignmentFlag.AlignRight)

        grid_layout.addWidget(self.labelPlotType, 0, 0, 1, 1)
        grid_layout.addWidget(self.comboBoxPlotType, 0, 1, 1, 3)

        grid_layout.addWidget(self.labelX, 1, 0, 1, 1)
        grid_layout.addWidget(self.comboBoxFieldTypeX, 1, 1, 1, 1)
        grid_layout.addWidget(self.comboBoxFieldX, 1, 2, 1, 1)
        grid_layout.addWidget(self.spinBoxFieldX, 1, 3, 1, 1)

        grid_layout.addWidget(self.labelY, 2, 0, 1, 1)
        grid_layout.addWidget(self.comboBoxFieldTypeY, 2, 1, 1, 1)
        grid_layout.addWidget(self.comboBoxFieldY, 2, 2, 1, 1)
        grid_layout.addWidget(self.spinBoxFieldY, 2, 3, 1, 1)

        grid_layout.addWidget(self.labelZ, 3, 0, 1, 1)
        grid_layout.addWidget(self.comboBoxFieldTypeZ, 3, 1, 1, 1)
        grid_layout.addWidget(self.comboBoxFieldZ, 3, 2, 1, 1)
        grid_layout.addWidget(self.spinBoxFieldZ, 3, 3, 1, 1)

        grid_layout.addWidget(self.labelC, 4, 0, 1, 1)
        grid_layout.addWidget(self.comboBoxFieldTypeC, 4, 1, 1, 1)
        grid_layout.addWidget(self.comboBoxFieldC, 4, 2, 1, 1)
        grid_layout.addWidget(self.spinBoxFieldC, 4, 3, 1, 1)

        grid_layout.addWidget(norm_label, 5, 0, 1, 1)
        grid_layout.addWidget(self.comboBoxRefMaterial, 5, 1, 1, 3)

        group_box_layout.addLayout(grid_layout)

        dock_layout.addWidget(self.groupBox)

        self.toolbox = CustomToolBox(parent=dock_container)
        self.toolbox.setEnabled(True)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.toolbox.sizePolicy().hasHeightForWidth())

        # Initialize PreprocessingUI
        self.preprocess = PreprocessingUI(self)

        # Initialize LaMEPlotUI
        self.histogram = HistogramUI(self)
        self.correlation = CorrelationUI(self)
        self.noise_reduction = ImageProcessingUI(self)

        self.field_viewer = CustomPage(obj_name="FieldViewerPage", parent=self)
        self.field_viewer.addWidget(self.histogram)
        self.field_viewer.addWidget(self.correlation)
        self.field_viewer.addWidget(self.noise_reduction)
        field_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.field_viewer.addItem(field_spacer)
        atom_icon = QIcon(str(ICONPATH / "icon-atom-64.svg"))
        page_name = "Field Viewer" 
        self.toolbox.addItem(self.field_viewer, atom_icon, page_name)

        self.toolbox.set_page_icons(
            page_name,
            light_icon = ICONPATH / "icon-atom-64.svg",
            dark_icon = ICONPATH / "icon-atom-dark-64.svg"
        )
        
        # Initialize scatter page
        self.scatter = ScatterUI(self)
        # Initialize n-dimensional page (TEC and radar plots)
        self.ndimensional = NDimUI(self)

        # Initialize dimentionality reduction class from DataAnalysis
        self.dimreduction = DimensionalReductionPage(dock=self)

        # Initialize cluster class from DataAnalysis
        self.clustering = ClusterPage(dock=self)

        self.toolbox.setSizePolicy(sizePolicy)
        self.toolbox.setMinimumSize(QSize(300, 0))
        self.toolbox.setMaximumSize(QSize(300, 16777215))
        self.toolbox.setToolTip("")
        self.toolbox.setObjectName("toolBox")

        dock_layout.addWidget(self.toolbox)
        dock_container.setLayout(dock_layout)
        self.setWidget(dock_container)

    def connect_widgets(self):
        self.toolbox.currentChanged.connect(self.toolbox_changed)
        self.comboBoxPlotType.currentTextChanged.connect(lambda _: setattr(self.ui.style_data, 'plot_type', self.comboBoxPlotType.currentText()))
        self.comboBoxFieldTypeC.popup_callback = lambda: self.update_field_type_combobox_options(
            self.comboBoxFieldTypeC,
            self.comboBoxFieldC,
            ax='c',
            user_activated=True
        )
        self.comboBoxFieldTypeC.currentTextChanged.connect(
            lambda new_field_type: self.update_field_type(ax='c', field_type=new_field_type, user_activated=True)
        )
        self.comboBoxFieldC.popup_callback = lambda: self.update_field_combobox_options(
            self.comboBoxFieldC,
            self.comboBoxFieldTypeC,
            spinbox=self.spinBoxFieldC,
            ax='c',
            user_activated=True
        )
        self.comboBoxFieldC.currentTextChanged.connect(
            lambda new_field: self.update_field(ax='c', field=new_field, user_activated=True)
        )
        # update spinbox associated with map/color field
        self.spinBoxFieldC.valueChanged.connect(lambda _: self.field_spinbox_changed(ax='c'))

        self.comboBoxFieldTypeX.popup_callback = lambda: self.update_field_type_combobox_options(
            self.comboBoxFieldTypeX,
            self.comboBoxFieldX,
            ax='x',
            user_activated=True
        )
        self.comboBoxFieldTypeX.currentTextChanged.connect(
            lambda new_field_type: self.update_field_type(ax='x', field_type=new_field_type, user_activated=True)
        )
        self.comboBoxFieldX.popup_callback = lambda: self.update_field_combobox_options(
            self.comboBoxFieldX,
            self.comboBoxFieldTypeX,
            spinbox=self.spinBoxFieldX,
            ax='x',
            user_activated=True
        )
        self.comboBoxFieldX.currentTextChanged.connect(
            lambda new_field: self.update_field(ax='x', field=new_field, user_activated=True)
        )
        # update spinbox associated with map/color field
        self.spinBoxFieldX.valueChanged.connect(lambda _: self.field_spinbox_changed(ax='x'))

        self.comboBoxFieldTypeY.popup_callback = lambda: self.update_field_type_combobox_options(
            self.comboBoxFieldTypeY,
            self.comboBoxFieldY,
            ax='y',
            user_activated=True
            )
        self.comboBoxFieldTypeY.currentTextChanged.connect(
            lambda new_field_type: self.update_field_type(ax='y', field_type=new_field_type, user_activated=True)
        )
        self.comboBoxFieldY.popup_callback = lambda: self.update_field_combobox_options(
            self.comboBoxFieldY,
            self.comboBoxFieldTypeY,
            spinbox=self.spinBoxFieldY,
            ax='y',
            user_activated=True
            )
        self.comboBoxFieldY.currentTextChanged.connect(
            lambda new_field: self.update_field(ax='y', field=new_field, user_activated=True)
        )
        # update spinbox associated with map/color field
        self.spinBoxFieldY.valueChanged.connect(lambda _: self.field_spinbox_changed(ax='y'))

        self.comboBoxFieldTypeZ.popup_callback = lambda: self.update_field_type_combobox_options(
            self.comboBoxFieldTypeZ,
            self.comboBoxFieldZ,
            ax='z',
            user_activated=True
            )
        self.comboBoxFieldTypeZ.currentTextChanged.connect(
            lambda new_field_type: self.update_field_type(ax='z', field_type=new_field_type, user_activated=True)
        )
        self.comboBoxFieldZ.popup_callback = lambda: self.update_field_combobox_options(
            self.comboBoxFieldZ,
            self.comboBoxFieldTypeZ,
            spinbox=self.spinBoxFieldZ,
            ax='z',
            user_activated=True
            )
        self.comboBoxFieldZ.currentTextChanged.connect(
            lambda new_field: self.update_field(ax='z', field=new_field, user_activated=True)
        )
        self.spinBoxFieldZ.valueChanged.connect(lambda _: self.field_spinbox_changed(ax='z'))

        self.comboBoxRefMaterial.addItems(self.ui.app_data.ref_list.values)          # Select analyte Tab
        self.comboBoxRefMaterial.activated.connect(lambda: self.update_ref_chem_combobox(self.comboBoxRefMaterial.currentText())) 
        self.comboBoxRefMaterial.setCurrentIndex(self.ui.app_data.ref_index)

    def connect_observers(self):
        """Connects properties to observer functions."""
        self.ui.style_data.plotTypeChanged.connect(lambda plot_type: self.update_plot_type(plot_type))

        self.ui.app_data.fieldTypeChanged.connect(lambda ax, new_text: self.update_field_type(ax, new_text))
        self.ui.app_data.fieldChanged.connect(lambda ax, new_text: self.update_field(ax, new_text))

        self.ui.app_data.normReferenceChanged.connect(lambda new_text: self.update_norm_reference_combobox(new_text))

    def connect_logger(self):
        """Connects widgets to logger."""
        # plot and axes controls
        self.toolbox.currentChanged.connect(lambda: log(f"toolBox, index=[{self.toolbox.itemText(self.toolbox.currentIndex())}]",prefix="UI"))
        self.comboBoxPlotType.currentTextChanged.connect(lambda: log(f"comboBoxPlotType value=[{self.comboBoxPlotType.currentText()}]", prefix="UI"))
        self.comboBoxFieldTypeC.currentTextChanged.connect(lambda: log(f"comboBoxFieldTypeC, value=[{self.comboBoxFieldTypeC.currentText()}]",prefix="UI"))
        self.comboBoxFieldC.currentTextChanged.connect(lambda: log(f"comboBoxFieldC, value=[{self.comboBoxFieldC.currentText()}]",prefix="UI"))
        self.spinBoxFieldC.valueChanged.connect(lambda: log(f"spinBoxFieldC value=[{self.spinBoxFieldC.value()}]", prefix="UI"))
        self.comboBoxFieldTypeX.currentTextChanged.connect(lambda: log(f"comboBoxFieldTypeX, value=[{self.comboBoxFieldTypeX.currentText()}]",prefix="UI"))
        self.comboBoxFieldX.currentTextChanged.connect(lambda: log(f"comboBoxFieldX, value=[{self.comboBoxFieldX.currentText()}]",prefix="UI"))
        self.spinBoxFieldX.valueChanged.connect(lambda: log(f"spinBoxFieldX value=[{self.spinBoxFieldX.value()}]", prefix="UI"))
        self.comboBoxFieldTypeY.currentTextChanged.connect(lambda: log(f"comboBoxFieldTypeY, value=[{self.comboBoxFieldTypeY.currentText()}]",prefix="UI"))
        self.comboBoxFieldY.currentTextChanged.connect(lambda: log(f"comboBoxFieldY, value=[{self.comboBoxFieldY.currentText()}]",prefix="UI"))
        self.spinBoxFieldY.valueChanged.connect(lambda: log(f"spinBoxFieldY value=[{self.spinBoxFieldY.value()}]", prefix="UI"))
        self.comboBoxFieldTypeZ.currentTextChanged.connect(lambda: log(f"comboBoxFieldTypeZ, value=[{self.comboBoxFieldTypeZ.currentText()}]",prefix="UI"))
        self.comboBoxFieldZ.currentTextChanged.connect(lambda: log(f"comboBoxFieldZ, value=[{self.comboBoxFieldZ.currentText()}]",prefix="UI"))
        self.spinBoxFieldZ.valueChanged.connect(lambda: log(f"spinBoxFieldZ value=[{self.spinBoxFieldZ.value()}]", prefix="UI"))
        
        ## right/plot tree dock
        self.comboBoxRefMaterial.activated.connect(lambda: log(f"comboBoxRefMaterial value=[{self.comboBoxRefMaterial.currentText()}]", prefix="UI"))

    def toggle_spot_tab(self):
        #self.actionSpotTools.toggle()
        if self.ui.lame_action.SpotTools.isChecked():
            # add spot page to MainWindow.toolBox
            self.spot_tools = SpotPage(self.tab_dict['sample'], self)
            self.ui.lame_action.ImportSpots.setVisible(True)
        elif self.tab_dict['spot'] is not None:
            self.toolbox.removeItem(self.tab_dict['spot'])
            self.ui.lame_action.ImportSpots.setVisible(False)
        self.reindex_tab_dict()

    def toggle_special_tab(self):
        if self.ui.lame_action.SpecialTools.isChecked():
            self.special_tools = SpecialPage(self.tab_dict['cluster'], self)
        elif self.tab_dict['special'] is not None:
            self.toolbox.removeItem(self.tab_dict['special'])

        self.reindex_tab_dict()

    def reindex_tab_dict(self):
        """Resets the dictionaries for the Control Toolbox and plot types.
        
        The dictionary ``self.tab_dict retains the index for each of the Control Toolbox pages.  This way they
        can be easily referenced by name.  At the same time, the dictionary ``self.field_control_settings`` retains the plot
        types available to each page of the control toolbox and the override options when polygons or profiles
        are active."""
        # Create dictionary for left tabs
        self.tab_dict = {'spot': None, 'special': None}

        self.field_control_settings = {
            -1: ControlSettings(
                page_name="",
                saved_index=0,
                plot_list=['field map'],
                axes={
                    'x': AxisSettings(),
                    'y': AxisSettings(),
                    'z': AxisSettings(),
                    'c': AxisSettings(label='Map')
                }
            )
        }

        for tid in range(self.toolbox.count()):
            tab_name = self.toolbox.itemText(tid).lower()
            match tab_name:
                case 'preprocess':
                    self.tab_dict['process'] = tid
                    self.field_control_settings[tid] = ControlSettings(
                        page_name=tab_name,
                        saved_index=0,
                        plot_list=['field map', 'gradient map'],
                        axes={ax: AxisSettings() for ax in ['x','y','z','c']}
                    )
                case 'field viewer':
                    self.tab_dict['sample'] = tid
                    self.field_control_settings[tid] = ControlSettings(
                        page_name=tab_name,
                        saved_index=0,
                        plot_list=['field map', 'histogram', 'correlation'],
                        axes={ax: AxisSettings() for ax in ['x','y','z','c']}
                    )
                case 'spot data':
                    self.tab_dict['spot'] = tid
                    self.field_control_settings[tid] = ControlSettings(
                        page_name=tab_name,
                        saved_index=0,
                        plot_list=['field map', 'gradient map'],
                        axes={ax: AxisSettings() for ax in ['x','y','z','c']}
                    )
                case 'scatter and heatmaps':
                    self.tab_dict['scatter'] = tid
                    self.field_control_settings[tid] = ControlSettings(
                        page_name=tab_name,
                        saved_index=0,
                        plot_list=['scatter', 'heatmap', 'ternary map'],
                        axes={
                            'x': AxisSettings(label='X'),
                            'y': AxisSettings(label='Y'),
                            'z': AxisSettings(label='Z'),
                            'c': AxisSettings(label='Color')
                        }
                    )
                case 'n-dimensional':
                    self.tab_dict['ndim'] = tid
                    self.field_control_settings[tid] = ControlSettings(
                        page_name=tab_name,
                        saved_index=0,
                        plot_list=['TEC', 'Radar'],
                        axes={
                            'x': AxisSettings(),
                            'y': AxisSettings(),
                            'z': AxisSettings(),
                            'c': AxisSettings(label='Color')
                        }
                    )
                case 'dimensional reduction':
                    self.tab_dict['dim_red'] = tid
                    self.field_control_settings[tid] = ControlSettings(
                        page_name=tab_name,
                        saved_index=0,
                        plot_list=['variance','basis vectors','dimension scatter','dimension heatmap','dimension score map'],
                        axes={
                            'x': AxisSettings(label='PC'),
                            'y': AxisSettings(label='PC'),
                            'z': AxisSettings(),
                            'c': AxisSettings(label='Color')
                        }
                    )
                case 'clustering':
                    self.tab_dict['cluster'] = tid
                    self.field_control_settings[tid] = ControlSettings(
                        page_name=tab_name,
                        saved_index=0,
                        plot_list=['cluster map', 'cluster score map', 'cluster performance'],
                        axes={ax: AxisSettings() for ax in ['x','y','z','c']}
                    )
                case 'p-t-t functions':
                    self.tab_dict['special'] = tid
                    self.field_control_settings[tid] = ControlSettings(
                        page_name=tab_name,
                        saved_index=0,
                        plot_list=['field map', 'gradient map', 'cluster score map', 'dimension score map', 'profile'],
                        axes={
                            'x': AxisSettings(),
                            'y': AxisSettings(),
                            'z': AxisSettings(),
                            'c': AxisSettings(label='Map')
                        }
                    )

    def toolbox_changed(self, tab_id=None):
        """Updates styles associated with toolbox page

        Executes on change of ``MainWindow.toolBox.currentIndex()``.  Updates style related widgets.
        """
        if self.ui.app_data.sample_id == '':
            return

        if not tab_id:
            tab_id = self.toolbox.currentIndex()

        data = self.ui.app_data.current_data

        # run clustering before changing plot_type if user selects clustering tab
        if tab_id == self.tab_dict['cluster'] :
            self.clustering.compute_clusters_update_groups()
            plot_clusters(self,data,self.ui.app_data,self.ui.style_data)
        # run dim red before changing plot_type if user selects dim red tab
        if tab_id == self.tab_dict['dim_red'] :
            if self.ui.app_data.update_pca_flag or not data.processed.match_attribute('data_type','pca score'):
                self.dimreduction.compute_dim_red(data, self.ui.app_data)
        # update the plot type comboBox options
        self.update_plot_type_combobox_options()
        self.ui.style_data.plot_type = self.field_control_settings[tab_id].plot_list[self.field_control_settings[tab_id].saved_index]

        if self.toolbox.currentIndex() == self.tab_dict['cluster']:
            self.clustering.toggle_cluster_widgets()

        self.plot_flag = True
        # If canvasWindow is set to SingleView, update the plot
        if self.ui.canvas_widget.canvasWindow.currentIndex() == self.ui.canvas_widget.tab_dict['sv']:
        # trigger update to plot
            self.ui.schedule_update()

    def update_plot_type_combobox_options(self):
        """Updates plot type combobox based on current toolbox index or certain dock widget controls."""
        if self.ui.profile_state == True or self.ui.polygon_state == True:
            plot_idx = -1
        else:
            plot_idx = self.toolbox.currentIndex()

        plot_types = self.field_control_settings[plot_idx].plot_list
        
        if plot_types == self.comboBoxPlotType.allItems():
            return

        self.comboBoxPlotType.blockSignals(True)
        self.comboBoxPlotType.clear()
        self.comboBoxPlotType.addItems(plot_types)
        self.comboBoxPlotType.setCurrentText(plot_types[self.field_control_settings[plot_idx].saved_index])
        self.comboBoxPlotType.blockSignals(False)

        self.ui.style_data.plot_type = self.comboBoxPlotType.currentText()

    def update_plot_type(self, new_plot_type=None, force=False):
        """Updates styles when plot type is changed

        Executes on change of ``self.comboBoxPlotType``.  Updates ``self.plot_type[0]`` to the current index of the 
        combobox, then updates the style widgets to match the dictionary entries and updates the plot.
        """
        #if not force:
        #    if self._plot_type == self.comboBoxPlotType.currentText()
        #        return

        # set plot flag to false
        if new_plot_type:
            if new_plot_type != self.comboBoxPlotType.currentText():
                self.comboBoxPlotType.setCurrentText(new_plot_type)
                self.ui.plot_types[self.toolbox.currentIndex()][0] = self.comboBoxPlotType.currentIndex()

        else:
            self.ui.style_data.plotTypeChanged.blockSignals(True)
            self.ui.style_data.plot_type = self.comboBoxPlotType.currentText()
            self.ui.style_data.plotTypeChanged.blockSignals(False)

        plot_type = self.ui.style_data.plot_type

        # update ui
        match self.ui.style_data.plot_type.lower():
            case 'field map' | 'gradient map':
                self.ui.lame_action.SwapAxes.setEnabled(True)
            case 'scatter' | 'heatmap':
                self.ui.lame_action.SwapAxes.setEnabled(True)
            case 'correlation':
                self.ui.lame_action.SwapAxes.setEnabled(False)
                if self.correlation.comboBoxCorrelationMethod.currentText() == 'none':
                    self.correlation.comboBoxCorrelationMethod.setCurrentText('Pearson')
            case 'cluster performance' | 'cluster map' | 'cluster score ':
                self.clustering.toggle_cluster_widgets()
            case _:
                self.ui.lame_action.SwapAxes.setEnabled(False)

        self.init_field_widgets(self.ui.style_data.axis_settings, plot_type=plot_type)

        # update field widgets
        self.update_field_widgets()

        # For field maps, set X and Y axes to coordinate fields
        if plot_type in ['field map', 'gradient map']:
            # Set X and Y to coordinate fields for maps
            self.comboBoxFieldTypeX.setCurrentText('coordinate')
            self.comboBoxFieldX.setCurrentText('Xc')
            self.comboBoxFieldTypeY.setCurrentText('coordinate')
            self.comboBoxFieldY.setCurrentText('Yc')
            
            # Update the app_data to reflect these changes
            self.ui.app_data.set_field_type('x', 'coordinate')
            self.ui.app_data.set_field('x', 'Xc')
            self.ui.app_data.set_field_type('y', 'coordinate')
            self.ui.app_data.set_field('y', 'Yc')
            
            # Manually trigger axis_variable_changed to update styling widgets
            if hasattr(self.ui, 'styling_dock'):
                self.ui.styling_dock.axis_variable_changed('Xc', 'x')
                self.ui.styling_dock.axis_variable_changed('Yc', 'y')

        self.ui.plot_flag = False
        # update all plot widgets
        axis_settings = self.ui.style_data.axis_settings[plot_type].axes
        for ax, settings in axis_settings.items():
            if settings.enabled:
                self.update_field(ax, self.axis_widget_dict[ax]['childbox'].currentText())
                self.update_field_type(ax, self.axis_widget_dict[ax]['parentbox'].currentText())
        self.ui.plot_flag = True

        if self.ui.style_data.plot_type != '':
            self.ui.schedule_update()

    def init_field_widgets(self, axis_settings, plot_type=None):
        """
        Initializes widgets associated with axes for plotting

        Enables and sets visibility of labels, comboboxes, and spinboxes associated with
        axes for choosing plot dimensions, including color.

        Parameters
        ----------
        axis_settings : dict
            Dictionary with axes settings for axes widgets
        plot_type : str, Optional
            Plot type, by default None
        """
        if plot_type is None:
            plot_type = self.ui.style_data.plot_type

        axis_settings = axis_settings[plot_type].axes

        # enable and set visibility of widgets
        for ax, setting in axis_settings.items():
            widget_dict = self.axis_widget_dict[ax]
            label, parentbox, childbox, spinbox = (
                widget_dict[k] for k in ['label', 'parentbox', 'childbox', 'spinbox']
            )

            # set field label text
            label.setEnabled(setting.enabled)
            label.setVisible(setting.enabled)

            # set parent and child comboboxes
            parentbox.setActive(setting.enabled)
            childbox.setActive(setting.enabled)

            # set field spinboxes
            if spinbox is not None:
                spinbox.setEnabled(setting.spinbox)
                spinbox.setVisible(setting.spinbox)

    def update_field_widgets(self):
        """Updates field widgets with saved settings
         
        Updates the label text, field type combobox, and field combobox with saved values associated with a
        control toolbox tab.
        """
        idx = None
        if (hasattr(self, 'profile_dock') and self.ui.profile_dock.actionProfileToggle.isChecked()) or (hasattr(self, 'mask_dock') and self.ui.mask_dock.polygon_tab.actionPolyToggle.isChecked()):
            idx = -1
        else:
            idx = self.toolbox.currentIndex()

        # prevent updating of plot as all the changes are made
        flag = False
        if self.ui.plot_flag:
            flag = True
            self.ui.plot_flag = False

        control_setting = self.field_control_settings[idx]
        for ax, widget_dict in self.axis_widget_dict.items():
            setting = control_setting.axes[ax]

            label, parentbox, childbox, spinbox = (
                widget_dict[k] for k in ['label', 'parentbox', 'childbox', 'spinbox']
            )
            label.setText(setting.label)

            if setting.field_type is not None:
                self.ui.app_data.set_field_type(ax, setting.field_type)
            else:
                self.update_field_type_combobox_options(parentbox, childbox, ax=ax)
                # If no saved field type and 'none' is available, select it
                if 'none' in parentbox.allItems():
                    parentbox.setCurrentText('none')

            if setting.field is not None:
                self.ui.app_data.set_field(ax, setting.field)
            else:
                self.update_field_combobox_options(childbox, parentbox, spinbox, ax=ax)
                # If no saved field and 'none' is available, select it  
                if 'none' in childbox.allItems():
                    childbox.setCurrentText('none')

        if flag:
            self.ui.plot_flag = True

    def update_field_type_combobox_options(self, parentbox, childbox=None, ax=None, user_activated=False):
        """Updates a field type combobox list.

        Ensures signals are not emitted during list refresh and preserves the
        previous selection if it is still valid. Only user interaction will
        trigger currentTextChanged afterwards.

        Parameters
        ----------
        parentbox : CustomComboBox
            Field type combobox to be updated on popup
        childbox : CustomComboBox, optional
            Field combobox associated with parent combobox, by default None
        ax : str, optional
            Axis string, by default None
        user_activated : bool, optional
            Indicates whether the call is user activated (True) or in response to
            code (False), by default False
        """
        if self.ui.app_data.sample_id == '' or self.ui.style_data.plot_type == '':
            return

        old_list = parentbox.allItems()
        old_field_type = parentbox.currentText()

        # get field type options from app_data
        new_list = self.ui.app_data.get_field_type_list(ax, self.ui.style_data)

        # if the list hasn't changed, no update is needed
        if new_list == old_list:
            return

        # block signals while repopulating items
        parentbox.blockSignals(True)
        parentbox.clear()
        parentbox.addItems(new_list)

        # restore previous selection if possible, otherwise default to first item
        if old_field_type in new_list:
            parentbox.setCurrentIndex(new_list.index(old_field_type))
        else:
            parentbox.setCurrentIndex(0)
        parentbox.blockSignals(False)

        # handle child combobox if supplied
        if childbox is None:
            return

        field_dict = self.ui.app_data.field_dict

        if parentbox.currentText() == 'none':
            childbox.blockSignals(True)
            childbox.clear()
            childbox.setPlaceholderText('none')
            childbox.blockSignals(False)
            return

        # normalize field type if needed
        check_field_type = old_field_type.replace(' (normalized)', '') if 'normalized' in old_field_type else old_field_type

        childbox.blockSignals(True)
        if check_field_type not in new_list:
            childbox.clear()
            childbox.addItems(field_dict[new_list[0]])
            childbox.setCurrentIndex(0)
        elif childbox.currentText() not in field_dict.get(check_field_type, []):
            childbox.clear()
            childbox.addItems(field_dict[check_field_type])
            childbox.setCurrentIndex(0)
        childbox.blockSignals(False)

        
    def update_field_combobox_options(self, childbox, parentbox=None, spinbox=None, ax=None, add_none=False, user_activated=False):
        """Updates a field comobobox list.

        Executed on popup of a field combobox or by forcing an update to the list
        of fields.  If a parent combobox is supplied, then the field list is
        associated with the current field type selected in the parent combobox.

        If no parent combobox is supplied, then the field type is assumed to be
        'Analyte'.  If the parent combobox has no field type selected, then the
        child combobox is cleared and returned.

        If the field type is 'Analyte', then the field list is sorted based on
        the current sort method selected in the app_data.sort_method.
        
        Parameters
        ----------
        childbox : CustomComboBox
            Field combobox to be updated on popup
        parentbox : CustomComboBox, optional
            Field type comobobox associated with child combobox, by default None
        ax : str, optional
            Axis string, by default None
        user_activated : bool, optional
            Indicates whether the call is user activated (True) or in response to
            code (False), by default False
        """
        old_list = childbox.allItems()
        old_field = childbox.currentText()

        # determine field type
        if parentbox is None:
            field_type = 'Analyte'
        elif parentbox.currentText() in [None, '', 'none', 'None']:
            childbox.blockSignals(True)
            childbox.clear()
            childbox.blockSignals(False)
            return
        else:
            field_type = parentbox.currentText()

        field_list = self.ui.app_data.get_field_list(field_type)

        if add_none:
            field_list.insert(0, 'none')

        # no change, do nothing
        if field_list == old_list:
            return

        # block signals while rebuilding the list
        childbox.blockSignals(True)
        childbox.clear()
        childbox.addItems(field_list)

        # restore old selection if possible, else default to first item
        if old_field in field_list:
            childbox.setCurrentIndex(field_list.index(old_field))
        else:
            childbox.setCurrentIndex(0)
        childbox.blockSignals(False)

        # keep spinbox in sync if present
        if spinbox is not None:
            spinbox.blockSignals(True)
            spinbox.setMinimum(0)
            spinbox.setMaximum(childbox.count() - 1)
            spinbox.setValue(childbox.currentIndex())
            spinbox.blockSignals(False)
 
    def update_field_type(self, ax, field_type=None, user_activated=False):
        """Used to update widgets associated with an axis after a field type change to either the combobox or underlying data.

        Used to update, x, y, z, and c axes related widgets including fields, spinboxes, labels, limits and scale.

        Parameters
        ----------
        ax : str
            Axis, options include ``x``, ``y``, ``z``, and ``c``
        field_type : str, optional
            New field type value for axis to update ``app_data`` or combobox, by default None
        user_activated : bool
            Indicated whether the user has triggered the change
        """
        # only update field if the axis is enabled 
        if not self.ui.style_data.axis_settings[self.ui.style_data.plot_type].axes[ax].enabled:
            return

        label, parentbox, childbox, spinbox = (
            self.axis_widget_dict[ax][k] for k in ['label', 'parentbox', 'childbox', 'spinbox']
        )

        current_type = parentbox.currentText() if field_type is None else field_type
        if current_type in ['None', 'none', None]:
            childbox.blockSignals(True)
            childbox.setCurrentText('None')
            childbox.blockSignals(False)
            if spinbox is not None:
                spinbox.setValue(-1)
            self.ui.app_data.set_field_type(ax, 'None')
            self.ui.app_data.set_field(ax, 'None')
            return

        if field_type is None or user_activated:   # user interaction, or direct setting of combobox
            # set field type property to combobox
            self.ui.app_data.blockSignals(True)
            self.ui.app_data.set_field_type(ax, parentbox.currentText())
            self.ui.app_data.blockSignals(False)
        else:   # direct setting of property
            if field_type == parentbox.currentText() and field_type == self.ui.app_data.get_field_type(ax):
                return
            self.ui.app_data.set_field_type(ax, parentbox.currentText())
            # set combobox to field
            parentbox.setCurrentText(field_type)

        # update plot
        self.ui.schedule_update()


    def update_field(self, ax, field=None, user_activated=False):
        """Used to update widgets associated with an axis after a field change to either the combobox or underlying data.

        Used to update, x, y, z, and c axes related widgets including fields, spinboxes, labels, limits and scale.  

        Parameters
        ----------
        ax : str
            Axis, options include ``x``, ``y``, ``z``, and ``c``
        field : str, optional
            New field value for axis to update ``app_data`` or combobox, by default None
        user_activated : bool
            Indicated whether the user has triggered the change
        """
        # only update field if the axis is enabled 
        if not self.ui.style_data.axis_settings[self.ui.style_data.plot_type].axes[ax].enabled:
            return

        label, parentbox, childbox, spinbox = (
            self.axis_widget_dict[ax][k] for k in ['label', 'parentbox', 'childbox', 'spinbox']
        )

        if parentbox.currentText() in ['None', 'none', None]:
            childbox.blockSignals(True)
            childbox.setCurrentText('None')
            childbox.blockSignals(False)
            if spinbox is not None:
                spinbox.setValue(-1)
            self.ui.app_data.set_field(ax, 'None')
            self.ui.style_data.clabel = ''
            return

        if field is None or user_activated:   # user interaction, or direct setting of combobox
            # set field property to combobox
            self.ui.app_data.blockSignals(True)
            self.ui.app_data.set_field(ax, childbox.currentText())
            self.ui.app_data.blockSignals(False)
        else:   # direct setting of property
            if not (field == childbox.currentText() and field == self.ui.app_data.get_field(ax)):

                # set combobox to field
                childbox.blockSignals(True)
                childbox.setCurrentText(field)
                childbox.blockSignals(False)

            # check if c_field property needs to be updated too
            if self.ui.app_data.get_field(ax) != childbox.currentText():
                self.ui.app_data.set_field(ax, childbox.currentText())

        if spinbox is not None and spinbox.value() != childbox.currentIndex():
            spinbox.setValue(childbox.currentIndex())

        # update autoscale widgets
        if ax == 'c' and self.toolbox.currentIndex() == self.tab_dict['process']:
            self.ui.update_autoscale_widgets(self.ui.app_data.get_field(ax), self.ui.app_data.get_field_type(ax))

        if field not in [None, '','none','None']:
            data = self.ui.app_data.current_data

            # update bin width for histograms
            if ax == 'x' and self.ui.style_data.plot_type == 'histogram':
                # update hist_bin_width
                self.ui.app_data.update_num_bins = False
                self.ui.app_data.update_hist_bin_width()
                self.ui.app_data.update_num_bins = True

            # initialize color widgets
            if ax == 'c':
                self.ui.style_dock.set_color_axis_widgets()

            # update axes properties
            if ax == 'c' and self.ui.style_data.plot_type not in ['correlation']:
                self.ui.style_data.clim = [data.processed.get_attribute(field,'plot_min'), data.processed.get_attribute(field,'plot_max')]
                self.ui.style_data.clabel = data.processed.get_attribute(field,'label')
                self.ui.style_data.cscale = data.processed.get_attribute(field,'norm')
            elif self.ui.style_data.plot_type not in []:
                self.ui.style_data.set_axis_lim(ax, [data.processed.get_attribute(field,'plot_min'), data.processed.get_attribute(field,'plot_max')])
                self.ui.style_data.set_axis_label(ax, data.processed.get_attribute(field,'label'))
                self.ui.style_data.set_axis_scale(ax, data.processed.get_attribute(field,'norm'))

        else:
            self.ui.style_data.clabel = ''

        # update plot
        self.ui.schedule_update()

    # updates scatter styles when ColorByField comboBox is changed
    # this seems to be unused - can maybe be deleted
    # def update_color_field_type(self):
    #     """Executes on change to *ColorByField* combobox
        
    #     Updates style associated with ``MainWindow.comboBoxFieldTypeC``.  Also updates
    #     ``MainWindow.comboBoxFieldC`` and ``MainWindow.comboBoxCScale``."""
    #     self.color_field_type = self.comboBoxFieldTypeC.currentText()

    #     # need this line to update field comboboxes when colorby field is updated
    #     self.update_field_combobox(self.comboBoxFieldTypeC, self.comboBoxFieldC)
    #     self.update_color_field_spinbox()
    #     if self.ui.style_data.plot_type == '':
    #         return

    #     style = self.ui.style_data.style_dict[self.ui.style_data.plot_type]
    #     if self.ui.app_data.c_field_type == self.comboBoxFieldTypeC.currentText():
    #         return

    #     self.ui.app_data.c_field_type = self.comboBoxFieldTypeC.currentText()
    #     if self.comboBoxFieldTypeC.currentText() != '':
    #         self.set_style_widgets()

    #     if self.comboBoxPlotType.isEnabled() == False | self.comboBoxFieldTypeC.isEnabled() == False:
    #         return

    #     # only run update current plot if color field is selected or the color by field is clusters
    #     if self.comboBoxFieldTypeC.currentText() != 'none' or self.comboBoxFieldC.currentText() != '' or self.comboBoxFieldTypeC.currentText() in ['cluster']:
    #         self.ui.schedule_update()

    def field_spinbox_changed(self, ax):
        """Updates associated field combobox when spinbox is changed.
        
        Parameters
        ----------
        ax : str
            Axis, options include ``x``, ``y``, ``z``, and ``c``
        """
        spinbox = self.axis_widget_dict[ax]['spinbox']
        childbox = self.axis_widget_dict[ax]['childbox']

        spinbox.blockSignals(True)
        if spinbox.value() != childbox.currentIndex():
            childbox.setCurrentIndex(spinbox.value())
            self.update_field(ax)
        spinbox.blockSignals(False)

    def update_norm_reference_combobox(self, new_norm_reference):
        if self.toolbox.currentIndex() == self.tab_dict['ndim']:
            self.ui.schedule_update()

    def update_ref_chem_combobox(self, ref_val):
        """Changes reference computing normalized analytes

        Sets all `self.app_data.ref_chem` to a common normalizing reference.

        Parameters
        ----------
        ref_val : str
            Name of reference value from combobox/dropdown
        """
        # update `self.app_data.ref_chem`
        ref_index = self.ui.app_data.update_ref_chem_index(ref_val)

        if ref_index:
            self.comboBoxRefMaterial.setCurrentIndex(ref_index)
            
            # loop through normalized ratios and enable/disable ratios based
            # on the new reference's analytes
            if self.ui.app_data.sample_id == '':
                return

            tree = 'Ratio (normalized)'
            branch = self.ui.app_data.sample_id
            for ratio in self.ui.data[branch].processed.match_attribute('data_type','Ratio'):
                item, check = self.ui.plot_tree.find_leaf(tree, branch, leaf=ratio)
                if item is None:
                    raise TypeError(f"Missing item ({ratio}) in plot_tree.")
                analyte_1, analyte_2 = ratio.split(' / ')

                if check:
                    # ratio normalized
                    # check if ratio can be normalized (note: normalization is not handled here)
                    refval_1 = self.ui.app_data.current_data.ref_chem[re.sub(r'\d', '', analyte_1).lower()]
                    refval_2 = self.ui.app_data.current_data.ref_chem[re.sub(r'\d', '', analyte_2).lower()]
                    ratio_flag = False
                    if (refval_1 > 0) and (refval_2 > 0):
                        ratio_flag = True
                    #print([analyte, refval_1, refval_2, ratio_flag])

                    # if normization cannot be done, make text italic and disable item
                    if ratio_flag:
                        font = item.font()
                        font.setItalic(False)
                        item.setFont(font)
                        item.setEnabled(True)
                    else:
                        font = item.font()
                        font.setItalic(True)
                        item.setFont(font)
                        item.setEnabled(False)

            # trigger update to plot
            self.ui.schedule_update()
        #self.update_all_plots()

    def get_axis_field(self, ax):
        """Grabs the field name from a given axis

        The field name for a given axis comes from a comboBox, and depends upon the plot type.
        Parameters
        ----------
        ax : str
            Axis, options include ``x``, ``y``, ``z``, and ``c``
        """
        plot_type = self.comboBoxPlotType.currentText()
        if ax == 'c':
            return self.comboBoxFieldC.currentText()

        match plot_type:
            case 'histogram':
                if ax in ['x', 'y']:
                    return self.comboBoxFieldC.currentText()
            case 'scatter' | 'heatmap':
                match ax:
                    case 'x':
                        return self.comboBoxFieldX.currentText()
                    case 'y':
                        return self.comboBoxFieldY.currentText()
                    case 'z':
                        return self.comboBoxFieldZ.currentText()
            case 'PCA scatter' | 'PCA heatmap':
                match ax:
                    case 'x':
                        return f'PC{self.dimreduction.spinBoxPCX.value()}'
                    case 'y':
                        return f'PC{self.dimreduction.spinBoxPCY.value()}'
            case 'field map' | 'ternary map' | 'PCA score' | 'cluster map' | 'cluster score':
                return ax.upper()

class FieldLogicUI():
    """Methods associated with fields and field type, specifically comboboxes

    Parameters
    ----------
    data : AttributeDataFrame, optional
        Initializes data frame, defaults to None
    """        
    def __init__(self, data=None):
        self.data = data

    def update_data(self, data):
        """Updates the data

        Parameters
        ----------
        data : AttributeDataFrame
            New data frame
        """        
        if not ((data is None) and (not isinstance(data, AttributeDataFrame))):
            raise TypeError("data should be an AttributeDataFrame")
        self.data = data

    # -------------------------------------
    # Field type and field combobox pairs
    # -------------------------------------
    # updates field type comboboxes for analyses and plotting
    def update_field_type_combobox(self, comboBox, addNone=False, plot_type=''):
        """Updates field type combobox
        
        Used to update ``MainWindow.comboBoxHistFieldType``, ``MainWindow.comboBoxFilterFieldType``,
        ``MainWindow.comboBoxFieldTypeX``, ``MainWindow.comboBoxFieldTypeY``,
        ``MainWindow.comboBoxFieldTypeZ``, and ``MainWindow.comboBoxColorByField``

        Parameters
        ----------
        combobox : QComboBox
            The combobox to update.
        addNone : bool
            Adds ``None`` to the top of the ``combobox`` list
        plot_type : str
            The plot type helps to define the set of field types available, by default ``''`` (no change)
        """
        data_type_dict = self.data.processed.get_attribute_dict('data_type')

        match plot_type.lower():
            case 'correlation' | 'histogram' | 'tec':
                if 'Cluster' in data_type_dict:
                    field_list = ['Cluster']
                else:
                    field_list = []
            case 'cluster score':
                if 'Cluster score' in data_type_dict:
                    field_list = ['Cluster score']
                else:
                    field_list = []
            case 'cluster':
                if 'Cluster' in data_type_dict:
                    field_list = ['Cluster']
                else:
                    field_list = ['Cluster score']
            case 'cluster performance':
                field_list = []
            case 'pca score':
                if 'PCA score' in data_type_dict:
                    field_list = ['PCA score']
                else:
                    field_list = []
            case 'ternary map':
                field_list = []
            case _:
                field_list = ['Analyte', 'Analyte (normalized)']

                # add check for ratios
                if 'Ratio' in data_type_dict:
                    field_list.append('Ratio')
                    field_list.append('Ratio (normalized)')

                if 'pca score' in data_type_dict:
                    field_list.append('PCA score')

                if 'Cluster' in data_type_dict:
                    field_list.append('Cluster')

                if 'Cluster score' in data_type_dict:
                    field_list.append('Cluster score')

        # add None to list?
        if addNone:
            field_list.insert(0, 'None')

        # clear comboBox items
        comboBox.clear()
        # add new items
        comboBox.addItems(field_list)

        # ----start debugging----
        # print('update_field_type_combobox: '+plot_type+',  '+comboBox.currentText())
    # ----end debugging----

    # updates field comboboxes for analysis and plotting
    def update_field_combobox(self, parentBox, childBox, *args, **kwargs):
        """Updates comboBoxes with fields for plots or analysis

        Updates lists of fields in comboBoxes that are used to generate plots or used for analysis.
        Calls ``MainWindow.get_field_list()`` to construct the list.

        Parameters
        ----------
        parentBox : QComboBox, None
            ComboBox used to select field type ('Analyte', 'Analyte (normalized)', 'Ratio', etc.), if None, then 'Analyte'

        childBox : QComboBox
            ComboBox with list of field values
        """
        if self.data is None:
            return

        if parentBox is None or parentBox.currentText() == '':
            fields = self.app_data.get_field_list('Analyte')
        else:
            fields = self.app_data.get_field_list(parentBox.currentText())

        childBox.clear()
        childBox.addItems(fields)

        # ----start debugging----
        # if parentBox is not None:
        #     print('update_field_combobox: '+parentBox.currentText())
        # else:
        #     print('update_field_combobox: None')
        # print(fields)
        # ----end debugging----

        # get a named list of current fields for sample
