import re
import numpy as np
import pandas as pd
from scipy.stats import yeojohnson

class Dataset:
    def __init__(self, data_frame):

        self.raw_data = data_frame  # Includes analytes, ratios, and special data
        self.cropped_data = None
        self.processed_data = None
        self.data_types = {}  # Dictionary to track whether a column is analyte, ratio, or special

    def assign_data_type(self, column_name, data_type):
        """Assign whether the data is analyte, ratio, or special."""
        self.data_types[column_name] = data_type

    def crop(self, x_range, y_range):
        """Crop all data types based on x, y range."""
        self.cropped_data = self.raw_data[(self.raw_data['x'] >= x_range[0]) & (self.raw_data['x'] <= x_range[1]) &
                                          (self.raw_data['y'] >= y_range[0]) & (self.raw_data['y'] <= y_range[1])]

    def process(self, method):
        """Apply processing method to all data types."""
        self.processed_data = method(self.cropped_data)

    def separate_computed_data(self):
        """Separate the processed data into analytes, ratios, and special for computed_data."""
        analytes = []
        ratios = []
        special = []

        for column, data_type in self.data_types.items():
            if data_type == 'analyte':
                analytes.append(column)
            elif data_type == 'ratio':
                ratios.append(column)
            elif data_type == 'special':
                special.append(column)

        return {
            'analytes': self.processed_data[analytes],
            'ratios': self.processed_data[ratios],
            'special': self.processed_data[special]
        }
    

class Sample:
    def __init__(self, sample_id, file_path):
        # assign sample ID
        self.sample_id = sample_id

        # load data
        sample_df = pd.read_csv(file_path, engine='c')
        self.dataset = Dataset(sample_df)

        self.computed_data = {
            'Analyte': pd.DataFrame(),
            'Ratio': pd.DataFrame(),
            'Special': pd.DataFrame(),
            'PCA Score': pd.DataFrame(),
            'Cluster': pd.DataFrame(columns=['fuzzy c-means', 'k-means']),
            'Cluster Score': pd.DataFrame(),
        }
        self.analyte_metadata = analyte_metadata
        self.ratio_metadata = ratio_metadata

    def assign_data_type(self):
        """Assign types (analyte, ratio, special) based on metadata."""
        for analyte in self.analyte_metadata:
            self.dataset.assign_data_type(analyte, 'analyte')
        
        for ratio in self.ratio_metadata:
            self.dataset.assign_data_type(ratio, 'ratio')
        
        # Assuming special datasets are predefined or found in metadata
        special_datasets = ['SpecialData1', 'SpecialData2']  # Example special dataset names
        for special in special_datasets:
            self.dataset.assign_data_type(special, 'special')

    def preprocess_data(self):
        """Preprocess the raw data and store the results in computed_data."""
        # Cropping and processing the raw data
        self.dataset.crop(x_range=(0, 100), y_range=(0, 100))  # Example ranges
        self.dataset.process(self.some_processing_method)
        
        # Separate processed data into different computed categories
        separated_data = self.dataset.separate_computed_data()
        self.computed_data['Analyte'] = separated_data['analytes']
        self.computed_data['Ratio'] = separated_data['ratios']
        self.computed_data['Special'] = separated_data['special']


class DataProcessor:
    def __init__(self, samples):
        self.samples = samples  # Dictionary of Sample objects, keyed by sample_id

    def preprocess_all_samples(self):
        """Preprocess all samples (including analytes, ratios, and special data)."""
        for sample_id, sample in self.samples.items():
            sample.assign_data_type()  # Make sure each column is labeled correctly
            sample.preprocess_data()

    def filter_all_samples(self, analyte_name, filter_func):
        """Filter all samples for a given analyte."""
        for sample in self.samples.values():
            sample.apply_filter(analyte_name, filter_func)


