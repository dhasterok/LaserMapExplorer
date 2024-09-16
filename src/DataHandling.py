import re, copy
import numpy as np
import pandas as pd
from src.ExtendedDF import AttributeDataFrame
from scipy.stats import yeojohnson

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
    compute_map_aspect_ratio :
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
        # assign sample ID
        self.sample_id = sample_id

        # load data
        sample_df = pd.read_csv(file_path, engine='c')
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
        self.raw_data.set_attribute(self.raw_data.columns,'data_type',data_type)

        self.x = self.orig_x = self.raw_data['X']
        self.y = self.orig_y = self.raw_data['Y']

        # create dataframes for cropped data and processed data
        self.cropped_raw_data = copy.deepcopy(self.raw_data)

        # set selected_analytes to columns excluding X and Y (future-proofed)
        #self.selected_analytes = self.raw_data.columns[2:].tolist()  # Skipping first two columns
        analyte_columns = self.raw_data.find_columns(attribute='data_type',value='analyte')
        self.processed_data = self.raw_data.copy_columns(columns=analyte_columns)
        self.processed_data.set_attribute(attribute='use', columns=analyte_columns, values=True)
        self.processed_data.set_attribute(attribute='upper_bound', columns=analyte_columns, values=99.5)
        self.processed_data.set_attribute(attribute='diff_lower_bound', columns=analyte_columns, values=0.05)
        self.processed_data.set_attribute(attribute='diff_upper_bound', columns=analyte_columns, values=99)
        self.processed_data.set_attribute(attribute='v_min', columns=analyte_columns, values=None)
        self.processed_data.set_attribute(attribute='v_max', columns=analyte_columns, values=None)
        self.processed_data.set_attribute(attribute='norm', columns=analyte_columns, values='linear')
        self.processed_data.set_attribute(attribute='auto_scale', columns=analyte_columns, values=True)
        self.processed_data.set_attribute(attribute='negative_method', columns=analyte_columns, values=negative_method)

        self.computed_data = {
            'Analyte': pd.DataFrame(),
            'Ratio': sample_df[ratio_columns] if ratio_columns else pd.DataFrame(),
            'Special': pd.DataFrame(),
            'PCA Score': pd.DataFrame(),
            'Cluster': pd.DataFrame(columns=['fuzzy c-means', 'k-means']),
            'Cluster Score': pd.DataFrame(),
        }

        self.ratio_info = pd.DataFrame(columns = [ 'analyte_1', 'analyte_2', 'norm', 'upper_bound', 'lower_bound', 'd_l_bound', 'd_u_bound', 'use', 'auto_scale'])

        # initialize X and Y axes bounds for plotting and cropping, initially the entire map
        self._xlim = self._xlim_raw = [self.raw_data['X'].min(), self.raw_data['X'].max()]
        self._ylim = self._ylim_raw = [self.raw_data['Y'].min(), self.raw_data['Y'].max()]

        # initialize crop flag to false
        self.crop = False

        # Remove the ratio columns from the raw_data and store the rest
        non_ratio_columns = [col for col in sample_df.columns if col not in ratio_columns]
        self.raw_data = sample_df[non_ratio_columns]


        #----------------

        analytes = pd.DataFrame()
        # setup a dataframe with parameters for autoscaling and handling negative values for each analyte
        # analytes['analytes']=self.selected_analytes
        # analytes['sample_id'] = sample_id
        # analytes['norm'] = 'linear'
        # analytes['lower_bound'] = 0.05
        # analytes['upper_bound'] = 99.5
        # analytes['d_l_bound'] = 0.05 
        # analytes['d_u_bound'] = 99
        # analytes['v_min'] = None
        # analytes['v_max'] = None
        # analytes['auto_scale'] = True
        # analytes['use'] = True
        # analytes['negative_method'] = negative_method

        # self.analyte_info = analytes

        # set mask of size of analyte array
        self.crop_mask = np.ones_like(self.raw_data['X'], dtype=bool)
        self.filter_mask = np.ones_like(self.raw_data['X'].values, dtype=bool)
        self.polygon_mask = np.ones_like(self.raw_data['X'], dtype=bool)
        self.cluster_mask = np.ones_like(self.raw_data['X'], dtype=bool)
        self.mask = \
            self.crop_mask & \
            self.filter_mask & \
            self.polygon_mask & \
            self.cluster_mask

        # autoscale and negative handling
        self.prep_data()

        # determine aspect ratio

    # --------------------------------------
    # Define properties and setter functions
    # --------------------------------------
    # Raw X-axis limits
    @property
    def xlim_raw(self):
        return self._xlim_raw

    # Raw Y-axis limits
    @property
    def ylim_raw(self):
        return self._ylim_raw

    # Cropped X-axis limits
    @property
    def xlim(self):
        return self._xlim

    @xlim.setter
    def xlim(self, minval=None, maxval=None):
        if minval:
            self._xlim[0] = minval
        if maxval:
            self._xlim[1] = maxval
        self.update_crop_mask()

    # Cropped Y-axis limits
    @property
    def ylim(self):
        return self._ylim

    @ylim.setter
    def ylim(self, minval=None, maxval=None):
        if minval:
            self._ylim[0] = minval
        if maxval:
            self._ylim[1] = maxval
        self.update_crop_mask()
    
    def update_crop_mask(self):
        """Automatically update the crop_mask whenever crop bounds change."""
        self.crop = True

        df = self.raw_data
        self.crop_mask = (
            (df['X'] >= self.xlim[0]) & 
            (df['X'] <= self.xlim[1]) &
            (df['Y'] <= df['Y'].max() - self.ylim[0]) &
            (df['Y'] >= df['Y'].max() - self.ylim[1])
        )

        #crop original_data based on self.crop_mask
        self.cropped_raw_data = self.raw_data[self.crop_mask].reset_index(drop=True)

        #crop clipped_analyte_data based on self.crop_mask
        self.processed_data = self.processed_data[self.crop_mask].reset_index(drop=True)

        for analysis_type, df in self.computed_data.items():
            if isinstance(df, pd.DataFrame):
                df = df[self.crop_mask].reset_index(drop=True)


        self.prep_data(sample_id)

    def reset_crop(self):
        """Resets dataframe to original bounds."""        
        self.crop = False

        self.xlim = self.xlim_raw
        self.ylim = self.ylim_raw

        self.processed_data = copy.deepcopy(self.raw_data)
        self.cropped_raw_data = copy.deepcopy(self.raw_data)
        self.computed_data = {
            'Ratio':None,
            'Calculated':None,
            'Special':None,
            'PCA Score':None,
            'Cluster':None,
            'Cluster Score':None
        }

        # reset axis mask and mask
        self.crop_mask = np.ones_like( self.raw_data['X'], dtype=bool)
        self.mask = np.ones_like( self.raw_data['X'], dtype=bool)
        # self.data[self.sample_id]['mask'] = \
        #         self.data[self.sample_id]['crop_mask'] & \
        #         self.data[self.sample_id]['filter_mask'] & \
        #         self.data[self.sample_id]['polygon_mask'] & \
        #         self.data[self.sample_id]['cluster_mask']

        self.prep_data()
        # re-compute aspect ratio
        self.compute_map_aspect_ratio()

    def compute_map_aspect_ratio(self):
        """Computes aspect ratio of current sample
        
        The aspect ratio is needed for maps and computations of areas as the pixels may not be square in dimension.
        The aspect ratio is defined as dy/dx where dy is y_range/n_y and dx is x_range/n_x.
        """
        self.x = self.processed_data['X']
        self.y = self.processed_data['Y']

        self.x_range = self.x.max() - self.x.min()
        self.y_range = self.y.max() - self.y.min()

        self.dx = self.x_range/self.x.nunique()
        self.dy = self.y_range/self.y.nunique()

        self.aspect_ratio = self.dy / self.dx

        self.array_size = (self.y.nunique(), self.x.nunique())

    def update_resolution(self, dx, dy):
        """Updates DX and DY for a dataframe

        Recalculates X and Y for a dataframe
        """
        X = round(self.raw_data['X']/self.dx)
        Y = round(self.raw_data['Y']/self.dy)

        Xp = round(self.processed_data['X']/self.dx)
        Yp = round(self.processed_data['Y']/self.dy)

        self.dx = dx
        self.dy = dy

        self.raw_data['X'] = self.dx*X
        self.raw_data['Y'] = self.dy*Y

        self.processed_data['X'] = self.dx*Xp
        self.processed_data['Y'] = self.dy*Yp

        self.compute_map_aspect_ratio()

    def prep_data(self, analyte_1=None, analyte_2=None):
        """Prepares data to be used in analysis

        1. Obtains raw DataFrame
        2. Handles negative values based on option chosen
        3. Scale data  (linear,log, loggit)
        4. Autoscales data if choosen by user

        The prepped data is stored in one of 2 Dataframes: analysis_analyte_data or computed_analyte_data
        """

        sample_id = self.sample_id

        if analyte_1: #if single analyte
            if not isinstance(analyte_1,list):
                analytes = [analyte_1]
        else: #if analyte is not provided update all analytes in analytes_df
            analytes = self.analyte_info[self.analyte_info['sample_id']==sample_id]['analytes']

        analyte_info = self.analyte_info.loc[
                                 (self.analyte_info['analytes'].isin(analytes))]
            
        if not analyte_2: #not a ratio
            
            # perform negative value handling
            for neg_method in analyte_info['negative_method'].unique():
                filtered_analytes = analyte_info[analyte_info['negative_method'] == neg_method]['analytes']
                filtered_data = self.cropped_raw_data[filtered_analytes].values
                self.processed_data.loc[:,filtered_analytes] = self.transform_array(filtered_data,neg_method)
                
                
            # shifts analyte values so that all values are postive
            # adj_data = pd.DataFrame(self.transform_plots(self.cropped_raw_data[analytes].values), columns= analytes)
            
            
            # #perform scaling for groups of analytes with same norm parameter
            # for norm in analyte_info['norm'].unique():
            #     filtered_analytes = analyte_info[(analyte_info['norm'] == norm)]['analytes']
            #     filtered_data = adj_data[filtered_analytes].values
            #     if norm == 'log':

            #         # np.nanlog handles NaN value
            #         self.processed_data.loc[:,filtered_analytes] = np.log10(filtered_data, where=~np.isnan(filtered_data))
            #         # print(self.processed_analyte_data[sample_id].loc[:10,analytes])
            #         # print(self.processed_data.loc[:10,analytes])
            #     elif norm == 'logit':
            #         # Handle division by zero and NaN values
            #         with np.errstate(divide='ignore', invalid='ignore'):
            #             analyte_array = np.log10(filtered_data / (10**6 - filtered_data), where=~np.isnan(filtered_data))
            #             self.processed_data.loc[:,filtered_analytes] = analyte_array
            #     else:
            #         # set to clipped data with original values if linear normalisation
            #         self.processed_data.loc[:,filtered_analytes] = filtered_data

            # perform autoscaling on columns where auto_scale is set to true
            for auto_scale in analyte_info['auto_scale'].unique():
                filtered_analytes = analyte_info[analyte_info['auto_scale'] == auto_scale]['analytes']

                for analyte_1 in filtered_analytes:
                    parameters = analyte_info.loc[(analyte_info['sample_id']==sample_id)
                                          & (analyte_info['analytes']==analyte_1)].iloc[0]
                    filtered_data =  self.processed_data[analytes][analyte_1].values
                    lq = parameters['lower_bound']
                    uq = parameters['upper_bound']
                    d_lb = parameters['diff_lower_bound']
                    d_ub = parameters['diff_upper_bound']
                    if auto_scale:
                        self.processed_data[analyte_1] = self.outlier_detection(filtered_data.reshape(-1, 1),lq, uq, d_lb,d_ub)
                    else:
                        #clip data using ub and lb
                        lq_val = np.nanpercentile(filtered_data, lq, axis=0)
                        uq_val = np.nanpercentile(filtered_data, uq, axis=0)
                        filtered_data = np.clip(filtered_data, lq_val, uq_val)
                        self.processed_data[analyte_1] = filtered_data

                    # update v_min and v_max in self.analyte_info
                    self.analyte_info.loc[
                                             (self.analyte_info['analytes']==analyte_1),'v_max'] = np.nanmax(filtered_data)
                    self.analyte_info.loc[
                                             (self.analyte_info['analytes']==analyte_1), 'v_min'] = np.nanmin(filtered_data)

            #add x and y columns from raw data
            self.processed_data['X'] = self.cropped_raw_data['X']
            self.processed_data['Y'] = self.cropped_raw_data['Y']

        else:  #if ratio
            ratio_df = self.cropped_raw_data[[analyte_1,analyte_2]] #consider original data for ratio

            ratio_name = analyte_1+' / '+analyte_2

            # shifts analyte values so that all values are postive
            # ratio_array = self.transform_plots(ratio_df.values)
            ratio_array= ratio_df.values
            ratio_df = pd.DataFrame(ratio_array, columns= [analyte_1,analyte_2])
            
            # mask = (ratio_df[analyte_1] > 0) & (ratio_df[analyte_2] > 0)
            
            mask =   (ratio_df[analyte_2] == 0)

            ratio_array = np.where(mask, ratio_array[:,0] / ratio_array[:,1], np.nan)

            # Get the index of the row that matches the criteria
            index_to_update = self.ratio_info.loc[
                    (self.ratio_info['analyte_1'] == analyte_1) &
                    (self.ratio_info['analyte_2'] == analyte_2)
                ].index

            # Check if we found such a row
            if len(index_to_update) > 0:
                idx = index_to_update[0]

                if pd.isna(self.ratio_info.at[idx, 'lower_bound']): #if bounds are not updated in dataframe
                    #sets auto scale to true by default with default values for lb,db, d_lb and d_ub
                    auto_scale = True
                    norm = self.ratio_info.at[idx, 'norm']
                    lb = 0.05
                    ub = 99.5
                    d_lb = 99
                    d_ub = 99
                    self.ratio_info.at[idx, 'lower_bound'] = lb
                    self.ratio_info.at[idx, 'upper_bound'] = ub
                    self.ratio_info.at[idx, 'd_l_bound'] = d_lb
                    self.ratio_info.at[idx, 'd_u_bound'] = d_ub
                    self.ratio_info.at[idx, 'auto_scale'] = auto_scale
                    neg_method = self.comboBoxNegativeMethod.currentText()
                    min_positive_value = min(ratio_array[ratio_array>0])
                    self.ratio_info.at[idx, 'negative_method'] = neg_method
                    # self.ratio_info.at[idx, 'min_positive_value'] = min_positive_value
                else: #if bounds exist in ratios_df
                    norm = self.ratio_info.at[idx, 'norm']
                    lb = self.ratio_info.at[idx, 'lower_bound']
                    ub = self.ratio_info.at[idx, 'upper_bound']
                    d_lb = self.ratio_info.at[idx, 'd_l_bound']
                    d_ub = self.ratio_info.at[idx, 'd_u_bound']
                    auto_scale = self.ratio_info.at[idx, 'auto_scale']
                    neg_method = self.ratio_info.at[idx, 'negative_method']
                    # min_positive_value = self.ratio_info.at[idx, 'min_positive_value']
                    
                    
                # if norm == 'log':

                #     # np.nanlog handles NaN value
                #     ratio_array = np.log10(ratio_array, where=~np.isnan(ratio_array))
                #     # print(self.processed_analyte_data[sample_id].loc[:10,analytes])
                #     # print(self.processed_data.loc[:10,analytes])
                # elif norm == 'logit':
                #     # Handle division by zero and NaN values
                #     with np.errstate(divide='ignore', invalid='ignore'):
                #         ratio_array = np.log10(ratio_array / (10**6 - ratio_array), where=~np.isnan(ratio_array))
                # else:
                #     # set to clipped data with original values if linear normalisation
                #     pass

                # perform negative value handling
                ratio_array = self.transform_array(ratio_array,neg_method)     

                if auto_scale:

                    ratio_array = self.outlier_detection(ratio_array.reshape(-1, 1),lb, ub, d_lb,d_ub)
                else:
                    #clip data using ub and lb
                    lq_val = np.nanpercentile(ratio_array, lq, axis=0)
                    uq_val = np.nanpercentile(ratio_array, uq, axis=0)
                    ratio_array = np.clip(ratio_array, lq_val, uq_val)

                if self.computed_data['Ratio'].empty:
                    self.computed_data['Ratio'] = self.cropped_raw_data[['X','Y']]

                self.computed_data['Ratio'][ratio_name] = ratio_array

                self.ratio_info.at[idx, 'v_min'] = np.nanmin(ratio_array)
                self.ratio_info.at[idx, 'v_max'] = np.nanmax(ratio_array)
    
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

    def outlier_detection(data ,lq=0.0005, uq=99.5, d_lq=9.95 , d_uq=99):
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

    def transform_array(array, negative_method):
        """Negative and zero handling

        Parameters
        ----------
        array : numpy.ndarray
            Input data
        negative_method : str
            negative_method obtained from analyte info
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
                if array.ndim == 2:
                    # Calculate min and max values for each column and adjust their shapes for broadcasting
                    min_val = np.nanmin(array, axis=0, keepdims=True) - 0.0001
                    max_val = np.nanmax(array, axis=0, keepdims=True)

                    # Adjust the shape of min_val and max_val for broadcasting
                    adjusted_min_val = min_val
                    adjusted_max_val = max_val

                    # Check if min values are less than or equal 0
                    min_leq_zero = adjusted_min_val <= 0

                    # Perform transformation with broadcasting
                    t_array = np.where(
                        min_leq_zero,
                        (adjusted_max_val * (array - adjusted_min_val)) / (adjusted_max_val - adjusted_min_val),
                        array
                    )
                else:
                    # 1D array case, similar to original logic
                    min_val = np.nanmin(array) - 0.0001
                    max_val = np.nanmax(array)
                    if min_val < 0:
                        t_array = (max_val * (array - min_val)) / (max_val - min_val)
                    else:
                        t_array = np.copy(array)
                return t_array
            case 'yeo-johnson transformation':
                # Apply Yeo-Johnson transformation
                t_array, lambda_yeojohnson = yeojohnson(array)
                return t_array
    
