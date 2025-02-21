import sys, os, re, copy, random, darkdetect
import numpy as np
import pandas as pd
pd.options.mode.copy_on_write = True
import matplotlib
matplotlib.use('Qt5Agg')
from PyQt6.QtWidgets import QWidget, QDialog
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
        self.csv_files = []
        self.laser_map_dict = {}
        self.persistent_filters = pd.DataFrame()
        self.persistent_filters = pd.DataFrame(columns=['use', 'field_type', 'field', 'norm', 'min', 'max', 'operator', 'persistent'])
        self.plot_type = 'analyte map'
        self.field_type_list = ['Analyte', 'Analyte (normalized)']

        self.app_data = AppData(self.data)

        # Plot Selector
        #-------------------------
        self.sort_method = 'mass'

        self.plot_info = {}

         # preferences
        self.default_preferences = {'Units':{'Concentration': 'ppm', 'Distance': 'µm', 'Temperature':'°C', 'Pressure':'MPa', 'Date':'Ma', 'FontSize':11, 'TickDir':'out'}}
        self.preferences = copy.deepcopy(self.default_preferences)

        self.io = LameIO(self, connect_actions=False)

        self.plot_style = Styling(self)
        
        # Initialise plotviewer form
        self.plot_viewer = PlotViewer(self)
        self.update_bins = False

        self.showMass = False
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
        self.cluster_dict = {
            'active method' : 'k-means',
            'k-means':{'n_clusters':5, 'seed':23, 'selected_clusters':[]},
            'fuzzy c-means':{'n_clusters':5, 'exponent':2.1, 'distance':'euclidean', 'seed':23, 'selected_clusters':[]}
        }

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
            file_path = os.path.join(self.app_data.selected_directory, self.csv_files[index])
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
        if self.sample_id == '':
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
    # Histogram functions and plotting
    # -------------------------------------
    def histogram_get_range(self, field_type, field):
        """Updates the bin width

        Generally called when the number of bins is changed by the user.  Updates the plot.
        """

        if (field_type == '') or (field == ''):
            return

        # get currently selected data
        current_plot_df = self.data[self.sample_id].get_map_data(field, field_type)

        # update bin width
        range = (np.nanmax(current_plot_df['array']) - np.nanmin(current_plot_df['array']))

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
        map_df = self.data[self.sample_id].get_map_data(field, field_type)

        # update n bins
        self.spinBoxBinWidth.setValue( int((np.nanmax(map_df['array']) - np.nanmin(map_df['array'])) / self.spinBoxBinWidth.value()) )
        self.update_bins = True

        # update histogram
        if self.plot_type == 'histogram':
            # trigger update to plot
            self.plot_style.schedule_update()

    def plot_histogram(self, hist_type, field_type, field, n_bins):
        """Plots a histogramn in the canvas window"""
        plot_data = None
        #print('plot histogram')
        # create Mpl canvas
        canvas = mplc.MplCanvas(parent=self, ui= self.plot_viewer)

        #if field_type == 'Ratio':
        #    analyte_1 = field.split(' / ')[0]
        #    analyte_2 = field.split(' / ')[1]

        if hist_type == 'log-scaling' and field_type == 'Analyte':
            print('raw_data for log-scaling')
            x = self.get_scatter_data(plot_type='histogram', processed=False, field_type=field_type,field = field)['x']
        else:
            print('processed_data for histogram')
            x = self.get_scatter_data(plot_type='histogram', processed=True, field_type=field_type,field = field)['x']

        # determine edges
        xmin,xmax,xscale,xlbl = self.plot_style.get_axis_values(x['type'],x['field'])
        self.plot_style.xlim = [xmin, xmax]
        self.plot_style.xscale = xscale
        #if xscale == 'log':
        #    x['array'] = np.log10(x['array'])
        #    xmin = np.log10(xmin)
        #    xmax = np.log10(xmax)

        #bin_width = (xmax - xmin) / n_bins
        #print(n_bins)
        #print(bin_width)
        
        if (xscale == 'linear') or (xscale == 'scientific'):
            edges = np.linspace(xmin, xmax, n_bins)
        else:
            edges = np.linspace(10**xmin, 10**xmax, n_bins)

        #print(edges)

        # histogram style
        lw = self.plot_style.line_width
        if lw > 0:
            htype = 'step'
        else:
            htype = 'bar'

        # CDF or PDF
        match hist_type:
            case 'CDF':
                cumflag = True
            case _:
                cumflag = False

        # Check if the algorithm is in the current group and if results are available
        if field_type == 'cluster' and field != '':
            method = self.cluster_dict['active method']

            # Get the cluster labels for the data
            cluster_color, cluster_label, _ = self.plot_style.get_cluster_colormap(self.cluster_dict[method],alpha=self.plot_style.marker_alpha)
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

                if hist_type != 'log-scaling' :
                    plot_data = canvas.axes.hist( cluster_data,
                            cumulative=cumflag,
                            histtype=htype,
                            bins=edges,
                            color=bar_color, edgecolor=ecolor,
                            linewidth=lw,
                            label=cluster_label[int(i)],
                            alpha=self.plot_style.marker_alpha/100,
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
            self.add_colorbar(canvas, None, cbartype='discrete', grouplabels=cluster_label, groupcolors=cluster_color, alpha=self.plot_style.marker_alpha/100)
            #canvas.axes.legend()
        else:
            clusters = None
            # Regular histogram
            bar_color = self.plot_style.marker_color
            if htype == 'step':
                ecolor = self.plot_style.line_color
            else:
                ecolor = None

            if hist_type != 'log-scaling' :
                plot_data = canvas.axes.hist( x['array'],
                        cumulative=cumflag,
                        histtype=htype,
                        bins=edges,
                        color=bar_color, edgecolor=ecolor,
                        linewidth=lw,
                        alpha=self.plot_style.marker_alpha/100,
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
                canvas.axes.plot(sorted_data, counts, color=bar_color, lw=lw, alpha=self.plot_style.marker_alpha/100)

        # axes
        # label font
        if 'font' == '':
            font = {'size':self.plot_style.font}
        else:
            font = {'font':self.plot_style.font, 'size':self.plot_style.font_size}

        # set y-limits as p-axis min and max in self.data[self.sample_id].axis_dict
        if hist_type != 'log-scaling' :
            pflag = False
            if 'pstatus' not in self.data[self.sample_id].axis_dict[x['field']]:
                pflag = True
            elif self.data[self.sample_id].axis_dict[x['field']]['pstatus'] == 'auto':
                pflag = True

            if pflag:
                ymin, ymax = canvas.axes.get_ylim()
                d = {'pstatus':'auto', 'pmin':fmt.oround(ymin,order=2,toward=0), 'pmax':fmt.oround(ymax,order=2,toward=1)}
                self.data[self.sample_id].axis_dict[x['field']].update(d)
                # self.plot_style.set_axis_widgets('y', x['field'])

            # grab probablility axes limits
            _, _, _, _, ymin, ymax = self.plot_style.get_axis_values(x['type'],x['field'],ax='p')

            # x-axis
            canvas.axes.set_xlabel(xlbl, fontdict=font)
            if xscale == 'log':
            #    self.logax(canvas.axes, [xmin,xmax], axis='x', label=xlbl)
                canvas.axes.set_xscale(xscale,base=10)
            # if self.plot_style.xscale == 'linear':
            # else:
            #     canvas.axes.set_xlim(xmin,xmax)
            canvas.axes.set_xlim(xmin,xmax)

            if xscale == 'scientific':
                canvas.axes.ticklabel_format(axis='x', style='sci', scilimits=(0,0))

            # y-axis
            canvas.axes.set_ylabel(hist_type, fontdict=font)
            canvas.axes.set_ylim(ymin,ymax)
        else:
            canvas.axes.set_xscale('log',base=10)
            canvas.axes.set_yscale('log',base=10)

            canvas.axes.set_xlabel(r"$\log_{10}($" + f"{field}" + r"$)$", fontdict=font)
            canvas.axes.set_ylabel(r"$\log_{10}(N > \log_{10}$" + f"{field}" + r"$)$", fontdict=font)

        canvas.axes.tick_params(labelsize=self.plot_style.font_size,direction=self.plot_style.tick_dir)
        canvas.axes.set_box_aspect(self.plot_style.aspect_ratio)

        self.plot_style.update_figure_font(canvas, self.plot_style.font)

        canvas.fig.tight_layout()

        self.plot_info = {
            'tree': 'Histogram',
            'sample_id': self.sample_id,
            'plot_name': field_type+'_'+field,
            'field_type': field_type,
            'field': field,
            'plot_type': 'histogram',
            'type': hist_type,
            'n_bins': n_bins,
            'figure': canvas,
            'style': self.plot_style.style_dict[self.plot_style.plot_type],
            'cluster_groups': clusters,
            'view': [True,False],
            'position': [],
            'data': plot_data
        }

        self.plot_viewer.add_plotwidget_to_plot_viewer(self.plot_info)

    def plot_correlation(self, corr_method, squared = False,field_type = None, field = None):
        """Creates an image of the correlation matrix"""
        #print('plot_correlation')

        canvas = mplc.MplCanvas(parent=self, ui= self.plot_viewer)
        canvas.axes.clear()

        # get the data for computing correlations
        df_filtered, analytes = self.data[self.sample_id].get_processed_data()

        # Calculate the correlation matrix
        method = corr_method.lower()
        if not field_type:
            correlation_matrix = df_filtered.corr(method=method)
        else:
            algorithm = field
            cluster_group = self.data[self.sample_id].processed_data.loc[:,algorithm]
            selected_clusters = self.cluster_dict[algorithm]['selected_clusters']

            ind = np.isin(cluster_group, selected_clusters)

            correlation_matrix = df_filtered[ind].corr(method=method)
        
        columns = correlation_matrix.columns

        font = {'size':self.plot_style.font_size}

        # mask lower triangular matrix to show only upper triangle
        mask = np.zeros_like(correlation_matrix, dtype=bool)
        mask[np.tril_indices_from(mask)] = True
        correlation_matrix = np.ma.masked_where(mask, correlation_matrix)

        norm = self.plot_style.color_norm()

        # plot correlation or correlation^2
        square_flag = squared
        if square_flag:
            cax = canvas.axes.imshow(correlation_matrix**2, cmap=self.plot_style.get_colormap(), norm=norm)
            canvas.array = correlation_matrix**2
        else:
            cax = canvas.axes.imshow(correlation_matrix, cmap=self.plot_style.get_colormap(), norm=norm)
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
        cax.set_clim(self.plot_style.clim[0], self.plot_style.clim[1])

        # Set tick labels
        ticks = np.arange(len(columns))
        canvas.axes.tick_params(length=0, labelsize=8,
                        labelbottom=False, labeltop=True, labelleft=False, labelright=True,
                        bottom=False, top=True, left=False, right=True)

        canvas.axes.set_yticks(ticks, minor=False)
        canvas.axes.set_xticks(ticks, minor=False)

        labels = self.plot_style.toggle_mass(columns)

        canvas.axes.set_xticklabels(labels, rotation=90, ha='center', va='bottom', fontproperties=font)
        canvas.axes.set_yticklabels(labels, ha='left', va='center', fontproperties=font)

        canvas.axes.set_title('')

        self.plot_style.update_figure_font(canvas, self.plot_style.font)

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
            'style': self.plot_style.style_dict[self.plot_style.plot_type],
            'cluster_groups': [],
            'view': [True,False],
            'position': [],
            'data': correlation_matrix,
        }

        self.plot_viewer.add_plotwidget_to_plot_viewer(self.plot_info)

    # -------------------------------------
    # Scatter/Heatmap functions
    # -------------------------------------
    def get_scatter_data(self, plot_type,field_type=None, field= None, processed=True, field_type_x= None, field_type_y=None, field_type_z=None, field_x=None, field_y= None, field_z= None, color_by_field =None):

        scatter_dict = {'x': {'type': None, 'field': None, 'label': None, 'array': None},
                'y': {'type': None, 'field': None, 'label': None, 'array': None},
                'z': {'type': None, 'field': None, 'label': None, 'array': None},
                'c': {'type': None, 'field': None, 'label': None, 'array': None}}

        match plot_type:
            case 'histogram':
                if processed or field_type != 'Analyte':
                    scatter_dict['x'] = self.data[self.sample_id].get_vector(field_type, field, norm=self.plot_style.xscale)
                else:
                    scatter_dict['x'] = self.data[self.sample_id].get_vector(field_type, field, norm=self.plot_style.xscale, processed=False)
            case 'PCA scatter' | 'PCA heatmap':
                scatter_dict['x'] = self.data[self.sample_id].get_vector('PCA score', f'PC{self.spinBoxPCX.value()}', norm=self.plot_style.xscale)
                scatter_dict['y'] = self.data[self.sample_id].get_vector('PCA score', f'PC{self.spinBoxPCY.value()}', norm=self.plot_style.yscale)
                if (field_type is None) or (self.comboBoxColorByField.currentText != ''):
                    scatter_dict['c'] = self.data[self.sample_id].get_vector(field_type, field)
            case _:
                scatter_dict['x'] = self.data[self.sample_id].get_vector(field_type_x, field_x, norm=self.plot_style.xscale)
                scatter_dict['y'] = self.data[self.sample_id].get_vector(field_type_y, field_y, norm=self.plot_style.yscale)
                if (field_type is not None) and (field_type != ''):
                    scatter_dict['z'] = self.data[self.sample_id].get_vector(field_type_z, field_z, norm=self.plot_style.zscale)
                elif (field_z is not None) and (field_z != ''):
                    scatter_dict['c'] = self.data[self.sample_id].get_vector(field_type, field, norm=self.plot_style.cscale)

        # set axes widgets
        if (scatter_dict['x']['field'] is not None) and (scatter_dict['y']['field'] != ''):
            if scatter_dict['x']['field'] not in self.data[self.sample_id].axis_dict.keys():
                self.plot_style.initialize_axis_values(scatter_dict['x']['type'], scatter_dict['x']['field'])
                # self.plot_style.set_axis_widgets('x', scatter_dict['x']['field'])

        if (scatter_dict['y']['field'] is not None) and (scatter_dict['y']['field'] != ''):
            if scatter_dict['y']['field'] not in self.data[self.sample_id].axis_dict.keys():
                self.plot_style.initialize_axis_values(scatter_dict['y']['type'], scatter_dict['y']['field'])
                # self.plot_style.set_axis_widgets('y', scatter_dict['y']['field'])

        if (scatter_dict['z']['field'] is not None) and (scatter_dict['z']['field'] != ''):
            if scatter_dict['z']['field'] not in self.data[self.sample_id].axis_dict.keys():
                self.plot_style.initialize_axis_values(scatter_dict['z']['type'], scatter_dict['z']['field'])
                # self.plot_style.set_axis_widgets('z', scatter_dict['z']['field'])

        if (scatter_dict['c']['field'] is not None) and (scatter_dict['c']['field'] != ''):
            if scatter_dict['c']['field'] not in self.data[self.sample_id].axis_dict.keys():
                self.plot_style.set_color_axis_widgets()
                # self.plot_style.set_axis_widgets('c', scatter_dict['c']['field'])

        return scatter_dict

    
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

            # create for legend items
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

        data_type_dict = self.data[self.sample_id].processed_data.get_attribute_dict('data_type')

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

        # self.plot_style.toggle_style_widgets()

        # add None to list?
        if addNone:
            field_list.insert(0, 'None')

        # clear comboBox items
        comboBox.clear()
        # add new items
        comboBox.addItems(field_list)


    # -------------------------------
    # Blockly functions
    # -------------------------------
    # gets the set of fields types
    def update_blockly_field_types(self,workflow = None):
        """Gets the fields types available and invokes workflow function
          which updates field type dropdown in blockly workflow

        Set names are consistent with QComboBox.
        """
        
        data_type_dict = self.data[self.sample_id].processed_data.get_attribute_dict('data_type')
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
        filepath = os.path.join(self.BASEDIR, 'resources/analytes_list', filename+'.txt')
        analyte_dict ={}
        with open(filepath, 'r') as f:
            for line in f.readlines():
                field, norm = line.replace('\n','').split(',')
                analyte_dict[field] = norm

        self.update_analyte_ratio_selection(analyte_dict)


    def update_field_list_from_file(self,filename):
        filepath = os.path.join(self.BASEDIR, 'resources/fields_list', filename+'.txt')
        field_dict ={}
        with open(filepath, 'r') as f:
            for line in f.readlines():
                field, field_type = line.replace('\n','').split('||')
                field_dict[field_type] = field

        print(field_dict)

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
