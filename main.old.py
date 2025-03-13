import sys, os, re, copy, random, darkdetect
from PyQt6.QtCore import ( Qt, QTimer, QUrl, QSize, QRectF )
from PyQt6.QtWidgets import (
    QCheckBox, QTableWidgetItem, QVBoxLayout, QGridLayout,
    QMessageBox, QHeaderView, QMenu, QFileDialog, QWidget, QToolButton,
    QDialog, QLabel, QTableWidget, QInputDialog, QAbstractItemView,
    QSplashScreen, QApplication, QMainWindow, QSizePolicy
)
from PyQt6.QtGui import ( QIntValidator, QDoubleValidator, QPixmap, QFont, QIcon )
from src.app.UITheme import UIThemes

#from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
import pyqtgraph as pg
from pyqtgraph.GraphicsScene import exportDialog
from pyqtgraph import (
    setConfigOption, colormap, ColorBarItem,ViewBox, TargetItem, ImageItem,
    GraphicsLayoutWidget, ScatterPlotItem, AxisItem, PlotDataItem
)
#from datetime import datetimec
import numpy as np
import pandas as pd
pd.options.mode.copy_on_write = True
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
#from matplotlib.figure import Figure
#from matplotlib.projections.polar import PolarAxes
#from matplotlib.collections import PathCollection
import matplotlib.gridspec as gs
#import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import Patch
import matplotlib.colors as colors
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
import cmcrameri as cmc
from scipy.stats import yeojohnson, percentileofscore
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
#from sklearn_extra.cluster import KMedoids
import skfuzzy as fuzz
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from src.common.ChemPlot import plot_map_mpl, plot_small_histogram, plot_histogram, plot_correlation, get_scatter_data, plot_scatter, plot_ternary_map
from src.common.plot_spider import plot_spider_norm
from src.common.scalebar import scalebar
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
from src.app.Actions import Actions
from src.common.DataHandling import SampleObj
from src.app.PlotTree import PlotTree
from src.common.Masking import MaskDock
from src.app.CropImage import CropTool
from src.app.ImageProcessing import ImageProcessing as ip
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
from src.common.Logger import LoggerDock
from src.common.Calculator import CalculatorDock
from src.common.varfunc import ObservableDict
from src.app.AppData import AppData

# to prevent segmentation error at startup
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
setConfigOption('imageAxisOrder', 'row-major') # best performance
## Run both (from docs/) to compile docstrings into sphinx, the second only when docstrings have not changed
## sphinx-apidoc -o source ../src
## sphinx-build -b html source/ build/html

## !pyrcc5 resources.qrc -o src/ui/resources_rc.py
## !pyuic5 designer/mainwindow.ui -o src/ui/MainWindow.py
## !pyuic5 designer/QuickViewDialog.ui -o src/ui/QuickViewDialog.py
## !pyuic5 -x designer/AnalyteSelectionDialog.ui -o src/ui/AnalyteSelectionDialog.py
## !pyuic5 -x designer/FieldSelectionDialog.ui -o src/ui/FieldSelectionDialog.py
## !pyuic5 -x designer/FileSelectorDialog.ui -o src/ui/FileSelectorDialog.py
## !pyuic5 -x designer/PreferencesWindow.ui -o src/ui/PreferencesWindow.py
## !pyuic5 -x designer/MapImportDialog.ui -o src/ui/MapImportDialog.py
## !pyuic5 -x designer/SpotImportDialog.ui -o src/ui/SpotImportDialog.py
# pylint: disable=fixme, line-too-long, no-name-in-module, trailing-whitespace