# -------------------------------------
# Data functions functions
# -------------------------------------
class DataHandling():
    def __init__(self):
        pass

    def prep_data(self, data, sample_id, analyte_1=None, analyte_2=None):
        """Prepares data to be used in analysis

        1. Obtains raw DataFrame
        2. Handles negative values based on option chosen
        3. Scale data  (linear,log, loggit)
        4. Autoscales data if choosen by user

        The prepped data is stored in one of 2 Dataframes: analysis_analyte_data or computed_analyte_data
        """
        if analyte_1: #if single analyte
            if not isinstance(analyte_1,list):
                analytes = [analyte_1]
        else: #if analyte is not provided update all analytes in analytes_df
            analytes = data[sample_id]['analyte_info'][data[sample_id]['analyte_info']['sample_id']==sample_id]['analytes']

        analyte_info = data[sample_id]['analyte_info'].loc[
                                 (data[sample_id]['analyte_info']['analytes'].isin(analytes))]
            
        if not analyte_2: #not a ratio
            
            # perform negative value handling
            for neg_method in analyte_info['negative_method'].unique():
                filtered_analytes = analyte_info[analyte_info['negative_method'] == neg_method]['analytes']
                filtered_data = data[sample_id]['cropped_raw_data'][filtered_analytes].values
                data[sample_id]['processed_data'].loc[:,filtered_analytes] = self.transform_array(filtered_data,neg_method)
                
                
            # shifts analyte values so that all values are postive
            # adj_data = pd.DataFrame(self.transform_plots(self.data[sample_id]['cropped_raw_data'][analytes].values), columns= analytes)
            
            
            # #perform scaling for groups of analytes with same norm parameter
            # for norm in analyte_info['norm'].unique():
            #     filtered_analytes = analyte_info[(analyte_info['norm'] == norm)]['analytes']
            #     filtered_data = adj_data[filtered_analytes].values
            #     if norm == 'log':

            #         # np.nanlog handles NaN value
            #         self.data[sample_id]['processed_data'].loc[:,filtered_analytes] = np.log10(filtered_data, where=~np.isnan(filtered_data))
            #         # print(self.processed_analyte_data[sample_id].loc[:10,analytes])
            #         # print(self.data[sample_id]['processed_data'].loc[:10,analytes])
            #     elif norm == 'logit':
            #         # Handle division by zero and NaN values
            #         with np.errstate(divide='ignore', invalid='ignore'):
            #             analyte_array = np.log10(filtered_data / (10**6 - filtered_data), where=~np.isnan(filtered_data))
            #             self.data[sample_id]['processed_data'].loc[:,filtered_analytes] = analyte_array
            #     else:
            #         # set to clipped data with original values if linear normalisation
            #         self.data[sample_id]['processed_data'].loc[:,filtered_analytes] = filtered_data

            # perform autoscaling on columns where auto_scale is set to true
            for auto_scale in analyte_info['auto_scale'].unique():
                filtered_analytes = analyte_info[analyte_info['auto_scale'] == auto_scale]['analytes']

                for analyte_1 in filtered_analytes:
                    parameters = analyte_info.loc[(analyte_info['sample_id']==sample_id)
                                          & (analyte_info['analytes']==analyte_1)].iloc[0]
                    filtered_data =  data[sample_id]['processed_data'][analytes][analyte_1].values
                    lq = parameters['lower_bound']
                    uq = parameters['upper_bound']
                    d_lb = parameters['d_l_bound']
                    d_ub = parameters['d_u_bound']
                    if auto_scale:

                        data[sample_id]['processed_data'][analyte_1] = self.outlier_detection(filtered_data.reshape(-1, 1),lq, uq, d_lb,d_ub)
                    else:
                        #clip data using ub and lb
                        lq_val = np.nanpercentile(filtered_data, lq, axis=0)
                        uq_val = np.nanpercentile(filtered_data, uq, axis=0)
                        filtered_data = np.clip(filtered_data, lq_val, uq_val)
                        data[sample_id]['processed_data'][analyte_1] = filtered_data

                    # update v_min and v_max in self.data[sample_id]['analyte_info']
                    data[sample_id]['analyte_info'].loc[
                                             (data[sample_id]['analyte_info']['analytes']==analyte_1),'v_max'] = np.nanmax(filtered_data)
                    data[sample_id]['analyte_info'].loc[
                                             (data[sample_id]['analyte_info']['analytes']==analyte_1), 'v_min'] = np.nanmin(filtered_data)

            #add x and y columns from raw data
            data[sample_id]['processed_data']['X'] = data[sample_id]['cropped_raw_data']['X']
            data[sample_id]['processed_data']['Y'] = data[sample_id]['cropped_raw_data']['Y']

        else:  #if ratio
            ratio_df = data[sample_id]['cropped_raw_data'][[analyte_1,analyte_2]] #consider original data for ratio

            ratio_name = analyte_1+' / '+analyte_2

            # shifts analyte values so that all values are postive
            # ratio_array = self.transform_plots(ratio_df.values)
            ratio_array= ratio_df.values
            ratio_df = pd.DataFrame(ratio_array, columns= [analyte_1,analyte_2])
            
            # mask = (ratio_df[analyte_1] > 0) & (ratio_df[analyte_2] > 0)
            
            mask =   (ratio_df[analyte_2] == 0)

            ratio_array = np.where(mask, ratio_array[:,0] / ratio_array[:,1], np.nan)

            # Get the index of the row that matches the criteria
            index_to_update = data[sample_id]['ratio_info'].loc[
                    (data[sample_id]['ratio_info']['analyte_1'] == analyte_1) &
                    (data[sample_id]['ratio_info']['analyte_2'] == analyte_2)
                ].index

            # Check if we found such a row
            if len(index_to_update) > 0:
                idx = index_to_update[0]

                if pd.isna(data[sample_id]['ratio_info'].at[idx, 'lower_bound']): #if bounds are not updated in dataframe
                    #sets auto scale to true by default with default values for lb,db, d_lb and d_ub
                    auto_scale = True
                    norm = data[sample_id]['ratio_info'].at[idx, 'norm']
                    lb = 0.05
                    ub = 99.5
                    d_lb = 99
                    d_ub = 99
                    data[sample_id]['ratio_info'].at[idx, 'lower_bound'] = lb
                    data[sample_id]['ratio_info'].at[idx, 'upper_bound'] = ub
                    data[sample_id]['ratio_info'].at[idx, 'd_l_bound'] = d_lb
                    data[sample_id]['ratio_info'].at[idx, 'd_u_bound'] = d_ub
                    data[sample_id]['ratio_info'].at[idx, 'auto_scale'] = auto_scale
                    neg_method = self.comboBoxNegativeMethod.currentText()
                    min_positive_value = min(ratio_array[ratio_array>0])
                    data[sample_id]['ratio_info'].at[idx, 'negative_method'] = neg_method
                    # self.data[sample_id]['ratio_info'].at[idx, 'min_positive_value'] = min_positive_value
                else: #if bounds exist in ratios_df
                    norm = data[sample_id]['ratio_info'].at[idx, 'norm']
                    lb = data[sample_id]['ratio_info'].at[idx, 'lower_bound']
                    ub = data[sample_id]['ratio_info'].at[idx, 'upper_bound']
                    d_lb = data[sample_id]['ratio_info'].at[idx, 'd_l_bound']
                    d_ub = data[sample_id]['ratio_info'].at[idx, 'd_u_bound']
                    auto_scale = data[sample_id]['ratio_info'].at[idx, 'auto_scale']
                    neg_method = data[sample_id]['ratio_info'].at[idx, 'negative_method']
                    # min_positive_value = data[sample_id]['ratio_info'].at[idx, 'min_positive_value']
                    
                    
                # if norm == 'log':

                #     # np.nanlog handles NaN value
                #     ratio_array = np.log10(ratio_array, where=~np.isnan(ratio_array))
                #     # print(self.processed_analyte_data[sample_id].loc[:10,analytes])
                #     # print(self.data[sample_id]['processed_data'].loc[:10,analytes])
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

                if self.data[sample_id]['computed_data']['Ratio'].empty:
                    self.data[sample_id]['computed_data']['Ratio'] = self.data[sample_id]['cropped_raw_data'][['X','Y']]

                self.data[sample_id]['computed_data']['Ratio'][ratio_name] = ratio_array

                self.data[sample_id]['ratio_info'].at[idx, 'v_min'] = np.nanmin(ratio_array)
                self.data[sample_id]['ratio_info'].at[idx, 'v_max'] = np.nanmax(ratio_array)
    
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
            Update the scal information of the data, by default False
        """        
        if analyte_1: #if normalising single analyte
            if not analyte_2: #not a ratio
                data[sample_id]['analyte_info'].loc[(data[sample_id]['analyte_info']['sample_id']==sample_id)
                                 & (data[sample_id]['analyte_info']['analytes']==analyte_1),'norm'] = norm
                analytes = [analyte_1]
            else:
               data[sample_id]['ratio_info'].loc[
                   (data[sample_id]['ratio_info']['analyte_1'] == analyte_1) &
                   (data[sample_id]['ratio_info']['analyte_2'] == analyte_2),'norm'] = norm
               analytes = [analyte_1+' / '+analyte_2]

        else: #if normalising all analytes in sample
            data[sample_id]['analyte_info'].loc[(data[sample_id]['analyte_info']['sample_id']==sample_id),'norm'] = norm
            analytes = data[sample_id]['analyte_info'][data[sample_id]['analyte_info']['sample_id']==sample_id]['analytes']


        self.prep_data(sample_id, analyte_1, analyte_2)

        #update self.data['norm']
        for analyte in analytes:
            data[sample_id]['norm'][analyte] = norm

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
        #     axis_mask  = np.ones_like( self.data[sample_id]['raw_data']['X'], dtype=bool)
        # else:
        #     axis_mask = self.data[self.sample_id]['axis_mask']
        
        # retrieve axis mask for that sample
        axis_mask = data[sample_id]['axis_mask']
        
        #crop plot if filter applied
        df = data[sample_id]['raw_data'][['X','Y']][axis_mask].reset_index(drop=True)

        print(field_type)

        match field_type:
            case 'Analyte' | 'Analyte (normalized)':
                # unnormalized
                df ['array'] = data[sample_id]['processed_data'].loc[:,field].values
                #get analyte info
                norm = data[sample_id]['analyte_info'].loc[data[sample_id]['analyte_info']['analytes']==field,'norm'].iloc[0]
                
                #perform scaling for groups of analytes with same norm parameter
                
                if norm == 'log' and scale_data:
                    df['array'] = np.where(~np.isnan(df['array']), np.log10(df['array']), df['array'])

                    # print(self.processed_analyte_data[sample_id].loc[:10,analytes])
                    # print(self.data[sample_id]['processed_data'].loc[:10,analytes])
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
                #df['array'] = self.data[sample_id]['computed_data'].loc[:,field_1].values / self.data[sample_id]['processed_data'].loc[:,field_2].values
                df['array'] = data[sample_id]['computed_data']['Ratio'].loc[:,field].values
                
                # normalize
                if 'normalized' in field_type:
                    refval_1 = self.ref_chem[re.sub(r'\d', '', field_1).lower()]
                    refval_2 = self.ref_chem[re.sub(r'\d', '', field_2).lower()]
                    df['array'] = df['array'] * (refval_2 / refval_1)

                #get norm value
                norm = data[sample_id]['ratio_info'].loc['norm',(data[sample_id]['ratio_info']['analyte_1']==field_1 & data[sample_id]['ratio_info']['analyte_2']==field_2)].iloc[0]

                if norm == 'log' and scale_data:
                    df ['array'] = np.where(~np.isnan(df['array']), np.log10(df ['array']))
                    # print(self.processed_analyte_data[sample_id].loc[:10,analytes])
                    # print(self.data[sample_id]['processed_data'].loc[:10,analytes])
                elif norm == 'logit' and scale_data:
                    # Handle division by zero and NaN values
                    with np.errstate(divide='ignore', invalid='ignore'):
                        df['array'] = np.where(~np.isnan(df['array']), np.log10(df['array'] / (10**6 - df['array'])))

            case _:#'PCA Score' | 'Cluster' | 'Cluster Score' | 'Special' | 'Computed':
                df['array'] = data[sample_id]['computed_data'][field_type].loc[:,field].values
            
        # ----begin debugging----
        # print(df.columns)
        # ----end debugging----

        # crop plot if filter applied
        # current_plot_df = current_plot_df[self.data[self.sample_id]['axis_mask']].reset_index(drop=True)
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


        #n
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