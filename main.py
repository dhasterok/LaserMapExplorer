import sys, os, re, copy, random, darkdetect
from PyQt5.QtCore import ( Qt, QTimer, QUrl, QSize, QRectF )
from PyQt5.QtWidgets import (
    QCheckBox, QTableWidgetItem, QVBoxLayout, QGridLayout,
    QMessageBox, QHeaderView, QMenu, QFileDialog, QWidget, QToolButton,
    QDialog, QLabel, QTableWidget, QInputDialog, QAbstractItemView,
    QSplashScreen, QApplication, QMainWindow, QSizePolicy
)
from PyQt5.QtGui import ( QIntValidator, QDoubleValidator, QPixmap, QFont, QIcon )
from src.UITheme import UIThemes

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
from src.ternary_plot import ternary
from src.plot_spider import plot_spider_norm
from src.scalebar import scalebar
from src.LameIO import LameIO
import src.csvdict as csvdict
#import src.radar_factory
from src.radar import Radar
from src.ui.MainWindow import Ui_MainWindow
#from src.ui.PreferencesWindow import Ui_PreferencesWindow
from src.AnalyteSelectionWindow import AnalyteDialog
from src.TableFunctions import TableFcn as TableFcn
import src.CustomMplCanvas as mplc
from src.DataHandling import SampleObj
from src.PlotTree import PlotTree
from src.CropImage import CropTool
from src.ImageProcessing import ImageProcessing as ip
from src.StyleToolbox import Styling
from src.Profile import Profiling
from src.Polygon import PolygonManager
from src.Calculator import CustomFieldCalculator as cfc
from src.SpecialFunctions import SpecialFunctions as specfun
from src.NoteTaking import Notes
from src.Browser import Browser
from src.Workflow import Workflow
import src.QuickView as QV
from lame_helper import BASEDIR, ICONPATH, SSPATH, load_stylesheet
from src.ExtendedDF import AttributeDataFrame
import src.format as fmt
from src.colorfunc import get_hex_color, get_rgb_color
import config
from src.Logger import QTextEditLogger