# Define the stylesheet
# light_stylesheet = """
#     QToolButton {
#         color: #000000;
#         border: none;
#         border-radius: 6px;
#     }
#     QToolButton::menu-indicator {
#         image: none;
#     }
#     QToolButton:hover {
#         background-color: #c8c8c8; /* Change background color on hover */
#     }
#     QToolButton:checked {
#         background-color: #c8c8c8; /* Change background color on hover */
#     }
class MainWindow(QMainWindow, Ui_MainWindow):
    """MainWindow

    _extended_summary_

    Parameters
    ----------
    QtWidgets : Main window widgets
        _description_
    Ui_MainWindow : Qt.MainWindow
        Main window  UI.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes the GUI and sets up connections from widgets to functions
        
        Attributes
        ----------
        aspect_ratio : float
            The aspect ratio for the current sample.
        axis_dict : dict of dict
            Dictionary containing axes for individual plot fields.  Setting these properties will set them for
            all plots which use the same field, though it does not update them on previous plots.

            Keywords for the first level are given by the field names used for plotting associated with entries
            into the field-related QComboBoxes.  Associated with each field are the axes properties.
        
            [*field*] : (dict) -- field as (*str*)
                | 'label' : (str) -- axis label, may include units or custom names
                | 'status' : (str) -- *auto* or *custom* indicates the use of default bounds or user defined axes limits
                | 'min' : (float) -- minimum axis value
                | 'max' : (float) -- maximum axis value
                | 'scale' : (str) -- normalization for analyte, options include ``linear`` or ``log``, though this is not included for all field types
                | 'pstatus' : (str) -- *auto* or *custom* limits for probability axis on histograms when displayed as a PDF type
                | 'pmin' : (float) -- minimum probability value
                | 'pmax' : (float) -- maximum probability value
        mask_tab : dict
            Holds the indices for tabs in ``tabWidgetMask``
        calc_dict : dict
            Holds the custom field names and formulas set by the user in the calculator
        canvas_tab : dict
            Holds the indices for tabs in ``canvasWindow``
        cluster_dict : dict of dict
            A dictionary that holds settings and cluster metadata used for plotting.  Each cluster method has its own key and associated dictionary.
            cluster_dict[*method*], where *method* is ``k-means`` or ``fuzzy c-means``

            **'active method' : (str)** -- current selected method for plotting, masking, etc.

            [*method*] : (dict) -- clustering method as (*str*)
                | 'n_clusters' : (int) -- number of clusters, set in ``spinBoxNClusters``
                | 'seed' : (int) -- seed for clustering, which can be user input (``lineEditSeed``) or randomly generated (``toolButtonRandomSeed``), default is 23
                | 'exponent' : (float) -- exponent for fuzzy c-means, dictates the amount of overlap possible between the different clusters, set by ``horizontalSliderClusterExponent``, default is 2.1
                | 'distance' : (str) -- distance metric for fuzzy c-means, *haven't gotten this to work yet, check scikit-learn package*
                | 'selected_clusters' : (list) -- clusters selected in ``tableWidgetViewGroups`` for plotting
                | *cluster_id* : (dict) -- the key is an integer, with metadata associated with each cluster_id
                | 'norm' : (matplotlib.colors.Norm) -- norm for plotting colormap

            [*cluster_id*] : (dict) -- cluster index as (*int*), this data is displayed for the user in ``tableWidgetViewGroups``
                | 'name' : (str) -- user-defined name for cluster, defaults to ``f"Cluster {cluster_id}"``
                | 'link' : (list) -- list of clusters id's linked to current cluster
                | 'color' : (str) -- hex color string
        left_tab : dict
            Holds the indices for pages in ``toolBox``

        ndim_list: (list)
            Fields used to for ``TEC`` and ``radar`` style plots.
        plot_info : dict
            Dictionary that holds information about plots.  These dictionaries are often saved to the tree when the user clicks
            the ``actionSaveToTree`` toolbar button.  

            | 'tree' : (str) -- tree name, ``Analyte``, ``Analyte (normalized)``
            | 'sample_id' : (str) -- sample id, which doubles as ``treeView`` branch
            | 'plot_name' : (str) -- plot name, which doubles as ``treeView`` leaf
            | 'plot_type' : (str) -- type of plot (e.g., ``field map``, ``scatter``, ``Cluster Score``)
            | 'field_type' : (list of str) -- type of field(s) used to create plot
            | 'field' : (list of str) -- analyte or other field(s) used to create plot
            | 'figure' : (pgGraphicsWidget or mplc.MplCanvas) -- object holding figure for display
            | 'style' : (dict) -- dictionary associated with ``styles[*plot_type*]``
            | 'cluster_groups' : (list) -- cluster groups used to generate plot
            | 'view' : (bool,bool) -- indicates whether ``plot_info['figure']`` is displayed in SingleView and/or MultiView
            | 'position' : (list) -- location *(row,col)* in ``layoutMultiView`` a value of None indicates not displayed in MultiView

            Plot specific keys include:
            | 'bin_width' : (float) -- histogram bin width
            | 'type' : (str) -- ``PDF`` (probablity density function) or ``CDF`` (cumulative density function)
            | 'method' : (str) -- correlation method, ``Pearson``, ``Spearman``, or ``Kendall``
            | 'squared_flag' : (bool) -- squared correlation if ``True``

            .. seealso::
                :ref:`add_plotwidget_to_tree` for details about saving *plot_info* to the tree (Plot Selector)
        QVAnalyteList : list of str
            ordered set of analytes to display in on the Quick View tab
        sample_id : str
            The name of the current sample, chosen by the user with ``comboBoxSampleID``.  *sample_id* is used as the key into several dictionaries.
        sort_method : str
            Method used to sort the analytes.  This is changed by choosing a different sorting method for the analytes by pushing the ``toolButtonSortAnalyte``.
            However, only the analytes for the current sample with be sorted.  Other samples will be sorted when when they are reselected.  To ensure that all samples
            use the same sorting algorithm, change the default preferences using the PreferencesDialog.  Sort methods include
            - alphabetical
            - atomic number
            - mass
            - radius
            - compatibility

        view_mode : int
            Keeps track of viewing mode.  ``0`` for auto, ``1`` for dark and ``2`` for ``light``

        widgetSingleView : QVBoxLayout
            Widget holding layout for Single View tab of ``canvasWindow``
        widgetMultiView : QGridLayout
            Widget holding layout for Multi View tab of ``canvasWindow``
        widgetQuickView : QGridLayout
            Widget holding layout for Quick View tab of ``canvasWindow``
        """
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setupUi(self)

        # Add this line to set the size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # this flag sets whether the plot can be updated.  Mostly off during change_sample
        self.plot_flag = False
        self.logger_options = {
                'IO': False,
                'Data': False,
                'Analyte selector': False,
                'Plot selector': False,
                'Plotting': True,
                'Polygon': False,
                'Profile': False,
                'Masking': True,
                'Styles': True,
                'Calculator': True,
                'Browser': False
            }
        self.help_mapping = create_help_mapping(self)

        # The data dictionary will hold the data with a key for each sample
        self.data = {}

        # until there is actually some data to store, disable certain widgets
        self.toggle_data_widgets()

        # initialize the application data
        #   contains:
        #       critical UI properties
        #       notifiers when properties change
        #       data structure and properties (DataHandling), data
        self.app_data = AppData(self.data)
        self.connect_app_data_observers(self.app_data)

        # initialize the styling data and dock
        self.plot_style = StylingDock(self, debug=self.logger_options['Styles'])
        self.plot_style.load_theme_names()
        self.connect_plot_style_observers(self.plot_style)

        # [convention] maps notifier properties with their associated UI update functions
        #   format of the UI update functions should be self.update_[property_name]_[widget_type]
        #   there should be an associated update function for the widgets to update properties
        #   with a similar format for the function name without _[widget_type]

        #Initialize nested data which will hold the main sets of data for analysis
        self.BASEDIR = BASEDIR

        self.lasermaps = {}
        self.prev_plot = ''
        self.pyqtgraph_widget = None
        self.isUpdatingTable = False
        self.default_cursor = False
        self.duplicate_plot_info = None
        self.update_ui = True
        self.profile_state = False
        self.polygon_state = False
        
        self.calc_dict = {}

        self.laser_map_dict = {}
        self.persistent_filters = pd.DataFrame()
        self.persistent_filters = pd.DataFrame(columns=['use', 'field_type', 'field', 'norm', 'min', 'max', 'operator', 'persistent'])
        

        #initialise status bar
        #self.statusBar = self.statusBar()

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

        # multi-view
        self.multi_view_index = []
        self.multiview_info_label = {}
        layout_multi_view = QGridLayout()
        layout_multi_view.setSpacing(0) # Set margins to 0 if you want to remove margins as well
        layout_multi_view.setContentsMargins(0, 0, 0, 0)
        self.widgetMultiView.setLayout(layout_multi_view)
        self.widgetMultiView.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.toolButtonRemoveMVPlot.clicked.connect(lambda: self.remove_multi_plot(self.comboBoxPlots.currentText()))
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
        # right toolbar plot layout
        # histogram view
        layout_histogram_view = QVBoxLayout()
        layout_histogram_view.setSpacing(0)
        layout_histogram_view.setContentsMargins(0, 0, 0, 0)
        self.widgetHistView.setLayout(layout_histogram_view)

        # bottom tab plot layout
        # profile view
        # layout_profile_view = QVBoxLayout()
        # layout_profile_view.setSpacing(0)
        # layout_profile_view.setContentsMargins(0, 0, 0, 0)
        # self.widgetProfilePlot.setLayout(layout_profile_view)
        # self.widgetProfilePlot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        #Flags to prevent plotting when widgets change
        self.point_selected = False
        self.check_analysis = True
        self.update_bins = True
        self.update_cluster_flag = True
        self.update_pca_flag = True
        self.plot_flag = True

        self.plot_info = ObservableDict()

        # set locations of dock widgets
        #self.setCorner(0x00002,0x1) # sets left toolbox to bottom left corner
        #self.setCorner(0x00003,0x2) # sets right toolbox to bottom right corner
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)

        # preferences
        self.default_preferences = {'Units':{'Concentration': 'ppm', 'Distance': 'µm', 'Temperature':'°C', 'Pressure':'MPa', 'Date':'Ma', 'FontSize':11, 'TickDir':'out'}}
        # in future will be set from preference ui
        self.preferences = copy.deepcopy(self.default_preferences)

        # code is more resilient if toolbox indices for each page is not hard coded
        # will need to change case text if the page text is changed
        # left toolbox
        self.reindex_left_tab()
        self.actionSpotTools.setChecked(False)
        self.actionSpotTools.triggered.connect(self.toggle_spot_tab)
        self.actionImportSpots.setVisible(False)

        self.actionSpecialTools.setChecked(False)
        self.actionSpecialTools.triggered.connect(self.toggle_special_tab)

        # right toolbox
        self.style_tab = {}
        for tid in range(self.toolBoxStyle.count()):
            match self.toolBoxStyle.itemText(tid).lower():
                case 'axes and labels':
                    self.style_tab.update({'axes': tid})
                case 'annotations and scale':
                    self.style_tab.update({'annotations': tid})
                case 'markers and lines':
                    self.style_tab.update({'markers': tid})
                case 'coloring':
                    self.style_tab.update({'colors': tid})
                case 'regression':
                    self.style_tab.update({'regression': tid})

        self.canvas_tab = {}
        for tid in range(self.canvasWindow.count()):
            match self.canvasWindow.tabText(tid).lower():
                case 'single view':
                    self.canvas_tab.update({'sv': tid})
                case 'multi view':
                    self.canvas_tab.update({'mv': tid})
                case 'quick view':
                    self.canvas_tab.update({'qv': tid})
        
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

        self.toolBar.insertWidget(self.actionSelectAnalytes,self.widgetSampleSelect)
        self.toolBar.insertWidget(self.actionUpdatePlot,self.widgetPlotTypeSelect)

        self.toolbar_actio = Actions(self)

        # Set initial view
        self.toolBox.setCurrentIndex(self.left_tab['sample'])
        if hasattr(self, "mask_dock"):
            self.mask_dock.tabWidgetMask.setCurrentIndex(self.mask_tab['filter'])
        self.toolBoxStyle.setCurrentIndex(0)
        self.canvasWindow.setCurrentIndex(self.canvas_tab['sv'])

        # create dictionaries for default plot styles
        #-------------------------
        self.plot_types = {self.left_tab['sample']: [0, 'field map', 'histogram', 'correlation'],
            self.left_tab['process']: [0, 'field map', 'gradient map'],
            self.left_tab['spot']: [0, 'field map', 'gradient map'],
            # self.mask_tab['polygon']: [0, 'field map'],
            self.left_tab['scatter']: [0, 'scatter', 'heatmap', 'ternary map'],
            self.left_tab['ndim']: [0, 'TEC', 'Radar'],
            self.left_tab['multidim']: [0, 'variance','vectors','PCA scatter','PCA heatmap','PCA score'],
            self.left_tab['cluster']: [0, 'cluster', 'cluster score', 'cluster performance'],
            self.left_tab['special']: [0,'field map', 'gradient map', 'cluster score', 'PCA score', 'profile'],
            -1: [0, 'field map']}



        # Menu and Toolbar
        #-------------------------
        self.io = LameIO(parent=self, connect_actions=True, debug=self.logger_options['IO'])

        # Connect the "Open" action to a function
        self.actionQuit_LaME.triggered.connect(self.quit)

        # Intialize Tabs as not enabled
        self.PreprocessPage.setEnabled(False)
        self.SelectAnalytePage.setEnabled(False)
        #self.SpotDataPage.setEnabled(False)
        #self.PolygonPage.setEnabled(False)
        self.ScatterPage.setEnabled(False)
        self.NDIMPage.setEnabled(False)
        self.MultidimensionalPage.setEnabled(False)
        self.ClusteringPage.setEnabled(False)
        #self.ProfilingPage.setEnabled(False)
        #self.PTtPage.setEnabled(False)

        self.actionSavePlotToTree.triggered.connect(self.add_plotwidget_to_tree)
        self.actionSelectAnalytes.triggered.connect(self.open_select_analyte_dialog)
        #self.actionSpotData.triggered.connect(lambda: self.toggle_spot_tab)

        #apply filters
        self.actionClearFilters.triggered.connect(lambda: self.apply_filters(fullmap=True))
        self.actionClearFilters.setEnabled(False)
        self.actionFilterToggle.triggered.connect(lambda: self.apply_filters(fullmap=False))
        self.actionFilterToggle.setEnabled(False)
        self.actionPolygonMask.triggered.connect(lambda: self.apply_filters(fullmap=False))
        self.actionPolygonMask.setEnabled(False)
        self.actionClusterMask.triggered.connect(lambda: self.apply_filters(fullmap=False))
        self.actionClusterMask.setEnabled(False)
        #self.actionNoiseReduction.triggered.connect()
        self.actionNoiseReduction.setEnabled(False)

        self.actionCorrelation.triggered.connect(lambda: self.open_tab('samples'))
        self.actionHistograms.triggered.connect(lambda: self.open_tab('preprocess'))
        self.actionBiPlot.triggered.connect(lambda: self.open_tab('scatter'))
        self.actionTernary.triggered.connect(self.open_ternary)
        self.actionTEC.triggered.connect(lambda: self.open_tab('ndim'))
        self.actionCluster.triggered.connect(lambda: self.open_tab('clustering'))
        self.actionReset.triggered.connect(lambda: self.reset_analysis())
        self.actionSwapAxes.triggered.connect(self.swap_xy)
        self.actionSwapAxes.setEnabled(False)

        self.actionFilters.triggered.connect(lambda: self.open_mask_dock('filter'))
        self.actionPolygons.triggered.connect(lambda: self.open_mask_dock('polygon'))
        self.actionClusters.triggered.connect(lambda: self.open_mask_dock('cluster'))

        self.info_tab = {}
        self.actionInfo.triggered.connect(self.open_info_dock)

        self.actionHelp.setCheckable(True)
        self.actionHelp.toggled.connect(self.toggle_help_mode)


        # For light and dark themes, connects actionViewMode
        self.theme = UIThemes(app, self)


        # initiate Workflow 
        self.actionWorkflowTool.triggered.connect(self.open_workflow)

        self.plot_tree = PlotTree(self)

        #init table_fcn
        self.table_fcn = TableFcn(self)

        # Select analyte Tab
        #-------------------------
        # The reference chemistry is shown in two comboboxes... they should always display the same
        # reference chemistry
        self.comboBoxRefMaterial.addItems(self.app_data.ref_list.values)          # Select analyte Tab
        self.comboBoxNDimRefMaterial.addItems(self.app_data.ref_list.values)      # NDim Tab
        self.comboBoxRefMaterial.activated.connect(lambda: self.update_ref_chem_combobox(self.comboBoxRefMaterial.currentText())) 
        self.comboBoxNDimRefMaterial.activated.connect(lambda: self.update_ref_chem_combobox(self.comboBoxNDimRefMaterial.currentText()))
        self.comboBoxRefMaterial.setCurrentIndex(0)
        self.comboBoxNDimRefMaterial.setCurrentIndex(0)

        self.toolButtonScaleEqualize.clicked.connect(self.update_equalize_color_scale)
        self.spinBoxFieldIndex.valueChanged.connect(self.hist_field_update)

        self.comboBoxCorrelationMethod.activated.connect(self.update_corr_method)
        self.checkBoxCorrelationSquared.stateChanged.connect(self.correlation_squared_callback)


        self.comboBoxOutlierMethod.addItems(['none', 'quantile critera','quantile and distance critera', 'Chauvenet criterion', 'log(n>x) inflection'])
        self.comboBoxOutlierMethod.setCurrentText('Chauvenet criterion')
        self.comboBoxOutlierMethod.activated.connect(lambda: self.update_outlier_removal(self.comboBoxOutlierMethod.currentText()
))

        self.comboBoxNegativeMethod.addItems(['ignore negatives', 'minimum positive', 'gradual shift', 'Yeo-Johnson transform'])
        self.comboBoxNegativeMethod.activated.connect(lambda: self.update_neg_handling(self.comboBoxNegativeMethod.currentText()))

        # Selecting analytes
        #-------------------------
        self.comboBoxSampleId.currentTextChanged.connect(self.update_sample_id)
        self.canvasWindow.currentChanged.connect(self.canvas_changed)


        self.lineEditResolutionNx.precision = None
        self.lineEditResolutionNy.precision = None

        pixelwidthvalidator = QDoubleValidator()
        pixelwidthvalidator.setBottom(0.0)
        self.lineEditDX.setValidator(pixelwidthvalidator)
        self.lineEditDY.setValidator(pixelwidthvalidator)

        # auto scale
        quantilevalidator = QDoubleValidator(0.0, 100, 3)

        self.lineEditLowerQuantile.precision = 3
        self.lineEditLowerQuantile.setValidator(quantilevalidator)
        self.lineEditLowerQuantile.editingFinished.connect(lambda: self.auto_scale(True))

        self.lineEditUpperQuantile.precision = 3
        self.lineEditUpperQuantile.setValidator(quantilevalidator)
        self.lineEditUpperQuantile.editingFinished.connect(lambda: self.auto_scale(True))

        self.lineEditDifferenceLowerQuantile.precision = 3
        self.lineEditDifferenceLowerQuantile.setValidator(quantilevalidator)
        self.lineEditDifferenceLowerQuantile.editingFinished.connect(lambda: self.auto_scale(True))

        self.lineEditDifferenceUpperQuantile.precision = 3
        self.lineEditDifferenceUpperQuantile.setValidator(quantilevalidator)
        self.lineEditDifferenceUpperQuantile.editingFinished.connect(lambda: self.auto_scale(True))

        # auto scale controls
        self.toolButtonAutoScale.clicked.connect(lambda: self.auto_scale(False))
        # self.toolButtonAutoScale.clicked.connect(self.update_SV)
        self.toolButtonAutoScale.setChecked(True)

        # Preprocess Tab
        #-------------------------
        # histogram
        self.default_bins = 100
        #self.comboBoxHistFieldType.activated.connect()
        self.comboBoxHistFieldType.activated.connect(self.update_histogram_field_type)
        self.comboBoxHistField.activated.connect(self.update_histogram_field)
        self.spinBoxNBins.setValue(self.default_bins)
        self.spinBoxNBins.valueChanged.connect(self.update_histogram_num_bins)
        self.doubleSpinBoxBinWidth.valueChanged.connect(self.update_histogram_bin_width)
        self.toolButtonHistogramReset.clicked.connect(self.app_data.histogram_reset_bins)
        self.toolButtonHistogramReset.clicked.connect(lambda: plot_histogram(self, self.data, self.app_data, self.plot_style))

        #uncheck crop is checked
        self.toolBox.currentChanged.connect(lambda: self.canvasWindow.setCurrentIndex(self.canvas_tab['sv']))

        # Noise reduction
        self.noise_reduction = ip(self)

        # Initiate crop tool
        self.crop_tool = CropTool(self)
        self.actionCrop.triggered.connect(self.crop_tool.init_crop)



        # Filter Tabs
        #-------------------------
        self.lineEditDX.editingFinished.connect(self.update_dx)
        self.lineEditDY.editingFinished.connect(self.update_dy)
        self.actionFullMap.triggered.connect(self.reset_crop)
        parent.actionFullMap.triggered.connect(self.reset_to_full_view)
        parent.actionFullMap.triggered.connect(lambda: self.actionCrop.setChecked(False))
        parent.actionFullMap.setEnabled(False)

        self.toolButtonSwapResolution.clicked.connect(self.update_swap_resolution)
        self.toolButtonPixelResolutionReset.clicked.connect(self.reset_pixel_resolution)

        # Scatter and Ternary Tab
        #-------------------------
        self.toolButtonTernaryMap.clicked.connect(lambda: plot_ternary_map(self, self.data[self.app_data.sample_id], self.app_data, self.plot_style))

        self.comboBoxFieldTypeX.activated.connect(lambda: self.update_field_combobox(self.comboBoxFieldTypeX, self.comboBoxFieldX))
        self.comboBoxFieldTypeY.activated.connect(lambda: self.update_field_combobox(self.comboBoxFieldTypeY, self.comboBoxFieldY))
        self.comboBoxFieldTypeZ.activated.connect(lambda: self.update_field_combobox(self.comboBoxFieldTypeZ, self.comboBoxFieldZ))


        # Multidimensional Tab
        #------------------------
        self.pca_results = []
        self.spinBoxPCX.valueChanged.connect(self.plot_pca)
        self.spinBoxPCY.valueChanged.connect(self.plot_pca)


        self.comboBoxColorField.setPlaceholderText("None")
        self.spinBoxColorField.lineEdit().setReadOnly(True)
        self.spinBoxFieldIndex.lineEdit().setReadOnly(True)

        # Scatter and Ternary Tab
        #-------------------------
        self.comboBoxFieldX.activated.connect(lambda: plot_scatter(self, self.data, self.app_data, self.plot_style))
        self.comboBoxFieldY.activated.connect(lambda: plot_scatter(self, self.data, self.app_data, self.plot_style))
        self.comboBoxFieldZ.activated.connect(lambda: plot_scatter(self, self.data, self.app_data, self.plot_style))


        # N-Dim Tab
        #-------------------------
        # setup comboBoxNDIM
        self.comboBoxNDimAnalyteSet.clear()
        self.comboBoxNDimAnalyteSet.addItems(list(self.app_data.ndim_list_dict.keys()))

        #self.comboBoxNDimRefMaterial.addItems(self.app_data.ref_list.values) This is done with the Set analyte tab initialization above.
        self.toolButtonNDimAnalyteAdd.clicked.connect(lambda: self.update_ndim_table('analyteAdd'))
        self.toolButtonNDimAnalyteSetAdd.clicked.connect(lambda: self.update_ndim_table('analytesetAdd'))
        self.toolButtonNDimUp.clicked.connect(lambda: self.table_fcn.move_row_up(self.tableWidgetNDim))
        self.toolButtonNDimDown.clicked.connect(lambda: self.table_fcn.move_row_down(self.tableWidgetNDim))
        self.toolButtonNDimSelectAll.clicked.connect(self.tableWidgetNDim.selectAll)
        self.toolButtonNDimRemove.clicked.connect(lambda: self.table_fcn.delete_row(self.tableWidgetNDim))
        self.toolButtonNDimSaveList.clicked.connect(self.save_ndim_list)

        # N-dim table
        header = self.tableWidgetNDim.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)

        # Profile Tab
        #-------------------------
        #self.lineEditPointRadius.setValidator(QIntValidator())
        #self.lineEditYThresh.setValidator(QIntValidator())
        # self.profiling = Profiling(self)
        # #self.comboBoxProfileList.addItem('Create New Profile')
        # #self.comboBoxProfileList.activated.connect(lambda: self.profiling.on_profile_selected(self.comboBoxProfileList.currentText()))

        # # create new profile or update existing
        # self.toolButtonPlotProfile.clicked.connect(lambda: self.profiling.on_profile_selected(self.comboBoxProfileList.currentText()))

        # #select entire row
        # header = self.tableWidgetProfilePoints.horizontalHeader()
        # header.setSectionResizeMode(0,QHeaderView.Stretch)
        # header.setSectionResizeMode(1,QHeaderView.ResizeToContents)
        # header.setSectionResizeMode(2,QHeaderView.ResizeToContents)

        # self.tableWidgetProfilePoints.setSelectionBehavior(QTableWidget.SelectRows)
        # self.toolButtonPointUp.clicked.connect(lambda: self.table_fcn.move_row_up(self.tableWidgetProfilePoints))
        # self.toolButtonPointDown.clicked.connect(lambda: self.table_fcn.move_row_down(self.tableWidgetProfilePoints))
        # self.toolButtonPointDelete.clicked.connect(lambda: self.table_fcn.delete_row(self.tableWidgetProfilePoints))
        # self.comboBoxProfileSort.currentIndexChanged.connect(self.plot_profile_and_table)
        # self.toolButtonProfileInterpolate.clicked.connect(lambda: self.profiling.interpolate_points(interpolation_distance=int(self.lineEditIntDist.text()), radius= int(self.lineEditPointRadius.text())))
        # # update profile plot when point type is changed
        # self.comboBoxPointType.currentIndexChanged.connect(lambda: self.profiling.plot_profiles())
        # # update profile plot when selected subplot is changed
        # self.spinBoxProfileSelectedSubplot.valueChanged.connect(lambda: self.profiling.plot_profiles())
        # # update profile plot when Num subplot is changed
        # self.spinBoxProfileNumSubplots.valueChanged.connect(lambda: self.profiling.plot_profiles())
        # self.spinBoxProfileNumSubplots.valueChanged.connect(self.update_profile_spinbox)
        # # update profile plot when field in subplot table is changed
        # self.toolButtonProfileAddField.clicked.connect(lambda: self.profiling.plot_profiles())
        
        # # Connect the add and remove field buttons to methods
        # self.toolButtonProfileAddField.clicked.connect(self.profiling.add_field_to_listview)
        # self.toolButtonProfileRemove.clicked.connect(self.profiling.remove_field_from_listview)
        # self.toolButtonProfileRemove.clicked.connect(lambda: self.profiling.plot_profiles())
        # self.comboBoxProfileFieldType.activated.connect(lambda: self.update_field_combobox(self.comboBoxProfileFieldType, self.comboBoxProfileField))

        # # below line is commented because plot_profiles is automatically triggered when user clicks on map once they are in profiling tab
        # # self.toolButtonPlotProfile.clicked.connect(lambda:self.profiling.plot_profiles())
        # self.toolButtonPointSelectAll.clicked.connect(self.tableWidgetProfilePoints.selectAll)
        # # Connect toolButtonProfileEditToggle's clicked signal to toggle edit mode
        # self.toolButtonProfileEditToggle.clicked.connect(self.profiling.toggle_edit_mode)

        # # Connect toolButtonProfilePointToggle's clicked signal to toggle point visibility
        # self.toolButtonProfilePointToggle.clicked.connect(self.profiling.toggle_point_visibility)


        # Special Tab
        #------------------------
        #SV/MV tool box
        self.toolButtonPan.setCheckable(True)
        self.toolButtonPan.setCheckable(True)

        self.toolButtonZoom.setCheckable(True)
        self.toolButtonZoom.setCheckable(True)


        
        # Styling Tab
        #-------------------------

        # initalize self.comboBoxPlotType
        self.update_plot_type_combobox_options()
        self.comboBoxPlotType.currentIndexChanged.connect(self.update_plot_type)

        # Initialize a variable to store the current plot type
        self.plot_style.plot_type = 'field map'


        setattr(self.comboBoxMVPlots, "allItems", lambda: [self.comboBoxMVPlots.itemText(i) for i in range(self.comboBoxMVPlots.count())])
        
        # Connect the signal to your handler
        self.field = None
        self.comboBoxColorField.currentIndexChanged.connect(self.on_field_changed)
        self.field_type = None
        self.comboBoxColorByField.currentIndexChanged.connect(self.on_field_type_changed)

        # Connect the checkbox's stateChanged signal to our update function
        # self.doubleSpinBoxMarkerSize.valueChanged.connect(lambda: self.plot_scatter(save=False))
        #self.comboBoxColorByField.activated.connect(lambda: self.update_field_combobox(self.comboBoxColorByField, self.comboBoxColorField))

        # Calculator tab
        #-------------------------
        if hasattr(self,'notes'):
            self.notes.update_equation_menu()

        # Profile filter tab
        #-------------------------

        # Notes tab
        #-------------------------
        self.actionNotes.triggered.connect(self.open_notes)

        
        # Plot toolbars
        #-------------------------

        # single view tools
        self.toolButtonHome.clicked.connect(lambda: self.toolbar_plotting('home', 'SV'))
        self.toolButtonPan.clicked.connect(lambda: self.toolbar_plotting('pan', 'SV', self.toolButtonPan.isChecked()))
        self.toolButtonZoom.clicked.connect(lambda: self.toolbar_plotting('zoom', 'SV', self.toolButtonZoom.isChecked()))
        self.toolButtonAnnotate.clicked.connect(lambda: self.toolbar_plotting('annotate', 'SV'))
        self.toolButtonDistance.toggled.connect(self.toggle_distance_tool)
        self.toolButtonDistance.clicked.connect(lambda: self.toolbar_plotting('distance', 'SV'))
        self.toolButtonPopFigure.clicked.connect(lambda: self.toolbar_plotting('pop', 'SV'))
        # self.toolButtonSave.clicked.connect(lambda: self.toolbar_plotting('save', 'SV', self.toolButtonSave.isChecked()))
        SaveMenu_items = ['Figure', 'Data']
        SaveMenu = QMenu()
        SaveMenu.triggered.connect(self.save_plot)
        self.toolButtonSave.setMenu(SaveMenu)
        for item in SaveMenu_items:
            SaveMenu.addAction(item)
        self.canvas_changed()

        # multi-view tools
        self.actionCalculator.triggered.connect(self.open_calculator)
        self.open_calculator()
        self.calculator.hide()

        # Setup Help
        #-------------------------
        self.actionReportBug.triggered.connect(lambda: self.open_browser('report_bug'))
        self.actionUserGuide.triggered.connect(lambda: self.open_browser('user_guide'))
        self.actionTutorials.triggered.connect(lambda: self.open_browser('tutorials'))

        # self.centralwidget.installEventFilter(self)
        # self.canvasWindow.installEventFilter(self)
        # self.dockWidgetLeftToolbox.installEventFilter(self)
        # self.dockWidgetRightToolbox.installEventFilter(self)
        # self.dockWidgetMaskToolbox.installEventFilter(self)

        # Create a button to hide/show the dock
        self.toolButtonLeftDock = QToolButton(self)
        self.toolButtonLeftDock.setFixedSize(24, 24)
        self.toolButtonLeftDock.setIconSize(QSize(18, 18))
        self.toolButtonLeftDock.setCheckable(True)
        self.toolButtonLeftDock.setIcon(QIcon(':/resources/icons/icon-left_toolbar_show-64.svg'))
        self.toolButtonLeftDock.toggled.connect(lambda checked: self.toolButtonLeftDock.setIcon(QIcon(':/resources/icons/icon-left_toolbar_show-64.svg') if checked else QIcon(':/resources/icons/icon-left_toolbar_hide-64.svg')))

        self.toolButtonRightDock = QToolButton(self)
        self.toolButtonRightDock.setFixedSize(24, 24)
        self.toolButtonRightDock.setIconSize(QSize(18, 18))
        self.toolButtonRightDock.setCheckable(True)
        self.toolButtonRightDock.setIcon(QIcon(':/resources/icons/icon-right_toolbar_show-64.svg'))
        self.toolButtonRightDock.toggled.connect(lambda checked: self.toolButtonRightDock.setIcon(QIcon(':/resources/icons/icon-right_toolbar_show-64.svg') if checked else QIcon(':/resources/icons/icon-right_toolbar_hide-64.svg')))

        self.toolButtonBottomDock = QToolButton(self)
        self.toolButtonBottomDock.setFixedSize(24, 24)
        self.toolButtonBottomDock.setIconSize(QSize(18, 18))
        self.toolButtonBottomDock.setCheckable(True)
        self.toolButtonBottomDock.setIcon(QIcon(':/resources/icons/icon-bottom_toolbar_show-64.svg'))
        self.toolButtonBottomDock.toggled.connect(lambda checked: self.toolButtonBottomDock.setIcon(QIcon(':/resources/icons/icon-bottom_toolbar_show-64.svg') if checked else QIcon(':/resources/icons/icon-bottom_toolbar_hide-64.svg')))

        self.toolButtonLeftDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.dockWidgetLeftToolbox, button=self.toolButtonLeftDock))
        self.toolButtonRightDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.dockWidgetPlotTree, button=None))
        self.toolButtonRightDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.dockWidgetStyling, button=self.toolButtonRightDock))


        # Add the button to the status bar
        self.labelInvalidValues = QLabel("Negative/zeros: False, NaNs: False")
        self.statusbar.addPermanentWidget(self.labelInvalidValues)

        self.statusbar.addPermanentWidget(self.toolButtonLeftDock)
        self.statusbar.addPermanentWidget(self.toolButtonBottomDock)
        self.statusbar.addPermanentWidget(self.toolButtonRightDock)

        self.toolBox.currentChanged.connect(self.toolbox_changed)

        # logger
        self.actionLogger.triggered.connect(self.open_logger)

        self.dockWidgetLeftToolbox.show()
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWidgetLeftToolbox)
        self.dockWidgetLeftToolbox.setFloating(False)
        self.dockWidgetPlotTree.show()
        self.dockWidgetStyling.show()
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockWidgetPlotTree)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockWidgetStyling)
        self.dockWidgetPlotTree.setFloating(False)
        self.dockWidgetStyling.setFloating(False)

    def connect_app_data_observers(self, app_data):
        app_data.add_observer("sort_method", self.update_sort_method)
        app_data.add_observer("ref_chem", self.update_ref_index_combobox)
        app_data.add_observer("sample_list", self.update_sample_list_combobox)
        app_data.add_observer("sample_id", self.update_sample_id_combobox)
        app_data.add_observer("apply_process_to_all_data", self.update_autoscale_checkbox)
        app_data.add_observer("equalize_color_scale", self.update_equalize_color_scale_toolbutton)
        app_data.add_observer("hist_field_type", self.update_hist_field_type_combobox)
        app_data.add_observer("hist_field", self.update_hist_field_combobox)
        app_data.add_observer("hist_bin_width", self.update_hist_bin_width_spinbox)
        app_data.add_observer("hist_num_bins", self.update_hist_num_bins_spinbox)
        app_data.add_observer("hist_plot_style", self.update_hist_plot_style_combobox)
        app_data.add_observer("corr_method", self.update_corr_method_combobox)
        app_data.add_observer("corr_squared", self.update_corr_squared_checkbox)
        app_data.add_observer("noise_red_method", self.update_noise_red_method_combobox)
        app_data.add_observer("noise_red_option1", self.update_noise_red_option1_spinbox)
        app_data.add_observer("noise_red_option2", self.update_noise_red_option2_spinbox)
        app_data.add_observer("gradient_flag", self.update_gradient_flag_checkbox)
        app_data.add_observer("x_field_type", self.update_x_field_type_combobox)
        app_data.add_observer("y_field_type", self.update_y_field_type_combobox)
        app_data.add_observer("z_field_type", self.update_z_field_type_combobox)
        app_data.add_observer("x_field", self.update_x_field_combobox)
        app_data.add_observer("y_field", self.update_y_field_combobox)
        app_data.add_observer("z_field", self.update_z_field_combobox)
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
        plot_style.add_observer("plot_type", self.update_plot_type_combobox)
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
        plot_style.add_observer("c_field_type", self.update_color_field_type_combobox)
        plot_style.add_observer("c_field", self.update_color_field_combobox)
        plot_style.add_observer("cmap", self.update_cmap_combobox)
        plot_style.add_observer("cbar_reverse", self.update_cbar_reverse_checkbox)
        plot_style.add_observer("cbar_direction", self.update_cbar_direction_combobox)
        plot_style.add_observer("clim", self.update_clim_lineedits)
        plot_style.add_observer("clabel", self.update_clabel_lineedit)
        plot_style.add_observer("cscale", self.update_cscale_combobox)
        plot_style.add_observer("resolution", self.update_resolution_spinbox)

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
        self.comboBoxSampleId.setCurrentIndex(0)

        self.canvasWindow.setCurrentIndex(self.canvas_tab['sv'])
        self.init_tabs()
        self.change_sample()
        # self.profile_dock.profiling.add_samples()
        # self.polygon.add_samples()

        self.plot_style.schedule_update()

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
        self.plot_style.schedule_update()


    def update_equalize_color_scale_toolbutton(self, value):
        self.toolButtonScaleEqualize.setChecked(value)

        if self.plot_style.plot_type == 'field map':
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
            # update x axis limits in style_dict 
            self.plot_style.initialize_axis_values(self.field_type, field)
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
            # update y axis limits in style_dict 
            self.plot_style.initialize_axis_values(self.field_type, field)
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

    def update_hist_field_type_combobox(self, value):
        """Updates ``MainWindow.comboBoxHistFieldType.currentText()``

        Called as an update to ``app_data.hist_field_type``.  Updates the histogram field type (also controls field maps).  Schedules a plot update.

        Parameters
        ----------
        value : str
            New field type.
        """
        self.comboBoxHistFieldType.setCurrentText(value)
        if self.plot_style.plot_type == "histogram":
            self.plot_style.schedule_update()

    def update_hist_field_combobox(self, value):
        """Updates ``MainWindow.comboBoxHistFieldType.currentText()``

        Called as an update to ``app_data.hist_field``.  Updates the histogram field.  Schedules a plot update.

        Parameters
        ----------
        value : str
            New field type.
        """
        self.comboBoxHistField.setCurrentText(value)

        # update 
        self.spinBoxFieldIndex.setMinimum(0)
        self.spinBoxFieldIndex.setMaximum(self.comboBoxHistField.count() - 1)
        self.spinBoxFieldIndex.setValue(self.comboBoxHistField.currentIndex())

        if self.toolBox.currentIndex() == self.left_tab['sample'] and self.plot_style.plot_type in ['field map','histogram','correlation']:
            self.plot_style.color_field_type = self.comboBoxHistFieldType.currentText()
            self.plot_style.color_field = self.comboBoxHistField.currentText()

            self.plot_style.schedule_update()

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

    def update_x_field_type_combobox(self, new_field_type):
        self.comboBoxFieldTypeX.setCurrentText(new_field_type)
        if self.toolBox.currentIndex() == self.left_tab['scatter']:
            self.plot_style.schedule_update()

    def update_y_field_type_combobox(self, new_field_type):
        self.comboBoxFieldTypeY.setCurrentText(new_field_type)
        if self.toolBox.currentIndex() == self.left_tab['scatter']:
            self.plot_style.schedule_update()

    def update_z_field_type_combobox(self, new_field_type):
        self.comboBoxFieldTypeZ.setCurrentText(new_field_type)
        if self.toolBox.currentIndex() == self.left_tab['scatter']:
            self.plot_style.schedule_update()

    def update_x_field_combobox(self, new_field):
        self.comboBoxFieldX.setCurrentText(new_field)
        if self.toolBox.currentIndex() == self.left_tab['scatter']:
            self.plot_style.schedule_update()

    def update_y_field_combobox(self, new_field):
        self.comboBoxFieldY.setCurrentText(new_field)
        if self.toolBox.currentIndex() == self.left_tab['scatter']:
            self.plot_style.schedule_update()

    def update_z_field_combobox(self, new_field):
        self.comboBoxFieldZ.setCurrentText(new_field)
        if self.toolBox.currentIndex() == self.left_tab['scatter']:
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

    def update_ndim_quantile_index_combobox(self, new_ndim_quantile_index):
        self.comboBoxNDimQuantiles.setCurrentIndex(new_ndim_quantile_index)
        if self.toolBox.currentIndex() == self.left_tab['ndim']:
            self.plot_style.schedule_update()

    def update_dim_red_method_combobox(self, new_dim_red_method):
        self.comboBoxNoiseReductionMethod.setCurrentText(new_dim_red_method)
        if self.toolBox.currentIndex() == self.left_tab['multidim']:
            self.plot_style.schedule_update()

    def update_dim_red_x_spinbox(self, new_dim_red_x):
        self.spinBoxPCX.setValue(int(new_dim_red_x))
        if self.toolBox.currentIndex() == self.left_tab['multidim']:
            self.plot_style.schedule_update()

    def update_dim_red_y_spinbox(self, new_dim_red_y):
        self.spinBoxPCY.setValue(int(new_dim_red_y))
        if self.toolBox.currentIndex() == self.left_tab['multidim']:
            self.plot_style.schedule_update()

    def update_cluster_method_combobox(self, new_cluster_method):
        self.comboBoxClusterMethod.setCurrentText(new_cluster_method)
        if self.toolBox.currentIndex() == self.left_tab['cluster']:
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
        self.horizontalSliderClusterExponent.setValue(new_cluster_exponent)
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
            print(f"update_sample_id: {self.app_data.sample_id}\n")

        # See if the user wants to really change samples and save or discard the current work
        if self.data and self.app_data.sample_id != '':
            # Create and configure the QMessageBox
            msgBox = QMessageBox.warning(self,
                    "Save sample",
                    "Do you want to save the current analysis?",
                    QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Save)
            #iconWarning = QIcon(":/resources/icons/icon-warning-64.svg")
            #msgBox.setWindowIcon(iconWarning)  # Set custom icon

            # Display the dialog and wait for user action
            response = msgBox.exec()

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

        self.change_sample()

    def update_equalize_color_scale(self):
        self.app_data.equalize_color_scale = self.toolButtonScaleEqualize.isChecked()
        if self.plot_style.plot_type == "field map":
            self.plot_style.schedule_update()

    def update_corr_method(self):
        self.app_data.corr_method = self.comboBoxCorrelationMethod.currentText()

        self.correlation_method_callback()

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

    def update_color_field_type_combobox(self, new_field_type):
        self.comboBoxColorByField.setCurrentText(new_field_type)

        self.update_field_combobox(self.comboBoxColorByField, self.comboBoxColorField)
        self.plot_style.color_field = self.comboBoxColorField.currentText()
        self.plot_style.update_color_field_spinbox()

        self.plot_style.schedule_update()

    def update_color_field_combobox(self, new_field):
        self.comboBoxColorField.setCurrentText(new_field)
        self.plot_style.schedule_update()

    def update_color_field_spinbox(self, value):
        self.spinBoxColorField.setMinimum(0)
        self.spinBoxColorField.setMaximum(self.comboBoxColorField.count() - 1)
        #self.spinBoxFieldIndex.valueChanged.connect(self.hist_field_update)

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


    def update_autoscale_checkbox(self, value):
        """Updates the ``MainWindow.checkBoxApplyAll`` which controls the data processing methods."""
        if value is None:
            self.checkBoxApplyAll.setChecked(True)
        else:
            self.checkBoxApplyAll.setChecked(False)

        self.plot_style.schedule_update()

    
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


    def reindex_left_tab(self):
        self.left_tab = {}
        self.left_tab.update({'spot': None})
        self.left_tab.update({'special': None})
        for tid in range(0,self.toolBox.count()):
            match self.toolBox.itemText(tid).lower():
                case 'preprocess':
                    self.left_tab.update({'process': tid})
                case 'field viewer':
                    self.left_tab.update({'sample': tid})
                case 'spot data':
                    self.left_tab.update({'spot': tid})
                case 'polygons':
                    self.left_tab.update({'polygons': tid})
                case 'profiling':
                    self.left_tab.update({'profile': tid})
                case 'scatter and heatmaps':
                    self.left_tab.update({'scatter': tid})
                case 'n-dim':
                    self.left_tab.update({'ndim': tid})
                case 'dimensional reduction':
                    self.left_tab.update({'multidim': tid})
                case 'clustering':
                    self.left_tab.update({'cluster': tid})
                case 'p-t-t functions':
                    self.left_tab.update({'special': tid})


    def logger_visibility_change(self, visible):
        """
        Redirect stdout based on the visibility of the logger dock.
        """
        if visible:
            sys.stdout = self.logger  # Redirect stdout to logger
        else:
            sys.stdout = sys.__stdout__  # Restore to default stdout    

    
    def on_field_type_changed(self):
        # Update self.field_type whenever combo box changes
        self.field_type = self.comboBoxColorByField.currentText()

    def on_field_changed(self):
        # Update self.field_type whenever combo box changes
        self.field = self.comboBoxColorField.currentText()

    def update_show_mass(self):
        """
        Update ``plot_style.show_mass`` whenever the checkbox changes.
        state is an int, so we convert it to bool by checking if it equals QtCore.Qt.Checked.
        """
        self.plot_style.show_mass = self.checkBoxShowMass.isChecked()
        self.plot_style.schedule_update()

    # -------------------------------------
    # Reset to start
    # -------------------------------------
    def reset_analysis(self, selection='full'):
        if self.app_data.sample_id == '':
            return

        if selection =='full':  # nuke the current setup and start over fresh
            # show dialog to to get confirmation from user
            msgBox = QMessageBox.warning(self,
                "Reset analyes",
                "Do you wish to discard all work and reset analyses?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Save | QMessageBox.StandardButton.No
            )
            #iconWarning = QIcon()
            #iconWarning.addPixmap(QPixmap(":/resources/icons/icon-warning-64.svg"), QIcon.Normal, QIcon.Off)
            #msgBox.setWindowIcon(iconWarning)  # Set custom icon

            # Display the dialog and wait for user action
            response = msgBox.exec()

            if response == QMessageBox.StandardButton.No:
                return
            elif response == QMessageBox.StandardButton.Save:
                self.io.save_project()

            #reset Data
            self.data = {}

            #reset App, but keep the sample list and current sample
            sample_id = self.app_data.sample_id
            sample_list = self.app_data.sample_list

            self.app_data = AppData(self.data)

            #reset Styling
            self.plot_style = StylingDock(self.data, debug=self.logger_options['Style'])

            self.multi_view_index = []
            self.laser_map_dict = {}
            self.multiview_info_label = {}
            self.ndim_list = []
            self.lasermaps = {}
            #self.treeModel.clear()
            self.prev_plot = ''
            self.plot_tree = PlotTree(self)

            # reset styles
            self.plot_style.reset_default_styles()

            # reset plot layouts
            self.clear_layout(self.widgetSingleView.layout())
            self.clear_layout(self.widgetMultiView.layout())
            self.clear_layout(self.widgetQuickView.layout())

            # trigger update to plot
            self.plot_style.schedule_update()

            self.mask_dock.filter_tab.tableWidgetFilters.clearContents()
            self.mask_dock.filter_tab.tableWidgetFilters.setRowCount(0)

            # reset sample_id and sample_list
            self.app_data.sample_list = sample_list
            self.app_data.sample_id = sample_id
        elif selection == 'sample': #sample is changed

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
            if hasattr(self, "polygon"):
                # self.polygon is created in mask_dock.polygon_tab
                self.polygon.clear_polygons()

            #clear profiling
            if hasattr(self, "profile_dock"):
                self.profile_dock.profiling.clear_profiles()
                self.profile_dock.profile_toggle.setChecked(False)



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
        
    def init_tabs(self):
        self.toolBox.setCurrentIndex(self.left_tab['sample'])
    
        self.SelectAnalytePage.setEnabled(True)
        self.PreprocessPage.setEnabled(True)
        if hasattr(self,"spot_tools"):
            self.spot_tools.setEnabled(True)
        self.ScatterPage.setEnabled(True)
        self.NDIMPage.setEnabled(True)
        self.MultidimensionalPage.setEnabled(True)
        self.ClusteringPage.setEnabled(True)
        if hasattr(self,"special_tools"):
            self.special_tools.setEnabled(True)

    def change_sample(self):
        """Changes sample and plots first map"""
        if self.logger_options['Data']:
            print(f"change_sample\n")
            
        # set plot flag to false, allow plot to update only at the end
        self.plot_flag = False

        self.reset_analysis('sample')

        # add sample to sample dictionary
        if self.app_data.sample_id not in self.data:
            # obtain index of current sample
            index = self.app_data.sample_list.index(self.app_data.sample_id)

            # load sample's *.lame file
            file_path = os.path.join(self.app_data.selected_directory, self.app_data.csv_files[index])
            self.data[self.app_data.sample_id] = SampleObj(self.app_data.sample_id, file_path, self.comboBoxOutlierMethod.currentText(), self.comboBoxNegativeMethod.currentText(), self.app_data.ref_chem, debug=self.logger_options['Data'])
            self.connect_data_observers(self.data[self.app_data.sample_id])

            # enable widgets that require self.data not be empty
            self.toggle_data_widgets()
            
            # add sample to the plot tree
            self.plot_tree.add_sample(self.app_data.sample_id)
            self.plot_tree.update_tree()

        else:
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


        # sort data
        self.plot_tree.sort_tree(None, method=self.app_data.sort_method)

        # precalculate custom fields
        if self.calculator.precalculate_custom_fields:
            for name in self.calc_dict.keys():
                if name in self.data[self.app_data.sample_id].processed_data.columns:
                    continue
                self.calculator.comboBoxFormula.setCurrentText(name)
                self.calculator.calculate_new_field(save=False)

        # update docks
        if hasattr(self, "mask_dock"):
            self.update_mask_dock()

        if hasattr(self,'notes'):
            # change notes file to new sample.  This will initiate the new file and autosave timer.
            self.notes.notes_file = os.path.join(self.app_data.selected_directory,self.app_data.sample_id+'.rst')

        if hasattr(self,"info_dock"):
            self.info_dock.update_tab_widget()

        if hasattr(self, 'workflow'):
            self.update_blockly_field_types()

        # update data handling parameters
        self.update_ui_on_sample_change()
        
        # updates a label on the statusBar that displays the
        # number of negatives/zeros and nan values
        self.update_invalid_data_labels()
        
        self.init_tabs()

        # set field map to first available analyte
        if self.app_data.selected_analytes is not None:
            self.plot_style.color_field = self.app_data.selected_analytes[0]
        
        # update slot connections that depend on the sample
        self.toolButtonOutlierReset.clicked.connect(lambda: self.data[self.app_data.sample_id].reset_data_handling(self.comboBoxOutlierMethod.currentText(), self.comboBoxNegativeMethod.currentText()))

        # add spot data
        if hasattr(self, "spot_tab") and not self.data[self.app_data.sample_id].spotdata.empty:
            self.io.populate_spot_table()

        # reset filters
        self.actionClusterMask.setEnabled(False)
        self.actionPolygonMask.setEnabled(False)
        # this should come from the filter table checkboxes, not the UI checkbox
        #if not self.checkBoxPersistentFilter.isChecked():
        #    self.actionClearFilters.setEnabled(False)
        #    self.actionFilterToggle.setEnabled(False)
        self.actionNoiseReduction.setEnabled(False)

        # reset flags
        self.update_cluster_flag = True
        self.update_pca_flag = True

        # reset all plot types on change of tab to the first option
        for key in self.plot_types.keys():
            self.plot_types[key][0] = 0

        # set to single-view, tree view, and sample and fields tab
        self.toolBoxStyle.setCurrentIndex(0)
        self.toolBox.setCurrentIndex(self.left_tab['sample'])
        self.plot_style.set_style_widgets(self.plot_style.plot_type)

        # set canvas to single view
        self.canvasWindow.setCurrentIndex(self.canvas_tab['sv'])
        self.canvas_changed()
        
        # set toolbox
        self.toolBox.setCurrentIndex(self.left_tab['sample'])
        self.toolbox_changed()

        # update comboboxes to reflect list of available field types and fields
        self.update_all_field_comboboxes()
        # set color field and hist field as 'Analyte'
        self.plot_style.color_field_type = 'Analyte'
        self.plot_style.color_field = analyte_list[0]

        if self.plot_style.plot_type != 'field map':
            self.plot_style.plot_type = 'field map'

        # allow plots to be updated again
        self.plot_flag = True

        # trigger update to plot
        self.plot_style.schedule_update()

    def connect_data_observers(self, data):
        data.add_observer("nx", self.update_nx_lineedit)
        data.add_observer("ny", self.update_ny_lineedit)
        data.add_observer("dx", self.update_dx_lineedit)
        data.add_observer("dy", self.update_dy_lineedit)

    def update_ui_on_sample_change(self):
        # update dx, dy, nx, ny
        self.update_dx_lineedit(self.data[self.app_data.sample_id].dx)
        self.update_dy_lineedit(self.data[self.app_data.sample_id].dy)
        self.update_nx_lineedit(self.data[self.app_data.sample_id].nx)
        self.update_nx_lineedit(self.data[self.app_data.sample_id].ny)

        # update hist_field_type and hist_field
        self.hist_field_type = 'Analyte'
        field = ''
        if self.app_data.selected_analytes is None:
            field = self.data[self.app_data.sample_id].processed_data.match_attribute('data_type','Analyte')[0]
        else:
            field = self.app_data.selected_analytes[0]
        self.app_data.hist_field = field

        # hist_bin_width and should be updated along with hist_num_bins
        self.app_data.hist_num_bins = self.app_data.default_hist_num_bins

        # update UI with auto scale and neg handling parameters from 'Analyte Info'
        self.update_spinboxes(field_type='Analyte', field=analyte_list[0])
        # update noise reduction, outlier detection, neg. handling, quantile bounds, diff bounds
        self.data[self.app_data.sample_id].negative_method = self.data[self.app_data.sample_id].processed_data.get_attribute(field,'negative_method')
        self.data[self.app_data.sample_id].outlier_method = self.data[self.app_data.sample_id].processed_data.get_attribute(field,'outlier_method')
        self.data[self.app_data.sample_id].smoothing_method = self.data[self.app_data.sample_id].processed_data.get_attribute(field,'smoothing_method')
        self.data[self.app_data.sample_id].data_min_quantile = self.data[self.app_data.sample_id].processed_data.get_attribute(field,'lower_bound')
        self.data[self.app_data.sample_id].data_max_quantile = self.data[self.app_data.sample_id].processed_data.get_attribute(field,'upper_bound')
        self.data[self.app_data.sample_id].data_min_diff_quantile = self.data[self.app_data.sample_id].processed_data.get_attribute(field,'diff_lower_bound')
        self.data[self.app_data.sample_id].data_max_diff_quantile = self.data[self.app_data.sample_id].processed_data.get_attribute(field,'diff_upper_bound')

        # reference chemistry is set when the data are initialized
        #self.data[self.app_data.sample_id].ref_chem = self.app_data.ref_chem
        ref_name = self.data[self.app_data.sample_id].ref_chem.reference
        if ref_name in self.app_data.ref_list:
            self.app_data.ref_index = self.app_data.ref_list.tolist().index(ref_name)

        # update multidim method, pcx to 1 and pcy to 2 (if pca exists)
        # ???
        # update cluster method and cluster properties (if cluster exists)
        # ???
        

    def update_mask_dock(self):
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
        if hasattr(self, "polygon"):
            # self.polygon is created in mask_dock.polygon_tab
            self.polygon.clear_polygons()

        #clear profiling
        if hasattr(self, "profile_dock"):
            self.profile_dock.profiling.clear_profiles()
            self.profile_dock.profile_toggle.setChecked(False)


        self.mask_dock.filter_tab.update_filter_values()
        self.mask_dock.filter_tab.update_filter_table(reload=True)
        self.profile_dock.profiling.update_table_widget()
        self.polygon.update_table_widget()

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


    def hist_field_update(self):
        self.spinBoxFieldIndex.blockSignals(True)
        self.comboBoxHistField.setCurrentIndex(self.spinBoxFieldIndex.value())

        self.spinBoxColorField.setValue(self.spinBoxFieldIndex.value())

        self.spinBoxFieldIndex.blockSignals(False)

    def open_preferences_dialog(self):
        pass

    
    def update_analyte_ratio_selection(self,analyte_dict):
        """Updates analytes/ratios in mainwindow and its corresponding scale used for each field

        Updates analytes/ratios and its corresponding scale used for each field based on selection made by user in Analyteselection window or if user choses analyte list in blockly
        
        Parameters
            ----------
            analyte_dict: dict
                key: Analyte/Ratio name
                value: scale used (linear/log/logit)
        """
        #update self.data['norm'] with selection
        for analyte in self.data[self.app_data.sample_id].processed_data.match_attribute('data_type','Analyte'):
            if analyte in list(analyte_dict.keys()):
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
        #update analysis type combo in styles
        self.check_analysis_type()

        self.update_all_field_comboboxes()
        self.update_blockly_field_types()

    # Other windows/dialogs
    # -------------------------------------
    def open_workflow(self):
        """Opens Workflow dock.

        Opens workflow dock, creates on first instance.
        """
        if not hasattr(self, 'workflow'):
            self.workflow = Workflow(self)

            if not (self.workflow in self.help_mapping.keys()):
                self.help_mapping[self.workflow] = 'workflow'

        self.workflow.show()


        #self.workflow.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

    def open_mask_dock(self, tab_name=None):
        """Opens Mask dock

        Opens mask dock, creates on first instance.
        """
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

        Opens Profile dock, creates on first instance.
        :see also:
            Profile
        """
        if not hasattr(self, 'profile'):
            self.profile_dock = ProfileDock(self, debug=self.logger_options['Profile'])

            if not (self.profile_dock in self.help_mapping.keys()):
                self.help_mapping[self.profile_dock] = 'profiles'

        self.profile_dock.show()


    def open_notes(self):
        """Opens Notes dock

        Opens Notes dock, creates on first instance.
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

        Opens Calculator dock, creates on first instance.
        """            
        if not hasattr(self, 'logger'):
            calc_file = os.path.join(BASEDIR,f'resources/app_data/calculator.txt')
            self.calculator = CalculatorDock(self, filename=calc_file, debug=self.logger_options['Calculator'])

            if not (self.calculator in self.help_mapping.keys()):
                self.help_mapping[self.calculator] = 'calculator'

        self.calculator.show()



        #self.calculator.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

    def open_info_dock(self):
        if not hasattr(self, 'info_dock'):
            self.info_dock = InfoDock(self, "LaME Info")

            for tid in range(self.info_dock.info_tab_widget.count()):
                match self.info_dock.info_tab_widget.tabText(tid).lower():
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
        """Opens Logger dock

        Opens Logger dock, creates on first instance.
        """            
        if not hasattr(self, 'logger'):
            logfile = os.path.join(BASEDIR,f'resources/log/lame.log')
            self.logger = LoggerDock(logfile, self)
            self.logger.visibilityChanged.connect(self.logger_visibility_change)
        else:
            self.logger.show()

        self.help_mapping[self.logger] = 'logger'

        #self.logger.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

    def open_browser(self, action=None):
        """Opens Browser dock with documentation

        Opens Browser dock, creates on first instance.
        """            
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
    
    # -------------------------------
    # User interface functions
    # -------------------------------
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

    def update_plot_type_combobox_options(self):
        """Updates plot type combobox based on current toolbox index or certain dock widget controls."""
        self.comboBoxPlotType.clear()
        if self.profile_state == True or self.polygon_state == True:
            plot_idx = -1
        else:
            plot_idx = self.toolBox.currentIndex()

        self.comboBoxPlotType.addItems(self.plot_types[plot_idx][1:])
        self.comboBoxPlotType.setCurrentIndex(self.plot_types[plot_idx][0])
        self.plot_style.plot_type = self.comboBoxPlotType.currentText()
        if hasattr(self,"plot_style"):
            self.plot_style.set_style_widgets(self.plot_style.plot_type)

    def update_plot_type_combobox(self, new_plot_type):
        self.comboBoxPlotType.setCurrentText(new_plot_type)

        self.plot_style.toggle_style_widgets()

        self.plot_types[self.toolBox.currentIndex()][0] = self.comboBoxPlotType.currentIndex()

        match self.plot_style.plot_type.lower():
            case 'field map' | 'gradient map':
                self.actionSwapAxes.setEnabled(True)
            case 'scatter' | 'heatmap':
                self.actionSwapAxes.setEnabled(True)
            case 'correlation':
                self.actionSwapAxes.setEnabled(False)
                if self.comboBoxCorrelationMethod.currentText() == 'None':
                    self.comboBoxCorrelationMethod.setCurrentText('Pearson')
            case 'cluster performance':
                self.labelClusterMax.show()
                self.spinBoxClusterMax.show()
                self.labelNClusters.hide()
                self.spinBoxNClusters.hide()
            case 'cluster' | 'cluster score':
                self.labelClusterMax.hide()
                self.spinBoxClusterMax.hide()
                self.labelNClusters.show()
                self.spinBoxNClusters.show()
            case _:
                self.actionSwapAxes.setEnabled(False)

        self.signal_state = False
        self.plot_style.set_style_widgets(plot_type=self.plot_style.plot_type)
        self.signal_state = True
        #self.check_analysis_type()

        if self.plot_style.plot_type != '':
            self.plot_style.schedule_update()

    def update_plot_type(self):
        """Updates plot_style.plot_type in the StylingDock.
        
        Updates the plot_type.  Updates to other plot style properties and widgets
        is triggered by this change, but not handled in this method.

        :see also: StylingDock.plot_type, self.update_plot_type_combobox
        """
        self.plot_style.plot_type = self.comboBoxPlotType.currentText()


    def toolbox_changed(self):
        """Updates styles associated with toolbox page

        Executes on change of ``MainWindow.toolBox.currentIndex()``.  Updates style related widgets.
        """
        if self.logger_options['UI']:
            print(f"toolbox_changed")

        if self.app_data.sample_id == '':
            return

        tab_id = self.toolBox.currentIndex()

        # update the plot type comboBox options
        self.comboBoxPlotType.blockSignals(True)
        self.update_plot_type_combobox_options()
        self.comboBoxPlotType.setCurrentIndex(self.plot_types[self.toolBox.currentIndex()][0])
        self.comboBoxPlotType.blockSignals(False)

        # set to most used plot type on selected tab
        self.plot_style.plot_type = self.plot_types[tab_id][self.plot_types[tab_id][0]+1]
        
        match self.plot_types[tab_id][0]:
            case 'cluster' | 'cluster score':
                self.labelClusterMax.hide()
                self.spinBoxClusterMax.hide()
                self.labelNClusters.show()
                self.spinBoxNClusters.show()
            case 'cluster performance':
                self.labelClusterMax.show()
                self.spinBoxClusterMax.show()
                self.labelNClusters.hide()
                self.spinBoxNClusters.hide()
            
        # get the current plot type
        #plot_type = self.plot_style.plot_type
        #self.plot_style.set_style_widgets(plot_type=plot_type, style=self.plot_style.plot_type[plot_type])

        # If canvasWindow is set to SingleView, update the plot
        if self.canvasWindow.currentIndex() == self.canvas_tab['sv']:
        # trigger update to plot
            self.plot_style.schedule_update()

    def open_ternary(self):
        """Executes on actionTernary
        
        Opens the scatter tab and sets the ternary analytes.
        """
        self.open_tab('scatter')

        if self.app_data.sample_id:
            idx = 0
            while self.comboBoxFieldX.currentText() == self.comboBoxFieldY.currentText():
                self.comboBoxFieldY.setCurrentIndex(idx)
                idx += 1

            if self.comboBoxFieldTypeZ.currentText() == 'None':
                self.comboBoxFieldTypeZ.setCurrentText('Analyte')
                self.comboBoxFieldZ.setCurrentIndex(2)

    def input_ternary_name_dlg(self):
        """Opens a dialog to save new colormap

        Executes on ``MainWindow.toolButtonSaveTernaryColormap`` is clicked
        """
        name, ok = QInputDialog.getText(self, 'Custom ternary colormap', 'Enter new colormap name:')
        if ok:
            # update colormap structure
            self.ternary_colormaps.append({'scheme': name,
                    'top': get_hex_color(self.toolButtonTCmapXColor.palette().button().color()),
                    'left': get_hex_color(self.toolButtonTCmapYColor.palette().button().color()),
                    'right': get_hex_color(self.toolButtonTCmapZColor.palette().button().color()),
                    'center': get_hex_color(self.toolButtonTCmapMColor.palette().button().color())})
            # update comboBox
            self.comboBoxTernaryColormap.addItem(name)
            self.comboBoxTernaryColormap.setText(name)
            # add new row to file
            df = pd.DataFrame.from_dict(self.ternary_colormaps)
            df.to_csv('resources/styles/ternary_colormaps_new.csv', index=False)
        else:
            # throw a warning that name is not saved
            return
        
    def swap_xy(self):
        """Swaps X and Y coordinates of sample map

        Executes on ``MainWindow.toolButtonSwapXY.clicked``.  Updates data dictionary and other map related derived results.
        """
        match self.plot_style.plot_type:
            case 'field map':
                # swap x and y
                self.data[self.app_data.sample_id].swap_xy()

            case 'scatter' | 'heatmap':
                if self.comboBoxFieldZ.currentText() != '':
                    y_field_type = self.comboBoxFieldTypeX.currentText()
                    y_field = self.comboBoxFieldX.currentText()

                    z_field_type = self.comboBoxFieldTypeY.currentText()
                    z_field = self.comboBoxFieldY.currentText()

                    x_field_type = self.comboBoxFieldTypeZ.currentText()
                    x_field = self.comboBoxFieldZ.currentText()

                    self.comboBoxFieldTypeX.setCurrentText(x_field_type)
                    self.comboBoxFieldX.setCurrentText(x_field)

                    self.comboBoxFieldTypeY.setCurrentText(y_field_type)
                    self.comboBoxFieldY.setCurrentText(y_field)

                    self.comboBoxFieldTypeZ.setCurrentText(z_field_type)
                    self.comboBoxFieldZ.setCurrentText(z_field)
                else:
                    y_field_type = self.comboBoxFieldTypeX.currentText()
                    y_field = self.comboBoxFieldX.currentText()

                    x_field_type = self.comboBoxFieldTypeY.currentText()
                    x_field = self.comboBoxFieldY.currentText()

                    self.comboBoxFieldTypeX.setCurrentText(x_field_type)
                    self.comboBoxFieldX.setCurrentText(x_field)

                    self.comboBoxFieldTypeY.setCurrentText(y_field_type)
                    self.comboBoxFieldY.setCurrentText(y_field)
            case _:
                return

        # trigger update to plot
        self.plot_style.schedule_update()
        # self.update_all_plots()

    def update_aspect_ratio_controls(self):
        """Updates aspect ratio controls when ``MainWindow.toolButtonSwapResolution`` is clicked.

        Swaps ``lineEditDX`` and ``lineEditDY``
        """ 
        self.lineEditDX.value = self.data[self.app_data.sample_id].dx
        self.lineEditDY.value = self.data[self.app_data.sample_id].dy

        array_size = self.data[self.app_data.sample_id].array_size
        self.lineEditResolutionNx.value = array_size[1]
        self.lineEditResolutionNy.value = array_size[0]

        # trigger update to plot
        self.plot_style.schedule_update()

    def update_norm(self, norm, field=None):

        self.data[self.app_data.sample_id].update_norm(norm=norm, field=field)

        # trigger update to plot
        self.plot_style.schedule_update()

    def update_fields(self, sample_id, plot_type, field_type, field,  plot=False):
        # updates comboBoxPlotType,comboBoxColorByField and comboBoxColorField comboboxes using tree, branch and leaf
        if sample_id == self.app_data.sample_id:
            if plot_type != self.plot_style.plot_type:
                self.comboBoxPlotType.setCurrentText(plot_type)

            if field_type != self.field_type:
                if field_type =='Calculated':  # correct name 
                    self.comboBoxColorByField.setCurrentText('Calculated')
                else:
                    self.comboBoxColorByField.setCurrentText(field_type)
                self.plot_style.color_by_field_callback() # added color by field callback to update color field

            if field != self.field:
                self.comboBoxColorField.setCurrentText(field)
                self.plot_style.color_field_callback(plot)
    
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
        self.update_ref_chem_combobox_UI(ref_index)
    
    
    # toolbar functions
    def update_ref_chem_combobox_BE(self, ref_val):
        """Changes reference computing normalized analytes

        Sets all `self.app_data.ref_chem` to a common normalizing reference.

        Parameters
        ----------
        ref_val : str
            Name of reference value from combobox/dropdown
        """
        ref_index =  self.app_data.ref_list.tolist().index(ref_val)

        if ref_index:
            self.data[self.app_data.sample_id].ref_chem = self.app_data.ref_chem

            return ref_index


    def update_ref_chem_combobox_UI(self, ref_index):
        """Changes reference computing normalized analytes

        Sets all QComboBox to a common normalizing reference.

        Parameters
        ----------
        ref_index : int
            Index of reference value from combobox/dropdown
        """
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

    def update_invalid_data_labels(self):
        """Updates flags on statusbar indicating negative/zero and nan values within the processed_data_frame"""        

        data = self.data[self.app_data.sample_id].processed_data

        columns = data.match_attributes({'data_type': 'Analyte', 'use': True}) + data.match_attributes({'data_type': 'Ratio', 'use': True})
        negative_count = any(data[columns] <= 0)
        nan_count = any(np.isnan(data[columns]))
        
        self.labelInvalidValues.setText(f"Negative/zeros: {negative_count}, NaNs: {nan_count}")


    def auto_scale(self,update = False):
        """Auto-scales pixel values in map

        Executes on ``MainWindow.toolButtonAutoScale`` click.

        Outliers can make it difficult to view the variations of values within a map.
        This is a larger problem for linear scales, but can happen when log-scaled. Auto-
        scaling the data clips the values at a lower and upper bound.  Auto-scaling may be
        acceptable as minerals that were not specifically calibrated can have erroneously
        high or low (even negative) values.

        Parameters
        ----------
        update : bool
            Update auto scale parameters, by default, False
        """
        sample_id = self.plot_info['sample_id']
        field = self.plot_info['field']
        if '/' in field:
            analyte_1, analyte_2 = field.split(' / ')
        else:
            analyte_1 = field
            analyte_2 = None



        lb = self.lineEditLowerQuantile.value
        ub = self.lineEditUpperQuantile.value
        d_lb = self.lineEditDifferenceLowerQuantile.value
        d_ub = self.lineEditDifferenceUpperQuantile.value
        auto_scale = self.toolButtonAutoScale.isChecked()

        if auto_scale and not update:
            #reset to default auto scale values
            lb = 0.05
            ub = 99.5
            d_lb = 99
            d_ub = 99

            self.lineEditLowerQuantile.value = lb
            self.lineEditUpperQuantile.value = ub
            self.lineEditDifferenceLowerQuantile.value = d_lb
            self.lineEditDifferenceUpperQuantile.value = d_ub
            self.lineEditDifferenceLowerQuantile.setEnabled(True)
            self.lineEditDifferenceUpperQuantile.setEnabled(True)

        elif not auto_scale and not update:
            # show unbounded plot when auto scale switched off
            lb = 0
            ub = 100
            self.lineEditLowerQuantile.value = lb
            self.lineEditUpperQuantile.value = ub
            self.lineEditDifferenceLowerQuantile.setEnabled(False)
            self.lineEditDifferenceUpperQuantile.setEnabled(False)

        # if update is true
        if analyte_1 and not analyte_2:
            if self.checkBoxApplyAll.isChecked():
                # Apply to all analytes in sample
                columns = self.data[sample_id].processed_data.columns

                # clear existing plot info from tree to ensure saved plots using most recent data
                for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                    self.plot_tree.clear_tree_data(tree)
            else:
                columns = analyte_1

            # update column attributes
            self.data[sample_id].processed_data.set_attribute(columns, 'auto_scale', auto_scale)
            self.data[sample_id].processed_data.set_attribute(columns, 'upper_bound', ub)
            self.data[sample_id].processed_data.set_attribute(columns, 'lower_bound', lb)
            self.data[sample_id].processed_data.set_attribute(columns, 'diff_upper_bound', d_ub)
            self.data[sample_id].processed_data.set_attribute(columns, 'diff_lower_bound', d_lb)
            self.data[sample_id].processed_data.set_attribute(columns, 'negative_method', self.comboBoxNegativeMethod.currentText())

            # update data with new auto-scale/negative handling
            self.prep_data(sample_id)
            self.update_invalid_data_labels()

        else:
            if self.checkBoxApplyAll.isChecked():
                # Apply to all ratios in sample
                self.data[sample_id]['ratio_info']['auto_scale'] = auto_scale
                self.data[sample_id]['ratio_info']['upper_bound']= ub
                self.data[sample_id]['ratio_info']['lower_bound'] = lb
                self.data[sample_id]['ratio_info']['d_l_bound'] = d_lb
                self.data[sample_id]['ratio_info']['d_u_bound'] = d_ub
                # clear existing plot info from tree to ensure saved plots using most recent data
                for tree in ['Ratio', 'Ratio (normalized)']:
                    self.plot_tree.clear_tree_data(tree)
                self.prep_data(sample_id)
                self.update_invalid_data_labels()
            else:
                self.data[sample_id]['ratio_info'].loc[ (self.data[sample_id]['ratio_info']['analyte_1']==analyte_1)
                                            & (self.data[sample_id]['ratio_info']['analyte_2']==analyte_2),'auto_scale']  = auto_scale
                self.data[sample_id]['ratio_info'].loc[ (self.data[sample_id]['ratio_info']['analyte_1']==analyte_1)
                                            & (self.data[sample_id]['ratio_info']['analyte_2']==analyte_2),
                                            ['upper_bound','lower_bound','d_l_bound', 'd_u_bound']] = [ub,lb,d_lb, d_ub]
                self.prep_data(sample_id, analyte_1,analyte_2)
                self.update_invalid_data_labels()
        
        if hasattr(self,"mask_dock"):
            self.mask_dock.filter_tab.update_filter_values()

        # trigger update to plot
        self.plot_style.schedule_update()
        #self.show()
        
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
        #self.plot_widget_dict[selected_plot_name] = widget
        #self.add_remove(selected_plot_name)
        self.comboBoxPlots.clear()
        self.comboBoxPlots.addItems(self.multi_view_index)
    

    # -------------------------------
    # Crop functions - also see CropTool class below
    # -------------------------------
    def reset_to_full_view(self):
        """Reset the map to full view (i.e., remove crop)

        Executes on ``MainWindow.actionFullMap`` is clicked.
        """

        sample_id = self.app_data.sample_id
        #set original bounds
        
        #remove crop overlays
        self.crop_tool.remove_overlays()

        self.data[sample_id].reset_crop()
        
        # reapply existing filters
        if self.actionFilterToggle.isChecked():
            self.apply_field_filters(update_plot=False)
            # should look for filters built on computed fields and remove them
        if self.actionPolygonMask.isChecked():
            self.apply_polygon_mask(update_plot=False)

        # reset cluster mask (no valid clustering exists)
        self.actionClusterMask.setEnabled(False)
        self.actionClusterMask.setChecked(False)
        self.data[sample_id].cluster_mask = np.ones_like(self.data[sample_id].mask, dtype=bool)

        self.apply_filters(fullmap=False)

        self.parent.data[self.sample_id].crop = False

    def apply_crop(self):
        
        sample_id = self.plot_info['sample_id']
        data = self.data[sample_id]

        field_type = self.field_type
        field = self.field
        current_plot_df = self.data[self.app_data.sample_id].get_map_data(field, field_type)
        
        data.mask = data.mask[data.crop_mask]
        data.polygon_mask = data.polygon_mask[data.crop_mask]
        data.filter_mask = data.filter_mask[data.crop_mask]
        data.prep_data()
        self.update_invalid_data_labels()

        # replot after cropping 
        self.plot_map_pg(sample_id, field_type, field)
        
        self.actionCrop.setChecked(False)
        data.crop = True

        # clear existing plot info from tree to ensure plot is using most recent data
        for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
            self.clear_tree_data(tree)


    # -------------------------------
    # Filter functions
    # -------------------------------
    def apply_filters(self, fullmap=False):
        """Applies filter to map data

        Applies user specified data filters to mask data for analysis and calls ``MainWindow.update_SV`` to update the current figure.
        Updates mask for the current sample whenever the crop (axis), filter, polygon, or cluster mask changes.
        Updates figure if the *Single View* canvas is active.

        Parameters
        ----------
        fullmap : bool, optional
            If ``True``, filters are ignored, otherwise the map is filtered, by default ``False``
        """
        #reset all masks in current sample id
        sample_id = self.app_data.sample_id

        # remove all masks
        if fullmap:
            #user clicked on Map viewable
            self.actionFilterToggle.setChecked(False)
            self.actionPolygonMask.setChecked(False)
            self.actionClusterMask.setChecked(False)

            self.actionClearFilters.setEnabled(False)
            self.actionFilterToggle.setEnabled(False)
            self.actionPolygonMask.setEnabled(False)
            self.actionClusterMask.setEnabled(False)

            self.data[sample_id].mask = np.ones_like(self.data[sample_id].mask, dtype=bool)
            return

        # apply interval filters
        if self.actionFilterToggle.isChecked():
            filter_mask = self.data[sample_id].filter_mask
        else:
            filter_mask = np.ones_like( self.data[sample_id].mask, dtype=bool)

        # apply polygon filters
        if self.actionPolygonMask.isChecked():
            polygon_mask = self.data[sample_id].polygon_mask
        else:
            polygon_mask = np.ones_like( self.data[sample_id].mask, dtype=bool)

        # apply cluster mask
        if self.actionClusterMask.isChecked():
            # apply map mask
            cluster_mask = self.data[sample_id].cluster_mask
        else:
            cluster_mask = np.ones_like( self.data[sample_id].mask, dtype=bool)

        self.data[sample_id].mask = filter_mask & polygon_mask & cluster_mask

        # if single view is active
        if self.canvasWindow.currentIndex() == self.canvas_tab['sv']:
            # trigger update to plot
            self.plot_style.schedule_update()

    # Field filter functions
    # -------------------------------
    def apply_field_filters(self, update_plot=True):
        """Creates the field filter for masking data

        Updates ``MainWindow.data[sample_id].filter_mask`` and if ``update_plot==True``, updates ``MainWindow.data[sample_id].mask``.

        Parameters
        ----------
        update_plot : bool, optional
            If true, calls ``MainWindow.apply_filters`` which also calls ``MainWindow.update_SV``, by default True
        """        
        sample_id = self.app_data.sample_id

        # create array of all true
        self.data[sample_id].filter_mask = np.ones_like(self.data[sample_id].mask, dtype=bool)

        # remove all masks
        self.actionClearFilters.setEnabled(True)
        self.actionFilterToggle.setEnabled(True)
        self.actionFilterToggle.setChecked(True)

        # apply interval filters
        #print(self.data[sample_id].filter_df)
        self.data[self.app_data.sample_id].apply_field_filters()

        if update_plot:
            self.apply_filters(fullmap=False)

    # Polygon mask functions
    # -------------------------------
    def apply_polygon_mask(self, update_plot=True):
        """Creates the polygon mask for masking data

        Updates ``MainWindow.data[sample_id].polygon_mask`` and if ``update_plot==True``, updates ``MainWindow.data[sample_id].mask``.

        Parameters
        ----------
        update_plot : bool, optional
            If true, calls ``MainWindow.apply_filters`` which also calls ``MainWindow.update_SV``, by default True
        """        
        sample_id = self.app_data.sample_id

        # create array of all true
        self.data[sample_id].polygon_mask = np.ones_like(self.data[sample_id].mask, dtype=bool)

        # remove all masks
        self.actionClearFilters.setEnabled(True)
        self.actionPolygonMask.setEnabled(True)
        self.actionPolygonMask.setChecked(True)

        # apply polygon mask
        # Iterate through each polygon in self.polygons[self.main_window.sample_id]
        for row in range(self.tableWidgetPolyPoints.rowCount()):
            #check if checkbox is checked
            checkBox = self.tableWidgetPolyPoints.cellWidget(row, 4)

            if checkBox.isChecked():
                pid = int(self.tableWidgetPolyPoints.item(row,0).text())

                polygon_points = self.polygon.polygons[sample_id][pid].points
                polygon_points = [(x,y) for x,y,_ in polygon_points]

                # Convert the list of (x, y) tuples to a list of points acceptable by Path
                path = Path(polygon_points)

                # Create a grid of points covering the entire array
                # x, y = np.meshgrid(np.arange(self.array.shape[1]), np.arange(self.array.shape[0]))

                points = pd.concat([self.data[sample_id].processed_data['X'], self.data[sample_id].processed_data['Y']] , axis=1).values
                # Use the path to determine which points are inside the polygon
                inside_polygon = path.contains_points(points)

                # Reshape the result back to the shape of self.array
                inside_polygon_mask = np.array(inside_polygon).reshape(self.data[self.app_data.sample_id].array_size, order =  'C')
                inside_polygon = inside_polygon_mask.flatten('F')
                # Update the polygon mask - include points that are inside this polygon
                self.data[sample_id].polygon_mask &= inside_polygon

                #clear existing polygon lines
                #self.polygon.clear_lines()

        if update_plot:
            self.apply_filters(fullmap=False)

    # Cluster mask functions
    # -------------------------------
    def apply_cluster_mask(self, inverse=False, update_plot=True):
        """Creates a mask from selected clusters

        Uses selected clusters in ``MainWindow.tableWidgetViewGroups`` to create a mask (or inverse mask).  Masking is controlled
        clicking either ``MainWindow.toolButtonGroupMask`` or ``MainWindow.toolButtonGroupMaskInverse``.  The masking can be turned
        on or off by changing the checked state of ``MainWindow.actionClusterMask`` on the *Left Toolbox \\ Filter Page*.

        Updates ``MainWindow.data[sample_id].cluster_mask`` and if ``update_plot==True``, updates ``MainWindow.data[sample_id].mask``.

        Parameters
        ----------
        inverse : bool, optional
            Inverts selected clusters to define the mask when ``MainWindow.toolButtonGroupMaskInverse`` is clicked, otherwise
            the selected clusers are used to define the mask when ``MainWindow.toolButtonGroupMask`` is clicked, by default False
        update_plot : bool, optional
            If true, calls ``MainWindow.apply_filters`` which also calls ``MainWindow.update_SV``, by default True
        """
        sample_id = self.app_data.sample_id

        method = self.app_data.cluster_dict['active method']
        selected_clusters = self.app_data.cluster_dict[method]['selected_clusters']

        # Invert list of selected clusters
        if not inverse:
            selected_clusters = [cluster_idx for cluster_idx in range(self.app_data.cluster_dict[method]['n_clusters']) if cluster_idx not in selected_clusters]

        # create boolean array with selected_clusters == True
        cluster_group = self.data[sample_id].processed_data.loc[:,method]
        ind = np.isin(cluster_group, selected_clusters)
        self.data[sample_id].cluster_mask = ind

        self.actionClearFilters.setEnabled(True)
        self.actionClusterMask.setEnabled(True)
        self.actionClusterMask.setChecked(True)

        self.update_cluster_flag = True

        if update_plot:
            self.apply_filters(fullmap=False)

    # This is not currently used by anything as far as I can tell.
    # def remove_widgets_from_layout(self, layout, object_names_to_remove):
    #     """
    #     Remove plot widgets from the provided layout based on their objectName properties.

    #     Parameters
    #     ----------
    #     layout : Qlayout
    #         Layout that object is removed from.
    #     object_names_to_remove : any
    #         Names of objects to remove.
    #     """
    #     for i in reversed(range(layout.count())):  # Reverse to avoid skipping due to layout change
    #         item = layout.itemAt(i)
    #         widget = item.widget()
    #         if widget and widget.objectName() in object_names_to_remove:
    #             widget.setParent(None)
    #             widget.deleteLater()
    #         # Handle child layouts
    #         elif hasattr(item, 'layout') and item.layout():
    #             child_layout = item.layout()
    #             if child_layout.objectName() in object_names_to_remove:
    #                 # Remove all widgets from the child layout
    #                 while child_layout.count():
    #                     child_item = child_layout.takeAt(0)
    #                     if child_item.widget():
    #                         child_item.widget().setParent(None)
    #                         child_item.widget().deleteLater()
    #                 # Now remove the layout itself
    #                 layout.removeItem(child_layout)
    #                 del child_layout

    #     layout.update()


    # -------------------------------
    # Mouse/Plot interactivity Events
    # -------------------------------
    def mouse_moved_pg(self,event,plot):
        pos_view = plot.vb.mapSceneToView(event)  # This is in view coordinates
        pos_scene = plot.vb.mapViewToScene(pos_view)  # Map from view to scene coordinates
        any_plot_hovered = False
        for (field, view), (_, p, array) in self.lasermaps.items():
            # print(p.sceneBoundingRect(), pos)
            if p.sceneBoundingRect().contains(pos_scene) and view == self.canvasWindow.currentIndex() and not self.toolButtonPan.isChecked() and not self.toolButtonZoom.isChecked() :

                # mouse_point = p.vb.mapSceneToView(pos)
                mouse_point = pos_view
                x, y = mouse_point.x(), mouse_point.y()

                x_i = round(x*array.shape[1]/self.data[self.app_data.sample_id].x_range)
                y_i = round(y*array.shape[0]/self.data[self.app_data.sample_id].y_range)

                # if hover within lasermap array
                if 0 <= x_i < array.shape[1] and 0 <= y_i < array.shape[0] :
                    if not self.default_cursor and not self.actionCrop.isChecked():
                        QApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)
                        self.default_cursor = True
                    any_plot_hovered = True
                    value = array[y_i, x_i]  # assuming self.array is numpy self.array

                    if self.canvasWindow.currentIndex() == self.canvas_tab['sv']:
                        if self.toolButtonPolyCreate.isChecked() or (self.toolButtonPolyMovePoint.isChecked() and self.point_selected):
                            # Update the position of the zoom view
                            self.update_zoom_view_position(x, y)
                            self.zoomViewBox.show()
                            self.polygon.show_polygon_lines(x,y)
                        # elif self.actionCrop.isChecked() and self.crop_tool.start_pos:
                        #     self.crop_tool.expand_rect(pos_view)
                        else:
                            # hide zoom view
                            self.zoomViewBox.hide()

                        self.labelSVInfoX.setText('X: '+str(round(x)))
                        self.labelSVInfoY.setText('Y: '+str(round(y)))
                        self.labelSVInfoValue.setText(f"V: {round(value,2)} {self.preferences['Units']['Concentration']}")
                    else: #multi-view
                        self.labelMVInfoX.setText('X: '+str(round(x)))
                        self.labelMVInfoY.setText('Y: '+str(round(y)))

                    for (field, view), (target, _,array) in self.lasermaps.items():
                        if not self.actionCrop.isChecked():
                            target.setPos(mouse_point)
                            target.show()
                            value = array[y_i, x_i]
                            if field in self.multiview_info_label:
                                self.multiview_info_label[field][1].setText('v: '+str(round(value,2)))
                # break
        if not any_plot_hovered and not self.actionCrop.isChecked():
            QApplication.restoreOverrideCursor()
            self.default_cursor = False
            for target, _, _ in self.lasermaps.values():
                target.hide() # Hide crosshairs if no plot is hovered
            # hide zoom view
            self.zoomViewBox.hide()

    def plot_clicked(self, event,array,field, plot,radius=5):

        # get click location
        click_pos = plot.vb.mapSceneToView(event.scenePos())
        x, y = click_pos.x(), click_pos.y()
        view = self.canvasWindow.currentIndex() #view
        # Convert the click position to plot coordinates
        self.array_x = array.shape[1]
        self.array_y = array.shape[0]
        x_i = round(x*self.array_x/self.data[self.app_data.sample_id].x_range)
        y_i = round(y*self.array_y/self.data[self.app_data.sample_id].y_range)

        # Ensure indices are within plot bounds
        if not(0 <= x_i < self.array_x) or not(0 <= y_i < self.array_y):
            #do nothing
            return

        # elif self.actionCrop.isChecked():
        #     self.crop_tool.create_rect(event, click_pos)
        # if event.button() == Qt.LeftButton and self.main_window.pushButtonStartProfile.isChecked():
       #apply profiles
        elif self.toolButtonPlotProfile.isChecked() or self.toolButtonPointMove.isChecked():
            self.profile_dock.profiling.plot_profile_scatter(event, field,view, plot, x, y,x_i, y_i)
        #create polygons
        elif self.toolButtonPolyCreate.isChecked() or self.toolButtonPolyMovePoint.isChecked() or self.toolButtonPolyAddPoint.isChecked() or self.toolButtonPolyRemovePoint.isChecked():
            self.polygon.plot_polygon_scatter(event, field, x, y,x_i, y_i)

        #apply crop
        elif self.actionCrop.isChecked() and event.button() == Qt.RightButton:
            self.crop_tool.apply_crop()

    def plot_laser_map_cont(self,layout,array,img,p1,cm, view):
        # Single views (add histogram)
        if (self.canvasWindow.currentIndex() == self.canvas_tab['sv']) and (view == self.canvasWindow.currentIndex()):
            # Try to remove the colorbar just in case it was added somehow
            # for i in reversed(range(p1.layout.count())):  # Reverse to avoid skipping due to layout change
            #     item = p1.layout.itemAt(i)
            #     if isinstance(item, ColorBarItem):
            #         p1.layout.removeAt(i)
            # Create the histogram item

            ## histogram - removed for now as is not working as expected
            # histogram = HistogramLUTWidget( orientation='horizontal')
            # histogram.setObjectName('histogram')
            # histogram.gradient.setColorMap(cm)
            # histogram.setImageItem(img)
            # histogram.setBackground('w')
            # layout.addWidget(histogram, 3, 0,  1, 2)
            ## end removal
            pass

        else:
            # multi view (add colorbar)
            object_names_to_remove = ['histogram', 'pushButtonResetZoom', 'pushButtonResetPlot', 'buttons']
            # self.remove_widgets_from_layout(layout, object_names_to_remove)
            # plot = glw.getItem(0, 0)
            cbar = ColorBarItem(orientation = 'h',colorMap = cm)
            cbar.setObjectName('colorbar')
            cbar.setImageItem(img, insert_in=p1)
            cbar.setLevels([np.nanmin(array), np.nanmax(array)])

    def init_zoom_view(self):
        # Set the initial zoom level
        self.zoomLevel = 0.02  # Adjust as needed for initial zoom level
        # Create a ViewBox for the zoomed view
        self.zoomViewBox = ViewBox(border={'color': 'w', 'width': 1})
        self.zoomImg = ImageItem()
        self.zoomViewBox.addItem(self.zoomImg)
        self.zoomViewBox.setAspectLocked(True)
        self.zoomViewBox.invertY(True)
        # Add the zoom ViewBox as an item to the main plot (self.plot is your primary plot object)
        self.plot.addItem(self.zoomViewBox, ignoreBounds=True)

        # Configure initial size and position (you'll update this dynamically later)
        self.zoomViewBox.setFixedWidth(400)  # Width of the zoom box in pixels
        self.zoomViewBox.setFixedHeight(400)  # Height of the zoom box in pixels

        # Optionally, set up a crosshair or marker in the zoom window
        self.zoomTarget = TargetItem(symbol='+', size = 5)
        self.zoomViewBox.addItem(self.zoomTarget)
        self.zoomTarget.hide()  # Initially hidden
        self.zoomViewBox.hide()

        # self.update_zoom_view_position(0, 0, array)  # Initial position

    def update_zoom_view_position(self, x, y):

        # Assuming you have a method like this to update the zoom view
        # Calculate the new position for the zoom view
        xOffset = 50  # Horizontal offset from cursor to avoid overlap
        yOffset = 100  # Vertical offset from cursor to display below it

        # Adjust position to ensure the zoom view remains within the plot bounds
        x_pos = min(max(x + xOffset, 0), self.plot.viewRect().width() - self.zoomViewBox.width())
        y_pos = min(max(y + yOffset, 0), self.plot.viewRect().height() - self.zoomViewBox.height())

        x_range = self.data[self.app_data.sample_id].x_range
        y_range = self.data[self.app_data.sample_id].y_range

        # Update the position of the zoom view
        self.zoomViewBox.setGeometry(x_pos, y_pos, self.zoomViewBox.width(), self.zoomViewBox.height())

        # Calculate the region to zoom in on
        zoomRect = QRectF(x - x_range * self.zoomLevel,
                y - y_range * self.zoomLevel,
                x_range * self.zoomLevel * 2,
                y_range * self.zoomLevel * 2)

        # Update the zoom view's displayed region
        # self.zoomViewBox.setRange(rect=zoomRect, padding=0)
        if self.mask_dock.polygon_tab.action_edge_detect.isChecked():
            self.zoomImg.setImage(image=self.noise_reduction.edge_array)  # user edge_array too zoom with edge_det
        else:
            self.zoomImg.setImage(image=self.array)  # Make sure this uses the current image data

        self.zoomImg.setRect(0,0,x_range,y_range)
        self.zoomViewBox.setRange(zoomRect) # Set the zoom area in the image
        self.zoomImg.setColorMap(colormap.get(self.plot_style.cmap, source = 'matplotlib'))
        self.zoomTarget.setPos(x, y)  # Update target position
        self.zoomTarget.show()
        self.zoomViewBox.setZValue(1e10)

    def reset_zoom(self, vb,histogram):
        vb.enableAutoRange()
        histogram.autoHistogramRange()

    # -------------------------------------
    # Field type and field combobox pairs
    # -------------------------------------
    # updates field type comboboxes for analyses and plotting
    def update_field_type_combobox(self, comboBox, addNone=False, plot_type=''):
        """Updates field type combobox
        
        Used to update ``MainWindow.comboBoxHistFieldType``, ``mask_dock.filter_tab.comboBoxFilterFieldType``,
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
        if self.app_data.sample_id == '':
            return

        match plot_type.lower():
            case 'correlation' | 'histogram' | 'tec':
                if 'Cluster' in self.app_data.field_dict:
                    field_list = ['Cluster']
                else:
                    field_list = []
            case 'cluster score':
                if 'Cluster score' in self.app_data.field_dict:
                    field_list = ['Cluster score']
                else:
                    field_list = []
            case 'cluster':
                if 'Cluster' in self.app_data.field_dict:
                    field_list = ['Cluster']
                else:
                    field_list = ['Cluster score']
            case 'cluster performance':
                field_list = []
            case 'pca score':
                if 'PCA score' in self.app_data.field_dict:
                    field_list = ['PCA score']
                else:
                    field_list = []
            case 'ternary map':
                self.labelCbarDirection.setEnabled(True)
                self.comboBoxCbarDirection.setEnabled(True)
            case _:
                field_list = ['Analyte', 'Analyte (normalized)']

                # add check for ratios
                if 'Ratio' in self.app_data.field_dict:
                    field_list.append('Ratio')
                    field_list.append('Ratio (normalized)')

                if 'PCA score' in self.app_data.field_dict:
                    field_list.append('PCA score')

                if 'Cluster' in self.app_data.field_dict:
                    field_list.append('Cluster')

                if 'Cluster score' in self.app_data.field_dict:
                    field_list.append('Cluster score')

        self.plot_style.toggle_style_widgets()

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
            fields = self.app_data.field_dict[field_type.lower()]

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

        # gets the set of fields

    # -------------------------------------
    # General plot functions
    # -------------------------------------
    def update_SV(self, plot_type=None, field_type=None, field=None):
        """Updates current plot (not saved to plot selector)

        Updates the current plot (as determined by ``MainWindow.comboBoxPlotType.currentText()`` and options in ``MainWindow.toolBox.selectedIndex()``.

        save : bool, optional
            save plot to plot selector, Defaults to False.
        """
        if self.logger_options['Plotting']:
            print(f"update_SV\n  plot_type: {plot_type}\n  field_type: {field_type}\n  field: {field}")

        if self.app_data.sample_id == '' or not self.plot_style.plot_type:
            return

        if not plot_type:
            plot_type = self.plot_style.plot_type
        
        match plot_type:
            case 'field map':
                sample_id = self.app_data.sample_id
                if not field_type:
                    field_type = self.field_type
                
                if not field:
                    field = self.field

                if not field_type or not field or (field_type == '') or (field == ''):
                    return

                if (hasattr(self, "mask_dock") and self.mask_dock.polygon_tab.polygon_toggle.isChecked()) or (hasattr(self, "profile_dock") and self.profile_dock.profile_toggle.isChecked()):
                    self.plot_map_pg(sample_id, field_type, field)
                    # show created profiles if exists
                    if (hasattr(self, "profile_dock") and self.profile_dock.profile_toggle.isChecked()) and (self.app_data.sample_id in self.profile_dock.profiling.profiles):
                        self.profile_dock.profiling.clear_plot()
                        self.profile_dock.profiling.plot_existing_profile(self.plot)
                    elif (hasattr(self, "mask_dock") and self.mask_dock.polygon_tab.polygon_toggle.isChecked()) and (self.app_data.sample_id in self.polygon.polygons):  
                        self.polygon.clear_plot()
                        self.polygon.plot_existing_polygon(self.plot)
                else:
                    if self.toolBox.currentIndex() == self.left_tab['process']:
                        canvas, plot_info = plot_map_mpl(self, self.data[self.app_data.sample_id], self.app_data, self.plot_style, field_type, field, add_histogram=True)
                    else:
                        canvas, plot_info = plot_map_mpl(self, self.data[self.app_data.sample_id], self.app_data, self.plot_style, field_type, field, add_histogram=False)

                    self.add_plotwidget_to_canvas(plot_info)
                    self.plot_tree.add_tree_item(plot_info)
                
                #update UI with auto scale and neg handling parameters from 'Analyte/Ratio Info'
                self.update_spinboxes(field, field_type)
                
            case 'gradient map':
                if self.comboBoxNoiseReductionMethod.currentText() == 'none':
                    QMessageBox.warning(self,'Warning','Noise reduction must be performed before computing a gradient.')
                    return
                self.noise_reduction.noise_reduction_method_callback()
            case 'correlation':
                if self.comboBoxCorrelationMethod.currentText() == 'none':
                    return
                canvas, self.plot_info = plot_correlation(self, self.data[self.app_data.sample_id], self.app_data, self.plot_style)


            case 'TEC' | 'Radar':
                self.plot_ndim()

            case 'histogram':
                canvas, self.plot_info = plot_histogram(self, self.data[self.app_data.sample_id], self.app_data, self.plot_style)


            case 'scatter' | 'heatmap':
                if self.comboBoxFieldX.currentText() == self.comboBoxFieldY.currentText():
                    return
                canvas, self.plot_info = plot_scatter(self, data, self.app_data, self.plot_style)


            case 'variance' | 'vectors' | 'PCA scatter' | 'PCA heatmap' | 'PCA score':
                self.plot_pca()

            case 'cluster' | 'cluster score':
                self.plot_clusters()
            
            case 'cluster performance':
                self.cluster_performance_plot()

        self.clear_layout(self.widgetSingleView.layout())
        self.widgetSingleView.layout().addWidget(canvas)

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
        #print('add_plotwidget_to_canvas')

        sample_id = plot_info['sample_id']
        tree = plot_info['plot_type']
        # widget_dict = self.plot_widget_dict[tree][sample_id][plot_name]

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
            #             self.statusBar.showMessage('Plot already displayed on canvas.')
            #             return
            plot_exists = False # to check if plot is already in comboBoxMVPlots
            for index in range(self.comboBoxMVPlots.count()):
                if self.comboBoxMVPlots.itemText(index) == name:
                    plot_exists = True
                
            if plot_exists and name != self.SV_plot_name:
                #plot exists in MV and is doesnt exist in SV
                self.statusBar.showMessage('Plot already displayed on canvas.')
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
    
    def get_SV_widget(self, index):
        layout = self.widgetSingleView.layout()
        if layout is not None:
            item = layout.itemAt(index)
            if item is not None:
                return item.widget()
        return None
        
    def move_widget_between_layouts(self,source_layout, target_layout, widget, row=None, col=None):
        """
        Move a widget from source_layout to a specific position in target layout,  (row, col) if target layout is a QGridLayout.
        This function also inserts a placeholder in the original position to maintain layout integrity.
        """
        # Remove widget from source layout
        index = source_layout.indexOf(widget)

        source_layout.removeWidget(widget)
        # widget.hide()
        # If the source layout is a grid, handle placeholders differently
        if isinstance(source_layout, QGridLayout):
            placeholder = QWidget()
            placeholder.setFixedSize(widget.size())
            src_row, src_col, _, _ = source_layout.getItemPosition(index)
            source_layout.addWidget(placeholder, src_row, src_col)
        else:
            placeholder = QWidget()  # Create an empty placeholder widget for non-grid layouts
            placeholder.setFixedSize(widget.size())

            source_layout.insertWidget(0, placeholder)
            
            
        if isinstance(target_layout, QGridLayout):
            # Add widget to the target grid layout
            target_layout.addWidget(widget, row, col)
        else:
            # Add widget to the target layout
            target_layout.addWidget(widget)
        widget.show()  # Ensure the widget is visible in the new layout

    def add_plotwidget_to_tree(self):
        """Adds plot widget to plot selector

        Adds most types of plots to the plot selector.  Plot types ``Analyte``, ``Ratio`` and their normalized
        counterparts are automatically added when produced so they are skipped.
        """
        #print('add_plotwidget_to_tree')

        # if the current plot is a standard map type, then it should be added automatically
        if self.plot_info['tree'] in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
            return

        # add plot to dictionary for tree
        #self.plot_widget_dict[self.plot_info['tree']][self.app_data.sample_id][self.plot_info['plot_name']] = {'info':self.plot_info, 'view':view, 'position':None}

        # updates tree with new plot name
        self.plot_tree.add_tree_item(self.plot_info)

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

    def toggle_distance_tool(self):
        canvas = self.get_SV_widget(1)
        if not isinstance(canvas, mplc.MplCanvas):
            return

        if not self.toolButtonDistance.isChecked():
            canvas.distance_reset()
            for line, dtext in zip(reversed(canvas.saved_line), reversed(canvas.saved_dtext)):
                line.remove()
                dtext.remove()
            canvas.saved_line = []
            canvas.saved_dtext = []
            canvas.draw()

    def toolbar_plotting(self,function,view,enable=None):
        """Controls functionality of the toolbar

        Controls the viewing behavior, home view, pan, zoom, pop out, and saving.

        Parameters
        ----------
        function : str
            Button fuction
        view : _type_
            _description_
        enable : _type_
            _description_
        """
        
        match view:
            case 'SV':
                canvas = self.sv_widget
            case 'MV':
                pass
            case 'QV':
                pass

        if function == 'home':
            self.toolButtonPan.setChecked(False)
            self.toolButtonZoom.setChecked(False)
            self.toolButtonAnnotate.setChecked(False)

            if isinstance(canvas,mplc.MplCanvas):
                canvas.restore_view()

            elif isinstance(canvas,GraphicsLayoutWidget):
                canvas.getItem(0, 0).getViewBox().autoRange()

        if function == 'pan':
            self.toolButtonZoom.setChecked(False)
            self.toolButtonAnnotate.setChecked(False)

            if isinstance(canvas,mplc.MplCanvas):
                # Toggle pan mode in Matplotlib
                self.mpl_toolbar.pan()
                print(self.mpl_toolbar)
                #canvas.figure.canvas.toolbar.pan()

            elif isinstance(canvas,GraphicsLayoutWidget):
                # Enable or disable panning
                canvas.getItem(0, 0).getViewBox().setMouseMode(ViewBox.PanMode if enable else ViewBox.RectMode)

        if function == 'zoom':
            self.toolButtonPan.setChecked(False)
            self.toolButtonAnnotate.setChecked(False)

            if isinstance(canvas,mplc.MplCanvas):
                # Toggle zoom mode in Matplotlib
                self.mpl_toolbar.zoom()  # Assuming your Matplotlib canvas has a toolbar with a zoom function
            elif isinstance(canvas,GraphicsLayoutWidget):
                # Assuming pyqtgraph_widget is a GraphicsLayoutWidget or similar
                if enable:

                    canvas.getItem(0, 0).getViewBox().setMouseMode(ViewBox.RectMode)
                else:
                    canvas.getItem(0, 0).getViewBox().setMouseMode(ViewBox.PanMode)

        if function == 'annotate':
            self.toolButtonPan.setChecked(False)
            self.toolButtonZoom.setChecked(False)
        
        if function == 'distance':
            self.toolButtonPan.setChecked(False)
            self.toolButtonZoom.setChecked(False)


        if function == 'preference':
            if isinstance(canvas,mplc.MplCanvas):
                self.mpl_toolbar.edit_parameters()

            elif isinstance(canvas,GraphicsLayoutWidget):
                # Assuming it's about showing/hiding axes
                if enable:
                    canvas.showAxis('left', True)
                    canvas.showAxis('bottom', True)
                else:
                    canvas.showAxis('left', False)
                    canvas.showAxis('bottom', False)

        if function == 'axes':
            if isinstance(canvas,mplc.MplCanvas):
                self.mpl_toolbar.configure_subplots()

            elif isinstance(canvas,GraphicsLayoutWidget):
                # Assuming it's about showing/hiding axes
                if enable:
                    canvas.showAxis('left', True)
                    canvas.showAxis('bottom', True)
                else:
                    canvas.showAxis('left', False)
                    canvas.showAxis('bottom', False)
        
        if function == 'pop':
            self.toolButtonPan.setChecked(False)
            self.toolButtonZoom.setChecked(False)
            self.toolButtonAnnotate.setChecked(False)

            if isinstance(canvas,mplc.MplCanvas):
                self.pop_figure = mplc.MplDialog(self,canvas,self.plot_info['plot_name'])
                self.pop_figure.show()

            # since the canvas is moved to the dialog, the figure needs to be recreated in the main window
            # trigger update to plot        
            self.plot_style.schedule_update()

        if function == 'save':
            if isinstance(canvas,mplc.MplCanvas):
                self.mpl_toolbar.save_figure()
            elif isinstance(canvas,GraphicsLayoutWidget):
                # Save functionality for pyqtgraph
                export = exportDialog.ExportDialog(canvas.getItem(0, 0).scene())
                export.show(canvas.getItem(0, 0).getViewBox())
                export.exec()
                
    def save_plot(self, action):
        """Sorts analyte table in dialog"""        
        # get save method (Figure/Data)
        canvas = self.sv_widget #get the widget in SV layout
        method = action.text()
        if method == 'Figure':
            if isinstance(canvas, mplc.MplCanvas):
                self.mpl_toolbar.save_figure()

            elif isinstance(canvas,GraphicsLayoutWidget):
                # Save functionality for pyqtgraph
                export = exportDialog.ExportDialog(canvas.getItem(0, 0).scene())
                export.show(canvas.getItem(0, 0).getViewBox())

        elif method == 'Data':
            if self.plot_info:
                sample_id = self.plot_info['sample_id']
                plot_type = self.plot_info['plot_type']
                
                match plot_type:
                    case 'field map':
                        field_type = self.plot_info['field_type']
                        field = self.plot_info['field']
                        save_data = self.data[self.app_data.sample_id].get_map_data(field, field_type)
                    case 'gradient map':
                        field_type = self.plot_info['field_type']
                        field = self.plot_info['field']
                        save_data = self.data[self.app_data.sample_id].get_map_data(field, field_type)
                        filtered_image = self.noise_red_array
                    case 'cluster':
                        save_data= self.data[self.app_data.sample_id].processed_data[field]
                    case _:
                        save_data = self.plot_info['data']
                    
            #open dialog to get name of file
            file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv);;All Files (*)")
            if file_name:
                with open(file_name, 'wb') as file:
                    # self.save_data holds data used for current plot 
                    save_data.to_csv(file,index = False)
                
                self.statusBar.showMessage("Plot Data saved successfully")
                



    def add_colorbar(self, canvas, cax, cbartype='continuous', grouplabels=None, groupcolors=None):
        """Adds a colorbar to a MPL figure

        Parameters
        ----------
        canvas : mplc.MplCanvas
            canvas object
        cax : axes
            color axes object
        cbartype : str
            Type of colorbar, ``dicrete`` or ``continuous``, Defaults to continuous
        grouplabels : list of str, optional
            category/group labels for tick marks
        """
        #print("add_colorbar")
        # Add a colorbar
        cbar = None
        if self.plot_style.cbar_dir == 'none':
            return

        # discrete colormap - plot as a legend
        if cbartype == 'discrete':

            if grouplabels is None or groupcolors is None:
                return

            # create patches for legend items
            p = [None]*len(grouplabels)
            for i, label in enumerate(grouplabels):
                p[i] = Patch(facecolor=groupcolors[i], edgecolor='#111111', linewidth=0.5, label=label)

            if self.plot_style.cbar_dir == 'vertical':
                canvas.axes.legend(
                        handles=p,
                        handlelength=1,
                        loc='upper left',
                        bbox_to_anchor=(1.025,1),
                        fontsize=self.plot_style.font_size,
                        frameon=False,
                        ncol=1
                    )
            elif self.plot_style.cbar_dir == 'horizontal':
                canvas.axes.legend(
                        handles=p,
                        handlelength=1,
                        loc='upper center',
                        bbox_to_anchor=(0.5,-0.1),
                        fontsize=self.plot_style.font_size,
                        frameon=False,
                        ncol=3
                    )
        # continuous colormap - plot with colorbar
        else:
            if self.plot_style.cbar_dir == 'vertical':
                if self.plot_style.plot_type == 'correlation':
                    loc = 'left'
                else:
                    loc = 'right'
                cbar = canvas.fig.colorbar( cax,
                        ax=canvas.axes,
                        orientation=self.plot_style.cbar_dir,
                        location=loc,
                        shrink=0.62,
                        fraction=0.1,
                        alpha=1
                    )
            elif self.plot_style.cbar_dir == 'horizontal':
                cbar = canvas.fig.colorbar( cax,
                        ax=canvas.axes,
                        orientation=self.plot_style.cbar_dir,
                        location='bottom',
                        shrink=0.62,
                        fraction=0.1,
                        alpha=1
                    )
            else:
                # should never reach this point
                assert self.plot_style.cbar_dir == 'none', "Colorbar direction is set to none, but is trying to generate anyway."
                return

            cbar.set_label(self.plot_style.clabel, size=self.plot_style.font_size)
            cbar.ax.tick_params(labelsize=self.plot_style.font_size)
            cbar.set_alpha(1)

        # adjust tick marks if labels are given
        if cbartype == 'continuous' or grouplabels is None:
            ticks = None
        # elif cbartype == 'discrete':
        #     ticks = np.arange(0, len(grouplabels))
        #     cbar.set_ticks(ticks=ticks, labels=grouplabels, minor=False)
        #else:
        #    print('(add_colorbar) Unknown type: '+cbartype)

    

    # -------------------------------------
    # laser map functions and plotting
    # -------------------------------------
    def array_to_image(self, map_df):
        """Prepares map for display by converting to RGBA image

        Parameters
        ----------
        map_df : pandas.DataFrame
            Map data to convert

        Returns
        -------
        numpy.ndarray
            An rgba array
        """
        mask = self.data[self.app_data.sample_id].mask

        array = np.reshape(map_df['array'].values, self.data[self.app_data.sample_id].array_size, order=self.data[self.app_data.sample_id].order)

        # Step 1: Normalize your data array for colormap application
        norm = colors.Normalize(vmin=np.nanmin(array), vmax=np.nanmax(array))
        cmap = self.plot_style.get_colormap()

        # Step 2: Apply the colormap to get RGB values, then normalize to [0, 255] for QImage
        rgb_array = cmap(norm(array))[:, :, :3]  # Drop the alpha channel returned by cmap
        rgb_array = (rgb_array * 255).astype(np.uint8)

        # Step 3: Create an RGBA array where the alpha channel is based on self.data[self.app_data.sample_id].mask
        rgba_array = np.zeros((*rgb_array.shape[:2], 4), dtype=np.uint8)
        rgba_array[:, :, :3] = rgb_array  # Set RGB channels
        mask_r = np.reshape(mask, self.data[self.app_data.sample_id].array_size, order=self.data[self.app_data.sample_id].order)

        rgba_array[:, :, 3] = np.where(mask_r, 255, 100)  # Set alpha channel based on self.data[self.app_data.sample_id].mask

        return array, rgba_array


    def plot_map_pg(self, sample_id, field_type, field):
        """Create a graphic widget for plotting a map

        Create a map using pyqtgraph.

        Parameters
        ----------
        sample_id : str
            Sample identifier
        field_type : str
            Type of field for plotting
        field : str
            Field for plotting
        """        
        # ----start debugging----
        # print('[plot_map_pg] sample_id: '+sample_id+'   field_type: '+'   field: '+field)
        # ----end debugging----

        # get data for current map
        scale = self.plot_style.cscale
        map_df = self.data[self.app_data.sample_id].get_map_data(field, field_type, norm=scale)

        # store map_df to save_data if data needs to be exported
        self.save_data = map_df
        
        #Change transparency of values outside mask
        self.array, rgba_array = self.array_to_image(map_df)

        # plotWidget = QWidget()
        # layout = QVBoxLayout()
        # layout.setSpacing(0)
        # plotWidget.setLayout(layout)

        title = ''

        view = self.canvasWindow.currentIndex()
        if view == self.canvas_tab['sv']:
            title = field
        elif view == self.canvas_tab['mv']:
            title = sample_id + '_' + field
        else:
            view = self.canvas_tab['sv']
            self.canvasWindow.setCurrentIndex(view)
            title = field

        graphicWidget = GraphicsLayoutWidget(show=True)
        graphicWidget.setObjectName('LaserMap')
        graphicWidget.setBackground('w')

        # layout.addWidget(graphicWidget)

        # Create the ImageItem
        img_item = ImageItem(image=self.array, antialias=False)

        #set aspect ratio of rectangle
        img_item.setRect(self.data[self.app_data.sample_id].x.min(),
                self.data[self.app_data.sample_id].y.min(),
                self.data[self.app_data.sample_id].x_range,
                self.data[self.app_data.sample_id].y_range)

        #--- add non-interactive image with integrated color ------------------
        plotWindow = graphicWidget.addPlot(0,0,title=field.replace('_',' '))

        plotWindow.addItem(img_item)

        # turn off axes and
        plotWindow.showAxes(False, showValues=(True,False,False,True) )
        plotWindow.invertY(True)
        plotWindow.setAspectLocked()

        # Prevent zooming/panning outside the default view
        ## These cut off parts of the map when plotting.
        #plotWindow.setRange(yRange=[self.y.min(), self.y.max()])
        #plotWindow.setLimits(xMin=self.x.min(), xMax=self.x.max(), yMin=self.y.min(), yMax = self.y.max())
        #plotWindow.setLimits(maxXRange=self.data[self.app_data.sample_id].x_range, maxYRange=self.data[self.app_data.sample_id].y_range)

        #supress right click menu
        plotWindow.setMenuEnabled(False)

        # colorbar
        cmap = colormap.get(self.plot_style.cmap, source = 'matplotlib')
        #clb,cub,cscale,clabel = self.plot_style.get_axis_values(field_type,field)
        # cbar = ColorBarItem(values=(clb,cub), width=25, colorMap=cmap, label=clabel, interactive=False, limits=(clb,cub), orientation=self.plot_style.cbar_dir, pen='black')
        img_item.setLookupTable(cmap.getLookupTable())
        # graphicWidget.addItem(cbar)
        pg.setConfigOption('leftButtonPan', False)

        # ... Inside your plotting function
        target = TargetItem(symbol = '+', )
        target.setZValue(1e9)
        plotWindow.addItem(target)

        # store plots in self.lasermap to be used in profiling. self.lasermaps is a multi index dictionary with index: (field, view)
        self.lasermaps[field,view] = (target, plotWindow, self.array)

        #hide pointer
        target.hide()

        plotWindow.scene().sigMouseClicked.connect(lambda event,array=self.array, k=field, plot=plotWindow: self.plot_clicked(event,array, k, plotWindow))

        #remove previous plot in single view
        if view == 1:
            #create label with analyte name
            #create another label for value of the corresponding plot
            labelMVInfoField = QLabel()
            # labelMVInfoValueLabel.setMaximumSize(QSize(20, 16777215))
            labelMVInfoField.setObjectName("labelMVInfoField"+field)
            labelMVInfoField.setText(field)
            font = QFont()
            font.setPointSize(9)
            labelMVInfoField.setFont(font)
            verticalLayout = QVBoxLayout()
            # Naming the verticalLayout
            verticalLayout.setObjectName(field + str(view))
            verticalLayout.addWidget(labelMVInfoField)

            labelMVInfoValue = QLabel()
            labelMVInfoValue.setObjectName("labelMVInfoValue"+field)
            labelMVInfoValue.setFont(font)
            verticalLayout.addWidget(labelMVInfoValue)
            self.gridLayoutMVInfo.addLayout(verticalLayout, 0, self.gridLayoutMVInfo.count()+1, 1, 1)
            # Store the reference to verticalLayout in a dictionary
            self.multiview_info_label[field] = (labelMVInfoField, labelMVInfoValue)
        else:
            #print(self.lasermaps)
            #print(self.prev_plot)
            if self.prev_plot and (self.prev_plot,0) in self.lasermaps:
                self.plot_info['view'][0] = False
                del self.lasermaps[(self.prev_plot,0)]
            # update variables which stores current plot in SV
            self.plot = plotWindow
            self.prev_plot = field
            self.init_zoom_view()
            # uncheck edge detection
            self.mask_dock.polygon_tab.action_edge_detect.setChecked(False)


        # Create a SignalProxy to handle mouse movement events
        # Create a SignalProxy for this plot and connect it to mouseMoved

        plotWindow.scene().sigMouseMoved.connect(lambda event,plot=plotWindow: self.mouse_moved_pg(event,plot))

        #add zoom window
        plotWindow.getViewBox().autoRange()

        # add edge detection
        if self.mask_dock.polygon_tab.action_edge_detect.isChecked():
            self.noise_reduction.add_edge_detection()

        if view == 0 and self.plot_info:
            self.plot_info['view'][0] = False
            tmp = [True,False]
        else:
            tmp = [False,True]


        self.plot_info = {
            'tree': 'Analyte',
            'sample_id': sample_id,
            'plot_name': field,
            'plot_type': 'field map',
            'field_type': field_type,
            'field': field,
            'figure': graphicWidget,
            'style': self.plot_style.style_dict[self.plot_style.plot_type],
            'cluster_groups': None,
            'view': tmp,
            'position': None
            }

        #self.plot_widget_dict[self.plot_info['tree']][self.plot_info['sample_id']][self.plot_info['plot_name']] = {'info':self.plot_info, 'view':view, 'position':None}
        self.add_plotwidget_to_canvas(self.plot_info)

        #self.update_tree(plot_info=self.plot_info)
        self.plot_tree.add_tree_item(self.plot_info)

        # add small histogram
        if (self.toolBox.currentIndex() == self.left_tab['sample']) and (view == self.canvas_tab['sv']):
            plot_small_histogram(self, self.data[self.app_data.sample_id], self.app_data, self.plot_style, map_df)


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



    # -------------------------------------
    # Histogram functions and plotting
    # -------------------------------------
    def update_histogram_field_type(self):
        """"Executes when the histogram field type is changed"""
        self.app_data.hist_field_type = self.comboBoxHistFieldType.currentText()
        self.update_field_combobox(self.comboBoxHistFieldType, self.comboBoxHistField)
        #if self.plot_style.plot_type != 'histogram':
        #    self.comboBoxPlotType.setCurrentText('histogram')
        if self.plot_style.plot_type == 'field map':
            self.plot_style.color_field_type = self.comboBoxHistFieldType.currentText()

        self.histogram_update_bin_width()

        self.spinBoxFieldIndex.setMaximum(self.comboBoxHistField.count())

        self.plot_style.schedule_update()

    def update_histogram_field(self):
        """Executes when the histogram field is changed"""
        #if self.plot_style.plot_type != 'histogram':
        #    self.comboBoxPlotType.setCurrentText('histogram')
        self.app_data.hist_field = self.comboBoxHistField.currentText()

        if self.plot_style.plot_type == 'field map':
            self.plot_style.color_field = self.app_data.hist_field
        self.spinBoxFieldIndex.setValue(self.comboBoxHistField.currentIndex())

        self.update_histogram_bin_width()

        if self.plot_style.plot_type in ['field map', 'histogram']:
            self.plot_style.schedule_update()

    def update_histogram_num_bins(self):
        """Updates the bin width

        Generally called when the number of bins is changed by the user.  Updates the plot.
        """
        if not self.update_bins:
            return

        if (self.comboBoxHistFieldType.currentText() == '') or (self.comboBoxHistField.currentText() == ''):
            return

        #print('histogram_update_bin_width')
        self.update_bins = False

        # update app_data.histogram_num_bins
        self.app_data.hist_num_bins = self.spinBoxNBins.value()

        # get currently selected data
        current_plot_df = self.data[self.app_data.sample_id].get_map_data(self.comboBoxHistField.currentText(), self.comboBoxHistFieldType.currentText())

        # update bin width
        range = (np.nanmax(current_plot_df['array']) - np.nanmin(current_plot_df['array']))
        self.doubleSpinBoxBinWidth.setMinimum(int(range / self.spinBoxNBins.maximum()))
        self.doubleSpinBoxBinWidth.setMaximum(int(range / self.spinBoxNBins.minimum()))
        self.doubleSpinBoxBinWidth.setValue( int(range / self.spinBoxNBins.value()) )
        self.update_bins = True

        # update histogram
        if self.plot_style.plot_type == 'histogram':
            # trigger update to plot
            self.plot_style.schedule_update()

    def update_histogram_bin_width(self):
        """Updates the number of bins

        Generally called when the bin width is changed by the user.  Updates the plot.
        """
        if not self.update_bins:
            return
        #print('update_n_bins')
        self.update_bins = False
        self.app_data.hist_bin_width = self.doubleSpinBoxBinWidth.value()
        try:
            # get currently selected data
            map_df = self.data[self.app_data.sample_id].get_map_data(self.comboBoxHistField.currentText(), self.comboBoxHistFieldType.currentText())

            # update n bins
            self.spinBoxNBins.setValue( int((np.nanmax(map_df['array']) - np.nanmin(map_df['array'])) / self.doubleSpinBoxBinWidth.value()) )
            self.update_bins = True
        except:
            self.update_bins = True
            return

        # update histogram
        if self.plot_style.plot_type == 'histogram':
            # trigger update to plot
            self.plot_style.schedule_update()


    def number_of_clusters_callback(self):
        """Updates cluster dictionary with the new number of clusters

        Updates ``MainWindow.cluster_dict[*method*]['n_clusters'] from ``MainWindow.spinBoxNClusters``.  Updates cluster results.
        """
        self.app_data.cluster_dict[self.comboBoxClusterMethod.currentText()]['n_clusters'] = self.spinBoxNClusters.value()

        self.update_cluster_flag = True
        # trigger update to plot
        self.plot_style.schedule_update()

    def cluster_distance_callback(self):
        """Updates cluster dictionary with the new distance metric

        Updates ``MainWindow.cluster_dict[*method*]['distance'] from ``MainWindow.comboBoxClusterDistance``.  Updates cluster results.
        """
        self.app_data.cluster_dict[self.comboBoxClusterMethod.currentText()]['distance'] = self.comboBoxClusterDistance.currentText()

        self.update_cluster_flag = True
        # trigger update to plot
        self.plot_style.schedule_update()

    def cluster_exponent_callback(self):
        """Updates cluster dictionary with the new exponent

        Updates ``MainWindow.cluster_dict[*method*]['exponent'] from ``MainWindow.horizontalSliderClusterExponent``.  Updates cluster results.
        """
        self.app_data.cluster_dict[self.comboBoxClusterMethod.currentText()]['exponent'] = self.horizontalSliderClusterExponent.value()/10

        self.update_cluster_flag = True
        # trigger update to plot
        self.plot_style.schedule_update()
    
    def cluster_seed_callback(self):
        """Updates cluster dictionary with the new exponent

        Updates ``MainWindow.cluster_dict[*method*]['seed'] from ``MainWindow.lineEditSeed``.  Updates cluster results.
        """
        self.app_data.cluster_dict[self.comboBoxClusterMethod.currentText()]['exponent'] = int(self.lineEditSeed.text())

        self.update_cluster_flag = True
        # trigger update to plot
        self.plot_style.schedule_update()

    def generate_random_seed(self):
        """Generates a random seed for clustering

        Updates ``MainWindow.cluster_dict[*method*]['seed'] using a random number generator with one of 10**9 integers. 
        """        
        r = random.randint(0,1000000000)
        self.lineEditSeed.value = r
        self.app_data.cluster_dict[self.comboBoxClusterMethod.currentText()]['seed'] = r

        self.update_cluster_flag = True
        # trigger update to plot
        self.plot_style.schedule_update()

    def cluster_method_callback(self):
        """Updates clustering-related widgets

        Enables/disables widgets in *Left Toolbox \\ Clustering* page.  Updates widget values/text with values saved in ``MainWindow.cluster_dict``.
        """
        print('cluster_method_callback')
        if self.app_data.sample_id == '':
            return

        # update_clusters_ui - Enables/disables tools associated with clusters
        method = self.comboBoxClusterMethod.currentText()
        self.app_data.cluster_dict['active method'] = method

        if method not in self.data[self.app_data.sample_id].processed_data.columns:
            self.update_cluster_flag = True

        # Number of Clusters
        self.labelNClusters.setEnabled(True)
        self.spinBoxNClusters.blockSignals(True)
        self.spinBoxNClusters.setEnabled(True)
        self.spinBoxNClusters.setValue(int(self.app_data.cluster_dict[method]['n_clusters']))
        self.spinBoxNClusters.blockSignals(False)

        match method:
            case 'k-means':
                # Enable parameters relevant to KMeans
                # Exponent
                self.labelExponent.setEnabled(False)
                self.labelClusterExponent.setEnabled(False)
                self.horizontalSliderClusterExponent.setEnabled(False)

                # Distance
                self.labelClusterDistance.setEnabled(False)
                self.comboBoxClusterDistance.setEnabled(False)

                # Seed
                self.labelClusterStartingSeed.setEnabled(True)
                self.lineEditSeed.setEnabled(True)
                self.lineEditSeed.value = self.app_data.cluster_dict[method]['seed']

            case 'fuzzy c-means':
                # Enable parameters relevant to Fuzzy Clustering
                # Exponent
                self.labelExponent.setEnabled(True)
                self.labelClusterExponent.setEnabled(True)
                self.horizontalSliderClusterExponent.setEnabled(True)
                self.horizontalSliderClusterExponent.setValue(int(self.app_data.cluster_dict[method]['exponent']*10))

                # Distance
                self.labelClusterDistance.setEnabled(True)
                self.comboBoxClusterDistance.setEnabled(True)
                self.comboBoxClusterDistance.setCurrentText(self.app_data.cluster_dict[method]['distance'])

                # Seed
                self.labelClusterStartingSeed.setEnabled(True)
                self.lineEditSeed.setEnabled(True)
                self.lineEditSeed.value = self.app_data.cluster_dict[method]['seed']

        if self.update_cluster_flag:
            self.plot_style.schedule_update()

    def update_clusters(self):
        """Executed on update to cluster table.

        Updates ``MainWindow.cluster_dict`` and plot when the selected cluster have changed.
        """        
        if not self.isUpdatingTable:
            selected_clusters = []
            method = self.app_data.cluster_dict['active method']

            # get the selected clusters
            for idx in self.tableWidgetViewGroups.selectionModel().selectedRows():
                selected_clusters.append(idx.row())
            selected_clusters.sort()

            # update selected cluster list in cluster_dict
            if selected_clusters:
                if np.array_equal(self.app_data.cluster_dict[method]['selected_clusters'], selected_clusters):
                    return
                self.app_data.cluster_dict[method]['selected_clusters'] = selected_clusters
            else:
                self.app_data.cluster_dict[method]['selected_clusters'] = []

            # update plot
            if (self.plot_style.plot_type not in ['cluster', 'cluster score']) and (self.field_type == 'cluster'):
                # trigger update to plot
                self.plot_style.schedule_update()

    # 4. Davies-Bouldin Index
    # The Davies-Bouldin Index (DBI) measures the ratio of within-cluster scatter to between-cluster separation. Lower values indicate better clustering.

    # Process:
    # Run KMeans for a range of k.
    # Compute the Davies-Bouldin index for each k.
    # Select the k with the lowest DBI score.
    # Interpretation: The k with the lowest DBI score is generally the best number of clusters.
    # from sklearn.metrics import davies_bouldin_score

    # def davies_bouldin_method(data, max_clusters=10):
    #     db_scores = []
    #     k_range = range(2, max_clusters + 1)
        
    #     for k in k_range:
    #         kmeans = KMeans(n_clusters=k)
    #         kmeans.fit(data)
    #         cluster_labels = kmeans.labels_
    #         db_score = davies_bouldin_score(data, cluster_labels)
    #         db_scores.append(db_score)
        
    #     # Plot Davies-Bouldin index scores
    #     plt.figure(figsize=(8, 6))
    #     plt.plot(k_range, db_scores, 'bx-')
    #     plt.xlabel('Number of clusters (k)')
    #     plt.ylabel('Davies-Bouldin Score')
    #     plt.title('Davies-Bouldin Index Method For Optimal k')
    #     plt.show()



    def update_ndim_table(self,calling_widget):
        # Updates N-Dim table

        # :param calling_widget:
        # :type calling_widget: QWidget
        # 
        def on_use_checkbox_state_changed(row, state):
            # Update the 'use' value in the filter_df for the given row
            self.data[self.app_data.sample_id].filter_df.at[row, 'use'] = state == Qt.CheckState.Checked

        if calling_widget == 'analyteAdd':
            el_list = [self.comboBoxNDimAnalyte.currentText().lower()]
            self.comboBoxNDimAnalyteSet.setCurrentText = 'user defined'
        elif calling_widget == 'analytesetAdd':
            el_list = self.ndim_list_dict[self.comboBoxNDimAnalyteSet.currentText()]

        analytes_list = self.data[self.app_data.sample_id].processed_data.match_attribute('data_type','Analyte')

        analytes = [col for iso in el_list for col in analytes_list if re.sub(r'\d', '', col).lower() == re.sub(r'\d', '',iso).lower()]

        self.ndim_list.extend(analytes)

        for analyte in analytes:
            # Add a new row at the end of the table
            row = self.tableWidgetNDim.rowCount()
            self.tableWidgetNDim.insertRow(row)

            # Create a QCheckBox for the 'use' column
            chkBoxItem_use = QCheckBox()
            chkBoxItem_use.setCheckState(True)
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


    def group_changed(self):
        if self.app_data.sample_id == '':
            return

        # block signals
        self.tableWidgetViewGroups.blockSignals(True)
        self.spinBoxClusterGroup.blockSignals(True)

        # Clear the list widget
        self.tableWidgetViewGroups.clearContents()
        self.tableWidgetViewGroups.setHorizontalHeaderLabels(['Name','Link','Color'])

        method = self.comboBoxClusterMethod.currentText()
        if method in self.data[self.app_data.sample_id].processed_data.columns:
            if not self.data[self.app_data.sample_id].processed_data[method].empty:
                clusters = self.data[self.app_data.sample_id].processed_data[method].dropna().unique()
                clusters.sort()

                self.app_data.cluster_dict[method]['selected_clusters'] = []
                try:
                    self.app_data.cluster_dict[method].pop(99)
                except:
                    pass

                i = 0
                while True:
                    try:
                        self.app_data.cluster_dict[method].pop(i)
                        i += 1
                    except:
                        break


                # set number of rows in tableWidgetViewGroups
                # set default colors for clusters and update associated widgets
                self.spinBoxClusterGroup.setMinimum(1)
                if 99 in clusters:
                    self.tableWidgetViewGroups.setRowCount(len(clusters)-1)
                    self.spinBoxClusterGroup.setMaximum(len(clusters)-1)

                    hexcolor = self.plot_style.set_default_cluster_colors(mask=True)
                else:
                    self.tableWidgetViewGroups.setRowCount(len(clusters))
                    self.spinBoxClusterGroup.setMaximum(len(clusters))

                    hexcolor = self.plot_style.set_default_cluster_colors(mask=False)

                for c in clusters:
                    if c == 99:
                        cluster_name = 'Mask'
                        self.app_data.cluster_dict[method].update({c: {'name':cluster_name, 'link':[], 'color':hexcolor[-1]}})
                        break
                    else:
                        cluster_name = f'Cluster {c+1}'

                    # Initialize the flag
                    self.isUpdatingTable = True
                    self.tableWidgetViewGroups.setItem(c, 0, QTableWidgetItem(cluster_name))
                    self.tableWidgetViewGroups.setItem(c, 1, QTableWidgetItem(''))
                    # colors in table are set by self.plot_style.set_default_cluster_colors()
                    #self.tableWidgetViewGroups.setItem(i, 2, QTableWidgetItem(cluster_color))
                    self.tableWidgetViewGroups.selectRow(c)
                    
                    self.app_data.cluster_dict[method].update({c: {'name':cluster_name, 'link':[], 'color':hexcolor[c]}})

                if 99 in clusters:
                    self.app_data.cluster_dict[method]['selected_clusters'] = clusters[:-1]
                else:
                    self.app_data.cluster_dict[method]['selected_clusters'] = clusters
        else:
            print(f'(group_changed) Cluster method, ({method}) is not defined')

        #print(self.app_data.cluster_dict)
        self.tableWidgetViewGroups.blockSignals(False)
        self.spinBoxClusterGroup.blockSignals(False)
        self.isUpdatingTable = False

    def cluster_label_changed(self, item):
        # Initialize the flag
        if not self.isUpdatingTable: #change name only when cluster renamed
            # Get the new name and the row of the changed item
            new_name = item.text()

            row = item.row()
            if item.column() > 0:
                return

            # Extract the cluster id (assuming it's stored in the table)
            cluster_id = row

            old_name = self.app_data.cluster_dict[self.app_data.cluster_dict['active method']][cluster_id]['name']
            # Check for duplicate names
            for i in range(self.tableWidgetViewGroups.rowCount()):
                if i != row and self.tableWidgetViewGroups.item(i, 0).text() == new_name:
                    # Duplicate name found, revert to the original name and show a warning
                    item.setText(old_name)
                    QMessageBox.warning(self, "Clusters", "Duplicate name not allowed.")
                    return

            # Update self.data[self.app_data.sample_id].processed_data with the new name
            if self.app_data.cluster_dict['active method'] in self.data[self.app_data.sample_id].processed_data.columns:
                # Find the rows where the value matches cluster_id
                rows_to_update = self.data[self.app_data.sample_id].processed_data.loc[:,self.app_data.cluster_dict['active method']] == cluster_id

                # Update these rows with the new name
                self.data[self.app_data.sample_id].processed_data.loc[rows_to_update, self.app_data.cluster_dict['active method']] = new_name

            # update current_group to reflect the new cluster name
            self.app_data.cluster_dict[self.app_data.cluster_dict['active method']][cluster_id]['name'] = new_name

            # update plot with new cluster name
            # trigger update to plot
            self.plot_style.schedule_update()

    def toggle_color_widgets(self, switch):
        """Toggles enabled state of color related widgets

        Parameters
        ----------
        switch : bool
            Toggles enabled state of color widgets
        """
        if switch:
            self.comboBoxColorByField.setEnabled(True)
            self.comboBoxColorField.setEnabled(True)
            self.comboBoxFieldColormap.setEnabled(True)
            self.checkBoxReverseColormap.setEnabled(True)
            self.comboBoxCbarDirection.setEnabled(True)
            self.lineEditCbarLabel.setEnabled(True)
            self.lineEditColorLB.setEnabled(True)
            self.lineEditColorUB.setEnabled(True)
            self.comboBoxColorScale.setEnabled(True)
        else:
            self.comboBoxColorByField.setEnabled(False)
            self.comboBoxColorField.setEnabled(False)
            self.comboBoxFieldColormap.setEnabled(False)
            self.comboBoxCbarDirection.setEnabled(False)
            self.lineEditCbarLabel.setEnabled(False)
            self.lineEditColorLB.setEnabled(False)
            self.lineEditColorUB.setEnabled(False)
            self.comboBoxColorScale.setEnabled(False)

        self.labelColorByField.setEnabled(self.comboBoxColorByField.isEnabled())
        self.labelColorField.setEnabled(self.comboBoxColorField.isEnabled())
        self.labelFieldColormap.setEnabled(self.comboBoxFieldColormap.isEnabled())
        self.labelReverseColormap.setEnabled(self.checkBoxReverseColormap.isEnabled())
        self.labelCbarDirection.setEnabled(self.comboBoxCbarDirection.isEnabled())
        self.labelCbarLabel.setEnabled(self.lineEditCbarLabel.isEnabled())
        self.labelColorBounds.setEnabled(self.lineEditColorLB.isEnabled())
        self.labelColorScale.setEnabled(self.comboBoxColorScale.isEnabled())


    # updates all field type and field comboboxes
    def update_all_field_comboboxes(self):
        """Updates all field type and field comboBoxes"""
        # histograms
        self.update_field_type_combobox(self.comboBoxHistFieldType)
        self.update_field_combobox(self.comboBoxHistFieldType, self.comboBoxHistField)

        # filters
        if hasattr(self, "mask_dock"):
            self.update_field_type_combobox(self.mask_dock.filter_tab.comboBoxFilterFieldType)
            self.update_field_combobox(self.mask_dock.filter_tab.comboBoxFilterFieldType, self.mask_dock.filter_tab.comboBoxFilterField)

        # scatter and heatmaps
        self.update_field_type_combobox(self.comboBoxFieldTypeX)
        self.update_field_combobox(self.comboBoxFieldTypeX, self.comboBoxFieldX)

        self.update_field_type_combobox(self.comboBoxFieldTypeY)
        self.update_field_combobox(self.comboBoxFieldTypeY, self.comboBoxFieldY)

        self.update_field_type_combobox(self.comboBoxFieldTypeZ, addNone=True)
        self.update_field_combobox(self.comboBoxFieldTypeZ, self.comboBoxFieldZ)

        # n-Dim
        self.update_field_combobox(None, self.comboBoxNDimAnalyte)

        # profiles
        #self.update_field_type_combobox(self.comboBoxProfileFieldType)
        #self.update_field_combobox(self.comboBoxProfileFieldType, self.comboBoxProfileField)

        # field dialog
        if hasattr(self, 'field_dialog'):
            # field selector window
            self.update_field_type_combobox(self.field_dialog.comboBoxFieldType)
            self.update_field_combobox(self.field_dialog.comboBoxFieldType, self.field_dialog.comboBoxField)



        # colors
        addNone = True
        if self.plot_style.plot_type in ['field map','PCA score','cluster','cluster score']:
            addNone = False
        self.update_field_type_combobox(self.comboBoxColorByField, addNone=addNone, plot_type=self.plot_style.plot_type)
        self.update_field_combobox(self.comboBoxColorByField, self.comboBoxColorField)
        self.spinBoxColorField.setFixedWidth(20)
        self.spinBoxColorField.setMinimum(0)
        self.spinBoxColorField.setMaximum(self.comboBoxColorField.count() - 1)

        # calculator
        # self.update_field_type_combobox(self.comboBoxCalcFieldType)
        # self.update_field_combobox(self.comboBoxCalcFieldType, self.comboBoxCalcField)

        # dating
        if hasattr(self, "special_tab"):
            self.update_field_combobox(self.special_tab.comboBoxIsotopeAgeFieldType1, self.special_tab.comboBoxIsotopeAgeField1)
            self.update_field_combobox(self.special_tab.comboBoxIsotopeAgeFieldType2, self.special_tab.comboBoxIsotopeAgeField2)
            self.update_field_combobox(self.special_tab.comboBoxIsotopeAgeFieldType3, self.special_tab.comboBoxIsotopeAgeField3)


    def check_analysis_type(self):
        """Updates field type/field paired comboBoxes
        
        .. seealso::
            ``UIControls.UIFieldLogic.update_field_type_combobox`` and ``UICongrols.UIFieldLogic.update_field_combobox``
        """
        #print('check_analysis_type')
        self.check_analysis = True
        self.update_field_type_combobox(self.comboBoxColorByField, addNone=True, plot_type=self.plot_style.plot_type)
        self.update_field_combobox(self.comboBoxColorByField, self.comboBoxColorField)
        self.spinBoxColorField.setMinimum(0)
        self.spinBoxColorField.setMaximum(self.comboBoxColorField.count() - 1)
        self.spinBoxFieldIndex.setMinimum(0)
        self.spinBoxFieldIndex.setMaximum(self.comboBoxHistField.count() - 1)
        self.check_analysis = False

    def update_spinboxes(self, field, field_type='Analyte'):
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
            'Special', 'computed'. Some options require a field. Defaults to 'Analyte'
        """
        match field_type:
            case 'Analyte' | 'Analyte (normalized)':
                pass
            case 'Ratio' | 'Ratio (normalized)':
                field_1 = field.split(' / ')[0]
                field_2 = field.split(' / ')[1]
            case _:
                return

        # get Auto scale parameters and neg handling from analyte info
        data = self.data[self.app_data.sample_id].processed_data
        parameters = data.column_attributes[field]

        if self.canvasWindow.currentIndex() == self.canvas_tab['sv']:
            auto_scale = parameters['auto_scale']
            #self.spinBoxX.setValue(int(parameters['x_max']))

            self.toolButtonAutoScale.setChecked(bool(auto_scale))
            if auto_scale:
                self.lineEditDifferenceLowerQuantile.setEnabled(True)
                self.lineEditDifferenceUpperQuantile.setEnabled(True)
            
            else:
                self.lineEditDifferenceLowerQuantile.setEnabled(False)
                self.lineEditDifferenceUpperQuantile.setEnabled(False)

            # update Auto scale UI
            self.lineEditLowerQuantile.value = parameters['lower_bound']
            self.lineEditUpperQuantile.value = parameters['upper_bound']
            self.lineEditDifferenceLowerQuantile.value = parameters['diff_lower_bound']
            self.lineEditDifferenceUpperQuantile.value = parameters['diff_upper_bound']

            # Update Neg Value handling combobox 
            index = self.comboBoxNegativeMethod.findText(str(parameters['negative_method']))
            if index != -1:  # If the text is found in the combobox
                self.comboBoxNegativeMethod.setCurrentIndex(index)
            
            # Update filter UI 
            if hasattr(self, "mask_dock"):
                self.mask_dock.filter_tab.lineEditFMin.value = data[field].min()
                self.mask_dock.filter_tab.lineEditFMax.value = data[field].max()

    def update_ratio_df(self,sample_id,analyte_1, analyte_2,norm):
        parameter = self.data[sample_id]['ratio_info'].loc[(self.data[sample_id]['ratio_info']['analyte_1'] == analyte_1) & (self.data[sample_id]['ratio_info']['analyte_2'] == analyte_2)]
        if parameter.empty:
            ratio_info = {'sample_id': self.app_data.sample_id, 'analyte_1':analyte_1, 'analyte_2':analyte_2, 'norm': norm,
                            'upper_bound':np.nan,'lower_bound':np.nan,'d_bound':np.nan,'use': True,'auto_scale': True}
            self.data[sample_id]['ratio_info'].loc[len(self.data[sample_id]['ratio_info'])] = ratio_info

            self.data[self.app_data.sample_id].prep_data(sample_id, analyte_1=analyte_1, analyte_2=analyte_2)
            self.update_invalid_data_labels()

    def toggle_help_mode(self):
        """Toggles help mode

        Toggles ``MainWindow.actionHelp``, when checked, the cursor will change so indicates help tool is active.
        """        
        if self.actionHelp.isChecked():
            self.setCursor(Qt.CursorShape.WhatsThisCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)




    # -------------------------------
    # Unclassified functions
    # -------------------------------
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
                self.profile_dock.actionControlPoints.setChecked(False)
                self.actionPointMove.setChecked(False)
                self.actionPolyCreate.setChecked(False)
                self.actionPolyMovePoint.setChecked(False)
                self.actionPolyAddPoint.setChecked(False)
                self.actionPolyRemovePoint.setChecked(False)
            case 'profiling':
                self.actionCrop.setChecked(False)
                self.actionPolyCreate.setChecked(False)
                self.actionPolyMovePoint.setChecked(False)
                self.actionPolyAddPoint.setChecked(False)
                self.actionPolyRemovePoint.setChecked(False)
            case 'polygon':
                self.actionCrop.setChecked(False)
                self.profile_dock.actionControlPoints.setChecked(False)
                self.profile_dock.actionMovePoint.setChecked(False)

    
    # -------------------------------
    # Blockly functions
    # -------------------------------
    # gets the set of fields types
    def update_blockly_field_types(self):
        """Gets the fields types available and invokes workflow function
          which updates field type dropdown in blockly workflow

        Set names are consistent with QComboBox.
        """

        field_type_list = ['Analyte', 'Analyte (normalized)']
        
        data_type_dict = self.data[self.app_data.sample_id].processed_data.get_attribute_dict('data_type')

        # add check for ratios
        if 'Ratio' in data_type_dict:
            field_type_list.append('Ratio')
            field_type_list.append('Ratio (normalized)')

        if 'pca score' in data_type_dict:
            field_type_list.append('PCA score')

        if 'cluster' in data_type_dict:
            field_type_list.append('Cluster')

        if 'cluster score' in data_type_dict:
            field_type_list.append('Cluster score')
        
        if hasattr(self, "workflow"):
            self.workflow.update_field_type_list(field_type_list) #invoke workflow function to update blockly 'fieldType' dropdowns

    def update_blockly_analyte_dropdown(self,filename, unsaved_changes):
        """update analyte/ratio lists dropdown with the selected analytes/ratios

        Parameters
            ----------
            filename: str
                filename returned from analyte selection window
            saved: bool
                if the user saved was saved by user
        """

        
            
        self.workflow.refresh_analyte_dropdown(analyte_list_names)

    def update_analyte_selection_from_file(self,filename):
        filepath = os.path.join(self.BASEDIR, 'resources/analytes list', filename+'.txt')
        analyte_dict ={}
        with open(filepath, 'r') as f:
            for line in f.readlines():
                field, norm = line.replace('\n','').split(',')
                analyte_dict[field] = norm

        self.update_analyte_ratio_selection(analyte_dict)


    def update_bounds(self,ub=None,lb=None,d_ub=None,d_lb=None):
        sample_id = self.app_data.sample_id
        # Apply to all analytes in sample
        columns = self.data[self.app_data.sample_id].processed_data.columns

        # update column attributes
        if (lb and ub):
            self.data[sample_id].set_attribute(columns, 'upper_bound', ub)
            self.data[sample_id].set_attribute(columns, 'lower_bound', lb)
        else:
            self.data[sample_id].set_attribute(columns, 'diff_upper_bound', d_ub)
            self.data[sample_id].set_attribute(columns, 'diff_lower_bound', d_lb)

        # update data with new auto-scale/negative handling


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