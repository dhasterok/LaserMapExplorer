import sys, os, re, copy, random, darkdetect
from PyQt6.QtCore import ( Qt, QTimer, QUrl, QSize, QRectF )
from PyQt6.QtWidgets import (
    QCheckBox, QTableWidgetItem, QVBoxLayout, QGridLayout,
    QMessageBox, QHeaderView, QMenu, QFileDialog, QWidget, QToolButton,
    QDialog, QLabel, QTableWidget, QInputDialog, QAbstractItemView,
    QSplashScreen, QApplication, QMainWindow, QSizePolicy
)
from PyQt6.QtGui import ( QIntValidator, QDoubleValidator, QPixmap, QFont, QIcon )
from src.common.CustomWidgets import CustomCheckButton
from src.app.UITheme import UIThemes

#from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
# import pyqtgraph as pg
# from pyqtgraph.GraphicsScene import exportDialog
# from pyqtgraph import (
#     setConfigOption, colormap, ColorBarItem,ViewBox, TargetItem, ImageItem,
#     GraphicsLayoutWidget, ScatterPlotItem, AxisItem, PlotDataItem
# )
#from datetime import datetimec
import numpy as np
import pandas as pd
pd.options.mode.copy_on_write = True
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
import cmcrameri as cmc
from src.common.LamePlot import plot_map_mpl, plot_small_histogram, plot_histogram, plot_correlation, get_scatter_data, plot_scatter, plot_ternary_map, plot_ndim, plot_pca, plot_clusters, cluster_performance_plot
from src.app.LameIO import LameIO
import src.common.csvdict as csvdict
#import src.radar_factory
from src.common.radar import Radar
from src.ui.MainWindow import Ui_MainWindow
#from src.ui.PreferencesWindow import Ui_PreferencesWindow
from src.app.FieldSelectionWindow import FieldDialog
from src.app.AnalyteSelectionWindow import AnalyteDialog
from src.common.TableFunctions import TableFcn as TableFcn
import src.common.CustomMplCanvas as mplc
from src.app.PlotTree import PlotTree
from src.common.DataAnalysis import Clustering, DimensionalReduction
from src.common.Masking import MaskDock
from src.app.CropImage import CropTool
from src.app.ImageProcessing import ImageProcessing
from src.app.StyleToolbox import StylingDock
from src.app.Profile import Profiling, ProfileDock
from src.common.Polygon import PolygonManager
from src.app.SpotTools import SpotPage
from src.app.SpecialTools import SpecialPage
from src.common.NoteTaking import Notes
from src.common.Browser import Browser
from src.app.Workflow import Workflow
from src.app.InfoViewer import InfoDock
import src.app.QuickView as QV
from src.app.config import BASEDIR, ICONPATH, SSPATH, DEBUG, load_stylesheet
from src.common.ExtendedDF import AttributeDataFrame
import src.common.format as fmt
from src.common.colorfunc import get_hex_color, get_rgb_color
import src.app.config as config
from src.app.help_mapping import create_help_mapping
from src.common.Logger import LogCounter, LoggerDock
from src.common.Calculator import CalculatorDock
from src.common.varfunc import ObservableDict
from src.app.AppData import AppData

# to prevent segmentation error at startup
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
# setConfigOption('imageAxisOrder', 'row-major') # best performance

