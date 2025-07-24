import copy, random
from pathlib import Path
import numpy as np
import pandas as pd
import src.common.csvdict as csvdict
from src.app.config import APPDATA_PATH
from src.common.Observable import Observable
from src.common.Logger import auto_log_methods

@auto_log_methods(logger_key='Data')
class AppData(Observable):
    """
    AppData is a central data model and state manager for the LaserMapExplorer application.

    This class encapsulates all application-level data, user preferences, and analysis settings,
    and provides property-based accessors and mutators for all relevant state. It manages sample
    data, field selections, plotting and histogram settings, clustering and dimensionality reduction
    parameters, and user interface preferences. AppData also implements the Observable pattern,
    notifying observers (such as UI widgets) when relevant properties change.

    AppData is responsible for:
    - Storing and managing user preferences (units, font size, tick direction, etc.).
    - Maintaining references to all loaded sample data and their processed attributes.
    - Providing property-based access to current sample, field, and field type selections for
      plotting.
    - Managing histogram and color scale settings for data visualization.
    - Storing and updating clustering and dimensionality reduction parameters.
    - Handling reference chemistry data for normalization.
    - Supporting multi-dimensional analyte selection and quantile settings.
    - Notifying observers of changes to any relevant property, enabling reactive UI updates.

    Attributes
    ----------
    logger_key : str
        Identifier for logging.
    default_preferences : dict
        Default user preferences for units, font size, etc.
    preferences : dict
        Current user preferences (deep copy of default_preferences).
    selected_directory : str
        Currently selected directory for file operations.
    sample_list : list
        List of sample IDs currently loaded.
    data : dict
        Dictionary mapping sample IDs to SampleObj data classes.
    field_dict : dict
        Dictionary of field types for the current sample.
    plot_info : dict
        Dictionary for storing plot-related information.
    outlier_methods : list
        Available methods for outlier detection.
    negative_methods : list
        Available methods for handling negative values.
    noise_red_options : dict
        Options for noise reduction methods and their parameters.
    cluster_dict : dict
        Dictionary of clustering method parameters and results.
    scatter_preset_dict : dict
        Preset field lists for scatter diagrams.
    ndim_list_dict : dict
        Preset analyte lists for multi-dimensional analysis.
    ndim_analyte_df : pd.DataFrame
        DataFrame of analytes for N-Dim analysis.
    ref_data : pd.DataFrame
        Reference chemistry data for normalization.
    ref_list : pd.Series
        List of reference chemistry sources.
    axis : list
        List of axis labels ('x', 'y', 'z', 'c').

    Properties
    ----------
    sort_method : str
        Method used to sort the sample list.
    ref_index : int
        Index of the reference chemistry source.
    ref_chem : pd.Series
        Reference chemistry for the current reference index.
    sample_id : str
        ID of the currently selected sample.
    equalize_color_scale : bool
        Whether to equalize color scale for histograms.
    default_hist_num_bins : int
        Default number of histogram bins.
    hist_bin_width : float
        Width of histogram bins.
    hist_num_bins : int
        Number of histogram bins.
    hist_plot_style : str
        Style of histogram plot.
    corr_method : str
        Method used for correlation plots.
    corr_squared : bool
        Whether to use squared correlation values.
    noise_red_method : str
        Method used for noise reduction.
    noise_red_option1 : int or float
        First option for noise reduction method.
    noise_red_option2 : int or float
        Second option for noise reduction method.
    apply_noise_red : str
        Whether to apply noise reduction.
    gradient_flag : bool
        Whether to plot the gradient.
    edge_detection_method : str
        Method used for edge detection.
    x_field_type, y_field_type, z_field_type, c_field_type : str
        Field types for axes and color mapping.
    x_field, y_field, z_field, c_field : str
        Fields for axes and color mapping.
    scatter_preset : str
        Preset for scatter plot styles.
    heatmap_style : str
        Style of heatmap to use.
    norm_reference : str
        Reference used for normalizing analyte and ratio data.
    ndim_analyte_set : str
        Set of analytes used for N-Dim analysis.
    ndim_list : list
        List of analytes for N-Dim analysis.
    ndim_quantile_index : int
        Index of quantile set for N-Dim analysis.
    dim_red_method : str
        Method for dimensionality reduction.
    dim_red_x, dim_red_y : int
        Axis indices for dimensionality reduction.
    dim_red_x_max, dim_red_y_max : int
        Maximum axis indices for dimensionality reduction.
    cluster_method : str
        Current clustering method.
    max_clusters : int
        Maximum number of clusters.
    num_clusters : int
        Number of clusters to use.
    cluster_seed : int
        Random seed for clustering.
    cluster_exponent : float
        Exponent for fuzzy c-means clustering.
    cluster_distance : str
        Distance metric for clustering.
    selected_clusters : list
        List of selected clusters for masking.
    dim_red_precondition : bool
        Whether to precondition dimensionality reduction with PCA.
    num_basis_for_precondition : int
        Number of basis vectors for preconditioning.

    Methods
    -------
    get_field(ax)
    set_field(ax, value)
        Sets the field for the specified axis.
    get_field_type(ax)
        Returns the field type for the specified axis.
    set_field_type(ax, value)
        Sets the field type for the specified axis.
    validate_field_type(new_field_type)
        Validates if the new field type exists in the current sample's processed data.
    validate_field(field_type, new_field)
        Validates if the new field exists for the given field type.
    get_field_list(set_name='Analyte', filter_type='all')
        Gets the fields associated with a defined set.
    update_hist_bin_width()
        Updates the bin width for histograms.
    update_hist_num_bins()
        Updates the number of bins for histograms.
    histogram_reset_bins()
        Resets number of histogram bins to the default.
    _set_clustering_parameters()
        Sets clustering parameters based on the current method.
    generate_random_seed()
        Generates a random seed for clustering.
    cluster_group_changed(data, plot_style)

    Notes
    -----
    This class is designed to be used as a singleton or shared instance within the application,
    serving as the authoritative source of state for all data analysis and visualization operations.
    """
    def __init__(self, data):
        super().__init__()

        self.logger_key = 'Data'

        self.default_preferences = {
            'Units':{
                'Concentration': 'ppm',
                'Distance': 'µm',
                'Temperature':'°C',
                'Pressure':'MPa',
                'Date':'Ma'
            },
            'FontSize':11,
            'TickDir':'out',
        }

        # in future will be set from preference ui
        self.preferences = copy.deepcopy(self.default_preferences)
        self.selected_directory = Path()

        self._sort_method = 'mass'

        # reference chemistry
        self.ref_data = pd.read_excel(APPDATA_PATH / 'earthref.xlsx')
        self.ref_data = self.ref_data[self.ref_data['sigma']!=1]
        self.ref_list = self.ref_data['layer']+' ['+self.ref_data['model']+'] '+ self.ref_data['reference']
        self._ref_index = 0

        self._sample_list = []
        self.csv_files = []

        # a dictionary of sample_id containing SampleObj data class
        self.data = data

        # a dictionary of the field_types in self.data[sample_id].processed_data
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

        self.outlier_methods = [
            'none',
            'quantile critera',
            'quantile and distance critera',
            'Chauvenet criterion',
            'log(n>x) inflection'
        ]
        self.negative_methods = [
            'ignore negatives',
            'minimum positive',
            'gradual shift',
            'Yeo-Johnson transform'
        ]
        # histogram related data and methods
        self._equalize_color_scale = False

        self._default_hist_num_bins = 100
        self._hist_bin_width = 0
        self._hist_num_bins = 0
        self._hist_plot_style = None
        self.update_bin_width = True
        self.update_num_bins = True
        self._corr_method = None
        self._corr_squared = False

        self._noise_red_method = 'none'
        self.noise_red_options = {
            'none':{},
            'median':{
                'option1_min':1,
                'option1_max':5,
                'option1_step':2,
                'option1':3,
            },
            'wiener':{
                'option1_min':1,
                'option1_max':199,
                'option1_step':2,
                'option1':30,
            },
            'gaussian':{
                'option1_min':1,
                'option1_max':199,
                'option1_step':2,
                'option1':30,
            },
            'edge-preserving':{
                'option1_min':0,
                'option1_max':200,
                'option1_step':5,
                'option1':30,
                'option2_min':0,
                'option2_max':1,
                'option2_step':0.1,
                'option2':0.1,
            },
            'bilateral':{
                'option1_min':0,
                'option1_max':200,
                'option1_step':5,
                'option1':30,
                'option2_min':0,
                'option2_max':200,
                'option2_step':5.0,
                'option2':75.0,
            },
        }
        if 'option1' in self.noise_red_options[self._noise_red_method]:
            self._noise_red_option1 = self.noise_red_options[self._noise_red_method]['option1']
        else:
            self._noise_red_option1 = 0
        if 'option2' in self.noise_red_options[self._noise_red_method]:
            self._noise_red_option2 = self.noise_red_options[self._noise_red_method]['option2']
        else:
            self._noise_red_option2 = 0.0

        self._apply_noise_red = "No"
        self._gradient_flag = False
        self._edge_detection_method = "zero cross"

        self._scatter_preset = ""
        # get scatter presets list
        self.scatter_list_path = APPDATA_PATH / 'scatter_presets.csv'
        try:
            self.scatter_preset_dict = csvdict.import_csv_to_dict(self.scatter_list_path)
        except FileNotFoundError:
            self.scatter_preset_dict = {}

        self._heatmap_style = "counts"

        self._norm_reference = ""

        # get N-Dim lists
        self.ndim_list_path = APPDATA_PATH / 'TEC_presets.csv'
        try:
            self.ndim_list_dict = csvdict.import_csv_to_dict(self.ndim_list_path)
        except FileNotFoundError:
            self.ndim_list_dict = {
                    'majors': ['Si','Ti','Al','Fe','Mn','Mg','Ca','Na','K','P'],
                    'full trace': [
                        'Cs','Rb','Ba','Th','U','K','Nb','Ta','La','Ce','Pb',
                        'Mo','Pr','Sr','P','Ga','Zr','Hf','Nd','Sm','Eu','Li',
                        'Ti','Gd','Dy','Ho','Y','Er','Yb','Lu'
                    ],
                    'REE': ['La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu'],
                    'metals': ['Na','Al','Ca','Zn','Sc','Cu','Fe','Mn','V','Co','Mg','Ni','Cr'],
                }
        if 'REE' in self.ndim_list_dict:
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
        self._dim_red_x_max = 2 # should change based on the number of fields used to compute basis
        self._dim_red_y_max = 2 # should change based on the number of fields used to compute basis

        self._cluster_method = "k-means"
        self.cluster_dict = {
            'k-means': {
                'n_clusters':5,
                'seed':23,
                'selected_clusters':[],
            },
            'fuzzy c-means':{
                'n_clusters':5,
                'exponent':2.1,
                'distance':'euclidean',
                'seed':23,
                'selected_clusters':[]
            },
        }
        self._max_clusters = 10
        self._num_clusters = self.cluster_dict[self._cluster_method]['n_clusters']
        if 'distance' in self.cluster_dict[self._cluster_method]:
            self._cluster_distance = self.cluster_dict[self._cluster_method]['distance']
        else:
            self._cluster_distance = None
        if 'exponent' in self.cluster_dict[self._cluster_method]:
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
        """
        Returns the field associated with the specified axis.
        
        Parameters
        ----------
        ax : int
            The axis index (0 for x, 1 for y, 2 for z, 3 for c).

        Returns
        -------
        str
            The field associated with the specified axis.

        Raises
        ------
        ValueError if the axis index is invalid.
        """
        return getattr(self, f"{self.axis[ax]}_field")

    def set_field(self, ax, value):
        """
        Sets the field associated with the specified axis.
        
        Parameters
        ----------
        ax : int
            The axis index (0 for x, 1 for y, 2 for z, 3 for c).
        value : str
            The field to set for the specified axis.

        Raises
        ------
        ValueError if the axis index is invalid.
        """
        setattr(self, f"{self.axis[ax]}_field", value)

    def get_field_type(self, ax):
        """
        Returns the field type associated with the specified axis.
        
        Parameters
        ----------
        ax : int
            The axis index (0 for x, 1 for y, 2 for z, 3 for c).

        Returns
        -------
        str
            The field type associated with the specified axis.

        Raises
        ------
        ValueError if the axis index is invalid.
        """
        return getattr(self, f"{self.axis[ax]}_field_type")

    def set_field_type(self, ax, value):
        """
        Sets the field type associated with the specified axis.
        
        Parameters
        ----------
        ax : int
            The axis index (0 for x, 1 for y, 2 for z, 3 for c).
        value : str
            The field type to set for the specified axis.

        Raises
        ------
        ValueError if the axis index is invalid or if the field type does
            not exist in the current sample's processed data.
        """
        setattr(self, f"{self.axis[ax]}_field_type", value)

    def validate_field_type(self, new_field_type):
        """Validates if the new field type exists in the current sample's processed data.
        
        Parameters
        ----------
        new_field_type : str
            The field type to validate.
        Returns
        -------
        bool
            True if the field type exists, False otherwise.

        Raises
        ------
        ValueError if the sample_id is empty or the field type is not found.
        """
        if self.sample_id == "":
            return False
        data_types = self.data[self.sample_id].processed_data.get_attribute_dict('data_type')
        if new_field_type in data_types:
            return True
        else:
            raise ValueError("Field type not found.")

    def validate_field(self, field_type, new_field):
        return True
        # field_list = self.get_field_list(set_name=field_type)
        # if new_field in field_list:
        # return true
        # else:
        # raise ValueError("field not found.")

    @property
    def sort_method(self):
        """ (str): The method used to sort the sample list."""
        return self._sort_method
    
    @sort_method.setter
    def sort_method(self, new_method):
        if new_method == self._sort_method:
            return

        self._sort_method = new_method
        self.notify_observers("sort_method", new_method)

    @property
    def ref_index(self):
        """int : The index of the reference chemistry source used for normalization."""
        return self._ref_index
    
    @ref_index.setter
    def ref_index(self, new_index):
        if new_index == self._ref_index:
            return

        self._ref_index = new_index
        self.notify_observers("ref_index", new_index)

    @property
    def ref_chem(self):
        """pd.Series : The reference chemistry for the current reference index."""
        chem = self.ref_data.iloc[self._ref_index].copy()
        chem.index = [str(col).replace('_ppm', '') for col in chem.index]

        return chem

    @property
    def sample_list(self):
        """list : A list of sample IDs in the current sample list."""
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
        """str : The ID/name of the currently selected sample."""
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
        """bool : Whether to equalize the color scale for histograms."""
        return self._equalize_color_scale
    
    @equalize_color_scale.setter
    def equalize_color_scale(self, flag):
        if flag == self._equalize_color_scale:
            return
    
        self._equalize_color_scale = flag
        self.notify_observers("equalize_color_scale", flag)

    @property
    def default_hist_num_bins(self):
        """int : The default number of histogram bins."""
        return self._default_hist_num_bins

    @property
    def hist_bin_width(self):
        """float : The width of histogram bins."""
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
        """int : The number of histogram bins."""
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
        """str : The style of histogram plot to use."""
        return self._hist_plot_style
    
    @hist_plot_style.setter
    def hist_plot_style(self, hist_style):
        if hist_style == self._hist_plot_style:
            return
        elif hist_style not in ['PDF','CDF','log-scaling']:
            raise ValueError("Unknown histogram plot style")

        self._hist_plot_style = hist_style
        self.notify_observers("hist_plot_style", hist_style)

    @property
    def corr_method(self):
        """str : The method used for correlation plots."""
        return self._corr_method
    
    @corr_method.setter
    def corr_method(self, method):
        if method == self._corr_method:
            return
        elif method not in ['none', 'Pearson', 'Spearman', 'Kendall']:
            raise ValueError("Unknown correlation plot type")
    
        self._corr_method = method
        self.notify_observers("corr_method", method)

    @property
    def corr_squared(self):
        """bool : Whether to use squared correlation values."""
        return self._corr_squared
    
    @corr_squared.setter
    def corr_squared(self, flag):
        if flag == self._corr_squared:
            return
    
        self._corr_squared = flag
        self.notify_observers("@corr_squared", flag)

    @property
    def noise_red_method(self):
        """str : The method used for noise reduction."""
        return self._noise_red_method
    
    @noise_red_method.setter
    def noise_red_method(self, method):
        if method == self._noise_red_method:
            return
    
        self._noise_red_method = method
        self.notify_observers("noise_red_method", method)

    @property
    def noise_red_option1(self):
        """int | float : The first option for noise reduction method."""
        return self._noise_red_option1
    
    @noise_red_option1.setter
    def noise_red_option1(self, value):
        if value == self._noise_red_option1:
            return
    
        self._noise_red_option1 = value
        self.notify_observers("noise_red_option1", value)

    @property
    def noise_red_option2(self):
        """int | float : The second option for noise reduction method."""
        return self._noise_red_option2
    
    @noise_red_option2.setter
    def noise_red_option2(self, value):
        if value == self._noise_red_option2:
            return
    
        self._noise_red_option2 = value
        self.notify_observers("noise_red_option2", value)

    @property
    def apply_noise_red(self):
        """str : Whether to apply noise reduction."""
        return self._apply_noise_red
    
    @apply_noise_red.setter
    def apply_noise_red(self, flag):
        if flag == self._apply_noise_red:
            return
    
        self._apply_noise_red = flag
        self.notify_observers("apply_noise_red", flag)
    
    @property
    def gradient_flag(self):
        """bool : Whether to plot the gradient."""
        return self._gradient_flag
    
    @gradient_flag.setter
    def gradient_flag(self, flag):
        if flag == self._gradient_flag:
            return
    
        self._gradient_flag = flag
        self.notify_observers("gradient_flag", flag)

    @property
    def edge_detection_method(self):
        """str : The method used for edge detection."""
        return self._edge_detection_method

    @edge_detection_method.setter
    def edge_detection_method(self, method):
        if method == self._edge_detection_method:
            return
        
        self._edge_detection_method = method
    
    ### Scatter Properties ###
    @property
    def x_field_type(self):
        """str : Field type for x field."""
        return self._x_field_type

    @x_field_type.setter
    def x_field_type(self, new_field_type):
        if new_field_type != self._x_field_type:
            self.validate_field_type(new_field_type)
            self._x_field_type = new_field_type
            self.notify_observers("field_type", 0, new_field_type)

    @property
    def y_field_type(self):
        """str : Field type for y field."""
        return self._y_field_type

    @y_field_type.setter
    def y_field_type(self, new_field_type):
        if new_field_type != self._y_field_type:
            self.validate_field_type(new_field_type)
            self._y_field_type = new_field_type
            self.notify_observers("field_type", 1, new_field_type)

    @property
    def z_field_type(self):
        """str : Field type for z field."""
        return self._z_field_type

    @z_field_type.setter
    def z_field_type(self, new_field_type):
        if new_field_type != self._z_field_type:
            self.validate_field_type(new_field_type)
            self._z_field_type = new_field_type
            self.notify_observers("field_type", 2, new_field_type)

    @property
    def c_field_type(self):
        """str : Field type for color field or map data."""
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
        """str : Field associated with x-axis or A-vertex on a ternary diagram."""
        return self._x_field
    
    @x_field.setter
    def x_field(self, new_field):
        if new_field == self._x_field:
            return
    
        self._x_field = new_field
        self.notify_observers("field", 0, new_field)
    
    @property
    def y_field(self):
        """str : Field associated with y-axis or B-vertex on a ternary diagram."""
        return self._y_field
    
    @y_field.setter
    def y_field(self, new_field):
        if new_field == self._y_field:
            return
    
        self._y_field = new_field
        self.notify_observers("field", 1, new_field)
    
    @property
    def z_field(self):
        """str : Field associated with z-axis or C-vertex on a ternary diagram."""
        return self._z_field
    
    @z_field.setter
    def z_field(self, new_field):
        if new_field == self._z_field:
            return
    
        self._z_field = new_field
        self.notify_observers("field", 2, new_field)

    @property
    def c_field(self):
        """str : Field associated with color on many plots."""
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
        """str : The preset for scatter plot styles."""
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
        """str : The style of heatmap to use."""
        return self._heatmap_style
    
    @heatmap_style.setter
    def heatmap_style(self, new_style):
        if new_style == self._heatmap_style:
            return
    
        self._heatmap_style = new_style
        self.notify_observers("heatmap_style", new_style)


    ### Multidimensional Properties ###
    @property
    def norm_reference(self):
        """str : The reference used for normalizing analyte and ratio data."""
        return self._norm_reference
    
    @norm_reference.setter
    def norm_reference(self, new_ref):
        if new_ref == self._norm_reference:
            return
    
        self._norm_reference = new_ref
        self.notify_observers("norm_reference", new_ref)

    @property
    def ndim_analyte_set(self):
        """str : The set of analytes used for N-Dim analysis."""
        return self._ndim_analyte_set
    
    @ndim_analyte_set.setter
    def ndim_analyte_set(self, new_list):
        if new_list == self._ndim_analyte_set:
            return
        elif new_list not in self.ndim_list_dict:
            raise ValueError(f"N Dim list ({new_list}) is not a defined option.")
    
        self._ndim_analyte_set = new_list
        self.notify_observers("ndim_analyte_set", new_list) 

    @property
    def ndim_list(self):
        """list : The list of analytes used for N-Dim analysis."""
        return self._ndim_list

    @ndim_list.setter
    def ndim_list(self, new_list):
        self._ndim_list = new_list
        self.notify_observers("ndim_list", new_list)

    @property
    def ndim_quantile_index(self):
        """int : The index of the quantile set used for N-Dim analysis."""
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
        """str : The method used for dimensionality reduction."""
        return self._dim_red_method
    
    @dim_red_method.setter
    def dim_red_method(self, method):
        if method == self._dim_red_method:
            return
    
        self._dim_red_method = method
        self.notify_observers("dim_red_method", method)

    @property
    def dim_red_x(self):
        """int : The x-axis index for dimensionality reduction."""
        return self._dim_red_x
    
    @dim_red_x.setter
    def dim_red_x(self, new_value):
        if new_value == self._dim_red_x:
            return
    
        self._dim_red_x = new_value
        self.notify_observers("dim_red_x", new_value)

    @property
    def dim_red_x_max(self):
        """int : The maximum x-axis index for dimensionality reduction."""
        return self._dim_red_x_max

    @dim_red_x_max.setter
    def dim_red_x_max(self, new_max):
        if new_max == self._dim_red_x_max:
            return
        self._dim_red_x_max = new_max
        self.notify_observers("dim_red_x_max", new_max)

    @property
    def dim_red_y(self):
        """int : The y-axis index for dimensionality reduction."""
        return self._dim_red_y

    @dim_red_y.setter
    def dim_red_y(self, new_value):
        if new_value == self._dim_red_y:
            return
    
        self._dim_red_y = new_value
        self.notify_observers("dim_red_x", new_value)
    
    @property
    def dim_red_y_max(self):
        """int : The maximum y-axis index for dimensionality reduction."""
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
        """list : The available clustering methods."""
        return list(self.cluster_dict.keys())

    @property
    def cluster_method(self):
        """str : The current clustering method used for data analysis."""
        return self._cluster_method
    
    @cluster_method.setter
    def cluster_method(self, method):
        if method == self._cluster_method:
            return
        elif method not in self.cluster_method_options:
            raise ValueError(f"Unknown cluster type ({method})")

        self._cluster_method = method
        self._set_clustering_parameters()
        self.notify_observers("cluster_method", method)

    @property
    def max_clusters(self):
        """int : The maximum number of clusters allowed for testing cluster performance."""
        return self._max_clusters
    
    @max_clusters.setter
    def max_clusters(self, new_value):
        if new_value == self._max_clusters:
            return
    
        self._max_clusters = new_value
        self.notify_observers("max_clusters", new_value)

    @property
    def num_clusters(self):
        """int : The number of clusters to use in clustering."""
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
        """int : The random seed used for clustering."""
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
        """float : The exponent used in fuzzy c-means clustering."""
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
        """str : The distance metric used in clustering."""
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
        """list : The list of selected clusters for masking."""
        return self._selected_clusters
    
    @selected_clusters.setter
    def selected_clusters(self, new_list):
        if new_list == self._selected_clusters:
            return
    
        self._selected_clusters = new_list
        self.notify_observers("selected_clusters", new_list)

    @property
    def dim_red_precondition(self):
        """bool : Whether to precondition the dimensionality reduction with PCA."""
        return self._dim_red_precondition
    
    @dim_red_precondition.setter
    def dim_red_precondition(self, flag):
        if flag == self._dim_red_precondition:
            return
    
        self._dim_red_precondition = flag
        self.notify_observers("dim_red_precondition", flag)

    @property
    def num_basis_for_precondition(self):
        """int : The number of basis vectors to use for preconditioning in dimensionality reduction.
        """
        return self._num_basis_for_precondition
    
    @num_basis_for_precondition.setter
    def num_basis_for_precondition(self, new_value):
        if new_value == self._num_basis_for_precondition:
            return
    
        self._num_basis_for_precondition = new_value
        self.notify_observers("num_basis_for_precondition", new_value)

    @property
    def field_dict(self):
        """dict : A dictionary of field names and their types for the current sample.

        This dictionary is used to populate field selection widgets and ensure valid selections.
        Coordinate fields are excluded from this dictionary.
        """
        self._field_dict = self.data[self.sample_id].processed_data.get_attribute_dict('data_type')
        if 'coordinate' in self._field_dict:
            self._field_dict.pop("coordinate")
        return self._field_dict
    
    @property
    def selected_fields(self, field_type='Analyte'):
        """list : The selected fields for the current sample."""
        if self.data and self.sample_id != '':
            return self.data[self.sample_id].processed_data.match_attributes({'data_type':field_type, 'use': True}).values
        else:
            return []

    def get_field_list(self, field_type='Analyte', filter_type='all'):
        """Gets the fields associated with a defined set

        Set names are consistent with QComboBox.
        The set names are: ``Analyte``, ``Analyte (normalized)``, ``Ratio``, ``Calculated Field``,
        ``PCA Score``, ``Cluster``, ``Cluster Score``, ``Special``
        and ``None``.  The set names are used to filter the data to a specific set of fields.
        The ``filter_type`` parameter is used to filter the data to only fields that are used
        in analysis.  The options for ``filter_type`` are ``'all'`` and ``'used'``.  If
        ``filter_type`` is set to ``'all'``, all fields in the set will be returned.  If
        ``filter_type`` is set to ``'used'``, only fields that are used in analysis will be returned.

        Parameters
        ----------
        field_type : str, optional
            name of set list, by default 'Analyte'
        filter_type : str, optional
            Filters data to columns selected for analysis, by default 'all'

        Returns
        -------
        list
            Set_fields, a list of fields within the input set
        """
        if self.sample_id == '':
            return ['']

        data = self.data[self.sample_id].processed_data

        if filter_type not in ['all', 'used']:
            raise ValueError("filter must be 'all' or 'used'.")

        if 'normalized' in field_type:
            field_type = field_type.replace(' (normalized)','')

        field_list = self.field_dict[field_type]

        if field_type == 'Analyte':
            _, field_list = self.data[self.sample_id].sort_data(self.sort_method)

        # filter list by selected analytes
        if filter_type == 'used':
            field_list = [f for f in field_list if f in self.selected_fields(field_type)]
        
        return field_list

    def update_hist_bin_width(self):
        """Updates the bin width for histograms

        This method calculates the bin width based on the currently selected data field and type.
        It retrieves the data for the selected field and type, calculates the range of values,
        and sets the bin width based on the number of histogram bins.
        """
        if (self.c_field_type == '') or (self.c_field == ''):
            return

        # get currently selected data
        map_df = self.data[self.sample_id].get_map_data(self._c_field, self._c_field_type)

        # update bin width
        data_range = np.nanmax(map_df['array']) - np.nanmin(map_df['array'])
        self.hist_bin_width = data_range / self._hist_num_bins

    def update_hist_num_bins(self):
        """Updates the number of bins for histograms

        This method calculates the number of histogram bins based on the currently selected data
        field and type.  It retrieves the data for the selected field and type, calculates the
        range of values, and sets the number of bins based on the bin width.
        """
        if (self.c_field_type == '') or (self.c_field == ''):
            return

        # get currently selected data
        map_df = self.data[self.sample_id].get_map_data(self._c_field, self._c_field_type)

        # update n bins
        data_range = np.nanmax(map_df['array']) - np.nanmin(map_df['array'])
        self.hist_num_bins = int( data_range / self._hist_bin_width)

    def histogram_reset_bins(self):
        """Resets number of histogram bins to the default."""
        self.hist_num_bins = self.default_hist_num_bins

    def _set_clustering_parameters(self):
        """Sets clustering parameters

        This method updates the clustering parameters based on the current clustering
        method.  It retrieves the number of clusters, seed, distance metric, and exponent
        from the cluster dictionary for the selected clustering method and updates the
        corresponding instance variables.  If the clustering method does not have a
        distance metric or exponent defined, it sets them to None or 0 respectively.  It
        also updates the number of clusters and seed in the cluster dictionary for the
        selected method.
        """
        if 'distance' in self.cluster_dict[self._cluster_method]:
            self.cluster_distance = self.cluster_dict[self._cluster_method]['distance']
        if 'exponent' in self.cluster_dict[self._cluster_method]:
            self.cluster_exponent = self.cluster_dict[self._cluster_method]['exponent']

    def generate_random_seed(self):
        """Generates a random seed for clustering.

        This method generates a random integer between 0 and 1,000,000,000 to be used as
        a seed for clustering algorithms. This is useful for ensuring reproducibility in
        clustering results by providing a consistent starting point for random number
        generation in clustering algorithms.  The generated seed is stored in the
        instance variable `self.cluster_seed`.  The seed can be used in clustering methods
        like k-means or fuzzy c-means to ensure that the results can be replicated across
        different runs of the algorithm.  The seed is generated using Python's
        `random.randint` function.
        """        
        r = random.randint(0,1000000000)
        self.cluster_seed = r
        

    def cluster_group_changed(self, data, plot_style):
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
                except Exception as e:
                    pass

                i = 0
                while True:
                    try:
                        self.cluster_dict[method].pop(str(i))
                        i += 1
                    except Exception as e:
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