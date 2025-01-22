import sys, os, re, copy, random, darkdetect
import numpy as np
import pandas as pd
pd.options.mode.copy_on_write = True
import matplotlib
matplotlib.use('Qt5Agg')
from PyQt5.QtWidgets import QWidget, QDialog
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
from src.common.ternary_plot import ternary
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
from src.app.PlotViewerWindow import PlotViewer
from src.app.Actions import Actions
from src.common.DataHandling import SampleObj
from src.app.PlotTree import PlotTree
from src.app.CropImage import CropTool
from src.app.ImageProcessing import ImageProcessing as ip
from src.app.StyleToolbox import Styling
from src.app.Profile import Profiling
from src.common.Polygon import PolygonManager
from src.common.Calculator import CustomFieldCalculator as cfc
from src.app.SpecialTools import SpecialFunctions as specfun
from src.common.NoteTaking import Notes
from src.common.Browser import Browser
import src.app.QuickView as QV
from src.app.config import BASEDIR, ICONPATH, SSPATH, DEBUG, load_stylesheet
from src.common.ExtendedDF import AttributeDataFrame
import src.common.format as fmt
from src.common.colorfunc import get_hex_color, get_rgb_color
import src.app.config as config
from src.app.help_mapping import create_help_mapping
from src.common.Logger import LoggerDock
import os



