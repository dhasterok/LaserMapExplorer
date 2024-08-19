import sys, os, re, copy, random, pickle, darkdetect
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import (
    Qt, QTimer, QRectF, QPointF, QUrl, pyqtSlot, QSize, QEvent
)
from PyQt5.QtWidgets import (
    QColorDialog, QCheckBox, QComboBox,  QTableWidgetItem, QVBoxLayout, QGridLayout,
    QMessageBox, QHeaderView, QMenu, QGraphicsRectItem, QLineEdit, QFileDialog, QWidget,
    QDialog, QLabel, QTableWidget, QInputDialog, QAbstractItemView, QProgressBar,
    QSplashScreen, QDialogButtonBox, QApplication, QMainWindow, QSizePolicy, QGraphicsPolygonItem
)
from PyQt5.QtGui import (
    QIntValidator, QDoubleValidator, QColor, QImage, QPainter, QPixmap, QFont, QPen, QPalette,
    QCursor, QBrush, QStandardItemModel, QStandardItem, QTextCursor, QDropEvent, QFontDatabase, QIcon, QWindow
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
import pyqtgraph as pg
from pyqtgraph.GraphicsScene import exportDialog
from pyqtgraph import (
    setConfigOption, colormap, ColorBarItem,ViewBox, TargetItem, ImageItem,
    GraphicsLayoutWidget, ScatterPlotItem, AxisItem, PlotDataItem
)
from datetime import datetime
import numpy as np
import numexpr as ne
import pandas as pd
pd.options.mode.copy_on_write = True

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.projections.polar import PolarAxes
from matplotlib.collections import PathCollection
import matplotlib.gridspec as gs
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import Patch
import matplotlib.colors as colors
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
import cmcrameri as cmc
from scipy import ndimage
from scipy.signal import convolve2d, wiener, decimate
from scipy.stats import yeojohnson, percentileofscore
from sklearn.cluster import KMeans
#from sklearn_extra.cluster import KMedoids
import skfuzzy as fuzz
import cv2
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from src.ternary_plot import ternary
from src.plot_spider import plot_spider_norm
from src.scalebar import scalebar
import src.lame_fileio as lameio
#import src.radar_factory
from src.radar import Radar
from src.ui.MainWindow import Ui_MainWindow
from src.ui.PreferencesWindow import Ui_PreferencesWindow
from src.AnalyteSelectionWindow import AnalyteDialog
#from src.WebEngineView import WebEngine
import src.MapImporter as MapImporter
import src.SpotImporter as SpotImporter
from src.ui.QuickViewDialog import Ui_QuickViewDialog
from rst2pdf.createpdf import RstToPdf
from docutils.core import publish_string
from lame_helper import BASEDIR, ICONPATH, SSPATH, load_stylesheet
from src.ExtendedDF import AttributeDataFrame
import src.CustomWidgets
import src.format as fmt

setConfigOption('imageAxisOrder', 'row-major') # best performance
## sphinx-build -b html docs/source/ docs/build/html
## !pyrcc5 resources.qrc -o src/ui/resources_rc.py
## !pyuic5 designer/mainwindow.ui -o src/ui/MainWindow.py
## !pyuic5 designer/QuickViewDialog.ui -o src/ui/QuickViewDialog.py
## !pyuic5 -x designer/AnalyteSelectionDialog.ui -o src/ui/AnalyteSelectionDialog.py
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
        data : dict
            Dictionary containing a dictionary of each sample with the raw, processed, and computed (analyses) DataFrames, mask array, and informational dataframes
            with relevant data.  The dictionary is nested with the first level keys defined by the sample ID.
            
            [*sample_id*] : (str) -- sample identifier
                | 'analyte_info' : (dataframe) -- holds information regarding each analyte in sample id,
                    | 'analytes' (str) -- name of analyte
                    | 'sample_id' (str) -- sample id
                    | 'norm' (str) -- type of normalisation used(linear,log,logit)
                    | 'upper_bound' (float) -- upper bound for autoscaling/scaling
                    | 'lower_bound' (float) -- lower bound for autoscaling/scaling
                    | 'd_l_bound' (float) -- difference lower bound for autoscaling
                    | 'd_u_bound' (float) -- difference upper bound for autoscaling
                    | 'v_min' (float) -- max value of analyte
                    | 'v_max' (float) -- min value of analyte
                    | 'auto_scale' (bool) -- indicates whether auto_scaling is switched on for that analyte, use percentile bounds if False
                    | 'use' (bool) -- indicates whether the analyte is being used in the analysis
                | 'ratio_info' : (dataframe) -- holds information  regarding computerd ratios 
                    | 'analyte_1' (str) -- name of analyte at numerator of ratio
                    | 'analyte_2' (str) -- name of analyte at denominator of ratio
                    | 'norm' (str) -- type of normalisation used(linear,log,logit)
                    | 'upper_bound' (float) --  upper bound for autoscaling/scaling
                    | 'lower_bound' (float) --  lower bound for autoscaling/scaling
                    | 'd_l_bound' (float) --  difference lower bound for autoscaling
                    | 'd_u_bound' (float) --  difference upper bound for autoscaling
                    | 'v_min' (float) -- max value of analyte
                    | 'v_max' (float) -- min value of analyte
                    | 'auto_scale' (bool) -- indicates whether auto_scaling is switched on for that analyte, use percentile bounds if False
                    | 'use' (bool) -- indicates whether the analyte is being used in the analysis
                
                | 'crop' : () --
                | 'x_max' : () --
                | 'x_min' : () --
                | 'y_max' : () --
                | 'y_min' : () --
                | 'crop_x_max' : () --
                | 'crop_x_min' : () --
                | 'crop_y_max' : () --
                | 'crop_y_min' : () --
                | 'processed data': () --
                | 'raw_data': () -- 
                | 'cropped_raw_data': () --
                
            | 'ratio_info' : (dataframe) --
            | 'crop' : () --
            | 'x_max' : () --
            | 'x_min' : () --
            | 'y_max' : () --
            | 'y_min' : () --
            | 'crop_x_max' : () --
            | 'crop_x_min' : () --
            | 'crop_y_max' : () --
            | 'crop_y_min' : () --
            | 'processed data': () --
            | 'raw_data': () -- 
            | 'cropped_raw_data': () -- 
            | 'raw data' : (pandas.DataFrame) --
            | 'x_min' : (float) -- minimum x of full data
            | 'x_max' : (float) -- maximum x of full data
            | 'y_min' : (float) -- minimum y of full data
            | 'y_max' : (float) -- maximum y of full data
            | 'crop_x_min' : (float) -- minimum x of cropped data
            | 'crop_x_max' : (float) -- maximum x of cropped data
            | 'crop_x_min' : (float) -- minimum y of cropped data
            | 'crop_x_max' : (float) -- maximum y of cropped data
            | 'norm' : () --
            | 'analysis data' : (pandas.DataFrame) --
            | 'cropped_raw_data' : (pandas.DataFrame) --
            | 'computed_data' : (dict) --
                | 'PCA Score' : (pandas.DataFrame) --
                | 'Cluster' : (pandas.DataFrame) --
                | 'Cluster Score' : (pandas.DataFrame) --
            | 'processed_data' : (pandas.DataFrame) --
            ['filter_info'] : (pandas.DataFrame) -- stores filters for each sample
                | 'field_type' : (str) -- field type
                | 'field' : (str) -- name of field
                | 'norm' : (str) -- scale normalization function, ``linear`` or ``log``
                | 'min' : (float) -- minimum value for filtering
                | 'max' : (float) -- maximum value for filtering
                | 'operator' : (str) -- boolean operator for combining filters, ``and`` or ``or``
                | 'use' : (bool) -- ``True`` indicates the filter should be used to filter data
                | 'persistent' : (bool) -- ``True`` retains the filter when the sample is changed

            | 'axis_mask' : (MaskObj) -- mask created from cropped data.
            | 'filter_mask' : (MaskObj) -- mask created by a combination of filters.  Filters are displayed for the user in ``tableWidgetFilters``.
            | 'polygon_mask' : (MaskObj) -- mask created from selected polygons.
            | 'cluster_mask' : (MaskObj) -- mask created from selected or inverse selected cluster groups.  Once this mask is set, it cannot be reset unless it is turned off, clustering is recomputed, and selected clusters are used to produce a new mask.
            | 'mask' : () -- combined mask, derived from filter_mask & 'polygon_mask' & 'axis_mask'
        left_tab : dict
            Holds the indices for pages in ``toolBox``
        map_plot_types : list
            A list of plots that result in a map, i.e., ['analyte map', 'ternary map', 'PCA Score', 'Cluster', 'Cluster Score'].  This list is generally used as a check when setting certain styles or other plotting behavior related to maps.
        marker_dict : dict
            Dictionary of marker names used to translate ``comboBoxMarker`` to a subset of matplotlib makers symbol, though not all matplotlib markers
            are used.

            - o : circle
            - s : square
            - d : diamond
            - ^ : triangle (up)
            - v : triangle (down)
            - h : hexagon
            - p : pentagon

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
            | 'figure' : (pgGraphicsWidget or MplCanvas) -- object holding figure for display
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
        styles : dict of dict
            Dictionary with plot style information that saves the properties of style widgets.  There is a keyword
            for each plot type listed in ``comboBoxPlotType``.  The exact behavior of each style item may vary depending upon the
            plot type.  While data related to plot and color axes may be stored in *styles*, *axis_dict* stores labels, bounds and scale for most plot fields.

            styles[plot_type] -- plot types include ``analyte map``, ``histogram``, ``correlation``, ``gradient map``, ``scatter``, ``heatmap``, ``ternary map``
            ``TEC``, ``radar``, ``variance``, ``vectors``, ``pca scatter``, ``pca heatmap``, ``PCA Score``, ``Clusters``, ``Cluster Score``, ``profile``

            ['Axes'] -- associated with widgets in the toolBoxTreeView > Styling > Axes tab
                | 'XLabel' : (str) -- x-axis label, set in ``lineEditXLabel``
                | 'YLabel' : (str) -- y-axis label, set in ``lineEditYLabel``
                | 'ZLabel' : (str) -- z-axis label, set in ``lineEditZLabel``, used only for ternary plots
                | 'XLim' : (list of float) -- x-axis bounds, set by ``lineEditXLB`` and ``lineEditXUB`` for the lower and upper bounds
                | 'YLim' : (list of float) -- y-axis bounds, set by ``lineEditYLB`` and ``lineEditYUB`` for the lower and upper bounds
                | 'XScale' : (str) -- x-axis normalization ``linear`` or ``log`` (note for ternary plots the scale is linear), set by ``comboBoxXScale``
                | 'YScale' : (str) -- y-axis normalization ``linear`` or ``log`` (note for ternary plots the scale is linear), set by ``comboBoxYScale``
                | 'TickDir' : (str) -- tick direction for all axes, ``none``, ``in`` or ``out``, set by ``comboBoxTickDirection``
                | 'AspectRatio' : (float) -- aspect ratio of plot area (relative to figure units, not axes), set in ``lineEditAspectRatio``
            ['Text'] -- associated with widgets in the toolBoxTreeView > Styling > Annotations tab
                | 'Font' : (str) -- font type, pulled from the system font library, set in ``fontComboBox``
                | 'Size' : (str) -- font size in points, set in ``doubleSpinBoxFontSize``
            ['Scale'] -- associated with widgets in the toolBoxTreeView > Styling > Annotations tab
                | 'Direction' : (str) -- direction of distance scale bar on maps, options include ``none``, ``horizontal`` and ``vertical``, set by ``comboBoxScaleDirection``
                | 'Location' : (str) -- position of scale bar on maps, options include ``southeast``, ``northeast``, ``northwest``, and ``southwest``, set by ``comboBoxScaleLocation``
                | 'OverlayColor' : (hex str) -- color of overlay objects and annotations, also color of vectors on pca scatter/heatmap, set by ``toolButtonOverlayColor``
            ['Markers'] -- associated with widgets in the toolBoxTreeView > Styling > Markers tab
                | 'Symbol' : (str) -- marker symbol defined by matplotlib styles in the attribute ``markerdict``
                | 'Size' : (int) -- marker size in points, set by ``doubleSpinBoxMarkerSize``
                | 'Alpha' : (int) -- marker transparency, set by ``horizontalSliderMarkerAlpha``
            ['Lines'] -- associated with widgets in the toolBoxTreeView > Styling > Lines tab
                | 'LineWidth' : (float) -- width of line objects, varies between plot types, set by ``comboBoxLineWidth``
                | 'LineColor' : (float) -- width of line objects, varies between plot types, set by ``comboBoxLineWidth``
                | 'Multiplier' : (hex str) -- color of markers, set by ``toolButtonLineColor``
            ['Colors'] -- associated with widgets in the toolBoxTreeView > Styling > Colors tab
                | 'Color' : (hex str) -- color of markers, set by ``toolButtonMarkerColor``
                | 'ColorByField' : (str) -- field type used to set colors in a figure, set by ``comboBoxColorByField``
                | 'Field' : (str) -- field used to set colors in a figure, set by ``comboBoxColorField``
                | 'Colormap' : (str) -- colormap used in figure, set by ``comboBoxFieldColormap``
                | 'Reverse' : (bool) -- inverts colormap, set by ``checkBoxReverseColormap``
                | 'CLim' : (list of float) -- color bounds, set by ``lineEditXLB`` and ``lineEditXUB`` for the lower and upper bounds
                | 'CScale' : (str) -- c-axis normalization ``linear`` or ``log`` (note for ternary plots the scale is linear), set by ``comboBoxYScale``
                | 'Direction' : (str) -- colorbar direction, options include ``none``, ``vertical``, and ``horizontal``, set by ``comboBoxCbarDirection``
                | 'CLabel' : (str) -- colorbar label, set in ``lineEditCbarLabel``
                | 'Resolution' : (int) -- used to set discritization in 2D and ternary heatmaps, set by ``spinBoxHeatmapResolution``
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

        #Initialise nested data which will hold the main sets of data for analysis
        self.data = {}

        # this does not work
        #darkdetect.listener(lambda: self.switch_view_mode(0))
        
        self.clipped_ratio_data = pd.DataFrame()
        self.analyte_data = {}  #stores orginal analyte data
        self.clipped_analyte_data = {} # stores processed analyted data
        # self.data['computed_data'] = {} # stores computed analyted data (ratios, custom fields)
        self.sample_id = ''
        self.aspect_ratio = 1.0
        #self.data = {}
        self.selected_analytes = []
        self.ndim_list = []
        self.lasermaps = {}
        self.prev_plot = ''
        self.order = 'F'
        self.pyqtgraph_widget = None
        self.isUpdatingTable = False
        self.cursor = False
        self.duplicate_plot_info= None
        
        self.project_name = None
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
        #self.mpl_toolbar = NavigationToolbar(MplCanvas())
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
            self.QV_analyte_list = lameio.import_csv_to_dict(os.path.join(BASEDIR,'resources/styles/qv_lists.csv'))
        except:
            self.QV_analyte_list = {'default':['Si29','Ti47','Al27','Cr52','Fe56','Mn55','Mg24','Ca43','K39','Na23','P31',
                'Ba137','Th232','U238','La139','Ce140','Pb206','Pr141','Sr88','Zr90','Hf178','Nd146','Eu153',
                'Gd157','Tb159','Dy163','Ho165','Y89','Er166','Tm169','Yb172','Lu175']}

        self.toolButtonNewList.clicked.connect(lambda: quickView(self))
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

        # set theme
        self.view_mode = 0
        self.switch_view_mode(self.view_mode)
        self.actionViewMode.triggered.connect(lambda: self.switch_view_mode(self.view_mode+1))



        # create dictionaries for default plot styles
        #-------------------------
        self.markerdict = {'circle':'o', 'square':'s', 'diamond':'d', 'triangle (up)':'^', 'triangle (down)':'v', 'hexagon':'h', 'pentagon':'p'}
        self.comboBoxMarker.clear()
        self.comboBoxMarker.addItems(self.markerdict.keys())
        self.map_plot_types = ['analyte map', 'ternary map', 'PCA Score', 'Cluster', 'Cluster Score']

        self.plot_types = {self.left_tab['sample']: [0, 'analyte map', 'correlation'],
            self.left_tab['process']: [0, 'analyte map', 'gradient map', 'histogram'],
            self.left_tab['spot']: [0, 'analyte map', 'gradient map'],
            self.left_tab['polygons']: [0, 'analyte map'],
            self.left_tab['profile']: [0, 'analyte map'],
            self.left_tab['scatter']: [0, 'scatter', 'heatmap', 'ternary map'],
            self.left_tab['ndim']: [0, 'TEC', 'Radar'],
            self.left_tab['multidim']: [0, 'variance','vectors','pca scatter','pca heatmap','PCA Score'],
            self.left_tab['cluster']: [0, 'Cluster', 'Cluster Score'],
            self.left_tab['special']: [0,'analyte map', 'gradient map', 'Cluster Score', 'PCA Score', 'profile']}

        self.styles = {}
        self.load_theme_names()

        # initalize self.comboBoxPlotType
        self.comboBoxPlotType.clear()
        self.comboBoxPlotType.addItems(self.plot_types[self.toolBox.currentIndex()][1:])
        self.comboBoxPlotType.setCurrentIndex(self.plot_types[self.toolBox.currentIndex()][0])
        
        # create analyte sort menu
        sortmenu_items = ['alphabetical', 'atomic number', 'mass', 'compatibility', 'radius']
        SortMenu = QMenu()
        SortMenu.triggered.connect(self.apply_sort)
        self.toolButtonSortAnalyte.setMenu(SortMenu)
        for item in sortmenu_items:
            SortMenu.addAction(item)
        

        # Menu and Toolbar
        #-------------------------
        # Connect the "Open" action to a function
        self.actionOpenSample.triggered.connect(self.open_sample)
        self.actionOpenDirectory.triggered.connect(lambda: self.open_directory(dir_name=None))
        self.actionImportSpots.triggered.connect(self.import_spots)
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
        self.actionImportFiles.triggered.connect(lambda: self.import_files())
        self.actionOpenProject.triggered.connect(lambda: self.open_project())
        self.actionSaveProject.triggered.connect(lambda: self.save_project())
        self.actionSwapAxes.triggered.connect(self.swap_xy)
        self.actionSwapAxes.setEnabled(False)

        self.actionReportBug.triggered.connect(lambda: self.browser.setUrl(QUrl('https://github.com/dhasterok/LaserMapExplorer/issues')))

        #create plot tree
        self.create_tree()
        # self.open_directory()

        #init table_fcn
        self.table_fcn = Table_Fcn(self)

        # Select analyte Tab
        #-------------------------
        self.ref_data = pd.read_excel(os.path.join(BASEDIR,'resources/app_data/earthref.xlsx'))
        self.ref_data = self.ref_data[self.ref_data['sigma']!=1]
        self.sort_data = pd.read_excel(os.path.join(BASEDIR,'resources/app_data/element_info.xlsx'))
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

        self.comboBoxNegativeMethod.addItems(['Ignore negative values', 'Minimum positive value', 'Gradual shift', 'Yeo-Johnson transformation'])
        self.comboBoxNegativeMethod.activated.connect(self.update_neg_handling)

        # Selecting analytes
        #-------------------------
        # Connect the currentIndexChanged signal of comboBoxSampleId to load_data method
        self.comboBoxSampleId.activated.connect(lambda: self.change_sample(self.comboBoxSampleId.currentIndex()))
        self.canvasWindow.currentChanged.connect(self.canvas_changed)

        #normalising
        self.comboBoxNorm.clear()
        self.comboBoxNorm.addItems(['linear','log','logit'])
        self.comboBoxNorm.activated.connect(lambda: self.update_norm(self.sample_id, self.comboBoxNorm.currentText(), update = True))

        self.lineEditResolutionNx.precision = None
        self.lineEditResolutionNy.precision = None

        pixelwidthvalidator = QDoubleValidator()
        pixelwidthvalidator.setBottom(0.0)
        self.lineEditDX.setValidator(pixelwidthvalidator)
        self.lineEditDY.setValidator(pixelwidthvalidator)
        self.lineEditDX.editingFinished.connect(self.update_resolution)
        self.lineEditDY.editingFinished.connect(self.update_resolution)
        self.toolButtonSwapResolution.clicked.connect(self.swap_resolution)

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
        self.swap_xy_val = False

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
        self.noise_red_img = None
        self.grad_img = None
        self.noise_red_options = {'median':{'label1':'Kernel size', 'value1':5, 'label2':None},
            'gaussian':{'label1':'Kernel size', 'value1':5, 'label2':'Sigma', 'value2':self.gaussian_sigma(5)},
            'wiener':{'label1':'Kernel size', 'value1':5, 'label2':None},
            'edge-preserving':{'label1':'Sigma S', 'value1':5, 'label2':'Sigma R', 'value2': 0.2},
            'bilateral':{'label1':'Diameter', 'value1':9, 'label2':'Sigma', 'value2':75}}

        self.comboBoxNoiseReductionMethod.activated.connect(self.noise_reduction_method_callback)
        self.update_noise1_flag = False
        self.spinBoxNoiseOption1.valueChanged.connect(self.noise_reduction_option1_callback)
        self.spinBoxNoiseOption1.setEnabled(False)
        self.labelNoiseOption1.setEnabled(False)
        self.update_noise2_flag = False
        self.doubleSpinBoxNoiseOption2.valueChanged.connect(self.noise_reduction_option2_callback)
        self.doubleSpinBoxNoiseOption2.setEnabled(False)
        self.labelNoiseOption2.setEnabled(False)
        self.checkBoxGradient.stateChanged.connect(self.noise_reduction_method_callback)

        # Initiate crop tool
        self.crop_tool = Crop_tool(self)
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
        self.comboBoxFilterField.activated.connect(self.update_filter_values)

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

        # add edge detection algorithm to aid in creating polygons
        self.edge_img = None
        self.toolButtonEdgeDetect.clicked.connect(self.add_edge_detection)
        self.comboBoxEdgeDetectMethod.activated.connect(self.add_edge_detection)

        # Scatter and Ternary Tab
        #-------------------------
        self.toolButtonTernaryMap.clicked.connect(self.plot_ternarymap)

        self.comboBoxFieldTypeX.activated.connect(lambda: self.update_field_combobox(self.comboBoxFieldTypeX, self.comboBoxFieldX))
        self.comboBoxFieldTypeY.activated.connect(lambda: self.update_field_combobox(self.comboBoxFieldTypeY, self.comboBoxFieldY))
        self.comboBoxFieldTypeZ.activated.connect(lambda: self.update_field_combobox(self.comboBoxFieldTypeZ, self.comboBoxFieldZ))
        self.comboBoxFieldX.activated.connect(self.update_SV)
        self.comboBoxFieldY.activated.connect(self.update_SV)
        self.comboBoxFieldZ.activated.connect(self.update_SV)

        # ternary colormaps
        # create ternary colors dictionary
        df = pd.read_csv(os.path.join(BASEDIR,'resources/styles/ternary_colormaps.csv'))
        self.ternary_colormaps = df.to_dict(orient='records')
        self.comboBoxTernaryColormap.clear()
        schemes = []
        for cmap in self.ternary_colormaps:
            schemes.append(cmap['scheme'])
        self.comboBoxTernaryColormap.addItems(schemes)
        self.comboBoxTernaryColormap.addItem('user defined')

        # dialog for adding and saving new colormaps
        self.toolButtonSaveTernaryColormap.clicked.connect(self.input_ternary_name_dlg)

        # select new ternary colors
        self.toolButtonTCmapXColor.clicked.connect(lambda: self.button_color_select(self.toolButtonTCmapXColor))
        self.toolButtonTCmapYColor.clicked.connect(lambda: self.button_color_select(self.toolButtonTCmapYColor))
        self.toolButtonTCmapZColor.clicked.connect(lambda: self.button_color_select(self.toolButtonTCmapZColor))
        self.toolButtonTCmapMColor.clicked.connect(lambda: self.button_color_select(self.toolButtonTCmapMColor))
        self.comboBoxTernaryColormap.currentIndexChanged.connect(lambda: self.ternary_colormap_changed())
        self.ternary_colormap_changed()

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
        self.tableWidgetViewGroups.selectionModel().selectionChanged.connect(self.update_clusters)

        # Scatter and Ternary Tab
        #-------------------------
        self.comboBoxFieldX.activated.connect(lambda: self.plot_scatter())
        self.comboBoxFieldY.activated.connect(lambda: self.plot_scatter())
        self.comboBoxFieldZ.activated.connect(lambda: self.plot_scatter())


        # N-Dim Tab
        #-------------------------
        analyte_set = ['majors', 'full trace', 'REE', 'metals']
        self.comboBoxNDimAnalyteSet.addItems(analyte_set)
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
        #self.toolButtonNDimSaveList.clicked.connect(self.ndim_table.save_list)

        # N-dim table
        header = self.tableWidgetNDim.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1,QHeaderView.Stretch)
        header.setSectionResizeMode(2,QHeaderView.Stretch)

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
        self.tableWidgetProfilePoints.setSelectionBehavior(QTableWidget.SelectRows)
        self.toolButtonPointUp.clicked.connect(lambda: self.table_fcn.move_row_up(self.tableWidgetProfilePoints))
        self.toolButtonPointDown.clicked.connect(lambda: self.table_fcn.move_row_down(self.tableWidgetProfilePoints))
        self.toolButtonPointDelete.clicked.connect(lambda: self.table_fcn.delete_row(self.tableWidgetProfilePoints))
        self.comboBoxProfileSort.currentIndexChanged.connect(self.plot_profile_and_table)
        self.toolButtonProfileInterpolate.clicked.connect(lambda: self.profiling.interpolate_points(interpolation_distance=int(self.lineEditIntDist.text()), radius= int(self.lineEditPointRadius.text())))
        self.comboBoxPointType.currentIndexChanged.connect(lambda: self.profiling.plot_profiles())
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

        self.comboBoxDatingMethod.activated.connect(self.callback_dating_method)

        self.comboBoxIsotopeAgeFieldType1.activated.connect(lambda: self.update_field_combobox(self.comboBoxIsotopeAgeFieldType1, self.comboBoxIsotopeAgeField1))
        self.comboBoxIsotopeAgeFieldType2.activated.connect(lambda: self.update_field_combobox(self.comboBoxIsotopeAgeFieldType2, self.comboBoxIsotopeAgeField2))
        self.comboBoxIsotopeAgeFieldType3.activated.connect(lambda: self.update_field_combobox(self.comboBoxIsotopeAgeFieldType3, self.comboBoxIsotopeAgeField3))

        self.pushButtonComputeAge.clicked.connect(self.compute_date_map)

        # Styling Tab
        #-------------------------
        # set style theme
        self.comboBoxStyleTheme.activated.connect(self.read_theme)

        # comboBox with plot type
        # overlay and annotation properties
        self.toolButtonOverlayColor.clicked.connect(self.overlay_color_callback)
        self.toolButtonMarkerColor.clicked.connect(self.marker_color_callback)
        self.toolButtonLineColor.clicked.connect(self.line_color_callback)
        self.toolButtonClusterColor.clicked.connect(self.cluster_color_callback)
        self.toolButtonXAxisReset.clicked.connect(lambda: self.axis_reset_callback('x'))
        self.toolButtonYAxisReset.clicked.connect(lambda: self.axis_reset_callback('y'))
        self.toolButtonCAxisReset.clicked.connect(lambda: self.axis_reset_callback('c'))
        self.toolButtonClusterColorReset.clicked.connect(self.set_default_cluster_colors)
        #self.toolButtonOverlayColor.setStyleSheet("background-color: white;")

        setattr(self.comboBoxMarker, "allItems", lambda: [self.comboBoxMarker.itemText(i) for i in range(self.comboBoxMarker.count())])
        setattr(self.comboBoxLineWidth, "allItems", lambda: [self.comboBoxLineWidth.itemText(i) for i in range(self.comboBoxLineWidth.count())])
        setattr(self.comboBoxColorByField, "allItems", lambda: [self.comboBoxColorByField.itemText(i) for i in range(self.comboBoxColorByField.count())])
        setattr(self.comboBoxColorField, "allItems", lambda: [self.comboBoxColorField.itemText(i) for i in range(self.comboBoxColorField.count())])
        setattr(self.comboBoxFieldColormap, "allItems", lambda: [self.comboBoxFieldColormap.itemText(i) for i in range(self.comboBoxFieldColormap.count())])
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

        # colormaps
        # matplotlib colormaps
        self.mpl_colormaps = colormap.listMaps('matplotlib')
        for i in range(len(self.mpl_colormaps) - 1, -1, -1):
            if self.mpl_colormaps[i].endswith('_r'):
                # If the item ends with '_r', remove it from the list
                del self.mpl_colormaps[i]

        # custom colormaps
        self.custom_color_dict = lameio.import_csv_to_dict(os.path.join(BASEDIR,'resources/app_data/custom_colormaps.csv'))
        for key in self.custom_color_dict:
            self.custom_color_dict[key] = [h for h in self.custom_color_dict[key] if h]

        # add list of colormaps to comboBoxFieldColormap and set callbacks
        self.comboBoxFieldColormap.clear()
        self.comboBoxFieldColormap.addItems(list(self.custom_color_dict.keys())+self.mpl_colormaps)
        self.comboBoxFieldColormap.activated.connect(self.field_colormap_callback)
        self.checkBoxReverseColormap.stateChanged.connect(self.colormap_direction_callback)

        # callback functions
        self.comboBoxPlotType.currentIndexChanged.connect(lambda: self.plot_type_callback(update=True))
        self.toolButtonUpdatePlot.clicked.connect(self.update_SV)
        self.toolButtonSaveTheme.clicked.connect(self.input_theme_name_dlg)
        # axes
        self.axis_dict = {}
        self.lineEditXLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('x',self.lineEditXLabel.text()))
        self.lineEditYLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('y',self.lineEditYLabel.text()))
        self.lineEditZLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('z',self.lineEditZLabel.text()))
        self.lineEditCbarLabel.editingFinished.connect(lambda: self.axis_label_edit_callback('c',self.lineEditCbarLabel.text()))

        self.comboBoxXScale.activated.connect(lambda: self.axis_scale_callback(self.comboBoxXScale,'x'))
        self.comboBoxYScale.activated.connect(lambda: self.axis_scale_callback(self.comboBoxYScale,'y'))
        self.comboBoxColorScale.activated.connect(lambda: self.axis_scale_callback(self.comboBoxColorScale,'c'))

        self.lineEditXLB.setValidator(QDoubleValidator())
        self.lineEditXLB.precision = 3
        self.lineEditXLB.toward = 0
        self.lineEditXUB.setValidator(QDoubleValidator())
        self.lineEditXUB.precision = 3
        self.lineEditXUB.toward = 1
        self.lineEditYLB.setValidator(QDoubleValidator())
        self.lineEditYLB.precision = 3
        self.lineEditYLB.toward = 0
        self.lineEditYUB.setValidator(QDoubleValidator())
        self.lineEditYUB.precision = 3
        self.lineEditYUB.toward = 1
        self.lineEditColorLB.setValidator(QDoubleValidator())
        self.lineEditColorLB.precision = 3
        self.lineEditColorLB.toward = 0
        self.lineEditColorUB.setValidator(QDoubleValidator())
        self.lineEditColorUB.precision = 3
        self.lineEditColorUB.toward = 1
        self.lineEditAspectRatio.setValidator(QDoubleValidator())

        self.lineEditXLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('x', 0, float(self.lineEditXLB.text())))
        self.lineEditXUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('x', 1, float(self.lineEditXUB.text())))
        self.lineEditYLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('y', 0, float(self.lineEditYLB.text())))
        self.lineEditYUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('y', 1, float(self.lineEditYUB.text())))
        self.lineEditColorLB.editingFinished.connect(lambda: self.axis_limit_edit_callback('c', 0, float(self.lineEditColorLB.text())))
        self.lineEditColorUB.editingFinished.connect(lambda: self.axis_limit_edit_callback('c', 1, float(self.lineEditColorUB.text())))

        self.lineEditAspectRatio.editingFinished.connect(self.aspect_ratio_callback)
        self.comboBoxTickDirection.activated.connect(self.tickdir_callback)
        # annotations
        self.fontComboBox.activated.connect(self.font_callback)
        self.doubleSpinBoxFontSize.valueChanged.connect(self.font_size_callback)
        # ---------
        # These are tools are for future use, when individual annotations can be added
        self.tableWidgetAnnotation.setVisible(False)
        self.toolButtonAnnotationDelete.setVisible(False)
        self.toolButtonAnnotationSelectAll.setVisible(False)
        # ---------

        # scales
        self.lineEditScaleLength.setValidator(QDoubleValidator())
        self.comboBoxScaleDirection.activated.connect(self.scale_direction_callback)
        self.comboBoxScaleLocation.activated.connect(self.scale_location_callback)
        self.lineEditScaleLength.editingFinished.connect(self.scale_length_callback)
        #overlay color
        self.comboBoxMarker.activated.connect(self.marker_symbol_callback)
        self.doubleSpinBoxMarkerSize.valueChanged.connect(self.marker_size_callback)
        self.horizontalSliderMarkerAlpha.sliderReleased.connect(self.slider_alpha_changed)
        # lines
        self.comboBoxLineWidth.activated.connect(self.line_width_callback)
        self.lineEditLengthMultiplier.editingFinished.connect(self.length_multiplier_callback)
        # colors
        # marker color
        self.comboBoxColorByField.activated.connect(self.color_by_field_callback)
        self.comboBoxColorField.activated.connect(self.color_field_callback)
        self.comboBoxFieldColormap.activated.connect(self.field_colormap_callback)
        self.comboBoxCbarDirection.activated.connect(self.cbar_direction_callback)
        # resolution
        self.spinBoxHeatmapResolution.valueChanged.connect(lambda: self.resolution_callback(update_plot=True))
        # clusters
        self.spinBoxClusterGroup.valueChanged.connect(self.select_cluster_group_callback)


        # Calculator tab
        #-------------------------
        self.calc_filename = os.path.join(BASEDIR,f'resources/app_data/calculator.txt')
        self.calc_load_dict()
        self.add_formula = True
        self.precalculate_custom_fields = False
        self.labelCalcMessage.setWordWrap(True)
        self.textEditCalcScreen.textChanged.connect(self.calc_set_add_formula)
        buttons = [
                ('+', self.pushButtonAdd, self.calc_insert_operator),
                ('-', self.pushButtonSubtract, self.calc_insert_operator),
                ('*', self.pushButtonMultiply, self.calc_insert_operator),
                ('/', self.pushButtonDivide, self.calc_insert_operator),
                ('^()', self.pushButtonPower, self.calc_insert_operator),
                ('^2', self.pushButtonSquare, self.calc_insert_operator),
                ('^-1', self.pushButtonInverse, self.calc_insert_operator),
                ('10^()', self.pushButtonPower10, self.calc_insert_operator),
                ('()', self.pushButtonBrackets, self.calc_insert_operator),
                ('sqrt', self.pushButtonSqrt, self.calc_insert_function),
                ('exp', self.pushButtonExp, self.calc_insert_function),
                ('ln', self.pushButtonLn, self.calc_insert_function),
                ('log', self.pushButtonLog, self.calc_insert_function),
                ('abs', self.pushButtonAbs, self.calc_insert_function),
                ('case', self.pushButtonCase, self.calc_insert_function),
                ('otherwise', self.pushButtonOtherwise, self.calc_insert_function),
                ('grad', self.pushButtonCalcGrad, self.calc_insert_function),
                ('area', self.pushButtonCalcArea, self.calc_insert_function),
                (' < ', self.pushButtonLessThan, self.calc_insert_operator),
                (' > ', self.pushButtonGreaterThan, self.calc_insert_operator),
                (' <= ', self.pushButtonLessThanEqualTo, self.calc_insert_operator),
                (' >= ', self.pushButtonGreaterThanEqualTo, self.calc_insert_operator),
                (' == ', self.pushButtonEqualTo, self.calc_insert_operator),
                (' != ', self.pushButtonNotEqualTo, self.calc_insert_operator),
                (' and ', self.pushButtonAnd, self.calc_insert_operator),
                (' or ', self.pushButtonOr, self.calc_insert_operator),
                (' not ', self.pushButtonNot, self.calc_insert_operator),
                (None, self.toolButtonCalcHelp, self.calc_help),
                (None, self.toolButtonCalcAddField, self.calc_add_field),
                (None, self.toolButtonCalcDelete, self.calc_delete_formula),
                (None, self.toolButtonCalculate, self.calculate_new_field)
            ]

        def create_handler(handler, text=None):
            if text is not None:
                return lambda: handler(text)
            else:
                return handler

        for text, button, handler in buttons:
            button.clicked.connect(create_handler(handler, text))

        self.toolButtonCalcSave.clicked.connect(lambda: self.calculate_new_field(save=True))
        self.comboBoxCalcFormula.activated.connect(self.calc_load_formula)
        self.comboBoxCalcFieldType.currentIndexChanged.connect(lambda: self.update_field_combobox(self.comboBoxCalcFieldType, self.comboBoxCalcField))
        self.toolButtonCalcClear.clicked.connect(self.textEditCalcScreen.clear)
        self.update_field_combobox(self.comboBoxCalcFieldType, self.comboBoxCalcField)

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
        self.notes_file = None
        self.textEditNotes.setFont(QFont("Monaco", 10))
        self.toolButtonNotesImage.clicked.connect(self.notes_add_image)

        # heading menu
        hmenu_items = ['H1','H2','H3']
        formatHeadingMenu = QMenu()
        formatHeadingMenu.triggered.connect(lambda x:self.add_header_line(x.text()))
        self.add_menu(hmenu_items,formatHeadingMenu)
        self.toolButtonNotesHeading.setMenu(formatHeadingMenu)

        # info menu
        infomenu_items = ['Sample info','List analytes used','Current plot details','Filter table','PCA results','Cluster results']
        notesInfoMenu = QMenu()
        notesInfoMenu.triggered.connect(lambda x:self.add_info_note(x.text()))
        self.add_menu(infomenu_items,notesInfoMenu)
        self.toolButtonNotesInfo.setMenu(notesInfoMenu)

        self.toolButtonNotesBold.clicked.connect(lambda: self.format_note_text('bold'))
        self.toolButtonNotesItalic.clicked.connect(lambda: self.format_note_text('italics'))

        # compile rst
        self.toolButtonNotesSave.clicked.connect(self.save_notes_to_pdf)

        # autosave notes
        self.autosaveTimer = QTimer()
        self.autosaveTimer.setInterval(300000)
        self.autosaveTimer.timeout.connect(self.save_notes_file)

        # Plot Info
        #-------------------------
        self.textEditPlotInfo.setReadOnly(True)
        
        # Browser
        #-------------------------
        # self.open_browser()
        # self.browser = WebEngine(self)
        # self.toolButtonBrowserHome.clicked.connect(self.browser_home_callback)
        # self.lineEditBrowserLocation.editingFinished.connect(self.browser_location_callback)
        # self.toolButtonBack.clicked.connect(self.browser.back)
        # self.toolButtonForward.clicked.connect(self.browser.forward)

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
        self.actionCalculator.triggered.connect(lambda: self.toolBoxTreeView.currentIndex(self.right_tab['calculator']))

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

        self.toolBox.currentChanged.connect(self.toolbox_changed)


        # ----start debugging----
        # self.test_get_field_list()
        # ----end debugging----
    
    # -------------------------------------
    # Reset to start
    # -------------------------------------
    def reset_analysis(self, selection='full'):
        if self.sample_id == '':
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
            self.selected_analytes = []
            self.ndim_list = []
            self.lasermaps = {}
            self.treeModel.clear()
            self.prev_plot = ''
            self.create_tree()
            self.change_sample(self.comboBoxSampleId.currentIndex())

            # reset styles
            self.axis_dict = {}
            self.reset_default_styles()

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

    def initialise_samples_and_tabs(self):
        #clear the current analysis
        self.reset_analysis()
        self.sample_ids = [os.path.splitext(file)[0].replace('.lame','') for file in self.csv_files]
        # set first sample id as default
        self.comboBoxSampleId.addItems(self.sample_ids)
        self.comboBoxSampleId.setCurrentIndex(0)
        # Populate the sampleidcomboBox with the file names
        self.canvasWindow.setCurrentIndex(self.canvas_tab['sv'])
        self.change_sample(0)
        self.init_tabs()
        self.profiling.add_samples()
        self.polygon.add_samples()

    # -------------------------------------
    # File I/O related functions
    # -------------------------------------
    def open_sample(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setNameFilter("LaME CSV (*.csv)")
        if dialog.exec_():
            file_list = dialog.selectedFiles()
            self.selected_directory = os.path.dirname(os.path.abspath(file_list[0]))
            
            self.csv_files = [os.path.split(file)[1] for file in file_list if file.endswith('.csv')]
            if self.csv_files == []:
                # warning dialog
                self.statusBar.showMessage("No valid csv files found.")
                return
        else:
            return
        self.initialise_samples_and_tabs()


    def open_directory(self, dir_name=None):
        """Open directory with samples

        Executes on ``MainWindow.actionOpen`` and ``MainWindow.actionOpenDirectory``.  Opening a directory, enables
        the toolboxes.

        Alternatively, *open_dicrectory* is called after ``MapImporter`` successfully completes an import and the tool
        is closed.

        Opens a dialog to select directory filled with samples.  Updates sample list in
        ``MainWindow.comboBoxSampleID`` and comboBoxes associated with analyte lists.  The first sample
        in list is loaded by default.

        Parameters
        ----------
        dir_name : str
            Path to datafiles, if ``None``, an open directory dialog is openend, by default ``None``
        """
        if dir_name is None:
            dialog = QFileDialog()
            dialog.setFileMode(QFileDialog.Directory)
            # Set the default directory to the current working directory
            # dialog.setDirectory(os.getcwd())
            dialog.setDirectory(BASEDIR)
            if dialog.exec_():
                self.selected_directory = dialog.selectedFiles()[0]
            else:
                self.statusBar.showMessage("Open directory canceled.")
                return
        else:
            self.selected_directory = dir_name

        file_list = os.listdir(self.selected_directory)
        self.csv_files = [file for file in file_list if file.endswith('.lame.csv')]
        if self.csv_files == []:
            # warning dialog
            self.statusBar.showMessage("No valid csv files found.")
            return

        self.initialise_samples_and_tabs()

    def populate_spot_table(self):
        """Populates spot table when spot file is opened or sample is changed

        Populates ``MainWindow.tableWidgetSpots``.
        """        
        if self.sample_id == '':
            return
        
        filtered_df = self.spotdata[self.sample_id==self.spotdata['sample_id']]
        filtered_df = filtered_df['sample_id','X','Y','visible','display_text']

        self.tableWidgetSpots.clearContents()
        self.tableWidgetSpots.setRowCount(len(filtered_df))
        header = self.tableWidgetSpots.horizontalHeader()

        for row_index, row in filtered_df.iterrows():
            for col_index, value in enumerate(row):
                self.tableWidgetSpots.setItem(row_index, col_index, QTableWidgetItem(str(value)))
        
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

        if self.sample_id == self.sample_ids[index]:
            # if selected sample id is same as previous
            return

        # stop autosave timer
        self.save_notes_file()
        self.autosaveTimer.stop()

        if self.data:
            # Create and configure the QMessageBox
            messageBoxChangeSample = QMessageBox()
            iconWarning = QtGui.QIcon()
            iconWarning.addPixmap(QtGui.QPixmap(":/icons/resources/icons/icon-warning-64.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)

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

        file_path = os.path.join(self.selected_directory, self.csv_files[index])
        self.sample_id = self.sample_ids[index]

        # notes and autosave timer
        self.notes_file = os.path.join(self.selected_directory,self.sample_id+'.rst')
        # open notes file if it exists
        if os.path.exists(self.notes_file):
            with open(self.notes_file,'r') as file:
                self.textEditNotes.setText(file.read())
        # put current notes into self.textEditNotes
        self.autosaveTimer.start()

        # add sample to sample dictionary
        if self.sample_id not in self.data:
            sample_id = self.sample_id
            #initialise nested dict for each sample
            self.data[self.sample_id] = {}
            #set info dataframes for each sample
            self.data[self.sample_id]['analyte_info'] = pd.DataFrame(columns = ['analytes', 'norm', 'upper_bound', 'lower_bound', 'd_l_bound', 'd_u_bound', 'use'])
            self.data[self.sample_id]['ratio_info'] = pd.DataFrame(columns = [ 'analyte_1', 'analyte_2', 'norm', 'upper_bound', 'lower_bound', 'd_l_bound', 'd_u_bound', 'use', 'auto_scale'])
            self.data[self.sample_id]['filter_info'] = pd.DataFrame(columns = [ 'use', 'field_type', 'field', 'norm', 'min', 'max', 'operator', 'use', 'persistent'])

            #Set crop to false
            self.data[self.sample_id]['crop'] = False

            sample_df = pd.read_csv(file_path, engine='c')
            sample_df = sample_df.loc[:, ~sample_df .columns.str.contains('^Unnamed')]
            # self.data[sample_id] = pd.read_csv(file_path, engine='c')
            self.data[sample_id]['raw_data'] = sample_df
            ######
            # BUG?
            self.selected_analytes = self.data[sample_id]['raw_data'].columns[2:].tolist()
            # The columns used to read [5:] here, but that is from the matlab ExcelConcatenator files
            # The ones from the new import tool should only include an X and Y so only the first two
            # columns should be skipped.  But there may be other cases where other columns can slip
            # in, which should be excluded for LA-ICP-MS data, but may not be for other file types?
            # May need to future proof this line.
            ######
            self.data[sample_id]['computed_data'] = {
                'Ratio':pd.DataFrame(),
                'Calculated': self.add_ree(sample_df),
                'PCA Score':pd.DataFrame(),
                'Cluster':pd.DataFrame(columns = ['fuzzy c-means', 'k-means']),
                'Cluster Score':pd.DataFrame(),
                'Special':pd.DataFrame(),
                }
            analytes = pd.DataFrame()
            analytes['analytes']=self.selected_analytes
            analytes['sample_id'] = sample_id
            analytes['norm'] = 'linear'

            #update self.data['norm']
            self.data[sample_id]['norm'] = {}

            for analyte in self.selected_analytes:
                self.data[sample_id]['norm'][analyte] = 'linear'

            # obtain axis bounds for plotting and cropping, initially the entire map
            self.data[sample_id]['x_max'] = self.data[sample_id]['crop_x_max'] = self.data[sample_id]['raw_data']['X'].max()
            self.data[sample_id]['x_min'] = self.data[sample_id]['crop_x_min'] = self.data[sample_id]['raw_data']['X'].min()
            self.data[sample_id]['y_max'] = self.data[sample_id]['crop_y_max'] = self.data[sample_id]['raw_data']['Y'].max()
            self.data[sample_id]['y_min'] = self.data[sample_id]['crop_y_min'] = self.data[sample_id]['raw_data']['Y'].min()

            # setup a dataframe with parameters for autoscaling and handling negative values for each analyte
            analytes['lower_bound'] = 0.05
            analytes['upper_bound'] = 99.5
            analytes['d_l_bound'] = 0.05 
            analytes['d_u_bound'] = 99
            analytes['v_min'] = None
            analytes['v_max'] = None
            analytes['auto_scale'] = True
            analytes['use'] = True
            analytes['negative_method'] = self.comboBoxNegativeMethod.currentText()
            
            df = self.data[sample_id]['raw_data'][self.selected_analytes]
            # # Replace non-positive values with NaN
            # df_positive = df.where(df > 0, np.nan)
            # # Get the minimum positive values
            # min_positive_values = df_positive.min()
            
            # analytes['min_positive_value'] = min_positive_values
            self.data[sample_id]['analyte_info'] = analytes

            # create dataframes for cropped data and processed data
            self.data[self.sample_id]['cropped_raw_data'] = copy.deepcopy(self.data[self.sample_id]['raw_data'])
            self.data[self.sample_id]['processed_data'] = copy.deepcopy(self.data[self.sample_id]['raw_data'][self.selected_analytes])

            # for plot_type in self.plot_widget_dict.keys():
            #     if sample_id not in self.plot_widget_dict[plot_type]:
            #         self.plot_widget_dict[plot_type][sample_id]={}

            # set mask of size of analyte array
            # self.data[self.sample_id]['axis_mask'] = MaskObj( np.ones_like( self.data[sample_id]['raw_data']['X'], dtype=bool) )
            # self.data[self.sample_id]['axis_mask'].register_callback(self.apply_filters(fullmap=False))
            # self.data[self.sample_id]['filter_mask'] = MaskObj( np.ones_like( self.data[sample_id]['raw_data']['X'], dtype=bool) )
            # self.data[self.sample_id]['filter_mask'].register_callback(self.apply_filters(fullmap=False))
            # self.data[self.sample_id]['polygon_mask'] = MaskObj( np.ones_like( self.data[sample_id]['raw_data']['X'], dtype=bool) )
            # self.data[self.sample_id]['polygon_mask'].register_callback(self.apply_filters(fullmap=False))
            # self.data[self.sample_id]['cluster_mask'] = MaskObj( np.ones_like( self.data[sample_id]['raw_data']['X'], dtype=bool) )
            # self.data[self.sample_id]['cluster_mask'].register_callback(self.apply_filters(fullmap=False))
            self.data[self.sample_id]['axis_mask'] = np.ones_like( self.data[sample_id]['raw_data']['X'], dtype=bool)
            self.data[self.sample_id]['filter_mask'] = np.ones_like( self.data[sample_id]['raw_data']['X'].values, dtype=bool)
            self.data[self.sample_id]['polygon_mask'] = np.ones_like( self.data[sample_id]['raw_data']['X'], dtype=bool)
            self.data[self.sample_id]['cluster_mask'] = np.ones_like( self.data[sample_id]['raw_data']['X'], dtype=bool)
            self.data[self.sample_id]['mask'] = \
                self.data[self.sample_id]['axis_mask'] & \
                self.data[self.sample_id]['filter_mask'] & \
                self.data[self.sample_id]['polygon_mask'] & \
                self.data[self.sample_id]['cluster_mask']

            # autoscale and negative handling
            self.prep_data()

            # determine aspect ratio
            self.compute_map_aspect_ratio()

            #get plot array
            current_plot_df = self.get_map_data(sample_id=sample_id, field=self.selected_analytes[0], field_type='Analyte')
            #set
            self.styles['analyte map']['Colors']['Field'] = self.selected_analytes[0]

            self.create_tree(sample_id)
            self.update_tree(self.data[sample_id]['norm'])
        else:
            #update filters, polygon, profiles with existing data
            self.compute_map_aspect_ratio()

            self.actionClearFilters.setEnabled(False)
            if np.all(self.data[self.sample_id]['filter_mask']):
                self.actionFilterToggle.setEnabled(False)
            else:
                self.actionFilterToggle.setEnabled(True)
                self.actionClearFilters.setEnabled(True)

            if np.all(self.data[self.sample_id]['polygon_mask']):
                self.actionPolygonMask.setEnabled(False)
            else:
                self.actionPolygonMask.setEnabled(True)
                self.actionClearFilters.setEnabled(True)

            if np.all(self.data[self.sample_id]['cluster_mask']):
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
        self.apply_sort(None, method=self.sort_method)

        # reset flags
        self.update_cluster_flag = True
        self.update_pca_flag = True
        self.plot_flag = False

        # precalculate custom fields
        if self.precalculate_custom_fields:
            for name in self.calc_dict.keys():
                if name in self.data[self.sample_id]['computed_data']['Calculated'].columns:
                    continue
                self.comboBoxCalcFormula.setCurrentText(name)
                self.calculate_new_field(save=False)

        #update UI with auto scale and neg handling parameters from 'Analyte Info'
        
        self.update_spinboxes(sample_id=self.sample_id, field_type='Analyte', field = self.analyte_list[0])

        # reset all plot types on change of tab to the first option
        for key in self.plot_types.keys():
            self.plot_types[key][0] = 0
        # set to single-view, tree view, and sample and fields tab
        self.canvasWindow.setCurrentIndex(self.canvas_tab['sv'])
        self.toolBoxStyle.setCurrentIndex(0)
        self.toolBoxTreeView.setCurrentIndex(self.right_tab['tree'])
        self.toolBox.setCurrentIndex(self.left_tab['sample'])
        self.set_style_widgets(self.comboBoxPlotType.currentText())

        self.styles['analyte map']['Colors']['ColorByField'] = 'Analyte'
        self.styles['analyte map']['Colors']['Field'] = self.analyte_list[0] 
        if self.comboBoxPlotType.currentText() != 'analyte map':
            self.comboBoxPlotType.setCurrentText('analyte map')
        self.toolbox_changed(update=False)
        self.update_all_field_comboboxes()
        self.update_field_combobox(self.comboBoxColorByField,self.comboBoxColorField)

        self.update_filter_values()
        self.histogram_update_bin_width()

        # plot first analyte as lasermap
        # self.comboBoxColorByField.setCurrentText(self.styles['analyte map']['Colors']['ColorByField'])
        # self.color_by_field_callback()
        # fields = self.get_field_list('Analyte')
        # self.styles['analyte map']['Colors']['Field'] = fields[0]
        # self.comboBoxColorField.setCurrentText(fields[0])
        # self.initialize_axis_values('Analyte', fields[0])
        # self.color_field_callback()
        # self.set_style_widgets('analyte map')
        
        # update toolbar
        self.canvas_changed()

        self.update_plot = True
        self.update_SV()

    def open_preferences_dialog(self):
        pass

    def import_files(self):
        """Import selected map files."""
        # import data dialog
        self.importDialog = MapImporter.MapImporter(self)
        self.importDialog.show()

        # read directory
        #if self.importDialog.ok:
        #    self.open_directory(dir_name=self.importDialog.root_path)

        # change sample
    
    def import_spots(self):
        """Import a data file with spot data."""
        # import spot dialog
        self.spotDialog = SpotImporter.SpotImporter(self)
        self.spotDialog.show()

        if not self.spotDialog.ok:
            return

        self.populate_spot_table()


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

        analytes_list = self.data[self.sample_id]['analyte_info']['analytes'].values

        self.analyteDialog = AnalyteDialog(analytes_list,self.data[self.sample_id]['norm'], self.data[self.sample_id]['processed_data'], self)
        self.analyteDialog.show()

        result = self.analyteDialog.exec_()  # Store the result here
        if result == QDialog.Accepted:
            #update self.data['norm'] with selection
            self.data[self.sample_id]['norm'] = self.analyteDialog.norm_dict

            self.update_tree(self.data[self.sample_id]['norm'], norm_update = True)
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
        if self.sample_id == '':
            return

        tab_id = self.toolBox.currentIndex()

        # update the plot type comboBox options
        self.comboBoxPlotType.blockSignals(True)
        self.comboBoxPlotType.clear()
        self.comboBoxPlotType.addItems(self.plot_types[tab_id][1:])
        self.comboBoxPlotType.blockSignals(False)

        # set to most used plot type on selected tab
        self.comboBoxPlotType.setCurrentIndex(self.plot_types[tab_id][0])

        # get the current plot type
        #plot_type = self.comboBoxPlotType.currentText()
        #self.set_style_widgets(plot_type=plot_type, style=self.styles[plot_type])

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
                    'top': self.get_hex_color(self.toolButtonTCmapXColor.palette().button().color()),
                    'left': self.get_hex_color(self.toolButtonTCmapYColor.palette().button().color()),
                    'right': self.get_hex_color(self.toolButtonTCmapZColor.palette().button().color()),
                    'center': self.get_hex_color(self.toolButtonTCmapMColor.palette().button().color())})
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
                self.swap_xy_val = not self.swap_xy_val

                if self.swap_xy_val:
                    self.order = 'C'
                else:
                    self.order = 'F'

                # swap x and y
                # print(self.data[self.sample_id][['X','Y']])
                self.swap_xy_data(self.data[self.sample_id]['raw_data'])

                self.swap_xy_data(self.data[self.sample_id]['processed_data']) #this rotates processed data as well

                # self.swap_xy_data(self.data[self.sample_id]['computed_data']['Cluster'])
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

    def swap_xy_data(self, df):
        """Swaps X and Y of a dataframe

        Swaps coordinates for all maps in sample dataframe.

        :param df: data frme to swap X and Y coordinates.
        :type df: pandas.DataFrame
        """
        xtemp = df['Y']
        df['Y'] = df['X']
        df['X'] = xtemp

        # resort values, should be ascending in Y then X
        df = df.sort_values(['Y','X'])

        self.compute_map_aspect_ratio()

    def swap_resolution(self):
        """Swaps DX and DY for a dataframe

        Recalculates X and Y for a dataframe
        """
        X = round(self.data[self.sample_id]['raw_data']['X']/self.dx)
        Y = round(self.data[self.sample_id]['raw_data']['Y']/self.dy)

        Xp = round(self.data[self.sample_id]['processed_data']['X']/self.dx)
        Yp = round(self.data[self.sample_id]['processed_data']['Y']/self.dy)

        dx = self.dx
        self.dx = self.dy
        self.dy = dx

        units = self.preferences['Units']['Distance']
        self.lineEditDX.value = self.dx
        self.lineEditDY.value = self.dy

        self.data[self.sample_id]['raw_data']['X'] = self.dx*X
        self.data[self.sample_id]['raw_data']['Y'] = self.dy*Y

        self.data[self.sample_id]['processed_data']['X'] = self.dx*Xp
        self.data[self.sample_id]['processed_data']['Y'] = self.dy*Yp

        self.compute_map_aspect_ratio()

        self.update_SV()

    def update_resolution(self):
        """Updates DX and DY for a dataframe

        Recalculates X and Y for a dataframe
        """
        X = round(self.data[self.sample_id]['raw_data']['X']/self.dx)
        Y = round(self.data[self.sample_id]['raw_data']['Y']/self.dy)

        Xp = round(self.data[self.sample_id]['processed_data']['X']/self.dx)
        Yp = round(self.data[self.sample_id]['processed_data']['Y']/self.dy)

        self.dx = self.lineEditDX.value
        self.dy = self.lineEditDY.value

        self.data[self.sample_id]['raw_data']['X'] = self.dx*X
        self.data[self.sample_id]['raw_data']['Y'] = self.dy*Y

        self.data[self.sample_id]['processed_data']['X'] = self.dx*Xp
        self.data[self.sample_id]['processed_data']['Y'] = self.dy*Yp

        self.compute_map_aspect_ratio()

        self.update_SV()


    # toolbar functions
    def change_ref_material(self, comboBox1, comboBox2):
        """Changes reference computing normalized analytes

        Sets all QComboBox to a common normalizing reference.

        :param comboBox1: user changed QComboBox
        :type comboBox1: QComboBox
        :param comboBox2: QComboBox to update
        :type comboBox2: QComboBox
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
            item, check = self.find_leaf(tree, branch, leaf=ratio_name)

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

        sample_id = self.plot_info['sample_id']
        #set original bounds
        self.data[sample_id]['crop_x_max'] = self.data[sample_id]['x_max']
        self.data[sample_id]['crop_x_min'] = self.data[sample_id]['x_min']
        self.data[sample_id]['crop_y_max'] = self.data[sample_id]['y_max']
        self.data[sample_id]['crop_y_min'] = self.data[sample_id]['y_min']
        #remove crop overlays
        self.crop_tool.remove_overlays()

        self.data[sample_id]['processed_data'] = copy.deepcopy(self.data[sample_id]['raw_data'])
        self.data[sample_id]['cropped_raw_data'] = copy.deepcopy(self.data[sample_id]['raw_data'])
        self.data[sample_id]['computed_data'] = {
            'Ratio':None,
            'Calculated':None,
            'Special':None,
            'PCA Score':None,
            'Cluster':None,
            'Cluster Score':None
        }

        # reset axis mask and mask
        self.data[self.sample_id]['axis_mask'] = np.ones_like( self.data[sample_id]['raw_data']['X'], dtype=bool)
        self.data[self.sample_id]['mask'] = np.ones_like( self.data[sample_id]['raw_data']['X'], dtype=bool)
        # self.data[self.sample_id]['mask'] = \
        #         self.data[self.sample_id]['axis_mask'] & \
        #         self.data[self.sample_id]['filter_mask'] & \
        #         self.data[self.sample_id]['polygon_mask'] & \
        #         self.data[self.sample_id]['cluster_mask']
        self.prep_data()
        # re-compute aspect ratio
        self.compute_map_aspect_ratio()

        # reapply existing filters
        if self.actionFilterToggle.isChecked():
            self.apply_field_filters(update_plot=False)
            # should look for filters built on computed fields and remove them
        if self.actionPolygonMask.isChecked():
            self.apply_polygon_mask(update_plot=False)

        # reset cluster mask (no valid clustering exists)
        self.actionClusterMask.setEnabled(False)
        self.actionClusterMask.setChecked(False)
        self.data[sample_id]['cluster_mask'] = np.ones_like(self.data[sample_id]['mask'], dtype=bool)

        self.apply_filters(fullmap=False)

        self.data[self.sample_id]['crop'] = False

    # for a disappearing button
    # def mouseEnter(self, event):
    #     self.toolButtonPopFigure.setVisible(True)

    # def mouseLeave(self, event):
    #     self.toolButtonPopFigure.setVisible(False)

    # color picking functions
    def button_color_select(self, button):
        """Select background color of button

        :param button: button clicked
        :type button: QPushbutton | QToolButton
        """
        old_color = button.palette().color(button.backgroundRole())
        color_dlg = QColorDialog(self)
        color_dlg.setCurrentColor(old_color)
        color_dlg.setCustomColor(int(1),old_color)

        color = color_dlg.getColor()

        if color.isValid():
            button.setStyleSheet("background-color: %s;" % color.name())
            QColorDialog.setCustomColor(int(1),color)
            if button.accessibleName().startswith('Ternary'):
                button.setCurrentText('user defined')

    def get_hex_color(self, color):
        """Converts QColor to hex-rgb format

        Parameters
        ----------
        color : list of int
            RGB color triplet

        Returns
        -------
        str : 
            hex code for an RGB color triplet
        """
        if type(color) is tuple:
            color = np.round(255*np.array(color))
            color[color < 0] = 0
            color[color > 255] = 255
            return "#{:02x}{:02x}{:02x}".format(int(color[0]), int(color[1]), int(color[2]))
        else:
            return "#{:02x}{:02x}{:02x}".format(color.red(), color.green(), color.blue())

    def get_rgb_color(self, color):
        """Convert from hex to RGB formatted color

        Parameters
        ----------
        color : str or list
            Converts a hex str to RGB colors.  If list, should be a list of hex str.

        Returns
        -------
        list of int or list of RGB tuples:
            RGB color triplets used to create colormaps.
        """        
        if not color:
            return []
        elif isinstance(color,str):
            color = color.lstrip('#').lower()
            return [int(color[0:2],16), int(color[2:4],16), int(color[4:6],16)]
        else:
            color_list = [None]*len(color)
            for i, hexcolor in enumerate(color):
                rgb = self.get_rgb_color(hexcolor)
                color_list[i] = tuple(float(c)/255 for c in rgb) + (1.0,)
            return color_list

    def ternary_colormap_changed(self):
        """Changes toolButton backgrounds associated with ternary colormap

        Updates ternary colormap when swatch colors are changed in the Scatter and Heatmaps >
        Map from Ternary groupbox.  The ternary colored chemical map is updated.
        """
        for cmap in self.ternary_colormaps:
            if cmap['scheme'] == self.comboBoxTernaryColormap.currentText():
                self.toolButtonTCmapXColor.setStyleSheet("background-color: %s;" % cmap['top'])
                self.toolButtonTCmapYColor.setStyleSheet("background-color: %s;" % cmap['left'])
                self.toolButtonTCmapZColor.setStyleSheet("background-color: %s;" % cmap['right'])
                self.toolButtonTCmapMColor.setStyleSheet("background-color: %s;" % cmap['center'])

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
                self.data[sample_id]['analyte_info']['auto_scale'] = auto_scale
                self.data[sample_id]['analyte_info']['upper_bound']= ub
                self.data[sample_id]['analyte_info']['lower_bound'] = lb
                self.data[sample_id]['analyte_info']['d_l_bound'] = d_lb
                self.data[sample_id]['analyte_info']['d_u_bound'] = d_ub
                # clear existing plot info from tree to ensure saved plots using most recent data
                for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                    self.clear_tree_data(tree)
                self.prep_data(sample_id)
            else:
                self.data[sample_id]['analyte_info'].loc[self.data[sample_id]['analyte_info']['analytes']==analyte_1,
                    'auto_scale'] = auto_scale
                self.data[sample_id]['analyte_info'].loc[self.data[sample_id]['analyte_info']['analytes']==analyte_1,
                    ['upper_bound', 'lower_bound', 'd_l_bound', 'd_u_bound']] = [ub, lb, d_lb, d_ub]
                self.prep_data(sample_id, analyte_1,analyte_2)
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
                    self.clear_tree_data(tree)
                self.prep_data(sample_id)
            else:
                self.data[sample_id]['ratio_info'].loc[ (self.data[sample_id]['ratio_info']['analyte_1']==analyte_1)
                                            & (self.data[sample_id]['ratio_info']['analyte_2']==analyte_2),'auto_scale']  = auto_scale
                self.data[sample_id]['ratio_info'].loc[ (self.data[sample_id]['ratio_info']['analyte_1']==analyte_1)
                                            & (self.data[sample_id]['ratio_info']['analyte_2']==analyte_2),
                                            ['upper_bound','lower_bound','d_l_bound', 'd_u_bound']] = [ub,lb,d_lb, d_ub]
                self.prep_data(sample_id, analyte_1,analyte_2)
        
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
        if '/' in field:
            analyte_1, analyte_2 = field.split(' / ')
        else:
            analyte_1 = field
            analyte_2 = None
            
        if analyte_1 and not analyte_2:
            if self.checkBoxApplyAll.isChecked():
                # Apply to all iolties
                self.data[sample_id]['analyte_info']['negative_method'] = self.comboBoxNegativeMethod.currentText()
                # clear existing plot info from tree to ensure saved plots using most recent data
                for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                    self.clear_tree_data(tree)
                self.prep_data(sample_id)
            else:
                self.data[sample_id]['analyte_info'].loc[self.data[sample_id]['analyte_info']['analytes']==analyte_1,
                'negative_method'] = self.comboBoxNegativeMethod.currentText()
                self.prep_data(sample_id, analyte_1,analyte_2)
        else:
            if self.checkBoxApplyAll.isChecked():
                # Apply to all ratios
                self.data[sample_id]['ratio_info']['negative_method'] = self.comboBoxNegativeMethod.currentText()
                for tree in ['Ratio', 'Ratio (normalized)']:
                    self.clear_tree_data(tree)
                self.prep_data(sample_id)
            else:
                self.data[sample_id]['ratio_info'].loc[ (self.data[sample_id]['ratio_info']['analyte_1']==analyte_1)
                                        & (self.data[sample_id]['ratio_info']['analyte_2']==analyte_2),'negative_method']  = self.comboBoxNegativeMethod.currentText()
                self.prep_data(sample_id, analyte_1,analyte_2)
        
        self.update_filter_values()
        self.update_SV()
        

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
            if axis:
                # Filtering rows based on the conditions on 'X' and 'Y' columns
                self.data[self.sample_id]['axis_mask'] = ((current_plot_df['X'] >= self.data[sample_id]['crop_x_min']) & (current_plot_df['X'] <= self.data[sample_id]['crop_x_max']) &
                               (current_plot_df['Y'] <= current_plot_df['Y'].max() - self.data[sample_id]['crop_y_min']) & (current_plot_df['Y'] >= current_plot_df['Y'].max() - self.data[sample_id]['crop_y_max']))


                #crop original_data based on self.data[self.sample_id]['axis_mask']
                self.data[sample_id]['cropped_raw_data'] = self.data[sample_id]['raw_data'][self.data[self.sample_id]['axis_mask']].reset_index(drop=True)


                #crop clipped_analyte_data based on self.data[self.sample_id]['axis_mask']
                self.data[sample_id]['processed_data'] = self.data[sample_id]['processed_data'][self.data[self.sample_id]['axis_mask']].reset_index(drop=True)

                #crop each df of computed_analyte_data based on self.data[self.sample_id]['axis_mask']
                for analysis_type, df in self.data[sample_id]['computed_data'].items():
                    if isinstance(df, pd.DataFrame):
                        df = df[self.data[self.sample_id]['axis_mask']].reset_index(drop=True)


                self.prep_data(sample_id)

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

    
    def save_project(self):
        projects_dir = os.path.join(BASEDIR, "projects")
        
        # Ensure the projects directory exists
        if not os.path.exists(projects_dir):
            os.makedirs(projects_dir)
        
        # Open QFileDialog to enter a new project name
        file_dialog = QFileDialog(self, "Save Project", projects_dir)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setFileMode(QFileDialog.AnyFile)
        file_dialog.setOption(QFileDialog.ShowDirsOnly, True)
        
        if file_dialog.exec_() == QFileDialog.Accepted:
            selected_dir = file_dialog.selectedFiles()[0]
            
            # Ensure a valid directory name is selected
            if selected_dir:
                self.project_name = os.path.basename(selected_dir)
                project_dir = os.path.join(projects_dir, self.project_name)
                
                # Creating the required directory structure and store raw data
                if not os.path.exists(project_dir):
                    os.makedirs(project_dir)
                    for sample_id in self.data.keys():
                        # create directory for each sample in self.data
                        os.makedirs(os.path.join(project_dir, sample_id))
                        # store raw data
                        self.data[sample_id]['raw_data'].to_csv(os.path.join(project_dir, sample_id, 'lame.csv'), index = False)
                        # create rest of directories
                        os.makedirs(os.path.join(project_dir, sample_id, 'figure_data'))
                        os.makedirs(os.path.join(project_dir, sample_id, 'figures'))
                        os.makedirs(os.path.join(project_dir, sample_id, 'tables'))
                
                # Paths for different files
                # csv_path = os.path.join(project_dir, f'{project_name}.lame.csv')
                # rst_path = os.path.join(project_dir, f'{project_name}.lame.rst')
                # poly_path = os.path.join(project_dir, 'polygon.poly')
                # prfl_path = os.path.join(project_dir, 'profiles.prfl')
                
                # store the lame.csv, lame.rst and lame.pdf files 
                



                # Saving data to the directory structure
                data_dict = {
                    'data': self.data,
                    'styles': self.styles,
                    'axis_dict': self.axis_dict,
                    'plot_infos': self.get_plot_info_from_tree(self.treeModel),
                    'sample_id': self.sample_id,
                    'sample_ids': self.sample_ids
                }
                
                # Save the main data dictionary as a pickle file
                pickle_path = os.path.join(project_dir, f'{self.project_name}.pkl')
                with open(pickle_path, 'wb') as file:
                    pickle.dump(data_dict, file)
                
                for sample_id in self.data.keys():
                    self.profiling.save_profiles(project_dir, sample_id)
                    self.polygon.save_polygons(project_dir, sample_id)
                
                self.statusBar.showMessage("Analysis saved successfully")

    # def open_project(self):
    #     if self.data:
    #         # Create and configure the QMessageBox
    #         messageBoxChangeSample = QMessageBox()
    #         iconWarning = QtGui.QIcon()
    #         iconWarning.addPixmap(QtGui.QPixmap(":/icons/resources/icons/icon-warning-64.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)

    #         messageBoxChangeSample.setWindowIcon(iconWarning)  # Set custom icon
    #         messageBoxChangeSample.setText("Do you want to save current analysis")
    #         messageBoxChangeSample.setWindowTitle("Save analysis")
    #         messageBoxChangeSample.setStandardButtons(QMessageBox.Discard | QMessageBox.Cancel | QMessageBox.Save)

    #         # Display the dialog and wait for user action
    #         response = messageBoxChangeSample.exec_()

    #         if response == QMessageBox.Save:
    #             self.save_project()
    #             self.reset_analysis('sample')
    #         elif response == QMessageBox.Discard:
    #             self.reset_analysis('sample')
    #         else: #user pressed cancel
    #             self.comboBoxSampleId.setCurrentText(self.sample_id)
    #             return
    #     file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Pickle Files (*.pkl);;All Files (*)")
    #     if file_name:
    #         with open(file_name, 'rb') as file:
    #             data_dict = pickle.load(file)
    #         if data_dict:
    #             self.data = data_dict['data']
    #             self.profiling.profiles = data_dict['profiling'] 
    #             self.polygon.polygons = data_dict['polygons'] 
    #             self.styles = data_dict['styles']
    #             self.axis_dict = data_dict['axis_dict']
    #             self.sample_ids = data_dict['sample_ids']
    #             self.sample_id = data_dict['sample_id'] 
    #             self.selected_dirctory= data_dict['selected_directory'] 
    #             self.create_tree(self.sample_id)
    #             #update tree with selected analytes
    #             self.update_tree(self.data[self.sample_id]['norm'], norm_update = False)
    #             #print(data_dict['plot_infos'])
    #             #add plot info to tree
    #             for plot_info in data_dict['plot_infos']:
    #                 if plot_info:
    #                     canvas = MplCanvas(fig=plot_info['figure'])
    #                     plot_info['figure'] = canvas
    #                     self.add_tree_item(plot_info)
            
    #             self.sample_ids = data_dict['sample_ids']
    #             # update sample id combo
    #             self.comboBoxSampleId.clear()
    #             self.comboBoxSampleId.addItems(self.sample_ids)
    #             self.sample_id = data_dict['sample_id']
    #             #compute aspect ratio
    #             self.compute_map_aspect_ratio()
                
    #             #inilialise tabs
    #             self.init_tabs()
    #             self.statusBar.showMessage("Analysis loaded successfully")  
                
                
    #             # reset flags
    #             self.update_cluster_flag = True
    #             self.update_pca_flag = True
    #             self.plot_flag = False

    #             self.update_all_field_comboboxes()
    #             self.update_filter_values()

    #             self.histogram_update_bin_width()

    #             # plot first analyte as lasermap
    #             self.styles['analyte map']['Colors']['ColorByField'] = 'Analyte'
    #             self.comboBoxColorByField.setCurrentText(self.styles['analyte map']['Colors']['ColorByField'])
    #             self.color_by_field_callback()
    #             fields = self.get_field_list('Analyte')
    #             self.styles['analyte map']['Colors']['Field'] = fields[0]
    #             self.comboBoxColorField.setCurrentText(fields[0])
    #             self.color_field_callback()

    #             self.plot_flag = True
    #             self.update_SV()


    def open_project(self):
        if self.data:
            # Create and configure the QMessageBox
            messageBoxChangeSample = QMessageBox()
            iconWarning = QtGui.QIcon()
            iconWarning.addPixmap(QtGui.QPixmap(":/icons/resources/icons/icon-warning-64.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)

            messageBoxChangeSample.setWindowIcon(iconWarning)  # Set custom icon
            messageBoxChangeSample.setText("Do you want to save current analysis?")
            messageBoxChangeSample.setWindowTitle("Save analysis")
            messageBoxChangeSample.setStandardButtons(QMessageBox.Discard | QMessageBox.Cancel | QMessageBox.Save)

            # Display the dialog and wait for user action
            response = messageBoxChangeSample.exec_()

            if response == QMessageBox.Save:
                self.save_project()
                self.reset_analysis('full')
            elif response == QMessageBox.Discard:
                self.reset_analysis('full')
            else:  # user pressed cancel
                self.comboBoxSampleId.setCurrentText(self.sample_id)
                return
        
        projects_dir = os.path.join(BASEDIR, "projects")
        
        # Open QFileDialog to select the project folder
        file_dialog = QFileDialog(self, "Open Project", projects_dir)
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.setOption(QFileDialog.ShowDirsOnly, True)
        
        if file_dialog.exec_() == QFileDialog.Accepted:
            selected_dir = file_dialog.selectedFiles()[0]
            
            # Ensure a valid directory is selected
            if selected_dir:
                project_name = os.path.basename(selected_dir)
                project_dir = os.path.join(projects_dir, project_name)
                
                # Path to the pickle file
                pickle_path = os.path.join(project_dir, f'{project_name}.pkl')
                if os.path.exists(pickle_path):
                    with open(pickle_path, 'rb') as file:
                        data_dict = pickle.load(file)
                    if data_dict:
                        self.data = data_dict['data']
                        self.styles = data_dict['styles']
                        self.axis_dict = data_dict['axis_dict']
                        self.sample_ids = data_dict['sample_ids']
                        self.sample_id = data_dict['sample_id']
                        self.project_name = project_name
                        
                        self.create_tree(self.sample_id)
                        # Update tree with selected analytes
                        self.update_tree(self.data[self.sample_id]['norm'], norm_update=False)
                        # Add plot info to tree
                        for plot_info in data_dict['plot_infos']:
                            if plot_info:
                                canvas = MplCanvas(fig=plot_info['figure'])
                                plot_info['figure'] = canvas
                                self.add_tree_item(plot_info)
                        
                        # Update sample id combo
                        self.comboBoxSampleId.clear()
                        self.comboBoxSampleId.addItems(self.data.keys())
                        # set the comboBoxSampleId with the correct sample id
                        self.comboBoxSampleId.setCurrentIndex(0)
                        self.sample_id = data_dict['sample_id']
                        
                        


                        # Compute aspect ratio
                        self.compute_map_aspect_ratio()
                        
                        # Initialize tabs
                        self.init_tabs()
                        
                        
                        # Reset flags
                        self.update_cluster_flag = True
                        self.update_pca_flag = True
                        self.plot_flag = False

                        self.update_all_field_comboboxes()
                        self.update_filter_values()

                        self.histogram_update_bin_width()

                        # add sample id to self.profiles, self.polygons and load saved profiles and polygons
                        for sample_id in self.data.keys():
                            self.profiling.add_samples()
                            self.profiling.load_profiles(project_dir, sample_id)
                            self.polygon.add_samples()
                            self.polygon.load_polygons(project_dir, sample_id)

                        # Plot first analyte as lasermap
                        self.styles['analyte map']['Colors']['ColorByField'] = 'Analyte'
                        self.comboBoxColorByField.setCurrentText(self.styles['analyte map']['Colors']['ColorByField'])
                        self.color_by_field_callback()
                        fields = self.get_field_list('Analyte')
                        self.styles['analyte map']['Colors']['Field'] = fields[0]
                        self.comboBoxColorField.setCurrentText(fields[0])
                        self.color_field_callback()

                        self.plot_flag = True
                        self.update_SV()

                        self.statusBar.showMessage("Project loaded successfully")
    
    def extract_plot_info(self, item):
        """
        Recursively extract plot_info from QStandardItem and append to a flat list.
        """
        # Retrieve the plot_info from the UserRole data
        plot_info = item.data(Qt.UserRole)
        if isinstance(plot_info, dict) and 'figure' in plot_info:
            # Check if it contains an MplCanvas object
            if isinstance(plot_info['figure'], MplCanvas):
                # Create a copy of plot_info and replace the MplCanvas object with its Figure
                plot_info_copy = plot_info.copy()
                plot_info_copy['figure'] = plot_info['figure'].fig
                self.plot_info_list.append(plot_info_copy)

        # Recursively process each child of this item
        for i in range(item.rowCount()):
            child = item.child(i)
            if child:
                self.extract_plot_info(child)  # Process child recursively

    def get_plot_info_from_tree(self, model):
        """
        Extract plot_info data from the root of QStandardItemModel as a flat list.
        """
        self.plot_info_list = []  # Reset the list each time this method is called
        root = model.invisibleRootItem()
        for i in range(root.rowCount()):
            self.extract_plot_info(root.child(i))
        return self.plot_info_list
     
    def create_item_from_data(self,data):
        """Recursively create QStandardItem from data."""
        item = QStandardItem(data['text'])
        if 'plot_info' in data.keys():
            #create new matplotlib canvas and save fig
            canvas = MplCanvas(fig=data['plot_info']['figure'])
            data['plot_info']['figure'] = canvas
            #store plot dictionary in tree
            item.setData(data['plot_info'], role=Qt.UserRole)
        for child_data in data['children']:
            child_item = self.create_item_from_data(child_data)
            item.appendRow(child_item)
        return item

    def update_tables(self):
        self.update_filter_table(reload = True)
        self.profiling.update_table_widget()
        self.polygon.update_table_widget()
        pass


    # -------------------------------
    # Crop functions - also see Crop_tool class below
    # -------------------------------
    def apply_crop(self):
        
        sample_id = self.plot_info['sample_id']
        field_type = self.comboBoxColorByField.currentText()
        field = self.comboBoxColorField.currentText()
        current_plot_df = self.get_map_data(sample_id, field, field_type=field_type)
        
        self.data[self.sample_id]['axis_mask'] = ((current_plot_df['X'] >= self.data[sample_id]['crop_x_min']) & (current_plot_df['X'] <= self.data[sample_id]['crop_x_max']) &
                       (current_plot_df['Y'] <=  self.data[sample_id]['crop_y_max']) & (current_plot_df['Y'] >= self.data[sample_id]['crop_y_min']))


        #crop original_data based on self.data[self.sample_id]['axis_mask']
        self.data[sample_id]['cropped_raw_data'] = self.data[sample_id]['raw_data'][self.data[self.sample_id]['axis_mask']].reset_index(drop=True)

        #crop clipped_analyte_data based on self.data[self.sample_id]['axis_mask']
        self.data[sample_id]['processed_data'] = self.data[sample_id]['processed_data'][self.data[self.sample_id]['axis_mask']].reset_index(drop=True)

        #crop each df of computed_analyte_data based on self.data[self.sample_id]['axis_mask']
        for analysis_type, df in self.data[sample_id]['computed_data'].items():
            if isinstance(df, pd.DataFrame):
                self.data[sample_id]['computed_data'][analysis_type] = df[self.data[self.sample_id]['axis_mask']].reset_index(drop=True)

        self.data[self.sample_id]['mask'] = self.data[self.sample_id]['mask'][self.data[self.sample_id]['axis_mask']]
        self.data[self.sample_id]['polygon_mask'] = self.data[self.sample_id]['polygon_mask'][self.data[self.sample_id]['axis_mask']]
        self.data[self.sample_id]['filter_mask'] = self.data[self.sample_id]['filter_mask'][self.data[self.sample_id]['axis_mask']]
        self.prep_data(sample_id)
        #self.update_all_plots()
        # compute new aspect ratio
        self.compute_map_aspect_ratio()
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

            self.data[sample_id]['mask'] = np.ones_like(self.data[sample_id]['mask'], dtype=bool)
            return

        # apply interval filters
        if self.actionFilterToggle.isChecked():
            filter_mask = self.data[sample_id]['filter_mask']
        else:
            filter_mask = np.ones_like( self.data[sample_id]['mask'], dtype=bool)

        # apply polygon filters
        if self.actionPolygonMask.isChecked():
            polygon_mask = self.data[sample_id]['polygon_mask']
        else:
            polygon_mask = np.ones_like( self.data[sample_id]['mask'], dtype=bool)

        # apply cluster mask
        if self.actionClusterMask.isChecked():
            # apply map mask
            cluster_mask = self.data[sample_id]['cluster_mask']
        else:
            cluster_mask = np.ones_like( self.data[sample_id]['mask'], dtype=bool)

        self.data[sample_id]['mask'] = self.data[sample_id]['axis_mask'] & filter_mask & polygon_mask & cluster_mask

        # if single view is active
        if self.canvasWindow.currentIndex() == self.canvas_tab['sv']:
            self.update_SV()

    # Field filter functions
    # -------------------------------
    def update_filter_values(self):
        field_type = self.comboBoxFilterFieldType.currentText()
        field = self.comboBoxFilterField.currentText()

        if not field:
            return

        if 'Analyte' in field_type:
            f_val =  self.data[self.sample_id]['analyte_info'].loc[(self.data[self.sample_id]['analyte_info']['analytes'] == field)].iloc[0][['v_min', 'v_max']]
        elif 'Ratio' in field_type:
            if '/' in field:
                analyte_1, analyte_2 = field.split(' / ')
                f_val = self.data[self.sample_id]['ratio_info'].loc[(self.data[self.sample_id]['ratio_info']['analyte_1'] == analyte_1) & (self.data[self.sample_id]['ratio_info']['analyte_2'] == analyte_2)].iloc[0][['v_min', 'v_max']]
        else:
            pass

        self.lineEditFMin.value = f_val['v_min']
        self.callback_lineEditFMin()
        self.lineEditFMax.value = f_val['v_max']
        self.callback_lineEditFMax()

    def callback_lineEditFMin(self):
        """Updates ``MainWindow.doubleSpinBoxFMinQ.value`` when ``MainWindow.lineEditFMin.value`` is changed"""        
        if self.sample_id == '':
            return
        try:
            array = self.get_map_data(self.sample_id, self.comboBoxFilterField.currentText(), field_type=self.comboBoxFilterFieldType.currentText())['array'].dropna()
        except:
            return

        self.doubleSpinBoxFMinQ.blockSignals(True)
        self.doubleSpinBoxFMinQ.setValue(percentileofscore(array, self.lineEditFMin.value))
        self.doubleSpinBoxFMinQ.blockSignals(False)

    def callback_lineEditFMax(self):
        """Updates ``MainWindow.doubleSpinBoxFMaxQ.value`` when ``MainWindow.lineEditFMax.value`` is changed"""        
        if self.sample_id == '':
            return

        try:
            array = self.get_map_data(self.sample_id, self.comboBoxFilterField.currentText(), field_type=self.comboBoxFilterFieldType.currentText())['array'].dropna()
        except:
            return

        self.doubleSpinBoxFMaxQ.blockSignals(True)
        self.doubleSpinBoxFMaxQ.setValue(percentileofscore(array, self.lineEditFMax.value))
        self.doubleSpinBoxFMaxQ.blockSignals(False)

    def callback_doubleSpinBoxFMinQ(self):
        """Updates ``MainWindow.lineEditFMin.value`` when ``MainWindow.doubleSpinBoxFMinQ.value`` is changed"""        
        array = self.get_map_data(self.sample_id, self.comboBoxFilterField.currentText(), field_type=self.comboBoxFilterFieldType.currentText())['array'].dropna()

        self.lineEditFMin.value = np.percentile(array, self.doubleSpinBoxFMinQ.value())

    def callback_doubleSpinBoxFMaxQ(self):
        """Updates ``MainWindow.lineEditFMax.value`` when ``MainWindow.doubleSpinBoxFMaxQ.value`` is changed"""        
        array = self.get_map_data(self.sample_id, self.comboBoxFilterField.currentText(), field_type=self.comboBoxFilterFieldType.currentText())['array'].dropna()

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
            for index, row in self.data[self.sample_id]['filter_info'].iterrows():
                current_row = self.tableWidgetFilters.rowCount()
                self.tableWidgetFilters.insertRow(current_row)

                # Create and set the checkbox for 'use'
                chkBoxItem_use = QCheckBox()
                chkBoxItem_use.setCheckState(QtCore.Qt.Checked if row['use'] else QtCore.Qt.Unchecked)
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
                chkBoxItem_select.setCheckState(QtCore.Qt.Checked if row.get('select', False) else QtCore.Qt.Unchecked)
                self.tableWidgetFilters.setCellWidget(current_row, 7, chkBoxItem_select)

        else:
            # open tabFilterList
            self.tabWidget.setCurrentIndex(self.bottom_tab['filter'])

            def on_use_checkbox_state_changed(row, state):
                # Update the 'use' value in the filter_df for the given row
                self.data[self.sample_id]['filter_info'].at[row, 'use'] = state == QtCore.Qt.Checked

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
            chkBoxItem_use.setCheckState(QtCore.Qt.Checked)
            chkBoxItem_use.stateChanged.connect(lambda state, row=row: on_use_checkbox_state_changed(row, state))

            chkBoxItem_select = QTableWidgetItem()
            chkBoxItem_select.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                QtCore.Qt.ItemIsEnabled)

            if 'Analyte' in field_type:
                chkBoxItem_select.setCheckState(QtCore.Qt.Unchecked)
                analyte_1 = field
                analyte_2 = None
                scale = self.data[self.sample_id]['analyte_info'].loc[(self.data[self.sample_id]['analyte_info']['analytes'] == field)].iloc[0]['norm']
            elif 'Ratio' in field_type:
                chkBoxItem_select.setCheckState(QtCore.Qt.Unchecked)
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
            self.data[self.sample_id]['filter_info'].loc[len(self.data[self.sample_id]['filter_info'])] = filter_info

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
            if chkBoxItem.checkState() == QtCore.Qt.Checked:
                self.tableWidgetFilters.removeRow(row)
                self.data[sample_id]['filter_info'].drop(self.data[sample_id]['filter_info'][(self.data[sample_id]['filter_info']['field'] == field)].index, inplace=True)

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
            self.data[self.sample_id]['filter_info'].to_csv(filter_file, index=False)

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
        self.data[self.sample_id]['filter_info'] = filter_info

        self.update_filter_table()

    def apply_field_filters(self, update_plot=True):
        """Creates the field filter for masking data

        Updates ``MainWindow.data[sample_id]['filter_mask']`` and if ``update_plot==True``, updates ``MainWindow.data[sample_id]['mask']``.

        Parameters
        ----------
        update_plot : bool, optional
            If true, calls ``MainWindow.apply_filters`` which also calls ``MainWindow.update_SV``, by default True
        """        
        sample_id = self.sample_id

        # create array of all true
        self.data[sample_id]['filter_mask'] = np.ones_like(self.data[sample_id]['mask'], dtype=bool)

        # remove all masks
        self.actionClearFilters.setEnabled(True)
        self.actionFilterToggle.setEnabled(True)
        self.actionFilterToggle.setChecked(True)

        # apply interval filters
        #print(self.data[sample_id]['filter_info'])

        # Check if rows in self.data[sample_id]['filter_info'] exist and filter array in current_plot_df
        # by creating a mask based on min and max of the corresponding filter analytes
        for index, filter_row in self.data[sample_id]['filter_info'].iterrows():
            if filter_row['use']:
                analyte_df = self.get_map_data(sample_id=sample_id, field=filter_row['field'], field_type=filter_row['field_type'])
                
                operator = filter_row['operator']
                if operator == 'and':
                    self.data[sample_id]['filter_mask'] = self.data[sample_id]['filter_mask'] & ((filter_row['min'] <= analyte_df['array'].values) & (analyte_df['array'].values <= filter_row['max']))
                elif operator == 'or':
                    self.data[sample_id]['filter_mask'] = self.data[sample_id]['filter_mask'] | ((filter_row['min'] <= analyte_df['array'].values) & (analyte_df['array'].values <= filter_row['max']))

        if update_plot:
            self.apply_filters(fullmap=False)

    # Polygon mask functions
    # -------------------------------
    def apply_polygon_mask(self, update_plot=True):
        """Creates the polygon mask for masking data

        Updates ``MainWindow.data[sample_id]['polygon_mask']`` and if ``update_plot==True``, updates ``MainWindow.data[sample_id]['mask']``.

        Parameters
        ----------
        update_plot : bool, optional
            If true, calls ``MainWindow.apply_filters`` which also calls ``MainWindow.update_SV``, by default True
        """        
        sample_id = self.sample_id

        # create array of all true
        self.data[sample_id]['polygon_mask'] = np.ones_like(self.data[sample_id]['mask'], dtype=bool)

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

                points = np.vstack((self.x, self.y)).T

                # Use the path to determine which points are inside the polygon
                inside_polygon = path.contains_points(points)

                # Reshape the result back to the shape of self.array
                # inside_polygon_mask = inside_polygon.reshape(self.array.shape)

                # Update the polygon mask - include points that are inside this polygon
                self.data[sample_id]['polygon_mask'] &= inside_polygon

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
        on or off by changing the checked state of ``MainWindow.actionClusterMask`` on the *Left Toolbox \> Filter Page*.

        Updates ``MainWindow.data[sample_id]['cluster_mask']`` and if ``update_plot==True``, updates ``MainWindow.data[sample_id]['mask']``.

        Parameters
        ----------
        inverse : bool, optional
            Inverts selected clusters to define the mask when ``MainWindow.toolButtonGroupMaskInverse`` is clicked, otherwise
            the selected clusers are used to define the mask when ``MainWindow.toolButtonGroupMask`` is clicked, by default False
        update_plot : bool, optional
            If true, calls ``MainWindow.apply_filters`` which also calls ``MainWindow.update_SV``, by default True
        """
        sample_id = self.sample_id

        #self.data[sample_id]['cluster_mask'] = np.ones_like(self.data[sample_id]['mask'], dtype=bool)

        method = self.cluster_dict['active method']
        selected_clusters = self.cluster_dict[method]['selected_clusters']

        # Invert list of selected clusters
        if not inverse:
            selected_clusters = [cluster_idx for cluster_idx in range(self.cluster_dict[method]['n_clusters']) if cluster_idx not in selected_clusters]

        # create boolean array with selected_clusters == True
        cluster_group = self.data[sample_id]['computed_data']['Cluster'].loc[:,method]
        ind = np.isin(cluster_group, selected_clusters)
        self.data[sample_id]['cluster_mask'] = ind

        self.actionClearFilters.setEnabled(True)
        self.actionClusterMask.setEnabled(True)
        self.actionClusterMask.setChecked(True)

        self.update_cluster_flag = True

        if update_plot:
            self.apply_filters(fullmap=False)


    def update_norm(self,sample_id, norm=None, analyte_1=None, analyte_2=None, update=False):
        """Update the norm of the data.

        Parameters
        ----------
        sample_id : str
            Sample identifier
        norm : str, optional
            Data scale method ``linear`` or ``log``, by default None
        analyte_1 : str, optional
            Analyte, numerator of ratio if *analyte_2* is not None, by default None
        analyte_2 : str, optional
            Denominator of ratio, by default None
        update : bool, optional
            Update the scal information of the data, by default False
        """        
        if analyte_1: #if normalising single analyte
            if not analyte_2: #not a ratio
                self.data[sample_id]['analyte_info'].loc[(self.data[sample_id]['analyte_info']['sample_id']==sample_id)
                                 & (self.data[sample_id]['analyte_info']['analytes']==analyte_1),'norm'] = norm
                analytes = [analyte_1]
            else:
               self.data[sample_id]['ratio_info'].loc[
                   (self.data[sample_id]['ratio_info']['analyte_1'] == analyte_1) &
                   (self.data[sample_id]['ratio_info']['analyte_2'] == analyte_2),'norm'] = norm
               analytes = [analyte_1+' / '+analyte_2]

        else: #if normalising all analytes in sample
            self.data[sample_id]['analyte_info'].loc[(self.data[sample_id]['analyte_info']['sample_id']==sample_id),'norm'] = norm
            analytes = self.data[sample_id]['analyte_info'][self.data[sample_id]['analyte_info']['sample_id']==sample_id]['analytes']


        self.prep_data(sample_id, analyte_1, analyte_2)

        #update self.data['norm']
        for analyte in analytes:
            self.data[sample_id]['norm'][analyte] = norm

        #if update:
        # self.update_all_plots()
        # self.update_plot()
        self.update_SV()

    def prep_data(self, sample_id=None, analyte_1=None, analyte_2=None):
        """Prepares data to be used in analysis

        1. Obtains raw DataFrame
        2. Handles negative values based on option chosen
        3. Scale data  (linear,log, loggit)
        4. Autoscales data if choosen by user

        The prepped data is stored in one of 2 Dataframes: analysis_analyte_data or computed_analyte_data
        """
        if sample_id is None:
            sample_id = self.sample_id #set to default sample_id

        if analyte_1: #if single analyte
            analytes = [analyte_1]
        else: #if analyte is not provided update all analytes in analytes_df
            analytes = self.data[sample_id]['analyte_info'][self.data[sample_id]['analyte_info']['sample_id']==sample_id]['analytes']

        analyte_info = self.data[sample_id]['analyte_info'].loc[
                                 (self.data[sample_id]['analyte_info']['analytes'].isin(analytes))]
        
        
        
            
            
            
        if not analyte_2: #not a ratio
            
            # perform negative value handling
            for neg_method in analyte_info['negative_method'].unique():
                filtered_analytes = analyte_info[analyte_info['negative_method'] == neg_method]['analytes']
                filtered_data = self.data[sample_id]['cropped_raw_data'][filtered_analytes].values
                self.data[sample_id]['processed_data'].loc[:,filtered_analytes] = self.transform_array(filtered_data,neg_method)
                
                
            # shifts analyte values so that all values are postive
            # adj_data = pd.DataFrame(self.transform_plots(self.data[sample_id]['cropped_raw_data'][analytes].values), columns= analytes)
            
            
            # #perform scaling for groups of analytes with same norm parameter
            # for norm in analyte_info['norm'].unique():
            #     filtered_analytes = analyte_info[(analyte_info['norm'] == norm)]['analytes']
            #     filtered_data = adj_data[filtered_analytes].values
            #     if norm == 'log':

            #         # np.nanlog handles NaN value
            #         self.data[sample_id]['processed_data'].loc[:,filtered_analytes] = np.log10(filtered_data, where=~np.isnan(filtered_data))
            #         # print(self.processed_analyte_data[sample_id].loc[:10,analytes])
            #         # print(self.data[sample_id]['processed_data'].loc[:10,analytes])
            #     elif norm == 'logit':
            #         # Handle division by zero and NaN values
            #         with np.errstate(divide='ignore', invalid='ignore'):
            #             analyte_array = np.log10(filtered_data / (10**6 - filtered_data), where=~np.isnan(filtered_data))
            #             self.data[sample_id]['processed_data'].loc[:,filtered_analytes] = analyte_array
            #     else:
            #         # set to clipped data with original values if linear normalisation
            #         self.data[sample_id]['processed_data'].loc[:,filtered_analytes] = filtered_data

            # perform autoscaling on columns where auto_scale is set to true
            for auto_scale in analyte_info['auto_scale'].unique():
                filtered_analytes = analyte_info[analyte_info['auto_scale'] == auto_scale]['analytes']

                for analyte_1 in filtered_analytes:
                    parameters = analyte_info.loc[(analyte_info['sample_id']==sample_id)
                                          & (analyte_info['analytes']==analyte_1)].iloc[0]
                    filtered_data =  self.data[sample_id]['processed_data'][analytes][analyte_1].values
                    lq = parameters['lower_bound']
                    uq = parameters['upper_bound']
                    d_lb = parameters['d_l_bound']
                    d_ub = parameters['d_u_bound']
                    if auto_scale:

                        self.data[sample_id]['processed_data'][analyte_1] = self.outlier_detection(filtered_data.reshape(-1, 1),lq, uq, d_lb,d_ub)
                    else:
                        #clip data using ub and lb
                        lq_val = np.nanpercentile(filtered_data, lq, axis=0)
                        uq_val = np.nanpercentile(filtered_data, uq, axis=0)
                        filtered_data = np.clip(filtered_data, lq_val, uq_val)
                        self.data[sample_id]['processed_data'][analyte_1] = filtered_data

                    # update v_min and v_max in self.data[sample_id]['analyte_info']
                    self.data[sample_id]['analyte_info'].loc[
                                             (self.data[sample_id]['analyte_info']['analytes']==analyte_1),'v_max'] = np.nanmax(filtered_data)
                    self.data[sample_id]['analyte_info'].loc[
                                             (self.data[sample_id]['analyte_info']['analytes']==analyte_1), 'v_min'] = np.nanmin(filtered_data)

            #add x and y columns from raw data
            self.data[sample_id]['processed_data']['X'] = self.data[sample_id]['cropped_raw_data']['X']
            self.data[sample_id]['processed_data']['Y'] = self.data[sample_id]['cropped_raw_data']['Y']

        else:  #if ratio
            ratio_df = self.data[sample_id]['cropped_raw_data'][[analyte_1,analyte_2]] #consider original data for ratio

            ratio_name = analyte_1+' / '+analyte_2

            # shifts analyte values so that all values are postive
            # ratio_array = self.transform_plots(ratio_df.values)
            ratio_array= ratio_df.values
            ratio_df = pd.DataFrame(ratio_array, columns= [analyte_1,analyte_2])
            
            # mask = (ratio_df[analyte_1] > 0) & (ratio_df[analyte_2] > 0)
            
            mask =   (ratio_df[analyte_2] == 0)

            ratio_array = np.where(mask, ratio_array[:,0] / ratio_array[:,1], np.nan)

            # Get the index of the row that matches the criteria
            index_to_update = self.data[sample_id]['ratio_info'].loc[
                    (self.data[sample_id]['ratio_info']['analyte_1'] == analyte_1) &
                    (self.data[sample_id]['ratio_info']['analyte_2'] == analyte_2)
                ].index

            # Check if we found such a row
            if len(index_to_update) > 0:
                idx = index_to_update[0]

                if pd.isna(self.data[sample_id]['ratio_info'].at[idx, 'lower_bound']): #if bounds are not updated in dataframe
                    #sets auto scale to true by default with default values for lb,db, d_lb and d_ub
                    auto_scale = True
                    norm = self.data[sample_id]['ratio_info'].at[idx, 'norm']
                    lb = 0.05
                    ub = 99.5
                    d_lb = 99
                    d_ub = 99
                    self.data[sample_id]['ratio_info'].at[idx, 'lower_bound'] = lb
                    self.data[sample_id]['ratio_info'].at[idx, 'upper_bound'] = ub
                    self.data[sample_id]['ratio_info'].at[idx, 'd_l_bound'] = d_lb
                    self.data[sample_id]['ratio_info'].at[idx, 'd_u_bound'] = d_ub
                    self.data[sample_id]['ratio_info'].at[idx, 'auto_scale'] = auto_scale
                    neg_method = self.comboBoxNegativeMethod.currentText()
                    min_positive_value = min(ratio_array[ratio_array>0])
                    self.data[sample_id]['ratio_info'].at[idx, 'negative_method'] = neg_method
                    # self.data[sample_id]['ratio_info'].at[idx, 'min_positive_value'] = min_positive_value
                else: #if bounds exist in ratios_df
                    norm = self.data[sample_id]['ratio_info'].at[idx, 'norm']
                    lb = self.data[sample_id]['ratio_info'].at[idx, 'lower_bound']
                    ub = self.data[sample_id]['ratio_info'].at[idx, 'upper_bound']
                    d_lb = self.data[sample_id]['ratio_info'].at[idx, 'd_l_bound']
                    d_ub = self.data[sample_id]['ratio_info'].at[idx, 'd_u_bound']
                    auto_scale = self.data[sample_id]['ratio_info'].at[idx, 'auto_scale']
                    neg_method = self.data[sample_id]['ratio_info'].at[idx, 'negative_method']
                    # min_positive_value = self.data[sample_id]['ratio_info'].at[idx, 'min_positive_value']
                    
                    
                # if norm == 'log':

                #     # np.nanlog handles NaN value
                #     ratio_array = np.log10(ratio_array, where=~np.isnan(ratio_array))
                #     # print(self.processed_analyte_data[sample_id].loc[:10,analytes])
                #     # print(self.data[sample_id]['processed_data'].loc[:10,analytes])
                # elif norm == 'logit':
                #     # Handle division by zero and NaN values
                #     with np.errstate(divide='ignore', invalid='ignore'):
                #         ratio_array = np.log10(ratio_array / (10**6 - ratio_array), where=~np.isnan(ratio_array))
                # else:
                #     # set to clipped data with original values if linear normalisation
                #     pass

                # perform negative value handling
                ratio_array = self.transform_array(ratio_array,neg_method)     

                if auto_scale:

                    ratio_array = self.outlier_detection(ratio_array.reshape(-1, 1),lb, ub, d_lb,d_ub)
                else:
                    #clip data using ub and lb
                    lq_val = np.nanpercentile(ratio_array, lq, axis=0)
                    uq_val = np.nanpercentile(ratio_array, uq, axis=0)
                    ratio_array = np.clip(ratio_array, lq_val, uq_val)

                if self.data[sample_id]['computed_data']['Ratio'].empty:
                    self.data[sample_id]['computed_data']['Ratio'] = self.data[sample_id]['cropped_raw_data'][['X','Y']]

                self.data[sample_id]['computed_data']['Ratio'][ratio_name] = ratio_array

                self.data[sample_id]['ratio_info'].at[idx, 'v_min'] = np.nanmin(ratio_array)
                self.data[sample_id]['ratio_info'].at[idx, 'v_max'] = np.nanmax(ratio_array)

    def remove_widgets_from_layout(self, layout, object_names_to_remove):
        """
        Remove plot widgets from the provided layout based on their objectName properties.

        :param layout:
        :type layout:
        :param object_names_to_remove:
        :type object_names_to_remove:
        """
        for i in reversed(range(layout.count())):  # Reverse to avoid skipping due to layout change
            item = layout.itemAt(i)
            widget = item.widget()
            if widget and widget.objectName() in object_names_to_remove:
                widget.setParent(None)
                widget.deleteLater()
            # Handle child layouts
            elif hasattr(item, 'layout') and item.layout():
                child_layout = item.layout()
                if child_layout.objectName() in object_names_to_remove:
                    # Remove all widgets from the child layout
                    while child_layout.count():
                        child_item = child_layout.takeAt(0)
                        if child_item.widget():
                            child_item.widget().setParent(None)
                            child_item.widget().deleteLater()
                    # Now remove the layout itself
                    layout.removeItem(child_layout)
                    del child_layout

        layout.update()


    # -------------------------------
    # Mouse/Plot interactivity Events
    # -------------------------------
    def mouse_moved_pg(self,event,plot):
        pos_view = plot.vb.mapSceneToView(event)  # This is in view coordinates
        pos_scene = plot.vb.mapViewToScene(pos_view)  # Map from view to scene coordinates
        any_plot_hovered = False
        for (k,v), (_, p, array) in self.lasermaps.items():
            # print(p.sceneBoundingRect(), pos)
            if p.sceneBoundingRect().contains(pos_scene) and v == self.canvasWindow.currentIndex() and not self.toolButtonPan.isChecked() and not self.toolButtonZoom.isChecked() :

                # mouse_point = p.vb.mapSceneToView(pos)
                mouse_point = pos_view
                x, y = mouse_point.x(), mouse_point.y()

                x_i = round(x*array.shape[1]/self.x_range)
                y_i = round(y*array.shape[0]/self.y_range)

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

                    for (k,v), (target, _,array) in self.lasermaps.items():
                        if not self.actionCrop.isChecked():
                            target.setPos(mouse_point)
                            target.show()
                            value = array[y_i, x_i]
                            if k in self.multiview_info_label:
                                self.multiview_info_label[k][1].setText('v: '+str(round(value,2)))
                # break
        if not any_plot_hovered and not self.actionCrop.isChecked():
            QApplication.restoreOverrideCursor()
            self.cursor = False
            for target, _, _ in self.lasermaps.values():
                target.hide() # Hide crosshairs if no plot is hovered
            # hide zoom view
            self.zoomViewBox.hide()

    def plot_clicked(self, event,array,k, plot,radius=5):

        # get click location
        click_pos = plot.vb.mapSceneToView(event.scenePos())
        x, y = click_pos.x(), click_pos.y()
        v = self.canvasWindow.currentIndex() #view
        # Convert the click position to plot coordinates
        self.array_x = array.shape[1]
        self.array_y = array.shape[0]
        x_i = round(x*self.array_x/self.x_range)
        y_i = round(y*self.array_y/self.y_range)

        # Ensure indices are within plot bounds
        if not(0 <= x_i < self.array_x) or not(0 <= y_i < self.array_y):
            #do nothing
            return

        # elif self.actionCrop.isChecked():
        #     self.crop_tool.create_rect(event, click_pos)
        # if event.button() == QtCore.Qt.LeftButton and self.main_window.pushButtonStartProfile.isChecked():
       #apply profiles
        elif self.toolButtonPlotProfile.isChecked() or self.toolButtonPointMove.isChecked():
            self.profiling.plot_profile_scatter(event, array, k,v, plot, x, y,x_i, y_i)
        #create polygons
        elif self.toolButtonPolyCreate.isChecked() or self.toolButtonPolyMovePoint.isChecked() or self.toolButtonPolyAddPoint.isChecked() or self.toolButtonPolyRemovePoint.isChecked():
            self.polygon.plot_polygon_scatter(event, k, x, y,x_i, y_i)

        #apply crop
        elif self.actionCrop.isChecked() and event.button() == QtCore.Qt.RightButton:
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

        style = self.styles[self.comboBoxPlotType.currentText()]

        # Assuming you have a method like this to update the zoom view
        # Calculate the new position for the zoom view
        xOffset = 50  # Horizontal offset from cursor to avoid overlap
        yOffset = 100  # Vertical offset from cursor to display below it

        # Adjust position to ensure the zoom view remains within the plot bounds
        x_pos = min(max(x + xOffset, 0), self.plot.viewRect().width() - self.zoomViewBox.width())
        y_pos = min(max(y + yOffset, 0), self.plot.viewRect().height() - self.zoomViewBox.height())

        # Update the position of the zoom view
        self.zoomViewBox.setGeometry(x_pos, y_pos, self.zoomViewBox.width(), self.zoomViewBox.height())

        # Calculate the region to zoom in on
        zoomRect = QtCore.QRectF(x - self.x_range * self.zoomLevel, y - self.y_range * self.zoomLevel, self.x_range * self.zoomLevel * 2, self.y_range * self.zoomLevel * 2)

        # Update the zoom view's displayed region
        # self.zoomViewBox.setRange(rect=zoomRect, padding=0)
        if self.toolButtonEdgeDetect.isChecked():
            self.zoomImg.setImage(image=self.edge_array)  # user edge_array too zoom with edge_det
        else:
            self.zoomImg.setImage(image=self.array)  # Make sure this uses the current image data

        self.zoomImg.setRect(0,0,self.x_range,self.y_range)
        self.zoomViewBox.setRange(zoomRect) # Set the zoom area in the image
        self.zoomImg.setColorMap(colormap.get(style['Colors']['Colormap'], source = 'matplotlib'))
        self.zoomTarget.setPos(x, y)  # Update target position
        self.zoomTarget.show()
        self.zoomViewBox.setZValue(1e10)

    def reset_zoom(self, vb,histogram):
        vb.enableAutoRange()
        histogram.autoHistogramRange()


    # -------------------------------------
    # Image processing functions
    # -------------------------------------
    def add_edge_detection(self):
        """ Add edge detection to the current laser map plot.

        Executes on change of ``MainWindow.comboBoxEdgeDetectMethod`` when ``MainWindow.toolButtonEdgeDetect`` is checked.
        Options include 'sobel', 'canny', and 'zero_cross'.
        """
        #print('add_edge_detection')
        style = self.styles[self.comboBoxPlotType.currentText()]
        if self.edge_img:
            # remove existing filters
            self.plot.removeItem(self.edge_img)

        if self.toolButtonEdgeDetect.isChecked():
            algorithm = self.comboBoxEdgeDetectMethod.currentText().lower()
            if algorithm == 'sobel':
                # Apply Sobel edge detection
                sobelx = cv2.Sobel(self.array, cv2.CV_64F, 1, 0, ksize=5)
                sobely = cv2.Sobel(self.array, cv2.CV_64F, 0, 1, ksize=5)
                edge_detected_image = np.sqrt(sobelx**2 + sobely**2)
            elif algorithm == 'canny':

                # Normalize the array to [0, 1]
                normalized_array = (self.array - np.nanmin(self.array)) / (np.nanmax(self.array) - np.nanmin(self.array))

                # Scale to [0, 255] and convert to uint8
                scaled_array = (normalized_array * 255).astype(np.uint8)

                # Apply Canny edge detection
                edge_detected_image = cv2.Canny(scaled_array, 100, 200)
            elif algorithm == 'zero cross':
                # Apply Zero Crossing edge detection (This is a placeholder as OpenCV does not have a direct function)
                # You might need to implement a custom function or find a library that supports Zero Crossing
                edge_detected_image = self.zero_crossing_laplacian(self.array)  # Placeholder, replace with actual Zero Crossing implementation
            else:
                raise ValueError("Unsupported algorithm. Choose 'sobel', 'canny', or 'zero cross'.")

            # Assuming you have a way to display this edge_detected_image on your plot.
            # This could be an update to an existing ImageItem or creating a new one if necessary.
            self.edge_array = edge_detected_image
            if (np.nanmin(self.edge_array) < 0) or (np.nanmax(self.edge_array) > 255):
                self.edge_array = (self.edge_array - np.nanmin(self.edge_array)) / (np.nanmax(self.edge_array) - np.nanmin(self.edge_array))

                # Scale to [0, 255] and convert to uint8
                self.edge_array = (self.edge_array * 255).astype(np.uint8)

            self.edge_img = ImageItem(image=self.edge_array)
            #set aspect ratio of rectangle
            #self.edge_img.setRect(0,0,self.x_range,self.y_range)
            # edge_img.setAs
            #cm = colormap.get(style['Colors']['Colormap'], source = 'matplotlib')
            #self.edge_img.setColorMap(cm)
            #self.plot.addItem(self.edge_img)

            overlay_image = np.zeros(self.edge_array.shape+(4,), dtype=np.uint8)
            colorlist = self.get_rgb_color(self.styles['analyte map']['Scale']['OverlayColor'])
            overlay_image[..., 0] = colorlist[0]  # Red channel
            overlay_image[..., 1] = colorlist[1]  # Green channel
            overlay_image[..., 2] = colorlist[2]  # Blue channel
            overlay_image[..., 3] = 0.9*self.edge_array

            self.edge_img = ImageItem(image=overlay_image)

            #set aspect ratio of rectangle
            self.edge_img.setRect(0,0,self.x_range,self.y_range)
            self.plot.addItem(self.edge_img)

    def zero_crossing_laplacian(self,array):
        """Apply Zero Crossing on the Laplacian of the image.

        :param array: array representing the image.
        :type array: numpy.ndarray

        :return: Edge-detected image using the zero crossing method.
        """
        # Normalize the array to [0, 1]
        normalized_array = (array - np.nanmin(array)) / (np.nanmax(array) - np.nanmin(array))

        # Scale to [0, 255] and convert to uint8
        image = (normalized_array * 255).astype(np.uint8)


        # Apply Gaussian filter for noise reduction
        blurred_image = ndimage.gaussian_filter(image, sigma=6)

        # Apply Laplacian operator
        # laplacian_image = ndimage.laplace(blurred_image)

        LoG_kernel = np.array([
                                [0, 0,  1, 0, 0],
                                [0, 1,  2, 1, 0],
                                [1, 2,-16, 2, 1],
                                [0, 1,  2, 1, 0],
                                [0, 0,  1, 0, 0]
                            ])


        laplacian_image = convolve2d(blurred_image,LoG_kernel)

        # Find zero crossings
        zero_crossings = np.zeros_like(laplacian_image)
        # Shift the image by one pixel in all directions
        for shift in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            shifted = np.roll(np.roll(laplacian_image, shift[0], axis=0), shift[1], axis=1)
            # A zero crossing occurs where the product of the original and the shifted image is less than zero (sign change)
            zero_mask = (laplacian_image * shifted) < 0
            zero_crossings[zero_mask] = 1
        return zero_crossings

    def noise_reduction_method_callback(self):
        """Noise reduction method callback

        Executes when ``MainWindow.comboBoxNoiseReductionMethod.currentText()`` is changed.
        Enables ``MainWindow.spinBoxNoiseOption1`` and ``MainWindow.doubleSpinBoxNoiseOption2`` (if applicable)
        and associated labels.  Constraints on the ranges are added to the spin boxes.

        After enabling options, it runs ``noise_reduction``.
        """
        algorithm = self.comboBoxNoiseReductionMethod.currentText().lower()

        match algorithm:
            case 'none':
                # turn options off
                self.labelNoiseOption1.setEnabled(False)
                self.labelNoiseOption1.setText('')
                self.spinBoxNoiseOption1.setEnabled(False)
                self.labelNoiseOption2.setEnabled(False)
                self.labelNoiseOption2.setText('')
                self.doubleSpinBoxNoiseOption2.setEnabled(False)

                self.noise_reduction(algorithm)
                self.comboBoxApplyNoiseReduction.setEnabled(False)
                self.labelApplySmoothing.setEnabled(False)
                self.checkBoxGradient.setEnabled(False)
                self.labelGradient.setEnabled(False)

                self.actionNoiseReduction.setEnabled(False)

                self.update_SV()
            case _:
                # set option 1
                self.spinBoxNoiseOption1.blockSignals(True)
                self.labelNoiseOption1.setEnabled(True)
                self.labelNoiseOption1.setText(self.noise_red_options[algorithm]['label1'])
                self.spinBoxNoiseOption1.setEnabled(True)
                match algorithm:
                    case 'median':
                        self.spinBoxNoiseOption1.setRange(1,5)
                        self.spinBoxNoiseOption1.setSingleStep(2)
                    case 'gaussian' | 'wiener':
                        self.spinBoxNoiseOption1.setRange(1,199)
                        self.spinBoxNoiseOption1.setSingleStep(2)
                    case 'edge-preserving':
                        self.spinBoxNoiseOption1.setRange(0,200)
                        self.spinBoxNoiseOption1.setSingleStep(5)
                    case _:
                        self.spinBoxNoiseOption1.setRange(0,200)
                        self.spinBoxNoiseOption1.setSingleStep(5)

                self.spinBoxNoiseOption1.setValue(int(self.noise_red_options[algorithm]['value1']))
                self.spinBoxNoiseOption1.blockSignals(False)
                #self.comboBoxApplyNoiseReduction.setEnabled(True)
                #self.labelApplySmoothing.setEnabled(True)
                self.checkBoxGradient.setEnabled(True)
                self.labelGradient.setEnabled(True)
                self.actionNoiseReduction.setEnabled(True)

                val1 = self.spinBoxNoiseOption1.value()

                # set option 2
                if self.noise_red_options[algorithm]['label2'] is None:
                    # no option 2
                    self.labelNoiseOption2.setEnabled(False)
                    self.labelNoiseOption2.setText('')
                    self.doubleSpinBoxNoiseOption2.setEnabled(False)

                    self.noise_reduction(algorithm, val1)
                else:
                    # yes option 2
                    self.doubleSpinBoxNoiseOption2.blockSignals(True)
                    self.labelNoiseOption2.setEnabled(True)
                    self.labelNoiseOption2.setText(self.noise_red_options[algorithm]['label2'])
                    self.doubleSpinBoxNoiseOption2.setEnabled(True)
                    match algorithm:
                        case 'edge-preserving':
                            self.doubleSpinBoxNoiseOption2.setRange(0,1)
                        case 'bilateral':
                            self.doubleSpinBoxNoiseOption2.setRange(0,200)

                    self.doubleSpinBoxNoiseOption2.setValue(self.noise_red_options[algorithm]['value2'])
                    self.doubleSpinBoxNoiseOption2.blockSignals(False)

                    val2 = self.doubleSpinBoxNoiseOption2.value()
                    self.noise_reduction(algorithm, val1, val2)

    def gaussian_sigma(self, ksize):
        """Sets default Gaussian sigma.

        Same as default in OpenCV, i.e., 0.3*((ksize-1)*0.5 - 1) + 0.8. This functions sets the sigma
        value for ``cv2.GaussianBlur`` only when ``MainWindow.comboBoxNoiseReductionMethod`` is 'Gaussian' and new kernel
        value is set by the user via ``MainWindow.spinBoxNoiseReductionOption1.value()``.
        """
        return 0.3*((ksize-1)*0.5 - 1) + 0.8

    def run_noise_reduction(self):
        """Gets parameters and runs noise reduction"""

        algorithm = self.comboBoxNoiseReductionMethod.currentText().lower()
        if algorithm == 'none':
            return

        val1 = self.noise_red_options[algorithm]['value1']
        if self.noise_red_options[algorithm]['label2'] is None:
            self.noise_reduction(algorithm,val1)
        else:
            val2 = self.noise_red_options[algorithm]['value2']
            self.noise_reduction(algorithm,val1,val2)

    def noise_reduction_option1_callback(self):
        """Callback executed when the first noise reduction option is changed

        Updates noise reduction applied to map(s) when ``MainWindow.spinBoxNoiseOption1.value()`` is changed by
        the user."""
        algorithm = self.comboBoxNoiseReductionMethod.currentText().lower()

        # get option 1
        val1 = self.spinBoxNoiseOption1.value()
        match algorithm:
            case 'median' | 'gaussian' | 'wiener':
                # val1 must be odd
                if val1 % 2 != 1:
                    val1 = val1 + 1
        self.noise_red_options[algorithm]['value1'] = val1

        # add a second parameter (if required and run noise reduction)
        if self.noise_red_options[algorithm]['label2'] is None:
            self.noise_reduction(algorithm,val1)

        else:
            if algorithm == 'gaussian':
                val2 = self.gaussian_sigma(val1)
                self.doubleSpinBoxNoiseOption2.blockSignals(True)
                self.doubleSpinBoxNoiseOption2.setValue(val2)
                self.doubleSpinBoxNoiseOption2.blockSignals(False)
                self.noise_red_options[algorithm]['value2'] = val2
            else:
                val2 = self.doubleSpinBoxNoiseOption2.value()

            self.noise_reduction(algorithm,val1,val2)

    def noise_reduction_option2_callback(self):
        """Callback executed when the second noise reduction option is changed

        Updates noise reduction applied to map(s) when ``MainWindow.spinBoxNoiseOption2.value()`` is changed by
        the user.  Note, not all noise reduction methods have a second option."""
        algorithm = self.comboBoxNoiseReductionMethod.currentText().lower()

        val1 = self.spinBoxNoiseOption1.value()
        val2 = self.doubleSpinBoxNoiseOption2.value()
        self.noise_red_options[algorithm]['value2'] = val2
        self.noise_reduction(algorithm,val1,val2)

    def noise_reduction(self, algorithm, val1=None, val2=None):
        """
        Add noise reduction to the current laser map plot.

        Executes on change of ``MainWindow.comboBoxNoiseReductionMethod``, ``MainWindow.spinBoxNoiseOption1`` and
        ``MainWindow.doubleSpinBoxOption2``. Updates map(s).

        Reduces noise by smoothing via one of several algorithms chosen from
        ``MainWindow.comboBoxNoiseReductionMethod``.

        Parameters
        ----------
        algorithm : str
            Options include:
            | 'None' - no smoothing
            | 'Median' - simple blur that computes each pixel from the median of a window including surrounding points
            | 'Gaussian' - a simple Gaussian blur
            | 'Weiner' - a Fourier domain filtering method that low pass filters to smooth the map
            | 'Edge-preserving' - filter that does an excellent job of preserving edges when smoothing
            | 'Bilateral' - an edge-preserving Gaussian weighted filter
        val1 : int, optional
            First filter argument, required for all filters
        val2 : float, optional
            Second filter argument, required for *Gaussian*, *Edge-preserving*, and *Bilateral* methods
        """
        # if self.noise_red_img:
        #     # Remove existing filters
        #     self.plot.removeItem(self.noise_red_img)

        # if self.grad_img:
        #     self.plot.removeItem(self.grad_img)

        # Assuming self.array is the current image data
        # get data for current map
        field_type = self.comboBoxColorByField.currentText()
        field = self.comboBoxColorField.currentText()
        map_df = self.get_map_data(self.sample_id, field, field_type=field_type)

        # plot map
        self.array = np.reshape(map_df['array'].values, self.array_size, order=self.order)

        match algorithm:
            case 'none':
                return
            case 'median':
                # Apply Median filter
                filtered_image = cv2.medianBlur(self.array.astype(np.float32), int(val1))  # Kernel size is 5
            case 'gaussian':
                # Apply Median filter
                filtered_image = cv2.GaussianBlur(self.array.astype(np.float32),
                        int(val1), sigmaX=float(val2), sigmaY=float(val2))  # Kernel size is 5
            case 'wiener':
                # Apply Wiener filter
                # Wiener filter in scipy expects the image in double precision
                # Myopic deconvolution, kernel size set by spinBoxNoiseOption1
                filtered_image = wiener(self.array.astype(np.float64), (int(val1), int(val1)))
                filtered_image = filtered_image.astype(np.float32)  # Convert back to float32 to maintain consistency
            case 'edge-preserving':
                # Apply Edge-Preserving filter (RECURSIVE_FILTER or NORMCONV_FILTER)
                # Normalize the array to [0, 1]
                normalized_array = (self.array - np.nanmin(self.array)) / (np.nanmax(self.array) - np.nanmin(self.array))

                # Scale to [0, 255] and convert to uint8
                image = (normalized_array * 255).astype(np.uint8)
                filtered_image = cv2.edgePreservingFilter(image, flags=1, sigma_s=float(val1), sigma_r=float(val2))

                # convert back to original units
                filtered_image = (filtered_image.astype(np.float32) / 255) * (np.nanmax(self.array) - np.nanmin(self.array)) + np.nanmin(self.array)
                
            case 'bilateral':
                # Apply Bilateral filter
                # Parameters are placeholders, you might need to adjust them based on your data
                filtered_image = cv2.bilateralFilter(self.array.astype(np.float32), int(val1), float(val2), float(val2))

        # Update or create the image item for displaying the filtered image
        self.noise_red_array = filtered_image

        if self.checkBoxGradient.isChecked():
            self.plot_gradient()
            return

        # uncomment for pyqtgraph version
        # -----------
        # self.noise_red_img = ImageItem(image=self.noise_red_array)

        # # Set aspect ratio of rectangle
        # self.noise_red_img.setRect(0, 0, self.x_range, self.y_range)

        # # Optionally, set a color map
        # self.comboBoxPlotType.setCurrentText('analyte map')
        # cm = colormap.get(self.styles['analyte map']['Colors']['Colormap'], source='matplotlib')
        # self.noise_red_img.setColorMap(cm)

        # # Add the image item to the plot
        # self.plot.addItem(self.noise_red_img)

        # uncomment for matplotlib version
        # -----------
        canvas = MplCanvas(parent=self)

        style = self.styles['analyte map']

        norm = self.color_norm(style)

        cax = canvas.axes.imshow(filtered_image, cmap=self.get_colormap(),  aspect=self.aspect_ratio, interpolation='none', norm=norm)

        # set color limits
        self.add_colorbar(canvas, cax, style)
        cax.set_clim(style['Colors']['CLim'][0], style['Colors']['CLim'][1])

        # use mask to create an alpha layer
        mask = self.data[self.sample_id]['mask'].astype(float)
        reshaped_mask = np.reshape(mask, self.array_size, order=self.order)

        alphas = colors.Normalize(0, 1, clip=False)(reshaped_mask)
        alphas = np.clip(alphas, .4, 1)
        #cax = canvas.axes.imshow(self.array, alpha=alphas, cmap=self.get_colormap(),  aspect=self.aspect_ratio, interpolation='none', norm=norm)
        #canvas.axes.set_facecolor('w')

        alpha_mask = np.where(reshaped_mask == 0, 0.5, 0)  
        canvas.axes.imshow(np.ones_like(alpha_mask), aspect=self.aspect_ratio, interpolation='none', cmap='Greys', alpha=alpha_mask)

        # add scalebar
        self.add_scalebar(canvas.axes)

        canvas.axes.tick_params(direction=None,
            labelbottom=False, labeltop=False, labelright=False, labelleft=False,
            bottom=False, top=False, left=False, right=False)
        canvas.fig.tight_layout()

        field = self.comboBoxColorField.currentText()
        self.plot_info = {
            'tree': 'Analyte',
            'sample_id': self.sample_id,
            'plot_name': field,
            'plot_type': 'analyte map',
            'field_type': self.comboBoxColorByField.currentText(),
            'field': field,
            'figure': canvas,
            'style': style,
            'cluster_groups': None,
            'view': [True,False],
            'position': None
            }

        self.clear_layout(self.widgetSingleView.layout())
        self.widgetSingleView.layout().addWidget(canvas)

        self.add_tree_item(self.plot_info)

    def plot_gradient(self):
        """Produces a gradient map

        Executes only when ``MainWindow.comboBoxNoiseReductionMethod.currentText()`` is not ``none``, computes noise reduction and displays gradient map"""
        # update plot type comboBox
        self.plot_flag = False
        self.comboBoxPlotType.setCurrentText('gradient map')
        self.plot_flat = True

        # Compute gradient
        grad_array = np.gradient(self.noise_red_array)
        # gradient magnitude
        self.grad_mag = np.sqrt(grad_array[0]**2 + grad_array[1]**2)

        dx = decimate(grad_array[0],10)
        dy = decimate(grad_array[1],10)

        x = np.arange((dx.T).shape[0])*10
        y = np.arange((dy.T).shape[1])*10
        X, Y = np.meshgrid(x, y)

        # uncomment for pyqtgraph version
        # -----------
        # remove existing gradient map
        # if self.grad_img:
        #     self.plot.removeItem(self.grad_img)

        # self.grad_img = ImageItem(image=self.grad_mag)
        # self.grad_img.setRect(0, 0, self.x_range, self.y_range)

        # # Optionally, set a color map
        # cm = colormap.get(self.styles['gradient map']['Colors']['Colormap'], source='matplotlib')
        # self.grad_img.setColorMap(cm)

        # # Add the image item to the plot
        # self.plot.addItem(self.grad_img)

        # uncomment for matplotlib version
        # -----------
        canvas = MplCanvas(parent=self)

        style = self.styles['analyte map']

        q = np.quantile(self.grad_mag.flatten(), q=[0.025, 0.975])
        norm = colors.Normalize(q[0],q[1], clip=False)

        cax = canvas.axes.imshow(self.grad_mag, cmap=self.get_colormap(),  aspect=self.aspect_ratio, interpolation='none', norm=norm)
        canvas.axes.quiver(X,Y,dx,dy, color=style['Scale']['OverlayColor'], linewidth=0.5)

        # set color limits
        #self.add_colorbar(canvas, cax, style)
        #cax.set_clim(style['Colors']['CLim'][0], style['Colors']['CLim'][1])

        # use mask to create an alpha layer
        mask = self.data[self.sample_id]['mask'].astype(float)
        reshaped_mask = np.reshape(mask, self.array_size, order=self.order)

        alphas = colors.Normalize(0, 1, clip=False)(reshaped_mask)
        alphas = np.clip(alphas, .4, 1)
        #cax = canvas.axes.imshow(self.array, alpha=alphas, cmap=self.get_colormap(),  aspect=self.aspect_ratio, interpolation='none', norm=norm)
        #canvas.axes.set_facecolor('w')

        alpha_mask = np.where(reshaped_mask == 0, 0.5, 0)  
        canvas.axes.imshow(np.ones_like(alpha_mask), aspect=self.aspect_ratio, interpolation='none', cmap='Greys', alpha=alpha_mask)

        # add scalebar
        self.add_scalebar(canvas.axes)

        canvas.axes.tick_params(direction=None,
            labelbottom=False, labeltop=False, labelright=False, labelleft=False,
            bottom=False, top=False, left=False, right=False)
        canvas.fig.tight_layout()

        field = self.comboBoxColorField.currentText()
        self.plot_info = {
            'tree': 'Analyte',
            'sample_id': self.sample_id,
            'plot_name': field,
            'plot_type': 'analyte map',
            'field_type': self.comboBoxColorByField.currentText(),
            'field': field,
            'figure': canvas,
            'style': style,
            'cluster_groups': None,
            'view': [True,False],
            'position': None
            }

        self.clear_layout(self.widgetSingleView.layout())
        self.widgetSingleView.layout().addWidget(canvas)


    # -------------------------------------
    # Style related fuctions/callbacks
    # -------------------------------------
    def reset_default_styles(self):
        """Resets ``MainWindow.styles`` dictionary to default values."""
        default_plot_style = {'Axes': {'XLim': [0,1], 'XScale': 'linear', 'XLabel': '', 'YLim': [0,1], 'YScale': 'linear', 'YLabel': '', 'ZLabel': '', 'AspectRatio': '1.0', 'TickDir': 'out'},
                               'Text': {'Font': '', 'FontSize': 11.0},
                               'Scale': {'Direction': 'none', 'Location': 'northeast', 'Length': None, 'OverlayColor': '#ffffff'},
                               'Markers': {'Symbol': 'circle', 'Size': 6, 'Alpha': 30},
                               'Lines': {'LineWidth': 1.5, 'Multiplier': 1, 'Color': '#1c75bc'},
                               'Colors': {'Color': '#1c75bc', 'ColorByField': 'None', 'Field': '', 'Colormap': 'viridis', 'Reverse': False, 'CLim':[0,1], 'CScale':'linear', 'Direction': 'vertical', 'CLabel': '', 'Resolution': 10}
                               }

        # try to load one of the preferred fonts
        default_font = ['Avenir','Candara','Myriad Pro','Myriad','Aptos','Calibri','Helvetica','Arial','Verdana']
        names = QFontDatabase().families()
        for font in default_font:
            if font in names:
                self.fontComboBox.setCurrentFont(QFont(font, 11))
                default_plot_style['Text']['Font'] = self.fontComboBox.currentFont().family()
                break
            # try:
            #     self.fontComboBox.setCurrentFont(QFont(font, 11))
            #     default_plot_style['Text']['Font'] = self.fontComboBox.currentFont().family()
            # except:
            #     print(f'Could not find {font} font')



        self.styles = {'analyte map': copy.deepcopy(default_plot_style),
                'correlation': copy.deepcopy(default_plot_style),
                'histogram': copy.deepcopy(default_plot_style),
                'gradient map': copy.deepcopy(default_plot_style),
                'scatter': copy.deepcopy(default_plot_style),
                'heatmap': copy.deepcopy(default_plot_style),
                'ternary map': copy.deepcopy(default_plot_style),
                'TEC': copy.deepcopy(default_plot_style),
                'Radar': copy.deepcopy(default_plot_style),
                'variance': copy.deepcopy(default_plot_style),
                'vectors': copy.deepcopy(default_plot_style),
                'pca scatter': copy.deepcopy(default_plot_style),
                'pca heatmap': copy.deepcopy(default_plot_style),
                'PCA Score': copy.deepcopy(default_plot_style),
                'Cluster': copy.deepcopy(default_plot_style),
                'Cluster Score': copy.deepcopy(default_plot_style),
                'profile': copy.deepcopy(default_plot_style)}

        # update default styles
        for k in self.styles.keys():
            self.styles[k]['Text']['Font'] = self.fontComboBox.currentFont().family()

        self.styles['analyte map']['Colors']['Colormap'] = 'plasma'
        self.styles['analyte map']['Colors']['ColorByField'] = 'Analyte'

        self.styles['correlation']['Axes']['AspectRatio'] = 1.0
        self.styles['correlation']['Text']['FontSize'] = 8
        self.styles['correlation']['Colors']['Colormap'] = 'RdBu'
        self.styles['correlation']['Colors']['Direction'] = 'vertical'
        self.styles['correlation']['Colors']['CLim'] = [-1,1]

        self.styles['vectors']['Axes']['AspectRatio'] = 1.0
        self.styles['vectors']['Colors']['Colormap'] = 'RdBu'

        self.styles['gradient map']['Colors']['Colormap'] = 'RdYlBu'

        self.styles['Cluster Score']['Colors']['Colormap'] = 'plasma'
        self.styles['Cluster Score']['Colors']['Direction'] = 'vertical'
        self.styles['Cluster Score']['Colors']['ColorByField'] = 'Cluster Score'
        self.styles['Cluster Score']['Colors']['ColorField'] = 'Cluster0'
        self.styles['Cluster Score']['Colors']['CScale'] = 'linear'

        self.styles['Cluster']['Colors']['CScale'] = 'discrete'
        self.styles['Cluster']['Markers']['Alpha'] = 100

        self.styles['PCA Score']['Colors']['CScale'] = 'linear'
        self.styles['PCA Score']['Colors']['ColorByField'] = 'PCA Score'
        self.styles['PCA Score']['Colors']['ColorField'] = 'PC1'

        self.styles['scatter']['Axes']['AspectRatio'] = 1

        self.styles['heatmap']['Axes']['AspectRatio'] = 1
        self.styles['heatmap']['Colors']['CLim'] = [1,1000]
        self.styles['heatmap']['Colors']['CScale'] = 'log'
        self.styles['TEC']['Axes']['AspectRatio'] = 0.62
        self.styles['variance']['Axes']['AspectRatio'] = 0.62
        self.styles['pca scatter']['Lines']['Color'] = '#4d4d4d'
        self.styles['pca scatter']['Lines']['LineWidth'] = 0.5
        self.styles['pca scatter']['Axes']['AspectRatio'] = 1
        self.styles['pca heatmap']['Axes']['AspectRatio'] = 1
        self.styles['pca heatmap']['Lines']['Color'] = '#ffffff'

        self.styles['variance']['Text']['FontSize'] = 8

        self.styles['histogram']['Axes']['AspectRatio'] = 0.62
        self.styles['histogram']['Lines']['LineWidth'] = 0

        self.styles['profile']['Axes']['AspectRatio'] = 0.62
        self.styles['profile']['Lines']['LineWidth'] = 1.0
        self.styles['profile']['Markers']['Size'] = 12
        self.styles['profile']['Colors']['Color'] = '#d3d3d3'
        self.styles['profile']['Lines']['Color'] = '#d3d3d3'

    # Themes
    # -------------------------------------
    def load_theme_names(self):
        """Loads theme names and adds them to the theme comboBox
        
        Looks for saved style themes (*.sty) in ``resources/styles/`` directory and adds them to
        ``MainWindow.comboBoxStyleTheme``.  After setting list, the comboBox is set to default style.
        """
        # read filenames with *.sty
        file_list = os.listdir(os.path.join(BASEDIR,'resources/styles/'))
        style_list = [file.replace('.sty','') for file in file_list if file.endswith('.sty')]

        # add default to list
        style_list.insert(0,'default')

        # update theme comboBox
        self.comboBoxStyleTheme.clear()
        self.comboBoxStyleTheme.addItems(style_list)
        self.comboBoxStyleTheme.setCurrentIndex(0)

        self.reset_default_styles()

    def read_theme(self):
        """Reads a style theme
        
        Executes when the user changes the ``MainWindow.comboBoxStyleTheme.currentIndex()``.
        """
        name = self.comboBoxStyleTheme.currentText()

        if name == 'default':
            self.reset_default_styles()
            return

        with open(os.path.join(BASEDIR,f'resources/styles/{name}.sty'), 'rb') as file:
            self.styles = pickle.load(file)

    def input_theme_name_dlg(self):
        """Opens a dialog to save style theme

        Executes on ``MainWindow.toolButtonSaveTheme`` is clicked.  The theme is added to
        ``MainWindow.comboBoxStyleTheme`` and the style widget settings for each plot type (``MainWindow.styles``) are saved as a
        dictionary into the theme name with a ``.sty`` extension.
        """
        name, ok = QInputDialog.getText(self, 'Save custom theme', 'Enter theme name:')
        if ok:
            # update comboBox
            self.comboBoxStyleTheme.addItem(name)
            self.comboBoxStyleTheme.setCurrentText(name)

            # append theme to file of saved themes
            with open(os.path.join(BASEDIR,f'resources/styles/{name}.sty'), 'wb') as file:
                pickle.dump(self.styles, file, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            # throw a warning that name is not saved
            QMessageBox.warning(None,'Error','could not save theme.')

            return

    # general style functions
    # -------------------------------------
    def toggle_style_widgets(self):
        """Enables/disables all style widgets

        Toggling of enabled states are based on ``MainWindow.toolBox`` page and the current plot type
        selected in ``MainWindow.comboBoxPlotType."""
        #print('toggle_style_widgets')
        plot_type = self.comboBoxPlotType.currentText().lower()

        # annotation properties
        self.fontComboBox.setEnabled(True)
        self.doubleSpinBoxFontSize.setEnabled(True)
        match plot_type.lower():
            case 'analyte map' | 'gradient map':
                # axes properties
                self.lineEditXLB.setEnabled(True)
                self.lineEditXUB.setEnabled(True)
                self.comboBoxXScale.setEnabled(False)
                self.lineEditYLB.setEnabled(True)
                self.lineEditYUB.setEnabled(True)
                self.comboBoxYScale.setEnabled(False)
                self.lineEditXLabel.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)
                self.comboBoxTickDirection.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(True)
                self.comboBoxScaleLocation.setEnabled(True)
                self.lineEditScaleLength.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if len(self.spotdata) != 0:
                    self.comboBoxMarker.setEnabled(True)
                    self.doubleSpinBoxMarkerSize.setEnabled(True)
                    self.horizontalSliderMarkerAlpha.setEnabled(True)
                    self.labelMarkerAlpha.setEnabled(True)

                    self.toolButtonMarkerColor.setEnabled(True)
                else:
                    self.comboBoxMarker.setEnabled(False)
                    self.doubleSpinBoxMarkerSize.setEnabled(False)
                    self.horizontalSliderMarkerAlpha.setEnabled(False)
                    self.labelMarkerAlpha.setEnabled(False)

                    self.toolButtonMarkerColor.setEnabled(False)

                # line properties
                #if len(self.polygon.polygons) > 0:
                #    self.comboBoxLineWidth.setEnabled(True)
                #else:
                #    self.comboBoxLineWidth.setEnabled(False)
                self.comboBoxLineWidth.setEnabled(True)
                self.toolButtonLineColor.setEnabled(True)
                self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(True)
                self.comboBoxColorField.setEnabled(True)
                self.comboBoxFieldColormap.setEnabled(True)
                self.lineEditColorLB.setEnabled(True)
                self.lineEditColorUB.setEnabled(True)
                self.comboBoxColorScale.setEnabled(True)
                self.comboBoxCbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(True)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'correlation' | 'vectors':
                # axes properties
                self.lineEditXLB.setEnabled(False)
                self.lineEditXUB.setEnabled(False)
                self.comboBoxXScale.setEnabled(False)
                self.lineEditYLB.setEnabled(False)
                self.lineEditYUB.setEnabled(False)
                self.comboBoxYScale.setEnabled(False)
                self.lineEditXLabel.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.comboBoxXScale.setEnabled(False)
                self.comboBoxYScale.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.lineEditScaleLength.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(False)
                self.lineEditLengthMultiplier.setEnabled(False)
                self.toolButtonLineColor.setEnabled(False)

                # color properties
                self.toolButtonMarkerColor.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(True)
                self.comboBoxColorScale.setEnabled(False)
                self.lineEditColorLB.setEnabled(True)
                self.lineEditColorUB.setEnabled(True)
                self.comboBoxCbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(False)
                if plot_type.lower() == 'correlation':
                    self.comboBoxColorByField.setEnabled(True)
                    if self.comboBoxColorByField.currentText() == 'Cluster':
                        self.comboBoxColorField.setEnabled(True)
                    else:
                        self.comboBoxColorField.setEnabled(False)

                else:
                    self.comboBoxColorByField.setEnabled(False)
                    self.comboBoxColorField.setEnabled(False)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'histogram':
                # axes properties
                self.lineEditXLB.setEnabled(True)
                self.lineEditXUB.setEnabled(True)
                self.comboBoxXScale.setEnabled(True)
                self.lineEditYLB.setEnabled(True)
                self.lineEditYUB.setEnabled(True)
                self.comboBoxYScale.setEnabled(False)
                self.lineEditXLabel.setEnabled(True)
                self.lineEditYLabel.setEnabled(True)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(True)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.lineEditScaleLength.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(True)
                self.labelMarkerAlpha.setEnabled(True)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)
                self.toolButtonLineColor.setEnabled(True)
                self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(True)
                # if color by field is set to clusters, then colormap fields are on,
                # field is set by cluster table
                self.comboBoxColorScale.setEnabled(False)
                if self.comboBoxColorByField.currentText().lower() == 'none':
                    self.toolButtonMarkerColor.setEnabled(True)
                    self.comboBoxColorField.setEnabled(False)
                    self.comboBoxCbarDirection.setEnabled(False)
                else:
                    self.toolButtonMarkerColor.setEnabled(False)
                    self.comboBoxColorField.setEnabled(True)
                    self.comboBoxCbarDirection.setEnabled(True)

                self.comboBoxFieldColormap.setEnabled(False)
                self.lineEditColorLB.setEnabled(False)
                self.lineEditColorUB.setEnabled(False)
                self.lineEditCbarLabel.setEnabled(False)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'scatter' | 'pca scatter':
                # axes properties
                if (self.toolBox.currentIndex() != self.left_tab['scatter']) or (self.comboBoxFieldZ.currentText() == ''):
                    self.lineEditXLB.setEnabled(True)
                    self.lineEditXUB.setEnabled(True)
                    self.comboBoxXScale.setEnabled(True)
                    self.lineEditYLB.setEnabled(True)
                    self.lineEditYUB.setEnabled(True)
                    self.comboBoxYScale.setEnabled(True)
                else:
                    self.lineEditXLB.setEnabled(False)
                    self.lineEditXUB.setEnabled(False)
                    self.comboBoxXScale.setEnabled(False)
                    self.lineEditYLB.setEnabled(False)
                    self.lineEditYUB.setEnabled(False)
                    self.comboBoxYScale.setEnabled(False)

                self.lineEditXLabel.setEnabled(True)
                self.lineEditYLabel.setEnabled(True)
                if self.comboBoxFieldZ.currentText() == '':
                    self.lineEditZLabel.setEnabled(False)
                else:
                    self.lineEditZLabel.setEnabled(True)
                self.lineEditAspectRatio.setEnabled(True)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.lineEditScaleLength.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(True)
                self.doubleSpinBoxMarkerSize.setEnabled(True)
                self.horizontalSliderMarkerAlpha.setEnabled(True)
                self.labelMarkerAlpha.setEnabled(True)

                # line properties
                if self.comboBoxFieldZ.currentText() == '':
                    self.comboBoxLineWidth.setEnabled(True)
                    self.toolButtonLineColor.setEnabled(True)
                else:
                    self.comboBoxLineWidth.setEnabled(False)
                    self.toolButtonLineColor.setEnabled(False)

                if plot_type == 'pca scatter':
                    self.lineEditLengthMultiplier.setEnabled(True)
                else:
                    self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(True)
                # if color by field is none, then use marker color,
                # otherwise turn off marker color and turn all field and colormap properties to on
                if self.comboBoxColorByField.currentText().lower() == 'none':
                    self.toolButtonMarkerColor.setEnabled(True)

                    self.comboBoxColorField.setEnabled(False)
                    self.comboBoxFieldColormap.setEnabled(False)
                    self.lineEditColorLB.setEnabled(False)
                    self.lineEditColorUB.setEnabled(False)
                    self.comboBoxColorScale.setEnabled(False)
                    self.comboBoxCbarDirection.setEnabled(False)
                    self.lineEditCbarLabel.setEnabled(False)
                elif self.comboBoxColorByField.currentText() == 'Cluster':
                    self.toolButtonMarkerColor.setEnabled(False)

                    self.comboBoxColorField.setEnabled(True)
                    self.comboBoxFieldColormap.setEnabled(False)
                    self.lineEditColorLB.setEnabled(False)
                    self.lineEditColorUB.setEnabled(False)
                    self.comboBoxColorScale.setEnabled(False)
                    self.comboBoxCbarDirection.setEnabled(True)
                    self.lineEditCbarLabel.setEnabled(False)
                else:
                    self.toolButtonMarkerColor.setEnabled(False)

                    self.comboBoxColorField.setEnabled(True)
                    self.comboBoxFieldColormap.setEnabled(True)
                    self.lineEditColorLB.setEnabled(True)
                    self.lineEditColorUB.setEnabled(True)
                    self.comboBoxColorScale.setEnabled(True)
                    self.comboBoxCbarDirection.setEnabled(True)
                    self.lineEditCbarLabel.setEnabled(True)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'heatmap' | 'pca heatmap':
                # axes properties
                if (self.toolBox.currentIndex() != self.left_tab['scatter']) or (self.comboBoxFieldZ.currentText() == ''):
                    self.lineEditXLB.setEnabled(True)
                    self.lineEditXUB.setEnabled(True)
                    self.comboBoxXScale.setEnabled(True)
                    self.lineEditYLB.setEnabled(True)
                    self.lineEditYUB.setEnabled(True)
                    self.comboBoxYScale.setEnabled(True)
                else:
                    self.lineEditXLB.setEnabled(False)
                    self.lineEditXUB.setEnabled(False)
                    self.comboBoxXScale.setEnabled(False)
                    self.lineEditYLB.setEnabled(False)
                    self.lineEditYUB.setEnabled(False)
                    self.comboBoxYScale.setEnabled(False)

                self.lineEditXLabel.setEnabled(True)
                self.lineEditYLabel.setEnabled(True)
                if (self.toolBox.currentIndex() != self.left_tab['scatter']) or (self.comboBoxFieldZ.currentText() == ''):
                    self.lineEditZLabel.setEnabled(False)
                else:
                    self.lineEditZLabel.setEnabled(True)
                self.lineEditAspectRatio.setEnabled(True)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.toolButtonOverlayColor.setEnabled(False)
                self.lineEditScaleLength.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                if self.comboBoxFieldZ.currentText() == '':
                    self.comboBoxLineWidth.setEnabled(True)
                    self.toolButtonLineColor.setEnabled(True)
                else:
                    self.comboBoxLineWidth.setEnabled(False)
                    self.toolButtonLineColor.setEnabled(False)

                if plot_type == 'pca heatmap':
                    self.lineEditLengthMultiplier.setEnabled(True)
                else:
                    self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.toolButtonMarkerColor.setEnabled(False)
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxColorField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(True)
                self.lineEditColorLB.setEnabled(True)
                self.lineEditColorUB.setEnabled(True)
                self.comboBoxColorScale.setEnabled(True)
                self.comboBoxCbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(True)

                self.spinBoxHeatmapResolution.setEnabled(True)
            case 'ternary map':
                # axes properties
                self.lineEditXLB.setEnabled(True)
                self.lineEditXUB.setEnabled(True)
                self.comboBoxXScale.setEnabled(False)
                self.lineEditYLB.setEnabled(True)
                self.lineEditYUB.setEnabled(True)
                self.comboBoxXScale.setEnabled(False)
                self.lineEditXLabel.setEnabled(True)
                self.lineEditYLabel.setEnabled(True)
                self.lineEditZLabel.setEnabled(True)
                self.lineEditAspectRatio.setEnabled(False)
                self.comboBoxTickDirection.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(True)
                self.comboBoxScaleLocation.setEnabled(True)
                self.lineEditScaleLength.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if len(self.spotdata.spots) != 0:
                    self.comboBoxMarker.setEnabled(True)
                    self.doubleSpinBoxMarkerSize.setEnabled(True)
                    self.horizontalSliderMarkerAlpha.setEnabled(True)
                    self.labelMarkerAlpha.setEnabled(True)

                    self.toolButtonMarkerColor.setEnabled(True)
                else:
                    self.comboBoxMarker.setEnabled(False)
                    self.doubleSpinBoxMarkerSize.setEnabled(False)
                    self.horizontalSliderMarkerAlpha.setEnabled(False)
                    self.labelMarkerAlpha.setEnabled(False)

                    self.toolButtonMarkerColor.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(False)
                self.lineEditLengthMultiplier.setEnabled(False)
                self.toolButtonLineColor.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxColorField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(False)
                self.comboBoxColorScale.setEnabled(False)
                self.lineEditColorLB.setEnabled(False)
                self.lineEditColorUB.setEnabled(False)
                self.comboBoxCbarDirection.setEnabled(True)
                self.lineEditCbarLabel.setEnabled(False)

                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'tec' | 'radar':
                # axes properties
                self.lineEditXLB.setEnabled(False)
                self.lineEditXUB.setEnabled(False)
                self.lineEditXLabel.setEnabled(False)
                if plot_type == 'tec':
                    self.lineEditYLB.setEnabled(True)
                    self.lineEditYUB.setEnabled(True)
                    self.lineEditYLabel.setEnabled(True)
                else:
                    self.lineEditYLB.setEnabled(False)
                    self.lineEditYUB.setEnabled(False)
                    self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(True)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.lineEditScaleLength.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(False)
                self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(True)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)
                self.toolButtonLineColor.setEnabled(True)
                self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.comboBoxColorByField.setEnabled(True)
                if self.comboBoxColorByField.currentText().lower() == 'none':
                    self.toolButtonMarkerColor.setEnabled(True)
                    self.comboBoxColorField.setEnabled(False)
                    self.comboBoxFieldColormap.setEnabled(False)
                    self.comboBoxCbarDirection.setEnabled(False)
                elif self.comboBoxColorByField.currentText().lower() == 'cluster':
                    self.toolButtonMarkerColor.setEnabled(False)
                    self.comboBoxColorField.setEnabled(True)
                    self.comboBoxFieldColormap.setEnabled(False)
                    self.comboBoxCbarDirection.setEnabled(True)

                self.comboBoxColorScale.setEnabled(False)
                self.lineEditColorLB.setEnabled(False)
                self.lineEditColorUB.setEnabled(False)
                self.lineEditCbarLabel.setEnabled(False)
                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'variance':
                # axes properties
                self.lineEditXLB.setEnabled(False)
                self.lineEditXUB.setEnabled(False)
                self.lineEditXLabel.setEnabled(False)
                self.lineEditYLB.setEnabled(False)
                self.lineEditYUB.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(True)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.lineEditScaleLength.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                self.comboBoxMarker.setEnabled(True)
                self.doubleSpinBoxMarkerSize.setEnabled(True)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)
                self.toolButtonLineColor.setEnabled(True)
                self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.toolButtonMarkerColor.setEnabled(True)
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(False)
                self.lineEditColorLB.setEnabled(False)
                self.lineEditColorUB.setEnabled(False)
                self.comboBoxColorScale.setEnabled(False)
                self.comboBoxCbarDirection.setEnabled(False)
                self.lineEditCbarLabel.setEnabled(False)
                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'pca score' | 'cluster score' | 'cluster':
                # axes properties
                self.lineEditXLB.setEnabled(True)
                self.lineEditXUB.setEnabled(True)
                self.lineEditYLB.setEnabled(True)
                self.lineEditYUB.setEnabled(True)
                self.lineEditXLabel.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(False)
                self.comboBoxTickDirection.setEnabled(False)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(True)
                self.comboBoxScaleLocation.setEnabled(True)
                self.lineEditScaleLength.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(True)

                # marker properties
                if len(self.spotdata) != 0:
                    self.comboBoxMarker.setEnabled(True)
                    self.doubleSpinBoxMarkerSize.setEnabled(True)
                    self.horizontalSliderMarkerAlpha.setEnabled(True)
                    self.labelMarkerAlpha.setEnabled(True)

                    self.toolButtonMarkerColor.setEnabled(True)
                else:
                    self.comboBoxMarker.setEnabled(False)
                    self.doubleSpinBoxMarkerSize.setEnabled(False)
                    self.horizontalSliderMarkerAlpha.setEnabled(False)
                    self.labelMarkerAlpha.setEnabled(False)

                    self.toolButtonMarkerColor.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)
                self.toolButtonLineColor.setEnabled(True)
                self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                if plot_type == 'clusters':
                    self.comboBoxColorByField.setEnabled(False)
                    self.comboBoxColorField.setEnabled(False)
                    self.comboBoxFieldColormap.setEnabled(False)
                    self.lineEditColorLB.setEnabled(False)
                    self.lineEditColorUB.setEnabled(False)
                    self.comboBoxColorScale.setEnabled(False)
                    self.comboBoxCbarDirection.setEnabled(False)
                    self.lineEditCbarLabel.setEnabled(False)
                else:
                    self.comboBoxColorByField.setEnabled(True)
                    self.comboBoxColorField.setEnabled(True)
                    self.comboBoxFieldColormap.setEnabled(True)
                    self.lineEditColorLB.setEnabled(True)
                    self.lineEditColorUB.setEnabled(True)
                    self.comboBoxColorScale.setEnabled(True)
                    self.comboBoxCbarDirection.setEnabled(True)
                    self.lineEditCbarLabel.setEnabled(True)
                self.spinBoxHeatmapResolution.setEnabled(False)
            case 'profile':
                # axes properties
                self.lineEditXLB.setEnabled(True)
                self.lineEditXUB.setEnabled(True)
                self.lineEditXLabel.setEnabled(True)
                self.lineEditYLB.setEnabled(False)
                self.lineEditYUB.setEnabled(False)
                self.lineEditYLabel.setEnabled(False)
                self.lineEditZLabel.setEnabled(False)
                self.lineEditAspectRatio.setEnabled(True)
                self.comboBoxTickDirection.setEnabled(True)

                # scalebar properties
                self.comboBoxScaleDirection.setEnabled(False)
                self.comboBoxScaleLocation.setEnabled(False)
                self.lineEditScaleLength.setEnabled(True)
                self.toolButtonOverlayColor.setEnabled(False)

                # marker properties
                self.comboBoxMarker.setEnabled(True)
                self.doubleSpinBoxMarkerSize.setEnabled(True)
                self.horizontalSliderMarkerAlpha.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)

                # line properties
                self.comboBoxLineWidth.setEnabled(True)
                self.toolButtonLineColor.setEnabled(True)
                self.lineEditLengthMultiplier.setEnabled(False)

                # color properties
                self.toolButtonMarkerColor.setEnabled(True)
                self.comboBoxColorByField.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(True)
                self.lineEditColorLB.setEnabled(False)
                self.lineEditColorUB.setEnabled(False)
                self.comboBoxColorScale.setEnabled(False)
                self.comboBoxCbarDirection.setEnabled(False)
                self.lineEditCbarLabel.setEnabled(False)
                self.spinBoxHeatmapResolution.setEnabled(False)

        # enable/disable labels
        # axes properties
        self.labelXLim.setEnabled(self.lineEditXLB.isEnabled())
        self.toolButtonXAxisReset.setEnabled(self.labelXLim.isEnabled())
        self.labelXScale.setEnabled(self.comboBoxXScale.isEnabled())
        self.labelYLim.setEnabled(self.lineEditYLB.isEnabled())
        self.toolButtonYAxisReset.setEnabled(self.labelYLim.isEnabled())
        self.labelYScale.setEnabled(self.comboBoxYScale.isEnabled())
        self.labelXLabel.setEnabled(self.lineEditXLabel.isEnabled())
        self.labelYLabel.setEnabled(self.lineEditYLabel.isEnabled())
        self.labelZLabel.setEnabled(self.lineEditZLabel.isEnabled())
        self.labelAspectRatio.setEnabled(self.lineEditAspectRatio.isEnabled())
        self.labelTickDirection.setEnabled(self.comboBoxTickDirection.isEnabled())

        # scalebar properties
        self.labelScaleLocation.setEnabled(self.comboBoxScaleLocation.isEnabled())
        self.labelScaleDirection.setEnabled(self.comboBoxScaleDirection.isEnabled())
        if self.toolButtonOverlayColor.isEnabled():
            self.labelOverlayColor.setEnabled(True)
        else:
            self.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % '#e6e6e6')
            self.labelOverlayColor.setEnabled(False)
        self.labelScaleLength.setEnabled(self.lineEditScaleLength.isEnabled())

        # marker properties
        self.labelMarker.setEnabled(self.comboBoxMarker.isEnabled())
        self.labelMarkerSize.setEnabled(self.doubleSpinBoxMarkerSize.isEnabled())
        self.labelTransparency.setEnabled(self.horizontalSliderMarkerAlpha.isEnabled())

        # line properties
        self.labelLineWidth.setEnabled(self.comboBoxLineWidth.isEnabled())
        self.labelLineColor.setEnabled(self.toolButtonLineColor.isEnabled())
        self.labelLengthMultiplier.setEnabled(self.lineEditLengthMultiplier.isEnabled())

        # color properties
        if self.toolButtonMarkerColor.isEnabled():
            self.labelMarkerColor.setEnabled(True)
        else:
            self.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % '#e6e6e6')
            self.labelMarkerColor.setEnabled(False)
        self.labelColorByField.setEnabled(self.comboBoxColorByField.isEnabled())
        self.labelColorField.setEnabled(self.comboBoxColorField.isEnabled())
        self.checkBoxReverseColormap.setEnabled(self.comboBoxFieldColormap.isEnabled())
        self.labelReverseColormap.setEnabled(self.checkBoxReverseColormap.isEnabled())
        self.labelFieldColormap.setEnabled(self.comboBoxFieldColormap.isEnabled())
        self.labelColorScale.setEnabled(self.comboBoxColorScale.isEnabled())
        self.labelColorBounds.setEnabled(self.lineEditColorLB.isEnabled())
        self.toolButtonCAxisReset.setEnabled(self.labelColorBounds.isEnabled())
        self.labelCbarDirection.setEnabled(self.comboBoxCbarDirection.isEnabled())
        self.labelCbarLabel.setEnabled(self.lineEditCbarLabel.isEnabled())
        self.labelHeatmapResolution.setEnabled(self.spinBoxHeatmapResolution.isEnabled())

    def set_style_widgets(self, plot_type=None, style=None):
        """Sets values in right toolbox style page

        :param plot_type: dictionary key into ``MainWindow.style``
        :type plot_type: str, optional
        """
        print('set_style_widgets')
        tab_id = self.toolBox.currentIndex()

        if plot_type is None:
            plot_type = self.plot_types[tab_id][self.plot_types[tab_id][0]+1]
            self.comboBoxPlotType.blockSignals(True)
            self.comboBoxPlotType.clear()
            self.comboBoxPlotType.addItems(self.plot_types[tab_id][1:])
            self.comboBoxPlotType.setCurrentText(plot_type)
            self.comboBoxPlotType.blockSignals(False)
        elif plot_type == '':
            return

        # toggle actionSwapAxes
        match plot_type:
            case 'analyte map':
                self.actionSwapAxes.setEnabled(True)
            case 'scatter' | 'heatmap':
                self.actionSwapAxes.setEnabled(True)
            case _:
                self.actionSwapAxes.setEnabled(False)

        if style is None:
            style = self.styles[plot_type]

        # axes properties
        # for map plots, check to see that 'X' and 'Y' are initialized
        if plot_type.lower() in self.map_plot_types:
            if ('X' not in list(self.axis_dict.keys())) or ('Y' not in list(self.axis_dict.keys())):
                # initialize 'X' and 'Y' axes
                # all plot types use the same map dimensions so just use Analyte for the field_type
                self.initialize_axis_values('Analyte','X')
                self.initialize_axis_values('Analyte','Y')
            xmin,xmax,xscale,xlabel = self.get_axis_values('Analyte','X')
            ymin,ymax,yscale,ylabel = self.get_axis_values('Analyte','Y')

            # set style dictionary values for X and Y
            style['Axes']['XLim'] = [xmin, xmax]
            style['Axes']['XScale'] = xscale
            style['Axes']['XLabel'] = 'X'
            style['Axes']['YLim'] = [ymin, ymax]
            style['Axes']['YScale'] = yscale
            style['Axes']['YLabel'] = 'Y'
            style['Axes']['AspectRatio'] = self.aspect_ratio

            # do not round axes limits for maps
            self.lineEditXLB.precision = None
            self.lineEditXUB.precision = None
            self.lineEditXLB.value = style['Axes']['XLim'][0]
            self.lineEditXUB.value = style['Axes']['XLim'][1]

            self.lineEditYLB.value = style['Axes']['YLim'][0]
            self.lineEditYUB.value = style['Axes']['YLim'][1]
        else:
            # round axes limits for everything that isn't a map
            self.lineEditXLB.value = style['Axes']['XLim'][0]
            self.lineEditXUB.value = style['Axes']['XLim'][1]

            self.lineEditYLB.value = style['Axes']['YLim'][0]
            self.lineEditYUB.value = style['Axes']['YLim'][1]

        self.comboBoxXScale.setCurrentText(style['Axes']['XScale'])
        self.lineEditXLabel.setText(style['Axes']['XLabel'])

        self.comboBoxYScale.setCurrentText(style['Axes']['YScale'])
        self.lineEditYLabel.setText(style['Axes']['YLabel'])

        self.lineEditZLabel.setText(style['Axes']['ZLabel'])
        self.lineEditAspectRatio.setText(str(style['Axes']['AspectRatio']))

        # annotation properties
        #self.fontComboBox.setCurrentFont(style['Text']['Font'])
        self.doubleSpinBoxFontSize.blockSignals(True)
        self.doubleSpinBoxFontSize.setValue(style['Text']['FontSize'])
        self.doubleSpinBoxFontSize.blockSignals(False)

        # scalebar properties
        self.comboBoxScaleLocation.setCurrentText(style['Scale']['Location'])
        self.comboBoxScaleDirection.setCurrentText(style['Scale']['Direction'])
        if (style['Scale']['Length'] is None) and (plot_type in self.map_plot_types):
            style['Scale']['Length'] = self.default_scale_length()

            self.lineEditScaleLength.value = style['Scale']['Length']
        else:
            self.lineEditScaleLength.value = None
            
        self.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % style['Scale']['OverlayColor'])

        # marker properties
        self.comboBoxMarker.setCurrentText(style['Markers']['Symbol'])

        self.doubleSpinBoxMarkerSize.blockSignals(True)
        self.doubleSpinBoxMarkerSize.setValue(style['Markers']['Size'])
        self.doubleSpinBoxMarkerSize.blockSignals(False)

        self.horizontalSliderMarkerAlpha.setValue(int(style['Markers']['Alpha']))
        self.labelMarkerAlpha.setText(str(self.horizontalSliderMarkerAlpha.value()))

        # line properties
        self.comboBoxLineWidth.setCurrentText(str(style['Lines']['LineWidth']))
        self.lineEditLengthMultiplier.value = style['Lines']['Multiplier']
        self.toolButtonLineColor.setStyleSheet("background-color: %s;" % style['Lines']['Color'])

        # color properties
        self.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % style['Colors']['Color'])
        self.update_field_type_combobox(self.comboBoxColorByField,addNone=True,plot_type=plot_type)
        self.comboBoxColorByField.setCurrentText(style['Colors']['ColorByField'])

        if style['Colors']['ColorByField'] == '':
            self.comboBoxColorField.clear()
        else:
            self.update_field_combobox(self.comboBoxColorByField, self.comboBoxColorField)

        if style['Colors']['Field'] in self.comboBoxColorField.allItems():
            self.comboBoxColorField.setCurrentText(style['Colors']['Field'])
        else:
            style['Colors']['Field'] = self.comboBoxColorField.currentText()

        self.comboBoxFieldColormap.setCurrentText(style['Colors']['Colormap'])
        self.checkBoxReverseColormap.blockSignals(True)
        self.checkBoxReverseColormap.setChecked(style['Colors']['Reverse'])
        self.checkBoxReverseColormap.blockSignals(False)
        if style['Colors']['Field'] in list(self.axis_dict.keys()):
            style['Colors']['CLim'] = [self.axis_dict[style['Colors']['Field']]['min'], self.axis_dict[style['Colors']['Field']]['max']]
            style['Colors']['CLabel'] = self.axis_dict[style['Colors']['Field']]['label']
        self.lineEditColorLB.value = style['Colors']['CLim'][0]
        self.lineEditColorUB.value = style['Colors']['CLim'][1]
        if style['Colors']['ColorByField'] == 'Cluster':
            # set ColorField to active cluster method
            self.comboBoxColorField.setCurrentText(self.cluster_dict['active method'])

            # set color scale to discrete
            self.comboBoxColorScale.clear()
            self.comboBoxColorScale.addItem('discrete')
            self.comboBoxColorScale.setCurrentText('discrete')

            self.styles[plot_type]['Colors']['CScale'] = 'discrete'
        else:
            # set color scale options to linear/log
            self.comboBoxColorScale.clear()
            self.comboBoxColorScale.addItems(['linear','log'])
            self.styles[plot_type]['Colors']['CScale'] = 'linear'
            self.comboBoxColorScale.setCurrentText(self.styles[plot_type]['Colors']['CScale'])
            
        self.comboBoxColorScale.setCurrentText(style['Colors']['CScale'])
        self.comboBoxCbarDirection.setCurrentText(style['Colors']['Direction'])
        self.lineEditCbarLabel.setText(style['Colors']['CLabel'])

        self.spinBoxHeatmapResolution.blockSignals(True)
        self.spinBoxHeatmapResolution.setValue(style['Colors']['Resolution'])
        self.spinBoxHeatmapResolution.blockSignals(False)

        # turn properties on/off based on plot type and style settings
        self.toggle_style_widgets()

        # update plot (is this line needed)
        # self.update_SV()

    def get_style_dict(self):
        """Get style properties"""        
        plot_type = self.comboBoxPlotType.currentText()
        self.plot_types[self.toolBox.currentIndex()][0] = self.comboBoxPlotType.currentIndex()

        # update axes properties
        self.styles[plot_type]['Axes'] = {'XLim': [float(self.lineEditXLB.text()), float(self.lineEditXUB.text())],
                    'XLabel': self.lineEditXLabel.text(),
                    'YLim': [float(self.lineEditYLB.text()), float(self.lineEditYUB.text())],
                    'YLabel': self.lineEditYLabel.text(),
                    'ZLabel': self.lineEditZLabel.text(),
                    'AspectRatio': float(self.lineEditAspectRatio.text()),
                    'TickDir': self.comboBoxTickDirection.text()}

        # update annotation properties
        self.styles[plot_type]['Text'] = {'Font': self.fontComboBox.currentFont(),
                    'FontSize': self.doubleSpinBoxFontSize.value()}

        # update scale properties
        self.styles[plot_type]['Scale'] = {'Location': self.comboBoxScaleLocation.currentText(),
                    'Direction': self.comboBoxScaleDirection.currentText(),
                    'OverlayColor': self.get_hex_color(self.toolButtonOverlayColor.palette().button().color())}

        # update marker properties
        self.styles[plot_type]['Markers'] = {'Symbol': self.comboBoxMarker.currentText(),
                    'Size': self.doubleSpinBoxMarkerSize.value(),
                    'Alpha': float(self.horizontalSliderMarkerAlpha.value())}

        # update line properties
        self.styles[plot_type]['Lines'] = {'LineWidth': float(self.comboBoxLineWidth.currentText()),
                    'Multiplier': float(self.lineEditLengthMultiplier.text()),
                    'Color': self.get_hex_color(self.toolButtonMarkerColor.palette().button().color())}

        # update color properties
        self.styles[plot_type]['Colors'] = {'Color': self.get_hex_color(self.toolButtonMarkerColor.palette().button().color()),
                    'ColorByField': self.comboBoxColorByField.currentText(),
                    'Field': self.comboBoxColorField.currentText(),
                    'Colormap': self.comboBoxFieldColormap.currentText(),
                    'Reverse': self.checkBoxReverseColormap.isChecked(),
                    'CLim': [float(self.lineEditColorLB.text()), float(self.lineEditColorUB.text())],
                    'CScale': self.comboBoxColorScale.currentText(),
                    'Direction': self.comboBoxCbarDirection.currentText(),
                    'CLabel': self.lineEditCbarLabel.text(),
                    'Resolution': self.spinBoxHeatmapResolution.value()}

    # style widget callbacks
    # -------------------------------------
    def plot_type_callback(self, update=False):
        """Updates styles when plot type is changed

        Executes on change of ``MainWindow.comboBoxPlotType``.  Updates ``MainWindow.plot_type[0]`` to the current index of the 
        combobox, then updates the style widgets to match the dictionary entries and updates the plot.
        """
        print('plot_type_callback')
        # set plot flag to false
        plot_type = self.comboBoxPlotType.currentText()
        self.plot_types[self.toolBox.currentIndex()][0] = self.comboBoxPlotType.currentIndex()
        match plot_type:
            case 'analyte map':
                self.actionSwapAxes.setEnabled(True)
            case 'scatter' | 'heatmap':
                self.actionSwapAxes.setEnabled(True)
            case 'correlation':
                self.actionSwapAxes.setEnabled(False)
                if self.comboBoxCorrelationMethod.currentText() == 'None':
                    self.comboBoxCorrelationMethod.setCurrentText('Pearson')
            case _:
                self.actionSwapAxes.setEnabled(False)

        self.set_style_widgets(plot_type=plot_type)
        #self.check_analysis_type()

        if update:
            self.update_SV()

    # axes
    # -------------------------------------
    def get_axis_field(self, ax):
        """Grabs the field name from a given axis

        The field name for a given axis comes from a comboBox, and depends upon the plot type.
        :param ax: axis, options include ``x``, ``y``, ``z``, and ``c``
        :type ax: str
        """
        plot_type = self.comboBoxPlotType.currentText()
        if ax == 'c':
            return self.comboBoxColorField.currentText()

        match plot_type:
            case 'histogram':
                if ax in ['x', 'y']:
                    return self.comboBoxHistField.currentText()
            case 'scatter' | 'heatmap':
                match ax:
                    case 'x':
                        return self.comboBoxFieldX.currentText()
                    case 'y':
                        return self.comboBoxFieldY.currentText()
                    case 'z':
                        return self.comboBoxFieldZ.currentText()
            case 'pca scatter' | 'pca heatmap':
                match ax:
                    case 'x':
                        return f'PC{self.spinBoxPCX.value()}'
                    case 'y':
                        return f'PC{self.spinBoxPCY.value()}'
            case 'analyte map' | 'ternary map' | 'PCA Score' | 'Cluster' | 'Cluster Score':
                return ax.upper()


    def axis_label_edit_callback(self, ax, new_label):
        """Updates axis label in dictionaries from widget

        :param ax: axis, options include ``x``, ``y``, ``z``, and ``c``
        :type ax: str
        :param new_label: new label set by user
        :type new_label: str
        """
        plot_type = self.comboBoxPlotType.currentText()

        old_label = self.styles[plot_type]['Axes'][ax.upper()+'Label']

        # if label has not changed return
        if old_label == new_label:
            return

        # change label in dictionary
        field = self.get_axis_field(ax)
        self.axis_dict[field]['label'] = new_label
        self.styles[plot_type]['Axes'][ax.upper()+'Label'] = new_label

        # update plot
        self.update_SV()

    def axis_limit_edit_callback(self, ax, bound, new_value):
        """Updates axis limit in dictionaries from widget

        :param ax: axis, options include ``x``, ``y``, ``z``, and ``c``
        :type ax: str
        :param bound: ``0`` for lower and ``1`` for upper
        :type bound: int
        :param new_value: new value set by user
        :type new_value: float
        """
        plot_type = self.comboBoxPlotType.currentText()

        if ax == 'c':
            old_value = self.styles[plot_type]['Colors']['CLim'][bound]
        else:
            old_value = self.styles[plot_type]['Axes'][ax.upper()+'Lim'][bound]

        # if label has not changed return
        if old_value == new_value:
            return

        if ax == 'c' and plot_type in ['heatmap', 'correlation']:
            self.update_SV()
            return

        # change label in dictionary
        field = self.get_axis_field(ax)
        if bound:
            if plot_type == 'histogram' and ax == 'y':
                self.axis_dict[field]['pmax'] = new_value
                self.axis_dict[field]['pstatus'] = 'custom'
            else:
                self.axis_dict[field]['max'] = new_value
                self.axis_dict[field]['status'] = 'custom'
        else:
            if plot_type == 'histogram' and ax == 'y':
                self.axis_dict[field]['pmin'] = new_value
                self.axis_dict[field]['pstatus'] = 'custom'
            else:
                self.axis_dict[field]['min'] = new_value
                self.axis_dict[field]['status'] = 'custom'

        if ax == 'c':
            self.styles[plot_type]['Colors'][f'{ax.upper()}Lim'][bound] = new_value
        else:
            self.styles[plot_type]['Axes'][f'{ax.upper()}Lim'][bound] = new_value

        # update plot
        self.update_SV()

    def axis_scale_callback(self, comboBox, ax):
        plot_type = self.comboBoxPlotType.currentText()

        new_value = comboBox.currentText()
        if ax == 'c':
            if self.styles[plot_type]['Colors']['CLim'] == new_value:
                return
        elif self.styles[plot_type]['Axes'][ax.upper()+'Scale'] == new_value:
            return

        field = self.get_axis_field(ax)
        self.axis_dict[field]['scale'] = new_value

        if ax == 'c':
            self.styles[plot_type]['Colors']['CScale'] = new_value
        else:
            self.styles[plot_type]['Axes'][ax.upper()+'Scale'] = new_value

        # update plot
        self.update_SV()

    def set_color_axis_widgets(self):
        """Sets the color axis widgets

        Sets color axis limits and label
        """
        #print('set_color_axis_widgets')
        field = self.comboBoxColorField.currentText()
        if field == '':
            return
        self.lineEditColorLB.value = self.axis_dict[field]['min']
        self.lineEditColorUB.value = self.axis_dict[field]['max']
        self.comboBoxColorScale.setCurrentText(self.axis_dict[field]['scale'])

    def set_axis_widgets(self, ax, field):
        """Sets axis widgets in the style toolbox

        Updates axes limits and labels.

        :param ax: axis 'x', 'y', or 'z'
        :type ax: str
        :param field: field plotted on axis, used as key to ``MainWindow.axis_dict``
        :type field: str
        """
        #print('set_axis_widgets')
        match ax:
            case 'x':
                if field == 'X':
                    self.lineEditXLB.value = self.axis_dict[field]['min']
                    self.lineEditXUB.value = self.axis_dict[field]['max']
                else:
                    self.lineEditXLB.value = self.axis_dict[field]['min']
                    self.lineEditXUB.value = self.axis_dict[field]['max']
                self.lineEditXLabel.setText(self.axis_dict[field]['label'])
                self.comboBoxXScale.setCurrentText(self.axis_dict[field]['scale'])
            case 'y':
                if self.comboBoxPlotType.currentText() == 'histogram':
                    self.lineEditYLB.value = self.axis_dict[field]['pmin']
                    self.lineEditYUB.value = self.axis_dict[field]['pmax']
                    self.lineEditYLabel.setText(self.comboBoxHistType.currentText())
                    self.comboBoxYScale.setCurrentText('linear')
                else:
                    if field == 'X':
                        self.lineEditYLB.value = self.axis_dict[field]['min']
                        self.lineEditYUB.value = self.axis_dict[field]['max']
                    else:
                        self.lineEditYLB.value = self.axis_dict[field]['min']
                        self.lineEditYUB.value = self.axis_dict[field]['max']
                    self.lineEditYLabel.setText(self.axis_dict[field]['label'])
                    self.comboBoxYScale.setCurrentText(self.axis_dict[field]['scale'])
            case 'z':
                self.lineEditZLabel.setText(self.axis_dict[field]['label'])

    def axis_reset_callback(self, ax):
        """Resets axes widgets and plot axes to auto values

        Axes parameters with ``MainWindow.axis_dict['status']`` can be ``auto`` or ``custom``, where ``custom``
        is set by the user in the appropriate *lineEdit* widgets.  The ``auto`` status is set by the full range
        of values of a data column.        

        Parameters
        ----------
        ax : str
            axis to reset values, can be ``x``, ``y``, and ``c``

        .. seealso::
            :ref: `initialize_axis_values` for initializing the axis dictionary
        """
        #print('axis_reset_callback')
        if ax == 'c':
            if self.comboBoxPlotType.currentText() == 'vectors':
                self.styles['vectors']['Colors']['CLim'] = [np.amin(self.pca_results.components_), np.amax(self.pca_results.components_)]
                self.set_color_axis_widgets()
            elif not (self.comboBoxColorByField.currentText() in ['None','Cluster']):
                field_type = self.comboBoxColorByField.currentText()
                field = self.comboBoxColorField.currentText()
                if field == '':
                    return
                self.initialize_axis_values(field_type, field)
                self.set_color_axis_widgets()
        else:
            match self.comboBoxPlotType.currentText().lower():
                case 'analyte map' | 'cluster' | 'cluster score' | 'pca score':
                    field = ax.upper()
                    self.initialize_axis_values('Analyte', field)
                    self.set_axis_widgets(ax, field)
                case 'histogram':
                    field = self.comboBoxHistField.currentText()
                    if ax == 'x':
                        field_type = self.comboBoxHistFieldType.currentText()
                        self.initialize_axis_values(field_type, field)
                        self.set_axis_widgets(ax, field)
                    else:
                        self.axis_dict[field].update({'pstatus':'auto', 'pmin':None, 'pmax':None})

                case 'scatter' | 'heatmap':
                    if ax == 'x':
                        field_type = self.comboBoxFieldTypeX.currentText()
                        field = self.comboBoxFieldX.currentText()
                    else:
                        field_type = self.comboBoxFieldTypeY.currentText()
                        field = self.comboBoxFieldY.currentText()
                    if (field_type == '') | (field == ''):
                        return
                    self.initialize_axis_values(field_type, field)
                    self.set_axis_widgets(ax, field)

                case 'pca scatter' | 'pca heatmap':
                    field_type = 'PCA Score'
                    if ax == 'x':
                        field = self.spinBoxPCX.currentText()
                    else:
                        field = self.spinBoxPCY.currentText()
                    self.initialize_axis_values(field_type, field)
                    self.set_axis_widgets(ax, field)

                case _:
                    return

        self.update_SV()

    def get_axis_values(self, field_type, field, ax=None):
        """Gets axis values

        Returns the axis parameters *field_type* \> *field* for plotting, including the minimum and maximum vales,
        the scale (``linear`` or ``log``) and the axis label.  For x, y and color axes associated with the plot,
        no axis needs to be supplied.  For a probability axis associated with histogram PDF plots, ``ax=p``.

        Parameters
        ----------
        field_type : str
            Field type of axis data
        field : str
            Field name of axis data
        ax : str, optional
            stored axis: ``p`` for probability axis, otherwise all are same, by default None

        Returns
        -------
        float, float, str, float
            Axis parameters: minimum, maximum, scale (``linear`` or ``log``), axis label
        """        
        #print('get_axis_values')
        if field not in self.axis_dict.keys():
            self.initialize_axis_values(field_type, field)

        # get axis values from self.axis_dict
        amin = self.axis_dict[field]['min']
        amax = self.axis_dict[field]['max']
        scale = self.axis_dict[field]['scale']
        label = self.axis_dict[field]['label']

        # if probability axis associated with histogram
        if ax == 'p':
            pmin = self.axis_dict[field]['pmin']
            pmax = self.axis_dict[field]['pmax']
            return amin, amax, scale, label, pmin, pmax

        return amin, amax, scale, label

    def initialize_axis_values(self, field_type, field):
        #print('initialize_axis_values')
        # initialize variables
        if field not in self.axis_dict.keys():
            #print('initialize self.axis_dict["field"]')
            self.axis_dict.update({field:{'status':'auto', 'label':field, 'min':None, 'max':None}})

        #current_plot_df = pd.DataFrame()
        if field not in ['X','Y']:
            df = self.get_map_data(self.sample_id, field, field_type)
            array = df['array'][self.data[self.sample_id]['mask']].values if not df.empty else []
        else:
            # field 'X' and 'Y' require separate extraction
            array = self.data[self.sample_id]['raw_data'].loc[:,field].values

        match field_type:
            case 'Analyte' | 'Analyte (normalized)':
                if field in ['X','Y']:
                    scale = 'linear'
                else:
                    #current_plot_df = self.data[self.sample_id]['processed_data'].loc[:,field].values
                    symbol, mass = self.parse_field(field)
                    if field_type == 'Analyte':
                        self.axis_dict[field]['label'] = f"$^{{{mass}}}${symbol} ({self.preferences['Units']['Concentration']})"
                    else:
                        self.axis_dict[field]['label'] = f"$^{{{mass}}}${symbol}$_N$ ({self.preferences['Units']['Concentration']})"

                    #amin = self.data[self.sample_id]['analyte_info'].loc[(self.data[self.sample_id]['analyte_info']['analytes']==field),'v_min'].values[0]
                    #amax = self.data[self.sample_id]['analyte_info'].loc[(self.data[self.sample_id]['analyte_info']['analytes']==field),'v_max'].values[0]
                    scale = self.data[self.sample_id]['analyte_info'].loc[(self.data[self.sample_id]['analyte_info']['analytes']==field),'norm'].values[0]

                amin = np.nanmin(array)
                amax = np.nanmax(array)
            case 'Ratio' | 'Ratio (normalized)':
                field_1 = field.split(' / ')[0]
                field_2 = field.split(' / ')[1]
                symbol_1, mass_1 = self.parse_field(field_1)
                symbol_2, mass_2 = self.parse_field(field_2)
                if field_type == 'Ratio':
                    self.axis_dict[field]['label'] = f"$^{{{mass_1}}}${symbol_1} / $^{{{mass_2}}}${symbol_2}"
                else:
                    self.axis_dict[field]['label'] = f"$^{{{mass_1}}}${symbol_1}$_N$ / $^{{{mass_2}}}${symbol_2}$_N$"

                amin = np.nanmin(array)
                amax = np.nanmax(array)
                scale = self.data[self.sample_id]['ratio_info'].loc[
                    (self.data[self.sample_id]['ratio_info']['analyte_1']==field_1) & (self.data[self.sample_id]['ratio_info']['analyte_2']==field_2),
                    'norm'].values[0]
            case _:
                #current_plot_df = self.data[self.sample_id]['computed_data'][field_type].loc[:,field].values
                scale = 'linear'

                amin = np.nanmin(array)
                amax = np.nanmax(array)

        # do not round 'X' and 'Y' so full extent of map is viewable
        if field not in ['X','Y']:
            amin = fmt.oround(amin, order=2, toward=0)
            amax = fmt.oround(amax, order=2, toward=1)

        d = {'status':'auto', 'min':amin, 'max':amax, 'scale':scale}

        self.axis_dict[field].update(d)
        #print(self.axis_dict[field])

    def parse_field(self,field):

        match = re.match(r"([A-Za-z]+)(\d*)", field)
        symbol = match.group(1) if match else field
        mass = int(match.group(2)) if match.group(2) else None

        return symbol, mass

    def aspect_ratio_callback(self):
        """Update aspect ratio

        Updates ``MainWindow.style`` dictionary after user change
        """
        plot_type = self.comboBoxPlotType.currentText()
        if self.styles[plot_type]['Axes']['AspectRatio'] == self.lineEditAspectRatio.text():
            return

        self.styles[plot_type]['Axes']['AspectRatio'] = self.lineEditAspectRatio.text()
        self.update_SV()

    def tickdir_callback(self):
        plot_type = self.comboBoxPlotType.currentText()
        if self.styles[plot_type]['Axes']['TickDir'] == self.comboBoxTickDirection.currentText():
            return

        self.styles[plot_type]['Axes']['TickDir'] = self.comboBoxTickDirection.currentText()
        self.update_SV()

    # text and annotations
    # -------------------------------------
    def font_callback(self):
        plot_type = self.comboBoxPlotType.currentText()
        if self.styles[plot_type]['Text']['Font'] == self.fontComboBox.currentFont().family():
            return

        self.styles[plot_type]['Text']['Font'] = self.fontComboBox.currentFont().family()
        self.update_SV()

    def font_size_callback(self):
        plot_type = self.comboBoxPlotType.currentText()
        if self.styles[plot_type]['Text']['FontSize'] == self.doubleSpinBoxFontSize.value():
            return

        self.styles[plot_type]['Text']['FontSize'] = self.doubleSpinBoxFontSize.value()
        self.update_SV()

    def update_figure_font(self, canvas, font_name):
        if font_name == '':
            return

        # Update font of all text elements in the figure
        try:
            for text_obj in canvas.fig.findobj(match=plt.Text):
                text_obj.set_fontname(font_name)
        except:
            print('Unable to update figure font.')

    def toggle_mass(self, labels):
        """Removes mass from labels

        Removes mass if ``MainWindow.checkBoxShowMass.isChecked()`` is False

        :param labels: input labels
        :type labels: str

        :return: output labels with or without mass
        :rtype: list
        """
        if not self.checkBoxShowMass.isChecked():
            labels = [re.sub(r'\d', '', col) for col in labels]

        return labels

    # scales
    # -------------------------------------
    def scale_direction_callback(self):
        plot_type = self.comboBoxPlotType.currentText()
        direction = self.comboBoxScaleDirection.currentText()
        if self.styles[plot_type]['Scale']['Direction'] == direction:
            return

        self.styles[plot_type]['Scale']['Direction'] = direction
        if direction == 'none':
            self.labelScaleLocation.setEnabled(False)
            self.comboBoxScaleLocation.setEnabled(False)
            self.labelScaleLength.setEnabled(False)
            self.lineEditScaleLength.setEnabled(False)
            self.lineEditScaleLength.value = None
        else:
            self.labelScaleLocation.setEnabled(True)
            self.comboBoxScaleLocation.setEnabled(True)
            self.labelScaleLength.setEnabled(True)
            self.lineEditScaleLength.setEnabled(True)
            # set scalebar length if plot is a map type
            if plot_type in self.map_plot_types:
                if self.styles[plot_type]['Scale']['Length'] is None:
                    scale_length = self.default_scale_length()
                elif ((direction == 'horizontal') and (self.styles[plot_type]['Scale']['Length'] > self.x_range)) or ((direction == 'vertical') and (self.styles[plot_type]['Scale']['Length'] > self.y_range)):
                    scale_length = self.default_scale_length()
                else:
                    scale_length = self.styles[plot_type]['Scale']['Length']
                self.styles[plot_type]['Scale']['Length'] = scale_length
                self.lineEditScaleLength.value = scale_length
            else:
                self.lineEditScaleLength.value = None

        self.update_SV()

    def scale_location_callback(self):
        plot_type = self.comboBoxPlotType.currentText()

        if self.styles[plot_type]['Scale']['Location'] == self.comboBoxScaleLocation.currentText():
            return

        self.styles[plot_type]['Scale']['Location'] = self.comboBoxScaleLocation.currentText()
        self.update_SV()

    def scale_length_callback(self):
        """Updates length of scalebar on map-type plots
        
        Executes on change of ``MainWindow.lineEditScaleLength``, updates length if within bounds set by plot dimensions, then updates plot.
        """        
        plot_type = self.comboBoxPlotType.currentText()

        # if length is changed to None
        if self.lineEditScaleLength.text() == '':
            if self.styles[plot_type]['Scale']['Length'] is None:
                return
            else:
                self.styles[plot_type]['Scale']['Length'] = None
                self.update_SV()
                return

        scale_length = float(self.lineEditScaleLength.text())
        if plot_type in self.map_plot_types:
            # make sure user input is within bounds, do not change
            if ((self.comboBoxScaleDirection.currentText() == 'horizontal') and (scale_length > self.x_range)) or (scale_length <= 0):
                scale_length = self.styles[plot_type]['Scale']['Length']
                self.lineEditScaleLength.value = scale_length
                return
            elif ((self.comboBoxScaleDirection.currentText() == 'vertical') and (scale_length > self.y_range)) or (scale_length <= 0):
                scale_length = self.styles[plot_type]['Scale']['Length']
                self.lineEditScaleLength.value = scale_length
                return
        else:
            self.lineEditScaleLength.value = None
            return

        # update style dictionary
        if scale_length == self.styles[plot_type]['Scale']['Length']:
            return
        self.styles[plot_type]['Scale']['Length'] = scale_length

        # update plot
        self.update_SV()

    def overlay_color_callback(self):
        """Updates color of overlay markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.toolButtonOverlayColor`` color.
        """
        plot_type = self.comboBoxPlotType.currentText()
        # change color
        self.button_color_select(self.toolButtonOverlayColor)

        color = self.get_hex_color(self.toolButtonOverlayColor.palette().button().color())
        # update style
        if self.styles[plot_type]['Scale']['OverlayColor'] == color:
            return

        self.styles[plot_type]['Scale']['OverlayColor'] = color
        # update plot
        self.update_SV()

    # markers
    # -------------------------------------
    def marker_symbol_callback(self):
        """Updates marker symbol

        Updates marker symbols on current plot on change of ``MainWindow.comboBoxMarker.currentText()``.
        """
        plot_type = self.comboBoxPlotType.currentText()
        if self.styles[plot_type]['Markers']['Symbol'] == self.comboBoxMarker.currentText():
            return
        self.styles[plot_type]['Markers']['Symbol'] = self.comboBoxMarker.currentText()

        self.update_SV()

    def marker_size_callback(self):
        """Updates marker size

        Updates marker size on current plot on change of ``MainWindow.doubleSpinBoxMarkerSize.value()``.
        """
        plot_type = self.comboBoxPlotType.currentText()
        if self.styles[plot_type]['Markers']['Size'] == self.doubleSpinBoxMarkerSize.value():
            return
        self.styles[plot_type]['Markers']['Size'] = self.doubleSpinBoxMarkerSize.value()

        self.update_SV()

    def slider_alpha_changed(self):
        """Updates transparency on scatter plots.

        Executes on change of ``MainWindow.horizontalSliderMarkerAlpha.value()``.
        """
        plot_type = self.comboBoxPlotType.currentText()
        self.labelMarkerAlpha.setText(str(self.horizontalSliderMarkerAlpha.value()))

        if self.horizontalSliderMarkerAlpha.isEnabled():
            self.styles[plot_type]['Markers']['Alpha'] = float(self.horizontalSliderMarkerAlpha.value())
            self.update_SV()

    # lines
    # -------------------------------------
    def line_width_callback(self):
        """Updates line width

        Updates line width on current plot on change of ``MainWindow.comboBoxLineWidth.currentText()."""
        plot_type = self.comboBoxPlotType.currentText()
        if self.styles[plot_type]['Lines']['LineWidth'] == float(self.comboBoxLineWidth.currentText()):
            return

        self.styles[plot_type]['Lines']['LineWidth'] = float(self.comboBoxLineWidth.currentText())
        self.update_SV()

    def length_multiplier_callback(self):
        """Updates line length multiplier

        Used when plotting vector components in multidimensional plots.  Values entered by the user must be (0,10]
        """
        plot_type = self.comboBoxPlotType.currentText()
        if not float(self.lineEditLengthMultiplier.text()):
            self.lineEditLengthMultiplier.values = self.styles[plot_type]['Lines']['Multiplier']

        value = float(self.lineEditLengthMultiplier.text())
        if self.styles[plot_type]['Lines']['Multiplier'] == value:
            return
        elif (value < 0) or (value >= 100):
            self.lineEditLengthMultiplier.values = self.styles[plot_type]['Lines']['Multiplier']
            return

        self.styles[plot_type]['Lines']['Multiplier'] = value
        self.update_SV()

    def line_color_callback(self):
        """Updates color of plot markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.toolButtonLineColor`` color.
        """
        plot_type = self.comboBoxPlotType.currentText()
        # change color
        self.button_color_select(self.toolButtonLineColor)
        color = self.get_hex_color(self.toolButtonLineColor.palette().button().color())
        if self.styles[plot_type]['Lines']['Color'] == color:
            return

        # update style
        self.styles[plot_type]['Lines']['Color'] = color

        # update plot
        self.update_SV()

    # colors
    # -------------------------------------
    def marker_color_callback(self):
        """Updates color of plot markers

        Uses ``QColorDialog`` to select new marker color and then updates plot on change of backround ``MainWindow.toolButtonMarkerColor`` color.
        """
        plot_type = self.comboBoxPlotType.currentText()
        # change color
        self.button_color_select(self.toolButtonMarkerColor)
        color = self.get_hex_color(self.toolButtonMarkerColor.palette().button().color())
        if self.styles[plot_type]['Colors']['Color'] == color:
            return

        # update style
        self.styles[plot_type]['Colors']['Color'] = color

        # update plot
        self.update_SV()

    def resolution_callback(self, update_plot=False):
        """Updates heatmap resolution

        Updates the resolution of heatmaps when ``MainWindow.spinBoxHeatmapResolution`` is changed.

        Parameters
        ----------
        update_plot : bool, optional
            Sets the resolution of a heatmap for either Cartesian or ternary plots and both *heatmap* and *pca heatmap*, by default ``False``
        """        
        style = self.styles[self.comboBoxPlotType.currentText()]

        style['Colors']['Resolution'] = self.spinBoxHeatmapResolution.value()

        if update_plot:
            self.update_SV()

    # updates scatter styles when ColorByField comboBox is changed
    def color_by_field_callback(self):
        """Executes on change to *ColorByField* combobox
        
        Updates style associated with ``MainWindow.comboBoxColorByField``.  Also updates
        ``MainWindow.comboBoxColorField`` and ``MainWindow.comboBoxColorScale``."""
        #print('color_by_field_callback')
        # need this line to update field comboboxes when colorby field is updated
        self.update_field_combobox(self.comboBoxColorByField, self.comboBoxColorField)
        plot_type = self.comboBoxPlotType.currentText()
        if plot_type == '':
            return

        style = self.styles[plot_type]
        if style['Colors']['ColorByField'] == self.comboBoxColorByField.currentText():
            return

        style['Colors']['ColorByField'] = self.comboBoxColorByField.currentText()
        if self.comboBoxColorByField.currentText() != '':
            self.set_style_widgets(plot_type)

        if self.comboBoxPlotType.isEnabled() == False | self.comboBoxColorByField.isEnabled() == False:
            return

        # only run update current plot if color field is selected or the color by field is clusters
        if self.comboBoxColorByField.currentText() != 'None' or self.comboBoxColorField.currentText() != '' or self.comboBoxColorByField.currentText() in ['Cluster']:
            self.update_SV()

    def color_field_callback(self, plot= True):
        """Updates color field and plot

        Executes on change of ``MainWindow.comboBoxColorField``
        """
        #print('color_field_callback')
        plot_type = self.comboBoxPlotType.currentText()
        field = self.comboBoxColorField.currentText()
        if self.styles[plot_type]['Colors']['Field'] == field:
            return

        self.styles[plot_type]['Colors']['Field'] = field

        if field != '' and field is not None:
            if field not in self.axis_dict.keys():
                self.initialize_axis_values(self.comboBoxColorByField.currentText(), field)

            self.set_color_axis_widgets()
            if plot_type not in ['correlation']:
                self.styles[plot_type]['Colors']['CLim'] = [self.axis_dict[field]['min'], self.axis_dict[field]['max']]
                self.styles[plot_type]['Colors']['CLabel'] = self.axis_dict[field]['label']
        else:
            self.lineEditCbarLabel.setText('')
        if plot:
            self.update_SV()

    def field_colormap_callback(self):
        """Sets the color map

        Sets the colormap in ``MainWindow.styles`` for the current plot type, set from ``MainWindow.comboBoxFieldColormap``.
        """
        plot_type = self.comboBoxPlotType.currentText()
        if self.styles[plot_type]['Colors']['Colormap'] == self.comboBoxFieldColormap.currentText():
            return

        self.toggle_style_widgets()
        self.styles[self.comboBoxPlotType.currentText()]['Colors']['Colormap'] = self.comboBoxFieldColormap.currentText()

        self.update_SV()

    def colormap_direction_callback(self):
        """Set colormap direction (normal/reverse)

        Reverses colormap if ``MainWindow.checkBoxReverseColormap.isChecked()`` is ``True``."""
        plot_type = self.comboBoxPlotType.currentText()
        if self.styles[plot_type]['Colors']['Reverse'] == self.checkBoxReverseColormap.isChecked():
            return

        self.styles[plot_type]['Colors']['Reverse'] = self.checkBoxReverseColormap.isChecked()

        self.update_SV()

    def get_cluster_colormap(self, cluster_dict, alpha=100):
        """Converts hex colors to a colormap

        Creates a discrete colormap given a list of hex color strings.  The colors in cluster_dict are set/changed in the ``MainWindow.tableWidgetViewGroups``.

        Parameters
        ----------
        cluster_dict : dict
            Dictionary with cluster information    
        alpha : int, optional
            Transparency to be added to color, by default 100

        Returns
        -------
        matplotlib.colormap
            A discrete (colors.ListedColormap) colormap
        """
        n = cluster_dict['n_clusters']
        cluster_color = [None]*n
        cluster_label = [None]*n
        
        # convert colors from hex to rgb and add to cluster_color list
        for i in range(n):
            color = self.get_rgb_color(cluster_dict[i]['color'])
            cluster_color[i] = tuple(float(c)/255 for c in color) + (float(alpha)/100,)
            cluster_label[i] = cluster_dict[i]['name']

        # mask
        if 99 in list(cluster_dict.keys()):
            color = self.get_rgb_color(cluster_dict[99]['color'])
            cluster_color.append(tuple(float(c)/255 for c in color) + (float(alpha)/100,))
            cluster_label.append(cluster_dict[99]['name'])
            cmap = colors.ListedColormap(cluster_color, N=n+1)
        else:
            cmap = colors.ListedColormap(cluster_color, N=n)

        return cluster_color, cluster_label, cmap

    def get_colormap(self, N=None):
        """Gets the color map

        Gets the colormap from ``MainWindow.styles`` for the current plot type and reverses or sets as discrete in needed.

        Parameters
        ----------
        N : int, optional
            Creates a discrete color map, if not supplied, the colormap is continuous, Defaults to None.

        Returns
        -------
        matplotlib.colormap.ListedColormap : colormap
        """
        if self.canvasWindow.currentIndex() == self.canvas_tab['qv']:
            plot_type = 'analyte map'
        else:
            plot_type = self.comboBoxPlotType.currentText()

        name = self.styles[plot_type]['Colors']['Colormap']
        if name in self.mpl_colormaps:
            if N is not None:
                cmap = plt.get_cmap(name, N)
            else:
                cmap = plt.get_cmap(name)
        else:
            cmap = self.create_custom_colormap(name, N)

        if self.styles[plot_type]['Colors']['Reverse']:
            cmap = cmap.reversed()

        return cmap

    def create_custom_colormap(self, name, N=None):
        """Creates custom colormaps

        Custom colormaps as found in ``resources/appdata/custom_colormaps.xlsx``.

        Parameters
        ----------
        name : str
            Name of colormap
        N : int, optional
            Number of colors to compute using colormap, by default None

        Returns
        -------
        matplotlib.LinearSegmentedColormap
            Colormap
        """
        if N is None:
            N = 256

        color_list = self.get_rgb_color(self.custom_color_dict[name])

        cmap = colors.LinearSegmentedColormap.from_list(name, color_list, N=N)

        return cmap

    def clim_callback(self):
        """Sets the color limits

        Sets the color limits in ``MainWindow.styles`` for the current plot type.
        """
        plot_type = self.comboBoxPlotType.currentText()
        if self.styles[plot_type]['Colors']['CLim'][0] == float(self.lineEditColorLB.text()) and self.styles[plot_type]['Colors']['CLim'][1] == float(self.lineEditColorUB.text()):
            return

        self.styles[plot_type]['Colors']['CLim'] = [float(self.lineEditColorLB.text()), float(self.lineEditColorUB.text())]

        self.update_SV()

    def cbar_direction_callback(self):
        """Sets the colorbar direction

        Sets the colorbar direction in ``MainWindow.styles`` for the current plot type.
        """
        plot_type = self.comboBoxPlotType.currentText()
        if self.styles[plot_type]['Colors']['Direction'] == self.comboBoxCbarDirection.currentText():
            return
        self.styles[plot_type]['Colors']['Direction'] = self.comboBoxCbarDirection.currentText()

        self.update_SV()

    def cbar_label_callback(self):
        """Sets color label

        Sets the color label in ``MainWindow.styles`` for the current plot type.
        """
        plot_type = self.comboBoxPlotType.currentText()
        if self.styles[plot_type]['Colors']['CLabel'] == self.lineEditCbarLabel.text():
            return
        self.styles[plot_type]['Colors']['CLabel'] = self.lineEditCbarLabel.text()

        if self.comboBoxCbarLabel.isEnabled():
            self.update_SV()

    # cluster styles
    # -------------------------------------
    def cluster_color_callback(self):
        """Updates color of a cluster

        Uses ``QColorDialog`` to select new cluster color and then updates plot on change of
        backround ``MainWindow.toolButtonClusterColor`` color.  Also updates ``MainWindow.tableWidgetViewGroups``
        color associated with selected cluster.  The selected cluster is determined by ``MainWindow.spinBoxClusterGroup.value()``
        """
        #print('cluster_color_callback')
        if self.tableWidgetViewGroups.rowCount() == 0:
            return

        selected_cluster = self.spinBoxClusterGroup.value()-1

        # change color
        self.button_color_select(self.toolButtonClusterColor)
        color = self.get_hex_color(self.toolButtonClusterColor.palette().button().color())
        self.cluster_dict[self.cluster_dict['active method']][selected_cluster]['color'] = color
        if self.tableWidgetViewGroups.item(selected_cluster,2).text() == color:
            return

        # update_table
        self.tableWidgetViewGroups.setItem(selected_cluster,2,QTableWidgetItem(color))

        # update plot
        if self.comboBoxColorByField.currentText() == 'Cluster':
            self.update_SV()

    def set_default_cluster_colors(self, mask=False):
        """Sets cluster group to default colormap

        Sets the colors in ``MainWindow.tableWidgetViewGroups`` to the default colormap in
        ``MainWindow.styles['Cluster']['Colors']['Colormap'].  Change the default colormap
        by changing ``MainWindow.comboBoxColormap``, when ``MainWindow.comboBoxColorByField.currentText()`` is ``Cluster``.

        Returns
        -------
            str : hexcolor
        """
        #print('set_default_cluster_colors')
        # cluster colormap
        cmap = self.get_colormap(N=self.tableWidgetViewGroups.rowCount())

        # set color for each cluster and place color in table
        colors = [cmap(i) for i in range(cmap.N)]

        hexcolor = []
        for i in range(self.tableWidgetViewGroups.rowCount()):
            hexcolor.append(self.get_hex_color(colors[i]))
            self.tableWidgetViewGroups.blockSignals(True)
            self.tableWidgetViewGroups.setItem(i,2,QTableWidgetItem(hexcolor[i]))
            self.tableWidgetViewGroups.blockSignals(False)

        if mask:
            hexcolor.append(self.styles['Cluster']['Scale']['OverlayColor'])

        self.toolButtonClusterColor.setStyleSheet("background-color: %s;" % self.tableWidgetViewGroups.item(self.spinBoxClusterGroup.value()-1,2).text())

        return hexcolor


    # -------------------------------------
    # General plot functions
    # -------------------------------------
    def update_SV(self):
        """Updates current plot (not saved to plot selector)

        Updates the current plot (as determined by ``MainWindow.comboBoxPlotType.currentText()`` and options in ``MainWindow.toolBox.selectedIndex()``.

        save : bool, optional
            save plot to plot selector, Defaults to False.
        """
        #print('update_SV, self.plot_flag: '+str(self.plot_flag)+'   sample_id: '+self.sample_id+'   field_type: '+self.comboBoxColorByField.currentText()+'   field: '+self.comboBoxColorField.currentText())
        #if self.sample_id == '' or not self.comboBoxPlotType.currentText() or not self.plot_flag:
        if self.sample_id == '' or not self.comboBoxPlotType.currentText():
            return

        match self.comboBoxPlotType.currentText():
            case 'analyte map':
                sample_id = self.sample_id
                field_type = self.comboBoxColorByField.currentText()
                field = self.comboBoxColorField.currentText()

                if not field_type or not field:
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
                self.update_spinboxes(sample_id, field, field_type)
                
                # if not self.comboBoxColorField.currentText():
                #     return

                # if analysis in ['Analyte', 'Ratio']:
                #     map_type = 'analyte'
                # elif analysis == 'Analyte (normalized)':
                #     map_type = 'analyte_norm'
                # else:
                #     return

                # current_plot_df = self.get_map_data(sample_id=sample_id, field=field, field_type=analysis)
                # if analysis == 'Ratio':
                #     analyte_1 = field.split(' / ')[0]
                #     analyte_2 = field.split(' / ')[1]
                #     self.create_plot(current_plot_df, sample_id, plot_type = map_type, analyte_1=analyte_1, analyte_2=analyte_2, plot=True)
                # else: #Not a ratio
                #     self.create_plot(current_plot_df, sample_id, plot_type = map_type, analyte_1=field, plot=True)

            case 'gradient map':
                if self.comboBoxNoiseReductionMethod.currentText() == 'none':
                    QMessageBox.warning(None,'Warning','Noise reduction must be performed before computing a gradient.')
                    return
                self.noise_reduction_method_callback()
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

            case 'variance' | 'vectors' | 'pca scatter' | 'pca heatmap' | 'PCA Score':
                self.plot_pca()

            case 'Cluster' | 'Cluster Score':
                self.plot_clusters()

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
        self.add_tree_item(plot_info)
    
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
            # canvas is not a mplcanvas  
            pass
    def display_QV(self):
        """Plots selected maps to the Quick View tab

        Adds plots of predefined analytes to the Quick View tab in a grid layout."""
        self.canvasWindow.setCurrentIndex(self.canvas_tab['qv'])
        if self.sample_id == '':
            return

        style = self.styles['analyte map']

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
            canvas = MplCanvas()

            # determine location of plot
            col = i % ncol
            row = i // ncol

            # get data for current analyte
            current_plot_df = self.get_map_data(self.sample_id, field=analyte, field_type='Analyte')
            reshaped_array = np.reshape(current_plot_df['array'].values, self.array_size, order=self.order)

            # add image to canvas
            cmap = self.get_colormap()
            cax = canvas.axes.imshow(reshaped_array, cmap=cmap,  aspect=self.aspect_ratio, interpolation='none')
            font = {'family': 'sans-serif', 'stretch': 'condensed', 'size': 8, 'weight': 'semibold'}
            canvas.axes.text(0.025*self.array_size[0],0.1*self.array_size[1], analyte, fontdict=font, color=style['Scale']['OverlayColor'], ha='left', va='top')
            canvas.axes.set_axis_off()
            canvas.fig.tight_layout()

            # add canvas to quickView grid layout
            self.widgetQuickView.layout().addWidget(canvas,row,col)

    def toggle_distance_tool(self):
        canvas = self.get_SV_widget(1)
        if not isinstance(canvas, MplCanvas):
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
            if isinstance(canvas,MplCanvas):
                canvas.restore_view()
            elif isinstance(canvas,GraphicsLayoutWidget):
                canvas.getItem(0, 0).getViewBox().autoRange()

        if function == 'pan':
            self.toolButtonZoom.setChecked(False)
            self.toolButtonAnnotate.setChecked(False)
            if isinstance(canvas,MplCanvas):
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
            if isinstance(canvas,MplCanvas):
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
            if isinstance(canvas,MplCanvas):
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
            if isinstance(canvas,MplCanvas):
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
            if isinstance(canvas,MplCanvas):
                self.pop_figure = MplDialog(self,canvas,self.plot_info['plot_name'])
                self.pop_figure.show()

            # since the canvas is moved to the dialog, the figure needs to be recreated in the main window
            self.update_SV()

        if function == 'save':
            
            if isinstance(canvas,MplCanvas):
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
            
            if isinstance(canvas, MplCanvas):
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
                        save_data = self.get_map_data(self.sample_id, field, field_type=field_type)
                    case 'gradient map':
                        field_type = self.plot_info['field_type']
                        field = self.plot_info['field']
                        save_data = self.get_map_data(self.sample_id, field, field_type=field_type)
                        filtered_image = self.noise_red_array
                    case 'Cluster':
                        save_data= self.data[self.sample_id]['computed_data'][plot_type]
                        
                    case _:
                        save_data = self.plot_info['data']
                    
                
                
                
                
                
            #open dialog to get name of file
            file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv);;All Files (*)")
            if file_name:
                with open(file_name, 'wb') as file:
                    # self.save_data holds data used for current plot 
                    save_data.to_csv(file,index = False)
                
                self.statusBar.showMessage("Plot Data saved successfully")
                

    def default_scale_length(self):
        """Sets default length of a scale bar for map-type plots

        Returns
        -------
        float
            Length of scalebar dependent on direction of scalebar.
        """        
        plot_type = self.comboBoxPlotType.currentText()
        direction = self.styles[plot_type]['Scale']['Direction']
        if (plot_type not in self.map_plot_types) or (direction == 'none'):
            return None

        if direction == 'vertical':
            length = 10**np.floor(np.log10(self.y_range))
            if length > self.x_range:
                length = 0.2 * self.y_range
        else: # direction == horizontal
            length = 10**np.floor(np.log10(self.x_range))
            if length > self.x_range:
                length = 0.2 * self.x_range

        return length

    def compute_map_aspect_ratio(self):
        """Computes aspect ratio of current sample
        
        The aspect ratio is needed for maps and computations of areas as the pixels may not be square in dimension.
        The aspect ratio is defined as dy/dx where dy is y_range/n_y and dx is x_range/n_x.
        """
        self.x = self.data[self.sample_id]['processed_data']['X']
        self.y = self.data[self.sample_id]['processed_data']['Y']

        self.x_range = self.x.max() -  self.x.min()
        self.y_range = self.y.max() -  self.y.min()

        self.dx = self.x_range/self.x.nunique()
        self.dy = self.y_range/self.y.nunique()

        units = self.preferences['Units']['Distance']
        self.lineEditDX.value = self.dx
        self.lineEditDY.value = self.dy

        self.aspect_ratio = self.dy / self.dx

        self.array_size = (self.y.nunique(), self.x.nunique())
        
        self.lineEditResolutionNx.value = self.array_size[1]
        self.lineEditResolutionNy.value = self.array_size[0]

    def add_scalebar(self, ax):
        """Add a scalebar to a map

        Parameters
        ----------
        ax : 
            Axes to place scalebar on.
        """        
        style = self.styles[self.comboBoxPlotType.currentText()]

        # add scalebar
        direction = style['Scale']['Direction']
        length = style['Scale']['Length']
        if (length is not None) and (direction != 'none'):
            if direction == 'horizontal':
                dd = self.dx
            else:
                dd = self.dy
            sb = scalebar( width=length,
                    pixel_width=dd,
                    units=self.preferences['Units']['Distance'],
                    location=style['Scale']['Location'],
                    orientation=direction,
                    color=style['Scale']['OverlayColor'],
                    ax=ax )

            sb.create()
        else:
            return

    def add_colorbar(self, canvas, cax, style, cbartype='continuous', grouplabels=None, groupcolors=None):
        """Adds a colorbar to a MPL figure

        Parameters
        ----------
        canvas : MplCanvas
            canvas object
        cax : axes
            color axes object
        style : dict
            plot style parameters
        cbartype : str
            Type of colorbar, ``dicrete`` or ``continuous``, Defaults to continuous
        grouplabels : list of str, optional
            category/group labels for tick marks
        """
        # Add a colorbar
        cbar = None
        if style['Colors']['Direction'] == 'none':
            return

        if grouplabels is None or groupcolors is None:
            return

        # discrete colormap - plot as a legend
        if cbartype == 'discrete':
            # create patches for legend items
            p = [None]*len(grouplabels)
            for i, label in enumerate(grouplabels):
                p[i] = Patch(facecolor=groupcolors[i], edgecolor='#111111', linewidth=0.5, label=label)

            if style['Colors']['Direction'] == 'vertical':
                canvas.axes.legend(
                        handles=p,
                        handlelength=1,
                        loc='upper left',
                        bbox_to_anchor=(1.025,1),
                        fontsize=style['Text']['FontSize'],
                        frameon=False,
                        ncol=1
                    )
            elif style['Colors']['Direction'] == 'horizontal':
                canvas.axes.legend(
                        handles=p,
                        handlelength=1,
                        loc='upper center',
                        bbox_to_anchor=(0.5,-0.1),
                        fontsize=style['Text']['FontSize'],
                        frameon=False,
                        ncol=3
                    )
        # continuous colormap - plot with colorbar
        else:
            if style['Colors']['Direction'] == 'vertical':
                if self.comboBoxPlotType.currentText() == 'correlation':
                    loc = 'left'
                else:
                    loc = 'right'
                cbar = canvas.fig.colorbar( cax,
                        ax=canvas.axes,
                        orientation=style['Colors']['Direction'],
                        location=loc,
                        shrink=0.62,
                        fraction=0.1,
                        alpha=1
                    )
            elif style['Colors']['Direction'] == 'horizontal':
                cbar = canvas.fig.colorbar( cax,
                        ax=canvas.axes,
                        orientation=style['Colors']['Direction'],
                        location='bottom',
                        shrink=0.62,
                        fraction=0.1,
                        alpha=1
                    )
            else:
                # should never reach this point
                assert style['Colors']['Direction'] == 'none', "Colorbar direction is set to none, but is trying to generate anyway."
                return

            cbar.set_label(style['Colors']['CLabel'], size=style['Text']['FontSize'])
            cbar.ax.tick_params(labelsize=style['Text']['FontSize'])
            cbar.set_alpha(1)

        # adjust tick marks if labels are given
        if cbartype == 'continuous' or grouplabels is None:
            ticks = None
        # elif cbartype == 'discrete':
        #     ticks = np.arange(0, len(grouplabels))
        #     cbar.set_ticks(ticks=ticks, labels=grouplabels, minor=False)
        #else:
        #    print('(add_colorbar) Unknown type: '+cbartype)

    def color_norm(self, style, N=None):
        """Normalize colors for colormap

        Parameters
        ----------
        style : dict
            Styles associated with current plot type, required for all plot types except those with discrete
            colormaps i.e., ``Cluster``.
        N : int, optional
            The number of colors for discrete color maps, Defaults to None
        
        Returns
        -------
            matplotlib.colors.Norm
                Color norm for plotting.
        """
        norm = None
        match style['Colors']['CScale']:
            case 'linear':
                norm = colors.Normalize(vmin=style['Colors']['CLim'][0], vmax=style['Colors']['CLim'][1])
            case 'log':
                norm = colors.LogNorm(vmin=style['Colors']['CLim'][0], vmax=style['Colors']['CLim'][1])
            case 'discrete':
                if N is None:
                    QMessageBox(self,"Warning","N must not be None when color scale is discrete.")
                    return
                boundaries = np.arange(-0.5, N, 1)
                norm = colors.BoundaryNorm(boundaries, N, clip=True)

        #scalarMappable = plt.cm.ScalarMappable(cmap=self.get_colormap(), norm=norm)

        return norm
    

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
        mask = self.data[self.sample_id]['mask']

        array = np.reshape(map_df['array'].values, self.array_size, order=self.order)

        # Step 1: Normalize your data array for colormap application
        norm = colors.Normalize(vmin=np.nanmin(array), vmax=np.nanmax(array))
        cmap = self.get_colormap()

        # Step 2: Apply the colormap to get RGB values, then normalize to [0, 255] for QImage
        rgb_array = cmap(norm(array))[:, :, :3]  # Drop the alpha channel returned by cmap
        rgb_array = (rgb_array * 255).astype(np.uint8)

        # Step 3: Create an RGBA array where the alpha channel is based on self.data[self.sample_id]['mask']
        rgba_array = np.zeros((*rgb_array.shape[:2], 4), dtype=np.uint8)
        rgba_array[:, :, :3] = rgb_array  # Set RGB channels
        mask_r = np.reshape(mask, self.array_size, order=self.order)

        rgba_array[:, :, 3] = np.where(mask_r, 255, 100)  # Set alpha channel based on self.data[self.sample_id]['mask']

        return array, rgba_array

    def plot_map_mpl(self, sample_id, field_type, field):
        """Create a matplotlib canvas for plotting a map

        Create a map using ``MplCanvas``.

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
        canvas = MplCanvas(parent=self)

        style = self.styles['analyte map']

        # set color limits
        if field not in self.axis_dict:
            self.initialize_axis_values(field_type,field)
            self.set_style_widgets(plot_type='analyte map',style=style)

        # get data for current map
        map_df = self.get_map_data(self.sample_id, field, field_type=field_type)

        # store map_df to save_data if data needs to be exported
        self.save_data = map_df.copy()

        # equalized color bins to CDF function
        if self.toolButtonScaleEqualize.isChecked():
            sorted_data = map_df['array'].sort_values()
            cum_sum = sorted_data.cumsum()
            cdf = cum_sum / cum_sum.iloc[-1]
            map_df.loc[sorted_data.index, 'array'] = cdf.values

        # plot map
        reshaped_array = np.reshape(map_df['array'].values, self.array_size, order=self.order)
            
        norm = self.color_norm(style)

        cax = canvas.axes.imshow(reshaped_array, cmap=self.get_colormap(),  aspect=self.aspect_ratio, interpolation='none', norm=norm)


        self.add_colorbar(canvas, cax, style)
        cax.set_clim(style['Colors']['CLim'][0], style['Colors']['CLim'][1])

        # use mask to create an alpha layer
        mask = self.data[self.sample_id]['mask'].astype(float)
        reshaped_mask = np.reshape(mask, self.array_size, order=self.order)

        alphas = colors.Normalize(0, 1, clip=False)(reshaped_mask)
        alphas = np.clip(alphas, .4, 1)

        alpha_mask = np.where(reshaped_mask == 0, 0.5, 0)  
        canvas.axes.imshow(np.ones_like(alpha_mask), aspect=self.aspect_ratio, interpolation='none', cmap='Greys', alpha=alpha_mask)
        canvas.array = reshaped_array

        # font = {'family': 'sans-serif', 'stretch': 'condensed', 'size': 8, 'weight': 'semibold'}
        # canvas.axes.text(0.025*self.array_size[0],0.1*self.array_size[1], field, fontdict=font, color=style['Scale']['OverlayColor'], ha='left', va='top')
        #canvas.axes.set_axis_off()
        canvas.axes.tick_params(direction=None,
            labelbottom=False, labeltop=False, labelright=False, labelleft=False,
            bottom=False, top=False, left=False, right=False)

        canvas.set_initial_extent()
        
        # add scalebar
        self.add_scalebar(canvas.axes)

        canvas.fig.tight_layout()

        # add small histogram
        if (self.toolBox.currentIndex() == self.left_tab['sample']) and (self.canvasWindow.currentIndex() == self.canvas_tab['sv']):
            self.plot_small_histogram(map_df,field)



        self.plot_info = {
            'tree': field_type,
            'sample_id': sample_id,
            'plot_name': field,
            'plot_type': 'analyte map',
            'field_type': field_type,
            'field': field,
            'figure': canvas,
            'style': style,
            'cluster_groups': None,
            'view': [True,False],
            'position': None
            }
        
        self.add_plotwidget_to_canvas( self.plot_info)
        # self.widgetSingleView.layout().addWidget(canvas)

        self.add_tree_item(self.plot_info)

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

        style = self.styles['analyte map']

        # get data for current map
        map_df = self.get_map_data(sample_id, field, field_type=field_type)

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
        img_item.setRect(self.x.min(),self.y.min(),self.x_range,self.y_range)

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
        #plotWindow.setLimits(maxXRange=self.x_range, maxYRange=self.y_range)

        #supress right click menu
        plotWindow.setMenuEnabled(False)

        # colorbar
        cmap = colormap.get(style['Colors']['Colormap'], source = 'matplotlib')
        #clb,cub,cscale,clabel = self.get_axis_values(field_type,field)
        # cbar = ColorBarItem(values=(clb,cub), width=25, colorMap=cmap, label=clabel, interactive=False, limits=(clb,cub), orientation=style['Colors']['Direction'], pen='black')
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
            # labelMVInfoValueLabel.setMaximumSize(QtCore.QSize(20, 16777215))
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
            'style': style,
            'cluster_groups': None,
            'view': tmp,
            'position': None
            }

        #self.plot_widget_dict[self.plot_info['tree']][self.plot_info['sample_id']][self.plot_info['plot_name']] = {'info':self.plot_info, 'view':view, 'position':None}
        self.add_plotwidget_to_canvas(self.plot_info)

        #self.update_tree(plot_info=self.plot_info)
        self.add_tree_item(self.plot_info)

        # add small histogram
        if (self.toolBox.currentIndex() == self.left_tab['sample']) and (view == self.canvas_tab['sv']):
            self.plot_small_histogram(map_df,field)


    # -------------------------------------
    # Correlation functions and plotting
    # -------------------------------------
    def correlation_method_callback(self):
        """Updates colorbar label for correlation plots"""
        method = self.comboBoxCorrelationMethod.currentText()
        if self.styles['correlation']['Colors']['CLabel'] == method:
            return

        if self.checkBoxCorrelationSquared.isChecked():
            power = '^2'
        else:
            power = ''

        # update colorbar label for change in method
        match method:
            case 'Pearson':
                self.styles['correlation']['Colors']['CLabel'] = method + "'s $r" + power + "$"
            case 'Spearman':
                self.styles['correlation']['Colors']['CLabel'] = method + "'s $\\rho" + power + "$"
            case 'Kendall':
                self.styles['correlation']['Colors']['CLabel'] = method + "'s $\\tau" + power + "$"

        if self.comboBoxPlotType.currentText() != 'correlation':
            self.comboBoxPlotType.setCurrentText('correlation')
            self.set_style_widgets('correlation')

        self.update_SV()

    def correlation_squared_callback(self):
        style = self.styles['correlation']
        # update color limits and colorbar
        if self.checkBoxCorrelationSquared.isChecked():
            self.styles['correlation']['Colors']['CLim'] = [0,1]
            self.styles['correlation']['Colors']['Colormap'] = 'cmc.oslo'
        else:
            self.styles['correlation']['Colors']['CLim'] = [-1,1]
            self.styles['correlation']['Colors']['Colormap'] = 'RdBu'

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

        canvas = MplCanvas(parent=self)
        canvas.axes.clear()

        # get the data for computing correlations
        df_filtered, analytes = self.get_processed_data()

        # Calculate the correlation matrix
        method = self.comboBoxCorrelationMethod.currentText().lower()
        if self.comboBoxColorByField.currentText().lower() == 'none':
            correlation_matrix = df_filtered.corr(method=method)
        else:
            algorithm = self.comboBoxColorField.currentText()
            cluster_group = self.data[self.sample_id]['computed_data']['Cluster'].loc[:,algorithm]
            selected_clusters = self.cluster_dict[algorithm]['selected_clusters']

            ind = np.isin(cluster_group, selected_clusters)

            correlation_matrix = df_filtered[ind].corr(method=method)
        
        
        
        columns = correlation_matrix.columns

        style = self.styles['correlation']
        font = {'size':style['Text']['FontSize']}

        # mask lower triangular matrix to show only upper triangle
        mask = np.zeros_like(correlation_matrix, dtype=bool)
        mask[np.tril_indices_from(mask)] = True
        correlation_matrix = np.ma.masked_where(mask, correlation_matrix)

        norm = self.color_norm(style)

        # plot correlation or correlation^2
        square_flag = self.checkBoxCorrelationSquared.isChecked()
        if square_flag:
            cax = canvas.axes.imshow(correlation_matrix**2, cmap=self.get_colormap(), norm=norm)
            canvas.array = correlation_matrix**2
        else:
            cax = canvas.axes.imshow(correlation_matrix, cmap=self.get_colormap(), norm=norm)
            canvas.array = correlation_matrix
            
        # store correlation_matrix to save_data if data needs to be exported
        self.save_data = canvas.array

        canvas.axes.spines['top'].set_visible(False)
        canvas.axes.spines['bottom'].set_visible(False)
        canvas.axes.spines['left'].set_visible(False)
        canvas.axes.spines['right'].set_visible(False)

        # Add colorbar to the plot
        self.add_colorbar(canvas, cax, style)

        # set color limits
        cax.set_clim(style['Colors']['CLim'][0], style['Colors']['CLim'][1])

        # Set tick labels
        ticks = np.arange(len(columns))
        canvas.axes.tick_params(length=0, labelsize=8,
                        labelbottom=False, labeltop=True, labelleft=False, labelright=True,
                        bottom=False, top=True, left=False, right=True)

        canvas.axes.set_yticks(ticks, minor=False)
        canvas.axes.set_xticks(ticks, minor=False)

        labels = self.toggle_mass(columns)

        canvas.axes.set_xticklabels(labels, rotation=90, ha='center', va='bottom', fontproperties=font)
        canvas.axes.set_yticklabels(labels, ha='left', va='center', fontproperties=font)

        canvas.axes.set_title('')

        self.update_figure_font(canvas, style['Text']['Font'])

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
            'style': style,
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

        self.histogram_update_bin_width()

    def histogram_field_callback(self):
        """Executes when the histogram field is changed"""
        self.histogram_update_bin_width()

    def histogram_update_bin_width(self):
        """Updates the bin width

        Generally called when the number of bins is changed by the user.  Updates the plot.
        """
        if not self.update_bins:
            return
        #print('histogram_update_bin_width')
        self.update_bins = False

        # get currently selected data
        current_plot_df = self.get_map_data(self.sample_id, self.comboBoxHistField.currentText(), field_type=self.comboBoxHistFieldType.currentText())

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
        map_df = self.get_map_data(self.sample_id, field=self.comboBoxHistField.currentText(), analysis_type=self.comboBoxHistFieldType.currentText())

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

    def plot_small_histogram(self, current_plot_df, field):
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
        canvas = SimpleMplCanvas()
        #canvas.axes.clear()

        style = self.styles['histogram']

        # Histogram
        #remove by mask and drop rows with na
        mask = self.data[self.sample_id]['mask']
        mask = mask & current_plot_df['array'].notna()

        array = current_plot_df['array'][mask].values
        len(array)

        logflag = False
        if self.styles['analyte map']['Colors']['CScale'] == 'log':
            print('log scale')
            logflag = True
            array = np.log10(array)

        bin_width = (np.nanmax(array) - np.nanmin(array)) / self.default_bins
        edges = np.arange(np.nanmin(array), np.nanmax(array) + bin_width, bin_width)

        if sum(mask) != len(mask):
            canvas.axes.hist(current_plot_df['array'], bins=edges, density=True, color='#b3b3b3', edgecolor=None, linewidth=style['Lines']['LineWidth'], log=logflag, alpha=0.6, label='unmasked')
        _, _, patches = canvas.axes.hist(array, bins=edges, density=True, color=style['Colors']['Color'], edgecolor=None, linewidth=style['Lines']['LineWidth'], log=logflag, alpha=0.6)
        # color histogram bins by analyte colormap?
        if self.checkBoxShowHistCmap.isChecked():
            cmap = self.get_colormap()
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
        canvas.axes.set_xlabel(field, fontdict={'size':8})

        # Size the histogram in the widget
        canvas.axes.margins(x=0)
        pos = canvas.axes.get_position()
        canvas.axes.set_position([pos.x0/2, 3*pos.y0, pos.width+pos.x0, pos.height-1.5*pos.y0])

        self.clear_layout(self.widgetHistView.layout())
        self.widgetHistView.layout().addWidget(canvas)

        #self.widgetHistView.hide()
        #self.widgetHistView.show()

    def plot_histogram(self):
        """Plots a histogramn the canvas window"""
        
        plot_data = None
        #print('plot histogram')
        # create Mpl canvas
        canvas = MplCanvas(parent=self)

        style = self.styles['histogram']

        nbins = int(self.spinBoxNBins.value())

        analysis = self.comboBoxHistFieldType.currentText()
        field = self.comboBoxHistField.currentText()
        #if analysis == 'Ratio':
        #    analyte_1 = field.split(' / ')[0]
        #    analyte_2 = field.split(' / ')[1]

        x, _, _, _, = self.get_scatter_values('histogram')

        # determine edges
        xmin,xmax,xscale,xlbl = self.get_axis_values(x['type'],x['field'])
        style['Axes']['XLim'] = [xmin, xmax]
        style['Axes']['XScale'] = xscale
        #if xscale == 'log':
        #    x['array'] = np.log10(x['array'])
        #    xmin = np.log10(xmin)
        #    xmax = np.log10(xmax)

        #bin_width = (xmax - xmin) / nbins
        #print(nbins)
        #print(bin_width)

        if xscale == 'linear':
            edges = np.linspace(xmin, xmax, nbins)
        else:
            edges = 10**np.linspace(np.log10(xmin), np.log10(xmax), nbins)
            
        print(edges)

        # histogram style
        lw = style['Lines']['LineWidth']
        if lw > 0:
            htype = 'step'
        else:
            htype = 'bar'

        # CDF or PDF
        match self.comboBoxHistType.currentText():
            case 'PDF':
                cumflag = False
            case 'CDF':
                cumflag = True

        # Check if the algorithm is in the current group and if results are available
        if self.comboBoxColorByField.currentText() == 'Cluster' and self.comboBoxColorField.currentText() != '':
            method = self.cluster_dict['active method']

            # Get the cluster labels for the data
            cluster_color, cluster_label, _ = self.get_cluster_colormap(self.cluster_dict[method],alpha=style['Markers']['Alpha'])
            cluster_group = self.data[self.sample_id]['computed_data']['Cluster'].loc[:,method]
            clusters = self.cluster_dict[method]['selected_clusters']

            # Plot histogram for all clusters
            for i in clusters:
                cluster_data = x['array'][cluster_group == i]

                bar_color = cluster_color[int(i)]
                if htype == 'step':
                    ecolor = bar_color
                else:
                    ecolor = None

                plot_data = canvas.axes.hist( cluster_data,
                        cumulative=cumflag,
                        histtype=htype,
                        bins=edges,
                        color=bar_color, edgecolor=ecolor,
                        linewidth=lw,
                        label=cluster_label[int(i)],
                        alpha=style['Markers']['Alpha']/100,
                        density=True
                    )

            # Add a legend
            self.add_colorbar(canvas, None, style, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
            #canvas.axes.legend()
        else:
            clusters = None
            # Regular histogram
            bar_color = style['Colors']['Color']
            if htype == 'step':
                ecolor = style['Lines']['Color']
            else:
                ecolor = None

            plot_data = canvas.axes.hist( x['array'],
                    cumulative=cumflag,
                    histtype=htype,
                    bins=edges,
                    color=bar_color, edgecolor=ecolor,
                    linewidth=lw,
                    alpha=style['Markers']['Alpha']/100,
                    density=True
                )

        # axes
        # set y-limits as p-axis min and max in self.axis_dict
        pflag = False
        if 'pstatus' not in self.axis_dict[x['field']]:
            pflag = True
        elif self.axis_dict[x['field']]['pstatus'] == 'auto':
            pflag = True

        if pflag:
            ymin, ymax = canvas.axes.get_ylim()
            d = {'pstatus':'auto', 'pmin':fmt.oround(ymin,order=2,toward=0), 'pmax':fmt.oround(ymax,order=2,toward=1)}
            self.axis_dict[x['field']].update(d)
            self.set_axis_widgets('y', x['field'])

        # grab probablility axes limits
        _, _, _, _, ymin, ymax = self.get_axis_values(x['type'],x['field'],ax='p')

        # label font
        if 'font' == '':
            font = {'size':style['Text']['FontSize']}
        else:
            font = {'font':style['Text']['Font'], 'size':style['Text']['FontSize']}


        # x-axis
        canvas.axes.set_xlabel(xlbl, fontdict=font)
        if xscale == 'log':
        #    self.logax(canvas.axes, [xmin,xmax], axis='x', label=xlbl)
            canvas.axes.set_xscale(xscale,base=10)
        # if style['Axes']['Scale'] == 'linear':
        # else:
        #     canvas.axes.set_xlim(xmin,xmax)
        canvas.axes.set_xlim(xmin,xmax)

        # y-axis
        canvas.axes.set_ylabel(self.comboBoxHistType.currentText(), fontdict=font)
        canvas.axes.set_ylim(ymin,ymax)

        canvas.axes.tick_params(labelsize=style['Text']['FontSize'],direction=style['Axes']['TickDir'])
        canvas.axes.set_box_aspect(style['Axes']['AspectRatio'])

        self.update_figure_font(canvas, style['Text']['Font'])

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
            'style': style,
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
    def plot_scatter(self, canvas=None):
        """Creates a plots from self.toolBox Scatter page.

        Creates both scatter and heatmaps (spatial histograms) for bi- and ternary plots.

        :param values: Defaults to None
        :type values:
        :param fig: Defaults to None
        :type fig:
        :param save: Flag for saving widget to self.toolBoxTreeView Plot Selector page, Defaults to False
        :type save: bool, optional
        """
        #print('plot_scatter')
        plot_type = self.comboBoxPlotType.currentText()
        style = self.styles[plot_type]

        if self.comboBoxFieldX.currentText() == "" or self.comboBoxFieldY.currentText() == "":
            return

        if canvas is None:
            plot_flag = True
            canvas = MplCanvas(parent=self)
        else:
            plot_flag = False

        # get data for plotting
        x, y, z, c = self.get_scatter_values(plot_type)

        match plot_type.split()[-1]:
            # scatter
            case 'scatter':
                if style['Colors']['ColorByField'] == None:
                    c = {'field': None, 'type': None, 'units': None, 'array': None}

                if len(z['array']) == 0:
                    # biplot
                    self.biplot(canvas,x,y,c,style)
                else:
                    # ternary
                    self.ternary_scatter(canvas,x,y,z,c,style)

            # heatmap
            case 'heatmap':
                # biplot
                if len(z['array']) == 0:
                    self.hist2dbiplot(canvas,x,y,style)
                # ternary
                else:
                    self.hist2dternplot(canvas,x,y,z,style,c=c)

        canvas.axes.margins(x=0)

        if plot_flag:
            self.update_figure_font(canvas, style['Text']['Font'])
            self.clear_layout(self.widgetSingleView.layout())
            self.widgetSingleView.layout().addWidget(canvas)

    def biplot(self, canvas, x, y, c, style):
        """Creates scatter bi-plots

        A general function for creating scatter plots of 2-dimensions.

        :param fig: figure object
        :type fig: matplotlib.figure
        :param x: data associated with field ``MainWindow.comboBoxFieldX.currentText()`` as x coordinate
        :type x: dict
        :param y: data associated with field ``MainWindow.comboBoxFieldX.currentText()`` as y coordinate
        :type y: dict
        :param c: data associated with field ``MainWindow.comboBoxColorField.currentText()`` as marker colors
        :type c: dict
        :param style: style parameters
        :type style: dict
        """
        if len(c['array']) == 0:
            # single color
            canvas.axes.scatter(x['array'], y['array'], c=style['Colors']['Color'],
                s=style['Markers']['Size'],
                marker=self.markerdict[style['Markers']['Symbol']],
                edgecolors='none',
                alpha=style['Markers']['Alpha']/100)
            cb = None
            
            plot_data = pd.DataFrame(np.vstack((x['array'], y['array'])).T, columns = ['x','y'])
            
        elif style['Colors']['ColorByField'] == 'Cluster':
            # color by cluster
            method = self.comboBoxColorField.currentText()
            if method not in list(self.cluster_dict.keys()):
                return
            else:
                if 0 not in list(self.cluster_dict[method].keys()):
                    return

            cluster_color, cluster_label, cmap = self.get_cluster_colormap(self.cluster_dict[method],alpha=style['Markers']['Alpha'])
            cluster_group = self.data[self.sample_id]['computed_data']['Cluster'].loc[:,method]
            selected_clusters = self.cluster_dict[method]['selected_clusters']

            ind = np.isin(cluster_group, selected_clusters)

            norm = self.color_norm(style,self.cluster_dict[method]['n_clusters'])

            cb = canvas.axes.scatter(x['array'][ind], y['array'][ind], c=c['array'][ind],
                s=style['Markers']['Size'],
                marker=self.markerdict[style['Markers']['Symbol']],
                edgecolors='none',
                cmap=cmap,
                alpha=style['Markers']['Alpha']/100,
                norm=norm)

            self.add_colorbar(canvas, cb, style, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
            plot_data = pd.DataFrame(np.vstack((x['array'][ind],y['array'][ind], c['array'][ind], cluster_group[ind])).T, columns = ['x','y','c','cluster_group'])
        else:
            # color by field
            norm = self.color_norm(style)
            cb = canvas.axes.scatter(x['array'], y['array'], c=c['array'],
                s=style['Markers']['Size'],
                marker=self.markerdict[style['Markers']['Symbol']],
                edgecolors='none',
                cmap=self.get_colormap(),
                alpha=style['Markers']['Alpha']/100,
                norm=norm)

            self.add_colorbar(canvas, cb, style)
            plot_data = pd.DataFrame(np.vstack((x['array'], y['array'], c['array'])).T, columns = ['x','y','c'])
            

        # axes
        xmin, xmax, xscale, xlbl = self.get_axis_values(x['type'],x['field'])
        ymin, ymax, yscale, ylbl = self.get_axis_values(y['type'],y['field'])

        # labels
        font = {'size':style['Text']['FontSize']}
        canvas.axes.set_xlabel(xlbl, fontdict=font)
        canvas.axes.set_ylabel(ylbl, fontdict=font)

        # axes limits
        canvas.axes.set_xlim(xmin,xmax)
        canvas.axes.set_ylim(ymin,ymax)

        # tick marks
        canvas.axes.tick_params(direction=style['Axes']['TickDir'],
            labelsize=style['Text']['FontSize'],
            labelbottom=True, labeltop=False, labelleft=True, labelright=False,
            bottom=True, top=True, left=True, right=True)

        # aspect ratio
        canvas.axes.set_box_aspect(style['Axes']['AspectRatio'])
        canvas.fig.tight_layout()

        if xscale == 'log':
            canvas.axes.set_xscale(xscale,base=10)
        if yscale == 'log':
            canvas.axes.set_yscale(yscale,base=10)

        plot_name = f"{x['field']}_{y['field']}_{'scatter'}"

        self.plot_info = {
            'tree': 'Geochemistry',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': 'scatter',
            'field_type': [x['type'], y['type'], '', c['type']],
            'field': [x['field'], y['field'], '', c['field']],
            'figure': canvas,
            'style': style,
            'cluster_groups': [],
            'view': [True,False],
            'position': [],
            'data':  plot_data
        }

    def ternary_scatter(self, canvas, x, y, z, c, style):
        """Creates ternary scatter plots

        A general function for creating ternary scatter plots.

        :param fig: figure object
        :type fig: matplotlib.figure
        :param x: coordinate associated with top vertex
        :type x: dict
        :param y: coordinate associated with left vertex
        :type y: dict
        :param z: coordinate associated with right vertex
        :type z: dict
        :param c: color dimension
        :type c: dict
        :param style: style parameters
        :type style: dict
        :param save: flag indicating whether the plot should be saved to the plot tree
        :type save: bool
        """
        labels = [x['field'], y['field'], z['field']]
        tp = ternary(canvas.axes, labels, 'scatter')

        if len(c['array']) == 0:
            tp.ternscatter( x['array'], y['array'], z['array'],
                    marker=self.markerdict[style['Markers']['Symbol']],
                    size=style['Markers']['Size'],
                    color=style['Colors']['Color'],
                    alpha=style['Markers']['Alpha']/100,
                )
            cb = None
            plot_data = pd.DataFrame(np.vstack((x['array'],y['array'], z['array'])).T, columns = ['x','y','z'])
            
        elif style['Colors']['ColorByField'] == 'Cluster':
            # color by cluster
            method = self.comboBoxColorField.currentText()
            if method not in list(self.cluster_dict.keys()):
                return
            else:
                if 0 not in list(self.cluster_dict[method].keys()):
                    return

            cluster_color, cluster_label, cmap = self.get_cluster_colormap(self.cluster_dict[method],alpha=style['Markers']['Alpha'])
            cluster_group = self.data[self.sample_id]['computed_data']['Cluster'].loc[:,method]
            selected_clusters = self.cluster_dict[method]['selected_clusters']

            ind = np.isin(cluster_group, selected_clusters)

            norm = self.color_norm(style,self.cluster_dict[method]['n_clusters'])

            _, cb = tp.ternscatter( x['array'][ind], y['array'][ind], z['array'][ind],
                    categories=c['array'][ind],
                    marker=self.markerdict[style['Markers']['Symbol']],
                    size=style['Markers']['Size'],
                    cmap=cmap,
                    norm=norm,
                    labels=True,
                    alpha=style['Markers']['Alpha']/100,
                    orientation='None'
                )

            self.add_colorbar(canvas, cb, style, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
            plot_data = pd.DataFrame(np.vstack((x['array'][ind],y['array'][ind], z['array'][ind], cluster_group[ind])).T, columns = ['x','y','z','cluster_group'])
        else:
            # color field
            norm = self.color_norm(style)
            _, cb = tp.ternscatter(x['array'], y['array'], z['array'],
                    categories=c['array'],
                    marker=self.markerdict[style['Markers']['Symbol']],
                    size=style['Markers']['Size'],
                    cmap=style['Colors']['Colormap'],
                    norm=norm,
                    alpha=style['Markers']['Alpha']/100,
                    orientation=style['Colors']['Direction']
                )

            if cb:
                cb.set_label(c['label'])
                plot_data = pd.DataFrame(np.vstack((x['array'], y['array'], c['array'])).T, columns = ['x','y','c'])
        plot_name = f"{x['field']}_{y['field']}_{z['field']}_{'ternscatter'}"
        self.plot_info = {
            'tree': 'Geochemistry',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': 'scatter',
            'field_type': [x['type'], y['type'], z['type'], c['type']],
            'field': [x['field'], y['field'], z['field'], c['field']],
            'figure': canvas,
            'style': style,
            'cluster_groups': [],
            'view': [True,False],
            'position': [],
            'data': plot_data
        }

    def hist2dbiplot(self, canvas, x, y, style):
        """Creates 2D histogram figure

        A general function for creating 2D histograms (heatmaps).

        :param fig: figure object
        :type fig: matplotlib.figure
        :param x: x-dimension
        :type x: dict
        :param y: y-dimension
        :type y: dict
        :param style: style parameters
        :type style: dict
        :param save: saves figure widget to plot tree
        :type save: bool
        """
        # color by field
        norm = self.color_norm(style)
        h = canvas.axes.hist2d(x['array'], y['array'], bins=style['Colors']['Resolution'], norm=norm, cmap=self.get_colormap())
        self.add_colorbar(canvas, h[3], style)

        # axes
        xmin, xmax, xscale, xlbl = self.get_axis_values(x['type'],x['field'])
        ymin, ymax, yscale, ylbl = self.get_axis_values(y['type'],y['field'])

        # labels
        font = {'size':style['Text']['FontSize']}
        canvas.axes.set_xlabel(xlbl, fontdict=font)
        canvas.axes.set_ylabel(ylbl, fontdict=font)

        # axes limits
        canvas.axes.set_xlim(xmin,xmax)
        canvas.axes.set_ylim(ymin,ymax)

        # tick marks
        canvas.axes.tick_params(direction=style['Axes']['TickDir'],
                        labelsize=style['Text']['FontSize'],
                        labelbottom=True, labeltop=False, labelleft=True, labelright=False,
                        bottom=True, top=True, left=True, right=True)

        # aspect ratio
        canvas.axes.set_box_aspect(style['Axes']['AspectRatio'])

        if xscale == 'log':
            canvas.axes.set_xscale(xscale,base=10)
        if yscale == 'log':
            canvas.axes.set_yscale(yscale,base=10)

        plot_name = f"{x['field']}_{y['field']}_{'heatmap'}"
        self.plot_info = {
            'tree': 'Geochemistry',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': 'heatmap',
            'field_type': [x['type'], y['type'], '', ''],
            'field': [x['field'], y['field'], '', ''],
            'figure': canvas,
            'style': style,
            'cluster_groups': [],
            'view': [True,False],
            'position': [],
            'data': pd.DataFrame(np.vstack((x['array'],y['array'])).T, columns = ['x','y'])
        }

    def hist2dternplot(self, canvas, x, y, z, style, c=None):
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

        if len(c['array']) == 0:
            tp = ternary(canvas.axes, labels, 'heatmap')

            norm = self.color_norm(style)
            hexbin_df, cb = tp.ternhex(a=x['array'], b=y['array'], c=z['array'],
                bins=style['Colors']['Resolution'],
                plotfield='n',
                cmap=style['Colors']['Colormap'],
                orientation=style['Colors']['Direction'],
                norm=norm)

            if cb is not None:
                cb.set_label('log(N)')
        else:
            pass
            # axs = fig.subplot_mosaic([['left','upper right'],['left','lower right']], layout='constrained', width_ratios=[1.5, 1])

            # for idx, ax in enumerate(axs):
            #     tps[idx] = ternary(ax, labels, 'heatmap')

            # hexbin_df = ternary.ternhex(a=x['array'], b=y['array'], c=z['array'], val=c['array'], bins=style['Colors']['Resolution'])

            # cb.set_label(c['label'])

            # #tp.ternhex(hexbin_df=hexbin_df, plotfield='n', cmap=style['Colors']['Colormap'], orientation='vertical')

        plot_name = f"{x['field']}_{y['field']}_{z['field']}_{'heatmap'}"
        self.plot_info = {
            'tree': 'Geochemistry',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': 'heatmap',
            'field_type': [x['type'], y['type'], z['type'], ''],
            'field': [x['field'], y['field'], z['field'], ''],
            'figure': canvas,
            'style': style,
            'cluster_groups': [],
            'view': [True,False],
            'position': [],
            'data' : pd.DataFrame(np.vstack((x['array'],y['array'], z['array'])).T, columns = ['x','y','z'])
        }

    def plot_ternarymap(self, canvas):
        """Creates map colored by ternary coordinate positions"""
        if self.comboBoxPlotType.currentText() != 'ternary map':
            self.comboBoxPlotType.setCurrentText('ternary map')
            self.set_style_widgets('ternary map')

        style = self.styles['ternary map']

        canvas = MplCanvas(sub=121,parent=self)

        afield = self.comboBoxFieldX.currentText()
        bfield = self.comboBoxFieldY.currentText()
        cfield = self.comboBoxFieldZ.currentText()

        a = self.data[self.sample_id]['processed_data'].loc[:,afield].values
        b = self.data[self.sample_id]['processed_data'].loc[:,bfield].values
        c = self.data[self.sample_id]['processed_data'].loc[:,cfield].values

        ca = self.get_rgb_color(self.get_hex_color(self.toolButtonTCmapXColor.palette().button().color()))
        cb = self.get_rgb_color(self.get_hex_color(self.toolButtonTCmapYColor.palette().button().color()))
        cc = self.get_rgb_color(self.get_hex_color(self.toolButtonTCmapZColor.palette().button().color()))
        cm = self.get_rgb_color(self.get_hex_color(self.toolButtonTCmapMColor.palette().button().color()))

        t = ternary(canvas.axes)

        cval = t.terncolor(a, b, c, ca, cb, cc, cp=cm)

        M, N = self.array_size

        # Reshape the array into MxNx3
        map_data = np.zeros((M, N, 3), dtype=np.uint8)
        map_data[:len(cval), :, :] = cval.reshape(M, N, 3, order=self.order)

        canvas.axes.imshow(map_data, aspect=self.aspect_ratio)
        canvas.array = map_data

        # add scalebar
        self.add_scalebar(canvas.axes)

        grid = None
        if style['Colors']['Direction'] == 'vertical':
            grid = gs.GridSpec(5,1)
        elif style['Colors']['Direction'] == 'horizontal':
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
            'style': style,
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

        df_filtered, analytes = self.get_processed_data()

        # Preprocess the data
        scaler = StandardScaler()
        df_scaled = scaler.fit_transform(df_filtered)

        # Perform PCA
        self.pca_results = PCA(n_components=min(len(df_filtered.columns), len(df_filtered)))  # Adjust n_components as needed

        # compute pca scores
        pca_scores = pd.DataFrame(self.pca_results.fit_transform(df_scaled), columns=[f'PC{i+1}' for i in range(self.pca_results.n_components_)])
        self.styles['vectors']['Colors']['CLim'] = [np.amin(self.pca_results.components_), np.amax(self.pca_results.components_)]

        # Add PCA scores to DataFrame for easier plotting
        if self.data[self.sample_id]['computed_data']['PCA Score'].empty:
            self.data[self.sample_id]['computed_data']['PCA Score'] = self.data[self.sample_id]['cropped_raw_data'][['X','Y']]

        self.data[self.sample_id]['computed_data']['PCA Score'].loc[self.data[self.sample_id]['mask'], pca_scores.columns ] = pca_scores

        #update min and max of PCA spinboxes
        if self.pca_results.n_components_ > 0:
            self.spinBoxPCX.setMinimum(1)
            self.spinBoxPCY.setMinimum(1)
            self.spinBoxPCX.setMaximum(self.pca_results.n_components_+1)
            self.spinBoxPCY.setMaximum(self.pca_results.n_components_+1)
            if self.spinBoxPCY.value() == 1:
                self.spinBoxPCY.setValue(int(2))

        self.update_field_type_combobox(self.comboBoxColorByField, addNone=False, plot_type='PCA Score')
        self.update_field_combobox(self.comboBoxColorByField, self.comboBoxColorField)
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

        if self.update_pca_flag or self.data[self.sample_id]['computed_data']['PCA Score'].empty:
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
                canvas = MplCanvas(parent=self)
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

        self.update_figure_font(canvas, self.styles[plot_type]['Text']['Font'])

        self.plot_info = {
            'tree': 'Multidimensional Analysis',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': self.comboBoxPlotType.currentText(),
            'field_type':self.comboBoxColorByField.currentText(),
            'field':  self.comboBoxColorField.currentText(),
            'figure': canvas,
            'style': self.styles[plot_type],
            'cluster_groups': [],
            'view': [True,False],
            'position': [],
            'data': plot_data
        }

        self.update_canvas(canvas)
        self.update_field_combobox(self.comboBoxHistFieldType, self.comboBoxHistField)

    def plot_pca_variance(self):
        """Creates a plot of explained variance, individual and cumulative, for PCA

        Returns
        -------
        MplCanvas
            
        """        
        canvas = MplCanvas(parent=self)

        # pca_dict contains variance ratios for the principal components
        variances = self.pca_results.explained_variance_ratio_
        n_components = range(1, len(variances)+1)
        cumulative_variances = variances.cumsum()  # Calculate cumulative explained variance

        style = self.styles['variance']

        # Plotting the explained variance
        canvas.axes.plot(n_components, variances, linestyle='-', linewidth=style['Lines']['LineWidth'],
            marker=self.markerdict[style['Markers']['Symbol']], markeredgecolor=style['Colors']['Color'], markerfacecolor='none', markersize=style['Markers']['Size'],
            color=style['Colors']['Color'], label='Explained Variance')

        # Plotting the cumulative explained variance
        canvas.axes.plot(n_components, cumulative_variances, linestyle='-', linewidth=style['Lines']['LineWidth'],
            marker=self.markerdict[style['Markers']['Symbol']], markersize=style['Markers']['Size'],
            color=style['Colors']['Color'], label='Cumulative Variance')

        # Adding labels, title, and legend
        xlbl = 'Principal Component'
        ylbl = 'Variance Ratio'

        canvas.axes.legend(fontsize=style['Text']['FontSize'])

        # Adjust the y-axis limit to make sure the plot includes all markers and lines
        canvas.axes.set_ylim([0, 1.0])  # Assuming variance ratios are between 0 and 1

        # labels
        font = {'size':style['Text']['FontSize']}
        canvas.axes.set_xlabel(xlbl, fontdict=font)
        canvas.axes.set_ylabel(ylbl, fontdict=font)

        # tick marks
        canvas.axes.tick_params(direction=style['Axes']['TickDir'],
            labelsize=style['Text']['FontSize'],
            labelbottom=True, labeltop=False, labelleft=True, labelright=False,
            bottom=True, top=True, left=True, right=True)

        canvas.axes.set_xticks(range(1, len(n_components) + 1, 5))
        canvas.axes.set_xticks(n_components, minor=True)

        # aspect ratio
        canvas.axes.set_box_aspect(style['Axes']['AspectRatio'])
        
        plot_data = pd.DataFrame(np.vstack((n_components, variances, cumulative_variances)).T, columns = ['Components','Variance','Cumulative Variance'])
        return canvas, plot_data

    def plot_pca_vectors(self):
        """Displays a heat map of PCA vector components

        Returns
        -------
        MplCanvas
            Creates figure on MplCanvas
        """        
        canvas = MplCanvas(parent=self)

        style = self.styles['vectors']

        # pca_dict contains 'components_' from PCA analysis with columns for each variable
        # No need to transpose for heatmap representation
        analytes = self.data[self.sample_id]['analyte_info'].loc[:,'analytes']

        components = self.pca_results.components_
        # Number of components and variables
        n_components = components.shape[0]
        n_variables = components.shape[1]

        norm = self.color_norm(style)
        cax = canvas.axes.imshow(components, cmap=self.get_colormap(), aspect=1.0, norm=norm)
        canvas.array = components

        # Add a colorbar
        self.add_colorbar(canvas,cax,style)
        # if style['Colors']['Direction'] == 'vertical':
        #     cbar = canvas.fig.colorbar(cax, ax=canvas.axes, orientation=style['Colors']['Direction'], location='right', shrink=0.62, fraction=0.1)
        #     cbar.set_label('PCA Score', size=style['Text']['FontSize'])
        #     cbar.ax.tick_params(labelsize=style['Text']['FontSize'])
        # elif style['Colors']['Direction'] == 'horizontal':
        #     cbar = canvas.fig.colorbar(cax, ax=canvas.axes, orientation=style['Colors']['Direction'], location='bottom', shrink=0.62, fraction=0.1)
        #     cbar.set_label('PCA Score', size=style['Text']['FontSize'])
        #     cbar.ax.tick_params(labelsize=style['Text']['FontSize'])
        # else:
        #     cbar = canvas.fig.colorbar(cax, ax=canvas.axes, orientation=style['Colors']['Direction'], location='bottom', shrink=0.62, fraction=0.1)


        xlbl = 'Principal Components'

        # Optional: Rotate x-axis labels for better readability
        # plt.xticks(rotation=45)

        # labels
        font = {'size':style['Text']['FontSize']}
        canvas.axes.set_xlabel(xlbl, fontdict=font)

        # tickmarks and labels
        canvas.axes.tick_params(labelsize=style['Text']['FontSize'])
        canvas.axes.tick_params(axis='x', direction=style['Axes']['TickDir'],
                        labelsize=style['Text']['FontSize'],
                        labelbottom=False, labeltop=True,
                        bottom=True, top=True)

        canvas.axes.tick_params(axis='y', length=0, direction=style['Axes']['TickDir'],
                        labelsize=style['Text']['FontSize'],
                        labelleft=True, labelright=False,
                        left=True, right=True)

        canvas.axes.set_xticks(range(0, n_components, 5))
        canvas.axes.set_xticks(range(0, n_components, 1), minor=True)
        canvas.axes.set_xticklabels(np.arange(1, n_components+1, 5))

        #ax.set_yticks(n_components, labels=[f'Var{i+1}' for i in range(len(n_components))])
        canvas.axes.set_yticks(range(0, n_variables,1), minor=False)
        canvas.axes.set_yticklabels(self.toggle_mass(analytes), ha='right', va='center')

        canvas.fig.tight_layout()
        plot_data = pd.DataFrame(components, columns = list(map(str, range(n_variables))))
        return canvas, plot_data

    def plot_pca_components(self, canvas):
        """Adds vector components to PCA scatter and heatmaps

        Parameters
        ----------
        canvas : MplCanvas
            Canvas object for plotting

        .. seealso::
            ``MainWindow.plot_pca_vectors``
        """
        #print('plot_pca_components')
        style = self.styles[self.comboBoxPlotType.currentText()]
        if style['Lines']['LineWidth'] == 0:
            return

        # field labels
        analytes = self.data[self.sample_id]['analyte_info'].loc[:,'analytes']
        nfields = len(analytes)

        # components
        pc_x = int(self.spinBoxPCX.value())-1
        pc_y = int(self.spinBoxPCY.value())-1

        x = self.pca_results.components_[:,pc_x]
        y = self.pca_results.components_[:,pc_y]

        # mulitiplier for scale
        m = style['Lines']['Multiplier'] #np.min(np.abs(np.sqrt(x**2 + y**2)))

        # arrows
        canvas.axes.quiver(np.zeros(nfields), np.zeros(nfields), m*x, m*y, color=style['Lines']['Color'],
            angles='xy', scale_units='xy', scale=1, # arrow angle and scale set relative to the data
            linewidth=style['Lines']['LineWidth'], headlength=2, headaxislength=2) # arrow properties

        # labels
        for i, analyte in enumerate(analytes):
            if x[i] > 0 and y[i] > 0:
                canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='left', va='bottom', color=style['Lines']['Color'])
            elif x[i] < 0 and y[i] > 0:
                canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='left', va='top', color=style['Lines']['Color'])
            elif x[i] > 0 and y[i] < 0:
                canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='right', va='bottom', color=style['Lines']['Color'])
            elif x[i] < 0 and y[i] < 0:
                canvas.axes.text(m*x[i], m*y[i], analyte, fontsize=8, ha='right', va='top', color=style['Lines']['Color'])

        plot_data = pd.DataFrame(np.vstack((x,y)).T, columns = ['PC x', 'PC Y'])
        return plot_data
    # -------------------------------------
    # Cluster functions
    # -------------------------------------
    def plot_score_map(self):
        """Plots score maps

        Creates a score map for PCA and clusters.  Maps are displayed on an ``MplCanvas``.
        """
        canvas = MplCanvas(parent=self)

        plot_type = self.comboBoxPlotType.currentText()
        style = self.styles[plot_type]

        # data frame for plotting
        match plot_type:
            case 'PCA Score':
                idx = int(self.comboBoxColorField.currentIndex()) + 1
                field = f'PC{idx}'
            case 'Cluster Score':
                #idx = int(self.comboBoxColorField.currentIndex())
                #field = f'{idx}'
                field = self.comboBoxColorField.currentText()
            case _:
                print('(MainWindow.plot_score_map) Unknown score type'+plot_type)
                return canvas

        reshaped_array = np.reshape(self.data[self.sample_id]['computed_data'][plot_type][field].values, self.array_size, order=self.order)

        cax = canvas.axes.imshow(reshaped_array, cmap=style['Colors']['Colormap'], aspect=self.aspect_ratio, interpolation='none')
        canvas.array = reshaped_array

         # Add a colorbar
        self.add_colorbar(canvas, cax, style, field)

        canvas.axes.set_title(f'{plot_type}')
        canvas.axes.tick_params(direction=None,
            labelbottom=False, labeltop=False, labelright=False, labelleft=False,
            bottom=False, top=False, left=False, right=False)
        #canvas.axes.set_axis_off()

        # add scalebar
        self.add_scalebar(canvas.axes)

        return canvas, self.data[self.sample_id]['computed_data'][plot_type][field]

    def plot_cluster_map(self):
        """Produces a map of cluster categories
        
        Creates the map on an ``MplCanvas``.  Each cluster category is assigned a unique color.
        """
        print('plot_cluster_map')
        canvas = MplCanvas(parent=self)

        plot_type = self.comboBoxPlotType.currentText()
        method = self.comboBoxClusterMethod.currentText()
        style = self.styles[plot_type]

        # data frame for plotting
        groups = self.data[self.sample_id]['computed_data'][plot_type][method].values
        reshaped_array = np.reshape(groups, self.array_size, order=self.order)

        n_clusters = len(np.unique(groups))

        cluster_color, cluster_label, cmap = self.get_cluster_colormap(self.cluster_dict[method], alpha=style['Markers']['Alpha'])

        #boundaries = np.arange(-0.5, n_clusters, 1)
        #norm = colors.BoundaryNorm(boundaries, cmap.N, clip=True)
        norm = self.color_norm(style,n_clusters)

        #cax = canvas.axes.imshow(self.array.astype('float'), cmap=style['Colors']['Colormap'], norm=norm, aspect = self.aspect_ratio)
        cax = canvas.axes.imshow(reshaped_array.astype('float'), cmap=cmap, norm=norm, aspect=self.aspect_ratio)
        canvas.array = reshaped_array
        #cax.cmap.set_under(style['Scale']['OverlayColor'])

        self.add_colorbar(canvas, cax, style, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)

        canvas.fig.subplots_adjust(left=0.05, right=1)  # Adjust these values as needed
        canvas.fig.tight_layout()

        canvas.axes.set_title(f'Clustering ({method})')
        canvas.axes.tick_params(direction=None,
            labelbottom=False, labeltop=False, labelright=False, labelleft=False,
            bottom=False, top=False, left=False, right=False)
        #canvas.axes.set_axis_off()

        # add scalebar
        self.add_scalebar(canvas.axes)

        return canvas, self.data[self.sample_id]['computed_data'][plot_type][method]

    def  compute_clusters(self):
        """Computes cluster results
        
        Cluster properties are defined in the ``MainWindow.toolBox.ClusterPage``."""
        print('\n===compute_clusters===')
        if self.sample_id == '':
            return

        df_filtered, isotopes = self.get_processed_data()
        filtered_array = df_filtered.values
        array = filtered_array[self.data[self.sample_id]['mask']]

        method = self.comboBoxClusterMethod.currentText()
        n_clusters = self.spinBoxNClusters.value()
        exponent = float(self.horizontalSliderClusterExponent.value()) / 10
        seed = int(self.lineEditSeed.text())

        if exponent == 1:
            exponent = 1.0001
        distance_type = self.comboBoxClusterDistance.currentText()

        self.statusbar.showMessage('Precomputing distance for clustering...')
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


        if self.data[self.sample_id]['computed_data']['Cluster'].empty:
            self.data[self.sample_id]['computed_data']['Cluster'][['X','Y']] = self.data[self.sample_id]['cropped_raw_data'][['X','Y']]

        # set all masked data to cluster id -1
        self.data[self.sample_id]['computed_data']['Cluster'].loc[~self.data[self.sample_id]['mask'],method] = 99 

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
                kmeans = KMeans(n_clusters=n_clusters, init='k-means++', random_state=seed)

                # produce k-means model from data
                model = kmeans.fit(array)

                #add k-means results to self.data
                self.data[self.sample_id]['computed_data']['Cluster'].loc[self.data[self.sample_id]['mask'],'k-means'] = model.predict(array)

            # fuzzy c-means
            case 'fuzzy c-means':
                # add x y from raw data if empty dataframe
                if self.data[self.sample_id]['computed_data']['Cluster Score'].empty:
                    self.data[self.sample_id]['computed_data']['Cluster Score'] = self.data[self.sample_id]['cropped_raw_data'][['X','Y']]

                # compute cluster scores
                cntr, u, _, _, _, _, _ = fuzz.cluster.cmeans(array.T, n_clusters, exponent, error=0.00001, maxiter=1000, seed=seed)
                #cntr, u, _, _, _, _, _ = fuzz.cluster.cmeans(array.T, n_clusters, exponent, metric='precomputed', error=0.00001, maxiter=1000, seed=seed)
                # cntr, u, _, _, _, _, _ = fuzz.cluster.cmeans(array.T, n_clusters, exponent, error=0.005, maxiter=1000,seed =23)

                # assign cluster scores to self.data
                for n in range(n_clusters):
                    self.data[self.sample_id]['computed_data']['Cluster Score'].loc[:,str(n)] = pd.NA
                    self.data[self.sample_id]['computed_data']['Cluster Score'].loc[self.data[self.sample_id]['mask'],str(n)] = u[n-1,:]

                #add cluster results to self.data
                self.data[self.sample_id]['computed_data']['Cluster'].loc[self.data[self.sample_id]['mask'],'fuzzy c-means'] = np.argmax(u, axis=0)

        # update cluster table in style menu
        self.group_changed()

        self.statusbar.showMessage('Clustering successful')

        self.update_field_type_combobox(self.comboBoxColorByField, addNone=False, plot_type='Cluster')
        self.update_field_combobox(self.comboBoxColorByField, self.comboBoxColorField)
        self.update_cluster_flag = False

    def plot_clusters(self):
        """Plot maps associated with clustering

        Will produce plots of Clusters or Cluster Scores and computes clusters if necesseary.
        """        
        print('plot_clusters')
        if self.sample_id == '':
            return

        method = self.comboBoxClusterMethod.currentText()
        if self.update_cluster_flag or \
                self.data[self.sample_id]['computed_data']['Cluster'].empty or \
                (method not in list(self.data[self.sample_id]['computed_data']['Cluster Score'].keys())):
            self.compute_clusters()


        self.cluster_dict['active method'] = method

        plot_type = self.comboBoxPlotType.currentText()

        match plot_type:
            case 'Cluster':
                self.comboBoxColorField.setCurrentText(method)
                plot_name = f"{plot_type}_{method}_map"
                canvas, plot_data = self.plot_cluster_map()
            case 'Cluster Score':
                plot_name = f"{plot_type}_{method}_{self.comboBoxColorField.currentText()}_score_map"
                canvas, plot_data = self.plot_score_map()
            case _:
                print(f'Unknown PCA plot type: {plot_type}')
                return

        self.update_figure_font(canvas, self.styles[plot_type]['Text']['Font'])

        self.plot_info = {
            'tree': 'Multidimensional Analysis',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': self.comboBoxPlotType.currentText(),
            'field_type':self.comboBoxColorByField.currentText(),
            'field':  self.comboBoxColorField.currentText(),
            'figure': canvas,
            'style': self.styles[plot_type],
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

        Enables/disables widgets in Left Toolbox > Clustering Page.  Updates widget values/text with values saved in ``MainWindow.cluster_dict``.
        """
        print('cluster_method_callback')
        if self.sample_id == '':
            return

        # update_clusters_ui - Enables/disables tools associated with clusters
        method = self.comboBoxClusterMethod.currentText()
        self.cluster_dict['active method'] = method

        if method not in self.data[self.sample_id]['computed_data']['Cluster']:
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

    def select_cluster_group_callback(self):
        """Set cluster color button background after change of selected cluster group

        Sets ``MainWindow.toolButtonClusterColor`` background on change of ``MainWindow.spinBoxClusterGroup``
        """
        if self.tableWidgetViewGroups.rowCount() == 0:
            return
        self.toolButtonClusterColor.setStyleSheet("background-color: %s;" % self.tableWidgetViewGroups.item(self.spinBoxClusterGroup.value()-1,2).text())

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
            if (self.comboBoxPlotType.currentText() not in ['Cluster', 'Cluster Score']) and (self.comboBoxColorByField.currentText() == 'Cluster'):
                self.update_SV()


    # -------------------------------------
    # TEC and Radar plots
    # -------------------------------------

    def plot_ndim(self):
        """Produces trace element compatibility (TEC) and Radar plots
        
        Geochemical TEC diagrams are a staple of geochemical analysis, often referred to as spider diagrams, which display a set of elements
        arranged by compatibility.  Radar plots show data displayed on a set of radial spokes (axes), giving the appearance of a radar screen
        or spider web.
        
        The function updates ``MainWindow.plot_info`` with the displayed plot metadata and figure ``MplCanvas`` for display in the centralWidget views.
        """
        if not self.ndim_list:
            return

        df_filtered, _  = self.get_processed_data()

        match self.comboBoxNorm.currentText():
            case 'log':
                df_filtered.loc[:,:] = 10**df_filtered.values
            case 'mixed':
                pass
            case 'linear':
                # do nothing
                pass
        df_filtered = df_filtered[self.data[self.sample_id]['mask']]

        ref_i = self.comboBoxNDimRefMaterial.currentIndex()

        plot_type = self.comboBoxPlotType.currentText()
        style = self.styles[plot_type]

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
        labels = self.toggle_mass(self.ndim_list)
            
        if self.comboBoxColorByField.currentText() == 'Cluster' and self.comboBoxColorField.currentText() != '':
            method = self.comboBoxColorField.currentText()
            cluster_dict = self.cluster_dict[method]
            cluster_color, cluster_label, cmap = self.get_cluster_colormap(cluster_dict, alpha=style['Markers']['Alpha'])

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
                canvas = MplCanvas(parent=self, proj='radar')

                axes_interval = 5
                if cluster_flag and method in self.data[self.sample_id]['computed_data']['Cluster']:
                    # Get the cluster labels for the data
                    cluster_group = self.data[self.sample_id]['computed_data']['Cluster'][method][self.data[self.sample_id]['mask']]

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
                canvas = MplCanvas(parent=self)

                yl = [np.inf, -np.inf]
                if cluster_flag and method in self.data[self.sample_id]['computed_data']['Cluster']:
                    # Get the cluster labels for the data
                    cluster_group = self.data[self.sample_id]['computed_data']['Cluster'][method][self.data[self.sample_id]['mask']]

                    df_filtered['clusters'] = cluster_group

                    # Plot tec for all clusters
                    for i in clusters:
                        # Create RGBA color
                        #print(f'Cluster {i}')
                        canvas.axes,yl_tmp = plot_spider_norm(
                                data=df_filtered.loc[df_filtered['clusters']==i,:],
                                ref_data=self.ref_data, norm_ref_data=self.ref_data['model'][ref_i],
                                layer=self.ref_data['layer'][ref_i], el_list=self.ndim_list ,
                                style='Quanta', quantiles=quantiles, ax=canvas.axes, c=cluster_color[i], label=cluster_label[i]
                            )
                        #store max y limit to convert the set y limit of axis
                        yl = [np.floor(np.nanmin([yl[0] , yl_tmp[0]])), np.ceil(np.nanmax([yl[1] , yl_tmp[1]]))]

                    # Put a legend below current axis
                    box = canvas.axes.get_position()
                    canvas.axes.set_position([box.x0, box.y0 - box.height * 0.1,
                                    box.width, box.height * 0.9])

                    self.add_colorbar(canvas, None, style, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color)
                    #canvas.axes.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=3, handlelength=1)

                    self.logax(canvas.axes, yl, 'y')
                    canvas.axes.set_ylim(yl)

                    canvas.axes.set_xticklabels(labels, rotation=angle)
                else:
                    canvas.axes,yl, plot_data = plot_spider_norm(data=df_filtered, ref_data=self.ref_data, norm_ref_data=self.ref_data['model'][ref_i], layer=self.ref_data['layer'][ref_i], el_list=self.ndim_list, style='Quanta', quantiles=quantiles, ax=canvas.axes)

                    canvas.axes.set_xticklabels(labels, rotation=angle)
                canvas.axes.set_ylabel('Abundance / ['+self.ref_data['model'][ref_i]+', '+self.ref_data['layer'][ref_i]+']')
                canvas.fig.tight_layout()

        if cluster_flag:
            plot_name = f"{plot_type}_"
        else:
            plot_name = f"{plot_type}_all"

        self.update_figure_font(canvas, self.styles[plot_type]['Text']['Font'])

        self.plot_info = {
            'tree': 'Geochemistry',
            'sample_id': self.sample_id,
            'plot_name': plot_name,
            'plot_type': plot_type,
            'field_type': 'analyte',
            'field': self.ndim_list,
            'figure': canvas,
            'style': style,
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
            self.data[self.sample_id]['filter_info'].at[row, 'use'] = state == QtCore.Qt.Checked

        if calling_widget == 'analyteAdd':
            el_list = [self.comboBoxNDimAnalyte.currentText().lower()]
            self.comboBoxNDimAnalyteSet.setCurrentText = 'user defined'
        elif calling_widget == 'analytesetAdd':
            analyte_set = self.comboBoxNDimAnalyteSet.currentText().lower()

            ####
            #### This needs to be set up more generic so that a user defined sets can be added to the list
            ####
            if analyte_set == 'majors':
                el_list = ['Si','Ti','Al','Fe','Mn','Mg','Ca','Na','K','P']
            elif analyte_set == 'full trace':
                el_list = ['Cs','Rb','Ba','Th','U','K','Nb','Ta','La','Ce','Pb','Mo','Pr','Sr','P','Ga','Zr','Hf','Nd','Sm','Eu','Li','Ti','Gd','Dy','Ho','Y','Er','Yb','Lu']
            elif analyte_set == 'ree':
                el_list = ['La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu']
            elif analyte_set == 'metals':
                el_list = ['Na','Al','Ca','Zn','Sc','Cu','Fe','Mn','V','Co','Mg','Ni','Cr']

        analytes_list = self.data[self.sample_id]['analyte_info'].loc[:, 'analytes'].values

        analytes = [col for iso in el_list for col in analytes_list if re.sub(r'\d', '', col).lower() == re.sub(r'\d', '',iso).lower()]

        self.ndim_list.extend(analytes)

        for analyte in analytes:
            # Add a new row at the end of the table
            row = self.tableWidgetNDim.rowCount()
            self.tableWidgetNDim.insertRow(row)

            # Create a QCheckBox for the 'use' column
            chkBoxItem_use = QCheckBox()
            chkBoxItem_use.setCheckState(QtCore.Qt.Checked)
            chkBoxItem_use.stateChanged.connect(lambda state, row=row: on_use_checkbox_state_changed(row, state))

            chkBoxItem_select = QTableWidgetItem()
            chkBoxItem_select.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                QtCore.Qt.ItemIsEnabled)

            chkBoxItem_select.setCheckState(QtCore.Qt.Unchecked)
            norm = self.data[self.sample_id]['analyte_info'].loc[(self.data[self.sample_id]['analyte_info']['analytes'] == analyte)].iloc[0]['norm']

            self.tableWidgetNDim.setCellWidget(row, 0, chkBoxItem_use)
            self.tableWidgetNDim.setItem(row, 1,
                                     QTableWidgetItem(self.sample_id))
            self.tableWidgetNDim.setItem(row, 2,
                                     QTableWidgetItem(analyte))

            self.tableWidgetNDim.setItem(row, 3,
                                     QTableWidgetItem(norm))
            self.tableWidgetNDim.setItem(row, 4,
                                     chkBoxItem_select)

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
        if method in self.data[self.sample_id]['computed_data']['Cluster']:
            if not self.data[self.sample_id]['computed_data']['Cluster'][method].empty:
                clusters = self.data[self.sample_id]['computed_data']['Cluster'][method].dropna().unique()
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

                    hexcolor = self.set_default_cluster_colors(mask=True)
                else:
                    self.tableWidgetViewGroups.setRowCount(len(clusters))
                    self.spinBoxClusterGroup.setMaximum(len(clusters))

                    hexcolor = self.set_default_cluster_colors(mask=False)

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
                    # colors in table are set by self.set_default_cluster_colors()
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

            # Update self.data[self.sample_id]['computed_data']['Cluster'] with the new name
            if self.cluster_dict['active method'] in self.data[self.sample_id]['computed_data']['Cluster']:
                # Find the rows where the value matches cluster_id
                rows_to_update = self.data[self.sample_id]['computed_data']['Cluster'][self.cluster_dict['active method']] == cluster_id

                # Update these rows with the new name
                self.data[self.sample_id]['computed_data']['Cluster'].loc[rows_to_update, self.cluster_dict['active method']] = new_name

            # update current_group to reflect the new cluster name
            self.cluster_dict[self.cluster_dict['active method']][cluster_id]['name'] = new_name

            # update plot with new cluster name
            self.update_SV()

    def outlier_detection(self, data ,lq=0.0005, uq=99.5, d_lq=9.95 , d_uq=99):
        # Ensure data is a numpy array
        data = np.array(data)

        # Shift values to positive concentrations
        v0 = np.nanmin(data, axis=0) - 0.001
        data_shifted = np.log10(data - v0)

        # Calculate required quantiles and differences
        lq_val = np.nanpercentile(data_shifted, lq, axis=0)
        uq_val = np.nanpercentile(data_shifted, uq, axis=0)
        sorted_indices = np.argsort(data_shifted, axis=0)
        sorted_data = np.take_along_axis(data_shifted, sorted_indices, axis=0)


        diff_sorted_data = np.diff(sorted_data, axis=0)
        # Adding a 0 to the beginning of each column to account for the reduction in size by np.diff
        diff_sorted_data = np.insert(diff_sorted_data, 0, 0, axis=0)
        diff_array_uq_val = np.nanpercentile(diff_sorted_data, d_uq, axis=0)
        diff_array_lq_val = np.nanpercentile(diff_sorted_data, d_lq, axis=0)
        upper_cond = (sorted_data > uq_val) & (diff_sorted_data > diff_array_uq_val)

        # Initialize arrays for results
        clipped_data = np.copy(sorted_data)

        # Upper bound outlier filter
        for col in range(sorted_data.shape[1]):
            up_indices = np.where(upper_cond[:, col])[0]
            if len(up_indices) > 0:
                uq_outlier_index = up_indices[0]
                clipped_data[uq_outlier_index:, col] = clipped_data[uq_outlier_index-1, col]

        lower_cond = (sorted_data < lq_val) & (diff_sorted_data > diff_array_lq_val)
        # Lower bound outlier filter
        for col in range(sorted_data.shape[1]):
            low_indices = np.where(lower_cond[:, col])[0]
            if len(low_indices) > 0:
                lq_outlier_index = low_indices[-1]
                clipped_data[:lq_outlier_index+1, col] = clipped_data[lq_outlier_index+1, col]

        clipped_data = np.take_along_axis(clipped_data, np.argsort(sorted_indices, axis=0), axis=0)
        # Unshift the data
        clipped_data = 10**clipped_data + v0

        return clipped_data

    def transform_array(self, array, negative_method):
        """Negative and zero handling

        Parameters
        ----------
        array : numpy.ndarray
            Input data
        negative_method : str
            negative_method obtained from analyte info
        Returns
        -------
        numpy.ndarray
            Transformed data
        """


        #n
        match negative_method.lower():
            case 'ignore negative values':
                t_array = np.copy(array)
                t_array = np.where(t_array > 0, t_array, np.nan)
                return t_array
            case 'minimum positive value':
                min_positive_value = np.nanmin(array[array > 0])
                t_array = np.where(array < 0, min_positive_value, array)
                return t_array
            case 'gradual shift':
                if array.ndim == 2:
                    # Calculate min and max values for each column and adjust their shapes for broadcasting
                    min_val = np.nanmin(array, axis=0, keepdims=True) - 0.0001
                    max_val = np.nanmax(array, axis=0, keepdims=True)

                    # Adjust the shape of min_val and max_val for broadcasting
                    adjusted_min_val = min_val
                    adjusted_max_val = max_val

                    # Check if min values are less than or equal 0
                    min_leq_zero = adjusted_min_val <= 0

                    # Perform transformation with broadcasting
                    t_array = np.where(
                        min_leq_zero,
                        (adjusted_max_val * (array - adjusted_min_val)) / (adjusted_max_val - adjusted_min_val),
                        array
                    )
                else:
                    # 1D array case, similar to original logic
                    min_val = np.nanmin(array) - 0.0001
                    max_val = np.nanmax(array)
                    if min_val < 0:
                        t_array = (max_val * (array - min_val)) / (max_val - min_val)
                    else:
                        t_array = np.copy(array)
                return t_array
            case 'yeo-johnson transformation':
                # Apply Yeo-Johnson transformation
                t_array, lambda_yeojohnson = yeojohnson(array)
                return t_array

    # make this part of the calculated fields
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

        match plot_type.lower():
            case 'correlation' | 'histogram' | 'tec':
                if self.data[self.sample_id]['computed_data']['Cluster'].empty:
                    field_list = []
                    self.toggle_style_widgets()
                else:
                    field_list = ['Cluster']
                    self.toggle_style_widgets()
            case 'cluster score':
                if self.data[self.sample_id]['computed_data']['Cluster Score'].empty:
                    field_list = []
                    self.toggle_style_widgets()
                else:
                    field_list = ['Cluster Score']
                    self.toggle_style_widgets()
            case 'cluster':
                if self.data[self.sample_id]['computed_data']['Cluster'].empty:
                    field_list = []
                    self.toggle_style_widgets()
                else:
                    field_list = ['Cluster']
                    self.toggle_style_widgets()
            case 'pca score':
                if self.data[self.sample_id]['computed_data']['PCA Score'].empty:
                    field_list = []
                    self.toggle_style_widgets()
                else:
                    field_list = ['PCA Score']
                    self.toggle_style_widgets()
            case 'ternary map':
                self.toggle_style_widgets()
                self.labelCbarDirection.setEnabled(True)
                self.comboBoxCbarDirection.setEnabled(True)
            case _:
                field_list = ['Analyte', 'Analyte (normalized)']

                # add check for ratios
                for field in self.data[self.sample_id]['computed_data']:
                    if not (self.data[self.sample_id]['computed_data'][field].empty):
                        field_list.append(field)
                        if field == 'Ratio':
                            field_list.append('Ratio (normalized)')
                self.toggle_style_widgets()

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

        # colors
        addNone = True
        if self.comboBoxPlotType.currentText() in ['analyte map','PCA Score','Cluster','Cluster Score']:
            addNone = False
        self.update_field_type_combobox(self.comboBoxColorByField, addNone=addNone, plot_type=self.comboBoxPlotType.currentText())
        self.update_field_combobox(self.comboBoxColorByField, self.comboBoxColorField)

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

        match set_name:
            case 'Analyte' | 'Analyte (normalized)':
                set_fields = self.data[self.sample_id]['analyte_info'].loc[self.data[self.sample_id]['analyte_info']['use']== True,'analytes'].values.tolist()
            case 'Ratio' | 'Ratio (normalized)':
                analytes_1 = self.data[self.sample_id]['ratio_info'].loc[self.data[self.sample_id]['ratio_info']['use']== True,'analyte_1']
                analytes_2 =  self.data[self.sample_id]['ratio_info'].loc[self.data[self.sample_id]['ratio_info']['use']== True,'analyte_2']
                ratios = analytes_1 +' / '+ analytes_2
                set_fields = ratios.values.tolist()
            case 'None':
                return []
            case _:
                #populate field name with column names of corresponding dataframe remove 'X', 'Y' is it exists
                set_fields = [col for col in self.data[self.sample_id]['computed_data'][set_name].columns.tolist() if col not in ['X', 'Y']]

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
        self.check_analysis = False

    def update_spinboxes(self, sample_id, field, field_type='Analyte'):
        """
        Retrieves Auto scale parameters and neg handling method from Analyte/Ratio Info and updates UI.

        Parameters
        ----------
        sample_id : str
            Sample identifier
        field : str, optional
            Name of field to plot, Defaults to None
        analysis_type : str, optional
            Field type for plotting, options include: 'Analyte', 'Ratio', 'pca', 'Cluster', 'Cluster Score',
            'Special', 'computed'. Some options require a field. Defaults to 'Analyte'
        """
        match field_type:
            case 'Analyte' | 'Analyte (normalized)':
                # get Auto scale parameters and neg handling from analyte info
                parameters = self.data[sample_id]['analyte_info'].loc[self.data[sample_id]['analyte_info']['analytes']==field].iloc[0]
            
            case 'Ratio' | 'Ratio (normalized)':
                field_1 = field.split(' / ')[0]
                field_2 = field.split(' / ')[1]
                # get Auto scale parameters and neg handling from Ratio info
                parameters = self.data[sample_id]['ratio_info'].loc[self.data[sample_id]['analyte_info']['analytes']==field].iloc[0]  
            case _:
                return
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
            self.lineEditDifferenceLowerQuantile.value = parameters['d_l_bound']
            self.lineEditDifferenceUpperQuantile.value = parameters['d_u_bound']

            # Update Neg Value handling combobox 
            index = self.comboBoxNegativeMethod.findText(str(parameters['negative_method']))
            if index != -1:  # If the text is found in the combobox
                self.comboBoxNegativeMethod.setCurrentIndex(index)
            
            # Update filter UI 
            self.lineEditFMin.value = parameters['v_min']
            self.lineEditFMax.value = parameters['v_max']
            self.callback_lineEditFMin()
            self.callback_lineEditFMax()

    # ----start debugging----
    # def test_get_field_list(self):
    #     self.open_directory()

    #     self.compute_pca()

    #     for type in ['Analyte', 'Analyte (normalized)', 'Ratio', 'PCA Score']:
    #         print(self.get_field_list(set_name=type))
    # ----end debugging----


    # -------------------------------------
    # Data functions functions
    # -------------------------------------
    def get_map_data(self, sample_id, field, field_type='Analyte'):
        """
        Retrieves and processes the mapping data for the given sample and analytes, then plots the result if required.

        The method also updates certain parameters in the analyte data frame related to scaling.
        Based on the plot type, this method internally calls the appropriate plotting functions.

        Parameters
        ----------
        sample_id : str
            Sample identifier
        field : str, optional
            Name of field to plot, Defaults to None
        analysis_type : str, optional
            Field type for plotting, options include: 'Analyte', 'Ratio', 'pca', 'Cluster', 'Cluster Score',
            'Special', 'computed'. Some options require a field. Defaults to 'Analyte'

        Returns
        -------
        pandas.DataFrame
            Processed data for plotting. This is only returned if analysis_type is not 'laser' or 'hist'.
        """
        # ----begin debugging----
        # print('[get_map_data] sample_id: '+sample_id+'   field_type: '+field_type+'   field: '+field)
        # ----end debugging----

        # if sample_id != self.sample_id:
        #     #axis mask is not used when plot analytes of a different sample
        #     axis_mask  = np.ones_like( self.data[sample_id]['raw_data']['X'], dtype=bool)
        # else:
        #     axis_mask = self.data[self.sample_id]['axis_mask']
        
        # retrieve axis mask for that sample
        axis_mask = self.data[self.sample_id]['axis_mask']
        
        #crop plot if filter applied
        df = self.data[sample_id]['raw_data'][['X','Y']][axis_mask].reset_index(drop=True)

        print(field_type)

        match field_type:
            case 'Analyte' | 'Analyte (normalized)':
                # unnormalized
                df ['array'] = self.data[sample_id]['processed_data'].loc[:,field].values
                #get analyte info
                norm = self.data[sample_id]['analyte_info'].loc[self.data[sample_id]['analyte_info']['analytes']==field,'norm'].iloc[0]
                
                #perform scaling for groups of analytes with same norm parameter
                
                if norm == 'log':
                    df['array'] = np.where(~np.isnan(df['array']), np.log10(df['array']), df['array'])

                    # print(self.processed_analyte_data[sample_id].loc[:10,analytes])
                    # print(self.data[sample_id]['processed_data'].loc[:10,analytes])
                elif norm == 'logit':
                    # Handle division by zero and NaN values
                    with np.errstate(divide='ignore', invalid='ignore'):
                        df['array'] = np.where(~np.isnan(df['array']), np.log10(df['array'] / (10**6 - df['array'])))
                
                # normalize
                if 'normalized' in field_type:
                    refval = self.ref_chem[re.sub(r'\d', '', field).lower()]
                    df['array'] = df['array'] / refval

            case 'Ratio' | 'Ratio (normalized)':
                field_1 = field.split(' / ')[0]
                field_2 = field.split(' / ')[1]

                # unnormalized
                #df['array'] = self.data[sample_id]['computed_data'].loc[:,field_1].values / self.data[sample_id]['processed_data'].loc[:,field_2].values
                df['array'] = self.data[sample_id]['computed_data']['Ratio'].loc[:,field].values
                
                #get norm value
                norm = self.data[sample_id]['ratio_info'].loc['norm',(self.data[sample_id]['ratio_info']['analyte_1']==field_1 & self.data[sample_id]['ratio_info']['analyte_2']==field_2)].iloc[0]

                if norm == 'log':
                    df ['array'] = np.where(~np.isnan(df['array']), np.log10(df ['array']))
                    # print(self.processed_analyte_data[sample_id].loc[:10,analytes])
                    # print(self.data[sample_id]['processed_data'].loc[:10,analytes])
                elif norm == 'logit':
                    # Handle division by zero and NaN values
                    with np.errstate(divide='ignore', invalid='ignore'):
                        df['array'] = np.where(~np.isnan(df['array']), np.log10(df['array'] / (10**6 - df['array'])))
                # normalize
                if 'normalized' in field_type:
                    refval_1 = self.ref_chem[re.sub(r'\d', '', field_1).lower()]
                    refval_2 = self.ref_chem[re.sub(r'\d', '', field_2).lower()]
                    df['array'] = df['array'] * (refval_2 / refval_1)

            case _:#'PCA Score' | 'Cluster' | 'Cluster Score' | 'Special' | 'Computed':
                df['array'] = self.data[sample_id]['computed_data'][field_type].loc[:,field].values
            
        # ----begin debugging----
        # print(df.columns)
        # ----end debugging----

        # crop plot if filter applied
        # current_plot_df = current_plot_df[self.data[self.sample_id]['axis_mask']].reset_index(drop=True)
        return df

    # extracts data for scatter plot
    def get_scatter_values(self,plot_type):
        """Creates a dictionary of values for plotting

        Returns
        -------
        dict
            Four return variables, x, y, z, and c, each as a dict with locations for bi- and
            ternary plots.  Each contain a 'field', 'type', 'label', and 'array'.  x, y and z
            contain coordinates and c contains the colors
        """
        value_dict = {
            'x': {'field': None, 'type': None, 'label': None, 'array': None},
            'y': {'field': None, 'type': None, 'label': None, 'array': None},
            'z': {'field': None, 'type': None, 'label': None, 'array': None},
            'c': {'field': None, 'type': None, 'label': None, 'array': None}
        }

        match plot_type:
            case 'histogram':
                value_dict['x']['field'] = self.comboBoxHistField.currentText()
                value_dict['x']['type'] = self.comboBoxHistFieldType.currentText()
                value_dict['y']['field'] = None
                value_dict['y']['type'] = None
                value_dict['z']['field'] = None
                value_dict['z']['type'] = None
                value_dict['c']['field'] = None
                value_dict['c']['type'] = None
            case 'scatter' | 'heatmap' | 'ternary map':
                value_dict['x']['field'] = self.comboBoxFieldX.currentText()
                value_dict['x']['type'] = self.comboBoxFieldTypeX.currentText()
                value_dict['y']['field'] = self.comboBoxFieldY.currentText()
                value_dict['y']['type'] = self.comboBoxFieldTypeY.currentText()
                value_dict['z']['field'] = self.comboBoxFieldZ.currentText()
                value_dict['z']['type'] = self.comboBoxFieldTypeZ.currentText()
                value_dict['c']['field'] = self.comboBoxColorField.currentText()
                value_dict['c']['type'] = self.comboBoxColorByField.currentText()
            case 'pca scatter' | 'pca heatmap':
                value_dict['x']['field'] = f'PC{self.spinBoxPCX.value()}'
                value_dict['x']['type'] = 'PCA Score'
                value_dict['y']['field'] = f'PC{self.spinBoxPCY.value()}'
                value_dict['y']['type'] = 'PCA Score'

                value_dict['z']['field'] = None
                value_dict['z']['type'] = None
                value_dict['c']['field'] = self.comboBoxColorField.currentText()
                value_dict['c']['type'] = self.comboBoxColorByField.currentText()
            case _:
                print('get_scatter_values(): Not defined for ' + self.comboBoxPlotType.currentText())
                return

        for k, v in value_dict.items():
            # only need to setup when fields exist
            if v['field'] is None:
                continue

            match v['type']:
                case 'Analyte' | 'Analyte (normalized)':
                    df = self.get_map_data(self.sample_id, field=v['field'], field_type=v['type'])
                    v['label'] = v['field'] + ' (' + self.preferences['Units']['Concentration'] + ')'
                case 'Ratio':
                    #analyte_1, analyte_2 = v['field'].split('/')
                    df = self.get_map_data(self.sample_id, field=v['field'], field_type=v['type'])
                    v['label'] = v['field']
                case 'PCA Score' | 'Cluster' | 'Cluster Score':
                    df = self.get_map_data(self.sample_id, field=v['field'], field_type=v['type'])
                    v['label'] = v['field']
                case 'Special':
                    df = self.get_map_data(self.sample_id, field=v['field'], field_type=v['type'])
                    v['label'] = v['field']
                case _:
                    df = pd.DataFrame({'array': []})  # Or however you want to handle this case

            value_dict[k]['array'] = df['array'][self.data[self.sample_id]['mask']].values if not df.empty else []

            # set axes widgets
            if v['field'] not in self.axis_dict.keys():
                self.initialize_axis_values(v['type'], v['field'])

            if k == 'c':
                self.set_color_axis_widgets()
            else:
                self.set_axis_widgets(k, v['field'])

            # set lineEdit labels for axes
            # self.lineEditXLabel.setText(value_dict['x']['label'])
            # self.lineEditYLabel.setText(value_dict['y']['label'])
            # self.lineEditZLabel.setText(value_dict['z']['label'])
            # self.lineEditCbarLabel.setText(value_dict['c']['label'])

        return value_dict['x'], value_dict['y'], value_dict['z'], value_dict['c']

    def callback_dating_method(self):
        """Updates isotopes and decay constants when dating method changes.

        Default decay constants are as follows:
        * Lu-Hf : :math:`1.867 \pm 0.008 \times 10^{-5}` Ma (Sonderlund et al., EPSL, 2004, https://doi.org/10.1016/S0012-821X(04)00012-3)
        * Re-Os : :math:`1.666 \pm 0.005 \times 10^{-5}` Ma (Selby et al., GCA, 2007, https://doi.org/10.1016/j.gca.2007.01.008)
        """        
        match self.comboBoxDatingMethod.currentText():
            case "Lu-Hf":
                self.labelIsotope1.setText("Lu175")
                if "Lu175" in self.analyte_list and self.comboBoxIsotopeAgeFieldType1.currentText() == "Analyte":
                    self.comboBoxIsotopeAgeField1.setCurrentText("Lu175")
                self.labelIsotope2.setText("Hf176")
                if "Hf176" in self.analyte_list and self.comboBoxIsotopeAgeFieldType2.currentText() == "Analyte":
                    self.comboBoxIsotopeAgeField2.setCurrentText("Hf176")
                self.labelIsotope3.setText("Hf178")
                if "Hf178" in self.analyte_list and self.comboBoxIsotopeAgeFieldType3.currentText() == "Analyte":
                    self.comboBoxIsotopeAgeField3.setCurrentText("Hf178")

                # Sonderlund et al., EPSL, 2004, https://doi.org/10.1016/S0012-821X(04)00012-3
                self.lineEditDecayConstant.value = 1.867e-5 # Ma
                self.lineEditDecayConstantUncertainty.value = 0.008e-5 # Ma
            case "Re-Os":
                self.labelIsotope1.setText("Re187")
                if "Re187" in self.analyte_list and self.comboBoxIsotopeAgeFieldType1.currentText() == "Analyte":
                    self.comboBoxIsotopeAgeField1.setCurrentText("Re187")
                self.labelIsotope2.setText("Os187")
                if "Os187" in self.analyte_list and self.comboBoxIsotopeAgeFieldType2.currentText() == "Analyte":
                    self.comboBoxIsotopeAgeField2.setCurrentText("Os187")
                self.labelIsotope3.setText("Os188")
                if "Os188" in self.analyte_list and self.comboBoxIsotopeAgeFieldType3.currentText() == "Analyte":
                    self.comboBoxIsotopeAgeField3.setCurrentText("Os188")

                # Selby et al., GCA, 2007, https://doi.org/10.1016/j.gca.2007.01.008
                self.lineEditDecayConstant.value = 1.666e-5 # Ma
                self.lineEditDecayConstantUncertainty.value = 0.005e-5 # Ma
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

    def compute_date_map(self):
        """Compute one of several date maps"""
        decay_constant = self.lineEditDecayConstant.value
        method = self.comboBoxDatingMethod.currentText()
        match method:
            case "Lu-Hf":
                Lu175 = self.get_map_data(self.sample_id, self.comboBoxIsotopeAgeField1.currentText(), self.comboBoxIsotopeAgeFieldType1.currentText())
                Hf176 = self.get_map_data(self.sample_id, self.comboBoxIsotopeAgeField2.currentText(), self.comboBoxIsotopeAgeFieldType2.currentText())
                Hf178 = self.get_map_data(self.sample_id, self.comboBoxIsotopeAgeField3.currentText(), self.comboBoxIsotopeAgeFieldType3.currentText())

                if self.data[self.sample_id]['computed_data']['Calculated'].empty:
                    self.data[self.sample_id]['computed_data']['Calculated'][['X','Y']] = self.data[self.sample_id]['cropped_raw_data'][['X','Y']]

                date_map = np.log((Hf176['array'].values/Hf178['array'].values - 3.55)/(Lu175['array'].values/Hf178['array'].values) + 1) / decay_constant 

            case "Re-Os":
                pass

        # save date_map to Calculated dataframe
        self.data[self.sample_id]['computed_data']['Calculated'].loc[self.data[self.sample_id]['mask'],method] = date_map
        
        # update styles and plot
        self.comboBoxColorByField.setCurrentText('Calculated')
        self.color_by_field_callback()
        self.comboBoxColorField.setCurrentText(method)
        self.color_field_callback()
        #self.set_style_widgets(plot_type='analyte map')

        #self.update_SV()

    def get_processed_data(self):
        """Gets the processed data for analysis

        Returns
        -------
        pandas.DataFrame
            Filtered data frame 
        bool
            Analytes included from processed data
        """
        if self.sample_id == '':
            return

        # return normalised, filtered data with that will be used for analysis
        use_analytes = self.data[self.sample_id]['analyte_info'].loc[(self.data[self.sample_id]['analyte_info']['use']==True), 'analytes'].values

        df_filtered = self.data[self.sample_id]['processed_data'][use_analytes]

        #get analyte info to extract choice of scale
        analyte_info = self.data[self.sample_id]['analyte_info'].loc[
                                 (self.data[self.sample_id]['analyte_info']['analytes'].isin(use_analytes))]
        
        #perform scaling for groups of analytes with same norm parameter
        for norm in analyte_info['norm'].unique():
            filtered_analytes = analyte_info[(analyte_info['norm'] == norm)]['analytes']
            filtered_data = df_filtered[filtered_analytes].values
            if norm == 'log':

                # np.nanlog handles NaN value
                df_filtered[filtered_analytes] = np.where(~np.isnan(filtered_data), np.log10(filtered_data))
                # print(self.processed_analyte_data[sample_id].loc[:10,analytes])
                # print(self.data[sample_id]['processed_data'].loc[:10,analytes])
            elif norm == 'logit':
                # Handle division by zero and NaN values
                with np.errstate(divide='ignore', invalid='ignore'):
                    df_filtered[filtered_analytes] = np.where(~np.isnan(filtered_data), np.log10(filtered_data / (10**6 - filtered_data)))

        # Combine the two masks to create a final mask
        nan_mask = df_filtered.notna().all(axis=1)
        
        
        # mask nan values and add to self.data[self.sample_id]['mask']
        self.data[self.sample_id]['mask'] = self.data[self.sample_id]['mask']  & nan_mask.values

        return df_filtered, use_analytes

    def import_data(self, path):
        """Reads data files and returns data dictionary

        Reads available csv files in ``path`` and returns a dictionary with sample id's (file names minus extension).

        Parameters
        ----------
        path : str
            Path with data files.
        
        Returns
        -------
        dict
            Dictionary of dataframes
        """
        # Get a list of all files in the directory
        file_list = os.listdir(path)
        csv_files = [file for file in file_list if file.endswith('.csv')]
        csv_files = csv_files[0:2]
        # layout = self.widgetLaserMap.layout()
        # progressBar = QProgressDialog("Loading CSV files...", None, 0,
        #                               len(csv_files))
        # layout.addWidget(progressBar, 3, 0,  1, 2)
        # progressBar.setWindowTitle("Loading")
        # progressBar.setWindowModality(QtCore.Qt.WindowModal)
        # Loop through the CSV files and read them using pandas
        data_dict = {}
        i = 0
        for csv_file in csv_files:
            file_path = os.path.join(path, csv_file)
            df = pd.read_csv(file_path, engine='c')
            file_name = os.path.splitext(csv_file)[0].replace('.lame','')
            # Get the file name without extension
            data_dict[file_name] = df
            i += 1
            # progressBar.setValue(i)
        return data_dict

    def update_ratio_df(self,sample_id,analyte_1, analyte_2,norm):
        parameter = self.data[sample_id]['ratio_info'].loc[(self.data[sample_id]['ratio_info']['analyte_1'] == analyte_1) & (self.data[sample_id]['ratio_info']['analyte_2'] == analyte_2)]
        if parameter.empty:
            ratio_info = {'sample_id': self.sample_id, 'analyte_1':analyte_1, 'analyte_2':analyte_2, 'norm': norm,
                            'upper_bound':np.nan,'lower_bound':np.nan,'d_bound':np.nan,'use': True,'auto_scale': True}
            self.data[sample_id]['ratio_info'].loc[len(self.data[sample_id]['ratio_info'])] = ratio_info

            self.prep_data(sample_id, analyte_1=analyte_1, analyte_2=analyte_2)


    # -------------------------------
    # Plot Selector (tree) functions
    # -------------------------------
    def create_tree(self,sample_id = None):
        """Create plot selector tree

        Initializes ``MainWindow.treeView``.  The ``tree`` is intialized for each of the plot groups.
        ``Analyte`` its normalized counterpart are initialized with the full list of analytes.  Table
        data are stored in ``MainWindow.treeModel``.
        
        Parameters
        ----------
        sample_id : str
            Sample name, Defaults to None
        """
        if not self.data:
            treeView  = self.treeView
            treeView.setHeaderHidden(True)
            self.treeModel = QStandardItemModel()
            rootNode = self.treeModel.invisibleRootItem()
            self.analytes_items = StandardItem('Analyte', 11, True)
            self.norm_analytes_items = StandardItem('Analyte (normalized)', 11, True)
            self.ratios_items = StandardItem('Ratio', 11, True)
            self.norm_ratios_items = StandardItem('Ratio (normalized)', 11, True)
            self.histogram_items = StandardItem('Histogram', 11, True)
            self.correlation_items = StandardItem('Correlation', 11, True)
            self.geochemistry_items = StandardItem('Geochemistry', 11, True)
            self.multidim_items = StandardItem('Multidimensional Analysis', 11, True)
            self.calculated_items = StandardItem('Calculated Map', 11, True)

            rootNode.appendRows([self.analytes_items, self.norm_analytes_items, self.ratios_items, self.norm_ratios_items,
                                self.histogram_items,self.correlation_items, self.geochemistry_items,
                                self.multidim_items, self.calculated_items])
            treeView.setModel(self.treeModel)
            treeView.expandAll()
            treeView.doubleClicked.connect(self.tree_double_click)
        elif sample_id:
            #self.analytes_items.setRowCount(0)
            sample_id_item = StandardItem(sample_id, 11)
            norm_sample_id_item = StandardItem(sample_id, 11)
            #histogram_sample_id_item = StandardItem(sample_id, 11)
            ratio_sample_id_item = StandardItem(sample_id, 11)
            norm_ratio_sample_id_item = StandardItem(sample_id, 11)
            for analyte in self.data[sample_id]['analyte_info'].loc[:,'analytes']:
                analyte_item = StandardItem(analyte)
                sample_id_item.appendRow(analyte_item)
                #histogram_item = StandardItem(analyte)
                #histogram_sample_id_item.appendRow(histogram_item)
                norm_item = StandardItem(analyte)
                norm_sample_id_item.appendRow(norm_item)
            self.analytes_items.appendRow(sample_id_item)
            #self.histogram_items.appendRow(histogram_sample_id_item)
            self.ratios_items.appendRow(ratio_sample_id_item)
            self.norm_ratios_items.appendRow(norm_ratio_sample_id_item)
            self.norm_analytes_items.appendRow(norm_sample_id_item)

            # print('\ncreate_tree: analyte_items')
            # print(self.analytes_items)
            # print('\n')
    
    def apply_sort(self, action, method=None):

        if method is None:
            method = action.text()
            self.sort_method = method

        # retrieve analyte_list
        self.analyte_list = self.data[self.sample_id]['analyte_info']['analytes']
        
        # sort analyte sort based on method chosen by user
        self.analyte_list = self.sort_analytes(method, self.analyte_list)
        
        # sort analyte dataframes in a self.data
        # Convert the 'analytes' column in DataFrame to a categorical type with the specified order
        self.data[self.sample_id]['analyte_info']['analytes'] = pd.Categorical(
            self.data[self.sample_id]['analyte_info']['analytes'],
            categories=self.analyte_list,
            ordered=True
        )
        
        # Sort the DataFrame by the 'analytes' column
        self.data[self.sample_id]['analyte_info'] = self.data[self.sample_id]['analyte_info'].sort_values('analytes')
        
        # Ensure all analytes in self.analyte_list are actually columns in the DataFrame
        # This step filters out any items in self.analyte_list that are not columns in the DataFrame
        columns_to_order = [analyte for analyte in self.analyte_list if analyte in self.data[self.sample_id]['raw_data'].columns]
        
        # Reorder the columns of the DataFrame based on self.analyte_list
        self.data[self.sample_id]['raw_data'][columns_to_order] = self.data[self.sample_id]['raw_data'][columns_to_order]
        
        self.data[self.sample_id]['processed_data'][columns_to_order] = self.data[self.sample_id]['processed_data'][columns_to_order]
        
        self.data[self.sample_id]['cropped_raw_data'][columns_to_order] = self.data[self.sample_id]['cropped_raw_data'][columns_to_order]

        self.data[self.sample_id]['norm'] = {key: self.data[self.sample_id]['norm'][key] for key in self.analyte_list if key in self.data[self.sample_id]['norm']}
         
        #self.update_tree(self.data[self.sample_id]['norm'])
        # Reorder tree items according to the new analyte list
        # Sort the tree branches
        self.sort_tree_branch(self.analytes_items, self.analyte_list)
        self.sort_tree_branch(self.norm_analytes_items, self.analyte_list)
        self.sort_tree_branch(self.ratios_items, self.analyte_list)
        self.sort_tree_branch(self.norm_ratios_items, self.analyte_list)
    
    def sort_tree_branch(self, branch, order_list):
        """Sorts a branch in ``MainWindow.treeView`` given an ordered list

        Sorts the branch given an ordered list, resulting from the user selection from the dropdown menu when ``MainWindow.toolButtonSortAnalyte`` is pushed.

        Parameters
        ----------
        branch : str
            Branch to sort leaf items
        order_list : list
            The desired order for the leaf items.
        """        
        #for i in range(branch.rowCount()):
        i = 0
        leaf = branch.child(i)

        # Create a list of tuples containing the row index and item reference
        item_list = [(i, leaf.takeChild(i)) for i in range(leaf.rowCount()-1,-1,-1)]

        item_list.sort(key=lambda x: order_list.index(x[1].text()) if x[1].text() in order_list else len(order_list))

        for i in range(len(item_list)-1,-1,-1):
            leaf.removeRow(i)

        for row, (original_index, item) in enumerate(item_list):
            leaf.insertRow(row, item)

        # # Sort this list based on the order_list ensuring that each item is found in the order_list
        # # If not found, it is placed at the end
        # item_list.sort(key=lambda x: order_list.index(x[1].text()) if x[1].text() in order_list else len(order_list))
        
        # # Move the items within the leaf to reflect the new order
        # # We move the items to the beginning in the order defined by the sorted list
        # #for i in range(len(item_list)):
        # #    leaf.removeRow(i)

        # for new_index, (original_index, item) in enumerate(item_list):
        #     leaf.insertRow(new_index, item)
        #     # if original_index != new_index:  # Check if item needs to be moved
        #     #     # Take the item out from its current position
        #     #     #taken_item = leaf.takeChild(original_index)
        #     #     # Insert the item at its new position
        #     #     #leaf.insertRow(new_index, taken_item)
        #     #     leaf.insertRow(new_index, item)
        #     #     if (original_index > new_index):
        #     #         leaf.removeRow(original_index+1)
        #     #     else:
        #     #         leaf.removeRow(original_index)

    def retrieve_plotinfo_from_tree(self, tree_index=None, tree=None, branch=None, leaf=None):
        """Gets the plot_info associated with a tree location
        
        Can recall the plot info given the index into the tree (top level group in ``Plot Selector``), or by the tree, branch, leaf location.
        
        Parameters
        ----------
        tree_index : QModelIndex
            Index into the ``Plot Selector`` tree items
        tree : str
            Top level of tree, categorized by the type of plots
        branch : str
            Associated with sample ID
        leaf : str
            Lowest level of tree, associated with an individual plot
        
        Returns
        -------
        dict
            Plot_info dictionary with plot widget and information about the plot construction
        """
        #print('retrieve_table_data')
        if tree_index is not None:
            tree = tree_index.parent().parent().data()
            branch = tree_index.parent().data()
            leaf = tree_index.data()

        item,item_flag = self.find_leaf(tree, branch, leaf)

        if not item_flag:
            return None, True

        if not item.isEnabled():
            return None, False

        # ----start debugging----
        # print(tree_index)
        # print('item')
        # print(tree+':'+branch+':'+leaf)
        # ----end debugging----

        plot_info = item.data(role=Qt.UserRole)

        # ----start debugging----
        # print(plot_info)
        # print('\nsuccessfully retrieved plot info\n')
        # ----end debugging----

        return plot_info, True

    def tree_double_click(self,tree_index):
        """Double-click on plot selector
        
        When the user double-clicks on the ``Plot Selector``, the stored plot is placed on the current canvas.

        Parameters
        ----------
        val : PyQt5.QtCore.QModelIndex
            Item selected in ``Plot Selector``
        """
        # get double-click result
        self.plot_info, flag = self.retrieve_plotinfo_from_tree(tree_index=tree_index)

        if not flag:
            return

        tree = tree_index.parent().parent().data()
        branch = tree_index.parent().data()
        leaf = tree_index.data()


        #print(tree+':'+branch+':'+leaf)

        if tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
            #current_plot_df = self.get_map_data(sample_id=level_2_data, field=level_3_data, field_type='Analyte')
            #self.create_plot(current_plot_df, sample_id=level_2_data, plot_type='analyte', analyte_1=level_3_data)
            # if leaf in self.plot_widget_dict[tree][branch].keys():
            #     widget_dict = self.plot_widget_dict[tree][branch][leaf]
            #     self.add_plotwidget_to_canvas(widget_dict['info'], view=widget_dict['view'], position=widget_dict['position'])
            self.initialize_axis_values(tree, leaf)
            style = self.styles['analyte map']
            self.set_style_widgets('analyte map', style)
            if self.plot_info:
                print('tree_double_click: add_plotwidget_to_canvas')
                self.add_plotwidget_to_canvas(self.plot_info)
                # updates comboBoxColorByField and comboBoxColorField comboboxes 
                self.update_fields(self.plot_info['sample_id'], self.plot_info['plot_type'],self.plot_info['field_type'], self.plot_info['field'])
                #update UI with auto scale and neg handling parameters from 'Analyte/Ratio Info'
                self.update_spinboxes(self.plot_info['sample_id'],self.plot_info['field'],self.plot_info['field_type'])
            else:
                # print('tree_double_click: plot_map_pg')
                if self.toolBox.currentIndex() not in [self.left_tab['sample'], self.left_tab['process'], self.left_tab['polygons'], self.left_tab['profile']]:
                    self.toolBox.setCurrentIndex(self.left_tab['sample'])


                # else:
                #     pass

                
                
                # if self.canvasWindow.currentIndex() == self.canvas_tab['sv']:
                #     self.plot_map_mpl(sample_id=branch, field_type=tree, field=leaf)
                # else:
                #     self.plot_map_pg(sample_id=branch, field_type=tree, field=leaf)

                # updates comboBoxColorByField and comboBoxColorField comboboxes and creates new plot
                self.update_fields(branch,'analyte map',tree, leaf, plot=True)
                #set styles

                #update UI with auto scale and neg handling parameters from 'Analyte/Ratio Info'
                self.update_spinboxes(sample_id=branch, field=leaf, field_type = tree)

        elif tree in ['Histogram', 'Correlation', 'Geochemistry', 'Multidimensional Analysis', 'Calculated Map']:
            if self.plot_info:
                self.add_plotwidget_to_canvas(self.plot_info)
                # updates comboBoxColorByField and comboBoxColorField comboboxes 
                self.update_fields(self.plot_info['sample_id'], self.plot_info['plot_type'],self.plot_info['field_type'], self.plot_info['field'])

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
                self.color_by_field_callback() # added color by field callback to update color field
            if field != self.comboBoxColorField.currentText():
                self.comboBoxColorField.setCurrentText(field)
                self.color_field_callback(plot)
            

    def update_tree(self, analyte_df, norm_update=False):
        """Updates plot selector list and data

        Updates the tree with the list of analytes in ``MainWindow.data[sample_id]['norm']`` and background color
        to light yellow for analytes used in analyses.
        
        Parameters
        ----------
        analyte_df : pandas.DataFrame
            Data frame with information about analytes, scales, limits and use in analysis
        norm_update : bool
            Flag for updating norm list. Defaults to False
        """
        #print('update_tree')
        if self.sample_id == '':
            return

        if darkdetect.isDark():
            hexcolor = '#696880'
        else:
            hexcolor = '#FFFFC8'

        sample_id = self.sample_id

        # Un-highlight all leaf in the trees
        self.unhighlight_tree(self.ratios_items)
        self.unhighlight_tree(self.analytes_items)

        self.data[sample_id]['analyte_info'].loc[:,'use'] = False
        if not (len(analyte_df.keys()) > 0):
            return

        for analyte, norm in analyte_df.items():
            if '/' in analyte:
                analyte_1, analyte_2 = analyte.split(' / ')
                self.update_ratio_df(self.sample_id, analyte_1, analyte_2, norm)
                ratio_name = f"{analyte_1} / {analyte_2}"
                # Populate ratios_items if the pair doesn't already exist
                item1,check = self.find_leaf('Ratio', branch = self.sample_id, leaf = ratio_name)

                if norm_update:
                    item1,check = self.find_leaf('Ratio', branch = self.sample_id, leaf = ratio_name)
                    item2,check = self.find_leaf('Ratio (normalized)', branch = self.sample_id, leaf = ratio_name)
                # else:
                #     item1,check = self.find_leaf('Ratio', branch = self.sample_id, leaf = ratio_name)
                #     item2,check = self.find_leaf('Ratio (normalized)', branch = self.sample_id, leaf = ratio_name)

                if not check: #if ratio doesn't exist
                    # ratio
                    child_item = StandardItem(ratio_name)
                    # child_item.setBackground(QBrush(QColor(hexcolor)))
                    item1.appendRow(child_item)

                    # ratio normalized
                    # check if ratio can be normalized (note: normalization is not handled here)
                    refval_1 = self.ref_chem[re.sub(r'\d', '', analyte_1).lower()]
                    refval_2 = self.ref_chem[re.sub(r'\d', '', analyte_2).lower()]
                    ratio_flag = False
                    if (refval_1 > 0) and (refval_2 > 0):
                        ratio_flag = True
                    #print([analyte, refval_1, refval_2, ratio_flag])

                    child_item2 = StandardItem(ratio_name)
                    # child_item2.setBackground(QBrush(QColor(hexcolor)))
                    # if normization cannot be done, make text italic and disable item
                    if not ratio_flag:
                        font = child_item2.font()
                        font.setItalic(True)
                        child_item2.setFont(font)
                        child_item2.setEnabled(False)
                    item2.appendRow(child_item2)
                # else:
                #     item1.setBackground(QBrush(QColor(hexcolor)))
                #     item2.setBackground(QBrush(QColor(hexcolor)))

            else: #single analyte
                analyte_1 = analyte
                analyte_2 = None
                item,check = self.find_leaf('Analyte', branch = sample_id, leaf = analyte)
                # if norm_update:
                #     item,check = self.find_leaf('Analyte (normalized)', branch = sample_id, leaf = analyte)
                # else:
                #     item,check = self.find_leaf('Analyte', branch = sample_id, leaf = analyte)

                item.setBackground(QBrush(QColor(hexcolor)))

                self.data[self.sample_id]['analyte_info'].loc[(self.data[sample_id]['analyte_info']['analytes']==analyte),'use'] = True

            if norm_update: #update if analytes are returned from analyte selection window
                self.update_norm(self.sample_id, norm, analyte_1=analyte_1, analyte_2=analyte_2)

    def add_tree_item(self, plot_info):
        """Updates plot selector list and adds plot information data to tree item
        
        Parameters
        ----------
        plot_info : dict
            Plot related data (including plot widget) to tree item associated with the plot.
        """
        if plot_info is None:
            return

        #print('add_tree_item')
        sample_id = plot_info['sample_id']
        leaf = plot_info['plot_name']
        tree = plot_info['tree']
        if tree == 'Calculated':
            tree= 'Calculated Map'

        tree_items = self.get_tree_items(tree)
        
        
        # Ensure there's a persistent reference to items.
        # if not hasattr(self, 'item_refs'):
        #     self.item_refs = {}  # Initialize once
        
        #check if leaf is in tree
        item,check = self.find_leaf(tree=tree, branch=sample_id, leaf=leaf)
        # sample id item and plot item both dont exist
        if item is None and check is None:
            # create new branch for sample id
            sample_id_item = StandardItem(sample_id, 11)

            # create new leaf item
            plot_item = StandardItem(leaf)

            # store plot dictionary in leaf
            plot_item.setData(plot_info, role=Qt.UserRole)

            sample_id_item.appendRow(plot_item)
            tree_items.appendRow(sample_id_item)
            
            # Store references
            # self.item_refs[(tree, sample_id)] = sample_id_item
            # self.item_refs[(tree, sample_id, leaf)] = plot_item
            
        # sample id item exists plot item doesnt exist
        elif item is not None and not check:
            # create new leaf item
            plot_item = StandardItem(leaf)

            # store plot dictionary in leaf
            plot_item.setData(plot_info, role=Qt.UserRole)

            #item is sample id item (branch)
            item.appendRow(plot_item)
            
            # Update reference
            # self.item_refs[(tree, sample_id, leaf)] = plot_item

        # sample id item exists and plot item exists
        elif item is not None and check: 
            # store plot dictionary in tree
            item.setData(plot_info, role=Qt.UserRole)
            
            # self.item_refs[(tree, sample_id, leaf)] = item
 
    def unhighlight_tree(self, tree):
        """Reset the highlight of all items in the tree.
        
        Parameters
        ----------
        tree : str
            Highest level of tree with branches to unhighlight
        """
        #bgcolor = tree.background().color()
        if darkdetect.isDark():
            bgcolor = '#1e1e1e'
        else:
            bgcolor = '#ffffff'

        for i in range(tree.rowCount()):
            branch_item = tree.child(i)
            # branch_item.setBackground(QBrush(QColor(bgcolor)))  # white or any default background color
            for j in range(branch_item.rowCount()):
                leaf_item = branch_item.child(j)
                leaf_item.setBackground(QBrush(QColor(bgcolor)))  # white or any default background color

    def get_tree_items(self, tree):
        """Returns items associated with the specified tree
        
        Parameters
        ----------
        tree : str
            Name of tree in ``MainWindow.treeView``

        Returns
        -------
        Qt.AbstractModelItem
            The set of items under *tree*
        """
        match tree:
            case 'Analyte':
                return  self.analytes_items
            case 'Analyte (normalized)':
                return self.norm_analytes_items
            case 'Ratio':
                return self.ratios_items
            case 'Ratio (normalized)':
                return self.norm_ratios_items
            case 'Histogram':
                return self.histogram_items
            case 'Correlation':
                return self.correlation_items
            case 'Geochemistry':
                return self.geochemistry_items
            case 'Multidimensional Analysis':
                return self.multidim_items
            case 'Calculated Map':
                return self.calculated_items

    def find_leaf(self, tree, branch, leaf):
        """Get a branch or leaf item from treeView
        
        Parameters
        ----------
        tree : str
            Highest level of tree, ``plot_info['tree']``
        branch : str
            Middle tree level, ``plot_info['sample_id']``
        leaf : str
            Lowest level of tree, ``plot_info['plot_name']``

        Returns
        -------
        tuple
            (item, flag), item is a branch (``flag==False``) or leaf (``flag==True``), if item neither return is ``(None, None)``.
        """
        #print('find_leaf')
        #print(f'{tree} : {branch} : {leaf}')
        tree_items = self.get_tree_items(tree)

        #Returns leaf_item & True if leaf exists, else returns branch_item, False
        if tree_items:
            for index in range(tree_items.rowCount()):
                branch_item = tree_items.child(index)
                if branch_item.text() == branch:
                    for index in range(branch_item.rowCount()):
                        leaf_item = branch_item.child(index)
                        if leaf_item.text() == leaf:
                            return (leaf_item, True)
                    return (branch_item,False)
        return (None,None)

    def clear_tree_data(self, tree):
        """Removes item data from all items in a given tree
        
        Parameters
        ----------
        tree : str
            Name of tree in ``MainWindow.treeView``
        """
        tree_items = self.get_tree_items(tree)

        def clear_item_data(item):
            """Recursively clear data from the item and its children"""
            item.setData(None, role=Qt.UserRole)
            for index in range(item.rowCount()):
                child_item = item.child(index)
                clear_item_data(child_item)
        
        for index in range(tree_items.rowCount()):
            branch_item = tree_items.child(index)
            clear_item_data(branch_item)

    # -------------------------------
    # Calculator
    # -------------------------------
    def calc_set_add_formula(self):
        """Sets whether to add a new function

        Sets ``MainWindow.add_formula`` to ``True``, a flag used by ``MainWindow.calculate_new_field`` to determine
        whether to add an item to ``MainWindow.comboBoxCalcFormula``.
        """        
        self.add_formula = True

    def calc_help(self):
        """Loads the help webpage associated with the calculator in the Help tab"""
        filename = os.path.join(BASEDIR,"docs/build/html/custom_fields.html")

        self.lineEditBrowserLocation.setText(filename)

        if filename:
            # Load the selected HTML file into the QWebEngineView
            self.browser.setUrl(QUrl.fromLocalFile(filename))
        
    def calc_insert_operator(self, operator):
        """Inserts an operator into the calculator

        When the user pushes an operator button on the calculator, *operator* is inserted 
        into ``MainWindow.textEditCalcScreen``.

        Parameters
        ----------
        operator : str
            Inserts operators from calculator
        """        
        print('calc_insert_operator')
        cursor = self.textEditCalcScreen.textCursor()
        cursor.insertText(operator)
    
    def calc_insert_function(self, function):
        """Inserts a function into the calculator

        When the user pushes a function button on the calculator, *operator* is inserted 
        into ``MainWindow.textEditCalcScreen``.  The ``case()`` function inserts ``(cond, expr)``
        as both a condition and expression are required to compute.  

        Parameters
        ----------
        operator : str
            Inserts operators from calculator
        """        
        print('calc_insert_function')
        cursor = self.textEditCalcScreen.textCursor()
        if cursor.hasSelection():
            cursor.insertText(f"{function}({cursor.selectedText()})")
            # add semicolon to end of case and otherwise functions
            if function in ['case', 'otherwise']:
                cursor.insertText(f"; ")
        else:
            # case should have conditional and expression
            if function == 'case':
                cursor.insertText(f"{function}(cond, expr); ")
            else:
                cursor.insertText(f"{function}()")
                # if otherwise add semicolon to end
                if function == 'otherwise':
                    cursor.insertText(f"; ")
    
    def calc_add_field(self):
        """Adds the selected field to the calculator

        Adds the selected field as ``{field_type.field}``.  If the field is normalized,
        a ``_N`` is added to the end of the field name, i.e., ``{field_type.field_N}``.
        """        
        # get field type and name
        field_type = self.comboBoxCalcFieldType.currentText()
        field = self.comboBoxCalcField.currentText()

        # combine name in calculator style
        match field_type:
            case 'Analyte (normalized)':
                fieldname = f'Analyte.{field}_N'
            case 'Ratio (normalized)':
                fieldname = f'Ratio.{field}_N'
            case 'Calculated':
                fieldname = f'Calculated.{field}'
            case _:
                if field != '':
                    fieldname = f'{field_type}.{field}'

        # add to calculation screen
        cursor = self.textEditCalcScreen.textCursor()
        cursor.insertText(f"{{{fieldname}}}")

    #def calc_clear_text(self):
    #    self.textEditCalcScreen.clear()

    def calc_load_dict(self):
        """Loads saved calculated fields

        Loads the file saved in ``self.calc_filename``, unless the file is overridden by user preferences.  The file
        should be formatted as *name: expression*.  The expression may contain mulitple *case(cond, expr)* separated by a ``;``.
        """        
        self.calc_dict = {}
        try:
            with open(self.calc_filename, 'r') as file:
                # read file with name: expression
                for line in file:
                    line = line.strip()  # Remove leading/trailing whitespace, including newline characters
                    if ':' in line:  # Check if the line contains a ':'
                        name, expression = line.split(':', 1)  # Split only on the first ':'
                        name = name.strip()  # Remove any leading/trailing whitespace from name
                        expression = expression.strip()  # Remove any leading/trailing whitespace from expression
                        self.calc_dict[name] = expression

                # update comboBoxCalcFormula
                self.comboBoxCalcFormula.clear()
                name_list = list(self.calc_dict.keys())
                self.comboBoxCalcFormula.addItems(name_list)
        except FileNotFoundError as e:
            # Return an empty dictionary if the file does not exist
            QMessageBox.warning(None,'Warning','Could not load custom calculated fields.\n Starting with empty custom field dictionary.')

    def calc_delete_formula(self):
        """Deletes a previously stored formula
        
        Removes the formula from ``MainWindow.comboBoxCalcFormula``, the file given by ``MainWindow.calc_filename`` and 
        ``MainWindow.data[MainWindow.sample_id]['computed_data']['Calculated']``.
        """
        func = 'calc_delete_formula'

        # get name of formula
        name = self.comboBoxCalcFormula.currentText()

        # remove name from comboBoxCalcFormula
        self.comboBoxCalcFormula.removeItem(self.comboBoxCalcFormula.currentIndex())

        # remove line with name from calculator formula file
        try:
            # Read all lines from the file
            with open(self.calc_filename, 'r') as file:
                lines = file.readlines()

            # Filter out the lines that contain the name_to_remove
            lines_to_keep = [line for line in lines if not line.startswith(f'{name}:')]

            # Write the remaining lines back to the file
            with open(self.calc_filename, 'w') as file:
                file.writelines(lines_to_keep)

        except FileNotFoundError as e:
            err = 'could not find file'
            self.calc_error(func, err, e)
            pass

        # remove field from Calculated dataframe
        self.data[self.sample_id]['computed_data']['Calculated'].drop([name], axis=1, inplace=True)
    
    def calc_load_formula(self):
        """Loads a predefined formula to use in the calculator"""        
        name = self.comboBoxCalcFormula.currentText()

        self.textEditCalcScreen.clear()
        self.textEditCalcScreen.setText(self.calc_dict[name])

        self.add_formula = False
        
    def calc_parse(self, txt=None):
        """Prepares expression for calculating a custom field 

        Parses ``MainWindow.textEditCalcScreen`` to produce an expression that can be evaluated.
        """
        func = 'calc_parse'

        # Get text 
        if txt is None:
            txt = self.textEditCalcScreen.toPlainText()
            txt = ''.join(txt.split())
        print(txt)

        txt = txt.replace('^','**')
        txt = txt.replace('log(','log10(')
        txt = txt.replace('ln(','log(')
        txt = txt.replace('grad(','gradient(')

        cond = []
        expr = []
        if ('case' in txt) or ('otherwise' in txt):
            cases = txt.split(';')
            # if last case includes a ';', there will be an extra blank in cases list, remove it
            if cases[-1] == '':
                cases.pop()

            # deal with otherwise first as it will be used to set all the values and then cases will reset them
            idx = [i for i, j in enumerate(['foo', 'bar', 'baz']) if j == 'bar']
            if idx is not None:
                cond[0] = 'any'
                expr[0] = cases.index(idx)[10:-1]
                cases.pop(idx)

            for c in cases:
                c = c[5:-1]
                # separate conditional from expression
                try:
                    cond_temp, expr_temp = c.split(',')
                except Exception as e:
                    err = "a case statement must include a conditional and an expression separated by a comma, ',' and end with a ';'."
                    self.calc_error(func, err, e)
                    return None, None

                # parse conditional and expression
                _, cond_temp = self.calc_parse(txt=cond_temp)
                _, expr_temp = self.calc_parse(txt=expr_temp)

                # append list
                cond = cond + cond_temp
                expr = expr + expr_temp

            return cond, expr
        else:
            cond = None

        if txt.count('(') != txt.count(')'):
            'mismatched parentheses in expr'
            self.calc_error(func, err, '')
            return None

        if txt.count('{') != txt.count('}'):
            'mismatched braces in expr'
            self.calc_error(func, err, '')
            return None
        
        field_list = re.findall(r'\{.*?\}', txt)
        print(field_list)
        var = {}
        for field_str in field_list:
            field_str = field_str.replace('{','')
            field_str = field_str.replace('}','')
            try:
                field_type, field = field_str.split('.')
            except Exception as e:
                err = "field type and field must be separated by a '.'"
                self.calc_error(func, err, e)
            if field[-2:] == '_N':
                field = field[:-2]
                if field_type in ['Analyte', 'Ratio']:
                    field_type = f"{field_type} (normalized)"

            if field in list(var.keys()):
                continue

            df = self.get_map_data(self.sample_id, field, field_type)
            var.update({field: df['array']})

            txt = txt.replace(f"{{{field_str}}}", f"{field}")
        
        if len(var) == 0:
            var = None
        expr = [txt, var]

        print(expr)

        return cond, expr

    def calculate_new_field(self, save=False):
        """Calculates a new field from ``MainWindow.textEditCalcScreen``

        When ``MainWindow.toolButtonCalculate`` is clicked, ...

        If ``save == True``, the formula to ``resources/app_data/calculator.txt`` file so it can be recalled
        and used at a future time or in another sample.  Pushing ``MainWindow.toolButtonCalcSave``,
        opens a dialog prompting the user to input the name for the newly calculated field.

        Parameters
        ----------
        save: bool, optional
            Determines whether to save upon successful calculation, by default ``False``
        """
        func = 'calculate_new_field'

        # open dialog to get new field
        if self.add_formula:
            new_field, ok = QInputDialog.getText(self, 'Save expression', 'Enter custon field name:')
            if ok:
                # check for valid field name
                if self.partial_match_in_list(['_N',':'],new_field):
                    err = "new field name cannot have an '_N' or ':' in the name"
                    self.calc_error(func, err, '')
                    ok = False
                    
            if not ok:
                return
        else:
            new_field = self.comboBoxCalcFormula.currentText()

        # parse the expression
        cond, expr = self.calc_parse()
        if cond is None:    # no conditionals
            result = self.calc_evaluate_expr(expr[0], val_dict=expr[1])
            if result is None:
                return
            self.data[self.sample_id]['computed_data']['Calculated'][new_field] = result
        elif expr is None:
            err = "expr returned 'None' could not evaluate formula. Check syntax."
            self.calc_error(func, err, '')
            return
        else:   # conditionals
            # start with empty dataFrame
            result = pd.DataFrame({new_field: np.nan*np.zeros_like(self.data[self.sample_id]['computed_data']['Calculated'].iloc[:,0])})

            # loop over cases (cond, expr)
            for i in range(0,len(cond),2):
                if (i == 0) and (cond[i] == 'any'):
                    try:
                        res = self.calc_evaluate_expr(expr[0], val_dict=expr[1])
                    except Exception as e:
                        err = "could not evaluate otherwise expression. Check syntax."
                        self.calc_error(func, err, e)
                        return
                    self.data[self.sample_id]['computed_data']['Calculated'][new_field] = result
                    continue

                # conditional yields boolean numpy.ndarray keep
                try:
                    keep = self.calc_evaluate_expr(cond[i], val_dict=cond[i+1])
                except Exception as e:
                    err = "could not evaluate conditional statement. Check syntax."
                    self.calc_error(func, err, e)
                    return

                # check for missing or incorrectly type for conditional
                if keep is None:
                    err = 'conditional did not return boolean result.'
                    self.calc_error(func, err, '')
                    return
                elif not isinstance(keep, np.ndarray):
                    if not np.issubdtype(keep.dtype, np.bool_):
                        err = 'conditional did not return boolean result.\n  Did you swap the conditional and expression?'
                        self.calc_error(func, err, '')
                        return

                # check for size error
                if keep.shape[0] != result.shape[0]:
                    err = 'the conditional size does not match the size of expected computed array.'
                    self.calc_error(func, err, '')
                    return

                # compute expression for indexes where keep==`True`
                try:
                    res = self.calc_evaluate_expr(expr[i], val_dict=expr[i+1], keep=keep)
                except Exception as e:
                    err = "could not evaluate expression. Check syntax."
                    self.calc_error(func, err, e)
                    return

                if res is None:
                    err = 'the expression failed to return an array of values.'
                    self.calc_error(func, err, '')
                    return

                result.loc[keep,new_field] = res

            self.data[self.sample_id]['computed_data']['Calculated'][new_field] = result

        # update comboBoxCalcFormula
        self.comboBoxCalcFormula.addItem(new_field)
        self.comboBoxCalcFormula.setCurrentText(new_field)

        if self.comboBoxCalcFieldType.currentText == 'Calculated':
            self.update_field_combobox(self.comboBoxCalcFieldType, self.comboBoxCalcField)

        # get the formula and add to custom field dictionary
        formula = self.textEditCalcScreen.toPlainText()
        self.calc_dict.update({'field':new_field, 'expr':formula})

        # append calculator file
        if save:
            try:
                with open(self.calc_filename, 'a') as file:
                    file.write(f"{new_field}: {formula}\n")
            except Exception as e:
                # throw a warning that nam
                err = 'could not save expression, problem with write.'
                self.calc_error(func, err, e)
                return

    def calc_evaluate_expr(self, expr, val_dict=None, keep=None):
        """Evaluates an expression and returns the result

        Parameters
        ----------
        expr : string
            Expression to be evaluated.  The expression can be a conditional expression, which results
            in returning a np.ndarray of bool, otherwise, generally np.ndarray of float
        val_dict : dict
            Dictionary with variable names as the key and values taken from the data, generally np.ndarray, by default ``None``
        keep : np.ndarray of bool or None, optional
            An array of True/False values that are used to evaluate the expression of limited values,
            i.e., generally when cases are involved.

        Returns
        -------
        np.ndarray of float or bool
            Result of evaluated expression.
        """        
        func = 'calc_evaluate_expr'
        try:
            if val_dict is None:
                result = ne.evaluate(expr)
            else:
                result = ne.evaluate(expr, local_dict=val_dict)
            self.labelCalcMessage.setText("Success")
            if keep is None or result.ndim == 0:
                return result
            else:
                return result[keep]
        except Exception as e:
            err = 'unable to evaluate expression.'
            self.calc_error(func, err, e)
            return None

    def calc_error(self, func, err, addinfo):
        """Raise a calculator-related error

        Parameters
        ----------
        func : str
            Function that threw the error
        err : str
            Error string
        addinfo : str
            Additional info (generally exception raised)
        """        
        self.labelCalcMessage.setText(f"Error: {err}")
        QMessageBox.warning(self,'Calculation Error',f"Error: {err}\n\n({func}) {addinfo}")

        

    # -------------------------------
    # Notes functions
    # -------------------------------
    def add_menu(self, menu_items, menu_obj):
        """Adds items to a context menu

        :param menu_items: Names of the menu text to add
        :type menu_items: list
        :param menu_obj: context menu object
        :type menu_obj: QMenu
        """
        for item in menu_items:
            action = menu_obj.addAction(item)
            action.setIconVisibleInMenu(False)

    def save_notes_file(self):
        """Saves notes to an *.rst file

        Autosaves the notes to a file ``[sample_id].rst``
        """
        if self.notes_file is None:
            return

        self.statusbar.showMessage('Saving notes...')

        # write file
        with open(self.notes_file,'w') as file:
            file.write(str(self.textEditNotes.toPlainText()))

        self.statusbar.clearMessage()

    def notes_add_image(self):
        """Adds placeholder image to notes

        Uses the reStructured Text figure format
        """
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setNameFilter("Image Files (*.jpg *.png *.tif)")
        filenames = []

        if dialog.exec_():
            filenames = dialog.selectedFiles()
        else:
            return

        for fn in filenames:
            self.textEditNotes.insertPlainText(f"\n\n.. figure:: {fn}\n")
            self.textEditNotes.insertPlainText("    :align: center\n")
            self.textEditNotes.insertPlainText("    :alt: alternate text\n")
            self.textEditNotes.insertPlainText("    :width: 150mm\n")
            self.textEditNotes.insertPlainText("\n    Caption goes here.\n")

    def add_header_line(self, level):
        """Formats a selected line as a header

        Places a symbol consistent with the heading level below the selected text line.

        Parameters
        ----------
        level : str
            The header level is determined from a context menu associated with ``MainWindow.toolButtonNotesHeading``
        """
        # define symbols for heading level
        match level:
            case 'H1':
                symbol = '*'
            case 'H2':
                symbol = '='
            case 'H3':
                symbol = '-'

        # Get the current text cursor
        cursor = self.textEditNotes.textCursor()

        # Get the current line number and position
        line_number = cursor.blockNumber()

        # Move the cursor to the end of the selected line
        cursor.movePosition(QTextCursor.EndOfLine)
        #cursor.movePosition(QTextCursor.NextBlock)

        # Insert the line of "="
        cursor.insertText('\n' + f'{symbol}' * (cursor.block().length() - 1))

    def format_note_text(self, style):
        """Formats the text

        Formats selected text as bold, italic or literal in restructured text format.

        Parameters
        ----------
        style : str
            Type of formatting
        """
        cursor = self.textEditNotes.textCursor()
        selected_text = cursor.selectedText()

        match style:
            case 'italics':
                modified_text = f"*{selected_text}*"
            case 'bold':
                modified_text = f"**{selected_text}**"
            case 'literal':
                modified_text = f"``{selected_text}``"

        cursor.insertText(modified_text)

    def add_info_note(self, infotype):
        """Adds preformatted notes

        Parameters
        ----------
        infotype : str
            Name of preformatted information
        """
        match infotype:
            case 'Sample info':
                self.textEditNotes.insertPlainText(f'**Sample ID: {self.sample_id}**\n')
                self.textEditNotes.insertPlainText('*' * (len(self.sample_id) + 15) + '\n')
                self.textEditNotes.insertPlainText(f'\n:Date: {datetime.today().strftime("%Y-%m-%d")}\n')
                # width/height
                # list of all analytes
                self.textEditNotes.insertPlainText(':User: Your name here\n')
                pass
            case 'List analytes used':
                fields = self.get_field_list()
                self.textEditNotes.insertPlainText('\n\n:analytes used: '+', '.join(fields))
            case 'Current plot details':
                text = ['\n\n:plot type: '+self.plot_info['plot_type'],
                        ':plot name: '+self.plot_info['plot_name']+'\n']
                self.textEditNotes.insertPlainText('\n'.join(text))
            case 'Filter table':
                filter_table = self.data[self.sample_id]['filter_info']
                rst_table = self.to_rst_table(filter_table)

                self.textEditNotes.insertPlainText(rst_table)
            case 'PCA results':
                if not self.pca_results:
                    return
                analytes = self.data[self.sample_id]['analyte_info'].loc[:,'analytes'].values
                analytes = np.insert(analytes,0,'lambda')

                matrix = np.vstack([self.pca_results.explained_variance_ratio_, self.pca_results.components_])

                header = self.data[self.sample_id]['computed_data']['PCA Score'].columns[2:].to_numpy()

                #print(type(analytes))
                #print(type(header))
                #print(type(matrix))
                self.add_table_note(matrix, row_labels=analytes, col_labels=header)
            case 'Cluster results':
                if not self.cluster_results:
                    return

    def add_table_note(self, matrix, row_labels=None, col_labels=None):
        """Convert matrix to restructured text

        Adds a table to the note tab, including row lables and column headers.

        Parameters
        ----------
        matrix : 2D array
            Data for printing
        row_labels : str, optional
            Row labels
        col_labels : str, optional
            Column header
        """
        if matrix is None:
            return ''

        #matrix = self.convert_to_string(matrix)
        matrix = fmt.oround_matrix(matrix, order=3)

        # Add row labels to the matrix if provided
        if row_labels is not None:
            matrix = np.column_stack((row_labels, matrix))
            if col_labels is not None:
                col_labels = np.insert(col_labels,0,' ')

        # Add column headings to the matrix if provided
        if col_labels is not None:
            matrix = np.vstack((col_labels, matrix))

        # Calculate column widths
        col_widths = np.max([np.vectorize(len)(matrix.astype(str))], axis=0)

        # Generate the reST table
        table = ""
        for i, row in enumerate(matrix):
            table += "|"
            for col, width in zip(row, col_widths[i,:]):
                table += f" {col:{int(width)}} |"
            table += "\n"

        self.textEditNotes.insertPlainText(table)


    # CSV tables
    # .. csv-table:: Table Title
    #     :file: CSV file path and name
    #     :widths: 30, 70       # percentage widths
    #     :header-rows: 1

    #def convert_to_string(self, array):
    #    return np.array2string(array, formatter={'all': lambda x: f'{x:02f}'})

    def save_notes_to_pdf(self):
        """Converts notes *.rst file to *.pdf"""
        # save note file first to ensure all changes have been recorded
        self.save_notes_file()

        # replace all spaces with \ space
        filename = self.notes_file
        try:
            pdf_file_path = filename.replace('.rst', '.pdf')

            # use rst2pdf on the command line to export the file as a pdf
            #os.system(f"cat {filename} | rst2pdf -o --use-floating-images {os.path.splitext(filename)[0]+'.pdf'}")

            with open(filename, 'r') as file:
                rst_content = file.read()
            
            pdf = RstToPdf()
            pdf_content = pdf.createPdf(text=rst_content, output=pdf_file_path)
            
            #with open(pdf_file_path, 'wb') as pdf_file:
            #    pdf_file.write(pdf_content)
            
            self.statusBar.showMessage("PDF successfully generated...")
        except Exception as e:
            # if it doesn't work
            QMessageBox.warning(self,"Error", "Could not save to pdf.\n"+e)

    def to_rst_table(self, df):
        """Converts a Pandas DataFrame to a reST table string.

        Parameters
        ----------
        df : pandas.DataFrame
            Data table to convert to restructured text

        Returns
        -------
        str
            Table in restructred text format
        """
        def rst_row(row):
            return ' '.join(f'{str(item):^10}' for item in row)

        # Extracting column names and data as lists
        columns = df.columns.tolist()
        data = df.values.tolist()
        
        # Creating reST table components
        header = rst_row(columns)
        separator = ' '.join(['-'*10]*len(columns))
        rows = [rst_row(row) for row in data]
        
        # Combining components into the reST table format
        rst_table = '\n'.join([header, separator] + rows)
        return rst_table

    def open_browser(self):
        """Creates and opens a browser in the bottom tabWidget

        A browser for the LaME documentation.  It can access some external sites, but the browser is primarily for help data.
        """        
        # Open a file dialog to select a local HTML file
        # Create a QWebEngineView widget
        self.browser = WebEngineView(self)
        self.verticalLayoutBrowser.addWidget(self.browser)

        #file_name, _ = QFileDialog.getOpenFileName(self, "Open HTML File", "", "HTML Files (*.html *.htm)")
        self.browser_home_callback()

    def browser_home_callback(self):
        """The browser returns to the documentation index.html file"""        
        filename = os.path.join(BASEDIR,"docs/build/html/index.html")

        self.lineEditBrowserLocation.setText(filename)

        if filename:
            # Load the selected HTML file into the QWebEngineView
            self.browser.setUrl(QUrl.fromLocalFile(filename))
        
    def browser_location_callback(self, location=None):
        """Tries to load the page given in ``MainWindow.lineEditBrowserLocation``

        Parameters
        ----------
        location : str, optional
            Name of webpage (excluding base directory and .html)
        """
        if not location:
            location = self.lineEditBrowserLocation.text()
        else:
            location = os.path.join(BASEDIR,"docs/build/html/"+location+".html")

        self.lineEditBrowserLocation.setText(location)

        try:
            if location:
                self.browser.setUrl(QUrl.fromLocalFile(location))
        except:
            pass
            #self.browser.setUrl(QUrl(os.path.abspath('docs/build/html/404.html')))

    def toggle_help_mode(self):
        """Toggles help mode

        Toggles ``MainWindow.actionHelp``, when checked, the cursor will change so indicates help tool is active.
        """        
        if self.actionHelp.isChecked():
            self.setCursor(Qt.WhatsThisCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def eventFilter(self, source, event):
        """Event filter to capture mouse press events

        If help mode is active, the clicked widget opens the help browser.

        Parameters
        ----------
        source : any
            Calling application or dialog
        event : 
            Mouse click.

        Returns
        -------
        bool
            ``True`` if help is opened, otherwise ``False``
        """        
        if event.type() == QEvent.MouseButtonPress and self.actionHelp.isChecked():
            self.actionHelp.setChecked(False)
            self.setCursor(Qt.ArrowCursor)
            match source:
                case self.centralwidget | self.canvasWindow:
                    self.browser_location_callback('center_pane')
                case self.toolBox | self.dockWidgetLeftToolbox:
                    self.browser_location_callback('left_toolbox')
                case self.toolBoxTreeView | self.dockWidgetRightToolbox:
                    self.browser_location_callback('right_toolbox')
                case self.dockWidgetBottomTabs | self.tabWidget:
                    self.browser_location_callback('lower_tabs')
                case _:
                    return False
            self.tabWidget.setCurrentIndex(self.bottom_tab['help'])
            return True
        return super().eventFilter(source, event)


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

    def sort_analytes(self, method, analytes, order = 'd'):
        """Sort the analyte list

        Sorting the analyte list can make data selection easier, or improve the pattern of correlations and PCA vectors.

        Parameters
        ----------
        method : str
            Method used for sorting.  Options include ``'alphabetical'``, ``'atomic number'``, ``'mass'``, ``'compatibility'``, and ``'radius'``.
        analytes : list
            List of analytes to sort
        order : str, optional
            Sets order as ascending (``'a'``) or decending (``'d'``), by default 'd'

        Returns
        -------
        list
            Sorted analyte list.
        """        
        # Extract element symbols and any mass numbers if present
        parsed_analytes = []
        for analyte in analytes:
            # Extracts the element symbol and mass if available (e.g., "Al27" -> ("Al", 27))
            match = re.match(r"([A-Za-z]+)(\d*)", analyte)
            element_symbol = match.group(1) if match else analyte
            mass_number = int(match.group(2)) if match.group(2) else None
            parsed_analytes.append((element_symbol, mass_number))
        
        # Convert to DataFrame for easier manipulation
        df_analytes = pd.DataFrame(parsed_analytes, columns=['element_symbol', 'mass'])

        # Merge with sort_data for additional information
        df_analytes = df_analytes.merge(self.sort_data, on='element_symbol', how='left')

        # Sort based on the selected method
        match method:
            case 'alphabetical':
                df_analytes.sort_values(by='element_symbol', ascending=True, inplace=True)
            case 'atomic number':
                df_analytes.sort_values(by='atomic_number', ascending=True, inplace=True)
            case 'mass':
                # Use provided mass or average mass if not available
                df_analytes['computed_mass'] = df_analytes['mass'].fillna(df_analytes['average_mass'])
                df_analytes.sort_values(by='computed_mass', ascending=True, inplace=True)
            case 'compatibility':
                df_analytes.sort_values(by='order', ascending=False, inplace=True)
            case 'radius':
                df_analytes.sort_values(by='radius1', ascending=True, inplace=True)
            
        analytes = df_analytes['element_symbol'] + df_analytes['mass'].astype(str)
        # Return the sorted list of analytes as (symbol, mass) tuples
        return analytes.to_list()

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
    # Unclassified functions
    # -------------------------------
    def switch_view_mode(self, view_mode):
        if view_mode > 2:
            view_mode = 0
        self.view_mode = view_mode

        match self.view_mode:
            case 0: # auto
                if darkdetect.isDark():
                    self.set_dark_theme()
                else:
                    self.set_light_theme()

                self.actionViewMode.setIcon(QIcon(os.path.join(ICONPATH,'icon-sun-and-moon-64.svg')))
                self.actionViewMode.setIconText('Auto')
            case 1: # dark
                self.set_dark_theme()
            case 2: # light
                self.set_light_theme()

    def set_dark_theme(self):
        ss = load_stylesheet('dark.qss')
        app.setStyleSheet(ss)

        self.actionViewMode.setIcon(QIcon(os.path.join(ICONPATH,'icon-moon-64.svg')))
        self.actionViewMode.setIconText('Dark')

        self.actionSelectAnalytes.setIcon(QIcon(os.path.join(ICONPATH,'icon-atom-dark-64.svg')))
        self.actionOpenProject.setIcon(QIcon(os.path.join(ICONPATH,'icon-open-session-dark-64.svg')))
        self.actionSaveProject.setIcon(QIcon(os.path.join(ICONPATH,'icon-save-session-dark-64.svg')))
        self.actionFullMap.setIcon(QIcon(os.path.join(ICONPATH,'icon-fit-to-width-dark-64.svg')))
        self.actionCrop.setIcon(QIcon(os.path.join(ICONPATH,'icon-crop-dark-64.svg')))
        self.actionSwapAxes.setIcon(QIcon(os.path.join(ICONPATH,'icon-swap-dark-64.svg')))
        self.toolButtonSwapResolution.setIcon(QIcon(os.path.join(ICONPATH,'icon-swap-resolution-dark-64.svg')))
        # Notes
        self.toolButtonNotesHeading.setIcon(QIcon(os.path.join(ICONPATH,'icon-heading-dark-64.svg')))
        self.toolButtonNotesBold.setIcon(QIcon(os.path.join(ICONPATH,'icon-bold-dark-64.svg')))
        self.toolButtonNotesItalic.setIcon(QIcon(os.path.join(ICONPATH,'icon-italics-dark-64.svg')))
        self.toolButtonNotesBulletList.setIcon(QIcon(os.path.join(ICONPATH,'icon-bullet-list-dark-64.svg')))
        self.toolButtonNotesNumList.setIcon(QIcon(os.path.join(ICONPATH,'icon-numbered-list-dark-64.svg')))
        self.toolButtonNotesImage.setIcon(QIcon(os.path.join(ICONPATH,'icon-image-64.svg')))
        self.toolButtonNotesSave.setIcon(QIcon(os.path.join(ICONPATH,'icon-pdf-dark-64.svg')))
        # Reset Buttons
        self.toolButtonXAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-dark-64.svg')))
        self.toolButtonYAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-dark-64.svg')))
        self.toolButtonCAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-dark-64.svg')))
        self.toolButtonClusterColorReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-dark-64.svg')))
        self.toolButtonHistogramReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-dark-64.svg')))
        # Plot Tree
        self.toolButtonSortAnalyte.setIcon(QIcon(os.path.join(ICONPATH,'icon-sort-dark-64.svg')))
        self.toolButtonRemovePlot.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        # Samples
        self.toolBox.setItemIcon(self.left_tab['sample'],QIcon(os.path.join(ICONPATH,'icon-atom-dark-64.svg')))
        self.toolButtonScaleEqualize.setIcon(QIcon(os.path.join(ICONPATH,'icon-histeq-dark-64.svg')))
        self.toolButtonAutoScale.setIcon(QIcon(os.path.join(ICONPATH,'icon-autoscale-dark-64.svg')))
        self.toolBox.setItemIcon(self.left_tab['process'],QIcon(os.path.join(ICONPATH,'icon-histogram-dark-64.svg')))
        self.toolBox.setItemIcon(self.left_tab['multidim'],QIcon(os.path.join(ICONPATH,'icon-dimensional-analysis-dark-64.svg')))
        self.toolBox.setItemIcon(self.left_tab['cluster'],QIcon(os.path.join(ICONPATH,'icon-cluster-dark-64.svg')))
        self.toolBox.setItemIcon(self.left_tab['scatter'],QIcon(os.path.join(ICONPATH,'icon-ternary-dark-64.svg')))
        # Spot Data
        self.toolButtonSpotMove.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-point-dark-64.svg')))
        self.toolButtonSpotToggle.setIcon(QIcon(os.path.join(ICONPATH,'icon-show-hide-dark-64.svg')))
        self.toolButtonSpotSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-dark-64.svg')))
        self.toolButtonSpotAnalysis.setIcon(QIcon(os.path.join(ICONPATH,'icon-analysis-dark-64.svg')))
        self.toolButtonSpotRemove.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        # N-Dim
        self.toolBox.setItemIcon(self.left_tab['ndim'],QIcon(os.path.join(ICONPATH,'icon-TEC-dark-64.svg')))
        self.toolButtonNDimDown.setIcon(QIcon(os.path.join(ICONPATH,'icon-down-arrow-dark-64.svg')))
        self.toolButtonNDimUp.setIcon(QIcon(os.path.join(ICONPATH,'icon-up-arrow-dark-64.svg')))
        self.toolButtonNDimSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-dark-64.svg')))
        self.toolButtonNDimRemove.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        # Filter
        self.toolButtonFilterSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-dark-64.svg')))
        self.toolButtonFilterUp.setIcon(QIcon(os.path.join(ICONPATH,'icon-up-arrow-dark-64.svg')))
        self.toolButtonFilterDown.setIcon(QIcon(os.path.join(ICONPATH,'icon-down-arrow-dark-64.svg')))
        self.toolButtonFilterRemove.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        # Polygons
        self.toolBox.setItemIcon(self.left_tab['polygons'],QIcon(os.path.join(ICONPATH,'icon-polygon-new-dark-64.svg')))
        self.toolButtonPolyCreate.setIcon(QIcon(os.path.join(ICONPATH,'icon-polygon-new-dark-64.svg')))
        self.toolButtonPolyAddPoint.setIcon(QIcon(os.path.join(ICONPATH,'icon-add-point-dark-64.svg')))
        self.toolButtonPolyRemovePoint.setIcon(QIcon(os.path.join(ICONPATH,'icon-remove-point-dark-64.svg')))
        self.toolButtonPolyMovePoint.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-point-dark-64.svg')))
        self.toolButtonPolyLink.setIcon(QIcon(os.path.join(ICONPATH,'icon-link-dark-64.svg')))
        self.toolButtonPolyDelink.setIcon(QIcon(os.path.join(ICONPATH,'icon-unlink-dark-64.svg')))
        self.toolButtonPolyDelete.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        # Profile
        self.toolBox.setItemIcon(self.left_tab['profile'],QIcon(os.path.join(ICONPATH,'icon-profile-dark-64.svg')))
        self.toolButtonClearProfile.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        self.toolButtonPointDelete.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        self.toolButtonPointSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-dark-64.svg')))
        self.toolButtonPointMove.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-point-dark-64.svg')))
        self.toolButtonProfileInterpolate.setIcon(QIcon(os.path.join(ICONPATH,'icon-interpolate-dark-64.svg')))
        self.toolButtonPlotProfile.setIcon(QIcon(os.path.join(ICONPATH,'icon-profile-dark-64.svg')))
        self.toolButtonPointDown.setIcon(QIcon(os.path.join(ICONPATH,'icon-down-arrow-dark-64.svg')))
        self.toolButtonPointUp.setIcon(QIcon(os.path.join(ICONPATH,'icon-up-arrow-dark-64.svg')))
        # Browser
        self.toolButtonBrowserHome.setIcon(QIcon(os.path.join(ICONPATH,'icon-home-dark-64.svg')))
        self.toolButtonForward.setIcon(QIcon(os.path.join(ICONPATH,'icon-forward-arrow-dark-64.svg')))
        self.toolButtonBack.setIcon(QIcon(os.path.join(ICONPATH,'icon-back-arrow-dark-64.svg')))
        # Group Box Plot Tools
        self.toolButtonHome.setIcon(QIcon(os.path.join(ICONPATH,'icon-home-dark-64.svg')))
        self.toolButtonRemoveAllMVPlots.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        self.toolButtonPopFigure.setIcon(QIcon(os.path.join(ICONPATH,'icon-popout-dark-64.svg')))
        self.toolButtonAnnotate.setIcon(QIcon(os.path.join(ICONPATH,'icon-annotate-dark-64.svg')))
        self.toolButtonPan.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-dark-64.svg')))
        self.toolButtonZoom.setIcon(QIcon(os.path.join(ICONPATH,'icon-zoom-dark-64.svg')))
        self.toolButtonDistance.setIcon(QIcon(os.path.join(ICONPATH,'icon-distance-dark-64.svg')))
        # Calculator
        self.toolButtonCalculate.setIcon(QIcon(os.path.join(ICONPATH,'icon-calculator-dark-64.svg')))
        self.actionCalculator.setIcon(QIcon(os.path.join(ICONPATH,'icon-calculator-dark-64.svg')))
        self.toolBoxTreeView.setItemIcon(self.right_tab['calculator'],QIcon(os.path.join(ICONPATH,'icon-calculator-dark-64.svg')))
        self.toolButtonCalcDelete.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-dark-64.svg')))
        # Style Toolbox
        self.toolBoxStyle.setItemIcon(0,QIcon(os.path.join(ICONPATH,'icon-axes-dark-64.svg')))
        self.toolBoxStyle.setItemIcon(1,QIcon(os.path.join(ICONPATH,'icon-text-and-scales-dark-64.svg')))
        self.toolBoxStyle.setItemIcon(2,QIcon(os.path.join(ICONPATH,'icon-marker-and-lines-dark-64.svg')))
        self.toolBoxStyle.setItemIcon(3,QIcon(os.path.join(ICONPATH,'icon-rgb-dark-64.svg')))
        # Cluster tab
        self.toolBoxStyle.setItemIcon(4,QIcon(os.path.join(ICONPATH,'icon-cluster-dark-64.svg')))
        self.toolButtonClusterLink.setIcon(QIcon(os.path.join(ICONPATH,'icon-link-dark-64.svg')))
        self.toolButtonClusterDelink.setIcon(QIcon(os.path.join(ICONPATH,'icon-unlink-dark-64.svg')))

    def set_light_theme(self):
        ss = load_stylesheet('light.qss')
        app.setStyleSheet(ss)

        self.actionViewMode.setIcon(QIcon(os.path.join(ICONPATH,'icon-sun-64.svg')))
        self.actionViewMode.setIconText('Light')

        self.actionSelectAnalytes.setIcon(QIcon(os.path.join(ICONPATH,'icon-atom-64.svg')))
        self.actionOpenProject.setIcon(QIcon(os.path.join(ICONPATH,'icon-open-session-64.svg')))
        self.actionSaveProject.setIcon(QIcon(os.path.join(ICONPATH,'icon-save-session-64.svg')))
        self.actionFullMap.setIcon(QIcon(os.path.join(ICONPATH,'icon-fit-to-width-64.svg')))
        self.actionCrop.setIcon(QIcon(os.path.join(ICONPATH,'icon-crop-64.svg')))
        self.actionSwapAxes.setIcon(QIcon(os.path.join(ICONPATH,'icon-swap-64.svg')))
        self.toolButtonSwapResolution.setIcon(QIcon(os.path.join(ICONPATH,'icon-swap-resolution-64.svg')))
        # Notes
        self.toolButtonNotesHeading.setIcon(QIcon(os.path.join(ICONPATH,'icon-heading-64.svg')))
        self.toolButtonNotesBold.setIcon(QIcon(os.path.join(ICONPATH,'icon-bold-64.svg')))
        self.toolButtonNotesItalic.setIcon(QIcon(os.path.join(ICONPATH,'icon-italics-64.svg')))
        self.toolButtonNotesBulletList.setIcon(QIcon(os.path.join(ICONPATH,'icon-bullet-list-64.svg')))
        self.toolButtonNotesNumList.setIcon(QIcon(os.path.join(ICONPATH,'icon-numbered-list-64.svg')))
        self.toolButtonNotesImage.setIcon(QIcon(os.path.join(ICONPATH,'icon-image-dark-64.svg')))
        self.toolButtonNotesSave.setIcon(QIcon(os.path.join(ICONPATH,'icon-pdf-64.svg')))
        # Reset Buttons
        self.toolButtonXAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-64.svg')))
        self.toolButtonYAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-64.svg')))
        self.toolButtonCAxisReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-64.svg')))
        self.toolButtonClusterColorReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-64.svg')))
        self.toolButtonHistogramReset.setIcon(QIcon(os.path.join(ICONPATH,'icon-reset-64.svg')))
        # Plot Tree
        self.toolButtonSortAnalyte.setIcon(QIcon(os.path.join(ICONPATH,'icon-sort-64.svg')))
        self.toolButtonRemovePlot.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        # Samples
        self.toolBox.setItemIcon(self.left_tab['sample'],QIcon(os.path.join(ICONPATH,'icon-atom-64.svg')))
        self.toolButtonScaleEqualize.setIcon(QIcon(os.path.join(ICONPATH,'icon-histeq-64.svg')))
        self.toolButtonAutoScale.setIcon(QIcon(os.path.join(ICONPATH,'icon-autoscale-64.svg')))
        self.toolBox.setItemIcon(self.left_tab['process'],QIcon(os.path.join(ICONPATH,'icon-histogram-64.svg')))
        self.toolBox.setItemIcon(self.left_tab['multidim'],QIcon(os.path.join(ICONPATH,'icon-dimensional-analysis-64.svg')))
        self.toolBox.setItemIcon(self.left_tab['cluster'],QIcon(os.path.join(ICONPATH,'icon-cluster-64.svg')))
        self.toolBox.setItemIcon(self.left_tab['scatter'],QIcon(os.path.join(ICONPATH,'icon-ternary-64.svg')))
        # Spot Data
        self.toolButtonSpotMove.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-point-64.svg')))
        self.toolButtonSpotToggle.setIcon(QIcon(os.path.join(ICONPATH,'icon-show-hide-64.svg')))
        self.toolButtonSpotSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-64.svg')))
        self.toolButtonSpotAnalysis.setIcon(QIcon(os.path.join(ICONPATH,'icon-analysis-64.svg')))
        self.toolButtonSpotRemove.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        # N-Dim
        self.toolBox.setItemIcon(self.left_tab['ndim'],QIcon(os.path.join(ICONPATH,'icon-TEC-64.svg')))
        self.toolButtonNDimDown.setIcon(QIcon(os.path.join(ICONPATH,'icon-down-arrow-64.svg')))
        self.toolButtonNDimUp.setIcon(QIcon(os.path.join(ICONPATH,'icon-up-arrow-64.svg')))
        self.toolButtonNDimSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-64.svg')))
        self.toolButtonNDimRemove.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        # Filter
        self.toolButtonFilterSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-64.svg')))
        self.toolButtonFilterUp.setIcon(QIcon(os.path.join(ICONPATH,'icon-up-arrow-64.svg')))
        self.toolButtonFilterDown.setIcon(QIcon(os.path.join(ICONPATH,'icon-down-arrow-64.svg')))
        self.toolButtonFilterRemove.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        # Polygons
        self.toolBox.setItemIcon(self.left_tab['polygons'],QIcon(os.path.join(ICONPATH,'icon-polygon-new-64.svg')))
        self.toolButtonPolyCreate.setIcon(QIcon(os.path.join(ICONPATH,'icon-polygon-new-64.svg')))
        self.toolButtonPolyAddPoint.setIcon(QIcon(os.path.join(ICONPATH,'icon-add-point-64.svg')))
        self.toolButtonPolyRemovePoint.setIcon(QIcon(os.path.join(ICONPATH,'icon-remove-point-64.svg')))
        self.toolButtonPolyMovePoint.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-point-64.svg')))
        self.toolButtonPolyLink.setIcon(QIcon(os.path.join(ICONPATH,'icon-link-64.svg')))
        self.toolButtonPolyDelink.setIcon(QIcon(os.path.join(ICONPATH,'icon-unlink-64.svg')))
        self.toolButtonPolyDelete.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        # Profile
        self.toolBox.setItemIcon(self.left_tab['profile'],QIcon(os.path.join(ICONPATH,'icon-profile-64.svg')))
        self.toolButtonClearProfile.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        self.toolButtonPointDelete.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        self.toolButtonPointSelectAll.setIcon(QIcon(os.path.join(ICONPATH,'icon-select-all-64.svg')))
        self.toolButtonPointMove.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-point-64.svg')))
        self.toolButtonProfileInterpolate.setIcon(QIcon(os.path.join(ICONPATH,'icon-interpolate-64.svg')))
        self.toolButtonPlotProfile.setIcon(QIcon(os.path.join(ICONPATH,'icon-profile-64.svg')))
        self.toolButtonPointDown.setIcon(QIcon(os.path.join(ICONPATH,'icon-down-arrow-64.svg')))
        self.toolButtonPointUp.setIcon(QIcon(os.path.join(ICONPATH,'icon-up-arrow-64.svg')))
        # Browser
        self.toolButtonBrowserHome.setIcon(QIcon(os.path.join(ICONPATH,'icon-home-64.svg')))
        self.toolButtonForward.setIcon(QIcon(os.path.join(ICONPATH,'icon-forward-arrow-64.svg')))
        self.toolButtonBack.setIcon(QIcon(os.path.join(ICONPATH,'icon-back-arrow-64.svg')))
        # Group Box Plot Tools
        self.toolButtonHome.setIcon(QIcon(os.path.join(ICONPATH,'icon-home-64.svg')))
        self.toolButtonRemoveAllMVPlots.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        self.toolButtonPopFigure.setIcon(QIcon(os.path.join(ICONPATH,'icon-popout-64.svg')))
        self.toolButtonAnnotate.setIcon(QIcon(os.path.join(ICONPATH,'icon-annotate-64.svg')))
        self.toolButtonPan.setIcon(QIcon(os.path.join(ICONPATH,'icon-move-64.svg')))
        self.toolButtonZoom.setIcon(QIcon(os.path.join(ICONPATH,'icon-zoom-64.svg')))
        self.toolButtonDistance.setIcon(QIcon(os.path.join(ICONPATH,'icon-distance-64.svg')))
        # Calculator
        self.toolButtonCalculate.setIcon(QIcon(os.path.join(ICONPATH,'icon-calculator-64.svg')))
        self.actionCalculator.setIcon(QIcon(os.path.join(ICONPATH,'icon-calculator-64.svg')))
        self.toolBoxTreeView.setItemIcon(self.right_tab['calculator'],QIcon(os.path.join(ICONPATH,'icon-calculator-64.svg')))
        self.toolButtonCalcDelete.setIcon(QIcon(os.path.join(ICONPATH,'icon-delete-64.svg')))
        # Style Toolbox
        self.toolBoxStyle.setItemIcon(0,QIcon(os.path.join(ICONPATH,'icon-axes-64.svg')))
        self.toolBoxStyle.setItemIcon(1,QIcon(os.path.join(ICONPATH,'icon-text-and-scales-64.svg')))
        self.toolBoxStyle.setItemIcon(2,QIcon(os.path.join(ICONPATH,'icon-marker-and-lines-64.svg')))
        self.toolBoxStyle.setItemIcon(3,QIcon(os.path.join(ICONPATH,'icon-rgb-64.svg')))
        # Cluster tab
        self.toolBoxStyle.setItemIcon(4,QIcon(os.path.join(ICONPATH,'icon-cluster-64.svg')))
        self.toolButtonClusterLink.setIcon(QIcon(os.path.join(ICONPATH,'icon-link-64.svg')))
        self.toolButtonClusterDelink.setIcon(QIcon(os.path.join(ICONPATH,'icon-unlink-64.svg')))

# -------------------------------
# Classes
# -------------------------------
# Matplotlib Canvas object
# -------------------------------
class SimpleMplCanvas(FigureCanvas):
    """Matplotlib canvas object for non-interactive plots

    Parameters
    ----------
    sub : int, optional
        Subplot location, by default 111
    parent : object, optional
        Parent calling MplCanvas, by default None
    width : int, optional
        Width in inches, by default 5
    height : int, optional
        Height in inches, by default 4
    proj : str, optional
        Projection, by default None
    """    
    def __init__(self, sub=111, parent=None, width=5, height=4, proj=None):
        self.fig = Figure(figsize=(width, height))
        if proj is not None:
            self.axes = self.fig.add_subplot(sub, projection='radar')
        else:
            self.axes = self.fig.add_subplot(sub)
        super(SimpleMplCanvas, self).__init__(self.fig)

class MplCanvas(FigureCanvas):
    """Matplotlib canvas object for interactive plots

    Parameters
    ----------
    sub : int, optional
        Subplot location, by default 111
    parent : object, optional
        Parent calling MplCanvas, by default None
    width : int, optional
        Width in inches, by default 5
    height : int, optional
        Height in inches, by default 4
    proj : str, optional
        Projection, by default None
    """    
    def __init__(self,fig=None, sub=111, parent=None, width=5, height=4, proj=None):
        #create MPLCanvas with existing figure (required when loading saved projects)
        if fig:
            self.fig = fig
        else:
            self.fig = Figure(figsize=(width, height))
        if proj is not None:
            self.axes = self.fig.add_subplot(sub, projection='radar')
        else:
            self.axes = self.fig.add_subplot(sub)
        super(MplCanvas, self).__init__(self.fig)

        self.main_window = parent

        # for placing text annotations
        # --------------------
        self.setCursorPosition()

        # restoring initial axes
        # --------------------
        self.initial_extent = None

        # distance measurement
        # --------------------
        # Variables to store points and line
        self.first_point = None
        self.line = None
        self.dtext = None
        self.saved_line = []
        self.saved_dtext = []
        self.array = None
        if self.main_window is not None:
            if self.main_window.comboBoxPlotType.currentText() in self.main_window.map_plot_types:
                self.map_flag = True
            else:
                self.map_flag = False

            # Connect the button and canvas events
            self.mpl_connect('button_press_event', self.distanceOnClick)
            self.mpl_connect('motion_notify_event', self.distanceOnMove)
            self.mpl_connect('motion_notify_event', self.mouseLocation)

    def enterEvent(self, event):
        # Set cursor to cross when the mouse enters the window
        self.setCursor(Qt.CrossCursor)

    def leaveEvent(self, event):
        # Reset cursor to default when the mouse leaves the window
        self.unsetCursor()

    def mouseLocation(self,event):
        """Get mouse location on axes for display

        Displays the location and value of a map in ``MainWindow.widgetPlotInfoSV``.

        Parameters
        ----------
        event : event data
            Includes the location of mouse pointer.
        """        
        if (not event.inaxes) or (event.xdata is None) or (event.ydata is None):
            return

        if event.inaxes.get_label() == '<colorbar>':
            return

        if self.map_flag:
            if self.array is None:
                return
            # pixel location on current MplCanvas
            x_i = round(event.xdata)
            if x_i < 0:
                x_i = 0
            elif x_i > self.array.shape[1]-1:
                x_i = self.array.shape[1]
            
            y_i = round(event.ydata)
            if y_i < 0:
                y_i = 0
            elif y_i > self.array.shape[0]-1:
                y_i = self.array.shape[0]
            
            x = x_i*self.main_window.dx
            y = y_i*self.main_window.dy

            label =  f" {self.main_window.preferences['Units']['Concentration']}"
        else:
            x = event.xdata
            y = event.ydata
            self.main_window.labelSVInfoValue.setText(f"V: N/A")

            if self.array is not None:
                x_i = round(x)
                y_i = round(y)

                label = ''
        

        if self.array is not None:
            value = self.array[y_i][x_i]
            txt = f"V: {value:.4g}{label}"
            self.main_window.labelSVInfoValue.setText(txt)

        txt = f'X: {x:.4g}'
        self.main_window.labelSVInfoX.setText(txt)
        txt = f'Y: {y:.4g}'
        self.main_window.labelSVInfoY.setText(txt)

    def set_initial_extent(self):
        """Initial extent of the plot

        Sets the initital extent of the plot.
        """
        xlim = self.axes.get_xlim()
        ylim = self.axes.get_ylim()
        self.initial_extent = [xlim[0], xlim[1], ylim[0], ylim[1]]
        #print(f"Initial extent set to: {self.initial_extent}")

    def restore_view(self):
        """Restores the initial extent

        Restores the initial extent when ``MainWindow.toolButtonHome`` is clicked.
        """
        if self.initial_extent:
            self.axes.set_xlim(self.initial_extent[:2])
            self.axes.set_ylim(self.initial_extent[2:])
        else:
            self.axes.set_xlim(auto=True)
            self.axes.set_ylim(auto=True)
        self.draw()

    def load_figure(self, fig):
        """Load existing figure
        
        Parameters
        ----------
        fig : matplotlib.Figure
            Matplotlib figure.
        """
        self.fig = fig
        self.axes = self.fig.gca()  # Get current axes
        self.draw()  # Redraw the canvas with the loaded figure

    def setCursorPosition(self):
        """Gets the cursor position on an MplCanvas

        Mouse listener
        """        
        self.cid = self.mpl_connect('button_press_event', self.textOnClick)

    def textOnClick(self, event):
        """Adds text to plot at clicked position

        Only adds a text to a plot when the Annotate button is checked.

        Parameters
        ----------
        event : MouseEvent
            Mouse click event.
        """        
        if (self.main_window.canvasWindow.currentIndex() != self.main_window.canvas_tab['sv']) or (not self.main_window.toolButtonAnnotate.isChecked()):
            return

        x,y = event.xdata, event.ydata
        # get text
        txt, ok = QInputDialog.getText(self, 'Figure', 'Enter text:')
        if not ok:
            return

        style = self.main_window.styles[self.main_window.comboBoxPlotType.currentText()]
        self.axes.text(x,y,txt, color=style['Scale']['OverlayColor'], fontsize=style['Text']['FontSize'])
        self.draw()

    def calculate_distance(self,p1,p2):
        """Calculuates distance on a figure

        Parameters
        ----------
        p1 : _type_
            _description_
        p2 : _type_
            _description_

        Returns
        -------
        float
            Distance between two given points.
        """
        if self.map_flag:
            dx = self.main_window.dx
            dy = self.main_window.dy
        else:
            dx = 1
            dy = 1

        return np.sqrt(((p2[0] - p1[0])*dx)**2 + ((p2[1] - p1[1])*dy)**2)

    def plot_line(self, p1, p2):
        """Plots line from distance calculation

        Parameters
        ----------
        p1, p2 : tuple
            Endpoints of line.

        Returns
        -------
        matplotlib.plot
            Handle to line
        """        
        plot_type = self.main_window.plot_info['plot_type']
        style = self.main_window.styles[plot_type]

        # plot line (keep only first returned handle)
        p = self.axes.plot([p1[0], p2[0]], [p1[1], p2[1]],
                ':', c=style['Scale']['OverlayColor'], lw=style['Lines']['LineWidth']
            )[0]

        return p
 
    def plot_text(self, p1,p2):
        """Adds distance to plot and updates distance label

        Updates distance in ``MainWindow.labelSVInfoDistance`` and adds distance
        at the end of the measuring line.

        Parameters
        ----------
        p1, p2 : tuple
            Endpoints of line.

        Returns
        -------
        matplotlib.text
            Handle to text.
        """        
        plot_type = self.main_window.plot_info['plot_type']
        style = self.main_window.styles[plot_type]

        # compute distance
        distance = self.calculate_distance(p1, p2)

        # Update distance label in widget 
        distance_text = f"{distance:.4g} {self.main_window.preferences['Units']['Distance']}"
        self.main_window.labelSVInfoDistance.setText(f"D: {distance_text}")

        # Update distance label on map
        if self.map_flag:
            xrange = self.main_window.x.nunique()*self.main_window.aspect_ratio
            yrange = self.main_window.y.nunique()
        else:
            xl = self.axes.get_xlim
            xrange = xl[1] - xl[0]
            yl = self.axes.get_ylim
            xrange = yl[1] - yl[0]

        # x-shift for text
        dx = 0.03*xrange
        if p2[0] > p1[0]:
            halign = 'left'
        else:
            dx = -dx
            halign = 'right'

        # y-shift for text
        dy = 0.03*yrange
        if p2[1] > p1[1]:
            valign = 'bottom'
        else:
            dy = -dy
            valign = 'top'

        # text on plot
        font = {'family':style['Text']['Font'], 'size':style['Text']['FontSize']-2}
        t = self.axes.text(p2[0]+dx, p2[1]+dy, distance_text, ha=halign, va=valign, fontdict=font, c=style['Scale']['OverlayColor'])

        return t

    def distanceOnClick(self, event):
        """Updates static endpoints of distance measuring line.

        Updates the endpoint of the distance measuring line and calls methods that 
        update the line and text.  Updates ``MplCanvas.first_point`` if it is the start of the line
        and ``MplCanvas.line_saved`` and ``MplCanvas.dtext_saved`` if it is the end of the line.

        Parameters
        ----------
        event : MouseEvent
            Mouse click event.
        """        
        self.setCursor(Qt.CrossCursor)
        if self.main_window.toolButtonDistance.isChecked():
            if event.inaxes:
                if self.first_point is None:
                    # First click
                    self.first_point = (event.xdata, event.ydata)
                    self.main_window.labelSVInfoDistance.setText(f"D: 0 {self.main_window.preferences['Units']['Distance']}")
                else:
                    # Second click
                    second_point = (event.xdata, event.ydata)

                    self.saved_line.append(self.plot_line(self.first_point, second_point))
                    self.saved_dtext.append(self.plot_text(self.first_point, second_point))
                    
                    self.distance_reset()

            self.draw()

    def distanceOnMove(self, event):
        """Updates dynamic second point of distance measuring line.

        Updates the second endpoint of the distance measuring line and calls methods that 
        update the line and text.  Updates ``MplCanvas.line`` and ``MplCanvas.dtext``.

        Parameters
        ----------
        event : MouseEvent
            Mouse click event.
        """        
        self.setCursor(Qt.CrossCursor)
        if (self.main_window.toolButtonDistance.isChecked()) and (self.first_point is not None) and event.inaxes:
            if self.line:
                self.line.remove()
            if self.dtext:
                self.dtext.remove()

            second_point = (event.xdata,event.ydata)
            self.line = self.plot_line(self.first_point, second_point)
            self.dtext = self.plot_text(self.first_point, second_point)

            self.draw()

    def distance_reset(self):
        """Resets distance variables and clears plot

        Sets ``MplCanvas.first_point`` to ``None``, ``MplCanvas.line`` and ``MplCanvas.dtext``.
        If ``MainWindow.toolButtonDistance`` is not checked, then ``MainWindow.labelSVInfoDistance`` is 
        also reset.
        """        
        self.first_point = None
        if self.line:
            self.line.remove()
            self.line = None
        if self.dtext:
            self.dtext.remove()
            self.dtext = None
        self.draw()
        if not self.main_window.toolButtonDistance.isChecked():
            self.main_window.labelSVInfoDistance.setText("D: N/A")

class MplDialog(QDialog):
    def __init__(self, parent, canvas, title=''):
        """A plot dialog

        This dialog is used to plot a matplotlib figure.  In general the dialog is used when a figure popped out from ``MainWindow.canvasWindow`` using ``MainWindow.toolButtonPopFigure``.

        Parameters
        ----------
        parent : MainWindow
            Calling class.
        canvas : MplCanvas
            Matplotlib plot canvas.
        title : str, optional
            Dialog title, by default ''
        """        
        super(MplDialog, self).__init__(parent)

        self.main_window = parent

        self.setWindowTitle(title)

        # Create a QVBoxLayout to hold the canvas and toolbar
        layout = QVBoxLayout(self)

        # Create a NavigationToolbar and add it to the layout
        self.toolbar = NavigationToolbar(canvas, self)

        # use custom buttons
        unwanted_buttons = ["Back", "Forward", "Customize", "Subplots"]

        icons_buttons = {
            "Home": QtGui.QIcon("resources/icons/icon-home-64.svg"),
            "Pan": QtGui.QIcon("resources/icons/icon-move-64.svg"),
            "Zoom": QtGui.QIcon("resources/icons/icon-zoom-64.svg"),
            "Save": QtGui.QIcon("resources/icons/icon-save-file-64.svg")
        }
        for action in self.toolbar.actions():
            if action.text() in unwanted_buttons:
                self.toolbar.removeAction(action)
            if action.text() in icons_buttons:
                action.setIcon(icons_buttons.get(action.text(), QtGui.QIcon()))

        self.toolbar.setMaximumHeight(int(32))
        self.toolbar.setIconSize(QSize(24,24))

        # Add toolbar to self.layout
        layout.addWidget(self.toolbar,0)

        # Add a matplotlib canvas to self.layout
        layout.addWidget(canvas,1)

        # Create a button box for OK and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box,2)

        self.main_window.clear_layout(self.main_window.widgetSingleView.layout())


class StandardItem(QStandardItem):
    def __init__(self, txt='', font_size=11, set_bold=False):
        super().__init__()

        fnt  = QFont()
        fnt.setPointSize(font_size)
        fnt.setBold(set_bold)
        self.setEditable(False)
        self.setText(txt)
        self.setFont(fnt)


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


# QuickViewDialog gui
# -------------------------------
class quickView(QDialog, Ui_QuickViewDialog):
    """Creates a dialog for the user to select and order analytes for Quick View

    Opens an instance of QuickViewDialog for the user to select and order analytes for Quick View.
    The lists are automatically saved for future use.

    Parameters
    ----------
    QDialog : QDialog
        
    Ui_QuickViewDialog : QuickViewDialog
        User interface design.
    """    
    def __init__(self, parent=None):
        """Initializes quickView

        Parameters
        ----------
        analyte_list : list
            List of analytes to populate column 0 of  ``quickView.tableWidget``.
        quickview_list : dict
            Dictionary to be updated with an ordered list of analytes to be added to the ``MainWindow.layoutQuickView``.
        parent : None, optional
            Parent UI, by default None
        """        
        super().__init__(parent)
        self.setupUi(self)
        self.analyte_list = self.data[self.sample_id]['analyte_info']['analytes']

        if darkdetect.isDark():
            self.toolButtonSort.setIcon(QIcon(os.path.join(ICONPATH,'icon-sort-dark-64.svg')))
            self.toolButtonSave.setIcon(QIcon(os.path.join(ICONPATH,'icon-save-dark-64.svg')))

        self.tableWidget = TableWidgetDragRows()  # Assuming TableWidgetDragRows is defined elsewhere
        self.setup_table()
        
        # Setup sort menu and associated toolButton
        self.setup_sort_menu()
        
        # Save functionality
        self.toolButtonSave.clicked.connect(self.save_selected_analytes)
        # Close dialog signal
        self.pushButtonClose.clicked.connect(lambda: self.done(0))
        self.layout().insertWidget(0, self.tableWidget)
        self.show()

    def setup_table(self):
        """Sets up analyte selection table in dialog"""
        self.tableWidget.setRowCount(len(self.analyte_list))
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(['Analyte', 'Show'])
        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.populate_table()

    def populate_table(self):
        """Populates dialog table with analytes"""
        # Before repopulating, save the current state of checkboxes
        checkbox_states = {}
        for row in range(self.tableWidget.rowCount()):
            checkbox = self.tableWidget.cellWidget(row, 1)
            if checkbox:
                analyte = self.tableWidget.item(row, 0).text()
                checkbox_states[analyte] = checkbox.isChecked()

        # Clear the table and repopulate
        self.tableWidget.setRowCount(len(self.analyte_list))
        for row, analyte in enumerate(self.analyte_list):
            item = QTableWidgetItem(analyte)
            self.tableWidget.setItem(row, 0, item)
            checkbox = QCheckBox()
            # Restore the checkbox state based on the previous state if available
            checkbox.setChecked(checkbox_states.get(analyte, True))
            self.tableWidget.setCellWidget(row, 1, checkbox)

    def setup_sort_menu(self):
        """Adds options to sort menu"""
        sortmenu_items = ['alphabetical', 'atomic number', 'mass', 'compatibility', 'radius']
        SortMenu = QMenu()
        SortMenu.triggered.connect(self.apply_sort)
        self.toolButtonSort.setMenu(SortMenu)
        for item in sortmenu_items:
            SortMenu.addAction(item)

    def apply_sort(self, action):
        """Sorts analyte table in dialog"""        
        method = action.text()
        self.analyte_list = self.main_window.sort_analytes(method, self.analyte_list)
        self.populate_table()  # Refresh table with sorted data

    def save_selected_analytes(self):
        """Gets list of analytes and group name when Save button is clicked

        #     Retrieves the user defined name from ``quickView.lineEditViewName`` and list of analytes using ``quickView.column_to_list()``
        #     and adds them to a dictionary item with the name defined as the key.

        #     Raises
        #     ------
        #         A warning is raised if the user does not provide a name.  The list is not added to the dictionary in this case.
        #     """        
        self.view_name = self.lineEditViewName.text().strip()
        if not self.view_name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid view name.")
            return

        selected_analytes = [self.tableWidget.item(row, 0).text() for row in range(self.tableWidget.rowCount()) if self.tableWidget.cellWidget(row, 1).isChecked()]
        self.QV_analyte_list[self.view_name] = selected_analytes

        # update self.comboBoxQVList combo box with view_name
        self.comboBoxQVList.addItem(self.view_name)
        
        # Save to CSV
        self.save_to_csv()

    def save_to_csv(self):
        """Opens a message box, prompting user to in put a file to save the table list"""
        file_path = os.path.join(BASEDIR,'resources', 'styles', 'qv_lists.csv')
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # append dictionary to file of saved qv_lists
        lameio.export_dict_to_csv(self.QV_analyte_list, file_path)
        

        QMessageBox.information(self, "Save Successful", f"Analytes view saved under '{self.view_name}' successfully.")
        
       
# WebEngineView - Web engine for viewing userguide help pages
# -------------------------------
class WebEngineView(QWebEngineView):
    """Creates a web engine widget to display user guide

    _extended_summary_

    Parameters
    ----------
    QWebEngineView : QWebEngine
        A web engine widget
    """    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_window = parent

        # Connect signals
        self.loadFinished.connect(self.on_load_finished)
        self.loadStarted.connect(self.on_load_started)
        self.loadProgress.connect(self.on_load_progress)
        self.page().profile().setHttpAcceptLanguage("en-US,en;q=0.9")
        self.page().profile().setHttpUserAgent("MyBrowser 1.0")

        # Set up a JavaScript console message handler
        self.page().setWebChannel(None)
        self.page().setFeaturePermission(QUrl(), QWebEnginePage.Notifications, QWebEnginePage.PermissionGrantedByUser)
        self.page().javaScriptConsoleMessage = self.handle_console_message

    @pyqtSlot(bool)
    def on_load_finished(self, success):
        if not success:
            self.setUrl(QUrl(os.path.abspath('docs/build/html/404.html')))
            #self.show_error_page()

    @pyqtSlot()
    def on_load_started(self):
        self.main_window.statusBar.showMessage("Loading started...")

    @pyqtSlot(int)
    def on_load_progress(self, progress):
        """Adds a loading progress message to the MainWindow.statusBar 

        Parameters
        ----------
        progress : int
            Loading fraction
        """        
        self.main_window.statusBar.showMessage(f"Loading progress: {progress}%")

    def show_error_page(self):
        html = f"<html><body><img src={os.path.abspath('docs/build/html/404.html')} /></html>"
        self.setHtml(html)

    def handle_console_message(self, level, message, line, source_id):
        pass
        #print(f"JavaScript Console: {message} at line {line} in {source_id}")


# TableWidgetDragRows
# -------------------------------
class TableWidgetDragRows(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDragDropMode(QAbstractItemView.InternalMove)

    def dropEvent(self, event: QDropEvent):
        if not event.isAccepted() and event.source() == self:
            drop_row = self.drop_on(event)

            rows = sorted(set(item.row() for item in self.selectedItems()))
            rows_to_move = []
            for row_index in rows:
                row_data = []
                for column_index in range(self.columnCount()):
                    item = self.item(row_index, column_index)
                    if item:
                        row_data.append(QTableWidgetItem(item))
                    else:
                        widget = self.cellWidget(row_index, column_index)
                        if isinstance(widget, QCheckBox):
                            state = widget.isChecked()
                            row_data.append(state)
                        else:
                            row_data.append(None)
                rows_to_move.append(row_data)
            
            for row_index in reversed(rows):
                self.removeRow(row_index)
                if row_index < drop_row:
                    drop_row -= 1

            for row_index, data in enumerate(rows_to_move):
                row_pos = row_index + drop_row
                self.insertRow(row_pos)
                for column_index, value in enumerate(data):
                    if isinstance(value, QTableWidgetItem):
                        self.setItem(row_pos, column_index, value)
                    elif isinstance(value, bool):  # It's a checkbox state
                        checkbox = QCheckBox()
                        checkbox.setChecked(value)
                        self.setCellWidget(row_pos, column_index, checkbox)
            event.accept()
            #select the chosen row
            self.select_rows(drop_row, len(rows_to_move))
        super().dropEvent(event)
    
    def select_rows(self, start_row, num_rows):
        for row in range(start_row, start_row + num_rows):
            for column in range(self.columnCount()):
                item = self.item(row, column)
                if item:
                    item.setSelected(True)

    def drop_on(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return self.rowCount()

        return index.row() + 1 if self.is_below(event.pos(), index) else index.row()

    def is_below(self, pos, index):
        rect = self.visualRect(index)
        margin = 2
        if pos.y() - rect.top() < margin:
            return False
        elif rect.bottom() - pos.y() < margin:
            return True
        # noinspection PyTypeChecker
        return rect.contains(pos, True) and not (int(self.model().flags(index)) & Qt.ItemIsDropEnabled) and pos.y() >= rect.center().y()


# Classes
# -------------------------------
class CustomAxis(AxisItem):
    def __init__(self, *args, **kwargs):
        AxisItem.__init__(self, *args, **kwargs)
        self.scale_factor = 1.0

    def setScaleFactor(self, scale_factor):
        self.scale_factor = scale_factor

    def tickStrings(self, values, scale, spacing):
        # Scale the values back to the original scale
        scaled_values = [v * self.scale_factor for v in values]
        # Format the tick strings as you want them to appear
        return ['{:.2f}'.format(v) for v in scaled_values]

# Functions for tables
# -------------------------------
class Table_Fcn:
    """Common table operations class

    For moving and deleting rows in QTableWidgets
    """
    def __init__(self,main_window):
        self.main_window = main_window

    def move_row_up(self, table):
        """Moves a row up one position in a table

        Moves the selected row in a table up one position. If multiple are selected only the top row is moved.

        Parameters
        ----------
        table : QTableWidget
        """

        # Get selected row
        row = table.currentRow()
        if len(table.selectedItems()) > 0:
            return

        if row > 0:
            table.insertRow(row - 1)
            for i in range(table.columnCount()):
                table.setItem(row - 1, i, table.takeItem(row + 1, i))
            table.removeRow(row + 1)
            table.setCurrentCell(row - 1, 0)

            match table.accessibleName():
                case 'Profiling':
                    self.main_window.comboBoxProfileSort.setCurrentIndex(0) #set dropdown sort to no

                    # Update self.profiles[self.main_window.sample_id] here accordingly
                    for key, profile in self.main_window.profiling.profiles[self.main_window.sample_id].items():
                        if row >0:
                            profile[row], profile[row -1 ] = profile[row - 1], profile[row]
                    self.main_window.profiling.plot_profiles()
                    if self.main_window.profiling.main_window.toolButtonProfileInterpolate.isChecked(): #reset interpolation if selected
                        self.main_window.profiling.clear_interpolation()
                        self.main_window.profiling.interpolate_points(interpolation_distance=int(self.main_window.lineEditIntDist.text()), radius= int(self.main_window.lineEditPointRadius.text()))
                #case 'NDim':
                    # update plot

                #case 'Filters':
                    # update filters
                    # update plots

    def move_row_down(self,table):
        """Moves a row down one position in a table

        Moves the selected row in a table down one position. If multiple are selected only the top row is moved.

        Parameters
        ----------
        table : QTableWidget
        """

        # Similar to move_row_up, but moving the row down
        row = table.currentRow()
        if len(table.selectedItems()) > 0:
            return

        max_row = table.rowCount() - 1
        if row < max_row:
            table.insertRow(row + 2)
            for i in range(table.columnCount()):
                table.setItem(row + 2, i, table.takeItem(row, i))
            table.removeRow(row)
            table.setCurrentCell(row + 1, 0)
            match table.accesibleName():
                case 'Profiling':
                    # update point order of each profile
                    for key, profile in self.main_window.profiling.profiles[self.main_window.sample_id].items():
                        if row < len(profile) - 1:
                            profile[row], profile[row + 1] = profile[row + 1], profile[row]
                    self.main_window.profiling.plot_profiles()
                    if self.main_window.toolButtonProfileInterpolate.isChecked(): #reset interpolation if selected
                        self.main_window.profiling.clear_interpolation()
                        self.main_window.profiling.interpolate_points(interpolation_distance=int(self.main_window.lineEditIntDist.text()), radius= int(self.main_window.lineEditPointRadius.text()))

    def delete_row(self,table):
        """Deletes selected rows in a table

        Parameters
        ----------
        table : QTableWidget
        """
        rows = [index.row() for index in table.selectionModel().selectedRows()][::-1] #sort descending to pop in order
        match table.accessibleName():
            case 'Profiling':
                for row in rows:
                    # Get selected row and delete it
                    table.removeRow(row)
                    # remove point from each profile and its corresponding scatter plot item


                    for key, profile in self.main_window.profiling.profiles[self.main_window.sample_id].items():
                        if row < len(profile):
                            scatter_item = profile[row][3]  # Access the scatter plot item
                            for _, (_, plot, _) in self.main_window.lasermaps.items():
                                plot.removeItem(scatter_item)
                            profile.pop(row) #index starts at 0

                self.main_window.profiling.plot_profiles(sort_axis = False)

                if self.main_window.toolButtonProfileInterpolate.isChecked(): #reset interpolation if selected
                    self.main_window.profiling.clear_interpolation()
                    self.main_window.profiling.interpolate_points(interpolation_distance=int(self.main_window.lineEditIntDist.text()), radius= int(self.main_window.lineEditPointRadius.text()))

            case 'NDim':
                for row in rows:
                    # Get selected row and delete it
                    table.removeRow(row)
                    self.main_window.ndim_list.pop(row)

            case 'Filters':
                for row in rows:
                    # Get selected row and delete it
                    table.removeRow(row)

            case 'Polygon':
                for row in rows:
                    # Get p_id
                    item = self.main_window.tableWidgetPolyPoints.item(row, 0)
                    p_id = int(item.text())
                    # Get selected row and delete it
                    table.removeRow(row)
                    if p_id in self.main_window.polygon.lines[self.main_window.sample_id]:
                        # remove point from each profile and its corresponding scatter plot item
                        for p in self.main_window.polygon.polygons[self.main_window.sample_id][p_id].points:
                            scatter_item = p[2]  # Access the scatter plot item
                            for _, (_, plot, _) in self.main_window.lasermaps.items():
                                plot.removeItem(scatter_item)
                        # Remove existing temporary line(s) if any
                        for line in self.main_window.polygon.lines[self.main_window.sample_id][p_id].lines:
                            for _, (_, plot, _) in self.main_window.lasermaps.items():
                                plot.removeItem(line)
                    

                        
                    # delete polygon from list
                    del self.main_window.polygon.polygons[self.main_window.sample_id][p_id]

# Cropping
# -------------------------------
class Crop_tool:
    """Crop maps

    Cropping maps sets the maximum extent of the map for analysis.

    Attributes
    ----------
    overlays: QGraphicsRectItem()
        contains data for the figure overlay showing crop region
    """
    def __init__(self, main_window):
        self.main_window = main_window
        # Initialize overlay rectangles
        self.overlays = []
    def init_crop(self):
        """Sets intial crop region as full map extent."""


        if self.main_window.actionCrop.isChecked():
            if self.main_window.data[self.main_window.sample_id]['crop']:
                # reset to full view and remove overlays if user unselects crop tool
                self.main_window.reset_to_full_view()
            # Original extent of map
            self.x_range = self.main_window.x_range
            self.y_range = self.main_window.y_range

            # Central crop rectangle dimensions (half width and height of the plot)
            crop_rect_width = self.x_range / 2
            crop_rect_height =self.y_range / 2

            # Position the crop_rect at the center of the plot
            crop_rect_x = (self.x_range - crop_rect_width) / 2
            crop_rect_y = (self.y_range - crop_rect_height) / 2

            self.crop_rect = ResizableRectItem(parent=self, rect=QRectF(crop_rect_x, crop_rect_y, crop_rect_width, crop_rect_height))
            self.crop_rect.setPen(QPen(QColor(255, 255, 255), 4, Qt.DashLine))
            self.crop_rect.setZValue(1e9)
            self.main_window.plot.addItem(self.crop_rect)

            for _ in range(4):
                overlay = QGraphicsRectItem()
                overlay.setBrush(QColor(0, 0, 0, 120))  # Semi-transparent dark overlay
                self.crop_rect.setZValue(1e9)
                self.main_window.plot.addItem(overlay)
                self.overlays.append(overlay)

            self.update_overlay(self.crop_rect.rect())

            self.actionFullMap.setEnabled(True)
        else:
            # reset to full view and remove overlays if user unselects crop tool
            self.main_window.reset_to_full_view()
            self.main_window.actionCrop.setChecked(False)
            self.main_window.actionFullMap.setEnabled(False)

    def remove_overlays(self):
        """Removes darkened overlay following completion of crop."""
        if len(self.overlays)> 0: #remove crop rect and overlays
            self.main_window.plot.removeItem(self.crop_rect)
            for overlay in self.overlays:
                self.main_window.plot.removeItem(overlay)
            self.overlays = []

    def update_overlay(self, rect):
        """Updates the overlay after user moves a boundary.

        Parameters
        ----------
        rect:
        """
        # Adjust the overlay rectangles based on the new crop_rect
        plot_rect = self.main_window.plot.viewRect()

        # Top overlay
        self.overlays[0].setRect(QRectF(plot_rect.topLeft(), QPointF(plot_rect.right(), rect.top())))
        # Bottom overlay
        self.overlays[1].setRect(QRectF(QPointF(plot_rect.left(), rect.bottom()), plot_rect.bottomRight()))
        # Left overlay
        self.overlays[2].setRect(QRectF(QPointF(plot_rect.left(), rect.top()), QPointF(rect.left(), rect.bottom())))
        # Right overlay
        self.overlays[3].setRect(QRectF(QPointF(rect.right(), rect.top()), QPointF(plot_rect.right(), rect.bottom())))

    def apply_crop(self):
        """Uses selected crop extent to set viewable area and map region for analysis."""
        if self.crop_rect:
            crop_rect = self.crop_rect.rect()  # self.crop_rect is ResizableRectItem
            self.main_window.data[self.main_window.sample_id]['crop_x_min'] = crop_rect.left()
            self.main_window.data[self.main_window.sample_id]['crop_x_max'] = crop_rect.right()
            self.main_window.data[self.main_window.sample_id]['crop_y_min'] = crop_rect.top()
            self.main_window.data[self.main_window.sample_id]['crop_y_max'] = crop_rect.bottom()
            if len(self.overlays)> 0: #remove crop rect and overlays
                self.main_window.plot.removeItem(self.crop_rect)
                for overlay in self.overlays:
                    self.main_window.plot.removeItem(overlay)
            #update plot with crop
            self.main_window.apply_crop()


# Rectangle for cropping
# -------------------------------
class ResizableRectItem(QGraphicsRectItem):
    def __init__(self, rect=None, parent=None):
        super(ResizableRectItem, self).__init__(rect)
        self.setAcceptHoverEvents(True)
        self.edgeTolerance = 50  # Adjusted for better precision
        self.resizing = False
        self.dragStartPos = None
        self.dragStartRect = None
        self.cursorChangeThreshold = 50  # Distance from corner to change cursor
        self.parent = parent
        self.pos = None

    def hoverMoveEvent(self, event):
        pos = event.pos()
        rect = self.rect()
        if (abs(pos.x() - rect.left()) < self.edgeTolerance and abs(pos.y() - rect.top()) < self.edgeTolerance) or \
           (abs(pos.x() - rect.right()) < self.edgeTolerance and abs(pos.y() - rect.bottom()) < self.edgeTolerance):
            self.setCursor(QCursor(Qt.SizeFDiagCursor))
        elif (abs(pos.x() - rect.left()) < self.edgeTolerance and abs(pos.y() - rect.bottom()) < self.edgeTolerance) or \
           (abs(pos.x() - rect.right()) < self.edgeTolerance and abs(pos.y() - rect.top()) < self.edgeTolerance):
            self.setCursor(QCursor(Qt.SizeBDiagCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
        super(ResizableRectItem, self).hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if self.onEdge(event.pos()):
            self.resizing = True
            self.dragStartPos = event.pos()
            self.dragStartRect = self.rect()
        else:
            super(ResizableRectItem, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing:
            self.resizeRect(event.pos())
        else:
            super(ResizableRectItem, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.resizing = False
        super(ResizableRectItem, self).mouseReleaseEvent(event)

    def onEdge(self, pos):
        rect = self.rect()
        if (abs(pos.x() - rect.left()) < self.cursorChangeThreshold and abs(pos.y() - rect.top()) < self.cursorChangeThreshold):
            self.pos = 'TL' # top, left
            return True
        elif (abs(pos.x() - rect.right()) < self.cursorChangeThreshold and abs(pos.y() - rect.bottom()) < self.cursorChangeThreshold):
            self.pos = 'BR' # bottom, right
            return True
        elif (abs(pos.x() - rect.left()) < self.cursorChangeThreshold and abs(pos.y() - rect.bottom()) < self.cursorChangeThreshold):
            self.pos = 'BL' # bottom, left
            return True
        elif (abs(pos.x() - rect.right()) < self.cursorChangeThreshold and abs(pos.y() - rect.top()) < self.cursorChangeThreshold):
            self.pos = 'TR' # top, right
            return True
        return False

    def resizeRect(self, newPos):
        rect = self.dragStartRect.normalized()
        if self.pos:
            if self.pos =='TL' or self.pos =='BL':  # left
                rect.setLeft(newPos.x())
            elif self.pos =='TR' or self.pos =='BR': # right
                rect.setRight(newPos.x())
            if self.pos =='TR' or self.pos =='TL': # top
                rect.setTop(newPos.y())
            elif self.pos =='BR' or self.pos =='BL': # bottom
                rect.setBottom(newPos.y())

        # Ensure the rectangle does not exceed plot boundaries
        rect = self.validateRect(rect)

        self.setRect(rect)
        self.parent.update_overlay(rect)

    def validateRect(self, rect):
        plot_width, plot_height = self.parent.x_range, self.parent.y_range  # Assuming these are the plot dimensions
        if rect.left() < 0:
            rect.setLeft(0)
        if rect.top() < 0:
            rect.setTop(0)
        if rect.right() > plot_width:
            rect.setRight(plot_width)
        if rect.bottom() > plot_height:
            rect.setBottom(plot_height)
        return rect



# Polygons
# -------------------------------

class Polygon:
    def __init__(self, p_id):
        self.p_id = p_id
        self.points = []  # List to store points as (x, y, scatter)
        self.lines = []  # List to store lines as graphical items


# class PolygonManager:
#     """Operations related to polygon generation and manipulation

#     Polygons can be used to select or exclude regions of maps for analysis.

#     Methods
#     -------
#     increment_pid()
#         creates a new polygon pid for addressing polygon when toolButtonPolyCreate is checked
#     plot_polygon_scatter:

#     distance_to_line_segment:
#     show_polygon_lines:
#     update_table_widget:
#     """
#     def __init__(self, main_window):
#         self.main_window = main_window
#         self.polygons = {}          #dict of polygons
#         self.lines ={}              #temp dict for lines in polygon
#         self.point_index = None             # index for move point
#         self.p_id = None           # polygon ID
#         self.p_id_gen = 0 #Polygon_id generator

#     def add_samples(self):
#         #add sample id to dictionary
#         for sample_id in self.main_window.sample_ids:
#             if sample_id not in self.polygons:
#                 self.polygons[sample_id] = {}

#     # Method to increment p_id_gen
#     def increment_pid(self):
#         """Creates new polygon pid

#         When toolButtonPolyCreate is checked, a new polygon pid is created.
#         """
#         self.main_window.toolButtonPolyCreate.isChecked()
#         self.p_id_gen += 1
#         self.p_id = self.p_id_gen
#         self.main_window.actionClearFilters.setEnabled(True)
#         self.main_window.actionPolygonMask.setEnabled(True)
#         self.main_window.actionPolygonMask.setChecked(True)

#     def plot_polygon_scatter(self, event,k, x, y, x_i, y_i):
#         #create profile dict for this sample if it doesnt exisist
#         if self.main_window.sample_id not in self.polygons:
#             self.polygons[self.main_window.sample_id] = {}
#             self.lines[self.main_window.sample_id] = {}

#         self.array_x = self.main_window.array.shape[1]
#         self.array_y = self.main_window.array.shape[0]
#         # turn off profile (need to suppress context menu on right click)
#         if event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyCreate.isChecked():
#             self.main_window.toolButtonPolyCreate.setChecked(False)
#             self.main_window.toolButtonPolyMovePoint.setEnabled(True)

#             # Finalize and draw the polygon
#             self.show_polygon_lines(x,y, complete = True)

#             return
#         elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyMovePoint.isChecked():
#             self.main_window.toolButtonPolyMovePoint.setChecked(False)
#             self.main_window.point_selected = False
#             return

#         elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyAddPoint.isChecked():
#             self.main_window.toolButtonPolyAddPoint.setChecked(False)
#             return

#         elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyRemovePoint.isChecked():
#             self.main_window.toolButtonPolyRemovePoint.setChecked(False)
#             return
#         elif event.button() == QtCore.Qt.RightButton or event.button() == QtCore.Qt.MiddleButton:
#             return

#         elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyMovePoint.isChecked():
#             # move point
#             selection_model = self.main_window.tableWidgetPolyPoints.selectionModel()

#             # Check if there is any selection
#             if selection_model.hasSelection():
#                 selected_rows = selection_model.selectedRows()
#                 if selected_rows:
#                     # Assuming you're interested in the first selected row
#                     first_selected_row = selected_rows[0].row()

#                     # Get the item in the first column of this row
#                     item = self.main_window.tableWidgetPolyPoints.item(first_selected_row, 0)

#                     # Check if the item is not None
#                     if item is not None:
#                         self.p_id = int(item.text())  # Get polygon id to move point

#                     else:
#                         QMessageBox.warning(self.main_window, "Selection Error", "No item found in the first column of the selected row.")
#                 else:
#                     QMessageBox.warning(self.main_window, "Selection Error", "No row is selected.")
#             else:
#                 QMessageBox.warning(self.main_window, "Selection Error", "No selection is made in the table.")


#             if self.main_window.point_selected:
#                 #remove selected point
#                 prev_scatter = self.polygons[self.main_window.sample_id][self.p_id][self.point_index][2]
#                 self.main_window.plot.removeItem(prev_scatter)


#                 # Create a scatter plot item at the clicked position
#                 scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
#                 scatter.setZValue(1e9)
#                 self.main_window.plot.addItem(scatter)


#                 #update self.point_index index of self.polygons[self.main_window.sample_id]with new point data

#                 self.polygons[self.main_window.sample_id][self.p_id][self.point_index] = (x,y, scatter)

#                 # Finalize and draw the polygon
#                 self.show_polygon_lines(x,y, complete = True)

#                 self.main_window.point_selected = False
#                 #update plot and table widget
#                 # self.update_table_widget()
#             else:
#                 # find nearest profile point
#                 mindist = 10**12
#                 for i, (x_p,y_p,_) in enumerate(self.polygons[self.main_window.sample_id][self.p_id]):
#                     dist = (x_p - x)**2 + (y_p - y)**2
#                     if mindist > dist:
#                         mindist = dist
#                         self.point_index = i
#                 if (round(mindist*self.array_x/self.main_window.x_range) < 50):
#                     self.main_window.point_selected = True


#         elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyAddPoint.isChecked():
#             # add point
#             # user must first choose line of polygon
#             # choose the vertext points to add point based on line
#             # Find the closest line segment to the click location
#             min_distance = float('inf')
#             insert_after_index = None
#             for i in range(len(self.polygons[self.main_window.sample_id][self.p_id])):
#                 p1 = self.polygons[self.main_window.sample_id][self.p_id][i]
#                 p2 = self.polygons[self.main_window.sample_id][self.p_id][(i + 1) % len(self.polygons[self.main_window.sample_id][self.p_id])]  # Loop back to the start for the last segment
#                 dist = self.distance_to_line_segment(x, y, p1[0], p1[1], p2[0], p2[1])
#                 if dist < min_distance:
#                     min_distance = dist
#                     insert_after_index = i

#             # Insert the new point after the closest line segment
#             if insert_after_index is not None:
#                 scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
#                 scatter.setZValue(1e9)
#                 self.main_window.plot.addItem(scatter)
#                 self.polygons[self.main_window.sample_id][self.p_id].insert(insert_after_index + 1, (x, y, scatter))

#             # Redraw the polygon with the new point
#             self.show_polygon_lines(x, y, complete=True)

#         elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyRemovePoint.isChecked():
#             # remove point
#             # draw polygon without selected point
#             # remove point
#             # Find the closest point to the click location
#             min_distance = float('inf')
#             point_to_remove_index = None
#             for i, (px, py, _) in enumerate(self.polygons[self.main_window.sample_id][self.p_id]):
#                 dist = ((px - x)**2 + (py - y)**2)**0.5
#                 if dist < min_distance:
#                     min_distance = dist
#                     point_to_remove_index = i

#             # Remove the closest point
#             if point_to_remove_index is not None:
#                 _, _, scatter_item = self.polygons[self.main_window.sample_id][self.p_id].pop(point_to_remove_index)
#                 self.main_window.plot.removeItem(scatter_item)

#             # Redraw the polygon without the removed point
#             self.show_polygon_lines(x, y, complete=True)

#             self.main_window.toolButtonPolyRemovePoint.setChecked(False)

#         elif event.button() == QtCore.Qt.LeftButton:
#             # Create a scatter self.main_window.plot item at the clicked position
#             scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
#             scatter.setZValue(1e9)
#             self.main_window.plot.addItem(scatter)

#             # add x and y to self.polygons[self.main_window.sample_id] dict
#             if self.p_id not in self.polygons[self.main_window.sample_id]:
#                 self.polygons[self.main_window.sample_id][self.p_id] = [(x,y, scatter)]

#             else:
#                 self.polygons[self.main_window.sample_id][self.p_id].append((x,y, scatter))

#     def distance_to_line_segment(self, px, py, x1, y1, x2, y2):
#         """Computes distance to the line segment of a polygon

#         Determines the minimum distance from a point (px,py) to a line segment defined by
#         the points (x1,y1) and (x2,y2).

#         Parameters
#         ----------
#         px, py : float
#             Point used to determine minimum distance
#         x1, y1 : float
#             Point 1 on a line
#         x2, y2 : float
#             Point 2 on a line

#         Returns
#         -------
#         float
#             Minimum distance from point to a line
#         """        
#         # Calculate the distance from point (px, py) to the line segment defined by points (x1, y1) and (x2, y2)
#         # This is a simplified version; you might need a more accurate calculation based on your coordinate system
#         return min(((px - x1)**2 + (py - y1)**2)**0.5, ((px - x2)**2 + (py - y2)**2)**0.5)

#     def show_polygon_lines(self, x,y, complete = False):
#         if self.main_window.sample_id in self.polygons:
#             if self.p_id in self.polygons[self.main_window.sample_id]:
#                 # Remove existing temporary line(s) if any
#                 if self.p_id in self.lines[self.main_window.sample_id]:
#                     for line in self.lines[self.main_window.sample_id][self.p_id]:
#                         self.main_window.plot.removeItem(line)
#                 self.lines[self.main_window.sample_id][self.p_id] = []

#                 points = self.polygons[self.main_window.sample_id][self.p_id]
#                 if len(points) == 1:
#                     # Draw line from the first point to cursor
#                     line = PlotDataItem([points[0][0], x], [points[0][1], y], pen='r')
#                     self.main_window.plot.addItem(line)
#                     self.lines[self.main_window.sample_id][self.p_id].append(line)
#                 elif not complete and len(points) > 1:

#                     if self.main_window.point_selected:
#                         # self.point_index is the index of the pont that needs to be moved

#                         # create polygon with moved point
#                         x_points = [p[0] for p in points[:self.point_index]] + [x]+ [p[0] for p in points[(self.point_index+1):]]
#                         y_points = [p[1] for p in points[:self.point_index]] + [y]+ [p[1] for p in points[(self.point_index+1):]]

#                     else:

#                         # create polygon with new point
#                         x_points = [p[0] for p in points] + [x, points[0][0]]
#                         y_points = [p[1] for p in points] + [y, points[0][1]]
#                     # Draw shaded polygon + lines to cursor
#                     poly_item = QGraphicsPolygonItem(QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in zip(x_points, y_points)]))
#                     poly_item.setBrush(QtGui.QColor(100, 100, 150, 100))
#                     self.main_window.plot.addItem(poly_item)
#                     self.lines[self.main_window.sample_id][self.p_id].append(poly_item)

#                     # Draw line from last point to cursor
#                     # line = PlotDataItem([points[-1][0], x], [points[-1][1], y], pen='r')
#                     # self.main_window.plot.addItem(line)
#                     # self.lines[self.main_window.sample_id][self.p_id].append(line)

#                 elif complete and len(points) > 2:
#                     points = [QtCore.QPointF(x, y) for x, y, _ in self.polygons[self.main_window.sample_id][self.p_id]]
#                     polygon = QtGui.QPolygonF(points)
#                     poly_item = QGraphicsPolygonItem(polygon)
#                     poly_item.setBrush(QtGui.QColor(100, 100, 150, 100))
#                     self.main_window.plot.addItem(poly_item)
#                     self.lines[self.main_window.sample_id][self.p_id].append(poly_item)

#                     self.update_table_widget()
#                     # Find the row where the first column matches self.p_id and select it
#                     for row in range(self.main_window.tableWidgetPolyPoints.rowCount()):
#                         item = self.main_window.tableWidgetPolyPoints.item(row, 0)  # Assuming the ID is stored in the first column
#                         if item and int(item.text()) == self.p_id:
#                             self.main_window.tableWidgetPolyPoints.selectRow(row)
#                             break

#     def update_table_widget(self):
#         """Update polygon table

#         Updates ``MainWindow.tableWidgetPolyPoints`` with 
#         """        
#         if self.main_window.sample_id in self.polygons: #if polygons for that sample if exists

#             self.main_window.tableWidgetPolyPoints.clearContents()  # Clear existing rows
#             self.main_window.tableWidgetPolyPoints.setRowCount(0)

#             for pid, val in self.polygons[self.main_window.sample_id].items():
#                 row_position = self.main_window.tableWidgetPolyPoints.rowCount()
#                 self.main_window.tableWidgetPolyPoints.insertRow(row_position)

#                 # Fill in the data
#                 self.main_window.tableWidgetPolyPoints.setItem(row_position, 0, QTableWidgetItem(str(pid)))
#                 self.main_window.tableWidgetPolyPoints.setItem(row_position, 1, QTableWidgetItem(f'poly {pid}'))
#                 self.main_window.tableWidgetPolyPoints.setItem(row_position, 2, QTableWidgetItem(str('')))
#                 self.main_window.tableWidgetPolyPoints.setItem(row_position, 3, QTableWidgetItem(str('In')))

#                 # Create a QCheckBox
#                 checkBox = QCheckBox()
#                 checkBox.setChecked(True) # Set its checked state

#                 # Connect the stateChanged signal
#                 checkBox.stateChanged.connect(lambda: self.main_window.apply_polygon_mask(update_plot=True))

#                 # Add the checkbox to the table
#                 self.main_window.tableWidgetPolyPoints.setCellWidget(row_position, 4, checkBox)

#         # update polygon mask
#         self.main_window.apply_polygon_mask(update_plot=True)

#     def clear_lines(self):
#         if self.p_id in self.polygons[self.main_window.sample_id]:
#             # Remove existing temporary line(s) if any
#             if self.p_id in self.lines[self.main_window.sample_id]:
#                 for line in self.lines[self.main_window.sample_id][self.p_id]:
#                     self.main_window.plot.removeItem(line)
#             self.lines[self.main_window.sample_id][self.p_id] = []

#     def clear_polygons(self):
#         if self.main_window.sample_id in self.polygons:
#             self.main_window.tableWidgetPolyPoints.clearContents()
#             self.main_window.tableWidgetPolyPoints.setRowCount(0)
#             self.clear_lines()
#             self.lines[self.main_window.sample_id] ={}              #temp dict for lines in polygon
#             self.point_index = None             # index for move point
#             self.p_id = None           # polygon ID
#             self.p_id_gen = 0 #Polygon_id generator

class PolygonManager:
    """Operations related to polygon generation and manipulation

    Polygons can be used to select or exclude regions of maps for analysis.

    Methods
    -------
    increment_pid()
        creates a new polygon pid for addressing polygon when toolButtonPolyCreate is checked
    plot_polygon_scatter:

    distance_to_line_segment:
    show_polygon_lines:
    update_table_widget:
    """
    def __init__(self, main_window):
        self.main_window = main_window
        self.polygons = {}  # Dict to store polygons for each sample
        self.p_id = None  # Current polygon ID
        self.p_id_gen = 0  # Polygon ID generator
        self.point_index = None             # index for move point
        # plot selected polygon from table
        self.main_window.tableWidgetPolyPoints.selectionModel().selectionChanged.connect(lambda: self.view_selected_polygon)

    def add_samples(self):
        for sample_id in self.main_window.sample_ids:
            if sample_id not in self.polygons:
                self.polygons[sample_id] = {}

    def increment_pid(self):
        """Creates a new polygon ID"""
        self.p_id_gen += 1
        self.p_id = self.p_id_gen
        # Create new polygon instance
        self.polygons[self.main_window.sample_id][self.p_id] = Polygon(self.p_id)
        self.main_window.actionClearFilters.setEnabled(True)
        self.main_window.actionPolygonMask.setEnabled(True)
        self.main_window.actionPolygonMask.setChecked(True)

    def save_polygons(self, project_dir, sample_id):
        """Save polygons to a file"""
        if sample_id in self.polygons:
            for p_id, polygon in self.polygons[sample_id].items():
                file_name = os.path.join(project_dir, sample_id, f'polygon_{p_id}.plgn')
                serializable_polygon = self.transform_polygon_for_pickling(polygon)
                with open(file_name, 'wb') as file:
                    pickle.dump(serializable_polygon, file)
            print("Polygons saved successfully.")

    def load_polygons(self, project_dir, sample_id):
        """Load polygons from a file"""
        directory = os.path.join(project_dir, sample_id)
        for file_name in os.listdir(directory):
            if file_name.endswith(".plgn"):
                file_path = os.path.join(directory, file_name)
                with open(file_path, 'rb') as file:
                    serializable_polygon = pickle.load(file)
                    polygon = self.reconstruct_polygon(serializable_polygon)
                    p_id = polygon.p_id
                    self.polygons[sample_id][p_id] = polygon
        self.update_table_widget()
        print("Polygons loaded successfully.")

    def transform_polygon_for_pickling(self, polygon):
        """Transform the polygon into a serializable format"""
        serializable_polygon = {
            'p_id': polygon.p_id,
            'points': [],
            'polygon_points': [],  # To store points of QGraphicsPolygonItem
            'lines':[]
        }

        for point in polygon.points:
            x, y, scatter = point
            scatter_state = self.extract_scatter_plot_state(scatter)
            serializable_polygon['points'].append((x, y, scatter_state))

        for line in polygon.lines:
            if isinstance(line, QGraphicsPolygonItem):
                polygon_points = [line.polygon() for line in polygon.lines]
                serializable_polygon['polygon_points'] = [[(point.x(), point.y()) for point in poly] for poly in polygon_points]
            else:
                # Assuming lines are stored as tuples of data points (x1, y1, x2, y2)
                serializable_polygon['lines'].append(line.getData())
        return serializable_polygon

    def extract_scatter_plot_state(self, scatter):
        """Extract the state of a scatter plot item"""
        data = scatter.getData()
        symbol = scatter.opts['symbol']
        size = scatter.opts['size']
        z_value = scatter.zValue()
        return {'data': data, 'symbol': symbol, 'size': size, 'z_value': z_value}

    def reconstruct_polygon(self, serializable_polygon):
        """Reconstruct a polygon from a serializable format"""
        polygon = Polygon(serializable_polygon['p_id'])
        for point in serializable_polygon['points']:
            x, y, scatter_state = point
            scatter = self.recreate_scatter_plot(scatter_state)
            polygon.points.append((x, y, scatter))

        for line_data in serializable_polygon['lines']:
            line = PlotDataItem(line_data[0], line_data[1], pen='r')
            polygon.lines.append(line)

        # Reconstruct the QGraphicsPolygonItem using the saved points
        for polygon_points in serializable_polygon['polygon_points']:
            polygon_item = QGraphicsPolygonItem()
            polygon_path = QtGui.QPainterPath()
            if polygon_points:
                polygon_path.moveTo(polygon_points[0][0], polygon_points[0][1])
                for point in polygon_points[1:]:
                    polygon_path.lineTo(point[0], point[1])
                polygon_item.setPolygon(QtGui.QPolygonF(polygon_path.toFillPolygon()))
                polygon_item.setBrush(QtGui.QColor(100, 100, 150, 100))
                polygon.lines.append(polygon_item)
            return polygon

    def recreate_scatter_plot(self, state):
        """Recreate a scatter plot item from a saved state"""
        scatter = ScatterPlotItem(state['data'][0], state['data'][1], symbol=state['symbol'], size=state['size'])
        scatter.setZValue(state['z_value'])
        return scatter

    def plot_polygon_scatter(self, event,k, x, y, x_i, y_i):
        if self.p_id in self.polygons[self.main_window.sample_id]:
            points = self.polygons[self.main_window.sample_id][self.p_id].points
            print('p')
        self.array_x = self.main_window.array.shape[1]
        self.array_y = self.main_window.array.shape[0]
        # turn off profile (need to suppress context menu on right click)
        if event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyCreate.isChecked():
            self.main_window.toolButtonPolyCreate.setChecked(False)
            self.main_window.toolButtonPolyMovePoint.setEnabled(True)

            # Finalize and draw the polygon
            self.show_polygon_lines(x,y, complete = True)

            return
        elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyMovePoint.isChecked():
            self.main_window.toolButtonPolyMovePoint.setChecked(False)
            self.main_window.point_selected = False
            return

        elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyAddPoint.isChecked():
            self.main_window.toolButtonPolyAddPoint.setChecked(False)
            return

        elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPolyRemovePoint.isChecked():
            self.main_window.toolButtonPolyRemovePoint.setChecked(False)
            return
        elif event.button() == QtCore.Qt.RightButton or event.button() == QtCore.Qt.MiddleButton:
            return

        elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyMovePoint.isChecked():
            # move point
            selection_model = self.main_window.tableWidgetPolyPoints.selectionModel()

            # Check if there is any selection
            if selection_model.hasSelection():
                selected_rows = selection_model.selectedRows()
                if selected_rows:
                    # Assuming you're interested in the first selected row
                    first_selected_row = selected_rows[0].row()

                    # Get the item in the first column of this row
                    item = self.main_window.tableWidgetPolyPoints.item(first_selected_row, 0)

                    # Check if the item is not None
                    if item is not None:
                        self.p_id = int(item.text())  # Get polygon id to move point

                    else:
                        QMessageBox.warning(self.main_window, "Selection Error", "No item found in the first column of the selected row.")
                else:
                    QMessageBox.warning(self.main_window, "Selection Error", "No row is selected.")
            else:
                QMessageBox.warning(self.main_window, "Selection Error", "No selection is made in the table.")


            if self.main_window.point_selected:
                #remove selected point
                prev_scatter = points[self.point_index][2]
                self.main_window.plot.removeItem(prev_scatter)


                # Create a scatter plot item at the clicked position
                scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                scatter.setZValue(1e9)
                self.main_window.plot.addItem(scatter)


                #update self.point_index index of self.polygons[self.main_window.sample_id]with new point data

                points[self.point_index] = (x,y, scatter)

                # Finalize and draw the polygon
                self.show_polygon_lines(x,y, complete = True)

                self.main_window.point_selected = False
                #update plot and table widget
                # self.update_table_widget()
            else:
                # find nearest profile point
                mindist = 10**12
                for i, (x_p,y_p,_) in enumerate(points):
                    dist = (x_p - x)**2 + (y_p - y)**2
                    if mindist > dist:
                        mindist = dist
                        self.point_index = i
                if (round(mindist*self.array_x/self.main_window.x_range) < 50):
                    self.main_window.point_selected = True


        elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyAddPoint.isChecked():
            # add point
            # user must first choose line of polygon
            # choose the vertext points to add point based on line
            # Find the closest line segment to the click location
            min_distance = float('inf')
            insert_after_index = None
            for i in range(len(points)):
                p1 = points[i]
                p2 = points[(i + 1) % len(points)]  # Loop back to the start for the last segment
                dist = self.distance_to_line_segment(x, y, p1[0], p1[1], p2[0], p2[1])
                if dist < min_distance:
                    min_distance = dist
                    insert_after_index = i

            # Insert the new point after the closest line segment
            if insert_after_index is not None:
                scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                scatter.setZValue(1e9)
                self.main_window.plot.addItem(scatter)
                points.insert(insert_after_index + 1, (x, y, scatter))

            # Redraw the polygon with the new point
            self.show_polygon_lines(x, y, complete=True)

        elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyRemovePoint.isChecked():
            # remove point
            # draw polygon without selected point
            # remove point
            # Find the closest point to the click location
            min_distance = float('inf')
            point_to_remove_index = None
            for i, (px, py, _) in enumerate(points.points):
                dist = ((px - x)**2 + (py - y)**2)**0.5
                if dist < min_distance:
                    min_distance = dist
                    point_to_remove_index = i

            # Remove the closest point
            if point_to_remove_index is not None:
                _, _, scatter_item = points.pop(point_to_remove_index)
                self.main_window.plot.removeItem(scatter_item)

            # Redraw the polygon without the removed point
            self.show_polygon_lines(x, y, complete=True)

            self.main_window.toolButtonPolyRemovePoint.setChecked(False)

        elif event.button() == QtCore.Qt.LeftButton:
            # Create a scatter self.main_window.plot item at the clicked position
            scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
            scatter.setZValue(1e9)
            self.main_window.plot.addItem(scatter)

            # add x and y to self.polygons[self.main_window.sample_id] dict
            if self.p_id not in self.polygons[self.main_window.sample_id]:
                points = [(x,y, scatter)]

            else:
                points.append((x,y, scatter))

    def distance_to_line_segment(self, px, py, x1, y1, x2, y2):
        """Computes distance to the line segment of a polygon

        Determines the minimum distance from a point (px,py) to a line segment defined by
        the points (x1,y1) and (x2,y2).

        Parameters
        ----------
        px, py : float
            Point used to determine minimum distance
        x1, y1 : float
            Point 1 on a line
        x2, y2 : float
            Point 2 on a line

        Returns
        -------
        float
            Minimum distance from point to a line
        """        
        # Calculate the distance from point (px, py) to the line segment defined by points (x1, y1) and (x2, y2)
        # This is a simplified version; you might need a more accurate calculation based on your coordinate system
        return min(((px - x1)**2 + (py - y1)**2)**0.5, ((px - x2)**2 + (py - y2)**2)**0.5)

    def show_polygon_lines(self, x,y, complete = False):
        
        if self.p_id in self.polygons[self.main_window.sample_id]:
            lines = self.polygons[self.main_window.sample_id][self.p_id].lines
            # Remove existing temporary line(s) if any
            for line in lines:
                self.main_window.plot.removeItem(line)
            lines.clear()
            points = self.polygons[self.main_window.sample_id][self.p_id].points
            if len(points) == 1:
                # Draw line from the first point to cursor
                line = PlotDataItem([points[0][0], x], [points[0][1], y], pen='r')
                self.main_window.plot.addItem(line)
                lines.append(line)
            elif not complete and len(points) > 1:

                if self.main_window.point_selected:
                    # self.point_index is the index of the pont that needs to be moved

                    # create polygon with moved point
                    x_points = [p[0] for p in points[:self.point_index]] + [x]+ [p[0] for p in points[(self.point_index+1):]]
                    y_points = [p[1] for p in points[:self.point_index]] + [y]+ [p[1] for p in points[(self.point_index+1):]]

                else:

                    # create polygon with new point
                    x_points = [p[0] for p in points] + [x, points[0][0]]
                    y_points = [p[1] for p in points] + [y, points[0][1]]
                # Draw shaded polygon + lines to cursor
                poly_item = QGraphicsPolygonItem(QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in zip(x_points, y_points)]))
                poly_item.setBrush(QtGui.QColor(100, 100, 150, 100))
                self.main_window.plot.addItem(poly_item)
                lines.append(poly_item)

                # Draw line from last point to cursor
                # line = PlotDataItem([points[-1][0], x], [points[-1][1], y], pen='r')
                # self.main_window.plot.addItem(line)
                # lines.append(line)

            elif complete and len(points) > 2:
                points = [QtCore.QPointF(x, y) for x, y, _ in points]
                polygon = QtGui.QPolygonF(points)
                poly_item = QGraphicsPolygonItem(polygon)
                poly_item.setBrush(QtGui.QColor(100, 100, 150, 100))
                self.main_window.plot.addItem(poly_item)
                lines.append(poly_item)

                self.update_table_widget()
                # Find the row where the first column matches self.p_id and select it
                for row in range(self.main_window.tableWidgetPolyPoints.rowCount()):
                    item = self.main_window.tableWidgetPolyPoints.item(row, 0)  # Assuming the ID is stored in the first column
                    if item and int(item.text()) == self.p_id:
                        self.main_window.tableWidgetPolyPoints.selectRow(row)
                        break


    def update_table_widget(self):
        """Update the polygon table"""
        if self.main_window.sample_id in self.polygons:
            self.main_window.tableWidgetPolyPoints.clearContents()
            self.main_window.tableWidgetPolyPoints.setRowCount(0)

            for p_id, polygon in self.polygons[self.main_window.sample_id].items():
                row_position = self.main_window.tableWidgetPolyPoints.rowCount()
                self.main_window.tableWidgetPolyPoints.insertRow(row_position)

                self.main_window.tableWidgetPolyPoints.setItem(row_position, 0, QTableWidgetItem(str(p_id)))
                self.main_window.tableWidgetPolyPoints.setItem(row_position, 1, QTableWidgetItem(f'Polygon {p_id}'))
                self.main_window.tableWidgetPolyPoints.setItem(row_position, 2, QTableWidgetItem(str('')))
                self.main_window.tableWidgetPolyPoints.setItem(row_position, 3, QTableWidgetItem('In'))

                checkBox = QCheckBox()
                checkBox.setChecked(True)
                checkBox.stateChanged.connect(lambda: self.main_window.apply_polygon_mask(update_plot=True))
                self.main_window.tableWidgetPolyPoints.setCellWidget(row_position, 4, checkBox)

        self.main_window.apply_polygon_mask(update_plot=False)

    def clear_lines(self):
            if self.p_id in self.polygons[self.main_window.sample_id]:
                # Remove existing temporary line(s) if any
                for line in self.polygons[self.main_window.sample_id][self.p_id].lines:
                    self.main_window.plot.removeItem(line)

    def clear_polygons(self):
        if self.main_window.sample_id in self.polygons:
            self.main_window.tableWidgetPolyPoints.clearContents()
            self.main_window.tableWidgetPolyPoints.setRowCount(0)

            for polygon in self.polygons[self.main_window.sample_id].values():
                for point in polygon.points:
                    _, _, scatter_item = point
                    self.main_window.plot.removeItem(scatter_item)
                for line in polygon.lines:
                    self.main_window.plot.removeItem(line)

            self.polygons[self.main_window.sample_id] = {}
            self.point_index = None             # index for move point
            self.p_id = None           # polygon ID
            self.p_id_gen = 0 #Polygon_id generator

    def plot_existing_polygon(self, plot, p_id= None):
        """Plot the first existing polygon for the current sample ID.

        If there are polygons for the sample ID, select the row in the table widget
        and plot the first polygon with its points and lines.
        """
        sample_id = self.main_window.sample_id

        if sample_id in self.polygons:
            if len(self.polygons[sample_id])>0: #if polygons exist
                if not p_id:
                    # Get the first polygon ID and its corresponding polygon object
                    p_id = next(iter(self.polygons[sample_id]))
                
                polygon = self.polygons[sample_id][p_id]
                

                # Clear any existing selections in the table
                self.main_window.tableWidgetPolyPoints.clearSelection()

                # Find the row where the first column matches the first polygon ID and select it
                for row in range(self.main_window.tableWidgetPolyPoints.rowCount()):
                    item = self.main_window.tableWidgetPolyPoints.item(row, 0)  # Assuming the ID is stored in the first column
                    if item and int(item.text()) == p_id:
                        self.main_window.tableWidgetPolyPoints.selectRow(row)
                        break

                # Plot the points for the polygon
                for x, y, scatter in polygon.points:
                    scatter.setParentItem(None)  # Ensure the scatter is removed from any previous plots
                    scatter.setZValue(1e9)  # Ensure it is drawn on top
                    plot.addItem(scatter)

                # Plot the lines for the polygon
                for line_data in polygon.lines:
                    if isinstance(line_data, QGraphicsPolygonItem):
                        # Re-add the polygon shape to the plot
                        plot.addItem(line_data)
                    else:
                        # Assume line_data is from PlotDataItem or similar and contains (x, y) data
                        line_data = PlotDataItem(line_data[0], line_data[1], pen='r')
                        line_data.setParentItem(None)  # Ensure the line is removed from any previous plots
                        plot.addItem(line_data)

    def view_selected_polygon(self):
        """View the selected polygon when a selection is made in the table widget."""
        sample_id = self.main_window.sample_id

        if sample_id in self.polygons:
            # Get the selected rows in the table widget
            selected_rows = self.main_window.tableWidgetPolyPoints.selectionModel().selectedRows()

            if selected_rows:
                # Assume only one row can be selected at a time for simplicity
                selected_row = selected_rows[0]
                polygon_id_item = self.main_window.tableWidgetPolyPoints.item(selected_row.row(), 0)

                if polygon_id_item:
                    polygon_id = int(polygon_id_item.text())

                    if polygon_id in self.polygons[sample_id]:
                        # Clear the plot before adding the new polygon
                        self.clear_plot()

                        # Plot the selected polygon
                        self.plot_existing_polygon( self.main_window.plot, polygon_id)

    def clear_plot(self):
        """Clear all existing polygons from the plot."""
        for sample_id, polygons in self.polygons.items():
            for polygon in polygons.values():
                for _, _, scatter in polygon.points:
                    self.main_window.plot.removeItem(scatter)
                for line in polygon.lines:
                    self.main_window.plot.removeItem(line)


# Profiles
# -------------------------------
class Profile:
    def __init__(self,name,sort,radius,thresh,int_dist, point_error):
        self.name = name  
        self.points = {}
        self.i_points = {}
        self.sort = sort
        self.radius = radius
        self.y_axis_thresh = thresh
        self.int_dist = int_dist
        self.point_error = point_error


class Profiling:
    def __init__(self,main_window):
        self.main_window = main_window
        # Initialize other necessary attributes
        # Initialize variables and states as needed
        self.profiles = {}
        self.point_selected = False  # move point button selected
        self.point_index = -1              # index for move point
        self.all_errorbars = []       #stores points of profiles
        self.selected_points = {}  # Track selected points, e.g., {point_index: selected_state}
        self.edit_mode_enabled = False  # Track if edit mode is enabled
        self.original_colors = {}
        self.profile_name = None

    def add_samples(self):
        #add sample id to dictionary
        for sample_id in self.main_window.sample_ids:
            if sample_id not in self.profiles:
                self.profiles[sample_id] = {}
        

    # def save_profiles(self,project_dir, sample_id):
    #     if sample_id in self.profiles:
    #         for profile_name, profile in self.profiles[sample_id].items():
    #             file_name =  os.path.join(project_dir,sample_id,f'{profile_name}.prfl')
    #             with open(file_name, 'wb') as file:
    #                 pickle.dump(profile, file)
    #         print("Profile saved successfully.")



    def save_profiles(self, project_dir, sample_id):
        if sample_id in self.profiles:
            for profile_name, profile in self.profiles[sample_id].items():
                file_name = os.path.join(project_dir, sample_id, f'{profile_name}.prfl')
                serializable_profile = self.transform_profile_for_pickling(profile)
                with open(file_name, 'wb') as file:
                    pickle.dump(serializable_profile, file)
            print("Profile saved successfully.")

    def load_profiles(self, project_dir, sample_id):
        directory = os.path.join(project_dir, sample_id)
        for file_name in os.listdir(directory):
            if file_name.endswith(".prfl"):
                file_path = os.path.join(directory, file_name)
                with open(file_path, 'rb') as file:
                    profile_name = os.path.basename(file_path).split('.')[0]
                    serializable_profile = pickle.load(file)
                    profile = self.reconstruct_profile(serializable_profile)
                    self.profiles[sample_id][profile_name] = profile
        self.populate_combobox()
        print("All profiles loaded successfully.")

    def transform_profile_for_pickling(self, profile):
        serializable_profile = {
            'name': profile.name,
            'sort': profile.sort,
            'radius': profile.radius,
            'y_axis_thresh': profile.y_axis_thresh,
            'int_dist': profile.int_dist,
            'point_error': profile.point_error,
            'points': {},
            'i_points': {}
        }
        for (k, v), points in profile.points.items():
            serializable_points = []
            for point in points:
                x, y, circ_val, scatter, interpolate = point
                scatter_state = self.extract_scatter_plot_state(scatter)
                serializable_points.append((x, y, circ_val, scatter_state, interpolate))
            serializable_profile['points'][(k, v)] = serializable_points
        for (k, v), i_points in profile.i_points.items():
            serializable_i_points = []
            for point in i_points:
                x, y, circ_val, scatter, interpolate = point
                scatter_state = self.extract_scatter_plot_state(scatter)
                serializable_i_points.append((x, y, circ_val, scatter_state, interpolate))
            serializable_profile['i_points'][(k, v)] = serializable_i_points
        return serializable_profile

    def extract_scatter_plot_state(self, scatter):
        data = scatter.getData()
        symbol = scatter.opts['symbol']
        size = scatter.opts['size']
        z_value = scatter.zValue()
        return {'data': data, 'symbol': symbol, 'size': size, 'z_value': z_value}

    def recreate_scatter_plot(self, state):
        scatter = ScatterPlotItem(state['data'][0], state['data'][1], symbol=state['symbol'], size=state['size'])
        scatter.setZValue(state['z_value'])
        return scatter



    def reconstruct_profile(self, serializable_profile):
        profile = Profile(
            serializable_profile['name'],
            serializable_profile['sort'],
            serializable_profile['radius'],
            serializable_profile['y_axis_thresh'],
            serializable_profile['int_dist'],
            serializable_profile['point_error']
        )
        for (k, v), points in serializable_profile['points'].items():
            reconstructed_points = []
            for point in points:
                x, y, circ_val, scatter_state, interpolate = point
                scatter = self.recreate_scatter_plot(scatter_state)
                reconstructed_points.append((x, y, circ_val, scatter, interpolate))
            profile.points[(k, v)] = reconstructed_points
        for (k, v), i_points in serializable_profile['i_points'].items():
            reconstructed_i_points = []
            for point in i_points:
                x, y, circ_val, scatter_state, interpolate = point
                scatter = self.recreate_scatter_plot(scatter_state)
                reconstructed_i_points.append((x, y, circ_val, scatter, interpolate))
            profile.i_points[(k, v)] = reconstructed_i_points
        return profile
    
    def populate_combobox(self):
        self.main_window.comboBoxProfileList.clear()
        self.main_window.comboBoxProfileList.addItem('Create New Profile')
        for profile_name in self.profiles[self.main_window.sample_id].keys():
            self.main_window.comboBoxProfileList.addItem(profile_name)
        

    def load_profiles_from_directory(self, project_dir, sample_id):
        directory = os.path.join(project_dir,sample_id)
        for file_name in os.listdir(directory):
            if file_name.endswith(".prfl"):
                file_path = os.path.join(directory, file_name)
                with open(file_path, 'rb') as file:
                    profile_name = os.path.basename(file_path).split('.')[0]
                    self.profiles[sample_id][profile_name] = pickle.load(file)

        self.populate_combobox()
        print("All profiles loaded successfully.")

    def on_profile_selected(self, profile_name):
        if profile_name == 'Create New Profile':
            new_profile_name, ok = QInputDialog.getText(self.main_window, 'New Profile', 'Enter new profile name:')
            if ok and new_profile_name:
                if new_profile_name in self.profiles[self.main_window.sample_id]:
                    QMessageBox.warning(self.main_window, 'Error', 'Profile name already exists!')
                else:
                    self.clear_profiles()
                    sort = self.main_window.comboBoxProfileSort.currentText()
                    radius = self.main_window.lineEditPointRadius.text() 
                    thresh = self.main_window.lineEditPointRadius.text()
                    int_dist = self.main_window.lineEditIntDist.text()
                    point_error = self.main_window.comboBoxPointType.currentText()

                    # create new profile instance
                    self.profiles[self.main_window.sample_id][new_profile_name] = Profile(new_profile_name,sort,radius,thresh,int_dist, point_error)
                    # self.i_profiles[self.main_window.sample_id][new_profile_name] = {}
                    self.main_window.comboBoxProfileList.addItem(new_profile_name)
                    self.main_window.comboBoxProfileList.setCurrentText(new_profile_name)
                    self.profile_name = new_profile_name
            else:
                self.main_window.comboBoxProfileList.setCurrentIndex(0)  # Reset to 'Create New Profile'
        else:
            self.profile_name = profile_name
            self.plot_existing_profile(self.main_window.plot)
            profile = self.profiles[self.main_window.sample_id][self.profile_name]
            self.main_window.comboBoxProfileSort.setCurrentText(profile.sort)
            self.main_window.lineEditPointRadius.setText(profile.radius) 
            self.main_window.lineEditPointRadius.setText(profile.y_axis_thresh)
            self.main_window.lineEditIntDist.setText(profile.int_dist)
            self.main_window.comboBoxPointType.setCurrentText(profile.point_error)
            self.plot_profiles()
            self.update_table_widget()

    def cart_to_dist(self,pixel:int,direction = 'y') -> float:
        if direction == 'x':
            return pixel*self.main_window.array_size[1]/self.main_window.x_range
        else:
            return pixel*self.main_window.array_size[0]/self.main_window.y_range
    
    def dist_to_cart(self,dist:float, direction = 'y')-> int:
        if direction == 'x':
            return round(dist*self.main_window.dx)
        else:
            return round(dist*self.main_window.dy)

    def plot_profile_scatter(self, event, array,k,v, plot, x, y, x_i, y_i):
        #k is key (name of Analyte)
        #create profile dict particular sample if it doesnt exisist
        # if self.main_window.sample_id not in self.profiles:
        #     self.profiles[self.main_window.sample_id] = {}
        #     self.i_profiles[self.main_window.sample_id] = {}
        
        self.array_x = array.shape[1] #no of colmns
        self.array_y = array.shape[0] #no of rows
        interpolate = False
        radius= int(self.main_window.lineEditPointRadius.text())

        profile = self.profiles[self.main_window.sample_id][self.profile_name].points
        
        # turn off profile (need to suppress context menu on right click)
        if event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPlotProfile.isChecked():
            self.main_window.toolButtonPlotProfile.setChecked(False)
            self.main_window.toolButtonPointMove.setEnabled(True)
            return
        elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPointMove.isChecked():
            self.main_window.toolButtonPointMove.setChecked(False)
            self.point_selected = False
            return
        elif event.button() == QtCore.Qt.RightButton or event.button() == QtCore.Qt.MiddleButton:
            return



        elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPlotProfile.isChecked()) and self.main_window.toolButtonPointMove.isChecked():

            # move point
            if self.point_selected:
                #remove selected point
                prev_scatter = profile[k,v][self.point_index][3]
                plot.removeItem(prev_scatter)


                # Create a scatter plot item at the clicked position
                scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                scatter.setZValue(1e9)
                plot.addItem(scatter)
                # Find all points within the specified radius
                circ_val = []
                circ_cord = []

                p_radius_y = self.dist_to_cart(radius, 'y') # pixel radius in pixels y direction
                p_radius_x = self.dist_to_cart(radius, 'x') # pixel radius in pixels x direction
                
                for i in range(max(0, y_i - p_radius_y), min(self.array_y, y_i + p_radius_y + 1)):
                    for j in range(max(0, x_i - p_radius_x), min(self.array_x , x_i + p_radius_x + 1)):
                        if self.calculate_distance(self.cart_to_dist(y_i - i)**2 , self.cart_to_dist(x_i - j)**2) <= radius:
                            value = array[i, j]
                            circ_cord.append([i, j])
                            circ_val.append( value)


                # for i in range(max(0, y_i - radius), min(self.array_y, y_i + radius + 1)):
                #     for j in range(max(0, x_i - radius), min(self.array_x , x_i + radius + 1)):
                #         if np.sqrt((x_i - j)**2 + (y_i - i)**2) <= radius:
                #             value = array[i, j]
                #             circ_cord.append([i, j])
                #             circ_val.append( value)

                #update self.point_index index of self.profiles[self.self.profile_name] with new point data
                if (k,v) in profile:

                    profile[k,v][self.point_index] = (x,y, circ_val,scatter, interpolate)


                if self.main_window.canvasWindow.currentIndex() == self.main_window.canvas_tab['mv']:
                    # Add the scatter item to all other plots and save points in profile
                    for (k,v), (_, p, array) in self.main_window.lasermaps.items():
                        circ_val = []
                        if p != plot and v==1 and self.array_x ==array.shape[1] and self.array_y ==array.shape[0] : #only add scatters to other lasermaps of same sample
                            # Create a scatter plot item at the clicked position
                            scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                            scatter.setZValue(1e9)
                            p.addItem(scatter)
                            for c in circ_cord:
                                value = array[c[0], c[1]]
                                circ_val.append( value)
                            if (k,v) in profile:
                                profile[k,v][self.point_index] = (x,y, circ_val,scatter, interpolate)

                #update plot and table widget
                self.main_window.plot_profiles()
                self.update_table_widget()
                if self.main_window.toolButtonProfileInterpolate.isChecked(): #reset interpolation if selected
                    self.clear_interpolation()
                    self.interpolate_points(interpolation_distance=int(self.main_window.lineEditIntDist.text()), radius= int(self.main_window.lineEditPointRadius.text()))
            else:
                # find nearest profile point
                mindist = 10**12
                for i, (x_p,y_p,_,_,interpolate) in enumerate(profile[k]):
                    dist = (x_p - x)**2 + (y_p - y)**2
                    if mindist > dist:
                        mindist = dist
                        self.point_index = i
                if not(round(mindist*self.array_x/self.main_window.x_range) < 50):
                    self.point_selected = True


        elif event.button() == QtCore.Qt.LeftButton:  #plot profile
            #switch to profile tab
            self.main_window.tabWidget.setCurrentIndex(self.main_window.bottom_tab['profile'])

            # Create a scatter plot item at the clicked position
            scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
            scatter.setZValue(1e9)
            plot.addItem(scatter)
            # Find all points within the specified radius
            circ_val = []
            circ_cord = []
            p_radius_y = self.dist_to_cart(radius, 'y') # pixel radius in pixels y direction
            p_radius_x = self.dist_to_cart(radius, 'x') # pixel radius in pixels x direction
            
            for i in range(max(0, y_i - p_radius_y), min(self.array_y, y_i + p_radius_y + 1)):
                for j in range(max(0, x_i - p_radius_x), min(self.array_x , x_i + p_radius_x + 1)):
                    if self.calculate_distance(self.cart_to_dist(y_i - i) , self.cart_to_dist(x_i - j)) <= radius: # filter values that lies within radius
                        value = array[i, j]
                        circ_cord.append([i, j])
                        circ_val.append( value)

            #add values within circle of radius in profile
            if (k,v) in profile:
                profile[(k,v)].append((x,y,circ_val,scatter, interpolate))
            else:
                profile[(k,v)] = [(x,y, circ_val,scatter, interpolate)]


            if self.main_window.canvasWindow.currentIndex() == self.main_window.canvas_tab['mv']:
                # Add the scatter item to all other plots and save points in profile
                for (k,v), (_, p,  array) in self.main_window.lasermaps.items():
                    circ_val = []
                    if p != plot and v==1 and self.array_x ==array.shape[1] and self.array_y ==array.shape[0] : #only add scatters to other lasermaps of same sample
                        # Create a scatter plot item at the clicked position
                        scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                        scatter.setZValue(1e9)
                        p.addItem(scatter)
                        for c in circ_cord:
                            value = array[c[0], c[1]]
                            circ_val.append( value)
                        if (k,v) in profile:
                            profile[k,v].append((x,y,circ_val, interpolate))
                        else:
                            profile[k,v] = [(x,y, circ_val,scatter, interpolate)]

            self.plot_profiles()
            self.update_table_widget()
    
    def plot_existing_profile(self,plot):
        # clear exisiting plot
        self.clear_plot()
        if self.profile_name in self.profiles[self.main_window.sample_id]:
            profile = self.profiles[self.main_window.sample_id][self.profile_name].points        
            for (k,v) in profile:
                for x,y,_,_,_ in profile[k,v]:
                    # Create a scatter plot items
                    scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                    scatter.setZValue(1e9)
                    plot.addItem(scatter)

    def interpolate_points(self, interpolation_distance,radius):
        
        """
        Interpolate linear points between each pair of points in the profiles.
        """
        profile = self.profiles[self.main_window.sample_id][self.profile_name].points
        i_profile = self.profiles[self.main_window.sample_id][self.profile_name].i_points

        if self.main_window.toolButtonProfileInterpolate.isChecked():
            interpolate = True
            for (k,v), points in profile.items():
                for i in range(len(points) - 1):
                    start_point = points[i]
                    end_point = points[i + 1]
                    if i==0:
                        i_profile[(k,v)] = [start_point]
                    else:
                        i_profile[(k,v)].append(start_point)

                    # Calculate the distance between start and end points
                    dist = self.calculate_distance(start_point, end_point)

                    # Determine the number of interpolations based on the distance
                    num_interpolations = max(int(dist / interpolation_distance), 0)

                    # Calculate the unit vector in the direction from start_point to end_point
                    dx = (end_point[0] - start_point[0]) / dist
                    dy = (end_point[1] - start_point[1]) / dist

                    # # Generate linearly spaced points between start_point and end_point
                    # for t in np.linspace(0, 1, num_interpolations + 2)[1:-1]:  # Exclude the endpoints
                    #     x = start_point[0] + t * (end_point[0] - start_point[0])
                    #     y = start_point[1] + t * (end_point[1] - start_point[1])

                    for t in range(0, num_interpolations+1):
                        x = start_point[0] + t * interpolation_distance * dx
                        y = start_point[1] + t * interpolation_distance * dy

                        x_i = self.dist_to_cart(x,'x') #index points
                        y_i = self.dist_to_cart(y,'y')

                        # Add the scatter item to all other plots and save points in profile
                        _, p, array= self.main_window.lasermaps[(k,v)]
                        if v==self.main_window.canvasWindow.currentIndex() and self.array_x ==array.shape[1] and self.array_y ==array.shape[0] : #only add scatters to other lasermaps of same sample
                            # Create a scatter plot item at the clicked position
                            scatter = ScatterPlotItem([x], [y], symbol='+', size=5)
                            scatter.setZValue(1e9)
                            p.addItem(scatter)
                            # Find all points within the specified radius
                            circ_val = []

                            p_radius_y = self.dist_to_cart(radius, 'y') # pixel radius in pixels y direction
                            p_radius_x = self.dist_to_cart(radius, 'x') # pixel radius in pixels x direction
                            
                            for i in range(max(0, y_i - p_radius_y), min(self.array_y, y_i + p_radius_y + 1)):
                                for j in range(max(0, x_i - p_radius_x), min(self.array_x , x_i + p_radius_x + 1)):
                                    if self.calculate_distance(self.cart_to_dist(y_i - i)**2 , self.cart_to_dist(x_i - j)**2) <= radius:
                                        value = array[i, j]
                                        circ_val.append( value)

                            # for i in range(max(0, y_i - radius), min(self.array_y, y_i + radius + 1)):
                            #     for j in range(max(0, x_i - radius), min(self.array_x , x_i + radius + 1)):
                            #         if np.sqrt((x - j * self.main_window.x_range / self.array_x)**2 + (y - i * self.main_window.y_range / self.array_y)**2)  <= radius:
                            #             value = array[i, j]
                            #             circ_val.append(value)
                            if (k,v) in i_profile:
                                i_profile[(k,v)].append((x,y,circ_val, scatter, interpolate))

                    i_profile[(k,v)].append(end_point)
            # After interpolation, update the plot and table widget
            self.plot_profiles(interpolate= interpolate)
        else:
            self.clear_interpolation()
            #plot original profile
            self.plot_profiles(interpolate= False)
        # self.update_table_widget(interpolate= True)

    def clear_plot(self):
        """Clear all existing profiles from the plot."""
        if self.main_window.sample_id in self.profiles:
            for profile_name, profile in self.profiles[self.main_window.sample_id].items():
                # Clear points from the plot
                for (k, v), points in profile.points.items():
                    for _, _, _, scatter, _ in points:
                        self.main_window.plot.removeItem(scatter)

                # Clear interpolated points from the plot (if applicable)
                for (k, v), i_points in profile.i_points.items():
                    for _, _, _, scatter, _ in i_points:
                        self.main_window.plot.removeItem(scatter)

    def clear_interpolation(self):
            i_profile = self.profiles[self.main_window.sample_id][self.profile_name].i_points
            # remove interpolation
            if len(i_profile)>0:
                for (k,v), profile in i_profile.items():
                    for point in profile:
                        scatter_item = point[3]  # Access the scatter plot item
                        interpolate =point[4]
                        if interpolate:
                            _, plot, _ = self.main_window.lasermaps[(k,v)]
                            plot.removeItem(scatter_item)

    def plot_profiles(self, interpolate= False, sort_axis=None):
        profile = self.profiles[self.main_window.sample_id][self.profile_name].points
        i_profile = self.profiles[self.main_window.sample_id][self.profile_name].i_points
        def process_points( points, sort_axis):
            # Sort the points based on the user-specified axis
            if sort_axis == 'x':
                points.sort(key=lambda p: p[0])  # Sort by x-coordinate of median point
            elif sort_axis == 'y':
                points.sort(key=lambda p: p[1])  # Sort by y-coordinate of median point

            median_values = []
            lower_quantiles = []
            upper_quantiles = []
            mean_values = []
            standard_errors = []
            distances = [0]

            for i, group in enumerate(points):

                values = [p for p in group[2]] # Extract values
                median_values.append(np.median(values))
                lower_quantiles.append(np.quantile(values, 0.25))
                upper_quantiles.append(np.quantile(values, 0.75))
                mean_values.append(np.mean(values))
                standard_errors.append(np.std(values, ddof=1) / np.sqrt(len(values)))
                if i>0:
                    dist = self.calculate_distance(points[i - 1], points[i])
                    distances.append(distances[-1] + dist)

            return distances, median_values, lower_quantiles, upper_quantiles,mean_values,standard_errors

        def group_profiles_by_range(sort_axis, range_threshold,interpolate,point_type):
            if not interpolate:
                profiles = profile
            else:
                profiles = i_profile
            # Group profiles based on range similarity
            profile_groups = {}
            keys = []
            if self.main_window.canvasWindow.currentIndex() == self.main_window.canvas_tab['mv']: #multiview
                keys= [(k,v) for (k,v) in profiles.keys() if v== 1]



            else: #singleview
                keys = [(k,v) for (k,v) in profiles.keys() if v== 0]

            colors = [cmap(i / len(keys)) for i in range(len(keys))]

            for (k,v) in keys:
                points =  profiles[(k,v)]
                distances, medians, lowers, uppers, mean,s_error  = process_points(points, sort_axis)
                if point_type == 'mean':
                    range_value = np.nanmax(mean) - np.nanmin(mean)

                    similar_group_found = False

                    for group_key, _ in profile_groups.items():
                        if abs(range_value - group_key) <= range_threshold:
                            profile_groups[group_key].append((k, distances, mean, s_error, np.nanmin(mean)))
                            similar_group_found = True
                            break
                    if not similar_group_found:
                        profile_groups[range_value] = [(k, distances, mean, s_error, np.nanmin(mean, np.nanmax(mean)))]
                else:

                    range_value = np.nanmax(medians)- np.nanmin(medians)

                    similar_group_found = False

                    for group_key, _ in profile_groups.items():
                        if abs(range_value - group_key) <= range_threshold:
                            profile_groups[group_key].append((k, distances, medians, lowers, uppers, np.nanmin(medians), np.nanmax(medians)))
                            similar_group_found = True
                            break
                    if not similar_group_found:
                        profile_groups[range_value] = [(k, distances, medians, lowers, uppers, np.nanmin(medians), np.nanmax(medians))]

            return profile_groups, colors


        if not interpolate:
            profiles = profile
        else:
            profiles = i_profile

        style = self.main_window.styles['profile']

        if len(list(profiles.values())[0])>0: #if profile has values
            self.main_window.tabWidget.setCurrentIndex(self.main_window.bottom_tab['profile']) #show profile plot tab
            sort_axis=self.main_window.comboBoxProfileSort.currentText()
            range_threshold=int(self.main_window.lineEditYThresh.text())
            # Clear existing plot
            layout = self.main_window.widgetProfilePlot.layout()
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Get the colormap specified by the user
            cmap = self.main_window.get_colormap()
            # Determine point type from the pushButtonProfileType text
            if self.main_window.comboBoxPointType.currentText() == 'median + IQR':
                point_type = 'median'
            else:
                point_type ='mean'
            # Group profiles and set up the figure
            profile_groups,colors = group_profiles_by_range(sort_axis, range_threshold, interpolate, point_type)
            # Initialize the figure
            self.fig = Figure()
            #Connect the pick_event signal to a handler that will process the picked points.
            self.fig.canvas.mpl_connect('pick_event', self.on_pick)
            num_groups = len(profile_groups)
            num_subplots = (num_groups + 1) // 2  # Two groups per subplot, rounding up
            subplot_idx = 1
            #reset existing error_bar list
            self.all_errorbars = []
            original_range = None
            original_min = None
            twinx_min = None
            original_max = None
            twinx_max = None
            # Adjust subplot spacing
            # fig.subplots_adjust(hspace=0.1)  # Adjust vertical spacing
            ax = self.fig.add_subplot(num_subplots, 1, subplot_idx)

            for idx, (range_value, group_profiles) in enumerate(profile_groups.items()):
                scale_factor = 0
                if idx > 1 and idx % 2 == 0:  # Create a new subplot for every 2 groups after the first two
                    subplot_idx += 1
                    ax = self.fig.add_subplot(num_subplots, 1, subplot_idx)
                    original_range = range_value

                elif idx % 2 == 1:  # Create a new axis for every second group

                    twinx_range = range_value
                    scale_factor = original_range/twinx_range
                    ax2 = ax.twinx()
                    ax.set_zorder(ax2.get_zorder()+1)
                    # ax = ax2
                else:
                    original_range = range_value
                el_labels = []
                # Plot each profile in the group
                if point_type == 'mean':
                    for g_idx,(profile_key, distances, means,s_errors, min_val, max_val) in enumerate(group_profiles):
                        if scale_factor>0: #needs scaling
                            if g_idx == 0: #the min value of the group is stored in first row of each group_profiles
                                twinx_min = min_val
                                twinx_min = max_val
                                # Scale values and errors
                                scaled_values = [(value - twinx_min) * scale_factor + original_min for value in means]
                                scaled_errors = [error * scale_factor for error in s_errors]

                            # Plot markers with ax.scatter
                            scatter = ax.scatter(distances, scaled_values,
                                                  color=colors[idx+g_idx],
                                                  s=style['Markers']['Size'],
                                                  marker=self.main_window.markerdict[style['Markers']['Symbol']],
                                                  edgecolors='none',
                                                  picker=5,
                                                  label=f'{profile_key}',
                                                  zorder=2*g_idx+1)

                            #plot errorbars with no marker
                            _, _, barlinecols = ax.errorbar(distances, scaled_errors,
                                                            yerr=scaled_errors,
                                                            fmt='none',
                                                            color=colors[idx+g_idx],
                                                            ecolor=style['Colors']['Color'],
                                                            elinewidth=style['Lines']['LineWidth'],
                                                            capsize=0,
                                                            zorder=2*g_idx)

                            # Assuming you have the scaling factors and original data range
                            scale_factor = (original_max - original_min) / (twinx_max - twinx_min)

                            # Determine positions for custom ticks on ax2
                            # Choose representative values from the original scale you want as ticks on ax2
                            original_tick_values = [twinx_min, (twinx_max + twinx_min) / 2, twinx_max]

                            # Calculate the scaled positions of these ticks on ax
                            scaled_tick_positions = [(value - twinx_min) * scale_factor + original_min for value in original_tick_values]

                        else:
                            if g_idx == 0:
                                original_min = min_val
                                original_max = max_val
                            # Plot markers with ax.scatter
                            scatter = ax.scatter(distances, means,
                                                color=colors[idx+g_idx],
                                                s=style['Markers']['Size'],
                                                marker=self.main_window.markerdict[style['Markers']['Symbol']],
                                                edgecolors='none',
                                                picker=5,
                                                label=f'{profile_key[:-1]}',
                                                zorder = 2*g_idx+1)

                            #plot errorbars with no marker
                            _, _, barlinecols = ax.errorbar(distances, means,
                                                            yerr=s_errors,
                                                            fmt='none',
                                                            color=colors[idx+g_idx],
                                                            ecolor=style['Colors']['Color'],
                                                            elinewidth=style['Lines']['LineWidth'],
                                                            capsize=0, zorder=2*g_idx)

                        self.all_errorbars.append((scatter,barlinecols[0]))
                        self.original_colors[profile_key] = colors[idx+g_idx]  # Assuming colors is accessible
                        self.selected_points[profile_key] = [False] * len(means)
                        el_labels.append(profile_key.split('_')[-1]) #get element name
                        y_axis_text = ','.join(el_labels)
                        if scale_factor>0:
                            ax2.set_ylabel(f'{y_axis_text}')
                            ax2.set_yticks(scaled_tick_positions)
                            ax2.set_yticklabels([f"{value:.2f}" for value in original_tick_values])
                        else:
                            ax.set_ylabel(f'{y_axis_text}')
                        # Append the new Line2D objects to the list
                        # self.markers.extend(marker)
                else:
                    for g_idx,(profile_key, distances, medians, lowers, uppers, min_val, max_val) in enumerate(group_profiles):
                        #asymmetric error bars
                        errors = [[median - lower for median, lower in zip(medians, lowers)],
                            [upper - median for upper, median in zip(uppers, medians)]]
                        if scale_factor>0: #needs scaling
                            if g_idx == 0: #the min value of the group is stored in first row of each group_profiles
                                twinx_min = min_val
                                twinx_max = max_val


                            # Scale values and errors
                            scaled_values = [(value - twinx_min) * scale_factor + original_min for value in medians]
                            # Assuming errors is structured as [lower_errors, upper_errors]
                            scaled_lower_errors = [error * scale_factor for error in errors[0]]
                            scaled_upper_errors = [error * scale_factor for error in errors[1]]

                            # Now, scaled_errors is ready to be used in plotting functions
                            scaled_errors = [scaled_lower_errors, scaled_upper_errors]
                            # Plot markers with ax.scatter
                            scatter = ax.scatter(distances, scaled_values,
                                                color=colors[idx+g_idx],
                                                s=style['Markers']['Size'],
                                                marker=self.main_window.markerdict[style['Markers']['Symbol']],
                                                edgecolors='none',
                                                picker=5,
                                                gid=profile_key,
                                                label=f'{profile_key}',
                                                zorder=2*g_idx+1)
                            # ax2.scatter(distances, medians, color=colors[idx+g_idx],s=self.scatter_size, picker=5, gid=profile_key, edgecolors = 'none', label=f'{profile_key[:-1]}')
                            #plot errorbars with no marker
                            _, _, barlinecols = ax.errorbar(distances, scaled_values,
                                                            yerr=scaled_errors,
                                                            fmt='none',
                                                            color=colors[idx+g_idx],
                                                            ecolor=style['Colors']['Color'],
                                                            elinewidth=style['Lines']['LineWidth'],
                                                            capsize=0,
                                                            zorder=2*g_idx)


                            # Assuming you have the scaling factors and original data range
                            scale_factor = (original_max - original_min) / (twinx_max - twinx_min)

                            # Determine positions for custom ticks on ax2
                            # Choose representative values from the original scale you want as ticks on ax2
                            original_tick_values = [twinx_min, (twinx_max + twinx_min) / 2, twinx_max]

                            # Calculate the scaled positions of these ticks on ax
                            scaled_tick_positions = [(value - twinx_min) * scale_factor + original_min for value in original_tick_values]
                        else:
                            if g_idx == 0: #the min value of the group is stored in first row of each group_profiles
                                original_min = min_val
                                original_max = max_val

                            # Plot markers with ax.scatter
                            scatter = ax.scatter(distances, medians,
                                                 color=colors[idx+g_idx],
                                                 s=style['Markers']['Size'],
                                                 marker=self.main_window.markerdict[style['Markers']['Symbol']],
                                                 edgecolors='none',
                                                 picker=5,
                                                 gid=profile_key,
                                                 label=f'{profile_key}',
                                                 zorder=2*g_idx+1)

                            #plot errorbars with no marker
                            _, _, barlinecols = ax.errorbar(distances, medians,
                                                            yerr=errors,
                                                            fmt='none',
                                                            color=colors[idx+g_idx],
                                                            ecolor=style['Colors']['Color'],
                                                            elinewidth=style['Lines']['LineWidth'],
                                                            capsize=0,
                                                            zorder=2*g_idx)

                        self.all_errorbars.append((scatter,barlinecols[0]))
                        self.original_colors[profile_key] = colors[idx+g_idx]  # Assuming colors is accessible
                        self.selected_points[profile_key] = [False] * len(medians)
                        el_labels.append(profile_key[:-1].split('_')[-1]) #get element name
                        y_axis_text = ','.join(el_labels)
                        if scale_factor>0:
                            ax2.set_ylabel(f'{y_axis_text}')
                            ax2.set_yticks(scaled_tick_positions)
                            ax2.set_yticklabels([f"{value:.2f}" for value in original_tick_values])
                        else:
                            ax.set_ylabel(f'{y_axis_text}')

            # Set labels only for the bottom subplot
                if subplot_idx == num_subplots:
                    ax.set_xlabel('Distance')
                else:
                    # Remove the x-axis for the first subplot
                    ax.xaxis.set_visible(False)
                # ax.set_ylabel(f'Axis {idx}')
                # Adjust legend position based on the subplot index
                legend_loc = 'upper left' if idx % 2 == 0 else 'upper right'
                # ax.legend(title=f'Axis {idx}', loc=legend_loc, bbox_to_anchor=(1.05, 1))

            # self.fig.tight_layout(pad=3, h_pad=None, w_pad=None, rect=None)
            self.fig.tight_layout(pad=3,w_pad=0, h_pad=0)
            self.fig.subplots_adjust(wspace=0, hspace=0)
            self.fig.legend(loc='outside right upper')

            # Embed the matplotlib plot in a QWidget
            canvas = FigureCanvas(self.fig)
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.addWidget(canvas)
            widget.setLayout(layout)

            # Add the new plot widget to the layout
            self.main_window.widgetProfilePlot.layout().addWidget(widget)
            widget.show()
        else:
            self.clear_profiles()

    def clear_profiles(self):
        if self.main_window.sample_id in self.profiles: #if profiles have been initiated for the samples
            if self.profile_name in self.profiles[self.main_window.sample_id]: #if profiles for that sample if exists
                # Clear all scatter plot items from the lasermaps
                for _, (_, plot, _) in self.main_window.lasermaps.items():
                    items_to_remove = [item for item in plot.listDataItems() if isinstance(item, ScatterPlotItem)]
                    for item in items_to_remove:
                        plot.removeItem(item)

                # Clear the profiles data
                # profile.clear()

                # Clear all data from the table
                self.main_window.tableWidgetProfilePoints.clearContents()

                # Remove all rows
                self.main_window.tableWidgetProfilePoints.setRowCount(0)

                # Clear the profile plot widget
                layout = self.main_window.widgetProfilePlot.layout()
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

    def calculate_distance(self, point1, point2):
        # Simple Euclidean distance
        if isinstance(point1, (tuple, list)) and isinstance(point2, (tuple, list)):
        # Simple Euclidean distance for 2D points
            return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
        else:
            return np.sqrt((point1**2 + point2**2))
        

    def  update_table_widget(self, update = False):
        if self.main_window.sample_id in self.profiles:
            if self.profile_name in self.profiles[self.main_window.sample_id]: #if profiles for that sample if exists
                profile = self.profiles[self.main_window.sample_id][self.profile_name].points
                self.main_window.tableWidgetProfilePoints.setRowCount(0)  # Clear existing rows
                point_number = 0
                first_data_point = list(profile.values())[0]
                for data_point in first_data_point:
                    x, y, _,_,_ = data_point  # Assuming data_point structure
                    row_position = self.main_window.tableWidgetProfilePoints.rowCount()
                    self.main_window.tableWidgetProfilePoints.insertRow(row_position)

                    # Fill in the data
                    self.main_window.tableWidgetProfilePoints.setItem(row_position, 0, QTableWidgetItem(str(point_number)))
                    self.main_window.tableWidgetProfilePoints.setItem(row_position, 1, QTableWidgetItem(str(round(x))))
                    self.main_window.tableWidgetProfilePoints.setItem(row_position, 2, QTableWidgetItem(str(round(y))))
                    point_number += 1

                # Enable or disable buttons based on the presence of points
                self.toggle_buttons(self.main_window.tableWidgetProfilePoints.rowCount() > 0)

    def toggle_buttons(self, enable):
        self.main_window.toolButtonPointUp.setEnabled(enable)
        self.main_window.toolButtonPointDown.setEnabled(enable)
        self.main_window.toolButtonPointDelete.setEnabled(enable)

    def on_pick(self, event):

        if self.edit_mode_enabled and isinstance(event.artist, PathCollection):
            # The picked scatter plot
            picked_scatter = event.artist
            # Indices of the picked points, could be multiple if overlapping
            ind = event.ind[0]  # Let's handle the first picked point for simplicity
            profile_key = picked_scatter.get_gid()
            # Determine the color of the picked point
            facecolors = picked_scatter.get_facecolors().copy()
            original_color = colors.to_rgba(self.original_colors[profile_key])  # Assuming you have a way to map indices to original colors

            # Toggle selection state
            self.selected_points[profile_key][ind] = not self.selected_points[profile_key][ind]

            num_points = len(picked_scatter.get_offsets())
            # If initially, there's only one color for all points,
            # we might need to ensure the array is expanded to explicitly cover all points.
            if len(facecolors) == 1 and num_points > 1:
                facecolors = np.tile(facecolors, (num_points, 1))


            if not self.selected_points[profile_key][ind]:
                # If already grey (picked)
                # Set to original color
                facecolors[ind] = colors.to_rgba(original_color)
            else:
                # Set to grey
                facecolors[ind] = (0.75, 0.75, 0.75, 1)

            picked_scatter.set_facecolors(facecolors)
            # Update the scatter plot sizes
            picked_scatter.set_sizes(np.full(num_points, self.main_window.styles['profile']['Markers']['Size']))
            self.fig.canvas.draw_idle()

    def toggle_edit_mode(self):
        """Toggles profile editing mode.

        State determined by toolButtonProfileEditMode checked.
        """
        self.edit_mode_enabled = not self.edit_mode_enabled

    def toggle_point_visibility(self):
        """Toggles visibility of individual profile points

        Toggled points are still retained in the data, but an associated boolean field indicates
        whether they should be displayed or not.
        """        
        for profile_key in self.selected_points.keys():
            # Retrieve the scatter object using its profile key
            scatter, barlinecol = self.get_scatter_errorbar_by_gid(profile_key)
            if scatter is None:
                continue

            facecolors = scatter.get_facecolors().copy()
            num_points = len(scatter.get_offsets())

            # If initially, there's only one color for all points, expand the colors array
            if len(facecolors) == 1 and num_points > 1:
                facecolors = np.tile(facecolors, (num_points, 1))

            # Get the current array of colors (RGBA) for the LineCollection
            line_colors = barlinecol.get_colors().copy()

            # Ensure the color array is not a single color by expanding it if necessary
            if len(line_colors) == 1 and len(barlinecol.get_segments()) > 1:
                line_colors = np.tile(line_colors, (num_points, 1))

            # Iterate through each point to adjust visibility based on selection state
            for idx, selected in enumerate(self.selected_points[profile_key]):
                if selected:
                    if facecolors[idx][-1] > 0:
                        # Toggle visibility by setting alpha to 0 (invisible) or back to its original value
                        new_alpha = 0.0
                    else:
                        new_alpha= 1.0  # Assume original alpha was 1.0
                    line_colors[idx][-1] = new_alpha  # Set alpha to 0 for the line at index idx
                    facecolors[idx][-1] = new_alpha #hid/unhide scatter
            barlinecol.set_colors(line_colors)
            scatter.set_facecolors(facecolors)
        self.fig.canvas.draw_idle()

    def get_scatter_errorbar_by_gid(self, gid):
        #return the correct scatter for corresponding key
        for (scatter, errorbars) in self.all_errorbars:
            if scatter.get_gid() == gid:
                return (scatter, errorbars)
        return None


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
    app.setWindowIcon(QtGui.QIcon(os.path.join(BASEDIR, os.path.join(ICONPATH,'LaME-64.svg'))))
    main = MainWindow()

    # Set the main window to fullscreen
    #main.showFullScreen()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()