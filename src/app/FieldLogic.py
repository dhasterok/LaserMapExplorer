import os, re
from pathlib import Path
from PyQt6.QtCore import ( Qt, pyqtSignal, QObject, QEvent, QSize )
from PyQt6.QtWidgets import (
    QMessageBox, QTableWidget, QDialog, QTableWidgetItem, QLabel, QComboBox,
    QHeaderView, QFileDialog, QAbstractItemView, QVBoxLayout, QHBoxLayout,
    QSizePolicy, QWidget, QGroupBox, QGridLayout, QSpinBox, QDockWidget, QToolBox,
    QSpacerItem, QMainWindow
)
from PyQt6.QtGui import ( QImage, QColor, QFont, QPixmap, QPainter, QBrush, QIcon )
from src.ui.AnalyteSelectionDialog import Ui_Dialog
from src.ui.FieldSelectionDialog import Ui_FieldDialog
from src.app.config import BASEDIR, ICONPATH, RESOURCE_PATH

from src.common.ExtendedDF import AttributeDataFrame
from src.common.CustomWidgets import CustomDockWidget, CustomPage, RotatedHeaderView, CustomComboBox, CustomToolBox
from src.app.Preprocessing import PreprocessingUI
from src.app.LamePlotUI import HistogramUI, CorrelationUI, ScatterUI, NDimUI
from src.app.ImageProcessing import ImageProcessingUI
from src.app.DataAnalysis import ClusterPage, DimensionalReductionPage
from src.app.SpotTools import SpotPage
from src.app.SpecialTools import SpecialPage
from src.common.Logger import LoggerConfig, auto_log_methods, log

from src.common.LamePlot import plot_clusters


