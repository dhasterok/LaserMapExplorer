from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QColorDialog, QCheckBox, QComboBox,  QTableWidgetItem, QHBoxLayout, QVBoxLayout, QGridLayout, QMessageBox
from PyQt5.QtWidgets import QFileDialog, QProgressDialog, QWidget, QTabWidget, QDialog, QLabel, QListWidgetItem, QTableWidget, QInputDialog
from PyQt5.Qt import QStandardItemModel,QStandardItem
from pyqtgraph import PlotWidget, ScatterPlotItem, mkPen, AxisItem, PlotDataItem
from pyqtgraph.Qt import QtWidgets
from pyqtgraph.GraphicsScene import exportDialog
from PyQt5.QtGui import QIntValidator, QColor, QImage, QPainter, QPixmap
import pyqtgraph as pg
import sys  # We need sys so that we can pass argv to QApplication
import os
import numpy as np
import pandas as pd
from PyQt5.QtGui import QTransform, QFont
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.collections import PathCollection
import matplotlib.pyplot as plt
from matplotlib.path import Path
from PyQt5.QtWidgets import QStyledItemDelegate
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QBrush, QColor
from PyQt5.QtCore import pyqtSignal
from src.rotated import RotatedHeaderView
import cmcrameri.cm as cmc
from src.ternary_plot import ternary
from sklearn.cluster import KMeans
from sklearn_extra.cluster import KMedoids
import skfuzzy as fuzz
from matplotlib.colors import Normalize
import matplotlib.patches as mpatches
from matplotlib.colors import BoundaryNorm
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from src.plot_spider import plot_spider_norm
import re
import matplotlib.ticker as ticker
from src.radar import Radar
from src.calculator import CalWindow
from src.ui.MainWindow import Ui_MainWindow
from src.ui.IsotopeSelectionDialog import Ui_Dialog
import scipy.stats
from scipy import ndimage
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from cv2 import Canny, Sobel, CV_64F, bilateralFilter, medianBlur, edgePreservingFilter
from scipy.signal import convolve2d, wiener
from PyQt5.QtWidgets import QGraphicsRectItem
from PyQt5.QtCore import QRectF, Qt, QPointF
from PyQt5.QtGui import QPen, QColor, QCursor
import copy

