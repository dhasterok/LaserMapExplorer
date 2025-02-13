import copy
import numpy as np
import pandas as pd
import src.common.csvdict as csvdict

from src.common.Observable import Observable

class AppData(Observable):
    def __init__(self):
        super().__init__()
        self.default_preferences = {'Units':{'Concentration': 'ppm', 'Distance': 'µm', 'Temperature':'°C', 'Pressure':'MPa', 'Date':'Ma', 'FontSize':11, 'TickDir':'out'}}
        # in future will be set from preference ui
        self.preferences = copy.deepcopy(self.default_preferences)

        self._sample_list = []
        self.csv_files = []

        self.data = {}
        self._sample_id = ""

        self.plot_info = {}

        # histogram related data and methods
        self._hist_field_type = ""
        self._hist_field = ""
        self._hist_bin_width = 0
        self._hist_num_bins = 100
        self._hist_plot_style = "PDF"
        self.update_bin_width = True
        self.update_num_bins = True
        self._corr_plot_style = "none"
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

        self._x_field_type = ""
        self._y_field_type = ""
        self._z_field_type = ""
        self._c_field_type = ""

        self._x_field = ""
        self._y_field = ""
        self._z_field = ""
        self._c_field = ""

        self._scatter_preset = ""
        self._heatmap_style = "counts"
        self._ternary_colormap = ""
        self._ternary_color_x = ""
        self._ternary_color_y = ""
        self._ternary_color_z = ""

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
            self._ndim_analyte_set = self.ndim_list_dict.keys(0)

        self.ndim_analyte_df = pd.DataFrame(columns=['use', 'analyte'])

        self._ndim_analyte_set = self.ndim_list_dict[next(iter(self.ndim_list_dict))]
        self.ndim_quantiles = {
            0: [0.5],
            1: [0.25, 0.75],
            2: [0.25, 0.5, 0.75],
            3: [0.05, 0.25, 0.5, 0.75, 0.95]
        }
        self._ndim_quantile_index = 0
        
        self._dim_red_method = "Principal component analysis (PCA)"
        self._dim_red_x = 0
        self._dim_red_y = 1

        self._cluster_type = "k-means"
        self.cluster_dict = {
            'k-means':{'n_clusters':5, 'seed':23, 'selected_clusters':[]},
            'fuzzy c-means':{'n_clusters':5, 'exponent':2.1, 'distance':'euclidean', 'seed':23, 'selected_clusters':[]}
        }
        self._num_clusters = self.cluster_dict[self._cluster_type]['n_clusters']
        if 'distance' in self.cluster_dict[self._cluster_type].keys():
            self._cluster_distance = self.cluster_dict[self._cluster_type]['distance']
        else:
            self._cluster_distance = 0
        if 'exponent' in self.cluster_dict[self._cluster_type].keys():
            self._cluster_exponent = self.cluster_dict[self._cluster_type]['exponent']
        else:
            self._cluster_distance = 0
        self._cluster_seed = self.cluster_dict[self._cluster_type]['seed']
        self._selected_clusters = self.cluster_dict[self._cluster_type]['selected_clusters']

        


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
    def sample_list(self):
        return self._sample_list

    @sample_list.setter
    def sample_list(self, new_sample_list):
        if new_sample_list == self._sample_list:
            return
        
        # update sample list and id of current sample
        self._sample_list = new_sample_list
        self._sample_id = new_sample_list[0]

        # notify observers to update widgets
        self.notify_observers("sample_list", new_sample_list)

    @property
    def sample_id(self):
        return self._sample_id
    
    @sample_id.setter
    def sample_id(self, new_sample_id):
        if new_sample_id == self._sample_id:
            return

        self._sample_id = new_sample_id
        self.notify_observers("sample_id", new_sample_id)

    ### Histogram Properties ###
    @property
    def hist_field_type(self):
        return self._hist_field_type
    
    @hist_field_type.setter
    def hist_field_type(self, new_field_type):
        if new_field_type == self._hist_field_type:
            return

        # update hist_field_type
        self.validate_field_type(new_field_type)
        self._hist_field_type = new_field_type
        self.notify_observers("hist_field_type", new_field_type)

        # update hist_field
        field_list = self.get_field_list(set_name=self._hist_field_type)
        self.hist_field = field_list[0]


    @property
    def hist_field(self):
        return self._hist_field

    @hist_field.setter
    def hist_field(self, new_field):
        if new_field == self._hist_field:
            return

        self.validate_field(self._hist_field_type, new_field)
        self._hist_field = new_field
        self.notify_observers("hist_field", new_field)

        # update hist_bin_width
        self.update_num_bins = False
        self.update_hist_bin_width()
        self.update_num_bins = True


    @property
    def hist_bin_width(self):
        return self._hist_bin_width
    
    @hist_bin_width.setter
    def hist_bin_width(self, new_bin_width):
        if new_bin_width == self._hist_bin_width:
            return

        self._hist_bin_width = new_bin_width
        self.notify_observers("hist_bin_width", new_bin_width)

        # update hist_num_bins
        if self.update_num_bins:
            self.update_bin_width = False
            self.update_hist_num_bins()
            self.update_bin_width = True


    @property
    def hist_num_bins(self):
        return self._hist_num_bins
    
    @hist_num_bins.setter
    def hist_num_bins(self, new_num_bins):
        if new_num_bins == self._new_num_bins:
            return
        
        self._hist_num_bins = new_num_bins
        self.notify_observers("hist_num_bins", new_num_bins)

        # update hist_bin_width
        if self.update_bin_width:
            self.update_num_bins = False
            self.update_hist_bin_width()
            self.update_num_bins = True
    

    @property
    def hist_plot_style(self):
        return self._hist_plot_style
    
    @hist_plot_style.setter
    def hist_plot_style(self, new_plot_style):
        if new_plot_style == self._hist_plot_style:
            return
        elif new_plot_style not in ['PDF','CDF','log-scaling']:
            ValueError("Unknown histogram plot style")

        self._hist_plot_style = new_plot_style
        self.notify_observers("hist_plot_style", new_plot_style)

    @property
    def corr_plot_style(self):
        return self._corr_plot_style
    
    @corr_plot_style.setter
    def corr_plot_style(self, new_corr_plot_style):
        if new_corr_plot_style == self._corr_plot_style:
            return
        elif new_corr_plot_style not in ['none', 'Pearson', 'Spearman', 'Kendall']:
            ValueError("Unknow correlation plot type")
    
        self._corr_plot_style = new_corr_plot_style
        self.notify_observers("corr_plot_style", new_corr_plot_style)

    @property
    def corr_squared(self):
        return self._corr_squared
    
    @corr_squared.setter
    def corr_squared(self, new_corr_squared):
        if new_corr_squared == self._corr_squared:
            return
    
        self._corr_squared = new_corr_squared
        self.notify_observers("corr_squared", new_corr_squared)

    @property
    def noise_red_method(self):
        return self._noise_red_method
    
    @noise_red_method.setter
    def noise_red_method(self, new_noise_red_method):
        if new_noise_red_method == self._noise_red_method:
            return
    
        self._noise_red_method = new_noise_red_method
        self.notify_observers("noise_red_method", new_noise_red_method)

    @property
    def noise_red_option1(self):
        return self._noise_red_option1
    
    @noise_red_option1.setter
    def noise_red_option1(self, new_noise_red_option1):
        if new_noise_red_option1 == self._noise_red_option1:
            return
    
        self._noise_red_option1 = new_noise_red_option1
        self.notify_observers("noise_red_option1", new_noise_red_option1)

    @property
    def noise_red_option2(self):
        return self._noise_red_option2
    
    @noise_red_option2.setter
    def noise_red_option2(self, new_noise_red_option2):
        if new_noise_red_option2 == self._noise_red_option2:
            return
    
        self._noise_red_option2 = new_noise_red_option2
        self.notify_observers("noise_red_option2", new_noise_red_option2)

    @property
    def apply_noise_red(self):
        return self._apply_noise_red
    
    @apply_noise_red.setter
    def apply_noise_red(self, new_apply_noise_red):
        if new_apply_noise_red == self._apply_noise_red:
            return
    
        self._apply_noise_red = new_apply_noise_red
        self.notify_observers("apply_noise_red", new_apply_noise_red)
    
    @property
    def gradient_flag(self):
        return self._gradient_flag
    
    @gradient_flag.setter
    def gradient_flag(self, new_gradient_flag):
        if new_gradient_flag == self._gradient_flag:
            return
    
        self._gradient_flag = new_gradient_flag
        self.notify_observers("gradient_flag", new_gradient_flag)
    
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
            self.notify_observers("x_field_type", new_field_type)

    @property
    def y_field_type(self):
        """str: Plot type used to determine plot method and associated style settings."""
        return self._y_field_type

    @y_field_type.setter
    def y_field_type(self, new_field_type):
        if new_field_type != self._y_field_type:
            self.validate_field_type(new_field_type)
            self._y_field_type = new_field_type
            self.notify_observers("y_field_type", new_field_type)

    @property
    def z_field_type(self):
        """str: Plot type used to determine plot method and associated style settings."""
        return self._z_field_type

    @z_field_type.setter
    def z_field_type(self, new_field_type):
        if new_field_type != self._z_field_type:
            self.validate_field_type(new_field_type)
            self._z_field_type = new_field_type
            self.notify_observers("z_field_type", new_field_type)

    @property
    def c_field_type(self):
        """str: Plot type used to determine plot method and associated style settings."""
        return self._c_field_type

    @c_field_type.setter
    def c_field_type(self, new_field_type):
        if new_field_type != self._c_field_type:
            self.validate_field_type(new_field_type)
            self._c_field_type = new_field_type
            self.notify_observers("c_field_type", new_field_type)

    @property
    def x_field(self):
        return self._x_field
    
    @x_field.setter
    def x_field(self, new_x_field):
        if new_x_field == self._x_field:
            return
    
        self._x_field = new_x_field
        self.notify_observers("x_field", new_x_field)
    
    @property
    def y_field(self):
        return self._y_field
    
    @y_field.setter
    def y_field(self, new_y_field):
        if new_y_field == self._y_field:
            return
    
        self._y_field = new_y_field
        self.notify_observers("y_field", new_y_field)
    
    @property
    def z_field(self):
        return self._z_field
    
    @z_field.setter
    def z_field(self, new_z_field):
        if new_z_field == self._z_field:
            return
    
        self._z_field = new_z_field
        self.notify_observers("z_field", new_z_field)

    @property
    def c_field(self):
        return self._c_field
    
    @c_field.setter
    def c_field(self, new_c_field):
        if new_c_field == self._c_field:
            return
    
        self._c_field = new_c_field
        self.notify_observers("c_field", new_c_field)

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
    def heatmap_style(self, new_heatmap_style):
        if new_heatmap_style == self._heatmap_style:
            return
    
        self._heatmap_style = new_heatmap_style
        self.notify_observers("heatmap_style", new_heatmap_style)

    ### Ternary Map ###
    @property
    def ternary_colormap(self):
        return self._ternary_colormap
    
    @ternary_colormap.setter
    def ternary_colormap(self, new_ternary_colormap):
        if new_ternary_colormap == self._ternary_colormap:
            return
    
        self._ternary_colormap = new_ternary_colormap
        self.notify_observers("ternary_colormap", new_ternary_colormap)


    @property
    def ternary_color_x(self):
        return self._ternary_color_x
    
    @ternary_color_x.setter
    def ternary_color_x(self, new_ternary_color_x):
        if new_ternary_color_x == self._ternary_color_x:
            return
    
        self._ternary_color_x = new_ternary_color_x
        self.notify_observers("ternary_color_x", new_ternary_color_x)

    @property
    def ternary_color_y(self):
        return self._ternary_color_y
    
    @ternary_color_y.setter
    def ternary_color_y(self, new_ternary_color_y):
        if new_ternary_color_y == self._ternary_color_y:
            return
    
        self._ternary_color_y = new_ternary_color_y
        self.notify_observers("ternary_color_y", new_ternary_color_y)

    @property
    def ternary_color_z(self):
        return self._ternary_color_z
    
    @ternary_color_z.setter
    def ternary_color_z(self, new_ternary_color_z):
        if new_ternary_color_z == self._ternary_color_z:
            return
    
        self._ternary_color_z = new_ternary_color_z
        self.notify_observers("ternary_color_z", new_ternary_color_z)

    ### Multidimensional Properties ###
    @property
    def norm_reference(self):
        return self._norm_reference
    
    @norm_reference.setter
    def norm_reference(self, new_norm_reference):
        if new_norm_reference == self._norm_reference:
            return
    
        self._norm_reference = new_norm_reference
        self.notify_observers("norm_reference", new_norm_reference)

    @property
    def ndim_analyte_set(self):
        return self._ndim_analyte_set
    
    @ndim_analyte_set.setter
    def ndim_analyte_set(self, new_ndim_analyte_set):
        if new_ndim_analyte_set == self._ndim_analyte_set:
            return
        elif new_ndim_analyte_set not in self.ndim_list_dict.keys():
            ValueError(f"N Dim list ({new_dim_analyte_set}) is not a defined option.")
    
        self._ndim_analyte_set = new_ndim_analyte_set
        self.notify_observers("ndim_analyte_set", new_ndim_analyte_set) 

    @property
    def ndim_quantile_index(self):
        return self._ndim_quantile_index
    
    @ndim_quantile_index.setter
    def ndim_quantile_index(self, new_ndim_quantile_index):
        if new_ndim_quantile_index == self._ndim_quantile_index:
            return
    
        self._ndim_quantile_index = new_ndim_quantile_index
        self.notify_observers("ndim_quantile_index", new_ndim_quantile_index)



    ### Dimensional Reduction Properties ###
    @property
    def dim_red_method(self):
        return self._dim_red_method
    
    @dim_red_method.setter
    def dim_red_method(self, new_dim_red_method):
        if new_dim_red_method == self._dim_red_method:
            return
    
        self._dim_red_method = new_dim_red_method
        self.notify_observers("dim_red_method", new_dim_red_method)

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
    def dim_red_y(self):
        return self._dim_red_y
    
    @dim_red_y.setter
    def dim_red_y(self, new_dim_red_y):
        if new_dim_red_y == self._dim_red_y:
            return
    
        self._dim_red_y = new_dim_red_y
        self.notify_observers("dim_red_y", new_dim_red_y)

    ### Cluster Properties ###
    @property
    def cluster_type(self):
        return self._cluster_type
    
    @cluster_type.setter
    def cluster_type(self, new_cluster_type):
        if new_cluster_type == self._cluster_type:
            return
        elif new_cluster_type not in list(self.cluster_dict.keys()):
            ValueError(f"Unknown cluster type ({new_cluster_type})")

        self._cluster_type = new_cluster_type
        self.notify_observers("cluster_type", new_cluster_type)

    @property
    def num_clusters(self):
        return self._num_clusters
    
    @num_clusters.setter
    def num_clusters(self, new_num_clusters):
        if new_num_clusters == self._num_clusters:
            return
    
        self._num_clusters = new_num_clusters
        self.notify_observers("num_clusters", new_num_clusters)

    @property
    def cluster_seed(self):
        return self._cluster_seed
    
    @cluster_seed.setter
    def cluster_seed(self, new_cluster_seed):
        if new_cluster_seed == self._cluster_seed:
            return
    
        self._cluster_seed = new_cluster_seed
        self.notify_observers("cluster_seed", new_cluster_seed)

    @property
    def cluster_exponent(self):
        return self._cluster_exponent
    
    @cluster_exponent.setter
    def cluster_exponent(self, new_cluster_exponent):
        if new_cluster_exponent == self._cluster_exponent:
            return
    
        self._cluster_exponent = new_cluster_exponent
        self.notify_observers("cluster_exponent", new_cluster_exponent)

    @property
    def cluster_distance(self):
        return self._cluster_distance
    
    @cluster_distance.setter
    def cluster_distance(self, new_cluster_distance):
        if new_cluster_distance == self._cluster_distance:
            return
    
        self._cluster_distance = new_cluster_distance
        self.notify_observers("cluster_distance", new_cluster_distance)

    @property
    def selected_clusters(self):
        return self._selected_clusters
    
    @selected_clusters.setter
    def selected_clusters(self, new_selected_clusters):
        if new_selected_clusters == self._selected_clusters:
            return
    
        self._selected_clusters = new_selected_clusters
        self.notify_observers("selected_clusters", new_selected_clusters)

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
                    set_fields = data.match_attributes({'data_type': 'analyte', 'use': True})
                else:
                    set_fields = data.match_attribute('data_type', 'analyte')
            case 'Ratio' | 'Ratio (normalized)':
                if filter == 'used':
                    set_fields = data.match_attributes({'data_type': 'ratio', 'use': True})
                else:
                    set_fields = data.match_attribute('data_type', 'ratio')
            case 'None':
                return []
            case _:
                set_fields = data.match_attribute('data_type', set_name.lower())

        return set_fields

    def update_hist_bin_width(self):
        """Updates the bin width

        Generally called when the number of bins is changed by the user.  Updates the plot.
        """
        if (self.hist_field_type == '') or (self.hist_field == ''):
            return

        # get currently selected data
        map_df = self.data[self.sample_id].get_map_data(self._hist_field, self._hist_field_type)

        # update bin width
        range = np.nanmax(map_df['array']) - np.nanmin(map_df['array'])
        self.hist_bin_widt = range / self._hist_num_bins

    def update_hist_num_bins(self):
        """Updates the number of bins

        Generally called when the bin width is changed by the user.  Updates the plot.
        """
        if (self.hist_field_type == '') or (self.hist_field == ''):
            return

        # get currently selected data
        map_df = self.data[self.sample_id].get_map_data(self._hist_field, self._hist_field_type)

        # update n bins
        range = np.nanmax(map_df['array']) - np.nanmin(map_df['array'])
        self.hist_num_bins = int( range / self._hist_bin_width.value() )
