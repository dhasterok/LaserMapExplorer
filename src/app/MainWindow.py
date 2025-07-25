import sys, os, re, copy, random, darkdetect
from datetime import datetime
from PyQt6.QtCore import ( Qt, QTimer, QUrl, QSize, QRectF )
from PyQt6.QtWidgets import (
    QCheckBox, QTableWidgetItem, QVBoxLayout, QGridLayout,
    QMessageBox, QHeaderView, QMenu, QFileDialog, QWidget, QToolButton,
    QDialog, QLabel, QTableWidget, QInputDialog, QAbstractItemView,
    QSplashScreen, QApplication, QMainWindow, QSizePolicy
) # type: ignore
from PyQt6.QtGui import ( QIntValidator, QDoubleValidator, QPixmap, QFont, QIcon ) 
from src.common.CustomWidgets import CustomCheckButton
from src.app.UITheme import UIThemes
import numpy as np
import pandas as pd
pd.options.mode.copy_on_write = True
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
import cmcrameri as cmc
from src.common.LamePlot import plot_map_mpl, plot_small_histogram, plot_histogram, plot_correlation, get_scatter_data, plot_scatter, plot_ternary_map, plot_ndim, plot_pca, plot_clusters, cluster_performance_plot
from src.app.LameIO import LameIO
import src.common.csvdict as csvdict
from src.common.radar import Radar
from src.ui.MainWindow import Ui_MainWindow
from src.app.FieldLogic import AnalyteDialog, FieldDialog
from src.common.TableFunctions import TableFcn as TableFcn
from src.app.PlotTree import PlotTree
from src.app.CanvasWidget import CanvasWidget
from src.app.DataAnalysis import ClusterPage, DimensionalReductionPage
from src.common.Masking import MaskDock
from src.app.CropImage import CropTool
from src.app.ImageProcessing import ImageProcessingUI
from src.app.LamePlotUI import HistogramUI, CorrelationUI, ScatterUI, NDimUI
from src.app.StylingUI import StylingDock
from src.app.Preprocessing import PreprocessingUI
from src.app.Profile import Profiling, ProfileDock
from src.common.Regression import RegressionDock
from src.common.Polygon import PolygonManager
from src.app.SpotTools import SpotPage
from src.app.SpecialTools import SpecialPage
from src.common.ReSTNotes import Notes
from src.common.Browser import Browser
from src.app.Workflow import Workflow
from src.app.InfoViewer import InfoDock
from src.app.config import BASEDIR, ICONPATH, SSPATH, load_stylesheet
from src.common.colorfunc import get_hex_color, get_rgb_color
import src.app.config as config
from src.app.help_mapping import create_help_mapping
from src.common.Logger import LoggerConfig, auto_log_methods, log, no_log, LoggerDock
from src.common.Calculator import CalculatorDock
from src.app.AppData import AppData
#import src.radar_factory
#from src.ui.PreferencesWindow import Ui_PreferencesWindow
#from datetime import datetimec

# to prevent segmentation error at startup
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
# setConfigOption('imageAxisOrder', 'row-major') # best performance