# to prevent segmentation error at startup
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
setConfigOption('imageAxisOrder', 'row-major') # best performance
## sphinx-build -b html docs/source/ docs/build/html
## !pyrcc5 resources.qrc -o src/ui/resources_rc.py
## !pyuic5 designer/mainwindow.ui -o src/ui/MainWindow.py
## !pyuic5 designer/QuickViewDialog.ui -o src/ui/QuickViewDialog.py
## !pyuic5 -x designer/AnalyteSelectionDialog.ui -o src/ui/AnalyteSelectionDialog.py
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
        bottom_tab : dict
            Holds the indices for tabs in ``tabWidget``
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
            | 'plot_type' : (str) -- type of plot (e.g., ``analyte map``, ``scatter``, ``Cluster Score``)
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
        right_tab : dict
            Holds the indices for pages in ``toolBoxTreeView``
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
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.buttons_layout = None  # create a reference to your layout

        #Initialize nested data which will hold the main sets of data for analysis
        self.data = {}
        self.BASEDIR = BASEDIR
        self.clipped_ratio_data = pd.DataFrame()
        self.analyte_data = {}  #stores orginal analyte data
        self.clipped_analyte_data = {} # stores processed analyted data
        self.sample_id = ''

        self.lasermaps = {}
        self.prev_plot = ''
        self.pyqtgraph_widget = None
        self.isUpdatingTable = False
        self.cursor = False
        self.duplicate_plot_info= None
        
        self.calc_dict = {}

        self.laser_map_dict = {}

        #initialise status bar
        self.statusBar = self.statusBar()

        # Plot Selector
        #-------------------------
        self.sort_method = 'mass'

        
        # Plot Layouts
        #-------------------------
        # Central widget plot view layouts
        # single view
        layout_single_view = QVBoxLayout()
        layout_single_view.setSpacing(0)
        layout_single_view.setContentsMargins(0, 0, 0, 0)
        self.widgetSingleView.setLayout(layout_single_view)
        self.widgetSingleView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
        self.widgetMultiView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolButtonRemoveMVPlot.clicked.connect(lambda: self.remove_multi_plot(self.comboBoxPlots.currentText()))
        self.toolButtonRemoveAllMVPlots.clicked.connect(lambda: self.clear_layout(self.widgetMultiView.layout()))

        # quick view
        layout_quick_view = QGridLayout()
        layout_quick_view.setSpacing(0) # Set margins to 0 if you want to remove margins as well
        layout_quick_view.setContentsMargins(0, 0, 0, 0)
        self.widgetQuickView.setLayout(layout_quick_view)
        self.widgetQuickView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        layout_profile_view = QVBoxLayout()
        layout_profile_view.setSpacing(0)
        layout_profile_view.setContentsMargins(0, 0, 0, 0)
        self.widgetProfilePlot.setLayout(layout_profile_view)
        self.widgetProfilePlot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        #Flags to prevent plotting when widgets change
        self.point_selected = False
        self.check_analysis = True
        self.update_bins = True
        self.update_cluster_flag = True
        self.update_pca_flag = True
        self.plot_flag = True

        self.plot_info = {}

        # set locations of doc widgets
        self.setCorner(0x00002,0x1) # sets left toolbox to bottom left corner
        self.setCorner(0x00003,0x2) # sets right toolbox to bottom right corner

        # preferences
        self.default_preferences = {'Units':{'Concentration': 'ppm', 'Distance': 'µm', 'Temperature':'°C', 'Pressure':'MPa', 'Date':'Ma', 'FontSize':11, 'TickDir':'out'}}
        # in future will be set from preference ui
        self.preferences = copy.deepcopy(self.default_preferences)

        # code is more resilient if toolbox indices for each page is not hard coded
        # will need to change case text if the page text is changed
        # left toolbox
        self.left_tab = {}
        for tid in range(0,self.toolBox.count()):
            match self.toolBox.itemText(tid).lower():
                case 'samples and fields':
                    self.left_tab.update({'sample': tid})
                case 'preprocess':
                    self.left_tab.update({'process': tid})
                case 'spot data':
                    self.left_tab.update({'spot': tid})
                case 'polygons':
                    self.left_tab.update({'polygons': tid})
                case 'scatter and heatmaps':
                    self.left_tab.update({'scatter': tid})
                case 'n-dim':
                    self.left_tab.update({'ndim': tid})
                case 'dimensional reduction':
                    self.left_tab.update({'multidim': tid})
                case 'clustering':
                    self.left_tab.update({'cluster': tid})
                case 'profiling':
                    self.left_tab.update({'profile': tid})
                case 'p-t-t functions':
                    self.left_tab.update({'special': tid})

        # right toolbox
        self.right_tab = {}
        for tid in range(self.toolBoxTreeView.count()):
            match self.toolBoxTreeView.itemText(tid).lower():
                case 'plot selector':
                    self.right_tab.update({'tree': tid})
                case 'styling':
                    self.right_tab.update({'style': tid})
                case 'regression':
                    self.right_tab.update({'regression': tid})
                case 'calculator':
                    self.right_tab.update({'calculator': tid})

        self.bottom_tab = {}
        for tid in range(self.tabWidget.count()):
            match self.tabWidget.tabText(tid).lower():
                case 'notes':
                    self.bottom_tab.update({'notes': tid})
                case 'filters':
                    self.bottom_tab.update({'filter': tid})
                case 'profiles':
                    self.bottom_tab.update({'profile': tid})
                case 'plot info':
                    self.bottom_tab.update({'plotinfo': tid})
                case 'help':
                    self.bottom_tab.update({'help': tid})

        self.canvas_tab = {}
        for tid in range(self.canvasWindow.count()):
            match self.canvasWindow.tabText(tid).lower():
                case 'single view':
                    self.canvas_tab.update({'sv': tid})
                case 'multi view':
                    self.canvas_tab.update({'mv': tid})
                case 'quick view':
                    self.canvas_tab.update({'qv': tid})


        self.toolBar.insertWidget(self.actionSelectAnalytes,self.widgetSampleSelect)

        # Set initial view
        self.toolBox.setCurrentIndex(self.left_tab['sample'])
        self.tabWidget.setCurrentIndex(self.bottom_tab['notes'])
        self.toolBoxStyle.setCurrentIndex(0)
        self.toolBoxTreeView.setCurrentIndex(self.right_tab['tree'])
        self.canvasWindow.setCurrentIndex(self.canvas_tab['sv'])


        # create dictionaries for default plot styles
        #-------------------------

        self.plot_types = {self.left_tab['sample']: [0, 'analyte map', 'correlation'],
            self.left_tab['process']: [0, 'analyte map', 'gradient map', 'histogram'],
            self.left_tab['spot']: [0, 'analyte map', 'gradient map'],
            self.left_tab['polygons']: [0, 'analyte map'],
            self.left_tab['profile']: [0, 'analyte map'],
            self.left_tab['scatter']: [0, 'scatter', 'heatmap', 'ternary map'],
            self.left_tab['ndim']: [0, 'TEC', 'Radar'],
            self.left_tab['multidim']: [0, 'variance','vectors','PCA scatter','PCA heatmap','PCA score'],
            self.left_tab['cluster']: [0, 'cluster', 'cluster score', 'cluster performance'],
            self.left_tab['special']: [0,'analyte map', 'gradient map', 'cluster score', 'PCA score', 'profile']}


        # initalize self.comboBoxPlotType
        self.comboBoxPlotType.clear()
        self.comboBoxPlotType.addItems(self.plot_types[self.toolBox.currentIndex()][1:])
        self.comboBoxPlotType.setCurrentIndex(self.plot_types[self.toolBox.currentIndex()][0])
        
        # Menu and Toolbar
        #-------------------------
        self.io = LameIO(self)

        # Connect the "Open" action to a function
        self.actionQuit_LaME.triggered.connect(self.quit)

        # Intialize Tabs as not enabled
        self.SelectAnalytePage.setEnabled(False)
        self.PreprocessPage.setEnabled(False)
        self.SpotDataPage.setEnabled(False)
        self.PolygonPage.setEnabled(False)
        self.ScatterPage.setEnabled(False)
        self.NDIMPage.setEnabled(False)
        self.MultidimensionalPage.setEnabled(False)
        self.ClusteringPage.setEnabled(False)
        self.ProfilingPage.setEnabled(False)
        self.PTtPage.setEnabled(False)

        self.actionSavePlotToTree.triggered.connect(self.add_plotwidget_to_tree)
        self.actionSelectAnalytes.triggered.connect(self.open_select_analyte_dialog)
        self.actionSpotData.triggered.connect(lambda: self.open_tab('spot data'))

        self.actionFullMap.triggered.connect(self.reset_to_full_view)
        self.actionFullMap.triggered.connect(lambda: self.actionCrop.setChecked(False))
        self.actionFullMap.setEnabled(False)

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
        self.actionProfiles.triggered.connect(lambda: self.open_tab('profiles'))
        self.actionCluster.triggered.connect(lambda: self.open_tab('clustering'))
        self.actionReset.triggered.connect(lambda: self.reset_analysis())
        self.actionSwapAxes.triggered.connect(self.swap_xy)
        self.actionSwapAxes.setEnabled(False)

        self.browser = Browser(self)
        self.actionReportBug.triggered.connect(lambda: self.browser.setUrl(QUrl('https://github.com/dhasterok/LaserMapExplorer/issues')))

        # For light and dark themes, connects actionViewMode
        self.theme = UIThemes(app, self)


        # initiate Workflow 
        self.workflow = Workflow(self)

        self.plot_tree = PlotTree(self)

        #init table_fcn
        self.table_fcn = TableFcn(self)

        # Select analyte Tab
        #-------------------------
        self.ref_data = pd.read_excel(os.path.join(BASEDIR,'resources/app_data/earthref.xlsx'))
        self.ref_data = self.ref_data[self.ref_data['sigma']!=1]
        ref_list = self.ref_data['layer']+' ['+self.ref_data['model']+'] '+ self.ref_data['reference']

        self.comboBoxRefMaterial.addItems(ref_list.values)          # Select analyte Tab
        self.comboBoxRefMaterial.setCurrentIndex(0)
        self.comboBoxNDimRefMaterial.addItems(ref_list.values)      # NDim Tab
        self.comboBoxNDimRefMaterial.setCurrentIndex(0)
        self.comboBoxRefMaterial.activated.connect(lambda: self.change_ref_material(self.comboBoxRefMaterial, self.comboBoxNDimRefMaterial))
        self.comboBoxNDimRefMaterial.activated.connect(lambda: self.change_ref_material(self.comboBoxNDimRefMaterial, self.comboBoxRefMaterial))
        self.comboBoxRefMaterial.setCurrentIndex(0)
        self.ref_chem = None
        self.change_ref_material(self.comboBoxRefMaterial, self.comboBoxNDimRefMaterial)
        

        self.comboBoxCorrelationMethod.activated.connect(self.correlation_method_callback)
        self.checkBoxCorrelationSquared.stateChanged.connect(self.correlation_squared_callback)

        self.comboBoxOutlierMethod.addItems(['set quantiles','quantiles and distance', 'Chauvenet criterion', 'log(n>x) inflection'])
        self.comboBoxOutlierMethod.activated.connect(self.update_outlier_removal)

        self.comboBoxNegativeMethod.addItems(['ignore negatives', 'minimum positive', 'gradual shift', 'Yeo-Johnson transform'])
        self.comboBoxNegativeMethod.activated.connect(self.update_neg_handling)

        # Selecting analytes
        #-------------------------
        # Connect the currentIndexChanged signal of comboBoxSampleId to load_data method
        self.comboBoxSampleId.activated.connect(lambda: self.change_sample(self.comboBoxSampleId.currentIndex()))
        self.canvasWindow.currentChanged.connect(self.canvas_changed)

        #normalising
        self.comboBoxNorm.clear()
        self.comboBoxNorm.addItems(['linear','log','logit'])
        self.comboBoxNorm.activated.connect(lambda: self.update_norm(self.comboBoxNorm.currentText()))

        self.lineEditResolutionNx.precision = None
        self.lineEditResolutionNy.precision = None

        pixelwidthvalidator = QDoubleValidator()
        pixelwidthvalidator.setBottom(0.0)
        self.lineEditDX.setValidator(pixelwidthvalidator)
        self.lineEditDY.setValidator(pixelwidthvalidator)
        self.lineEditDX.editingFinished.connect(self.update_resolution)
        self.lineEditDY.editingFinished.connect(self.update_resolution)

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
        self.comboBoxHistFieldType.activated.connect(self.histogram_field_type_callback)
        self.comboBoxHistField.activated.connect(self.histogram_field_callback)
        self.spinBoxNBins.setValue(self.default_bins)
        self.spinBoxNBins.valueChanged.connect(self.histogram_update_bin_width)
        self.spinBoxBinWidth.valueChanged.connect(self.histogram_update_n_bins)
        self.toolButtonHistogramReset.clicked.connect(self.histogram_reset_bins)
        self.comboBoxHistType.activated.connect(self.update_SV)
        self.toolButtonHistogramReset.clicked.connect(self.plot_histogram)

        #uncheck crop is checked
        self.toolBox.currentChanged.connect(lambda: self.canvasWindow.setCurrentIndex(self.canvas_tab['sv']))

        # Noise reduction
        self.noise_reduction = ip(self)

        # Initiate crop tool
        self.crop_tool = CropTool(self)
        self.actionCrop.triggered.connect(self.crop_tool.init_crop)

        # Spot Data Tab
        #-------------------------
        self.spotdata = AttributeDataFrame()

        # spot table
        header = self.tableWidgetSpots.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.Stretch)
        header.setSectionResizeMode(1,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4,QHeaderView.Stretch)

        # Filter Tabs
        #-------------------------
        self.load_filter_tables()
        self.lineEditFMin.precision = 8
        self.lineEditFMin.toward = 0
        self.lineEditFMax.precision = 8
        self.lineEditFMax.toward = 1

        self.lineEditFMin.editingFinished.connect(self.callback_lineEditFMin)
        self.lineEditFMax.editingFinished.connect(self.callback_lineEditFMax)
        self.doubleSpinBoxFMinQ.valueChanged.connect(self.callback_doubleSpinBoxFMinQ)
        self.doubleSpinBoxFMaxQ.valueChanged.connect(self.callback_doubleSpinBoxFMaxQ)

        self.toolButtonAddFilter.clicked.connect(self.update_filter_table)
        self.toolButtonAddFilter.clicked.connect(lambda: self.apply_field_filters())

        self.comboBoxFilterFieldType.activated.connect(lambda: self.update_field_combobox(self.comboBoxFilterFieldType, self.comboBoxFilterField))
        self.comboBoxFilterField.currentIndexChanged.connect(self.update_filter_values)

        self.toolButtonFilterUp.clicked.connect(lambda: self.table_fcn.move_row_up(self.tableWidgetFilters))
        self.toolButtonFilterUp.clicked.connect(lambda: self.apply_field_filters(update_plot=True))
        self.toolButtonFilterDown.clicked.connect(lambda: self.table_fcn.move_row_down(self.tableWidgetFilters))
        self.toolButtonFilterDown.clicked.connect(lambda: self.apply_field_filters(update_plot=True))
        # There is currently a special function for removing rows, convert to table_fcn.delete_row
        self.toolButtonFilterRemove.clicked.connect(self.remove_selected_rows)
        self.toolButtonFilterRemove.clicked.connect(lambda: self.table_fcn.delete_row(self.tableWidgetFilters))
        self.toolButtonFilterRemove.clicked.connect(lambda: self.apply_field_filters(update_plot=True))
        self.toolButtonFilterSelectAll.clicked.connect(self.tableWidgetFilters.selectAll)

        self.toolButtonFilterSave.clicked.connect(self.save_filter_table)
        self.comboBoxFilterPresets.activated.connect(self.read_filter_table)

        # initiate Polygon class
        self.polygon = PolygonManager(self)
        self.toolButtonPolyCreate.clicked.connect(self.polygon.increment_pid)
        self.toolButtonPolyDelete.clicked.connect(lambda: self.table_fcn.delete_row(self.tableWidgetPolyPoints))


        # Scatter and Ternary Tab
        #-------------------------
        self.toolButtonTernaryMap.clicked.connect(self.plot_ternarymap)

        self.comboBoxFieldTypeX.activated.connect(lambda: self.update_field_combobox(self.comboBoxFieldTypeX, self.comboBoxFieldX))
        self.comboBoxFieldTypeY.activated.connect(lambda: self.update_field_combobox(self.comboBoxFieldTypeY, self.comboBoxFieldY))
        self.comboBoxFieldTypeZ.activated.connect(lambda: self.update_field_combobox(self.comboBoxFieldTypeZ, self.comboBoxFieldZ))


        # polygon table
        header = self.tableWidgetPolyPoints.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1,QHeaderView.Stretch)
        header.setSectionResizeMode(2,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4,QHeaderView.ResizeToContents)

        # Multidimensional Tab
        #------------------------
        self.pca_results = []
        self.spinBoxPCX.valueChanged.connect(self.plot_pca)
        self.spinBoxPCY.valueChanged.connect(self.plot_pca)

        # Clustering Tab
        #-------------------------
        # cluster dictionary
        self.cluster_dict = {
            'active method' : 'k-means',
            'k-means':{'n_clusters':5, 'seed':23, 'selected_clusters':[]},
            'fuzzy c-means':{'n_clusters':5, 'exponent':2.1, 'distance':'euclidean', 'seed':23, 'selected_clusters':[]}
        }

        # number of clusters
        self.spinBoxNClusters.valueChanged.connect(self.number_of_clusters_callback)

        # Populate the comboBoxClusterDistance with distance metrics
        # euclidean (a.k.a. L2-norm) = euclidean
        # manhattan (a.k.a. L1-norm and cityblock)= manhattan
        # mahalanobis = mahalanobis(n_components=n_pca_basis)
        # cosine = cosine_distances
        distance_metrics = ['euclidean', 'manhattan', 'mahalanobis', 'cosine']

        self.comboBoxClusterDistance.clear()
        self.comboBoxClusterDistance.addItems(distance_metrics)
        self.comboBoxClusterDistance.setCurrentIndex(0)
        self.comboBoxClusterDistance.activated.connect(self.cluster_distance_callback)

        # cluster exponent
        self.horizontalSliderClusterExponent.setMinimum(10)  # Represents 1.0 (since 10/10 = 1.0)
        self.horizontalSliderClusterExponent.setMaximum(30)  # Represents 3.0 (since 30/10 = 3.0)
        self.horizontalSliderClusterExponent.setSingleStep(1)  # Represents 0.1 (since 1/10 = 0.1)
        self.horizontalSliderClusterExponent.setTickInterval(1)
        self.horizontalSliderClusterExponent.valueChanged.connect(lambda value: self.labelClusterExponent.setText(str(value/10)))
        self.horizontalSliderClusterExponent.sliderReleased.connect(self.cluster_exponent_callback)

        # starting seed
        self.lineEditSeed.setValidator(QIntValidator(0,1000000000))
        self.lineEditSeed.editingFinished.connect(self.cluster_seed_callback)
        self.toolButtonRandomSeed.clicked.connect(self.generate_random_seed)

        # cluster method
        self.comboBoxClusterMethod.activated.connect(self.cluster_method_callback)
        self.cluster_method_callback()

        # Connect cluster method comboBox to slot
        self.comboBoxClusterMethod.currentIndexChanged.connect(self.group_changed)

        # Connect the itemChanged signal to a slot
        self.tableWidgetViewGroups.setSelectionMode(QAbstractItemView.MultiSelection)
        self.tableWidgetViewGroups.itemChanged.connect(self.cluster_label_changed)

        self.comboBoxColorField.currentText() == 'none'
        self.spinBoxColorField.lineEdit().setReadOnly(True)
        self.tableWidgetViewGroups.selectionModel().selectionChanged.connect(self.update_clusters)

        # Scatter and Ternary Tab
        #-------------------------
        self.comboBoxFieldX.activated.connect(lambda: self.plot_scatter())
        self.comboBoxFieldY.activated.connect(lambda: self.plot_scatter())
        self.comboBoxFieldZ.activated.connect(lambda: self.plot_scatter())


        # N-Dim Tab
        #-------------------------
        # get N-Dim lists
        self.ndim_list = []
        self.ndim_list_filename = 'resources/app_data/TEC_presets.csv'
        try:
            self.ndim_list_dict = csvdict.import_csv_to_dict(os.path.join(BASEDIR,self.ndim_list_filename))
        except:
            self.ndim_list_dict = {
                    'majors': ['Si','Ti','Al','Fe','Mn','Mg','Ca','Na','K','P'],
                    'full trace': ['Cs','Rb','Ba','Th','U','K','Nb','Ta','La','Ce','Pb','Mo','Pr','Sr','P','Ga','Zr','Hf','Nd','Sm','Eu','Li','Ti','Gd','Dy','Ho','Y','Er','Yb','Lu'],
                    'REE': ['La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu'],
                    'metals': ['Na','Al','Ca','Zn','Sc','Cu','Fe','Mn','V','Co','Mg','Ni','Cr']
                }
        # setup comboBoxNDIM
        self.comboBoxNDimAnalyteSet.clear()
        self.comboBoxNDimAnalyteSet.addItems(list(self.ndim_list_dict.keys()))

        #self.comboBoxNDimRefMaterial.addItems(ref_list.values) This is done with the Set analyte tab initialization above.
        self.toolButtonNDimAnalyteAdd.clicked.connect(lambda: self.update_ndim_table('analyteAdd'))
        self.toolButtonNDimAnalyteAdd.clicked.connect(self.update_SV)
        self.toolButtonNDimAnalyteSetAdd.clicked.connect(lambda: self.update_ndim_table('analytesetAdd'))
        self.toolButtonNDimAnalyteSetAdd.clicked.connect(self.update_SV)
        self.toolButtonNDimUp.clicked.connect(lambda: self.table_fcn.move_row_up(self.tableWidgetNDim))
        self.toolButtonNDimUp.clicked.connect(self.update_SV)
        self.toolButtonNDimDown.clicked.connect(lambda: self.table_fcn.move_row_down(self.tableWidgetNDim))
        self.toolButtonNDimDown.clicked.connect(self.update_SV)
        self.toolButtonNDimSelectAll.clicked.connect(self.tableWidgetNDim.selectAll)
        self.toolButtonNDimRemove.clicked.connect(lambda: self.table_fcn.delete_row(self.tableWidgetNDim))
        self.toolButtonNDimRemove.clicked.connect(self.update_SV)
        self.toolButtonNDimSaveList.clicked.connect(self.save_ndim_list)

        # N-dim table
        header = self.tableWidgetNDim.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1,QHeaderView.Stretch)

        # Profile Tab
        #-------------------------
        self.lineEditPointRadius.setValidator(QIntValidator())
        self.lineEditYThresh.setValidator(QIntValidator())
        self.profiling = Profiling(self)
        self.comboBoxProfileList.addItem('Create New Profile')
        self.comboBoxProfileList.activated.connect(lambda: self.profiling.on_profile_selected(self.comboBoxProfileList.currentText()))
        # create new profile or update existing
        self.toolButtonPlotProfile.clicked.connect(lambda: self.profiling.on_profile_selected(self.comboBoxProfileList.currentText()))

        #select entire row
        header = self.tableWidgetProfilePoints.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.Stretch)
        header.setSectionResizeMode(1,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2,QHeaderView.ResizeToContents)

        self.tableWidgetProfilePoints.setSelectionBehavior(QTableWidget.SelectRows)
        self.toolButtonPointUp.clicked.connect(lambda: self.table_fcn.move_row_up(self.tableWidgetProfilePoints))
        self.toolButtonPointDown.clicked.connect(lambda: self.table_fcn.move_row_down(self.tableWidgetProfilePoints))
        self.toolButtonPointDelete.clicked.connect(lambda: self.table_fcn.delete_row(self.tableWidgetProfilePoints))
        self.comboBoxProfileSort.currentIndexChanged.connect(self.plot_profile_and_table)
        self.toolButtonProfileInterpolate.clicked.connect(lambda: self.profiling.interpolate_points(interpolation_distance=int(self.lineEditIntDist.text()), radius= int(self.lineEditPointRadius.text())))
        # update profile plot when point type is changed
        self.comboBoxPointType.currentIndexChanged.connect(lambda: self.profiling.plot_profiles())
        # update profile plot when selected subplot is changed
        self.spinBoxProfileSelectedSubplot.valueChanged.connect(lambda: self.profiling.plot_profiles())
        # update profile plot when Num subplot is changed
        self.spinBoxProfileNumSubplots.valueChanged.connect(lambda: self.profiling.plot_profiles())
        # update profile plot when field in subplot table is changed
        self.toolButtonProfileAddField.clicked.connect(lambda: self.profiling.plot_profiles())
        
        # Connect the add and remove field buttons to methods
        self.toolButtonProfileAddField.clicked.connect(self.profiling.add_field_to_listview)
        self.toolButtonProfileRemove.clicked.connect(self.profiling.remove_field_from_listview)
        self.toolButtonProfileRemove.clicked.connect(lambda: self.profiling.plot_profiles())
        self.comboBoxProfileFieldType.activated.connect(lambda: self.update_field_combobox(self.comboBoxProfileFieldType, self.comboBoxProfileField))

        # below line is commented because plot_profiles is automatically triggered when user clicks on map once they are in profiling tab
        # self.toolButtonPlotProfile.clicked.connect(lambda:self.profiling.plot_profiles())
        self.toolButtonPointSelectAll.clicked.connect(self.tableWidgetProfilePoints.selectAll)
        # Connect toolButtonProfileEditToggle's clicked signal to toggle edit mode
        self.toolButtonProfileEditToggle.clicked.connect(self.profiling.toggle_edit_mode)

        # Connect toolButtonProfilePointToggle's clicked signal to toggle point visibility
        self.toolButtonProfilePointToggle.clicked.connect(self.profiling.toggle_point_visibility)

        # -------
        # These tools are for setting profile plot controls
        self.groupBoxProfilePlotControl.setVisible(True)
        # -------

        # Special Tab
        #------------------------
        #SV/MV tool box
        self.toolButtonPan.setCheckable(True)
        self.toolButtonPan.setCheckable(True)

        self.toolButtonZoom.setCheckable(True)
        self.toolButtonZoom.setCheckable(True)

        # Dating
        self.SpecialFunctions = specfun(parent=self)
        self.comboBoxIsotopeAgeFieldType1.activated.connect(lambda: self.update_field_combobox(self.comboBoxIsotopeAgeFieldType1, self.comboBoxIsotopeAgeField1))
        self.comboBoxIsotopeAgeFieldType2.activated.connect(lambda: self.update_field_combobox(self.comboBoxIsotopeAgeFieldType2, self.comboBoxIsotopeAgeField2))
        self.comboBoxIsotopeAgeFieldType3.activated.connect(lambda: self.update_field_combobox(self.comboBoxIsotopeAgeFieldType3, self.comboBoxIsotopeAgeField3))

        
        # Styling Tab
        #-------------------------
        self.style = Styling(self)
        self.style.load_theme_names()

        setattr(self.comboBoxMVPlots, "allItems", lambda: [self.comboBoxMVPlots.itemText(i) for i in range(self.comboBoxMVPlots.count())])

        # self.doubleSpinBoxMarkerSize.valueChanged.connect(lambda: self.plot_scatter(save=False))
        #self.comboBoxColorByField.activated.connect(lambda: self.update_field_combobox(self.comboBoxColorByField, self.comboBoxColorField))

        # cluster table
        header = self.tableWidgetViewGroups.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.Stretch)
        header.setSectionResizeMode(1,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2,QHeaderView.ResizeToContents)
        self.toolButtonGroupMask.clicked.connect(lambda: self.apply_cluster_mask(inverse=False))
        self.toolButtonGroupMaskInverse.clicked.connect(lambda: self.apply_cluster_mask(inverse=True))


        # Calculator tab
        #-------------------------
        self.calculator = cfc(parent=self) # initalize custom field calculator

        # Profile filter tab
        #-------------------------
        header = self.tableWidgetFilters.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2,QHeaderView.Stretch)
        header.setSectionResizeMode(3,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7,QHeaderView.ResizeToContents)

        # Notes tab
        #-------------------------
        self.notes = Notes(self)

        # Plot Info
        #-------------------------
        self.textEditPlotInfo.setReadOnly(True)
        
        # Browser
        #-------------------------

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
        self.actionCalculator.triggered.connect(lambda: self.toolBoxTreeView.setCurrentIndex(self.right_tab['calculator']))

        #reset check boxes to prevent incorrect behaviour during plot click
        self.toolButtonPlotProfile.clicked.connect(lambda: self.reset_checked_items('profiling'))
        self.toolButtonPointMove.clicked.connect(lambda: self.reset_checked_items('profiling'))
        self.toolButtonPolyCreate.clicked.connect(lambda: self.reset_checked_items('polygon'))
        self.toolButtonPolyMovePoint.clicked.connect(lambda: self.reset_checked_items('polygon'))
        self.toolButtonPolyAddPoint.clicked.connect(lambda: self.reset_checked_items('polygon'))
        self.toolButtonPolyRemovePoint.clicked.connect(lambda: self.reset_checked_items('polygon'))


        # Setup Help
        #-------------------------
        self.actionHelp.triggered.connect(self.toggle_help_mode)
        self.centralwidget.installEventFilter(self)
        self.canvasWindow.installEventFilter(self)
        self.dockWidgetLeftToolbox.installEventFilter(self)
        self.dockWidgetRightToolbox.installEventFilter(self)
        self.dockWidgetBottomTabs.installEventFilter(self)

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
        self.toolButtonRightDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.dockWidgetRightToolbox, button=self.toolButtonRightDock))
        self.toolButtonBottomDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.dockWidgetBottomTabs, button=self.toolButtonBottomDock))

        # Add the button to the status bar
        self.labelInvalidValues = QLabel("Negative/zeros: False, NaNs: False")
        self.statusbar.addPermanentWidget(self.labelInvalidValues)

        self.statusbar.addPermanentWidget(self.toolButtonLeftDock)
        self.statusbar.addPermanentWidget(self.toolButtonBottomDock)
        self.statusbar.addPermanentWidget(self.toolButtonRightDock)


        self.toolBox.currentChanged.connect(self.toolbox_changed)

        if config.debug:
            # Redirect sys.stdout to the QTextEdit
            sys.stdout = QTextEditLogger(self)

        # ----start debugging----
        # self.test_get_field_list()
        # ----end debugging----
    
    # -------------------------------------
    # Reset to start
    # -------------------------------------
    def reset_analysis(self, selection='full'):
        if self.sample_id == '':
            return

        messageBoxResetSample = QMessageBox()
        iconWarning = QIcon()
        iconWarning.addPixmap(QPixmap(":/resources/icons/icon-warning-64.svg"), QIcon.Normal, QIcon.Off)

        messageBoxResetSample.setWindowIcon(iconWarning)  # Set custom icon
        messageBoxResetSample.setText("Do you wish to discard all work and revert to the original data?")
        messageBoxResetSample.setWindowTitle("Reset analyses")
        messageBoxResetSample.setStandardButtons(QMessageBox.Reset | QMessageBox.Cancel)

        # Display the dialog and wait for user action
        response = messageBoxResetSample.exec_()

        if response == QMessageBox.Cancel:
            return

        if selection =='full':
            #reset self.data
            self.data = {}
            # self.plot_widget_dict = {
            #     'Analyte':{},
            #     'Histogram':{},
            #     'Correlation':{},
            #     'Multidimensional Analysis':{},
            #     'Geochemistry':{},
            #     'Calculated':{}
            # }
            self.multi_view_index = []
            self.laser_map_dict = {}
            self.multiview_info_label = {}
            self.ndim_list = []
            self.lasermaps = {}
            #self.treeModel.clear()
            self.prev_plot = ''
            self.plot_tree = PlotTree(self)
            self.change_sample(self.comboBoxSampleId.currentIndex())

            # reset styles
            self.style.reset_default_styles()

            # reset plot layouts
            self.clear_layout(self.widgetSingleView.layout())
            self.clear_layout(self.widgetMultiView.layout())
            self.clear_layout(self.widgetQuickView.layout())

            # make the first plot
            self.plot_flag = True
            # self.update_SV()
        elif selection == 'sample': #sample is changed

            #clear filter table
            self.tableWidgetFilters.clearContents()
            self.tableWidgetFilters.setRowCount(0)

            #clear profiling
            self.profiling.clear_profiles()

            #clear polygons
            self.polygon.clear_polygons()

        pass

    def toggle_dock_visibility(self, dock, button):
        if dock.isVisible():
            dock.hide()
            button.setChecked(False)
        else:
            dock.show()
            button.setChecked(True)
        
    def init_tabs(self):
        self.toolBox.setCurrentIndex(self.left_tab['sample'])
    
        self.SelectAnalytePage.setEnabled(True)
        self.PreprocessPage.setEnabled(True)
        self.SpotDataPage.setEnabled(True)
        self.PolygonPage.setEnabled(True)
        self.ScatterPage.setEnabled(True)
        self.NDIMPage.setEnabled(True)
        self.MultidimensionalPage.setEnabled(True)
        self.ClusteringPage.setEnabled(True)
        self.ProfilingPage.setEnabled(True)
        self.PTtPage.setEnabled(True)

    def change_sample(self, index):
        """Changes sample and plots first map

        Parameters
        ----------
        index: int
            index of sample name for identifying data.  The values are based on the
            comboBoxSampleID
        """
        if config.debug:
            print(f"change_sample, index: {index}")

        if self.sample_id == self.sample_ids[index]:
            # if selected sample id is same as previous
            return

        self.sample_id = self.sample_ids[index]

        ######
        # THIS DOESN'T DO ANYTHING ANYMORE, BUT WHEN A NEW SAMPLE IS LOADED, IT NEEDS TO CHECK FOR PERSISTANT FILTERS AND THEN ADD THEM TO THE NEW SAMPLEOBJ
        # initialize filter_info dataframe for storing filter properties
        # if self.filter_df is not None and not self.filter_info.empty:
        #     if any(self.filter_info['persistent']):
        #         # Keep only rows where 'persistent' is True
        #         self.filter_info = self.filter_info[self.filter_info['persistent'] == True]

        # stop autosave timer
        self.notes.save_notes_file()
        self.notes.autosaveTimer.stop()

        if self.data:
            # Create and configure the QMessageBox
            messageBoxChangeSample = QMessageBox()
            iconWarning = QIcon()
            iconWarning.addPixmap(QPixmap(":/resources/icons/icon-warning-64.svg"), QIcon.Normal, QIcon.Off)

            messageBoxChangeSample.setWindowIcon(iconWarning)  # Set custom icon
            messageBoxChangeSample.setText("Do you want to save current analysis")
            messageBoxChangeSample.setWindowTitle("Save analysis")
            messageBoxChangeSample.setStandardButtons(QMessageBox.Discard | QMessageBox.Cancel | QMessageBox.Save)

            # Display the dialog and wait for user action
            response = messageBoxChangeSample.exec_()

            if response == QMessageBox.Save:
                self.save_project()
                self.reset_analysis('sample')
            elif response == QMessageBox.Discard:
                self.reset_analysis('sample')
            else: #user pressed cancel
                self.comboBoxSampleId.setCurrentText(self.sample_id)
                return

        # notes and autosave timer
        self.notes_file = os.path.join(self.selected_directory,self.sample_id+'.rst')
        # open notes file if it exists
        if os.path.exists(self.notes_file):
            with open(self.notes_file,'r') as file:
                self.textEditNotes.setText(file.read())
        # put current notes into self.textEditNotes
        self.notes.autosaveTimer.start()

        # add sample to sample dictionary
        if self.sample_id not in self.data:
            # load sample's *.lame file
            file_path = os.path.join(self.selected_directory, self.csv_files[index])
            self.data[self.sample_id] = SampleObj(self.sample_id, file_path, self.comboBoxNegativeMethod.currentText())
            self.update_labels()

            # set slot for swapXY button
            self.toolButtonSwapResolution.clicked.connect(self.data[self.sample_id].swap_resolution)
            self.update_aspect_ratio_controls()

            # get selected_analyte columns
            selected_analytes = self.data[self.sample_id].processed_data.match_attributes({'data_type': 'analyte', 'use': True})

            # set analyte map to first available analyte
            if not selected_analytes:
                self.style.color_field = selected_analytes[0]

            self.plot_tree.add_sample(self.sample_id)
            self.plot_tree.update_tree()
        else:
            #update filters, polygon, profiles with existing data
            self.actionClearFilters.setEnabled(False)
            if np.all(self.data[self.sample_id].filter_mask):
                self.actionFilterToggle.setEnabled(False)
            else:
                self.actionFilterToggle.setEnabled(True)
                self.actionClearFilters.setEnabled(True)

            if np.all(self.data[self.sample_id].polygon_mask):
                self.actionPolygonMask.setEnabled(False)
            else:
                self.actionPolygonMask.setEnabled(True)
                self.actionClearFilters.setEnabled(True)

            if np.all(self.data[self.sample_id].cluster_mask):
                self.actionClusterMask.setEnabled(False)
            else:
                self.actionClusterMask.setEnabled(True)
                self.actionClearFilters.setEnabled(True)

            self.update_tables()

            #return

        # add spot data
        if not self.spotdata.empty:
            self.populate_spot_table()

        # reset filters
        self.actionClusterMask.setEnabled(False)
        self.actionPolygonMask.setEnabled(False)
        if not self.checkBoxPersistentFilter.isChecked():
            self.actionClearFilters.setEnabled(False)
            self.actionFilterToggle.setEnabled(False)
        self.actionNoiseReduction.setEnabled(False)

        # sort data
        self.plot_tree.sort_tree(None, method=self.sort_method)

        # reset flags
        self.update_cluster_flag = True
        self.update_pca_flag = True
        self.plot_flag = False

        # precalculate custom fields
        if self.calculator.precalculate_custom_fields:
            for name in self.calc_dict.keys():
                if name in self.data[self.sample_id].processed_data.columns:
                    continue
                self.comboBoxCalcFormula.setCurrentText(name)
                self.calculate_new_field(save=False)

        #update UI with auto scale and neg handling parameters from 'Analyte Info'
        analyte_list = self.data[self.sample_id].processed_data.match_attribute('data_type','analyte')

        self.update_spinboxes(field_type='Analyte', field=analyte_list[0])

        # reset all plot types on change of tab to the first option
        for key in self.plot_types.keys():
            self.plot_types[key][0] = 0
        # set to single-view, tree view, and sample and fields tab
        self.canvasWindow.setCurrentIndex(self.canvas_tab['sv'])
        self.toolBoxStyle.setCurrentIndex(0)
        self.toolBoxTreeView.setCurrentIndex(self.right_tab['tree'])
        self.toolBox.setCurrentIndex(self.left_tab['sample'])
        self.style.set_style_widgets(self.comboBoxPlotType.currentText())

        self.style.color_field_type = 'Analyte'
        self.style.color_field = analyte_list[0]
        if self.comboBoxPlotType.currentText() != 'analyte map':
            self.comboBoxPlotType.setCurrentText('analyte map')
        self.toolbox_changed(update=False)
        self.update_all_field_comboboxes()
        self.update_field_combobox(self.comboBoxColorByField,self.comboBoxColorField)
        self.spinBoxColorField.setMinimum(0)
        self.spinBoxColorField.setMaximum(self.comboBoxColorField.count() - 1)

        self.update_filter_values()
        self.histogram_update_bin_width()

        # update toolbar
        self.canvas_changed()

        self.update_plot = True
        self.update_SV()

    def open_preferences_dialog(self):
        pass



    # Other windows/dialogs
    # -------------------------------------
    def open_select_analyte_dialog(self):
        """Opens Select Analyte dialog

        Opens a dialog to select analytes for analysis either graphically or in a table.  Selection updates the list of analytes, and ratios in plot selector and comboBoxes.
        
        .. seealso::
            :ref:`AnalyteSelectionWindow` for the dialog
        """
        if self.sample_id == '':
            return

        self.analyte_dialog = AnalyteDialog(self)
        self.analyte_dialog.show()

        result = self.analyte_dialog.exec_()  # Store the result here
        if result == QDialog.Accepted:
            #update self.data['norm'] with selection
            for analyte in self.data[self.sample_id].processed_data.match_attribute('data_type','Analyte'):
                if analyte in list(self.analyte_dialog.norm_dict.keys()):
                    self.data[self.sample_id].set_attribute(analyte, 'use', True)
                else:
                    self.data[self.sample_id].set_attribute(analyte, 'use', False)

            for analyte, norm in self.analyte_dialog.norm_dict.items():
                if '/' in analyte:
                    if analyte not in self.data[self.sample_id].processed_data.columns:
                        analyte_1, analyte_2 = analyte.split(' / ') 
                        self.data[self.sample_id].compute_ratio(analyte_1, analyte_2)

                self.data[self.sample_id].processed_data.set_attribute(analyte,'norm',norm)

            self.plot_tree.update_tree(norm_update=True)
            #update analysis type combo in styles
            self.check_analysis_type()

            self.update_all_field_comboboxes()
        if result == QDialog.Rejected:
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
            'scatter', 'ndim', pca', 'clustering', 'profiles', 'Special'
        """
        match tab_name.lower():
            case 'samples':
                self.toolBox.setCurrentIndex(self.left_tab['sample'])
            case 'preprocess':
                self.toolBox.setCurrentIndex(self.left_tab['process'])
            case 'spot data':
                self.toolBox.setCurrentIndex(self.left_tab['spot'])
            case 'polygons':
                self.toolBox.setCurrentIndex(self.left_tab['polygons'])
                self.tabWidget.setCurrentIndex(self.bottom_tab['note'])
            case 'scatter':
                self.toolBox.setCurrentIndex(self.left_tab['scatter'])
            case 'ndim':
                self.toolBox.setCurrentIndex(self.left_tab['ndim'])
            case 'multidimensional':
                self.toolBox.setCurrentIndex(self.left_tab['multidim'])
            case 'clustering':
                self.toolBox.setCurrentIndex(self.left_tab['cluster'])
            case 'profiles':
                self.toolBox.setCurrentIndex(self.left_tab['profile'])
                self.tabWidget.setCurrentIndex(self.bottom_tab['profile'])
            case 'special':
                self.toolBox.setCurrentIndex(self.left_tab['special'])

    def canvas_changed(self):
        """Sets visibility of canvas tools and updates canvas plots"""        
        if self.sample_id == '':
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
            self.SpotDataPage.setEnabled(True)
            self.PolygonPage.setEnabled(True)
            self.ScatterPage.setEnabled(True)
            self.NDIMPage.setEnabled(True)
            self.MultidimensionalPage.setEnabled(True)
            self.ClusteringPage.setEnabled(True)
            self.ProfilingPage.setEnabled(True)
            self.PTtPage.setEnabled(True)

            self.toolBoxStyle.setEnabled(True)
            self.comboBoxPlotType.setEnabled(True)
            self.comboBoxStyleTheme.setEnabled(True)
            self.toolButtonUpdatePlot.setEnabled(True)
            self.toolButtonSaveTheme.setEnabled(True)

            self.StylingPage.setEnabled(True)
            self.CalculatorPage.setEnabled(True)

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
            self.SpotDataPage.setEnabled(False)
            self.PolygonPage.setEnabled(False)
            self.ScatterPage.setEnabled(False)
            self.NDIMPage.setEnabled(False)
            self.MultidimensionalPage.setEnabled(False)
            self.ClusteringPage.setEnabled(False)
            self.ProfilingPage.setEnabled(True)
            self.PTtPage.setEnabled(False)

            self.toolBoxTreeView.setCurrentIndex(self.right_tab['tree'])
            self.StylingPage.setEnabled(False)
            self.CalculatorPage.setEnabled(False)
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
            self.SpotDataPage.setEnabled(False)
            self.PolygonPage.setEnabled(False)
            self.ScatterPage.setEnabled(False)
            self.NDIMPage.setEnabled(False)
            self.MultidimensionalPage.setEnabled(False)
            self.ClusteringPage.setEnabled(False)
            self.ProfilingPage.setEnabled(False)
            self.PTtPage.setEnabled(False)

            self.toolBoxTreeView.setCurrentIndex(self.right_tab['tree'])
            self.StylingPage.setEnabled(False)
            self.CalculatorPage.setEnabled(False)

            self.display_QV()

    def toolbox_changed(self, update=True):
        """Updates styles associated with toolbox page

        Executes on change of ``MainWindow.toolBox.currentIndex()``.  Updates style related widgets.

        Parameters
        ----------
        update_plot : bool
            ``True`` forces update plot, when the canavas window tab is on single view, by default ``True``
        """
        if config.debug:
            print(f"toolbox_changed, update: {update}")

        if self.sample_id == '':
            return

        tab_id = self.toolBox.currentIndex()

        # update the plot type comboBox options
        self.comboBoxPlotType.blockSignals(True)
        self.comboBoxPlotType.clear()
        self.comboBoxPlotType.addItems(self.plot_types[tab_id][1:])
        self.comboBoxPlotType.blockSignals(False)

        # set to most used plot type on selected tab
        self.style.plot_type = self.plot_types[tab_id][self.plot_types[tab_id][0]+1]
        
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
        #plot_type = self.comboBoxPlotType.currentText()
        #self.style.set_style_widgets(plot_type=plot_type, style=self.style.plot_type[plot_type])

        # If canvasWindow is set to SingleView, update the plot
        if self.canvasWindow.currentIndex() == self.canvas_tab['sv'] and update:
            self.update_SV()

    def open_ternary(self):
        """Executes on actionTernary
        
        Opens the scatter tab and sets the ternary analytes.
        """
        self.open_tab('scatter')

        if self.sample_id:
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
        match self.comboBoxPlotType.currentText():
            case 'analyte map':
                # swap x and y
                self.data[self.sample_id].swap_xy()

                self.update_aspect_ratio_controls()

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

        # update plots
        self.update_SV()
        # self.update_all_plots()

    def update_aspect_ratio_controls(self):
        self.lineEditDX.value = self.data[self.sample_id].dx
        self.lineEditDY.value = self.data[self.sample_id].dy

        array_size = self.data[self.sample_id].array_size
        self.lineEditResolutionNx.value = array_size[1]
        self.lineEditResolutionNy.value = array_size[0]

    def update_norm(self, norm, field=None):

        self.data[self.sample_id].update_norm(norm=norm, field=field)

        self.update_SV()

    def update_fields(self, sample_id, plot_type, field_type, field,  plot=False):
        # updates comboBoxPlotType,comboBoxColorByField and comboBoxColorField comboboxes using tree, branch and leaf
        if sample_id == self.sample_id:
            if plot_type != self.comboBoxPlotType.currentText():
                self.comboBoxPlotType.setCurrentText(plot_type)

            if field_type != self.comboBoxColorByField.currentText():
                if field_type =='Calculated Map':  # correct name 
                    self.comboBoxColorByField.setCurrentText('Calculated')
                else:
                    self.comboBoxColorByField.setCurrentText(field_type)
                self.style.color_by_field_callback() # added color by field callback to update color field

            if field != self.comboBoxColorField.currentText():
                self.comboBoxColorField.setCurrentText(field)
                self.style.color_field_callback(plot)
            
    def update_resolution(self):
        """Updates DX and DY for a dataframe

        Recalculates X and Y for a dataframe
        """
        self.data[self.sample_id].update_resolution(self.lineEditDX.value, self.lineEditDY.value)

        self.update_aspect_ratio_controls()

        self.update_SV()

    # toolbar functions
    def change_ref_material(self, comboBox1, comboBox2):
        """Changes reference computing normalized analytes

        Sets all QComboBox to a common normalizing reference.

        Parameters
        ----------
        comboBox1 : QComboBox
            user changed QComboBox
        comboBox2 : QComboBox
            QComboBox to update
        """
        comboBox2.setCurrentIndex(comboBox1.currentIndex())

        self.ref_chem = self.ref_data.iloc[comboBox1.currentIndex()]
        self.ref_chem.index = [col.replace('_ppm', '') for col in self.ref_chem.index]

        # loop through normalized ratios and enable/disable ratios based
        # on the new reference's analytes
        if self.sample_id == '':
            return

        tree = 'Ratio (normalized)'
        branch = self.sample_id
        for i, row in self.data[branch]['ratio_info'].iterrows():
            analyte_1 = row['analyte_1']
            analyte_2 = row['analyte_2']
            ratio_name = f"{analyte_1} / {analyte_2}"
            item, check = self.plot_tree.find_leaf(tree, branch, leaf=ratio_name)

            if check:
                # ratio normalized
                # check if ratio can be normalized (note: normalization is not handled here)
                refval_1 = self.ref_chem[re.sub(r'\d', '', analyte_1).lower()]
                refval_2 = self.ref_chem[re.sub(r'\d', '', analyte_2).lower()]
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

        self.update_SV()
        #self.update_all_plots()

    def reset_to_full_view(self):
        """Reset the map to full view (i.e., remove crop)

        Executes on ``MainWindow.actionFullMap`` is clicked.
        """

        sample_id = self.sample_id
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

        self.data[self.sample_id].crop = False

    # for a disappearing button
    # def mouseEnter(self, event):
    #     self.toolButtonPopFigure.setVisible(True)

    # def mouseLeave(self, event):
    #     self.toolButtonPopFigure.setVisible(False)

    # color picking functions

    def update_labels(self):
        """Updates flags on statusbar indicating negative/zero and nan values within the processed_data_frame"""        

        data = self.data[self.sample_id].processed_data

        columns = data.match_attributes({'data_type': 'analyte', 'use': True}) + data.match_attributes({'data_type': 'ratio', 'use': True})
        negative_count = any(data[columns] <= 0)
        nan_count = any(np.isnan(data[columns]))
        
        self.labelInvalidValues.setText(f"Negative/zeros: {negative_count}, NaNs: {nan_count}")


    def plot_profile_and_table(self):
        self.profiling.plot_profiles()
        self.profiling.update_table_widget()

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
                columns = self.data[sample_id].raw_data.columns

                # clear existing plot info from tree to ensure saved plots using most recent data
                for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                    self.plot_tree.clear_tree_data(tree)
            else:
                columns = analyte_1

            # update column attributes
            self.data[sample_id].set_attribute(columns, 'auto_scale', auto_scale)
            self.data[sample_id].set_attribute(columns, 'upper_bound', ub)
            self.data[sample_id].set_attribute(columns, 'lower_bound', lb)
            self.data[sample_id].set_attribute(columns, 'diff_upper_bound', d_ub)
            self.data[sample_id].set_attribute(columns, 'diff_lower_bound', d_lb)
            self.data[sample_id].set_attribute(columns, 'negative_method', self.comboBoxNegativeMethod.currentText())

            # update data with new auto-scale/negative handling
            self.prep_data(sample_id)
            self.update_labels()

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
                self.update_labels()
            else:
                self.data[sample_id]['ratio_info'].loc[ (self.data[sample_id]['ratio_info']['analyte_1']==analyte_1)
                                            & (self.data[sample_id]['ratio_info']['analyte_2']==analyte_2),'auto_scale']  = auto_scale
                self.data[sample_id]['ratio_info'].loc[ (self.data[sample_id]['ratio_info']['analyte_1']==analyte_1)
                                            & (self.data[sample_id]['ratio_info']['analyte_2']==analyte_2),
                                            ['upper_bound','lower_bound','d_l_bound', 'd_u_bound']] = [ub,lb,d_lb, d_ub]
                self.prep_data(sample_id, analyte_1,analyte_2)
                self.update_labels()
        
        self.update_filter_values()
        self.update_SV()
        #self.show()
        
    def update_neg_handling(self):
        """Auto-scales pixel values in map

        Executes when the value ``MainWindow.comboBoxNegativeMethod`` is changed.

        Changes how negative values are handled for each analyte, the followinf options are available:
            Ignore negative values, Minimum positive value, Gradual shift, Yeo-Johnson transformation
        """
        sample_id = self.plot_info['sample_id']
        field = self.plot_info['field']
            
        if self.checkBoxApplyAll.isChecked():
            # Apply to all iolties
            analyte_list = self.data[self.sample_id].raw_data.match_attribute('data_type', 'analyte') + self.data[self.sample_id].raw_data.match_attribute('data_type', 'ratio')
            self.data[sample_id].raw_data.set_attribute(analyte_list, 'negative_method', self.comboBoxNegativeMethod.currentText())
            # clear existing plot info from tree to ensure saved plots using most recent data
            for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                self.plot_tree.clear_tree_data(tree)
            self.data[sample_id].prep_data()
        else:
            self.data[sample_id].raw_data.set_attribute(field, 'negative_method', self.comboBoxNegativeMethod.currentText())
            self.data[sample_id].prep_data(field)
        
        self.update_labels()
        self.update_filter_values()
        self.update_SV()

    def update_outlier_removal(self):
        """Removes outliers from one or all analytes."""        
        pass

    def update_plot(self,bin_s=True, axis=False, reset=False):
        """"Update plot

        :param bin_s: Defaults to True
        :type bin_s: bool, optional
        :param axis: Defaults to False
        :type axis: bool, optional
        :param reset: Defaults to False
        :type reset: bool, optional"""
        #print('update_plot')
        if self.update_spinboxes_bool:
            self.canvasWindow.setCurrentIndex(self.canvas_tab['sv'])
            lb = self.doubleSpinBoxLB.value()
            ub = self.doubleSpinBoxUB.value()
            d_lb = self.doubleSpinBoxDLB.value()
            d_ub = self.doubleSpinBoxDUB.value()


            bins = self.spinBoxNBins.value()
            analyte_str = self.current_plot
            analyte_str_list = analyte_str.split('_')
            auto_scale = self.toolButtonAutoScale.isChecked()
            sample_id = self.current_plot_information['sample_id']
            analyte_1 = self.current_plot_information['analyte_1']
            analyte_2 = self.current_plot_information['analyte_2']
            plot_type = self.current_plot_information['plot_type']
            plot_name = self.current_plot_information['plot_name']
            current_plot_df = self.current_plot_df

            # Computing data range using the 'array' column
            data_range = current_plot_df['array'].max() - current_plot_df['array'].min()
            #change axis range for all plots in sample

            # Removed during DataHandling update
            # if axis:
            #     # Filtering rows based on the conditions on 'X' and 'Y' columns
            #     self.data[self.sample_id].crop_mask = ((current_plot_df['X'] >= self.data[sample_id].crop_x_min) & (current_plot_df['X'] <= self.data[sample_id].crop_x_max) &
            #                    (current_plot_df['Y'] <= current_plot_df['Y'].max() - self.data[sample_id].crop_y_min) & (current_plot_df['Y'] >= current_plot_df['Y'].max() - self.data[sample_id].crop_y_max))


            #     #crop original_data based on self.data[self.sample_id]['crop_mask']
            #     self.data[sample_id]['cropped_raw_data'] = self.data[sample_id]['raw_data'][self.data[self.sample_id]['crop_mask']].reset_index(drop=True)


            #     #crop clipped_analyte_data based on self.data[self.sample_id]['crop_mask']
            #     self.data[sample_id]['processed_data'] = self.data[sample_id]['processed_data'][self.data[self.sample_id]['crop_mask']].reset_index(drop=True)

            #     #crop each df of computed_analyte_data based on self.data[self.sample_id]['crop_mask']
            #     for analysis_type, df in self.data[sample_id]['computed_data'].items():
            #         if isinstance(df, pd.DataFrame):
            #             df = df[self.data[self.sample_id]['crop_mask']].reset_index(drop=True)


            #     self.prep_data(sample_id)

            if plot_type=='histogram':
                if reset:
                    n_bins  = self.default_bins
                # If bin_width is not specified, calculate it
                if bin_s:
                    bin_width = data_range / n_bins
                    self.spinBoxBinWidth.setValue(int(np.floor(bin_width)))
                else:
                    bin_width = self.spinBoxBinWidth.value()

                self.plot_histogram(self.current_plot_df,self.current_plot_information, bin_width )
            else:
                self.plot_laser_map(self.current_plot_df, self.current_plot_information)
            # self.add_plot(isotope_str,clipped_isotope_array)
            self.run_noise_reduction()
            self.add_edge_detection()

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
    
    def update_tables(self):
        self.update_filter_table(reload = True)
        self.profiling.update_table_widget()
        self.polygon.update_table_widget()
        pass


    # -------------------------------
    # Crop functions - also see CropTool class below
    # -------------------------------
    def apply_crop(self):
        
        sample_id = self.plot_info['sample_id']
        field_type = self.comboBoxColorByField.currentText()
        field = self.comboBoxColorField.currentText()
        current_plot_df = self.get_map_data(field, field_type)
        
        self.data[self.sample_id].mask = self.data[self.sample_id].mask[self.data[self.sample_id].crop_mask]
        self.data[self.sample_id].polygon_mask = self.data[self.sample_id].polygon_mask[self.data[self.sample_id].crop_mask]
        self.data[self.sample_id].filter_mask = self.data[self.sample_id].filter_mask[self.data[self.sample_id].crop_mask]
        self.prep_data(sample_id)
        self.update_labels()

        # replot after cropping 
        self.plot_map_pg(sample_id, field_type, field)
        
        self.actionCrop.setChecked(False)
        self.data[self.sample_id]['crop'] = True

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
        sample_id = self.sample_id

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
            self.update_SV()

    # Field filter functions
    # -------------------------------
    def update_filter_values(self):
        """Updates widgets that display the filter bounds for a selected field.

        Updates ``MainWindow.lineEditFMin`` and ``MainWindow.lineEditFMax`` values for display when the
        field in ``MainWindow.comboBoxFilterField`` is changed.
        """
        if self.sample_id == '':
            return
        
        # field = self.comboBoxFilterField.currentText()
        # if not field:
        #     return
        if not (field := self.comboBoxFilterField.currentText()): return
        
        data = self.data[self.sample_id].processed_data

        self.lineEditFMin.value = data[field].min()
        self.callback_lineEditFMin()
        self.lineEditFMax.value = data[field].max()
        self.callback_lineEditFMax()

    def callback_lineEditFMin(self):
        """Updates ``MainWindow.doubleSpinBoxFMinQ.value`` when ``MainWindow.lineEditFMin.value`` is changed"""        
        if self.sample_id == '':
            return

        if (self.comboBoxFilterField.currentText() == '') or (self.comboBoxFilterFieldType.currentText() == ''):
            return

        try:
            array = self.get_map_data(self.comboBoxFilterField.currentText(), self.comboBoxFilterFieldType.currentText())['array'].dropna()
        except:
            return

        self.doubleSpinBoxFMinQ.blockSignals(True)
        self.doubleSpinBoxFMinQ.setValue(percentileofscore(array, self.lineEditFMin.value))
        self.doubleSpinBoxFMinQ.blockSignals(False)

    def callback_lineEditFMax(self):
        """Updates ``MainWindow.doubleSpinBoxFMaxQ.value`` when ``MainWindow.lineEditFMax.value`` is changed"""        
        if self.sample_id == '':
            return

        if (self.comboBoxFilterField.currentText() == '') or (self.comboBoxFilterFieldType.currentText() == ''):
            return

        try:
            array = self.get_map_data(self.comboBoxFilterField.currentText(), self.comboBoxFilterFieldType.currentText())['array'].dropna()
        except:
            return

        self.doubleSpinBoxFMaxQ.blockSignals(True)
        self.doubleSpinBoxFMaxQ.setValue(percentileofscore(array, self.lineEditFMax.value))
        self.doubleSpinBoxFMaxQ.blockSignals(False)

    def callback_doubleSpinBoxFMinQ(self):
        """Updates ``MainWindow.lineEditFMin.value`` when ``MainWindow.doubleSpinBoxFMinQ.value`` is changed"""        
        array = self.get_map_data(self.comboBoxFilterField.currentText(), self.comboBoxFilterFieldType.currentText())['array'].dropna()

        self.lineEditFMin.value = np.percentile(array, self.doubleSpinBoxFMinQ.value())

    def callback_doubleSpinBoxFMaxQ(self):
        """Updates ``MainWindow.lineEditFMax.value`` when ``MainWindow.doubleSpinBoxFMaxQ.value`` is changed"""        
        array = self.get_map_data(self.comboBoxFilterField.currentText(), self.comboBoxFilterFieldType.currentText())['array'].dropna()

        self.lineEditFMax.value = np.percentile(array, self.doubleSpinBoxFMaxQ.value())

    def update_filter_table(self, reload = False):
        """Update data for analysis when fiter table is updated.

        Parameters
        ----------
        reload : bool, optional
            Reload ``True`` updates the filter table, by default False
        """
        # If reload is True, clear the table and repopulate it from 'filter_info'
        if reload:
            # Clear the table
            self.tableWidgetFilters.setRowCount(0)

            # Repopulate the table from 'filter_info'
            for index, row in self.data[self.sample_id].filter_df.iterrows():
                current_row = self.tableWidgetFilters.rowCount()
                self.tableWidgetFilters.insertRow(current_row)

                # Create and set the checkbox for 'use'
                chkBoxItem_use = QCheckBox()
                chkBoxItem_use.setCheckState(Qt.Checked if row['use'] else Qt.Unchecked)
                chkBoxItem_use.stateChanged.connect(lambda state, row=current_row: on_use_checkbox_state_changed(row, state))
                self.tableWidgetFilters.setCellWidget(current_row, 0, chkBoxItem_use)

                # Add other items from the row
                self.tableWidgetFilters.setItem(current_row, 1, QTableWidgetItem(row['field_type']))
                self.tableWidgetFilters.setItem(current_row, 2, QTableWidgetItem(row['field']))
                self.tableWidgetFilters.setItem(current_row, 3, QTableWidgetItem(row['scale']))
                self.tableWidgetFilters.setItem(current_row, 4, QTableWidgetItem(fmt.dynamic_format(row['min'])))
                self.tableWidgetFilters.setItem(current_row, 5, QTableWidgetItem(fmt.dynamic_format(row['max'])))
                self.tableWidgetFilters.setItem(current_row, 6, QTableWidgetItem(row['operator']))

                # Create and set the checkbox for selection (assuming this is a checkbox similar to 'use')
                chkBoxItem_select = QCheckBox()
                chkBoxItem_select.setCheckState(Qt.Checked if row.get('select', False) else Qt.Unchecked)
                self.tableWidgetFilters.setCellWidget(current_row, 7, chkBoxItem_select)

        else:
            # open tabFilterList
            self.tabWidget.setCurrentIndex(self.bottom_tab['filter'])

            def on_use_checkbox_state_changed(row, state):
                # Update the 'use' value in the filter_df for the given row
                self.data[self.sample_id].filter_df.at[row, 'use'] = state == Qt.Checked

            field_type = self.comboBoxFilterFieldType.currentText()
            field = self.comboBoxFilterField.currentText()
            f_min = self.lineEditFMin.value
            f_max = self.lineEditFMax.value
            operator = self.comboBoxFilterOperator.currentText()
            # Add a new row at the end of the table
            row = self.tableWidgetFilters.rowCount()
            self.tableWidgetFilters.insertRow(row)

            # Create a QCheckBox for the 'use' column
            chkBoxItem_use = QCheckBox()
            chkBoxItem_use.setCheckState(Qt.Checked)
            chkBoxItem_use.stateChanged.connect(lambda state, row=row: on_use_checkbox_state_changed(row, state))

            chkBoxItem_select = QTableWidgetItem()
            chkBoxItem_select.setFlags(Qt.ItemIsUserCheckable |
                                Qt.ItemIsEnabled)

            if 'Analyte' in field_type:
                chkBoxItem_select.setCheckState(Qt.Unchecked)
                analyte_1 = field
                analyte_2 = None
                scale = self.data[self.sample_id]['analyte_info'].loc[(self.data[self.sample_id]['analyte_info']['analytes'] == field)].iloc[0]['norm']
            elif 'Ratio' in field_type:
                chkBoxItem_select.setCheckState(Qt.Unchecked)
                analyte_1, analyte_2 = field.split(' / ')
                scale = self.data[self.sample_id]['analyte_info'].loc[(self.data[self.sample_id]['analyte_info']['analytes'] == analyte_1)].iloc[0]['norm'].value
                #norm = self.data[self.sample_id]['ratio_info'].loc[(self.data[self.sample_id]['ratio_info']['analyte_1'] == analyte_1)
                #        & (self.data[self.sample_id]['ratio_info']['analyte_2'] == analyte_2)].iloc[0]['norm']
            else:
                scale = 'linear'

            self.tableWidgetFilters.setCellWidget(row, 0, chkBoxItem_use)
            self.tableWidgetFilters.setItem(row, 1, QTableWidgetItem(field_type))
            self.tableWidgetFilters.setItem(row, 2, QTableWidgetItem(field))
            self.tableWidgetFilters.setItem(row, 3, QTableWidgetItem(scale))
            self.tableWidgetFilters.setItem(row, 4, QTableWidgetItem(fmt.dynamic_format(f_min)))
            self.tableWidgetFilters.setItem(row, 5, QTableWidgetItem(fmt.dynamic_format(f_max)))
            self.tableWidgetFilters.setItem(row, 6, QTableWidgetItem(operator))
            self.tableWidgetFilters.setItem(row, 7, chkBoxItem_select)

            filter_info = {'use':True, 'field_type': field_type, 'field': field, 'norm':scale ,'min': f_min,'max':f_max, 'operator':operator, 'persistent':True}
            self.data[self.sample_id].filter_df.loc[len(self.data[self.sample_id].filter_df)] = filter_info

        self.apply_field_filters()

    def remove_selected_rows(self):
        """Remove selected rows from filter table.

        Removes selected rows from ``MainWindow.tableWidgetFilter``.
        """
        sample_id = self.sample_id

        print(self.tableWidgetFilters.selectedIndexes())

        # We loop in reverse to avoid issues when removing rows
        for row in range(self.tableWidgetFilters.rowCount()-1, -1, -1):
            chkBoxItem = self.tableWidgetFilters.item(row, 7)
            field_type = self.tableWidgetFilters.item(row, 1).text()
            field = self.tableWidgetFilters.item(row, 2).text()
            if chkBoxItem.checkState() == Qt.Checked:
                self.tableWidgetFilters.removeRow(row)
                self.data[sample_id].filter_df.drop(self.data[sample_id].filter_df[(self.data[sample_id].filter_df['field'] == field)].index, inplace=True)

        self.apply_field_filters(sample_id)

    def save_filter_table(self):
        """Opens a dialog to save filter table

        Executes on ``MainWindow.toolButtonFilterSave`` is clicked.  The filter is added to
        ``MainWindow.tableWidgetFilters`` and save into a dictionary to a file with a ``.fltr`` extension.
        """
        name, ok = QInputDialog.getText(self, 'Save filter table', 'Enter filter table name:')
        if ok:
            # file name for saving
            filter_file = os.path.join(BASEDIR,f'resources/filters/{name}.fltr')

            # save dictionary to file
            self.data[self.sample_id].filter_df.to_csv(filter_file, index=False)

            # update comboBox
            self.comboBoxFilterPresets.addItem(name)
            self.comboBoxFilterPresets.setCurrentText(name)

            self.statusBar.showMessage(f'Filters successfully saved as {filter_file}')
        else:
            # throw a warning that name is not saved
            QMessageBox.warning(None,'Error','could not save filter table.')

            return

    def load_filter_tables(self):
        """Loads filter names and adds them to the filter presets comboBox
        
        Looks for saved filter tables (*.fltr) in ``resources/filters/`` directory and adds them to
        ``MainWindow.comboBoxFilterPresets``.
        """
        # read filenames with *.sty
        file_list = os.listdir(os.path.join(BASEDIR,'resources/filters/'))
        filter_list = [file.replace('.fltr','') for file in file_list if file.endswith('.fltr')]

        # add default to list
        filter_list.insert(0,'')

        # update theme comboBox
        self.comboBoxFilterPresets.clear()
        self.comboBoxFilterPresets.addItems(filter_list)
        self.comboBoxFilterPresets.setCurrentIndex(0)

    def read_filter_table(self):
        filter_name = self.comboBoxFilterPresets.currentText()

        # If no filter_name is chosen, return
        if filter_name == '':
            return

        # open filter with name filter_name
        filter_file = os.path.join(BASEDIR,f'resources/filters/{filter_name}.fltr')
        filter_info = pd.read_csv(filter_file)

        # put filter_info into data and table
        self.data[self.sample_id].filter_df = filter_info

        self.update_filter_table()

    def apply_field_filters(self, update_plot=True):
        """Creates the field filter for masking data

        Updates ``MainWindow.data[sample_id].filter_mask`` and if ``update_plot==True``, updates ``MainWindow.data[sample_id].mask``.

        Parameters
        ----------
        update_plot : bool, optional
            If true, calls ``MainWindow.apply_filters`` which also calls ``MainWindow.update_SV``, by default True
        """        
        sample_id = self.sample_id

        # create array of all true
        self.data[sample_id].filter_mask = np.ones_like(self.data[sample_id].mask, dtype=bool)

        # remove all masks
        self.actionClearFilters.setEnabled(True)
        self.actionFilterToggle.setEnabled(True)
        self.actionFilterToggle.setChecked(True)

        # apply interval filters
        #print(self.data[sample_id].filter_df)

        # Check if rows in self.data[sample_id]['filter_info'] exist and filter array in current_plot_df
        # by creating a mask based on min and max of the corresponding filter analytes
        for index, filter_row in self.data[sample_id].filter_df.iterrows():
            if filter_row['use'].any():
                analyte_df = self.get_map_data(filter_row['field'], filter_row['field_type'])
                
                operator = filter_row['operator']
                if operator == 'and':
                    self.data[sample_id].filter_mask = self.data[sample_id].filter_mask & ((filter_row['min'] <= analyte_df['array'].values) & (analyte_df['array'].values <= filter_row['max']))
                elif operator == 'or':
                    self.data[sample_id].filter_mask = self.data[sample_id].filter_mask | ((filter_row['min'] <= analyte_df['array'].values) & (analyte_df['array'].values <= filter_row['max']))

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
        sample_id = self.sample_id

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
                inside_polygon_mask = np.array(inside_polygon).reshape(self.data[self.sample_id].array_size, order =  'C')
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
        sample_id = self.sample_id

        method = self.cluster_dict['active method']
        selected_clusters = self.cluster_dict[method]['selected_clusters']

        # Invert list of selected clusters
        if not inverse:
            selected_clusters = [cluster_idx for cluster_idx in range(self.cluster_dict[method]['n_clusters']) if cluster_idx not in selected_clusters]

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

                x_i = round(x*array.shape[1]/self.data[self.sample_id].x_range)
                y_i = round(y*array.shape[0]/self.data[self.sample_id].y_range)

                # if hover within lasermap array
                if 0 <= x_i < array.shape[1] and 0 <= y_i < array.shape[0] :
                    if not self.cursor and not self.actionCrop.isChecked():
                        QApplication.setOverrideCursor(Qt.BlankCursor)
                        self.cursor = True
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
            self.cursor = False
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
        x_i = round(x*self.array_x/self.data[self.sample_id].x_range)
        y_i = round(y*self.array_y/self.data[self.sample_id].y_range)

        # Ensure indices are within plot bounds
        if not(0 <= x_i < self.array_x) or not(0 <= y_i < self.array_y):
            #do nothing
            return

        # elif self.actionCrop.isChecked():
        #     self.crop_tool.create_rect(event, click_pos)
        # if event.button() == Qt.LeftButton and self.main_window.pushButtonStartProfile.isChecked():
       #apply profiles
        elif self.toolButtonPlotProfile.isChecked() or self.toolButtonPointMove.isChecked():
            self.profiling.plot_profile_scatter(event, field,view, plot, x, y,x_i, y_i)
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

        x_range = self.data[self.sample_id].x_range
        y_range = self.data[self.sample_id].y_range

        # Update the position of the zoom view
        self.zoomViewBox.setGeometry(x_pos, y_pos, self.zoomViewBox.width(), self.zoomViewBox.height())

        # Calculate the region to zoom in on
        zoomRect = QRectF(x - x_range * self.zoomLevel,
                y - y_range * self.zoomLevel,
                x_range * self.zoomLevel * 2,
                y_range * self.zoomLevel * 2)

        # Update the zoom view's displayed region
        # self.zoomViewBox.setRange(rect=zoomRect, padding=0)
        if self.toolButtonEdgeDetect.isChecked():
            self.zoomImg.setImage(image=self.edge_array)  # user edge_array too zoom with edge_det
        else:
            self.zoomImg.setImage(image=self.array)  # Make sure this uses the current image data

        self.zoomImg.setRect(0,0,x_range,y_range)
        self.zoomViewBox.setRange(zoomRect) # Set the zoom area in the image
        self.zoomImg.setColorMap(colormap.get(self.style.cmap, source = 'matplotlib'))
        self.zoomTarget.setPos(x, y)  # Update target position
        self.zoomTarget.show()
        self.zoomViewBox.setZValue(1e10)

    def reset_zoom(self, vb,histogram):
        vb.enableAutoRange()
        histogram.autoHistogramRange()



    # -------------------------------------
    # General plot functions
    # -------------------------------------
    def get_map_data(self, field, field_type, norm='linear'):
        """Wrapper for ``DataHandling.get_map_data`` that ensure proper call from ``MainWindow`` methods.

        Parameters
        ----------
        field : str
            Field requested.
        field_type : str
            Field type, if normalized it will include reference chemistry in call.
        norm : str, optional
            Sets whether to return the data scaled (linear, log, etc.), by default False

        Returns
        -------
        df : pandas.DataFrame
        """        
        if 'normalized' in field_type:
            df = self.data[self.sample_id].get_map_data(field, field_type, norm=norm, ref_chem=self.ref_chem)
        else:
            df = self.data[self.sample_id].get_map_data(field, field_type, norm=norm)

        return df

    def update_SV(self, plot_type=None, field_type=None, field=None):
        """Updates current plot (not saved to plot selector)

        Updates the current plot (as determined by ``MainWindow.comboBoxPlotType.currentText()`` and options in ``MainWindow.toolBox.selectedIndex()``.

        save : bool, optional
            save plot to plot selector, Defaults to False.
        """
        if config.debug:
            print(f"update_SV\n  plot_type: {plot_type}\n  field_type: {field_type}\n  field: {field}")

        if self.sample_id == '' or not self.comboBoxPlotType.currentText():
            return

        if not plot_type:
            plot_type = self.comboBoxPlotType.currentText()
        
        match plot_type:
            case 'analyte map':
                sample_id = self.sample_id
                if not field_type:
                    field_type = self.comboBoxColorByField.currentText()
                
                if not field:
                    field = self.comboBoxColorField.currentText()

                if not field_type or not field or (field_type == '') or (field == ''):
                    return

                if self.toolBox.currentIndex() in [self.left_tab['polygons'], self.left_tab['profile']]:
                    self.plot_map_pg(sample_id, field_type, field)
                    # show created profiles if exists
                    if self.toolBox.currentIndex() == self.left_tab['profile'] and (self.sample_id in self.profiling.profiles):
                        self.profiling.clear_plot()
                        self.profiling.plot_existing_profile(self.plot)
                    elif self.toolBox.currentIndex() == self.left_tab['polygons'] and (self.sample_id in self.polygon.polygons):  
                        self.polygon.clear_plot()
                        self.polygon.plot_existing_polygon(self.plot)
                else:
                    self.plot_map_mpl(sample_id, field_type, field)
                
                #update UI with auto scale and neg handling parameters from 'Analyte/Ratio Info'
                self.update_spinboxes(field, field_type)
                
            case 'gradient map':
                if self.comboBoxNoiseReductionMethod.currentText() == 'none':
                    QMessageBox.warning(None,'Warning','Noise reduction must be performed before computing a gradient.')
                    return
                self.noise_reduction.noise_reduction_method_callback()
            case 'correlation':
                if self.comboBoxCorrelationMethod.currentText() == 'none':
                    return
                self.plot_correlation()

            case 'TEC' | 'Radar':
                self.plot_ndim()

            case 'histogram':
                self.plot_histogram()

            case 'scatter' | 'heatmap':
                if self.comboBoxFieldX.currentText() == self.comboBoxFieldY.currentText():
                    return
                self.plot_scatter()

            case 'variance' | 'vectors' | 'PCA scatter' | 'PCA heatmap' | 'PCA score':
                self.plot_pca()

            case 'cluster' | 'cluster score':
                self.plot_clusters()
            
            case 'cluster performance':
                self.cluster_performance_plot()

        # self.update_plot_info_tab(self.plot_info)

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

            if (self.comboBoxPlotType.currentText() == 'analyte map') and (self.toolBox.currentIndex() == self.left_tab['sample']):
                current_map_df = self.get_map_data(plot_info['plot_name'], plot_info['field_type'], norm=self.style.cscale)
                self.plot_small_histogram(current_map_df)
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
        #self.plot_widget_dict[self.plot_info['tree']][self.sample_id][self.plot_info['plot_name']] = {'info':self.plot_info, 'view':view, 'position':None}

        # updates tree with new plot name
        self.add_tree_item(self.plot_info)

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
                data = self.comboBoxMVPlots.itemData(i, role=Qt.UserRole)

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
        if self.sample_id == '':
            return

        key = self.comboBoxQVList.currentText()

        # establish number of rows and columns
        ratio = 1.8 # aspect ratio of gridlayout
        # ratio = ncol / nrow, nplots = ncol * nrow
        ncol = int(np.sqrt(len(self.QV_analyte_list[key])*ratio))

        # fields in current sample
        fields = self.get_field_list()

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
            current_plot_df = self.get_map_data(analyte, 'Analyte')
            reshaped_array = np.reshape(current_plot_df['array'].values, self.data[self.sample_id].array_size, order=self.data[self.sample_id].order)

            # add image to canvas
            cmap = self.style.get_colormap()
            cax = canvas.axes.imshow(reshaped_array, cmap=cmap,  aspect=self.data[self.sample_id].aspect_ratio, interpolation='none')
            font = {'family': 'sans-serif', 'stretch': 'condensed', 'size': 8, 'weight': 'semibold'}
            canvas.axes.text( 0.025*self.data[self.sample_id].array_size[0],
                    0.1*self.data[self.sample_id].array_size[1],
                    analyte,
                    fontdict=font,
                    color=self.style.overlay_color,
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
            self.update_SV()

        if function == 'save':
            if isinstance(canvas,mplc.MplCanvas):
                self.mpl_toolbar.save_figure()
            elif isinstance(canvas,GraphicsLayoutWidget):
                # Save functionality for pyqtgraph
                export = exportDialog.ExportDialog(canvas.getItem(0, 0).scene())
                export.show(canvas.getItem(0, 0).getViewBox())
                export.exec_()
                
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
                    case 'analyte map':
                        field_type = self.plot_info['field_type']
                        field = self.plot_info['field']
                        save_data = self.get_map_data(field, field_type)
                    case 'gradient map':
                        field_type = self.plot_info['field_type']
                        field = self.plot_info['field']
                        save_data = self.get_map_data(field, field_type)
                        filtered_image = self.noise_red_array
                    case 'cluster':
                        save_data= self.data[self.sample_id].processed_data[field]
                    case _:
                        save_data = self.plot_info['data']
                    
            #open dialog to get name of file
            file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv);;All Files (*)")
            if file_name:
                with open(file_name, 'wb') as file:
                    # self.save_data holds data used for current plot 
                    save_data.to_csv(file,index = False)
                
                self.statusBar.showMessage("Plot Data saved successfully")
                


    def add_scalebar(self, ax):
        """Add a scalebar to a map

        Parameters
        ----------
        ax : 
            Axes to place scalebar on.
        """        
        # add scalebar
        direction = self.style.scale_dir
        length = self.style.scale_length
        if (length is not None) and (direction != 'none'):
            if direction == 'horizontal':
                dd = self.data[self.sample_id].dx
            else:
                dd = self.data[self.sample_id].dy
            sb = scalebar( width=length,
                    pixel_width=dd,
                    units=self.preferences['Units']['Distance'],
                    location=self.style.scale_location,
                    orientation=direction,
                    color=self.style.overlay_color,
                    ax=ax )

            sb.create()
        else:
            return

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
        if self.style.cbar_dir == 'none':
            return

        # discrete colormap - plot as a legend
        if cbartype == 'discrete':

            if grouplabels is None or groupcolors is None:
                return

            # create patches for legend items
            p = [None]*len(grouplabels)
            for i, label in enumerate(grouplabels):
                p[i] = Patch(facecolor=groupcolors[i], edgecolor='#111111', linewidth=0.5, label=label)

            if self.style.cbar_dir == 'vertical':
                canvas.axes.legend(
                        handles=p,
                        handlelength=1,
                        loc='upper left',
                        bbox_to_anchor=(1.025,1),
                        fontsize=self.style.font_size,
                        frameon=False,
                        ncol=1
                    )
            elif self.style.cbar_dir == 'horizontal':
                canvas.axes.legend(
                        handles=p,
                        handlelength=1,
                        loc='upper center',
                        bbox_to_anchor=(0.5,-0.1),
                        fontsize=self.style.font_size,
                        frameon=False,
                        ncol=3
                    )
        # continuous colormap - plot with colorbar
        else:
            if self.style.cbar_dir == 'vertical':
                if self.comboBoxPlotType.currentText() == 'correlation':
                    loc = 'left'
                else:
                    loc = 'right'
                cbar = canvas.fig.colorbar( cax,
                        ax=canvas.axes,
                        orientation=self.style.cbar_dir,
                        location=loc,
                        shrink=0.62,
                        fraction=0.1,
                        alpha=1
                    )
            elif self.style.cbar_dir == 'horizontal':
                cbar = canvas.fig.colorbar( cax,
                        ax=canvas.axes,
                        orientation=self.style.cbar_dir,
                        location='bottom',
                        shrink=0.62,
                        fraction=0.1,
                        alpha=1
                    )
            else:
                # should never reach this point
                assert self.style.cbar_dir == 'none', "Colorbar direction is set to none, but is trying to generate anyway."
                return

            cbar.set_label(self.style.clabel, size=self.style.font_size)
            cbar.ax.tick_params(labelsize=self.style.font_size)
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

        :param map_df: contains map data to convert
        :type map_df: pandas.DataFrame

        :returns: an rgba array
        :rtype: numpy.ndarray
        """
        mask = self.data[self.sample_id].mask

        array = np.reshape(map_df['array'].values, self.data[self.sample_id].array_size, order=self.data[self.sample_id].order)

        # Step 1: Normalize your data array for colormap application
        norm = colors.Normalize(vmin=np.nanmin(array), vmax=np.nanmax(array))
        cmap = self.style.get_colormap()

        # Step 2: Apply the colormap to get RGB values, then normalize to [0, 255] for QImage
        rgb_array = cmap(norm(array))[:, :, :3]  # Drop the alpha channel returned by cmap
        rgb_array = (rgb_array * 255).astype(np.uint8)

        # Step 3: Create an RGBA array where the alpha channel is based on self.data[self.sample_id].mask
        rgba_array = np.zeros((*rgb_array.shape[:2], 4), dtype=np.uint8)
        rgba_array[:, :, :3] = rgb_array  # Set RGB channels
        mask_r = np.reshape(mask, self.data[self.sample_id].array_size, order=self.data[self.sample_id].order)

        rgba_array[:, :, 3] = np.where(mask_r, 255, 100)  # Set alpha channel based on self.data[self.sample_id].mask

        return array, rgba_array

    def plot_map_mpl(self, sample_id, field_type, field):
        """Create a matplotlib canvas for plotting a map

        Create a map using ``mplc.MplCanvas``.

        Parameters
        ----------
        sample_id : str
            Sample identifier
        field_type : str
            Type of field for plotting
        field : str
            Field for plotting
        """        
        # create plot canvas
        canvas = mplc.MplCanvas(parent=self)

        # set color limits
        if field not in self.data[self.sample_id].axis_dict:
            self.style.initialize_axis_values(field_type,field)
            self.style.set_style_widgets()

        # get data for current map
        #scale = self.data[self.sample_id].processed_data.get_attribute(field, 'norm')
        scale = self.style.cscale
        map_df = self.data[self.sample_id].get_map_data(field, field_type, ref_chem=self.ref_chem)

        array_size = self.data[self.sample_id].array_size
        aspect_ratio = self.data[self.sample_id].aspect_ratio

        # store map_df to save_data if data needs to be exported
        self.save_data = map_df.copy()

        # equalized color bins to CDF function
        if self.toolButtonScaleEqualize.isChecked():
            sorted_data = map_df['array'].sort_values()
            cum_sum = sorted_data.cumsum()
            cdf = cum_sum / cum_sum.iloc[-1]
            map_df.loc[sorted_data.index, 'array'] = cdf.values

        # plot map
        reshaped_array = np.reshape(map_df['array'].values, array_size, order=self.data[self.sample_id].order)
            
        norm = self.style.color_norm()

        cax = canvas.axes.imshow(reshaped_array, cmap=self.style.get_colormap(),  aspect=aspect_ratio, interpolation='none', norm=norm)

        self.add_colorbar(canvas, cax)
        match self.style.cscale:
            case 'linear':
                clim = self.style.clim
            case 'log':
                clim = self.style.clim
                #clim = np.log10(self.style.clim)
            case 'logit':
                print('Color limits for logit are not currently implemented')

        cax.set_clim(clim[0], clim[1])

        # use mask to create an alpha layer
        mask = self.data[self.sample_id].mask.astype(float)
        reshaped_mask = np.reshape(mask, array_size, order=self.data[self.sample_id].order)

        alphas = colors.Normalize(0, 1, clip=False)(reshaped_mask)
        alphas = np.clip(alphas, .4, 1)

        alpha_mask = np.where(reshaped_mask == 0, 0.5, 0)  
        canvas.axes.imshow(np.ones_like(alpha_mask), aspect=aspect_ratio, interpolation='none', cmap='Greys', alpha=alpha_mask)
        canvas.array = reshaped_array

        canvas.axes.tick_params(direction=None,
            labelbottom=False, labeltop=False, labelright=False, labelleft=False,
            bottom=False, top=False, left=False, right=False)

        canvas.set_initial_extent()
        
        # add scalebar
        self.add_scalebar(canvas.axes)

        canvas.fig.tight_layout()

        # add small histogram
        if (self.toolBox.currentIndex() == self.left_tab['sample']) and (self.canvasWindow.currentIndex() == self.canvas_tab['sv']):
            self.plot_small_histogram(map_df)

        self.plot_info = {
            'tree': field_type,
            'sample_id': sample_id,
            'plot_name': field,
            'plot_type': 'analyte map',
            'field_type': field_type,
            'field': field,
            'figure': canvas,
            'style': self.style.style_dict[self.style.plot_type],
            'cluster_groups': None,
            'view': [True,False],
            'position': None
            }
        
        self.add_plotwidget_to_canvas(self.plot_info)
        # self.widgetSingleView.layout().addWidget(canvas)

        self.plot_tree.add_tree_item(self.plot_info)

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
        scale = self.style.cscale
        map_df = self.get_map_data(field, field_type, norm=scale)

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
        img_item.setRect(self.data[self.sample_id].x.min(),
                self.data[self.sample_id].y.min(),
                self.data[self.sample_id].x_range,
                self.data[self.sample_id].y_range)

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
        #plotWindow.setLimits(maxXRange=self.data[self.sample_id].x_range, maxYRange=self.data[self.sample_id].y_range)

        #supress right click menu
        plotWindow.setMenuEnabled(False)

        # colorbar
        cmap = colormap.get(self.style.cmap, source = 'matplotlib')
        #clb,cub,cscale,clabel = self.style.get_axis_values(field_type,field)
        # cbar = ColorBarItem(values=(clb,cub), width=25, colorMap=cmap, label=clabel, interactive=False, limits=(clb,cub), orientation=self.style.cbar_dir, pen='black')
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
            self.toolButtonEdgeDetect.setChecked(False)


        # Create a SignalProxy to handle mouse movement events
        # Create a SignalProxy for this plot and connect it to mouseMoved

        plotWindow.scene().sigMouseMoved.connect(lambda event,plot=plotWindow: self.mouse_moved_pg(event,plot))

        #add zoom window
        plotWindow.getViewBox().autoRange()

        # add edge detection
        if self.toolButtonEdgeDetect.isChecked():
            self.add_edge_detection()

        if view == 0 and self.plot_info:
            self.plot_info['view'][0] = False
            tmp = [True,False]
        else:
            tmp = [False,True]


        self.plot_info = {
            'tree': 'Analyte',
            'sample_id': sample_id,
            'plot_name': field,
            'plot_type': 'analyte map',
            'field_type': field_type,
            'field': field,
            'figure': graphicWidget,
            'style': self.style.style_dict[self.style.plot_type],
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
            self.plot_small_histogram(map_df)


    # -------------------------------------
    # Correlation functions and plotting
    # -------------------------------------
    def correlation_method_callback(self):
        """Updates colorbar label for correlation plots"""
        method = self.comboBoxCorrelationMethod.currentText()
        if self.style.clabel == method:
            return

        if self.checkBoxCorrelationSquared.isChecked():
            power = '^2'
        else:
            power = ''

        # update colorbar label for change in method
        match method:
            case 'Pearson':
                self.style.clabel = method + "'s $r" + power + "$"
            case 'Spearman':
                self.style.clabel = method + "'s $\\rho" + power + "$"
            case 'Kendall':
                self.style.clabel = method + "'s $\\tau" + power + "$"

        if self.comboBoxPlotType.currentText() != 'correlation':
            self.comboBoxPlotType.setCurrentText('correlation')
            self.style.set_style_widgets('correlation')

        self.update_SV()

    def correlation_squared_callback(self):
        """Produces a plot of the squared correlation."""        
        # update color limits and colorbar
        if self.checkBoxCorrelationSquared.isChecked():
            self.style.clim = [0,1]
            self.style.cmap = 'cmc.oslo'
        else:
            self.style.clim = [-1,1]
            self.style.cmap = 'RdBu'

        # update label
        if self.plot_flag:
            self.plot_flag = False
            self.correlation_method_callback()
            self.plot_flag = True
        else:
            self.correlation_method_callback()

        self.update_SV()

    def plot_correlation(self):
        """Creates an image of the correlation matrix"""
        #print('plot_correlation')

        canvas = mplc.MplCanvas(parent=self)
        canvas.axes.clear()

        # get the data for computing correlations
        df_filtered, analytes = self.data[self.sample_id].get_processed_data()

        # Calculate the correlation matrix
        method = self.comboBoxCorrelationMethod.currentText().lower()
        if self.comboBoxColorByField.currentText().lower() == 'none':
            correlation_matrix = df_filtered.corr(method=method)
        else:
            algorithm = self.comboBoxColorField.currentText()
            cluster_group = self.data[self.sample_id].processed_data.loc[:,algorithm]
            selected_clusters = self.cluster_dict[algorithm]['selected_clusters']

            ind = np.isin(cluster_group, selected_clusters)

            correlation_matrix = df_filtered[ind].corr(method=method)
        
        columns = correlation_matrix.columns

        font = {'size':self.style.font_size}

        # mask lower triangular matrix to show only upper triangle
        mask = np.zeros_like(correlation_matrix, dtype=bool)
        mask[np.tril_indices_from(mask)] = True
        correlation_matrix = np.ma.masked_where(mask, correlation_matrix)

        norm = self.style.color_norm()

        # plot correlation or correlation^2
        square_flag = self.checkBoxCorrelationSquared.isChecked()
        if square_flag:
            cax = canvas.axes.imshow(correlation_matrix**2, cmap=self.style.get_colormap(), norm=norm)
            canvas.array = correlation_matrix**2
        else:
            cax = canvas.axes.imshow(correlation_matrix, cmap=self.style.get_colormap(), norm=norm)
            canvas.array = correlation_matrix
            
        # store correlation_matrix to save_data if data needs to be exported
        self.save_data = canvas.array

        canvas.axes.spines['top'].set_visible(False)
        canvas.axes.spines['bottom'].set_visible(False)
        canvas.axes.spines['left'].set_visible(False)
        canvas.axes.spines['right'].set_visible(False)

        # Add colorbar to the plot
        self.add_colorbar(canvas, cax)

        # set color limits
        cax.set_clim(self.style.clim[0], self.style.clim[1])

        # Set tick labels
        ticks = np.arange(len(columns))
        canvas.axes.tick_params(length=0, labelsize=8,
                        labelbottom=False, labeltop=True, labelleft=False, labelright=True,
                        bottom=False, top=True, left=False, right=True)

        canvas.axes.set_yticks(ticks, minor=False)
        canvas.axes.set_xticks(ticks, minor=False)

        labels = self.style.toggle_mass(columns)

        canvas.axes.set_xticklabels(labels, rotation=90, ha='center', va='bottom', fontproperties=font)
        canvas.axes.set_yticklabels(labels, ha='left', va='center', fontproperties=font)

        canvas.axes.set_title('')

        self.style.update_figure_font(canvas, self.style.font)

        if square_flag:
            plot_name = method+'_squared'
        else:
            plot_name = method

        self.plot_info = {
            'tree': 'Correlation',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': 'correlation',
            'method': method,
            'square_flag': square_flag,
            'field_type': None,
            'field': None,
            'figure': canvas,
            'style': self.style.style_dict[self.style.plot_type],
            'cluster_groups': [],
            'view': [True,False],
            'position': [],
            'data': correlation_matrix,
        }

        self.clear_layout(self.widgetSingleView.layout())
        self.widgetSingleView.layout().addWidget(canvas)


    # -------------------------------------
    # Histogram functions and plotting
    # -------------------------------------
    def histogram_field_type_callback(self):
        """"Executes when the histogram field type is changed"""
        self.update_field_combobox(self.comboBoxHistFieldType, self.comboBoxHistField)
        if self.comboBoxPlotType.currentText() != 'histogram':
            self.comboBoxPlotType.setCurrentText('histogram')
        self.histogram_update_bin_width()

    def histogram_field_callback(self):
        """Executes when the histogram field is changed"""
        if self.comboBoxPlotType.currentText() != 'histogram':
            self.comboBoxPlotType.setCurrentText('histogram')
        self.histogram_update_bin_width()

    def histogram_update_bin_width(self):
        """Updates the bin width

        Generally called when the number of bins is changed by the user.  Updates the plot.
        """
        if not self.update_bins:
            return

        if (self.comboBoxHistFieldType.currentText() == '') or (self.comboBoxHistField.currentText() == ''):
            return

        #print('histogram_update_bin_width')
        self.update_bins = False

        # get currently selected data
        current_plot_df = self.get_map_data(self.comboBoxHistField.currentText(), self.comboBoxHistFieldType.currentText())

        # update bin width
        range = (np.nanmax(current_plot_df['array']) - np.nanmin(current_plot_df['array']))
        self.spinBoxBinWidth.setMinimum(int(range / self.spinBoxNBins.maximum()))
        self.spinBoxBinWidth.setMaximum(int(range / self.spinBoxNBins.minimum()))
        self.spinBoxBinWidth.setValue( int(range / self.spinBoxNBins.value()) )
        self.update_bins = True

        # update histogram
        if self.comboBoxPlotType.currentText() == 'histogram':
            self.update_SV()

    def histogram_update_n_bins(self):
        """Updates the number of bins

        Generally called when the bin width is changed by the user.  Updates the plot.
        """
        if not self.update_bins:
            return
        #print('update_n_bins')
        self.update_bins = False

        # get currently selected data
        map_df = self.get_map_data(self.comboBoxHistField.currentText(), self.comboBoxHistFieldType.currentText())

        # update n bins
        self.spinBoxBinWidth.setValue( int((np.nanmax(map_df['array']) - np.nanmin(map_df['array'])) / self.spinBoxBinWidth.value()) )
        self.update_bins = True

        # update histogram
        if self.comboBoxPlotType.currentText() == 'histogram':
            self.update_SV()

    def histogram_reset_bins(self):
        """Resets number of histogram bins to default

        Resets ``MainWindow.spinBoxNBins.value()`` to default number of bins.  Updates bin width
        ``MainWindow.spinBoxBinWidth.value()`` if an analysis and field are selected
        """
        # update number of bins (should automatically trigger update of histogram bin widths)
        self.spinBoxNBins.setValue(self.default_bins)

        # update bin width
        #self.histogram_update_bin_width()

        if self.comboBoxPlotType.currentText() == 'histogram':
            self.update_SV()

    def plot_small_histogram(self, current_plot_df):
        """Creates a small histogram on the Samples and Fields tab associated with the selected map

        Parameters
        ----------
        current_plot_df : dict
            Current data for plotting
        field : str
            Name of field to plot
        """
        #print('plot_small_histogram')
        # create Mpl canvas
        canvas = mplc.SimpleMplCanvas()
        #canvas.axes.clear()


        # Histogram
        #remove by mask and drop rows with na
        mask = self.data[self.sample_id].mask
        if self.style.cscale == 'log' or 'logit':
            mask = mask & current_plot_df['array'].notna() & (current_plot_df['array'] > 0)
        else:
            mask = mask & current_plot_df['array'].notna()

        array = current_plot_df['array'][mask].values

        logflag = False
        # check the analyte map cscale, the histogram needs to be the same
        if self.style.cscale == 'log':
            print('log scale')
            logflag = True
            if any(array <= 0):
                print(f"Warning issues with values <= 0, (-): {sum(array < 0)}, (0): {sum(array == 0)}")
                return

        bin_width = (np.nanmax(array) - np.nanmin(array)) / self.default_bins
        edges = np.arange(np.nanmin(array), np.nanmax(array) + bin_width, bin_width)

        if sum(mask) != len(mask):
            canvas.axes.hist( 
                current_plot_df['array'], 
                bins=edges, 
                density=True, 
                color='#b3b3b3', 
                edgecolor=None, 
                linewidth=self.style.line_width, 
                log=logflag, 
                alpha=0.6, 
                label='unmasked' )

        _, _, patches = canvas.axes.hist(array,
                bins=edges,
                density=True,
                color=self.style.marker_color,
                edgecolor=None,
                linewidth=self.style.line_width,
                log=logflag,
                alpha=0.6 )

        # color histogram bins by analyte colormap?
        if self.checkBoxShowHistCmap.isChecked():
            cmap = self.style.get_colormap()
            for j, p in enumerate(patches):
                p.set_facecolor(cmap(j / len(patches)))

        # Turn off axis box
        canvas.axes.spines['top'].set_visible(False)
        canvas.axes.spines['bottom'].set_visible(True)
        canvas.axes.spines['left'].set_visible(False)
        canvas.axes.spines['right'].set_visible(False)

        # Set ticks and labels labels
        canvas.axes.tick_params(axis='y', which='both', left=False, right=False, labelleft=False)
        canvas.axes.tick_params(axis='x', which='both', bottom=True, top=False, labelbottom=True, labelsize=8)
        canvas.axes.set_xlabel(self.style.clabel, fontdict={'size':8})

        # Size the histogram in the widget
        canvas.axes.margins(x=0)
        pos = canvas.axes.get_position()
        canvas.axes.set_position((pos.x0/2, 3*pos.y0, pos.width+pos.x0, pos.height-1.5*pos.y0))

        self.clear_layout(self.widgetHistView.layout())
        self.widgetHistView.layout().addWidget(canvas)

        #self.widgetHistView.hide()
        #self.widgetHistView.show()

    def plot_histogram(self):
        """Plots a histogramn in the canvas window"""
        
        plot_data = None
        #print('plot histogram')
        # create Mpl canvas
        canvas = mplc.MplCanvas(parent=self)

        nbins = int(self.spinBoxNBins.value())

        analysis = self.comboBoxHistFieldType.currentText()
        field = self.comboBoxHistField.currentText()
        #if analysis == 'Ratio':
        #    analyte_1 = field.split(' / ')[0]
        #    analyte_2 = field.split(' / ')[1]

        if self.comboBoxHistType.currentText() == 'log-scaling' and self.comboBoxHistFieldType.currentText() == 'Analyte':
            print('raw_data for log-scaling')
            x = self.get_scatter_data('histogram', processed=False)['x']
        else:
            print('processed_data for histogram')
            x = self.get_scatter_data('histogram', processed=True)['x']

        # determine edges
        xmin,xmax,xscale,xlbl = self.style.get_axis_values(x['type'],x['field'])
        self.style.xlim = [xmin, xmax]
        self.style.xscale = xscale
        #if xscale == 'log':
        #    x['array'] = np.log10(x['array'])
        #    xmin = np.log10(xmin)
        #    xmax = np.log10(xmax)

        #bin_width = (xmax - xmin) / nbins
        #print(nbins)
        #print(bin_width)
        
        # dscale = temp = self.data[self.sample_id]['analyte_info'].loc[self.data[self.sample_id]['analyte_info']['analytes'] == field,'norm'].values.item()
        if (xscale == 'linear') or (xscale == 'scientific'):
            edges = np.linspace(xmin, xmax, nbins)
        else:
            edges = np.linspace(10**xmin, 10**xmax, nbins)

        #print(edges)

        # histogram style
        lw = self.style.line_width
        if lw > 0:
            htype = 'step'
        else:
            htype = 'bar'

        # CDF or PDF
        match self.comboBoxHistType.currentText():
            case 'CDF':
                cumflag = True
            case _:
                cumflag = False

        # Check if the algorithm is in the current group and if results are available
        if self.comboBoxColorByField.currentText() == 'cluster' and self.comboBoxColorField.currentText() != '':
            method = self.cluster_dict['active method']

            # Get the cluster labels for the data
            cluster_color, cluster_label, _ = self.style.get_cluster_colormap(self.cluster_dict[method],alpha=self.style.marker_alpha)
            cluster_group = self.data[self.sample_id].processed_data.loc[:,method]
            clusters = self.cluster_dict[method]['selected_clusters']

            # Plot histogram for all clusters
            for i in clusters:
                cluster_data = x['array'][cluster_group == i]

                bar_color = cluster_color[int(i)]
                if htype == 'step':
                    ecolor = bar_color
                else:
                    ecolor = None

                if self.comboBoxHistType.currentText() != 'log-scaling' :
                    plot_data = canvas.axes.hist( cluster_data,
                            cumulative=cumflag,
                            histtype=htype,
                            bins=edges,
                            color=bar_color, edgecolor=ecolor,
                            linewidth=lw,
                            label=cluster_label[int(i)],
                            alpha=self.style.marker_alpha/100,
                            density=True
                        )
                else:
                    # Filter out NaN and zero values
                    filtered_data = cluster_data[~np.isnan(cluster_data) & (cluster_data > 0)]

                    # Sort the data in ascending order
                    sorted_data = np.sort(filtered_data)

                    # Calculate log(number of values > x)
                    log_values = np.log10(sorted_data)
                    log_counts = np.log10(len(sorted_data) - np.arange(len(sorted_data)))

                    # Plot the data
                    canvas.axes.plot(log_values, log_counts, label=cluster_label[int(i)], color=bar_color, lw=lw)

            # Add a legend
            self.add_colorbar(canvas, None, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color, alpha=self.style.marker_alpha/100)
            #canvas.axes.legend()
        else:
            clusters = None
            # Regular histogram
            bar_color = self.style.marker_color
            if htype == 'step':
                ecolor = self.style.line_color
            else:
                ecolor = None

            if self.comboBoxHistType.currentText() != 'log-scaling' :
                plot_data = canvas.axes.hist( x['array'],
                        cumulative=cumflag,
                        histtype=htype,
                        bins=edges,
                        color=bar_color, edgecolor=ecolor,
                        linewidth=lw,
                        alpha=self.style.marker_alpha/100,
                        density=True
                    )
            else:
                # Filter out NaN and zero values
                filtered_data = x['array'][~np.isnan(x['array']) & (x['array'] > 0)]

                # Sort the data in ascending order
                sorted_data = np.sort(filtered_data)

                # Calculate log(number of values > x)
                #log_values = np.log10(sorted_data)
                counts = len(sorted_data) - np.arange(len(sorted_data))

                # Plot the data
                #canvas.axes.plot(log_values, log_counts, label=cluster_label[int(i)], color=bar_color, lw=lw)
                canvas.axes.plot(sorted_data, counts, color=bar_color, lw=lw, alpha=self.style.marker_alpha/100)

        # axes
        # label font
        if 'font' == '':
            font = {'size':self.style.font}
        else:
            font = {'font':self.style.font, 'size':self.style.font_size}

        # set y-limits as p-axis min and max in self.data[self.sample_id].axis_dict
        if self.comboBoxHistType.currentText() != 'log-scaling' :
            pflag = False
            if 'pstatus' not in self.data[self.sample_id].axis_dict[x['field']]:
                pflag = True
            elif self.data[self.sample_id].axis_dict[x['field']]['pstatus'] == 'auto':
                pflag = True

            if pflag:
                ymin, ymax = canvas.axes.get_ylim()
                d = {'pstatus':'auto', 'pmin':fmt.oround(ymin,order=2,toward=0), 'pmax':fmt.oround(ymax,order=2,toward=1)}
                self.data[self.sample_id].axis_dict[x['field']].update(d)
                self.style.set_axis_widgets('y', x['field'])

            # grab probablility axes limits
            _, _, _, _, ymin, ymax = self.style.get_axis_values(x['type'],x['field'],ax='p')

            # x-axis
            canvas.axes.set_xlabel(xlbl, fontdict=font)
            if xscale == 'log':
            #    self.logax(canvas.axes, [xmin,xmax], axis='x', label=xlbl)
                canvas.axes.set_xscale(xscale,base=10)
            # if self.style.xscale == 'linear':
            # else:
            #     canvas.axes.set_xlim(xmin,xmax)
            canvas.axes.set_xlim(xmin,xmax)

            if xscale == 'scientific':
                canvas.axes.ticklabel_format(axis='x', style='sci', scilimits=(0,0))

            # y-axis
            canvas.axes.set_ylabel(self.comboBoxHistType.currentText(), fontdict=font)
            canvas.axes.set_ylim(ymin,ymax)
        else:
            canvas.axes.set_xscale('log',base=10)
            canvas.axes.set_yscale('log',base=10)

            canvas.axes.set_xlabel(r"$\log_{10}($" + f"{field}" + r"$)$", fontdict=font)
            canvas.axes.set_ylabel(r"$\log_{10}(N > \log_{10}$" + f"{field}" + r"$)$", fontdict=font)

        canvas.axes.tick_params(labelsize=self.style.font_size,direction=self.style.tick_dir)
        canvas.axes.set_box_aspect(self.style.aspect_ratio)

        self.style.update_figure_font(canvas, self.style.font)

        canvas.fig.tight_layout()

        self.plot_info = {
            'tree': 'Histogram',
            'sample_id': self.sample_id,
            'plot_name': analysis+'_'+field,
            'field_type': analysis,
            'field': field,
            'plot_type': 'histogram',
            'type': self.comboBoxHistType.currentText(),
            'nbins': nbins,
            'figure': canvas,
            'style': self.style.style_dict[self.style.plot_type],
            'cluster_groups': clusters,
            'view': [True,False],
            'position': [],
            'data': plot_data
        }

        self.clear_layout(self.widgetSingleView.layout())
        self.widgetSingleView.layout().addWidget(canvas)


    # -------------------------------------
    # Scatter/Heatmap functions
    # -------------------------------------
    def get_scatter_data(self, plot_type, processed=True):

        scatter_dict = {'x': {'type': None, 'field': None, 'label': None, 'array': None},
                'y': {'type': None, 'field': None, 'label': None, 'array': None},
                'z': {'type': None, 'field': None, 'label': None, 'array': None},
                'c': {'type': None, 'field': None, 'label': None, 'array': None}}

        match plot_type:
            case 'histogram':
                if processed or self.comboBoxHistFieldType.currentText() != 'Analyte':
                    scatter_dict['x'] = self.data[self.sample_id].get_vector(self.comboBoxHistFieldType.currentText(), self.comboBoxHistField.currentText(), norm=self.style.xscale)
                else:
                    scatter_dict['x'] = self.data[self.sample_id].get_vector(self.comboBoxHistFieldType.currentText(), self.comboBoxHistField.currentText(), norm=self.style.xscale, processed=False)
            case 'PCA scatter' | 'PCA heatmap':
                scatter_dict['x'] = self.data[self.sample_id].get_vector('PCA score', f'PC{self.spinBoxPCX.value()}', norm=self.style.xscale)
                scatter_dict['y'] = self.data[self.sample_id].get_vector('PCA score', f'PC{self.spinBoxPCY.value()}', norm=self.style.yscale)
                if (self.comboBoxColorByField.currentText() is None) or (self.comboBoxColorByField.currentText != ''):
                    scatter_dict['c'] = self.data[self.sample_id].get_vector(self.comboBoxColorByField.currentText(), self.comboBoxColorField.currentText())
            case _:
                scatter_dict['x'] = self.data[self.sample_id].get_vector(self.comboBoxFieldTypeX.currentText(), self.comboBoxFieldX.currentText(), norm=self.style.xscale)
                scatter_dict['y'] = self.data[self.sample_id].get_vector(self.comboBoxFieldTypeY.currentText(), self.comboBoxFieldY.currentText(), norm=self.style.yscale)
                if (self.comboBoxColorByField.currentText() is not None) and (self.comboBoxColorByField.currentText() != ''):
                    scatter_dict['z'] = self.data[self.sample_id].get_vector(self.comboBoxFieldTypeZ.currentText(), self.comboBoxFieldZ.currentText(), norm=self.style.zscale)
                elif (self.comboBoxFieldZ.currentText() is not None) and (self.comboBoxFieldZ.currentText() != ''):
                    scatter_dict['c'] = self.data[self.sample_id].get_vector(self.comboBoxColorByField.currentText(), self.comboBoxColorField.currentText(), norm=self.style.cscale)

        # set axes widgets
        if (scatter_dict['x']['field'] is not None) and (scatter_dict['y']['field'] != ''):
            if scatter_dict['x']['field'] not in self.data[self.sample_id].axis_dict.keys():
                self.style.initialize_axis_values(scatter_dict['x']['type'], scatter_dict['x']['field'])
                self.style.set_axis_widgets('x', scatter_dict['x']['field'])

        if (scatter_dict['y']['field'] is not None) and (scatter_dict['y']['field'] != ''):
            if scatter_dict['y']['field'] not in self.data[self.sample_id].axis_dict.keys():
                self.style.initialize_axis_values(scatter_dict['y']['type'], scatter_dict['y']['field'])
                self.style.set_axis_widgets('y', scatter_dict['y']['field'])

        if (scatter_dict['z']['field'] is not None) and (scatter_dict['z']['field'] != ''):
            if scatter_dict['z']['field'] not in self.data[self.sample_id].axis_dict.keys():
                self.style.initialize_axis_values(scatter_dict['z']['type'], scatter_dict['z']['field'])
                self.style.set_axis_widgets('z', scatter_dict['z']['field'])

        if (scatter_dict['c']['field'] is not None) and (scatter_dict['c']['field'] != ''):
            if scatter_dict['c']['field'] not in self.data[self.sample_id].axis_dict.keys():
                self.style.set_color_axis_widgets()
                self.style.set_axis_widgets('c', scatter_dict['c']['field'])

        return scatter_dict


    def plot_scatter(self, canvas=None):
        """Creates a plots from self.toolBox Scatter page.

        Creates both scatter and heatmaps (spatial histograms) for bi- and ternary plots.

        Parameters
        ----------
        canvas : MplCanvas
            canvas within gui for plotting, by default ``None``
        """
        #print('plot_scatter')
        plot_type = self.comboBoxPlotType.currentText()

        # get data for plotting
        scatter_dict = self.get_scatter_data(plot_type)
        if (scatter_dict['x']['field'] == '') or (scatter_dict['y']['field'] == ''):
            return

        if canvas is None:
            plot_flag = True
            canvas = mplc.MplCanvas(parent=self)
        else:
            plot_flag = False

        match plot_type.split()[-1]:
            # scatter
            case 'scatter':
                if (scatter_dict['z']['field'] is None) or (scatter_dict['z']['field'] == ''):
                    # biplot
                    self.biplot(canvas,scatter_dict['x'],scatter_dict['y'],scatter_dict['c'])
                else:
                    # ternary
                    self.ternary_scatter(canvas,scatter_dict['x'],scatter_dict['y'],scatter_dict['z'],scatter_dict['c'])

            # heatmap
            case 'heatmap':
                # biplot
                if (scatter_dict['z']['field'] is None) or (scatter_dict['z']['field'] == ''):
                    self.hist2dbiplot(canvas,scatter_dict['x'],scatter_dict['y'])
                # ternary
                else:
                    self.hist2dternplot(canvas,scatter_dict['x'],scatter_dict['y'],scatter_dict['z'],scatter_dict['c'])

        canvas.axes.margins(x=0)

        if plot_flag:
            self.style.update_figure_font(canvas, self.style.font)
            self.clear_layout(self.widgetSingleView.layout())
            self.widgetSingleView.layout().addWidget(canvas)

    def biplot(self, canvas, x, y, c):
        """Creates scatter bi-plots

        A general function for creating scatter plots of 2-dimensions.

        Parameters
        ----------
        canvas : MplCanvas
            Canvas to be added to main window
        x : dict
            Data associated with field ``MainWindow.comboBoxFieldX.currentText()`` as x coordinate
        y : dict
            Data associated with field ``MainWindow.comboBoxFieldX.currentText()`` as y coordinate
        c : dict
            Data associated with field ``MainWindow.comboBoxColorField.currentText()`` as marker colors
        style : dict
            Style parameters
        """
        if (c['field'] is None) or (c['field'] == ''):
            # single color
            canvas.axes.scatter(x['array'], y['array'], c=self.style.marker_color,
                s=self.style.marker_size,
                marker=self.style.marker_dict[self.style.marker],
                edgecolors='none',
                alpha=self.style.marker_alpha/100)
            cb = None
            
            plot_data = pd.DataFrame(np.vstack((x['array'], y['array'])).T, columns = ['x','y'])
            
        elif self.style.color_field_type == 'cluster':
            # color by cluster
            method = self.comboBoxColorField.currentText()
            if method not in list(self.cluster_dict.keys()):
                return
            else:
                if 0 not in list(self.cluster_dict[method].keys()):
                    return

            cluster_color, cluster_label, cmap = self.style.get_cluster_colormap(self.cluster_dict[method],alpha=self.style.marker_alpha)
            cluster_group = self.data[self.sample_id].processed_data.loc[:,method]
            selected_clusters = self.cluster_dict[method]['selected_clusters']

            ind = np.isin(cluster_group, selected_clusters)

            norm = self.style.color_norm(self.cluster_dict[method]['n_clusters'])

            cb = canvas.axes.scatter(x['array'][ind], y['array'][ind], c=c['array'][ind],
                s=self.style.marker_size,
                marker=self.style.marker_dict[self.style.marker],
                edgecolors='none',
                cmap=cmap,
                alpha=self.style.marker_alpha/100,
                norm=norm)

            self.add_colorbar(canvas, cb, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
            plot_data = pd.DataFrame(np.vstack((x['array'][ind],y['array'][ind], c['array'][ind], cluster_group[ind])).T, columns = ['x','y','c','cluster_group'])
        else:
            # color by field
            norm = self.style.color_norm()
            cb = canvas.axes.scatter(x['array'], y['array'], c=c['array'],
                s=self.style.marker_size,
                marker=self.style.marker_dict[self.style.marker],
                edgecolors='none',
                cmap=self.style.get_colormap(),
                alpha=self.style.marker_alpha/100,
                norm=norm)

            self.add_colorbar(canvas, cb)
            plot_data = pd.DataFrame(np.vstack((x['array'], y['array'], c['array'])).T, columns = ['x','y','c'])
            

        # axes
        xmin, xmax, xscale, xlbl = self.style.get_axis_values(x['type'],x['field'])
        ymin, ymax, yscale, ylbl = self.style.get_axis_values(y['type'],y['field'])

        # labels
        font = {'size':self.style.font_size}
        canvas.axes.set_xlabel(xlbl, fontdict=font)
        canvas.axes.set_ylabel(ylbl, fontdict=font)

        # axes limits
        canvas.axes.set_xlim(xmin,xmax)
        canvas.axes.set_ylim(ymin,ymax)

        # tick marks
        canvas.axes.tick_params(direction=self.style.tick_dir,
            labelsize=self.style.font_size,
            labelbottom=True, labeltop=False, labelleft=True, labelright=False,
            bottom=True, top=True, left=True, right=True)

        # aspect ratio
        canvas.axes.set_box_aspect(self.style.aspect_ratio)
        canvas.fig.tight_layout()

        if xscale == 'log':
            canvas.axes.set_xscale(xscale,base=10)
        if yscale == 'log':
            canvas.axes.set_yscale(yscale,base=10)

        if xscale == 'scientific':
            canvas.axes.ticklabel_format(axis='x', style='sci', scilimits=(0,0))
        if yscale == 'scientific':
            canvas.axes.ticklabel_format(axis='y', style='sci', scilimits=(0,0))

        plot_name = f"{x['field']}_{y['field']}_{'scatter'}"

        self.plot_info = {
            'tree': 'Geochemistry',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': 'scatter',
            'field_type': [x['type'], y['type'], '', c['type']],
            'field': [x['field'], y['field'], '', c['field']],
            'figure': canvas,
            'style': self.style.style_dict[self.style.plot_type],
            'cluster_groups': [],
            'view': [True,False],
            'position': [],
            'data':  plot_data
        }

    def ternary_scatter(self, canvas, x, y, z, c):
        """Creates ternary scatter plots

        A general function for creating ternary scatter plots.

        Parameters
        ----------
        canvas : MplCanvas
            Canvas that contains axes and figure
        x : dict
            coordinate associated with top vertex
        y : dict
            coordinate associated with left vertex
        z : dict
            coordinate associated with right vertex
        c : dict
            color dimension
        """
        labels = [x['field'], y['field'], z['field']]
        tp = ternary(canvas.axes, labels, 'scatter')

        if (c['field'] is None) or (c['field'] == ''):
            tp.ternscatter( x['array'], y['array'], z['array'],
                    marker=self.style.marker_dict[self.style.marker],
                    size=self.style.marker_size,
                    color=self.style.marker_color,
                    alpha=self.style.marker_alpha/100,
                )
            cb = None
            plot_data = pd.DataFrame(np.vstack((x['array'],y['array'], z['array'])).T, columns = ['x','y','z'])
            
        elif self.style.color_field_type == 'cluster':
            # color by cluster
            method = self.comboBoxColorField.currentText()
            if method not in list(self.cluster_dict.keys()):
                return
            else:
                if 0 not in list(self.cluster_dict[method].keys()):
                    return

            cluster_color, cluster_label, cmap = self.style.get_cluster_colormap(self.cluster_dict[method],alpha=self.style.marker_alpha)
            cluster_group = self.data[self.sample_id].processed_data.loc[:,method]
            selected_clusters = self.cluster_dict[method]['selected_clusters']

            ind = np.isin(cluster_group, selected_clusters)

            norm = self.style.color_norm(self.cluster_dict[method]['n_clusters'])

            _, cb = tp.ternscatter( x['array'][ind], y['array'][ind], z['array'][ind],
                    categories=c['array'][ind],
                    marker=self.marker_dict[self.style.marker],
                    size=self.style.marker_size,
                    cmap=cmap,
                    norm=norm,
                    labels=True,
                    alpha=self.style.marker_alpha/100,
                    orientation='None' )

            self.add_colorbar(canvas, cb, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
            plot_data = pd.DataFrame(np.vstack((x['array'][ind],y['array'][ind], z['array'][ind], cluster_group[ind])).T, columns = ['x','y','z','cluster_group'])
        else:
            # color field
            norm = self.style.color_norm()
            _, cb = tp.ternscatter(x['array'], y['array'], z['array'],
                    categories=c['array'],
                    marker=self.style.marker_dict[self.style.marker],
                    size=self.style.marker_size,
                    cmap=self.style.cmap,
                    norm=norm,
                    alpha=self.style.marker_alpha/100,
                    orientation=self.style.cbar_dir )
            
            if cb:
                cb.set_label(c['label'])
                plot_data = pd.DataFrame(np.vstack((x['array'], y['array'], c['array'])).T, columns = ['x','y','c'])

        # axes limits
        canvas.axes.set_xlim(-1.01,1.01)
        canvas.axes.set_ylim(-0.01,1)

        plot_name = f"{x['field']}_{y['field']}_{z['field']}_{'ternscatter'}"
        self.plot_info = {
            'tree': 'Geochemistry',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': 'scatter',
            'field_type': [x['type'], y['type'], z['type'], c['type']],
            'field': [x['field'], y['field'], z['field'], c['field']],
            'figure': canvas,
            'style': self.style.style_dict[self.style.plot_type],
            'cluster_groups': [],
            'view': [True,False],
            'position': [],
            'data': plot_data
        }

    def hist2dbiplot(self, canvas, x, y):
        """Creates 2D histogram figure

        A general function for creating 2D histograms (heatmaps).

        Parameters
        ----------
        canvas : MplCanvas
            plotting canvas
        x : dict
            X-axis dictionary
        y : dict
            Y-axis dictionary
        """
        # color by field
        norm = self.style.color_norm()
        h = canvas.axes.hist2d(x['array'], y['array'], bins=self.style.resolution, norm=norm, cmap=self.style.get_colormap())
        self.add_colorbar(canvas, h[3])

        # axes
        xmin, xmax, xscale, xlbl = self.style.get_axis_values(x['type'],x['field'])
        ymin, ymax, yscale, ylbl = self.style.get_axis_values(y['type'],y['field'])

        # labels
        font = {'size':self.style.font_size}
        canvas.axes.set_xlabel(xlbl, fontdict=font)
        canvas.axes.set_ylabel(ylbl, fontdict=font)

        # axes limits
        canvas.axes.set_xlim(xmin,xmax)
        canvas.axes.set_ylim(ymin,ymax)

        if yscale == 'scientific':
            canvas.axes.ticklabel_format(axis='y', style=yscale)
        if yscale == 'scientific':
            canvas.axes.ticklabel_format(axis='y', style=yscale)

        # tick marks
        canvas.axes.tick_params(direction=self.style.tick_dir,
                        labelsize=self.style.font_size,
                        labelbottom=True, labeltop=False, labelleft=True, labelright=False,
                        bottom=True, top=True, left=True, right=True)

        # aspect ratio
        canvas.axes.set_box_aspect(self.style.aspect_ratio)

        if xscale == 'log':
            canvas.axes.set_xscale(xscale,base=10)
        if yscale == 'log':
            canvas.axes.set_yscale(yscale,base=10)

        if xscale == 'scientific':
            canvas.axes.ticklabel_format(axis='x', style='sci', scilimits=(0,0))
        if yscale == 'scientific':
            canvas.axes.ticklabel_format(axis='y', style='sci', scilimits=(0,0))

        plot_name = f"{x['field']}_{y['field']}_{'heatmap'}"
        self.plot_info = {
            'tree': 'Geochemistry',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': 'heatmap',
            'field_type': [x['type'], y['type'], '', ''],
            'field': [x['field'], y['field'], '', ''],
            'figure': canvas,
            'style': self.style.style_dict[self.style.plot_type],
            'cluster_groups': [],
            'view': [True,False],
            'position': [],
            'data': pd.DataFrame(np.vstack((x['array'],y['array'])).T, columns = ['x','y'])
        }

    def hist2dternplot(self, canvas, x, y, z, c):
        """Creates a ternary histogram figure

        A general function for creating scatter plots of 2-dimensions.

        Parameters
        ----------
        fig : matplotlib.figure
            Figure object
        x, y, z : dict
            Coordinates associated with top, left and right vertices, respectively
        style:  dict
            Style parameters
        save : bool
            Saves figure widget to plot tree
        c : str
            Display, mean, median, standard deviation plots for a fourth dimension in
            addition to histogram map. Default is None, which produces a histogram.
        """
        labels = [x['field'], y['field'], z['field']]

        if (c['field'] is None) or (c['field'] == ''):
            tp = ternary(canvas.axes, labels, 'heatmap')

            norm = self.style.color_norm()
            hexbin_df, cb = tp.ternhex(a=x['array'], b=y['array'], c=z['array'],
                bins=self.style.resolution,
                plotfield='n',
                cmap=self.style.cmap,
                orientation=self.style.cbar_dir,
                norm=norm)

            if cb is not None:
                cb.set_label('log(N)')
        else:
            pass
            # axs = fig.subplot_mosaic([['left','upper right'],['left','lower right']], layout='constrained', width_ratios=[1.5, 1])

            # for idx, ax in enumerate(axs):
            #     tps[idx] = ternary(ax, labels, 'heatmap')

            # hexbin_df = ternary.ternhex(a=x['array'], b=y['array'], c=z['array'], val=c['array'], bins=self.style.resolution)

            # cb.set_label(c['label'])

            # #tp.ternhex(hexbin_df=hexbin_df, plotfield='n', cmap=self.style.cmap, orientation='vertical')

        plot_name = f"{x['field']}_{y['field']}_{z['field']}_{'heatmap'}"
        self.plot_info = {
            'tree': 'Geochemistry',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': 'heatmap',
            'field_type': [x['type'], y['type'], z['type'], ''],
            'field': [x['field'], y['field'], z['field'], ''],
            'figure': canvas,
            'style': self.style.axis_dict[self.style.plot_style],
            'cluster_groups': [],
            'view': [True,False],
            'position': [],
            'data' : pd.DataFrame(np.vstack((x['array'],y['array'], z['array'])).T, columns = ['x','y','z'])
        }

    def plot_ternarymap(self, canvas):
        """Creates map colored by ternary coordinate positions"""
        if self.comboBoxPlotType.currentText() != 'ternary map':
            self.comboBoxPlotType.setCurrentText('ternary map')
            self.style.set_style_widgets('ternary map')

        canvas = mplc.MplCanvas(sub=121,parent=self)

        afield = self.comboBoxFieldX.currentText()
        bfield = self.comboBoxFieldY.currentText()
        cfield = self.comboBoxFieldZ.currentText()

        a = self.data[self.sample_id].processed_data.loc[:,afield].values
        b = self.data[self.sample_id].processed_data.loc[:,bfield].values
        c = self.data[self.sample_id].processed_data.loc[:,cfield].values

        ca = get_rgb_color(get_hex_color(self.toolButtonTCmapXColor.palette().button().color()))
        cb = get_rgb_color(get_hex_color(self.toolButtonTCmapYColor.palette().button().color()))
        cc = get_rgb_color(get_hex_color(self.toolButtonTCmapZColor.palette().button().color()))
        cm = get_rgb_color(get_hex_color(self.toolButtonTCmapMColor.palette().button().color()))

        t = ternary(canvas.axes)

        cval = t.terncolor(a, b, c, ca, cb, cc, cp=cm)

        M, N = self.data[self.sample_id].array_size

        # Reshape the array into MxNx3
        map_data = np.zeros((M, N, 3), dtype=np.uint8)
        map_data[:len(cval), :, :] = cval.reshape(M, N, 3, order=self.data[self.sample_id].order)

        canvas.axes.imshow(map_data, aspect=self.data[self.sample_id].aspect_ratio)
        canvas.array = map_data

        # add scalebar
        self.add_scalebar(canvas.axes)

        grid = None
        if self.style.cbar_dir == 'vertical':
            grid = gs.GridSpec(5,1)
        elif self.style.cbar_dir == 'horizontal':
            grid = gs.GridSpec(1,5)
        else:
            self.clear_layout(self.widgetSingleView.layout())
            self.widgetSingleView.layout().addWidget(canvas)
            return

        canvas.axes.set_position(grid[0:4].get_position(canvas.fig))
        canvas.axes.set_subplotspec(grid[0:4])              # only necessary if using tight_layout()

        canvas.axes2 = canvas.fig.add_subplot(grid[4])

        canvas.fig.tight_layout()

        t2 = ternary(canvas.axes2, labels=[afield,bfield,cfield])

        hbin = t2.hexagon(10)
        xc = np.array([v['xc'] for v in hbin])
        yc = np.array([v['yc'] for v in hbin])
        at,bt,ct = t2.xy2tern(xc,yc)
        cv = t2.terncolor(at,bt,ct, ca=ca, cb=cb, cc=cc, cp=cm)
        for i, hb in enumerate(hbin):
            t2.ax.fill(hb['xv'], hb['yv'], color=cv[i]/255, edgecolor='none')

        plot_name = f'{afield}_{bfield}_{cfield}_ternarymap'
        self.plot_info = {
            'tree': 'Geochemistry',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': 'ternary map',
            'field_type': [self.comboBoxFieldTypeX.currentText(),
                self.comboBoxFieldTypeY.currentText(),
                self.comboBoxFieldTypeZ.currentText(),
                ''],
            'field': [afield, bfield, cfield, ''],
            'figure': canvas,
            'style': self.style.style_dict[self.style.plot_type],
            'cluster_groups': [],
            'view': [True,False],
            'position': [],
            'data': map_data
        }

        self.clear_layout(self.widgetSingleView.layout())
        self.widgetSingleView.layout().addWidget(canvas)

    # -------------------------------------
    # PCA functions and plotting
    # -------------------------------------
    def compute_pca(self):
        #print('compute_pca')
        self.pca_results = {}

        df_filtered, analytes = self.data[self.sample_id].get_processed_data()

        # Preprocess the data
        scaler = StandardScaler()
        df_scaled = scaler.fit_transform(df_filtered)

        # Perform PCA
        self.pca_results = PCA(n_components=min(len(df_filtered.columns), len(df_filtered)))  # Adjust n_components as needed

        # compute pca scores
        pca_scores = pd.DataFrame(self.pca_results.fit_transform(df_scaled), columns=[f'PC{i+1}' for i in range(self.pca_results.n_components_)])
        self.style.clim = [np.amin(self.pca_results.components_), np.amax(self.pca_results.components_)]

        # Add PCA scores to DataFrame for easier plotting
        self.data[self.sample_id].add_columns('pca score',pca_scores.columns,pca_scores.values,self.data[self.sample_id].mask)

        #update min and max of PCA spinboxes
        if self.pca_results.n_components_ > 0:
            self.spinBoxPCX.setMinimum(1)
            self.spinBoxPCY.setMinimum(1)
            self.spinBoxPCX.setMaximum(self.pca_results.n_components_+1)
            self.spinBoxPCY.setMaximum(self.pca_results.n_components_+1)
            if self.spinBoxPCY.value() == 1:
                self.spinBoxPCY.setValue(int(2))

        self.update_all_field_comboboxes()
        self.update_pca_flag = False

    def plot_pca(self):
        """Plot principal component analysis (PCA)
        
        Wrapper for one of four types of PCA plots:
        * ``plot_pca_variance()`` a plot of explained variances
        * ``plot_pca_vectors()`` a plot of PCA vector components as a heatmap
        * uses ``plot_scatter()`` and ``plot_pca_components`` to produce both scatter and heatmaps of PCA scores with vector components.
        * ``plot_score_map()`` produces a plot of PCA scores for a single component as a map

        .. seealso::
            ``MainWindow.plot_scatter``
        """
        #'plot_pca')
        if self.sample_id == '':
            return

        if self.update_pca_flag or not self.data[self.sample_id].processed_data.match_attribute('data_type','pca score'):
            self.compute_pca()

        # Determine which PCA plot to create based on the combobox selection
        plot_type = self.comboBoxPlotType.currentText()

        match plot_type.lower():
            # make a plot of explained variance
            case 'variance':
                canvas, plot_data = self.plot_pca_variance()
                plot_name = plot_type

            # make an image of the PC vectors and their components
            case 'vectors':
                canvas, plot_data = self.plot_pca_vectors()
                plot_name = plot_type

            # make a scatter plot or heatmap of the data... add PC component vectors
            case 'pca scatter'| 'pca heatmap':
                pc_x = int(self.spinBoxPCX.value())
                pc_y = int(self.spinBoxPCY.value())

                if pc_x == pc_y:
                    return

                plot_name = plot_type+f'_PC{pc_x}_PC{pc_y}'
                # Assuming pca_df contains scores for the principal components
                # uncomment to use plot scatter instead of ax.scatter
                canvas = mplc.MplCanvas(parent=self)
                self.plot_scatter(canvas=canvas)

                plot_data= self.plot_pca_components(canvas)

            # make a map of a principal component score
            case 'pca score':
                if self.comboBoxColorByField.currentText().lower() == 'none' or self.comboBoxColorField.currentText() == '':
                    return

                # Assuming pca_df contains scores for the principal components
                canvas, plot_data = self.plot_score_map()
                plot_name = plot_type+f'_{self.comboBoxColorField.currentText()}'
            case _:
                print(f'Unknown PCA plot type: {plot_type}')
                return

        self.style.update_figure_font(canvas, self.style.font)

        self.plot_info = {
            'tree': 'Multidimensional Analysis',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': self.comboBoxPlotType.currentText(),
            'field_type':self.comboBoxColorByField.currentText(),
            'field':  self.comboBoxColorField.currentText(),
            'figure': canvas,
            'style': self.style.style_dict[self.style.plot_type],
            'cluster_groups': [],
            'view': [True,False],
            'position': [],
            'data': plot_data
        }

        self.update_canvas(canvas)
        #self.update_field_combobox(self.comboBoxHistFieldType, self.comboBoxHistField)

    def plot_pca_variance(self):
        """Creates a plot of explained variance, individual and cumulative, for PCA

        Returns
        -------
        mplc.MplCanvas
            
        """        
        canvas = mplc.MplCanvas(parent=self)

        # pca_dict contains variance ratios for the principal components
        variances = self.pca_results.explained_variance_ratio_
        n_components = range(1, len(variances)+1)
        cumulative_variances = variances.cumsum()  # Calculate cumulative explained variance

        # Plotting the explained variance
        canvas.axes.plot(n_components, variances, linestyle='-', linewidth=self.style.line_width,
            marker=self.style.marker_dict[self.style.marker], markeredgecolor=self.style.marker_color, markerfacecolor='none', markersize=self.style.marker_size,
            color=self.style.marker_color, label='Explained Variance')

        # Plotting the cumulative explained variance
        canvas.axes.plot(n_components, cumulative_variances, linestyle='-', linewidth=self.style.line_width,
            marker=self.style.marker_dict[self.style.marker], markersize=self.style.marker_size,
            color=self.style.marker_color, label='Cumulative Variance')

        # Adding labels, title, and legend
        xlbl = 'Principal Component'
        ylbl = 'Variance Ratio'

        canvas.axes.legend(fontsize=self.style.font_size)

        # Adjust the y-axis limit to make sure the plot includes all markers and lines
        canvas.axes.set_ylim([0, 1.0])  # Assuming variance ratios are between 0 and 1

        # labels
        font = {'size':self.style.font_size}
        canvas.axes.set_xlabel(xlbl, fontdict=font)
        canvas.axes.set_ylabel(ylbl, fontdict=font)

        # tick marks
        canvas.axes.tick_params(direction=self.style.tick_dir,
            labelsize=self.style.font_size,
            labelbottom=True, labeltop=False, labelleft=True, labelright=False,
            bottom=True, top=True, left=True, right=True)

        canvas.axes.set_xticks(range(1, len(n_components) + 1, 5))
        canvas.axes.set_xticks(n_components, minor=True)

        # aspect ratio
        canvas.axes.set_box_aspect(self.style.aspect_ratio)
        
        plot_data = pd.DataFrame(np.vstack((n_components, variances, cumulative_variances)).T, columns = ['Components','Variance','Cumulative Variance'])
        return canvas, plot_data

    def plot_pca_vectors(self):
        """Displays a heat map of PCA vector components

        Returns
        -------
        mplc.MplCanvas
            Creates figure on mplc.MplCanvas
        """        
        canvas = mplc.MplCanvas(parent=self)

        # pca_dict contains 'components_' from PCA analysis with columns for each variable
        # No need to transpose for heatmap representation
        analytes = self.data[self.sample_id].processed_data.match_attribute('data_type','analyte')

        components = self.pca_results.components_
        # Number of components and variables
        n_components = components.shape[0]
        n_variables = components.shape[1]

        norm = self.style.color_norm()
        cax = canvas.axes.imshow(components, cmap=self.style.get_colormap(), aspect=1.0, norm=norm)
        canvas.array = components

        # Add a colorbar
        self.add_colorbar(canvas, cax)
        # if self.style.cbar_dir == 'vertical':
        #     cbar = canvas.fig.colorbar(cax, ax=canvas.axes, orientation=self.style.cbar_dir, location='right', shrink=0.62, fraction=0.1)
        #     cbar.set_label('PCA score', size=self.style.font_size)
        #     cbar.ax.tick_params(labelsize=self.style.font_size)
        # elif self.style.cbar_dir == 'horizontal':
        #     cbar = canvas.fig.colorbar(cax, ax=canvas.axes, orientation=self.style.cbar_dir, location='bottom', shrink=0.62, fraction=0.1)
        #     cbar.set_label('PCA score', size=self.style.font_size)
        #     cbar.ax.tick_params(labelsize=self.style.font_size)
        # else:
        #     cbar = canvas.fig.colorbar(cax, ax=canvas.axes, orientation=self.style.cbar_dir, location='bottom', shrink=0.62, fraction=0.1)


        xlbl = 'Principal Components'

        # Optional: Rotate x-axis labels for better readability
        # plt.xticks(rotation=45)

        # labels
        font = {'size':self.style.font_size}
        canvas.axes.set_xlabel(xlbl, fontdict=font)

        # tickmarks and labels
        canvas.axes.tick_params(labelsize=self.style.font_size)
        canvas.axes.tick_params(axis='x', direction=self.style.tick_dir,
                        labelsize=self.style.font_size,
                        labelbottom=False, labeltop=True,
                        bottom=True, top=True)

        canvas.axes.tick_params(axis='y', length=0, direction=self.style.tick_dir,
                        labelsize=self.style.font_size,
                        labelleft=True, labelright=False,
                        left=True, right=True)

        canvas.axes.set_xticks(range(0, n_components, 5))
        canvas.axes.set_xticks(range(0, n_components, 1), minor=True)
        canvas.axes.set_xticklabels(np.arange(1, n_components+1, 5))

        #ax.set_yticks(n_components, labels=[f'Var{i+1}' for i in range(len(n_components))])
        canvas.axes.set_yticks(range(0, n_variables,1), minor=False)
        canvas.axes.set_yticklabels(self.style.toggle_mass(analytes), ha='right', va='center')

        canvas.fig.tight_layout()
        plot_data = pd.DataFrame(components, columns = list(map(str, range(n_variables))))
        return canvas, plot_data

    def plot_pca_components(self, canvas):
        """Adds vector components to PCA scatter and heatmaps

        Parameters
        ----------
        canvas : mplc.MplCanvas
            Canvas object for plotting

        .. seealso::
            ``MainWindow.plot_pca_vectors``
        """
        #print('plot_pca_components')
        if self.style.line_width == 0:
            return

        # field labels
        analytes = self.data[self.sample_id].processed_data.match_attribute('data_type','analyte')
        nfields = len(analytes)

        # components
        pc_x = int(self.spinBoxPCX.value())-1
        pc_y = int(self.spinBoxPCY.value())-1

        x = self.pca_results.components_[:,pc_x]
        y = self.pca_results.components_[:,pc_y]

        # mulitiplier for scale
        m = self.style.line_multiplier #np.min(np.abs(np.sqrt(x**2 + y**2)))

        # arrows
        canvas.axes.quiver(np.zeros(nfields), np.zeros(nfields), m*x, m*y, color=self.style.line_color,
            angles='xy', scale_units='xy', scale=1, # arrow angle and scale set relative to the data
            linewidth=self.style.line_width, headlength=2, headaxislength=2) # arrow properties

        # labels
        for i, analyte in enumerate(analytes):
            if x[i] > 0 and y[i] > 0:
                canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='left', va='bottom', color=self.style.line_color)
            elif x[i] < 0 and y[i] > 0:
                canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='left', va='top', color=self.style.line_color)
            elif x[i] > 0 and y[i] < 0:
                canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='right', va='bottom', color=self.style.line_color)
            elif x[i] < 0 and y[i] < 0:
                canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='right', va='top', color=self.style.line_color)

        plot_data = pd.DataFrame(np.vstack((x,y)).T, columns = ['PC x', 'PC Y'])
        return plot_data
    # -------------------------------------
    # Cluster functions
    # -------------------------------------
    def plot_score_map(self):
        """Plots score maps

        Creates a score map for PCA and clusters.  Maps are displayed on an ``mplc.MplCanvas``.
        """
        canvas = mplc.MplCanvas(parent=self)

        plot_type = self.comboBoxPlotType.currentText()

        # data frame for plotting
        match plot_type:
            case 'PCA score':
                idx = int(self.comboBoxColorField.currentIndex()) + 1
                field = f'PC{idx}'
            case 'cluster score':
                #idx = int(self.comboBoxColorField.currentIndex())
                #field = f'{idx}'
                field = self.comboBoxColorField.currentText()
            case _:
                print('(MainWindow.plot_score_map) Unknown score type'+plot_type)
                return canvas

        reshaped_array = np.reshape(self.data[self.sample_id].processed_data[field].values, self.data[self.sample_id].array_size, order=self.data[self.sample_id].order)

        cax = canvas.axes.imshow(reshaped_array, cmap=self.style.cmap, aspect=self.data[self.sample_id].aspect_ratio, interpolation='none')
        canvas.array = reshaped_array

         # Add a colorbar
        self.add_colorbar(canvas, cax, field)

        canvas.axes.set_title(f'{plot_type}')
        canvas.axes.tick_params(direction=None,
            labelbottom=False, labeltop=False, labelright=False, labelleft=False,
            bottom=False, top=False, left=False, right=False)
        #canvas.axes.set_axis_off()

        # add scalebar
        self.add_scalebar(canvas.axes)

        return canvas, self.data[self.sample_id].processed_data[field]

    def plot_cluster_map(self):
        """Produces a map of cluster categories
        
        Creates the map on an ``mplc.MplCanvas``.  Each cluster category is assigned a unique color.
        """
        print('plot_cluster_map')
        canvas = mplc.MplCanvas(parent=self)

        plot_type = self.comboBoxPlotType.currentText()
        method = self.comboBoxClusterMethod.currentText()

        # data frame for plotting
        #groups = self.data[self.sample_id][plot_type][method].values
        groups = self.data[self.sample_id].processed_data[method].values

        reshaped_array = np.reshape(groups, self.data[self.sample_id].array_size, order=self.data[self.sample_id].order)

        n_clusters = len(np.unique(groups))

        cluster_color, cluster_label, cmap = self.style.get_cluster_colormap(self.cluster_dict[method], alpha=self.style.marker_alpha)

        #boundaries = np.arange(-0.5, n_clusters, 1)
        #norm = colors.BoundaryNorm(boundaries, cmap.N, clip=True)
        norm = self.style.color_norm(n_clusters)

        #cax = canvas.axes.imshow(self.array.astype('float'), cmap=self.style.cmap, norm=norm, aspect = self.data[self.sample_id].aspect_ratio)
        cax = canvas.axes.imshow(reshaped_array.astype('float'), cmap=cmap, norm=norm, aspect=self.data[self.sample_id].aspect_ratio)
        canvas.array = reshaped_array
        #cax.cmap.set_under(style['Scale']['OverlayColor'])

        self.add_colorbar(canvas, cax, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)

        canvas.fig.subplots_adjust(left=0.05, right=1)  # Adjust these values as needed
        canvas.fig.tight_layout()

        canvas.axes.set_title(f'Clustering ({method})')
        canvas.axes.tick_params(direction=None,
            labelbottom=False, labeltop=False, labelright=False, labelleft=False,
            bottom=False, top=False, left=False, right=False)
        #canvas.axes.set_axis_off()

        # add scalebar
        self.add_scalebar(canvas.axes)

        return canvas, self.data[self.sample_id].processed_data[method]

    def plot_cluster_performance(self):
        """Plots used to estimate the optimal number of clusters

        1. Elbow Method
        The elbow method looks at the variance (or inertia) within clusters as the number
        of clusters increases. The idea is to plot the sum of squared distances between
        each point and its assigned cluster's centroid, known as the within-cluster sum
        of squares (WCSS) or inertia, for different values of k (number of clusters).

        Process:
        * Run KMeans for a range of cluster numbers (k).
        * Plot the inertia (WCSS) vs. the number of clusters.
        * Look for the "elbow" point, where the rate of decrease sharply slows down,
        indicating that adding more clusters does not significantly reduce the inertia.


        2. Silhouette Score
        The silhouette score measures how similar an object is to its own cluster compared
        to other clusters. The score ranges from -1 to 1, where:

        * A score close to 1 means the sample is well clustered.
        * A score close to 0 means the sample lies on the boundary between clusters.
        * A score close to -1 means the sample is assigned to the wrong cluster.

        In cases where clusters have widely varying sizes or densities, Silhouette Score may provide the best result.

        Process:
        * Run KMeans for a range of cluster numbers (k).
        * Calculate the silhouette score for each k.
        * Choose the k with the highest silhouette score.
        """        
        if self.sample_id == '':
            return

        method = self.comboBoxClusterMethod.currentText()

        # maximum clusters for producing an cluster performance
        max_clusters = self.spinBoxClusterMax.value() 

        # compute cluster results
        inertia, silhouette_scores = self.compute_clusters(max_clusters)

        second_derivative = np.diff(np.diff(inertia))

        #optimal_k = np.argmax(second_derivative) + 2  # Example heuristic

        # Plot inertia
        canvas = mplc.MplCanvas(parent=self)

        canvas.axes.plot(range(1, max_clusters+1), inertia, linestyle='-', linewidth=self.style.line_width,
            marker=self.style.marker_dict[self.style.marker], markeredgecolor=self.style.marker_color, markerfacecolor='none', markersize=self.style.marker_size,
            color=self.style.marker_color, label='Inertia')

        # Plotting the cumulative explained variance

        canvas.axes.set_xlabel('Number of clusters')
        canvas.axes.set_ylabel('Inertia', color=self.style.marker_color)
        canvas.axes.tick_params(axis='y', labelcolor=self.style.marker_color)
        canvas.axes.set_title(f'Cluster performance: {method}')
        #canvas.axes.axvline(x=optimal_k, linestyle='--', color='m', label=f'Elbow at k={optimal_k}')

        # aspect ratio
        canvas.axes.set_box_aspect(self.style.aspect_ratio)

        # Create a secondary y-axis to plot the second derivative
        canvas.axes2 = canvas.axes.twinx()
        canvas.axes2.plot(range(2, max_clusters), second_derivative, linestyle='-', linewidth=self.style.line_width,
            marker=self.style.marker_dict[self.style.marker], markersize=self.style.marker_size,
            color='r', label='3nd Derivative')

        canvas.axes2.set_ylabel('2nd Derivative', color='r')
        canvas.axes2.tick_params(axis='y', labelcolor='r')

        # aspect ratio
        canvas.axes2.set_box_aspect(self.style.aspect_ratio)

        canvas.axes3 = canvas.axes.twinx()
        canvas.axes3.plot(range(1, max_clusters+1), silhouette_scores, linestyle='-', linewidth=self.style.line_width,
            marker=self.style.marker_dict[self.style.marker], markeredgecolor='orange', markerfacecolor='none', markersize=self.style.marker_size,
            color='orange', label='Silhouette Scores')

        canvas.axes3.spines['right'].set_position(('outward', 60))  # Move it outward by 60 points
        canvas.axes3.set_ylabel('Silhouette score', color='orange')
        canvas.axes3.tick_params(axis='y', labelcolor='orange')

        canvas.axes3.set_box_aspect(self.style.aspect_ratio)


        #print(f"Second derivative of inertia: {second_derivative}")
        #print(f"Optimal number of clusters: {optimal_k}")

        plot_type = self.comboBoxPlotType.currentText()
        plot_name = f"{plot_type}_{method}"
        plot_data = {'inertia': inertia, '2nd derivative': second_derivative}

        self.plot_info = {
            'tree': 'Multidimensional Analysis',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': self.comboBoxPlotType.currentText(),
            'field_type':self.comboBoxColorByField.currentText(),
            'field':  self.comboBoxColorField.currentText(),
            'figure': canvas,
            'style': self.style.style_dict[self.style.plot_type],
            'cluster_groups': self.cluster_dict[method],
            'view': [True,False],
            'position': [],
            'data': plot_data
            }

        self.clear_layout(self.widgetSingleView.layout())
        self.widgetSingleView.layout().addWidget(canvas)

    def compute_clusters(self, max_clusters=None):
        """Computes cluster results
        
        Cluster properties are defined in the ``MainWindow.toolBox.ClusterPage``."""
        #print('\n===compute_clusters===')
        if self.sample_id == '':
            return

        df_filtered, isotopes = self.data[self.sample_id].get_processed_data()
        filtered_array = df_filtered.values
        array = filtered_array[self.data[self.sample_id].mask]

        # get clustering options
        if max_clusters is None:
            n_clusters = [self.spinBoxNClusters.value()]
        else:
            n_clusters = np.arange(1,max_clusters+1).astype(int)
            cluster_results = []
            silhouette_scores = []

        seed = int(self.lineEditSeed.text())
        method = self.comboBoxClusterMethod.currentText()
        exponent = float(self.horizontalSliderClusterExponent.value()) / 10

        if exponent == 1:
            exponent = 1.0001
        distance_type = self.comboBoxClusterDistance.currentText()

        #self.statusbar.showMessage('Precomputing distance for clustering...')
        # match distance_type:
        #     # euclidean (a.k.a. L2-norm)
        #     case 'euclidean':
        #         distance = euclidean(array)

        #     # manhattan (a.k.a. L1-norm and cityblock)
        #     case 'manhattan':
        #         distance = manhattan(array)

        #     # mahalanobis = MahalanobisDistance(n_components=n_pca_basis)
        #     case 'mahalanobis':
        #         inv_cov_matrix = np.linalg.inv(np.cov(array))

        #         distance = np.array([mahalanobis(x, np.mean(array, axis=0), inv_cov_matrix) for x in array])

        #     # fisher-rao (a.k.a. cosine?) = FisherRaoDistance()
        #     case 'cosine':
        #         distance = cosine_distances(array)


        # set all masked data to cluster id -1
        if max_clusters is None:
            self.data[self.sample_id].processed_data[method] = 99

            # Create labels array filled with -1
            #groups = np.full(filtered_array.shape[0], -1, dtype=int)
            self.toolButtonGroupMask.blockSignals(True)
            self.toolButtonGroupMaskInverse.blockSignals(True)
            self.toolButtonGroupMask.setChecked(False)
            self.toolButtonGroupMaskInverse.setChecked(False)
            self.toolButtonGroupMask.blockSignals(False)
            self.toolButtonGroupMaskInverse.blockSignals(False)

        self.statusbar.showMessage('Computing clusters...')
        match method:
            # k-means
            case 'k-means':
                # setup k-means
                for nc in n_clusters:
                    kmeans = KMeans(n_clusters=nc, init='k-means++', random_state=seed)

                    # produce k-means model from data
                    model = kmeans.fit(array)

                    #add k-means results to self.data
                    if max_clusters is None:
                        self.data[self.sample_id].add_columns('cluster', method, model.predict(array), self.data[self.sample_id].mask)
                    else:
                        kmeans.fit(array)
                        cluster_results.append(kmeans.inertia_)

                        if nc == 1:
                            silhouette_scores.append(0)
                        else:
                            silhouette_scores.append(silhouette_score(array, kmeans.labels_, sample_size=1000))
                        print(f"{nc}: {silhouette_scores}")

            # fuzzy c-means
            case 'fuzzy c-means':
                for nc in n_clusters:
                    # compute cluster scores
                    cntr, u, _, dist, _, _, _ = fuzz.cluster.cmeans(array.T, nc, exponent, error=0.00001, maxiter=1000, seed=seed)
                    #cntr, u, _, _, _, _, _ = fuzz.cluster.cmeans(array.T, n_clusters, exponent, metric='precomputed', error=0.00001, maxiter=1000, seed=seed)
                    # cntr, u, _, _, _, _, _ = fuzz.cluster.cmeans(array.T, n_clusters, exponent, error=0.005, maxiter=1000,seed =23)

                    labels = np.argmax(u, axis=0)

                    if max_clusters is None:
                        # assign cluster scores to self.data
                        for n in range(nc):
                            #self.data[self.sample_id]['computed_data']['cluster score'].loc[:,str(n)] = pd.NA
                            self.data[self.sample_id].add_columns('cluster score', 'cluster' + str(n), u[n-1,:], self.data[self.sample_id].mask)

                        #add cluster results to self.data
                        self.data[self.sample_id].add_columns('cluster', method, labels, self.data[self.sample_id].mask)
                    else:
                        # weighted sum of squared errors (WSSE)
                        wsse = np.sum((u ** exponent) * (dist ** 2))
                        cluster_results.append(wsse)

                        if nc == 1:
                            silhouette_scores.append(0)
                        else:
                            silhouette_scores.append(silhouette_score(array, labels, sample_size=1000))
                        print(f"{nc}: {silhouette_scores}")
            
        if max_clusters is None:
            # make sure the column is all integer values
            self.data[self.sample_id].processed_data[method] = self.data[self.sample_id].processed_data[method].astype(int)  

            # update cluster table in style menu
            self.group_changed()

            self.statusbar.showMessage('Clustering successful')

            self.update_all_field_comboboxes()
            self.update_cluster_flag = False
        else:
            return cluster_results, silhouette_scores

    def plot_clusters(self):
        """Plot maps associated with clustering

        Will produce plots of Clusters or Cluster Scores and computes clusters if necesseary.
        """        
        print('plot_clusters')
        if self.sample_id == '':
            return

        method = self.comboBoxClusterMethod.currentText()
        if self.update_cluster_flag or \
                self.data[self.sample_id].processed_data[method].empty or \
                (method not in list(self.data[self.sample_id].processed_data.columns)):
            self.compute_clusters()


        self.cluster_dict['active method'] = method

        plot_type = self.comboBoxPlotType.currentText()

        match plot_type:
            case 'cluster':
                self.comboBoxColorField.setCurrentText(method)
                plot_name = f"{plot_type}_{method}_map"
                canvas, plot_data = self.plot_cluster_map()
            case 'cluster score':
                plot_name = f"{plot_type}_{method}_{self.comboBoxColorField.currentText()}_score_map"
                canvas, plot_data = self.plot_score_map()
            case _:
                print(f'Unknown PCA plot type: {plot_type}')
                return

        self.style.update_figure_font(canvas, self.style.font)

        self.plot_info = {
            'tree': 'Multidimensional Analysis',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': self.comboBoxPlotType.currentText(),
            'field_type':self.comboBoxColorByField.currentText(),
            'field':  self.comboBoxColorField.currentText(),
            'figure': canvas,
            'style': self.style.style_dict[self.style.plot_type],
            'cluster_groups': self.cluster_dict[method],
            'view': [True,False],
            'position': [],
            'data': plot_data
            }

        self.clear_layout(self.widgetSingleView.layout())
        self.widgetSingleView.layout().addWidget(canvas)

    def number_of_clusters_callback(self):
        """Updates cluster dictionary with the new number of clusters

        Updates ``MainWindow.cluster_dict[*method*]['n_clusters'] from ``MainWindow.spinBoxNClusters``.  Updates cluster results.
        """
        self.cluster_dict[self.comboBoxClusterMethod.currentText()]['n_clusters'] = self.spinBoxNClusters.value()

        self.update_cluster_flag = True
        self.update_SV()

    def cluster_distance_callback(self):
        """Updates cluster dictionary with the new distance metric

        Updates ``MainWindow.cluster_dict[*method*]['distance'] from ``MainWindow.comboBoxClusterDistance``.  Updates cluster results.
        """
        self.cluster_dict[self.comboBoxClusterMethod.currentText()]['distance'] = self.comboBoxClusterDistance.currentText()

        self.update_cluster_flag = True
        self.update_SV()

    def cluster_exponent_callback(self):
        """Updates cluster dictionary with the new exponent

        Updates ``MainWindow.cluster_dict[*method*]['exponent'] from ``MainWindow.horizontalSliderClusterExponent``.  Updates cluster results.
        """
        self.cluster_dict[self.comboBoxClusterMethod.currentText()]['exponent'] = self.horizontalSliderClusterExponent.value()/10

        self.update_cluster_flag = True
        self.update_SV()
    
    def cluster_seed_callback(self):
        """Updates cluster dictionary with the new exponent

        Updates ``MainWindow.cluster_dict[*method*]['seed'] from ``MainWindow.lineEditSeed``.  Updates cluster results.
        """
        self.cluster_dict[self.comboBoxClusterMethod.currentText()]['exponent'] = int(self.lineEditSeed.text())

        self.update_cluster_flag = True
        self.update_SV()

    def generate_random_seed(self):
        """Generates a random seed for clustering

        Updates ``MainWindow.cluster_dict[*method*]['seed'] using a random number generator with one of 10**9 integers. 
        """        
        r = random.randint(0,1000000000)
        self.lineEditSeed.value = r
        self.cluster_dict[self.comboBoxClusterMethod.currentText()]['seed'] = r

        self.update_cluster_flag = True
        self.update_SV()

    def cluster_method_callback(self):
        """Updates clustering-related widgets

        Enables/disables widgets in *Left Toolbox \\ Clustering* page.  Updates widget values/text with values saved in ``MainWindow.cluster_dict``.
        """
        print('cluster_method_callback')
        if self.sample_id == '':
            return

        # update_clusters_ui - Enables/disables tools associated with clusters
        method = self.comboBoxClusterMethod.currentText()
        self.cluster_dict['active method'] = method

        if method not in self.data[self.sample_id].processed_data.columns:
            self.update_cluster_flag = True

        # Number of Clusters
        self.labelNClusters.setEnabled(True)
        self.spinBoxNClusters.blockSignals(True)
        self.spinBoxNClusters.setEnabled(True)
        self.spinBoxNClusters.setValue(int(self.cluster_dict[method]['n_clusters']))
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
                self.lineEditSeed.value = self.cluster_dict[method]['seed']

            case 'fuzzy c-means':
                # Enable parameters relevant to Fuzzy Clustering
                # Exponent
                self.labelExponent.setEnabled(True)
                self.labelClusterExponent.setEnabled(True)
                self.horizontalSliderClusterExponent.setEnabled(True)
                self.horizontalSliderClusterExponent.setValue(int(self.cluster_dict[method]['exponent']*10))

                # Distance
                self.labelClusterDistance.setEnabled(True)
                self.comboBoxClusterDistance.setEnabled(True)
                self.comboBoxClusterDistance.setCurrentText(self.cluster_dict[method]['distance'])

                # Seed
                self.labelClusterStartingSeed.setEnabled(True)
                self.lineEditSeed.setEnabled(True)
                self.lineEditSeed.value = self.cluster_dict[method]['seed']

        if self.update_cluster_flag:
            self.update_SV()

    def update_clusters(self):
        """Executed on update to cluster table.

        Updates ``MainWindow.cluster_dict`` and plot when the selected cluster have changed.
        """        
        if not self.isUpdatingTable:
            selected_clusters = []
            method = self.cluster_dict['active method']

            # get the selected clusters
            for idx in self.tableWidgetViewGroups.selectionModel().selectedRows():
                selected_clusters.append(idx.row())
            selected_clusters.sort()

            # update selected cluster list in cluster_dict
            if selected_clusters:
                if np.array_equal(self.cluster_dict[method]['selected_clusters'], selected_clusters):
                    return
                self.cluster_dict[method]['selected_clusters'] = selected_clusters
            else:
                self.cluster_dict[method]['selected_clusters'] = []

            # update plot
            if (self.comboBoxPlotType.currentText() not in ['cluster', 'cluster score']) and (self.comboBoxColorByField.currentText() == 'cluster'):
                self.update_SV()

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


    # -------------------------------------
    # TEC and Radar plots
    # -------------------------------------

    def plot_ndim(self):
        """Produces trace element compatibility (TEC) and Radar plots
        
        Geochemical TEC diagrams are a staple of geochemical analysis, often referred to as spider diagrams, which display a set of elements
        arranged by compatibility.  Radar plots show data displayed on a set of radial spokes (axes), giving the appearance of a radar screen
        or spider web.
        
        The function updates ``MainWindow.plot_info`` with the displayed plot metadata and figure ``mplc.MplCanvas`` for display in the centralWidget views.
        """
        if not self.ndim_list:
            return

        df_filtered, _  = self.data[self.sample_id].get_processed_data()

        match self.comboBoxNorm.currentText():
            case 'log':
                df_filtered.loc[:,:] = 10**df_filtered.values
            case 'mixed':
                pass
            case 'linear':
                # do nothing
                pass
        df_filtered = df_filtered[self.data[self.sample_id].mask]

        ref_i = self.comboBoxNDimRefMaterial.currentIndex()

        plot_type = self.comboBoxPlotType.currentText()
        plot_data = None

        # Get quantile for plotting TEC & radar plots
        match self.comboBoxNDimQuantiles.currentIndex():
            case 0:
                quantiles = [0.5]
            case 1:
                quantiles = [0.25, 0.75]
            case 2:
                quantiles = [0.25, 0.5, 0.75]
            case 3:
                quantiles = [0.05, 0.25, 0.5, 0.75, 0.95]

        # remove mass from labels
        if self.checkBoxShowMass.isChecked():
            angle = 45
        else:
            angle = 0
        labels = self.style.toggle_mass(self.ndim_list)
            
        if self.comboBoxColorByField.currentText() == 'cluster' and self.comboBoxColorField.currentText() != '':
            method = self.comboBoxColorField.currentText()
            cluster_dict = self.cluster_dict[method]
            cluster_color, cluster_label, cmap = self.style.get_cluster_colormap(cluster_dict, alpha=self.style.marker_alpha)

            clusters = cluster_dict['selected_clusters']
            if 0 in list(cluster_dict.keys()):
                cluster_flag = True
            else:
                cluster_dict = None
                cluster_flag = False
                print(f'No cluster data found for {method}, recompute?')
        else:
            cluster_dict = None
            cluster_flag = False

        
        match plot_type:
            case 'Radar':
                canvas = mplc.MplCanvas(parent=self, proj='radar')

                axes_interval = 5
                if cluster_flag and method in self.data[self.sample_id].processed_data.columns:
                    # Get the cluster labels for the data
                    cluster_group = self.data[self.sample_id].processed_data[method][self.data[self.sample_id].mask]

                    df_filtered['clusters'] = cluster_group
                    df_filtered = df_filtered[df_filtered['clusters'].isin(clusters)]
                    radar = Radar( 
                        canvas.axes,
                        df_filtered,
                        fields=self.ndim_list,
                        fieldlabels=labels,
                        quantiles=quantiles,
                        axes_interval=axes_interval,
                        group_field='clusters',
                        groups=clusters)

                    canvas.fig, canvas.axes = radar.plot(cmap = cmap)
                    canvas.axes.legend(loc='upper right', frameon='False')
                else:
                    radar = Radar(canvas.axes, df_filtered, fields=self.ndim_list, fieldlabels=labels, quantiles=quantiles, axes_interval=axes_interval, group_field='', groups=None)
                        
                    radar.plot()
                    
                    plot_data = radar.vals
                    
            case 'TEC':
                canvas = mplc.MplCanvas(parent=self)

                yl = [np.inf, -np.inf]
                if cluster_flag and method in self.data[self.sample_id].processed_data.columns:
                    # Get the cluster labels for the data
                    cluster_group = self.data[self.sample_id].processed_data[method][self.data[self.sample_id].mask]

                    df_filtered['clusters'] = cluster_group

                    # Plot tec for all clusters
                    for i in clusters:
                        # Create RGBA color
                        #print(f'Cluster {i}')
                        canvas.axes, yl_tmp, _ = plot_spider_norm(
                                data=df_filtered.loc[df_filtered['clusters']==i,:],
                                ref_data=self.ref_data, norm_ref_data=self.ref_data['model'][ref_i],
                                layer=self.ref_data['layer'][ref_i], el_list=self.ndim_list ,
                                style='Quanta', quantiles=quantiles, ax=canvas.axes, c=cluster_color[i], label=cluster_label[i]
                            )
                        #store max y limit to convert the set y limit of axis
                        yl = [np.floor(np.nanmin([yl[0] , yl_tmp[0]])), np.ceil(np.nanmax([yl[1] , yl_tmp[1]]))]

                    # Put a legend below current axis
                    box = canvas.axes.get_position()
                    canvas.axes.set_position((box.x0, box.y0 - box.height * 0.1, box.width, box.height * 0.9))

                    self.add_colorbar(canvas, None, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
                    #canvas.axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3, handlelength=1)

                    self.logax(canvas.axes, yl, 'y')
                    canvas.axes.set_ylim(yl)

                    canvas.axes.set_xticklabels(labels, rotation=angle)
                else:
                    canvas.axes, yl, plot_data = plot_spider_norm(data=df_filtered, ref_data=self.ref_data, norm_ref_data=self.ref_data['model'][ref_i], layer=self.ref_data['layer'][ref_i], el_list=self.ndim_list, style='Quanta', quantiles=quantiles, ax=canvas.axes)

                    canvas.axes.set_xticklabels(labels, rotation=angle)
                canvas.axes.set_ylabel(f"Abundance / [{self.ref_data['model'][ref_i]}, {self.ref_data['layer'][ref_i]}]")
                canvas.fig.tight_layout()

        if cluster_flag:
            plot_name = f"{plot_type}_"
        else:
            plot_name = f"{plot_type}_all"

        self.style.update_figure_font(canvas, self.style.font)

        self.plot_info = {
            'tree': 'Geochemistry',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': plot_type,
            'field_type': 'analyte',
            'field': self.ndim_list,
            'figure': canvas,
            'style': self.style.style_dict[self.style.plot_type],
            'cluster_groups': cluster_dict,
            'view': [True,False],
            'position': [],
            'data': plot_data
        }

        self.clear_layout(self.widgetSingleView.layout())
        self.widgetSingleView.layout().addWidget(canvas)

    def update_ndim_table(self,calling_widget):
        # Updates N-Dim table

        # :param calling_widget:
        # :type calling_widget: QWidget
        # 
        def on_use_checkbox_state_changed(row, state):
            # Update the 'use' value in the filter_df for the given row
            self.data[self.sample_id].filter_df.at[row, 'use'] = state == Qt.Checked

        if calling_widget == 'analyteAdd':
            el_list = [self.comboBoxNDimAnalyte.currentText().lower()]
            self.comboBoxNDimAnalyteSet.setCurrentText = 'user defined'
        elif calling_widget == 'analytesetAdd':
            el_list = self.ndim_list_dict[self.comboBoxNDimAnalyteSet.currentText()]

        analytes_list = self.data[self.sample_id].processed_data.match_attribute('data_type','analyte')

        analytes = [col for iso in el_list for col in analytes_list if re.sub(r'\d', '', col).lower() == re.sub(r'\d', '',iso).lower()]

        self.ndim_list.extend(analytes)

        for analyte in analytes:
            # Add a new row at the end of the table
            row = self.tableWidgetNDim.rowCount()
            self.tableWidgetNDim.insertRow(row)

            # Create a QCheckBox for the 'use' column
            chkBoxItem_use = QCheckBox()
            chkBoxItem_use.setCheckState(Qt.Checked)
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
                QMessageBox.warning(None,'Error','could not save TEC file.')
                
        else:
            # throw a warning that name is not saved
            QMessageBox.warning(None,'Error','could not save TEC list.')

            return

    def logax(self,ax, lim, axis='y', label='', tick_label_rotation=0):
        """
        Produces log-axes limits and labels.

        Parameters:
        ax (matplotlib.axes.Axes): The axes to modify.
        lim (list): The log10 values of the axes limits.
        axis (str): 'x' or 'y' to add ticks to x- or y-axis, default is 'y'.
        label (str): Label for the axis.
        tick_label_rotation (float): Angle of text rotation, default is 0.
        """
        # Create tick marks and labels
        mt = np.log10(np.arange(1, 10))
        ticks = []
        tick_labels = []
        for i in range(int(lim[0]), int(lim[1]) + 1):
            ticks.extend([i + m for m in mt])
            tick_labels.extend([f'$10^{{{i}}}$'] + [''] * (len(mt) - 1))

        # Apply settings based on the axis
        if axis.lower() == 'x':
            ax.set_xticks(ticks)
            ax.set_xticklabels(tick_labels, rotation=tick_label_rotation)
            ax.set_xlim([10**lim[0], 10**lim[1]])
            if label:
                ax.set_xlabel(label)
        elif axis.lower() == 'y':
            ax.set_yticks(ticks)
            ax.set_yticklabels(tick_labels, rotation=tick_label_rotation)
            ax.set_ylim([10**lim[0], 10**lim[1]])
            if label:
                ax.set_ylabel(label)
        else:
            print('Incorrect axis argument. Please use "x" or "y".')

    def group_changed(self):
        if self.sample_id == '':
            return

        # block signals
        self.tableWidgetViewGroups.blockSignals(True)
        self.spinBoxClusterGroup.blockSignals(True)

        # Clear the list widget
        self.tableWidgetViewGroups.clearContents()
        self.tableWidgetViewGroups.setHorizontalHeaderLabels(['Name','Link','Color'])

        method = self.comboBoxClusterMethod.currentText()
        if method in self.data[self.sample_id].processed_data.columns:
            if not self.data[self.sample_id].processed_data[method].empty:
                clusters = self.data[self.sample_id].processed_data[method].dropna().unique()
                clusters.sort()

                self.cluster_dict[method]['selected_clusters'] = []
                try:
                    self.cluster_dict[method].pop(99)
                except:
                    pass

                i = 0
                while True:
                    try:
                        self.cluster_dict[method].pop(i)
                        i += 1
                    except:
                        break


                # set number of rows in tableWidgetViewGroups
                # set default colors for clusters and update associated widgets
                self.spinBoxClusterGroup.setMinimum(1)
                if 99 in clusters:
                    self.tableWidgetViewGroups.setRowCount(len(clusters)-1)
                    self.spinBoxClusterGroup.setMaximum(len(clusters)-1)

                    hexcolor = self.style.set_default_cluster_colors(mask=True)
                else:
                    self.tableWidgetViewGroups.setRowCount(len(clusters))
                    self.spinBoxClusterGroup.setMaximum(len(clusters))

                    hexcolor = self.style.set_default_cluster_colors(mask=False)

                for c in clusters:
                    if c == 99:
                        cluster_name = 'Mask'
                        self.cluster_dict[method].update({c: {'name':cluster_name, 'link':[], 'color':hexcolor[-1]}})
                        break
                    else:
                        cluster_name = f'Cluster {c+1}'

                    # Initialize the flag
                    self.isUpdatingTable = True
                    self.tableWidgetViewGroups.setItem(c, 0, QTableWidgetItem(cluster_name))
                    self.tableWidgetViewGroups.setItem(c, 1, QTableWidgetItem(''))
                    # colors in table are set by self.style.set_default_cluster_colors()
                    #self.tableWidgetViewGroups.setItem(i, 2, QTableWidgetItem(cluster_color))
                    self.tableWidgetViewGroups.selectRow(c)
                    
                    self.cluster_dict[method].update({c: {'name':cluster_name, 'link':[], 'color':hexcolor[c]}})

                if 99 in clusters:
                    self.cluster_dict[method]['selected_clusters'] = clusters[:-1]
                else:
                    self.cluster_dict[method]['selected_clusters'] = clusters
        else:
            print(f'(group_changed) Cluster method, ({method}) is not defined')

        #print(self.cluster_dict)
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

            old_name = self.cluster_dict[self.cluster_dict['active method']][cluster_id]['name']
            # Check for duplicate names
            for i in range(self.tableWidgetViewGroups.rowCount()):
                if i != row and self.tableWidgetViewGroups.item(i, 0).text() == new_name:
                    # Duplicate name found, revert to the original name and show a warning
                    item.setText(old_name)
                    QMessageBox.warning(self, "Clusters", "Duplicate name not allowed.")
                    return

            # Update self.data[self.sample_id].processed_data with the new name
            if self.cluster_dict['active method'] in self.data[self.sample_id].processed_data.columns:
                # Find the rows where the value matches cluster_id
                rows_to_update = self.data[self.sample_id].processed_data.loc[:,self.cluster_dict['active method']] == cluster_id

                # Update these rows with the new name
                self.data[self.sample_id].processed_data.loc[rows_to_update, self.cluster_dict['active method']] = new_name

            # update current_group to reflect the new cluster name
            self.cluster_dict[self.cluster_dict['active method']][cluster_id]['name'] = new_name

            # update plot with new cluster name
            self.update_SV()


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
        if self.sample_id == '':
            return

        data_type_dict = self.data[self.sample_id].get_attribute_dict('data_type')

        match plot_type.lower():
            case 'correlation' | 'histogram' | 'tec':
                if 'cluster' in data_type_dict:
                    field_list = ['cluster']
                else:
                    field_list = []
            case 'cluster score':
                if 'cluster score' in data_type_dict:
                    field_list = ['cluster score']
                else:
                    field_list = []
            case 'cluster':
                if 'cluster' in data_type_dict:
                    field_list = ['cluster']
                else:
                    field_list = ['cluster score']
            case 'cluster performance':
                field_list = []
            case 'pca score':
                if 'pca score' in data_type_dict:
                    field_list = ['PCA score']
                else:
                    field_list = []
            case 'ternary map':
                self.labelCbarDirection.setEnabled(True)
                self.comboBoxCbarDirection.setEnabled(True)
            case _:
                field_list = ['Analyte', 'Analyte (normalized)']

                # add check for ratios
                if 'ratio' in data_type_dict:
                    field_list.append('Ratio')
                    field_list.append('Ratio (normalized)')

                if 'pca score' in data_type_dict:
                    field_list.append('PCA score')

                if 'cluster' in data_type_dict:
                    field_list.append('Cluster')

                if 'cluster score' in data_type_dict:
                    field_list.append('Cluster score')

        self.style.toggle_style_widgets()

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

    # updates field comboboxes for analysis and plotting
    def update_field_combobox(self, parentBox, childBox):
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
        if parentBox is None:
            fields = self.get_field_list('Analyte')
        else:
            fields = self.get_field_list(set_name=parentBox.currentText())

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

    # updates all field type and field comboboxes
    def update_all_field_comboboxes(self):
        """Updates all field type and field comboBoxes"""
        # histograms
        self.update_field_type_combobox(self.comboBoxHistFieldType)
        self.update_field_combobox(self.comboBoxHistFieldType, self.comboBoxHistField)

        # filters
        self.update_field_type_combobox(self.comboBoxFilterFieldType)
        self.update_field_combobox(self.comboBoxFilterFieldType, self.comboBoxFilterField)

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
        self.update_field_type_combobox(self.comboBoxProfileFieldType)
        self.update_field_combobox(self.comboBoxProfileFieldType, self.comboBoxProfileField)


        # colors
        addNone = True
        if self.comboBoxPlotType.currentText() in ['analyte map','PCA score','cluster','cluster score']:
            addNone = False
        self.update_field_type_combobox(self.comboBoxColorByField, addNone=addNone, plot_type=self.comboBoxPlotType.currentText())
        self.update_field_combobox(self.comboBoxColorByField, self.comboBoxColorField)
        self.spinBoxColorField.setFixedWidth(22)
        self.spinBoxColorField.setMinimum(0)
        self.spinBoxColorField.setMaximum(self.comboBoxColorField.count() - 1)

        # calculator
        self.update_field_combobox(self.comboBoxCalcFieldType, self.comboBoxCalcField)

        # dating
        self.update_field_combobox(self.comboBoxIsotopeAgeFieldType1, self.comboBoxIsotopeAgeField1)
        self.update_field_combobox(self.comboBoxIsotopeAgeFieldType2, self.comboBoxIsotopeAgeField2)
        self.update_field_combobox(self.comboBoxIsotopeAgeFieldType3, self.comboBoxIsotopeAgeField3)


    # gets the set of fields
    def get_field_list(self, set_name='Analyte'):
        """Gets the fields associated with a defined set

        Set names are consistent with QComboBox.

        Parameters
        ----------
        set_name : str, optional
            name of set list, options include ``Analyte``, ``Analyte (normalized)``, ``Ratio``, ``Calcualated Field``,
            ``PCA Score``, ``Cluster``, ``Cluster Score``, ``Special``, Defaults to ``Analyte``

        Returns
        -------
        list
            Set_fields, a list of fields within the input set
        """
        if self.sample_id == '':
            return ['']

        data = self.data[self.sample_id].processed_data

        match set_name:
            case 'Analyte' | 'Analyte (normalized)':
                set_fields = data.match_attributes({'data_type': 'analyte', 'use': True})
            case 'Ratio' | 'Ratio (normalized)':
                set_fields = data.match_attributes({'data_type': 'ratio', 'use': True})
            case 'None':
                return []
            case _:
                #populate field name with column names of corresponding dataframe remove 'X', 'Y' is it exists
                #set_fields = [col for col in self.data[self.sample_id]['computed_data'][set_name].columns.tolist() if col not in ['X', 'Y']]
                set_fields = data.match_attribute('data_type', set_name.lower())

        return set_fields

    def check_analysis_type(self):
        """Updates field type/field paired comboBoxes
        
        .. seealso::
            ``MainWindow.update_field_type_combobox`` and ``MainWindow.update_field_combobox``
        """
        #print('check_analysis_type')
        self.check_analysis = True
        self.update_field_type_combobox(self.comboBoxColorByField, addNone=True, plot_type=self.comboBoxPlotType.currentText())
        self.update_field_combobox(self.comboBoxColorByField, self.comboBoxColorField)
        self.spinBoxColorField.setMinimum(0)
        self.spinBoxColorField.setMaximum(self.comboBoxColorField.count() - 1)
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
        data = self.data[self.sample_id].processed_data
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
            self.lineEditFMin.value = data[field].min()
            self.lineEditFMax.value = data[field].max()
            self.callback_lineEditFMin()
            self.callback_lineEditFMax()

    def update_ratio_df(self,sample_id,analyte_1, analyte_2,norm):
        parameter = self.data[sample_id]['ratio_info'].loc[(self.data[sample_id]['ratio_info']['analyte_1'] == analyte_1) & (self.data[sample_id]['ratio_info']['analyte_2'] == analyte_2)]
        if parameter.empty:
            ratio_info = {'sample_id': self.sample_id, 'analyte_1':analyte_1, 'analyte_2':analyte_2, 'norm': norm,
                            'upper_bound':np.nan,'lower_bound':np.nan,'d_bound':np.nan,'use': True,'auto_scale': True}
            self.data[sample_id]['ratio_info'].loc[len(self.data[sample_id]['ratio_info'])] = ratio_info

            self.prep_data(sample_id, analyte_1=analyte_1, analyte_2=analyte_2)
            self.update_labels()

    def toggle_help_mode(self):
        """Toggles help mode

        Toggles ``MainWindow.actionHelp``, when checked, the cursor will change so indicates help tool is active.
        """        
        if self.actionHelp.isChecked():
            self.setCursor(Qt.WhatsThisCursor)
        else:
            self.setCursor(Qt.ArrowCursor)


    # -------------------------------
    # Plot Info Tab functions
    # -------------------------------
    def update_plot_info_tab(self, plot_info, write_info=True, level=0):
        """Prints plot info in the information tab
        
        Prints ``plot_info`` into the bottom information tab ``MainWindow.textEditPlotInfo``.

        Parameters
        ----------
        plot_info : dict
            Plot information dictionary.
        write_info : bool
            Flag to write dictionary contents when ``True``. When calling ``update_plot_info`` is used
            recursively to handle dictionaries within dictionaries, the flag is set to ``False``. By default ``True``
        level : int
            Indent level, by default ``0``

        Returns
        -------
        str
            When called recursively, a string is returned
        """
        content = ''
        if level > 0:
            indent = '&nbsp;'*(4*level)
        else:
            indent = ''

        for key, value in plot_info.items():
            if isinstance(value,str):
                if value == '':
                    content += f"{indent}<b>{key}:</b> ''<br>"
                else:
                    content += f"{indent}<b>{key}:</b> {value}<br>"
            elif isinstance(value,list) | isinstance(value,int) | isinstance(value,float):
                content += f"{indent}<b>{key}:</b> {value}<br>"
            elif isinstance(value,dict):
                content += f"{indent}<b>{key}:</b><br>"
                content += self.update_plot_info_tab(value, write_info=False, level=level+1)
            elif value is None:
                content += f"{indent}<b>{key}:</b> None<br>"
            else:
                content += f"{indent}<b>{key}:</b> {str(type(value))}<br>"
            
        if write_info: 
            self.textEditPlotInfo.clear()
            self.textEditPlotInfo.setText(content)
        else:
            return content


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
                self.toolButtonPlotProfile.setChecked(False)
                self.toolButtonPointMove.setChecked(False)
                self.toolButtonPolyCreate.setChecked(False)
                self.toolButtonPolyMovePoint.setChecked(False)
                self.toolButtonPolyAddPoint.setChecked(False)
                self.toolButtonPolyRemovePoint.setChecked(False)
            case 'profiling':
                self.actionCrop.setChecked(False)
                self.toolButtonPolyCreate.setChecked(False)
                self.toolButtonPolyMovePoint.setChecked(False)
                self.toolButtonPolyAddPoint.setChecked(False)
                self.toolButtonPolyRemovePoint.setChecked(False)
            case 'polygon':
                self.actionCrop.setChecked(False)
                self.toolButtonPlotProfile.setChecked(False)
                self.toolButtonPointMove.setChecked(False)

    def partial_match_in_list(self, lst, string):
        """Checks whether values in a list partially match a string

        Parameters
        ----------
        lst: list
            List of partial strings to find in ``string``
        string: str
            Text to test.

        Returns
        -------
        bool
            ``True`` if a match exists, ``False`` if no items match.
        """    
        for test_string in lst:
            if test_string in string:
                return True
        return False


# -------------------------------
# Classes
# -------------------------------

# Mask object
# -------------------------------
class MaskObj:
    def __init__(self, initial_value=None):
        self._value = initial_value
        self._callbacks = []

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        old_value = self._value
        self._value = new_value 
        self._notify_observers(old_value, new_value)

    def _notify_observers(self, old_value, new_value):
        for callback in self._callbacks:
            callback(old_value, new_value)
    
    def register_callback(self, callback):
        self._callbacks.append(callback)


# -------------------------------
# MAIN FUNCTION!!!
# Sure doesn't look like much
# -------------------------------
app = None
def create_app():
    global app
    app = QApplication(sys.argv)

    # Enable high-DPI scaling
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)

    if darkdetect.isDark():
        ss = load_stylesheet('dark.qss')
        app.setStyleSheet(ss)
    else:
        ss = load_stylesheet('light.qss')
        app.setStyleSheet(ss)

    return app

def show_splash():
    pixmap = QPixmap("lame_splash.png")
    splash = QSplashScreen(pixmap)
    splash.setMask(pixmap.mask())
    splash.show()
    QTimer.singleShot(3000, splash.close)

def main():
    app = create_app()
    show_splash()

    # Uncomment this line to set icon to App
    app.setWindowIcon(QIcon(os.path.join(BASEDIR, os.path.join(ICONPATH,'LaME-64.svg'))))
    main = MainWindow()

    # Set the main window to fullscreen
    #main.showFullScreen()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()