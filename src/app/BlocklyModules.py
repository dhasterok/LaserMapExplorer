from dataclasses import fields
import sys, os, re, copy, random, darkdetect
import numpy as np
import pandas as pd
pd.options.mode.copy_on_write = True
import matplotlib
matplotlib.use('Qt5Agg')
from PyQt6 import sip
from PyQt6.QtWidgets import QWidget, QDialog, QVBoxLayout
from PyQt6.QtCore import QObject, Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.gridspec as gs
from matplotlib.path import Path
from matplotlib.patches import Patch
import matplotlib.colors as colors
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
import cmcrameri as cmc
from scipy.stats import yeojohnson, percentileofscore
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import skfuzzy as fuzz
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from src.common.ternary_plot import ternary
from src.common.plot_spider import plot_spider_norm
from src.common.scalebar import scalebar
from src.app.LameIO import LameIO
import src.common.csvdict as csvdict
from src.common.LamePlot import create_plot, plot_map_mpl, plot_small_histogram, plot_histogram, plot_correlation, get_scatter_data, plot_scatter, plot_ternary_map, plot_ndim, plot_pca, plot_clusters, cluster_performance_plot, update_figure_font
from src.app.AnalyteDialog import AnalyteDialog
from src.app.FieldDialog import FieldDialog
from src.app.DataAnalysis import Clustering, DimensionalReduction
from src.common.TableFunctions import TableFcn as TableFcn
import src.common.CustomMplCanvas as mplc
from src.app.PlotViewerWindow import PlotViewer
from src.common.DataHandling import LaserSampleObj
from src.app.ImageProcessing import ImageProcessing as ip
from src.app.StyleToolbox import StyleData, StyleTheme
from src.app.Profile import Profiling
from src.common.Polygon import PolygonManager
from src.common.Calculator import CustomFieldCalculator as cfc
from src.common.reSTNotes import NotesDock
from src.common.Browser import Browser
from src.app.config import BASEDIR, ICONPATH, STYLE_PATH, load_stylesheet
from src.common.ExtendedDF import AttributeDataFrame
import src.common.format as fmt
# Removed unused imports: get_hex_color, get_rgb_color
import src.app.config as config
from src.app.help_mapping import create_help_mapping
from src.common.Logger import LoggerDock
from src.app.AppData import AppData
from src.common.Status import StatusMessageManager
import os
import json
from src.app.CanvasWidget import CanvasWidget, CanvasDialog

