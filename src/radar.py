import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import src.radar_factory as radar_factory

class Radar:
    def __init__(self, ax, data, fields, fieldlabels=None, group_field='', groups=None, quantiles=None, axes_interval=5):
        """Prepares a DataFrame for a radar plot.

        _extended_summary_

        Parameters
        ----------
        ax : matplotlib.axes
            Axis object
        data : pandas.DataFrame
            Data used for averaging.
        fields : list
            list of fields in data used to define the axes.
        fieldlabels : list
            Labels associated with fields. If ``None``, ``fieldlabels`` is set to ``fields``, by default None
        group_field : str, optional
            _description_, by default ''
        groups : _type_, optional
            _description_, by default None
        quantiles : _type_, optional
            _description_, by default None
        axes_interval : int, optional
            _description_, by default 5

        Raises
        ------
        ValueError
            _description_
        """        
        self.fields = fields
        if fieldlabels is None:
            self.fieldlabels = self.fields
        else:
            self.fieldlabels = fieldlabels
        self.data = data
        self.groups = groups
        self.quantiles = quantiles
        if ax is None:
            self.fig = Figure(figsize=(6, 6))
            self.ax = self.fig.add_subplot(projection='radar')
        else:
            self.ax = ax
        
        if self.quantiles is not None:
            if group_field == '':
                self.vals = np.zeros((1, len(self.fields), len(self.quantiles)))
            else:
                self.vals = np.zeros((len(self.groups), len(self.fields), len(self.quantiles)))
        else:
            self.vals = np.zeros((len(self.groups), len(self.fields)))

        if group_field == '':
            if self.quantiles is None:
                self.vals = self.data[self.fields].mean().to_numpy()
            else:
                for j, q in enumerate(self.quantiles):
                    self.vals[0, :, j] = self.data[self.fields].quantile(q)
        else:
            for i, group in enumerate(self.groups):
                ind = self.data[group_field] == group
                if self.quantiles is None:
                    self.vals[i, :] = self.data.loc[ind, self.fields].mean().to_numpy()
                else:
                    for j, q in enumerate(self.quantiles):
                        self.vals[i, :, j] = self.data.loc[ind, self.fields].quantile(q)
                        
        if not isinstance(axes_interval, int) or axes_interval < 1:
            raise ValueError("Axes interval must be a positive integer.")
        self.axes_interval = axes_interval
        self.normalized_axis_increment = 1 / axes_interval
        self.normalize_vals()
        self.radius = 1+ self.normalized_axis_increment


    
    def normalize_vals(self):
        """Normalizes the data in self.vals for radar plot visualization."""
        # Determine the number of fields and groups
        group_count, field_count = self.vals.shape[:2]

        # Check if the number of fields matches the number of labels
        if len(self.fields) != field_count:
            raise ValueError("The number of labels must match the number of fields.")

        # Determine min and max values for each field
        self.fieldmin = np.nanmin(self.vals[..., 0], axis=0)
        self.fieldmax = np.nanmax(self.vals[..., -1], axis=0)
        
        # Adjust fields where min and max are equal
        equal_fields = self.fieldmax == self.fieldmin
        self.fieldmin[equal_fields] = self.vals[0, equal_fields, 0] - 0.1 * self.vals[0, equal_fields, 0]
        self.fieldmax[equal_fields] = self.vals[0, equal_fields, -1] + 0.1 * self.vals[0, equal_fields, -1]
        
        # Calculate range and normalized axis increment
        field_range = self.fieldmax - self.fieldmin
        
        radius_adj = 1- self.normalized_axis_increment

        # Normalize data
        for k in range(self.vals.shape[2]):
            self.vals[:, :, k] = (self.vals[:, :, k] - self.fieldmin) * radius_adj  / field_range + self.normalized_axis_increment
    
    def plot(self, cmap=None):
        """_summary_

        _extended_summary_

        Parameters
        ----------
        cmap : matplotlib.colormap, optional
            colormap, by default None
        """        
        axes_precision = 2
        num_vars = len(self.fields)
        theta = radar_factory(num_vars, frame='polygon')
        
        #fig = Figure(figsize=(6, 6))
        #ax = fig.add_subplot(projection='radar')
        
        self.ax.set_theta_direction(-1)
         
        if cmap is None:
            # Create a colormap object based on the provided name
            cmap = plt.cm.get_cmap('viridis')
        
        group_count, field_count, q_count = self.vals.shape

        for idx in range(group_count):
            if group_count >1:
                color = cmap[self.groups[idx]]
                label = self.groups[idx]
            else:
                color = cmap(0.5)
                label = None
            if q_count == 1:
                self.ax.plot(theta, self.vals[idx, :], color = color, label = label)
                self.ax.fill(theta, self.vals[idx, :], alpha=0.25, color = color)
            elif q_count == 2:
                inner_vals = np.append(self.vals[idx, :, 0],self.vals[idx, 0, 0])
                outer_vals = np.append(self.vals[idx, :, 1],self.vals[idx, 0, 1])
                self.ax.fill_between(np.append(theta, theta[0]), inner_vals, outer_vals, alpha =0.2,  color = color)
            elif q_count == 3:
                # Plot lower and upper quantiles as a filled area
                inner_vals = np.append(self.vals[idx, :, 0],self.vals[idx, 0, 0])
                outer_vals = np.append(self.vals[idx, :, 2],self.vals[idx, 0, 2])
                self.ax.fill_between(np.append(theta, theta[0]), inner_vals, outer_vals, alpha =0.2,  color = color)
                # Plot middle quantile as a line
                self.ax.plot(theta, self.vals[idx, :, 1], color = color, label = label)
            elif q_count == 5:
                # Similar approach for 5 quantiles...
                # Plot lowest and highest as lines, and fill between lower-middle-upper
                self.ax.plot(theta, self.vals[idx, :, 0], linestyle='dashed', alpha=0.5, color = color)
                self.ax.plot(theta, self.vals[idx, :, 4], linestyle='dashed', alpha=0.5, color = color)
                self.ax.plot(theta, self.vals[idx, :, 2], color = color)
                inner_vals = np.append(self.vals[idx, :, 0],self.vals[idx, 0, 0])
                outer_vals = np.append(self.vals[idx, :, 1],self.vals[idx, 0, 1])
                self.ax.fill_between(np.append(theta, theta[0]), inner_vals, outer_vals, alpha =0.2, color = color)
                
        radius = np.linspace(0, 1, len(self.ax.get_yticks()))  # Assuming normalized radius
        
        axis_increment = (self.fieldmax-self.fieldmin)/(self.axes_interval)
        
        # Calculate positions for the isocurve labels
        # x_isocurves = np.cos(theta[:, None]) * radius
        # y_isocurves = np.sin(theta[:, None]) * radius
        
        # Iterate through all the number of points
        for j in range(field_count):
            # Axis label for each row
            row_axis_labels = np.arange(self.fieldmin[j], self.fieldmax[j] + axis_increment[j], axis_increment[j])

            # Display axis text for each isocurve
            for i in range(1, len(radius)):
                self.ax.text(theta[j], radius[i], f"{row_axis_labels[i-1]:.{axes_precision}f}",
                color='k', fontsize=8,
                ha='center', va='center')

        
        self.ax.set_xticklabels(self.fieldlabels)
        #self.ax.set_dotted_grid_lines()
        self.ax.get_yaxis_transform(which='grid')
        self.ax.set_rgrids([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    
# Usage
# data = pd.read_csv('/Users/a1904121/LaserMapExplorer/laser_mapping/Alex_garnet_maps/processed data/RM01.csv')
# # data = pd.read_csv('/Users/shavinkalu/Library/CloudStorage/GoogleDrive-a1904121@adelaide.edu.au/.shortcut-targets-by-id/1r_MeSExALnv9lHE58GoG7pbtC8TOwSk4/laser_mapping/Alex_garnet_maps/processed data/RM01.csv')
# el_list = data.columns[5:10]
# axes_interval = 5
# data['clusters'] = np.random.randint(1, 6, size=len(data))
# unique_labels = data['clusters'].unique()
# n_clusters = len(unique_labels)
# cmap = plt.get_cmap('viridis', n_clusters)
# # Extract colors from the colormap
# colors = [cmap(i) for i in range(cmap.N)]
# group_cmap = {}
# # Assign these colors to self.group_cmap
# for label, color in zip(unique_labels, colors):
#     group_cmap[label] = color

# radar = Radar(data, el_list, quantiles=[0.05,0.25, 0.5, 0.75,0.95], axes_interval = axes_interval, group_field ='clusters', groups = unique_labels)


# fig,ax = radar.plot(cmap = group_cmap)

# # ref_data = pd.read_excel('earthref.xlsx')

# # # data = pd.read_csv('/Users/a1904121/LaserMapExplorer/laser_mapping/Alex_garnet_maps/processed data/RM01.csv')
# data = pd.read_csv('/Users/shavinkalu/Library/CloudStorage/GoogleDrive-a1904121@adelaide.edu.au/.shortcut-targets-by-id/1r_MeSExALnv9lHE58GoG7pbtC8TOwSk4/laser_mapping/Alex_garnet_maps/processed data/RM01.csv')
# el_list = data.columns[5:10]

# # i = 1


# # # # plot_spider_norm(data, ref_data, norm_ref_data, layer,el_list=None, style='Quanta', quantiles=[0.05, 0.25, 0.5, 0.75, 0.95], ref_data_field='sio2', ref_data_val='median', ax=None)
# # fig, ax = plot_spider_norm(data = data[el_list.values],ref_data = ref_data,norm_ref_data =  ref_data['model'][i], layer = ref_data['layer'][i],el_list= el_list ,style = 'Quanta')

# # plt.show()


# # Example usage
# radar = Radar(data, el_list, quantiles = [0.25, 0.5, 0.75])
# radar.radar()