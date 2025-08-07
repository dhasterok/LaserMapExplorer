import sys, os, re, copy, random, darkdetect
import numpy as np
import pandas as pd
pd.options.mode.copy_on_write = True
import matplotlib
matplotlib.use('Qt5Agg')
from PyQt6.QtWidgets import QWidget, QDialog
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
from src.common.LamePlot import plot_map_mpl, plot_small_histogram, plot_histogram, plot_correlation, get_scatter_data, plot_scatter, plot_ternary_map, plot_ndim, plot_pca, plot_clusters, cluster_performance_plot
from src.app.FieldLogic import AnalyteDialog, FieldDialog
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
from src.app.SpecialTools import SpecialFunctions as specfun
from src.common.reSTNotes import NotesDock
from src.common.Browser import Browser
from src.app.config import BASEDIR, ICONPATH, SSPATH, load_stylesheet
from src.common.ExtendedDF import AttributeDataFrame
import src.common.format as fmt
from src.common.colorfunc import get_hex_color, get_rgb_color
import src.app.config as config
from src.app.help_mapping import create_help_mapping
from src.common.Logger import LoggerDock
from src.app.AppData import AppData
import os
import json

class LameBlockly(PlotViewer):
    def __init__(self,parent, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
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
        #Initialize nested data which will hold the main sets of data for analysis
        self.data = {}
        self.lasermaps = {}
        self.outlier_method = 'none'
        self.negative_method = 'ignore negatives'
        self.calc_dict = {}
        self.csv_files = []
        self.laser_map_dict = {}
        self.persistent_filters = pd.DataFrame()
        self.persistent_filters = pd.DataFrame(columns=['use', 'field_type', 'field', 'norm', 'min', 'max', 'operator', 'persistent'])
        self.plot_type = 'field map'
        self.field_type_list = ['Analyte', 'Analyte (normalized)']

        self.app_data = AppData(self.data)

        self.blockly  = parent.web_view.page() # This is the QWebEngineView that displays the Blockly interface
        self.statusLabel = parent.statusLabel
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
        
        self.plot_style = StyleData(self)
        #set style using 'default' style them
        self.style_themes = StyleTheme(self)
        self.plot_style.style_dict = self.style_themes.default_style_dict()
        
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
        self.ref_data = pd.read_excel(os.path.join(BASEDIR,'resources/app_data/earthref.xlsx'))
        self.ref_data = self.ref_data[self.ref_data['sigma']!=1]
        self.ref_list = self.ref_data['layer']+' ['+self.ref_data['model']+'] '+ self.ref_data['reference']

        self.ref_chem = None

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

        self.analyte_dialog = AnalyteDialog(self)
        self.analyte_dialog.show()

        result = self.analyte_dialog.exec()  # Store the result here
        if result == QDialog.DialogCode.Accepted:
            self.update_analyte_ratio_selection(analyte_dict= self.analyte_dialog.norm_dict)   
            
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

        self.field_selection_dialog = FieldDialog(self)
        self.field_selection_dialog.show()

        result = self.field_selection_dialog.exec()  # Store the result here
        if result == QDialog.DialogCode.Accepted:
            self.selected_fields =  self.field_selection_dialog.selected_fields
            
        if result == QDialog.DialogCode.Rejected:
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


    


    # -------------------------------------
    # laser map functions and plotting
    # -------------------------------------
    # def plot_map_mpl(self, sample_id, field_type, field):
    #     """Create a matplotlib canvas for plotting a map

    #     Create a map using ``mplc.MplCanvas``.

    #     Parameters
    #     ----------
    #     sample_id : str
    #         Sample identifier
    #     field_type : str
    #         Type of field for plotting
    #     field : str
    #         Field for plotting
    #     """        
    #     # create plot canvas
    #     canvas = mplc.MplCanvas(parent=self, ui= self.plot_viewer)

    #     # set color limits
    #     if field not in self.data[self.app_data.sample_id].axis_dict:
    #         self.plot_style.initialize_axis_values(field_type,field)
    #         self.plot_style.set_style_dictionary()

    #     # get data for current map
    #     #scale = self.data[self.app_data.sample_id].processed_data.get_attribute(field, 'norm')
    #     scale = self.plot_style.cscale
    #     map_df = self.data[self.app_data.sample_id].get_map_data(field, field_type)

    #     array_size = self.data[self.app_data.sample_id].array_size
    #     aspect_ratio = self.data[self.app_data.sample_id].aspect_ratio

    #     # store map_df to save_data if data needs to be exported
    #     self.save_data = map_df.copy()

    #     # # equalized color bins to CDF function
    #     # if self.toolButtonScaleEqualize.isChecked():
    #     #     sorted_data = map_df['array'].sort_values()
    #     #     cum_sum = sorted_data.cumsum()
    #     #     cdf = cum_sum / cum_sum.iloc[-1]
    #     #     map_df.loc[sorted_data.index, 'array'] = cdf.values

    #     # plot map
    #     reshaped_array = np.reshape(map_df['array'].values, array_size, order=self.data[self.app_data.sample_id].order)
            
    #     norm = self.plot_style.color_norm()

    #     cax = canvas.axes.imshow(reshaped_array, cmap=self.plot_style.get_colormap(),  aspect=aspect_ratio, interpolation='none', norm=norm)

    #     self.add_colorbar(canvas, cax)
    #     match self.plot_style.cscale:
    #         case 'linear':
    #             clim = self.plot_style.clim
    #         case 'log':
    #             clim = self.plot_style.clim
    #             #clim = np.log10(self.plot_style.clim)
    #         case 'logit':  
    #             print('Color limits for logit are not currently implemented')

    #     cax.set_clim(clim[0], clim[1])

    #     # use mask to create an alpha layer
    #     mask = self.data[self.app_data.sample_id].mask.astype(float)
    #     reshaped_mask = np.reshape(mask, array_size, order=self.data[self.app_data.sample_id].order)

    #     alphas = colors.Normalize(0, 1, clip=False)(reshaped_mask)
    #     alphas = np.clip(alphas, .4, 1)

    #     alpha_mask = np.where(reshaped_mask == 0, 0.5, 0)  
    #     canvas.axes.imshow(np.ones_like(alpha_mask), aspect=aspect_ratio, interpolation='none', cmap='Greys', alpha=alpha_mask)
    #     canvas.array = reshaped_array

    #     canvas.axes.tick_params(direction=None,
    #         labelbottom=False, labeltop=False, labelright=False, labelleft=False,
    #         bottom=False, top=False, left=False, right=False)

    #     canvas.set_initial_extent()


        
    #     # add scalebar
    #     self.add_scalebar(canvas.axes)

    #     canvas.fig.tight_layout()

    #     self.plot_info = {
    #         'tree': field_type,
    #         'sample_id': sample_id,
    #         'plot_name': field,
    #         'plot_type': 'field map',
    #         'field_type': field_type,
    #         'field': field,
    #         'figure': canvas,
    #         'style': self.plot_style.style_dict[self.plot_style.plot_type],
    #         'cluster_groups': None,
    #         'view': [True,False],
    #         'position': None
    #         }
        
    #     self.plot_viewer.add_plotwidget_to_plot_viewer(self.plot_info)


    # -------------------------------------
    # Histogram functions and plotting
    # -------------------------------------
    def histogram_get_range(self, field_type, field, hist_type, n_bins):
        """Updates the bin width

        Generally called when the number of bins is changed by the user.  Updates the plot.
        """

        if (field_type == '') or (field == ''):
            return

        self.plot_style.plot_type = 'histogram'
        self.app_data.x_field =field
        self.app_data.x_field_type =field_type
        self.app_data.hist_plot_style = hist_type
        self.app_data.hist_num_bins = n_bins
        plot_histogram(parent=self, data=self.data[self.app_data.sample_id], app_data=self.app_data, plot_style=self.plot_style)
        # update bin width
        range = (self.plot_style.xlim[1] - self.plot_style.xlim[0]) 

        return  range



    def histogram_update_n_bins(self,field,field_type):
        """Updates the number of bins

        Generally called when the bin width is changed by the user.  Updates the plot.
        """
        if not self.update_bins:
            return
        #print('update_n_bins')
        self.update_bins = False

        # get currently selected data
        map_df = self.data[self.app_data.sample_id].get_map_data(field, field_type)

        # update n bins
        self.spinBoxBinWidth.setValue( int((np.nanmax(map_df['array']) - np.nanmin(map_df['array'])) / self.spinBoxBinWidth.value()) )
        self.update_bins = True

        # update histogram
        if self.plot_type == 'histogram':
            # trigger update to plot
            self.plot_style.schedule_update()

    # -------------------------------
    # Blockly functions
    # -------------------------------
    # gets the set of fields types
    def update_blockly_field_types(self,workflow = None):
        """Gets the fields types available and invokes workflow function
          which updates field type dropdown in blockly workflow

        Set names are consistent with QComboBox.
        """
        
        data_type_dict = self.data[self.app_data.sample_id].processed_data.get_attribute_dict('data_type')
        # add check for ratios
        if 'ratio' in data_type_dict:
            self.field_type_list.append('Ratio')
            self.field_type_list.append('Ratio (normalized)')

        if 'pca score' in data_type_dict:
            self.field_type_list.append('PCA score')

        if 'cluster' in data_type_dict:
            self.field_type_list.append('Cluster')

        if 'cluster score' in data_type_dict:
            self.field_type_list.append('Cluster score')

        if hasattr(self,'field_selection_dialog'):
            self.field_selection_dialog.update_field_type_list() 
        
        if workflow:
            workflow.update_field_type_list(self.field_type_list) #invoke workflow function to update blockly 'fieldType' dropdowns

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
        filepath = os.path.join(BASEDIR, 'resources/analytes_list', filename+'.txt')
        analyte_dict ={}
        with open(filepath, 'r') as f:
            for line in f.readlines():
                field, norm = line.replace('\n','').split(',')
                analyte_dict[field] = norm

        self.update_analyte_ratio_selection(analyte_dict)


    def update_field_list_from_file(self,filename):
        filepath = os.path.join(BASEDIR, 'resources/fields_list', filename+'.txt')
        field_dict ={}
        with open(filepath, 'r') as f:
            for line in f.readlines():
                field, field_type = line.replace('\n','').split('||')
                field_dict[field_type] = field

        print(field_dict)

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
        if self.app_data.sample_id == '':
            return ['']

        data = self.data[self.app_data.sample_id].processed_data

        match set_name:
            case 'Analyte' | 'Analyte (normalized)':
                set_fields = data.match_attributes({'data_type': 'Analyte', 'use': True})
            case 'Ratio' | 'Ratio (normalized)':
                set_fields = data.match_attributes({'data_type': 'Ratio', 'use': True})
            case 'None':
                return []
            case _:
                #populate field name with column names of corresponding dataframe remove 'X', 'Y' is it exists
                #set_fields = [col for col in self.data[self.app_data.sample_id]['computed_data'][set_name].columns.tolist() if col not in ['X', 'Y']]
                set_fields = data.match_attribute('data_type', set_name.lower())

        return set_fields


    def update_axis_limits(self,style_dict, field =None):
        # Check if user changed XLim, YLim, ZLim, or CLim
        if "XLim" in style_dict:
            lowerVal = style_dict["XLim"][0]
            upperVal = style_dict["XLim"][1]
            self.plot_style.axis_limit_edit_callback("x", 0, float(lowerVal), field = 'X', ui_update=False)
            self.plot_style.axis_limit_edit_callback("x", 1, float(upperVal), field = 'X', ui_update=False)

        if "YLim" in style_dict:
            lowerVal = style_dict["YLim"][0]
            upperVal = style_dict["YLim"][1]
            self.plot_style.axis_limit_edit_callback("y", 0, float(lowerVal), field = 'Y', ui_update=False)
            self.plot_style.axis_limit_edit_callback("y", 1, float(upperVal), field = 'Y', ui_update=False)

        if "ZLim" in style_dict:
            lowerVal = style_dict["ZLim"][0]
            upperVal = style_dict["ZLim"][1]
            self.plot_style.axis_limit_edit_callback("z", 0, float(lowerVal), ui_update=False)
            self.plot_style.axis_limit_edit_callback("z", 1, float(upperVal), ui_update=False)

        if "CLim" in style_dict:
            lowerVal = style_dict["CLim"][0]
            upperVal = style_dict["CLim"][1]
            self.plot_style.axis_limit_edit_callback("c", 0, float(lowerVal), field, ui_update=False)
            self.plot_style.axis_limit_edit_callback("c", 1, float(upperVal), field, ui_update=False)

    
    
    def get_saved_lists(self,type):
        """
        Retrieves the names of saved analyte lists from the resources/analytes list directory.

        Returns
        -------
        list
            List of saved analyte list names.
        """
        path =''
        if type =='Analyte':
            path = 'resources/analytes_list'
        elif type =='field':
             path = 'resources/fields_list'
        directory = os.path.join(BASEDIR, path)
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