import os
from datetime import datetime
import traceback
from PyQt6.QtCore import ( Qt, QUrl, QMetaObject )
from PyQt6.QtWidgets import (
    QMessageBox,  QToolButton, QDialog, QLabel, QComboBox,
    QApplication, QMainWindow, QSizePolicy, QTreeView, QWidget
) # type: ignore
from PyQt6.QtGui import ( QIcon ) 
from src.common.CustomWidgets import CustomToolButton, CustomComboBox, CustomAction
from src.app.UITheme import ThemeManager, PreferencesManager, apply_font_to_children
from src.app.AppData import AppData
from src.app.StyleToolbox import StyleData
from src.app.MainToolBar import MainActions, MainMenubar, MainToolbar
from src.common.ScheduleTimer import Scheduler
import numpy as np
import pandas as pd
pd.options.mode.copy_on_write = True
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from src.common.LamePlot import (
    create_plot, plot_map_mpl, plot_histogram, plot_correlation, get_scatter_data, plot_scatter,
    plot_ternary_map, plot_ndim, plot_pca, plot_clusters, cluster_performance_plot
)
from src.app.LameIO import LameIO
from src.app.FieldLogic import ControlDock
from src.app.AnalyteDialog import AnalyteDialog
from src.app.FieldDialog import FieldDialog
from src.app.StylingUI import StylingDock
from src.app.LameStatusBar import MainStatusBar
from src.common.TableFunctions import TableFcn as TableFcn
from src.app.PlotTree import PlotTree
from src.app.CanvasWidget import CanvasWidget
from src.common.Masking import MaskDock
from src.app.CropImage import CropTool
from src.app.Profile import Profiling, ProfileDock
from src.common.Regression import RegressionDock
from src.common.Polygon import PolygonManager
from src.common.reSTNotes import NotesDock
from src.common.Browser import Browser
from src.app.Workflow import Workflow
from src.app.InfoViewer import InfoDock
from src.app.config import BASEDIR, APPDATA_PATH, ICONPATH, STYLE_PATH, load_stylesheet
from src.app.settings import prefs
from src.app.help_mapping import create_help_mapping
from src.common.Logger import LoggerConfig, auto_log_methods, log, no_log, LoggerDock
from src.common.Calculator import CalculatorDock
from src.app.PlotRegistry import PlotRegistry

import faulthandler
faulthandler.enable()

# to prevent segmentation error at startup
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
# setConfigOption('imageAxisOrder', 'row-major') # best performance