class LameBlockly(QObject):
    def __init__(self,parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        # setup initial logging options
        # self.logger = LogCounter()
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
                'UI': True
            }

        self.data = {}
        self.lasermaps = {}
        self.outlier_method = 'none'
        self.negative_method = 'ignore negatives'
        self.parent = parent
        self.calc_dict = {}
        self.csv_files = []
        self.laser_map_dict = {}
        self.persistent_filters = pd.DataFrame()
        self.persistent_filters = pd.DataFrame(columns=['use', 'field_type', 'field', 'norm', 'min', 'max', 'operator', 'persistent'])
        self.plot_type = 'field map'
        self.field_type_list = ['Analyte', 'Analyte (normalized)']

        self.app_data = AppData(self)

        self.blockly  = parent.web_view.page() # This is the QWebEngineView that displays the Blockly interface
        
        # set up status message manager
        self.statusLabel = parent.statusLabel
        self.status_manager = StatusMessageManager(self)
        # Plot Selector
        #-------------------------
        self.sort_method = 'mass'

        self.plot_info = {}

         # preferences
        self.default_preferences = {'Units':{'Concentration': 'ppm', 'Distance': 'µm', 'Temperature':'°C', 'Pressure':'MPa', 'Date':'Ma', 'FontSize':11, 'TickDir':'out'}}
        self.preferences = copy.deepcopy(self.default_preferences)
        # Workflow dock
        self.workflow_dock = parent
        self.io = LameIO(self, connect_actions=False)
        
        self.style_data = StyleData(self)
        
        # Create a popup dialog
        popup = QDialog(parent)
        popup.setWindowTitle("Plot Viewer")
        layout = QVBoxLayout(popup)

        # Pass popup as the parent to CanvasWidget
        self.canvas_widget = CanvasWidget(ui=self, parent=popup)
        layout.addWidget(self.canvas_widget)

        popup.setLayout(layout)
        self.display_figures = True  # show popup with controls & pause; False = embed and continue
        #popup.exec_()
        # # Initialise plotviewer form
        # self.plot_viewer = PlotViewer(self)
        self.update_bins = False

        self.showMass = False

        # Block ID
        self.block_id = None
        # # Noise reduction
        # self.noise_reduction = ip(self)

        # # Spot Data 
        # #-------------------------
        # self.spotdata = AttributeDataFrame()

        # # Filter
        # #-------------------------
        # self.load_filter_tables()

        # # Multidimensional
        # #------------------------
        # self.pca_results = []

        # # Clustering
        # #-------------------------
        # Initialise dimentionality reduction class 
        self.dimensional_reduction = DimensionalReduction()

        # Initialise class from DataAnalysis
        self.clustering = Clustering()


        # distance_metrics = ['euclidean', 'manhattan', 'mahalanobis', 'cosine']
        
        #         # Notes
        # #-------------------------
        # self.notes = Notes(self)

                # Select analyte Tab
        #-------------------------
        self.ref_selected = False

    def ensure_canvas_popup(self):
        """
        Ensure self.canvas_dialog exists and is valid.
        If it was deleted, recreate it.
        """
        dlg_exists = hasattr(self, "canvas_dialog") and self.canvas_dialog is not None
        if dlg_exists and sip.isdeleted(self.canvas_dialog):
            dlg_exists = False  # underlying C++ deleted

        if not dlg_exists:
            self.canvas_dialog = CanvasDialog(ui = self, parent=self.parent)
            self.canvas_widget = self.canvas_dialog.get_canvas()
            # Prevent Qt from auto-deleting when closed
            self.canvas_dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        
        self.canvas_dialog.raise_()
        self.canvas_dialog.activateWindow()


    def change_sample(self, index, save_analysis= True):
        """Changes sample and plots first map

        Parameters
        ----------
        index: int
            index of sample name for identifying data.
        """
        # if DEBUG:
        #     print(f"change_sample, index: {index}")

        if self.app_data.sample_id == self.app_data.sample_list[index]:
            # if selected sample id is same as previous
            return
            
        self.app_data.sample_id = self.app_data.sample_list[index]
        self.io.initialize_sample_object(self.outlier_method, self.negative_method)

    # -------------------------------------
    # Reset to start
    # -------------------------------------
    def reset_analysis(self, selection='full'):
        if self.app_data.sample_id == '':
            return



        if selection =='full':
            if self.data:
                #reset self.data
                self.data = {}
                self.multi_view_index = []
                self.laser_map_dict = {}
                self.multiview_info_label = {}
                self.ndim_list = []
                self.lasermaps = {}

                # make the first plot
                self.plot_flag = True
                # self.update_SV()
            # reset_sample id
            self.app_data.sample_id = None

    def open_select_analyte_dialog(self):
        """Opens Select Analyte dialog

        Opens a dialog to select analytes for analysis either graphically or in a table.  Selection updates the list of analytes, and ratios in plot selector and comboBoxes.
        
        .. seealso::
            :ref:`AnalyteSelectionWindow` for the dialog
        """
        if self.app_data.sample_id == '':
            return

        self.analyte_dialog = AnalyteDialog(self.parent, self.app_data.current_data, self.app_data)
        self.analyte_dialog.show()

        result = self.analyte_dialog.exec()  # Store the result here
        if result == QDialog.DialogCode.Accepted:
            self.app_data.update_field_selection(fields= self.analyte_dialog.norm_dict.keys(), norms=self.analyte_dialog.norm_dict.values())

        if result == QDialog.DialogCode.Rejected:
            pass
    
    def open_field_selector_dialog(self):
        """Opens Select Analyte dialog

        Opens a dialog to select analytes for analysis either graphically or in a table.  Selection updates the list of analytes, and ratios in plot selector and comboBoxes.
        
        .. seealso::
            :ref:`AnalyteSelectionWindow` for the dialog
        """
        if self.app_data.sample_id == '':
            return

        self.field_selection_dialog = FieldDialog(self.parent, self.app_data.current_data, self.app_data)
        self.field_selection_dialog.show()

        result = self.field_selection_dialog.exec()  # Store the result here
        if result == QDialog.DialogCode.Accepted:
            self.selected_fields =  self.field_selection_dialog.selected_field
            self.app_data.update_field_selection(fields=self.selected_fields)
        if result == QDialog.DialogCode.Rejected:
            pass



    # -------------------------------------
    # Histogram functions and plotting
    # -------------------------------------
    def histogram_get_range(self, field_type, field, hist_type, n_bins):
        """Updates the bin width

        Generally called when the number of bins is changed by the user.  Updates the plot.
        """

        if (field_type == '') or (field == ''):
            return

        self.style_data.plot_type = 'histogram'
        self.app_data.x_field =field
        self.app_data.y_field =field
        self.app_data.c_field =field
        self.app_data.x_field_type =field_type
        self.app_data.y_field_type =field_type
        self.app_data.c_field_type =field_type
        self.app_data.hist_plot_style = hist_type
        self.app_data.hist_num_bins = n_bins
        plot_histogram(parent=self, data=self.data[self.app_data.sample_id], app_data=self.app_data, style_data=self.style_data)
        # update bin width
        range = (self.style_data.xlim[1] - self.style_data.xlim[0]) 

        return  range


    # -------------------------------
    # Blockly functions
    # -------------------------------

    def update_analyte_selection_from_file(self,filename):
        filepath = os.path.join(BASEDIR, 'resources/analytes_list', filename+'.txt')
        analyte_dict ={}
        with open(filepath, 'r') as f:
            for line in f.readlines():
                field, norm = line.replace('\n','').split(',')
                analyte_dict[field] = norm

        self.app_data.update_field_selection(fields=analyte_dict.keys(), norms=analyte_dict.values())


    def load_fields_from_saved_list(self, list_name: str):
        """Return a list of fields given a saved list name (used by Blockly)."""
        filepath = os.path.join(BASEDIR, 'resources/fields_list', f"{list_name}.txt")
        fields = []
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) == 2:
                    _, field = parts
                    fields.append(field)
        return fields

    def update_bounds(self,ub=None,lb=None,d_ub=None,d_lb=None):
        sample_id = self.app_data.sample_id
        # Apply to all analytes in sample
        columns = self.data[self.app_data.sample_id].processed.columns

        # update column attributes
        if (lb and ub):
            self.data[sample_id].set_attribute(columns, 'upper_bound', ub)
            self.data[sample_id].set_attribute(columns, 'lower_bound', lb)
        else:
            self.data[sample_id].set_attribute(columns, 'diff_upper_bound', d_ub)
            self.data[sample_id].set_attribute(columns, 'diff_lower_bound', d_lb)

        # update data with new auto-scale/negative handling

    def update_axis_limits(self,style_dict, field =None):
        # Check if user changed XLim, YLim, ZLim, or CLim
        if "XLim" in style_dict:
            lowerVal = style_dict["XLim"][0]
            upperVal = style_dict["XLim"][1]
            self.style_data.axis_limit_edit_callback("x", 0, float(lowerVal), field = 'X', ui_update=False)
            self.style_data.axis_limit_edit_callback("x", 1, float(upperVal), field = 'X', ui_update=False)

        if "YLim" in style_dict:
            lowerVal = style_dict["YLim"][0]
            upperVal = style_dict["YLim"][1]
            self.style_data.axis_limit_edit_callback("y", 0, float(lowerVal), field = 'Y', ui_update=False)
            self.style_data.axis_limit_edit_callback("y", 1, float(upperVal), field = 'Y', ui_update=False)

        if "ZLim" in style_dict:
            lowerVal = style_dict["ZLim"][0]
            upperVal = style_dict["ZLim"][1]
            self.style_data.axis_limit_edit_callback("z", 0, float(lowerVal), ui_update=False)
            self.style_data.axis_limit_edit_callback("z", 1, float(upperVal), ui_update=False)

        if "CLim" in style_dict:
            lowerVal = style_dict["CLim"][0]
            upperVal = style_dict["CLim"][1]
            self.style_data.axis_limit_edit_callback("c", 0, float(lowerVal), field, ui_update=False)
            self.style_data.axis_limit_edit_callback("c", 1, float(upperVal), field, ui_update=False)

    
    
    def get_saved_lists(self,type):
        """
        Retrieves the names of saved analyte lists from the resources/analytes list directory.

        Returns
        -------
        list
            List of saved analyte list names.
        """
        path =''
        if type =='analyte':
            path = 'resources/analytes_list'
        elif type =='field':
             path = 'resources/fields_list'
        elif type =='TEC':
             path = 'resources/TEC_list'
        directory = BASEDIR / path
        list_names = [str(f).replace('.txt', '') for f in os.listdir(directory) if f.endswith('.txt')]
        return list_names
    

    def execute_code(self,output_text_edit,code=None):
        if not code:
            # Get the code from the output_text_edit and execute it
            code = output_text_edit.toPlainText()

        print(code)
        exec(code)

    ### Blockly functions ##
    def store_sample_ids(self):
        """
        Sends sample_ids to JavaScript to update the sample_ids list and refresh dropdowns.
        """
        # Convert the sample_ids list to a format that JavaScript can use (a JSON array)
        sample_ids_js_array = str(self.app_data.sample_list)
        self.blockly.runJavaScript(f"updateSampleDropdown({sample_ids_js_array})")

    def update_field_type_list(self, field_type_list):
        # Convert the field type list to JSON
        field_type_list_json = json.dumps(field_type_list)
        # Send the field type list to JavaScript
        self.blockly.runJavaScript(f"updateFieldTypeList({field_type_list_json})")
    


    def refresh_saved_lists_dropdown(self, type):
            """
            Calls the JavaScript function to refresh the analyteSavedListsDropdown in Blockly.
            """
            self.blockly.runJavaScript("refreshListsDropdown({type});")

    def update_styles(self):
        """
        Calls the JavaScript function to update the style widgets in Blockly.
        """
        if self.block_id:
            self.blockly.runJavaScript(
                f"updateStylingChain(workspace.getBlockById('{self.block_id}'))"
            )

    def refresh_all_field_type_dropdowns(self):
        """
        Calls the JavaScript function to refresh all field type dropdowns in Blockly workspace.
        """

        self.blockly.runJavaScript(f"refreshAllFieldTypeDropdowns(Blockly.getMainWorkspace())")

    def add_canvas_to_layout(self, canvas):
        """
        Adds the given canvas to the layout of the canvas widget.
        """
        if not self.canvas_widget or not hasattr(self.canvas_widget, "single_view"):
            print("Warning: canvas_widget or single_view not available")
            return

        if sip.isdeleted(self.canvas_widget.single_view):
            print("Warning: single_view was deleted, recreating...")
            self.canvas_widget.create_single_view()  # <-- you'll need to re-instantiate
            return

        if canvas:
            layout = self.canvas_widget.single_view.layout()
            if layout is not None:
                self.canvas_widget.clear_layout(layout)
                layout.addWidget(canvas)
            else:
                print("Warning: single_view.layout() is None")
            self.mpl_canvas = canvas


    def set_display_policy(self, canvas):
        """
        Sets the display policy for the canvas based on user preference.
        If display_figures is True, it shows a popup dialog with controls.
        Otherwise, it embeds the canvas directly into the layout.
        """
        if getattr(self, 'display_figures', True):
            # Popup dialog with controls; block until user picks an action
            self.ensure_canvas_popup()
            self.mpl_canvas = canvas
            self.canvas_widget.add_canvas_to_window(self.plot_info)
            self.canvas_dialog.show()
            user_action = self.canvas_widget.show_controls_and_exec(self.canvas_dialog)
            if user_action == 'stop':
                raise RuntimeError("Workflow stopped by user.")
            elif user_action == 'skip':
                # downstream save handlers should respect this flag
                if isinstance(self.plot_info, dict):
                    self.plot_info['skip_save'] = True
        else:
            # No popup; just embed and continue
            self.add_canvas_to_layout(canvas)