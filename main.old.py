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
from matplotlib.patches import Patch
import matplotlib.colors as colors
from src.common.ChemPlot import plot_map_mpl, plot_small_histogram, plot_histogram, plot_correlation, get_scatter_data, plot_scatter, plot_ternary_map
from src.common.plot_spider import plot_spider_norm
from src.common.scalebar import scalebar
from src.app.LameIO import LameIO
#import src.radar_factory
from src.ui.MainWindow import Ui_MainWindow
#from src.ui.PreferencesWindow import Ui_PreferencesWindow
from src.app.FieldSelectionWindow import FieldDialog
from src.app.AnalyteSelectionWindow import AnalyteDialog
from src.common.TableFunctions import TableFcn as TableFcn
import src.common.CustomMplCanvas as mplc
from src.app.Actions import Actions
from src.common.DataHandling import SampleObj
from src.app.PlotTree import PlotTree
from src.app.CropImage import CropTool
from src.app.ImageProcessing import ImageProcessing as ip
from src.app.StyleToolbox import StylingDock
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

    def __init__(self, *args, **kwargs):
 
        super(MainWindow, self).__init__(*args, **kwargs)

        self.setupUi(self)

        # Add this line to set the size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # this flag sets whether the plot can be updated.  Mostly off during change_sample
        self.plot_flag = False


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

        
        #Flags to prevent plotting when widgets change
        self.point_selected = False
        self.check_analysis = True
        self.update_bins = True
        self.update_cluster_flag = True
        self.update_pca_flag = True
        self.plot_flag = True

        self.plot_info = ObservableDict()

        # set locations of dock widgets
        
        # code is more resilient if toolbox indices for each page is not hard coded
        # will need to change case text if the page text is changed
        # left toolbox
        

        self.toolBar.insertWidget(self.actionSelectAnalytes,self.widgetSampleSelect)
        self.toolBar.insertWidget(self.actionUpdatePlot,self.widgetPlotTypeSelect)

        self.toolbar_actio = Actions(self)

        # Set initial view
        self.toolBox.setCurrentIndex(self.left_tab['sample'])
        if hasattr(self, "mask_dock"):
            self.mask_dock.tabWidgetMask.setCurrentIndex(self.mask_tab['filter'])
        self.toolBoxStyle.setCurrentIndex(0)
        self.canvasWindow.setCurrentIndex(self.tab_dict['sv'])

 
        # Menu and Toolbar
        #-------------------------
        self.io = LameIO(parent=self, connect_actions=True, debug=self.logger_options['IO'])

       
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
        self.toolBox.currentChanged.connect(lambda: self.canvasWindow.setCurrentIndex(self.tab_dict['sv']))

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

        # self.toolButtonSave.clicked.connect(lambda: self.toolbar_plotting('save', 'SV', self.toolButtonSave.isChecked()))
        SaveMenu_items = ['Figure', 'Data']
        SaveMenu = QMenu()
        SaveMenu.triggered.connect(self.save_plot)
        self.toolButtonSave.setMenu(SaveMenu)
        for item in SaveMenu_items:
            SaveMenu.addAction(item)
        self.canvas_changed()


        # Setup Help
        #-------------------------
        # self.centralwidget.installEventFilter(self)
        # self.canvasWindow.installEventFilter(self)
        # self.dockWidgetLeftToolbox.installEventFilter(self)
        # self.dockWidgetRightToolbox.installEventFilter(self)
        # self.dockWidgetMaskToolbox.installEventFilter(self)

        self.toolBox.currentChanged.connect(self.toolbox_changed)
 

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

        self.canvasWindow.setCurrentIndex(self.tab_dict['sv'])
        self.init_tabs()
        self.change_sample()
        # self.profile_dock.profiling.add_samples()
        # self.polygon.add_samples()

        self.schedule_update()

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
        self.schedule_update()


    def update_equalize_color_scale_toolbutton(self, value):
        self.toolButtonScaleEqualize.setChecked(value)

        if self.plot_style.plot_type == 'field map':
            self.schedule_update()

    

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

    def reset_crop(self):
        self.data[self.app_data.sample_id].reset_crop
        self.schedule_update()

    def update_swap_resolution(self):
        if not self.data or self.app_data.sample_id != '':
            return
            
        self.data[self.app_data.sample_id].swap_resolution 
        self.schedule_update()

    def reset_pixel_resolution(self):
        self.data[self.app_data.sample_id].reset_resolution
        self.schedule_update()
    
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
        self.schedule_update()

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
            self.schedule_update()

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
        self.canvasWindow.setCurrentIndex(self.tab_dict['sv'])
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
        self.schedule_update()

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
        if self.canvasWindow.currentIndex() == self.tab_dict['sv']:
        # trigger update to plot
            self.schedule_update()

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
        self.schedule_update()
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
        self.schedule_update()

    def update_norm(self, norm, field=None):

        self.data[self.app_data.sample_id].update_norm(norm=norm, field=field)

        # trigger update to plot
        self.schedule_update()

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
            self.schedule_update()
        #self.update_all_plots()

    
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

                    if self.canvasWindow.currentIndex() == self.tab_dict['sv']:
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
        if (self.canvasWindow.currentIndex() == self.tab_dict['sv']) and (view == self.canvasWindow.currentIndex()):
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
    # General plot functions
    # -------------------------------------
    

        
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

        if self.canvasWindow.currentIndex() == self.tab_dict['mv']:
            list = self.ui.comboBoxMVPlots.allItems()
            if not list:
                return

            for i, _ in enumerate(list):
                # get data from comboBoxMVPlots
                data = self.comboBoxMVPlots.itemData(i, role=Qt.ItemDataRole.UserRole)

                # get plot_info from tree location and
                # reset view to False and position to none
                plot_info = self.plot_tree.retrieve_plotinfo_from_tree(tree=data[2], branch=data[3], leaf=data[4])
                #print(plot_info)
                plot_info['view'][1] = False
                plot_info['position'] = None
            
            # clear hover information for lasermaps
            self.multi_view_index = []
            self.multiview_info_label = {}

            # clear plot list in comboBox
            self.comboBoxMVPlots.clear()
            


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
            self.schedule_update()

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
        if view == self.tab_dict['sv']:
            title = field
        elif view == self.tab_dict['mv']:
            title = sample_id + '_' + field
        else:
            view = self.tab_dict['sv']
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
        if (self.toolBox.currentIndex() == self.left_tab['sample']) and (view == self.tab_dict['sv']):
            plot_small_histogram(self, self.data[self.app_data.sample_id], self.app_data, self.plot_style, map_df)


  
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
                self.schedule_update()

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
            ``UIControls.UIFieldLogic.update_field_type_combobox`` and
            ``UICongrols.UIFieldLogic.update_field_combobox``
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

        if self.canvasWindow.currentIndex() == self.tab_dict['sv']:
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
 

    def update_analyte_selection_from_file(self,filename):
        filepath = os.path.join(self.BASEDIR, 'resources/analytes list', filename+'.txt')
        analyte_dict ={}
        with open(filepath, 'r') as f:
            for line in f.readlines():
                field, norm = line.replace('\n','').split(',')
                analyte_dict[field] = norm

        self.update_analyte_ratio_selection(analyte_dict)