pg.setConfigOption('imageAxisOrder', 'row-major') # best performance
## !pyrcc5 resources.qrc -o src/ui/resources_rc.py
## !pyuic5 designer/mainwindow.ui -o src/ui/MainWindow.py
## !pyuic5 -x designer/IsotopeSelectionDialog.ui -o src/ui/IsotopeSelectionDialog.py
# pylint: disable=fixme, line-too-long, no-name-in-module, trailing-whitespace
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        # Add this line to set the size policy
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.buttons_layout = None  # create a reference to your layout
        self.isotopes_df = pd.DataFrame(columns = ['sample_id', 'isotopes', 'norm','upper_bound','lower_bound','d_l_bound','d_u_bound', 'use'])
        self.ratios_df = pd.DataFrame(columns = ['sample_id', 'isotope_1','isotope_2', 'norm','upper_bound','lower_bound','d_l_bound','d_u_bound', 'use', 'auto_scale'])
        self.filter_df = pd.DataFrame(columns = ['sample_id', 'isotope_1', 'isotope_2', 'ratio','norm','f_min','f_max', 'use'])
        self.cluster_results=pd.DataFrame(columns = ['Fuzzy', 'KMeans', 'KMediods'])
        self.clipped_ratio_data = pd.DataFrame()
        self.isotope_data = {}  #stores orginal isotope data
        self.clipped_isotope_data = {} # stores processed isotoped data
        self.computed_isotope_data = {} # stores computed isotoped data (ratios, custom fields)
        self.sample_data_dict = {}
        self.plot_widget_dict ={'lasermap':{},'histogram':{},'lasermap_norm':{},'clustering':{},'scatter':{},'n-dim':{},'correlation':{}, 'pca':{}}
        self.multi_view_index = []
        self.laser_map_dict = {}
        self.multiview_info_label = {}
        self.selected_isotopes = []
        self.n_dim_list = []
        self.group_cmap = {}
        self.lasermaps = {}
        self.norm_dict = {} #holds values (log, logit, linear) of all isotopes
        self.proxies = []
        self.prev_plot = ''
        self.pop_plot = ''
        self.order= 'F'
        self.update_spinboxes_bool = False
        self.default_bins = 100
        self.swap_xy_val = False
        self.plot_id = {'clustering':{},'scatter':{},'n-dim':{}}
        self.fuzzy_results={}
        self.current_group = {'algorithm':None,'clusters': None}
        self.matplotlib_canvas = None
        self.pyqtgraph_widget = None
        self.isUpdatingTable = False
        colormaps = pg.colormap.listMaps('matplotlib')
        self.comboBoxMapColormap.clear()
        self.comboBoxMapColormap.addItems(colormaps)
        self.comboBoxFieldColormap.clear()
        self.comboBoxFieldColormap.addItems(colormaps)
        self.comboBoxClusterColormap.clear()
        self.comboBoxClusterColormap.addItems(colormaps)
        self.cm = self.comboBoxMapColormap.currentText()
        self.cursor = False
        self.comboBoxMapColormap.activated.connect(self.update_all_plots)
        layout_single_view = QtWidgets.QVBoxLayout()
        layout_single_view.setSpacing(0)
        self.widgetSingleView.setLayout(layout_single_view)
        self.widgetSingleView.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout_multi_view = QtWidgets.QHBoxLayout()
        layout_multi_view.setSpacing(0)# Set margins to 0 if you want to remove margins as well
        layout_multi_view.setContentsMargins(0, 0, 0, 0)
        self.point_selected = False
        self.sample_tab_id = 0
        self.process_tab_id = 1
        self.spot_tab_id = 2
        self.filter_tab_id = 3
        self.scatter_tab_id = 4
        self.ndim_tab_id = 5
        self.pca_tab_id = 6
        self.cluster_tab_id = 7
        self.profile_tab_id = 8
        self.special_tab_id = 9
        
        #edge_det_img
        self.edge_img = None
        #noise red image filter
        self.noise_red_img= None
        
        # create dictionaries for default plot styles
        self.markerdict = {'circle':'o', 'square':'s', 'diamond':'d', 'triangle (up)':'^', 'triangle (down)':'v', 'hexagon':'h', 'pentagon':'p'}
        self.comboBoxMarker.clear()
        self.comboBoxMarker.addItems(self.markerdict.keys())
        self.general_style = {'Concentration':'ppm', 'Distance':'um', 'Temperature':'°C', 'Pressure':'MPa', 'Date':'Ma', 'FontSize':11, 'TickDir':'out'}
        self.set_general_style()
        self.map_style = {self.sample_tab_id: {'Colormap':'plasma', 'ColorbarDirection':'vertical', 'ScaleLocation':'southeast', 'ScaleDirection':'horizontal', 'OverlayColor':'#ffffff'},
            self.scatter_tab_id: {'Colormap':'orange-violet-blue-white', 'ColorbarDirection':'vertical', 'ScaleLocation':'southeast', 'ScaleDirection':'horizontal', 'OverlayColor':'#ffffff'},
            self.pca_tab_id: {'Colormap':'viridis', 'ColorbarDirection':'vertical', 'ScaleLocation':'southeast', 'ScaleDirection':'horizontal', 'OverlayColor':'#ffffff'},
            self.cluster_tab_id: {'Colormap':'viridis', 'ColorbarDirection':'vertical', 'ScaleLocation':'southeast', 'ScaleDirection':'horizontal', 'OverlayColor':'#ffffff'}}
        self.current_scatter_type = {self.sample_tab_id:'Heatmap', self.scatter_tab_id:'Scatter', self.pca_tab_id:'Scatter', self.profile_tab_id:'Scatter'}
        self.scatter_style = {self.sample_tab_id: {'Marker':'circle', 'Size':6, 'LineWidth':1.5, 'Color':'#1c75bc', 'ColorByField':'None', 'Field':None, 'Colormap':'RdBu', 'Cmin':0, 'Cmax':0, 'Alpha':30, 'AspectRatio':1.0},
            self.scatter_tab_id: {'Marker':'circle', 'Size':6, 'LineWidth':1.5, 'Color':'#1c75bc', 'ColorByField':'None', 'Field':None, 'Colormap':'viridis', 'Cmin':0, 'Cmax':0, 'Alpha':30, 'AspectRatio':1.0},
            self.pca_tab_id: {'Marker':'circle', 'Size':6, 'LineWidth':1.5, 'Color':'#1c75bc', 'ColorByField':'None', 'Field':None, 'Colormap':'viridis', 'Cmin':0, 'Cmax':0, 'Alpha':30, 'AspectRatio':1.0},
            self.profile_tab_id: {'Marker':'circle', 'Size':6, 'LineWidth':1.5, 'Color':'#1c75bc', 'ColorByField':'None', 'Field':None, 'Colormap':'viridis', 'Cmin':0, 'Cmax':0, 'Alpha':30, 'AspectRatio':1.0}}
        self.heatmap_style = {self.sample_tab_id: {'Resolution':1, 'Colormap':'RdBu', 'AspectRatio':1.0},
            self.scatter_tab_id: {'Resolution':10, 'Colormap':'viridis', 'AspectRatio':1.0},
            self.pca_tab_id: {'Resolution':10, 'Colormap':'viridis', 'AspectRatio':1.0},
            self.profile_tab_id: {'Resolution':1, 'Colormap':'viridis', 'AspectRatio':1.0}}
        self.profilepoly_style = {}

        self.widgetMultiView.setLayout(layout_multi_view)
        self.widgetMultiView.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        layout_profile_view = QtWidgets.QVBoxLayout()
        layout_profile_view.setSpacing(0)

        # Menu and Toolbar
        #-------------------------
        self.widgetProfilePlot.setLayout(layout_profile_view)

        # Connect the "Open" action to a function
        self.actionOpen.triggered.connect(self.open_directory)
        # Intialize Tabs as not enabled
        self.SelectIsotopePage.setEnabled(False)
        self.PreprocessPage.setEnabled(False)
        self.SpotDataPage.setEnabled(False)
        self.FilterPage.setEnabled(False)
        self.ScatterPage.setEnabled(False)
        self.NDIMPage.setEnabled(False)
        self.PCAPage.setEnabled(False)
        self.ClusteringPage.setEnabled(False)
        self.ProfilingPage.setEnabled(False)
        self.SpecialFunctionPage.setEnabled(False)

        self.toolButtonLoadIsotopes.clicked.connect(self.open_select_isotope_dialog)
        self.actionSelectAnalytes.triggered.connect(self.open_select_isotope_dialog)
        self.actionSpotData.triggered.connect(lambda: self.open_tab('spot data'))
        self.actionFilter_Tools.triggered.connect(lambda: self.open_tab('filter'))
        self.actionBiPlot.triggered.connect(lambda: self.open_tab('scatter'))
        self.actionTEC.triggered.connect(lambda: self.open_tab('ndim'))
        self.actionPolygon.triggered.connect(lambda: self.open_tab('filter'))
        self.actionProfiles.triggered.connect(lambda: self.open_tab('profiles'))
        self.actionCluster.triggered.connect(lambda: self.open_tab('clustering'))
        self.actionReset.triggered.connect(lambda: self.reset_analysis())
        # Select Isotope Tab
        #-------------------------
        self.ref_data = pd.read_excel('resources/app_data/earthref.xlsx')
        ref_list = self.ref_data['layer']+' ['+self.ref_data['model']+'] '+ self.ref_data['reference']
        # self.comboBoxCorrelationMethod.activated.connect(self.plot_correlation)

        self.comboBoxRefMaterial.addItems(ref_list.values)          # Select Isotope Tab
        self.comboBoxNDimRefMaterial.addItems(ref_list.values)      # NDim Tab
        self.comboBoxRefMaterial.activated.connect(lambda: self.change_ref_material(self.comboBoxRefMaterial, self.comboBoxNDimRefMaterial))
        self.comboBoxNDimRefMaterial.activated.connect(lambda: self.change_ref_material(self.comboBoxNDimRefMaterial, self.comboBoxRefMaterial))

        # Selecting isotopes
        #-------------------------
        # Connect the currentIndexChanged signal of comboBoxSampleId to load_data method
        self.comboBoxSampleId.activated.connect(
            lambda: self.change_sample(self.comboBoxSampleId.currentIndex()))

        # self.toolButtonAddRatio.clicked.connect(lambda: self.ratios_items.appendRow(StandardItem(self.ratio_name)))


        # self.comboBoxFIsotope.activated.connect(
        #     lambda: self.get_map_data(self.sample_id,isotope_1=self.comboBoxFIsotope_1.currentText(),
        #                           isotope_2=self.comboBoxFIsotope_2.currentText(),view = 1))
        #

        #self.comboBoxPlots.activated.connect(lambda: self.add_remove(self.comboBoxPlots.currentText()))
        #self.toolButtonAddPlots.clicked.connect(lambda: self.add_multi_plot(self.comboBoxPlots.currentText()))
        self.toolButtonRemovePlots.clicked.connect(lambda: self.remove_multi_plot(self.comboBoxPlots.currentText()))
        #add ratio item to tree view

        #tabs = self.canvasWindow
        #tabs.tabCloseRequested.connect(lambda index: tabs.removeTab(index))
        #self.canvasWindow.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        #create plot tree

        self.create_tree()
        #self.open_directory()

        #normalising
        self.comboBoxNorm.clear()
        self.comboBoxNorm.addItems(['linear','log','logit'])
        self.comboBoxNorm.activated.connect(lambda: self.update_norm(self.sample_id, self.comboBoxNorm.currentText(), update = True))
        
        #init table_fcn
        self.table_fcn = Table_Fcn(self)
        
        # Preprocess Tab
        #-------------------------
        self.toolButtonSwapXY.clicked.connect(self.swap_xy)

        self.doubleSpinBoxUB.setMaximum(100)
        self.doubleSpinBoxUB.setMinimum(0)
        self.doubleSpinBoxLB.setMaximum(100)
        self.doubleSpinBoxLB.setMinimum(0)
        self.doubleSpinBoxDUB.setMaximum(100)
        self.doubleSpinBoxDUB.setMinimum(0)
        self.doubleSpinBoxDLB.setMaximum(100)
        self.doubleSpinBoxDLB.setMinimum(0)

        self.doubleSpinBoxLB.valueChanged.connect(lambda: self.auto_scale(True))
        self.doubleSpinBoxUB.valueChanged.connect(lambda: self.auto_scale(True))
        self.doubleSpinBoxDUB.valueChanged.connect(lambda: self.auto_scale(True))
        self.doubleSpinBoxDUB.valueChanged.connect(lambda: self.auto_scale(True))

        #self.spinBoxX.valueChanged.connect(lambda:self.update_plot(axis = True))
        #self.spinBoxY.valueChanged.connect(lambda:self.update_plot(axis = True))
        #self.spinBox_X.valueChanged.connect(lambda:self.update_plot(axis = True))
        #self.spinBox_Y.valueChanged.connect(lambda:self.update_plot(axis = True))
        self.toolButtonFullView.clicked.connect(self.reset_to_full_view)
        self.spinBoxNBins.valueChanged.connect(self.update_plot)
        self.spinBoxBinWidth.valueChanged.connect(lambda: self.update_plot(bin_s=False))
        self.toolBox.currentChanged.connect(lambda: self.canvasWindow.setCurrentIndex(0))
        #auto scale
        self.toolButtonAutoScale.clicked.connect(lambda: self.auto_scale(False) )
        self.toolButtonAutoScale.setChecked(True)
        self.toolButtonHistogramReset.clicked.connect(lambda: self.update_plot(reset = True))

        # Noise reduction
        self.comboBoxNRMethod.activated.connect(self.add_noise_reduction)
        self.spinBoxSmoothingFactor.valueChanged.connect(self.add_noise_reduction)
        self.spinBoxSmoothingFactor.setEnabled(False)
        self.labelSmoothingFactor.setEnabled(False)

        # Initiate crop tool
        self.crop_tool = Crop_tool(self)
        self.toolButtonCrop.clicked.connect(self.crop_tool.init_crop)
        self.toolButtonCropApply.clicked.connect(self.crop_tool.apply_crop)
        self.toolButtonCropApply.setEnabled(False)

        # Spot Data Tab
        #-------------------------

        # Filter Tabs
        #-------------------------
        # left pane
        self.toolButtonAddFilter.clicked.connect(self.update_filter_table)
        self.comboBoxFSelect.activated.connect(lambda: self.update_combo_boxes(self.comboBoxFSelect, self.comboBoxFIsotope))
        self.comboBoxFIsotope.activated.connect(self.update_filter_values)
        #     lambda: self.get_map_data(self.sample_id,isotope_1=self.comboBoxFIsotope_1.currentText(),
        #                           isotope_2=self.comboBoxFIsotope_2.currentText(),view = 1))

        # central-bottom pane
        self.toolButtonFilterUp.clicked.connect(lambda: self.table_fcn.move_row_up(self.tableWidgetFilters))
        self.toolButtonFilterDown.clicked.connect(lambda: self.table_fcn.move_row_down(self.tableWidgetFilters))
        # There is currently a special function for removing rows, convert to table_fcn.delete_row
        self.toolButtonFilterRemove.clicked.connect(self.remove_selected_rows)
        self.toolButtonFilterRemove.clicked.connect(lambda: self.table_fcn.delete_row(self.tableWidgetFilters))
        self.toolButtonFilterSelectAll.clicked.connect(self.tableWidgetFilters.selectAll)

        # initiate Polygon class
        self.polygon = Polygon(self)
        self.toolButtonPolyCreate.clicked.connect(self.polygon.increment_pid)
        self.toolButtonPolyDelete.clicked.connect(lambda: self.table_fcn.delete_row(self.tableWidgetPolyPoints))
        # Add edge detection algorithm to aid in creating polygons
        self.toolButtonEdgeDetection.clicked.connect(self.add_edge_detection)
        self.comboBoxEdgeDet.activated.connect(self.add_edge_detection)
        
        #Apply filters
        self.toolButtonMapViewable.clicked.connect(lambda: self.apply_filters(fullmap =True))
        self.toolButtonMapPolygon.clicked.connect(lambda: self.apply_filters(fullmap =False))
        
        self.toolButtonFilterToggle.clicked.connect(lambda:self.apply_filters(fullmap =False))
        self.toolButtonMapMask.clicked.connect(lambda:self.apply_filters(fullmap =False))
       
        # Scatter and Ternary Tab
        #-------------------------
        self.toolButtonPlotScatter.clicked.connect(lambda: self.plot_scatter(save=True))
        self.toolButtonTernaryMap.clicked.connect(self.plot_ternarymap)

        self.comboBoxScatterSelectX.activated.connect(lambda: self.update_combo_boxes(self.comboBoxScatterSelectX, self.comboBoxScatterIsotopeX))
        self.comboBoxScatterSelectY.activated.connect(lambda: self.update_combo_boxes(self.comboBoxScatterSelectY, self.comboBoxScatterIsotopeY))
        self.comboBoxScatterSelectZ.activated.connect(lambda: self.update_combo_boxes(self.comboBoxScatterSelectZ, self.comboBoxScatterIsotopeZ))

        # ternary colormaps
        # create ternary colors dictionary
        df = pd.read_csv('resources/styles/ternary_colormaps.csv')
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

        # PCA Tab
        #------------------------
        self.toolButtonPCAPlot.clicked.connect(self.plot_pca)

        # Clustering Tab
        #-------------------------
        # Populate the comboBoxCluster with distance metrics
        distance_metrics = ['cityblock', 'cosine', 'euclidean', 'l1', 'l2', 'manhattan']
        self.comboBoxClusterDistance.clear()
        self.comboBoxClusterDistance.addItems(distance_metrics)

        self.toolButtonRunClustering.clicked.connect(self.plot_clustering)

        # Connect slider's value changed signal to a function
        self.spinBoxNClusters.valueChanged.connect(lambda: self.spinBoxFCView.setMaximum(self.spinBoxNClusters.value()))

        self.horizontalSliderClusterExponent.setMinimum(10)  # Represents 1.0 (since 10/10 = 1.0)
        self.horizontalSliderClusterExponent.setMaximum(30)  # Represents 3.0 (since 30/10 = 3.0)
        self.horizontalSliderClusterExponent.setSingleStep(1)  # Represents 0.1 (since 1/10 = 0.1)
        self.horizontalSliderClusterExponent.setTickInterval(1)

        self.horizontalSliderClusterExponent.valueChanged.connect(lambda value: self.labelClusterExponent.setText(str(value/10)))
        self.comboBoxClusterMethod.activated.connect(self.update_cluster_ui)
        self.update_cluster_ui()

        # Connect color point radio button signals to a slot
        self.comboBoxColorMethod.currentIndexChanged.connect(self.group_changed)
        # Connect the itemChanged signal to a slot
        self.tableWidgetViewGroups.itemChanged.connect(self.cluster_label_changed)

        self.comboBoxColorMethod.currentText() == 'none'
        # self.tableWidgetViewGroups.selectionModel().selectionChanged.connect(self.update_clusters)

        # Scatter and Ternary Tab
        #-------------------------
        self.comboBoxScatterType.activated.connect(lambda: self.toggle_scatter_style_tab(self.toolBox.currentIndex()))
        self.comboBoxScatterIsotopeX.activated.connect(lambda: self.plot_scatter(save=False))
        self.comboBoxScatterIsotopeY.activated.connect(lambda: self.plot_scatter(save=False))
        self.comboBoxScatterIsotopeZ.activated.connect(lambda: self.plot_scatter(save=False))

        # N-Dim Tab
        #-------------------------
        
        isotope_set = ['majors', 'full trace', 'REE', 'metals']
        self.comboBoxNDimIsotopeSet.addItems(isotope_set)
        #self.comboBoxNDimRefMaterial.addItems(ref_list.values) This is done with the Set Isotope tab initialization above.
        self.toolButtonNDimIsotopeAdd.clicked.connect(lambda: self.update_n_dim_table('IsotopeAdd'))
        self.toolButtonNDimIsotopeSetAdd.clicked.connect(lambda: self.update_n_dim_table('IsotopeSetAdd'))
        self.toolButtonNDimPlot.clicked.connect(self.plot_n_dim)
        self.toolButtonNDimUp.clicked.connect(lambda: self.table_fcn.move_row_up(self.tableWidgetNDim))
        self.toolButtonNDimDown.clicked.connect(lambda: self.table_fcn.move_row_down(self.tableWidgetNDim))
        self.toolButtonNDimSelectAll.clicked.connect(self.tableWidgetNDim.selectAll)
        self.toolButtonNDimRemove.clicked.connect(lambda: self.table_fcn.delete_row(self.tableWidgetNDim))
        #self.toolButtonNDimSaveList.clicked.connect(self.ndim_table.save_list)


        # Profile Tab
        #-------------------------
        self.lineEditPointRadius.setValidator(QIntValidator())
        self.lineEditYThresh.setValidator(QIntValidator())
        self.profiling = Profiling(self)
        # self.toolButtonPlotProfile.clicked.connect(lambda: self.plot_profiles(self.comboBoxProfile1.currentText(), self.comboBoxProfile2.currentText()))
        # self.comboBoxProfile1.activated.connect(lambda: self.update_profile_comboboxes(False) )
        # self.toolButtonClearProfile.clicked.connect(self.profiling.on_clear_profile_clicked)
        # self.toolButtonStartProfile.clicked.connect(lambda :self.toolButtonStartProfile.setChecked(True))
        # self.toolButtonStartProfile.setCheckable(True)
        # self.comboBoxProfile2.activated.connect(self.update_profile_comboboxes)
        #select entire row
        self.tableWidgetProfilePoints.setSelectionBehavior(QTableWidget.SelectRows)
        self.toolButtonPointUp.clicked.connect(lambda: self.table_fcn.move_row_up(self.tableWidgetProfilePoints))
        self.toolButtonPointDown.clicked.connect(lambda: self.table_fcn.move_row_down(self.tableWidgetProfilePoints))
        self.toolButtonPointDelete.clicked.connect(lambda: self.table_fcn.delete_row(self.tableWidgetProfilePoints))
        self.comboBoxProfileSort.currentIndexChanged.connect(self.plot_profile_and_table)
        self.toolButtonIPProfile.clicked.connect(lambda: self.profiling.interpolate_points(interpolation_distance=int(self.lineEditIntDist.text()), radius= int(self.lineEditPointRadius.text())))
        self.comboBoxPointType.currentIndexChanged.connect(lambda: self.profiling.plot_profiles())
        # self.toolButtonPlotProfile.clicked.connect(lambda:self.profiling.plot_profiles())
        self.toolButtonPointSelectAll.clicked.connect(self.tableWidgetProfilePoints.selectAll)
        # Connect toolButtonProfileEditToggle's clicked signal to toggle edit mode
        self.toolButtonProfileEditToggle.clicked.connect(self.profiling.toggle_edit_mode)

        # Connect toolButtonProfilePointToggle's clicked signal to toggle point visibility
        self.toolButtonProfilePointToggle.clicked.connect(self.profiling.toggle_point_visibility)

        # Special Tab
        #------------------------
        #SV/MV tool box
        self.toolButtonPanSV.setCheckable(True)
        self.toolButtonPanMV.setCheckable(True)

        self.toolButtonZoomSV.setCheckable(True)
        self.toolButtonZoomMV.setCheckable(True)

        # Styling Tab
        #-------------------------
        self.toolBox.currentChanged.connect(self.toolbox_changed)

        # overlay and annotation properties
        self.toolButtonOverlayColor.clicked.connect(lambda: self.button_color_select(self.toolButtonOverlayColor))
        self.toolButtonMarkerColor.clicked.connect(lambda: self.button_color_select(self.toolButtonMarkerColor))
        #self.toolButtonOverlayColor.setStyleSheet("background-color: white;")

        setattr(self.comboBoxMarker, "allItems", lambda: [self.comboBoxMarker.itemText(i) for i in range(self.comboBoxMarker.count())])
        setattr(self.comboBoxLineWidth, "allItems", lambda: [self.comboBoxLineWidth.itemText(i) for i in range(self.comboBoxLineWidth.count())])
        setattr(self.comboBoxColorByField, "allItems", lambda: [self.comboBoxColorByField.itemText(i) for i in range(self.comboBoxColorByField.count())])
        setattr(self.comboBoxFieldColormap, "allItems", lambda: [self.comboBoxFieldColormap.itemText(i) for i in range(self.comboBoxFieldColormap.count())])

        self.comboBoxMarker.activated.connect(lambda: self.plot_scatter(save=False))
        self.doubleSpinBoxMarkerSize.valueChanged.connect(lambda: self.plot_scatter(save=False))
        #self.comboBoxColorByField.activated.connect(lambda: self.update_combo_boxes(self.comboBoxColorByField, self.comboBoxColorField))
        self.comboBoxColorByField.activated.connect(lambda: self.toggle_color_by_field(self.toolBox.currentIndex()))
        self.comboBoxColorField.activated.connect(lambda: self.plot_scatter(save=False))
        self.horizontalSliderMarkerAlpha.sliderReleased.connect(self.slider_alpha_changed)

        # Plot toolbar
        #-------------------------

        self.toolButtonHomeSV.clicked.connect(lambda: self.toolbar_plotting('home', 'SV', self.toolButtonHomeSV.isChecked()))
        # self.toolButtonHomeMV.clicked.connect

        self.toolButtonPanSV.clicked.connect(lambda: self.toolbar_plotting('pan', 'SV', self.toolButtonPanSV.isChecked()))
        # self.toolButtonPanMV.clicked.connect

        self.toolButtonZoomSV.clicked.connect(lambda: self.toolbar_plotting('zoom', 'SV', self.toolButtonZoomSV.isChecked()))
        # self.toolButtonZoomMV.clicked.connect

        self.toolButtonPreferencesSV.clicked.connect(lambda: self.toolbar_plotting('preference', 'SV', self.toolButtonPreferencesSV.isChecked()))
        # self.toolButtonPreferencesMV.clicked.connect

        self.toolButtonAxesSV.clicked.connect(lambda: self.toolbar_plotting('axes', 'SV', self.toolButtonAxesSV.isChecked()))
        # self.toolButtonAxesMV.clicked.connect

        self.toolButtonSaveSV.clicked.connect(lambda: self.toolbar_plotting('save', 'SV', self.toolButtonSaveSV.isChecked()))
        # self.toolButtonSaveMV.clicked.connect

        self.actionCalculator.triggered.connect(self.open_calculator)

        self.toolbox_changed()


    def toolbox_changed(self):
        """Updates styles associated with toolbox page
        
        Executes on change of self.toolBox.currentIndex().  Updates style related widgets.
        """
        match self.toolBox.currentIndex():
            case self.sample_tab_id:
                self.comboBoxScatterType.setCurrentText(self.current_scatter_type[self.sample_tab_id])
                self.set_map_style()
                self.set_scatter_style()
                self.toggle_scatter_style_tab(self.sample_tab_id)
            case self.process_tab_id:
                self.set_map_style()
            case self.scatter_tab_id:
                self.comboBoxScatterType.setCurrentText(self.current_scatter_type[self.scatter_tab_id])
                self.set_scatter_style()
                self.set_map_style()
                self.toggle_scatter_style_tab(self.scatter_tab_id)
            case self.pca_tab_id:
                self.comboBoxScatterType.setCurrentText(self.current_scatter_type[self.pca_tab_id])
                self.set_scatter_style()
                self.set_map_style()
                self.toggle_scatter_style_tab(self.pca_tab_id)
            case self.profile_tab_id:
                self.comboBoxScatterType.setCurrentText(self.current_scatter_type[self.profile_tab_id])
                self.set_scatter_style()
                self.toggle_scatter_style_tab(self.profile_tab_id)
            case self.cluster_tab_id:
                self.set_map_style()

    def slider_alpha_changed(self):
        """Updates transparency on scatter plots.
        
        Executes on change of self.horizontalSliderMarkerAlpha.value().
        """
        self.labelMarkerAlpha.setText(str(self.horizontalSliderMarkerAlpha.value()))
        match self.toolBox.currentIndex():
            case self.scatter_tab_id:
                self.scatter_style[self.scatter_tab_id]['Alpha'] = float(self.horizontalSliderMarkerAlpha.value())
            case self.pca_tab_id:
                self.scatter_style[self.pca_tab_id]['Alpha'] = float(self.horizontalSliderMarkerAlpha.value())
            case self.profile_tab_id:
                self.scatter_style[self.profile_tab_id]['Alpha'] = float(self.horizontalSliderMarkerAlpha.value())
        
        self.plot_scatter(save=False)

    def input_ternary_name_dlg(self):
        """Opens a dialog to save new colormap
        
        Executes on self.toolButtonSaveTernaryColormap.clicked.
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
        
        Executes on self.toolButtonSwapXY.clicked.  Updates data dictionary and other map related derived results.
        """
        self.swap_xy_val = not self.swap_xy_val

        if self.swap_xy_val:
            self.order = 'C'
        else:

            self.order = 'F'
        # swap x and y
        # print(self.sample_data_dict[self.sample_id][['X','Y']])
        self.swap_xy_data(self.sample_data_dict[self.sample_id])

        self.swap_xy_data(self.clipped_isotope_data[self.sample_id]) #this rotates processed data as well

        self.swap_xy_data(self.cluster_results)

        # update plots
        self.update_all_plots()

    def swap_xy_data(self, df):
        """Swaps X and Y of a dataframe

        Swaps coordinates for all maps in sample dataframe.

        :param df: data frme to swap X and Y coordinates.
        :type df: pandas.DataFrame
        """
        xtemp = df['Y']
        df['Y'] = df['X']
        df['X'] = xtemp

    # toolbar functions
    def open_tab(self, tab_name):
        """Opens specified toolBox tab

        :param tab_name: opens tab, values: 'samples', 'preprocess', 'spot data', 'filter',
              'scatter', 'ndim', pca', 'clustering', 'profiles', 'special'
        :type tab_name: str
        """
        match tab_name.lower():
            case 'samples':
                self.toolBox.setCurrentIndex(self.sample_tab_id)
            case 'preprocess':
                self.toolBox.setCurrentIndex(self.process_tab_id)
            case 'spot data':
                self.toolBox.setCurrentIndex(self.spot_tab_id)
            case 'filter':
                self.toolBox.setCurrentIndex(self.filter_tab_id)
                self.tabWidget.setCurrentIndex(1)
            case 'scatter':
                self.toolBox.setCurrentIndex(self.scatter_tab_id)
            case 'ndim':
                self.toolBox.setCurrentIndex(self.ndim_tab_id)
            case 'pca':
                self.toolBox.setCurrentIndex(self.pca_tab_id)
            case 'clustering':
                self.toolBox.setCurrentIndex(self.cluster_tab_id)
                self.tabWidget.setCurrentIndex(2)
            case 'profiles':
                self.toolBox.setCurrentIndex(self.profile_tab_id)
            case 'special':
                self.toolBox.setCurrentIndex(self.special_tab_id)

    def change_ref_material(self, comboBox1, comboBox2):
        """Changes reference computing normalized isotopes

        Sets all QComboBox to a common normalizing reference.

        :param comboBox1: user changed QComboBox
        :type comboBox1: QComboBox
        :param comboBox2: QComboBox to update
        :type comboBox2: QComboBox
        """
        comboBox2.setCurrentIndex(comboBox1.currentIndex())
        self.update_all_plots()

    def reset_to_full_view(self):
        """Reset the map to full view (i.e., remove crop)
        
        Executes on self.toolButtonFullView.clicked.
        """
        #set original bounds
        self.crop_x_max = self.x_max
        self.crop_x_min = self.x_min
        self.crop_y_max = self.y_max
        self.crop_y_min = self.y_min
        #remove crop overlays
        self.crop_tool.remove_overlays()
        # reset current plot df and mask to original
        # self.current_plot_df = self.current_plot_df_copy.copy()
        # self.mask = self.mask.copy()
        # self.cluster_results = self.cluster_results_copy
        
        # reset clipped_isotope_data and self.computed_isotope_data and current_plot_df
        sample_id = self.current_plot_information['sample_id']
        self.clipped_isotope_data[self.sample_id] = copy.deepcopy(self.isotope_data[self.sample_id])
        self.cropped_original_data[self.sample_id] = copy.deepcopy(self.isotope_data[self.sample_id])
        self.computed_isotope_data[self.sample_id] = {
            'ratio':None,
            'calculated':None,
            'special':None,
            'PCA score':None,
            'cluster':None,
            'cluster score':None
            }
        
        #reset axis mask
        self.axis_mask = np.ones_like( self.sample_data_dict[self.sample_id]['X'], dtype=bool)
        self.mask = self.filter_mask & self.polygon_mask & self.axis_mask
        self.prep_data()
        self.update_all_plots()
        
        self.toolButtonCrop.setChecked(False)
        
        self.plot.getViewBox().autoRange()

    # get a named list of current fields for sample
    def get_field_list(self, set_name='isotope'):
        """Gets the fields associated with a defined set

        Set names are consistent with QComboBox.

        :param set_name: name of set list, options include 'isotope', 'isotope (normalized)', 'calcualated field',
            'pca_score', 'cluster', 'cluster score', 'special', Defaults to 'isotope'
        :type set_name: str, optional

        :return: set_fields, a list of fields within the input set
        :rtype: list
        """
        match set_name:
            case 'isotope' | 'isotope (normalized)':
                set_fields = self.isotopes_df.loc[self.isotopes_df['sample_id']==self.sample_id,'isotopes']
            case 'ratio':
                set_fields = self.ratios_df.loc[self.isotopes_df['sample_id']==self.sample_id,'isotope_1'] + ' / ' + self.ratios_df.loc[self.isotopes_df['sample_id']==self.sample_id,'isotope_2']
            case 'calculated field':
                set_fields = None
            case 'pca score':
                set_fields = None
            case 'cluster':
                set_fields = None
            case 'cluster score':
                set_fields = None
            case 'special':
                set_fields = None
        return set_fields

    # color picking functions
    def button_color_select(self, button):
        """Select background color of button

        :param button: button clicked
        :type button: QPushbutton | QToolButton
        """
        color = QColorDialog.getColor()

        if color.isValid():
            button.setStyleSheet("background-color: %s;" % color.name())
            if button.accessibleName().startswith('Ternary'):
                button.setCurrentText('user defined')

    def get_hex_color(self, color):
        """Converts QColor to hex-rgb format

        :param color: rgb formatted color
        :type color: QColor

        :return: hex-rgb color 
        """
        return "#{:02x}{:02x}{:02x}".format(color.red(), color.green(), color.blue())

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

    def open_calculator(self):
        isotopes_list = self.isotopes_df['isotopes'].values
        self.calWindow = CalWindow(isotopes_list,self.sample_data_dict[self.sample_id] )
        self.calWindow.show()

    def plot_profile_and_table(self):
        self.profiling.plot_profiles()
        self.profiling.update_table_widget()

    def update_clusters(self):
        selected_clusters = []
        for idx in self.tableWidgetViewGroups.selectionModel().selectedRows():
            selected_clusters.append(self.tableWidgetViewGroups.item(idx.row(), 0).text())

        if selected_clusters:
            self.current_group['clusters'] = selected_clusters
        else:
            self.current_group['clusters'] = None

    def update_color_bar_position(self):
        """Updates the color bar position on a figure
        
        Currently unused
        """
        # Get the selected color bar position
        color_bar_position = self.comboBoxColorbarDirection.currentText().lower()

        # Iterate over your plots to update the color bar position
        for key, value in self.plot_widget_dict.items():
            # Assume each value has a 'fig' attribute representing the Figure
            fig = value['widget'][0].figure
            ax = fig.axes[0]  # Assuming the first axis is the one with the color bar

            # Remove existing color bars
            for cbar in fig.colorbar_artists:
                cbar.remove()

            # Add color bar with new orientation
            if color_bar_position == 'horizontal':
                orientation = 'horizontal'
            else:  # Default to vertical if not horizontal
                orientation = 'vertical'

            # Create a new color bar with the new orientation
            img = ax.images[0]  # Assuming the first image is the one to apply color bar
            fig.colorbar(img, ax=ax, orientation=orientation)

            # Redraw the figure to update the changes
            fig.canvas.draw_idle()

    # def scale_plot(self, array, lq, uq, d_lb, d_ub, norm='linear', outlier=False):
    #     """Clips data to defined bounds.

    #     Referenced by :func:`update_plot` and :func:`get_map_data`

    #     :param current_plot_df: data and properties of current plot
    #     :type current_plot_df: dict
    #     :param lq: lower quantile
    #     :type lq: double
    #     :param uq: upper quantile
    #     :type uq: double
    #     :param d_lb: difference lower quantile
    #     :type d_lb: double
    #     :param d_ub: difference upper quantile
    #     :type d_ub: double
    #     :param norm: norm to use for data, options include 'linear', 'log', and 'logit', defaults to 'linear'
    #     :type norm: str, optional
    #     :param outlier: runs outlier detection, defaults to False
    #     :type outlier: bool, optional
    #     """
        
        
        
    #     if outlier: #run outlier detection algorithm
    #         isotope_array = self.outlier_detection(, lq, uq, d_lb,d_ub)
    #     else:
    #         lq_val = np.nanpercentile(isotope_array, lq, axis=0)
    #         uq_val = np.nanpercentile(isotope_array, uq, axis=0)
    #         isotope_array = np.clip(isotope_array, lq_val, uq_val)
    #     isotope_array = self.transform_plots(isotope_array)


    #     if norm == 'log':
    #         # np.nanlog handles NaN values
    #         isotope_array = np.log10(isotope_array, where=~np.isnan(isotope_array))
    #     elif norm == 'logit':
    #         # Handle division by zero and NaN values
    #         with np.errstate(divide='ignore', invalid='ignore'):
    #             isotope_array = np.log10(isotope_array / (10**6 - isotope_array), where=~np.isnan(isotope_array))

    #     current_plot_df.loc[:, 'array'] = self.transform_plots(isotope_array)

    #     return current_plot_df

    def auto_scale(self,update = False):
        """Auto-scales pixel values in map

        Executes on self.toolButtonAutoScale.clicked.
        
        Outliers can make it difficult to view the variations of values within a map.
        This is a larger problem for linear scales, but can happen when log-scaled. Auto-
        scaling the data clips the values at a lower and upper bound.  Auto-scaling may be
        acceptable as minerals that were not specifically calibrated can have erroneously
        high or low (even negative) values.

        :param update: update, auto scale parameters updates
        :type update: bool
        """
        if self.update_spinboxes_bool: # spinboxes are not being updated
            sample_id = self.current_plot_information['sample_id']
            isotope_1 = self.current_plot_information['isotope_1']
            isotope_2 = self.current_plot_information['isotope_2']
            plot_type = self.current_plot_information['plot_type']
            lb = self.doubleSpinBoxLB.value()
            ub = self.doubleSpinBoxUB.value()
            d_lb = self.doubleSpinBoxDLB.value()
            d_ub = self.doubleSpinBoxDUB.value()
            auto_scale = self.toolButtonAutoScale.isChecked()
            # if isotope_1 and not isotope_2:
            #     auto_scale_value = self.isotopes_df.loc[(self.isotopes_df['sample_id']==self.sample_id)
            #                      & (self.isotopes_df['isotopes']==isotope_1),'auto_scale'].values[0]
            # else:
            #     auto_scale_value = self.ratios_df.loc[(self.ratios_df['sample_id']==self.sample_id)
            #                              & (self.ratios_df['isotope_1']==isotope_1)
            #                              & (self.ratios_df['isotope_2']==isotope_2),'auto_scale'].values[0]

            print(auto_scale)
            if auto_scale and not update:
                #reset to default auto scale values
                lb = 0.05
                ub = 99.5
                d_lb = 99
                d_ub = 99

            elif not auto_scale and not update:
                # show unbounded plot when auto scale switched off
                lb = 0
                ub = 100

            if isotope_1 and not isotope_2:

                self.isotopes_df.loc[(self.isotopes_df['sample_id']==self.sample_id)
                                  & (self.isotopes_df['isotopes']==isotope_1),'auto_scale']  = auto_scale
                self.isotopes_df.loc[(self.isotopes_df['sample_id']==self.sample_id)
                                         & (self.isotopes_df['isotopes']==isotope_1),
                                         ['upper_bound','lower_bound','d_l_bound', 'd_u_bound']] = [ub,lb,d_lb, d_ub]

            else:
                self.ratios_df.loc[(self.ratios_df['sample_id']==self.sample_id)
                                         & (self.ratios_df['isotope_1']==isotope_1)
                                         & (self.ratios_df['isotope_2']==isotope_2),'auto_scale']  = auto_scale
                self.ratios_df.loc[(self.ratios_df['sample_id']==self.sample_id)
                                          & (self.ratios_df['isotope_1']==isotope_1)
                                          & (self.ratios_df['isotope_2']==isotope_2),
                                          ['upper_bound','lower_bound','d_l_bound', 'd_u_bound']] = [ub,lb,d_lb, d_ub]
            #self.get_map_data(self.sample_id, isotope_1 = isotope_1, isotope_2 = isotope_2, plot_type = plot_type, update = True)
            self.prep_data(sample_id, isotope_1,isotope_2)
            self.update_filter_values()

    def apply_crop(self):
        current_plot_df = self.current_plot_df
        sample_id = self.current_plot_information['sample_id']
        
        
        self.axis_mask = ((current_plot_df['X'] >= self.crop_x_min) & (current_plot_df['X'] <= self.crop_x_max) &
                       (current_plot_df['Y'] <= current_plot_df['Y'].max() - self.crop_y_min) & (current_plot_df['Y'] >= current_plot_df['Y'].max() - self.crop_y_max))
        
        
        #crop original_data based on self.axis_mask
        self.cropped_original_data[sample_id] = self.isotope_data[sample_id][self.axis_mask].reset_index(drop=True) 
                        
        
        #crop clipped_isotope_data based on self.axis_mask
        self.clipped_isotope_data[sample_id] = self.clipped_isotope_data[sample_id][self.axis_mask].reset_index(drop=True)
        
        #crop each df of computed_isotope_data based on self.axis_mask
        for analysis_type, df in self.computed_isotope_data[sample_id].items():
            if isinstance(df, pd.DataFrame):
                df = df[self.axis_mask].reset_index(drop=True)
        
        self.mask = self.mask[self.axis_mask]
        self.prep_data(sample_id)
        self.update_all_plots()


    def update_plot(self,bin_s = True, axis = False, reset= False):
        """"Update plot
        
        :param bin_s: Defaults to True
        :type bin_s: bool, optional
        :param axis: Defaults to False
        :type axis: bool, optional
        :param reset: Defaults to False
        :type reset: bool, optional"""
        if self.update_spinboxes_bool:
            self.canvasWindow.setCurrentIndex(0)
            lb = self.doubleSpinBoxLB.value()
            ub = self.doubleSpinBoxUB.value()
            d_lb = self.doubleSpinBoxDLB.value()
            d_ub = self.doubleSpinBoxDUB.value()


            bins = self.spinBoxNBins.value()
            isotope_str = self.current_plot
            isotope_str_list = isotope_str.split('_')
            auto_scale = self.toolButtonAutoScale.isChecked()
            sample_id = self.current_plot_information['sample_id']
            isotope_1 = self.current_plot_information['isotope_1']
            isotope_2 = self.current_plot_information['isotope_2']
            plot_type = self.current_plot_information['plot_type']
            plot_name = self.current_plot_information['plot_name']
            current_plot_df = self.current_plot_df
            
            # current_plot_df = self.scale_plot(current_plot_df, lq= lb, uq=ub,d_lb=d_lb, d_ub=d_ub)

            # Computing data range using the 'array' column
            data_range = current_plot_df['array'].max() - current_plot_df['array'].min()
            #change axis range for all plots in sample
            if axis:
                print(self.crop_x_min)
                # self.isotopes_df.loc[(self.isotopes_df['sample_id']==sample_id), ['x_min','x_max','y_min','y_max']] = [self.crop_x_min,self.crop_x_max,self.crop_y_min,self.crop_y_max]

                # self.ratios_df.loc[(self.ratios_df['sample_id']==sample_id), ['x_min','x_max','y_min','y_max']] = [self.crop_x_min,self.crop_x_max,self.crop_y_min,self.crop_y_max]
                # Filtering rows based on the conditions on 'X' and 'Y' columns
                self.axis_mask = ((current_plot_df['X'] >= self.crop_x_min) & (current_plot_df['X'] <= self.crop_x_max) &
                               (current_plot_df['Y'] <= current_plot_df['Y'].max() - self.crop_y_min) & (current_plot_df['Y'] >= current_plot_df['Y'].max() - self.crop_y_max))
                
                
                #crop original_data based on self.axis_mask
                self.cropped_original_data[sample_id] = self.isotope_data[sample_id][self.axis_mask].reset_index(drop=True) 
                                
                
                #crop clipped_isotope_data based on self.axis_mask
                self.clipped_isotope_data[sample_id] = self.clipped_isotope_data[sample_id][self.axis_mask].reset_index(drop=True)
                
                #crop each df of computed_isotope_data based on self.axis_mask
                for analysis_type, df in self.computed_isotope_data[sample_id].items():
                    if isinstance(df, pd.DataFrame):
                        df = df[self.axis_mask].reset_index(drop=True)
                
                
                self.prep_data(sample_id)
                
            # self.clipped_isotope_data[sample_id][isotope_1] = current_plot_df['array'].values
            # self.update_norm(sample_id, isotope = isotope_1)
            
            # make copy of current_plot_df and crop of
            # self.isotope_data['sample_id']
            # self.current_plot_df_copy = self.current_plot_df.copy()
            # self.mask_copy = self.mask.copy()
            # self.cluster_results_copy = self.cluster_results.copy()
            # self.current_plot_df = current_plot_df[self.axis_mask].reset_index(drop=True)
            # self.cluster_results = self.cluster_results[self.axis_mask].reset_index(drop=True)
            # self.mask = self.mask[self.axis_mask]
            
            if plot_type=='histogram':
                if reset:
                    bins  = self.default_bins
                # If bin_width is not specified, calculate it
                if bin_s:
                    bin_width = data_range / bins
                    self.spinBoxBinWidth.setValue(int(np.floor(bin_width)))
                else:
                    bin_width = self.spinBoxBinWidth.value()
                    bins = int(np.floor(data_range / bin_width))
                    self.spinBoxNBins.setValue(bins)
                self.plot_histogram(self.current_plot_df,self.current_plot_information, bin_width )
            else:
                self.plot_laser_map(self.current_plot_df, self.current_plot_information)
            # self.add_plot(isotope_str,clipped_isotope_array)
            self.add_edge_detection()
            self.add_noise_reduction()

    def remove_multi_plot(self, selected_plot_name):
        """Removes selected plot from MulitView
        
        :param selected_plot_name:
        :type selected_plot_name:
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

    def add_plot(self, plot_information, current_plot_df = None):
        """Adds plot to plot widget dictionary and displays in selected view tab
        
        :param plot_information:
        :type plot_information: dict
        :param current_plot_df: Defaults to None
        :param type: dict, optional
        """
        plot_name = plot_information['plot_name']
        sample_id = plot_information['sample_id']
        plot_type = plot_information['plot_type']


        #get plot widget and view from plot_widget_dict
        for widget, view in zip(self.plot_widget_dict[plot_type][sample_id][plot_name]['widget'],self.plot_widget_dict[plot_type][sample_id][plot_name]['view']):
            if view == self.canvasWindow.currentIndex():
                selected_plot_widget = widget
                continue
            else:
                selected_plot_widget = widget

        if (self.canvasWindow.currentIndex() == 1) and plot_name not in self.multi_view_index:
            #Multi view
            layout = self.widgetMultiView.layout()

            # Set the inner grid layout for the inner widget
            layout.addWidget(selected_plot_widget)

            # Set spacing to 0 to remove gaps between widgets
            layout.setSpacing(0)

            # Set margins to 0 if you want to remove margins as well
            layout.setContentsMargins(0, 0, 0, 0)
            # show plot sinc parent is visible
            selected_plot_widget.show()
            #remove tab
            #self.canvasWindow.removeTab(tab_index)
            #get the the index of plot on multiview
            self.multi_view_index.append(plot_name)
            #self.canvasWindow.setEnabled(index,False)
            #self.add_remove(plot_name)
            #reduce the index of widgets right hand side of index tab by one
            self.comboBoxPlots.clear()
            self.comboBoxPlots.addItems(self.multi_view_index)
        elif self.canvasWindow.currentIndex() == 0:
            #Single view
            self.single_plot_name = plot_name

            #remove plot from multi view if the plot is already in multiview

            layout = self.widgetSingleView.layout()
            #remove current plot
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                if item is not None:
                    widget = item.widget()   # Get the widget from the item
                    if widget is not None:
                        layout.removeWidget(widget)  # Remove the widget from the layout
                        widget.setParent(None)      # Set the widget's parent to None
            # selected_plot_widget = self.plot_widget_dict[plot_type][sample_id][plot_name]['widget']
            self.current_plot = plot_name
            self.current_plot_information = plot_information
            self.current_plot_df = current_plot_df
            layout.addWidget(selected_plot_widget)
            selected_plot_widget.show()

            # Assuming widgetClusterMap is a QWidget with a QVBoxLayout containing figure_canvas
            for i in range(selected_plot_widget.layout().count()):
                widget = selected_plot_widget.layout().itemAt(i).widget()
                if isinstance(widget, FigureCanvas):
                    self.matplotlib_canvas = widget
                    self.pyqtgraph_widget = None
                    break
                elif isinstance(widget, pg.GraphicsLayoutWidget):
                    self.pyqtgraph_widget = widget
                    self.matplotlib_canvas = None
                    break

        # After adding the plots, refresh windows to fix toggle button issue
        self.hide()
        self.show()
    
    def save_analysis(self, location):
        
        
        
        pass
    
    
    def reset_analysis(self):
        self.isotopes_df = pd.DataFrame(columns = ['sample_id', 'isotopes', 'norm','upper_bound','lower_bound','d_l_bound','d_u_bound', 'use'])
        self.ratios_df = pd.DataFrame(columns = ['sample_id', 'isotope_1','isotope_2', 'norm','upper_bound','lower_bound','d_l_bound','d_u_bound', 'use', 'auto_scale'])
        self.filter_df = pd.DataFrame(columns = ['sample_id', 'isotope_1', 'isotope_2', 'ratio','norm','f_min','f_max', 'use'])
        self.cluster_results=pd.DataFrame(columns = ['Fuzzy', 'KMeans', 'KMediods'])
        self.clipped_ratio_data = pd.DataFrame()
        self.isotope_data = {}  #stores orginal isotope data
        self.clipped_isotope_data = {} # stores processed isotoped data
        self.computed_isotope_data = {} # stores computed isotoped data (ratios, custom fields)
        self.sample_data_dict = {}
        self.plot_widget_dict ={'lasermap':{},'histogram':{},'lasermap_norm':{},'clustering':{},'scatter':{},'n-dim':{},'correlation':{}, 'pca':{}}
        self.multi_view_index = []
        self.laser_map_dict = {}
        self.multiview_info_label = {}
        self.selected_isotopes = []
        self.n_dim_list = []
        self.group_cmap = {}
        self.lasermaps = {}
        self.norm_dict = {} #holds values (log, logit, linear) of all isotopes
        self.proxies = []
        self.treeModel.clear()
        
        self.create_tree()
        self.change_sample(self.comboBoxSampleId.currentIndex())
        
        
        
        pass
    
    def clear_analysis(self):
        # clears analysis 
        
        pass

    # def activate_ratios(self, state):
    #     """Adds ratios selection as options to certain comboBoxes and plot tree

    #     Activate ratios by selecting them in the Isotope Select dialog.

    #     :param state: 
    #     :type state: bool

    #     """
    #     if state == 2:  # Qt.Checked
    #         # Call your method here when the comboBox is checked
    #         self.labelIsotope_2.setEnabled(True)
    #         self.comboBoxIsotope_2.setEnabled(True)
    #         self.get_map_data(self.sample_id,
    #                           isotope_1=self.comboBoxIsotope_1.currentText(),
    #                           isotope_2=self.comboBoxIsotope_2.currentText(),view = 1)
    #         self.toolButtonAddRatio.setEnabled(True)
    #     else:
    #         self.labelIsotope_2.setEnabled(False)
    #         self.comboBoxIsotope_2.setEnabled(False)
    #         self.get_map_data(self.sample_id,isotope_1=self.comboBoxIsotope_1.currentText())
    #         self.toolButtonAddRatio.setEnabled(False)

    def update_filter_values(self):
        isotope_1 = self.comboBoxFIsotope.currentText()
        isotope_2 = None
        isotope_select = self.comboBoxFSelect.currentText()

        if isotope_select == 'Isotope':
            f_val = self.isotopes_df.loc[(self.isotopes_df['sample_id'] == self.sample_id)
                                        & (self.isotopes_df['isotopes'] == isotope_1)].iloc[0][['v_min', 'v_max']]
        else:
            if '/' in isotope_1:
                isotope_1, isotope_2 = isotope_1.split(' / ')
                f_val = self.ratios_df.loc[(self.ratios_df['sample_id'] == self.sample_id)
                                            & (self.ratios_df['isotope_1'] == isotope_1)& (self.ratios_df['isotope_2'] == isotope_2)].iloc[0][['v_min', 'v_max']]

        self.lineEditFMin.setText(str(self.dynamic_format(f_val['v_min'])))
        self.lineEditFMax.setText(str(self.dynamic_format(f_val['v_max'])))

    def update_filter_table(self):
        """Update data for analysis when fiter table is updated."""
        # open tabFilterList
        self.tabWidget.setCurrentIndex(1)

        def on_use_checkbox_state_changed(row, state):
            # Update the 'use' value in the filter_df for the given row
            self.filter_df.at[row, 'use'] = state == QtCore.Qt.Checked


        isotope_1 = self.comboBoxFIsotope.currentText()
        isotope_2 = None
        isotope_select = self.comboBoxFSelect.currentText()
        f_min = float(self.lineEditFMin.text())
        f_max = float(self.lineEditFMax.text())
        # Add a new row at the end of the table
        row = self.tableWidgetFilters.rowCount()
        self.tableWidgetFilters.insertRow(row)

        # Create a QCheckBox for the 'use' column
        chkBoxItem_use = QtWidgets.QCheckBox()
        chkBoxItem_use.setCheckState(QtCore.Qt.Checked)
        chkBoxItem_use.stateChanged.connect(lambda state, row=row: on_use_checkbox_state_changed(row, state))

        chkBoxItem_select = QTableWidgetItem()
        chkBoxItem_select.setFlags(QtCore.Qt.ItemIsUserCheckable |
                            QtCore.Qt.ItemIsEnabled)
        ratio = False
        if isotope_select == 'Isotope':
            chkBoxItem_select.setCheckState(QtCore.Qt.Unchecked)
            norm = self.isotopes_df.loc[(self.isotopes_df['sample_id'] == self.sample_id)
                                        & (self.isotopes_df['isotopes'] == isotope_1)].iloc[0]['norm']
        else:
            if '/' in isotope_1:
                ratio = True
                isotope_1, isotope_2 = isotope_1.split(' / ')
                norm = self.ratios_df.loc[(self.ratios_df['sample_id'] == self.sample_id)
                                          & (self.ratios_df['isotope_1'] == isotope_1) & (self.ratios_df['isotope_2'] == isotope_2)].iloc[0]['norm']

        self.tableWidgetFilters.setCellWidget(row, 0, chkBoxItem_use)
        self.tableWidgetFilters.setItem(row, 1,
                                 QtWidgets.QTableWidgetItem(self.sample_id))
        self.tableWidgetFilters.setItem(row, 2,
                                 QtWidgets.QTableWidgetItem(isotope_1))
        self.tableWidgetFilters.setItem(row, 3,
                                 QtWidgets.QTableWidgetItem(isotope_2))

        self.tableWidgetFilters.setItem(row, 4,
                                 QtWidgets.QTableWidgetItem(ratio))

        self.tableWidgetFilters.setItem(row, 5,
                                 QtWidgets.QTableWidgetItem(self.dynamic_format(f_min)))
        self.tableWidgetFilters.setItem(row, 6,
                                 QtWidgets.QTableWidgetItem(self.dynamic_format(f_max)))


        self.tableWidgetFilters.setItem(row, 7,
                                 chkBoxItem_select)


        filter_info = {'sample_id': self.sample_id, 'isotope_1': isotope_1, 'isotope_2': isotope_2, 'ratio': ratio,'norm':norm ,'f_min': f_min,'f_max':f_max, 'use':True}
        self.filter_df.loc[len(self.filter_df)]=filter_info

    def remove_selected_rows(self,sample):
        """Remove selected rows from filter table.
        
        :param sample:
        :type sample:
        """
        # We loop in reverse to avoid issues when removing rows
        for row in range(self.tableWidgetFilters.rowCount()-1, -1, -1):
            chkBoxItem = self.tableWidgetFilters.item(row, 7)
            sample_id = self.tableWidgetFilters.item(row, 1).text()
            isotope_1 = self.tableWidgetFilters.item(row, 2).text()
            isotope_2 = self.tableWidgetFilters.item(row, 3).text()
            ratio = bool(self.tableWidgetFilters.item(row, 4).text())
            if chkBoxItem.checkState() == QtCore.Qt.Checked:
                self.tableWidgetFilters.removeRow(row)
                if not ratio:
                    self.filter_df.drop(self.filter_df[(self.filter_df['sample_id'] == sample_id)
                                           & (self.filter_df['isotope_1'] == isotope_1)& (self.filter_df['ratio'] == ratio)].index, inplace=True)
                else:
                    # Remove corresponding row from filter_df
                    self.filter_df.drop(self.filter_df[(self.filter_df['sample_id'] == sample_id)
                                           & (self.filter_df['isotope_1'] == isotope_1)& (self.filter_df['isotope_2'] == isotope_2)].index, inplace=True)
        self.apply_filters(sample_id)

    def apply_filters(self, fullmap=False):
        """Applies filter to map data
        
        Applies user specified data filters to mask data for analysis

        :param fullmap: If True, filters are ignored, otherwise filter maps, Defaults to False
        :type fullmap: bool, optional"""
        #reset all masks
        self.polygon_mask = np.ones_like( self.mask, dtype=bool)
        self.filter_mask = np.ones_like( self.mask, dtype=bool)
        
        
        if fullmap:
            #user clicked on Map viewable
            self.toolButtonFilterToggle.setChecked(False)
            self.toolButtonMapPolygon.setChecked(False)
            self.toolButtonMapMask.setChecked(False)
            
        elif self.toolButtonFilterToggle.isChecked():
            # Check if rows in self.filter_df exist and filter array in current_plot_df
            # by creating a mask based on f_min and f_max of the corresponding filter isotopes
            self.filter_mask = np.ones_like(self.filter_mask, dtype=bool)
            for index, filter_row in self.filter_df.iterrows():
                if filter_row['use'] and filter_row['sample_id'] == self.sample_id:
                    if not filter_row['isotope_2']:
                        isotope_df = self.get_map_data(sample_id=filter_row['sample_id'], name = filter_row['isotope_1'],analysis_type = 'isotope', plot =False )
                    else: #if ratio    
                        isotope_df = self.get_map_data(sample_id=filter_row['sample_id'], name =  filter_row['isotope_1']+'/'+filter_row['isotope_2'],analysis_type = 'ratio', plot =False )
                
                    self.filter_mask = self.filter_mask & (isotope_df['array'].values <= filter_row['f_min']) | (isotope_df['array'].values >= filter_row['f_max'])
        elif self.toolButtonMapPolygon.isChecked():
            # apply polygon mask
            # Iterate through each polygon in self.polygons
            for row in range(self.tableWidgetPolyPoints.rowCount()):
                #check if checkbox is checked
                use = self.tableWidgetPolyPoints.item(row,4)
                
                if use.checkState() == Qt.Checked:
                    p_id = int(self.tableWidgetPolyPoints.item(row,0).text())
            
                    polygon_points = self.polygon.polygons[p_id] 
                    polygon_points = [(x,y) for x,y,_ in polygon_points]
                    
                    # Convert the list of (x, y) tuples to a list of points acceptable by Path
                    path = Path(polygon_points)
                    
                    # Create a grid of points covering the entire array
                    # x, y = np.meshgrid(np.arange(self.array.shape[1]), np.arange(self.array.shape[0]))
                    
                    points = np.vstack((self.x.flatten(), self.y.flatten())).T
                    
                    # Use the path to determine which points are inside the polygon
                    inside_polygon = path.contains_points(points)
                    
                    # Reshape the result back to the shape of self.array
                    # inside_polygon_mask = inside_polygon.reshape(self.array.shape)
                    
                    # Update the polygon mask - include points that are inside this polygon
                    self.polygon_mask &= inside_polygon
                    
        elif self.toolButtonMapMask.isChecked():
            # apply map mask
            pass

        self.mask = self.filter_mask & self.polygon_mask & self.axis_mask
        self.update_all_plots()

    def dynamic_format(self,value, threshold=1e3):
        """Prepares number for display
        
        :param threshold: order of magnitude for determining display as floating point or expressing in engineering nootation, Defaults to 1e3
        :type threshold: double
        
        :return: number formatted as string
        :rtype: str
        """
        if abs(value) > threshold:
            return "{:.4e}".format(value)  # Scientific notation with 2 decimal places
        else:
            return "{:.4f}".format(value)

    def update_norm(self,sample_id, norm = None, isotope=None, update = False):
        """
        
        :param sample_id:
        :type sample_id: int
        :param norm: Defaults to None
        :type norm: optional
        :param isotope:
        :type isotope:
        :param update:
        :type update:
        """
        if not norm:
            norm = self.isotopes_df.loc[(self.isotopes_df['sample_id']==sample_id)
                                 & (self.isotopes_df['isotopes']==isotope),'norm'].values[0]
        if isotope: #if normalising single isotope
            isotopes = [isotope]
            self.isotopes_df.loc[(self.isotopes_df['sample_id']==sample_id)
                                 & (self.isotopes_df['isotopes']==isotope),'norm'] = norm

        else: #if normalising all isotopes in sample
            self.isotopes_df.loc[(self.isotopes_df['sample_id']==sample_id),'norm'] = norm
            isotopes = self.isotopes_df[self.isotopes_df['sample_id']==sample_id]['isotopes']
            
        
        self.prep_data(sample_id, isotope)
        
        #update self.norm_dict
        for isotope in isotopes:
            self.norm_dict[sample_id][isotope] = norm
        
        if update:
            self.update_all_plots()
        # self.update_plot()

    def update_all_plots(self):
        """Updates all plots in plot widget dictionary"""
        self.cm = self.comboBoxMapColormap.currentText()
        for plot_type,sample_ids in self.plot_widget_dict.items():
            if plot_type == 'lasermap' or 'histogram' or 'lasermap_norm':
                for sample_id, plots in sample_ids.items():
                    for plot_name, plot in plots.items():
                        info = plot['info']
                        if not info['isotope_2']:
                            current_plot_df = self.get_map_data(sample_id=info['sample_id'], name = info['isotope_1'],analysis_type = 'isotope', plot =False )
                        else: #if ratio    
                            current_plot_df = self.get_map_data(sample_id=info['sample_id'], name =  info['isotope_1']+'/'+info['isotope_2'],analysis_type = 'ratio', plot =False )
                        
                        # self.plot_laser_map(current_plot_df,info)
                            
                        self.create_plot(current_plot_df, info['sample_id'], plot_type = plot_type, isotope_1=info['isotope_1'], isotope_2 = info['isotope_2'], plot= False)
            else:
                for sample_id, plots in sample_ids.items():
                    for plot_name, plot in plots.items():
                        # Retrieve the widget and figure for the specified plot
                        plot_widget = plot['widget'][0]
                        figure_canvas = plot_widget.layout().itemAt(0).widget()
                        fig = figure_canvas.figure
                        if plot_type == 'clustering':
                                    n_clusters = int(plot['info']['n_clusters'])
                                    # Get the new colormap from the comboBox
                                    new_cmap = plt.get_cmap(self.cm,5)
                                    img = []
                                    for ax in fig.get_axes():
                                        # Retrieve the image object from the axes
                                        # Recalculate boundaries and normalization based on the new colormap and clusters

                                        boundaries = np.arange(-0.5, n_clusters, 1)
                                        norm = BoundaryNorm(boundaries, n_clusters, clip=True)
                                        images = ax.get_images()
                                        if len(images)>0:
                                            im = images[0]
                                            img.append([ax,im]) #store image and axis in list
                                            # Update image with the new colormap and normalization
                                            im.set_cmap(new_cmap)
                                            im.set_norm(norm)
                                    for (ax, im) in img:
                                        #remove colobar axis

                                        cb = im.colorbar

                                        # Do any actions on the colorbar object (e.g. remove it)
                                        cb.remove()
                                        # Redraw the canvas to reflect the updates
                                        #plot new colorbar
                                        fig.colorbar(im, ax=ax, boundaries=boundaries[:-1], ticks=np.arange(n_clusters), orientation=self.comboBoxColorbarDirection.currentText().lower())
                                        figure_canvas.draw()
                                    # Redraw the figure layout to adjust for any changes
                                    fig.tight_layout()
                                    # Redraw the canvas to reflect the updates
                                    figure_canvas.draw()
                        elif plot_type == 'scatter':
                            # Retrieve the plot information
                            plot_info = plot['info']
                            #remove colorbar
                            fig.axes[1].clear()
                            fig.axes[1].remove()
                            # fig.axes[1].clear()
                            fig.subplots_adjust(bottom=0)  #default right padding
                            # figure_canvas.draw()
                            # fig.tight_layout()  # Automatically adjust layout
                            #self.plot_scatter(update= True, values = plot_info['values'], plot_type = plot_info['plot_type'], fig =plot_info['fig'], ternary_plot = plot_info['ternary_plot'] )
                            self.plot_scatter(values=plot_info['values'], fig=plot_info['fig'], save=True)
                            fig.tight_layout()
                            figure_canvas.draw()
                            
                            
    def prep_data(self, sample_id= None, isotope_1= None, isotope_2 = None):
        """Prepares data to be used in analysis
        
        1. Obtains raw DataFrame
        2. Shifts isotope values so that all values are postive
        3. Scale data  (linear,log, loggit)
        4. Autoscales data if choosen by user
        
        The prepped data is stored in one of 2 Dataframes: analysis_isotope_data or computed_isotope_data
        """
        
        if sample_id is None:
            sample_id = self.sample_id #set to default sample_id
        
        if isotope_1: #if single isotope
            isotopes = [isotope_1]
        else: #if isotope is not provided update all isotopes in isotopes_df
            isotopes = self.isotopes_df[self.isotopes_df['sample_id']==sample_id]['isotopes']
            
        isotope_info = self.isotopes_df.loc[(self.isotopes_df['sample_id'] == sample_id) & 
                                 (self.isotopes_df['isotopes'].isin(isotopes))]
        
        
        if not isotope_2: #not a ratio
            # shifts isotope values so that all values are postive
            adj_data = pd.DataFrame(self.transform_plots(self.cropped_original_data[sample_id][isotopes].values), columns= isotopes)
            
            
            #perform scaling for groups of isotopes with same norm parameter
            for norm in isotope_info['norm'].unique():
                filtered_isotopes = isotope_info[(isotope_info['norm'] == norm)]['isotopes']
                filtered_data = adj_data[filtered_isotopes].values
                if norm == 'log':
                    
                    # np.nanlog handles NaN value
                    self.clipped_isotope_data[sample_id].loc[:,filtered_isotopes] = np.log10(filtered_data, where=~np.isnan(filtered_data))
                    # print(self.processed_isotope_data[sample_id].loc[:10,isotopes])
                    # print(self.clipped_isotope_data[sample_id].loc[:10,isotopes])
                elif norm == 'logit':
                    # Handle division by zero and NaN values
                    with np.errstate(divide='ignore', invalid='ignore'):
                        isotope_array = np.log10(filtered_data / (10**6 - filtered_data), where=~np.isnan(filtered_data))
                        self.clipped_isotope_data[sample_id].loc[:,filtered_isotopes] = isotope_array
                else:
                    # set to clipped data with original values if linear normalisation
                    self.clipped_isotope_data[sample_id].loc[:,filtered_isotopes] = filtered_data
            
            
            # perform autoscaling on columns where auto_scale is set to true
            for auto_scale in isotope_info['auto_scale'].unique():
                filtered_isotopes = isotope_info[isotope_info['auto_scale'] == auto_scale]['isotopes']
                
                for isotope_1 in filtered_isotopes:
                    parameters = isotope_info.loc[(self.isotopes_df['sample_id']==sample_id)
                                          & (self.isotopes_df['isotopes']==isotope_1)].iloc[0]
                    filtered_data = self.clipped_isotope_data[sample_id][isotope_1].values
                    lq = parameters['lower_bound']
                    uq = parameters['upper_bound']
                    d_lb = parameters['d_l_bound']
                    d_ub = parameters['d_u_bound']
                    if auto_scale:

                        self.clipped_isotope_data[sample_id].loc[:,isotope_1] = self.outlier_detection(filtered_data.reshape(-1, 1),lq, uq, d_lb,d_ub)
                    else:
                        #clip data using ub and lb
                        lq_val = np.nanpercentile(filtered_data, lq, axis=0)
                        uq_val = np.nanpercentile(filtered_data, uq, axis=0)
                        filtered_data = np.clip(filtered_data, lq_val, uq_val)
                        self.clipped_isotope_data[sample_id].loc[:,isotope_1] = filtered_data
                    
                    
                    # update v_min and v_max in self.isotope_df
                    self.isotopes_df.loc[(self.isotopes_df['sample_id'] == sample_id) & 
                                             (self.isotopes_df['isotopes']==isotope_1),'v_max'][0] = filtered_data.min()
                    self.isotopes_df.loc[(self.isotopes_df['sample_id'] == sample_id) & 
                                             (self.isotopes_df['isotopes']==isotope_1), 'v_min'][0] = filtered_data.min()
            
            self.clipped_isotope_data[sample_id]['X'] = self.sample_data_dict[sample_id]['X']
            self.clipped_isotope_data[sample_id]['Y'] = self.sample_data_dict[sample_id]['Y']
            
            # create deep copy of clipped isotope data for analalysis
            self.analysis_isotope_data = copy.deepcopy(self.clipped_isotope_data)
            
        else:  #if ratio
            ratio_df = self.isotope_data[sample_id][[isotope_1,isotope_2]] #consider original data for ratio
            
            ratio_name = isotope_1+' / '+isotope_2
            

            
            # shifts isotope values so that all values are postive
            ratio_array = self.transform_plots(ratio_df.values)
            ratio_df = pd.DataFrame(filtered_data, columns= [isotope_1,isotope_2])

            mask = (ratio_df[isotope_1] > 0) & (ratio_df[isotope_2] > 0)

            ratio_array = np.where(mask, ratio_array[:,0] / ratio_array[:,0], np.nan)

            # Get the index of the row that matches the criteria
            index_to_update = self.ratios_df.loc[
                (self.ratios_df['sample_id'] == sample_id) &
                (self.ratios_df['isotope_1'] == isotope_1) &
                (self.ratios_df['isotope_2'] == isotope_2)
            ].index

            # Check if we found such a row
            if len(index_to_update) > 0:
                idx = index_to_update[0]

                if pd.isna(self.ratios_df.at[idx, 'lower_bound']): #if bounds are not updated in dataframe
                    norm = self.ratios_df.at[idx, 'norm']
                    self.ratios_df.at[idx, 'lower_bound'] = 0.05
                    self.ratios_df.at[idx, 'upper_bound'] = 99.5
                    self.ratios_df.at[idx, 'd_l_bound'] = 99
                    self.ratios_df.at[idx, 'd_u_bound'] = 99
                    
                else: #if bounds exist in ratios_df
                    norm = self.ratios_df.at[idx, 'norm']
                    lb = self.ratios_df.at[idx, 'lower_bound']
                    ub = self.ratios_df.at[idx, 'upper_bound']
                    d_lb = self.ratios_df.at[idx, 'd_l_bound']
                    d_ub = self.ratios_df.at[idx, 'd_u_bound']
                    auto_scale = self.ratios_df.at[idx, 'auto_scale']

                    
                    parameters = isotope_info.loc[(self.isotopes_df['sample_id']==sample_id)
                                          & (self.isotopes_df['isotopes']==isotope_1)].iloc[0]
                    # ratio_array = current_plot_df['array'].values
                    lb = parameters['lower_bound']
                    ub = parameters['upper_bound']
                    d_lb = parameters['d_l_bound']
                    d_ub = parameters['d_u_bound']
                
                if norm == 'log':
                    
                    # np.nanlog handles NaN value
                    ratio_array = np.log10(ratio_array, where=~np.isnan(ratio_array))
                    # print(self.processed_isotope_data[sample_id].loc[:10,isotopes])
                    # print(self.clipped_isotope_data[sample_id].loc[:10,isotopes])
                elif norm == 'logit':
                    # Handle division by zero and NaN values
                    with np.errstate(divide='ignore', invalid='ignore'):
                        ratio_array = np.log10(ratio_array / (10**6 - ratio_array), where=~np.isnan(ratio_array))
                else:
                    # set to clipped data with original values if linear normalisation
                    pass
                    
                if auto_scale:

                    ratio_array = self.outlier_detection(ratio_array,lq, uq, d_lb,d_ub)
                else:
                    #clip data using ub and lb
                    lq_val = np.nanpercentile(ratio_array, lq, axis=0)
                    uq_val = np.nanpercentile(ratio_array, uq, axis=0)
                    ratio_array = np.clip(ratio_array, lq_val, uq_val)
                self.computed_isotope_data[sample_id]['ratio'][ratio_name] = ratio_array

                self.ratios_df.at[idx, 'v_min'] = ratio_array.min()
                self.ratios_df.at[idx, 'v_max'] = ratio_array.max()
    
        

    def open_directory(self):
        """Open directory with samples
        
        Executes on self.toolBar.actionOpen and self.menuFile.action.Open_Directory.  self.toolBox
        pages are enabled upon successful load.

        Opens a dialog to select directory filled with samples.  Updates sample list in
        self.comboBoxSampleID and comboBoxes associated with isotope lists.  The first sample
        in list is loaded by default.
        """
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.Directory)
        # Set the default directory to the current working directory
        # dialog.setDirectory(os.getcwd())
        dialog.setDirectory('/Users/shavinkalu/Library/CloudStorage/GoogleDrive-a1904121@adelaide.edu.au/.shortcut-targets-by-id/1r_MeSExALnv9lHE58GoG7pbtC8TOwSk4/laser_mapping/Alex_garnet_maps/')
        if dialog.exec_():
            self.selected_directory = dialog.selectedFiles()[0]
            file_list = os.listdir(self.selected_directory)
            self.csv_files = [file for file in file_list if file.endswith('.csv')]
            if self.csv_files == []:
                # warning dialog
                return
            self.comboBoxSampleId.clear()
            self.comboBoxSampleId.addItems([os.path.splitext(file)[0] for file in self.csv_files])
            # Populate the sampleidcomboBox with the file names
            self.canvasWindow.setCurrentIndex(0)
            self.change_sample(0)
        # self.selected_directory='/Users/a1904121/LaserMapExplorer/laser_mapping/Alex_garnet_maps/processed data'
        # self.selected_directory='/Users/shavinkalu/Library/CloudStorage/GoogleDrive-a1904121@adelaide.edu.au/.shortcut-targets-by-id/1r_MeSExALnv9lHE58GoG7pbtC8TOwSk4/laser_mapping/Alex_garnet_maps/processed data'
        # self.selected_directory=''
        try:
            file_list = os.listdir(self.selected_directory)
        except:
            return
        self.csv_files = [file for file in file_list if file.endswith('.csv')]
        self.comboBoxSampleId.clear()
        self.comboBoxSampleId.addItems([os.path.splitext(file)[0] for file in self.csv_files])
        # Populate the sampleidcomboBox with the file names
        # self.canvasWindow.setCurrentIndex(0)
        # self.change_sample(0)

        self.toolBox.setCurrentIndex(self.sample_tab_id)

        self.SelectIsotopePage.setEnabled(True)
        self.PreprocessPage.setEnabled(True)
        self.SpotDataPage.setEnabled(True)
        self.FilterPage.setEnabled(True)
        self.ScatterPage.setEnabled(True)
        self.NDIMPage.setEnabled(True)
        self.PCAPage.setEnabled(True)
        self.ClusteringPage.setEnabled(True)
        self.ProfilingPage.setEnabled(True)
        self.SpecialFunctionPage.setEnabled(True)

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

    def plot_laser_map(self, current_plot_df, plot_information):
        plot_name = plot_information['plot_name']
        sample_id = plot_information['sample_id']
        plot_type = plot_information['plot_type']

        view = self.canvasWindow.currentIndex()
        
        self.x_range = current_plot_df['X'].max() - current_plot_df['X'].min()
        self.y_range = current_plot_df['Y'].max() - current_plot_df['Y'].min()
        self.x = current_plot_df['X'].values
        self.y = current_plot_df['Y'].values
        self.array_size = (current_plot_df['Y'].nunique(),current_plot_df['X'].nunique())
        
        array = np.reshape(current_plot_df['array'].values,
                                    self.array_size, order=self.order)
        duplicate = False
        plot_exist = False
        if plot_name in self.plot_widget_dict[plot_type][sample_id]:
            plot_exist = True
            duplicate = len(self.plot_widget_dict[plot_type][sample_id][plot_name]['view'])==1 and self.plot_widget_dict[plot_type][sample_id][plot_name]['view'][0] != self.canvasWindow.currentIndex()

        if plot_exist and not duplicate:
            widget_info = self.plot_widget_dict[plot_type][sample_id][plot_name]
            for widgetLaserMap, view in zip(widget_info['widget'],widget_info['view']):
                
                # Step 1: Normalize your data array for colormap application
                norm = Normalize(vmin=array.min(), vmax=array.max())
                cmap = plt.get_cmap(self.cm)  # Assuming self.cm is a valid colormap name
                
                # Step 2: Apply the colormap to get RGB values, then normalize to [0, 255] for QImage
                rgb_array = cmap(norm(array))[:, :, :3]  # Drop the alpha channel returned by cmap
                rgb_array = (rgb_array * 255).astype(np.uint8)
            
                # Step 3: Create an RGBA array where the alpha channel is based on self.mask
                rgba_array = np.zeros((*rgb_array.shape[:2], 4), dtype=np.uint8)
                rgba_array[:, :, :3] = rgb_array  # Set RGB channels
                
                mask_r = np.reshape(self.mask,
                                    self.array_size, order=self.order)
                
                rgba_array[:, :, 3] = np.where(mask_r, 255, 100)  # Set alpha channel based on self.mask
                            
                glw = widgetLaserMap.findChild(pg.GraphicsLayoutWidget, 'plotLaserMap')
                p1 = glw.getItem(0, 0)  # Assuming ImageItem is the first item in the plot
                img = p1.items[0]
                img.setImage(image=rgba_array)
                p1.invertY(True)   # vertical axis counts top to bottom
                #set aspect ratio of rectangle
                img.setRect(self.x.min(),self.y.min(),self.x_range,self.y_range)
                p1.setRange( yRange=[self.y.min(), self.y.max()])
                # To further prevent zooming or panning outside the default view, 
                p1.setLimits( yMin=self.y.min(), yMax = self.y.max())
                cm = pg.colormap.get(self.cm, source = 'matplotlib')
                # img.setColorMap(cm)
                histogram = widgetLaserMap.findChild(pg.HistogramLUTWidget, 'histogram')
                if view ==0:
                    # update variables which stores current plot in SV
                    self.plot = p1
                    self.array = array
                
                if histogram:
                    histogram.gradient.setColorMap(cm)
                    histogram.setImageItem(img)
                for i in reversed(range(p1.layout.count())):  # Reverse to avoid skipping due to layout change
                    item = p1.layout.itemAt(i)
                    if isinstance(item, pg.ColorBarItem):#find colorbar
                        item.setColorMap(cm)
                        item.setLevels([array.min(), array.max()])
                layout = widgetLaserMap.layout()
                # self.plot_laser_map_cont(layout,array,img,p1,cm,view)
        else:
            widgetLaserMap = QtWidgets.QWidget()
            layoutLaserMap = QtWidgets.QGridLayout()
            widgetLaserMap.setLayout(layoutLaserMap)
            layoutLaserMap.setSpacing(0)
            
            if duplicate:
                self.plot_widget_dict[plot_type][sample_id][plot_name]['widget'].append(widgetLaserMap)
                self.plot_widget_dict[plot_type][sample_id][plot_name]['view'].append(view)

            else:
                self.plot_widget_dict[plot_type][sample_id][plot_name] = {'widget':[widgetLaserMap],
                                                      'info':plot_information, 'view':[view]}
            
            #Change transparency of values outside mask
            # Step 1: Normalize your data array for colormap application
            norm = Normalize(vmin=array.min(), vmax=array.max())
            cmap = plt.get_cmap(self.cm)  # Assuming self.cm is a valid colormap name
        
            # Step 2: Apply the colormap to get RGB values, then normalize to [0, 255] for QImage
            rgb_array = cmap(norm(array))[:, :, :3]  # Drop the alpha channel returned by cmap
            rgb_array = (rgb_array * 255).astype(np.uint8)
        
            # Step 3: Create an RGBA array where the alpha channel is based on self.mask
            rgba_array = np.zeros((*rgb_array.shape[:2], 4), dtype=np.uint8)
            rgba_array[:, :, :3] = rgb_array  # Set RGB channels
            mask_r = np.reshape(self.mask,
                                self.array_size, order=self.order)
            
            rgba_array[:, :, 3] = np.where(mask_r, 255, 100)  # Set alpha channel based on self.mask
                        
            # self.array = array[:, ::-1]
            layout = widgetLaserMap.layout()
            glw = pg.GraphicsLayoutWidget(show=True)
            glw.setObjectName('plotLaserMap')
            # Create the ImageItem
            img = pg.ImageItem(image=rgba_array)

            #set aspect ratio of rectangle
            img.setRect(self.x.min(),self.y.min(),self.x_range,self.y_range)
            # img.setAs
            cm = pg.colormap.get(self.cm, source = 'matplotlib')
            # img.setColorMap(cm)

            # img.setLookupTable(cm.getLookupTable())
            #--- add non-interactive image with integrated color ------------------
            p1 = glw.addPlot(0,0,title=plot_name.replace('_',' '))
            # p1.setRange(padding=0)
            p1.showAxes(False, showValues=(True,False,False,True) )
            p1.invertY(True)
            #supress right click menu
            p1.setMenuEnabled(False)

            p1.addItem(img)
            # print(p1.getAspectRatio())
            p1.setAspectLocked()
            p1.setRange( yRange=[self.y.min(), self.y.max()])
            # To further prevent zooming or panning outside the default view, 
            p1.setLimits( yMin=self.y.min(), yMax = self.y.max())

            # ... Inside your plotting function
            target = pg.TargetItem(symbol = '+', )
            target.setZValue(1e9)
            p1.addItem(target)

            # Optionally, configure the appearance
            # For example, set the size of the crosshair
            name = sample_id+plot_name+str(view)
            self.lasermaps[name] = (target, p1, view, array)

            #hide pointer
            target.hide()

            p1.scene().sigMouseClicked.connect(lambda event,array=array, k=name, plot=p1: self.plot_clicked(event,array, k, p1))

            if view == 1:
                #create label with isotope name
                #create another label for value of the corresponding plot
                labelInfoVL = QtWidgets.QLabel(self.groupBoxInfoM)
                # labelInfoVL.setMaximumSize(QtCore.QSize(20, 16777215))
                labelInfoVL.setObjectName("labelInfoVL"+name)
                labelInfoVL.setText(plot_name)
                font = QtGui.QFont()
                font.setPointSize(9)
                labelInfoVL.setFont(font)
                verticalLayout = QtWidgets.QVBoxLayout()
                # Naming the verticalLayout
                verticalLayout.setObjectName(plot_name + str(view))
                verticalLayout.addWidget(labelInfoVL)

                labelInfoV = QtWidgets.QLabel(self.groupBoxInfoM)
                labelInfoV.setObjectName("labelInfoV"+name)
                labelInfoV.setFont(font)
                verticalLayout.addWidget(labelInfoV)
                self.gridLayoutInfoM.addLayout(verticalLayout, 0, self.gridLayoutInfoM.count()+1, 1, 1)
                # Store the reference to verticalLayout in a dictionary
                self.multiview_info_label[name] = (labelInfoVL, labelInfoV)
            else:
                #remove previous plot in single view
                if self.prev_plot:
                    del self.lasermaps[self.prev_plot]
                # update variables which stores current plot in SV
                self.plot = p1
                self.array = array
                self.prev_plot = name
                self.init_zoom_view()
                # uncheck edge detection
                self.toolButtonEdgeDetection.setChecked(False)

            # Create a SignalProxy to handle mouse movement events
            # self.proxy = pg.SignalProxy(p1.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
            # Create a SignalProxy for this plot and connect it to mouseMoved

            p1.scene().sigMouseMoved.connect(lambda event,plot=p1: self.mouse_moved(event,plot))
            # proxy = pg.SignalProxy(p1.scene().sigMouseMoved, rateLimit=60, slot=self.mouse_moved)
            # self.proxies.append(proxy)  # Assuming self.proxies is a list to store proxies

            # print(p1.getAspectRatio())
            # p1.autoRange()
            layout.addWidget(glw, 0, 0, 3, 2)
            glw.setBackground('w')
            p1.autoRange()
            #add zoom window
            # self.setup_zoom_window(layout)
            print(self.cm)
            self.plot_laser_map_cont(layout,array,img,p1,cm,view)

    def mouse_moved(self,event,plot):
        pos_view = plot.vb.mapSceneToView(event)  # This is in view coordinates
        pos_scene = plot.vb.mapViewToScene(pos_view)  # Map from view to scene coordinates
        any_plot_hovered = False
        for k, (_, p, v, array) in self.lasermaps.items():
            # print(p.sceneBoundingRect(), pos)
            if p.sceneBoundingRect().contains(pos_scene) and v == self.canvasWindow.currentIndex() and not self.toolButtonPanSV.isChecked() and not self.toolButtonZoomSV.isChecked() :

                # mouse_point = p.vb.mapSceneToView(pos)
                mouse_point = pos_view
                x, y = mouse_point.x(), mouse_point.y()

                # print(x,y)
                x_i = round(x*array.shape[1]/self.x_range)
                y_i = round(y*array.shape[0]/self.y_range)


                # if hover within lasermap array 
                if 0 <= x_i < array.shape[1] and 0 <= y_i < array.shape[0] :
                    if not self.cursor and not self.toolButtonCrop.isChecked():
                        QtWidgets.QApplication.setOverrideCursor(Qt.BlankCursor)
                        self.cursor = True
                    any_plot_hovered = True
                    value = array[y_i, x_i]  # assuming self.array is numpy self.array

                    if self.canvasWindow.currentIndex() == 0:
                        if self.toolButtonPolyCreate.isChecked() or (self.toolButtonPolyMovePoint.isChecked() and self.point_selected):
                            # Update the position of the zoom view
                            self.update_zoom_view_position(x, y)
                            self.zoomViewBox.show()
                            self.polygon.show_polygon_lines(x,y)
                        # elif self.toolButtonCrop.isChecked() and self.crop_tool.start_pos: 
                        #     self.crop_tool.expand_rect(pos_view)
                        else:
                            # hide zoom view
                            self.zoomViewBox.hide()

                        self.labelInfoX.setText('X: '+str(round(x)))
                        self.labelInfoY.setText('Y: '+str(round(y)))
                        self.labelInfoV.setText('V: '+str(round(value,2)))
                    else: #multi-view
                        self.labelInfoXM.setText('X: '+str(round(x)))
                        self.labelInfoYM.setText('Y: '+str(round(y)))

                    for k, (target, _, _,array) in self.lasermaps.items():
                        if not self.toolButtonCrop.isChecked():
                            target.setPos(mouse_point)
                            target.show()
                            value = array[y_i, x_i]
                            if k in self.multiview_info_label:
                                self.multiview_info_label[k][1].setText('v: '+str(round(value,2)))
                # break
        if not any_plot_hovered and not self.toolButtonCrop.isChecked():
            QtWidgets.QApplication.restoreOverrideCursor()
            self.cursor = False
            for target,_, _, _ in self.lasermaps.values():
                target.hide() # Hide crosshairs if no plot is hovered
            # hide zoom view
            self.zoomViewBox.hide()
    
    def plot_clicked(self, event,array,k, plot,radius=5):
        
        # get click location
        click_pos = plot.vb.mapSceneToView(event.scenePos())
        x, y = click_pos.x(), click_pos.y()

        # Convert the click position to plot coordinates
        self.array_x = array.shape[1]
        self.array_y = array.shape[0]
        x_i = round(x*self.array_x/self.x_range)
        y_i = round(y*self.array_y/self.y_range)

        # Ensure indices are within plot bounds
        if not(0 <= x_i < self.array_x) or not(0 <= y_i < self.array_y):
            #do nothing
            return

        # elif self.toolButtonCrop.isChecked():
        #     self.crop_tool.create_rect(event, click_pos)
        # if event.button() == QtCore.Qt.LeftButton and self.main_window.pushButtonStartProfile.isChecked():
        elif self.toolButtonPlotProfile.isChecked() or self.toolButtonPointMove.isChecked():
            self.profiling.plot_profile_scatter(event, array, k, plot, x, y,x_i, y_i)
        
        elif self.toolButtonPolyCreate.isChecked() or self.toolButtonPolyMovePoint.isChecked() or self.toolButtonPolyAddPoint.isChecked() or self.toolButtonPolyRemovePoint.isChecked():
            self.polygon.plot_polygon_scatter(event, k, x, y,x_i, y_i)

    def plot_laser_map_cont(self,layout,array,img,p1,cm, view):
        # Single views
        if self.canvasWindow.currentIndex()==0 and view==self.canvasWindow.currentIndex():
            # Try to remove the colorbar just in case it was added somehow
            # for i in reversed(range(p1.layout.count())):  # Reverse to avoid skipping due to layout change
            #     item = p1.layout.itemAt(i)
            #     if isinstance(item, pg.ColorBarItem):
            #         p1.layout.removeAt(i)
            # Create the histogram item


            histogram = pg.HistogramLUTWidget( orientation='horizontal')
            histogram.setObjectName('histogram')
            histogram.gradient.setColorMap(cm)
            histogram.setImageItem(img)
            histogram.setBackground('w')
            layout.addWidget(histogram, 3, 0,  1, 2)
            # Set the maximum length
            # max_length = 1.5 * p1.boundingRect().width()
            # histogram.setMaximumWidth(max_length)
            # Create a horizontal spacer to center the histogram
            # spacer = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
            # # Add a Reset Zoom button
            # reset_zoom_button = QtWidgets.QPushButton("Reset Zoom")
            # reset_zoom_button.setObjectName("pushButtonResetZoom")
            # # reset_button.setMaximumWidth(100)
            # reset_zoom_button.clicked.connect(lambda: self.reset_zoom(p1,histogram))
            # # layout.addWidget(reset_zoom_button, 4, 0, 1, 1)
            # reset_plot_button = QtWidgets.QPushButton("Reset Plot")
            # reset_plot_button.setObjectName("pushButtonResetPlot")
            # # reset_button.setMaximumWidth(100)
            # reset_plot_button.clicked.connect(lambda: print(histogram.getHistogramRange()))
            # # layout.addWidget(reset_plot_button, 4, 1, 1, 1)

            # hbox = QHBoxLayout()
            # hbox.addStretch(1)
            # hbox.addWidget(reset_zoom_button)
            # hbox.addWidget(reset_plot_button)
            # vbox = QVBoxLayout()
            # vbox.setObjectName('buttons')
            # vbox.addStretch(1)
            # vbox.addLayout(hbox)

            # layout.addLayout(vbox, 4, 0, 1, 2)
        else:
            # multi view
            object_names_to_remove = ['histogram', 'pushButtonResetZoom', 'pushButtonResetPlot', 'buttons']
            # self.remove_widgets_from_layout(layout, object_names_to_remove)
            # plot = glw.getItem(0, 0)
            cbar = pg.ColorBarItem(orientation = 'h',colorMap = cm)
            cbar.setObjectName('colorbar')
            cbar.setImageItem(img, insert_in=p1)
            cbar.setLevels([array.min(), array.max()])

    # def setup_zoom_window(self, layout):
    #     # Create a GraphicsLayoutWidget for the zoom window
    #     self.zoomWindow = pg.GraphicsLayoutWidget(show=True)
    #     self.zoomPlot = self.zoomWindow.addPlot(title="Zoom")
    #     self.zoomImg = pg.ImageItem()
    #     self.zoomPlot.addItem(self.zoomImg)
    #     # You might need to adjust the layout position according to your UI design
    #     layout.addWidget(self.zoomWindow, 0, 3, 1, 2)  # Example placement
    #     # Setup initial properties of the zoom window
    #     self.zoomFactor = 5  # How much to zoom in
    #     self.zoomPlot.showGrid(x=True, y=True)
    #     self.zoomPlot.setAspectLocked(True)
    #     self.zoomPlot.invertY(True)

    #     # Optionally, set up a crosshair or marker in the zoom window
    #     self.zoomTarget = pg.TargetItem(symbol='+')
    #     self.zoomPlot.addItem(self.zoomTarget)
    #     self.zoomTarget.hide()  # Initially hidden

    def init_zoom_view(self):
        # Set the initial zoom level
        self.zoomLevel = 0.02  # Adjust as needed for initial zoom level
        # Create a ViewBox for the zoomed view
        self.zoomViewBox = pg.ViewBox(border={'color': 'w', 'width': 1})
        self.zoomImg = pg.ImageItem()
        self.zoomViewBox.addItem(self.zoomImg)
        self.zoomViewBox.setAspectLocked(True)
        self.zoomViewBox.invertY(True)
        # Add the zoom ViewBox as an item to the main plot (self.plot is your primary plot object)
        self.plot.addItem(self.zoomViewBox, ignoreBounds=True)

        # Configure initial size and position (you'll update this dynamically later)
        self.zoomViewBox.setFixedWidth(400)  # Width of the zoom box in pixels
        self.zoomViewBox.setFixedHeight(400)  # Height of the zoom box in pixels

        # Optionally, set up a crosshair or marker in the zoom window
        self.zoomTarget = pg.TargetItem(symbol='+', size = 5)
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

        # Update the position of the zoom view
        self.zoomViewBox.setGeometry(x_pos, y_pos, self.zoomViewBox.width(), self.zoomViewBox.height())

        # Calculate the region to zoom in on
        zoomRect = QtCore.QRectF(x - self.x_range * self.zoomLevel, y - self.y_range * self.zoomLevel, self.x_range * self.zoomLevel * 2, self.y_range * self.zoomLevel * 2)

        # Update the zoom view's displayed region
        # self.zoomViewBox.setRange(rect=zoomRect, padding=0)
        if self.toolButtonEdgeDetection.isChecked():
            self.zoomImg.setImage(image=self.edge_array)  # user edge_array too zoom with edge_det
        else:
            self.zoomImg.setImage(image=self.array)  # Make sure this uses the current image data

        self.zoomImg.setRect(0,0,self.x_range,self.y_range)
        self.zoomViewBox.setRange(zoomRect) # Set the zoom area in the image
        self.zoomImg.setColorMap(pg.colormap.get(self.cm, source = 'matplotlib'))
        self.zoomTarget.setPos(x, y)  # Update target position
        self.zoomTarget.show()
        self.zoomViewBox.setZValue(1e10)
        
    def add_edge_detection(self):
        """
        Add edge detection to the current laser map plot.
        :param algorithm: String specifying the edge detection algorithm ('sobel', 'canny', 'zero_cross')
        """
        if self.edge_img:
            # remove existing filters
            self.plot.removeItem(self.edge_img)  
        
        if self.toolButtonEdgeDetection.isChecked():
            algorithm = self.comboBoxEdgeDet.currentText().lower()
            if algorithm == 'sobel':
                # Apply Sobel edge detection
                sobelx = Sobel(self.array, CV_64F, 1, 0, ksize=5)
                sobely = Sobel(self.array, CV_64F, 0, 1, ksize=5)
                edge_detected_image = np.sqrt(sobelx**2 + sobely**2)
            elif algorithm == 'canny':
               
                # Normalize the array to [0, 1]
                normalized_array = (self.array - np.min(self.array)) / (np.max(self.array) - np.min(self.array))
                
                # Scale to [0, 255] and convert to uint8
                scaled_array = (normalized_array * 255).astype(np.uint8)
                
                # Apply Canny edge detection
                edge_detected_image = Canny(scaled_array, 100, 200)
            elif algorithm == 'zero cross':
                # Apply Zero Crossing edge detection (This is a placeholder as OpenCV does not have a direct function)
                # You might need to implement a custom function or find a library that supports Zero Crossing
                edge_detected_image = self.zero_crossing_laplacian(self.array)  # Placeholder, replace with actual Zero Crossing implementation
            else:
                raise ValueError("Unsupported algorithm. Choose 'sobel', 'canny', or 'zero cross'.")
        
            # Assuming you have a way to display this edge_detected_image on your plot.
            # This could be an update to an existing ImageItem or creating a new one if necessary.
            self.edge_array = edge_detected_image
            self.edge_img = pg.ImageItem(image=self.edge_array)
            #set aspect ratio of rectangle
            self.edge_img.setRect(0,0,self.x_range,self.y_range)
            # edge_img.setAs
            cm = pg.colormap.get(self.cm, source = 'matplotlib')
            self.edge_img.setColorMap(cm)
            
            self.plot.addItem(self.edge_img)  
        
    def zero_crossing_laplacian(self,array):
        """
        Apply Zero Crossing on the Laplacian of the image.
        :param array: 2D numpy array representing the image.
        :return: Edge-detected image using the Zero Crossing method.
        """
        # Normalize the array to [0, 1]
        normalized_array = (array - np.min(array)) / (np.max(array) - np.min(array))
        
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
    
    def add_noise_reduction(self):
        """
        Add noise reduction to the current laser map plot.

        Executes on change of comboBoxNRMethod and spinBoxSmoothingFactor. Updates map.
         
        Reduces noise by smoothing via one of several algorithms chosen from
        comboBoxNRMethod.  Options include:
        'none' - no smoothing
        'median' - simple filter that computes each pixel from the median of a window including
            surrounding points
        'bilateral' - an edge-preserving Gaussian weighted filter
        'wernier' - a Fourier domain filtering method that low pass filters to smooth the map
        'edge-preserving' - filter that does an excellent job of preserving edges when smoothing
        """
        algorithm = self.comboBoxNRMethod.currentText().lower()
        
        if self.noise_red_img:
            # Remove existing filters
            self.plot.removeItem(self.noise_red_img)
            # disable smoothing factor until chosen
            if algorithm != 'edge-preserving':
                self.spinBoxSmoothingFactor.setEnabled(False)
                self.labelSF.setEnabled(False)
        
    
        # Assuming self.array is the current image data
        if algorithm == 'none':
            return
        if algorithm == 'median':
            # Apply Median filter
            filtered_image = medianBlur(self.array.astype(np.float32), 5)  # Kernel size is 5
        elif algorithm == 'bilateral':
            # Apply Bilateral filter
            # Parameters are placeholders, you might need to adjust them based on your data
            filtered_image = bilateralFilter(self.array.astype(np.float32), 9, 75, 75)
        elif algorithm == 'wiener':
            # Apply Wiener filter
            # Wiener filter in scipy expects the image in double precision
            filtered_image = wiener(self.array.astype(np.float64), (5, 5))  # Myopic deconvolution, kernel size is (5, 5)
            filtered_image = filtered_image.astype(np.float32)  # Convert back to float32 to maintain consistency
        elif algorithm == 'edge-preserving':
            # Apply Edge-Preserving filter (RECURSIVE_FILTER or NORMCONV_FILTER)
            if not self.spinBoxSmoothingFactor.isEnabled():
                self.spinBoxSmoothingFactor.setEnabled(True)
                self.labelSF.setEnabled(True)
            # Normalize the array to [0, 1]
            normalized_array = (self.array - np.min(self.array)) / (np.max(self.array) - np.min(self.array))
            
            # Scale to [0, 255] and convert to uint8
            image = (normalized_array * 255).astype(np.uint8)
            filtered_image = edgePreservingFilter(image, flags=1, sigma_s=int(self.spinBoxSmoothingFactor.value()), sigma_r=0.2)
            
        else:
            raise ValueError("Unsupported algorithm. Choose 'median' or 'bilateral' or 'weiner or 'edge-preserving'.")
    
        # Update or create the image item for displaying the filtered image
        self.noise_red_array = filtered_image
        self.noise_red_img = pg.ImageItem(image=self.noise_red_array)
        
        # Set aspect ratio of rectangle
        self.noise_red_img.setRect(0, 0, self.x_range, self.y_range)
    
        # Optionally, set a color map
        cm = pg.colormap.get(self.cm, source='matplotlib')
        self.noise_red_img.setColorMap(cm)
        
        # Add the image item to the plot
        self.plot.addItem(self.noise_red_img)

    def reset_zoom(self, vb,histogram):
        vb.enableAutoRange()
        histogram.autoHistogramRange()

    def plot_pca(self):
        """Plot PCA"""
        pca_dict = {}

        df_filtered, isotopes = self.get_processed_data()

        # Preprocess the data
        scaler = StandardScaler()
        df_scaled = scaler.fit_transform(df_filtered)

        # Perform PCA
        pca = PCA(n_components=min(len(df_filtered.columns), len(df_filtered)))  # Adjust n_components as needed
        pca_results = pca.fit_transform(df_scaled)

        # Convert PCA results to DataFrame for easier plotting
        pca_dict['results'] = pd.DataFrame(pca_results, columns=[f'PC{i+1}' for i in range(pca.n_components_)])
        pca_dict['explained_variance_ratio'] = pca.explained_variance_ratio_
        pca_dict['components_'] = pca.components_


        # Determine which PCA plot to create based on the combobox selection
        pca_plot_type = self.comboBoxPCAPlotType.currentText()

        plot_name = pca_plot_type
        sample_id = self.sample_id
        plot_type = 'pca'  # Assuming all PCA plots fall under a common plot type

        plot_exist = plot_name in self.plot_widget_dict[plot_type][sample_id]
        duplicate = plot_exist and len(self.plot_widget_dict[plot_type][sample_id][plot_name]['view']) == 1 and self.plot_widget_dict[plot_type][sample_id][plot_name]['view'][0] != self.canvasWindow.currentIndex()

        if plot_exist and not duplicate:
            widgetPCA = self.plot_widget_dict[plot_type][sample_id][plot_name]['widget'][0]
            figure_canvas = widgetPCA.findChild(FigureCanvas)
            figure_canvas.figure.clear()
            ax = figure_canvas.figure.subplots()
            self.update_pca_plot(pca_dict, pca_plot_type, ax)
            figure_canvas.draw()
        else:
            figure = Figure()
            ax = figure.add_subplot(111)
            self.update_pca_plot(pca_dict, pca_plot_type, ax)
            widgetPCA = QtWidgets.QWidget()
            widgetPCA.setLayout(QtWidgets.QVBoxLayout())
            figure_canvas = FigureCanvas(figure)
            toolbar = NavigationToolbar(figure_canvas, widgetPCA)
            #widgetPCA.layout().addWidget(toolbar)
            widgetPCA.layout().addWidget(figure_canvas)
            view = self.canvasWindow.currentIndex()

            plot_information = {
                'plot_name': plot_name,
                'sample_id': self.sample_id,
                'plot_type': plot_type,

            }

            if duplicate:
                self.plot_widget_dict[plot_type][sample_id][plot_name]['widget'].append(widgetPCA)
                self.plot_widget_dict[plot_type][sample_id][plot_name]['view'].append(view)
            else:
                self.plot_widget_dict[plot_type][sample_id][plot_name] = {'widget': [widgetPCA], 'info': plot_information, 'view': [view]}

            # Additional steps to add the PCA widget to the appropriate container in the UI
            self.add_plot(plot_information)
            self.update_tree(plot_information['plot_name'], data = plot_information, tree = 'PCA')

    def update_pca_plot(self, pca_dict, pca_plot_type, ax):

        isotopes = self.isotopes_df[self.isotopes_df['sample_id']==self.sample_id]['isotopes']
        n_components = range(1, len(pca_dict['explained_variance_ratio'])+1)
        match pca_plot_type:
            case 'Variance':
                s = self.scatter_style[self.pca_tab_id]

                # pca_dict contains variance ratios for the principal components
                variances = pca_dict['explained_variance_ratio']
                cumulative_variances = variances.cumsum()  # Calculate cumulative explained variance

                # Plotting the explained variance
                ax.plot(n_components, variances, linestyle='-', linewidth=s['LineWidth'],
                    marker=self.markerdict[s['Marker']], markeredgecolor=s['Color'], markerfacecolor='none', markersize=s['Size'],
                    color=s['Color'], label='Explained Variance')

                # Plotting the cumulative explained variance
                ax.plot(n_components, cumulative_variances, linestyle='-', linewidth=s['LineWidth'],
                    marker=self.markerdict[s['Marker']], markersize=s['Size'],
                    color=s['Color'], label='Cumulative Variance')

                # Adding labels, title, and legend
                xlbl = 'Principal Component'
                ylbl = 'Variance Ratio'
                ttxt = 'PCA Variance Explained'

                ax.legend()

                # Adjust the y-axis limit to make sure the plot includes all markers and lines
                ax.set_ylim([0, 1.0])  # Assuming variance ratios are between 0 and 1
            case 'Vectors':
                s = self.heatmap_style[self.pca_tab_id]
                # pca_dict contains 'components_' from PCA analysis with columns for each variable
                components = pca_dict['components_']  # No need to transpose for heatmap representation

                # Number of components and variables
                n_components = components.shape[0]
                n_variables = components.shape[1]

                cmap = plt.get_cmap(self.cm)
                cax = ax.imshow(components, cmap=plt.get_cmap(s['Colormap']), aspect=1.0)
                fig = ax.get_figure()
                # Adding a colorbar at the bottom of the plot
                cbar = fig.colorbar(cax, orientation='vertical', pad=0.2)
                cbar.set_label('PCA Score')

                xlbl = 'Principal Components'
                ylbl = 'Variables'
                ttxt = 'PCA Components Heatmap'

                # Optional: Rotate x-axis labels for better readability
                # plt.xticks(rotation=45)
            case 'PC X vs. PC Y':
                pc_x = int(self.spinBoxPCX.value())
                pc_y = int(self.spinBoxPCY.value())
                pca_df = pca_dict['results']
                # Assuming pca_df contains scores for the principal components
                ax.scatter(pca_df[f'PC{pc_x}'], pca_df[f'PC{pc_y}'])
                ax.set_xlabel(f'PC{pc_x}')
                ax.set_ylabel(f'PC{pc_y}')
                ax.set_title(f'PCA Plot: PC{pc_x} vs PC{pc_y}')
            case 'PC X Score Map':
                pc_x = int(self.spinBoxPCX.value())
                pca_df = pca_dict['results']
                # Assuming pca_df contains scores for the principal components
                ax.bar(range(len(pca_df)), pca_df[f'PC{pc_x}'])
                ax.set_xlabel('Sample Index')
                ax.set_ylabel(f'PC{pc_x} Score')
                ax.set_title(f'PCA Score Map for PC{pc_x}')
            case _:
                print(f"Unknown PCA plot type: {pca_plot_type}")

        # labels
        font = {'size':self.general_style['FontSize']}
        ax.set_xlabel(xlbl, fontdict=font)
        ax.set_ylabel(ylbl, fontdict=font)
        ax.set_title(ttxt, fontdict=font)

        match pca_plot_type:
            case 'Variance' | 'PC X vs. PC Y':
                # tick marks
                ax.tick_params(direction=self.general_style['TickDir'],
                    labelsize=self.general_style['FontSize'],
                    labelbottom=True, labeltop=False, labelleft=True, labelright=False,
                    bottom=True, top=True, left=True, right=True)

                ax.set_xticks(range(1, len(n_components) + 1, 5))
                ax.set_xticks(n_components, minor=True)

                # aspect ratio
                ax.set_box_aspect(s['AspectRatio'])
            case 'Vectors':
                ax.tick_params(axis='x', direction=self.general_style['TickDir'],
                                labelsize=self.general_style['FontSize'],
                                labelbottom=True, labeltop=False,
                                bottom=True, top=True)

                ax.tick_params(axis='y', length=0, direction=self.general_style['TickDir'],
                                labelsize=8,
                                labelleft=True, labelright=False,
                                left=True, right=True)

                ax.set_xticks(range(1, n_components+1, 5))
                ax.set_xticks(range(1, n_components+1, 1), minor=True)

                #ax.set_yticks(n_components, labels=[f'Var{i+1}' for i in range(len(n_components))])
                ax.set_yticks(range(1, n_variables+1,1), minor=False)
                ax.set_yticklabels(isotopes)
            case 'PC X Score Map':
                ax.tick_params(direction='none', labelbottom=False, labeltop=False, labelright=False, labelleft=False)

    def plot_correlation(self, plot=False):
        correlation_dict = {}

        df_filtered, isotopes = self.get_processed_data()

        # Calculate the correlation matrix
        correlation_matrix = df_filtered.corr()

        # Store the correlation matrix for plotting
        correlation_dict['correlation_matrix'] = correlation_matrix

        # Determine which correlation plot to create based on the combobox selection (assuming you have a combobox for different types of correlation plots, if not just set a default plot type)
        correlation_plot_type = 'Heatmap'

        plot_name = correlation_plot_type
        sample_id = self.sample_id
        plot_type = 'correlation'  # Assuming all correlation plots fall under a common plot type

        plot_exist = plot_name in self.plot_widget_dict[plot_type][sample_id]
        duplicate = plot_exist and len(self.plot_widget_dict[plot_type][sample_id][plot_name]['view']) == 1 and self.plot_widget_dict[plot_type][sample_id][plot_name]['view'][0] != self.canvasWindow.currentIndex()

        if plot_exist and not duplicate:
            widgetCorrelation = self.plot_widget_dict[plot_type][sample_id][plot_name]['widget'][0]
            figure_canvas = widgetCorrelation.findChild(FigureCanvas)
            figure_canvas.figure.clear()
            ax = figure_canvas.figure.subplots()
            self.update_correlation_plot(correlation_dict, ax)
            figure_canvas.draw()
        else:
            figure = Figure()
            ax = figure.add_subplot(111)
            self.update_correlation_plot(correlation_dict, ax)
            widgetCorrelation = QtWidgets.QWidget()
            widgetCorrelation.setLayout(QtWidgets.QVBoxLayout())
            figure_canvas = FigureCanvas(figure)
            toolbar = NavigationToolbar(figure_canvas, widgetCorrelation)
            # widgetCorrelation.layout().addWidget(toolbar)
            widgetCorrelation.layout().addWidget(figure_canvas)
            view = self.canvasWindow.currentIndex()

            plot_information = {
                'plot_name': plot_name,
                'sample_id': self.sample_id,
                'plot_type': plot_type,
            }

            if duplicate:
                self.plot_widget_dict[plot_type][sample_id][plot_name]['widget'].append(widgetCorrelation)
                self.plot_widget_dict[plot_type][sample_id][plot_name]['view'].append(view)
            else:
                self.plot_widget_dict[plot_type][sample_id][plot_name] = {'widget': [widgetCorrelation], 'info': plot_information, 'view': [view]}

            # Additional steps to add the Correlation widget to the appropriate container in the UI
            if plot:
                self.add_plot(plot_information) #do not plot correlation when directory changes
            self.update_tree(plot_information['plot_name'], data=plot_information, tree='Correlation')

    def update_correlation_plot(self, correlation_dict, ax):
        if self.comboBoxCorrelationMethod.currentText().lower == 'none':
            return

        s = self.heatmap_style[self.sample_tab_id]
        cmap = plt.get_cmap(s['Colormap'])
        correlation_matrix = correlation_dict['correlation_matrix']
        cax = ax.imshow(correlation_matrix, cmap=plt.get_cmap(s['Colormap']))

        fig = ax.get_figure()
        # Add colorbar to the plot
        cbar = fig.colorbar(cax, ax=ax)
        cbar.set_label(['Corr. coeff. ('+self.comboBoxCorrelationMethod.currentText(),')'])

        # Set tick labels
        ticks = np.arange(len(correlation_matrix.columns))
        ax.tick_params(length=0, labelsize=8,
                        labelbottom=False, labeltop=True, labelleft=False, labelright=True,
                        bottom=False, top=True, left=False, right=True)

        ax.set_yticks(ticks, minor=False)
        ax.set_xticks(ticks, minor=False)

        ax.set_xticklabels(correlation_matrix.columns, ha='left')
        ax.set_yticklabels(correlation_matrix.columns, rotation=90, ha='left')

        ax.set_title('Correlation Matrix')

    def plot_histogram(self, current_plot_df, plot_information, bin_width):
        """Displays histogram for current selected isotope.
        
        Parameter
        ---------
        
        current_plot_df: pandas.DataFrame
            current active plot
        plot_information: dict
            dictionary with information about plot widget
        bin_width: double
            width of histogram bins
        """
        mask = self.filter_mask & self.polygon_mask & current_plot_df['array'].notna()


        plot_name = plot_information['plot_name']
        sample_id = plot_information['sample_id']
        plot_type = plot_information['plot_type']
        array = current_plot_df['array'][mask].values
        edges = np.arange(array.min(), array.max() + bin_width, bin_width)

        plot_exist = plot_name in self.plot_widget_dict[plot_type][sample_id]
        duplicate = plot_exist and len(self.plot_widget_dict[plot_type][sample_id][plot_name]['view']) == 1 and self.plot_widget_dict[plot_type][sample_id][plot_name]['view'][0] != self.canvasWindow.currentIndex()


        if plot_exist and not duplicate:
            widgetHistogram = self.plot_widget_dict[plot_type][sample_id][plot_name]['widget'][0]
            figure_canvas = widgetHistogram.findChild(FigureCanvas)
            figure_canvas.figure.clear()
            ax = figure_canvas.figure.subplots()
            self.update_histogram(array, edges, ax)
            figure_canvas.draw()
        else:
            figure = Figure()
            ax = figure.add_subplot(111)
            self.update_histogram(array, edges, ax)
            widgetHistogram = QtWidgets.QWidget()
            widgetHistogram.setLayout(QtWidgets.QVBoxLayout())
            figure_canvas = FigureCanvas(figure)
            toolbar = NavigationToolbar(figure_canvas, widgetHistogram)  # Create the toolbar for the canvas
            # widgetHistogram.layout().addWidget(toolbar)  # Add the toolbar to the widget
            widgetHistogram.layout().addWidget(figure_canvas)
            view = self.canvasWindow.currentIndex()

            if duplicate:
                self.plot_widget_dict[plot_type][sample_id][plot_name]['widget'].append(widgetHistogram)
                self.plot_widget_dict[plot_type][sample_id][plot_name]['view'].append(view)
            else:
                self.plot_widget_dict[plot_type][sample_id][plot_name] = {'widget': [widgetHistogram], 'info': plot_information, 'view': [view]}


            # self.canvasWindow.setCurrentIndex(view)
            # Assuming you have a method to add the widget to the tab
            # self.add_histogram_tab(widgetHistogram, plot_name)

    def update_histogram(self, array, edges, ax):
        # Clear previous histogram
        ax.clear()
        # Check if the algorithm is in the current group and if results are available
        if 'algorithm' in self.current_group and self.current_group['algorithm'] in self.cluster_results:
            # Get the cluster labels for the data
            cluster_labels = self.cluster_results[self.current_group['algorithm']]
            clusters = cluster_labels.dropna().unique()


            # Plot histogram for all clusters
            for i in clusters:
                cluster_data = array[cluster_labels == i]
                # Create RGBA color with transparency by directly indexing the colormap
                # color = cmap(i)[:-1]  # Create a new RGBA tuple with alpha value
                color = self.goup_cmap[i][:-1] + (0.6,)
                ax.hist(cluster_data, bins=edges, color=color,edgecolor='black', linewidth=1.5, label=f'Cluster {i}', alpha=0.6)
        else:
            # Regular histogram
            ax.hist(array, bins=edges, color='blue', edgecolor='black', linewidth=1.5, label='Data')
        # Add a legend
        ax.legend()

        # Set labels
        ax.set_xlabel('Value')
        ax.set_ylabel('Frequency')

    def tern2xy(self, a, b, c):
        w = 0.5
        h = 0.5 / np.tan(np.pi/6)
        s = a + b + c
        a = a / s
        b = b / s
        c = c / s
        y = a * h
        x = (1 - b) * h / np.cos(np.pi/6) - y * np.tan(np.pi/6) - w
        return x, y

    # extracts data for scatter plot
    def get_scatter_values(self):
        """Creates a dictionary of values for plotting

        :return: four return variables, x, y, z, and c, each as a dict with locations for bi- and
            ternary plots.  Each contain a 'field', 'type', 'label', and 'array'.  x, y and z
            contain coordinates and c contains the colors
        :rtype: dict
        """
        value_dict = {
            'x': {'field': None, 'type': None, 'label': None, 'array': None},
            'y': {'field': None, 'type': None, 'label': None, 'array': None},
            'z': {'field': None, 'type': None, 'label': None, 'array': None},
            'c': {'field': None, 'type': None, 'label': None, 'array': None}
        }
        value_dict['x']['field'] = self.comboBoxScatterIsotopeX.currentText()
        value_dict['x']['type'] = self.comboBoxScatterSelectX.currentText().lower()
        value_dict['y']['field'] = self.comboBoxScatterIsotopeY.currentText()
        value_dict['y']['type'] = self.comboBoxScatterSelectY.currentText().lower()
        value_dict['z']['field'] = self.comboBoxScatterIsotopeZ.currentText()
        value_dict['z']['type'] = self.comboBoxScatterSelectZ.currentText().lower()
        value_dict['c']['field'] = self.comboBoxColorField.currentText()
        value_dict['c']['type'] = self.comboBoxColorByField.currentText().lower()

        for k, v in value_dict.items():
            if v['type'] == 'isotope' and v['field']:
                df = self.get_map_data(self.sample_id, v['field'], analysis_type=v['type'], plot=False)
                v['label'] = v['field'] + ' (' + self.general_style['Concentration'] + ')'
            elif v['type'] == 'ratio' and '/' in v['field']:
                isotope_1, isotope_2 = v['field'].split('/')
                df = self.get_map_data(self.sample_id, isotope_1, isotope_2, analysis_type=v['type'], plot=False)
                v['label'] = v['field']
            elif v['type'] == 'pca':
                #df = self.get_map_data(self.sample_id, v['field'], plot_type=None, plot=False)
                v['label'] = v['field']
            elif v['type'] == 'cluster':
                #df = self.get_map_data(self.sample_id, v['field'], plot_type=None, plot=False)
                v['label'] = v['field']
            elif v['type'] == 'cluster score':
                #df = self.get_map_data(self.sample_id, v['field'], plot_type=None, plot=False)
                v['label'] = v['field']
            elif v['type'] == 'special':
                return
            else:
                df = pd.DataFrame({'array': []})  # Or however you want to handle this case

            value_dict[k]['array'] = df['array'][self.filter_mask].values if not df.empty else []

        return value_dict['x'], value_dict['y'], value_dict['z'], value_dict['c']

    # updates scatter styles when ColorByField comboBox is changed
    def toggle_color_by_field(self, tab_id):
        if tab_id == self.scatter_tab_id or tab_id == self.pca_tab_id or tab_id == self.profile_tab_id:
            if self.comboBoxColorByField.currentText().lower() == 'none':
                # turn off ColorByField and enable Color
                self.labelMarkerColor.setEnabled(True)
                self.toolButtonMarkerColor.setEnabled(True)
                self.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % self.scatter_style[tab_id]['Color'])

                self.labelColorField.setEnabled(False)
                self.comboBoxColorField.setEnabled(False)

                self.labelFieldColormap.setEnabled(False)
                self.comboBoxFieldColormap.setEnabled(False)

                self.scatter_style[tab_id]['ColorByField'] = self.comboBoxColorByField.currentText()
                self.scatter_style[tab_id]['Field'] = self.comboBoxColorField.currentText()
                self.plot_scatter(save=False)
            else:
                # turn off single color and enable ColorByField
                self.labelColorField.setEnabled(True)
                self.comboBoxColorField.setEnabled(True)

                # fill ColorField comboBox
                fields = self.get_field_list(self.comboBoxColorByField.currentText().lower())
                self.comboBoxColorField.clear()
                if not (len(fields) == 0):
                    self.comboBoxColorField.addItems(fields)

                self.labelFieldColormap.setEnabled(True)
                self.comboBoxFieldColormap.setEnabled(True)

                self.labelMarkerColor.setEnabled(False)
                self.toolButtonMarkerColor.setEnabled(False)
                self.toolButtonMarkerColor.setStyleSheet("background-color: none;")

    # toggle heatmap resolution spinBox when the scatter type comboBox is changed
    def toggle_scatter_style_tab(self, tab_id):
        """Updates and toggles widgets in scatter style tab

        :param tab_id: tab_ind should be set by toolBox.currentIndex(), which determines the active
            widgets
        :type tab_id: int
        """
        if tab_id == self.sample_tab_id:
            self.comboBoxScatterType.setCurrentText('Heatmap')
        elif tab_id == self.profile_tab_id:
            self.comboBoxScatterType.setCurrentText('Scatter')

        match self.comboBoxScatterType.currentText().lower():
            case 'scatter':
                self.current_scatter_type[tab_id] = 'Scatter'
                # turn off heatmap related properties
                self.labelHeatmapResolution.setEnabled(False)
                self.spinBoxHeatmapResolution.setEnabled(False)

                # turn on Scatter related properties
                self.labelMarker.setEnabled(True)
                self.comboBoxMarker.setEnabled(True)
                self.labelMarkerSize.setEnabled(True)
                self.doubleSpinBoxMarkerSize.setEnabled(True)
                self.labelLineWidth.setEnabled(True)
                self.comboBoxLineWidth.setEnabled(True)
                self.labelMarkerAlpha.setEnabled(True)
                self.horizontalSliderMarkerAlpha.setEnabled(True)
                self.labelColorByField.setEnabled(True)
                self.comboBoxColorByField.setEnabled(True)
                #set properties
                if tab_id == self.scatter_tab_id or tab_id == self.pca_tab_id or tab_id == self.profile_tab_id:
                    val = self.comboBoxMarker.allItems()
                    self.comboBoxMarker.setCurrentIndex(val.index(self.scatter_style[tab_id]['Marker']))
                    self.doubleSpinBoxMarkerSize.setValue(self.scatter_style[tab_id]['Size'])
                    val = self.comboBoxLineWidth.allItems()
                    self.comboBoxLineWidth.setCurrentIndex(val.index(str(self.scatter_style[tab_id]['LineWidth'])))
                    val = self.comboBoxColorByField.allItems()
                    self.comboBoxColorByField.setCurrentIndex(val.index(self.scatter_style[tab_id]['ColorByField']))
                    self.horizontalSliderMarkerAlpha.setValue(int((self.scatter_style[tab_id]['Alpha'])))
                    self.labelMarkerAlpha.setText(str(self.horizontalSliderMarkerAlpha.value()))
                    self.labelMarkerAlpha.setText(str(self.scatter_style[tab_id]['Alpha']))

                # ColorByField
                if self.comboBoxColorByField.currentText().lower() == 'none':
                    # turn off ColorByField related properties
                    self.labelColorField.setEnabled(False)
                    self.comboBoxColorField.setEnabled(False)
                    self.labelFieldColormap.setEnabled(False)
                    self.comboBoxFieldColormap.setEnabled(False)

                    # turn on ColorByField=None related properties
                    self.labelMarkerColor.setEnabled(True)
                    self.toolButtonMarkerColor.setEnabled(True)
                    if tab_id == self.scatter_tab_id or tab_id == self.pca_tab_id or tab_id == self.profile_tab_id:
                        self.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % self.scatter_style[tab_id]['Color'])
                else:
                    # turn off ColorByField related properties
                    self.labelColorField.setEnabled(True)
                    self.comboBoxColorField.setEnabled(True)
                    self.labelFieldColormap.setEnabled(True)
                    self.comboBoxFieldColormap.setEnabled(True)
                    if tab_id == self.sample_tab_id or self.scatter_tab_id or tab_id == self.pca_tab_id or tab_id == self.profile_tab_id:
                        val = self.comboBoxFieldColormap.allItems()
                        self.comboBoxFieldColormap.setCurrentIndex(val.index(self.scatter_style[tab_id]['Colormap']))

                    # turn off ColorByField=None related fields
                    self.labelMarkerColor.setEnabled(False)
                    self.toolButtonMarkerColor.setEnabled(False)

            case 'heatmap':
                self.current_scatter_type[tab_id] = 'Heatmap'
                # turn on heatmap related fields
                self.labelHeatmapResolution.setEnabled(True)
                self.spinBoxHeatmapResolution.setEnabled(True)
                self.labelFieldColormap.setEnabled(True)
                self.comboBoxFieldColormap.setEnabled(True)
                if tab_id == self.sample_tab_id or tab_id == self.scatter_tab_id or tab_id == self.pca_tab_id or tab_id == self.profile_tab_id:
                    val = self.comboBoxFieldColormap.allItems()
                    self.comboBoxFieldColormap.setCurrentIndex(val.index(self.heatmap_style[tab_id]['Colormap']))

                # turn off Marker related fields
                self.labelMarker.setEnabled(False)
                self.comboBoxMarker.setEnabled(False)
                self.labelMarkerSize.setEnabled(False)
                self.doubleSpinBoxMarkerSize.setEnabled(False)
                self.labelLineWidth.setEnabled(False)
                self.comboBoxLineWidth.setEnabled(False)
                self.labelMarkerColor.setEnabled(False)
                self.toolButtonMarkerColor.setEnabled(False)
                self.toolButtonMarkerColor.setStyleSheet("background-color: none;")
                self.labelColorByField.setEnabled(False)
                self.comboBoxColorByField.setEnabled(False)
                self.labelColorField.setEnabled(False)
                self.comboBoxColorField.setEnabled(False)
                self.labelTransparency.setEnabled(False)
                self.labelMarkerAlpha.setEnabled(False)
                self.horizontalSliderMarkerAlpha.setEnabled(False)

    def get_general_style(self):
        """Updates dictionary with general style properties"""
        self.general_style = {'Concentration': self.lineEditAnalyteUnits.text(),
                                'Distance': self.lineEditScaleUnits.text(),
                                'Temperature': self.comboBoxTUnits.currentText(),
                                'Pressure': self.comboBoxPUnits.currentText(),
                                'Date': self.comboBoxDateUnits.currentText(),
                                'FontSize': self.doubleSpinBoxFontSize.value(),
                                'TickDir': self.comboBoxTickDirection.currentText()
                                }

    def set_general_style(self):
        """Sets style properties in Styling>General tab"""
        self.lineEditAnalyteUnits.setText(self.general_style['Concentration'])
        self.lineEditScaleUnits.setText(self.general_style['Distance'])
        self.comboBoxTUnits.setCurrentText(self.general_style['Temperature'])
        self.comboBoxPUnits.setCurrentText(self.general_style['Pressure'])
        self.comboBoxDateUnits.setCurrentText(self.general_style['Date'])
        self.doubleSpinBoxFontSize.setValue(self.general_style['FontSize'])
        self.comboBoxTickDirection.setCurrentText(self.general_style['TickDir'])

    def get_map_style(self, tab_id):
        """Updates dictionary with map style properties

        Updates self.map_style with widget status under Styling > Maps

        :param tab_ind: tab_ind should be set by toolBox.currentIndex(), which determines styles to
            update
        :type tab_ind: int
        """
        match tab_id:
            case self.sample_tab_id | self.pca_tab_id | self.cluster_tab_id:
                self.map_style[tab_id] = {'Colormap': self.comboBoxMapColormap.currentText(),
                                    'ColorbarDirection': self.comboBoxColorbarDirection.currentText(),
                                    'ScaleLocation': self.comboBoxScaleLocation.currentText(),
                                    'ScaleDirection': self.comboBoxScaleDirection.currentText(),
                                    'OverlayColor': self.get_hex_color(self.toolButtonOverlayColor.palette().button().color())
                                    }
            case self.scatter_tab_id:
                self.map_style[tab_id] = {'Colormap': self.comboBoxTernaryColormap.currentText(),
                                    'ColorbarDirection': self.comboBoxColorbarDirection.currentText(),
                                    'ScaleLocation': self.comboBoxScaleLocation.currentText(),
                                    'ScaleDirection': self.comboBoxScaleDirection.currentText(),
                                    'OverlayColor': self.get_hex_color(self.toolButtonOverlayColor.palette().button().color())
                                    }
            case _:
                self.map_style[self.sample_tab_id] = {'Colormap': self.comboBoxMapColormap.currentText(),
                                    'ColorbarDirection': self.comboBoxColorbarDirection.currentText(),
                                    'ScaleLocation': self.comboBoxScaleLocation.currentText(),
                                    'ScaleDirection': self.comboBoxScaleDirection.currentText(),
                                    'OverlayColor': self.get_hex_color(self.toolButtonOverlayColor.palette().button().color())
                                    }

    def set_map_style(self):
        """Sets style properties in Styling>Maps tab"""
        match self.toolBox.currentIndex():
            case self.pca_tab_id | self.cluster_tab_id:
                tab_id = self.toolBox.currentIndex()
                self.comboBoxMapColormap.setCurrentText(self.map_style[tab_id]['Colormap'])
            case self.scatter_tab_id:
                tab_id = self.scatter_tab_id
                self.comboBoxTernaryColormap.setCurrentText(self.map_style[tab_id]['Colormap'])
                self.TernaryColormapChanged()
            case _:
                tab_id = self.sample_tab_id
                self.comboBoxMapColormap.setCurrentText(self.map_style[tab_id]['Colormap'])

        self.comboBoxColorbarDirection.setCurrentText(self.map_style[tab_id]['ColorbarDirection'])
        self.comboBoxScaleLocation.setCurrentText(self.map_style[tab_id]['ScaleLocation'])
        self.comboBoxScaleDirection.setCurrentText(self.map_style[tab_id]['ScaleDirection'])
        self.toolButtonOverlayColor.setStyleSheet("background-color: %s;" % self.map_style[tab_id]['OverlayColor'])

    def set_scatter_style(self):
        """Sets style properties in Styling>Scatter and Heatmap tab"""
        tab_id = self.toolBox.currentIndex()
        if tab_id == self.sample_tab_id or tab_id == self.scatter_tab_id or tab_id == self.pca_tab_id or tab_id == self.profile_tab_id:
            # scatter
            self.comboBoxMarker.setCurrentText(self.scatter_style[tab_id]['Marker'])
            self.doubleSpinBoxMarkerSize.setValue(self.scatter_style[tab_id]['Size'])
            self.comboBoxLineWidth.setCurrentText(str(self.scatter_style[tab_id]['LineWidth']))
            self.toolButtonMarkerColor.setStyleSheet("background-color: %s;" % self.scatter_style[tab_id]['Color'])
            self.comboBoxColorByField.setCurrentText(self.scatter_style[tab_id]['ColorByField'])
            self.comboBoxColorField.setCurrentText(self.scatter_style[tab_id]['Field'])
            self.comboBoxFieldColormap.setCurrentText(self.scatter_style[tab_id]['Colormap'])
            self.horizontalSliderMarkerAlpha.setValue(int(self.scatter_style[tab_id]['Alpha']))
            self.labelMarkerAlpha.setText(str(self.horizontalSliderMarkerAlpha.value()))
            self.lineEditAspectRatio.setText(str(self.scatter_style[tab_id]['AspectRatio']))

            # heatmap
            self.spinBoxHeatmapResolution.setValue(self.heatmap_style[tab_id]['Resolution'])
            self.comboBoxFieldColormap.setCurrentText(self.heatmap_style[tab_id]['Colormap'])

    def get_scatter_style(self, tab_id):
        """Updates dictionaries with scatter and heatmap style properties

        :param tab_ind: tab_ind should be set by toolBox.currentIndex(), which determines styles to
            update
        :type tab_ind: int
        """
        if tab_id == self.sample_tab_id or tab_id == self.scatter_tab_id or tab_id == self.pca_tab_id or tab_id == self.profile_tab_id:
            match self.comboBoxScatterType.currentText().lower():
                case 'scatter':
                    self.scatter_style[tab_id] = {
                        'Marker': self.comboBoxMarker.currentText(),
                        'Size': self.doubleSpinBoxMarkerSize.value(),
                        'LineWidth': float(self.comboBoxLineWidth.currentText()),
                        'Color': self.get_hex_color(self.toolButtonMarkerColor.palette().button().color()),
                        'ColorByField': self.comboBoxColorByField.currentText(),
                        'Field': self.comboBoxColorField.currentText(),
                        'Colormap': self.comboBoxFieldColormap.currentText(),
                        'Alpha': float(self.horizontalSliderMarkerAlpha.value()),
                        'AspectRatio': float(self.lineEditAspectRatio.text())
                        }
                case 'heatmap':
                    self.heatmap_style[tab_id] = {'Resolution': self.spinBoxHeatmapResolution.value(),
                                                    'Colormap': self.comboBoxFieldColormap.currentText(),
                                                    'AspectRatio': float(self.lineEditAspectRatio.text())}

    def toggle_scale_direction(self):
        if self.map_style['ScaleDirection'] == 'none':
            self.labelScaleLocation.setEnabled(False)
            self.comboBoxScaleLocation.setEnabled(False)
        else:
            self.labelScaleLocation.setEnabled(True)
            self.comboBoxScaleLocation.setEnabled(True)



    #def plot_scatter(self, update=False, values = None, plot_type= None, fig= None, ternary_plot= None):
    #    self.get_general_style()
    #    self.get_scatter_style(self.toolBox.currentIndex())
    #    if not update:
    #        x, y, z, c = self.get_scatter_values() #get scatter values from elements chosen
    #        plot_type =  self.comboBoxScatterType.currentText().lower()
    #    else:
    #        # get saved scatter values to update plot
    #        x, y, z, c  = values

    #    # df = df.dropna(axis = 0).astype('int64')

    #    # x['array'], y['array'], z['array'] = df.iloc[:, 0].values, df.iloc[:, 1].values, df.iloc[:, 2].values


    #    cmap = matplotlib.colormaps.get_cmap(self.cm)

    #    if len(z['array'])>0 and len(c['array'])>0:  # 3d scatter plot with color

    #        labels = [x['elements'], y['elements'], z['elements']]

    #        if not update:
    #            ternary_plot = ternary(labels,plot_type,mul_axis=True )
    #            fig = ternary_plot.fig



    #        if plot_type =='scatter':
    #            _, cb = ternary_plot.ternscatter(x['array'], y['array'], z['array'], categories=  c['array'], cmap=cmap, orientation = self.comboBoxColorbarDirection.currentText().lower())

    #        else:
    #            ternary_plot.ternhex(x['array'], y['array'], z['array'], val= c['array'],n=int(self.spinBoxHeatmapResolution.value()), cmap = cmap, orientation = self.comboBoxColorbarDirection.currentText().lower())


    #        select_scatter = f"{x['elements']}_{y['elements']}_{z['elements']}_{c['elements']}_{plot_type}"
    #    elif len(z['array'])>0:  # Ternary plot

    #        labels = [x['elements'], y['elements'], z['elements']]
    #        if not update:
    #            ternary_plot = ternary(labels,plot_type)
    #            fig = ternary_plot.fig
    #        if plot_type =='scatter':
    #            if self.current_group['algorithm'] in self.cluster_results:
    #                cluster_labels = self.cluster_results[self.current_group['algorithm']]
    #                ternary_plot.ternscatter(x['array'], y['array'], z['array'], categories=cluster_labels, cmap=self.group_cmap, labels = True, orientation = self.comboBoxColorbarDirection.currentText().lower())
    #            else:
    #                ternary_plot.ternscatter(x['array'], y['array'], z['array'],cmap= cmap)
    #        else:
    #            ternary_plot.ternhex(x['array'], y['array'], z['array'],n=int(self.spinBoxHeatmapResolution.value()), color_map = cmap, orientation = self.comboBoxColorbarDirection.currentText().lower())
    #        fig.subplots_adjust(left=0.05, right=1)
    #        select_scatter = f"{x['elements']}_{y['elements']}_{z['elements']}_{plot_type}"
    #        # fig.tight_layout()
    #    else:  # 2d scatter plot
    #        if not update:
    #            fig = Figure()
    #        ax = fig.add_subplot(111)
    #        ax.scatter(x['array'], y['array'], alpha=0.5)
    #        select_scatter = f"{x['elements']}_{y['elements']}_{plot_type}"

    #        # add labels
    #        xlbl = self.comboBoxScatterIsotopeX.currentText()
    #        ylbl = self.comboBoxScatterIsotopeY.currentText()
    #        match self.comboBoxScatterSelectX.currentText().lower():
    #            case 'isotope':
    #                xlbl += ' ('+self.lineEditConcentrationUnits.text()+')'
    #        match self.comboBoxScatterSelectX.currentText().lower():
    #            case 'isotope':
    #                ylbl += ' ('+self.lineEditConcentrationUnits.text()+')'
    #        ax.set_xlabel(xlbl)
    #        ax.set_ylabel(ylbl)
    #        ax.tick_params(labelbottom=True, labeltop=False, labelleft=True, labelright=False, bottom=True, top=True, left=True, right=True)

    #        ax.set_box_aspect(float(self.lineEditAspectRatio.text()))

    #    if not update:
    #        plot_information = {
    #            'plot_name': select_scatter,
    #            'sample_id': self.sample_id,
    #            'plot_type': plot_type,
    #            'values': (x, y, c),
    #            'fig': fig,
    #            'ternary_plot': ternary_plot,
    #            'colorbar': cb
    #        }

    #        # Create a Matplotlib figure and axis

    #        widgetScatter = QtWidgets.QWidget()
    #        layout = QtWidgets.QVBoxLayout()
    #        widgetScatter.setLayout(layout)
    #        # scatter_plot = pg.PlotWidget(title=select_scatter)
    #        scatter_plot = FigureCanvas(fig)
    #        view = self.canvasWindow.currentIndex()
    #        # Add the plot widget to your layout
    #        layout.insertWidget(0,scatter_plot)
    #        toolbar = NavigationToolbar(scatter_plot)  # Create the toolbar for the canvas
    #        # widgetScatter.layout().addWidget(toolbar)

    #        self.plot_widget_dict['scatter'][self.sample_id][select_scatter] = {'widget':[widgetScatter],

    #                                               'info':plot_information, 'view':[view]}
    #        self.update_tree(plot_information['plot_name'], data = plot_information, tree = 'Scatter')
    #        self.add_plot(plot_information)

    def plot_scatter(self, values=None, fig=None, save=False):
        """Creates a plots from self.toolBox Scatter page.
        
        Creates both scatter and heatmaps (spatial histograms) for bi- and ternary plots.

        :param values: Defaults to None
        :type values:
        :param fig: Defaults to None
        :type fig:
        :param save: Flag for saving widget to self.toolBoxTreeView Plot Selector page, Defaults to False
        :type save: bool, optional"""
        # update plot style parameters
        self.get_general_style()
        self.get_scatter_style(self.toolBox.currentIndex())
        if fig == None:
            x, y, z, c = self.get_scatter_values() #get scatter values from elements chosen
        else:
            # get saved scatter values to update plot
            x, y, z, c = values

        match self.comboBoxScatterType.currentText().lower():
            # scatter
            case 'scatter':
                s = self.scatter_style[self.toolBox.currentIndex()]
                if s['ColorByField'] == None:
                    c = {'field': None, 'type': None, 'units': None, 'array': None}

                if len(z['array']) == 0:
                    # biplot
                    self.biplot(fig,x,y,c,s,save)
                else:
                    # ternary
                    self.ternary_scatter(fig,x,y,z,c,s,save)

            # heatmap
            case 'heatmap':
                s = self.heatmap_style[self.toolBox.currentIndex()]

                # biplot
                if len(z['array']) == 0:
                    self.hist2dbiplot(fig,x,y,s,save)
                # ternary
                else:
                    self.hist2dternplot(fig,x,y,z,s,save,c=c)



    def newplot(self, fig, plot_name, plot_information, save):
        """Creates new figure widget

        :param fig: figure object
        :type fig: matplotlib.Figure
        :param plot_name: used to name the plot in the tree
        :type plot_name: str
        :param plot_information: plot dictionary
        :type plot_information: dict
        :param save: if the new plot should be saved to be recalled later
        :type save: bool
        """
        # Create a Matplotlib figure and axis
        widgetScatter = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        widgetScatter.setLayout(layout)

        # scatter_plot = pg.PlotWidget(title=select_scatter)
        scatter_plot = FigureCanvas(fig)
        view = self.canvasWindow.currentIndex()

        # Add the plot widget to your layout
        layout.insertWidget(0,scatter_plot)
        toolbar = NavigationToolbar(scatter_plot)  # Create the toolbar for the canvas
        # widgetScatter.layout().addWidget(toolbar)

        if save:
            # adds plot to dictionary for tree
            self.plot_widget_dict['scatter'][self.sample_id][plot_name] = {'widget':[widgetScatter],
                                                    'info':plot_information, 'view':[view]}
            # updates tree
            self.update_tree(plot_information['plot_name'], data = plot_information, tree = 'Scatter')

            # makes plot viewable
            self.add_plot(plot_information)
        else:
            # refresh window
            self.add_temp_plot(plot_information, widgetScatter)

    def add_temp_plot(self, plot_information, selected_plot_widget):
        plot_name = plot_information['plot_name']
        sample_id = plot_information['sample_id']
        plot_type = plot_information['plot_type']

        self.canvasWindow.setCurrentIndex(0)

        #Single view
        self.single_plot_name = plot_name

        #remove plot from multi view if the plot is already in multiview

        layout = self.widgetSingleView.layout()
        #remove current plot
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            if item is not None:
                widget = item.widget()   # Get the widget from the item
                if widget is not None:
                    layout.removeWidget(widget)  # Remove the widget from the layout
                    widget.setParent(None)      # Set the widget's parent to None

        self.current_plot = plot_name
        self.current_plot_information = plot_information

        layout.addWidget(selected_plot_widget)
        selected_plot_widget.show()

        # Assuming widgetClusterMap is a QWidget with a QVBoxLayout containing figure_canvas
        for i in range(selected_plot_widget.layout().count()):
            widget = selected_plot_widget.layout().itemAt(i).widget()
            if isinstance(widget, FigureCanvas):
                self.matplotlib_canvas = widget
                self.pyqtgraph_widget = None
                break
            elif isinstance(widget, pg.GraphicsLayoutWidget):
                self.pyqtgraph_widget = widget
                self.matplotlib_canvas = None
                break

        self.hide()
        self.show()

    def biplot(self, fig, x, y, c, s, save):
        """Creates scatter bi-plots

        A general function for creating scatter plots of 2-dimensions.

        :param fig: figure object
        :type fig: matplotlib.figure
        :param x: data associated with field self.comboBoxScatterIsotopeX.currentText() as x coordinate
        :type x: dict
        :param y: data associated with field self.comboBoxScatterIsotopeX.currentText() as y coordinate
        :type y: dict
        :param c: data associated with field self.comboBoxColorField.currentText() as marker colors
        :type c: dict
        :param s: style parameters
        :type s: dict
        """
        if fig == None:
            new = True
            fig = Figure()
        else:
            new = False

        ax = fig.add_subplot(111)
        if len(c['array']) == 0:
            # single color
            ax.scatter(x['array'], y['array'], c=s['Color'], s=s['Size'], marker=self.markerdict[s['Marker']], edgecolors='none', alpha=s['Alpha']/100)
            cb = None
        else:
            # color by field
            ax.scatter(x['array'], y['array'], c=c['array'],
                s=s['Size'],
                marker=self.markerdict[s['Marker']],
                edgecolors='none',
                cmap=plt.get_cmap(s['Colormap']),
                alpha=s['Alpha']/100)
            
            norm = plt.Normalize(vmin=np.min(c['array']), vmax=np.max(c['array']))
            scalarMappable = plt.cm.ScalarMappable(cmap=plt.get_cmap(s['Colormap']), norm=norm)
            cb = fig.colorbar(scalarMappable, ax=ax, orientation='vertical', location='right', shrink=0.62)
            cb.set_label(c['label'])

        # labels
        font = {'size':self.general_style['FontSize']}
        ax.set_xlabel(x['label'], fontdict=font)
        ax.set_ylabel(y['label'], fontdict=font)

        # tick marks
        ax.tick_params(direction=self.general_style['TickDir'],
                        labelsize=self.general_style['FontSize'],
                        labelbottom=True, labeltop=False, labelleft=True, labelright=False,
                        bottom=True, top=True, left=True, right=True)

        # aspect ratio
        ax.set_box_aspect(s['AspectRatio'])

        if new:
            plot_name = f"{x['field']}_{y['field']}_{'scatter'}"
            plot_information = {
                'plot_name': plot_name,
                'sample_id': self.sample_id,
                'plot_type': 'scatter',
                'values': (x, y, c),
                'fig': fig,
                'colorbar': cb
            }
            self.newplot(fig, plot_name, plot_information, save)


    def ternary_scatter(self, fig, x, y, z, c, s, save):
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
        :param s: style parameters
        :type s: dict
        :param save: flag indicating whether the plot should be saved to the plot tree
        :type save: bool
        """
        if fig == None:
            new = True
            labels = [x['field'], y['field'], z['field']]
            fig = Figure(figsize=(6, 4))
            ax = fig.subplots()
            tp = ternary(ax, labels, 'scatter')
            #tp = ternary(labels, 'scatter')
            #fig = tp.fig
        else:
            new = False

        if len(c['array']) == 0:
            tp.ternscatter(x['array'], y['array'], z['array'], marker=self.markerdict[s['Marker']], size=s['Size'], color=s['Color'])
            cb = None
        else:
            _, cb = tp.ternscatter(x['array'], y['array'], z['array'], categories=c['array'],
                                            marker=self.markerdict[s['Marker']],
                                            size=s['Size'],
                                            cmap=s['Colormap'],
                                            orientation='vertical')
            cb.set_label(c['label'])
        
        if new:
            plot_name = f"{x['field']}_{y['field']}_{z['field']}_{'ternscatter'}"
            plot_information = {
                'plot_name': plot_name,
                'sample_id': self.sample_id,
                'plot_type': 'scatter',
                'values': (x, y, z, c),
                'fig': fig,
                'colorbar': cb
            }
            self.newplot(fig, plot_name, plot_information, save)


    def hist2dbiplot(self, fig, x, y, s, save):
        """Creates 2D histogram figure

        A general function for creating 2D histograms.

        :param fig: figure object
        :type fig: matplotlib.figure
        :param x: x-dimension
        :type x: dict
        :param y: y-dimension
        :type y: dict
        :param s: style parameters
        :type s: dict
        :param save: saves figure widget to plot tree
        :type save: bool
        """
        if fig == None:
            new = True
            fig = Figure()
        else:
            new = False

        ax = fig.add_subplot(111)

        # color by field
        ax.hist2d(x['array'], y['array'], bins=s['Resolution'], norm='log', cmap=plt.get_cmap(s['Colormap']))
            
        norm = plt.Normalize(vmin=0, vmax=3)
        scalarMappable = plt.cm.ScalarMappable(cmap=plt.get_cmap(s['Colormap']), norm=norm)
        cb = fig.colorbar(scalarMappable, ax=ax, orientation='vertical', location='right', shrink=0.62)
        cb.set_label('log(N)')

        # labels
        font = {'size':self.general_style['FontSize']}
        ax.set_xlabel(x['label'], fontdict=font)
        ax.set_ylabel(y['label'], fontdict=font)

        # tick marks
        ax.tick_params(direction=self.general_style['TickDir'],
                        labelsize=self.general_style['FontSize'],
                        labelbottom=True, labeltop=False, labelleft=True, labelright=False,
                        bottom=True, top=True, left=True, right=True)

        # aspect ratio
        ax.set_box_aspect(s['AspectRatio'])

        if new:
            plot_name = f"{x['field']}_{y['field']}_{'heatmap'}"
            plot_information = {
                'plot_name': plot_name,
                'sample_id': self.sample_id,
                'plot_type': 'scatter',
                'values': (x, y),
                'fig': fig,
                'colorbar': cb
            }
            self.newplot(fig, plot_name, plot_information, save)


    def hist2dternplot(self, fig, x, y, z, s, save, c=None):
        """Creates a ternary histogram figure

        A general function for creating scatter plots of 2-dimensions.

        :param fig: figure object
        :type fig: matplotlib.figure
        :param x: coordinate associated with top vertex
        :type x: dict
        :param y: coordinate associated with left vertex
        :type y: dict
        :param z: coordinate associated with right vertex
        :type z: dict
        :param s: style parameters
        :type s: dict
        :param save: saves figure widget to plot tree
        :type save: bool
        :param c: display, mean, median, standard deviation plots for a fourth dimension in
            addition to histogram map. Default is None, which produces a histogram.
        :type c: str
        """
        if fig == None:
            new = True
            labels = [x['field'], y['field'], z['field']]
            fig = Figure(figsize=(6, 4))
        else:
            new = False

        if len(c['array']) == 0:
            ax = fig.subplots()
            tp = ternary(ax, labels, 'heatmap')

            hexbin_df, cb = tp.ternhex(a=x['array'], b=y['array'], c=z['array'],
                bins=s['Resolution'],
                plotfield='n',
                cmap=s['Colormap'],
                orientation='vertical')

            #norm = plt.Normalize(vmin=0, vmax=3)
            #scalarMappable = plt.cm.ScalarMappable(cmap=plt.get_cmap(s['Colormap']), norm=norm)
            #cb = fig.colorbar(scalarMappable, ax=, orientation='vertical', location='right', shrink=0.62)
            cb.set_label('log(N)')
        else:
            axs = fig.subplot_mosaic([['left','upper right'],['left','lower right']], layout='constrained', width_ratios=[1.5, 1])

            for idx, ax in enumerate(axs):
                tps[idx] = ternary(ax, labels, 'heatmap')

            hexbin_df = ternary.ternhex(a=x['array'], b=y['array'], c=z['array'], val=c['array'], bins=s['Resolution'])

            cb.set_label(c['label'])

            #tp.ternhex(hexbin_df=hexbin_df, plotfield='n', cmap=s['Colormap'], orientation='vertical')

        if new:
            plot_name = f"{x['field']}_{y['field']}_{z['field']}_{'heatmap'}"
            plot_information = {
                'plot_name': plot_name,
                'sample_id': self.sample_id,
                'plot_type': 'scatter',
                'values': (x, y, z),
                'fig': fig,
                'colorbar': cb
            }
            self.newplot(fig, plot_name, plot_information, save)


    def plot_ternarymap(self):
        """Creates map colored by ternary coordinate positions"""
        self.get_general_style()
        self.get_scatter_style(self.toolBox.currentIndex())
        if fig == None:
            a, b, c = self.get_scatter_values() #get scatter values from elements chosen
        else:
            # get saved scatter values to update plot
            a, b, c,  = values

        selected_sample = self.sample_data_dict[self.sample_id]

        df = selected_sample[['X','Y']]
        
        if fig == None:
            new = True
            labels = [x['field'], y['field'], z['field']]
            fig = Figure(figsize=(6, 4))
            axs = [fig.add_subplots(['left' 'center']), fig.add_subplots(['right'])]
        else:
            new = False 

        ternary.ternmap(ax, selected_sample['X'],selected_sample['Y'], a,b,c, ca=[1,1,0], cb=[0.3,0.73,0.1], cc=[0,0,0.15], p=[1/3,1/3,1/3], cp = [])


    def plot_clustering(self):
        df_filtered, isotopes = self.get_processed_data()
        filtered_array = df_filtered.values
        # filtered_array = df_filtered.dropna(axis=0, how='any').values


        n_clusters = self.spinBoxNClusters.value()
        exponent = float(self.horizontalSliderClusterExponent.value()) / 10
        if exponent == 1:
            exponent = 1.0001
        distance_type = self.comboBoxClusterDistance.currentText()
        fuzzy_cluster_number = self.spinBoxFCView.value()

        if self.comboBoxClusterMethod.currentText() == 'all':
            # clustering_algorithms = {
            #     'KMeans': KMeans(n_clusters=n_clusters, init='k-means++'),
            #     'KMedoids': KMedoids(n_clusters=n_clusters, metric=distance_type),  # Assuming implementation
            #     'Fuzzy': 'fuzzy'  # Placeholder for fuzzy
            # }

            # Process for all clustering methods
            clustering_algorithms = {
                'KMeans': KMeans(n_clusters=n_clusters, init='k-means++'),
                'Fuzzy': 'fuzzy'  # Placeholder for fuzzy
            }
        elif self.comboBoxClusterMethod.currentText() == 'k-means':
            clustering_algorithms = {
                'KMeans': KMeans(n_clusters=n_clusters, init='k-means++')
                }
        elif self.comboBoxClusterMethod.currentText() == 'k-medoids':
            clustering_algorithms = {
                'KMedoids': KMedoids(n_clusters=n_clusters, metric=distance_type)  # Placeholder for fuzzy
            }

        elif self.comboBoxClusterMethod.currentText() == 'fuzzy c-means':
            clustering_algorithms = {
                'Fuzzy': 'fuzzy'  # Placeholder for fuzzy
            }


        self.process_clustering_methods( n_clusters, exponent, distance_type,fuzzy_cluster_number,  filtered_array,clustering_algorithms )


    def process_clustering_methods(self, n_clusters, exponent, distance_type, fuzzy_cluster_number, filtered_array, clustering_algorithms):
        #create unique id if new plot
        plot_type = 'clustering'
        if self.sample_id in self.plot_id[plot_type]:
            self.plot_id[plot_type][self.sample_id]  = self.plot_id[plot_type][self.sample_id]+1
        else:
            self.plot_id[plot_type][self.sample_id]  = 0

        plot_name =  plot_type+str(self.plot_id[plot_type][self.sample_id])

        # Create figure

        fig = Figure(figsize=(6, 4))
        # Adjust subplot parameters here for better alignment

        for i, (name, clustering) in enumerate(clustering_algorithms.items()):
            subplot_num = int('1'+str(len(clustering_algorithms))+str(i+1))
            #if len(clustering_algorithms) ==1:
                # Adjust the left and right margins
                # fig.subplots_adjust(left=0, right=1)

            ax = fig.add_subplot(subplot_num)

            # Create labels array filled with -1
            labels = np.full(filtered_array.shape[0], -1, dtype=int)
            if name == 'Fuzzy':
                cntr, u, _, _, _, _, _ = fuzz.cluster.cmeans(filtered_array.T, n_clusters, exponent, error=0.00001, maxiter=1000,seed =23)
                # cntr, u, _, _, _, _, _ = fuzz.cluster.cmeans(array.T, n_clusters, exponent, error=0.005, maxiter=1000,seed =23)
                for n in range(n_clusters):
                    self.fuzzy_results[n] = u[n-1,:]
                    if fuzzy_cluster_number>0:
                        labels[self.mask] = self.fuzzy_results[fuzzy_cluster_number][self.mask]
                    else:
                        labels[self.mask] = np.argmax(u, axis=0)[self.mask]
                        self.cluster_results[name][self.mask] = ['Cluster '+str(c) for c in labels]
            else:
                model = clustering.fit(filtered_array)
                labels[self.mask] = model.predict(filtered_array[self.mask])
                self.cluster_results[name][self.mask] = ['Cluster '+str(c) for c in labels]
            # Plot each clustering result
            self.plot_clustering_result(ax, labels, name, fuzzy_cluster_number)


        # Create and add the widget to layout
        self.add_clustering_widget_to_layout(fig,plot_name, plot_type)


    def plot_clustering_result(self, ax, labels, method_name, fuzzy_cluster_number):
        reshaped_array = np.reshape(labels, self.array_size, order=self.order)

        x_range = self.clipped_isotope_data[self.sample_id]['X'].max() -  self.clipped_isotope_data[self.sample_id]['X'].min()
        y_range = self.clipped_isotope_data[self.sample_id]['Y'].max() -  self.clipped_isotope_data[self.sample_id]['Y'].min()
        aspect_ratio =  (y_range/self.clipped_isotope_data[self.sample_id]['Y'].nunique())/ (x_range/self.clipped_isotope_data[self.sample_id]['X'].nunique())
        # aspect_ratio  = 1
        # aspect_ratio = 0.617
        fig = ax.figure
        if method_name == 'Fuzzy' and fuzzy_cluster_number>0:
            cmap = plt.get_cmap(self.cm)
            # img = ax.imshow(reshaped_array.T, cmap=cmap,  aspect=aspect_ratio)
            img = ax.imshow(reshaped_array, cmap=cmap,  aspect=aspect_ratio)
            fig.colorbar(img, ax=ax, orientation = self.comboBoxColorbarDirection.currentText().lower())
        else:
            unique_labels = np.unique(['Cluster '+str(c) for c in labels])
            unique_labels.sort()
            n_clusters = len(unique_labels)
            cmap = plt.get_cmap(self.cm, n_clusters)
            # Extract colors from the colormap
            colors = [cmap(i) for i in range(cmap.N)]
            # Assign these colors to self.group_cmap
            for label, color in zip(unique_labels, colors):
                self.group_cmap[label] = color

            boundaries = np.arange(-0.5, n_clusters, 1)
            norm = BoundaryNorm(boundaries, cmap.N, clip=True)
            img = ax.imshow(reshaped_array.astype('float'), cmap=cmap, norm=norm, aspect = aspect_ratio)
            fig.colorbar(img, ax=ax, ticks=np.arange(0, n_clusters), orientation = self.comboBoxColorbarDirection.currentText().lower())

        fig.subplots_adjust(left=0.05, right=1)  # Adjust these values as needed
        fig.tight_layout()
        # fig.canvas.manager.window.move(0,0)
        ax.set_title(f'{method_name} Clustering')
        ax.set_axis_off()

    def add_clustering_widget_to_layout(self, fig,plot_name, plot_type):



        widgetClusterMap = QtWidgets.QWidget()
        widgetClusterMap.setLayout(QtWidgets.QVBoxLayout())
        figure_canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(figure_canvas)  # Create the toolbar for the canvas
        widgetClusterMap.setObjectName('plotClusterMap')
        widgetClusterMap.layout().addWidget(figure_canvas)
        # widgetClusterMap.layout().addWidget(toolbar)
        self.plot_widget_dict['clustering'][self.sample_id][plot_name] = {'widget': [widgetClusterMap],
                                                              'info': {'plot_type': plot_type, 'sample_id': self.sample_id, 'n_clusters': self.spinBoxNClusters.value()},
                                                              'view': [self.canvasWindow.currentIndex()]}
        plot_information = {
            'plot_name': plot_name,
            'sample_id': self.sample_id,
            'plot_type': plot_type,

        }
        self.update_tree(plot_information['plot_name'], data = plot_information, tree = 'Clustering')
        self.add_plot(plot_information)

    def update_plot_with_new_colormap(self):
        if self.fig and self.clustering_results:
            for name, results in self.clustering_results.items():
                labels = results['labels']
                method_name = results['method_name']
                fuzzy_cluster_number = results['fuzzy_cluster_number']
                # Find the corresponding axis to update
                ax_index = list(self.clustering_results.keys()).index(name)
                ax = self.axs[ax_index]
                # Redraw the plot with the new colormap on the existing axis
                self.plot_clustering_result(ax, labels, method_name, fuzzy_cluster_number)

            # Redraw the figure canvas to reflect the updates
            self.fig.canvas.draw_idle()


    def update_cluster_ui(self):
        # update_clusters_ui - Enables/disables tools associated with clusters

        # Number of Clusters
        self.labelNClusters.setEnabled(True)
        self.spinBoxNClusters.setEnabled(True)

        if self.comboBoxClusterMethod.currentText() == 'k-means':
            # Enable parameters relevant to KMeans
            # Exponent
            self.labelExponent.setEnabled(False)
            self.labelClusterExponent.setEnabled(False)
            self.horizontalSliderClusterExponent.setEnabled(False)

            # Distance
            self.labelClusterDistance.setEnabled(False)
            self.comboBoxClusterDistance.setEnabled(False)

            # FC View
            self.labelFCView.setEnabled(False)
            self.spinBoxFCView.setEnabled(False)

        elif self.comboBoxClusterMethod.currentText() == 'k-medoids':
            # Enable parameters relevant to KMedoids
            # Exponent
            self.labelExponent.setEnabled(False)
            self.labelClusterExponent.setEnabled(False)
            self.horizontalSliderClusterExponent.setEnabled(False)

            # Distance
            self.labelClusterDistance.setEnabled(True)
            self.comboBoxClusterDistance.setEnabled(True)

            # FC View
            self.labelFCView.setEnabled(False)
            self.spinBoxFCView.setEnabled(False)

        elif self.comboBoxClusterMethod.currentText() == 'fuzzy c-means':
            # Enable parameters relevant to Fuzzy Clustering
            # Exponent
            self.labelExponent.setEnabled(True)
            self.labelClusterExponent.setEnabled(True)
            self.horizontalSliderClusterExponent.setEnabled(True)

            # Distance
            self.labelClusterDistance.setEnabled(False)
            self.comboBoxClusterDistance.setEnabled(False)

            # FC View
            self.labelFCView.setEnabled(True)
            self.spinBoxFCView.setEnabled(True)

        elif self.comboBoxClusterMethod.currentText() == 'all':
            # Enable parameters relevant to Fuzzy Clustering
            # Exponent
            self.labelExponent.setEnabled(True)
            self.labelClusterExponent.setEnabled(True)
            self.horizontalSliderClusterExponent.setEnabled(True)

            # Distance
            self.labelClusterDistance.setEnabled(True)
            self.comboBoxClusterDistance.setEnabled(True)

            # FC View
            self.labelFCView.setEnabled(True)
            self.spinBoxFCView.setEnabled(True)



    def get_processed_data(self):
        # return normalised, filtered data with that will be used for analysis
        use_isotopes = self.isotopes_df.loc[(self.isotopes_df['use']==True) & (self.isotopes_df['sample_id']==self.sample_id), 'isotopes'].values
        # Combine the two masks to create a final mask
        nan_mask = self.processed_isotope_data[self.sample_id][use_isotopes].notna().all(axis=1)
        
        # mask nan values and add to self.mask
        self.mask = self.mask  & nan_mask[self.axis_mask].values 

        df_filtered = self.processed_isotope_data[self.sample_id][use_isotopes][self.axis_mask]

        return df_filtered, use_isotopes


    def plot_n_dim(self):

        df_filtered, _  = self.get_processed_data()
        df_filtered = df_filtered[self.mask]

        ref_i = self.comboBoxNDimRefMaterial.currentIndex()

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

        plot_name = self.comboBoxNDimPlotType.currentText()
        if plot_name == 'Radar':
            axes_interval = 5
            if self.current_group['algorithm'] in self.cluster_results:
                # Get the cluster labels for the data

                cluster_labels = self.cluster_results[self.current_group['algorithm']][self.mask]
                df_filtered['clusters'] = cluster_labels

                radar = Radar(df_filtered, fields = self.n_dim_list, quantiles=quantiles, axes_interval = axes_interval, group_field ='clusters', groups = np.unique(cluster_labels.dropna()))

                fig,ax = radar.plot(cmap = self.group_cmap)
                ax.legend()
            else:
                radar = Radar(df_filtered, fields = self.n_dim_list, quantiles=quantiles, axes_interval = axes_interval, group_field ='', groups = None)

                fig,ax = radar.plot()
        else: #tec plot
            fig = Figure(figsize=(8, 6))
            ax = fig.add_subplot(111)
            yl = [np.inf, -np.inf]
            if self.current_group['algorithm'] in self.cluster_results:
                # Get the cluster labels for the data
                cluster_labels = self.cluster_results[self.current_group['algorithm']][self.mask]
                df_filtered['clusters'] = cluster_labels
                clusters = np.unique(cluster_labels)

                # Plot tec for all clusters
                for i in clusters:
                    # Create RGBA color
                    color = self.group_cmap[i][:-1]
                    ax,yl_tmp = plot_spider_norm(data = df_filtered.loc[df_filtered['clusters']==i,:],
                            ref_data = self.ref_data, norm_ref_data =  self.ref_data['model'][ref_i],
                            layer = self.ref_data['layer'][ref_i], el_list = self.n_dim_list ,
                            style = 'Quanta',quantiles = quantiles, ax = ax, c = color, label=f'{i}')
                    #store max y limit to convert the set y limit of axis
                    yl = [np.floor(np.nanmin([yl[0] , yl_tmp[0]])), np.ceil(np.nanmax([yl[1] , yl_tmp[1]]))]

                ax.legend()
                self.logax(ax, yl, 'y')
                ax.set_ylim(yl)
            else:
                ax,yl = plot_spider_norm(data = df_filtered, ref_data = self.ref_data, norm_ref_data =  self.ref_data['model'][ref_i], layer = self.ref_data['layer'][ref_i], el_list = self.n_dim_list ,style = 'Quanta', ax = ax)
            ax.set_ylabel('Abundance / ['+self.ref_data['model'][ref_i]+', '+self.ref_data['layer'][ref_i]+']')
            fig.tight_layout()
        widgetNDim = QtWidgets.QWidget()
        widgetNDim.setLayout(QtWidgets.QVBoxLayout())
        figure_canvas = FigureCanvas(fig)

        widgetNDim.setObjectName('plotNDim')
        widgetNDim.layout().addWidget(figure_canvas)


        plot_type = 'n-dim'
        #create unique id if new plot
        if self.sample_id in self.plot_id[plot_type]:
            self.plot_id[plot_type][self.sample_id]  = self.plot_id[plot_type][self.sample_id]+1
        else:
            self.plot_id[plot_type][self.sample_id]  = 0
        plot_name =  plot_name +'_'+str(self.plot_id[plot_type][self.sample_id])


        toolbar = NavigationToolbar(figure_canvas)  # Create the toolbar for the canvas
        # widgetNDim.layout().addWidget(toolbar)
        self.plot_widget_dict[plot_type][self.sample_id][plot_name] = {'widget': [widgetNDim],
                                                              'info': {'plot_type': plot_type, 'sample_id': self.sample_id},
                                                              'view': [self.canvasWindow.currentIndex()]}
        plot_information = {
            'plot_name': f'{plot_name}',
            'sample_id': self.sample_id,
            'plot_type': plot_type
        }
        self.update_tree(plot_information['plot_name'], data = plot_information, tree = 'n-Dim')
        self.add_plot(plot_information)

    def update_n_dim_table(self,calling_widget):

        def on_use_checkbox_state_changed(row, state):
            # Update the 'use' value in the filter_df for the given row
            self.filter_df.at[row, 'use'] = state == QtCore.Qt.Checked

        if calling_widget == 'IsotopeAdd':
            el_list = [self.comboBoxNDimIsotope.currentText().lower()]
            self.comboBoxNDimIsotopeSet.setCurrentText = 'user defined'
        elif calling_widget == 'IsotopeSetAdd':
            isotope_set = self.comboBoxNDimIsotopeSet.currentText().lower()

            ####
            #### This needs to be set up more generic so that a user defined sets can be added to the list
            ####
            if isotope_set == 'majors':
                el_list = ['Si','Ti','Al','Fe','Mn','Mg','Ca','Na','K','P']
            elif isotope_set == 'full trace':
                el_list = ['Cs','Rb','Ba','Th','U','K','Nb','Ta','La','Ce','Pb','Mo','Pr','Sr','P','Ga','Zr','Hf','Nd','Sm','Eu','Li','Ti','Gd','Dy','Ho','Y','Er','Yb','Lu']
            elif isotope_set == 'ree':
                el_list = ['La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu']
            elif isotope_set == 'metals':
                el_list = ['Na','Al','Ca','Zn','Sc','Cu','Fe','Mn','V','Co','Mg','Ni','Cr']

        isotopes_list = self.isotopes_df.loc[(self.isotopes_df['sample_id']==self.sample_id), 'isotopes'].values

        isotopes = [col for iso in el_list for col in isotopes_list if re.sub(r'\d', '', col).lower() == re.sub(r'\d', '',iso).lower()]

        self.n_dim_list.extend(isotopes)

        for isotope in isotopes:
            # Add a new row at the end of the table
            row = self.tableWidgetNDim.rowCount()
            self.tableWidgetNDim.insertRow(row)

            # Create a QCheckBox for the 'use' column
            chkBoxItem_use = QtWidgets.QCheckBox()
            chkBoxItem_use.setCheckState(QtCore.Qt.Checked)
            chkBoxItem_use.stateChanged.connect(lambda state, row=row: on_use_checkbox_state_changed(row, state))

            chkBoxItem_select = QTableWidgetItem()
            chkBoxItem_select.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                QtCore.Qt.ItemIsEnabled)

            chkBoxItem_select.setCheckState(QtCore.Qt.Unchecked)
            norm = self.isotopes_df.loc[(self.isotopes_df['sample_id'] == self.sample_id)
                                        & (self.isotopes_df['isotopes'] == isotope)].iloc[0]['norm']



            self.tableWidgetNDim.setCellWidget(row, 0, chkBoxItem_use)
            self.tableWidgetNDim.setItem(row, 1,
                                     QtWidgets.QTableWidgetItem(self.sample_id))
            self.tableWidgetNDim.setItem(row, 2,
                                     QtWidgets.QTableWidgetItem(isotope))

            self.tableWidgetNDim.setItem(row, 3,
                                     QtWidgets.QTableWidgetItem(norm))
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
            tick_labels.extend([f'$10^{i}$'] + [''] * (len(mt) - 1))

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
        # Clear the list widget
        self.tableWidgetViewGroups.clear()
        self.tableWidgetViewGroups.setHorizontalHeaderLabels(['Groups'])
        algorithm = ''
        # Check which radio button is checked and update the list widget
        if self.comboBoxColorMethod.currentText() == 'none':
            pass  # No clusters to display for 'None'
        elif self.comboBoxColorMethod.currentText() == 'fuzzy c-means':
            algorithm = 'Fuzzy'
        elif self.comboBoxColorMethod.currentText() == 'k-medoids':
            algorithm = 'KMediods'
        elif self.comboBoxColorMethod.currentText() == 'k-means':
            algorithm = 'KMeans'

        if algorithm in self.cluster_results:
            if not self.cluster_results[algorithm].empty:
                clusters = self.cluster_results[algorithm].dropna().unique()
                clusters.sort()
                self.tableWidgetViewGroups.setRowCount(len(clusters))

                for i, c in enumerate(clusters):
                    # item = QTableWidgetItem(str(c))
                    # Initialize the flag
                    self.isUpdatingTable = True
                    self.tableWidgetViewGroups.setItem(i, 0, QTableWidgetItem(c))
                    self.tableWidgetViewGroups.item(i, 0).setSelected(True)
                self.current_group = {'algorithm':algorithm,'clusters': clusters}


        else:
            self.current_group = {'algorithm':None,'clusters': None}
        self.isUpdatingTable = False

    def cluster_label_changed(self, item):
        # Initialize the flag
        if not self.isUpdatingTable: #change name only when cluster renamed
            # Get the new name and the row of the changed item
            new_name = item.text()
            row = item.row()
            print(new_name)
            # Extract the cluster id (assuming it's stored in the table)
            cluster_id = self.current_group['clusters'][row]

            # Check for duplicate names
            for i in range(self.tableWidgetViewGroups.rowCount()):
                if i != row and self.tableWidgetViewGroups.item(i, 0).text() == new_name:
                    # Duplicate name found, revert to the original name and show a warning
                    item.setText(cluster_id)
                    print("Duplicate name not allowed.")
                    return

            # Update self.cluster_results with the new name
            if self.current_group['algorithm'] in self.cluster_results:
                # Find the rows where the value matches cluster_id
                rows_to_update = self.cluster_results[self.current_group['algorithm']] == cluster_id

                # Update these rows with the new name
                self.cluster_results.loc[rows_to_update, self.current_group['algorithm']] = new_name
                self.group_cmap[new_name] = self.group_cmap[cluster_id]
                del self.group_cmap[cluster_id]
            # Optionally, update current_group to reflect the new cluster name
            self.current_group['clusters'][row] = new_name

    def outlier_detection(self, data ,lq = 0.0005, uq = 99.5,d_lq =9.95 , d_uq = 99):
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

    def transform_plots(self, array):
            if array.ndim == 2:
                # Calculate min and max values for each column and adjust their shapes for broadcasting
                min_val = np.nanmin(array, axis=0, keepdims=True) - 0.0001
                max_val = np.nanmax(array, axis=0, keepdims=True)
    
                # Adjust the shape of min_val and max_val for broadcasting
                adjusted_min_val = min_val
                adjusted_max_val = max_val
    
                # Check if min values are less than 0
                min_less_than_zero = adjusted_min_val < 0
    
                # Perform transformation with broadcasting
                t_array = np.where(
                    min_less_than_zero,
                    (adjusted_max_val * (array - adjusted_min_val)) / (adjusted_max_val - adjusted_min_val),
                    np.copy(array)
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


    def add_ree(self, sample_df):

        lree = ['la', 'ce', 'pr', 'nd', 'sm', 'eu', 'gd']
        hree = ['tb', 'dy', 'ho', 'er', 'tm', 'yb', 'lu']
        mree = ['sm', 'eu', 'gd']

        # Convert column names to lowercase and filter based on lree, hree, etc. lists
        lree_cols = [col for col in sample_df.columns if any([col.lower().startswith(iso) for iso in lree])]
        hree_cols = [col for col in sample_df.columns if any([col.lower().startswith(iso) for iso in hree])]
        mree_cols = [col for col in sample_df.columns if any([col.lower().startswith(iso) for iso in mree])]
        ree_cols = lree_cols + hree_cols

        # Sum up the values for each row
        sample_df['LREE'] = sample_df[lree_cols].sum(axis=1)
        sample_df['HREE'] = sample_df[hree_cols].sum(axis=1)
        sample_df['MREE'] = sample_df[mree_cols].sum(axis=1)
        sample_df['REE'] = sample_df[ree_cols].sum(axis=1)

        return sample_df


    def change_sample(self, index):
        """Changes sample and plots first map
        
        Parameter
        ---------
        index: int
            index of sample name for identifying data.  The values are based on the
            comboBoxSampleID
        """
        if self.sample_data_dict:
            # Create and configure the QMessageBox
            messageBoxChangeSample = QMessageBox()
            iconWarning = QtGui.QIcon()
            iconWarning.addPixmap(QtGui.QPixmap(":/icons/resources/icons/icon-warning-64.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            
            messageBoxChangeSample.setWindowIcon(iconWarning)  # Set custom icon
            messageBoxChangeSample.setText("Do you want to save current analysis")
            messageBoxChangeSample.setWindowTitle("Save analysis")
            messageBoxChangeSample.setStandardButtons(QMessageBox.Discard | QMessageBox.Cancel | QMessageBox.Save)
            
            # Display the dialog and wait for user action
            response = messageBoxChangeSample.exec_()
            
            
            if response == QMessageBox.Save:
                self.save_analysis()
            elif response == QMessageBox.Discard:
                self.reset_analysis()
            else:
                return
                
        
        
        file_path = os.path.join(self.selected_directory, self.csv_files[index])
        self.sample_id = os.path.splitext(self.csv_files[index])[0]

        # print(self.self.sample_id)
        ####
        #### Need to fix this so that it calculates the size appropriately when they load
        #### Also need a program that correctly converts a iolite file to one that is read in hear.
        ####
        if self.sample_id == 'TR1-07':
            self.aspect_ratio = 0.976
        elif self.sample_id == 'TR3-06':
            self.aspect_ratio = 0.874
        elif self.sample_id == 'WOS-02':
            self.aspect_ratio = 0.873


        # add sample to sample dictionary
        if self.sample_id not in self.sample_data_dict:
            self.update_spinboxes_bool = False #prevent update plot from runing
            sample_df = pd.read_csv(file_path, engine='c')
            sample_df  = sample_df.loc[:, ~sample_df .columns.str.contains('^Unnamed')]
            # self.sample_data_dict[self.sample_id] = pd.read_csv(file_path, engine='c')
            self.sample_data_dict[self.sample_id] = self.add_ree(sample_df)
            self.selected_isotopes = list(self.sample_data_dict[self.sample_id].columns[5:])
            self.computed_isotope_data[self.sample_id] = {
                'ratio':None,
                'calculated':None,
                'special':None,
                'PCA score':None,
                'cluster':None,
                'cluster score':None
                }
            isotopes = pd.DataFrame()
            isotopes['isotopes']=list(self.selected_isotopes)
            isotopes['sample_id'] = self.sample_id
            isotopes['norm'] = 'linear'
            
            #update self.norm_dict
            self.norm_dict[self.sample_id] = {}
            for isotope in self.selected_isotopes:
                self.norm_dict[self.sample_id][isotope] = 'linear'
            #obtain axis bounds for plotting and cropping
            self.x_max= self.crop_x_max = self.sample_data_dict[self.sample_id]['X'].max()
            self.x_min =self.crop_x_min = self.sample_data_dict[self.sample_id]['X'].min()
            self.y_max = self.crop_y_max = self.sample_data_dict[self.sample_id]['Y'].max()
            self.y_min = self.crop_y_min = self.sample_data_dict[self.sample_id]['Y'].min()
            isotopes['upper_bound'] = 99.5
            isotopes['lower_bound'] = 0.05
            isotopes['d_l_bound'] = 99
            isotopes['d_u_bound'] = 99
            self.isotope_data[self.sample_id] = self.sample_data_dict[self.sample_id][self.selected_isotopes]
            self.clipped_isotope_data = copy.deepcopy(self.isotope_data)
            self.cropped_original_data = copy.deepcopy(self.isotope_data)
            isotopes['v_min'] = np.min(self.clipped_isotope_data[self.sample_id], axis=0)
            isotopes['v_max'] = np.max(self.clipped_isotope_data[self.sample_id], axis=0)
            isotopes['auto_scale'] = True
            isotopes['use'] = True
            self.isotopes_df = pd.concat([self.isotopes_df, isotopes])
            
            # add sample_id to self.plot_widget_dict
            
            self.cluster_results=pd.DataFrame(columns = ['Fuzzy', 'KMeans', 'KMediods'])
            self.cluster_results['X'] = self.sample_data_dict[self.sample_id]['X']
            self.cluster_results['Y'] = self.sample_data_dict[self.sample_id]['Y']
            
            for plot_type in self.plot_widget_dict.keys():
                if self.sample_id not in self.plot_widget_dict[plot_type]:
                    self.plot_widget_dict[plot_type][self.sample_id]={}

            # set mask of size of isotope array
            self.filter_mask = np.ones_like( self.sample_data_dict[self.sample_id]['X'].values, dtype=bool)
            self.polygon_mask = np.ones_like( self.sample_data_dict[self.sample_id]['X'], dtype=bool)
            self.axis_mask = np.ones_like( self.sample_data_dict[self.sample_id]['X'], dtype=bool)
            self.mask = self.filter_mask & self.polygon_mask & self.axis_mask
            
            self.prep_data()
            self.comboBoxFIsotope.clear()
            self.comboBoxNDimIsotope.clear()
            # self.comboBoxFIsotope_2.clear()
            self.comboBoxFIsotope.addItems(isotopes['isotopes'])
            self.update_filter_values()
            self.comboBoxScatterIsotopeX.clear()
            self.comboBoxScatterIsotopeX.addItems(isotopes['isotopes'])
            self.comboBoxScatterIsotopeY.clear()
            self.comboBoxScatterIsotopeY.addItems(isotopes['isotopes'])
            self.comboBoxScatterIsotopeZ.clear()
            self.comboBoxScatterIsotopeZ.addItem('')
            self.comboBoxScatterIsotopeZ.addItems(isotopes['isotopes'])

            self.comboBoxNDimIsotope.addItems(isotopes['isotopes'])

            self.comboBoxColorField.clear()
            self.comboBoxColorField.addItem('')
            self.comboBoxColorField.addItems(isotopes['isotopes'])

            # self.spinBoxX.setMaximum(int(x_max))
            # self.spinBoxX.setMinimum(int(x_min))
            # self.spinBox_X.setMaximum(int(x_max))
            # self.spinBox_X.setMinimum(int(x_min))
            # self.spinBoxY.setMaximum(int(y_max))
            # self.spinBoxY.setMinimum(int(y_min))
            # self.spinBox_Y.setMaximum(int(y_max))
            # self.spinBox_Y.setMinimum(int(y_min))

            # self.checkBoxViewRatio.setChecked(False)
            
            # plot first isotope as lasermap
            
            #get plot array
            current_plot_df = self.get_map_data(sample_id=self.sample_id, name = self.selected_isotopes[0],analysis_type = 'isotope', plot =False )
            print(self.selected_isotopes[0])
            #create plot
            self.create_plot(current_plot_df,sample_id=self.sample_id, plot_type = 'lasermap', isotope_1= self.selected_isotopes[0])
            
            
            
            
            # self.plot_laser_map(current_plot_df,plot_information)
            # self.update_spinboxes(parameters, auto_scale_param)
            # self.add_plot(plot_information, current_plot_df)
            
            self.create_tree(self.sample_id)
            self.clear_analysis()
            self.update_tree(self.norm_dict[self.sample_id])

            self.update_spinboxes_bool = True  # Place this line at end of method

            if self.comboBoxCorrelationMethod.currentText().lower() != 'none':
                print('plot correlation')
                self.plot_correlation()


    def update_combo_boxes(self, parentBox, childBox):
        """Updates comboBoxes with fields for plots or analysis
        
        Updates lists of fields in comboBoxes that are used to generate plots or used for analysis.
        Calls :get_field_list(): to construct the list.

        Parameter
        ---------
        parentBox: QComboBox
            comboBox used to select field type ('isotope', 'isotope (norm)', 'ratio', etc.)
        childBox: QComboBox
            comboBox with list of field values
        """

        fields = self.get_field_list(set_name=parentBox.currentText().lower())
        childBox.clear()
        childBox.addItems(fields)


    def update_spinboxes(self,parameters,bins = None ,bin_width = None):
        if self.canvasWindow.currentIndex()==0:
            self.update_spinboxes_bool = False
            auto_scale = parameters['auto_scale']
            #self.spinBoxX.setValue(int(parameters['x_max']))

            self.toolButtonAutoScale.setChecked(auto_scale)
            if auto_scale:
                self.doubleSpinBoxDUB.setEnabled(True)
                self.doubleSpinBoxDLB.setEnabled(True)
            else:
                self.doubleSpinBoxDUB.setEnabled(False)
                self.doubleSpinBoxDLB.setEnabled(False)
            # self.spinBox_X.setMinimum(int(parameters['x_max']))
            # self.spinBox_X.setMaximum(int(parameters['x_min']))
            # self.spinBox_X.setValue(int(parameters['x_min']))

            # self.spinBoxY.setMaximum(int(parameters['y_max']))
            # self.spinBoxY.setMinimum(int(parameters['y_min']))
            # self.spinBoxY.setValue(int(parameters['y_max']))


            # self.spinBox_Y.setMaximum(int(parameters['y_max']))
            # self.spinBox_Y.setMinimum(int(parameters['y_min']))
            # self.spinBox_Y.setValue(int(parameters['y_min']))

            self.doubleSpinBoxUB.setValue(parameters['upper_bound'])
            self.doubleSpinBoxLB.setValue(parameters['lower_bound'])
            self.doubleSpinBoxDLB.setValue(parameters['d_l_bound'])
            self.doubleSpinBoxDUB.setValue(parameters['d_u_bound'])
            # self.spinBoxNBins.setMaximum(int(max(isotope_array)))
            # self.spinBoxBinWidth.setMaximum(int(max(isotope_array)))
            if bins: #update these spinboxes if value returned from histogram
                self.spinBoxNBins.setValue(int(bins))
                self.spinBoxBinWidth.setValue(int(bin_width))

            self.lineEditFMin.setText(str(self.dynamic_format(parameters['v_min'])))
            self.lineEditFMax.setText(str(self.dynamic_format(parameters['v_max'])))

            self.update_spinboxes_bool = True


    def get_map_data(self,sample_id, name = None, analysis_type = 'isotope', plot= True, update = False):

        """
        Retrieves and processes the mapping data for the given sample and isotopes, then plots the result if required.

        Parameters:
        - self.sample_id (str): Identifier for the sample to be processed.
        - isotope_1 (str, optional): Primary isotope for plotting. If not provided, it's inferred from the isotope data frame.
        - isotope_2 (str, optional): Secondary isotope for ratio plotting. If not provided, only the primary isotope will be plotted.
        - analysis_type (str, default='laser'): Specifies the type of analysis. Accepts 'isotope' , 'ratio', 'pca', 'cluster', 'cluster score', 'special', 'computed'
        - plot (bool, default=True): Determines if the plot should be shown after processing.
        - auto_scale (bool, default=False): Determines if auto-scaling should be re-applied to the plot. if False use fmin and fmax and clip array

        Returns:
        - DataFrame: Processed data for plotting. This is only returned if analysis_type is not 'laser' or 'hist'.

        Note:
        - The method also updates certain parameters in the isotope data frame related to scaling.
        - Based on the plot type, this method internally calls the appropriate plotting functions.
        """
        #crop plot if filter applied
        current_plot_df = self.sample_data_dict[self.sample_id][['X','Y']][self.axis_mask].reset_index(drop=True)
        
        match analysis_type:
            
            case 'isotope':
                current_plot_df['array'] = self.clipped_isotope_data[sample_id].loc[:,name].values
                        
            case 'ratio':
                current_plot_df['array'] = self.computed_isotope_data[sample_id][analysis_type].loc[:,name].values
            
            case 'pca':
                current_plot_df['array'] = self.computed_isotope_data[sample_id][analysis_type].values
                
            case 'cluster':
                current_plot_df['array'] = self.computed_isotope_data[sample_id][analysis_type].values
                
            case 'cluster score':
                current_plot_df['array'] = self.computed_isotope_data[sample_id][analysis_type].values
                
            case 'special':
                current_plot_df['array'] = self.computed_isotope_data[sample_id][analysis_type].values
            case 'computed':
                current_plot_df['array'] = self.computed_isotope_data[sample_id][analysis_type].values
        
        # crop plot if filter applied
        # current_plot_df = current_plot_df[self.axis_mask].reset_index(drop=True)


        return current_plot_df
        
    def create_plot(self,current_plot_df, sample_id = None, plot_type = 'lasermap', isotope_1 = None, isotope_2 = None, plot = True):
        # creates plot information and send to relevant plotting method
        # adds plot to canvas if specified by user
        if not sample_id:
            sample_id = self.sample_id
        
        
        parameters = self.isotopes_df.loc[(self.isotopes_df['sample_id']==sample_id)
                          & (self.isotopes_df['isotopes']==isotope_1)].iloc[0]
        
        if not isotope_2: #not a ratio
            current_plot_df['array'] = self.clipped_isotope_data[sample_id][isotope_1].values
            isotope_str = isotope_1
        else:
            # Get the index of the row that matches the criteria
            index_to_update = self.ratios_df.loc[
                (self.ratios_df['sample_id'] == sample_id) &
                (self.ratios_df['isotope_1'] == isotope_1) &
                (self.ratios_df['isotope_2'] == isotope_2)
            ].index
            idx = index_to_update[0]
            parameters  = self.ratios_df.iloc[idx]
            current_plot_df['array'] = self.computed_isotope_data[sample_id]['ratio'][isotope_1].values
            isotope_str = isotope_1 +' / '+ isotope_2
        if plot_type=='lasermap':
            
            
            plot_information={'plot_name':isotope_str,'sample_id':sample_id,
                              'isotope_1':isotope_1, 'isotope_2':isotope_2,
                              'plot_type':plot_type}
            self.plot_laser_map(current_plot_df,plot_information)
            self.update_spinboxes(parameters)

        elif plot_type=='histogram':

            bins =self.default_bins

            bin_width = (np.nanmax(current_plot_df['array']) - np.nanmin(current_plot_df['array'])) / bins
            
            plot_information={'plot_name':isotope_str,'sample_id':sample_id,
                              'isotope_1':isotope_1, 'isotope_2':isotope_2,
                              'plot_type':plot_type}
            self.plot_histogram(current_plot_df,plot_information,bin_width = bin_width)
            self.update_spinboxes(parameters,bins, bin_width)
        elif plot_type == 'lasermap_norm':
            ref_data_chem = self.ref_data.iloc[self.comboBoxRefMaterial.currentIndex()]
            ref_data_chem.index = [col.replace('_ppm', '') for col in ref_data_chem.index]
            ref_series =  ref_data_chem[re.sub(r'\d', '', isotope_1).lower()]
            current_plot_df['array']= current_plot_df['array'] / ref_series
            plot_information={'plot_name':isotope_str,'sample_id':sample_id,
                              'isotope_1':isotope_1, 'isotope_2':isotope_2,
                              'plot_type':plot_type}
            self.plot_laser_map(current_plot_df,plot_information)
            self.update_spinboxes(parameters)
        else:
            # Return df for analysis
            ## filter current_plot_df based on active filters
            current_plot_df['array'] = np.where(self.mask, current_plot_df['array'], np.nan)
            return current_plot_df
        if plot:
            self.add_plot(plot_information, current_plot_df)


    def toolbar_plotting(self,function,view,enable):
        if function == 'home':
            self.toolButtonPanSV.setChecked(False)
            self.toolButtonZoomSV.setChecked(False)
            if self.matplotlib_canvas:
                self.matplotlib_canvas.toolbar.home()
            if self.pyqtgraph_widget:
                self.pyqtgraph_widget.getItem(0, 0).getViewBox().autoRange()

        if function == 'pan':
            self.toolButtonZoomSV.setChecked(False)
            if self.matplotlib_canvas:
                # Toggle pan mode in Matplotlib
                self.matplotlib_canvas.toolbar.pan()
            if self.pyqtgraph_widget:
                # Enable or disable panning
                self.pyqtgraph_widget.getItem(0, 0).getViewBox().setMouseMode(pg.ViewBox.PanMode if enable else pg.ViewBox.RectMode)

        if function == 'zoom':
            self.toolButtonPanSV.setChecked(False)
            if self.matplotlib_canvas:
                # Toggle zoom mode in Matplotlib
                self.matplotlib_canvas.toolbar.zoom()  # Assuming your Matplotlib canvas has a toolbar with a zoom function
            if self.pyqtgraph_widget:
                # Assuming pyqtgraph_widget is a GraphicsLayoutWidget or similar
                if enable:

                    self.pyqtgraph_widget.getItem(0, 0).getViewBox().setMouseMode(pg.ViewBox.RectMode)
                else:
                    self.pyqtgraph_widget.getItem(0, 0).getViewBox().setMouseMode(pg.ViewBox.PanMode)

        if function == 'preference':
            if self.matplotlib_canvas:
                self.matplotlib_canvas.toolbar.edit_parameters()
            if self.pyqtgraph_widget:
                # Assuming it's about showing/hiding axes
                if enable:
                    self.pyqtgraph_widget.showAxis('left', True)
                    self.pyqtgraph_widget.showAxis('bottom', True)
                else:
                    self.pyqtgraph_widget.showAxis('left', False)
                    self.pyqtgraph_widget.showAxis('bottom', False)

        if function == 'axes':
            if self.matplotlib_canvas:
                self.matplotlib_canvas.toolbar.configure_subplots()
            if self.pyqtgraph_widget:
                # Assuming it's about showing/hiding axes
                if enable:
                    self.pyqtgraph_widget.showAxis('left', True)
                    self.pyqtgraph_widget.showAxis('bottom', True)
                else:
                    self.pyqtgraph_widget.showAxis('left', False)
                    self.pyqtgraph_widget.showAxis('bottom', False)

        if function == 'save':
            if self.matplotlib_canvas:
                self.matplotlib_canvas.toolbar.save_figure()
            if self.pyqtgraph_widget:
                # Save functionality for pyqtgraph
                export = exportDialog.ExportDialog(self.pyqtgraph_widget.getItem(0, 0).scene())
                export.show(self.pyqtgraph_widget.getItem(0, 0).getViewBox())
                export.exec_()
    def import_data(self, path):
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
            file_name = os.path.splitext(csv_file)[0]
            # Get the file name without extension
            data_dict[file_name] = df
            i += 1
            # progressBar.setValue(i)
        return data_dict

    def create_tree(self,sample_id = None):
        if self.isotopes_df.empty:
            treeView  = self.treeView
            treeView.setHeaderHidden(True)
            self.treeModel = QStandardItemModel()
            rootNode = self.treeModel.invisibleRootItem()
            self.isotopes_items = StandardItem('Isotope', 14, True)
            self.norm_isotopes_items = StandardItem('Normalised Isotope', 14, True)
            self.ratios_items = StandardItem('Ratio', 14, True)
            self.histogram_items = StandardItem('Histogram', 14, True)
            self.correlation_items = StandardItem('Correlation', 14, True)
            self.scatter_items = StandardItem('Scatter', 14, True)
            self.n_dim_items = StandardItem('n-Dim', 14, True)
            self.pca_items = StandardItem('PCA', 14, True)
            self.clustering_items = StandardItem('Clustering', 14, True)

            rootNode.appendRows([self.isotopes_items,self.norm_isotopes_items,self.ratios_items,self.histogram_items,self.correlation_items, self.scatter_items,
                                 self.n_dim_items, self.pca_items, self.clustering_items])
            treeView.setModel(self.treeModel)
            treeView.expandAll()
            treeView.doubleClicked.connect(self.tree_double_click)
        elif sample_id:
            #self.isotopes_items.setRowCount(0)
            sample_id_item = StandardItem(sample_id, 13)
            histogram_sample_id_item = StandardItem(sample_id, 13)
            ratio_sampe_id_item = StandardItem(sample_id, 13)
            norm_sample_id_item = StandardItem(sample_id, 13)
            for isotope in self.isotopes_df.loc[self.isotopes_df['sample_id']==sample_id,'isotopes']:
                isotope_item = StandardItem(isotope)
                sample_id_item.appendRow(isotope_item)
                histogram_item = StandardItem(isotope)
                histogram_sample_id_item.appendRow(histogram_item)
                norm_item = StandardItem(isotope)
                norm_sample_id_item.appendRow(norm_item)
            self.isotopes_items.appendRow(sample_id_item)
            self.histogram_items.appendRow(histogram_sample_id_item)
            self.ratios_items.appendRow(ratio_sampe_id_item)
            self.norm_isotopes_items.appendRow(norm_sample_id_item)
    def tree_double_click(self,val):
        level_1_data = val.parent().parent().data()
        level_2_data =val.parent().data()
        level_3_data = val.data()
        # self.checkBoxViewRatio.setChecked(False)
        if level_1_data == 'Isotope' :
            current_plot_df = self.get_map_data(sample_id = level_2_data,name = level_3_data, analysis_type = 'isotope')
            self.create_plot(current_plot_df,plot_type='lasermap', isotope_1=level_3_data)
            
        if level_1_data == 'Normalised Isotope' :
            current_plot_df = self.get_map_data(sample_id = level_2_data,name = level_3_data)
            self.create_plot(current_plot_df,plot_type='lasermap_norm', isotope_1=level_3_data)
            
        elif level_1_data == 'Histogram' :
            current_plot_df = self.get_map_data(sample_id = level_2_data,name = level_3_data)
            
            self.create_plot(current_plot_df,plot_type='histogram', isotope_1=level_3_data)
            
        # self.add_plot(val.data())
        elif level_1_data == 'Ratio' :
            isotopes= level_3_data.split(' / ')
            
            current_plot_df = self.get_map_data(sample_id = level_2_data,name = level_3_data, analysis_type = 'ratio')
            
            self.create_plot(current_plot_df,plot_type='lasermap', isotope_1= isotopes[0],isotope_2=isotopes[1])
            

        elif ((level_1_data == 'Clustering') or (level_1_data=='Scatter') or (level_1_data=='n-dim') or (level_1_data=='PCA')or (level_1_data=='Correlation')):
            plot_info ={'plot_name':level_3_data, 'plot_type':level_1_data.lower(),'sample_id':level_2_data }
            self.add_plot(plot_info)




    def open_select_isotope_dialog(self):
        isotopes_list = self.isotopes_df['isotopes'].values

        self.isotopeDialog = IsotopeSelectionWindow(isotopes_list,self.norm_dict[self.sample_id], self.clipped_isotope_data[self.sample_id], self)
        self.isotopeDialog.show()
        self.isotopeDialog.listUpdated.connect(lambda: self.update_tree(self.isotopeDialog.norm_dict, norm_update = True))
        result = self.isotopeDialog.exec_()  # Store the result here
        if result == QDialog.Accepted:
            self.norm_dict[self.sample_id] = self.isotopeDialog.norm_dict
            
        if result == QDialog.Rejected:
            self.update_tree(self.norm_dict[self.sample_id], norm_update = True)




    def update_tree(self,leaf,data = None,tree= 'Isotope', norm_update = False):
        if tree == 'Isotope':
            # Highlight isotopes in treeView
            # Un-highlight all leaf in the trees
            self.unhighlight_tree(self.ratios_items)
            self.unhighlight_tree(self.isotopes_items)
            self.isotopes_df.loc[self.isotopes_df['sample_id']==self.sample_id,'use'] = False
            if len(leaf.keys())>0:
                for isotope_pair, norm in leaf.items():
                    if '/' in isotope_pair:
                        isotope_1, isotope_2 = isotope_pair.split(' / ')
                        self.update_ratio_df(self.sample_id,isotope_1, isotope_2, norm)
                        ratio_name = f"{isotope_1} / {isotope_2}"
                        # Populate ratios_items if the pair doesn't already exist
                        item,check = self.find_leaf(tree = self.ratios_items, branch = self.sample_id, leaf = ratio_name)

                        if not check: #if ratio doesnt exist
                            child_item = StandardItem(ratio_name)
                            child_item.setBackground(QBrush(QColor(255, 255, 200)))
                            item.appendRow(child_item)
                        else:
                            item.setBackground(QBrush(QColor(255, 255, 200)))
                    else: #single isotope
                        
                        item,check = self.find_leaf(tree = self.isotopes_items, branch = self.sample_id, leaf = isotope_pair)
                        item.setBackground(QBrush(QColor(255, 255, 200)))
                        self.isotopes_df.loc[(self.isotopes_df['sample_id']==self.sample_id) & (self.isotopes_df['isotopes']==isotope_pair),'use'] = True
                        if norm_update: #update if isotopes are returned from Isotope selection window
                            self.update_norm(self.sample_id,norm,isotope_pair)

        elif tree=='Scatter':

            self.add_tree_item(self.sample_id,self.scatter_items,leaf,data)

        elif tree == 'Clustering':
            self.add_tree_item(self.sample_id,self.clustering_items,leaf,data)

        elif tree == 'n-Dim':
            self.add_tree_item(self.sample_id,self.n_dim_items,leaf,data)

        elif tree == 'PCA':
            self.add_tree_item(self.sample_id,self.pca_items,leaf,data)
        elif tree == 'Correlation':
            self.add_tree_item(self.sample_id,self.correlation_items,leaf,data)



    def add_tree_item(self,sample_id,tree, leaf, data):
        #check if leaf is in tree
        item,check = self.find_leaf(tree = tree, branch = sample_id, leaf = leaf)
        if item is None and check is None: #sample id item and plot item both dont exist
            cluster_sample_id_item = StandardItem(sample_id, 13)
            plot_item = StandardItem(leaf)
            if data is not None:
                # The role should be an integer, Qt.UserRole is the base value for custom roles
                custom_role = Qt.UserRole + 1

                # Store the dictionary in the item using a custom role
                plot_item.setData(data, custom_role)

            cluster_sample_id_item.appendRow(plot_item)
            tree.appendRow(cluster_sample_id_item)
        elif item is not None and check is False: #sample id item exists plot item doesnt exist
            plot_item = StandardItem(leaf)
            if data is not None:
                # The role should be an integer, Qt.UserRole is the base value for custom roles
                custom_role = Qt.UserRole + 1

                # Store the dictionary in the item using a custom role
                plot_item.setData(data, custom_role)
            #item is sample id item (branch)
            item.appendRow(plot_item)



    def unhighlight_tree(self, tree):
        """Reset the highlight of all items in the tree."""
        for i in range(tree.rowCount()):
            branch_item = tree.child(i)
            branch_item.setBackground(QBrush(QColor(255, 255, 255)))  # white or any default background color
            for j in range(branch_item.rowCount()):
                leaf_item = branch_item.child(j)
                leaf_item.setBackground(QBrush(QColor(255, 255, 255)))  # white or any default background color


    def find_leaf(self,tree, branch, leaf):
        #Returns leaf item,True  if leaf exists else returns branch item, False
            for index in range(tree.rowCount()):
                branch_item = tree.child(index)
                if branch_item.text() == branch:
                    for index in range(branch_item.rowCount()):
                        leaf_item = branch_item.child(index)
                        if leaf_item.text() == leaf:
                            return (leaf_item, True)
                    return (branch_item,False)
            return (None,None)



    def update_ratio_df(self,sample_id,isotope_1, isotope_2,norm):

        parameter= self.ratios_df.loc[(self.ratios_df['sample_id'] == sample_id) & (self.ratios_df['isotope_1'] == isotope_1) & (self.ratios_df['isotope_2'] == isotope_2)]
        if parameter.empty:
            ratio_info= {'sample_id': self.sample_id, 'isotope_1':isotope_1, 'isotope_2':isotope_2, 'norm': norm,
                            'upper_bound':np.nan,'lower_bound':np.nan,'d_bound':np.nan,'use': True,'auto_scale': True}
            self.ratios_df.loc[len(self.ratios_df)] = ratio_info



            self.prep_data(sample_id, isotope_1=isotope_1, isotope_2 = isotope_2)



class StandardItem(QStandardItem):
    def __init__(self, txt = '', font_size = 12, set_bold= False):
        super().__init__()

        fnt  = QFont()
        fnt.setBold(set_bold)
        self.setEditable(False)
        self.setText(txt)
        self.setFont(fnt)


class IsotopeSelectionWindow(QDialog, Ui_Dialog):
    listUpdated = pyqtSignal()
    def __init__(self, isotopes,norm_dict, clipped_data, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.isotopes = list(isotopes)
        self.norm_dict = norm_dict
        self.clipped_data = clipped_data
        self.correlation_matrix = None
        self.tableWidgetIsotopes.setRowCount(len(isotopes))
        self.tableWidgetIsotopes.setColumnCount(len(isotopes))
        self.tableWidgetIsotopes.setHorizontalHeaderLabels(list(isotopes))
        self.tableWidgetIsotopes.setHorizontalHeader(RotatedHeaderView(self.tableWidgetIsotopes))
        self.tableWidgetIsotopes.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidgetIsotopes.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.comboBoxScale.currentIndexChanged.connect(self.update_all_combos)

        self.tableWidgetIsotopes.setVerticalHeaderLabels(isotopes)
        self.correlation_methods = [
            "Pearson",
            "Spearman",
        ]

        for method in self.correlation_methods:
            self.comboBoxCorrelation.addItem(method)

        self.calculate_correlation()



        self.tableWidgetIsotopes.cellClicked.connect(self.toggle_cell_selection)

        self.tableWidgetSelected.setColumnCount(2)
        self.tableWidgetSelected.setHorizontalHeaderLabels(['Isotope Pair', 'normalisation'])

        self.pushButtonSaveSelection.clicked.connect(self.save_selection)

        self.pushButtonLoadSelection.clicked.connect(self.load_selection)

        self.pushButtonDone.clicked.connect(self.done_selection)

        self.pushButtonCancel.clicked.connect(self.reject)
        self.comboBoxCorrelation.activated.connect(self.calculate_correlation)
        self.tableWidgetIsotopes.setStyleSheet("QTableWidget::item:selected {background-color: yellow;}")
        if len(self.norm_dict.keys())>0:
            for isotope,norm in self.norm_dict.items():
                self.populate_isotope_list(isotope,norm)
        else:
            # Select diagonal pairs by default
            for i in range(len(self.isotopes)):
                row=column = i
                item = self.tableWidgetIsotopes.item(row, column)

                # If the item doesn't exist, create it
                if not item:
                    item = QTableWidgetItem()
                    self.tableWidgetIsotopes.setItem(row, column, item)
                    self.add_isotope_to_list(row, column)
                # If the cell is already selected, deselect it
                elif not item.isSelected():
                    item.setSelected(True)
                    self.add_isotope_to_list(row, column)
                else:
                    item.setSelected(False)
                    self.remove_isotope_from_list(row, column)
    def done_selection(self):
        self.update_list()
        self.accept()

    def update_all_combos(self):
        # Get the currently selected value in comboBoxScale
        selected_scale = self.comboBoxScale.currentText()

        # Iterate through all rows in tableWidgetSelected to update combo boxes
        for row in range(self.tableWidgetSelected.rowCount()):
            combo = self.tableWidgetSelected.cellWidget(row, 1)
            if combo is not None:  # Make sure there is a combo box in this cell
                combo.setCurrentText(selected_scale)  # Update the combo box value
    def update_scale(self):
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


    def calculate_correlation(self):
        selected_method = self.comboBoxCorrelation.currentText().lower()
        # Compute the correlation matrix
        self.correlation_matrix = self.clipped_data.corr(method=selected_method)
        for i, row_isotope in enumerate(self.isotopes):
            for j, col_isotope in enumerate(self.isotopes):

                correlation = self.correlation_matrix.loc[row_isotope, col_isotope]
                self.color_cell(i, j, correlation)
        self.create_colorbar()  # Call this to create and display the colorbar

    def color_cell(self, row, column, correlation):
        """Colors cells in """
        color = self.get_color_for_correlation(correlation)
        item = self.tableWidgetIsotopes.item(row, column)
        if not item:
            item = QTableWidgetItem()
            self.tableWidgetIsotopes.setItem(row, column, item)
        item.setBackground(color)

    def get_color_for_correlation(self, correlation):
            # Map correlation to RGB color
            r = 255 * (1 - (correlation > 0) * ( abs(correlation)))
            g = 255 * (1 - abs(correlation))
            b = 255 * (1 - (correlation < 0) * ( abs(correlation)))
            return QColor(int(r), int(g),int(b))

    def create_colorbar(self):
        colorbar_image = self.generate_colorbar_image(40, 200)  # Width, Height of colorbar
        colorbar_label = QLabel(self)
        colorbar_pixmap = QPixmap.fromImage(colorbar_image)
        self.labelColorbar.setPixmap(colorbar_pixmap)

    def generate_colorbar_image(self, width, height):
        image = QImage(width, height, QImage.Format_RGB32)
        painter = QPainter(image)
        painter.fillRect(0, 0, width, height, Qt.white)  # Fill background with white
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
        painter.setPen(Qt.black)
        for pos, label in zip(tick_positions, tick_labels):
            painter.drawLine(width - 20, pos, width-18 , pos)  # Draw tick mark
            painter.drawText(width-15 , pos + 5, label)   # Draw tick label
        painter.end()
        return image
    def toggle_cell_selection(self, row, column):
        item = self.tableWidgetIsotopes.item(row, column)

        # If the item doesn't exist, create it
        if not item:
            item = QTableWidgetItem()
            self.tableWidgetIsotopes.setItem(row, column, item)
            self.add_isotope_to_list(row, column)
        # If the cell is already selected, deselect it
        elif item.isSelected():
            item.setSelected(True)
            self.add_isotope_to_list(row, column)
        else:
            item.setSelected(False)
            self.remove_isotope_from_list(row, column)

    def add_isotope_to_list(self, row, column):
        row_header = self.tableWidgetIsotopes.verticalHeaderItem(row).text()
        col_header = self.tableWidgetIsotopes.horizontalHeaderItem(column).text()

        newRow = self.tableWidgetSelected.rowCount()
        self.tableWidgetSelected.insertRow(newRow)
        if row == column:
            self.tableWidgetSelected.setItem(newRow, 0, QTableWidgetItem(f"{row_header}"))
        else:
            # Add isotope pair to the first column
            self.tableWidgetSelected.setItem(newRow, 0, QTableWidgetItem(f"{row_header} / {col_header}"))

        # Add dropdown to the second column
        combo = QComboBox()
        combo.addItems(['linear', 'log'])
        self.tableWidgetSelected.setCellWidget(newRow, 1, combo)
        self.update_list()

    def remove_isotope_from_list(self, row, column):
        row_header = self.tableWidgetIsotopes.verticalHeaderItem(row).text()
        col_header = self.tableWidgetIsotopes.horizontalHeaderItem(column).text()
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


    def get_selected_data(self):
        data = []
        for i in range(self.tableWidgetSelected.rowCount()):
            isotope_pair = self.tableWidgetSelected.item(i, 0).text()
            combo = self.tableWidgetSelected.cellWidget(i, 1)
            selection = combo.currentText()
            data.append((isotope_pair, selection))
        return data


    def save_selection(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            with open(file_name, 'w') as f:
                for i in range(self.tableWidgetSelected.rowCount()):
                    isotope_pair = self.tableWidgetSelected.item(i, 0).text()
                    combo = self.tableWidgetSelected.cellWidget(i, 1)
                    selection = combo.currentText()
                    f.write(f"{isotope_pair},{selection}\n")

    def load_selection(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            with open(file_name, 'r') as f:
                for line in f.readlines():
                    self.populate_isotope_list(line)
            self.update_list()
            self.raise_()
            self.activateWindow()

    def update_list(self):
        self.norm_dict={}
        for i in range(self.tableWidgetSelected.rowCount()):
            isotope_pair = self.tableWidgetSelected.item(i, 0).text()
            combo = self.tableWidgetSelected.cellWidget(i, 1)
            selection = combo.currentText()
            self.norm_dict[isotope_pair] = selection
        self.listUpdated.emit()

    def populate_isotope_list(self, isotope_pair, norm):
        if '/' in isotope_pair:
            row_header, col_header = isotope_pair.split(' / ')
        else:
            row_header = col_header = isotope_pair
        # Select the cell in tableWidgetIsotope
        if row_header in self.isotopes:
            row_index = self.isotopes.index(row_header)
            col_index = self.isotopes.index(col_header)

            item = self.tableWidgetIsotopes.item(row_index, col_index)
            if not item:
                item = QTableWidgetItem()
                self.tableWidgetIsotopes.setItem(row_index, col_index, item)
            item.setSelected(True)

            # Add the loaded data to tableWidgetSelected
            newRow = self.tableWidgetSelected.rowCount()
            self.tableWidgetSelected.insertRow(newRow)
            self.tableWidgetSelected.setItem(newRow, 0, QTableWidgetItem(isotope_pair))
            combo = QComboBox()
            combo.addItems(['linear', 'log'])
            combo.setCurrentText(norm)
            self.tableWidgetSelected.setCellWidget(newRow, 1, combo)
            combo.currentIndexChanged.connect(self.update_scale)


class CustomAxis(AxisItem):
    def __init__(self, *args, **kwargs):
        AxisItem.__init__(self, *args, **kwargs)
        self.scale_factor = 1.0

    def setScaleFactor(self, scale_factor):
        self.scale_factor = scale_factor

    def tickStrings(self, values, scale, spacing):
        # Scale the values back to the original scale
        scaled_values = [v * self.scale_factor for v in values]
        print (scaled_values)
        # Format the tick strings as you want them to appear
        return ['{:.2f}'.format(v) for v in scaled_values]


class Table_Fcn:
    """Common table operations class

    For moving and deleting rows in QTableWidgets

    Methods
    -------
    move_row_up(table)
        moves a single row of table up one position
    move_row_down(table)
        moves a single row of table down one position
    delete_row(table)
        deletes selected rows from table
    """
    def __init__(self,main_window):
        self.main_window = main_window

    def move_row_up(self, table):
        """Moves a row up one position in a table

        Parameter
        ---------
        table: QTableWidget
            Moves the selected row in a table up one position. If multiple are selected
            only the top row is moved.
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

                    # Update self.profiles here accordingly
                    for key, profile in self.main_window.profiling.profiles.items():
                        if row >0:
                            profile[row], profile[row -1 ] = profile[row - 1], profile[row]
                    self.plot_profiles(sort_axis = False)
                    if self.main_window.toolButtonIPProfile.isChecked(): #reset interpolation if selected
                        self.clear_interpolation()
                        self.interpolate_points(interpolation_distance=int(self.main_window.lineEditIntDist.text()), radius= int(self.main_window.lineEditPointRadius.text()))
                #case 'NDim':
                    # update plot

                #case 'Filters':
                    # update filters
                    # update plots

    def move_row_down(self,table):
        """Moves a row down one position in a table

        Parameter
        ---------
        table: QTableWidget
            Moves the selected row in a table down one position. If multiple are selected
            only the top row is moved.
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
                    for key, profile in self.main_window.profiling.profiles.items():
                        if row < len(profile) - 1:
                            profile[row], profile[row + 1] = profile[row + 1], profile[row]
                    self.plot_profiles(sort_axis = False)
                    if self.main_window.toolButtonIPProfile.isChecked(): #reset interpolation if selected
                        self.clear_interpolation()
                        self.interpolate_points(interpolation_distance=int(self.main_window.lineEditIntDist.text()), radius= int(self.main_window.lineEditPointRadius.text()))

    def delete_row(self,table):
        """Deletes selected rows in a table

        Parameter
        ---------
        table: QTableWidget
        """
        rows = [index.row() for index in table.selectionModel().selectedRows()][::-1] #sort descending to pop in order
        print(table.accessibleName())
        match table.accessibleName():
            case 'Profiling':
                for row in rows:
                    # Get selected row and delete it
                    table.removeRow(row)
                    # remove point from each profile and its corresponding scatter plot item


                    for key, profile in self.main_window.profiling.profiles.items():
                        if row < len(profile):
                            scatter_item = profile[row][3]  # Access the scatter plot item
                            for _, (_, plot, _, _) in self.main_window.lasermaps.items():
                                plot.removeItem(scatter_item)
                            profile.pop(row) #index starts at 0

                self.main_window.profiling.plot_profiles(sort_axis = False)

                if self.main_window.toolButtonIPProfile.isChecked(): #reset interpolation if selected
                    self.main_window.profiling.clear_interpolation()
                    self.main_window.profiling.interpolate_points(interpolation_distance=int(self.main_window.lineEditIntDist.text()), radius= int(self.main_window.lineEditPointRadius.text()))

            case 'NDim':
                for row in rows:
                    # Get selected row and delete it
                    table.removeRow(row)

            case 'Filters':
                for row in rows:
                    # Get selected row and delete it
                    table.removeRow(row)
                    
            case 'Polygon':
                print('d')
                for row in rows:
                    # Get p_id
                    item = self.main_window.tableWidgetPolyPoints.item(row, 0)
                    p_id = int(item.text())
                    # Get selected row and delete it
                    table.removeRow(row)
                    
                    # remove point from each profile and its corresponding scatter plot item
                    for p in self.main_window.polygon.polygons[p_id]:
                        scatter_item = p[2]  # Access the scatter plot item
                        for _, (_, plot, _, _) in self.main_window.lasermaps.items():
                            plot.removeItem(scatter_item)
                    # delete polygon from list
                    del self.main_window.polygon.polygons[p_id]
                    # Remove existing temporary line(s) if any
                    if p_id in self.main_window.polygon.lines:
                        for line in self.main_window.polygon.lines[p_id]:
                            plot.removeItem(line)
                        self.main_window.polygon.lines[p_id] = []

    
class Crop_tool:
    """Crop maps

    Cropping maps sets the maximum extent of the map for analysis.

    Attributes
    ----------
    overlays: QGraphicsRectItem()
        contains data for the figure overlay showing crop region

    Methods
    -------
    init_crop()
        sets intial crop region as full map extent
    remove_overlays()
        removes darkened overlay following completion of crop
    update_overlay(rect)
        updates the overlay after user moves a boundary
    apply_crop()
        uses selected crop extent to set viewable area and map region for analysis
    """
    def __init__(self, main_window):
        self.main_window = main_window
        # Initialize overlay rectangles
        self.overlays = []

    def init_crop(self):
        """Sets intial crop region as full map extent."""
        if self.main_window.toolButtonCrop.isChecked():
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
            
            self.main_window.plot.addItem(self.crop_rect)

            for _ in range(4):
                overlay = QGraphicsRectItem()
                overlay.setBrush(QColor(0, 0, 0, 120))  # Semi-transparent dark overlay
                self.main_window.plot.addItem(overlay)
                self.overlays.append(overlay)
    
            self.update_overlay(self.crop_rect.rect())
            self.main_window.toolButtonCropApply.setEnabled(True)
        else:
            # reset to full view and remove overlays if user unselects crop tool
            self.main_window.reset_to_full_view()
            
    def remove_overlays(self):
        """Removes darkened overlay following completion of crop."""
        if len(self.overlays)> 0: #remove crop rect and overlays
            self.main_window.plot.removeItem(self.crop_rect)
            for overlay in self.overlays:
                self.main_window.plot.removeItem(overlay)
            self.main_window.toolButtonCropApply.setEnabled(False)
            self.overlays = []

    def update_overlay(self, rect):
        """Updates the overlay after user moves a boundary.
        
        Parameter
        ---------
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
            print(crop_rect.left())
            self.main_window.crop_x_min = crop_rect.left()
            self.main_window.crop_x_max = crop_rect.right()
            self.main_window.crop_y_min = crop_rect.top()
            self.main_window.crop_y_max = crop_rect.bottom()
            if len(self.overlays)> 0: #remove crop rect and overlays
                self.main_window.plot.removeItem(self.crop_rect)
                for overlay in self.overlays:
                    self.main_window.plot.removeItem(overlay)
                self.main_window.toolButtonCropApply.setEnabled(False)
            #update plot with crop
            self.main_window.apply_crop()
        
        
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
            self.pos = 'TL'
            return True
        elif (abs(pos.x() - rect.right()) < self.cursorChangeThreshold and abs(pos.y() - rect.bottom()) < self.cursorChangeThreshold):
            self.pos = 'BR'
            return True
        elif (abs(pos.x() - rect.left()) < self.cursorChangeThreshold and abs(pos.y() - rect.bottom()) < self.cursorChangeThreshold):
            self.pos = 'BL'
            return True
        elif (abs(pos.x() - rect.right()) < self.cursorChangeThreshold and abs(pos.y() - rect.top()) < self.cursorChangeThreshold):
            self.pos = 'TR'
            return True
        return False

    def resizeRect(self, newPos):
        rect = self.dragStartRect.normalized()
        if self.pos:
            if self.pos =='TL' or self.pos =='BL':
                rect.setLeft(newPos.x())
            elif self.pos =='TR' or self.pos =='BR':
                rect.setRight(newPos.x())
            if self.pos =='TR' or self.pos =='TL':
                rect.setTop(newPos.y())
            elif self.pos =='BR' or self.pos =='BL':
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