class ControlDock(CustomDockWidget):
    def __init__(self, ui=None):
        super().__init__(parent=ui)
        self.setWindowTitle("Control Toolbox")

        if not isinstance(ui, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        self.ui = ui

        self.setupUI()

        self.tab_dict = {}
        self.reindex_tab_dict()

        self.connect_widgets()
        self.connect_observers()
        self.connect_logger()

        self.axis_widget_dict = {
            'label': [self.labelX, self.labelY, self.labelZ, self.labelC],
            'parentbox': [self.comboBoxFieldTypeX, self.comboBoxFieldTypeY, self.comboBoxFieldTypeZ, self.comboBoxFieldTypeC],
            'childbox': [self.comboBoxFieldX, self.comboBoxFieldY, self.comboBoxFieldZ, self.comboBoxFieldC],
            'spinbox': [self.spinBoxFieldX, self.spinBoxFieldY, self.spinBoxFieldZ, self.spinBoxFieldC],
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
        self.comboBoxPlotType.currentTextChanged.connect(lambda: setattr(self.ui.style_data, 'plot_type', self.comboBoxPlotType.currentText()))
        self.comboBoxFieldTypeC.popup_callback = lambda: self.update_field_type_combobox_options(
            self.comboBoxFieldTypeC,
            self.comboBoxFieldC,
            ax=3,
            user_activated=True
            )
        self.comboBoxFieldTypeC.currentTextChanged.connect(lambda: self.update_field_type(ax=3))
        self.comboBoxFieldC.popup_callback = lambda: self.update_field_combobox_options(
            self.comboBoxFieldC,
            self.comboBoxFieldTypeC,
            spinbox=self.spinBoxFieldC,
            ax=3,
            user_activated=True
            )
        self.comboBoxFieldC.currentTextChanged.connect(lambda: self.update_field(ax=3))
        # update spinbox associated with map/color field
        self.spinBoxFieldC.valueChanged.connect(lambda: self.field_spinbox_changed(ax=3))

        self.comboBoxFieldTypeX.popup_callback = lambda: self.update_field_type_combobox_options(
            self.comboBoxFieldTypeX,
            self.comboBoxFieldX,
            ax=0,
            user_activated=True
            )
        self.comboBoxFieldTypeX.currentTextChanged.connect(lambda: self.update_field_type(ax=0))
        self.comboBoxFieldX.popup_callback = lambda: self.update_field_combobox_options(
            self.comboBoxFieldX,
            self.comboBoxFieldTypeX,
            spinbox=self.spinBoxFieldX,
            ax=0,
            user_activated=True
            )
        self.comboBoxFieldX.currentTextChanged.connect(lambda: self.update_field(ax=0))
        # update spinbox associated with map/color field
        self.spinBoxFieldX.valueChanged.connect(lambda: self.field_spinbox_changed(ax=0))

        self.comboBoxFieldTypeY.popup_callback = lambda: self.update_field_type_combobox_options(
            self.comboBoxFieldTypeY,
            self.comboBoxFieldY,
            ax=1,
            user_activated=True
            )
        self.comboBoxFieldTypeY.currentTextChanged.connect(lambda: self.update_field_type(ax=1))
        self.comboBoxFieldY.popup_callback = lambda: self.update_field_combobox_options(
            self.comboBoxFieldY,
            self.comboBoxFieldTypeY,
            spinbox=self.spinBoxFieldY,
            ax=1,
            user_activated=True
            )
        self.comboBoxFieldY.currentTextChanged.connect(lambda: self.update_field(ax=1))
        # update spinbox associated with map/color field
        self.spinBoxFieldY.valueChanged.connect(lambda: self.field_spinbox_changed(ax=1))

        self.comboBoxFieldTypeZ.popup_callback = lambda: self.update_field_type_combobox_options(
            self.comboBoxFieldTypeZ,
            self.comboBoxFieldZ,
            ax=2,
            user_activated=True
            )
        self.comboBoxFieldTypeZ.currentTextChanged.connect(lambda: self.update_field_type(ax=2))
        self.comboBoxFieldZ.popup_callback = lambda: self.update_field_combobox_options(
            self.comboBoxFieldZ,
            self.comboBoxFieldTypeZ,
            spinbox=self.spinBoxFieldZ,
            ax=2,
            user_activated=True
            )
        self.comboBoxFieldZ.currentTextChanged.connect(lambda: self.update_field(ax=2))
        self.spinBoxFieldZ.valueChanged.connect(lambda: self.field_spinbox_changed(ax=2))

        
        self.comboBoxRefMaterial.addItems(self.ui.app_data.ref_list.values)          # Select analyte Tab
        self.comboBoxRefMaterial.activated.connect(lambda: self.update_ref_chem_combobox(self.comboBoxRefMaterial.currentText())) 
        self.comboBoxRefMaterial.setCurrentIndex(self.ui.app_data.ref_index)

    def connect_observers(self):
        """Connects properties to observer functions."""
        self.ui.style_data.add_observer("plot_type", self.update_plot_type)

        self.ui.app_data.add_observer("x_field_type", self.update_field_type)
        self.ui.app_data.add_observer("x_field", self.update_field)
        self.ui.app_data.add_observer("y_field_type", self.update_field_type)
        self.ui.app_data.add_observer("y_field", self.update_field)
        self.ui.app_data.add_observer("z_field_type", self.update_field_type)
        self.ui.app_data.add_observer("z_field", self.update_field)
        self.ui.app_data.add_observer("c_field_type", self.update_field_type)
        self.ui.app_data.add_observer("c_field", self.update_field)

        self.ui.app_data.add_observer("norm_reference", self.update_norm_reference_combobox)

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
        else:
            self.toolbox.removeItem(self.tab_dict['spot'])
            self.ui.lame_action.ImportSpots.setVisible(False)
        self.reindex_tab_dict()

    def toggle_special_tab(self):
        if self.ui.lame_action.SpecialTools.isChecked():
            self.special_tools = SpecialPage(self.tab_dict['cluster'], self)
        else:
            self.toolbox.removeItem(self.tab_dict['special'])
        self.reindex_tab_dict()

    def reindex_tab_dict(self):
        """Resets the dictionaries for the Control Toolbox and plot types.
        
        The dictionary ``self.tab_dict retains the index for each of the Control Toolbox pages.  This way they
        can be easily referenced by name.  At the same time, the dictionary ``self.field_control_settings`` retains the plot
        types available to each page of the control toolbox and the override options when polygons or profiles
        are active."""
        # create diciontary for left tabs
        self.tab_dict = {}
        self.tab_dict.update({'spot': None})
        self.tab_dict.update({'special': None})

        # create dictionaries for default plot styles
        self.field_control_settings = {
            -1: {'saved_index': 0,
            'plot_list': ['field map'],
            'label': ['','','','Map'],
            'saved_field_type': [None, None, None, None],
            'saved_field': [None, None, None, None]}
        } # -1 is for digitizing polygons and profiles

        for tid in range(0,self.toolbox.count()):
            match self.toolbox.itemText(tid).lower():
                case 'preprocess':
                    self.tab_dict.update({'process': tid})
                    self.field_control_settings.update(
                        {self.tab_dict['process']: {
                            'saved_index': 0,
                            'plot_list': ['field map', 'gradient map'],
                            'label': ['','','','Map'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
                    )
                case 'field viewer':
                    self.tab_dict.update({'sample': tid})
                    self.field_control_settings.update(
                        {self.tab_dict['sample']: {
                            'saved_index': 0,
                            'plot_list': ['field map', 'histogram', 'correlation'],
                            'label': ['','','','Map'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
                    )
                case 'spot data':
                    self.tab_dict.update({'spot': tid})
                    self.field_control_settings.update(
                        {self.tab_dict['spot']: {
                            'saved_index': 0,
                            'plot_list': ['field map', 'gradient map'],
                            'label': ['','','','Map'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]}
                        }
                    )
                case 'scatter and heatmaps':
                    self.tab_dict.update({'scatter': tid})
                    self.field_control_settings.update(
                        {self.tab_dict['scatter']: {
                            'saved_index': 0,
                            'plot_list': ['scatter', 'heatmap', 'ternary map'],
                            'label': ['X','Y','Z','Color'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
                    )
                case 'n-dimensional':
                    self.tab_dict.update({'ndim': tid})
                    self.field_control_settings.update(
                        {self.tab_dict['ndim']: {
                            'saved_index': 0,
                            'plot_list': ['TEC', 'Radar'],
                            'label': ['','','','Color'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
                    )
                case 'dimensional reduction':
                    self.tab_dict.update({'dim_red': tid})
                    self.field_control_settings.update(
                        {self.tab_dict['dim_red']: {
                            'saved_index': 0,
                            'plot_list': ['variance','basis vectors','dimension scatter','dimension heatmap','dimension score map'],
                            'label': ['PC','PC','','Color'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
                    )
                case 'clustering':
                    self.tab_dict.update({'cluster': tid})
                    self.field_control_settings.update(
                        {self.tab_dict['cluster']: {
                            'saved_index': 0,
                            'plot_list': ['cluster map', 'cluster score map', 'cluster performance'],
                            'label': ['','','',''],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
                    )
                case 'p-t-t functions':
                    self.tab_dict.update({'special': tid})
                    self.field_control_settings.update(
                        {self.tab_dict['special']: {
                            'saved_index': 0,
                            'plot_list': ['field map', 'gradient map', 'cluster score map', 'dimension score map', 'profile'],
                            'label': ['','','','Map'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
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
            if self.ui.app_data.update_pca_flag or not data.processed_data.match_attribute('data_type','pca score'):
                self.dimreduction.compute_dim_red(data, self.ui.app_data)
        # update the plot type comboBox options
        self.update_plot_type_combobox_options()
        self.ui.style_data.plot_type = self.field_control_settings[tab_id]['plot_list'][self.field_control_settings[tab_id]['saved_index']]

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

        plot_types = self.field_control_settings[plot_idx]['plot_list']
        
        if plot_types == self.comboBoxPlotType.allItems():
            return

        self.comboBoxPlotType.blockSignals(True)
        self.comboBoxPlotType.clear()
        self.comboBoxPlotType.addItems(plot_types)
        self.comboBoxPlotType.setCurrentText(plot_types[self.field_control_settings[plot_idx]['saved_index']])
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
        if new_plot_type is not None and new_plot_type != '':
            if new_plot_type != self.comboBoxPlotType.currentText():
                self.comboBoxPlotType.setCurrentText(new_plot_type)
                self.ui.plot_types[self.toolbox.currentIndex()][0] = self.comboBoxPlotType.currentIndex()

        else:
            self.ui.style_data.plot_type = self.comboBoxPlotType.currentText()

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

        self.init_field_widgets(self.ui.style_data.plot_axis_dict, self.axis_widget_dict, plot_type=self.ui.style_data.plot_type)

        # update field widgets
        self.update_field_widgets()

        self.ui.plot_flag = False
        # update all plot widgets
        for ax in range(4):
            if self.ui.style_data.plot_axis_dict[self.ui.style_data.plot_type]['axis'][ax]:
                self.update_field(ax, self.axis_widget_dict['childbox'][ax].currentText())
                self.update_field_type(ax, self.axis_widget_dict['parentbox'][ax].currentText())
        self.ui.plot_flag = True

        if self.ui.style_data.plot_type != '':
            self.ui.schedule_update()

    def init_field_widgets(self, plot_axis_dict, widget_dict, plot_type=None):
        """
        Initializes widgets associated with axes for plotting

        Enables and sets visibility of labels, comboboxes, and spinboxes associated with
        axes for choosing plot dimensions, including color.

        Parameters
        ----------
        widget_dict : dict
            Dictionary with field associated widgets and properties
        
        :see also: self.axis_widget_dict
        """
        if plot_type is None:
            setting = plot_axis_dict[self.ui.style_data.plot_type]
        else:
            setting = plot_axis_dict[plot_type]

        # enable and set visibility of widgets
        widget_dict = self.axis_widget_dict
        for ax in range(4):
            label = widget_dict['label'][ax]
            parentbox = widget_dict['parentbox'][ax]
            childbox = widget_dict['childbox'][ax]
            spinbox = widget_dict['spinbox'][ax]

            # set field label text
            label.setEnabled(setting['axis'][ax])
            label.setVisible(setting['axis'][ax])

            # set parent and child comboboxes
            parentbox.setEnabled(setting['axis'][ax])
            parentbox.setVisible(setting['axis'][ax])

            childbox.setEnabled(setting['axis'][ax])
            childbox.setVisible(setting['axis'][ax])

            # set field spinboxes
            if spinbox is not None:
                spinbox.setEnabled(setting['spinbox'][ax])
                spinbox.setVisible(setting['spinbox'][ax])

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

        widget_dict = self.axis_widget_dict
        setting = self.field_control_settings[idx]
        for ax in range(4):
            widget_dict['label'][ax].setText(setting['label'][ax])

            if setting['saved_field_type'][ax] is not None:
                self.ui.app_data.set_field_type(ax, setting['save_field_type'][ax])
            else:
                parentbox = widget_dict['parentbox'][ax]
                childbox = widget_dict['childbox'][ax]
                self.update_field_type_combobox_options(parentbox, childbox, ax=ax)

            if setting['saved_field'][ax] is not None:
                self.ui.app_data.set_field(ax, setting['save_field'][ax])

        if flag:
            self.ui.plot_flag = True

    def update_field_type_combobox_options(self, parentbox, childbox=None, ax=None, user_activated=False):
        """Updates a field type comobobox list.

        This method can be used on popup or by forcing an update.
        
        Parameters
        ----------
        parentbox : CustomComboBox
            Field type comobobox to be updated on popup
        childbox : CustomComboBox, optional
            Field combobox associated with parent combobox, by default None
        ax : int, optional
            Axis index, by default None
        user_activated : bool, optional
            Indicates whether the call is user activated (True) or in response to
            code (False), by default False
        """
        if self.ui.app_data.sample_id == '' or self.ui.style_data.plot_type == '':
            return
            
        old_list = parentbox.allItems()
        old_field_type = parentbox.currentText()

        field_dict = self.ui.app_data.field_dict
        # get field type options from app_data
        new_list = self.ui.app_data.get_field_type_list(ax, self.ui.style_data) 


        # if the list hasn't changed then don't change anything
        if old_list and new_list == old_list:
            return

        # update the parent box list of field types
        parentbox.clear()
        parentbox.addItems(new_list)

        # if previous field type is in the new list, then keep it as the current choice until selected
        if user_activated:
            return

        if old_field_type in new_list:
            parentbox.setCurrentIndex(new_list.index(old_field_type))
        else:
            parentbox.setCurrentIndex(0)

        # if a childbox is supplied, then update it based on the field type
        if childbox is None:
            return

        if parentbox.currentText() == 'none':
            childbox.clear()
            childbox.setPlaceholderText('none')
            return

        if 'normalized' in old_field_type:
            old_field_type = old_field_type.replace(' (normalized)','')
        
        if old_field_type not in new_list:
            childbox.clear()
            childbox.addItems(field_dict[new_list[0]])
            childbox.setCurrentIndex(0)
        elif childbox.currentText() not in field_dict[old_field_type]:
            childbox.clear()
            childbox.addItems(field_dict[old_field_type])
            childbox.setCurrentIndex(0)
        
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
        ax : int, optional
            Axis index, by default None
        user_activated : bool, optional
            Indicates whether the call is user activated (True) or in response to
            code (False), by default False
        """
        old_list = childbox.allItems()
        # if no parent combobox supplied, then assume field type is `analyte`
        if parentbox is None:
            field_type = 'Analyte'

        # if parent combobox has no field type selected, clear childbox and return
        elif parentbox.currentText() in [None, '', 'none', 'None']:
            childbox.clear()
            return

        # if parent combobox is supplied, get the field list associated with current field type
        else:
            field_type = parentbox.currentText()
            
        field_list = self.ui.app_data.get_field_list(field_type)

        # add 'none' as first option if required
        if add_none:
            field_list.insert(0,'none')

        # if the new list is same as old, then nothing to update
        if old_list == field_list:
            return
        
        # clear and add a new list
        old_field = childbox.currentText()
        childbox.clear()
        childbox.addItems(field_list)

        # update the current index if old field is in the new list, otherwise set to first item
        print(f"{childbox.currentText()}")
        if user_activated:
            return

        if old_field in field_list:
            childbox.setCurrentIndex(field_list.index(old_field))
        else:
            childbox.setCurrentIndex(0)

        if spinbox is not None:
            spinbox.blockSignals(True)
            spinbox.setMinimum(0)
            spinbox.setMaximum(childbox.count() - 1)
            spinbox.setValue(childbox.currentIndex())
            spinbox.blockSignals(False)
 
    def update_field_type(self, ax, field_type=None):
        # only update field if the axis is enabled 
        if not self.ui.style_data.plot_axis_dict[self.ui.style_data.plot_type]['axis'][ax]:
            return

        parentbox = self.axis_widget_dict['parentbox'][ax]
        childbox = self.axis_widget_dict['childbox'][ax]
        spinbox = self.axis_widget_dict['spinbox'][ax]

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

        if field_type is None:   # user interaction, or direct setting of combobox
            # set field type property to combobox
            self.ui.app_data.set_field_type(ax, parentbox.currentText())
        else:   # direct setting of property
            if field_type == parentbox.currentText() and field_type == self.ui.app_data.get_field_type(ax):
                return
            self.ui.app_data.set_field_type(ax, parentbox.currentText())
            # set combobox to field
            parentbox.setCurrentText(field_type)

        # update plot
        self.ui.schedule_update()


    def update_field(self, ax, field=None):
        """Used to update widgets associated with an axis after a field change to either the combobox or underlying data.

        Used to update, x, y, z, and c axes related widgets including fields, spinboxes, labels, limits and scale.  

        Parameters
        ----------
        ax : int
            Axis to update, [x,y,z,c] should be supplied as an integer, [0,1,2,3], respectively
        field : str, optional
            New field value for axis to update ``app_data`` or combobox, by default None
        """
        # only update field if the axis is enabled 
        if not self.ui.style_data.plot_axis_dict[self.ui.style_data.plot_type]['axis'][ax]:
            return
            #self.set_axis_lim(ax, [data.processed_data.get_attribute(field,'plot_min'), data.processed_data.get_attribute(field,'plot_max')])
            #self.set_axis_label(ax, data.processed_data.get_attribute(field,'label'])
            #self.set_axis_scale(ax, data.processed_data.get_attribute(field,'norm'])

        parentbox = self.axis_widget_dict['parentbox'][ax]
        childbox = self.axis_widget_dict['childbox'][ax]
        spinbox = self.axis_widget_dict['spinbox'][ax]

        if parentbox.currentText() in ['None', 'none', None]:
            childbox.blockSignals(True)
            childbox.setCurrentText('None')
            childbox.blockSignals(False)
            if spinbox is not None:
                spinbox.setValue(-1)
            self.ui.app_data.set_field(ax, 'None')
            self.ui.style_data.clabel = ''
            return

        if field is None:   # user interaction, or direct setting of combobox
            # set field property to combobox
            self.ui.app_data.set_field(ax, childbox.currentText())
            #field = childbox.currentText()
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
        if ax == 3 and self.toolbox.currentIndex() == self.tab_dict['process']:
            self.ui.update_autoscale_widgets(self.ui.app_data.get_field(ax), self.ui.app_data.get_field_type(ax))

        if field not in [None, '','none','None']:
            data = self.ui.app_data.current_data

            # update bin width for histograms
            if ax == 0 and self.ui.style_data.plot_type == 'histogram':
                # update hist_bin_width
                self.ui.app_data.update_num_bins = False
                self.ui.app_data.update_hist_bin_width()
                self.ui.app_data.update_num_bins = True

            # initialize color widgets
            if ax == 3:
                self.ui.style_dock.set_color_axis_widgets()

            # update axes properties
            if ax == 3 and self.ui.style_data.plot_type not in ['correlation']:
                self.ui.style_data.clim = [data.processed_data.get_attribute(field,'plot_min'), data.processed_data.get_attribute(field,'plot_max')]
                self.ui.style_data.clabel = data.processed_data.get_attribute(field,'label')
                self.ui.style_data.cscale = data.processed_data.get_attribute(field,'norm')
            elif self.ui.style_data.plot_type not in []:
                self.ui.style_data.set_axis_lim(ax, [data.processed_data.get_attribute(field,'plot_min'), data.processed_data.get_attribute(field,'plot_max')])
                self.ui.style_data.set_axis_label(ax, data.processed_data.get_attribute(field,'label'))
                self.ui.style_data.set_axis_scale(ax, data.processed_data.get_attribute(field,'norm'))

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
        ax : int
            Axis to update, [x,y,z,c] should be supplied as an integer, [0,1,2,3], respectively
        """
        spinbox = self.axis_widget_dict['spinbox'][ax]
        childbox = self.axis_widget_dict['childbox'][ax]

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
        ref_index = self.update_ref_chem_combobox_BE(ref_val)

        if ref_index:
            self.comboBoxRefMaterial.setCurrentIndex(ref_index)
            
            # loop through normalized ratios and enable/disable ratios based
            # on the new reference's analytes
            if self.app_data.sample_id == '':
                return

            tree = 'Ratio (normalized)'
            branch = self.app_data.sample_id
            for ratio in self.data[branch].processed_data.match_attribute('data_type','Ratio'):
                item, check = self.plot_tree.find_leaf(tree, branch, leaf=ratio)
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
        data_type_dict = self.data.processed_data.get_attribute_dict('data_type')

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


# Analyte GUI
# -------------------------------
@auto_log_methods(logger_key='Selector')
class AnalyteDialog(QDialog, Ui_Dialog):
    """Creates an dialog to select analytes and ratios of analytes

    Creates a dialog with a matrix analytes vs. analytes with a background given by a correlation matrix.
    Selected analytes are identified by yellow highlighting the cell.  Cells on the diagonal (analyte row 
    and column are the same) are automatically selected.  Cells above the diagonal represent ratio of 
    row / column and cells below the diagonal represent the ratio of column / row.  The list of selected
    analytes and rows are displayed in the table along with the ability to change the scaling.
    
    Methods
    -------
    done_selection()
        Executes when `Done` button is clicked.
    cancel_selection()
        Handles the Cancel button click.
    closeEvent(event)
        Overrides the close event to check for unsaved changes.

    Parameters
    ----------
    parent : MainWindow
        Parent widget, should be the main window of the application.

    Returns
    -------
    AnalyteDialog
        An instance of the AnalyteDialog class, which is a QDialog for selecting analytes and ratios.
    """    
    listUpdated = pyqtSignal()
    def __init__(self, parent):
        if (parent.__class__.__name__ == 'Main'):
            super().__init__() #initialisng with no parent widget
        else:
            super().__init__(parent) #initialise with mainWindow as parentWidget
        self.setupUi(self)

        self.logger_key = 'Selector'

        sample_id = parent.app_data.sample_id

        if sample_id is None or sample_id == '':
            return

        self.data = parent.data[sample_id].processed_data

        self.norm_dict = {}

        self.analytes = self.data.match_attribute('data_type','Analyte')
        self.ratio = self.data.match_attribute('data_type','Ratio')
        for analyte in self.analytes+self.ratio:
            self.norm_dict[analyte] = self.data.get_attribute(analyte,'norm')

        # Initialize filename and unsaved changes flag
        self.base_title ='LaME: Select Analytes and Ratios'
        self.filename = 'untitled'
        self.unsaved_changes = False
        self.update_window_title()
        self.default_dir  = RESOURCE_PATH / "analyte_list"  # Default directory
        # setup scale (norm) combobox
        self.comboBoxScale.clear()

        self.scale_methods = parent.data[parent.app_data.sample_id].scale_options
        self.scale_methods.append('mixed')

        for scale in self.scale_methods:
            self.comboBoxScale.addItem(scale)
        self.comboBoxScale.currentIndexChanged.connect(self.update_all_combos)


        # setup correlation combobox
        self.correlation_matrix = None

        self.comboBoxCorrelation.clear()
        self.correlation_methods = ["Pearson", "Spearman"]
        for method in self.correlation_methods:
            self.comboBoxCorrelation.addItem(method)
        self.comboBoxCorrelation.activated.connect(self.calculate_correlation)


        # setup selected analyte table
        self.tableWidgetSelected.setColumnCount(2)
        self.tableWidgetSelected.setHorizontalHeaderLabels(['Field', 'Scaling'])


        # setup analyte table
        self.tableWidgetAnalytes.setStyleSheet("")  # Clears the local stylesheet

        self.tableWidgetAnalytes.setRowCount(len(self.analytes))
        self.tableWidgetAnalytes.setColumnCount(len(self.analytes))

        # setup header properties
        self.tableWidgetAnalytes.setObjectName("analyteTable")
        self.tableWidgetAnalytes.setStyleSheet("""
            QTableWidget#analyteTable::item { 
                background-color: white;  /* Default background color for items */
            }
            QHeaderView#analyteTable::section {
                background-color: none;  /* Reset background */
                font-weight: normal;     /* Reset font weight */
            }
            QHeaderView#analyteTable::section:hover {
                background-color: lightblue;  /* Change background on hover */
                font-weight: bold;            /* Bold on hover */
            }
        """)

        # initial font for headers to Normal weight
        header_font = self.tableWidgetAnalytes.horizontalHeader().font()
        header_font.setWeight(QFont.Weight.Normal)

        self.tableWidgetAnalytes.setHorizontalHeaderLabels(list(self.analytes))
        self.tableWidgetAnalytes.setHorizontalHeader(RotatedHeaderView(self.tableWidgetAnalytes))
        self.tableWidgetAnalytes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tableWidgetAnalytes.horizontalHeader().setFont(header_font)

        self.tableWidgetAnalytes.setVerticalHeaderLabels(self.analytes)
        self.tableWidgetAnalytes.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tableWidgetAnalytes.verticalHeader().setFont(header_font)

        # highlight diagonal (use analytes)
        self.tableWidgetAnalytes.setStyleSheet("QTableWidget::item:selected {background-color: yellow;}")
        if len(self.norm_dict.keys()) > 0:
            for analyte,norm in self.norm_dict.items():
                self.populate_analyte_list(analyte,norm)
        else:
            # Select diagonal pairs by default
            for i in range(len(self.analytes)):
                row = column = i
                item = self.tableWidgetAnalytes.item(row, column)

                # If the item doesn't exist, create it
                self.toggle_cell_selection(row, column)

        # Variables to track previous row/column for font reset
        self.prev_row = None
        self.prev_col = None

        # Enable mouse tracking to capture hover events
        self.tableWidgetAnalytes.setMouseTracking(True)
        self.tableWidgetAnalytes.viewport().setMouseTracking(True)

        # Connect mouse move event to custom handler
        self.tableWidgetAnalytes.viewport().installEventFilter(self)
        self.tableWidgetAnalytes.cellClicked.connect(self.toggle_cell_selection)


        # UI buttons
        self.pushButtonSaveSelection.clicked.connect(lambda _: self.save_selection())
        self.pushButtonLoadSelection.clicked.connect(lambda _: self.load_selection())
        self.pushButtonDone.clicked.connect(lambda _: self.done_selection())
        self.pushButtonCancel.clicked.connect(lambda _: self.cancel_selection())


        # compute correlations for background colors
        self.calculate_correlation()
    
    def update_window_title(self):
        """Updates the window title based on the filename and unsaved changes."""
        title = f"{self.base_title} - {self.filename}"
        if self.unsaved_changes:
            title += '*'
        self.setWindowTitle(title)

    def done_selection(self):
        """Executes when `Done` button is clicked."""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them before exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                self.update_list()
                self.accept()
            elif reply == QMessageBox.StandardButton.No:
                self.update_list()
                self.accept()
            else:  # Cancel
                pass  # Do nothing, stay in dialog
        else:
            self.update_list()
            self.accept()

    def cancel_selection(self):
        """Handles the Cancel button click."""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them before exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                self.reject()
            elif reply == QMessageBox.StandardButton.No:
                self.reject()
            else:  # Cancel
                pass  # Do nothing, stay in dialog
        else:
            self.reject()

    def closeEvent(self, event):
        """Overrides the close event to check for unsaved changes."""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                event.accept()
            elif reply == QMessageBox.StandardButton.No:
                event.accept()
            else:  # Cancel
                event.ignore()
        else:
            event.accept()

    def update_all_combos(self):
        """Updates the scale combo box (``comboBoxScale``) and the combo boxes within ``tableWidgetSelected``."""
        # Get the currently selected value in comboBoxScale
        selected_scale = self.comboBoxScale.currentText()

        # Iterate through all rows in tableWidgetSelected to update combo boxes
        for row in range(self.tableWidgetSelected.rowCount()):
            combo = self.tableWidgetSelected.cellWidget(row, 1)
            if isinstance(combo,QComboBox):  # Make sure there is a combo box in this cell
                combo.setCurrentText(selected_scale)  # Update the combo box value

        # Mark as unsaved changes
        self.unsaved_changes = True
        self.update_window_title()

    def update_scale(self):
        """Updates the scale combo box based on the selections in `tableWidgetSelected`."""        
        # Initialize a variable to store the first combo box's selection
        first_selection = None
        mixed = False  # Flag to indicate mixed selections

        # Iterate through all rows in tableWidgetSelected to check combo boxes
        for row in range(self.tableWidgetSelected.rowCount()):
            combo = self.tableWidgetSelected.cellWidget(row, 1)
            if combo is not None:  # Make sure there is a combo box in this cell
                # If first_selection has not been set, store the current combo box's selection
                if first_selection is None:
                    first_selection = combo.currentText()
                # If the current combo box's selection does not match first_selection, set mixed to True
                elif combo.currentText() != first_selection:
                    mixed = True
                    break  # No need to check further

        # If selections are mixed, set comboBoxScale to 'mixed', else set it to match first_selection
        if mixed:
            self.comboBoxScale.setCurrentText('mixed')
        else:
            self.comboBoxScale.setCurrentText(first_selection)

        # Mark as unsaved changes
        self.unsaved_changes = True
        self.update_window_title()

    def calculate_correlation(self):
        """Calculates correlation coefficient between two analytes.

        The correlation coefficient is used to color the background between two analytes displayed
        in `tableWidgetAnalytes` as a visual aid to help selection of potentially relevant ratios.
        """        
        selected_method = self.comboBoxCorrelation.currentText().lower()
        # Compute the correlation matrix
        self.correlation_matrix = self.data.corr(method=selected_method)
        for i, row_analyte in enumerate(self.analytes):
            for j, col_analyte in enumerate(self.analytes):

                correlation = self.correlation_matrix.loc[row_analyte, col_analyte]
                self.color_cell(i, j, correlation)
        self.create_colorbar()  # Call this to create and display the colorbar

    def color_cell(self, row, column, correlation):
        """Colors cells in the correlation table"""
        color = self.get_color_for_correlation(correlation)
        item = self.tableWidgetAnalytes.item(row, column)
        if not item:
            item = QTableWidgetItem()
            self.tableWidgetAnalytes.setItem(row, column, item)
        item.setBackground(color)

    def get_color_for_correlation(self, correlation):
        """Computes color associated with a given correlation value.

        Maps the correlation coefficient to an RGB color triplet for use in the `tableWidgetAnalytes`.

        Parameters
        ----------
        correlation : float
            Correlation coefficient for displaying on `tableWidgetAnalytes` with color background.

        Returns
        -------
        QColor
            RGB color triplet associated with correlation
        """        
        #cmap = plt.get_cmap('RdBu')
        #c = cmap((1 + correlation)/2)
        #r = c[1]
        #g = c[2]
        #b = c[3]

        # Map correlation to RGB color
        r = 255 * (1 - (correlation > 0) * ( abs(correlation)))
        g = 255 * (1 - abs(correlation))
        b = 255 * (1 - (correlation < 0) * ( abs(correlation)))
        return QColor(int(r), int(g),int(b))

    def create_colorbar(self):
        """Displays a colorbar for the ``tableWidgetAnalytes``."""        
        colorbar_image = self.generate_colorbar_image(40, 200)  # Width, Height of colorbar
        colorbar_label = QLabel(self)
        colorbar_pixmap = QPixmap.fromImage(colorbar_image)
        self.labelColorbar.setPixmap(colorbar_pixmap)

    def generate_colorbar_image(self, width, height):
        """Creates a colorbar for the ``tableWidgetAnalytes``.

        Parameters
        ----------
        width : int  
            Width of colorbar image.
        height : int
            Height of colorbar image.

        Returns
        -------
        QImage
            Colorbar image to be displayed in UI.
        """        
        image = QImage(width, height, QImage.Format.Format_RGB32)

        painter = QPainter(image)
        painter.fillRect(0, 0, width, height, QColor("white"))  # Fill background with white

        pad =20
        # Draw color gradient
        for i in range(pad,height-pad):
            correlation = 1 - (2 * i / height)  # Map pixel position to correlation value
            color = self.get_color_for_correlation(correlation)
            painter.setPen(color)
            painter.drawLine(10, i, width-20, i) # Leave space for ticks
        # Draw tick marks
        tick_positions = [pad, height // 2, height-pad - 1]  # Top, middle, bottom
        tick_labels = ['1', '0', '-1']
        painter.setPen(QColor("black"))
        for pos, label in zip(tick_positions, tick_labels):
            painter.drawLine(width - 20, pos, width-18 , pos)  # Draw tick mark
            painter.drawText(width-15 , pos + 5, label)   # Draw tick label
        painter.end()
        return image

    def toggle_cell_selection(self, row, column):
        """Toggles cell selection in `tableWidgetAnalytes` and adds or removes from list of
        analytes and ratios used by `MainWindow` methods.

        Parameters
        ----------
        row : int
            Row in `tableWidgetAnalytes` to toggle.
        column : int
            Column in `tableWidgetAnalytes` to toggle.
        """        
        item = self.tableWidgetAnalytes.item(row, column)

        # If the item doesn't exist, create it
        if not item:
            item = QTableWidgetItem()
            self.tableWidgetAnalytes.setItem(row, column, item)
            self.add_analyte_to_list(row, column)
        # If the cell is already selected, deselect it
        elif item.isSelected():
            item.setSelected(True)
            self.add_analyte_to_list(row, column)
        else:
            item.setSelected(False)
            self.remove_analyte_from_list(row, column)

    def add_analyte_to_list(self, row, column):
        """Adds an analyte or ratio to the list to use for analyses in ``MainWindow`` related methods.

        Parameters
        ----------
        row : int
            Row in `tableWidgetAnalytes` to select.
        column : int
            Column in `tableWidgetAnalytes` to select.
        """        
        row_header = self.tableWidgetAnalytes.verticalHeaderItem(row).text()
        col_header = self.tableWidgetAnalytes.horizontalHeaderItem(column).text()

        newRow = self.tableWidgetSelected.rowCount()
        self.tableWidgetSelected.insertRow(newRow)
        if row == column:
            self.tableWidgetSelected.setItem(newRow, 0, QTableWidgetItem(f"{row_header}"))
        else:
            # Add analyte pair to the first column
            self.tableWidgetSelected.setItem(newRow, 0, QTableWidgetItem(f"{row_header} / {col_header}"))

        # Add dropdown to the second column
        combo = QComboBox()
        combo.addItems(['linear', 'log'])
        self.tableWidgetSelected.setCellWidget(newRow, 1, combo)
        self.update_list()

        # Mark as unsaved changes
        self.unsaved_changes = True
        self.update_window_title()

    def remove_analyte_from_list(self, row, column):
        """Removes an analyte or ratio from the list to use in ``MainWindow`` related methods.

        Parameters
        ----------
        row : int
            Row in `tableWidgetAnalytes` to deselect.
        column : int
            Column in `tableWidgetAnalytes` to deselect.
        """        
        row_header = self.tableWidgetAnalytes.verticalHeaderItem(row).text()
        col_header = self.tableWidgetAnalytes.horizontalHeaderItem(column).text()
        if row == column:
            item_text = f"{row_header}"
        else:
            item_text = f"{row_header} / {col_header}"

        # Find the row with the corresponding text and remove it
        for i in range(self.tableWidgetSelected.rowCount()):
            if self.tableWidgetSelected.item(i, 0).text() == item_text:
                self.tableWidgetSelected.removeRow(i)
                self.update_list()
                break
        # Mark as unsaved changes
        self.unsaved_changes = True
        self.update_window_title()

    def get_selected_data(self):
        """Grabs data from `tableWidgetSelected`.

        Returns
        -------
        list of tuple
            A list of analytes and the selected norm
        """        
        data = []
        for i in range(self.tableWidgetSelected.rowCount()):
            analyte_pair = self.tableWidgetSelected.item(i, 0).text()
            combo = self.tableWidgetSelected.cellWidget(i, 1)
            selection = combo.currentText()
            data.append((analyte_pair, selection))
        return data

    def save_selection(self):
        """Saves the list of analytes (and ratios) and their norms so they can be quickly recalled for other samples."""        
        if not self.default_dir:
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", self.default_dir, "Text Files (*.txt);;All Files (*)")
        if file_name:
            file_path = Path(file_name)
            with file_path.open('w') as f:
                for i in range(self.tableWidgetSelected.rowCount()):
                    analyte_pair = self.tableWidgetSelected.item(i, 0).text()
                    combo = self.tableWidgetSelected.cellWidget(i, 1)
                    selection = combo.currentText()
                    f.write(f"{analyte_pair},{selection}\n")

            self.filename = file_path.name
            self.unsaved_changes = False
            self.update_window_title()

            self.raise_()
            self.activateWindow()
            self.show()
        

    def load_selection(self):
        """Loads a saved analyte (and ratio) list and fill the analyte table"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", self.default_dir, "Text Files (*.txt);;All Files (*)")
        if file_name:
            file_path = Path(file_name)
            self.clear_selections()
            with file_path.open('r') as f:
                for line in f.readlines():
                    field, norm = line.replace('\n','').split(',')
                    self.populate_analyte_list(field, norm)
            self.filename = file_path.name
            self.unsaved_changes = False
            self.update_window_title()
            self.update_list()
            self.raise_()
            self.activateWindow()
            self.show()
    
    def clear_selections(self):
        """Clears the current selections in the analyte table and selected list."""
        # Clear the selected analytes table
        self.tableWidgetSelected.setRowCount(0)
        self.tableWidgetSelected.clearContents()

        # Clear selection in the analyte table
        self.tableWidgetAnalytes.clearSelection()

        # Unselect any selected items in the analyte table
        for row in range(self.tableWidgetAnalytes.rowCount()):
            for column in range(self.tableWidgetAnalytes.columnCount()):
                item = self.tableWidgetAnalytes.item(row, column)
                if item:
                    item.setSelected(False)

        self.comboBoxScale.setCurrentIndex(0)
        self.comboBoxCorrelation.setCurrentIndex(0)

    def update_list(self):
        """Update the list of selected analytes""" 
        self.norm_dict={}
        for i in range(self.tableWidgetSelected.rowCount()):
            analyte_pair = self.tableWidgetSelected.item(i, 0).text()
            comboBox = self.tableWidgetSelected.cellWidget(i, 1)
            if not isinstance(comboBox, QComboBox):
                return
            self.norm_dict[analyte_pair] = comboBox.currentText()

            # update norm in data
            self.data.set_attribute(analyte_pair,'norm',comboBox.currentText())

    def populate_analyte_list(self, analyte_pair, norm='linear'):
        """Populates the list of selected analytes

        Parameters
        ----------
        analyte_pair : str
            Analyte or ratio, ratios are entered as analyte1 / analyte2.
        norm : str
            Normization method for vector, ``linear``, ``log``, ``logit``, and ``symlog``, Defaults to ``linear``
        """        
        if '/' in analyte_pair:
            row_header, col_header = analyte_pair.split(' / ')
        else:
            row_header = col_header = analyte_pair
        # Select the cell in tableWidgetanalyte
        if row_header in self.analytes and col_header in self.analytes:
            row_index = self.analytes.index(row_header)
            col_index = self.analytes.index(col_header)

            item = self.tableWidgetAnalytes.item(row_index, col_index)
            if not item:
                item = QTableWidgetItem()
                self.tableWidgetAnalytes.setItem(row_index, col_index, item)
            item.setSelected(True)

            # Add the loaded data to tableWidgetSelected
            new_row = self.tableWidgetSelected.rowCount()
            self.tableWidgetSelected.insertRow(new_row)
            self.tableWidgetSelected.setItem(new_row, 0, QTableWidgetItem(analyte_pair))
            combo = QComboBox()
            combo.addItems(['linear', 'log', 'logit', 'symlog'])
            combo.setCurrentText(norm)
            self.tableWidgetSelected.setCellWidget(new_row, 1, combo)
            combo.currentIndexChanged.connect(self.update_scale)

    def event_filter(self, obj, event):
        """Highlights row and column header of tableWidgetAnalytes as mouse moves over cells.

        Parameters
        ----------
        obj : widget
            Widget that is currently under the mouse pointer.
        event : QEvent
            Triggered by motion of mouse pointer.

        Returns
        -------
        event_filter
            Updated event_filter.
        """        
        if obj == self.tableWidgetAnalytes.viewport() and event.type() == event.MouseMove:
            # Get the row and column of the cell under the mouse
            index = self.tableWidgetAnalytes.indexAt(event.pos())
            row = index.row()
            col = index.column()

            # debugging
            #if self.debug:
            #   print(f"Mouse location: ({row}, {col})")

            # Reset the previous row and column to normal font if they exist
            if self.prev_row is not None:
                self._set_row_font(self.prev_row, QFont.Weight.Normal, QBrush())
            if self.prev_col is not None:
                self._set_col_font(self.prev_col, QFont.Weight.Normal, QBrush())

            # Apply bold font to the current row and column headers
            if row >= 0:
                self._set_row_font(row, QFont.Weight.Bold, QBrush(QColor("yellow")))
                self.prev_row = row
            if col >= 0:
                self._set_col_font(col, QFont.Weight.Bold, QBrush(QColor("yellow")))
                self.prev_col = col

        # Handle resetting when the mouse leaves the widget
        if obj == self.tableWidgetAnalytes.viewport() and event.type() == event.Leave:
            # Reset any bold headers when the mouse leaves the table
            if self.prev_row is not None:
                self._set_row_font(self.prev_row, QFont.Weight.Normal, QBrush())
            if self.prev_col is not None:
                self._set_col_font(self.prev_col, QFont.Weight.Normal, QBrush())
            self.prev_row = None
            self.prev_col = None

        self.tableWidgetAnalytes.viewport().update()  # Force a repaint

        return super().event_filter(obj, event)

    def _set_row_font(self, row, weight, brush):
        """Set the font weight for the vertical header row."""
        if row is not None:
            header_item = self.tableWidgetAnalytes.verticalHeaderItem(row)
            font = header_item.font()
            font.setWeight(weight)
            header_item.setFont(font)
            header_item.setBackground(brush)
            # Force a repaint
            self.tableWidgetAnalytes.viewport().update()

    def _set_col_font(self, col, weight, brush):
        """Set the font weight for the horizontal header column."""
        if col is not None:
            header_item = self.tableWidgetAnalytes.horizontalHeaderItem(col)
            font = header_item.font()
            font.setWeight(weight)
            header_item.setFont(font)
            header_item.setBackground(brush)
            # Force a repaint
            self.tableWidgetAnalytes.viewport().update()


class FieldDialog(QDialog, Ui_FieldDialog):
    """
    Creates a dialog to select fields (with their types) and create custom field lists.

    - The user selects a field type from comboBoxFieldType.
    - listWidgetFieldList is populated with all available fields for that field type.
    - The user can multi-select from listWidgetFieldList and add them to tableWidgetSelectedFields,
      which stores pairs of (field_name, field_type).
    - The user can also remove multiple selected fields from tableWidgetSelectedFields.

    A Save/Load mechanism allows storing/loading field name/type pairs in a text file.
    """

    def __init__(self, parent):
        if (parent.__class__.__name__ == 'Main'):
            super().__init__() #initialisng with no parent widget
        else:
            super().__init__(parent) #initialise with mainWindow as parentWidget
        self.setupUi(self)

        # Example: only continue if sample_id is given in the parent (this is your existing logic).
        if not getattr(parent, 'sample_id', None):
            return
        self.parent = parent
        # Store the reference to BASEDIR from parent (if needed).
        self.default_dir = os.path.join(parent.BASEDIR, "resources", "field_list") \
                           if hasattr(parent, "BASEDIR") else os.getcwd()

        # Initialize fields dictionary: { field_type: [field1, field2, ...], ... }
        # You might already have this dictionary in your class.
        # Adjust it as needed. This is just an example structure.
        self.fields = {
            "Type A": ["Field A1", "Field A2", "Field A3"],
            "Type B": ["Field B1", "Field B2"],
            "Type C": ["Field C1", "Field C2", "Field C3", "Field C4"]
        }

        # Set up the UI elements for multi-selection:
        self.listWidgetFieldList.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tableWidgetSelectedFields.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidgetSelectedFields.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # Configure tableWidgetSelectedFields with two columns: Field and Field Type
        self.tableWidgetSelectedFields.setColumnCount(2)
        self.tableWidgetSelectedFields.setHorizontalHeaderLabels(["Field", "Field Type"])
        self.tableWidgetSelectedFields.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Data structure to store selected fields as tuples: (field_type, field_name)
        self.selected_fields = []

        # Initialize file-related variables
        self.base_title = 'LaME: Create custom field list'
        self.filename = 'untitled'
        self.unsaved_changes = False
        self.update_window_title()

        # Connect signals/slots
        # You should have a comboBoxFieldType in your .ui for selecting the field type.
        # If you named it differently, adjust accordingly.
        
        self.update_field_type_list() 
        self.comboBoxFieldType.currentIndexChanged.connect(self.update_field_list)

        self.toolButtonAddField.clicked.connect(self.add_fields)
        self.toolButtonRemoveField.clicked.connect(self.delete_fields)
        self.pushButtonSave.clicked.connect(self.save_selection)
        self.pushButtonLoad.clicked.connect(self.load_selection)
        self.pushButtonDone.clicked.connect(self.done_selection)
        self.pushButtonCancel.clicked.connect(self.cancel_selection)

        # Initialize the field list with the first field type.
        self.update_field_list()


    # --------------------------------------------------------------------------
    # UI helpers
    # -------------------------------------------------------------------------
    def update_window_title(self):
        """Updates the window title based on the filename and unsaved changes."""
        title = f"{self.base_title} - {self.filename}"
        if self.unsaved_changes:
            title += '*'
        self.setWindowTitle(title)

    def update_field_type_list(self):
        """Populate the comboBoxfieldTypes with available field types."""
        self.comboBoxFieldType.clear()
        field_type_list = self.parent.field_type_list
        for f in field_type_list:
            self.comboBoxFieldType.addItem(f)
    
    def update_field_list(self):
        """Populate the listWidgetFieldList with fields for the current field type."""
        self.listWidgetFieldList.clear()
        field_type = self.comboBoxFieldType.currentText()
        
        field_list = self.parent.get_field_list(field_type)
        for f in field_list:
            self.listWidgetFieldList.addItem(f)

    def update_table(self):
        """Refresh the tableWidgetSelectedFields to match self.selected_fields."""
        self.tableWidgetSelectedFields.setRowCount(0)
        for row_idx, (field_type, field_name) in enumerate(self.selected_fields):
            self.tableWidgetSelectedFields.insertRow(row_idx)
            self.tableWidgetSelectedFields.setItem(row_idx, 0, QTableWidgetItem(field_name))
            self.tableWidgetSelectedFields.setItem(row_idx, 1, QTableWidgetItem(field_type))

    # --------------------------------------------------------------------------
    # Add / Remove
    # --------------------------------------------------------------------------
    def add_fields(self):
        """
        Add the currently selected fields (from listWidgetFieldList) to tableWidgetSelectedFields.
        Each added entry is a tuple (field_type, field_name).
        """
        field_type = self.comboBoxFieldType.currentText()

        selected_items = self.listWidgetFieldList.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, 'Warning', 'No fields selected to add.')
            return

        # For each selected item, add to self.selected_fields if not already present
        added_any = False
        for item in selected_items:
            field_name = item.text()
            if (field_type, field_name) not in self.selected_fields:
                self.selected_fields.append((field_type, field_name))
                added_any = True

        if added_any:
            self.update_table()
            self.unsaved_changes = True
            self.update_window_title()
        else:
            QMessageBox.information(self, 'Info', 'Selected field(s) already in the list.')

    def delete_fields(self):
        """
        Remove the selected row(s) from tableWidgetSelectedFields (and self.selected_fields).
        """
        selected_ranges = self.tableWidgetSelectedFields.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, 'Warning', 'No fields selected to remove.')
            return

        # Collect all selected row indices
        rows_to_remove = []
        for selection_range in selected_ranges:
            top = selection_range.topRow()
            bottom = selection_range.bottomRow()
            rows_to_remove.extend(range(top, bottom + 1))

        # Remove from self.selected_fields in descending order (to keep indices valid)
        for row_idx in sorted(rows_to_remove, reverse=True):
            if 0 <= row_idx < len(self.selected_fields):
                del self.selected_fields[row_idx]

        self.update_table()
        self.unsaved_changes = True
        self.update_window_title()

    # --------------------------------------------------------------------------
    # Load / Save
    # --------------------------------------------------------------------------
    def load_selection(self):
        """
        Loads field name/type pairs from a text file.

        Each line is expected to be in the format:
            field_type,field_name
        (You can change the delimiter to anything else you prefer.)
        """
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Load Field List", self.default_dir,
            "Text Files (*.txt);;All Files (*)", options=options
        )
        if not file_name:
            return

        loaded_fields = []
        with open(file_name, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                # Example format: Type A,Field A2
                if ',' in line:
                    f_type, f_name = line.split(',', 1)
                    loaded_fields.append((f_type, f_name))
                else:
                    # If the file doesn't have the correct format,
                    # you could handle it here or skip.
                    pass

        self.selected_fields = loaded_fields
        self.update_table()

        self.filename = os.path.basename(file_name)
        self.unsaved_changes = False
        self.update_window_title()

        # Bring the dialog to front
        self.raise_()
        self.activateWindow()
        self.show()

    def save_selection(self):
        """
        Saves the current selected fields (field_type, field_name) into a text file.

        Each line will be in the format:
            field_type,field_name
        """
        if not self.selected_fields:
            QMessageBox.warning(self, 'Warning', 'No fields to save.')
            return

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Field List", self.default_dir,
            "Text Files (*.txt);;All Files (*)", options=options
        )
        if not file_name:
            return

        with open(file_name, 'w', encoding='utf-8') as file:
            for (field_type, field_name) in self.selected_fields:
                file.write(f"{field_type},{field_name}\n")

        QMessageBox.information(self, 'Success', 'Field list saved successfully.')
        self.filename = os.path.basename(file_name)
        self.unsaved_changes = False
        self.update_window_title()

        self.raise_()
        self.activateWindow()
        self.show()

    # --------------------------------------------------------------------------
    # Done / Cancel
    # --------------------------------------------------------------------------
    def done_selection(self):
        """
        Executes when 'Done' button is clicked.  
        If unsaved changes exist, prompt the user to save or discard.
        """
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them before exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                self.accept()
            elif reply == QMessageBox.StandardButton.No:
                self.accept()
            else:
                # Cancel: do nothing, stay in dialog
                pass
        else:
            self.accept()

    def cancel_selection(self):
        """
        Handles the 'Cancel' button click.
        If unsaved changes exist, prompt user to save or discard.
        """
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them before exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                self.reject()
            elif reply == QMessageBox.StandardButton.No:
                self.reject()
            else:
                # Cancel: do nothing, stay in dialog
                pass
        else:
            self.reject()

    # --------------------------------------------------------------------------
    # Close event override (X button)
    # --------------------------------------------------------------------------
    def closeEvent(self, event):
        """
        Overrides the close event to check for unsaved changes.
        """
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                event.accept()
            elif reply == QMessageBox.StandardButton.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


class FieldDialog(QDialog, Ui_FieldDialog):
    """
    Creates a dialog to select fields (with their types) and create custom field lists.

    - The user selects a field type from comboBoxFieldType.
    - listWidgetFieldList is populated with all available fields for that field type.
    - The user can multi-select from listWidgetFieldList and add them to tableWidgetSelectedFields,
      which stores pairs of (field_name, field_type).
    - The user can also remove multiple selected fields from tableWidgetSelectedFields.

    A Save/Load mechanism allows storing/loading field name/type pairs in a text file.
    """

    def __init__(self, parent):
        if (parent.__class__.__name__ == 'Main'):
            super().__init__() #initialisng with no parent widget
        else:
            super().__init__(parent) #initialise with mainWindow as parentWidget
        self.setupUi(self)

        # Example: only continue if sample_id is given in the parent (this is your existing logic).
        if not getattr(parent, 'sample_id', None):
            return
        self.parent = parent
        # Store the reference to BASEDIR from parent (if needed).
        self.default_dir = os.path.join(parent.BASEDIR, "resources", "field_list") \
                           if hasattr(parent, "BASEDIR") else os.getcwd()

        # Initialize fields dictionary: { field_type: [field1, field2, ...], ... }
        # You might already have this dictionary in your class.
        # Adjust it as needed. This is just an example structure.
        self.fields = {
            "Type A": ["Field A1", "Field A2", "Field A3"],
            "Type B": ["Field B1", "Field B2"],
            "Type C": ["Field C1", "Field C2", "Field C3", "Field C4"]
        }

        # Set up the UI elements for multi-selection:
        self.listWidgetFieldList.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tableWidgetSelectedFields.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidgetSelectedFields.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # Configure tableWidgetSelectedFields with two columns: Field and Field Type
        self.tableWidgetSelectedFields.setColumnCount(2)
        self.tableWidgetSelectedFields.setHorizontalHeaderLabels(["Field", "Field Type"])
        self.tableWidgetSelectedFields.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Data structure to store selected fields as tuples: (field_type, field_name)
        self.selected_fields = []

        # Initialize file-related variables
        self.base_title = 'LaME: Create custom field list'
        self.filename = 'untitled'
        self.unsaved_changes = False
        self.update_window_title()

        # Connect signals/slots
        # You should have a comboBoxFieldType in your .ui for selecting the field type.
        # If you named it differently, adjust accordingly.
        
        self.update_field_type_list() 
        self.comboBoxFieldType.currentIndexChanged.connect(self.update_field_list)

        self.toolButtonAddField.clicked.connect(self.add_fields)
        self.toolButtonRemoveField.clicked.connect(self.delete_fields)
        self.pushButtonSave.clicked.connect(self.save_selection)
        self.pushButtonLoad.clicked.connect(self.load_selection)
        self.pushButtonDone.clicked.connect(self.done_selection)
        self.pushButtonCancel.clicked.connect(self.cancel_selection)

        # Initialize the field list with the first field type.
        self.update_field_list()


    # --------------------------------------------------------------------------
    # UI helpers
    # -------------------------------------------------------------------------
    def update_window_title(self):
        """Updates the window title based on the filename and unsaved changes."""
        title = f"{self.base_title} - {self.filename}"
        if self.unsaved_changes:
            title += '*'
        self.setWindowTitle(title)

    def update_field_type_list(self):
        """Populate the comboBoxfieldTypes with available field types."""
        self.comboBoxFieldType.clear()
        field_type_list = self.parent.field_type_list
        for f in field_type_list:
            self.comboBoxFieldType.addItem(f)
    
    def update_field_list(self):
        """Populate the listWidgetFieldList with fields for the current field type."""
        self.listWidgetFieldList.clear()
        field_type = self.comboBoxFieldType.currentText()
        
        field_list = self.parent.get_field_list(field_type)
        for f in field_list:
            self.listWidgetFieldList.addItem(f)

    def update_table(self):
        """Refresh the tableWidgetSelectedFields to match self.selected_fields."""
        self.tableWidgetSelectedFields.setRowCount(0)
        for row_idx, (field_type, field_name) in enumerate(self.selected_fields):
            self.tableWidgetSelectedFields.insertRow(row_idx)
            self.tableWidgetSelectedFields.setItem(row_idx, 0, QTableWidgetItem(field_name))
            self.tableWidgetSelectedFields.setItem(row_idx, 1, QTableWidgetItem(field_type))

    # --------------------------------------------------------------------------
    # Add / Remove
    # --------------------------------------------------------------------------
    def add_fields(self):
        """
        Add the currently selected fields (from listWidgetFieldList) to tableWidgetSelectedFields.
        Each added entry is a tuple (field_type, field_name).
        """
        field_type = self.comboBoxFieldType.currentText()

        selected_items = self.listWidgetFieldList.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, 'Warning', 'No fields selected to add.')
            return

        # For each selected item, add to self.selected_fields if not already present
        added_any = False
        for item in selected_items:
            field_name = item.text()
            if (field_type, field_name) not in self.selected_fields:
                self.selected_fields.append((field_type, field_name))
                added_any = True

        if added_any:
            self.update_table()
            self.unsaved_changes = True
            self.update_window_title()
        else:
            QMessageBox.information(self, 'Info', 'Selected field(s) already in the list.')

    def delete_fields(self):
        """
        Remove the selected row(s) from tableWidgetSelectedFields (and self.selected_fields).
        """
        selected_ranges = self.tableWidgetSelectedFields.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, 'Warning', 'No fields selected to remove.')
            return

        # Collect all selected row indices
        rows_to_remove = []
        for selection_range in selected_ranges:
            top = selection_range.topRow()
            bottom = selection_range.bottomRow()
            rows_to_remove.extend(range(top, bottom + 1))

        # Remove from self.selected_fields in descending order (to keep indices valid)
        for row_idx in sorted(rows_to_remove, reverse=True):
            if 0 <= row_idx < len(self.selected_fields):
                del self.selected_fields[row_idx]

        self.update_table()
        self.unsaved_changes = True
        self.update_window_title()

    # --------------------------------------------------------------------------
    # Load / Save
    # --------------------------------------------------------------------------
    def load_selection(self):
        """
        Loads field name/type pairs from a text file.

        Each line is expected to be in the format:
            field_type,field_name
        (You can change the delimiter to anything else you prefer.)
        """
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Load Field List", self.default_dir,
            "Text Files (*.txt);;All Files (*)", options=options
        )
        if not file_name:
            return

        loaded_fields = []
        with open(file_name, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                # Example format: Type A,Field A2
                if ',' in line:
                    f_type, f_name = line.split(',', 1)
                    loaded_fields.append((f_type, f_name))
                else:
                    # If the file doesn't have the correct format,
                    # you could handle it here or skip.
                    pass

        self.selected_fields = loaded_fields
        self.update_table()

        self.filename = os.path.basename(file_name)
        self.unsaved_changes = False
        self.update_window_title()

        # Bring the dialog to front
        self.raise_()
        self.activateWindow()
        self.show()

    def save_selection(self):
        """
        Saves the current selected fields (field_type, field_name) into a text file.

        Each line will be in the format:
            field_type,field_name
        """
        if not self.selected_fields:
            QMessageBox.warning(self, 'Warning', 'No fields to save.')
            return

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Field List", self.default_dir,
            "Text Files (*.txt);;All Files (*)", options=options
        )
        if not file_name:
            return

        with open(file_name, 'w', encoding='utf-8') as file:
            for (field_type, field_name) in self.selected_fields:
                file.write(f"{field_type},{field_name}\n")

        QMessageBox.information(self, 'Success', 'Field list saved successfully.')
        self.filename = os.path.basename(file_name)
        self.unsaved_changes = False
        self.update_window_title()

        self.raise_()
        self.activateWindow()
        self.show()

    # --------------------------------------------------------------------------
    # Done / Cancel
    # --------------------------------------------------------------------------
    def done_selection(self):
        """
        Executes when 'Done' button is clicked.  
        If unsaved changes exist, prompt the user to save or discard.
        """
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them before exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                self.accept()
            elif reply == QMessageBox.StandardButton.No:
                self.accept()
            else:
                # Cancel: do nothing, stay in dialog
                pass
        else:
            self.accept()

    def cancel_selection(self):
        """
        Handles the 'Cancel' button click.
        If unsaved changes exist, prompt user to save or discard.
        """
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them before exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                self.reject()
            elif reply == QMessageBox.StandardButton.No:
                self.reject()
            else:
                # Cancel: do nothing, stay in dialog
                pass
        else:
            self.reject()

    # --------------------------------------------------------------------------
    # Close event override (X button)
    # --------------------------------------------------------------------------
    def closeEvent(self, event):
        """
        Overrides the close event to check for unsaved changes.
        """
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_selection()
                event.accept()
            elif reply == QMessageBox.StandardButton.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