class Main():
    def __init__(self, *args, **kwargs):

        #Initialize nested data which will hold the main sets of data for analysis
        self.data = {}
        self.BASEDIR = BASEDIR
        self.sample_id = ''
        self.sample_ids =[]
        self.lasermaps = {}
        self.outlier_method = 'none'
        self.negative_method = 'ignore negatives'
        self.calc_dict = {}
        self.selected_directory = ''
        self.csv_files = []
        self.laser_map_dict = {}
        self.persistent_filters = pd.DataFrame()
        self.persistent_filters = pd.DataFrame(columns=['use', 'field_type', 'field', 'norm', 'min', 'max', 'operator', 'persistent'])
        self.plot_type = 'analyte map'
        # Plot Selector
        #-------------------------
        self.sort_method = 'mass'

        self.plot_info = {}

         # preferences
        self.default_preferences = {'Units':{'Concentration': 'ppm', 'Distance': 'µm', 'Temperature':'°C', 'Pressure':'MPa', 'Date':'Ma', 'FontSize':11, 'TickDir':'out'}}
        self.preferences = copy.deepcopy(self.default_preferences)

        self.io = LameIO(self, ui_update= False)

        self.plot_style = Styling(self, ui= False)
        
        # Initialise plotviewer form
        self.plot_viewer = PlotViewer(self)
        

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
        # # cluster dictionary
        # self.cluster_dict = {
        #     'active method' : 'k-means',
        #     'k-means':{'n_clusters':5, 'seed':23, 'selected_clusters':[]},
        #     'fuzzy c-means':{'n_clusters':5, 'exponent':2.1, 'distance':'euclidean', 'seed':23, 'selected_clusters':[]}
        # }

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
        if DEBUG:
            print(f"change_sample, index: {index}")

        if self.sample_id == self.sample_ids[index]:
            # if selected sample id is same as previous
            return
            
        self.sample_id = self.sample_ids[index]
        
        # self.notes.save_notes_file()
        # self.notes.autosaveTimer.stop()

        # # notes and autosave timer
        # self.notes_file = os.path.join(self.selected_directory,self.sample_id+'.rst')
        # # open notes file if it exists
        # if os.path.exists(self.notes_file):
        #     try:
        #         with open(self.notes_file,'r') as file:
        #             self.textEditNotes.setText(file.read())
        #     except:
        #         file_name = os.path.basename(self.notes_file)
        #         self.statusbar.showMessage(f'Cannot read {file_name}')
        #         pass
        # # put current notes into self.textEditNotes
        # self.notes.autosaveTimer.start()

        # add sample to sample dictionary
        if self.sample_id not in self.data:
            # load sample's *.lame file
            file_path = os.path.join(self.selected_directory, self.csv_files[index])
            self.data[self.sample_id] = SampleObj(self.sample_id, file_path, self.outlier_method, self.negative_method)

    # -------------------------------------
    # Reset to start
    # -------------------------------------
    def reset_analysis(self, selection='full'):
        if self.sample_id == '':
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
            self.sample_id = None

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
            self.update_analyte_ratio_selection(analyte_dict= self.analyte_dialog.norm_dict)   
            
        if result == QDialog.Rejected:
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
        for analyte in self.data[self.sample_id].processed_data.match_attribute('data_type','Analyte'):
            if analyte in list(analyte_dict.keys()):
                self.data[self.sample_id].processed_data.set_attribute(analyte, 'use', True)
            else:
                self.data[self.sample_id].processed_data.set_attribute(analyte, 'use', False)

        for analyte, norm in analyte_dict.items():
            if '/' in analyte:
                if analyte not in self.data[self.sample_id].processed_data.columns:
                    analyte_1, analyte_2 = analyte.split(' / ') 
                    self.data[self.sample_id].compute_ratio(analyte_1, analyte_2)

            self.data[self.sample_id].processed_data.set_attribute(analyte,'norm',norm)


    


    # -------------------------------------
    # laser map functions and plotting
    # -------------------------------------
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
        canvas = mplc.MplCanvas(parent=self, ui= self.plot_viewer)

        # set color limits
        if field not in self.data[self.sample_id].axis_dict:
            self.plot_style.initialize_axis_values(field_type,field)
            self.plot_style.set_style_dictionary()

        # get data for current map
        #scale = self.data[self.sample_id].processed_data.get_attribute(field, 'norm')
        scale = self.plot_style.cscale
        map_df = self.data[self.sample_id].get_map_data(field, field_type)

        array_size = self.data[self.sample_id].array_size
        aspect_ratio = self.data[self.sample_id].aspect_ratio

        # store map_df to save_data if data needs to be exported
        self.save_data = map_df.copy()

        # # equalized color bins to CDF function
        # if self.toolButtonScaleEqualize.isChecked():
        #     sorted_data = map_df['array'].sort_values()
        #     cum_sum = sorted_data.cumsum()
        #     cdf = cum_sum / cum_sum.iloc[-1]
        #     map_df.loc[sorted_data.index, 'array'] = cdf.values

        # plot map
        reshaped_array = np.reshape(map_df['array'].values, array_size, order=self.data[self.sample_id].order)
            
        norm = self.plot_style.color_norm()

        cax = canvas.axes.imshow(reshaped_array, cmap=self.plot_style.get_colormap(),  aspect=aspect_ratio, interpolation='none', norm=norm)

        self.add_colorbar(canvas, cax)
        match self.plot_style.cscale:
            case 'linear':
                clim = self.plot_style.clim
            case 'log':
                clim = self.plot_style.clim
                #clim = np.log10(self.plot_style.clim)
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

        # axes
        xmin, xmax, xscale, xlbl = self.plot_style.get_axis_values(None,field= 'X')
        ymin, ymax, yscale, ylbl = self.plot_style.get_axis_values(None,field= 'Y')


        # axes limits
        canvas.axes.set_xlim(xmin,xmax)
        canvas.axes.set_ylim(ymin,ymax)
        
        # add scalebar
        self.add_scalebar(canvas.axes)

        canvas.fig.tight_layout()

        self.plot_info = {
            'tree': field_type,
            'sample_id': sample_id,
            'plot_name': field,
            'plot_type': 'analyte map',
            'field_type': field_type,
            'field': field,
            'figure': canvas,
            'style': self.plot_style.style_dict[self.plot_style.plot_type],
            'cluster_groups': None,
            'view': [True,False],
            'position': None
            }
        
        self.plot_viewer.add_plotwidget_to_plot_viewer(self.plot_info)

    
    # -------------------------------------
    # General plot functions
    # -------------------------------------    
    

    def add_scalebar(self, ax):
        """Add a scalebar to a map

        Parameters
        ----------
        ax : 
            Axes to place scalebar on.
        """        
        # add scalebar
        direction = self.plot_style.scale_dir
        length = self.plot_style.scale_length
        if (length is not None) and (direction != 'none'):
            if direction == 'horizontal':
                dd = self.data[self.sample_id].dx
            else:
                dd = self.data[self.sample_id].dy
            sb = scalebar( width=length,
                    pixel_width=dd,
                    units=self.preferences['Units']['Distance'],
                    location=self.plot_style.scale_location,
                    orientation=direction,
                    color=self.plot_style.overlay_color,
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
                if self.plot_type == 'correlation':
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

    # -------------------------------
    # Blockly functions
    # -------------------------------
    # gets the set of fields types
    def update_blockly_field_types(self,workflow):
        """Gets the fields types available and invokes workflow function
          which updates field type dropdown in blockly workflow

        Set names are consistent with QComboBox.
        """

        field_type_list = ['Analyte', 'Analyte (normalized)']
        
        data_type_dict = self.data[self.sample_id].processed_data.get_attribute_dict('data_type')

        # add check for ratios
        if 'ratio' in data_type_dict:
            field_type_list.append('Ratio')
            field_type_list.append('Ratio (normalized)')

        if 'pca score' in data_type_dict:
            field_type_list.append('PCA score')

        if 'cluster' in data_type_dict:
            field_type_list.append('Cluster')

        if 'cluster score' in data_type_dict:
            field_type_list.append('Cluster score')
        
        workflow.update_field_type_list(field_type_list) #invoke workflow function to update blockly 'fieldType' dropdowns

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
        sample_id = self.sample_id
        # Apply to all analytes in sample
        columns = self.data[self.sample_id].processed_data.columns

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