class Polygon:
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
        self.polygons = {}          #dict of polygons
        self.lines ={}              #temp dict for lines in polygon
        self.point_index = None             # index for move point
        self.p_id = None           # polygon ID
        self.p_id_gen = 0 #Polygon_id generator
    
    # Method to increment p_id_gen
    def increment_pid(self):
        """Creates new polygon pid
        
        When toolButtonPolyCreate is checked, a new polygon pid is created.
        """
        self.main_window.toolButtonPolyCreate.isChecked()
        self.p_id_gen += 1
        self.p_id = self.p_id_gen
        
    def plot_polygon_scatter(self, event,k, x, y, x_i, y_i):
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
                prev_scatter = self.polygons[self.p_id][self.point_index][2]
                self.main_window.plot.removeItem(prev_scatter)


                # Create a scatter plot item at the clicked position
                scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                scatter.setZValue(1e9)
                self.main_window.plot.addItem(scatter)

                
                #update self.point_index index of self.polygonswith new point data

                self.polygons[self.p_id][self.point_index] = (x,y, scatter)
                
                # Finalize and draw the polygon
                self.show_polygon_lines(x,y, complete = True)
                
                self.main_window.point_selected = False
                #update plot and table widget
                # self.update_table_widget()
            else:
                # find nearest profile point
                mindist = 10**12
                for i, (x_p,y_p,_) in enumerate(self.polygons[self.p_id]):
                    dist = (x_p - x)**2 + (y_p - y)**2
                    if mindist > dist:
                        mindist = dist
                        self.point_index = i
                    print(dist, round(mindist*self.array_x/self.main_window.x_range))
                if (round(mindist*self.array_x/self.main_window.x_range) < 50):
                    self.main_window.point_selected = True
        
        
        elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyAddPoint.isChecked():
            # add point 
            # user must first choose line of polygon
            # choose the vertext points to add point based on line 
            # Find the closest line segment to the click location
            min_distance = float('inf')
            insert_after_index = None
            for i in range(len(self.polygons[self.p_id])):
                p1 = self.polygons[self.p_id][i]
                p2 = self.polygons[self.p_id][(i + 1) % len(self.polygons[self.p_id])]  # Loop back to the start for the last segment
                dist = self.distance_to_line_segment(x, y, p1[0], p1[1], p2[0], p2[1])
                if dist < min_distance:
                    min_distance = dist
                    insert_after_index = i
            
            # Insert the new point after the closest line segment
            if insert_after_index is not None:
                scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                scatter.setZValue(1e9)
                self.main_window.plot.addItem(scatter)
                self.polygons[self.p_id].insert(insert_after_index + 1, (x, y, scatter))
        
            # Redraw the polygon with the new point
            self.show_polygon_lines(x, y, complete=True)
            
           
        
        elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPolyCreate.isChecked()) and self.main_window.toolButtonPolyRemovePoint.isChecked():
            # remove point 
            # draw polygon without selected point
            # remove point
            # Find the closest point to the click location
            min_distance = float('inf')
            point_to_remove_index = None
            for i, (px, py, _) in enumerate(self.polygons[self.p_id]):
                dist = ((px - x)**2 + (py - y)**2)**0.5
                if dist < min_distance:
                    min_distance = dist
                    point_to_remove_index = i
            
            # Remove the closest point
            if point_to_remove_index is not None:
                _, _, scatter_item = self.polygons[self.p_id].pop(point_to_remove_index)
                self.main_window.plot.removeItem(scatter_item)
        
            # Redraw the polygon without the removed point
            self.show_polygon_lines(x, y, complete=True)
            
            self.main_window.toolButtonPolyRemovePoint.setChecked(False)
            
            
            
        elif event.button() == QtCore.Qt.LeftButton:
            # Create a scatter self.main_window.plot item at the clicked position
            scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
            scatter.setZValue(1e9)
            self.main_window.plot.addItem(scatter)
            
            # add x and y to self.polygons dict
            if self.p_id not in self.polygons:
                self.polygons[self.p_id] = [(x,y, scatter)]
                
            else:
                self.polygons[self.p_id].append((x,y, scatter))
                
    def distance_to_line_segment(self, px, py, x1, y1, x2, y2):
        # Calculate the distance from point (px, py) to the line segment defined by points (x1, y1) and (x2, y2)
        # This is a simplified version; you might need a more accurate calculation based on your coordinate system
        return min(((px - x1)**2 + (py - y1)**2)**0.5, ((px - x2)**2 + (py - y2)**2)**0.5)
        
    def show_polygon_lines(self, x,y, complete = False):
        if self.p_id in self.polygons:
            # Remove existing temporary line(s) if any
            if self.p_id in self.lines:
                for line in self.lines[self.p_id]:
                    self.main_window.plot.removeItem(line)
            self.lines[self.p_id] = []

            points = self.polygons[self.p_id]
            if len(points) == 1:
                # Draw line from the first point to cursor
                line = PlotDataItem([points[0][0], x], [points[0][1], y], pen='r')
                self.main_window.plot.addItem(line)
                self.lines[self.p_id].append(line)
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
                poly_item = QtWidgets.QGraphicsPolygonItem(QtGui.QPolygonF([QtCore.QPointF(x, y) for x, y in zip(x_points, y_points)]))
                poly_item.setBrush(QtGui.QColor(100, 100, 150, 100))
                self.main_window.plot.addItem(poly_item)
                self.lines[self.p_id].append(poly_item)

                # Draw line from last point to cursor
                # line = PlotDataItem([points[-1][0], x], [points[-1][1], y], pen='r')
                # self.main_window.plot.addItem(line)
                # self.lines[self.p_id].append(line)
                
            elif complete and len(points) > 2:
                points = [QtCore.QPointF(x, y) for x, y, _ in self.polygons[self.p_id]]
                polygon = QtGui.QPolygonF(points)
                poly_item = QtWidgets.QGraphicsPolygonItem(polygon)
                poly_item.setBrush(QtGui.QColor(100, 100, 150, 100))
                self.main_window.plot.addItem(poly_item)
                self.lines[self.p_id].append(poly_item)
                
                self.update_table_widget()
                # Find the row where the first column matches self.p_id and select it
                for row in range(self.main_window.tableWidgetPolyPoints.rowCount()):
                    item = self.main_window.tableWidgetPolyPoints.item(row, 0)  # Assuming the ID is stored in the first column
                    if item and int(item.text()) == self.p_id:
                        self.main_window.tableWidgetPolyPoints.selectRow(row)
                        break
                    
    def update_table_widget(self):
        self.main_window.tableWidgetPolyPoints.setRowCount(0)  # Clear existing rows
        
        for p_id, val in self.polygons.items():
            row_position = self.main_window.tableWidgetPolyPoints.rowCount()
            self.main_window.tableWidgetPolyPoints.insertRow(row_position)

            # Fill in the data
            self.main_window.tableWidgetPolyPoints.setItem(row_position, 0, QTableWidgetItem(str(p_id)))
            self.main_window.tableWidgetPolyPoints.setItem(row_position, 1, QTableWidgetItem(str('')))
            self.main_window.tableWidgetPolyPoints.setItem(row_position, 2, QTableWidgetItem(str('')))
            self.main_window.tableWidgetPolyPoints.setItem(row_position, 3, QTableWidgetItem(str('In')))
            
            chkBoxItem_select = QTableWidgetItem()
            chkBoxItem_select.setFlags(QtCore.Qt.ItemIsUserCheckable |
                               QtCore.Qt.ItemIsEnabled)

            chkBoxItem_select.setCheckState(QtCore.Qt.Checked)
            
            self.main_window.tableWidgetPolyPoints.setItem(row_position, 4, chkBoxItem_select)
            
            chkBoxItem_select.stateChanged.connect(self.main_window.apply_filters(fullmap = False))

        
        # def on_use_checkbox_state_changed(row, state):
        #     # Update the 'use' value in the filter_df for the given row
        #     self.filter_df.at[row, 'use'] = state == QtCore.Qt.Checked
            
        # Enable or disable buttons based on the presence of points
        # self.toggle_buttons(self.main_window.tableWidgetPolyPoints.rowCount() > 0)


