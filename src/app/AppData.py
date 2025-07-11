import os, copy
import numpy as np
import pandas as pd
import random
import src.common.csvdict as csvdict
from src.app.config import BASEDIR
from src.common.Observable import Observable
from src.common.Logger import LoggerConfig, auto_log_methods, log

@auto_log_methods(logger_key='Data')
class AppData(Observable):
    def __init__(self, data):
        super().__init__()

        self.logger_key = 'Data'

        self.default_preferences = {'Units':{'Concentration': 'ppm', 'Distance': 'µm', 'Temperature':'°C', 'Pressure':'MPa', 'Date':'Ma', 'FontSize':11, 'TickDir':'out'}}

        # options for scaling data
        self.scale_options = ['linear', 'log', 'symlog']

        # in future will be set from preference ui
        self.preferences = copy.deepcopy(self.default_preferences)
        self.selected_directory = ''

        self._sort_method = 'mass'

        # reference chemistry
        self.ref_data = pd.read_excel(os.path.join(BASEDIR,'resources/app_data/earthref.xlsx'))
        self.ref_data = self.ref_data[self.ref_data['sigma']!=1]
        self.ref_list = self.ref_data['layer']+' ['+self.ref_data['model']+'] '+ self.ref_data['reference']
        self._ref_index = 0

        self._sample_list = []
        self.csv_files = []

        # a dictionary of sample_id containing SampleObj data class
        self.data = data

        # a dictionary of the field_types in self.data[sample_id].processed_data.  "coord" is excluded.
        self._field_dict = {}

        self._ndim_list = []

        self._sample_id = ""

        self._x_field_type = ""
        self._y_field_type = ""
        self._z_field_type = ""
        self._c_field_type = ""

        self._x_field = ""
        self._y_field = ""
        self._z_field = ""
        self._c_field = ""

        self.plot_info = {}

        self.outlier_methods = ['none', 'quantile critera','quantile and distance critera', 'Chauvenet criterion', 'log(n>x) inflection']
        self.negative_methods = ['ignore negatives', 'minimum positive', 'gradual shift', 'Yeo-Johnson transform']
        # histogram related data and methods
        self._equalize_color_scale = False

        self._default_hist_num_bins = 100
        self._hist_bin_width = 0
        self._hist_num_bins = 100
        self._hist_plot_style = "PDF"
        self.update_bin_width = True
        self.update_num_bins = True
        self._corr_method = "none"
        self._corr_squared = False

        self._noise_red_method = 'none'
        self.noise_red_options = {
            'none':{},
            'median':{'option1_min':1, 'option1_max':5, 'option1_step':2, 'option1':3},
            'wiener':{'option1_min':1, 'option1_max':199, 'option1_step':2, 'option1':30},
            'gaussian':{'option1_min':1, 'option1_max':199, 'option1_step':2, 'option1':30},
            'edge-preserving':{'option1_min':0, 'option1_max':200, 'option1_step':5, 'option1':30, 'option2_min':0, 'option2_max':1, 'option2_step':0.1, 'option2':0.1},
            'bilateral':{'option1_min':0, 'option1_max':200, 'option1_step':5, 'option1':30, 'option2_min':0, 'option2_max':200, 'option2_step':5.0, 'option2':75.0}
        }
        if 'option1' in self.noise_red_options[self._noise_red_method].keys():
            self._noise_red_option1 = self.noise_red_options[self._noise_red_method]['option1']
        else:
            self._noise_red_option1 = 0
        if 'option2' in self.noise_red_options[self._noise_red_method].keys():
            self._noise_red_option2 = self.noise_red_options[self._noise_red_method]['option2']
        else:
            self._noise_red_option2 = 0.0

        self._apply_noise_red = "No"
        self._gradient_flag = False
        self._edge_detection_method = "zero cross"

        self._scatter_preset = ""
        self._heatmap_style = "counts"
        self._ternary_colormap = ""
        self._ternary_color_x = ""
        self._ternary_color_y = ""
        self._ternary_color_z = ""
        self._ternary_color_m = ""

        self._norm_reference = ""

        # get N-Dim lists
        self.ndim_list_filename = 'resources/app_data/TEC_presets.csv'
        try:
            self.ndim_list_dict = csvdict.import_csv_to_dict(os.path.join(BASEDIR,self.ndim_list_filename))
        except:
            self.ndim_list_dict = {
                    'majors': ['Si','Ti','Al','Fe','Mn','Mg','Ca','Na','K','P'],
                    'full trace': ['Cs','Rb','Ba','Th','U','K','Nb','Ta','La','Ce','Pb','Mo','Pr','Sr','P','Ga','Zr','Hf','Nd','Sm','Eu','Li','Ti','Gd','Dy','Ho','Y','Er','Yb','Lu'],
                    'REE': ['La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu'],
                    'metals': ['Na','Al','Ca','Zn','Sc','Cu','Fe','Mn','V','Co','Mg','Ni','Cr'],
                }
        if 'REE' in self.ndim_list_dict.keys():
            self._ndim_analyte_set = 'REE'
        else:
            self._ndim_analyte_set = list(self.ndim_list_dict.keys())[0]

        self.ndim_analyte_df = pd.DataFrame(columns=['use', 'Analyte'])

        self._ndim_analyte_set = self.ndim_list_dict[next(iter(self.ndim_list_dict))]
        self.ndim_quantiles = {
            0: [0.5],
            1: [0.25, 0.75],
            2: [0.25, 0.5, 0.75],
            3: [0.05, 0.25, 0.5, 0.75, 0.95]
        }
        self._ndim_quantile_index = 2
        
        self._dim_red_method = "PCA: Principal component analysis (PCA)"
        self._dim_red_x = 0
        self._dim_red_y = 0
        self._dim_red_x_min = 1 # should not change
        self._dim_red_x_max = 2 # should change based on the number of fields used to compute basis
        self._dim_red_y_min = 1 # should not change
        self._dim_red_y_max = 2 # should change based on the number of fields used to compute basis

        self._cluster_method = "k-means"
        self.cluster_dict = {
            'k-means':{'n_clusters':5, 'seed':23, 'selected_clusters':[]},
            'fuzzy c-means':{'n_clusters':5, 'exponent':2.1, 'distance':'euclidean', 'seed':23, 'selected_clusters':[]}
        }
        self._max_clusters = 10
        self._num_clusters = self.cluster_dict[self._cluster_method]['n_clusters']
        if 'distance' in self.cluster_dict[self._cluster_method].keys():
            self._cluster_distance = self.cluster_dict[self._cluster_method]['distance']
        else:
            self._cluster_distance = None
        if 'exponent' in self.cluster_dict[self._cluster_method].keys():
            self._cluster_exponent = self.cluster_dict[self._cluster_method]['exponent']
        else:
            self._cluster_exponent = 0
        self._cluster_seed = self.cluster_dict[self._cluster_method]['seed']
        self._selected_clusters = self.cluster_dict[self._cluster_method]['selected_clusters']
        self._dim_red_precondition = False
        self._num_basis_for_precondition = 0

        self.update_cluster_flag = False
        self.updating_cluster_table_flag = False
        self.update_pca_flag = False
        
        self.axis = ['x','y','z','c']

    def get_field(self, ax):
        return getattr(self, f"{self.axis[ax]}_field")

    def set_field(self, ax, value):
        setattr(self, f"{self.axis[ax]}_field", value)

    def get_field_type(self, ax):
        return getattr(self, f"{self.axis[ax]}_field_type")

    def set_field_type(self, ax, value):
        setattr(self, f"{self.axis[ax]}_field_type", value)

    def validate_field_type(self, new_field_type):
        if self.sample_id == "":
            return False
        data_types = self.data[self.sample_id].processed_data.get_attribute_dict('data_type')
        if new_field_type in data_types:
            return True
        else:
            ValueError("Field type not found.")

    def validate_field(self, field_type, new_field):
        return True
    
    #     field_list = self.get_field_list(set_name=field_type)
    #     if new_field in field_list:
    #         return true
    #     else:
    #         valueerror("field not found.")
    @property
    def sort_method(self):
        return self._sort_method
    
    @sort_method.setter
    def sort_method(self, new_method):
        if new_method == self._sort_method:
            return

        self._sort_method = new_method
        self.notify_observers("sort_method", new_method)

    @property
    def ref_index(self):
        """Index into reference chemistry database"""
        return self._ref_index
    
    @ref_index.setter
    def ref_index(self, new_index):
        if new_index == self._ref_index:
            return

        self._ref_index = new_index
        self.notify_observers("ref_index", new_index)

    @property
    def ref_chem(self):
        chem = self.ref_data.iloc[self._ref_index]
        chem.index = [col.replace('_ppm', '') for col in chem.index]

        return chem

    @property
    def sample_list(self):
        return self._sample_list

    @sample_list.setter
    def sample_list(self, new_list):
        if new_list == self._sample_list:
            return
        
        # update sample list and id of current sample
        self._sample_list = new_list
        self._sample_id = new_list[0]

        # notify observers to update widgets
        self.notify_observers("sample_list", new_list)
        self.notify_observers("sample_id", self._sample_id)

    @property
    def sample_id(self):
        return self._sample_id
    
    @sample_id.setter
    def sample_id(self, new_id):
        if new_id == self._sample_id:
            return

        self._sample_id = new_id
        self.notify_observers("sample_id", new_id)

    ### Histogram Properties ###
    @property
    def equalize_color_scale(self):
        return self._equalize_color_scale
    
    @equalize_color_scale.setter
    def equalize_color_scale(self, flag):
        if flag == self._equalize_color_scale:
            return
    
        self._equalize_color_scale = flag
        self.notify_observers("equalize_color_scale", flag)

    @property
    def default_hist_num_bins(self):
        """Default bin width for histograms."""
        return self._default_hist_num_bins


    @property
    def hist_bin_width(self):
        return self._hist_bin_width
    
    @hist_bin_width.setter
    def hist_bin_width(self, width):
        if width == self._hist_bin_width:
            return

        self._hist_bin_width = width
        self.notify_observers("hist_bin_width", width)

        # update hist_num_bins
        if self.update_num_bins:
            self.update_bin_width = False
            self.update_hist_num_bins()
            self.update_bin_width = True


    @property
    def hist_num_bins(self):
        return self._hist_num_bins
    
    @hist_num_bins.setter
    def hist_num_bins(self, num_bins):
        if num_bins == self._hist_num_bins:
            return
        
        self._hist_num_bins = num_bins
        self.notify_observers("hist_num_bins", num_bins)

        # update hist_bin_width
        if self.update_bin_width:
            self.update_num_bins = False
            self.update_hist_bin_width()
            self.update_num_bins = True
    

    @property
    def hist_plot_style(self):
        return self._hist_plot_style
    
    @hist_plot_style.setter
    def hist_plot_style(self, hist_style):
        if hist_style == self._hist_plot_style:
            return
        elif hist_style not in ['PDF','CDF','log-scaling']:
            ValueError("Unknown histogram plot style")

        self._hist_plot_style = hist_style
        self.notify_observers("hist_plot_style", hist_style)

    @property
    def corr_method(self):
        return self._corr_method
    
    @corr_method.setter
    def corr_method(self, method):
        if method == self._corr_method:
            return
        elif method not in ['none', 'Pearson', 'Spearman', 'Kendall']:
            ValueError("Unknow correlation plot type")
    
        self._corr_method = method
        self.notify_observers("corr_method", method)

    @property
    def corr_squared(self):
        return self._corr_squared
    
    @corr_squared.setter
    def corr_squared(self, flag):
        if flag == self._corr_squared:
            return
    
        self._corr_squared = flag
        self.notify_observers("@corr_squared", flag)

    @property
    def noise_red_method(self):
        return self._noise_red_method
    
    @noise_red_method.setter
    def noise_red_method(self, method):
        if method == self._noise_red_method:
            return
    
        self._noise_red_method = method
        self.notify_observers("noise_red_method", method)

    @property
    def noise_red_option1(self):
        return self._noise_red_option1
    
    @noise_red_option1.setter
    def noise_red_option1(self, value):
        if value == self._noise_red_option1:
            return
    
        self._noise_red_option1 = value
        self.notify_observers("noise_red_option1", value)

    @property
    def noise_red_option2(self):
        return self._noise_red_option2
    
    @noise_red_option2.setter
    def noise_red_option2(self, value):
        if value == self._noise_red_option2:
            return
    
        self._noise_red_option2 = value
        self.notify_observers("noise_red_option2", value)

    @property
    def apply_noise_red(self):
        return self._apply_noise_red
    
    @apply_noise_red.setter
    def apply_noise_red(self, flag):
        if flag == self._apply_noise_red:
            return
    
        self._apply_noise_red = flag
        self.notify_observers("apply_noise_red", flag)
    
    @property
    def gradient_flag(self):
        return self._gradient_flag
    
    @gradient_flag.setter
    def gradient_flag(self, flag):
        if flag == self._gradient_flag:
            return
    
        self._gradient_flag = flag
        self.notify_observers("gradient_flag", flag)

    @property
    def edge_detection_method(self):
        return self._edge_detection_method

    @edge_detection_method.setter
    def edge_detection_method(self, method):
        if method == self._edge_detection_method:
            return
        
        self._edge_detection_method = method
    
    ### Scatter Properties ###
    @property
    def x_field_type(self):
        """str: Plot type used to determine plot method and associated style settings."""
        return self._x_field_type

    @x_field_type.setter
    def x_field_type(self, new_field_type):
        if new_field_type != self._x_field_type:
            self.validate_field_type(new_field_type)
            self._x_field_type = new_field_type
            self.notify_observers("field_type", 0, new_field_type)

    @property
    def y_field_type(self):
        """str: Plot type used to determine plot method and associated style settings."""
        return self._y_field_type

    @y_field_type.setter
    def y_field_type(self, new_field_type):
        if new_field_type != self._y_field_type:
            self.validate_field_type(new_field_type)
            self._y_field_type = new_field_type
            self.notify_observers("field_type", 1, new_field_type)

    @property
    def z_field_type(self):
        """str: Plot type used to determine plot method and associated style settings."""
        return self._z_field_type

    @z_field_type.setter
    def z_field_type(self, new_field_type):
        if new_field_type != self._z_field_type:
            self.validate_field_type(new_field_type)
            self._z_field_type = new_field_type
            self.notify_observers("field_type", 2, new_field_type)

    @property
    def c_field_type(self):
        """(str) Field type associated with colors or a histrogram"""
        return self._c_field_type
    
    @c_field_type.setter
    def c_field_type(self, new_field_type):
        if new_field_type == self._c_field_type:
            return

        # update c_field_type
        #self.validate_field_type(new_field_type)
        self._c_field_type = new_field_type
        self.notify_observers("field_type", 3, new_field_type)

        # update c_field
        if new_field_type in ['', 'none', 'None']:
            self.c_field = ''
        else:
            self.c_field = self.field_dict[new_field_type][0]


    @property
    def x_field(self):
        return self._x_field
    
    @x_field.setter
    def x_field(self, new_field):
        if new_field == self._x_field:
            return
    
        self._x_field = new_field
        self.notify_observers("field", 0, new_field)
    
    @property
    def y_field(self):
        return self._y_field
    
    @y_field.setter
    def y_field(self, new_field):
        if new_field == self._y_field:
            return
    
        self._y_field = new_field
        self.notify_observers("field", 1, new_field)
    
    @property
    def z_field(self):
        return self._z_field
    
    @z_field.setter
    def z_field(self, new_field):
        if new_field == self._z_field:
            return
    
        self._z_field = new_field
        self.notify_observers("field", 2, new_field)

    @property
    def c_field(self):
        """(str) Field associated with colors or a histrogram"""
        return self._c_field

    @c_field.setter
    def c_field(self, new_field):
        if new_field == self._c_field:
            return

        #self.validate_field(self._c_field_type, new_field)
        self._c_field = new_field
        self.notify_observers("field", 3, new_field)

    @property
    def scatter_preset(self):
        return self._scatter_preset
    
    @scatter_preset.setter
    def scatter_preset(self, new_scatter_preset):
        if new_scatter_preset == self._scatter_preset:
            return
    
        self._scatter_preset = new_scatter_preset
        self.notify_observers("scatter_preset", new_scatter_preset)

    ### Heatmap Properties ###
    @property
    def heatmap_style(self):
        return self._heatmap_style
    
    @heatmap_style.setter
    def heatmap_style(self, new_style):
        if new_style == self._heatmap_style:
            return
    
        self._heatmap_style = new_style
        self.notify_observers("heatmap_style", new_style)

    ### Ternary Map ###
    @property
    def ternary_colormap(self):
        return self._ternary_colormap
    
    @ternary_colormap.setter
    def ternary_colormap(self, new_cmap):
        if new_cmap == self._ternary_colormap:
            return
    
        self._ternary_colormap = new_cmap
        self.notify_observers("ternary_colormap", new_cmap)


    @property
    def ternary_color_x(self):
        return self._ternary_color_x
    
    @ternary_color_x.setter
    def ternary_color_x(self, new_color):
        if new_color == self._ternary_color_x:
            return
    
        self._ternary_color_x = new_color
        self.notify_observers("ternary_color_x", new_color)

    @property
    def ternary_color_y(self):
        return self._ternary_color_y
    
    @ternary_color_y.setter
    def ternary_color_y(self, new_color):
        if new_color == self._ternary_color_y:
            return
    
        self._ternary_color_y = new_color
        self.notify_observers("ternary_color_y", new_color)

    @property
    def ternary_color_z(self):
        return self._ternary_color_z
    
    @ternary_color_z.setter
    def ternary_color_z(self, new_color):
        if new_color == self._ternary_color_z:
            return
    
        self._ternary_color_z = new_color
        self.notify_observers("ternary_color_z", new_color)

    @property
    def ternary_color_m(self):
        return self._ternary_color_m
    
    @ternary_color_m.setter
    def ternary_color_m(self, new_color):
        if new_color == self._ternary_color_m:
            return
    
        self._ternary_color_m = new_color
        self.notify_observers("ternary_color_m", new_color)

    ### Multidimensional Properties ###
    @property
    def norm_reference(self):
        return self._norm_reference
    
    @norm_reference.setter
    def norm_reference(self, new_ref):
        if new_ref == self._norm_reference:
            return
    
        self._norm_reference = new_ref
        self.notify_observers("norm_reference", new_ref)

    @property
    def ndim_analyte_set(self):
        return self._ndim_analyte_set
    
    @ndim_analyte_set.setter
    def ndim_analyte_set(self, new_list):
        if new_list == self._ndim_analyte_set:
            return
        elif new_list not in self.ndim_list_dict.keys():
            ValueError(f"N Dim list ({new_list}) is not a defined option.")
    
        self._ndim_analyte_set = new_list
        self.notify_observers("ndim_analyte_set", new_list) 

    @property
    def ndim_list(self):
        return self._ndim_list

    @ndim_list.setter
    def ndim_list(self, new_list):
        self._ndim_list = new_list
        self.notify_observers("ndim_list", new_list)

    @property
    def ndim_quantile_index(self):
        return self._ndim_quantile_index
    
    @ndim_quantile_index.setter
    def ndim_quantile_index(self, new_index):
        if new_index == self._ndim_quantile_index:
            return
    
        self._ndim_quantile_index = new_index
        self.notify_observers("ndim_quantile_index", new_index)



    ### Dimensional Reduction Properties ###
    @property
    def dim_red_method(self):
        return self._dim_red_method
    
    @dim_red_method.setter
    def dim_red_method(self, method):
        if method == self._dim_red_method:
            return
    
        self._dim_red_method = method
        self.notify_observers("dim_red_method", method)

    @property
    def dim_red_x(self):
        return self._dim_red_x
    
    @dim_red_x.setter
    def dim_red_x(self, new_dim_red_x):
        if new_dim_red_x == self._dim_red_x:
            return
    
        self._dim_red_x = new_dim_red_x
        self.notify_observers("dim_red_x", new_dim_red_x)

    @property
    def dim_red_x_min(self):
        return self._dim_red_x_min

    @property
    def dim_red_x_max(self):
        return self._dim_red_x_max

    @dim_red_x_max.setter
    def dim_red_x_max(self, new_max):
        if new_max == self._dim_red_x_max:
            return
        self._dim_red_x_max = new_max
        self.notify_observers("dim_red_x_max", new_max)

    @property
    def dim_red_y(self):
        return self._dim_red_y
    
    @property
    def dim_red_y_min(self):
        return self._dim_red_y_min

    @dim_red_y_min.setter
    def dim_red_y_min(self, new_min):
        if new_min == self._dim_red_y_min:
            return
        self._dim_red_y_min = new_min
        self.notify_observers("dim_red_y_min", new_min)

    @property
    def dim_red_y_max(self):
        return self._dim_red_x_max

    @dim_red_y_max.setter
    def dim_red_y_max(self, new_max):
        if new_max == self._dim_red_x_max:
            return
        self._dim_red_x_max = new_max
        self.notify_observers("dim_red_y_max", new_max)



    ### Cluster Properties ###
    @property
    def cluster_method_options(self):
        """Returns a list of available clustering methods."""
        return list(self.cluster_dict.keys())

    @property
    def cluster_method(self):
        return self._cluster_method
    
    @cluster_method.setter
    def cluster_method(self, method):
        if method == self._cluster_method:
            return
        elif method not in self.cluster_method_options:
            ValueError(f"Unknown cluster type ({method})")

        self._cluster_method = method
        self._set_clustering_parameters()
        self.notify_observers("cluster_method", method)

    @property
    def max_clusters(self):
        """The maximum number of clusters to test when producing estimates of the optimal number of clusters"""
        return self._max_clusters
    
    @max_clusters.setter
    def max_clusters(self, new_value):
        if new_value == self._max_clusters:
            return
    
        self._max_clusters = new_value
        self.notify_observers("max_clusters", new_value)

    @property
    def num_clusters(self):
        """The number of clusters used to classify the data"""
        return self._num_clusters
    
    @num_clusters.setter
    def num_clusters(self, new_value):
        if new_value == self._num_clusters:
            return
    
        self._num_clusters = new_value
        # update cluster dict with new number of clusters
        self.cluster_dict[self._cluster_method]['n_clusters'] = self._num_clusters
        self.notify_observers("num_clusters", new_value)

    @property
    def cluster_seed(self):
        return self._cluster_seed
    
    @cluster_seed.setter
    def cluster_seed(self, new_value):
        if new_value == self._cluster_seed:
            return
    
        self._cluster_seed = new_value
        # update cluster dict with new seed
        self.cluster_dict[self._cluster_method]['seed'] = self._cluster_seed
        self.notify_observers("cluster_seed", new_value)

    @property
    def cluster_exponent(self):
        return self._cluster_exponent
    
    @cluster_exponent.setter
    def cluster_exponent(self, new_value):
        if new_value == self._cluster_exponent:
            return
    
        self._cluster_exponent = new_value
        # update cluster dict with new cluster exponent value
        self.cluster_dict[self._cluster_method]['exponent'] = self._cluster_exponent
        self.notify_observers("cluster_exponent", new_value)

    @property
    def cluster_distance(self):
        return self._cluster_distance
    
    @cluster_distance.setter
    def cluster_distance(self, new_value):
        if new_value == self._cluster_distance:
            return
    
        self._cluster_distance = new_value
        # update cluster dict with new cluster distance method
        self.cluster_dict[self._cluster_method]['distance'] = self._cluster_distance
        self.notify_observers("cluster_distance", new_value)

    @property
    def selected_clusters(self):
        return self._selected_clusters
    
    @selected_clusters.setter
    def selected_clusters(self, new_list):
        if new_list == self._selected_clusters:
            return
    
        self._selected_clusters = new_list
        self.notify_observers("selected_clusters", new_list)

    @property
    def dim_red_precondition(self):
        return self._dim_red_precondition
    
    @dim_red_precondition.setter
    def dim_red_precondition(self, flag):
        if flag == self._dim_red_precondition:
            return
    
        self._dim_red_precondition = flag
        self.notify_observers("dim_red_precondition", flag)

    @property
    def num_basis_for_precondition(self):
        return self._num_basis_for_precondition
    
    @num_basis_for_precondition.setter
    def num_basis_for_precondition(self, new_value):
        if new_value == self._num_basis_for_precondition:
            return
    
        self._num_basis_for_precondition = new_value
        self.notify_observers("num_basis_for_precondition", new_value)

    @property
    def field_dict(self):
        """A dictionary of the field_types in the self.data[sample_id].processed_data dataframe, with "coord" excluded."""
        self._field_dict = self.data[self.sample_id].processed_data.get_attribute_dict('data_type')
        if 'coordinate' in self._field_dict:
            self._field_dict.pop("coordinate")
        return self._field_dict

    @property
    def selected_analytes(self):
        """Gets the list of selected analytes for use in analyses."""
        if self.data and self.sample_id != '':
            return self.data[self.sample_id].processed_data.match_attributes({'data_type': 'Analyte', 'use': True})

        return None

    def get_field_list(self, set_name='Analyte', filter='all'):
        """Gets the fields associated with a defined set

        Set names are consistent with QComboBox.

        Parameters
        ----------
        set_name : str, optional
            name of set list, options include ``Analyte``, ``Analyte (normalized)``, ``Ratio``, ``Calcualated Field``,
            ``PCA Score``, ``Cluster``, ``Cluster Score``, ``Special``, Defaults to ``Analyte``
        filter : str, optional
            Optionally filters data to columns selected for analysis, options are ``'all'`` and ``'used'``,
            by default `'all'`

        Returns
        -------
        list
            Set_fields, a list of fields within the input set
        """
        if self.sample_id == '':
            return ['']

        data = self.data[self.sample_id].processed_data

        if filter not in ['all', 'used']:
            raise ValueError("filter must be 'all' or 'used'.")

        set_fields = []
        match set_name:
            case 'Analyte' | 'Analyte (normalized)':
                if filter == 'used':
                    set_fields = data.match_attributes({'data_type': 'Analyte', 'use': True})
                else:
                    set_fields = data.match_attribute('data_type', 'Analyte')
            case 'Ratio' | 'Ratio (normalized)':
                if filter == 'used':
                    set_fields = data.match_attributes({'data_type': 'Ratio', 'use': True})
                else:
                    set_fields = data.match_attribute('data_type', 'Ratio')
            case 'None':
                return []
            case _:
                set_fields = data.match_attribute('data_type', set_name)

        return set_fields

    def update_hist_bin_width(self):
        """Updates the bin width

        Generally called when the number of bins is changed by the user.  Updates the plot.
        """
        if (self.c_field_type == '') or (self.c_field == ''):
            return

        # get currently selected data
        map_df = self.data[self.sample_id].get_map_data(self._c_field, self._c_field_type)

        # update bin width
        range = np.nanmax(map_df['array']) - np.nanmin(map_df['array'])
        self.hist_bin_widt = range / self._hist_num_bins

    def update_hist_num_bins(self):
        """Updates the number of bins

        Generally called when the bin width is changed by the user.  Updates the plot.
        """
        if (self.c_field_type == '') or (self.c_field == ''):
            return

        # get currently selected data
        map_df = self.data[self.sample_id].get_map_data(self._c_field, self._c_field_type)

        # update n bins
        range = np.nanmax(map_df['array']) - np.nanmin(map_df['array'])
        self.hist_num_bins = int( range / self._hist_bin_width)

    def histogram_reset_bins(self):
        """Resets number of histogram bins to default"""
        self.hist_num_bins = self.default_hist_num_bins

    def _set_clustering_parameters(self):
        """Sets clustering parameters

        Generally called when the clustering method is changed by the user.  Updates the plot.
        """
        if 'distance' in self.cluster_dict[self._cluster_method].keys():
            self.cluster_distance = self.cluster_dict[self._cluster_method]['distance']
        if 'exponent' in self.cluster_dict[self._cluster_method].keys():
            self.cluster_exponent = self.cluster_dict[self._cluster_method]['exponent']

    def generate_random_seed(self):
        """Generates a random seed for clustering

        Updates ``self.cluster_seed using a random number generator with one of 10**9 integers. 
        """        
        r = random.randint(0,1000000000)
        self.cluster_seed = r
        

    def cluster_group_changed(self,data, plot_style):
        """
        Updates the cluster dictionary and selected cluster groups.

        This method checks if the current clustering method is available in
        ``data.processed_data[method]``. If found, it retrieves and sorts
        the unique cluster labels, assigns colors using ``plot_style``,
        and updates the internal dictionary (``self.cluster_dict``) with
        each cluster’s information. If a mask cluster (label 99) exists,
        it is separately handled and assigned the last color.

        Parameters
        ----------
        data : object
            The data container with processed cluster information stored in
            ``data.processed_data[method]``.
        plot_style : object
            An object or utility providing default cluster color assignments.
        """
        if self.sample_id == '':
            return
        method =self.cluster_method
        if method in data.processed_data.columns:
            if not data.processed_data[method].empty:
                clusters = data.processed_data[method].dropna().unique()
                clusters.sort()

                self.cluster_dict[method]['selected_clusters'] = []
                try:
                   self.cluster_dict[method].pop(str(99))
                except:
                    pass

                i = 0
                while True:
                    try:
                        self.cluster_dict[method].pop(str(i))
                        i += 1
                    except:
                        break

                if 99 in clusters:
                    hexcolor = plot_style.set_default_cluster_colors(mask=True,n = len(clusters)-1)
                else:
                    hexcolor = plot_style.set_default_cluster_colors(mask=False, n = len(clusters))

                for c in clusters:
                    c = int(c)
                    if c == 99:
                        cluster_name = 'Mask'
                        self.cluster_dict[method].update({c: {'name':cluster_name, 'link':[], 'color':hexcolor[-1]}})
                        break
                    else:
                        cluster_name = f'Cluster {c+1}'

                    
                    self.cluster_dict[method].update({c: {'name':cluster_name, 'link':[], 'color':hexcolor[c]}})

                if 99 in clusters:
                   self.cluster_dict[method]['selected_clusters'] = clusters[:-1]
                else:
                   self.cluster_dict[method]['selected_clusters'] = clusters
        else:
            print(f'(group_changed) Cluster method, ({method}) is not defined')

    