@auto_log_methods(logger_key='Main')
class MainWindow(QMainWindow, Ui_MainWindow):
    """Creates the MainWindow

    Attributes
    ----------
    app_data : AppData
        Properties and methods for the calling UI, in this case, MainWindow
    data : dict
        Dictionary of samples with sample IDs as keys
    plot_style : StylingDock
        Properties and methods for styling plots and updating the Styling Dock
    """
    def __init__(self, app, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.app = app

        self.setupUi(self)

        # this flag sets whether the plot can be updated.  Mostly off during change_sample
        self.plot_flag = False
        self.profile_state = False # True if profiling toggle is set to on
        self.polygon_state = False # True if polygon toggle is set to on
        self.field_control_settings = {} # a dictionary that keeps track of UI data for each toolBox page

        # setup initial logging options
        self.logger_options = {
                'Main': True,
                'UI': True,
                'IO': True,
                'Data': True,
                'Analysis': True,
                'Canvas': True,
                'Plot': True,
                'Style': True,
                'Tree': True,
                'Mask': True,
                'Calculator': True,
                'Image': True,
                'Polygon': True,
                'Profile': True,
                'Selector': True,
                'Browser': True,
                'Error' : True,
                'Warning' : True,
            }
        LoggerConfig.set_options(self.logger_options)

        self.help_mapping = create_help_mapping(self)

        # The data dictionary will hold the data with a key for each sample
        self.data = {}

        self.plot_info = {}
        # until there is actually some data to store, disable certain widgets
        self.toggle_data_widgets()

        # initialize the application data
        #   contains:
        #       critical UI properties
        #       notifiers when properties change
        #       data structure and properties (DataHandling), data
        self.app_data = AppData(self.data)

        # initialize the styling data and dock
        self.plot_style = StylingDock(self)

        self.connect_app_data_observers(self.app_data)

        self.connect_logger()
        self.init_ui()
        self.connect_actions()
        self.connect_widgets()

        # holds the custom field names and formulas set by the user in the calculator
        self.calc_dict = {}

        #self.init_canvas_widget()

        self.mpl_canvas = None # will hold the current canvas

    @no_log
    def connect_logger(self):
        """Connects user interactions with widgets to the logger"""        
        ## MainWindow toolbar
        self.actionOpenSample.triggered.connect(lambda: log("actionOpenSample", prefix="UI"))
        self.actionOpenDirectory.triggered.connect(lambda: log("actionOpenDirectory", prefix="UI"))
        self.actionOpenProject.triggered.connect(lambda: log("actionOpenProject", prefix="UI"))
        self.actionSaveProject.triggered.connect(lambda: log("actionSaveProject", prefix="UI"))
        self.comboBoxSampleId.activated.connect(lambda: log(f"comboBoxSampleId, value=[{self.comboBoxSampleId.currentText()}]", prefix="UI"))
        self.actionSelectAnalytes.triggered.connect(lambda: log("actionSelectAnalytes", prefix="UI"))
        self.actionWorkflowTool.triggered.connect(lambda: log("actionWorkflowTool", prefix="UI"))
        self.actionFullMap.triggered.connect(lambda: log("actionFullMap", prefix="UI"))
        self.actionCrop.triggered.connect(lambda: log("actionCrop", prefix="UI"))
        self.actionSwapAxes.triggered.connect(lambda: log("actionSwapAxes", prefix="UI"))
        self.actionNoiseReduction.triggered.connect(lambda: log("actionNoiseReduction", prefix="UI"))
        self.actionClearFilters.triggered.connect(lambda: log("actionClearFilters", prefix="UI"))
        self.actionFilters.triggered.connect(lambda: log("actionFilters", prefix="UI"))
        self.actionPolygonMask.triggered.connect(lambda: log("actionPolygonMask", prefix="UI"))
        self.actionClusterMask.triggered.connect(lambda: log("actionClusterMask", prefix="UI"))
        self.actionUpdatePlot.triggered.connect(lambda: log("actionUpdatePlot", prefix="UI"))
        self.actionSavePlotToTree.triggered.connect(lambda: log("actionSavePlotToTree", prefix="UI"))
        self.actionNotes.triggered.connect(lambda: log("actionNotes", prefix="UI"))
        self.actionCalculator.triggered.connect(lambda: log("actionCalculator", prefix="UI"))
        self.actionReportBug.triggered.connect(lambda: log("actionReportBug", prefix="UI"))
        self.actionHelp.triggered.connect(lambda: log("actionHelp", prefix="UI"))
        self.actionReset.triggered.connect(lambda: log("actionReset", prefix="UI"))
        self.actionViewMode.triggered.connect(lambda: log("actionViewMode", prefix="UI"))

        ## left/control toolbox
        # plot and axes controls
        self.toolBox.currentChanged.connect(lambda: log(f"toolBox, index=[{self.toolBox.itemText(self.toolBox.currentIndex())}]",prefix="UI"))
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

        # preprocessing controls
        self.toolButtonScaleEqualize.clicked.connect(lambda: log(f"toolButtonScaleEqualize value=[{self.toolButtonScaleEqualize.isChecked()}]", prefix="UI"))
        self.checkBoxShowHistCmap.checkStateChanged.connect(lambda: log(f"checkBoxShowHistCmap value=[{self.checkBoxShowHistCmap.isChecked()}]", prefix="UI"))
        
        ## right/plot tree dock
        self.comboBoxRefMaterial.activated.connect(lambda: log(f"comboBoxRefMaterial value=[{self.comboBoxRefMaterial.currentText()}]", prefix="UI"))

        ## right/styling toolbox

        ## status bar



    def init_ui(self):
        """Initialize the UI"""
        # Add this line to set the size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)

        self.toolBar.insertWidget(self.actionSelectAnalytes,self.widgetSampleSelect)

        # Add the button to the status bar
        self.labelInvalidValues = QLabel("Negative/zeros: False, NaNs: False")
        self.statusbar.addPermanentWidget(self.labelInvalidValues)

        # Create a button to hide/show the dock
        self.toolButtonLeftDock = CustomCheckButton(QIcon(':/resources/icons/icon-left_toolbar_hide-64.svg'), QIcon(':/resources/icons/icon-left_toolbar_show-64.svg'), parent=self)
        self.toolButtonRightDock = CustomCheckButton(QIcon(':/resources/icons/icon-right_toolbar_hide-64.svg'), QIcon(':/resources/icons/icon-right_toolbar_show-64.svg'), parent=self)
        self.toolButtonBottomDock = CustomCheckButton(QIcon(':/resources/icons/icon-bottom_toolbar_hide-64.svg'), QIcon(':/resources/icons/icon-bottom_toolbar_show-64.svg'), parent=self)

        self.dockWidgetLeftToolbox.show()
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidgetLeftToolbox)
        self.dockWidgetLeftToolbox.setFloating(False)
        self.open_plot_tree()
        self.dockWidgetStyling.show()
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockWidgetStyling)
        self.dockWidgetStyling.setFloating(False)

        self.toolButtonLeftDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.dockWidgetLeftToolbox, button=self.toolButtonLeftDock))
        self.toolButtonRightDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.dockWidgetStyling, button=self.toolButtonRightDock))

        self.statusbar.addPermanentWidget(self.toolButtonLeftDock)
        self.statusbar.addPermanentWidget(self.toolButtonBottomDock)
        self.statusbar.addPermanentWidget(self.toolButtonRightDock)

        # left toolbox
        #-------------------------
        self.actionSpotTools.setChecked(False)
        self.actionSpotTools.triggered.connect(self.toggle_spot_tab)
        self.actionImportSpots.setVisible(False)

        self.actionSpecialTools.setChecked(False)
        self.actionSpecialTools.triggered.connect(self.toggle_special_tab)

        self.actionRegression.setChecked(False)
        self.actionRegression.triggered.connect(self.open_regression)

        # code is more resilient if toolbox indices for each page is not hard coded
        # will need to change case text if the page text is changed

        # Initialize dimentionality reduction class 
        self.DimRedPage = DimensionalReductionPage(parent=self)

        # Initialize class from DataAnalysis
        self.ClusterPage = ClusterPage(parent=self)

        self.reindex_left_tab()
        self.reindex_style_tab()
        self.reindex_canvas_tab()

        self.toolBox.setCurrentIndex(self.left_tab['sample'])

        self.canvas_widget = CanvasWidget(self)


        # Initialize PreprocessingUI
        self.preprocess = PreprocessingUI(self)

        # Initialize LaMEPlotUI
        self.histogram = HistogramUI(self)
        self.correlation = CorrelationUI(self)
        self.scatter = ScatterUI(self)
        self.ndimensional = NDimUI(self)

        self.init_tabs(enable=False)

        # connect actions to docks
        #-------------------------
        self.actionFilters.triggered.connect(lambda _: self.open_mask_dock('filter'))
        self.actionPolygons.triggered.connect(lambda _: self.open_mask_dock('polygon'))
        self.actionClusters.triggered.connect(lambda _: self.open_mask_dock('cluster'))
        self.actionProfiles.triggered.connect(lambda _: self.open_profile())
        self.actionCalculator.triggered.connect(lambda _: self.open_calculator())
        self.open_calculator()
        self.calculator.hide()
        self.actionNotes.triggered.connect(lambda _: self.open_notes())
        self.actionLogger.triggered.connect(lambda _: self.open_logger())
        self.actionWorkflowTool.triggered.connect(lambda _: self.open_workflow())
        self.info_tab = {}
        self.actionInfo.triggered.connect(lambda _: self.open_info_dock())

        self.io = LameIO(parent=self, connect_actions=True)

        self.actionHelp.setCheckable(True)
        self.actionHelp.toggled.connect(lambda _: self.toggle_help_mode())

        # initialize used classes
        self.crop_tool = CropTool(self)
        self.table_fcn = TableFcn(self)
        #self.clustertool = Clustering(self)
        self.noise_reduction = ImageProcessingUI(self)

        self.actionQuit_LaME.triggered.connect(self.quit)

        # For light and dark themes, connects actionViewMode
        self.theme = UIThemes(self.app, self)

    def connect_actions(self):
        self.actionReportBug.triggered.connect(lambda _: self.open_browser('report_bug'))
        self.actionUserGuide.triggered.connect(lambda _: self.open_browser('user_guide'))
        self.actionTutorials.triggered.connect(lambda _: self.open_browser('tutorials'))
        self.actionSelectAnalytes.triggered.connect(lambda _: self.open_select_analyte_dialog())

    def connect_widgets(self):
        """ Connects widgets to their respective methods and actions.
        
        This method sets up the connections for various widgets in the MainWindow,
        including the toolBox, comboBoxes, and buttons. It ensures that user interactions
        with these widgets trigger the appropriate methods for updating the UI and data.
        """
        self.toolBox.currentChanged.connect(lambda: self.canvasWindow.setCurrentIndex(self.canvas_tab['sv']))
        self.toolBox.currentChanged.connect(self.toolbox_changed)

        self.comboBoxSampleId.activated.connect(self.update_sample_id)

        self.actionFullMap.triggered.connect(self.preprocess.reset_crop)
        self.toolButtonSwapResolution.clicked.connect(self.preprocess.update_swap_resolution)
        self.toolButtonPixelResolutionReset.clicked.connect(self.preprocess.reset_pixel_resolution)


        self.comboBoxFieldTypeC.popup_callback = lambda: self.update_field_type_combobox_options(
            self.comboBoxFieldTypeC,
            self.comboBoxFieldC,
            ax=3,
            user_activated=True
            )
        self.comboBoxFieldTypeC.currentTextChanged.connect(lambda: self.plot_style.update_field_type(ax=3))
        self.comboBoxFieldC.popup_callback = lambda: self.update_field_combobox_options(
            self.comboBoxFieldC,
            self.comboBoxFieldTypeC,
            spinbox=self.spinBoxFieldC,
            ax=3,
            user_activated=True
            )
        self.comboBoxFieldC.currentTextChanged.connect(lambda: self.plot_style.update_field(ax=3))
        # update spinbox associated with map/color field
        self.spinBoxFieldC.valueChanged.connect(lambda: self.field_spinbox_changed(ax=3))

        self.comboBoxFieldTypeX.popup_callback = lambda: self.update_field_type_combobox_options(
            self.comboBoxFieldTypeX,
            self.comboBoxFieldX,
            ax=0,
            user_activated=True
            )
        self.comboBoxFieldTypeX.currentTextChanged.connect(lambda: self.plot_style.update_field_type(ax=0))
        self.comboBoxFieldX.popup_callback = lambda: self.update_field_combobox_options(
            self.comboBoxFieldX,
            self.comboBoxFieldTypeX,
            spinbox=self.spinBoxFieldX,
            ax=0,
            user_activated=True
            )
        self.comboBoxFieldX.currentTextChanged.connect(lambda: self.plot_style.update_field(ax=0))
        # update spinbox associated with map/color field
        self.spinBoxFieldX.valueChanged.connect(lambda: self.field_spinbox_changed(ax=0))

        self.comboBoxFieldTypeY.popup_callback = lambda: self.update_field_type_combobox_options(
            self.comboBoxFieldTypeY,
            self.comboBoxFieldY,
            ax=1,
            user_activated=True
            )
        self.comboBoxFieldTypeY.currentTextChanged.connect(lambda: self.plot_style.update_field_type(ax=1))
        self.comboBoxFieldY.popup_callback = lambda: self.update_field_combobox_options(
            self.comboBoxFieldY,
            self.comboBoxFieldTypeY,
            spinbox=self.spinBoxFieldY,
            ax=1,
            user_activated=True
            )
        self.comboBoxFieldY.currentTextChanged.connect(lambda: self.plot_style.update_field(ax=1))
        # update spinbox associated with map/color field
        self.spinBoxFieldY.valueChanged.connect(lambda: self.field_spinbox_changed(ax=1))

        self.comboBoxFieldTypeZ.popup_callback = lambda: self.update_field_type_combobox_options(
            self.comboBoxFieldTypeZ,
            self.comboBoxFieldZ,
            ax=2,
            user_activated=True
            )
        self.comboBoxFieldTypeZ.currentTextChanged.connect(lambda: self.plot_style.update_field_type(ax=2))
        self.comboBoxFieldZ.popup_callback = lambda: self.update_field_combobox_options(
            self.comboBoxFieldZ,
            self.comboBoxFieldTypeZ,
            spinbox=self.spinBoxFieldZ,
            ax=2,
            user_activated=True
            )
        self.comboBoxFieldZ.currentTextChanged.connect(lambda: self.plot_style.update_field(ax=2))
        self.spinBoxFieldZ.valueChanged.connect(lambda: self.field_spinbox_changed(ax=2))

        
        self.comboBoxRefMaterial.addItems(self.app_data.ref_list.values)          # Select analyte Tab
        self.comboBoxRefMaterial.activated.connect(lambda: self.update_ref_chem_combobox(self.comboBoxRefMaterial.currentText())) 
        self.comboBoxRefMaterial.setCurrentIndex(self.app_data.ref_index)

        # N-dim table
        header = self.tableWidgetNDim.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)




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
        if self.app_data.sample_id == '' or self.plot_style.plot_type == '':
            return
            
        old_list = parentbox.allItems()
        old_field_type = parentbox.currentText()

        field_dict = self.app_data.field_dict
        # get field type options from app_data
        new_list = self.app_data.get_field_type_list(ax, self.plot_style) 


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
            
        field_list = self.app_data.get_field_list(field_type)

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


    def init_tabs(self, enable=False):
        """Enables/disables UI for user.

        Enables control (left) toolbox, mask dock, info dock, and calculator.

        Parameters
        ----------
        enable : bool, optional
            Enables/disables select UI controls for user, by default False
        """
        self.toolBox.setCurrentIndex(self.left_tab['sample'])

        if not enable:
            self.plot_style.init_field_widgets(self.plot_style.plot_axis_dict, self.plot_style.axis_widget_dict)

            self.PreprocessPage.setEnabled(False)
            self.SelectAnalytePage.setEnabled(False)
            if hasattr(self, "spot_tools"):
                self.spot_tools.setEnabled(False)
            self.ScatterPage.setEnabled(False)
            self.NDIMPage.setEnabled(False)
            self.DimRedPage.setEnabled(False)
            self.ClusterPage.setEnabled(False)
            if hasattr(self, "special_tools"):
                self.special_tools.setEnabled(False)
            if hasattr(self, "mask_dock"):
                self.mask_dock.tabWidgetMask.setTabEnabled(0,False)
                self.mask_dock.tabWidgetMask.setTabEnabled(1,False)
                self.mask_dock.tabWidgetMask.setTabEnabled(2,False)
            if hasattr(self, "info_dock"):
                self.info_dock.setEnabled(False)
            if hasattr(self, "calculator"):
                self.calculator.setEnabled(False)
            self.toolBoxStyle.setEnabled(False)
        else:
            self.PreprocessPage.setEnabled(True)
            self.SelectAnalytePage.setEnabled(True)
            if hasattr(self,"spot_tools"):
                self.spot_tools.setEnabled(True)
            self.ScatterPage.setEnabled(True)
            self.NDIMPage.setEnabled(True)
            self.DimRedPage.setEnabled(True)
            self.ClusterPage.setEnabled(True)
            if hasattr(self,"special_tools"):
                self.special_tools.setEnabled(True)
            if hasattr(self, "mask_dock"):
                self.mask_dock.tabWidgetMask.setTabEnabled(0,True)
                self.mask_dock.tabWidgetMask.setTabEnabled(1,True)
                self.mask_dock.tabWidgetMask.setTabEnabled(2,True)
            if hasattr(self, "info_dock"):
                self.info_dock.setEnabled(True)
            if hasattr(self, "calculator"):
                self.calculator.setEnabled(True)
            self.toolBoxStyle.setEnabled(True)

    def toolbox_changed(self, tab_id=None):
        """Updates styles associated with toolbox page

        Executes on change of ``MainWindow.toolBox.currentIndex()``.  Updates style related widgets.
        """
        if self.app_data.sample_id == '':
            return

        if not tab_id:
            tab_id = self.toolBox.currentIndex()

        data = self.data[self.app_data.sample_id]

        # run clustering before changing plot_type if user selects clustering tab
        if tab_id == self.left_tab['cluster'] :
            self.ClusterPage.compute_clusters_update_groups()
            plot_clusters(self,data,self.app_data,self.plot_style)
        # run dim red before changing plot_type if user selects dim red tab
        if tab_id == self.left_tab['multidim'] :
            if self.app_data.update_pca_flag or not data.processed_data.match_attribute('data_type','pca score'):
                self.DimRedPage.compute_dim_red(data, self.app_data)
        # update the plot type comboBox options
        self.update_plot_type_combobox_options()
        self.plot_style.plot_type = self.field_control_settings[tab_id]['plot_list'][self.field_control_settings[tab_id]['saved_index']]

        if self.toolBox.currentIndex() == self.left_tab['cluster']:
            self.ClusterPage.toggle_cluster_widgets()

        # If canvasWindow is set to SingleView, update the plot
        if self.canvasWindow.currentIndex() == self.canvas_tab['sv']:
        # trigger update to plot
            self.plot_style.schedule_update()

    def quit(self):
        """Shutdown function

        Saves necessary files and then executes close() function.
        """        
        # save files

        self.close()

    def open_tab(self, tab_name):
        """Opens specified toolBox tab

        Opens the specified tab in ``MainWindow.toolbox``

        Parameters
        ----------
        tab_name : str
            opens tab, values: 'samples', 'preprocess', 'spot data', 'filter',
            'scatter', 'ndim', pca', 'filters','clustering', 'clusters', 'polygons',
            'profiles', 'special'
        """
        match tab_name.lower():
            case 'samples':
                self.toolBox.setCurrentIndex(self.left_tab['sample'])
                self.toolBox.show()
            case 'preprocess':
                self.toolBox.setCurrentIndex(self.left_tab['process'])
                self.toolBox.show()
            case 'spot data':
                self.toolBox.setCurrentIndex(self.left_tab['spot'])
                self.toolBox.show()
            case 'polygons':
                self.mask_dock.tabWidgetMask.setCurrentIndex(self.mask_tab['polygon'])
                self.mask_dock.show()
            case 'scatter':
                self.toolBox.setCurrentIndex(self.left_tab['scatter'])
                self.toolBox.show()
            case 'ndim':
                self.toolBox.setCurrentIndex(self.left_tab['ndim'])
                self.toolBox.show()
            case 'multidimensional':
                self.toolBox.setCurrentIndex(self.left_tab['multidim'])
                self.toolBox.show()
            case 'filters':
                self.mask_dock.tabWidgetMask.setCurrentIndex(self.mask_tab['filter'])
                self.mask_dock.tabWidgetMask.show()
            case 'clustering':
                self.toolBox.setCurrentIndex(self.left_tab['cluster'])
                self.toolBox.show()
            case 'clusters':
                self.mask_dock.tabWidgetMask.setCurrentIndex(self.mask_tab['cluster'])
                self.mask_dock.tabWidgetMask.show()
            case 'special':
                self.toolBox.setCurrentIndex(self.left_tab['special'])
                self.toolBox.show()
            case 'info':
                self.info_dock.tabWidgetInfo.setCurrentIndex(self.info_tab['info'])
                self.info_dock.tabWidgetInfo.show()

    def toggle_dock_visibility(self, dock, button=None):
        """Toggles the visibility and checked state of a dock and its controlling button

        _extended_summary_

        Parameters
        ----------
        dock : QDockWidget
            Dock widget to show or hide.
        button : QToolButton, QPushButton, QAction, optional
            Changes the checked state of button, by default None
        """        
        if dock.isVisible():
            dock.hide()
            if button is not None:
                button.setChecked(False)
        else:
            dock.show()
            if button is not None:
                button.setChecked(True)

    def toggle_data_widgets(self):
        """Disables/enables widgets if self.data is empty."""
        if self.data:
            self.actionSelectAnalytes.setEnabled(True)
            self.actionFullMap.setEnabled(True)
            self.actionCrop.setEnabled(True)
            self.actionSwapAxes.setEnabled(True)
            self.actionNoiseReduction.setEnabled(True)
            self.actionFilters.setEnabled(True)
            self.actionPolygons.setEnabled(True)
            self.actionClusters.setEnabled(True)
            self.actionProfiles.setEnabled(True)
            self.actionInfo.setEnabled(True)
            self.actionNotes.setEnabled(True)
            self.actionReset.setEnabled(True)
            self.actionUpdatePlot.setEnabled(True)
            self.actionSavePlotToTree.setEnabled(True)
        else:
            self.actionSelectAnalytes.setEnabled(False)
            self.actionFullMap.setEnabled(False)
            self.actionCrop.setEnabled(False)
            self.actionSwapAxes.setEnabled(False)
            self.actionNoiseReduction.setEnabled(False)
            self.actionFilters.setEnabled(False)
            self.actionPolygons.setEnabled(False)
            self.actionClusters.setEnabled(False)
            self.actionProfiles.setEnabled(False)
            self.actionInfo.setEnabled(False)
            self.actionNotes.setEnabled(False)
            self.actionReset.setEnabled(False)
            self.actionUpdatePlot.setEnabled(False)
            self.actionSavePlotToTree.setEnabled(False)

    def toggle_help_mode(self):
        """Toggles help mode

        Toggles ``MainWindow.actionHelp``, when checked, the cursor will change so indicates help tool is active.
        """        
        if self.actionHelp.isChecked():
            self.setCursor(Qt.CursorShape.WhatsThisCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)


    

    def connect_app_data_observers(self, app_data):
        #app_data.add_observer("sort_method", self.update_sort_method)
        app_data.add_observer("ref_chem", self.update_ref_index_combobox)
        app_data.add_observer("sample_list", self.update_sample_list_combobox)
        app_data.add_observer("sample_id", self.update_sample_id_combobox)
        app_data.add_observer("equalize_color_scale", self.update_equalize_color_scale_toolbutton)
        app_data.add_observer("x_field_type", self.plot_style.update_field_type)
        app_data.add_observer("x_field", self.plot_style.update_field)
        app_data.add_observer("y_field_type", self.plot_style.update_field_type)
        app_data.add_observer("y_field", self.plot_style.update_field)
        app_data.add_observer("z_field_type", self.plot_style.update_field_type)
        app_data.add_observer("z_field", self.plot_style.update_field)
        app_data.add_observer("c_field_type", self.plot_style.update_field_type)
        app_data.add_observer("c_field", self.plot_style.update_field)
        app_data.add_observer("norm_reference", self.update_norm_reference_combobox)
        app_data.add_observer("selected_clusters", self.update_selected_clusters_spinbox)

    def toggle_spot_tab(self, *args, **kwargs):
        #self.actionSpotTools.toggle()
        if self.actionSpotTools.isChecked():
            # add spot page to MainWindow.toolBox
            self.spot_tools = SpotPage(self.left_tab['sample'], self)
            self.actionImportSpots.setVisible(True)
        else:
            self.toolBox.removeItem(self.left_tab['spot'])
            self.actionImportSpots.setVisible(False)
        self.reindex_left_tab()

    def toggle_special_tab(self, *args, **kwargs):
        if self.actionSpecialTools.isChecked():
            self.special_tools = SpecialPage(self.left_tab['cluster'], self)
        else:
            self.toolBox.removeItem(self.left_tab['special'])
        self.reindex_left_tab()

    def reindex_left_tab(self):
        """Resets the dictionaries for the Control Toolbox and plot types.
        
        The dictionary ``self.left_tab retains the index for each of the Control Toolbox pages.  This way they
        can be easily referenced by name.  At the same time, the dictionary ``self.field_control_settings`` retains the plot
        types available to each page of the control toolbox and the override options when polygons or profiles
        are active."""
        # create diciontary for left tabs
        self.left_tab = {}
        self.left_tab.update({'spot': None})
        self.left_tab.update({'special': None})

        # create dictionaries for default plot styles
        self.field_control_settings = {
            -1: {'saved_index': 0,
            'plot_list': ['field map'],
            'label': ['','','','Map'],
            'saved_field_type': [None, None, None, None],
            'saved_field': [None, None, None, None]}
        } # -1 is for digitizing polygons and profiles

        for tid in range(0,self.toolBox.count()):
            match self.toolBox.itemText(tid).lower():
                case 'preprocess':
                    self.left_tab.update({'process': tid})
                    self.field_control_settings.update(
                        {self.left_tab['process']: {
                            'saved_index': 0,
                            'plot_list': ['field map', 'gradient map'],
                            'label': ['','','','Map'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
                    )
                case 'field viewer':
                    self.left_tab.update({'sample': tid})
                    self.field_control_settings.update(
                        {self.left_tab['sample']: {
                            'saved_index': 0,
                            'plot_list': ['field map', 'histogram', 'correlation'],
                            'label': ['','','','Map'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
                    )
                case 'spot data':
                    self.left_tab.update({'spot': tid})
                    self.field_control_settings.update(
                        {self.left_tab['spot']: {
                            'saved_index': 0,
                            'plot_list': ['field map', 'gradient map'],
                            'label': ['','','','Map'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]}
                        }
                    )
                case 'scatter and heatmaps':
                    self.left_tab.update({'scatter': tid})
                    self.field_control_settings.update(
                        {self.left_tab['scatter']: {
                            'saved_index': 0,
                            'plot_list': ['scatter', 'heatmap', 'ternary map'],
                            'label': ['X','Y','Z','Color'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
                    )
                case 'n-dim':
                    self.left_tab.update({'ndim': tid})
                    self.field_control_settings.update(
                        {self.left_tab['ndim']: {
                            'saved_index': 0,
                            'plot_list': ['TEC', 'Radar'],
                            'label': ['','','','Color'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
                    )
                case 'dimensional reduction':
                    self.left_tab.update({'multidim': tid})
                    self.field_control_settings.update(
                        {self.left_tab['multidim']: {
                            'saved_index': 0,
                            'plot_list': ['variance','basis vectors','dimension scatter','dimension heatmap','dimension score map'],
                            'label': ['PC','PC','','Color'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
                    )
                case 'clustering':
                    self.left_tab.update({'cluster': tid})
                    self.field_control_settings.update(
                        {self.left_tab['cluster']: {
                            'saved_index': 0,
                            'plot_list': ['cluster map', 'cluster score map', 'cluster performance'],
                            'label': ['','','',''],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
                    )
                case 'p-t-t functions':
                    self.left_tab.update({'special': tid})
                    self.field_control_settings.update(
                        {self.left_tab['special']: {
                            'saved_index': 0,
                            'plot_list': ['field map', 'gradient map', 'cluster score map', 'dimension score map', 'profile'],
                            'label': ['','','','Map'],
                            'saved_field_type': [None, None, None, None],
                            'saved_field': [None, None, None, None]
                        }}
                    )


    def reindex_style_tab(self):
        self.style_tab = {}
        for tid in range(self.toolBoxStyle.count()):
            match self.toolBoxStyle.itemText(tid).lower():
                case 'axes and labels':
                    self.style_tab.update({'axes': tid})
                case 'annotations and scale':
                    self.style_tab.update({'text': tid})
                case 'markers and lines':
                    self.style_tab.update({'markers': tid})
                case 'coloring':
                    self.style_tab.update({'colors': tid})
                case 'regression':
                    self.style_tab.update({'regression': tid})

    def reindex_canvas_tab(self):
        self.canvas_tab = {}
        for tid in range(self.canvasWindow.count()):
            match self.canvasWindow.tabText(tid).lower():
                case 'single view':
                    self.canvas_tab.update({'sv': tid})
                case 'multi view':
                    self.canvas_tab.update({'mv': tid})
                case 'quick view':
                    self.canvas_tab.update({'qv': tid})

    # -------------------------------
    # UI update functions
    # Executed when a property is changed
    # -------------------------------

    #def update_sort_method(self, new_method):
    #    self.plot_tree.sort_tree(new_method)
    #    self.data[self.app_data.sample_id].sort_data(new_method)

    def update_sample_list_combobox(self, new_sample_list):
        """Updates ``MainWindow.comboBoxSampleID.items()``

        Called as an update to ``app_data.sample_list``.  Updates sample ID list.

        Parameters
        ----------
        value : str
            New sample ID.
        """
        # Populate the comboBoxSampleId with the sample names
        self.comboBoxSampleId.clear()
        self.comboBoxSampleId.addItems(new_sample_list)

        self.change_directory()

    def update_sample_id_combobox(self, new_sample_id):
        """Updates ``MainWindow.comboBoxSampleID.currentText()``

        Called as an update to ``app_data.sample_id``.  Updates sample ID and calls ``change_sample``

        Parameters
        ----------
        value : str
            New sample ID.
        """
        if new_sample_id == self.comboBoxSampleId.currentText():
            return
        self.comboBoxSampleId.setCurrentText(new_sample_id)

        
        self.change_sample()

        # self.profile_dock.profiling.add_samples()
        # self.polygon.add_samples()

    def change_directory(self):
        # this will replace reset_analysis
        pass


    def change_sample(self):
        """Changes sample and plots first map.
        
        The UI is updated with a newly or previously loaded sample data."""
        # set plot flag to false, allow plot to update only at the end
        self.plot_flag = False

        if self.app_data.sample_id not in self.data:
            self.io.initialize_sample_object(outlier_method=self.comboBoxOutlierMethod.currentText(), negative_method = self.comboBoxNegativeMethod.currentText())
            self.preprocess.connect_data_observers(self.data[self.app_data.sample_id])
            # enable widgets that require self.data not be empty
            self.toggle_data_widgets()
            
            # add sample to the plot tree
            self.plot_tree.add_sample(self.app_data.sample_id)
            self.plot_tree.update_tree()

        self.update_mask_and_profile_widgets()

        # sort data
        self.plot_tree.sort_tree(self.app_data.sort_method)

        # precalculate custom fields
        if hasattr(self, "calculator") and self.calculator.precalculate_custom_fields:
            for name in self.calc_dict:
                if name in self.data[self.app_data.sample_id].processed_data.columns:
                    continue
                self.calculator.comboBoxFormula.setCurrentText(name)
                self.calculator.calculate_new_field(save=False)

        # reset flags
        self.app_data.update_cluster_flag = True
        self.app_data.update_pca_flag = True

        # update ui
        self.update_ui_on_sample_change()
        self.update_widget_data_on_sample_change()

        if self.plot_style.plot_type != 'field map':
            self.plot_style.plot_type = 'field map'

        if 'Analyte' in self.app_data.field_dict:
            self.app_data.c_field_type = 'Analyte'
            self.app_data.c_field = self.app_data.field_dict['Analyte'][0]
        elif 'Ratio' in self.app_data.field_dict:
            self.app_data.c_field_type = 'Ratio'
            self.app_data.c_field = self.app_data.field_dict['Ratio'][0]
        else:
            self.app_data.c_field_type = self.app_data.field_dict[0]
            self.app_data.c_field = self.app_data.field_dict[self.app_data.field_dict[0]][0]

        # allow plots to be updated again
        self.plot_flag = True

        # trigger update to plot
        self.plot_style.schedule_update()

    def update_ui_on_sample_change(self):
        # reset all plot types on change of tab to the first option
        for key in self.field_control_settings:
            self.field_control_settings[key]['saved_index'] = 0

        self.init_tabs(enable=True)

        self.toolButtonAutoScale.clicked.connect(lambda: self.data[self.app_data.sample_id].auto_scale_value(self.toolButtonAutoScale.isChecked()))

        # update slot connections that depend on the sample
        self.toolButtonOutlierReset.clicked.connect(lambda: self.data[self.app_data.sample_id].reset_data_handling(self.comboBoxOutlierMethod.currentText(), self.comboBoxNegativeMethod.currentText()))

        # add spot data
        if hasattr(self, "spot_tab") and not self.data[self.app_data.sample_id].spotdata.empty:
            self.io.populate_spot_table()

        # update docks
        if hasattr(self, "mask_dock"):
            self.update_mask_dock()

        if hasattr(self,'notes'):
            # change notes file to new sample.  This will initiate the new file and autosave timer.
            self.notes.notes_file = os.path.join(self.app_data.selected_directory,self.app_data.sample_id+'.rst')

        if hasattr(self,"info_dock"):
            self.info_dock.update_tab_widget()

        # set canvas to single view
        self.canvasWindow.setCurrentIndex(self.canvas_tab['sv'])
        self.canvas_widget.canvas_changed()
        
        # set toolbox tab indexes
        self.toolBoxStyle.setCurrentIndex(0)
        self.toolBox.setCurrentIndex(self.left_tab['sample'])
        self.toolbox_changed()

        # update combobox to reflect list of available field types and fields
        #self.update_field_type_combobox_options(self.comboBoxFieldTypeC, self.comboBoxFieldC)



    def update_widget_data_on_sample_change(self):
        self.update_field_combobox_options(self.comboBoxNDimAnalyte)

        data = self.data[self.app_data.sample_id]
        # update dx, dy, nx, ny
        self.preprocess.update_dx_lineedit(data.dx)
        self.preprocess.update_dy_lineedit(data.dy)
        self.preprocess.update_nx_lineedit(data.nx)
        self.preprocess.update_nx_lineedit(data.ny)

        # update c_field_type and c_field
        self.app_data.c_field_type = 'Analyte'
        field = ''
        selected_analytes = self.app_data.selected_fields(field_type='Analyte')
        if len(selected_analytes) == 0:
            field = data.processed_data.match_attribute('data_type','Analyte')[0]
        else:
            field = selected_analytes[0]
        self.app_data.c_field = field

        # hist_bin_width and should be updated along with hist_num_bins
        self.app_data.hist_num_bins = self.app_data.default_hist_num_bins

        # update UI with auto scale and neg handling parameters from 'Analyte Info'
        self.update_autoscale_widgets(field=self.comboBoxFieldC.currentText(), field_type=self.comboBoxFieldTypeC.currentText())

        # reference chemistry is set when the data are initialized
        data.ref_chem = self.app_data.ref_chem

        # update multidim method, pcx to 1 and pcy to 2 (if pca exists)
        # ???
        # update cluster method and cluster properties (if cluster exists)
        # ???

    def update_mask_and_profile_widgets(self):
        #update filters, polygon, profiles with existing data
        self.actionClearFilters.setEnabled(False)
        if np.all(self.data[self.app_data.sample_id].filter_mask):
            self.actionFilterToggle.setEnabled(False)
        else:
            self.actionFilterToggle.setEnabled(True)
            self.actionClearFilters.setEnabled(True)

        if np.all(self.data[self.app_data.sample_id].polygon_mask):
            self.actionPolygonMask.setEnabled(False)
        else:
            self.actionPolygonMask.setEnabled(True)
            self.actionClearFilters.setEnabled(True)

        if np.all(self.data[self.app_data.sample_id].cluster_mask):
            self.actionClusterMask.setEnabled(False)
        else:
            self.actionClusterMask.setEnabled(True)
            self.actionClearFilters.setEnabled(True)

        if hasattr(self, "mask_dock"):
            #reset filter table, keeping any persistent filters
            persistent = self.mask_dock.filter_tab.tableWidgetFilters.column_to_list("persistent")
            if all(persistent):
                pass
            elif any(persistent):
                for row in range(len(persistent)-1,-1,-1):
                    if not persistent[row]:
                        self.mask_dock.filter_tab.tableWidgetFilters.removeRow(row)
            else:
                self.mask_dock.filter_tab.tableWidgetFilters.clearContents()
                self.mask_dock.filter_tab.tableWidgetFilters.setRowCount(0)

            ##### Add back in the persistent filters

        #clear polygons
        if hasattr(self, "mask_dock"):
            if hasattr(self.mask_dock, "polygon_tab"):
                # self.polygon is created in mask_dock.polygon_tab
                self.mask_dock.polygon_tab.polygon_manager.clear_polygons()

        #clear profiling
        if hasattr(self, "profile_dock"):
            self.profile_dock.profiling.clear_profiles()
            self.profile_dock.profile_toggle.setChecked(False)


    def reset_checked_items(self,item):
        """Resets tool buttons as filters/masks are toggled

        Parameters
        ----------
        item : str
            Identifier associated with toggle button that was clicked.
        """        
        #unchecks tool buttons to prevent incorrect behaviour during plot click
        match item:
            case 'crop':
                if hasattr(self, "profile_dock"):
                    self.profile_dock.actionControlPoints.setChecked(False)
                if hasattr(self, "mask_dock"):
                    if hasattr(self.mask_dock, "polygon_tab"):
                        self.actionPointMove.setChecked(False)
                        self.actionPolyCreate.setChecked(False)
                        self.actionPolyMovePoint.setChecked(False)
                        self.actionPolyAddPoint.setChecked(False)
                        self.actionPolyRemovePoint.setChecked(False)
            case 'profiling':
                self.actionCrop.setChecked(False)
                if hasattr(self, "mask_dock"):
                    if hasattr(self.mask_dock, "polygon_tab"):
                        self.actionPolyCreate.setChecked(False)
                        self.actionPolyMovePoint.setChecked(False)
                        self.actionPolyAddPoint.setChecked(False)
                        self.actionPolyRemovePoint.setChecked(False)
            case 'polygon':
                self.actionCrop.setChecked(False)
                if hasattr(self, "profile_dock"):
                    self.profile_dock.actionControlPoints.setChecked(False)
                    self.profile_dock.actionMovePoint.setChecked(False)

    def update_autoscale_widgets(self, field, field_type='Analyte'):
        """
        Retrieves Auto scale parameters and neg handling method from Analyte/Ratio Info and updates UI.

        Parameters
        ----------
        sample_id : str
            Sample identifier
        field : str, optional
            Name of field to plot, Defaults to None
        analysis_type : str, optional
            Field type for plotting, options include: 'Analyte', 'Ratio', 'pca', 'cluster', 'cluster score',
            'Special', 'Computed'. Some options require a field. Defaults to 'Analyte'
        """
        if field == '' or field_type == '':
            return

        # get Auto scale parameters and neg handling from analyte info
        data = self.data[self.app_data.sample_id]
        parameters = data.processed_data.column_attributes[field]

        # update noise reduction, outlier detection, neg. handling, quantile bounds, diff bounds
        data.current_field = self.comboBoxFieldC.currentText()
        # data.negative_method = parameters['negative_method']
        # data.outlier_method = parameters['outlier_method']
        # data.smoothing_method = parameters['smoothing_method']
        # data.data_min_quantile = parameters['lower_bound']
        # data.data_max_quantile = parameters['upper_bound']
        # data.data_min_diff_quantile = parameters['diff_lower_bound']
        # data.data_max_diff_quantile = parameters['diff_upper_bound']

        auto_scale = parameters['auto_scale']
        self.toolButtonAutoScale.setChecked(bool(auto_scale))
        if auto_scale:
            self.lineEditDifferenceLowerQuantile.setEnabled(True)
            self.lineEditDifferenceUpperQuantile.setEnabled(True)
        else:
            self.lineEditDifferenceLowerQuantile.setEnabled(False)
            self.lineEditDifferenceUpperQuantile.setEnabled(False)

    def update_mask_dock(self):
        # Update filter UI 
        if hasattr(self, "mask_dock"):
            data = self.data[self.app_data.sample_id].processed_data
            field = self.mask_dock.filter_tab.comboBoxFilterField.currentText()

            self.mask_dock.filter_tab.lineEditFMin.value = data[field].min()
            self.mask_dock.filter_tab.lineEditFMax.value = data[field].max()

    def update_equalize_color_scale_toolbutton(self, value):
        self.toolButtonScaleEqualize.setChecked(value)

        if self.plot_style.plot_type == 'field map':
            self.plot_style.schedule_update()

    def field_spinbox_changed(self, ax):
        """Updates ``MainWindow.comboBoxFieldC``"""        
        widget = self.plot_style.axis_widget_dict

        widget['spinbox'][ax].blockSignals(True)
        if widget['spinbox'][ax].value() != widget['childbox'][ax].currentIndex():
            widget['childbox'][ax].setCurrentIndex(widget['spinbox'][ax].value())
            self.plot_style.update_field(ax)
        widget['spinbox'][ax].blockSignals(False)

    def update_norm_reference_combobox(self, new_norm_reference):
        if self.toolBox.currentIndex() == self.left_tab['ndim']:
            self.plot_style.schedule_update()

    def update_selected_clusters_spinbox(self, new_selected_clusters):
        if self.toolBox.currentIndex() == self.left_tab['cluster']:
            self.plot_style.schedule_update()


    def update_sample_id(self):
        """Updates ``app_data.sample_id``"""
        if self.app_data.sample_id == self.comboBoxSampleId.currentText():
            return

        # See if the user wants to really change samples and save or discard the current work
        if self.data and self.app_data.sample_id != '':
            # Create and configure the QMessageBox
            response = QMessageBox.warning(self,
                    "Save sample",
                    "Do you want to save the current analysis?",
                    QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Save)
            #iconWarning = QIcon(":/resources/icons/icon-warning-64.svg")
            #msgBox.setWindowIcon(iconWarning)  # Set custom icon


            # If the user clicks discard, then no need to save, just change the sample
            if response == QMessageBox.StandardButton.Save:
                self.io.save_project()
            elif response == QMessageBox.StandardButton.Cancel:
                # change the sample ID back to the current sample
                self.comboBoxSampleId.setCurrentText(self.app_data.sample_id)
                return

        # at this point, the user has decided to proceed with changing the sample
        # update the current sample ID
        self.app_data.sample_id = self.comboBoxSampleId.currentText()
        # initiate the sample change
        self.change_sample()

    def update_plot_type_combobox_options(self):
        """Updates plot type combobox based on current toolbox index or certain dock widget controls."""
        if self.profile_state == True or self.polygon_state == True:
            plot_idx = -1
        else:
            plot_idx = self.toolBox.currentIndex()

        plot_types = self.field_control_settings[plot_idx]['plot_list']
        
        if plot_types == self.comboBoxPlotType.allItems():
            return

        self.comboBoxPlotType.blockSignals(True)
        self.comboBoxPlotType.clear()
        self.comboBoxPlotType.addItems(plot_types)
        self.comboBoxPlotType.setCurrentText(plot_types[self.field_control_settings[plot_idx]['saved_index']])
        self.comboBoxPlotType.blockSignals(False)

        self.plot_style.plot_type = self.comboBoxPlotType.currentText()


    def update_equalize_color_scale(self):
        self.app_data.equalize_color_scale = self.toolButtonScaleEqualize.isChecked()
        if self.plot_style.plot_type == "field map":
            self.plot_style.schedule_update()



    def update_ref_index_combobox(self, new_index):
        rev_val = self.app_data.ref_list[new_index]
        self.update_ref_chem_combobox(rev_val)


    
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
                    refval_1 = self.data[self.app_data.sample_id].ref_chem[re.sub(r'\d', '', analyte_1).lower()]
                    refval_2 = self.data[self.app_data.sample_id].ref_chem[re.sub(r'\d', '', analyte_2).lower()]
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
            self.plot_style.schedule_update()
        #self.update_all_plots()

    # toolbar functions
    def update_ref_chem_combobox_BE(self, ref_val):
        """Changes reference computing normalized analytes

        Sets all `self.app_data.ref_chem` to a common normalizing reference.

        Parameters
        ----------
        ref_val : str
            Name of reference value from combobox/dropdown
        """
        ref_index = self.app_data.ref_list.tolist().index(ref_val)

        if ref_index:
            self.data[self.app_data.sample_id].ref_chem = self.app_data.ref_chem

            return ref_index



    # -------------------------------------
    # General plot functions
    # -------------------------------------
    def check_valid_fields(self):
        """Checks for valid fields and field types based on the plot type.
        
        Optional fields are not checked.
        
        Returns
        -------
        bool : True if it passes all tests, False if it does not"""
        axes = []
        invalid_values = [None, '', 'none', 'None']
        match self.plot_style.plot_type:
            case 'field map':
                axes = [3]
            case 'gradient map': 
                axes = [3]
            case 'ternary map':
                axes = [0,1,2]
            case 'correlation':
                return True
            case 'histogram':
                axes = [0]
            case 'scatter':
                axes = [0,1]
            case 'heatmap':
                axes = [0,1]
            case 'TEC' | 'radar':
                return True
            case 'variance' | 'basis vectors' | 'performance':
                return True
            case 'dimension score map':
                axes = [3]
            case 'dimension scatter', 'dimension heatmap':
                axes = [0,1]
            case 'cluster map':
                axes = [3]
            case 'cluster score map':
                axes = [3]
            case 'profile':
                axes = [3]
            case 'polygon':
                axes = [3]

        for ax in axes:
            if self.app_data.get_field_type(ax) in invalid_values:
                return False
            if self.app_data.get_field(ax) in invalid_values:
                return False

        return True


    def update_SV(self):
        """Updates current plot (not saved to plot selector)

        Updates the current plot (as determined by ``MainWindow.comboBoxPlotType.currentText()``
        and options in ``MainWindow.toolBox.selectedIndex()``.

        save : bool, optional
            save plot to plot selector, Defaults to False.
        """
        # check to make sure that the basic elements of a plot are satisfied, i.e.,
        #   sample_id is not an empty str
        #   plot_type is not empty or none
        #   field types and fields are valid for the appropriate axes
        if self.app_data.sample_id == '' or self.plot_style.plot_type in [None, '', 'none', 'None'] or not self.check_valid_fields():
            return

        data = self.data[self.app_data.sample_id]
        
        match self.plot_style.plot_type:
            case 'field map':
                sample_id = self.app_data.sample_id
                field_type = self.app_data.c_field_type
                field = self.app_data.c_field

                if (hasattr(self, "mask_dock") and self.mask_dock.polygon_tab.polygon_toggle.isChecked()) or (hasattr(self, "profile_dock") and self.profile_dock.profile_toggle.isChecked()):
                    canvas, self.plot_info,_ =  plot_map_mpl(self, data, self.app_data, self.plot_style, field_type, field, add_histogram=False)
                    # show increated profiles if exists
                    if (hasattr(self, "profile_dock") and self.profile_dock.profile_toggle.isChecked()) and (self.app_data.sample_id in self.profile_dock.profiling.profiles):
                        self.profile_dock.profiling.clear_plot()
                        self.profile_dock.profiling.plot_existing_profile(self.plot)
                    elif (hasattr(self, "mask_dock") and self.mask_dock.polygon_tab.polygon_toggle.isChecked()) and (self.app_data.sample_id in self.mask_dock.polygon_tab.polygon_manager.polygons):  
                        self.mask_dock.polygon_tab.polygon_manager.clear_polygons()
                        self.mask_dock.polygon_tab.polygon_manager.plot_existing_polygon(canvas)

                    
                else:
                    if self.toolBox.currentIndex() == self.left_tab['process']:
                        canvas, self.plot_info, hist_canvas = plot_map_mpl(self, data, self.app_data, self.plot_style, field_type, field, add_histogram=True)

                        if not self.widgetHistView.layout():
                            self.widgetHistView.setLayout(QVBoxLayout())

                        self.canvas_widget.clear_layout(self.widgetHistView.layout())
                        self.widgetHistView.layout().addWidget(hist_canvas)
                    else:
                        canvas, self.plot_info, _ = plot_map_mpl(self, data, self.app_data, self.plot_style, field_type, field, add_histogram=False)
                self.mpl_canvas = canvas
                self.canvas_widget.add_plotwidget_to_canvas(self.plot_info)
                    # I think add_tree_item is done in add_plotwidget_to_canvas, so it doesn't need to be repeated here
                    #self.plot_tree.add_tree_item(self.plot_info)

                if hasattr(self,"info_dock"):
                    self.info_dock.plot_info_tab.update_plot_info_tab(self.plot_info)
                
                return

            case 'gradient map':
                if self.comboBoxNoiseReductionMethod.currentText() == 'none':
                    QMessageBox.warning(self,'Warning','Noise reduction must be performed before computing a gradient.')
                    return
                self.noise_reduction.noise_reduction_method_callback()
            case 'correlation':
                if self.comboBoxCorrelationMethod.currentText() == 'none':
                    return
                canvas, self.plot_info = plot_correlation(self, data, self.app_data, self.plot_style)


            case 'TEC' | 'Radar':
                canvas, self.plot_info = plot_ndim(self, data, self.app_data, self.plot_style)

            case 'histogram':
                canvas, self.plot_info = plot_histogram(self, data, self.app_data, self.plot_style)

            case 'scatter' | 'heatmap':
                if self.comboBoxFieldX.currentText() == self.comboBoxFieldY.currentText():
                    return
                canvas, self.plot_info = plot_scatter(self, data, self.app_data, self.plot_style)

            case 'ternary map':
                if self.comboBoxFieldX.currentText() == self.comboBoxFieldY.currentText() or \
                    self.comboBoxFieldX.currentText() == self.comboBoxFieldZ.currentText() or \
                    self.comboBoxFieldY.currentText() == self.comboBoxFieldZ.currentText():
                    return

                canvas, self.plot_info = plot_ternary_map(self, data, self.app_data, self.plot_style)

            case 'variance' | 'basis vectors' | 'dimension scatter' | 'dimension heatmap' | 'dimension score map':
                if self.app_data.update_pca_flag or not data.processed_data.match_attribute('data_type','pca score'):
                    self.DimRedPage.compute_dim_red(data, self.app_data)
                canvas, self.plot_info = plot_pca(self, data, self.app_data, self.plot_style)

            case 'cluster map' | 'cluster score map':
                self.ClusterPage.compute_clusters_update_groups()
                canvas, self.plot_info = plot_clusters(self, data, self.app_data, self.plot_style)

            case 'cluster performance':
                # compute performace as a function of number of clusters
                self.ClusterPage.compute_clusters(data, self.app_data, max_clusters = self.app_data.max_clusters)
                canvas, self.plot_info = cluster_performance_plot(self, data, self.app_data, self.plot_style)

        # add canvas to layout
        if canvas:
            self.canvas_widget.clear_layout(self.widgetSingleView.layout())
            self.widgetSingleView.layout().addWidget(canvas)

        # add plot info to info_dock
        if hasattr(self,"info_dock"):
            self.info_dock.plot_info_tab.update_plot_info_tab(self.plot_info)



    # -------------------------------------
    # Dialogs and Windows
    # -------------------------------------
    def open_plot_tree(self):
        """Opens Plot Tree dock

        Opens Plot Tree dock, creates on first instance.  The Plot Tree is used to manage
        plots and their properties.
        """
        if not hasattr(self, 'plot_tree'):
            self.plot_tree = PlotTree(self)

            if self.plot_tree not in self.help_mapping:
                self.help_mapping[self.plot_tree] = 'right_toolbox'

            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_tree)
            self.plot_tree.setFloating(False)

            self.toolButtonRightDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.plot_tree, button=self.toolButtonRightDock))

        self.plot_tree.show()

    def open_workflow(self):
        """Opens Workflow dock.

        Opens Workflow dock, creates on first instance.  The Workflow is used to design
        processing algorithms that can batch process samples, or simply record the
        process of analyzing a sample.
        """
        if not hasattr(self, 'workflow'):
            self.workflow = Workflow(self)

            if self.workflow not in self.help_mapping:
                self.help_mapping[self.workflow] = 'workflow'

        self.workflow.show()


        #self.workflow.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

    def open_mask_dock(self, tab_name=None, *args, **kwargs):
        """Opens Mask Dock

        Opens Mask Dock, creates on first instance.  The Mask Dock includes tabs for
        filtering, creating and masking with polygons and masking by clusters.

        Parameters
        ----------
        tab_name : str, optional
            Will open the dock to the requested tab, options include 'filter', 'polygon'
            and cluster', by default None
        """
        if not hasattr(self, 'mask_dock'):
            self.mask_dock = MaskDock(self)

            self.mask_tab = {}
            for tid in range(self.mask_dock.tabWidgetMask.count()):
                match self.mask_dock.tabWidgetMask.tabText(tid).lower():
                    case 'filters':
                        self.mask_tab.update({'filter': tid})
                    case 'polygons':
                        self.mask_tab.update({'polygon': tid})
                    case 'clusters':
                        self.mask_tab.update({'cluster': tid})

            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.mask_dock)
            self.mask_dock.setFloating(False)

            self.toolButtonBottomDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.mask_dock, button=self.toolButtonBottomDock))

            if self.mask_dock not in self.help_mapping:
                self.help_mapping[self.mask_dock] = 'filtering'

            self.mask_dock.filter_tab.callback_lineEditFMin()
            self.mask_dock.filter_tab.callback_lineEditFMax()

        self.mask_dock.show()

        if tab_name is not None:
            self.mask_dock.tabWidgetMask.setCurrentIndex(self.mask_tab[tab_name])


    def open_profile(self, *args, **kwargs):
        """Opens Profile dock

        Opens Profile dock, creates on first instance.  The profile dock is used to create and display
        2-D profiles across maps.

        :see also:
            Profile
        """
        if not hasattr(self, 'profile'):
            self.profile_dock = ProfileDock(self)

            if self.profile_dock not in self.help_mapping:
                self.help_mapping[self.profile_dock] = 'profiles'

        self.profile_dock.show()

    def open_regression(self, *args, **kwargs):
        """Opens Regression dock

        Opens Regression dock, creates on first instance.  The regression dock is used to fit
        curves and models to data.
        """
        if not hasattr(self, 'profile'):
            self.regression_dock = RegressionDock(self)

            if self.regression_dock not in self.help_mapping:
                self.help_mapping[self.regression_dock] = 'regression'

        self.regression_dock.show()

    def open_notes(self):
        """Opens Notes Dock

        Opens Notes Dock, creates on first instance.  The notes can be used to record
        important information about the data, its processing and display the results.
        The notes may be useful for developing data reports/appendicies associated
        with publications.

        :see also:
            NoteTaking
        """            
        if not hasattr(self, 'notes'):
            if hasattr(self.app_data,'selected_directory') and self.app_data.sample_id != '':
                notes_file = os.path.join(self.app_data.selected_directory,f"{self.app_data.sample_id}.rst")
            else:
                notes_file = None

            self.notes = Notes(self, notes_file)
            info_menu_items = [
                ('Sample info', lambda: self.insert_info_note('sample info')),
                ('List analytes used', lambda: self.insert_info_note('analytes')),
                ('Current plot details', lambda: self.insert_info_note('plot info')),
                ('Filter table', lambda: self.insert_info_note('filters')),
                ('PCA results', lambda: self.insert_info_note('pca results')),
                ('Cluster results', lambda: self.insert_info_note('cluster results'))
            ]
            self.notes.info_menu_items = info_menu_items

            self.notes.update_equation_menu()

            if self.notes not in self.help_mapping:
                self.help_mapping[self.notes] = 'notes'

        self.notes.show()
        #self.notes.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

    def insert_info_note(self, infotype):
        data = self.data[self.app_data.sample_id]

        match infotype:
            case 'sample info':
                text = f'**Sample ID: {self.app_data.sample_id}**\n'
                text += '*' * (len(self.app_data.sample_id) + 15) + '\n'
                text += f'\n:Date: {datetime.today().strftime("%Y-%m-%d")}\n'
                text += ':User: Your name here\n\n'
                self.notes.print_info(text)
            case 'analytes':
                analytes = data.processed_data.match_attribute('data_type', 'Analyte')
                ratios = data.processed_data.match_attribute('data_type', 'Ratio')
                text = ''
                if analytes:
                    text += ':analytes collected: '+', '.join(analytes)
                    text += '\n'
                if ratios:
                    text += ':ratios computed: '+', '.join(ratios)
                    text += '\n'
                text += '\n'
                self.notes.print_info(text)
            case 'plot info':
                if self.plot_info:
                    text = ['\n\n:plot type: '+self.plot_info['plot_type'],
                            ':plot name: '+self.plot_info['plot_name']+'\n']
                    text = '\n'.join(text)
                    self.notes.print_info(text)
            case 'filters':
                rst_table = self.notes.to_rst_table(data.filter_df)

                self.notes.print_info(rst_table)
            case 'pca results':
                if not self.pca_results:
                    return

                # Retrieve analytes matching specified attributes
                analytes = data.processed_data.match_attributes({'data_type': 'Analyte', 'use': True})
                analytes = np.insert(analytes, 0, 'lambda')  # Insert 'lambda' at the start of the analytes array

                # Calculate explained variance in percentage
                explained_variance = self.pca_results.explained_variance_ratio_ * 100

                # Retrieve PCA score headers matching the attribute condition
                header = data.processed_data.match_attributes({'data_type': 'PCA score'})

                # Create a matrix with explained variance and PCA components
                matrix = np.vstack([explained_variance, self.pca_results.components_])

                # Filter matrix and header based on the MaxVariance option
                variance_mask = np.cumsum(explained_variance) <= self.options['MaxVariance']
                matrix = matrix[:, variance_mask]  # Keep columns where variance is <= MaxVariance
                header = np.array(header)[variance_mask]  # Apply the same filter to the header

                # Limit the number of columns based on MaxColumns option
                if self.options['MaxColumns'] is not None and  matrix.shape[1] > self.options['MaxColumns']:
                    header = np.concatenate([[analytes[0]], header[:self.options['MaxColumns']]])  # Include 'lambda' in header
                    matrix = matrix[:, :self.options['MaxColumns']]  # Limit matrix columns

                # add PCA results to table
                self.add_table_note(matrix, row_labels=analytes, col_labels=header)
            case 'cluster results':
                if not self.parent.cluster_results:
                    return


    def open_calculator(self):
        """Opens Calculator dock

        Opens Calculator dock, creates on first instance.  The Calculator is used to compute
        custom fields.
        """            
        if not hasattr(self, 'calculator'):
            calc_file = os.path.join(BASEDIR,f'resources/app_data/calculator.txt')
            self.calculator = CalculatorDock(ui=self, filename=calc_file)

            if self.calculator not in self.help_mapping:
                self.help_mapping[self.calculator] = 'calculator'

        self.calculator.show()
        #self.calculator.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

    def open_info_dock(self):
        """Opens Info Dock.
        
        Opens Info Dock, creates on first instance.  The Info Dock can be used to interrogate 
        the data and its metadata as well as plot related properties.
        """
        if not hasattr(self, 'info_dock'):
            self.info_dock = InfoDock(self, "LaME Info")

            for tid in range(self.info_dock.tabWidgetInfo.count()):
                match self.info_dock.tabWidgetInfo.tabText(tid).lower():
                    case 'plot':
                        self.info_tab.update({'plot': tid})
                    case 'metadata':
                        self.info_tab.update({'metadata': tid})
                    case 'data':
                        self.info_tab.update({'data': tid})
                    case 'fields':
                        self.info_tab.update({'field': tid})
        
            if self.info_dock not in self.help_mapping:
                self.help_mapping[self.info_dock] = 'info_tool'
        else:
            self.info_dock.show()


    def open_logger(self):
        """Creates or shows Logger Dock

        Creates or opens a dock-based logger.  The logger dock prints information that can be
        used to record user interactions with the interface, log function calls and arguments
        passed and record changes to the data.
        """            
        if not hasattr(self, 'logger_dock'):
            logfile = os.path.join(BASEDIR,f'resources/log/lame.log')
            self.logger_dock = LoggerDock(logfile, self)
            for key in self.logger_options:
                self.logger_options[key] = True

            if self.logger_dock not in self.help_mapping:
                self.help_mapping[self.logger_dock] = 'logging_tool'
        else:
            self.logger_dock.show()


        #self.logger.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

    def open_browser(self, action=None):
        """Opens Browser dock with documentation

        Opens Browser dock, creates on first instance.
        """
        if not hasattr(self, 'browser'):
            self.browser = Browser(self, self.help_mapping, BASEDIR)
        else:
            self.browser.show()

        #self.browser.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

        match action:
            case 'report_bug':
                self.browser.engine.setUrl(QUrl('https://github.com/dhasterok/LaserMapExplorer/issues'))
            case 'user guide':
                self.browser.go_to_home()
            case 'tutorials':
                self.browser.go_to_page(location='tutorials')
            case _:
                self.browser.go_to_home()

    def open_select_analyte_dialog(self):
        """Opens Select Analyte dialog

        Opens a dialog to select analytes for analysis either graphically or in a table.  
        Selection updates the list of analytes, and ratios in plot selector and comboBoxes.
        
        .. seealso::
            :ref:`AnalyteSelectionWindow` for the dialog
        """
        if self.app_data.sample_id == '':
            return

        self.analyte_dialog = AnalyteDialog(self)
        self.analyte_dialog.show()

        result = self.analyte_dialog.exec()  # Store the result here
        if result == QDialog.DialogCode.Accepted:
            self.update_analyte_ratio_selection(analyte_dict=self.analyte_dialog.norm_dict)   
            self.workflow.refresh_analyte_saved_lists_dropdown() #refresh saved analyte dropdown in blockly 
        if result == QDialog.DialogCode.Rejected:
            pass

    def update_analyte_ratio_selection(self,analyte_dict):
        """Updates analytes/ratios in mainwindow and its corresponding scale used for each field

        Updates analytes/ratios and its corresponding scale used for each field based
        on selection made by user in Analyteselection window or if user choses analyte
        list in blockly.
        
        Parameters
            ----------
            analyte_dict: dict
                key: Analyte/Ratio name
                value: scale used (linear/log/logit)
        """
        #update self.data['norm'] with selection
        for analyte in self.data[self.app_data.sample_id].processed_data.match_attribute('data_type','Analyte'):
            if analyte in analyte_dict:
                self.data[self.app_data.sample_id].processed_data.set_attribute(analyte, 'use', True)
            else:
                self.data[self.app_data.sample_id].processed_data.set_attribute(analyte, 'use', False)

        for analyte, norm in analyte_dict.items():
            if '/' in analyte:
                if analyte not in self.data[self.app_data.sample_id].processed_data.columns:
                    analyte_1, analyte_2 = analyte.split(' / ') 
                    self.data[self.app_data.sample_id].compute_ratio(analyte_1, analyte_2)

            self.data[self.app_data.sample_id].processed_data.set_attribute(analyte,'norm',norm)

        self.plot_tree.update_tree(norm_update=True)

        if self.left_tab['dimensional reduction'] == self.toolBox.currentIndex() or self.left_tab['clustering'] == self.toolBox.currentIndex():
            self.plot_style.schedule_update()

        #update analysis type combo in styles
        #self.check_analysis_type()
        #self.update_all_field_comboboxes()
        #self.update_blockly_field_types()


    def open_select_custom_field_dialog(self):
        """Opens Select Analyte dialog

        Opens a dialog to select analytes for analysis either graphically or in a table.  
        Selection updates the list of analytes, and ratios in plot selector and comboBoxes.
        
        .. seealso::
            :ref:`AnalyteSelectionWindow` for the dialog
        """
        if self.app_data.sample_id == '':
            return
        
        self.field_dialog = FieldDialog(self)
        self.field_dialog.show()

        result = self.field_dialog.exec()  # Store the result here
        if result == QDialog.DialogCode.Accepted:
            self.selected_fields = self.field_dialog.selected_fields
            self.workflow.refresh_custom_fields_lists_dropdown() #refresh saved analyte dropdown in blockly 
        if result == QDialog.DialogCode.Rejected:
            pass