class Profiling:
    def __init__(self,main_window):
        self.main_window = main_window
        # Initialize other necessary attributes
        # Initialize variables and states as needed
        self.profiles = {}
        self.i_profiles = {}        #interpolated profiles
        self.point_selected = False # move point button selected
        self.point_index = -1              # index for move point
        self.all_errorbars = []      #stores points of profiles
        self.selected_points = {}  # Track selected points, e.g., {point_index: selected_state}
        self.edit_mode_enabled = False  # Track if edit mode is enabled
        self.original_colors = {}
        self.scatter_size = 64

    def plot_profile_scatter(self, event, array,k, plot, x, y, x_i, y_i):
        self.array_x = array.shape[1]
        self.array_y = array.shape[0]
        
        interpolate = False
        
        radius= int(self.main_window.lineEditPointRadius.text())
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
                prev_scatter = self.profiles[k][self.point_index][3]
                plot.removeItem(prev_scatter)
    
    
                # Create a scatter plot item at the clicked position
                scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                scatter.setZValue(1e9)
                plot.addItem(scatter)
                # Find all points within the specified radius
                circ_val = []
                circ_cord = []
                for i in range(max(0, y_i - radius), min(self.array_y, y_i + radius + 1)):
                    for j in range(max(0, x_i - radius), min(self.array_x , x_i + radius + 1)):
                        if np.sqrt((x_i - j)**2 + (y_i - i)**2) <= radius:
                            value = array[i, j]
                            circ_cord.append([i, j])
                            circ_val.append( value)
    
                #update self.point_index index of self.profiles with new point data
                if k in self.profiles:
    
                    self.profiles[k][self.point_index] = (x,y, circ_val,scatter, interpolate)
    
    
                if self.main_window.canvasWindow.currentIndex() == 1:
                    # Add the scatter item to all other plots and save points in self.profiles
                    for k, (_, p, v, array) in self.main_window.lasermaps.items():
                        circ_val = []
                        if p != plot and v==1 and self.array_x ==array.shape[1] and self.array_y ==array.shape[0] : #only add scatters to other lasermaps of same sample
                            # Create a scatter plot item at the clicked position
                            scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                            scatter.setZValue(1e9)
                            p.addItem(scatter)
                            for c in circ_cord:
                                value = array[c[0], c[1]]
                                circ_val.append( value)
                            if k in self.profiles:
                                self.profiles[k][self.point_index] = (x,y, circ_val,scatter, interpolate)
    
                #update plot and table widget
                self.main_window.plot_profiles()
                self.update_table_widget()
                if self.main_window.toolButtonIPProfile.isChecked(): #reset interpolation if selected
                    self.clear_interpolation()
                    self.interpolate_points(interpolation_distance=int(self.main_window.lineEditIntDist.text()), radius= int(self.main_window.lineEditPointRadius.text()))
            else:
                # find nearest profile point
                mindist = 10**12
                for i, (x_p,y_p,_,_,interpolate) in enumerate(self.profiles[k]):
                    dist = (x_p - x)**2 + (y_p - y)**2
                    if mindist > dist:
                        mindist = dist
                        self.point_index = i
                if not(round(mindist*self.array_x/self.main_window.x_range) < 50):
                    self.point_selected = True

            
        elif event.button() == QtCore.Qt.LeftButton:
            #switch to profile tab
            self.main_window.tabWidget.setCurrentIndex(2)
    
            # Create a scatter plot item at the clicked position
            scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
            scatter.setZValue(1e9)
            plot.addItem(scatter)
            # Find all points within the specified radius
            circ_val = []
            circ_cord = []
            for i in range(max(0, y_i - radius), min(self.array_y, y_i + radius + 1)):
                for j in range(max(0, x_i - radius), min(self.array_x , x_i + radius + 1)):
                    if np.sqrt((x_i - j)**2 + (y_i - i)**2) <= radius:
                        value = array[i, j]
                        circ_cord.append([i, j])
                        circ_val.append( value)
    
            #add values within circle of radius in self.profiles
            if k in self.profiles:
                self.profiles[k].append((x,y,circ_val,scatter, interpolate))
            else:
                self.profiles[k] = [(x,y, circ_val,scatter, interpolate)]
    
    
            if self.main_window.canvasWindow.currentIndex() == 1:
                # Add the scatter item to all other plots and save points in self.profiles
                for k, (_, p, v, array) in self.main_window.lasermaps.items():
                    circ_val = []
                    if p != plot and v==1 and self.array_x ==array.shape[1] and self.array_y ==array.shape[0] : #only add scatters to other lasermaps of same sample
                        # Create a scatter plot item at the clicked position
                        scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                        scatter.setZValue(1e9)
                        p.addItem(scatter)
                        for c in circ_cord:
                            value = array[c[0], c[1]]
                            circ_val.append( value)
                        if k in self.profiles:
                            self.profiles[k].append((x,y,circ_val, scatter, interpolate))
                        else:
                            self.profiles[k] = [(x,y, circ_val,scatter, interpolate)]
    
            self.plot_profiles()
            self.update_table_widget()
    
    
    def interpolate_points(self, interpolation_distance,radius):
        """
        Interpolate linear points between each pair of points in the profiles.
        """
        if self.main_window.toolButtonIPProfile.isChecked():
            interpolate = True
            for k, points in self.profiles.items():
                for i in range(len(points) - 1):
                    start_point = points[i]
                    end_point = points[i + 1]
                    if i==0:
                        self.i_profiles[k] = [start_point]
                    else:
                        self.i_profiles[k].append(start_point)

                    # Calculate the distance between start and end points
                    dist = self.calculate_distance(start_point, end_point)

                    # Determine the number of interpolations based on the distance
                    num_interpolations = max(int(dist / interpolation_distance) - 1, 0)

                    # Generate linearly spaced points between start_point and end_point
                    for t in np.linspace(0, 1, num_interpolations + 2)[1:-1]:  # Exclude the endpoints
                        x = start_point[0] + t * (end_point[0] - start_point[0])
                        y = start_point[1] + t * (end_point[1] - start_point[1])

                        x_i = round(x*self.array_x /self.main_window.x_range) #index points
                        y_i = round(y*self.array_y/self.main_window.y_range)
                        # Add the scatter item to all other plots and save points in self.profiles
                        _, p, v, array= self.main_window.lasermaps[k]
                        if v==self.main_window.canvasWindow.currentIndex() and self.array_x ==array.shape[1] and self.array_y ==array.shape[0] : #only add scatters to other lasermaps of same sample
                            # Create a scatter plot item at the clicked position
                            scatter = ScatterPlotItem([x], [y], symbol='+', size=5)
                            scatter.setZValue(1e9)
                            p.addItem(scatter)
                            # Find all points within the specified radius
                            circ_val = []
                            for i in range(max(0, y_i - radius), min(self.array_y, y_i + radius + 1)):
                                for j in range(max(0, x_i - radius), min(self.array_x , x_i + radius + 1)):
                                    if np.sqrt((x_i - j)**2 + (y_i - i)**2) <= radius:
                                        value = array[i, j]
                                        circ_val.append(value)
                            if k in self.i_profiles:
                                self.i_profiles[k].append((x,y,circ_val, scatter, interpolate))

                    self.i_profiles[k].append(end_point)
            # After interpolation, update the plot and table widget
            self.plot_profiles(interpolate= interpolate)
        else:
            self.clear_interpolation()
            #plot original profile
            self.plot_profiles(interpolate= False)
        # self.update_table_widget(interpolate= True)

    def clear_interpolation(self):
            # remove interpolation
            if len(self.i_profiles)>0:
                for key, profile in self.i_profiles.items():
                    for point in profile:
                        scatter_item = point[3]  # Access the scatter plot item
                        interpolate =point[4]
                        if interpolate:
                            _, plot, _, _ = self.main_window.lasermaps[key]
                            plot.removeItem(scatter_item)

    def plot_profiles(self,interpolate= False, sort_axis='x'):
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
                profiles = self.profiles
            else:
                profiles = self.i_profiles
            # Group profiles based on range similarity
            profile_groups = {}
            keys = []
            if self.main_window.canvasWindow.currentIndex(): #multiview
                keys= [k for k in profiles.keys() if k[-1]== '1']



            else: #singleview
                keys = [k for k in profiles.keys() if k[-1]== '0']

            colors = [cmap(i / len(keys)) for i in range(len(keys))]

            for k in keys:
                points =  profiles[k]
                distances, medians, lowers, uppers, mean,s_error  = process_points(points, sort_axis)
                if point_type == 'mean':
                    range_value = np.max(mean)- np.min(mean)

                    similar_group_found = False

                    for group_key, _ in profile_groups.items():
                        if abs(range_value - group_key) <= range_threshold:
                            profile_groups[group_key].append((k, distances, mean, s_error, np.min(mean)))
                            similar_group_found = True
                            break
                    if not similar_group_found:
                        profile_groups[range_value] = [(k, distances, mean, s_error, np.min(mean, np.max(mean)))]
                else:

                    range_value = np.max(medians)- np.min(medians)

                    similar_group_found = False

                    for group_key, _ in profile_groups.items():
                        if abs(range_value - group_key) <= range_threshold:
                            profile_groups[group_key].append((k, distances, medians, lowers, uppers, np.min(medians), np.max(medians)))
                            similar_group_found = True
                            break
                    if not similar_group_found:
                        profile_groups[range_value] = [(k, distances, medians, lowers, uppers, np.min(medians), np.max(medians))]

            return profile_groups, colors


        if not interpolate:
            profiles = self.profiles
        else:
            profiles = self.i_profiles

        if len(list(profiles.values())[0])>0: #if self.profiles has values
            self.main_window.tabWidget.setCurrentIndex(2) #show profile plot tab
            sort_axis=self.main_window.comboBoxProfileSort.currentText()
            range_threshold=int(self.main_window.lineEditYThresh.text())
            # Clear existing plot
            layout = self.main_window.widgetProfilePlot.layout()
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Get the colormap specified by the user
            cmap = matplotlib.colormaps.get_cmap(self.main_window.comboBoxMapColormap.currentText())
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
                            scatter = ax.scatter(distances, scaled_values, color=colors[idx+g_idx], s=64, picker=5, label=f'{profile_key[:-1]}')

                            #plot errorbars with no marker
                            _, _, barlinecols = ax.errorbar(distances, scaled_errors, yerr=scaled_errors, fmt='none', color=colors[idx+g_idx], ecolor='lightgray', elinewidth=3, capsize=0)
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
                            scatter = ax.scatter(distances, means, color=colors[idx+g_idx], s=64, picker=5, label=f'{profile_key[:-1]}')

                            #plot errorbars with no marker
                            _, _, barlinecols = ax.errorbar(distances, means, yerr=s_errors, fmt='none', color=colors[idx+g_idx], ecolor='lightgray', elinewidth=3, capsize=0)

                        self.all_errorbars.append((scatter,barlinecols[0]))
                        self.original_colors[profile_key] = colors[idx+g_idx]  # Assuming colors is accessible
                        self.selected_points[profile_key] = [False] * len(means)
                        el_labels.append(profile_key[:-1].split('_')[-1]) #get element name
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
                            scatter = ax.scatter(distances, scaled_values, color=colors[idx+g_idx],s=self.scatter_size, picker=5, gid=profile_key, edgecolors = 'none', label=f'{profile_key[:-1]}')
                            # ax2.scatter(distances, medians, color=colors[idx+g_idx],s=self.scatter_size, picker=5, gid=profile_key, edgecolors = 'none', label=f'{profile_key[:-1]}')
                            #plot errorbars with no marker
                            _, _, barlinecols = ax.errorbar(distances, scaled_values, yerr=scaled_errors, fmt='none', color=colors[idx+g_idx], ecolor='lightgray', elinewidth=3, capsize=0)


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
                            scatter = ax.scatter(distances, medians, color=colors[idx+g_idx],s=self.scatter_size, picker=5, gid=profile_key, edgecolors = 'none', label=f'{profile_key[:-1]}')
                            #plot errorbars with no marker
                            _, _, barlinecols = ax.errorbar(distances, medians, yerr=errors, fmt='none', color=colors[idx+g_idx], ecolor='lightgray', elinewidth=3, capsize=0)
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
            self.on_clear_profile_clicked()

    def on_clear_profile_clicked(self):
        # Clear all scatter plot items from the lasermaps
        for _, (_, plot, _, _) in self.main_window.lasermaps.items():
            items_to_remove = [item for item in plot.listDataItems() if isinstance(item, ScatterPlotItem)]
            for item in items_to_remove:
                plot.removeItem(item)

        # Clear the profiles data
        self.profiles.clear()

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
        return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

    def update_table_widget(self):
        self.main_window.tableWidgetProfilePoints.setRowCount(0)  # Clear existing rows
        point_number = 0
        first_data_point = list(self.profiles.values())[0]
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
            original_color = matplotlib.colors.to_rgba(self.original_colors[profile_key])  # Assuming you have a way to map indices to original colors

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
                facecolors[ind] = matplotlib.colors.to_rgba(original_color)
            else:
                # Set to grey
                facecolors[ind] = (0.75, 0.75, 0.75, 1)

            picked_scatter.set_facecolors(facecolors)
            # Update the scatter plot sizes
            picked_scatter.set_sizes(np.full(num_points, self.scatter_size))
            self.fig.canvas.draw_idle()

    def toggle_edit_mode(self):

        self.edit_mode_enabled = not self.edit_mode_enabled

    def toggle_point_visibility(self):
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





app = None
def main():
    global app

    app = QtWidgets.QApplication(sys.argv)

    main = MainWindow()

    # Set the main window to fullscreen
    #main.showFullScreen()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()