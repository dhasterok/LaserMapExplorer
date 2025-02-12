import copy
import numpy as np

import src.common.Observable

class AppData(Observable):
    def __init__(self):
        super().__init__()
        self.default_preferences = {'Units':{'Concentration': 'ppm', 'Distance': 'µm', 'Temperature':'°C', 'Pressure':'MPa', 'Date':'Ma', 'FontSize':11, 'TickDir':'out'}}
        # in future will be set from preference ui
        self.preferences = copy.deepcopy(self.default_preferences)

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

        self._x_field_type = ""
        self._y_field_type = ""
        self._z_field_type = ""
        self._c_field_type = ""

        self._cluster_type = "k-means"
        self.cluster_dict = {
            'active method' : 'k-means',
            'k-means':{'n_clusters':5, 'seed':23, 'selected_clusters':[]},
            'fuzzy c-means':{'n_clusters':5, 'exponent':2.1, 'distance':'euclidean', 'seed':23, 'selected_clusters':[]}
        }


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
    def sample_id(self):
        return self._sample_id
    
    @sample_id.setter
    def sample_id(self, new_sample_id):
        if new_sample_id == self._sample_id:
            return

        self._sample_id = new_sample_id
        self.notify_observers("sample_id", new_sample_id)

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