@auto_log_methods(logger_key='Main')
class MainWindow(QMainWindow):
    """Creates the MainWindow

    Attributes
    ----------
    app_data : AppData
        Properties and methods for the calling UI, in this case, MainWindow
    data : dict
        Dictionary of samples with sample IDs as keys
    style_data : StylingDock
        Properties and methods for styling plots and updating the Styling Dock
    """
    def __init__(self, app, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.app = app

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


        # The data dictionary will hold the data with a key for each sample
        #   contains:
        #       the dataframe raw, processed, and calculated fields
        #       data column attributes
        #       data attributes
        #       basic processing methods
        self.data = {}

        # The plot info dictionary holds information about the current plot
        self.plot_info = {}

        # initialize the application data
        #   contains:
        #       critical UI properties
        #       notifiers when properties change
        #       data structure and properties (DataHandling), data
        self.app_data = AppData(parent=self)
        self.style_data = StyleData(parent=self)
        
        # initialize plot registry for canvas and metadata management
        self.plot_registry = PlotRegistry(app_data=self.app_data, max_cached_canvases=10)

        # used to schedule plot updates
        self.scheduler = Scheduler(callback=self.update_SV)

        # initialize the styling data and dock
        self.setupUI()

        self.help_mapping = create_help_mapping(self)

        # connect listeners for dynamic propagation
        prefs.settingsChanged.connect(self.on_ui_pref_changed)

        # initial apply
        self.on_ui_pref_changed()

        self.connect_app_data_observers(self.app_data)

        self.theme_manager = ThemeManager(initial="auto", parent=self)

        # Apply theme changes to all CustomToolButton instances
        self.theme_manager.theme_changed.connect(self._apply_theme_to_buttons)

        self.connect_actions()
        self.connect_widgets()

        # holds the custom field names and formulas set by the user in the calculator
        self.calc_dict = {}
        self.open_calculator()
        self.calculator.hide()

        self.info_tab = {}

        #self.init_canvas_widget()
        self.mpl_canvas = None # will hold the current canvas

        # Force initial update of theme
        self._apply_theme_to_buttons(self.theme_manager.theme)

        # self.mpl_canvas = MplCanvas()
        # self.mpl_canvas.axes.clear()
        # self.mpl_canvas.axes.imshow()
        # self.mpl_canvas.draw()


    def setupUI(self):
        """Initialize the UI"""
        # setup MainWindow
        self.setObjectName("MainWindow")
        self.resize(1158, 1073)
        #self.setMaximumSize(QSize(16777215, 16777215))
        icon = QIcon(str(ICONPATH / "LaME-64.svg"))
        self.setWindowIcon(icon)
        self.setUnifiedTitleAndToolBarOnMac(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)

        # Actions and Toolbar
        self.lame_action = MainActions(self)
        self.toolbar = MainToolbar(self, self.lame_action)
        self.menu_bar = MainMenubar(self, self.lame_action)
        self.setMenuBar(self.menu_bar)

        # Status bar
        self.statusbar = MainStatusBar(self)
        self.setStatusBar(self.statusbar)

        # Central widget (canvas and toolbar)
        self.canvas_widget = CanvasWidget(ui=self, parent=self)
        self.setCentralWidget(self.canvas_widget)

        self.control_dock = ControlDock(ui=self)

        # Add this line to set the size policy
        self.control_dock.toolbox.setCurrentIndex(0)
        self.control_dock.toolbox.layout().setSpacing(2)

        self.open_plot_tree()

        self.style_dock = StylingDock(ui=self)
        self.style_dock.toolbox.setCurrentIndex(0)
        self.style_dock.toolbox.layout().setSpacing(2)

        self.control_dock.show()
        self.style_dock.show()

        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.control_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.style_dock)

        self.control_dock.setFloating(False)
        self.style_dock.setFloating(False)
        
        QMetaObject.connectSlotsByName(self)

        self.control_dock.reindex_tab_dict()
        self.style_dock.reindex_tab_dict()

        self.control_dock.toolbox.setCurrentIndex(self.control_dock.tab_dict['sample'])

        self.init_tabs(enable=False)

        self.io = LameIO(ui=self, connect_actions=True)

        # initialize used classes
        self.crop_tool = CropTool(self)
        self.table_fcn = TableFcn(self)
        #self.clustertool = Clustering(self)

    def connect_actions(self):
        self.lame_action.connect_actions()

        self.canvas_widget.canvasWindow.currentChanged.connect(lambda _: self.canvas_widget.tab_changed())

    def connect_widgets(self):
        """ Connects widgets to their respective methods and lame_action.
        
        This method sets up the connections for various widgets in the MainWindow,
        including the toolBox, comboBoxes, and buttons. It ensures that user interactions
        with these widgets trigger the appropriate methods for updating the UI and data.
        """
        self.control_dock.toolbox.currentChanged.connect(lambda: self.canvas_widget.canvasWindow.setCurrentIndex(self.canvas_widget.tab_dict['sv']))
        self.lame_action.FullMap.triggered.connect(self.control_dock.preprocess.reset_crop)

    
    def on_ui_pref_changed(self, *args):
        scale = prefs.scale

        # Global font
        p = prefs.property()
        QApplication.instance().setFont(p['font'])

        # Update entire main window (or other key components)
        apply_font_to_children(self, p['font'])

        # Optional: Apply specific toolbar font and scaling
        for child in self.findChildren(QToolButton):
            if 'reset' in child.objectName().lower():
                child.setFont(p['toolbar_font'])
                child.setIconSize(p['reset_button_icon_size'])
            elif 'action' in child.objectName().lower():
                child.setFont(p['toolbar_font'])
                child.setIconSize(p['toolbar_icon_size'])
            else:
                child.setFont(p['toolbar_font'])
                child.setIconSize(p['toolbutton_icon_size'])

        for child in self.findChildren(CustomToolButton):
            if 'reset' in child.objectName().lower():
                child.setFont(p['toolbar_font'])
                child.setIconSize(p['reset_button_icon_size'])
            elif 'action' in child.objectName().lower():
                child.setFont(p['toolbar_font'])
                child.setIconSize(p['toolbar_icon_size'])
            else:
                child.setFont(p['toolbar_font'])
                child.setIconSize(p['toolbutton_icon_size'])

        for child in self.findChildren(QLabel):
            child.setFont(p['font'])

        for child in self.findChildren(QTreeView):
            child.setFont(p['font'])

        for child in self.findChildren(QComboBox):
            child.setFont(p['font'])

        for child in self.findChildren(CustomComboBox):
            child.setFont(p['font'])

        # propagate to other custom buttons: they should listen to prefs.scaleChanged or
        # you can emit a custom signal here for modules to pick up

    def _apply_theme_to_buttons(self, theme):
        for btn in self.findChildren(CustomToolButton):
            btn.set_theme(theme)

        for btn in self.findChildren(CustomAction):
            btn.set_theme(theme)

        self.control_dock.toolbox.set_theme(theme)
        self.style_dock.toolbox.set_theme(theme)
        
        # Apply theme to MaskDock if it exists
        if hasattr(self, 'mask_dock'):
            # Apply theme directly to MaskDock
            self.mask_dock.apply_theme(theme)
            # Force complete style refresh for the MaskDock and its components
            # This ensures that stylesheets are properly applied after theme changes
            self._force_widget_style_refresh(self.mask_dock)

    def _force_widget_style_refresh(self, widget):
        """Force a complete style refresh on a widget and all its children"""        
        # Apply direct stylesheet to QGroupBox widgets based on current theme
        current_theme = self.theme_manager.theme
        
        # Define theme-specific styles for QGroupBox
        if current_theme == "dark":
            groupbox_style = """
            QGroupBox {
                border: none;
                border-radius: 3px;
                background-color: #282828;
                font: 10px;
                margin-top: 15px;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left; 
                padding: 0 3px;
                color: #ffffff;
            }
            """
        else:  # light theme
            groupbox_style = """
            QGroupBox {
                border: none;
                border-radius: 3px;
                background-color: #e0e0e0;
                font: 10px;
                margin-top: 15px;
                color: #000000;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left; 
                padding: 0 3px;
                color: #000000;
            }
            """
        
        # Apply styles to all QGroupBox widgets in MaskDock
        from PyQt6.QtWidgets import QGroupBox
        groupboxes = widget.findChildren(QGroupBox)
        print(f"Found {len(groupboxes)} QGroupBox widgets in MaskDock")
        for groupbox in groupboxes:
            print(f"Applying theme to QGroupBox: {groupbox.title()}")
            groupbox.setStyleSheet(groupbox_style)
            groupbox.update()
            groupbox.repaint()  # Force immediate repaint
        
        # Standard style refresh for all other widgets
        style = widget.style()
        if style:
            style.unpolish(widget)
            style.polish(widget)
        widget.update()
        
        # Recursively refresh all child widgets
        for child_widget in widget.findChildren(QWidget):
            if not isinstance(child_widget, QGroupBox):  # Skip QGroupBox, already handled above
                child_style = child_widget.style()
                if child_style:
                    child_style.unpolish(child_widget)
                    child_style.polish(child_widget)
                child_widget.update()

    def init_tabs(self, enable=False):
        """Enables/disables UI for user.

        Enables control (left) toolbox, mask dock, info dock, and calculator.

        Parameters
        ----------
        enable : bool, optional
            Enables/disables select UI controls for user, by default False
        """
        self.control_dock.toolbox.setCurrentIndex(self.control_dock.tab_dict['sample'])

        if not enable:
            self.control_dock.init_field_widgets(self.style_data.axis_settings)

            self.control_dock.preprocess.setEnabled(False)
            self.control_dock.field_viewer.setEnabled(False)
            if hasattr(self, "spot_tools"):
                self.control_dock.spot_tools.setEnabled(False)
            self.control_dock.scatter.setEnabled(False)
            self.control_dock.ndimensional.setEnabled(False)
            self.control_dock.dimreduction.setEnabled(False)
            self.control_dock.clustering.setEnabled(False)
            if hasattr(self, "special_tools"):
                self.control_dock.special_tools.setEnabled(False)
            if hasattr(self, "mask_dock"):
                self.mask_dock.tab_widgets.setTabEnabled(0,False)
                self.mask_dock.tab_widgets.setTabEnabled(1,False)
                self.mask_dock.tab_widgets.setTabEnabled(2,False)
            if hasattr(self, "info_dock"):
                self.info_dock.setEnabled(False)
            if hasattr(self, "calculator"):
                self.calculator.setEnabled(False)
            self.style_dock.toolbox.setEnabled(False)
        else:
            self.control_dock.preprocess.setEnabled(True)
            self.control_dock.field_viewer.setEnabled(True)
            if hasattr(self,"spot_tools"):
                self.control_dock.spot_tools.setEnabled(True)
            self.control_dock.scatter.setEnabled(True)
            self.control_dock.ndimensional.setEnabled(True)
            self.control_dock.dimreduction.setEnabled(True)
            self.control_dock.clustering.setEnabled(True)
            if hasattr(self,"special_tools"):
                self.control_dock.special_tools.setEnabled(True)
            if hasattr(self, "mask_dock"):
                self.mask_dock.tab_widgets.setTabEnabled(0,True)
                self.mask_dock.tab_widgets.setTabEnabled(1,True)
                self.mask_dock.tab_widgets.setTabEnabled(2,True)
            if hasattr(self, "info_dock"):
                self.info_dock.setEnabled(True)
            if hasattr(self, "calculator"):
                self.calculator.setEnabled(True)
            self.style_dock.toolbox.setEnabled(True)


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
                self.control_dock.toolbox.setCurrentIndex(self.control_dock.tab_dict['sample'])
                self.control_dock.toolbox.show()
            case 'preprocess':
                self.control_dock.toolbox.setCurrentIndex(self.control_dock.tab_dict['process'])
                self.control_dock.toolbox.show()
            case 'spot data':
                self.control_dock.toolbox.setCurrentIndex(self.control_dock.tab_dict['spot'])
                self.control_dock.toolbox.show()
            case 'polygons':
                self.mask_dock.tab_widgets.setCurrentIndex(self.mask_tab['polygon'])
                self.mask_dock.show()
            case 'scatter':
                self.control_dock.toolbox.setCurrentIndex(self.control_dock.tab_dict['scatter'])
                self.control_dock.toolbox.show()
            case 'ndim':
                self.control_dock.toolbox.setCurrentIndex(self.control_dock.tab_dict['ndim'])
                self.control_dock.toolbox.show()
            case 'multidimensional':
                self.control_dock.toolbox.setCurrentIndex(self.control_dock.tab_dict['dim_red'])
                self.control_dock.toolbox.show()
            case 'filters':
                self.mask_dock.tab_widgets.setCurrentIndex(self.mask_tab['filter'])
                self.mask_dock.tab_widgets.show()
            case 'clustering':
                self.control_dock.toolbox.setCurrentIndex(self.control_dock.tab_dict['cluster'])
                self.control_dock.toolbox.show()
            case 'clusters':
                self.mask_dock.tab_widgets.setCurrentIndex(self.mask_tab['cluster'])
                self.mask_dock.tab_widgets.show()
            case 'special':
                self.control_dock.toolbox.setCurrentIndex(self.control_dock.tab_dict['special'])
                self.control_dock.toolbox.show()
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

    def connect_app_data_observers(self, app_data):
        #app_data.add_observer("sort_method", self.update_sort_method)
        app_data.selectedClustersChanged.connect(self.update_selected_clusters_spinbox)

    # -------------------------------
    # UI update functions
    # Executed when a property is changed
    # -------------------------------

    #def update_sort_method(self, new_method):
    #    self.plot_tree.sort_tree(new_method)
    #    self.app_data.current_data.sort_data(new_method)


    def change_directory(self):
        # this will replace reset_analysis
        pass

    def change_sample(self):
        """Changes sample and plots first map.
        
        The UI is updated with a newly or previously loaded sample data."""
        # set plot flag to false, allow plot to update only at the end
        self.plot_flag = False

        if self.app_data.sample_id not in self.data:
            self.io.initialize_sample_object(outlier_method=self.control_dock.preprocess.comboBoxOutlierMethod.currentText(), negative_method = self.control_dock.preprocess.comboBoxNegativeMethod.currentText())
            self.control_dock.preprocess.connect_data_observers(self.app_data.current_data)
            # enable widgets that require self.data not be empty
            if self.data:
                self.lame_action.toggle_actions(True)
            else:
                self.lame_action.toggle_actions(False)
            
            # add sample to the plot tree
            self.plot_tree.add_sample(self.app_data.sample_id)
            self.plot_tree.update_tree()

        self.update_mask_and_profile_widgets()

        # sort data
        self.plot_tree.sort_tree(self.app_data.sort_method)

        # precalculate custom fields
        if hasattr(self, "calculator") and self.calculator.precalculate_custom_fields:
            for name in self.calc_dict:
                if name in self.app_data.current_data.processed.columns:
                    continue
                self.calculator.comboBoxFormula.setCurrentText(name)
                self.calculator.calculate_new_field(save=False)

        # reset flags
        self.app_data.update_cluster_flag = True
        self.app_data.update_pca_flag = True

        # update ui
        self.update_ui_on_sample_change()
        self.update_widget_data_on_sample_change()

        if self.style_data.plot_type != 'field map':
            self.style_data.plot_type = 'field map'

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
        self.schedule_update()

    def update_ui_on_sample_change(self):
        # reset all plot types on change of tab to the first option
        for key in self.field_control_settings:
            self.field_control_settings[key]['saved_index'] = 0

        self.init_tabs(enable=True)

        self.control_dock.preprocess.toolButtonAutoScale.clicked.connect(lambda: self.app_data.current_data.auto_scale_value(self.control_dock.preprocess.toolButtonAutoScale.isChecked()))

        # update slot connections that depend on the sample
        self.control_dock.preprocess.toolButtonOutlierReset.clicked.connect(lambda: self.app_data.current_data.reset_data_handling(self.control_dock.preprocess.comboBoxOutlierMethod.currentText(), self.control_dock.preprocess.comboBoxNegativeMethod.currentText()))

        # add spot data
        if hasattr(self, "spot_tab") and not self.app_data.current_data.spotdata.empty:
            self.io.populate_spot_table()

        # update docks
        if hasattr(self, "mask_dock"):
            self.update_mask_dock()

        if hasattr(self,'notes'):
            # change notes file to new sample.  This will initiate the new file and autosave timer.
            self.notes_dock.notes.notes_file = self.app_data.selected_directory / f"{self.app_data.sample_id}.rst"


        if hasattr(self,"info_dock"):
            self.info_dock.update_tab_widget()

        # set canvas to single view
        self.canvas_widget.canvasWindow.setCurrentIndex(self.canvas_widget.tab_dict['sv'])
        self.canvas_widget.tab_changed()
        
        # set toolbox tab indexes
        self.style_dock.toolbox.setCurrentIndex(0)
        self.control_dock.toolbox.setCurrentIndex(self.control_dock.tab_dict['sample'])
        self.control_dock.toolbox_changed()

        # update combobox to reflect list of available field types and fields
        #self.update_field_type_combobox_options(self.comboBoxFieldTypeC, self.comboBoxFieldC)

    def update_widget_data_on_sample_change(self):
        self.control_dock.update_field_combobox_options(self.control_dock.ndimensional.comboBoxNDimAnalyte)

        data = self.app_data.current_data

        # update dx, dy, nx, ny
        self.control_dock.preprocess.update_dimension('x', data.dx)
        self.control_dock.preprocess.update_dimension('y', data.dy)
        self.control_dock.preprocess.update_resolution('x', data.nx)
        self.control_dock.preprocess.update_resolution('y', data.ny)

        # update c_field_type and c_field
        self.app_data.c_field_type = 'Analyte'
        field = ''
        selected_analytes = self.app_data.selected_fields(field_type='Analyte')
        if len(selected_analytes) == 0:
            field = data.processed.match_attribute('data_type','Analyte')[0]
        else:
            field = selected_analytes[0]
        self.app_data.c_field = field

        # hist_bin_width and should be updated along with hist_num_bins
        self.app_data.hist_num_bins = self.app_data._default_hist_num_bins

        # update UI with auto scale and neg handling parameters from 'Analyte Info'
        self.update_autoscale_widgets(field=self.control_dock.comboBoxFieldC.currentText(), field_type=self.control_dock.comboBoxFieldTypeC.currentText())

        # reference chemistry is set when the data are initialized
        data.ref_chem = self.app_data.ref_chem

        # update multidim method, pcx to 1 and pcy to 2 (if pca exists)
        # ???
        # update cluster method and cluster properties (if cluster exists)
        # ???

    def update_mask_and_profile_widgets(self):
        #update filters, polygon, profiles with existing data
        self.lame_action.ClearFilters.setEnabled(False)
        if np.all(self.app_data.current_data.filter_mask):
            self.lame_action.FilterToggle.setEnabled(False)
        else:
            self.lame_action.FilterToggle.setEnabled(True)
            self.lame_action.ClearFilters.setEnabled(True)

        if np.all(self.app_data.current_data.polygon_mask):
            self.lame_action.PolygonMask.setEnabled(False)
        else:
            self.lame_action.PolygonMask.setEnabled(True)
            self.lame_action.ClearFilters.setEnabled(True)

        if np.all(self.app_data.current_data.cluster_mask):
            self.lame_action.ClusterMask.setEnabled(False)
        else:
            self.lame_action.ClusterMask.setEnabled(True)
            self.lame_action.ClearFilters.setEnabled(True)

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
                self.lame_action.Crop.setChecked(False)
                if hasattr(self, "mask_dock"):
                    if hasattr(self.mask_dock, "polygon_tab"):
                        self.actionPolyCreate.setChecked(False)
                        self.actionPolyMovePoint.setChecked(False)
                        self.actionPolyAddPoint.setChecked(False)
                        self.actionPolyRemovePoint.setChecked(False)
            case 'polygon':
                self.lame_action.Crop.setChecked(False)
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
        parameters = self.app_data.current_data.processed.column_attributes[field]

        # update noise reduction, outlier detection, neg. handling, quantile bounds, diff bounds
        self.app_data.current_data.current_field = self.control_dock.comboBoxFieldC.currentText()
        # data.negative_method = parameters['negative_method']
        # data.outlier_method = parameters['outlier_method']
        # data.smoothing_method = parameters['smoothing_method']
        # data.data_min_quantile = parameters['lower_bound']
        # data.data_max_quantile = parameters['upper_bound']
        # data.data_min_diff_quantile = parameters['diff_lower_bound']
        # data.data_max_diff_quantile = parameters['diff_upper_bound']

        auto_scale = parameters['auto_scale']
        self.control_dock.preprocess.toolButtonAutoScale.setChecked(bool(auto_scale))
        if auto_scale:
            self.control_dock.preprocess.lineEditDifferenceLowerQuantile.setEnabled(True)
            self.control_dock.preprocess.lineEditDifferenceUpperQuantile.setEnabled(True)
        else:
            self.control_dock.preprocess.lineEditDifferenceLowerQuantile.setEnabled(False)
            self.control_dock.preprocess.lineEditDifferenceUpperQuantile.setEnabled(False)

    def update_mask_dock(self):
        # Update filter UI 
        if hasattr(self, "mask_dock"):
            field = self.mask_dock.filter_tab.comboBoxFilterField.currentText()

            self.mask_dock.filter_tab.lineEditFMin.value = self.app_data.current_data.processed[field].min()
            self.mask_dock.filter_tab.lineEditFMax.value = self.app_data.current_data.processed[field].max()


    def update_selected_clusters_spinbox(self, new_selected_clusters):
        if self.control_dock.toolbox.currentIndex() == self.control_dock.tab_dict['cluster']:
            self.schedule_update()




    def update_equalize_color_scale(self):
        self.app_data.equalize_color_scale = self.control_dock.preprocess.toolButtonScaleEqualize.isChecked()
        if self.style_data.plot_type == "field map":
            self.schedule_update()
 
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
            self.app_data.current_data.ref_chem = self.app_data.ref_chem

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
        match self.style_data.plot_type:
            case 'field map':
                axes = ['c']
            case 'gradient map': 
                axes = ['c']
            case 'ternary map':
                axes = ['x','y','z']
            case 'correlation':
                return True
            case 'histogram':
                axes = ['x']
            case 'scatter':
                axes = ['x','y']
            case 'heatmap':
                axes = ['x','y']
            case 'TEC' | 'radar':
                return True
            case 'variance' | 'basis vectors' | 'performance':
                return True
            case 'dimension score map':
                axes = ['c']
            case 'dimension scatter', 'dimension heatmap':
                axes = ['x','y']
            case 'cluster map':
                axes = ['c']
            case 'cluster score map':
                axes = ['c']
            case 'profile':
                axes = ['c']
            case 'polygon':
                axes = ['c']

        for ax in axes:
            if self.app_data.get_field_type(ax) in invalid_values:
                return False
            if self.app_data.get_field(ax) in invalid_values:
                return False

        return True

    def schedule_update(self):
        """Schedules an update to a plot only when ``self.ui.plot_flag == True``."""
        if self.plot_flag:
            self.scheduler.schedule_update()

    def update_SV(self):
        """Updates current plot (not saved to plot selector)

        Updates the current plot (as determined by ``MainWindow.comboBoxPlotType.currentText()``
        and options in ``MainWindow.toolBox.selectedIndex()``.

        save : bool, optional
            save plot to plot selector, Defaults to False.
        """
        # UI-specific validation checks
        if self.app_data.sample_id == '' or self.style_data.plot_type in [None, '', 'none', 'None'] or not self.check_valid_fields():
            return

        # Prevent recursive updates during plotting by disabling plot_flag
        old_plot_flag = self.plot_flag
        self.plot_flag = False

        data = self.app_data.current_data

        # Clean up previous canvas reference
        old_canvas = getattr(self, 'mpl_canvas', None)

        
        try:
            # Handle UI-specific preprocessing and validations
            canvas = None
            self.plot_info = None
            hist_canvas = None
            
            # Handle plot type specific UI validations and preprocessing
            match self.style_data.plot_type:
                case 'field map':
                    # Field map has special UI handling for mask/profile modes and histogram
                    if (hasattr(self, "mask_dock") and self.mask_dock.polygon_tab.polygon_toggle.isChecked()) or (hasattr(self, "profile_dock") and self.profile_dock.profile_toggle.isChecked()):
                        # Mask/profile mode - use create_plot directly
                        canvas, self.plot_info = create_plot(self, data, self.app_data, self.style_data)
                        
                        # Handle profile/mask specific UI updates
                        if (hasattr(self, "profile_dock") and self.profile_dock.profile_toggle.isChecked()) and (self.app_data.sample_id in self.profile_dock.profiling.profiles):
                            self.profile_dock.profiling.clear_plot()
                            self.profile_dock.profiling.plot_existing_profile(self.plot)
                        elif (hasattr(self, "mask_dock") and self.mask_dock.polygon_tab.polygon_toggle.isChecked()) and (self.app_data.sample_id in self.mask_dock.polygon_tab.polygon_manager.polygons):  
                            self.mask_dock.polygon_tab.polygon_manager.clear_polygons()
                            self.mask_dock.polygon_tab.polygon_manager.plot_existing_polygon(canvas)
                    else:
                        # Always use create_plot for main canvas
                        canvas, self.plot_info = create_plot(self, data, self.app_data, self.style_data)
                        
                        # Handle histogram separately if needed (UI-specific feature)
                        if self.control_dock.toolbox.currentIndex() == self.control_dock.tab_dict['process']:
                            from src.common.LamePlot import plot_map_mpl
                            field_type = self.app_data.c_field_type
                            field = self.app_data.c_field
                            _, _, hist_canvas = plot_map_mpl(self, data, self.app_data, self.style_data, field_type, field, add_histogram=True)
                            
                            # Handle histogram UI placement
                            if hist_canvas:
                                self.canvas_widget.clear_layout(self.control_dock.preprocess.widgetHistView.layout())
                                layout = self.control_dock.preprocess.widgetHistView.layout()
                                if layout is not None:
                                    layout.addWidget(hist_canvas)
                            
                    # Handle field map canvas placement (special case)
                    if canvas:
                        self.mpl_canvas = canvas
                        self.canvas_widget.add_canvas_to_window(self.plot_info)
                        
                case 'gradient map':
                    # UI validation for gradient map
                    if self.control_dock.noise_reduction.comboBoxNoiseReductionMethod.currentText() == 'none':
                        from PyQt6.QtWidgets import QMessageBox
                        QMessageBox.warning(self,'Warning','Noise reduction must be performed before computing a gradient.')
                        return
                    # Perform noise reduction computation (UI-specific)
                    self.control_dock.noise_reduction.noise_reduction_method_callback()
                    # Note: gradient plotting would go here after noise reduction
                    
                case 'correlation':
                    # UI validation for correlation
                    if self.control_dock.correlation.comboBoxCorrelationMethod.currentText() == 'none':
                        return
                    canvas, self.plot_info = create_plot(self, data, self.app_data, self.style_data)
                    
                case 'scatter' | 'heatmap':
                    # UI validation for scatter/heatmap - field comparison
                    canvas, self.plot_info = create_plot(self, data, self.app_data, self.style_data)
                    
                case 'ternary map':
                    # UI validation for ternary map - field comparisons
                    canvas, self.plot_info = create_plot(self, data, self.app_data, self.style_data)
                    
                case 'variance' | 'basis vectors' | 'dimension scatter' | 'dimension heatmap' | 'dimension score map':
                    # Handle PCA computation (UI-specific)
                    if self.app_data.update_pca_flag or not data.processed.match_attribute('data_type','pca score'):
                        self.control_dock.dimreduction.compute_dim_red(data, self.app_data)
                    canvas, self.plot_info = create_plot(self, data, self.app_data, self.style_data)
                    
                case 'cluster map' | 'cluster score map':
                    # Handle clustering computation (UI-specific)
                    self.control_dock.clustering.compute_clusters_update_groups()
                    canvas, self.plot_info = create_plot(self, data, self.app_data, self.style_data)
                    
                case 'cluster performance':
                    # Handle cluster performance computation (UI-specific)
                    self.control_dock.clustering.compute_clusters(data, self.app_data, max_clusters = self.app_data.max_clusters)
                    canvas, self.plot_info = create_plot(self, data, self.app_data, self.style_data)
                    
                case _:
                    # For other plot types, use create_plot directly
                    canvas, self.plot_info = create_plot(self, data, self.app_data, self.style_data)
            
            # Handle canvas placement for non-field map plots
            if canvas and self.style_data.plot_type != 'field map':
                layout = self.canvas_widget.single_view.layout()
                if layout is not None:
                    self.canvas_widget.clear_layout(layout)
                    layout.addWidget(canvas)
                else:
                    print("Warning: single_view.layout() is None")
                
                # Store reference after successful addition
                self.mpl_canvas = canvas

            # Add plot info to info_dock (UI-specific)
            if hasattr(self,"info_dock") and hasattr(self, 'plot_info') and self.plot_info:
                self.info_dock.plot_info_tab.update_plot_info_tab(self.plot_info)

        except Exception as e:
            print(f"Error in update_SV: {e}")
            print("Type of object:", type(e))
            traceback.print_exc()
            # Restore old canvas if new one failed
            if old_canvas is not None:
                self.mpl_canvas = old_canvas
        finally:
            # Always restore plot_flag to prevent infinite loops
            self.plot_flag = old_plot_flag


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
            # Connect plot registry to plot tree
            self.plot_tree.plot_registry = self.plot_registry

            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.plot_tree)
            self.plot_tree.setFloating(False)

            self.statusbar.toolButtonRightDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.plot_tree, button=self.toolButtonRightDock))

        self.plot_tree.show()

    def add_canvas_to_window(self, plot_info, position=None):
        """Add plot to canvas using the registry system.
        
        This method serves as a bridge between the old plot_info approach
        and the new registry-based canvas management.
        
        Parameters
        ----------
        plot_info : dict
            Plot information dictionary
        position : tuple, optional
            Position for multi-view plots
        """
        if not hasattr(self, 'canvas_widget'):
            log("CanvasWidget not available", "WARNING")
            return
            
        # Get or create canvas using registry
        plot_id = plot_info.get('plot_id')
        if plot_id:
            # Canvas from registry
            canvas = self.plot_registry.get_or_create_canvas(plot_id)
            if canvas:
                # Update plot_info with canvas reference for backward compatibility
                plot_info['figure'] = canvas
        
        # Use existing CanvasWidget logic
        self.canvas_widget.add_canvas_to_window(plot_info, position)

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
            for tid in range(self.mask_dock.tab_widgets.count()):
                match self.mask_dock.tab_widgets.tabText(tid).lower():
                    case 'filters':
                        self.mask_tab.update({'filter': tid})
                    case 'polygons':
                        self.mask_tab.update({'polygon': tid})
                    case 'clusters':
                        self.mask_tab.update({'cluster': tid})

            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.mask_dock)
            self.mask_dock.setFloating(False)

            self.statusbar.toolButtonBottomDock.clicked.connect(lambda: self.toggle_dock_visibility(dock=self.mask_dock, button=self.toolButtonBottomDock))

            if self.mask_dock not in self.help_mapping:
                self.help_mapping[self.mask_dock] = 'filtering'

            self.mask_dock.filter_tab.callback_edit_filter_min()
            self.mask_dock.filter_tab.callback_edit_filter_max()

        self.mask_dock.show()
        
        # Apply current theme to the newly created MaskDock
        self._force_widget_style_refresh(self.mask_dock)

        if tab_name is not None:
            self.mask_dock.tab_widgets.setCurrentIndex(self.mask_tab[tab_name])


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
                notes_file = self.app_data.selected_directory / f"{self.app_data.sample_id}.rst"
            else:
                notes_file = None

            self.notes_dock = NotesDock(self, filename=notes_file)
            info_menu_items = [
                ('Sample info', lambda: self.insert_info_note('sample info')),
                ('List analytes used', lambda: self.insert_info_note('analytes')),
                ('Current plot details', lambda: self.insert_info_note('plot info')),
                ('Filter table', lambda: self.insert_info_note('filters')),
                ('PCA results', lambda: self.insert_info_note('pca results')),
                ('Cluster results', lambda: self.insert_info_note('cluster results'))
            ]
            self.notes_dock.notes.info_menu_items = info_menu_items

            self.notes_dock.notes.update_equation_menu()

            if self.notes_dock not in self.help_mapping:
                self.help_mapping[self.notes_dock] = 'notes'

        self.notes_dock.show()
        #self.notes_dock.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

    def insert_info_note(self, infotype):
        data = self.app_data.current_data

        match infotype:
            case 'sample info':
                text = f'**Sample ID: {self.app_data.sample_id}**\n'
                text += '*' * (len(self.app_data.sample_id) + 15) + '\n'
                text += f'\n:Date: {datetime.today().strftime("%Y-%m-%d")}\n'
                text += ':User: Your name here\n\n'
                self.notes_dock.notes.print_info(text)
            case 'analytes':
                analytes = data.processed.match_attribute('data_type', 'Analyte')
                ratios = data.processed.match_attribute('data_type', 'Ratio')
                text = ''
                if analytes:
                    text += ':analytes collected: '+', '.join(analytes)
                    text += '\n'
                if ratios:
                    text += ':ratios computed: '+', '.join(ratios)
                    text += '\n'
                text += '\n'
                self.notes_dock.notes.print_info(text)
            case 'plot info':
                if self.plot_info:
                    text = ['\n\n:plot type: '+self.plot_info['plot_type'],
                            ':plot name: '+self.plot_info['plot_name']+'\n']
                    text = '\n'.join(text)
                    self.notes_dock.notes.print_info(text)
            case 'filters':
                rst_table = self.notes_dock.notes.to_rst_table(data.filter_df)

                self.notes_dock.notes.print_info(rst_table)
            case 'pca results':
                if not self.pca_results:
                    return

                # Retrieve analytes matching specified attributes
                analytes = data.processed.match_attributes({'data_type': 'Analyte', 'use': True})
                analytes = np.insert(analytes, 0, 'lambda')  # Insert 'lambda' at the start of the analytes array

                # Calculate explained variance in percentage
                explained_variance = self.pca_results.explained_variance_ratio_ * 100

                # Retrieve PCA score headers matching the attribute condition
                header = data.processed.match_attributes({'data_type': 'PCA score'})

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
            calc_file = APPDATA_PATH / "calculator.txt"
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
            logfile = BASEDIR / 'resources' / 'log' / 'lame.log'
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
            if hasattr(self, 'workflow'):
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
        for analyte in self.app_data.current_data.processed.match_attribute('data_type','Analyte'):
            if analyte in analyte_dict:
                self.app_data.current_data.processed.set_attribute(analyte, 'use', True)
            else:
                self.app_data.current_data.processed.set_attribute(analyte, 'use', False)

        for analyte, norm in analyte_dict.items():
            if '/' in analyte:
                if analyte not in self.app_data.current_data.processed.columns:
                    analyte_1, analyte_2 = analyte.split(' / ') 
                    self.app_data.current_data.compute_ratio(analyte_1, analyte_2)

            self.app_data.current_data.processed.set_attribute(analyte,'norm',norm)

        self.plot_tree.update_tree(norm_update=True)

        if self.control_dock.tab_dict['dim_red'] == self.control_dock.toolbox.currentIndex() or self.control_dock.tab_dict['cluster'] == self.control_dock.toolbox.currentIndex():
            self.schedule_update()

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
            if hasattr(self, 'workflow'):
                self.workflow.refresh_custom_fields_lists_dropdown() #refresh saved analyte dropdown in blockly 
        if result == QDialog.DialogCode.Rejected:
            pass