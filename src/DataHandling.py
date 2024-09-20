import re, copy
import numpy as np
import pandas as pd
from src.ExtendedDF import AttributeDataFrame
from scipy.stats import yeojohnson
from kneed import KneeLocator
from sklearn.cluster import DBSCAN
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

class SampleObj:
    """Creates a sample object to store and manipulate geochemical data in map form
    
    The sample object is initially constructed from the data within a *.lame.csv file and loaded into
    the ``raw_data`` dataframe.  The sample object also contains a number of properties in addition
    to the input data.  These include metadata that are linked to each column.  To make this link,
    the dataframe is initialized as an ``ExtendedDF.AttributeDataFrame``, which brings with it a
    number of methods to set, get and search the dataframe's metadata.

    
    Methods
    -------
    update_crop_mask :
        Automatically update the crop_mask whenever crop bounds change.
    reset_crop : 
        Resets dataframe to original bounds.
    update_resolution :
    prep_data :
    outlier_detection :
    transform_array :
    swap_xy :

            | 'analyte_info' : (dataframe) -- holds information regarding each analyte in sample id,
                | 'analytes' (str) -- name of analyte
                | 'sample_id' (str) -- sample id
                | 'norm' (str) -- type of normalisation used(linear,log,logit)
                | 'upper_bound' (float) -- upper bound for autoscaling/scaling
                | 'lower_bound' (float) -- lower bound for autoscaling/scaling
                | 'd_l_bound' (float) -- difference lower bound for autoscaling
                | 'd_u_bound' (float) -- difference upper bound for autoscaling
                | 'v_min' (float) -- max value of analyte
                | 'v_max' (float) -- min value of analyte
                | 'auto_scale' (bool) -- indicates whether auto_scaling is switched on for that analyte, use percentile bounds if False
                | 'use' (bool) -- indicates whether the analyte is being used in the analysis
            | 'ratio_info' : (dataframe) -- holds information  regarding computerd ratios 
                | 'analyte_1' (str) -- name of analyte at numerator of ratio
                | 'analyte_2' (str) -- name of analyte at denominator of ratio
                | 'norm' (str) -- type of normalisation used(linear,log,logit)
                | 'upper_bound' (float) --  upper bound for autoscaling/scaling
                | 'lower_bound' (float) --  lower bound for autoscaling/scaling
                | 'd_l_bound' (float) --  difference lower bound for autoscaling
                | 'd_u_bound' (float) --  difference upper bound for autoscaling
                | 'v_min' (float) -- max value of analyte
                | 'v_max' (float) -- min value of analyte
                | 'auto_scale' (bool) -- indicates whether auto_scaling is switched on for that analyte, use percentile bounds if False
                | 'use' (bool) -- indicates whether the analyte is being used in the analysis
            
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
            
        | 'ratio_info' : (dataframe) --
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
        | 'computed_data' : (dict) --
            | 'PCA Score' : (pandas.DataFrame) --
            | 'Cluster' : (pandas.DataFrame) --
            | 'Cluster Score' : (pandas.DataFrame) --
        | 'processed_data' : (pandas.DataFrame) --
        ['filter_info'] : (pandas.DataFrame) -- stores filters for each sample
            | 'field_type' : (str) -- field type
            | 'field' : (str) -- name of field
            | 'norm' : (str) -- scale normalization function, ``linear`` or ``log``
            | 'min' : (float) -- minimum value for filtering
            | 'max' : (float) -- maximum value for filtering
            | 'operator' : (str) -- boolean operator for combining filters, ``and`` or ``or``
            | 'use' : (bool) -- ``True`` indicates the filter should be used to filter data
            | 'persistent' : (bool) -- ``True`` retains the filter when the sample is changed

        | 'crop_mask' : (MaskObj) -- mask created from cropped axes.
        | 'filter_mask' : (MaskObj) -- mask created by a combination of filters.  Filters are displayed for the user in ``tableWidgetFilters``.
        | 'polygon_mask' : (MaskObj) -- mask created from selected polygons.
        | 'cluster_mask' : (MaskObj) -- mask created from selected or inverse selected cluster groups.  Once this mask is set, it cannot be reset unless it is turned off, clustering is recomputed, and selected clusters are used to produce a new mask.
        | 'mask' : () -- combined mask, derived from filter_mask & 'polygon_mask' & 'crop_mask'
    """    
    def __init__(self, sample_id, file_path, negative_method):
        """_summary_

        _extended_summary_

        Parameters
        ----------
        sample_id : str
            Sample identifier.
        file_path : str
            Path to data file for sample_id
        negative_method : str
            Method used to handle negative values in the dataset
        """
        self.sample_id = sample_id
        self.file_path = file_path
        self._negative_method = negative_method
        self._updating = True
        self._filter_df = pd.DataFrame()
        self._valid_data_types = ['analyte','ratio','computed','special','pca_score','cluster','cluster_score']

        self.reset_data()

    def reset_data(self):
        """Reverts back to the original data.

        What is reset?

        What is not reset?
        """        
        # load data
        sample_df = pd.read_csv(self.file_path, engine='c')
        sample_df = sample_df.loc[:, ~sample_df.columns.str.contains('^Unnamed')]  # Remove unnamed columns

        # determine column data types
        # initialize all as 'analyte'
        data_type = ['analyte']*sample_df.shape[1]

        # identify coordinate columns
        data_type[sample_df.columns.get_loc('X')] = 'coordinate'
        data_type[sample_df.columns.get_loc('Y')] = 'coordinate'

        # identify and ratio columns
        ratio_pattern = re.compile(r'([A-Za-z]+[0-9]*) / ([A-Za-z]+[0-9]*)')

        # List to store column names that match the ratio pattern
        ratio_columns = [col for col in sample_df.columns if ratio_pattern.match(col)]

        # Update the data_type list for ratio columns by finding their index positions
        for col in ratio_columns:
            col_index = sample_df.columns.get_loc(col)
            data_type[col_index] = 'ratio'

        # use an ExtendedDF.AttributeDataFrame to add attributes to the columns
        # may includes analytes, ratios, and special data
        self.raw_data = AttributeDataFrame(data=sample_df)
        self.raw_data.set_attribute(attribute='data_type', columns=list(self.raw_data.columns), values=data_type)

        self.x = self.orig_x = self.raw_data['X']
        self.y = self.orig_y = self.raw_data['Y']

        # create dataframes for cropped data and processed data
        # set selected_analytes to columns excluding X and Y (future-proofed)
        #self.selected_analytes = self.raw_data.columns[2:].tolist()  # Skipping first two columns
        analyte_columns = self.raw_data.match_attribute(attribute='data_type',value='analyte')
        self.processed_data = copy.deepcopy(self.raw_data)
        self.processed_data.set_attribute(attribute='units', columns=analyte_columns, values=None)
        self.processed_data.set_attribute(attribute='use', columns=analyte_columns, values=True)
        # quantile bounds
        self.processed_data.set_attribute(attribute='lower_bound', columns=analyte_columns, values=0.05)
        self.processed_data.set_attribute(attribute='upper_bound', columns=analyte_columns, values=99.5)
        # quantile bounds for differences
        self.processed_data.set_attribute(attribute='diff_lower_bound', columns=analyte_columns, values=0.05)
        self.processed_data.set_attribute(attribute='diff_upper_bound', columns=analyte_columns, values=99)
        # min and max unmasked values
        self.processed_data.set_attribute(attribute='v_min', columns=analyte_columns, values=None)
        self.processed_data.set_attribute(attribute='v_max', columns=analyte_columns, values=None)
        # linear/log scale
        self.processed_data.set_attribute(attribute='norm', columns=analyte_columns, values='linear')
        self.processed_data.set_attribute(attribute='auto_scale', columns=analyte_columns, values=True)
        self.processed_data.set_attribute(attribute='negative_method', columns=analyte_columns, values=self._negative_method)        

        # initialize X and Y axes bounds for plotting and cropping, initially the entire map
        self._xlim = [self.raw_data['X'].min(), self.raw_data['X'].max()]
        self._ylim = [self.raw_data['Y'].min(), self.raw_data['Y'].max()]

        # initialize crop flag to false
        self.crop = False

        # Remove the ratio columns from the raw_data and store the rest
        non_ratio_columns = [col for col in sample_df.columns if col not in ratio_columns]
        self.raw_data = sample_df[non_ratio_columns]

        # set mask of size of analyte array
        self._crop_mask = np.ones_like(self.raw_data['X'].values, dtype=bool)
        self.filter_mask = np.ones_like(self.raw_data['X'].values, dtype=bool)
        self.polygon_mask = np.ones_like(self.raw_data['X'].values, dtype=bool)
        self.cluster_mask = np.ones_like(self.raw_data['X'].values, dtype=bool)
        self.mask = \
            self.crop_mask & \
            self.filter_mask & \
            self.polygon_mask & \
            self.cluster_mask

        # autoscale and negative handling
        self.prep_data()

        # determine aspect ratio
    
    # def update_crop_mask(self):
    #     """Automatically update the crop_mask whenever crop bounds change."""
    #     for analysis_type, df in self.computed_data.items():
    #         if isinstance(df, pd.DataFrame):
    #             df = df[self.crop_mask].reset_index(drop=True)
    #     self.prep_data()

    # --------------------------------------
    # Define properties and setter functions
    # --------------------------------------
    # note properties are based on the cropped X and Y values
    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, new_x):
        if not self._updating:
            self._updating = True
            self._x = new_x
            self._dx = self.x_range / new_x.nunique() 
            self._updating = False

    # Define the y property
    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, new_y):
        if not self._updating:
            self._updating = True
            self._y = new_y
            self._dy = self.y_range / new_y.nunique() 
            self._updating = False

    @property
    def dx(self):
        return self._dx

    @dx.setter
    def dx(self, new_dx):
        if not self._updating:
            self._updating = True

            # Recalculates X for self.raw_data
            # (does not use self.processed_data because the x limits will otherwise be incorrect)
            X = round(self.raw_data['X']/self._dx)
            self._dx = new_dx
            X_new = new_dx*X

            # Extract cropped region and update self.processed_data
            self._x = X_new[self.crop_mask]
            self.processed_data['X'] = self._x

            self._updating = False

    @property
    def dy(self):
        return self._dy

    @dy.setter
    def dy(self, new_dy):
        if not self._updating:
            self._updating = True

            # Recalculates Y for self.raw_data
            # (does not use self.processed_data because the y limits will otherwise be incorrect)
            Y = round(self.raw_data['Y']/self._dy)
            self._dy = new_dy
            Y_new = new_dy*Y

            # Extract cropped region and update self.processed_data
            self._y = Y_new[self.crop_mask]
            self.processed_data['Y'] = self._y

            self._updating = False

    # Cropped X-axis limits
    @property
    def xlim(self):
        return (self._x.min(), self._x.max()) if self._x is not None else (None, None)

    # Cropped Y-axis limits
    @property
    def ylim(self):
        return (self._y.min(), self._y.max()) if self._y is not None else (None, None)

    @property
    def x_range(self):
        return self._x.max() - self._x.min() if self._x is not None else None

    @property
    def y_range(self):
        return self._y.max() - self._y.min() if self._y is not None else None
    
    @property
    def aspect_ratio(self):
        if self._dx and self._dy:
            return self._dy / self._dx
        return None

    @property
    def array_size(self):
        return (self._y.nunique(), self._x.nunique())

    @property
    def crop_mask(self):
        return self._crop_mask
    
    @crop_mask.setter
    def crop_mask(self, new_xlim, new_ylim):
        self.crop=True

        self._crop_mask = (
            (self.raw_data['X'] >= new_xlim[0]) & 
            (self.raw_data['X'] <= new_xlim[1]) &
            (self.raw_data['Y'] <= self.raw_data['Y'].max() - new_ylim[0]) &
            (self.raw_data['Y'] >= self.raw_data['Y'].max() - new_ylim[1])
        )

        #crop clipped_analyte_data based on self.crop_mask
        self.raw_data[self.crop_mask].reset_index(drop=True)
        self.processed_data = self.processed_data[self.crop_mask].reset_index(drop=True)

        self.x = self.processed_data['X']
        self.y = self.processed_data['Y']

        self._crop_mask = np.ones_like(self.raw_data['X'], dtype=bool)

        self.prep_data()

    @property
    def filter_df(self):
        return self._filter_df

    def add_column(self, data_type, column_name, array):
        """Add a column to the sample object

        Adds a column to ``SampleObj.processed_data``.

        Parameters
        ----------
        data_type : str
            The type of data stored in the column.
        column_name : str
            The name of the column to add.  If the column already exists, it overwrites the column.
        array : numpy.ndarray
            The data to be added to column_name of the data frame, i.e., ``SampleObj.processed_data[column_name]``.

        Returns
        -------
        str, None
            Returns a message (str) if a column is overwritten, otherwise returns ``None``.

        Raises
        ------
        ValueError
            Valid types are given in ``SampleObj._valid_data_types``.
        ValueError
            The length of array must be the same as the height of ``SampleObj.processed_data``.
        """        
        # check data type
        if data_type not in self._valid_data_types:
            raise ValueError("The (data_type) provided is not valid. Valid types include: " + ", ".join([f"{dt}" for dt in self._valid_data_types]))

        # check column name for duplicate
        if column_name in self.processed_data.columns:
            return "Column already exists... overwriting"
        
        # check array length
        if len(array) != self.processed_data.shape[0]:
            raise ValueError("Length of (array), must be the same as height as the data frame.")
        
        self.processed_data[column_name] = array
        self.processed_data.set_attribute(attribute='data_type', columns=column_name, values=data_type)
        self.processed_data.set_attribute(attribute='units', columns=column_name, values=None)
        self.processed_data.set_attribute(attribute='use', columns=column_name, values=False)
        # quantile bounds
        self.processed_data.set_attribute(attribute='lower_bound', columns=analyte_columns, values=0.05)
        self.processed_data.set_attribute(attribute='upper_bound', columns=analyte_columns, values=99.5)
        # quantile bounds for differences
        self.processed_data.set_attribute(attribute='diff_lower_bound', columns=analyte_columns, values=0.05)
        self.processed_data.set_attribute(attribute='diff_upper_bound', columns=analyte_columns, values=99)
        # min and max unmasked values
        v_min = self.processed_data[column_name][self.mask].min()
        v_max = self.processed_data[column_name][self.mask].max()
        self.processed_data.set_attribute(attribute='v_min', columns=column_name, values=v_min)
        self.processed_data.set_attribute(attribute='v_max', columns=column_name, values=v_max)
        # linear/log scale
        self.processed_data.set_attribute(attribute='norm', columns=column_name, values='linear')
        self.processed_data.set_attribute(attribute='auto_scale', columns=column_name, values=False)
        self.processed_data.set_attribute(attribute='negative_method', columns=column_name, values=None)

        return None

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

    def reset_crop(self):
        """Reset the data to the new bounds.

        _extended_summary_
        """        
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

        self.add_column('ratio',ratio_name,ratio_array)

    def prep_data(self):
        # Select columns where 'data_type' attribute is 'analyte'
        analyte_columns = [col for col in self.processed_data.columns if self.processed_data.get_attribute(col, 'data_type') == 'analyte']

        # Extract the analyte data
        analyte_data = self.processed_data[analyte_columns].values

        # Call function to determine optimal clusters
        optimal_clusters = self.find_optimal_clusters(analyte_data)
        print(f"Optimal number of clusters: {optimal_clusters}")

        # Fit KMeans with the optimal number of clusters
        kmeans = KMeans(n_clusters=optimal_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(analyte_data)

        # Apply your transformation and outlier detection to each cluster
        for cluster in range(optimal_clusters):
            cluster_mask = (cluster_labels == cluster)
            cluster_data = analyte_data[cluster_mask]

            # Apply negative value handling
            transformed_data = self.transform_array(cluster_data, negative_method='gradual shift')

            # Apply robust outlier detection
            processed_cluster = self.robust_outlier_detection(transformed_data)

            # Store the processed cluster back into the full dataset
            analyte_data[cluster_mask] = processed_cluster

        # Replace the original data in the processed_data DataFrame
        self.processed_data[analyte_columns] = analyte_data

    def find_optimal_clusters(data, max_clusters=10):
        inertia = []
        
        # Perform KMeans for cluster numbers from 1 to max_clusters
        for n_clusters in range(1, max_clusters+1):
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            kmeans.fit(data)
            inertia.append(kmeans.inertia_)  # Record the inertia (sum of squared distances)
        
        # Plot inertia values for the elbow method
        plt.plot(range(1, max_clusters+1), inertia, marker='o')
        plt.xlabel('Number of clusters')
        plt.ylabel('Inertia')
        plt.title('Elbow Method for Optimal Clusters')
        plt.show()

        # Identify the elbow point (this can be manually or programmatically selected)
        # Here, you might automate it with a threshold or second derivative
        # For simplicity, return the elbow manually or based on a heuristic
        optimal_clusters = np.argmin(np.diff(np.diff(inertia))) + 2  # Example heuristic
        return optimal_clusters

    def apply_cluster_transformations(data, analyte_columns, optimal_clusters):
        transformed_data = data.copy()
        
        for analyte in analyte_columns:
            analyte_data = data[analyte].values.reshape(-1, 1)
            
            # Scale the data for clustering
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(analyte_data)
            
            # Apply KMeans with the optimal number of clusters
            kmeans = KMeans(n_clusters=optimal_clusters[analyte])
            labels = kmeans.fit_predict(scaled_data)
            centroids = kmeans.cluster_centers_
            
            # Apply transform_array function to handle negative values
            # Adjust negative values based on cluster-based shift
            transformed_array = transform_array(analyte_data, labels, centroids)
            
            # Replace the column with transformed data
            transformed_data[analyte] = transformed_array.flatten()
        
        return transformed_data

    def apply_outlier_detection(data, analyte_columns):
        for analyte in analyte_columns:
            analyte_data = data[analyte].values
            
            # Apply robust outlier detection
            adjusted_data = robust_outlier_detection(analyte_data)
            
            # Replace the column with adjusted data
            data[analyte] = adjusted_data
        
        return data

    def elbow_auto_detection(data, max_clusters=10):
        inertia = []
        k_range = range(1, max_clusters + 1)
        
        for k in k_range:
            kmeans = KMeans(n_clusters=k)
            kmeans.fit(data)
            inertia.append(kmeans.inertia_)
        
        # Compute first and second derivatives
        first_derivative = np.diff(inertia)
        second_derivative = np.diff(first_derivative)
        
        # Find the index of the largest second derivative (i.e., the elbow)
        optimal_k = np.argmax(second_derivative) + 2  # Add 2 because np.diff reduces the length
        
        # Plot WCSS and mark the elbow
        plt.figure(figsize=(8, 6))
        plt.plot(k_range, inertia, 'bx-')
        plt.xlabel('Number of clusters (k)')
        plt.ylabel('Inertia (WCSS)')
        plt.title('Elbow Method for Optimal k')
        plt.axvline(x=optimal_k, linestyle='--', color='r', label=f'Elbow at k={optimal_k}')
        plt.legend()
        plt.show()
        
        return optimal_k

    def robust_outlier_detection(self, lq=0.0005, uq=99.5, d_lq=9.95, d_uq=99, compositional=True, max_val=1e6, n_clusters=2, shift_percentile=90):
        """Outlier detection with cluster-based correction for negatives and compositional constraints, using percentile-based shifting.

        Parameters
        ----------
        lq : float
            Lower quantile for detecting outliers (default is 0.0005).
        uq : float
            Upper quantile for detecting outliers (default is 99.5).
        d_lq : float
            Lower quantile for differences in sorted data (default is 9.95).
        d_uq : float
            Upper quantile for differences in sorted data (default is 99).
        compositional : bool
            If True, applies compositional data constraints (default is True).
        max_val : float
            Maximum allowable value for the data (default is 1e6).
        n_clusters : int
            Number of clusters for correcting negative values (default is 2).
        shift_percentile : float
            Percentile for selecting non-extreme values to base the shift on (default is 90).

        Returns
        -------
        np.ndarray
            Data with outliers clipped and adjusted for compositional constraints.
        """
        data = np.array(self.data)  # Convert data to a numpy array if not already
        
        # Handle below-zero values using cluster-based correction
        if np.nanmin(data) < 0:
            # Apply clustering to separate potential noise (negatives)
            kmeans = KMeans(n_clusters=n_clusters)
            valid_data = data[np.isfinite(data)].reshape(-1, 1)  # Exclude NaNs for clustering
            labels = kmeans.fit_predict(valid_data)
            
            # Find the cluster with the lowest mean and treat it as the potential noise cluster
            cluster_means = np.array([valid_data[labels == i].mean() for i in range(n_clusters)])
            noise_cluster = np.argmin(cluster_means)
            
            # Get the values in the noise cluster
            noise_data = valid_data[labels == noise_cluster]

            # Calculate the centroid of the noise cluster
            noise_centroid = np.mean(noise_data)
            
            # Determine the percentile value for shifting
            high_percentile_value = np.percentile(noise_data, shift_percentile)
            
            # Calculate the shift based on values within the specified percentile range
            shift_values = noise_data[noise_data >= high_percentile_value]
            if len(shift_values) > 0:
                min_shift_value = np.min(shift_values)
                shift_value = np.abs(min_shift_value)
                
                # Apply the shift to positive values within the noise cluster
                data[labels.reshape(data.shape) == noise_cluster] += shift_value
                
                # Move extreme negative values (outside the shift percentile) to the new minimum positive value
                data[labels.reshape(data.shape) == noise_cluster] = np.where(
                    data[labels.reshape(data.shape) == noise_cluster] < high_percentile_value, 
                    min_shift_value, 
                    data[labels.reshape(data.shape) == noise_cluster]
                )

        # Set a small epsilon to handle zeros (if compositional data)
        epsilon = 1e-10 if compositional else 0

        # Shift data to handle zeros and negative values for log transformations
        v0 = np.nanmin(data, axis=0) - epsilon
        data_shifted = np.log10(data - v0 + epsilon)

        # Quantile-based clipping (detect outliers)
        lq_val = np.nanpercentile(data_shifted, lq, axis=0)
        uq_val = np.nanpercentile(data_shifted, uq, axis=0)

        # Sort data and calculate differences between adjacent points
        sorted_indices = np.argsort(data_shifted, axis=0)
        sorted_data = np.take_along_axis(data_shifted, sorted_indices, axis=0)
        diff_sorted_data = np.diff(sorted_data, axis=0)

        # Account for the size reduction in np.diff by adding a zero row at the beginning
        diff_sorted_data = np.insert(diff_sorted_data, 0, 0, axis=0)
        diff_array_uq_val = np.nanpercentile(diff_sorted_data, d_uq, axis=0)
        diff_array_lq_val = np.nanpercentile(diff_sorted_data, d_lq, axis=0)

        # Initialize array for results
        clipped_data = np.copy(sorted_data)

        # Apply upper bound clipping based on quantiles and differences
        upper_cond = (sorted_data > uq_val) & (diff_sorted_data > diff_array_uq_val)
        for col in range(sorted_data.shape[1]):
            up_indices = np.where(upper_cond[:, col])[0]
            if len(up_indices) > 0:
                uq_outlier_index = up_indices[0]
                clipped_data[uq_outlier_index:, col] = clipped_data[uq_outlier_index - 1, col]

        # Apply lower bound clipping similarly based on lower quantile and difference
        lower_cond = (sorted_data < lq_val) & (diff_sorted_data > diff_array_lq_val)
        for col in range(sorted_data.shape[1]):
            low_indices = np.where(lower_cond[:, col])[0]
            if len(low_indices) > 0:
                lq_outlier_index = low_indices[-1]
                clipped_data[:lq_outlier_index + 1, col] = clipped_data[lq_outlier_index + 1, col]

        # Restore original data order and undo the log transformation
        clipped_data = np.take_along_axis(clipped_data, np.argsort(sorted_indices, axis=0), axis=0)
        clipped_data = 10**clipped_data + v0 - epsilon

        # Enforce upper bound (compositional constraint) to ensure data <= max_val
        clipped_data = np.where(clipped_data > max_val, max_val, clipped_data)

        # Ensure non-negative values and avoid exact zeros by shifting slightly if needed
        clipped_data = np.maximum(clipped_data, epsilon)

        return clipped_data


    def transform_array(array, negative_method):
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
            case 'ignore negative values':
                t_array = np.copy(array)
                t_array = np.where(t_array > 0, t_array, np.nan)
                return t_array

            case 'minimum positive value':
                min_positive_value = np.nanmin(array[array > 0])
                t_array = np.where(array < 0, min_positive_value, array)
                return t_array

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
                return t_array

            case 'cluster-based correction':
                # Use clustering to identify noise-like negative points
                reshaped_data = array.reshape(-1, 1)  # Reshape for clustering
                clustering = DBSCAN(eps=0.5, min_samples=10).fit(reshaped_data)
                labels = clustering.labels_
                noise_mask = (labels == -1)  # DBSCAN marks noise with -1
                t_array = np.copy(array)
                min_positive_value = np.nanmin(t_array[t_array > 0])

                # Adjust noise and negative values
                t_array[noise_mask | (t_array < 0)] = min_positive_value
                return t_array

            case 'yeo-johnson transformation':
                t_array, _ = yeojohnson(array)
                return t_array




    # def prep_data(self, analyte_1=None, analyte_2=None):
    #     """Prepares data to be used in analysis

    #     1. Obtains raw DataFrame
    #     2. Handles negative values based on option chosen
    #     3. Scale data  (linear,log, loggit)
    #     4. Autoscales data if choosen by user

    #     The prepped data is stored in one of 2 Dataframes: analysis_analyte_data or computed_analyte_data
    #     """
    #     if analyte_1: #if single analyte
    #         if not isinstance(analyte_1,list):
    #             analytes = [analyte_1]
    #     else: #if analyte is not provided update all analytes in analytes_df
    #         analytes = self.processed_data.match_attribute(attribute='data_type', value='analyte')

    #     #analyte_info = self.processed_data.attributes_to_dataframe()
            
    #     if not analyte_2: #not a ratio
            
    #         # perform negative value handling
    #         for neg_method in self.processed_data.get_attribute(analytes, 'negative_method').unique():
    #             filtered_analytes = self.processed_data.match_attribute('negative_method', neg_method)
    #             filtered_data = self.processed_data[filtered_analytes].values
    #             self.processed_data.loc[:,filtered_analytes] = self.transform_array(filtered_data,neg_method)
                
    #         # perform autoscaling on columns where auto_scale is set to true
    #         for auto_scale in analyte_info['auto_scale'].unique():
    #             filtered_analytes = analyte_info[analyte_info['auto_scale'] == auto_scale]['analytes']

    #             for analyte_1 in filtered_analytes:
    #                 lq = self.processed_data.get_attribute(analyte_1,'lower_bound')
    #                 uq = self.processed_data.get_attribute(analyte_1,'upper_bound')
    #                 d_lb = self.processed_data.get_attribute(analyte_1,'diff_lower_bound')
    #                 d_ub = self.processed_data.get_attribute(analyte_1,'diff_upper_bound')
    #                 if auto_scale:
    #                     self.processed_data[analyte_1] = self.outlier_detection(self.processed_data[analyte_1].values.reshape(-1, 1),lq, uq, d_lb, d_ub)
    #                 else:
    #                     #clip data using ub and lb
    #                     lq_val = np.nanpercentile(self.processed_data[analyte_1], lq, axis=0)
    #                     uq_val = np.nanpercentile(self.processed_data[analyte_1], uq, axis=0)
    #                     self.processed_data[analyte_1] = np.clip(self.processed_data[analyte_1], lq_val, uq_val)

    #     # update v_min and v_max in self.analyte_info
    #     v_min = self.processed_data[column_name][self.mask].min()
    #     v_max = self.processed_data[column_name][self.mask].max()
    #     self.processed_data.set_attribute('v_min', field, v_min)
    #     self.processed_data.set_attribute('v_max', field, v_max)

    #     else:  #if ratio
    #         self.compute_ratio(analyte_1, analyte_2)

    #         # Check if we found such a row
    #         if len(index_to_update) > 0:
    #             idx = index_to_update[0]

    #             neg_method = self.comboBoxNegativeMethod.currentText()
    #             min_positive_value = min(ratio_array[ratio_array>0])
    #             self.ratio_info.at[idx, 'negative_method'] = neg_method

    #             # perform negative value handling
    #             ratio_array = self.transform_array(ratio_array,neg_method)     

    #             if auto_scale:

    #                 ratio_array = self.outlier_detection(ratio_array.reshape(-1, 1),lb, ub, d_lb,d_ub)
    #             else:
    #                 #clip data using ub and lb
    #                 lq_val = np.nanpercentile(ratio_array, lq, axis=0)
    #                 uq_val = np.nanpercentile(ratio_array, uq, axis=0)
    #                 ratio_array = np.clip(ratio_array, lq_val, uq_val)

    #             if self.computed_data['Ratio'].empty:
    #                 self.computed_data['Ratio'] = self.cropped_raw_data[['X','Y']]

    #             self.processed_data['Ratio'][ratio_name] = ratio_array

    #             self.ratio_info.at[idx, 'v_min'] = np.nanmin(ratio_array)
    #             self.ratio_info.at[idx, 'v_max'] = np.nanmax(ratio_array)
    
    def update_norm(self, data, sample_id, norm=None, analyte_1=None, analyte_2=None, update=False):
        """Update the norm of the data.

        Parameters
        ----------
        sample_id : str
            Sample identifier
        norm : str, optional
            Data scale method ``linear`` or ``log``, by default None
        analyte_1 : str, optional
            Analyte, numerator of ratio if *analyte_2* is not None, by default None
        analyte_2 : str, optional
            Denominator of ratio, by default None
        update : bool, optional
            Update the scale information of the data, by default False
        """        
        if analyte_1: #if normalising single analyte
            if not analyte_2: #not a ratio
                self.analyte_info.loc[(self.analyte_info['sample_id']==sample_id)
                                 & (self.analyte_info['analytes']==analyte_1),'norm'] = norm
                analytes = [analyte_1]
            else:
               self.ratio_info.loc[
                   (self.ratio_info['analyte_1'] == analyte_1) &
                   (self.ratio_info['analyte_2'] == analyte_2),'norm'] = norm
               analytes = [analyte_1+' / '+analyte_2]

        else: #if normalising all analytes in sample
            self.analyte_info.loc[(self.analyte_info['sample_id']==sample_id),'norm'] = norm
            analytes = self.analyte_info[self.analyte_info['sample_id']==sample_id]['analytes']


        self.prep_data(sample_id, analyte_1, analyte_2)

        #update self.data['norm']
        for analyte in analytes:
            self.norm[analyte] = norm

        #if update:
        # self.update_all_plots()
        # self.update_plot()
        self.update_SV()

    def get_map_data(self, data, sample_id, field, field_type='Analyte', scale_data=False):
        """
        Retrieves and processes the mapping data for the given sample and analytes, then plots the result if required.

        The method also updates certain parameters in the analyte data frame related to scaling.
        Based on the plot type, this method internally calls the appropriate plotting functions.

        Parameters
        ----------
        sample_id : str
            Sample identifier
        field : str, optional
            Name of field to plot, Defaults to None
        analysis_type : str, optional
            Field type for plotting, options include: 'Analyte', 'Ratio', 'pca', 'Cluster', 'Cluster Score',
            'Special', 'computed'. Some options require a field. Defaults to 'Analyte'

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
        #     crop_mask  = np.ones_like( self.raw_data['X'], dtype=bool)
        # else:
        #     crop_mask = self.data[self.sample_id]['crop_mask']
        
        # retrieve axis mask for that sample
        crop_mask = self.crop_mask
        
        #crop plot if filter applied
        df = self.raw_data[['X','Y']][crop_mask].reset_index(drop=True)

        print(field_type)

        match field_type:
            case 'Analyte' | 'Analyte (normalized)':
                # unnormalized
                df ['array'] = self.processed_data.loc[:,field].values
                #get analyte info
                norm = self.analyte_info.loc[self.analyte_info['analytes']==field,'norm'].iloc[0]
                
                #perform scaling for groups of analytes with same norm parameter
                
                if norm == 'log' and scale_data:
                    df['array'] = np.where(~np.isnan(df['array']), np.log10(df['array']), df['array'])

                    # print(self.processed_analyte_data[sample_id].loc[:10,analytes])
                    # print(self.processed_data.loc[:10,analytes])
                elif norm == 'logit' and scale_data:
                    # Handle division by zero and NaN values
                    with np.errstate(divide='ignore', invalid='ignore'):
                        df['array'] = np.where(~np.isnan(df['array']), np.log10(df['array'] / (10**6 - df['array'])))
                
                # normalize
                if 'normalized' in field_type:
                    refval = self.ref_chem[re.sub(r'\d', '', field).lower()]
                    df['array'] = df['array'] / refval

            case 'Ratio' | 'Ratio (normalized)':
                field_1 = field.split(' / ')[0]
                field_2 = field.split(' / ')[1]

                # unnormalized
                #df['array'] = self.computed_data.loc[:,field_1].values / self.processed_data.loc[:,field_2].values
                df['array'] = self.computed_data['Ratio'].loc[:,field].values
                
                # normalize
                if 'normalized' in field_type:
                    refval_1 = self.ref_chem[re.sub(r'\d', '', field_1).lower()]
                    refval_2 = self.ref_chem[re.sub(r'\d', '', field_2).lower()]
                    df['array'] = df['array'] * (refval_2 / refval_1)

                #get norm value
                norm = self.ratio_info.loc['norm',(self.ratio_info['analyte_1']==field_1 & self.ratio_info['analyte_2']==field_2)].iloc[0]

                if norm == 'log' and scale_data:
                    df ['array'] = np.where(~np.isnan(df['array']), np.log10(df ['array']))
                    # print(self.processed_analyte_data[sample_id].loc[:10,analytes])
                    # print(self.processed_data.loc[:10,analytes])
                elif norm == 'logit' and scale_data:
                    # Handle division by zero and NaN values
                    with np.errstate(divide='ignore', invalid='ignore'):
                        df['array'] = np.where(~np.isnan(df['array']), np.log10(df['array'] / (10**6 - df['array'])))

            case _:#'PCA Score' | 'Cluster' | 'Cluster Score' | 'Special' | 'Computed':
                df['array'] = self.computed_data[field_type].loc[:,field].values
            
        # ----begin debugging----
        # print(df.columns)
        # ----end debugging----

        # crop plot if filter applied
        # current_plot_df = current_plot_df[self.data[self.sample_id]['crop_mask']].reset_index(drop=True)
        return df

    def outlier_detection(self, lq=0.0005, uq=99.5, d_lq=9.95 , d_uq=99):
        """_summary_

        _extended_summary_

        Parameters
        ----------
        data : _type_
            _description_
        lq : float, optional
            _description_, by default 0.0005
        uq : float, optional
            _description_, by default 99.5
        d_lq : float, optional
            _description_, by default 9.95
        d_uq : int, optional
            _description_, by default 99

        Returns
        -------
        _type_
            _description_
        """        
        # Ensure data is a numpy array
        data = np.array(data)

        # Shift values to positive concentrations
        v0 = np.nanmin(data, axis=0) - 0.001
        data_shifted = np.log10(data - v0)

        # Calculate required quantiles and differences
        lq_val = np.nanpercentile(data_shifted, lq, axis=0)
        uq_val = np.nanpercentile(data_shifted, uq, axis=0)
        sorted_indices = np.argsort(data_shifted, axis=0)
        sorted_data = np.take_along_axis(data_shifted, sorted_indices, axis=0)


        diff_sorted_data = np.diff(sorted_data, axis=0)
        # Adding a 0 to the beginning of each column to account for the reduction in size by np.diff
        diff_sorted_data = np.insert(diff_sorted_data, 0, 0, axis=0)
        diff_array_uq_val = np.nanpercentile(diff_sorted_data, d_uq, axis=0)
        diff_array_lq_val = np.nanpercentile(diff_sorted_data, d_lq, axis=0)
        upper_cond = (sorted_data > uq_val) & (diff_sorted_data > diff_array_uq_val)

        # Initialize arrays for results
        clipped_data = np.copy(sorted_data)

        # Upper bound outlier filter
        for col in range(sorted_data.shape[1]):
            up_indices = np.where(upper_cond[:, col])[0]
            if len(up_indices) > 0:
                uq_outlier_index = up_indices[0]
                clipped_data[uq_outlier_index:, col] = clipped_data[uq_outlier_index-1, col]

        lower_cond = (sorted_data < lq_val) & (diff_sorted_data > diff_array_lq_val)
        # Lower bound outlier filter
        for col in range(sorted_data.shape[1]):
            low_indices = np.where(lower_cond[:, col])[0]
            if len(low_indices) > 0:
                lq_outlier_index = low_indices[-1]
                clipped_data[:lq_outlier_index+1, col] = clipped_data[lq_outlier_index+1, col]

        clipped_data = np.take_along_axis(clipped_data, np.argsort(sorted_indices, axis=0), axis=0)
        # Unshift the data
        clipped_data = 10**clipped_data + v0

        return clipped_data

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
    #         case 'ignore negative values':
    #             t_array = np.copy(array)
    #             t_array = np.where(t_array > 0, t_array, np.nan)
    #             return t_array
    #         case 'minimum positive value':
    #             min_positive_value = np.nanmin(array[array > 0])
    #             t_array = np.where(array < 0, min_positive_value, array)
    #             return t_array
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
    #         case 'yeo-johnson transformation':
    #             # Apply Yeo-Johnson transformation
    #             t_array, lambda_yeojohnson = yeojohnson(array)
    #             return t_array
    
