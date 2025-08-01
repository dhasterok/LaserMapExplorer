import re, os, copy
import numpy as np
import pandas as pd
from src.common.ExtendedDF import AttributeDataFrame
from scipy.stats import yeojohnson
# from kneed import KneeLocator
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import src.common.format as fmt
from src.common.Observable import Observable
from src.common.SortAnalytes import sort_analytes
from src.common.outliers import chauvenet_criterion, quantile_and_difference
from PyQt6.QtWidgets import QMessageBox
from src.common.Status import StatusMessageManager
from src.common.format import symlog, inv_logit
from src.common.Logger import LoggerConfig, auto_log_methods


@auto_log_methods(logger_key='Data')
class SampleObj(Observable):
    """Creates a base sample object to store and manipulate geochemical data in map form
    
    The sample object is initially constructed from the data within a *.lame.csv file and loaded into
    the ``raw_data`` dataframe.  The sample object also contains a number of properties in addition
    to the input data.  These include metadata that are linked to each column.  To make this link,
    the dataframe is initialized as an ``ExtendedDF.AttributeDataFrame``, which brings with it a
    number of methods to set, get and search the dataframe's metadata.

    Parameters
    ----------
    sample_id : str
        Sample identifier.
    file_path : str
        Path to data file for sample_id
    outlier_method : str
        Method used ot handle outliers in the dataset
    negative_method : str
        Method used to handle negative values in the dataset
    ref_chem : pandas.DataFrame
        Reference chemistry for normalizing data
    debug : bool, optional
        If true, will result in verbose output to stdout
    
    Methods
    -------
    reset_data :
        Reverts back to the original data

    add_columns :
        Add one or more columns to the sample object

    delete_column :
        Deletes a column and associated attributes from the AttributeDataFrame

    get_attribute_dict :
        Creates a dictionary from an attribute where the unique values of the attribute becomes the
        keys and the items are lists with the column names that match each attribute_name

    swap_xy : 
        Swaps data in a SampleObj

    _swap_xy :
        Swaps X and Y of a dataframe
    
    swap_resolution :
        Swaps DX and DY for a dataframe

    reset_crop :
        Reset the data to the new bounds.

    compute_ratio :
        Compute a ratio field from two analytes

    cluster_data :
        Clusters data for use with data preprocessing


    prep_data :
        Applies adjustments to data data prior to analyses and plotting

    k_optimal_clusters :
        Predicts the optimal number of clusters

    outlier_detection :
        Outlier detection with cluster-based correction for negatives and compositional constraints, using percentile-based shifting

    transform_array :
        Negative and zero handling with clustering for noise detection

    update_norm :
        Update the norm of the data

    get_map_data :
        Retrieves and processes the mapping data for the given sample and analytes

    get_processed_data :
        Gets the processed data for analysis

    get_vector :
        Creates a dictionary of values for plotting

    ref_chem : dict
        Reference chemistry. By default `None`.

    Attributes
    ----------
    update_crop_mask :
        Automatically update the crop_mask whenever crop bounds change.
    reset_crop : 
        Resets dataframe to original bounds.
    raw_data :
    filter_df : (pandas.DataFrame) -- stores filters for each sample
        | 'field_type' : (str) -- field type
        | 'field' : (str) -- name of field
        | 'norm' : (str) -- scale normalization function, ``linear`` or ``log``
        | 'min' : (float) -- minimum value for filtering
        | 'max' : (float) -- maximum value for filtering
        | 'operator' : (str) -- boolean operator for combining filters, ``and`` or ``or``
        | 'use' : (bool) -- ``True`` indicates the filter should be used to filter data
        | 'persistent' : (bool) -- ``True`` retains the filter when the sample is changed

        | 'crop' : () --
        | 'x_max' : () --
        | 'x_min' : () --
        | 'y_max' : () --
        | 'y_min' : () --
        | 'crop_x_max' : () --
        | 'crop_x_min' : () --
        | 'crop_y_max' : () --
        | 'crop_y_min' : () --
        | 'processed data': () --
        | 'raw_data': () -- 
        | 'cropped_raw_data': () --
            
        | 'crop' : () --
        | 'x_max' : () --
        | 'x_min' : () --
        | 'y_max' : () --
        | 'y_min' : () --
        | 'crop_x_max' : () --
        | 'crop_x_min' : () --
        | 'crop_y_max' : () --
        | 'crop_y_min' : () --
        | 'raw_data': () -- 
        | 'cropped_raw_data': () -- 
        | 'raw data' : (pandas.DataFrame) --
        | 'x_min' : (float) -- minimum x of full data
        | 'x_max' : (float) -- maximum x of full data
        | 'y_min' : (float) -- minimum y of full data
        | 'y_max' : (float) -- maximum y of full data
        | 'crop_x_min' : (float) -- minimum x of cropped data
        | 'crop_x_max' : (float) -- maximum x of cropped data
        | 'crop_x_min' : (float) -- minimum y of cropped data
        | 'crop_x_max' : (float) -- maximum y of cropped data
        | 'norm' : () --
        | 'analysis data' : (pandas.DataFrame) --
        | 'cropped_raw_data' : (pandas.DataFrame) --

    'processed_data' : (pandas.DataFrame) --
    'crop_mask' : (MaskObj) -- mask created from cropped axes.
    'filter_mask' : (MaskObj) -- mask created by a combination of filters.  Filters are displayed for the user in ``tableWidgetFilters``.
    'polygon_mask' : (MaskObj) -- mask created from selected polygons.
    'cluster_mask' : (MaskObj) -- mask created from selected or inverse selected cluster groups.  Once this mask is set, it cannot be reset unless it is turned off, clustering is recomputed, and selected clusters are used to produce a new mask.
    'mask' : () -- combined mask, derived from filter_mask & 'polygon_mask' & 'crop_mask'
    """
    def __init__(self, sample_id, file_path, outlier_method, negative_method, smoothing_method=None, ui=None):
        super().__init__()

        self.ui = ui

        self.logger_key = 'Data'

        self.sample_id = sample_id
        self.file_path = file_path

        self._outlier_method = outlier_method
        
        self._negative_method = negative_method
        self._smoothing_method = smoothing_method
        self._updating = False

        self._default_lower_bound = 0.005
        self._default_upper_bound = 0.995

        self._default_difference_lower_bound= 0.005
        self._default_difference_upper_bound= 0.995

        self._data_min_quantile = 0.005
        self._data_max_quantile = 0.005
        self._data_min_diff_quantile = 0.005
        self._data_max_diff_quantile = 0.005

        self._nx = 0
        self._ny = 0
        self._dx = 0
        self._dy = 0

        # filter dataframe
        self.filter_df = pd.DataFrame(columns=[
            'use', 'field_type', 'field', 'norm', 'min', 'max', 'operator', 'persistent'
        ])

        # will be AttributeDataFrame once data is loaded into them
        self.raw_data = None
        self.processed_data = None

        self._outlier_method_options = [
            'none',
            'quantile criteria',
            'quantile and distance criteria',
            'Chauvenet criterion',
            'log(n>x) inflection'
        ]

        # matrix order set by x-y sorting, which changes when swapping axes
        self.is_swapped = False

        # data types stored in AttributeDataFrames.column_attributes['data_type']
        self._default_data_types = [
            'Analyte',
            'Ratio',
            'Computed',
            'Special',
            'PCA score',
            'Cluster',
            'Cluster score'
        ]
        self._valid_data_types = self._default_data_types

        self._default_scale_options = ['linear', 'log', 'inv_logit', 'symlog']

        
        # self._default_scale_options = {'standard':['linear', 'log', 'inv_logit', 'symlog'],
        #                                'linear':['linear'],
        #                                'discrete':['discrete']}

        self.order = 'F'
    


        self._scale_options = self._default_scale_options

        self.order = 'F'


    # --------------------------------------
    # Define properties and setter functions
    # --------------------------------------
    # note properties are based on the cropped X and Y values
    @property
    def x(self):
        """numpy.ndarray : Value of x-coordinate associated with map data"""
        return self._x

    @x.setter
    def x(self, new_x):
        if not self._updating:
            self._updating = True
            self._x = new_x
            self._dx = self.x_range / new_x.nunique()
            self._nx = new_x.nunique()
            self._updating = False

    # Define the y property
    @property
    def y(self):
        """numpy.ndarray : Value of y-coordinate associated with map data"""
        return self._y

    @y.setter
    def y(self, new_y):
        if not self._updating:
            self._updating = True
            self._y = new_y
            self._dy = self.y_range / new_y.nunique() 
            self._ny = new_y.nunique()
            self._updating = False

    @property
    def dx(self):
        """float : Width of pixels in x-direction."""
        return self._dx

    @dx.setter
    def dx(self, new_dx):
        if not self._updating:
            self._updating = True

            # Recalculates X for self.raw_data
            # (does not use self.processed_data because the x limits will otherwise be incorrect)
            # X = round(self.raw_data['Xc']/self._dx)
            X = self.raw_data['Xc']/self._dx
            self._dx = new_dx
            X_new = new_dx*X

            # Extract cropped region and update self.processed_data
            self._x = X_new[self.crop_mask]
            self.processed_data['Xc'] = self._x
            
            self._updating = False

            self.notify_observers("dx", self._dx)
        
    @property
    def dy(self):
        """float : Width of pixels in y-direction."""
        return self._dy

    @dy.setter
    def dy(self, new_dy):
        if not self._updating:
            self._updating = True

            # Recalculates Y for self.raw_data
            # (does not use self.processed_data because the y limits will otherwise be incorrect)
            Y = self.raw_data['Y']/self._dy
            self._dy = new_dy
            Y_new = new_dy*Y

            # Extract cropped region and update self.processed_data
            self._y = Y_new[self.crop_mask]
            self.processed_data['Y'] = self._y
            
            self._updating = False

            self.notify_observers("dy", self._dy)
        
    @property
    def nx(self):
        return self._nx
    
    @nx.setter
    def nx(self, new_nx):
        if new_nx == self._nx:
            return

        self._nx = new_nx
        self.notify_observers("nx", self._nx)

    @property
    def ny(self):
        return self._ny
    
    @ny.setter
    def ny(self, new_ny):
        if new_ny == self._ny:
            return

        self._ny = new_ny
        self.notify_observers("ny", self._ny)   

    # Cropped X-axis limits
    @property
    def xlim(self):
        """list : (float, float) Limits of pixels in x-direction."""
        return (self._x.min(), self._x.max()) if self._x is not None else (None, None)

    # Cropped Y-axis limits
    @property
    def ylim(self):
        """list : (float, float) Limits of pixels in y-direction."""
        return (self._y.min(), self._y.max()) if self._y is not None else (None, None)

    @property
    def x_range(self):
        """float : Range of pixels in x-direction."""
        return self._x.max() - self._x.min() if self._x is not None else None

    @property
    def y_range(self):
        """float : Range of pixels in y-direction."""
        return self._y.max() - self._y.min() if self._y is not None else None
    
    @property
    def aspect_ratio(self):
        """float : Aspect ratio of maps (dy / dx)."""
        if self._dx and self._dy:
            return self._dy / self._dx
        return None

    @property
    def array_size(self):
        """tuple : (int, int) Size of map in pixels"""
        return (self._y.nunique(), self._x.nunique())

    @property
    def apply_outlier_to_all(self):
        """bool : flag that indicates whether the outlier method should be applied to all analytes."""
        return self._apply_outlier_to_all
    
    @apply_outlier_to_all.setter
    def apply_outlier_to_all(self, new_apply_outlier_to_all):
        if new_apply_outlier_to_all == self._apply_outlier_to_all:
            return
    
        self._apply_outlier_to_all = new_apply_outlier_to_all
        self.notify_observers("apply_outlier_to_all", new_apply_outlier_to_all)

    @property
    def auto_scale_value(self):
        return self._auto_scale_value
    
    @auto_scale_value.setter
    def auto_scale_value(self, new_auto_scale_value):
        if new_auto_scale_value == self._auto_scale_value:
            return
        self._auto_scale_value = new_auto_scale_value
        self.prep_data()
        self.notify_observers("auto_scale_value", new_auto_scale_value)


    @property
    def outlier_method(self):
        """str : Method for predicting and clipping outliers."""        
        return self._outlier_method

    @outlier_method.setter
    def outlier_method(self, method):
        if method == self._outlier_method:
            return
        self._outlier_method = method
        self.prep_data()
        self.notify_observers("outlier_method", method)

    @property
    def negative_method(self):
        """str : Method for negative handling."""        
        return self._negative_method
 
    @negative_method.setter
    def negative_method(self, method):
        if method == self._negative_method:
            return
        self._negative_method = method
        self.prep_data()
        self.notify_observers("negative_method", method)

    @property
    def data_min_quantile(self):
        """float : minimum quantile used for autoscaling."""
        return self._data_min_quantile
    
    @data_min_quantile.setter
    def data_min_quantile(self, new_data_min_quantile):
        if new_data_min_quantile == self._data_min_quantile:
            return
    
        self._data_min_quantile = new_data_min_quantile
        self.notify_observers("data_min_quantile", new_data_min_quantile)

    @property
    def data_max_quantile(self):
        """float : maximum quantile used for autoscaling."""
        return self._data_max_quantile
    
    @data_max_quantile.setter
    def data_max_quantile(self, new_data_max_quantile):
        if new_data_max_quantile == self._data_max_quantile:
            return
    
        self._data_max_quantile = new_data_max_quantile
        self.notify_observers("data_max_quantile", new_data_max_quantile)

    @property
    def data_min_diff_quantile(self):
        """float : minimum quantile for differences used for autoscaling."""
        return self._data_min_diff_quantile
    
    @data_min_diff_quantile.setter
    def data_min_diff_quantile(self, new_data_min_diff_quantile):
        if new_data_min_diff_quantile == self._data_min_diff_quantile:
            return
    
        self._data_min_diff_quantile = new_data_min_diff_quantile
        self.notify_observers("data_min_diff_quantile", new_data_min_diff_quantile)

    @property
    def data_max_diff_quantile(self):
        """float : maximum quantile for differences used for autoscaling."""
        return self._data_max_diff_quantile
    
    @data_max_diff_quantile.setter
    def data_max_diff_quantile(self, new_data_max_diff_quantile):
        if new_data_max_diff_quantile == self._data_max_diff_quantile:
            return
    
        self._data_max_diff_quantile = new_data_max_diff_quantile
        self.notify_observers("data_max_diff_quantile", new_data_max_diff_quantile)

    @property
    def crop_mask(self):
        """numpy.ndarray: Boolean mask used to crop the raw data. True values will be used."""
        return self._crop_mask
    
    @crop_mask.setter
    def crop_mask(self, new_xlim, new_ylim):
        self.crop=True

        self._crop_mask = (
            (self.raw_data['Xc'] >= new_xlim[0]) & 
            (self.raw_data['Xc'] <= new_xlim[1]) &
            (self.raw_data['Yc'] <= self.raw_data['Yc'].max() - new_ylim[0]) &
            (self.raw_data['Yc'] >= self.raw_data['Yc'].max() - new_ylim[1])
        )

        #crop clipped_analyte_data based on self.crop_mask
        self.raw_data[self.crop_mask].reset_index(drop=True)
        self.processed_data = self.processed_data[self.crop_mask].reset_index(drop=True)

        self.x = self.processed_data['Xc']
        self.y = self.processed_data['Yc']

        self._crop_mask = np.ones_like(self.raw_data['Xc'], dtype=bool)

        self.prep_data()

    @property
    def scale_options(self):
        """list : options for scaling the data."""
        return self._scale_options

    @scale_options.setter
    def scale_options(self, new_list):
        if set(new_list).issubset(self._default_scale_options):
            self._scale_options = new_list
        else:
            raise ValueError("List (new_list) is not a subset of self._default_scale_options.")

    @property
    def valid_data_types(self):
        """list : data types possible for in processed_data."""
        return self._valid_data_types

    @valid_data_types.setter
    def valid_data_types(self, new_list):
        if set(new_list).issubset(self._default_data_types):
            self._valid_data_types = new_list
        else:
            raise ValueError("List (new_list) is not a subset of self._default_data_types.")

    @property
    def current_field(self):
        """str : """
        return self._current_field
    
    @current_field.setter
    def current_field(self, new_field):
        if new_field == self._current_field:
            return

        self._current_field = new_field
        if not hasattr(self,"processed_data"):
            return

        if new_field is None:
            # if new_field is None, use first analyte field
            field = self.processed_data.match_attribute('data_type','Analyte')[0]

            self.negative_method = self.processed_data.get_attribute(field, 'negative_method')
            self.outlier_method = self.processed_data.get_attribute(field, 'outlier_method')
            self.smoothing_method = self.processed_data.get_attribute(field, 'smoothing_method')
            self.data_min_quantile = self.processed_data.get_attribute(field,'lower_bound')
            self.data_max_quantile = self.processed_data.get_attribute(field,'upper_bound')
            self.data_min_diff_quantile = self.processed_data.get_attribute(field,'diff_lower_bound')
            self.data_max_diff_quantile = self.processed_data.get_attribute(field,'diff_upper_bound')
        else:
            # use new_field
            self.negative_method = self.processed_data.get_attribute(new_field, 'negative_method')
            self.outlier_method = self.processed_data.get_attribute(new_field, 'outlier_method')
            self.smoothing_method = self.processed_data.get_attribute(new_field, 'smoothing_method')
            self.data_min_quantile = self.processed_data.get_attribute(new_field,'lower_bound')
            self.data_max_quantile = self.processed_data.get_attribute(new_field,'upper_bound')
            self.data_min_diff_quantile = self.processed_data.get_attribute(new_field,'diff_lower_bound')
            self.data_max_diff_quantile = self.processed_data.get_attribute(new_field,'diff_upper_bound')

        self.notify_observers("apply_process_to_all_data", self._current_field)

    # validation functions
    def _is_valid_oulier_method(self, text):
        """Validates if a the method is a valid string.

        Valid outlier methods include: `'none'`, `'quantile criteria'`, 
        `'quantile and distance criteria'`, `'chauvenet criterion'`, `'log(n>x) inflection'`.

        
        Parameters
        ----------
        text : str
            Ensures the method is a valid oulier method.
        """
        return isinstance(text, str) and text.lower() in self._outlier_method_options

    def reset_data(self):
        """Reverts back to the original data.

        What is reset?

        What is not reset?
        """        
        # load data
        metadata_path = self.file_path.replace('.lame.','.lmdf.')
        metadata_df = None
        if os.path.exists(metadata_path):
            metadata_df = pd.read_csv(self.file_path, engine='c')

        sample_df = pd.read_csv(self.file_path, engine='c')
        sample_df = sample_df.loc[:, ~sample_df.columns.str.contains('^Unnamed')]  # Remove unnamed columns

        # determine column data types
        # initialize all as 'Analyte'
        data_type = ['Analyte']*sample_df.shape[1]

        # identify coordinate columns
        data_type[sample_df.columns.get_loc('Xc')] = 'coordinate'
        data_type[sample_df.columns.get_loc('Yc')] = 'coordinate'

        # identify and ratio columns
        ratio_pattern = re.compile(r'([A-Za-z]+[0-9]*) / ([A-Za-z]+[0-9]*)')

        # List to store column names that match the ratio pattern
        ratio_columns = [col for col in sample_df.columns if ratio_pattern.match(col)]

        # Update the data_type list for ratio columns by finding their index positions
        for col in ratio_columns:
            col_index = sample_df.columns.get_loc(col)
            data_type[col_index] = 'Ratio'

        # use an ExtendedDF.AttributeDataFrame to add attributes to the columns
        # may includes analytes, ratios, and special data
        self.raw_data = AttributeDataFrame(data=sample_df)
        self.raw_data.set_attribute(list(self.raw_data.columns), 'data_type', data_type)

        self.x = self._orig_x = self.raw_data['Xc']
        self.y = self._orig_y = self.raw_data['Yc']
        self._orig_dx = self.dx
        self._orig_dy = self.dy

        # initialize X and Y axes bounds for plotting and cropping, initially the entire map
        self._xlim = [self.raw_data['Xc'].min(), self.raw_data['Xc'].max()]
        self._ylim = [self.raw_data['Yc'].min(), self.raw_data['Yc'].max()]

        # initialize crop flag to false
        self.crop = False

        # Remove the ratio columns from the raw_data and store the rest
        #non_ratio_columns = [col for col in sample_df.columns if col not in ratio_columns]
        #self.raw_data = sample_df[non_ratio_columns]

        # set mask of size of analyte array
        self._crop_mask = np.ones_like(self.raw_data['Xc'].values, dtype=bool)
        self.filter_mask = np.ones_like(self.raw_data['Xc'].values, dtype=bool)
        self.polygon_mask = np.ones_like(self.raw_data['Xc'].values, dtype=bool)
        self.cluster_mask = np.ones_like(self.raw_data['Xc'].values, dtype=bool)
        self.mask = \
            self.crop_mask & \
            self.filter_mask & \
            self.polygon_mask & \
            self.cluster_mask

        self.dim_red_results = {}
        self.cluster_results = {}
        self.silhouette_scores = {}


        # autoscale and negative handling
        self.reset_data_handling()

    def reset_data_handling(self):
        """Resets processed_data back to raw before performing autoscaling.
        
        Any computed fields will be removed."""
        coordinate_columns = self.raw_data.match_attribute(attribute='data_type',value='coordinate')
        self.raw_data.set_attribute(coordinate_columns, 'units', None)
        self.raw_data.set_attribute(coordinate_columns, 'use', False)

        analyte_columns = self.raw_data.match_attribute(attribute='data_type',value='Analyte')
        self.raw_data.set_attribute(analyte_columns, 'units', None)
        self.raw_data.set_attribute(analyte_columns, 'use', True)
        # quantile bounds
        self.raw_data.set_attribute(analyte_columns, 'lower_bound', 0.05)
        self.raw_data.set_attribute(analyte_columns, 'upper_bound', 99.5)
        # quantile bounds for differences
        self.raw_data.set_attribute(analyte_columns, 'diff_lower_bound', 0.05)
        self.raw_data.set_attribute(analyte_columns, 'diff_upper_bound', 99)
        # linear/log scale
        self.raw_data.set_attribute(analyte_columns, 'norm', 'linear')
        self.raw_data.set_attribute(analyte_columns, 'auto_scale', True)

        analyte_columns = self.raw_data.match_attribute(attribute='data_type',value='Ratio')
        self.raw_data.set_attribute(analyte_columns, 'units', None)
        self.raw_data.set_attribute(analyte_columns, 'use', True)
        # quantile bounds
        self.raw_data.set_attribute(analyte_columns, 'lower_bound', self._default_lower_bound)
        self.raw_data.set_attribute(analyte_columns, 'upper_bound', self._default_upper_bound)
        # quantile bounds for differences
        self.raw_data.set_attribute(analyte_columns, 'diff_lower_bound', self._default_difference_lower_bound)
        self.raw_data.set_attribute(analyte_columns, 'diff_upper_bound', self._default_difference_upper_bound)
        # linear/log scale
        self.raw_data.set_attribute(analyte_columns, 'norm', 'linear')
        self.raw_data.set_attribute(analyte_columns, 'auto_scale', True)

        # cluster data
        # This determines the optimal number of clusters and creates cluster indicies that are used for preprocessing.
        # This should only need to be run once on the initial raw data, unless the set of used analytes changes.

        self.cluster_data()

        self.prep_data()
    
    # def update_crop_mask(self):
    #     """Automatically update the crop_mask whenever crop bounds change."""
    #     for analysis_type, df in self.computed_data.items():
    #         if isinstance(df, pd.DataFrame):
    #             df = df[self.crop_mask].reset_index(drop=True)
    #     self.prep_data()

    def reset_resolution(self):
        """Resets dx and dy to initial values."""        
        self.dx = self._orig_dx
        self.dy = self._orig_dy
        self.update_aspect_ratio_controls()

    def swap_xy(self):
        """Swaps data in a SampleObj."""        
        self.is_swapped = not self.is_swapped

        if self.is_swapped:
            self.order = 'C'
        else:
            self.order = 'F'

        self._swap_xy(self.raw_data)
        self._swap_xy(self.processed_data)

        self.x = self.raw_data['Xc']
        self.y = self.raw_data['Yc']

        # swap orientation of original dx and dy to be consistent with X and Y
        self._orig_dx, self._orig_dy = self._orig_dy, self._orig_dx

    def _swap_xy(self, df):
        """Swaps X and Y of a dataframe

        Swaps coordinates for all maps in sample dataframe.

        Parameters
        ----------
        df : pandas.DataFrame
            data frame to swap X and Y coordinates
        """
        xtemp = df['Yc']
        df['Yc'] = df['Xc']
        df['Xc'] = xtemp

        df = df.sort_values(['Yc','Xc'])

    def update_resolution(self, axis, value):
        """Updates DX and DY for a dataframe

        Recalculates X and Y for a dataframe when the user changes the value of
        pixel dimensions Dx or Dy

        Parameter
        ---------
        axis : str
            Indicates axis to update resolution, 'x' or 'y'.
        value: float
            Holds the new value that is used to update.
        """
        # update resolution based on user change
        if axis == 'x':
            self.dx = value
            dx = self.dx
        elif axis == 'y':
            self.dy = value
            dy = self.dy

    def swap_resolution(self):
        """Swaps DX and DY for a dataframe, updates X and Y

        Recalculates X and Y for a dataframe
        """  
        X = round(self.raw_data['Xc']/self.dx)
        Y = round(self.raw_data['Yc']/self.dy)

        Xp = round(self.processed_data['Xc']/self.dx)
        Yp = round(self.processed_data['Yc']/self.dy)

        dx = self.dx
        self.dx = self.dy
        self.dy = dx

        self.raw_data['Xc'] = self.dx*X
        self.raw_data['Yc'] = self.dy*Y

        self.processed_data['Xc'] = self.dx*Xp
        self.processed_data['Yc'] = self.dy*Yp

    def reset_crop(self):
        """Reset the data to the original bounds.

        Reseting the data to the original bounds results in deleting progress on analyses,
        computations, etc.
        """
        # bring up dialog asking if user wishes to proceed
        if not self.confirm_reset():
            return

        # Need to update to keep computed columns?
        self.reset_data()

    def compute_ratio(self, analyte_1, analyte_2):
        """Compute a ratio field from two analytes.

        Ratios are computed on the processed_data, after negative handling, but before autoscaling.

        Parameters
        ----------
        analyte_1 : str
            Analyte field to be used as numerator of ratio.
        analyte_2 : str
            Analyte field to be used as denominator of ratio.
        """
        # Create a mask where both analytes are positive
        mask = (self.processed_data[analyte_1] > 0) & (self.processed_data[analyte_2] > 0)

        # Calculate the ratio and set invalid values to NaN
        ratio_array = np.where(mask, self.processed_data[analyte_1] / self.processed_data[analyte_2], np.nan)

        # Generate the ratio column name
        ratio_name = f'{analyte_1} / {analyte_2}'

        self.add_columns('Ratio',ratio_name,ratio_array)
        self.processed_data.set_attribute(ratio_name, 'use', True)

    # ------------------------------------------
    # Dialogs
    # ------------------------------------------
    def confirm_reset(self):
        """A simple dialog that ensures the user wishes to reset data

        Returns
        -------
        bool
            ``True`` indicates user clicked ``Yes``, ``False`` for ``No``
        """        
        # Create a message box
        msgBox = QMessageBox.warning(self.ui,
            "Confirm Reset", 
            "Resetting to the full map will delete all analyses, computed fields, and reset filters.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        # Show the message box and get the user's response
        response = msgBox.exec()

        # Check the user's response
        if response == QMessageBox.StandardButton.No:
            return False  # User chose not to proceed
        return True  # User chose to proceed

    # ------------------------------------------
    # Methods related to the AttributeDataFrames
    # ------------------------------------------
    # note properties are based on the cropped X and Y values
    def add_columns(self, data_type, column_names, array, mask=None):
        """
        Add one or more columns to the sample object.

        Adds one or more columns to `SampleObj.processed_data`. If a mask is provided,
        the data is placed in the correct rows based on the mask.

        Parameters
        ----------
        data_type : str
            The type of data stored in the columns.
        column_names : str or list of str
            The name or names of the columns to add. If a column already exists, it will be overwritten.
        array : numpy.ndarray
            A 1D array (for single column) or 2D array (for multiple columns). The data to be added.
        mask : numpy.ndarray, optional
            A boolean mask that indicates which rows in the original data should be filled. If not provided,
            the length of `array` must match the height of `processed_data`.

        Returns
        -------
        dict or str
            Returns a message if a column is overwritten, or a dictionary with column names as keys
            and "overwritten" or "added" as values if multiple columns are added.

        Raises
        ------
        ValueError
            Valid types are given in `SampleObj._valid_data_types`.
        ValueError
            The number of columns in the array must match the length of `column_names` (if multiple columns are being added).
        ValueError
            The length of array must match the height of `processed_data` if no mask is provided.
        ValueError
            If a mask is provided, its length must match the height of `processed_data`, and the number of `True` values
            in the mask must match the number of rows in `array`.
        """
        # Ensure column_names is a list, even if adding a single column
        if isinstance(column_names, str):
            column_names = [column_names]
            array = np.expand_dims(array, axis=1)  # Convert 1D array to 2D for consistency

        # Check data type
        if data_type not in self._valid_data_types:
            raise ValueError("The (data_type) provided is not valid. Valid types include: " + ", ".join([f"{dt}" for dt in self._valid_data_types]))

        # Check if number of columns in array matches column_names
        if len(column_names) != array.shape[1]:
            raise ValueError("The number of columns in (array) must match the number of (column_names).")

        # Check array length or mask
        if mask is None:
            # No mask, array length must match the height of processed_data
            if len(array) != self.processed_data.shape[0]:
                raise ValueError("Length of (array) must be the same as the height of the data frame.")
        else:
            # Mask provided, check its validity
            if len(mask) != self.processed_data.shape[0]:
                raise ValueError("The length of (mask) must be the same as the number of rows in the data frame.")
            if array.shape[0] != mask.sum():
                raise ValueError("The number of rows in (array) must match the number of `True` values in the mask.")

        result = {}

        # Loop through each column
        for i, column_name in enumerate(column_names):
            # Check if the column already exists
            if column_name in self.processed_data.columns:
                result[column_name] = "overwritten"
            else:
                result[column_name] = "added"

            # Create the new column array
            if mask is None:
                # No mask: directly use the array for this column
                self.processed_data[column_name] = array[:, i]
            else:
                # Masked: fill a new column initialized with NaNs, then assign the masked rows
                full_column = np.full(self.processed_data.shape[0], np.nan)
                full_column[mask] = array[:, i]
                self.processed_data[column_name] = full_column

            # Set attributes for the newly added column
            self.processed_data.set_attribute(column_name, 'data_type', data_type)
            self.processed_data.set_attribute(column_name, 'units', None)
            self.processed_data.set_attribute(column_name, 'use', False)
            # Set quantile bounds
            self.processed_data.set_attribute(column_name, 'lower_bound', self._default_lower_bound)
            self.processed_data.set_attribute(column_name, 'upper_bound', self._default_upper_bound)
            # Set quantile bounds for differences
            self.processed_data.set_attribute(column_name, 'diff_lower_bound', self._default_difference_lower_bound)
            self.processed_data.set_attribute(column_name, 'diff_upper_bound', self._default_difference_upper_bound)

            self.processed_data.set_attribute(column_name,'label',self.create_label(column_name))

            # Set min and max unmasked values
            amin = np.min(self.processed_data[column_name][mask])
            amax = np.max(self.processed_data[column_name][mask])
            
            if column_name not in ['Xc','Yc']: # do not round 'X' and 'Y' so full extent of map is viewable
                amin = fmt.oround(amin, order=2, toward=0)
                amax = fmt.oround(amax, order=2, toward=1)
            self.processed_data.set_attribute(column_name,'plot_min',amin)
            self.processed_data.set_attribute(column_name,'plot_max',amax)

            # Set additional attributes
            self.processed_data.set_attribute(column_name, 'norm', 'linear')
            self.processed_data.set_attribute(column_name, 'negative_method', None)
            self.processed_data.set_attribute(column_name, 'outlier_method', None)
            self.processed_data.set_attribute(column_name, 'smoothing_method', None)
            self.processed_data.set_attribute(column_name, 'auto_scale', False)
            # add probability axis associated with histograms
            self.processed_data.set_attribute(column_name, 'p_min', None)
            self.processed_data.set_attribute(column_name, 'p_max', None)

        # Return a message if a single column was added, or the result dictionary for multiple columns
        if len(column_names) == 1:
            return result[column_names[0]]

        return result

    def delete_column(self, column_name):
        """Deletes a column and associated attributes from the AttributeDataFrame.

        Parameters
        ----------
        column_name : str
            Name of column to remove.

        Raises
        ------
        ValueError
            Raises an error if the column is not a member of the AttributeDataFrame.
        """        
        # Check if the column exists
        if column_name not in self.processed_data.columns:
            raise ValueError(f"Column {column_name} does not exist in the DataFrame.")
        
        # Remove the column from the DataFrame
        self.processed_data.drop(columns=[column_name], inplace=True)
        
        # Remove associated attributes, if any
        if column_name in self.processed_data.column_attributes:
            del self.processed_data.column_attributes[column_name]


    def apply_field_filters(self):
        """Applies filters based on field values.
        
        Field-based filters are stored in ``self.filter_df``.  This method updates ``self.filter_mask``.
        """        
        # Check if rows in self.data[sample_id]['filter_info'] exist and filter array in current_plot_df
        if self.filter_df.empty:
            self.filter_mask = np.ones_like(self.processed_data['Xc'].values, dtype=bool)
            return

        # by creating a mask based on min and max of the corresponding filter analytes
        for index, filter_row in self.filter_df.iterrows():
            if filter_row['use']:
                field_df = self.get_map_data(filter_row['field'], filter_row['field_type'])
                
                operator = filter_row['operator']
                if operator == 'and':
                    self.filter_mask = self.filter_mask & ((filter_row['min'] <= field_df['array'].values) & (field_df['array'].values <= filter_row['max']))
                elif operator == 'or':
                    self.filter_mask = self.filter_mask | ((filter_row['min'] <= field_df['array'].values) & (field_df['array'].values <= filter_row['max']))

    
    def sort_data(self, method):
        """
        Sorts analyte columns in the raw and processed data according to the specified method.

        This method retrieves a list of analytes from the `processed_data` DataFrame
        and reorders the columns in both `raw_data` and `processed_data` based on the
        sorting strategy provided. The sorting is performed using an external function
        `sort_analytes`, which takes the user-defined `method` and the analyte list as inputs.

        Parameters
        ----------
        method : str
            Sorting method selected by the user. This is passed to `sort_analytes` and
            determines the order in which analytes are arranged (e.g., alphabetical, PCA loadings,
            cluster association, etc.).

        Returns
        -------
        analyte_list : list
            the original list of analytes found in `processed_data`.
        sorted_analyte_list : list
            the list of analytes sorted according to the provided method.
        """ 
        # retrieve analyte_list
        analyte_list = self.processed_data.match_attribute('data_type','Analyte')

        # sort analyte sort based on method chosen by user
        sorted_analyte_list = sort_analytes(method, analyte_list)

        # Check if the current order already matches the desired sorted order
        if analyte_list == sorted_analyte_list:
            return analyte_list, sorted_analyte_list  # No sorting needed

        # Reorder the columns of the DataFrame based on self.analyte_list
        self.raw_data.sort_columns(sorted_analyte_list)
        if hasattr(self, "processed_data"):
            self.processed_data.sort_columns(sorted_analyte_list)

        return analyte_list, sorted_analyte_list

    def create_label(self, column_name):
        """Creates a default label for axes.

        Creates a default label for axes on plots, using the column name in processed_data.

        Parameters
        ----------
        column_name : str
            Column in processed_data.
        """        
        data_type = self.processed_data.get_attribute(column_name,'data_type') 
        label = None
        match data_type:
            case 'Analyte' | 'Analyte (normalized)': 
                symbol, mass = fmt.parse_isotope(column_name)
                if mass:
                    label = f"$^{{{mass}}}${symbol}"
                else:
                    label = f"{symbol}"

                unit = self.processed_data.get_attribute(column_name,'units')
                if data_type == 'Analyte':
                    label = f"{label} ({unit})"
                else: # normalized analyte
                    label = f"{label}$_N$ ({unit})"
            case 'Ratio' | 'Ratio (normalized)':
                field_1 = field.split(' / ')[0]
                field_2 = field.split(' / ')[1]
                symbol_1, mass_1 = fmt.parse_isotope(field_1)
                symbol_2, mass_2 = fmt.parse_isotope(field_2)

                # numerator
                label_1 = ''
                if mass_1: # isotope
                    label_1 = f"$^{{{mass_1}}}${symbol_1}"
                else: # element
                    label_1 = f"{symbol_1}"

                # denominator
                label_2 = ''
                if mass_2: # isotope
                    label_2 = f"$^{{{mass_2}}}${symbol_2}"
                else: # element
                    label_2 = f"{symbol_2}"

                if data_type == 'Ratio':
                    label = f"{label_1} / {label_2}"
                else:   # normalized ratio
                    label = f"{label_1}$_N$ / {label_2}$_N$"
            case _:
                unit = self.processed_data.get_attribute(column_name,'units')
                if unit == None:
                    label = f"{column_name}"
                else:
                    label = f"{column_name} ({unit})"

        return label

    def cluster_data(self):
        """Clusters data for use with data preprocessing

        _extended_summary_
        """
        # Step 1: Clustering
        # ------------------
        # Select columns where 'data_type' attribute is 'Analyte'
        analyte_columns = [col for col in self.raw_data.columns if (self.raw_data.get_attribute(col, 'data_type') == 'Analyte') 
            and (self.raw_data.get_attribute(col, 'use') is not None
            and self.raw_data.get_attribute(col, 'use')) ]

        # Extract the analyte data
        analyte_data = self.raw_data[analyte_columns].values

        # Mask invalid data (e.g., NaN, inf)
        mask_valid = np.isfinite(analyte_data).all(axis=1)

        # Filter out the invalid data
        analyte_data = analyte_data[mask_valid]

        # Calculate percentiles for central bulk of the valid data
        lower_percentile = np.percentile(analyte_data, 1.25, axis=0)
        upper_percentile = np.percentile(analyte_data, 98.75, axis=0)

        # Create a mask for central bulk of the data (within the range of percentiles)
        mask_central = np.all((analyte_data >= lower_percentile) & (analyte_data <= upper_percentile), axis=1)

        # Data for optimal cluster calculation: central 97.5%
        # Determine the optimal number of clusters using filtered_data
        optimal_clusters = self.k_optimal_clusters(analyte_data[mask_central])

        # Fit KMeans with the optimal number of clusters
        kmeans = KMeans(n_clusters=optimal_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(analyte_data)

        # Create a full-sized vector with NaN values where mask is False
        self.cluster_labels = np.full(mask_valid.shape[0], np.nan)
        self.cluster_labels[mask_valid] = cluster_labels

        # if DEBUG_PLOT:
        #     # Reshape the full_labels array based on unique X and Y values
        #     x_unique = self.raw_data['Xc'].nunique()  # Assuming 'X' is a column in raw_data
        #     y_unique = self.raw_data['Yc'].nunique()  # Assuming 'Y' is a column in raw_data

        #     # Ensure the reshaped array has the same shape as the spatial grid
        #     reshaped_labels = np.reshape(self.cluster_labels, (y_unique, x_unique), order='F')

        #     # Plot using imshow
        #     fig, ax1 = plt.subplots() 
        #     cax = ax1.imshow(reshaped_labels, cmap='viridis', interpolation='none')
        #     cbar = fig.colorbar(cax, label='Cluster Labels', ax=ax1, orientation='horizontal')
        #     ax1.set_title('Cluster Labels with NaN Handling')
        #     ax1.set_xlabel('X')
        #     ax1.set_ylabel('Y')
        #     fig.show()

    def prep_data(self, field=None):
        """Applies adjustments to data data prior to analyses and plotting.

        This method applies a workflow to adjust data to limit the number of data that are otherwise
        unusable due to incorrect calibrations, particularly for low and high element concentration regions.
        
        Data are adjusted according to the proceedure:
        | Determine optimal number of clusters and use it to classify the data using kmeans.
        | Transform each cluster, by handling negative data.  The method of negative handling is set by ``MainWindow.comboBoxNegativeMethod.currentText()``.
        | Compute ratios not imported (i.e., not in raw_data).
        | Determine outliers and limit their impact on analyses by clipping/autoscaling

        These calculations start from the cropped data, but do not include chemical, polygonal, or cluster filtering.

        Raises
        ------
        AssertionError
            processed_data has not yet been initialized.  processed_data should be created when the sample is initialized and prep_data is
            run for the first time.
        """ 
        attribute_df = None
        analyte_columns = []
        ratio_columns = []
        if (field == None) or (field == 'all'):
            # Select columns where 'data_type' attribute is 'Analyte'
            analyte_columns = self.raw_data.match_attributes({'data_type': 'Analyte', 'use': True})
            # analyte_columns = self.raw_data.match_attribute('data_type', 'Analyte')
            # analyte_columns = [col for col in analyte_columns if self.raw_data.get_attribute(col, 'use') is True]
            # analyte_columns = [col for col in self.raw_data.columns if (self.raw_data.get_attribute(col, 'data_type') == 'Analyte') 
                # and (self.raw_data.get_attribute(col, 'use') is not None
                # and self.raw_data.get_attribute(col, 'use')) ]

            # Select columns where 'data_type' attribute is 'Ratio'
            ratio_columns = self.raw_data.match_attributes({'data_type': 'Ratio', 'use': True})
            # ratio_columns = self.raw_data.match_attribute('data_type', 'Ratio')
            # ratio_columns = [col for col in ratio_columns if self.raw_data.get_attribute(col, 'use') is True]
            # ratio_columns = [col for col in self.raw_data.columns if (self.raw_data.get_attribute(col, 'data_type') == 'Ratio') 
            #     and (self.raw_data.get_attribute(col, 'use') is not None
            #     and self.raw_data.get_attribute(col, 'use')) ]

            columns = analyte_columns + ratio_columns

            # this needs to be updated to handle different negative handling methods for different fields.
            # may need to create a copy of processed_data overwriting with raw_data
            negative_method = self._negative_method
            self.processed_data = copy.deepcopy(self.raw_data)
            self.processed_data.set_attribute(analyte_columns, 'negative_method', negative_method)
        else:
            columns = field

        if not hasattr(self, 'processed_data'):
            raise AssertionError("processed_data has not yet been defined.")

        # Handle negative values
        # ----------------------
        # for col in analyte_columns:
        #     if col not in self.raw_data.columns:
        #         continue

        #     for idx in np.unique(self.cluster_labels):
        #         if np.isnan(idx):
        #             continue
        #         cluster_mask = self.cluster_labels == idx
        #         print(f"{(col, idx)} before: {sum(self.processed_data[col] < 0)}, {sum(self.processed_data[col][cluster_mask] < 0)}")
        #         transformed_data = self.transform_array(self.processed_data[col][cluster_mask],self.processed_data.get_attribute(col,'negative_method'))
        #         self.processed_data.loc[cluster_mask, col] = transformed_data
        #         print(f"{(col, idx)} after : {sum(self.processed_data[col] < 0)}, {sum(self.processed_data[col][cluster_mask] < 0)}, {sum(transformed_data < 0)}")

        # Compute ratios not included in raw_data
        # ---------------------------------------
        if ((field is None) or (field == 'all')) and (attribute_df is not None):
            ratios = attribute_df.columns[(data_type == 'Ratio').any()]

            ratios_not_in_raw_data = [col for col in ratios if col not in ratio_columns]

            for col in ratios_not_in_raw_data:
                columns = columns + col
                self.compute_ratio(analyte_1, analyte_2)

            self.processed_data.set_attribute(ratios_not_in_raw_data, 'lower_bound', attribute_df.loc['lower_bound', ratios_not_in_raw_data].tolist())
            self.processed_data.set_attribute(ratios_not_in_raw_data, 'upper_bound', attribute_df.loc['upper_bound', ratios_not_in_raw_data].tolist())
            self.processed_data.set_attribute(ratios_not_in_raw_data, 'diff_upper_bound', attribute_df.loc['diff_upper_bound', ratios_not_in_raw_data].tolist())
            self.processed_data.set_attribute(ratios_not_in_raw_data, 'diff_lower_bound', attribute_df.loc['diff_lower_bound', ratios_not_in_raw_data].tolist())
            self.processed_data.set_attribute(ratios_not_in_raw_data, 'norm', attribute_df.loc['norm', ratios_not_in_raw_data].tolist())
            self.processed_data.set_attribute(ratios_not_in_raw_data, 'auto_scale', attribute_df.loc['auto_scale', ratios_not_in_raw_data].tolist())


        # Clip outliers / autoscale the data
        # ------------------
        # loop over all fields
        for col in (col for col in self.processed_data.columns if self.processed_data.get_attribute(col, 'data_type') != 'coordinate'):

            lq = self.processed_data.get_attribute(col, 'lower_bound')
            uq = self.processed_data.get_attribute(col, 'upper_bound')
            # skip is autoscale is False for column
            if not self.processed_data.get_attribute(col, 'autoscale'):
                #clip data using ub and lb
                lq_val = np.nanpercentile(self.processed_data[col], lq, axis=0)
                uq_val = np.nanpercentile(self.processed_data[col], uq, axis=0)
                self.processed_data[col] = np.clip(self.processed_data[col], lq_val, uq_val)
                continue

            d_lq = self.processed_data.get_attribute(col, 'diff_lower_bound')
            d_uq = self.processed_data.get_attribute(col, 'diff_upper_bound')

            match self.processed_data.get_attribute(col, 'units'):
                case 'ppm':
                    compositional = True
                    max_val = 1e6
                    shift_percentile = 90
                case 'cps':
                    compositional = True
                    max_val = 1e6
                    shift_percentile = 90
                case _:
                    compositional = True
                    max_val = 1e6
                    shift_percentile = 90

            # Apply robust outlier detection to each cluster
            for idx in np.unique(self.cluster_labels):
                cluster_mask = (self.cluster_labels == idx)

                transformed_data = self.clip_outliers(self.processed_data[col][cluster_mask], lq, uq, d_lq, d_uq)
                self.processed_data.loc[cluster_mask, col] = transformed_data

                transformed_data = self.quantile_and_difference(self.processed_data[col][cluster_mask], lq, uq, d_lq, d_uq, compositional, max_val)
                self.processed_data.loc[cluster_mask, col] = transformed_data

        
        # Compute special fields?
        # -----------------------
        for col in self.processed_data.columns:
            self.processed_data.set_attribute(col,'label',self.create_label(col))
            
            # Set min and max unmasked values
            amin = np.min(self.processed_data[col])
            amax = np.max(self.processed_data[col])
            
            if col not in ['Xc','Yc']: # do not round 'X' and 'Y' so full extent of map is viewable
                amin = fmt.oround(amin, order=2, toward=0)
                amax = fmt.oround(amax, order=2, toward=1)
            self.processed_data.set_attribute(col,'plot_min',amin)
            self.processed_data.set_attribute(col,'plot_max',amax)

    def k_optimal_clusters(self, data, max_clusters=int(10)):
        """
        Predicts the optimal number of clusters.

        Predicts the optimal number of k-means clusters using the elbow method based on the within-cluster sum of squares (WCSS):

        .. math::
            WCSS = \\sum_{i=1}^k \\sum_{x \\in C_i} (x - \\mu_i)^2

        The optimal number of clusters is determined by selecting the k-value corresponding to the maximum value of the second derivative of WCSS.

        Parameters
        ----------
        data : numpy.ndarray
            Data used in clustering. Make sure it has NaN and ±inf values removed.
        max_clusters : int, optional
            Computes cluster results from 1 to ``max_clusters``, by default 10.

        Returns
        -------
        int
            The optimal number of k-means clusters.
        """
        inertia = []

        # clip outliers and make entirely positive
        percentile = 2.5
        min_pos = 1e-2
        for i in range(data.shape[1]):
            # Find the minimum positive value in the column
            col_min_pos = np.min(data[data[:, i] > 0, i])
            min_threshold = max(col_min_pos, min_pos)  # Choose the larger of min positive or 0.01

            # Set all values less than the threshold to the threshold value
            data[:, i] = np.where(data[:, i] < min_threshold, min_threshold, data[:, i])

        lower_bound = np.percentile(data, percentile, axis=0)
        upper_bound = np.percentile(data, 100-percentile, axis=0)

        # Clip values to the 5th and 95th percentiles per column
        data = np.log(np.clip(data, lower_bound, upper_bound))
        
        # Perform KMeans for cluster numbers from 1 to max_clusters
        for n_clusters in range(1, max_clusters+1):
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            kmeans.fit(data)
            inertia.append(kmeans.inertia_)  # Record the inertia (sum of squared distances)
        
        # Calculate second-order difference (second derivative)
        second_derivative = np.diff(np.diff(inertia))

        # Identify the elbow point
        # add 2 to the maximum index to obtain the optimal number of clusters,
        # 1 because it starts at 0 and 1 because it is the second derivative
        optimal_k = np.argmax(second_derivative) + 2  # Example heuristic

        # if DEBUG_PLOT:
        #     # Plot inertia
        #     fig, ax1 = plt.subplots()

        #     ax1.plot(range(1, max_clusters+1), inertia, marker='o', color='b', label='Inertia')
        #     ax1.set_xlabel('Number of clusters')
        #     ax1.set_ylabel('Inertia', color='b')
        #     ax1.tick_params(axis='y', labelcolor='b')
        #     ax1.set_title('Elbow Method for Optimal Clusters')
        #     ax1.axvline(x=optimal_k, linestyle='--', color='r', label=f'Elbow at k={optimal_k}')


        #     # Create a secondary y-axis to plot the second derivative
        #     ax2 = ax1.twinx()
        #     ax2.plot(range(2, max_clusters), second_derivative, marker='x', color='r', label='2nd Derivative')
        #     ax2.set_ylabel('2nd Derivative', color='r')
        #     ax2.tick_params(axis='y', labelcolor='r')

        #     self.logger.print(f"Second derivative of inertia: {second_derivative}")
        #     self.logger.print(f"Optimal number of clusters: {optimal_k}")

        return optimal_k


    def clip_outliers(self, array, outlier_method, pl=None, pu=None, dpl=None, dpu=None):
        """Attempts to remove outliers to by a method selected by the user.

        Parameters
        ----------
        array : numpy.ndarray
            Data vector
        outlier_method : str
            Method for removing outliers
        pl : float, optional
            Lower percentile bound required by selected methods
        pu : float, optional
            Upper percentile bound required by selected methods
        dpl : float, optional
            Lower percentile bound for distances required by selected methods
        dpu : float, optional
            Upper percentile bound for distances required by selected methods

        Returns
        -------
        numpy.ndarray
            Clipped data vector
        """        
        t_array = np.copy(array)

        match outlier_method.lower():
            case 'none':
                return t_array

            case 'quantile criteria':
                ql = np.nanpercentile(array, pl, axis=0)
                qu = np.nanpercentile(array, pu, axis=0)
                t_array = np.clip(array, ql, qu)
                
            case 'quantile and distance criteria':
                t_array = quantile_and_difference(array, pl, pu, dpl, dpu, compositional, max_val)
            case 'chauvenet criterion':
                mask = chauvenet_criterion(array, threshold=1)
                if not any(mask):
                    return t_array

                min_value = np.min(t_array[mask], axis=0)
                max_value = np.max(t_array[mask], axis=0)

                t_array[~mask & (t_array < min_value)] = min_value
                t_array[~mask & (t_array > max_value)] = max_value

            case 'log(n>x) inflection':
                pass

        return t_array

    def transform_array(self, array, negative_method):
        """
        Negative and zero handling with clustering for noise detection.

        Parameters
        ----------
        array : numpy.ndarray
            Input data
        negative_method : str
            Method for handling negative values
        Returns
        -------
        numpy.ndarray
            Transformed data
        """
        match negative_method.lower():
            case 'ignore negatives':
                # do nothing, the values remain unchanged
                t_array = np.copy(array)
                t_array = np.where(t_array > 0, t_array, np.nan)

            case 'minimum positive':
                # shift all negative values to be a minimum value
                min_positive_value = np.nanmin(array[array > 0])
                t_array = np.where(array < 0, min_positive_value, array)

            case 'gradual shift':
                # Handle multidimensional case (2D array)
                if array.ndim == 2:
                    min_val = np.nanmin(array, axis=0, keepdims=True) - 0.0001
                    max_val = np.nanmax(array, axis=0, keepdims=True)
                    t_array = np.where(min_val <= 0, 
                                    (max_val * (array - min_val)) / (max_val - min_val),
                                    array)
                else:
                    # 1D array case
                    min_val = np.nanmin(array) - 0.0001
                    max_val = np.nanmax(array)
                    t_array = (max_val * (array - min_val)) / (max_val - min_val) if min_val < 0 else np.copy(array)

            case 'yeo-johnson transform':
                t_array, _ = yeojohnson(array)

        return t_array

    def update_norm(self, norm=None, field=None):
        """Update the norm of the data.

        Parameters
        ----------
        sample_id : str
            Sample identifier
        norm : str, optional
            Data scale method ``linear`` or ``log``, by default None
        field : str, optional
            Field to change the norm, by default None
        update : bool, optional
            Update the scale information of the data, by default False
        """ 
        if field is not None: #if normalising single analyte
            self.processed_data.set_attribute(field,'norm',norm)
        else: #if normalising all analytes in sample
            self.processed_data.set_attribute(self.processed_data.match_attribute('data_type','Analyte'),'norm',norm)

        self.prep_data(field)

    def get_map_data(self, field, field_type='Analyte', norm=False, processed=True):
        """
        Retrieves and processes the mapping data for the given sample and analytes

        The method also updates certain parameters in the analyte data frame related to scaling.
        Based on the plot type, this method internally calls the appropriate plotting functions.

        Parameters
        ----------
        field : str
            Name of field to plot. By default `None`.
        field_type : str, optional
            Type of field to plot. Types include 'Analyte', 'Ratio', 'PCA', 'Cluster', 'Cluster score',
            'Special', 'Computed'. By default `'Analyte'`
        norm : str
            Scale data as linear, log, etc. based on stored norm.  If scale_data is `False`, the
            data are returned with a linear scale.  By default `False`.

        Returns
        -------
        pandas.DataFrame
            Processed data for plotting. This is only returned if analysis_type is not 'laser' or 'hist'.
        """
        # ----begin debugging----
        # print('[get_map_data] sample_id: '+sample_id+'   field_type: '+field_type+'   field: '+field)
        # ----end debugging----

        # if sample_id != self.sample_id:
        #     #axis mask is not used when plot analytes of a different sample
        #     crop_mask  = np.ones_like( self.raw_data['Xc'], dtype=bool)
        # else:
        #     crop_mask = self.data[self.sample_id]['crop_mask']
        
        # retrieve axis mask for that sample
        #crop_mask = self.crop_mask
        
        #crop plot if filter applied
        df = self.processed_data[['Xc','Yc']]

        match field_type:
            case 'Analyte' | 'Analyte (normalized)':
                # unnormalized
                if processed:
                    df['array'] = self.processed_data[field].values
                else:
                    df['array'] = self.raw_data[field].values

                #norm = self.processed_data.get_attribute(field, 'norm')
                
                #perform scaling for groups of analytes with same norm parameter
                match norm:
                    case 'log':
                        df['array'] = np.where((~np.isnan(df['array'])) & (df['array'] > 0), np.log10(df['array']), np.nan)
                    case 'inv_logit':
                        # Handle division by zero and NaN values
                        with np.errstate(divide='ignore', invalid='ignore'):
                            df['array'] = np.where((~np.isnan(df['array'])) & (df['array'] > 0), fmt.inv_logit(df['array']), np.nan)
                    case 'symlog':
                        df['array'] = np.where((~np.isnan(df['array'])) & (df['array'] > 0), fmt.symlog(df['array']), np.nan)
                
                # normalize
                if 'normalized' in field_type:
                    refval = self.ref_chem[re.sub(r'\d', '', field).lower()]
                    df['array'] = df['array'] / refval

            case 'Ratio' | 'Ratio (normalized)':
                field_1 = field.split(' / ')[0]
                field_2 = field.split(' / ')[1]

                # unnormalized
                df['array'] = self.processed_data[field].values
                
                # normalize
                if 'normalized' in field_type:
                    refval_1 = self.ref_chem[re.sub(r'\d', '', field_1).lower()]
                    refval_2 = self.ref_chem[re.sub(r'\d', '', field_2).lower()]
                    df['array'] = df['array'] * (refval_2 / refval_1)

                #get norm value
                if norm == 'log':
                    df['array'] = np.where((~np.isnan(df['array'])) & (df['array'] > 0), np.log10(df['array']), np.nan)

                elif norm == 'logit':
                    # Handle division by zero and NaN values
                    with np.errstate(divide='ignore', invalid='ignore'):
                        df['array'] = np.where((~np.isnan(df['array'])) & (df['array'] > 0), np.log10(df['array'] / (10**6 - df['array'])), np.nan)

            case _:#'PCA score' | 'Cluster' | 'Cluster score' | 'Special' | 'Computed':
                df['array'] = self.processed_data[field].values
            
        # ----begin debugging----
        # print(df.columns)
        # ----end debugging----
        return df

    def get_processed_data(self):
        """Gets the processed data for analysis

        Returns
        -------
        pandas.DataFrame
            Filtered data frame 
        bool
            Analytes included from processed data
        """
        if self.sample_id == '':
            return

        # return normalised, filtered data with that will be used for analysis
        #use_analytes = self.data[self.sample_id]['Analyte_info'].loc[(self.data[self.sample_id]['Analyte_info']['use']==True), 'Analytes'].values
        use_analytes = self.processed_data.match_attributes({'data_type': 'Analyte', 'use': True})

        df = self.processed_data[use_analytes]

        #perform scaling for groups of analytes with same norm parameter
        for norm in self.scale_options:
            analyte_set = self.processed_data.match_attributes({'data_type': 'Analyte', 'use': True, 'norm': norm})
            if not analyte_set:
                continue

            tmp_array = df[analyte_set].values
            if norm == 'log':
                # np.nanlog handles NaN value
                df[analyte_set] = np.where(~np.isnan(tmp_array), np.log10(tmp_array))
            elif norm == 'symlog':
                df[analyte_set] = np.where(~np.isnan(tmp_array), symlog(tmp_array))
            elif norm == 'inv_logit':
                # Handle division by zero and NaN values
                with np.errstate(divide='ignore', invalid='ignore'):
                    df[analyte_set] = np.where(~np.isnan(tmp_array), inv_logit(tmp_array))

        # Combine the two masks to create a final mask
        nan_mask = df.notna().all(axis=1)
        
        
        # mask nan values and add to self.mask
        self.mask = self.mask  & nan_mask.values

        return df, use_analytes
    
    # extracts data for scatter plot
    def get_vector(self, field_type, field, norm='linear', processed=True):
        """Creates a dictionary of values for plotting

        Returns
        -------
        dict
            Dictionary with array and additional relevant plot data, contains
            'field', 'type', 'label', and 'array'.
        """
        # initialize dictionary
        value_dict = {'type': field_type, 'field': field, 'label': None, 'array': None}

        if field == '':
            return value_dict

        # add label
        unit = self.processed_data.get_attribute(field, 'unit')
        if unit is None:
            value_dict['label'] = value_dict['field']
        else:
            value_dict['label'] = value_dict['field'] + ' (' + unit + ')'

        # add array
        df = self.get_map_data(field=field, field_type=field_type, norm='linear', processed=processed)
        value_dict['array'] = df['array'][self.mask].values if not df.empty else []

        return value_dict

    # def outlier_detection(self, lq=0.0005, uq=99.5, d_lq=9.95 , d_uq=99):
    #     """_summary_

    #     _extended_summary_

    #     Parameters
    #     ----------
    #     data : _type_
    #         _description_
    #     lq : float, optional
    #         _description_, by default 0.0005
    #     uq : float, optional
    #         _description_, by default 99.5
    #     d_lq : float, optional
    #         _description_, by default 9.95
    #     d_uq : int, optional
    #         _description_, by default 99

    #     Returns
    #     -------
    #     _type_
    #         _description_
    #     """        
    #     # Ensure data is a numpy array
    #     data = np.array(data)

    #     # Shift values to positive concentrations
    #     v0 = np.nanmin(data, axis=0) - 0.001
    #     data_shifted = np.log10(data - v0)

    #     # Calculate required quantiles and differences
    #     lq_val = np.nanpercentile(data_shifted, lq, axis=0)
    #     uq_val = np.nanpercentile(data_shifted, uq, axis=0)
    #     sorted_indices = np.argsort(data_shifted, axis=0)
    #     sorted_data = np.take_along_axis(data_shifted, sorted_indices, axis=0)


    #     diff_sorted_data = np.diff(sorted_data, axis=0)
    #     # Adding a 0 to the beginning of each column to account for the reduction in size by np.diff
    #     diff_sorted_data = np.insert(diff_sorted_data, 0, 0, axis=0)
    #     diff_array_uq_val = np.nanpercentile(diff_sorted_data, d_uq, axis=0)
    #     diff_array_lq_val = np.nanpercentile(diff_sorted_data, d_lq, axis=0)
    #     upper_cond = (sorted_data > uq_val) & (diff_sorted_data > diff_array_uq_val)

    #     # Initialize arrays for results
    #     clipped_data = np.copy(sorted_data)

    #     # Upper bound outlier filter
    #     for col in range(sorted_data.shape[1]):
    #         up_indices = np.where(upper_cond[:, col])[0]
    #         if len(up_indices) > 0:
    #             uq_outlier_index = up_indices[0]
    #             clipped_data[uq_outlier_index:, col] = clipped_data[uq_outlier_index-1, col]

    #     lower_cond = (sorted_data < lq_val) & (diff_sorted_data > diff_array_lq_val)
    #     # Lower bound outlier filter
    #     for col in range(sorted_data.shape[1]):
    #         low_indices = np.where(lower_cond[:, col])[0]
    #         if len(low_indices) > 0:
    #             lq_outlier_index = low_indices[-1]
    #             clipped_data[:lq_outlier_index+1, col] = clipped_data[lq_outlier_index+1, col]

    #     clipped_data = np.take_along_axis(clipped_data, np.argsort(sorted_indices, axis=0), axis=0)
    #     # Unshift the data
    #     clipped_data = 10**clipped_data + v0

    #     return clipped_data

    # def transform_array(array, negative_method):
    #     """Negative and zero handling

    #     Parameters
    #     ----------
    #     array : numpy.ndarray
    #         Input data
    #     negative_method : str
    #         negative_method obtained from analyte info
    #     Returns
    #     -------
    #     numpy.ndarray
    #         Transformed data
    #     """
    #     match negative_method.lower():
    #         case 'gradual shift':
    #             if array.ndim == 2:
    #                 # Calculate min and max values for each column and adjust their shapes for broadcasting
    #                 min_val = np.nanmin(array, axis=0, keepdims=True) - 0.0001
    #                 max_val = np.nanmax(array, axis=0, keepdims=True)

    #                 # Adjust the shape of min_val and max_val for broadcasting
    #                 adjusted_min_val = min_val
    #                 adjusted_max_val = max_val

    #                 # Check if min values are less than or equal 0
    #                 min_leq_zero = adjusted_min_val <= 0

    #                 # Perform transformation with broadcasting
    #                 t_array = np.where(
    #                     min_leq_zero,
    #                     (adjusted_max_val * (array - adjusted_min_val)) / (adjusted_max_val - adjusted_min_val),
    #                     array
    #                 )
    #             else:
    #                 # 1D array case, similar to original logic
    #                 min_val = np.nanmin(array) - 0.0001
    #                 max_val = np.nanmax(array)
    #                 if min_val < 0:
    #                     t_array = (max_val * (array - min_val)) / (max_val - min_val)
    #                 else:
    #                     t_array = np.copy(array)
    #             return t_array

    def auto_scale(self,sample_id, field, update = False):
        """Auto-scales pixel values in map

        Executes on ``MainWindow.toolButtonAutoScale`` click.

        Outliers can make it difficult to view the variations of values within a map.
        This is a larger problem for linear scales, but can happen when log-scaled. Auto-
        scaling the data clips the values at a lower and upper bound.  Auto-scaling may be
        acceptable as minerals that were not specifically calibrated can have erroneously
        high or low (even negative) values.

        Parameters
        ----------
        update : bool
            Update auto scale parameters, by default, False
        """
        if '/' in field:
            analyte_1, analyte_2 = field.split(' / ')
        else:
            analyte_1 = field
            analyte_2 = None



        lb = self.data_min_quantile
        ub = self.data_max_quantile
        d_lb = self.data_min_diff_quantile
        d_ub = self.data_max_diff_quantile
        auto_scale = self.auto_scale_value

        if auto_scale and not update:
            #reset to default auto scale values
            lb = 0.05
            ub = 99.5
            d_lb = 99
            d_ub = 99

            self.data_min_quantile = lb
            self.data_max_quantile = ub
            self.data_min_diff_quantile.value = d_lb
            self.data_max_diff_quantile = d_ub
            self.auto_scale_value = True

        elif not auto_scale and not update:
            # show unbounded plot when auto scale switched off
            lb = 0
            ub = 100
            self.data_min_quantile = lb
            self.data_max_quantile = ub
            self.data_min_diff_quantile.setEnabled(False)
            self.auto_scale_value = False

        # if update is true
        if analyte_1 and not analyte_2:
            if (self.apply_outlier_to_all):
                # Apply to all analytes in sample
                columns = self.processed_data.columns

                # clear existing plot info from tree to ensure saved plots using most recent data
                for tree in ['Analyte', 'Analyte (normalized)', 'Ratio', 'Ratio (normalized)']:
                    self.plot_tree.clear_tree_data(tree)
            else:
                columns = analyte_1

            # update column attributes
            self.processed_data.set_attribute(columns, 'auto_scale', auto_scale)
            self.processed_data.set_attribute(columns, 'upper_bound', ub)
            self.processed_data.set_attribute(columns, 'lower_bound', lb)
            self.processed_data.set_attribute(columns, 'diff_upper_bound', d_ub)
            self.processed_data.set_attribute(columns, 'diff_lower_bound', d_lb)
            self.processed_data.set_attribute(columns, 'negative_method', self.comboBoxNegativeMethod.currentText())

            # update data with new auto-scale/negative handling
            self.prep_data(sample_id)
            

        # else:
        #     if self.apply_outlier_to_all:
        #         # Apply to all ratios in sample
        #         self.processed_data['ratio_info']['auto_scale'] = auto_scale
        #         self.processed_data['ratio_info']['upper_bound']= ub
        #         self.processed_data['ratio_info']['lower_bound'] = lb
        #         self.processed_data['ratio_info']['d_l_bound'] = d_lb
        #         self.processed_data['ratio_info']['d_u_bound'] = d_ub
        #         self.prep_data(sample_id)
        #     else:
        #         self.processed_data['ratio_info'].loc[ (self.processed_data['ratio_info']['Analyte_1']==analyte_1)
        #                                     & (self.processed_data['ratio_info']['Analyte_2']==analyte_2),'auto_scale']  = auto_scale
        #         self.processed_data['ratio_info'].loc[ (self.processed_data['ratio_info']['Analyte_1']==analyte_1)
        #                                     & (self.processed_data['ratio_info']['Analyte_2']==analyte_2),
        #                                     ['upper_bound','lower_bound','d_l_bound', 'd_u_bound']] = [ub,lb,d_lb, d_ub]
        #         self.prep_data(sample_id, analyte_1,analyte_2)
        return True  # User chose to proceed



@auto_log_methods(logger_key='Data')
class LaserSampleObj(SampleObj):
    def __init__(self, sample_id, file_path, outlier_method, negative_method, smoothing_method=None, ref_chem=None, ui=None):
        super().__init__(sample_id, file_path, outlier_method, negative_method, smoothing_method=smoothing_method, ui=ui)
        self.ui = ui
        self.logger_key = 'Data'

        self._current_field = None
        self._ref_chem = ref_chem

        self.polygon = {}
        self.profile = {}

        # filter dataframe
        self.filter_df = pd.DataFrame()
        self.filter_df = pd.DataFrame(columns=['use', 'field_type', 'field', 'norm', 'min', 'max', 'operator', 'persistent'])

        self.spotdata = AttributeDataFrame()

        self.reset_data()


    # --------------------------------------
    # Define properties and setter functions
    # --------------------------------------
    # note properties are based on the cropped X and Y values
    
    @property
    def ref_chem(self):
        """dict : Reference chemistry"""
        return self._ref_chem

    @ref_chem.setter
    def ref_chem(self, d):
        self._ref_chem = d

@auto_log_methods(logger_key='Data')
class XRFSampleObj(SampleObj):
    def __init__(self, sample_id, file_path, outlier_method, negative_method, smoothing_method=None, ui=None):
        super().__init__(self, sample_id, file_path, outlier_method, negative_method, smoothing_method=smoothing_method, ui=ui)
        self.ui = ui
        self.logger_key = 'Data'