class MainWindow(QMainWindow, Ui_MainWindow):
    """_summary_

    _extended_summary_

    Attributes
    ----------
    app_data : AppData
        Properties and methods for the calling UI, in this case, MainWindow
    data : dict
        Dictionary of samples with sample IDs as keys
    plot_style : StylingDock
        Properties and methods for styling plots and updating the Styling Dock
    """
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setupUi(self)

        # this flag sets whether the plot can be updated.  Mostly off during change_sample
        self.plot_flag = False
        self.duplicate_plot_info = None
        self.profile_state = False # True if profiling toggle is set to on
        self.polygon_state = False # True if polygon toggle is set to on
        self.field_control_settings = {} # a dictionary that keeps track of UI data for each toolBox page

        # setup initial logging options
        self.logger = LogCounter()
        self.logger_options = {
                'IO': False,
                'Data': False,
                'Analyte selector': False,
                'Plot selector': False,
                'Plotting': False,
                'Polygon': False,
                'Profile': False,
                'Masking': False,
                'Tree': False,
                'Styles': True,
                'Calculator': False,
                'Browser': False,
                'UI': False
            }
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
        self.app_data = AppData(self.data, debug=self.logger_options['Data'])

        # initialize the styling data and dock
        self.plot_style = StylingDock(self, debug=self.logger_options['Styles'])

        self.connect_app_data_observers(self.app_data)
        self.connect_plot_style_observers(self.plot_style)

        # Initialise dimentionality reduction class 
        self.dimensional_reduction = DimensionalReduction(self)

        # Initialise class from DataAnalysis
        self.clustering = Clustering(self)

        self.init_ui()
        self.connect_actions()
        self.connect_widgets()

        # holds the custom field names and formulas set by the user in the calculator
        self.calc_dict = {}

        self.init_canvas_widget()

        self.mpl_canvas = None # will hold the current canvas

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
        self.dockWidgetPlotTree.show()
        self.dockWidgetStyling.show()
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockWidgetPlotTree)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockWidgetStyling)
        self.dockWidgetPlotTree.setFloating(False)
        self.dockWidgetStyling.setFloating(False)

        self.toolButtonLeftDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.dockWidgetLeftToolbox, button=self.toolButtonLeftDock))
        self.toolButtonRightDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.dockWidgetPlotTree, button=None))
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
        self.actionRegression.triggered.connect(self.toggle_regression_tab)

        # code is more resilient if toolbox indices for each page is not hard coded
        # will need to change case text if the page text is changed
        self.reindex_left_tab()
        self.reindex_style_tab()
        self.reindex_canvas_tab()

        self.toolBox.setCurrentIndex(self.left_tab['sample'])

        self.canvasWindow.currentChanged.connect(self.canvas_changed)
        self.canvasWindow.setCurrentIndex(self.canvas_tab['sv'])
        self.canvas_changed()
        self.init_tabs(enable=False)

        # connect actions to docks
        #-------------------------
        self.actionFilters.triggered.connect(lambda: self.open_mask_dock('filter'))
        self.actionPolygons.triggered.connect(lambda: self.open_mask_dock('polygon'))
        self.actionClusters.triggered.connect(lambda: self.open_mask_dock('cluster'))
        self.actionProfiles.triggered.connect(self.open_profile)
        self.actionCalculator.triggered.connect(self.open_calculator)
        self.open_calculator()
        self.calculator.hide()
        self.actionNotes.triggered.connect(self.open_notes)
        if hasattr(self,'notes'):
            # this won't do anything so it needs to get added somewhere else
            self.notes.update_equation_menu()
        self.actionLogger.triggered.connect(self.open_logger)
        self.actionWorkflowTool.triggered.connect(self.open_workflow)
        self.info_tab = {}
        self.actionInfo.triggered.connect(self.open_info_dock)

        self.io = LameIO(parent=self, connect_actions=True, debug=self.logger_options['IO'])

        self.actionHelp.setCheckable(True)
        self.actionHelp.toggled.connect(self.toggle_help_mode)

        # initialize used classes
        self.crop_tool = CropTool(self)
        self.plot_tree = PlotTree(self, debug=self.logger_options['Tree'])
        self.table_fcn = TableFcn(self)
        #self.clustertool = Clustering(self)
        #self.dimredtool = DimensionalReduction(self)
        self.noise_reduction = ImageProcessing(self)

        self.actionQuit_LaME.triggered.connect(self.quit)

        # For light and dark themes, connects actionViewMode
        self.theme = UIThemes(app, self)

    def init_canvas_widget(self):
        """Initializes the central canvas tabs"""
        # Plot Layouts
        #-------------------------
        # Central widget plot view layouts
        # single view
        layout_single_view = QVBoxLayout()
        layout_single_view.setSpacing(0)
        layout_single_view.setContentsMargins(0, 0, 0, 0)
        self.widgetSingleView.setLayout(layout_single_view)
        self.widgetSingleView.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.mpl_toolbar = None
        #self.mpl_toolbar = NavigationToolbar(mplc.MplCanvas())
        # for button show hide
        #self.toolButtonPopFigure.setVisible(False)
        #self.toolButtonPopFigure.raise_()
        #self.toolButtonPopFigure.enterEvent = self.mouseEnter
        #self.toolButtonPopFigure.leaveEvent = self.mouseLeave

        layout_histogram_view = QVBoxLayout()
        layout_histogram_view.setSpacing(0)
        layout_histogram_view.setContentsMargins(0, 0, 0, 0)
        self.widgetHistView.setLayout(layout_histogram_view)

        # multi-view
        self.multi_view_index = []
        self.multiview_info_label = {}
        layout_multi_view = QGridLayout()
        layout_multi_view.setSpacing(0) # Set margins to 0 if you want to remove margins as well
        layout_multi_view.setContentsMargins(0, 0, 0, 0)
        self.widgetMultiView.setLayout(layout_multi_view)
        self.widgetMultiView.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.toolButtonRemoveMVPlot.clicked.connect(lambda: self.remove_multi_plot(self.comboBoxMVPlots.currentText()))
        self.toolButtonRemoveAllMVPlots.clicked.connect(lambda: self.clear_layout(self.widgetMultiView.layout()))

        # quick view
        layout_quick_view = QGridLayout()
        layout_quick_view.setSpacing(0) # Set margins to 0 if you want to remove margins as well
        layout_quick_view.setContentsMargins(0, 0, 0, 0)
        self.widgetQuickView.setLayout(layout_quick_view)
        self.widgetQuickView.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        try:
            self.QV_analyte_list = csvdict.import_csv_to_dict(os.path.join(BASEDIR,'resources/styles/qv_lists.csv'))
        except:
            self.QV_analyte_list = {'default':['Si29','Ti47','Al27','Cr52','Fe56','Mn55','Mg24','Ca43','K39','Na23','P31',
                'Ba137','Th232','U238','La139','Ce140','Pb206','Pr141','Sr88','Zr90','Hf178','Nd146','Eu153',
                'Gd157','Tb159','Dy163','Ho165','Y89','Er166','Tm169','Yb172','Lu175']}

        self.toolButtonNewList.clicked.connect(lambda: QV.QuickView(self))
        self.comboBoxQVList.activated.connect(lambda: self.display_QV())



    def connect_actions(self):
        pass

    def connect_widgets(self):
        self.toolBox.currentChanged.connect(lambda: self.canvasWindow.setCurrentIndex(self.canvas_tab['sv']))
        self.toolBox.currentChanged.connect(self.toolbox_changed)
        self.comboBoxSampleId.activated.connect(self.update_sample_id)

        self.lineEditDX.editingFinished.connect(self.update_dx)
        self.lineEditDY.editingFinished.connect(self.update_dy)
        self.actionFullMap.triggered.connect(self.reset_crop)

        self.toolButtonSwapResolution.clicked.connect(self.update_swap_resolution)
        self.toolButtonPixelResolutionReset.clicked.connect(self.reset_pixel_resolution)


        pt_dict = self.plot_style.axis_widget_dict['plot type'][self.plot_style.plot_type]
        self.comboBoxFieldTypeC.popup_callback = lambda: self.update_field_type_combobox_options(self.comboBoxFieldTypeC, self.comboBoxFieldC, add_none=pt_dict['add_none'][3], global_list=True, user_activated=True)
        self.comboBoxFieldTypeC.currentTextChanged.connect(lambda: self.plot_style.update_field_type(ax=3))
        self.comboBoxFieldC.popup_callback = lambda: self.update_field_combobox_options(self.comboBoxFieldC, self.comboBoxFieldTypeC, spinbox=self.spinBoxFieldC, add_none=pt_dict['add_none'][3], user_activated=True)
        #self.comboBoxFieldC.currentTextChanged.connect(self.plot_style.update_c_field_combobox)
        self.comboBoxFieldC.currentTextChanged.connect(lambda: self.plot_style.update_field(ax=3))
        # update spinbox associated with map/color field
        self.spinBoxFieldC.valueChanged.connect(lambda: self.field_spinbox_changed(ax=3))

        self.comboBoxFieldTypeX.popup_callback = lambda: self.update_field_type_combobox_options(self.comboBoxFieldTypeX, self.comboBoxFieldX, add_none=pt_dict['add_none'][0], user_activated=True)
        self.comboBoxFieldTypeX.currentTextChanged.connect(lambda: self.plot_style.update_field_type(ax=0))
        self.comboBoxFieldX.popup_callback = lambda: self.update_field_combobox_options(self.comboBoxFieldX, self.comboBoxFieldTypeX, add_none=pt_dict['add_none'][0], user_activated=True)
        self.comboBoxFieldX.currentTextChanged.connect(lambda: self.plot_style.update_field(ax=0))
        # update spinbox associated with map/color field
        self.spinBoxFieldX.valueChanged.connect(lambda: self.field_spinbox_changed(ax=0))

        self.comboBoxFieldTypeY.popup_callback = lambda: self.update_field_type_combobox_options(self.comboBoxFieldTypeY, self.comboBoxFieldY, add_none=pt_dict['add_none'][1], user_activated=True)
        self.comboBoxFieldTypeY.currentTextChanged.connect(lambda: self.plot_style.update_field_type(ax=1))
        self.comboBoxFieldY.popup_callback = lambda: self.update_field_combobox_options(self.comboBoxFieldY, self.comboBoxFieldTypeY, add_none=pt_dict['add_none'][1], user_activated=True)
        self.comboBoxFieldY.currentTextChanged.connect(lambda: self.plot_style.update_field(ax=1))
        # update spinbox associated with map/color field
        self.spinBoxFieldY.valueChanged.connect(lambda: self.field_spinbox_changed(ax=1))

        self.comboBoxFieldTypeZ.popup_callback = lambda: self.update_field_type_combobox_options(self.comboBoxFieldTypeZ, self.comboBoxFieldZ, add_none=pt_dict['add_none'][2], user_activated=True)
        self.comboBoxFieldTypeZ.currentTextChanged.connect(lambda: self.plot_style.update_field_type(ax=2))
        self.comboBoxFieldZ.popup_callback = lambda: self.update_field_combobox_options(self.comboBoxFieldZ, self.comboBoxFieldTypeZ, add_none=pt_dict['add_none'][2], user_activated=True)
        self.comboBoxFieldZ.currentTextChanged.connect(lambda: self.plot_style.update_field(ax=2))

        # N-Dim Tab
        #-------------------------
        # setup comboBoxNDIM
        self.comboBoxNDimAnalyteSet.clear()
        self.comboBoxNDimAnalyteSet.addItems(list(self.app_data.ndim_list_dict.keys()))
        
        self.comboBoxRefMaterial.addItems(self.app_data.ref_list.values)          # Select analyte Tab
        self.comboBoxNDimRefMaterial.addItems(self.app_data.ref_list.values)      # NDim Tab
        self.comboBoxRefMaterial.activated.connect(lambda: self.update_ref_chem_combobox(self.comboBoxRefMaterial.currentText())) 
        self.comboBoxNDimRefMaterial.activated.connect(lambda: self.update_ref_chem_combobox(self.comboBoxNDimRefMaterial.currentText()))
        self.comboBoxRefMaterial.setCurrentIndex(self.app_data.ref_index)
        self.comboBoxNDimRefMaterial.setCurrentIndex(self.app_data.ref_index)
        self.comboBoxNDimQuantiles.setCurrentIndex(self.app_data.ndim_quantile_index)
        
        self.toolButtonNDimAnalyteAdd.clicked.connect(lambda: self.update_ndim_table('analyteAdd'))
        self.toolButtonNDimAnalyteSetAdd.clicked.connect(lambda: self.update_ndim_table('analyteSetAdd'))
        self.toolButtonNDimUp.clicked.connect(lambda: self.table_fcn.move_row_up(self.tableWidgetNDim))
        self.toolButtonNDimDown.clicked.connect(lambda: self.table_fcn.move_row_down(self.tableWidgetNDim))
        self.toolButtonNDimSelectAll.clicked.connect(self.tableWidgetNDim.selectAll)
        self.toolButtonNDimRemove.clicked.connect(lambda: self.table_fcn.delete_row(self.tableWidgetNDim))
        self.toolButtonNDimSaveList.clicked.connect(self.save_ndim_list)

        # N-dim table
        header = self.tableWidgetNDim.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        
        self.toolButtonSwapResolution.clicked.connect(self.update_swap_resolution)

        self.comboBoxOutlierMethod.addItems(self.app_data.outlier_methods)
        if 'Chauvenet criterion' in self.app_data.outlier_methods:
            self.comboBoxOutlierMethod.setCurrentText('Chauvenet criterion')
        self.comboBoxOutlierMethod.activated.connect(lambda: self.update_outlier_removal(self.comboBoxOutlierMethod.currentText()))

        self.comboBoxNegativeMethod.addItems(self.app_data.negative_methods)
        self.comboBoxNegativeMethod.activated.connect(lambda: self.update_neg_handling(self.comboBoxNegativeMethod.currentText()))

        # Dimensional reduction ui widgets
        self.ComboBoxDimRedTechnique.clear()
        self.ComboBoxDimRedTechnique.addItems(self.dimensional_reduction.dim_red_methods)
        self.app_data.dim_red_method = self.dimensional_reduction.dim_red_methods[0]
        self.spinBoxPCX.valueChanged.connect(lambda: setattr(self.app_data, "dim_red_x",self.spinBoxPCX.value()))
        self.spinBoxPCY.valueChanged.connect(lambda: setattr(self.app_data, "dim_red_y",self.spinBoxPCY.value()))

        # Clustering ui widgets
        self.spinBoxNClusters.valueChanged.connect(lambda: setattr(self.app_data, "num_clusters",self.spinBoxNClusters.value()))
        self.comboBoxClusterDistance.clear()
        self.comboBoxClusterDistance.addItems(self.clustering.distance_metrics)
        self.app_data.cluster_distance = self.clustering.distance_metrics[0] 

        self.comboBoxClusterDistance.activated.connect(lambda: setattr(self.app_data, "cluster_distance",self.comboBoxClusterDistance.currentText()))
        # cluster exponent
        self.horizontalSliderClusterExponent.setMinimum(10)  # Represents 1.0 (since 10/10 = 1.0)
        self.horizontalSliderClusterExponent.setMaximum(30)  # Represents 3.0 (since 30/10 = 3.0)
        self.horizontalSliderClusterExponent.setSingleStep(1)  # Represents 0.1 (since 1/10 = 0.1)
        self.horizontalSliderClusterExponent.setTickInterval(1)
        self.horizontalSliderClusterExponent.valueChanged.connect(lambda value: self.labelClusterExponent.setText(str(value/10)))
        self.horizontalSliderClusterExponent.sliderReleased.connect(lambda: setattr(self.app_data, "cluster_exponent",float(self.horizontalSliderClusterExponent.value()/10)))

        # starting seed
        self.lineEditSeed.setValidator(QIntValidator(0,1000000000))
        self.lineEditSeed.editingFinished.connect(lambda: setattr(self.app_data, "cluster_seed",int(self.lineEditSeed.text())))
        self.toolButtonRandomSeed.clicked.connect(self.app_data.generate_random_seed)

        # cluster method
        self.comboBoxClusterMethod.addItems(self.clustering.cluster_methods)
        self.app_data.cluster_method = self.clustering.cluster_methods[0]
        self.toggle_cluster_parameters(self.clustering.cluster_methods[0]) 
        self.comboBoxClusterMethod.activated.connect(lambda: setattr(self.app_data, "cluster_method",self.comboBoxClusterMethod.currentText()))


    def update_field_type_combobox_options(self, parentbox, childbox=None, add_none=False, global_list=False, user_activated=False):
        """Updates a field type comobobox list.

        This method can be used on popup or by forcing an update.
        
        Parameters
        ----------
        parentbox : CustomComboBox
            Field type comobobox to be updated on popup
        childbox : CustomComboBox (optional)
            Field combobox associated with parent combobox
        global_list: bool (optional)
            Indicates whether all field types should be included.  If not, the field type list is determined by
            ``plot_style.plot_type`` and the available field types.  By default, ``False``.
        """
        if self.app_data.sample_id == '' or self.plot_style.plot_type == '':
            return
            
        old_list = parentbox.allItems()
        old_field_type = parentbox.currentText()

        field_dict = self.app_data.field_dict

        new_list = []

        # check if the list should include all options, global_list == True
        if global_list:
            new_list = list(field_dict.keys())
            if 'normalized' not in new_list:
                new_list.append('Analyte (normalized)')
                if 'Ratio' in new_list:
                    new_list.append('Ratio (normalized)')
        else:
            # set the list based on plot_style.plot_type and available field types
            match self.plot_style.plot_type.lower():
                case 'correlation' | 'histogram' | 'tec':
                    if 'Cluster' in field_dict.keys():
                        new_list = ['Cluster']
                    else:
                        new_list = []
                case 'cluster score map':
                    if 'Cluster score' in field_dict.keys():
                        new_list = ['Cluster score']
                    else:
                        new_list = []
                case 'cluster':
                    if 'Cluster' in field_dict.keys():
                        new_list = ['Cluster']
                    elif 'Cluster score' in field_dict.keys():
                        new_list = ['Cluster score']
                    else:
                        new_list=[]
                case 'performance':
                    new_list = []
                case 'score map':
                    if 'score map' in field_dict.keys():
                        new_list = ['score map']
                    else:
                        new_list = []
                case 'ternary map':
                    self.labelCbarDirection.setEnabled(True)
                    self.comboBoxCbarDirection.setEnabled(True)
                case _:
                    new_list = ['Analyte', 'Analyte (normalized)']

                    # add check for ratios
                    if 'Ratio' in field_dict.keys():
                        new_list.append('Ratio')
                        new_list.append('Ratio (normalized)')

                    if 'score map' in field_dict.keys():
                        new_list.append('score map')

                    if 'Cluster' in field_dict.keys():
                        new_list.append('Cluster')

                    if 'Cluster score' in field_dict.keys():
                        new_list.append('Cluster score')

        # add 'None' as first option if required.
        if add_none:
            new_list.insert(0,'None')

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

        if parentbox.currentText() == 'None':
            childbox.clear()
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
        
    def update_field_combobox_options(self, childbox, parentbox=None, spinbox=None, add_none=False, user_activated=False):
        """Updates a field comobobox list.

        This method can be used on popup or by forcing an update.
        
        Parameters
        ----------
        childbox : CustomComboBox
            Field combobox to be updated on popup
        parentbox : CustomComboBox (optional)
            Field type comobobox associated with child combobox
        add_none: bool (optional)
            Indicates whether to add 'none' as an option
        """
        old_list = childbox.allItems()
        # if no parent combobox supplied, then assume field type is `analyte`
        if parentbox is None:
            field_list = self.app_data.field_dict['Analyte']

        # if parent combobox has no field type selected, clear childbox and return
        elif parentbox.currentText() in ['', 'none', 'None']:
            childbox.clear()
            return

        # if parent combobox is supplied, get the field list associated with current field type
        else:
            field_type = parentbox.currentText()
            if 'normalized' in field_type:
                field_type = field_type.replace(' (normalized)','')
            field_list = self.app_data.field_dict[field_type]

        # add 'None' as first option if required
        if add_none:
            field_list.insert(0,'None')

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
        self.toolBox.setCurrentIndex(self.left_tab['sample'])

        if not enable:
            self.plot_style.init_field_widgets(self.plot_style.axis_widget_dict)

            self.PreprocessPage.setEnabled(False)
            self.SelectAnalytePage.setEnabled(False)
            if hasattr(self, "spot_tools"):
                self.spot_tools.setEnabled(False)
            self.ScatterPage.setEnabled(False)
            self.NDIMPage.setEnabled(False)
            self.MultidimensionalPage.setEnabled(False)
            self.ClusteringPage.setEnabled(False)
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
            self.MultidimensionalPage.setEnabled(True)
            self.ClusteringPage.setEnabled(True)
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

    def toolbox_changed(self):
        """Updates styles associated with toolbox page

        Executes on change of ``MainWindow.toolBox.currentIndex()``.  Updates style related widgets.
        """
        if self.logger_options['UI']:
            self.logger.print(f"toolbox_changed")

        if self.app_data.sample_id == '':
            return

        tab_id = self.toolBox.currentIndex()

        data = self.data[self.app_data.sample_id]

        # run clustering before changing plot_type if user selects clustering tab
        if tab_id == self.left_tab['cluster'] :
            self.compute_clusters_update_groups()
            plot_clusters(self,data,self.app_data,self.plot_style)
        # run dim red before changing plot_type if user selects dim red tab
        if tab_id == self.left_tab['multidim'] :
            if self.app_data.update_pca_flag or not data.processed_data.match_attribute('data_type','pca score'):
                self.dimensional_reduction.compute_dim_red(data, self.app_data)
        # update the plot type comboBox options
        self.update_plot_type_combobox_options()
        self.plot_style.plot_type = self.field_control_settings[tab_id]['plot_list'][self.field_control_settings[tab_id]['saved_index']]

        match self.plot_style.plot_type:
            case 'cluster' | 'cluster score map':
                self.labelClusterMax.hide()
                self.spinBoxClusterMax.hide()
                self.labelNClusters.show()
                self.spinBoxNClusters.show()
            case 'cluster performance':
                self.labelClusterMax.show()
                self.spinBoxClusterMax.show()
                self.labelNClusters.hide()
                self.spinBoxNClusters.hide()
            
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
            'scatter', 'ndim', pca', 'filters',''clustering', 'cluster', 'polygons',
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
            self.actionReset.setEnabled(True)
            self.actionFilters.setEnabled(True)
            self.actionPolygons.setEnabled(True)
            self.actionClusters.setEnabled(True)
            self.actionProfiles.setEnabled(True)
            self.actionInfo.setEnabled(True)
            self.actionNotes.setEnabled(True)
        else:
            self.actionReset.setEnabled(False)
            self.actionFilters.setEnabled(False)
            self.actionPolygons.setEnabled(False)
            self.actionClusters.setEnabled(False)
            self.actionProfiles.setEnabled(False)
            self.actionInfo.setEnabled(False)
            self.actionNotes.setEnabled(False)

    def toggle_help_mode(self):
        """Toggles help mode

        Toggles ``MainWindow.actionHelp``, when checked, the cursor will change so indicates help tool is active.
        """        
        if self.actionHelp.isChecked():
            self.setCursor(Qt.CursorShape.WhatsThisCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def canvas_changed(self):
        """Sets visibility of canvas tools and updates canvas plots"""        
        if self.app_data.sample_id == '':
            self.toolButtonHome.setVisible(False)
            self.toolButtonPan.setVisible(False)
            self.toolButtonZoom.setVisible(False)
            self.toolButtonAnnotate.setVisible(False)
            self.toolButtonDistance.setVisible(False)
            self.toolButtonPopFigure.setVisible(False)
            self.toolButtonSave.setVisible(False)
            self.widgetPlotInfoSV.hide()
            self.labelMaxRows.setVisible(False)
            self.spinBoxMaxRows.setVisible(False)
            self.labelMaxCols.setVisible(False)
            self.spinBoxMaxCols.setVisible(False)
            self.comboBoxMVPlots.setVisible(False)
            self.toolButtonRemoveMVPlot.setVisible(False)
            self.toolButtonRemoveAllMVPlots.setVisible(False)
            self.widgetPlotInfoMV.hide()
            self.comboBoxQVList.setVisible(False)
            self.toolButtonNewList.setVisible(False)

            self.actionUpdatePlot.setEnabled(False)
            self.actionSavePlotToTree.setEnabled(False)
            return

        if self.canvasWindow.currentIndex() == self.canvas_tab['sv']:
            # plot toolbar items
            self.toolButtonHome.setVisible(True)
            self.toolButtonPan.setVisible(True)
            self.toolButtonZoom.setVisible(True)
            self.toolButtonAnnotate.setVisible(True)
            self.toolButtonDistance.setVisible(True)
            self.toolButtonPopFigure.setVisible(True)
            self.toolButtonSave.setVisible(True)
            self.widgetPlotInfoSV.show()
            self.labelMaxRows.setVisible(False)
            self.spinBoxMaxRows.setVisible(False)
            self.labelMaxCols.setVisible(False)
            self.spinBoxMaxCols.setVisible(False)
            self.comboBoxMVPlots.setVisible(False)
            self.toolButtonRemoveMVPlot.setVisible(False)
            self.toolButtonRemoveAllMVPlots.setVisible(False)
            self.widgetPlotInfoMV.hide()
            self.comboBoxQVList.setVisible(False)
            self.toolButtonNewList.setVisible(False)

            self.SelectAnalytePage.setEnabled(True)
            self.PreprocessPage.setEnabled(True)
            self.ScatterPage.setEnabled(True)
            self.NDIMPage.setEnabled(True)
            self.MultidimensionalPage.setEnabled(True)
            self.ClusteringPage.setEnabled(True)
            if hasattr(self, "spot_tools"):
                self.spot_tools.setEnabled(True)
            if hasattr(self, "special_tools"):
                self.special_tools.setEnabled(True)
            if hasattr(self, "mask_dock"):
                self.mask_dock.setEnabled(True)

            self.toolBoxStyle.setEnabled(True)
            self.comboBoxPlotType.setEnabled(True)
            self.comboBoxStyleTheme.setEnabled(True)
            self.actionUpdatePlot.setEnabled(True)
            self.actionSavePlotToTree.setEnabled(True)
            self.toolButtonSaveTheme.setEnabled(True)

            self.dockWidgetStyling.setEnabled(True)

            if self.duplicate_plot_info:
                self.add_plotwidget_to_canvas(self.duplicate_plot_info)
        elif self.canvasWindow.currentIndex() == self.canvas_tab['mv']:
            # plot toolbar items
            self.toolButtonHome.setVisible(False)
            self.toolButtonPan.setVisible(False)
            self.toolButtonZoom.setVisible(False)
            self.toolButtonAnnotate.setVisible(False)
            self.toolButtonDistance.setVisible(False)
            self.toolButtonPopFigure.setVisible(False)
            self.toolButtonSave.setVisible(True)
            self.widgetPlotInfoSV.hide()
            self.labelMaxRows.setVisible(True)
            self.spinBoxMaxRows.setVisible(True)
            self.labelMaxCols.setVisible(True)
            self.spinBoxMaxCols.setVisible(True)
            self.comboBoxMVPlots.setVisible(True)
            self.toolButtonRemoveMVPlot.setVisible(True)
            self.toolButtonRemoveAllMVPlots.setVisible(True)
            self.widgetPlotInfoMV.show()
            self.comboBoxQVList.setVisible(False)
            self.toolButtonNewList.setVisible(False)

            self.SelectAnalytePage.setEnabled(False)
            self.PreprocessPage.setEnabled(False)
            self.ScatterPage.setEnabled(False)
            self.NDIMPage.setEnabled(False)
            self.MultidimensionalPage.setEnabled(False)
            self.ClusteringPage.setEnabled(False)
            if hasattr(self, "spot_tools"):
                self.spot_tools.setEnabled(False)
            if hasattr(self, "special_tools"):
                self.special_tools.setEnabled(False)
            if hasattr(self, "mask_dock"):
                self.mask_dock.setEnabled(False)

            self.actionUpdatePlot.setEnabled(False)
            self.actionSavePlotToTree.setEnabled(False)

            self.dockWidgetStyling.setEnabled(False)
            if self.duplicate_plot_info:
                self.add_plotwidget_to_canvas(self.duplicate_plot_info)
        else:
            # plot toolbar items
            self.toolButtonHome.setVisible(False)
            self.toolButtonPan.setVisible(False)
            self.toolButtonZoom.setVisible(False)
            self.toolButtonAnnotate.setVisible(False)
            self.toolButtonDistance.setVisible(False)
            self.toolButtonPopFigure.setVisible(False)
            self.toolButtonSave.setVisible(True)
            self.widgetPlotInfoSV.hide()
            self.labelMaxRows.setVisible(False)
            self.spinBoxMaxRows.setVisible(False)
            self.labelMaxCols.setVisible(False)
            self.spinBoxMaxCols.setVisible(False)
            self.comboBoxMVPlots.setVisible(False)
            self.toolButtonRemoveMVPlot.setVisible(False)
            self.toolButtonRemoveAllMVPlots.setVisible(False)
            self.widgetPlotInfoMV.hide()
            self.comboBoxQVList.setVisible(True)
            self.toolButtonNewList.setVisible(True)

            self.SelectAnalytePage.setEnabled(False)
            self.PreprocessPage.setEnabled(False)
            self.ScatterPage.setEnabled(False)
            self.NDIMPage.setEnabled(False)
            self.MultidimensionalPage.setEnabled(False)
            self.ClusteringPage.setEnabled(False)
            if hasattr(self, "spot_tools"):
                self.spot_tools.setEnabled(False)
            if hasattr(self, "special_tools"):
                self.special_tools.setEnabled(False)
            if hasattr(self, "mask_dock"):
                self.mask_dock.setEnabled(False)

            self.dockWidgetStyling.setEnabled(False)
            self.actionUpdatePlot.setEnabled(False)
            self.actionSavePlotToTree.setEnabled(False)

            self.display_QV()

    

    def update_labels(self):
        """Updates flags on statusbar indicating negative/zero and nan values within the processed_data_frame"""        

        data = self.data[self.app_data.sample_id].processed_data

        columns = data.match_attributes({'data_type': 'Analyte', 'use': True}) + data.match_attributes({'data_type': 'Ratio', 'use': True})
        negative_count = any(data[columns] <= 0)
        nan_count = any(np.isnan(data[columns]))
        
        self.labelInvalidValues.setText(f"Negative/zeros: {negative_count}, NaNs: {nan_count}")


    def connect_app_data_observers(self, app_data):
        app_data.add_observer("sort_method", self.update_sort_method)
        app_data.add_observer("ref_chem", self.update_ref_index_combobox)
        app_data.add_observer("sample_list", self.update_sample_list_combobox)
        app_data.add_observer("sample_id", self.update_sample_id_combobox)
        app_data.add_observer("apply_process_to_all_data", self.update_autoscale_checkbox)
        app_data.add_observer("equalize_color_scale", self.update_equalize_color_scale_toolbutton)
        app_data.add_observer("field_type", self.plot_style.update_field_type)
        app_data.add_observer("field", self.plot_style.update_field)
        app_data.add_observer("hist_bin_width", self.update_hist_bin_width_spinbox)
        app_data.add_observer("hist_num_bins", self.update_hist_num_bins_spinbox)
        app_data.add_observer("hist_plot_style", self.update_hist_plot_style_combobox)
        app_data.add_observer("corr_method", self.update_corr_method_combobox)
        app_data.add_observer("corr_squared", self.update_corr_squared_checkbox)
        app_data.add_observer("noise_red_method", self.update_noise_red_method_combobox)
        app_data.add_observer("noise_red_option1", self.update_noise_red_option1_spinbox)
        app_data.add_observer("noise_red_option2", self.update_noise_red_option2_spinbox)
        app_data.add_observer("gradient_flag", self.update_gradient_flag_checkbox)
        app_data.add_observer("scatter_preset", self.update_scatter_preset_combobox)
        app_data.add_observer("heatmap_style", self.update_heatmap_style_combobox)
        app_data.add_observer("ternary_colormap", self.update_ternary_colormap_combobox)
        app_data.add_observer("ternary_color_x", self.update_ternary_color_x_toolbutton)
        app_data.add_observer("ternary_color_y", self.update_ternary_color_y_toolbutton)
        app_data.add_observer("ternary_color_z", self.update_ternary_color_z_toolbutton)
        app_data.add_observer("ternary_color_m", self.update_ternary_color_m_toolbutton)
        app_data.add_observer("norm_reference", self.update_norm_reference_combobox)
        app_data.add_observer("ndim_analyte_set", self.update_ndim_analyte_set_combobox)
        app_data.add_observer("ndim_quantile_index", self.update_ndim_quantile_index_combobox)
        app_data.add_observer("dim_red_method", self.update_dim_red_method_combobox)
        app_data.add_observer("dim_red_x", self.update_dim_red_x_spinbox)
        app_data.add_observer("dim_red_y", self.update_dim_red_y_spinbox)
        app_data.add_observer("dim_red_x_min", self.update_dim_red_x_min_spinbox)
        app_data.add_observer("dim_red_y_min", self.update_dim_red_y_min_spinbox)
        app_data.add_observer("dim_red_x_max", self.update_dim_red_x_max_spinbox)
        app_data.add_observer("dim_red_y_max", self.update_dim_red_y_max_spinbox)
        app_data.add_observer("cluster_method", self.update_cluster_method_combobox)
        app_data.add_observer("max_clusters", self.update_max_clusters_spinbox)
        app_data.add_observer("num_clusters", self.update_num_clusters_spinbox)
        app_data.add_observer("cluster_seed", self.update_cluster_seed_lineedit)
        app_data.add_observer("cluster_exponent", self.update_cluster_exponent_slider)
        app_data.add_observer("cluster_distance", self.update_cluster_distance_combobox)
        app_data.add_observer("dim_red_precondition", self.update_dim_red_precondition_checkbox)
        app_data.add_observer("num_basis_for_precondition", self.update_num_basis_for_precondition_spinbox)
        app_data.add_observer("selected_clusters", self.update_selected_clusters_spinbox)

    def connect_plot_style_observers(self, plot_style):
        plot_style.add_observer("plot_type", self.plot_style.update_plot_type)
        plot_style.add_observer("xlim", self.update_xlim_lineedits)
        plot_style.add_observer("xlabel", self.update_xlabel_lineedit)
        plot_style.add_observer("xscale", self.update_xscale_combobox)
        plot_style.add_observer("ylim", self.update_ylim_lineedits)
        plot_style.add_observer("ylabel", self.update_ylabel_lineedit)
        plot_style.add_observer("yscale", self.update_yscale_combobox)
        plot_style.add_observer("zlim", self.update_zlim_lineedits)
        plot_style.add_observer("zlabel", self.update_zlabel_lineedit)
        plot_style.add_observer("zscale", self.update_zscale_combobox)
        plot_style.add_observer("aspect_ratio", self.update_aspect_ratio_lineedit)
        plot_style.add_observer("tick_dir", self.update_tick_dir_combobox)
        plot_style.add_observer("font_family", self.update_font_family_combobox)
        plot_style.add_observer("font_size", self.update_font_size_spinbox)
        plot_style.add_observer("scale_dir", self.plot_style.update_scale_direction_combobox)
        plot_style.add_observer("scale_location", self.update_scale_location_combobox)
        plot_style.add_observer("scale_length", self.update_scale_length_lineedit)
        plot_style.add_observer("overlay_color", self.update_overlay_color_toolbutton)
        plot_style.add_observer("show_mass", self.update_show_mass_checkbox)
        plot_style.add_observer("marker_symbol", self.update_marker_symbol_combobox)
        plot_style.add_observer("marker_size", self.update_marker_size_spinbox)
        plot_style.add_observer("marker_color", self.update_marker_color_toolbutton)
        plot_style.add_observer("marker_alpha", self.update_marker_alpha_slider)
        plot_style.add_observer("line_width", self.update_line_width_combobox)
        plot_style.add_observer("line_multiplier", self.update_line_multiplier_lineedit)
        plot_style.add_observer("line_color", self.update_line_color_toolbutton)
        plot_style.add_observer("cmap", self.update_cmap_combobox)
        plot_style.add_observer("cbar_reverse", self.update_cbar_reverse_checkbox)
        plot_style.add_observer("cbar_direction", self.update_cbar_direction_combobox)
        plot_style.add_observer("clim", self.update_clim_lineedits)
        plot_style.add_observer("clabel", self.update_clabel_lineedit)
        plot_style.add_observer("cscale", self.update_cscale_combobox)
        plot_style.add_observer("resolution", self.update_resolution_spinbox)

    def connect_data_observers(self, data):
        data.add_observer("nx", self.update_nx_lineedit)
        data.add_observer("ny", self.update_ny_lineedit)
        data.add_observer("dx", self.update_dx_lineedit)
        data.add_observer("dy", self.update_dy_lineedit)
        data.add_observer("data_min_quantile", self.update_data_min_quantile)
        data.add_observer("data_max_quantile", self.update_data_max_quantile)
        data.add_observer("data_min_diff_quantile", self.update_data_min_diff_quantile)
        data.add_observer("data_max_diff_quantile", self.update_data_max_diff_quantile)
        data.add_observer("data_auto_scale_value", self.update_auto_scale_value)
        data.add_observer("apply_outlier_to_all", self.update_apply_outlier_to_all)
        data.add_observer("outlier_method", self.update_outlier_method)
        data.add_observer("outlier_method", self.update_negative_handling_method)


    def toggle_spot_tab(self):
        #self.actionSpotTools.toggle()
        if self.actionSpotTools.isChecked():
            # add spot page to MainWindow.toolBox
            self.spot_tools = SpotPage(self.left_tab['sample'], self)
            self.actionImportSpots.setVisible(True)
        else:
            self.toolBox.removeItem(self.left_tab['spot'])
            self.actionImportSpots.setVisible(False)
        self.reindex_left_tab()

    def toggle_special_tab(self):
        if self.actionSpecialTools.isChecked():
            self.special_tools = SpecialPage(self.left_tab['cluster'], self)
        else:
            self.toolBox.removeItem(self.left_tab['special'])
        self.reindex_left_tab()

    def toggle_regression_tab(self):
        if self.actionRegression.isChecked():
            pass
            #self.regression_tools = RegressionPage(self.right_tab['stylecolors'], self)
        else:
            self.toolBox.removeItem(self.left_tab['regression'])
        self.reindex_style_tab()

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
        self.field_control_settings = {-1: {'saved_index': 0, 'plot_list': ['field map'], 'label': ['','','','Map'], 'saved_field_type': [None, None, None, None], 'saved_field': [None, None, None, None]}} # -1 is for digitizing polygons and profiles

        for tid in range(0,self.toolBox.count()):
            match self.toolBox.itemText(tid).lower():
                case 'preprocess':
                    self.left_tab.update({'process': tid})
                    self.field_control_settings.update({self.left_tab['process']: {'saved_index': 0, 'plot_list': ['field map', 'gradient map'], 'label': ['','','','Map'], 'saved_field_type': [None, None, None, None], 'saved_field': [None, None, None, None]}})
                case 'field viewer':
                    self.left_tab.update({'sample': tid})
                    self.field_control_settings.update({self.left_tab['sample']: {'saved_index': 0, 'plot_list': ['field map', 'histogram', 'correlation'], 'label': ['','','','Map'], 'saved_field_type': [None, None, None, None], 'saved_field': [None, None, None, None]}})
                case 'spot data':
                    self.left_tab.update({'spot': tid})
                    self.field_control_settings.update({self.left_tab['spot']: {'saved_index': 0, 'plot_list': ['field map', 'gradient map'], 'label': ['','','','Map'], 'saved_field_type': [None, None, None, None], 'saved_field': [None, None, None, None]}})
                case 'scatter and heatmaps':
                    self.left_tab.update({'scatter': tid})
                    self.field_control_settings.update({self.left_tab['scatter']: {'saved_index': 0, 'plot_list': ['scatter', 'heatmap', 'ternary map'], 'label': ['X','Y','Z','Color'], 'saved_field_type': [None, None, None, None], 'saved_field': [None, None, None, None]}})
                case 'n-dim':
                    self.left_tab.update({'ndim': tid})
                    self.field_control_settings.update({self.left_tab['ndim']: {'saved_index': 0, 'plot_list': ['TEC', 'Radar'], 'label': ['','','','Color'], 'saved_field_type': [None, None, None, None], 'saved_field': [None, None, None, None]}})
                case 'dimensional reduction':
                    self.left_tab.update({'multidim': tid})
                    self.field_control_settings.update({self.left_tab['multidim']: {'saved_index': 0, 'plot_list': ['variance','basis vectors','dimension scatter','dimension heatmap','dimension score map'], 'label': ['PC','PC','','Color'], 'saved_field_type': [None, None, None, None], 'saved_field': [None, None, None, None]}})
                case 'clustering':
                    self.left_tab.update({'cluster': tid})
                    self.field_control_settings.update({self.left_tab['cluster']: {'saved_index': 0, 'plot_list': ['cluster', 'cluster score map', 'cluster performance'], 'label': ['','','',''], 'saved_field_type': [None, None, None, None], 'saved_field': [None, None, None, None]}})
                case 'p-t-t functions':
                    self.left_tab.update({'special': tid})
                    self.field_control_settings.update({self.left_tab['special']: {'saved_index': 0, 'plot_list': ['field map', 'gradient map', 'cluster score map', 'dimension score map', 'profile'], 'label': ['','','','Map'], 'saved_field_type': [None, None, None, None], 'saved_field': [None, None, None, None]}})


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

    def toggle_cluster_parameters(self,method):
        if method == 'k-means':
            self.horizontalSliderClusterExponent.setEnabled(False)
            self.labelClusterExponent.setEnabled(False)
            self.labelClusterDistance.setEnabled(False)
        else:
            self.horizontalSliderClusterExponent.setEnabled(True)
            self.labelClusterExponent.setEnabled(True)
            self.labelClusterDistance.setEnabled(True)
        
    # -------------------------------
    # UI update functions
    # Executed when a property is changed
    # -------------------------------


    def update_sort_method(self, new_method):
        self.plot_tree.sort_tree(None, method=new_method)

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
        if self.logger_options['Data']:
            self.logger.print(f"change_sample\n")

        # set plot flag to false, allow plot to update only at the end
        self.plot_flag = False

        if self.app_data.sample_id not in self.data:
            self.io.initialise_sample_object(outlier_method=self.comboBoxOutlierMethod.currentText(), negative_method = self.comboBoxNegativeMethod.currentText())
            self.connect_data_observers(self.data[self.app_data.sample_id])
            # enable widgets that require self.data not be empty
            self.toggle_data_widgets()
            
            # add sample to the plot tree
            self.plot_tree.add_sample(self.app_data.sample_id)
            self.plot_tree.update_tree()

        self.update_mask_and_profile_widgets()

        # sort data
        self.plot_tree.sort_tree(None, method=self.app_data.sort_method)

        # precalculate custom fields
        if hasattr(self, "calculator") and self.calculator.precalculate_custom_fields:
            for name in self.calc_dict.keys():
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

        # allow plots to be updated again
        self.plot_flag = True

        # trigger update to plot
        self.plot_style.schedule_update()

    def update_ui_on_sample_change(self):
        if self.logger_options['UI']:
            self.logger.print(f"update_ui_on_sample_change\n")
        # reset all plot types on change of tab to the first option
        for key in self.field_control_settings.keys():
            self.field_control_settings[key]['saved_index'] = 0

        self.init_tabs(enable=True)

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
        self.canvas_changed()
        
        # set toolbox tab indexes
        self.toolBoxStyle.setCurrentIndex(0)
        self.toolBox.setCurrentIndex(self.left_tab['sample'])
        self.toolbox_changed()

        # update combobox to reflect list of available field types and fields
        self.update_field_type_combobox_options(self.comboBoxFieldTypeC, self.comboBoxFieldC)



    def update_widget_data_on_sample_change(self):
        if self.logger_options['UI']:
            self.logger.print(f"update_widget_data_on_sample_change\n")

        self.update_field_combobox_options(self.comboBoxNDimAnalyte)

        data = self.data[self.app_data.sample_id]
        # update dx, dy, nx, ny
        self.update_dx_lineedit(data.dx)
        self.update_dy_lineedit(data.dy)
        self.update_nx_lineedit(data.nx)
        self.update_nx_lineedit(data.ny)

        # update c_field_type and c_field
        self.app_data.c_field_type = 'Analyte'
        field = ''
        if self.app_data.selected_analytes is None:
            field = data.processed_data.match_attribute('data_type','Analyte')[0]
        else:
            field = self.app_data.selected_analytes[0]
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
        if self.logger_options['Data']:
            self.logger.print(f"update_mask_and_profile_widgets\n")
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
            Field type for plotting, options include: 'Analyte', 'Ratio', 'pca', 'cluster', 'cluster score map',
            'Special', 'Computed'. Some options require a field. Defaults to 'Analyte'
        """
        if self.logger_options['Data']:
            self.logger.print(f"update_autoscale_widgets\n  field={field}")
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
        if self.logger_options['Data']:
            self.logger.print(f"update_mask_dock\n")
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
        if self.logger_options['UI']:
            self.logger.print(f"field_spinbox_changed: ax={ax}")

        widget = self.plot_style.axis_widget_dict

        widget['spinbox'][ax].blockSignals(True)
        if widget['spinbox'][ax].value() != widget['childbox'][ax].currentIndex():
            widget['childbox'][ax].setCurrentIndex(widget['spinbox'][ax].value())
            self.plot_style.update_field(ax)
        widget['spinbox'][ax].blockSignals(False)

    def update_hist_bin_width_spinbox(self, value):
        self.doubleSpinBoxBinWidth.setValue(value)
        if self.toolBox.currentIndex() == self.left_tab['sample'] and self.plot_style.plot_type == "histogram":
            self.plot_style.schedule_update()

    def update_hist_num_bins_spinbox(self, value):
        self.spinBoxNBins.setValue(value)
        if self.toolBox.currentIndex() == self.left_tab['sample'] and self.plot_style.plot_type == "histogram":
            self.plot_style.schedule_update()

    def update_hist_plot_style_combobox(self, new_hist_plot_style):
        self.comboBoxHistType.setCurrentText(new_hist_plot_style)
        if self.toolBox.currentIndex() == self.left_tab['sample'] and self.plot_style.plot_type == "histogram":
            self.plot_style.schedule_update()

    def update_corr_method_combobox(self, new_corr_method):
        self.comboBoxCorrelationMethod.setCurrentText(new_corr_method)
        if self.toolBox.currentIndex() == self.left_tab['sample'] and self.plot_style.plot_type == "correlation":
            self.plot_style.schedule_update()

    def update_corr_squared_checkbox(self, new_corr_squared):
        self.checkBoxCorrelationSquared.setChecked(new_corr_squared)
        if self.toolBox.currentIndex() == self.left_tab['sample'] and self.plot_style.plot_type == "correlation":
            self.plot_style.schedule_update()
    
    def update_noise_red_method_combobox(self, new_noise_red_method):
        self.comboBoxNoiseReductionMethod.setCurrentText(new_noise_red_method)
        if self.toolBox.currentIndex() == self.left_tab['sample']:
            self.plot_style.schedule_update()

    def update_noise_red_option1_spinbox(self, new_noise_red_option1):
        self.spinBoxNoiseOption1.setValue(new_noise_red_option1)
        if self.toolBox.currentIndex() == self.left_tab['sample']:
            self.plot_style.schedule_update()

    def update_noise_red_option2_spinbox(self, new_noise_red_option2):
        self.doubleSpinBoxNoiseOption2.setValue(new_noise_red_option2)
        if self.toolBox.currentIndex() == self.left_tab['sample']:
            self.plot_style.schedule_update()
    
    def update_gradient_flag_checkbox(self, new_gradient_flag):
        self.checkBoxGradient.setChecked(new_gradient_flag)
        if self.toolBox.currentIndex() == self.left_tab['sample']:
            self.plot_style.schedule_update()

    def update_scatter_preset_combobox(self, new_scatter_preset):
        if self.toolBox.currentIndex() == self.left_tab['scatter']:
            self.plot_style.schedule_update()

    def update_heatmap_style_combobox(self, new_heatmap_style):
        self.comboBoxHeatmaps.setCurrentText(new_heatmap_style)
        if self.toolBox.currentIndex() == self.left_tab['scatter']:
            self.plot_style.schedule_update()

    def update_ternary_colormap_combobox(self, new_ternary_colormap):
        self.comboBoxTernaryColormap.setCurrentText(new_ternary_colormap)
        if self.toolBox.currentIndex() == self.left_tab['scatter']:
            self.plot_style.schedule_update()

    def update_ternary_color_x_toolbutton(self, new_color):
        self.toolButtonTCmapXColor.setStyleSheet("background-color: %s;" % new_color)
        if self.toolBox.currentIndex() == self.left_tab['scatter']:
            self.plot_style.schedule_update()

    def update_ternary_color_y_toolbutton(self, new_color):
        self.toolButtonTCmapYColor.setStyleSheet("background-color: %s;" % new_color)
        if self.toolBox.currentIndex() == self.left_tab['scatter']:
            self.plot_style.schedule_update()

    def update_ternary_color_z_toolbutton(self, new_color):
        self.toolButtonTCmapZColor.setStyleSheet("background-color: %s;" % new_color)
        if self.toolBox.currentIndex() == self.left_tab['scatter']:
            self.plot_style.schedule_update()

    def update_ternary_color_m_toolbutton(self, new_color):
        self.toolButtonTCmapMColor.setStyleSheet("background-color: %s;" % new_color)
        if self.toolBox.currentIndex() == self.left_tab['scatter']:
            self.plot_style.schedule_update()

    def update_norm_reference_combobox(self, new_norm_reference):
        if self.toolBox.currentIndex() == self.left_tab['ndim']:
            self.plot_style.schedule_update()

    def update_ndim_analyte_set_combobox(self, new_ndim_analyte_set):
        self.comboBoxNDimAnalyteSet.setCurrentText(new_ndim_analyte_set)
        if self.toolBox.currentIndex() == self.left_tab['ndim']:
            self.plot_style.schedule_update()

    def update_ndim_table(self,calling_widget):
        """Updates tableWidgetNDim"""
        def on_use_checkbox_state_changed(row, state):
            # Update the 'use' value in the filter_df for the given row
            self.data[self.app_data.sample_id].filter_df.at[row, 'use'] = state == Qt.CheckState.Checked

        if calling_widget == 'analyteAdd':
            el_list = [self.comboBoxNDimAnalyte.currentText().lower()]
            self.comboBoxNDimAnalyteSet.setCurrentText('user defined')
        elif calling_widget == 'analyteSetAdd':
            el_list = self.app_data.ndim_list_dict[self.comboBoxNDimAnalyteSet.currentText()]

        analytes_list = self.data[self.app_data.sample_id].processed_data.match_attribute('data_type','Analyte')

        analytes = [col for iso in el_list for col in analytes_list if re.sub(r'\d', '', col).lower() == re.sub(r'\d', '',iso).lower()]

        self.app_data.ndim_list.extend(analytes)

        for analyte in analytes:
            # Add a new row at the end of the table
            row = self.tableWidgetNDim.rowCount()
            self.tableWidgetNDim.insertRow(row)

            # Create a QCheckBox for the 'use' column
            chkBoxItem_use = QCheckBox()
            chkBoxItem_use.setCheckState(Qt.CheckState.Checked)
            chkBoxItem_use.stateChanged.connect(lambda state, row=row: on_use_checkbox_state_changed(row, state))

            self.tableWidgetNDim.setCellWidget(row, 0, chkBoxItem_use)
            self.tableWidgetNDim.setItem(row, 1, QTableWidgetItem(analyte))
    
    def save_ndim_list(self):
        # get the list name from the user
        name, ok = QInputDialog.getText(self, 'Save custom TEC list', 'Enter name for new list:')
        if ok:
            try:
                self.ndim_list_dict[name] = self.tableWidgetNDim.column_to_list('Analyte')

                # export the csv
                csvdict.export_dict_to_csv(self.ndim_list_dict,self.ndim_list_filename)
            except:
                QMessageBox.warning(self,'Error','could not save TEC file.')
                
        else:
            # throw a warning that name is not saved
            QMessageBox.warning(self,'Error','could not save TEC list.')

            return

    def update_ndim_quantile_index_combobox(self, new_ndim_quantile_index):
        self.comboBoxNDimQuantiles.setCurrentIndex(new_ndim_quantile_index)
        if self.toolBox.currentIndex() == self.left_tab['ndim']:
            self.plot_style.schedule_update()

    def update_dim_red_method_combobox(self, new_dim_red_method):
        self.ComboBoxDimRedTechnique.setCurrentText(new_dim_red_method)
        # if self.toolBox.currentIndex() == self.left_tab['multidim']:
        #     self.plot_style.schedule_update()

    def update_dim_red_x_spinbox(self, new_dim_red_x):
        self.spinBoxPCX.setValue(int(new_dim_red_x))
        if self.toolBox.currentIndex() == self.left_tab['multidim']:
            self.plot_style.schedule_update()

    def update_dim_red_y_spinbox(self, new_dim_red_y):
        self.spinBoxPCY.setValue(int(new_dim_red_y))
        if self.toolBox.currentIndex() == self.left_tab['multidim']:
            self.plot_style.schedule_update()

    def update_dim_red_x_min_spinbox(self, new_dim_red_x_min):
        self.spinBoxPCX.setMinimum(int(new_dim_red_x_min))


    def update_dim_red_x_max_spinbox(self, new_dim_red_x_max):
        self.spinBoxPCX.setMaximum(int(new_dim_red_x_max))


    def update_dim_red_y_min_spinbox(self, new_dim_red_y_min):
        self.spinBoxPCY.setMinimum(int(new_dim_red_y_min))


    def update_dim_red_y_max_spinbox(self, new_dim_red_y):
        self.spinBoxPCY.setMaximum(int(new_dim_red_y))

    def update_cluster_method_combobox(self, new_cluster_method):
        self.comboBoxClusterMethod.setCurrentText(new_cluster_method)
        if self.toolBox.currentIndex() == self.left_tab['cluster']:
            self.toggle_cluster_parameters(new_cluster_method)
            self.plot_style.schedule_update()

    def update_max_clusters_spinbox(self, new_max_clusters):
        self.spinBoxClusterMax.setValue(int(new_max_clusters))
        if self.toolBox.currentIndex() == self.left_tab['cluster']:
            self.plot_style.schedule_update()

    def update_num_clusters_spinbox(self, new_num_clusters):
        self.spinBoxNClusters.setValue(int(new_num_clusters))
        if self.toolBox.currentIndex() == self.left_tab['cluster']:
            self.plot_style.schedule_update()

    def update_cluster_seed_lineedit(self, new_cluster_seed):
        self.lineEditSeed.setText(str(new_cluster_seed))
        if self.toolBox.currentIndex() == self.left_tab['cluster']:
            self.plot_style.schedule_update()

    def update_cluster_exponent_slider(self, new_cluster_exponent):
        self.horizontalSliderClusterExponent.setValue(int(new_cluster_exponent*10))
        self.labelClusterExponent.setText(str(new_cluster_exponent))
        if self.toolBox.currentIndex() == self.left_tab['cluster']:
            self.plot_style.schedule_update()

    def update_cluster_distance_combobox(self, new_cluster_distance):
        if self.toolBox.currentIndex() == self.left_tab['cluster']:
            self.plot_style.schedule_update()

    def update_dim_red_precondition_checkbox(self, new_pca_precondition):
        if self.toolBox.currentIndex() == self.left_tab['cluster']:
            self.plot_style.schedule_update()

    def update_num_basis_for_precondition_spinbox(self, new_num_pca_basis_for_precondition):
        if self.toolBox.currentIndex() == self.left_tab['cluster']:
            self.plot_style.schedule_update()

    def update_selected_clusters_spinbox(self, new_selected_clusters):
        if self.toolBox.currentIndex() == self.left_tab['cluster']:
            self.plot_style.schedule_update()


    def update_sample_id(self):
        """Updates ``app_data.sample_id``"""
        if self.app_data.sample_id == self.comboBoxSampleId.currentText():
            return

        if self.logger_options['Data']:
            self.logger.print(f"update_sample_id: {self.app_data.sample_id}\n")

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
        if self.logger_options['UI']:
            self.logger.print("update_plot_top_combobox_options")


        if self.profile_state == True or self.polygon_state == True:
            plot_idx = -1
        else:
            plot_idx = self.toolBox.currentIndex()

        plot_types = self.field_control_settings[plot_idx]['plot_list']
        
        if plot_types == self.comboBoxPlotType.allItems():
            return

        self.comboBoxPlotType.clear()
        self.comboBoxPlotType.addItems(plot_types)
        self.comboBoxPlotType.setCurrentText(plot_types[self.field_control_settings[plot_idx]['saved_index']])

        self.plot_style.plot_type = self.comboBoxPlotType.currentText()


    def update_equalize_color_scale(self):
        self.app_data.equalize_color_scale = self.toolButtonScaleEqualize.isChecked()
        if self.plot_style.plot_type == "field map":
            self.plot_style.schedule_update()

    def update_corr_method(self):
        self.app_data.corr_method = self.comboBoxCorrelationMethod.currentText()
        self.correlation_method_callback()

    def update_corr_squared(self):
        self.app_data.corr_squared = self.checkBoxCorrelationSquared.isChecked()
        self.correlation_squared_callback()

   # -------------------------------------
    # Correlation functions and plotting
    # -------------------------------------
    def correlation_method_callback(self):
        """Updates colorbar label for correlation plots"""
        method = self.app_data.corr_method
        if self.plot_style.clabel == method:
            return

        if self.app_data.corr_squared:
            power = '^2'
        else:
            power = ''

        # update colorbar label for change in method
        match method:
            case 'Pearson':
                self.plot_style.clabel = method + "'s $r" + power + "$"
            case 'Spearman':
                self.plot_style.clabel = method + "'s $\\rho" + power + "$"
            case 'Kendall':
                self.plot_style.clabel = method + "'s $\\tau" + power + "$"

        if self.plot_style.plot_type != 'correlation':
            self.plot_style.plot_type = 'correlation'

        # trigger update to plot
        self.plot_style.schedule_update()

    def correlation_squared_callback(self):
        """Produces a plot of the squared correlation."""        
        # update color limits and colorbar
        if self.app_data.corr_squared:
            self.plot_style.clim = [0,1]
            self.plot_style.cmap = 'cmc.oslo'
        else:
            self.plot_style.clim = [-1,1]
            self.plot_style.cmap = 'RdBu'

        # update label
        self.correlation_method_callback()

        # trigger update to plot
        self.plot_style.schedule_update()

    def update_xlim_lineedits(self, new_xlim):
        self.lineEditXLB.value = new_xlim[0]
        self.lineEditXUB.value = new_xlim[1]
        self.plot_style.schedule_update()

    def update_xlabel_lineedit(self, new_label):
        self.lineEditXLabel.setText(new_label)
        self.plot_style.schedule_update()
        
    def update_xscale_combobox(self, new_scale):
        self.comboBoxXScale.setCurrentText(new_scale)
        self.plot_style.schedule_update()

    def update_ylim_lineedits(self, new_ylim):
        self.lineEditYLB.value = new_ylim[0]
        self.lineEditYUB.value = new_ylim[1]
        self.plot_style.schedule_update()

    def update_ylabel_lineedit(self, new_label):
        self.lineEditYLabel.setText(new_label)
        self.plot_style.schedule_update()

    def update_yscale_combobox(self, new_scale):
        self.comboBoxYScale.setCurrentText(new_scale)
        self.plot_style.schedule_update()

    def update_zlim_lineedits(self, new_zlim):
        self.lineEditZLB.value = new_zlim[0]
        self.lineEditZUB.value = new_zlim[1]
        self.plot_style.schedule_update()

    def update_zlabel_lineedit(self, new_label):
        self.lineEditZLabel.setText(new_label)
        self.plot_style.schedule_update()
        
    def update_zscale_combobox(self, new_scale):
        self.comboBoxZScale.setCurrentText(new_scale)
        self.plot_style.schedule_update()

    def update_aspect_ratio_lineedit(self, new_aspect_ratio):
        self.lineEditAspectRatio.value = new_aspect_ratio
        self.plot_style.schedule_update()

    def update_tick_dir_combobox(self, new_tick_dir):
        self.comboBoxTickDirection.setCurrentText(new_tick_dir)
        self.plot_style.schedule_update()

    def update_scale_location_combobox(self, new_scale_location):
        self.comboBoxScaleLocation.setCurrentText(new_scale_location)
        self.plot_style.schedule_update()

    def update_scale_length_lineedit(self, new_scale_length):
        self.lineEditScaleLength.value = new_scale_length
        self.plot_style.schedule_update()

    def update_overlay_color_toolbutton(self, new_color):
        self.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % new_color)
        self.plot_style.schedule_update()

    def update_show_mass_checkbox(self, new_value):
        self.checkBoxShowMass.setChecked(new_value)
        self.plot_style.schedule_update()

    def update_marker_symbol_combobox(self, new_marker_symbol):
        self.comboBoxMarker.setCurrentText(new_marker_symbol)
        self.plot_style.schedule_update()

    def update_marker_size_spinbox(self, new_marker_size):
        self.doubleSpinBoxMarkerSize.setValue(new_marker_size)
        self.plot_style.schedule_update()

    def update_marker_color_toolbutton(self, new_color):
        self.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % new_color)
        self.plot_style.schedule_update()

    def update_marker_alpha_slider(self, new_alpha):
        self.horizontalSliderMarkerAlpha.setValue(new_alpha)
        self.plot_style.schedule_update()

    def update_line_width_combobox(self, new_line_width):
        self.doubleSpinBoxLineWidth.setValue(new_line_width)
        self.plot_style.schedule_update()

    def update_line_multiplier_lineedit(self, new_multiplier):
        self.lineEditLengthMultiplier.value = new_multiplier
        self.plot_style.schedule_update()

    def update_line_color_toolbutton(self, new_color):
        self.toolButtonLineColor.setStyleSheet("background-color: %s;" % new_color)
        self.plot_style.schedule_update()

    def update_font_family_combobox(self, new_font_family):
        self.fontComboBox.setCurrentText(new_font_family)
        self.plot_style.schedule_update()

    def update_font_size_spinbox(self, new_font_size):
        self.doubleSpinBoxFontSize.setValue(new_font_size)
        self.plot_style.schedule_update()

    def update_cmap_combobox(self, new_colormap):
        self.comboBoxFieldColormap.setCurrentText(new_colormap)
        self.plot_style.schedule_update()

    def update_cbar_reverse_checkbox(self, new_value):
        self.checkBoxReverseColormap.setChecked(new_value)
        self.plot_style.schedule_update()

    def update_cbar_direction_combobox(self, new_cbar_direction):
        self.comboBoxCbarDirection.setCurrentText(new_cbar_direction)
        self.plot_style.schedule_update()

    def update_clim_lineedits(self, new_xlim):
        self.lineEditColorLB.value = new_xlim[0]
        self.lineEditColorUB.value = new_xlim[1]
        self.plot_style.schedule_update()

    def update_clabel_lineedit(self, new_label):
        self.lineEditCbarLabel.setText(new_label)
        self.plot_style.schedule_update()
        
    def update_cscale_combobox(self, new_scale):
        self.comboBoxColorScale.setCurrentText(new_scale)
        self.plot_style.schedule_update()

    def update_resolution_spinbox(self, new_resolution):
        self.spinBoxHeatmapResolution.setValue(new_resolution)

        if self.plot_style.plot_type == "heatmap":
            self.plot_style.schedule_update()

    def update_dx_lineedit(self,value):
        """Updates ``MainWindow.lineEditDX.value``
        Called as an update to ``app_data.d_x``.  Updates Dx and  Schedules a plot update.

        Parameters
        ----------
        value : str
            x dimension.
        """
        self.lineEditDX.value = value
        if self.toolBox.currentIndex() == self.left_tab['process']:
            self.plot_style.schedule_update()
            field = "X"
            if isinstance(self.plot_info, dict) \
                and 'field_type' in self.plot_info \
                and 'field' in self.plot_info:
                # update x axis limits in style_dict 
                self.plot_style.initialize_axis_values(self.plot_info['field_type'], self.plot_info['field'])
                # update limits in styling tabs
                self.plot_style.set_axis_widgets("x",field)

    def update_dy_lineedit(self,value):
        """Updates ``MainWindow.lineEditDY.value``
        Called as an update to ``app_data.d_y``.  Updates Dy and  Schedules a plot update.

        Parameters
        ----------
        value : str
            x dimension.
        """
        self.lineEditDY.value = value
        if self.toolBox.currentIndex() == self.left_tab['process']:
            self.plot_style.schedule_update()
            field = "Y"
            if isinstance(self.plot_info, dict) \
                and 'field_type' in self.plot_info \
                and 'field' in self.plot_info:
                # update x axis limits in style_dict 
                self.plot_style.initialize_axis_values(self.plot_info['field_type'], self.plot_info['field'])
                # update limits in styling tabs
                self.plot_style.set_axis_widgets("y",field)

    def update_nx_lineedit(self,value):
        """Updates ``MainWindow.lineEditResolutionNx.value``
        Called as an update to ``app_data.n_x``.  Updates Nx and  Schedules a plot update.

        Parameters
        ----------
        value : str
            x dimension.
        """
        self.lineEditResolutionNx.value = value
        if self.toolBox.currentIndex() == self.left_tab['process']:
            self.plot_style.schedule_update()

    def update_ny_lineedit(self,value):
        """Updates ``MainWindow.lineEditResolutionNx.value``
        Called as an update to ``app_data.N_y``.  Updates Nx and  Schedules a plot update.

        Parameters
        ----------
        value : str
            x dimension.
        """
        self.lineEditResolutionNy.value = value
        if self.toolBox.currentIndex() == self.left_tab['process']:
            self.plot_style.schedule_update()

    def update_data_min_quantile(self,value):
        """Updates ``MainWindow.lineEditLowerQuantile.value``
        Called as an update to ``DataHandling.lineEditLowerQuantile``. 

        Parameters
        ----------
        value : float
            lower quantile value.
        """
        self.lineEditLowerQuantile.value = value
        self.update_labels()
        if hasattr(self,"mask_dock"):
            self.mask_dock.filter_tab.update_filter_values()
        if self.toolBox.currentIndex() == self.left_tab['process']:
            self.plot_style.scheduler.schedule_update()


    def update_data_max_quantile(self,value):
        """Updates ``MainWindow.lineEditLowerQuantile.value``
        Called as an update to ``DataHandling.lineEditLowerQuantile``. 
        
        Parameters
        ----------
        value : float
            lower quantile value.
        """
        self.lineEditUpperQuantile.value = value
        self.update_labels()
        if hasattr(self,"mask_dock"):
            self.mask_dock.filter_tab.update_filter_values()
        if self.toolBox.currentIndex() == self.left_tab['process']:
            self.plot_style.scheduler.schedule_update()

    def update_data_min_diff_quantile(self,value):
        """Updates ``MainWindow.lineEditLowerQuantile.value``
        Called as an update to ``DataHandling.lineEditLowerQuantile``. 
        Parameters
        ----------
        value : float
            lower quantile value.
        """
        self.lineEditDifferenceLowerQuantile.value = value
        self.update_labels()
        if hasattr(self,"mask_dock"):
            self.mask_dock.filter_tab.update_filter_values()
        if self.toolBox.currentIndex() == self.left_tab['process']:
            self.plot_style.scheduler.schedule_update()

    def update_data_max_diff_quantile(self,value):
        """Updates ``MainWindow.lineEditLowerQuantile.value``
        Called as an update to ``DataHandling.lineEditLowerQuantile``. 
        
        Parameters
        ----------
        value : float
            lower quantile value.
        """
        self.lineEditDifferenceUpperQuantile.value = value
        self.update_labels()
        if hasattr(self,"mask_dock"):
            self.mask_dock.filter_tab.update_filter_values()
        if self.toolBox.currentIndex() == self.left_tab['process']:
            self.plot_style.scheduler.schedule_update()


    def update_auto_scale_value(self,value):
        """Updates ``MainWindow.lineEditLowerQuantile.value``
        Called as an update to ``DataHandling.lineEditLowerQuantile``. 
        
        Parameters
        ----------
        value : float
            lower quantile value.
        """
        self.toolButtonAutoScale.setChecked(value)
        if value:
            self.lineEditDifferenceLowerQuantile.setEnabled(True)
            self.lineEditDifferenceUpperQuantile.setEnabled(True)
        else:
            self.lineEditDifferenceLowerQuantile.setEnabled(False)
            self.lineEditDifferenceUpperQuantile.setEnabled(False)
        if hasattr(self,"mask_dock"):
            self.mask_dock.filter_tab.update_filter_values()
        if self.toolBox.currentIndex() == self.left_tab['process']:
            self.plot_style.scheduler.schedule_update()

    def update_apply_outlier_to_all(self,value):
        """Updates ``MainWindow.lineEditLowerQuantile.value``
        Called as an update to ``DataHandling.lineEditLowerQuantile``. 
        
        Parameters
        ----------
        value : float
            lower quantile value.
        """
        self.checkBoxApplyAll.setChecked(value)
        ratio = ('/' in self.app_data.plot_info['field'])
        if value and not ratio: 
            # clear existing plot info from tree to ensure saved plots using most recent data
            for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                self.plot_tree.clear_tree_data(tree)
        elif value and not ratio:
            # clear existing plot info from tree to ensure saved plots using most recent data
            for tree in [ 'Ratio', 'Ratio (normalized)']:
                self.plot_tree.clear_tree_data(tree) 
        

    def update_outlier_method(self,method):
        """Updates ``MainWindow.comboBoxOutlierMethod.currentText()``

        Called as an update to ``DataHandling.outlier_method``.  Resets data bound widgets visibility upon change.

        Parameters
        ----------
        method : str
             Method used to remove outliers.
        """
        if self.data[self.app_data.sample_id].outlier_method == method:
            return

        self.data[self.app_data.sample_id].outlier_method = method

        match method.lower():
            case 'none':
                self.lineEditLowerQuantile.setEnabled(False)
                self.lineEditUpperQuantile.setEnabled(False)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'quantile criteria':
                self.lineEditLowerQuantile.setEnabled(True)
                self.lineEditUpperQuantile.setEnabled(True)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'quantile and distance criteria':
                self.lineEditLowerQuantile.setEnabled(True)
                self.lineEditUpperQuantile.setEnabled(True)
                self.lineEditDifferenceLowerQuantile.setEnabled(True)
                self.lineEditDifferenceUpperQuantile.setEnabled(True)
            case 'chauvenet criterion':
                self.lineEditLowerQuantile.setEnabled(False)
                self.lineEditUpperQuantile.setEnabled(False)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'log(n>x) inflection':
                self.lineEditLowerQuantile.setEnabled(False)
                self.lineEditUpperQuantile.setEnabled(False)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)

    def update_negative_handling_method(self,method):
        """Auto-scales pixel values in map

        Executes when the value ``MainWindow.comboBoxNegativeMethod`` is changed.

        Changes how negative values are handled for each analyte, the following options are available:
            Ignore negative values, Minimum positive value, Gradual shift, Yeo-Johnson transformation

        Parameters
        ----------
        method : str
            Method for dealing with negatives
        """
        data = self.data[self.app_data.sample_id]

        if self.checkBoxApplyAll.isChecked():
            # Apply to all iolties
            analyte_list = data.processed_data.match_attribute('data_type', 'Analyte') + data.processed_data.match_attribute('data_type', 'Ratio')
            data.negative_method = method
            # clear existing plot info from tree to ensure saved plots using most recent data
            for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                self.plot_tree.clear_tree_data(tree)
            data.prep_data()
        else:
            data.negative_method = method
            data.prep_data(self.app_data.c_field)
        
        self.update_invalid_data_labels()
        if hasattr(self,"mask_dock"):
            self.mask_dock.filter_tab.update_filter_values()

        # trigger update to plot
        self.plot_style.schedule_update()

    def update_autoscale_checkbox(self, value):
        """Updates the ``MainWindow.checkBoxApplyAll`` which controls the data processing methods."""
        if value is None:
            self.checkBoxApplyAll.setChecked(True)
        else:
            self.checkBoxApplyAll.setChecked(False)

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
            self.comboBoxNDimRefMaterial.setCurrentIndex(ref_index)
            
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

    def update_invalid_data_labels(self):
        """Updates flags on statusbar indicating negative/zero and nan values within the processed_data_frame"""        

        data = self.data[self.app_data.sample_id].processed_data

        columns = data.match_attributes({'data_type': 'Analyte', 'use': True}) + data.match_attributes({'data_type': 'Ratio', 'use': True})
        negative_count = any(data[columns] <= 0)
        nan_count = any(np.isnan(data[columns]))
        
        self.labelInvalidValues.setText(f"Negative/zeros: {negative_count}, NaNs: {nan_count}")

    def update_field_combobox(self, parentBox, childBox):
        """Updates comboBoxes with fields for plots or analysis

        Updates lists of fields in comboBoxes that are used to generate plots or used for analysis.

        Parameters
        ----------
        parentBox : QComboBox, None
            ComboBox used to select field type

        childBox : QComboBox
            ComboBox with list of field values
        """

        if parentBox is None:
            fields = self.app_data.field_dict['Analyte']
        else:
            if parentBox.currentText() == 'None':
                childBox.clear()
                return
            field_type = parentBox.currentText()
            if 'normalized' in field_type:
                field_type = field_type.replace(' (normalized)','')
            fields = self.app_data.field_dict[field_type]

        childBox.clear()
        childBox.addItems(fields)

        # ----start debugging----
        # if parentBox is not None:
        #     print('update_field_combobox: '+parentBox.currentText())
        # else:
        #     print('update_field_combobox: None')
        # print(fields)
        # ----end debugging----



    # -------------------------------------
    # Update properties from UI widgets and
    # anything else the widget updates
    # -------------------------------------
    def update_dx(self):
        self.data[self.app_data.sample_id].update_resolution('x', self.lineEditDX.value)
        self.plot_style.schedule_update()

    def update_dy(self):
        self.data[self.app_data.sample_id].update_resolution('y', self.lineEditDY.value)
        self.plot_style.schedule_update()

    def reset_crop(self):
        self.data[self.app_data.sample_id].reset_crop
        self.plot_style.schedule_update()

    def update_swap_resolution(self):
        if not self.data or self.app_data.sample_id != '':
            return

        self.data[self.app_data.sample_id].swap_resolution 
        self.plot_style.schedule_update()

    def reset_pixel_resolution(self):
        self.data[self.app_data.sample_id].reset_resolution
        self.plot_style.schedule_update()


    def update_outlier_removal(self, method):
        """Removes outliers from one or all analytes.
        
        Parameters
        ----------
        method : str
            Method used to remove outliers."""        
        if self.logger_options['UI']:
            self.logger.print(f"update_outlier_removal: method={method}")

        data = self.data[self.app_data.sample_id]

        if data.outlier_method == method:
            return

        data.outlier_method = method

        match method.lower():
            case 'none':
                self.lineEditLowerQuantile.setEnabled(False)
                self.lineEditUpperQuantile.setEnabled(False)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'quantile criteria':
                self.lineEditLowerQuantile.setEnabled(True)
                self.lineEditUpperQuantile.setEnabled(True)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'quantile and distance criteria':
                self.lineEditLowerQuantile.setEnabled(True)
                self.lineEditUpperQuantile.setEnabled(True)
                self.lineEditDifferenceLowerQuantile.setEnabled(True)
                self.lineEditDifferenceUpperQuantile.setEnabled(True)
            case 'chauvenet criterion':
                self.lineEditLowerQuantile.setEnabled(False)
                self.lineEditUpperQuantile.setEnabled(False)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)
            case 'log(n>x) inflection':
                self.lineEditLowerQuantile.setEnabled(False)
                self.lineEditUpperQuantile.setEnabled(False)
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)

    def update_neg_handling(self, method):
        """Auto-scales pixel values in map

        Executes when the value ``MainWindow.comboBoxNegativeMethod`` is changed.

        Changes how negative values are handled for each analyte, the following options are available:
            Ignore negative values, Minimum positive value, Gradual shift, Yeo-Johnson transformation

        Parameters
        ----------
        method : str
            Method for dealing with negatives
        """
        if self.logger_options['UI']:
            self.logger.print(f"update_neg_handling: method={method}")

        data = self.data[self.app_data.sample_id]

        if self.checkBoxApplyAll.isChecked():
            # Apply to all iolties
            analyte_list = data.processed_data.match_attribute('data_type', 'Analyte') + data.processed_data.match_attribute('data_type', 'Ratio')
            data.negative_method = method
            # clear existing plot info from tree to ensure saved plots using most recent data
            for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                self.plot_tree.clear_tree_data(tree)
            data.prep_data()
        else:
            data.negative_method = method

            assert self.app_data.c_field == self.comboBoxFieldC.currentText(), f"AppData.c_field {self.app_data.c_field} and MainWindow.comboBoxFieldC.currentText() {self.comboBoxFieldC.currentText()} do not match"
            data.prep_data(self.app_data.c_field)
        
        self.update_invalid_data_labels()
        if hasattr(self,"mask_dock"):
            self.mask_dock.filter_tab.update_filter_values()

        # trigger update to plot
        self.plot_style.schedule_update()

    

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
            case 'cluster score map':
                axes = [3]
            case 'dimension score map':
                axes = [3]
            case 'dimension scatter', 'dimension heatmap':
                axes = [0,1]
            case 'cluster':
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

        Updates the current plot (as determined by ``MainWindow.comboBoxPlotType.currentText()`` and options in ``MainWindow.toolBox.selectedIndex()``.

        save : bool, optional
            save plot to plot selector, Defaults to False.
        """
        if self.logger_options['Plotting']:
            self.logger.print(f"update_SV")

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
                    canvas, self.plot_info =  plot_map_mpl(self, data, self.app_data, self.plot_style, field_type, field, add_histogram=False)
                    # show increated profiles if exists
                    if (hasattr(self, "profile_dock") and self.profile_dock.profile_toggle.isChecked()) and (self.app_data.sample_id in self.profile_dock.profiling.profiles):
                        self.profile_dock.profiling.clear_plot()
                        self.profile_dock.profiling.plot_existing_profile(self.plot)
                    elif (hasattr(self, "mask_dock") and self.mask_dock.polygon_tab.polygon_toggle.isChecked()) and (self.app_data.sample_id in self.mask_dock.polygon_tab.polygon_manager.polygons):  
                        self.mask_dock.polygon_tab.polygon_manager.clear_polygons()
                        self.mask_dock.polygon_tab.polygon_manager.plot_existing_polygon(canvas)

                    
                else:
                    if self.toolBox.currentIndex() == self.left_tab['process']:
                        canvas, self.plot_info = plot_map_mpl(self, data, self.app_data, self.plot_style, field_type, field, add_histogram=True)
                    else:
                        canvas, self.plot_info = plot_map_mpl(self, data, self.app_data, self.plot_style, field_type, field, add_histogram=False)
                self.mpl_canvas = canvas
                self.add_plotwidget_to_canvas(self.plot_info)
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


            case 'variance' | 'basis vectors' | 'dimension scatter' | 'dimension heatmap' | 'dimension score map':
                if self.app_data.update_pca_flag or not data.processed_data.match_attribute('data_type','pca score'):
                    self.dimensional_reduction.compute_dim_red(data, self.app_data)
                canvas, self.plot_info = plot_pca(self, data, self.app_data, self.plot_style)

            case 'cluster' | 'cluster score map':
                self.compute_clusters_update_groups()
                canvas, self.plot_info = plot_clusters(self, data, self.app_data, self.plot_style)

            case 'cluster performance':
                # compute performace as a function of number of clusters
                self.clustering.compute_clusters(data, self.app_data, max_clusters = self.app_data.max_clusters)
                canvas, self.plot_info = cluster_performance_plot(self, data, self.app_data, self.plot_style)

        # add canvas to layout
        if canvas:
            self.clear_layout(self.widgetSingleView.layout())
            self.widgetSingleView.layout().addWidget(canvas)

        # add plot info to info_dock
        if hasattr(self,"info_dock"):
            self.info_dock.plot_info_tab.update_plot_info_tab(self.plot_info)

    def add_plotwidget_to_canvas(self, plot_info, position=None):
        """Adds plot to selected view

        Parameters
        ----------
        plot_info : dict
            A dictionary with details about the plot
        current_plot_df : dict, optional
            Defaults to None
        """
        if self.logger_options['Plotting']:
            self.logger.print(f"add_plotwidget_to_canvas\n  plot_info={plot_info}\n  position={position}")

        sample_id = plot_info['sample_id']
        tree = plot_info['plot_type']
        # widget_dict = self.axis_widget_dict[tree][sample_id][plot_name]

        # if on QuickView canvas, then set to SingleView canvas
        if self.canvasWindow.currentIndex() == self.canvas_tab['qv']:
            self.canvasWindow.setCurrentIndex(self.canvas_tab['sv'])

        # add figure to SingleView canvas
        if self.canvasWindow.currentIndex() == self.canvas_tab['sv']:
            #print('add_plotwidget_to_canvas: SV')
            self.clear_layout(self.widgetSingleView.layout())
            self.sv_widget = plot_info['figure']
            
            
            plot_info['view'][0] = True
            
            self.SV_plot_name = f"{plot_info['sample_id']}:{plot_info['plot_type']}:{plot_info['plot_name']}"
            #self.labelPlotInfo.

            for index in range(self.comboBoxMVPlots.count()):
                if self.comboBoxMVPlots.itemText(index) == self.SV_plot_name:
                    #plot exists in MVself.pyqtgraph_widget
                    self.move_widget_between_layouts(self.widgetMultiView.layout(), self.widgetSingleView.layout(),widget)
                    self.duplicate_plot_info = plot_info
                    self.hide()
                    self.show()
                    return
            
            if self.duplicate_plot_info: #if duplicate exisits and new plot has been plotted on SV
                #return duplicate back to MV
                row, col = self.duplicate_plot_info['position']
                #print(f'd{row,col}')
                dup_widget =self.duplicate_plot_info['figure']
                self.widgetMultiView.layout().addWidget( dup_widget, row, col )
                dup_widget.show()
                self.duplicate_plot_info = None #reset to avoid plotting previous duplicates
            else:
                #update toolbar and SV canvas
                self.update_canvas(self.sv_widget)
            self.sv_widget.show()

            if (self.plot_style.plot_type == 'field map') and (self.toolBox.currentIndex() == self.left_tab['sample']):
                current_map_df = self.data[self.app_data.sample_id].get_map_data(plot_info['plot_name'], plot_info['field_type'], norm=self.plot_style.cscale)
                plot_small_histogram(self, self.data[self.app_data.sample_id], self.app_data, self.plot_style, current_map_df)
        # add figure to MultiView canvas
        elif self.canvasWindow.currentIndex() == self.canvas_tab['mv']:
            #print('add_plotwidget_to_canvas: MV')
            name = f"{plot_info['sample_id']}:{plot_info['plot_type']}:{plot_info['plot_name']}"
            layout = self.widgetMultiView.layout()

            list = self.comboBoxMVPlots.allItems()
            
            # if list:
            #     for i, item in enumerate(list):
            #         mv_plot_data = self.comboBoxMVPlots.itemData(i)
            #         if mv_plot_data[2] == tree and mv_plot_data[3] == sample_id and mv_plot_data[4] == plot_name:
            #             self.statusBar().showMessage('Plot already displayed on canvas.')
            #             return
            plot_exists = False # to check if plot is already in comboBoxMVPlots
            for index in range(self.comboBoxMVPlots.count()):
                if self.comboBoxMVPlots.itemText(index) == name:
                    plot_exists = True
                
            if plot_exists and name != self.SV_plot_name:
                #plot exists in MV and is doesnt exist in SV
                self.statusBar().showMessage('Plot already displayed on canvas.')
                return
            
            # if position is given, use it
            if position:
                row = position[0]
                col = position[1]
                
                # remove widget that is currently in this place
                widget = layout.itemAtPosition(row,col)
                if widget is not None and name != self.SV_plot_name:
                    # layout.removeWidget(widget)
                    # widget.setParent(None)
                    widget.hide()

            # if no position, find first empty space
            else:
                keepgoing = True
                for row in range(self.spinBoxMaxRows.value()):
                    for col in range(self.spinBoxMaxCols.value()):
                        if layout.itemAtPosition(row,col):
                            #print(f'row: {row}   col : {col}')
                            continue
                        else:
                            keepgoing = False
                            break

                    if not keepgoing:
                        #print(f'row: {row}   col : {col}')
                        break

            # check if canvas is full
            if row == self.spinBoxMaxRows.value()-1 and col == self.spinBoxMaxCols.value()-1 and layout.itemAtPosition(row,col):
                QMessageBox.warning(self, "Add plot to canvas warning", "Canvas is full, to add more plots, increase row or column max.")
                return

            
            widget = plot_info['figure']
            plot_info['view'][1] = True
            plot_info['position'] = [row,col]
            
            
            if name == self.SV_plot_name and plot_exists: #if plot already exists in MV and SV
                self.move_widget_between_layouts(self.widgetSingleView.layout(),self.widgetMultiView.layout(),widget, row,col)
                self.duplicate_plot_info = plot_info
            elif name == self.SV_plot_name and not plot_exists: #if plot doesnt exist in MV but exists in SV
                # save plot info to replot when tab changes to single view and add plot to comboBox
                self.duplicate_plot_info = plot_info
                data = [row, col, tree, sample_id, name]
                self.move_widget_between_layouts(self.widgetSingleView.layout(),self.widgetMultiView.layout(),widget, row,col)
                self.comboBoxMVPlots.addItem(name, userData=data)
            else: #new plot which doesnt exist in single view
                # add figure to canvas
                layout.addWidget(widget,row,col)    
                
                data = [row, col, tree, sample_id, name]
                self.comboBoxMVPlots.addItem(name, userData=data)

        # self.hide()
        # self.show()

        # put plot_info back into table
        #print(plot_info)
        self.plot_tree.add_tree_item(plot_info)

    def compute_clusters_update_groups(self):
        """
        Computes clusters and updates cluster groups.

        This method:
        1. Checks if clustering needs to be updated based on the application data flags.
        2. Invokes the clustering computation if necessary.
        3. Applies updated cluster colors and refreshes the cluster tab in the Mask Dock.
        """
        data = self.data[self.app_data.sample_id]
        method = self.app_data.cluster_method
        if self.app_data.update_cluster_flag or \
                data.processed_data[method].empty or \
                (method not in list(data.processed_data.columns)):
            # compute clusters
            self.statusbar.showMessage('Computing clusters')
            self.clustering.compute_clusters(data, self.app_data, max_clusters = None)
            # update cluster colors
            self.app_data.cluster_group_changed(data, self.plot_style)
            # enable cluster tab actions and update group table
            if hasattr(self, 'mask_dock'):
                self.mask_dock.cluster_tab.toggle_cluster_actions()
                self.mask_dock.cluster_tab.update_table_widget()

            self.statusbar.showMessage('Clustering successful')

    # -------------------------------------
    # Dialogs and Windows
    # -------------------------------------
    def open_workflow(self):
        """Opens Workflow dock.

        Opens Workflow dock, creates on first instance.  The Workflow is used to design processing algorithms that
        can batch process samples, or simply record the process of analyzing a sample.
        """
        if self.logger_options['UI']:
            self.logger.print(f"open_workflow")

        if not hasattr(self, 'workflow'):
            self.workflow = Workflow(self)

            if not (self.workflow in self.help_mapping.keys()):
                self.help_mapping[self.workflow] = 'workflow'

        self.workflow.show()


        #self.workflow.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

    def open_mask_dock(self, tab_name=None):
        """Opens Mask Dock

        Opens Mask Dock, creates on first instance.  The Mask Dock includes tabs for filtering, creating and masking
        with polygons and masking by clusters.

        Parameters
        ----------
        tab_name : str (optional)
            Will open the dock to the requested tab, options include 'filter', 'polygon' and cluster', by default None
        """
        if self.logger_options['UI']:
            self.logger.print(f"open_mask_dock: tab_name={tab_name}")

        if not hasattr(self, 'mask_dock'):
            self.mask_dock = MaskDock(self, debug=self.logger_options['Masking'])

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

            if not (self.mask_dock in self.help_mapping.keys()):
                self.help_mapping[self.mask_dock] = 'filtering'

            self.mask_dock.filter_tab.callback_lineEditFMin()
            self.mask_dock.filter_tab.callback_lineEditFMax()

        self.mask_dock.show()

        if tab_name is not None:
            self.mask_dock.tabWidgetMask.setCurrentIndex(self.mask_tab[tab_name])


    def open_profile(self):
        """Opens Profile dock

        Opens Profile dock, creates on first instance.  The profile dock is used to create and display
        2-D profiles across maps.

        :see also:
            Profile
        """
        if not hasattr(self, 'profile'):
            self.profile_dock = ProfileDock(self, debug=self.logger_options['Profile'])

            if not (self.profile_dock in self.help_mapping.keys()):
                self.help_mapping[self.profile_dock] = 'profiles'

        self.profile_dock.show()


    def open_notes(self):
        """Opens Notes Dock

        Opens Notes Dock, creates on first instance.  The notes can be used to record important information about
        the data, its processing and display the results.  The notes may be useful for developing data reports/appendicies
        associated with publications.

        :see also:
            NoteTaking
        """            
        if not hasattr(self, 'notes'):
            if hasattr(self,'selected_directory') and self.app_data.sample_id != '':
                notes_file = os.path.join(self.app_data.selected_directory,f"{self.app_data.sample_id}.rst")
            else:
                notes_file = None

            self.notes = Notes(self, notes_file)

            if not (self.notes in self.help_mapping.keys()):
                self.help_mapping[self.notes] = 'notes'

        self.notes.show()
        #self.notes.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)


    def open_calculator(self):
        """Opens Calculator dock

        Opens Calculator dock, creates on first instance.  The Calculator is used to compute custom fields.
        """            
        if self.logger_options['UI']:
            self.logger.print(f"open_calculator")

        if not hasattr(self, 'calculator'):
            calc_file = os.path.join(BASEDIR,f'resources/app_data/calculator.txt')
            self.calculator = CalculatorDock(self, filename=calc_file, debug=self.logger_options['Calculator'])

            if not (self.calculator in self.help_mapping.keys()):
                self.help_mapping[self.calculator] = 'calculator'

        self.calculator.show()
        #self.calculator.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

    def open_info_dock(self):
        """Opens Info Dock.
        
        Opens Info Dock, creates on first instance.  The Info Dock can be used to interrogate the data and its
        metadata as well as plot related properties.
        """
        if self.logger_options['UI']:
            self.logger.print(f"open_info_dock")
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
        
        else:
            self.info_dock.show()

            self.help_mapping[self.info_dock] = 'info_tool'

    def open_logger(self):
        """Opens Logger Dock

        Opens Logger Dock, creates on first instance.  The Logger Dock prints information that can be used to recreate
        changes to data and functions that are called.
        """            
        if not hasattr(self, 'logger_dock'):
            logfile = os.path.join(BASEDIR,f'resources/log/lame.log')
            self.logger_dock = LoggerDock(logfile, self)
            for key in self.logger_options.keys():
                self.logger_options[key] = True
        else:
            self.logger_dock.show()

        self.help_mapping[self.logger_dock] = 'logger'

        #self.logger.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

    def open_browser(self, action=None):
        """Opens Browser dock with documentation

        Opens Browser dock, creates on first instance.
        """
        if self.logger_options['UI']:
            self.logger.print(f"open_browser")
        if not hasattr(self, 'browser'):
            self.browser = Browser(self, self.help_mapping, BASEDIR, debug=self.logger_options['Browser'])
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

        Opens a dialog to select analytes for analysis either graphically or in a table.  Selection updates the list of analytes, and ratios in plot selector and comboBoxes.
        
        .. seealso::
            :ref:`AnalyteSelectionWindow` for the dialog
        """
        if self.app_data.sample_id == '':
            return

        self.analyte_dialog = AnalyteDialog(self, debug=self.logger_options['Analyte selector'])
        self.analyte_dialog.show()

        result = self.analyte_dialog.exec()  # Store the result here
        if result == QDialog.DialogCode.Accepted:
            self.update_analyte_ratio_selection(analyte_dict= self.analyte_dialog.norm_dict)   
            self.workflow.refresh_analyte_saved_lists_dropdown() #refresh saved analyte dropdown in blockly 
        if result == QDialog.DialogCode.Rejected:
            pass


    def open_select_custom_field_dialog(self):
        """Opens Select Analyte dialog

        Opens a dialog to select analytes for analysis either graphically or in a table.  Selection updates the list of analytes, and ratios in plot selector and comboBoxes.
        
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

        """Clears a widget that contains plots

        Parameters
        ----------
        layout : QLayout
            A layout associated with a ``canvasWindow`` tab.
        """
        #remove current plot
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item is not None:
                widget = item.widget()   # Get the widget from the item
                if widget is not None:
                    widget.hide()
                    # layout.removeWidget(widget)  # Remove the widget from the layout
                    # widget.setParent(None)      # Set the widget's parent to None

        if self.canvasWindow.currentIndex() == self.canvas_tab['mv']:
            list = self.comboBoxMVPlots.allItems()
            if not list:
                return

            for i, _ in enumerate(list):
                # get data from comboBoxMVPlots
                data = self.comboBoxMVPlots.itemData(i, role=Qt.ItemDataRole.UserRole)

                # get plot_info from tree location and
                # reset view to False and position to none
                plot_info = self.retrieve_plotinfo_from_tree(tree=data[2], branch=data[3], leaf=data[4])
                #print(plot_info)
                plot_info['view'][1] = False
                plot_info['position'] = None
            
            # clear hover information for lasermaps
            self.multi_view_index = []
            self.multiview_info_label = {}

            # clear plot list in comboBox
            self.comboBoxMVPlots.clear()


    # -------------------------------------
    # Central canvas widget functions
    # -------------------------------------
    def clear_layout(self, layout):
        """Clears a widget that contains plots

        Parameters
        ----------
        layout : QLayout
            A layout associated with a ``canvasWindow`` tab.
        """
        #remove current plot
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item is not None:
                widget = item.widget()   # Get the widget from the item
                if widget is not None:
                    widget.hide()
                    # layout.removeWidget(widget)  # Remove the widget from the layout
                    # widget.setParent(None)      # Set the widget's parent to None

        if self.canvasWindow.currentIndex() == self.canvas_tab['mv']:
            list = self.comboBoxMVPlots.allItems()
            if not list:
                return

            for i, _ in enumerate(list):
                # get data from comboBoxMVPlots
                data = self.comboBoxMVPlots.itemData(i, role=Qt.ItemDataRole.UserRole)

                # get plot_info from tree location and
                # reset view to False and position to none
                plot_info = self.retrieve_plotinfo_from_tree(tree=data[2], branch=data[3], leaf=data[4])
                #print(plot_info)
                plot_info['view'][1] = False
                plot_info['position'] = None
            
            # clear hover information for lasermaps
            self.multi_view_index = []
            self.multiview_info_label = {}

            # clear plot list in comboBox
            self.comboBoxMVPlots.clear()        

    def remove_multi_plot(self, selected_plot_name):
        """Removes selected plot from MulitView

        Parameters
        ----------
        selected_plot_name : str
            Plot selected in ``MainWindow.treeWidget``
        """
        widget_index = self.multi_view_index.index(selected_plot_name)
        layout = self.widgetMultiView.layout()
        item = layout.itemAt(widget_index)  # Get the item at the specified index
        if item is not None:
            widget = item.widget()   # Get the widget from the item
            if widget is not None:
                layout.removeWidget(widget)  # Remove the widget from the layout
                widget.setParent(None)      # Set the widget's parent to None
        # if widget is not None:
        #     index = self.canvasWindow.addTab( widget, selected_plot_name)
        self.multi_view_index.pop(widget_index)
        for widget in self.multiview_info_label[selected_plot_name+'1']:
            widget.setParent(None)
            widget.deleteLater()
        del self.multiview_info_label[selected_plot_name+'1']
        del self.lasermaps[selected_plot_name+'1']
        #self.axis_widget_dict[selected_plot_name] = widget
        #self.add_remove(selected_plot_name)
        self.comboBoxMVPlots.clear()
        self.comboBoxMVPlots.addItems(self.multi_view_index)

    def update_canvas(self, new_canvas):
        # Clear the existing layout
        self.clear_layout(self.widgetSingleView.layout())
        
        
        # Add the new canvas to the layout
        self.widgetSingleView.layout().addWidget(new_canvas)
        
        try:
            # Recreate the NavigationToolbar with the new canvas
            self.mpl_toolbar = NavigationToolbar(new_canvas, self.widgetSingleView)
            #hide the toolbar
            self.mpl_toolbar.hide()
            self.widgetSingleView.layout().addWidget(self.mpl_toolbar)
        except:
            # canvas is not a mplc.MplCanvas  
            pass

    def display_QV(self):
        """Plots selected maps to the Quick View tab

        Adds plots of predefined analytes to the Quick View tab in a grid layout."""
        self.canvasWindow.setCurrentIndex(self.canvas_tab['qv'])
        if self.app_data.sample_id == '':
            return

        key = self.comboBoxQVList.currentText()

        # establish number of rows and columns
        ratio = 1.8 # aspect ratio of gridlayout
        # ratio = ncol / nrow, nplots = ncol * nrow
        ncol = int(np.sqrt(len(self.QV_analyte_list[key])*ratio))

        # fields in current sample
        fields = self.app_data.field_dict['Analyte']

        # clear the quickView layout
        self.clear_layout(self.widgetQuickView.layout())
        for i, analyte in enumerate(self.QV_analyte_list[key]):
            # if analyte is in list of measured fields
            if analyte not in fields:
                continue

            # create plot canvas
            canvas = mplc.MplCanvas()

            # determine location of plot
            col = i % ncol
            row = i // ncol

            # get data for current analyte
            current_plot_df = self.data[self.app_data.sample_id].get_map_data(analyte, 'Analyte')
            reshaped_array = np.reshape(current_plot_df['array'].values, self.data[self.app_data.sample_id].array_size, order=self.data[self.app_data.sample_id].order)

            # add image to canvas
            cmap = self.plot_style.get_colormap()
            cax = canvas.axes.imshow(reshaped_array, cmap=cmap,  aspect=self.data[self.app_data.sample_id].aspect_ratio, interpolation='none')
            font = {'family': 'sans-serif', 'stretch': 'condensed', 'size': 8, 'weight': 'semibold'}
            canvas.axes.text( 0.025*self.data[self.app_data.sample_id].array_size[0],
                    0.1*self.data[self.app_data.sample_id].array_size[1],
                    analyte,
                    fontdict=font,
                    color=self.plot_style.overlay_color,
                    ha='left', va='top' )
            canvas.axes.set_axis_off()
            canvas.fig.tight_layout()

            # add canvas to quickView grid layout
            self.widgetQuickView.layout().addWidget(canvas,row,col)

# -------------------------------
# MAIN FUNCTION!!!
# Sure doesn't look like much
# -------------------------------
app = None
def create_app():
    """_summary_

    _extended_summary_

    Returns
    -------
    _type_
        _description_
    """    
    global app
    app = QApplication(sys.argv)

    # Enable high-DPI scaling (enabled by default in PyQt6)

    if darkdetect.isDark():
        ss = load_stylesheet('dark.qss')
        app.setStyleSheet(ss)
    else:
        ss = load_stylesheet('light.qss')
        app.setStyleSheet(ss)

    return app

def show_splash():
    """Creates splash screen while LaME loads"""    
    pixmap = QPixmap("lame_splash.png")
    splash = QSplashScreen(pixmap)
    splash.setMask(pixmap.mask())
    splash.show()
    QTimer.singleShot(3000, splash.close)

def main():
    """Main function for LaME"""    
    app = create_app()
    show_splash()

    # Uncomment this line to set icon to App
    app.setWindowIcon(QIcon(os.path.join(BASEDIR, os.path.join(ICONPATH,'LaME-64.svg'))))

    # create application data properties with notifiable observers that can be used to
    # update widgets in the UI
    main = MainWindow()

    # Set the main window to fullscreen
    #main.showFullScreen()
    main.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()