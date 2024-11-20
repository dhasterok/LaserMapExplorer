import os, pickle
from PyQt5 import QtCore
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import ( QMessageBox, QInputDialog, QWidget, QTableWidgetItem, QVBoxLayout )
from pyqtgraph import ( ScatterPlotItem )
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.colors as colors
from matplotlib.collections import PathCollection
import numpy as np


# Profiles
# -------------------------------
# The following class defines the metadata of profiles created along with information regarding each point
class Profile:
    def __init__(self,name,sort,radius,thresh,int_dist, point_error):
        self.name = name  # name given by user for the profile
        self.points = {}  # stores points (x,y, circ_value, interpolate)
        self.i_points = {}
        self.sort = sort
        self.radius = radius
        self.y_axis_thresh = thresh
        self.int_dist = int_dist
        self.point_error = point_error
        self.scatter_points = {} # (scatter_value, interpolate)
        

class Profiling:
    def __init__(self, main_window):
        """Initialize the Profiling class.

        Sets up the profiling functionality, initializing necessary attributes and states.

        Parameters
        ----------
        main_window : object
            The main window object that the profiling class interacts with.
        """
        self.main_window = main_window
        # Initialize other necessary attributes
        # Initialize variables and states as needed
        self.profiles = {}
        self.point_selected = False  # move point button selected
        self.point_index = -1              # index for move point
        self.all_errorbars = []       #stores points of profiles
        self.selected_points = {}  # Track selected points, e.g., {point_index: selected_state}
        self.edit_mode_enabled = False  # Track if edit mode is enabled
        self.original_colors = {}
        self.profile_name = None

    def add_samples(self):
        """Add sample IDs to the profiles dictionary.

        Initializes an empty dictionary for each sample ID to store profiles.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        # add sample id to dictionary
        for sample_id in self.main_window.sample_ids:
            if sample_id not in self.profiles:
                self.profiles[sample_id] = {}

    def save_profiles(self, project_dir, sample_id):
        """Save profiles to files with *.prfl extension.

        Serializes and saves profile data for a given sample into the specified project directory.

        Parameters
        ----------
        project_dir : str
            The directory where profile data will be stored.
        sample_id : str
            The sample ID whose profiles are to be saved.

        Returns
        -------
        None
        """
        # convert the profile object to serializable object which can be pickled,
        if sample_id in self.profiles:
            for profile_name, profile in self.profiles[sample_id].items():
                file_name = os.path.join(project_dir, sample_id, f'{profile_name}.prfl')
                serializable_profile = self.transform_profile_for_pickling(profile)
                with open(file_name, 'wb') as file:
                    pickle.dump(serializable_profile, file)
            print("Profile saved successfully.")

    def load_profiles(self, project_dir, sample_id):
        """Load saved profiles from files.

        Deserializes and loads profile data for a given sample from the specified project directory.

        Parameters
        ----------
        project_dir : str
            The directory from which to load profile data.
        sample_id : str
            The sample ID whose profiles are to be loaded.

        Returns
        -------
        None
        """
        # add sample_id to profile dictionary if needed
        # open profile file, convert to original format and add saved profiles to self.profiles
        directory = os.path.join(project_dir, sample_id)
        for file_name in os.listdir(directory):
            if file_name.endswith(".prfl"):
                file_path = os.path.join(directory, file_name)
                with open(file_path, 'rb') as file:
                    profile_name = os.path.basename(file_path).split('.')[0]
                    serializable_profile = pickle.load(file)
                    profile = self.reconstruct_profile(serializable_profile)
                    self.profiles[sample_id][profile_name] = profile
        self.populate_combobox()
        print("All profiles loaded successfully.")

    def transform_profile_for_pickling(self, profile):
        """Convert profile object into a serializable format for pickling.

        Transforms profile attributes into basic data types to enable serialization using pickle.

        Parameters
        ----------
        profile : Profile
            The Profile object to be transformed.

        Returns
        -------
        serializable_profile : dict
            A dictionary containing the transformed profile data suitable for pickling.
        """
        serializable_profile = {
            'name': profile.name,
            'sort': profile.sort,
            'radius': profile.radius,
            'y_axis_thresh': profile.y_axis_thresh,
            'int_dist': profile.int_dist,
            'point_error': profile.point_error,
            'points': {},
            'i_points': {}
        }
        for (field, view), points in profile.points.items():
            serializable_points = []
            for point in points:
                x, y, circ_val, scatter, interpolate = point
                scatter_state = self.extract_scatter_plot_state(scatter)
                serializable_points.append((x, y, circ_val, scatter_state, interpolate))
            serializable_profile['points'][(field, view)] = serializable_points
        for (field, view), i_points in profile.i_points.items():
            serializable_i_points = []
            for point in i_points:
                x, y, circ_val, scatter, interpolate = point
                scatter_state = self.extract_scatter_plot_state(scatter)
                serializable_i_points.append((x, y, circ_val, scatter_state, interpolate))
            serializable_profile['i_points'][(field, view)] = serializable_i_points
        return serializable_profile

    def extract_scatter_plot_state(self, scatter):
        """Extract the state of a ScatterPlotItem for serialization.

        Collects data and properties from a ScatterPlotItem to create a serializable representation.

        Parameters
        ----------
        scatter : ScatterPlotItem
            The scatter plot item to extract the state from.

        Returns
        -------
        state : dict
            A dictionary containing data necessary to recreate the scatter plot item.
        """
        data = scatter.getData()
        symbol = scatter.opts['symbol']
        size = scatter.opts['size']
        z_value = scatter.zValue()
        return {'data': data, 'symbol': symbol, 'size': size, 'z_value': z_value}

    def recreate_scatter_plot(self, state):
        """Recreate a ScatterPlotItem from its saved state.

        Uses the serialized state to reconstruct a ScatterPlotItem instance.

        Parameters
        ----------
        state : dict
            The dictionary containing scatter plot data and properties.

        Returns
        -------
        scatter : ScatterPlotItem
            The reconstructed scatter plot item.
        """
        scatter = ScatterPlotItem(state['data'][0], state['data'][1], symbol=state['symbol'], size=state['size'])
        scatter.setZValue(state['z_value'])
        return scatter

    def reconstruct_profile(self, serializable_profile):
        """Reconstruct a Profile object from its serialized form.

        Deserializes and rebuilds a Profile object using the data from a serialized profile dictionary.

        Parameters
        ----------
        serializable_profile : dict
            The dictionary containing serialized profile data.

        Returns
        -------
        profile : Profile
            The reconstructed Profile object.
        """
        profile = Profile(
            serializable_profile['name'],
            serializable_profile['sort'],
            serializable_profile['radius'],
            serializable_profile['y_axis_thresh'],
            serializable_profile['int_dist'],
            serializable_profile['point_error']
        )
        for (field, view), points in serializable_profile['points'].items():
            reconstructed_points = []
            for point in points:
                x, y, circ_val, scatter_state, interpolate = point
                scatter = self.recreate_scatter_plot(scatter_state)
                reconstructed_points.append((x, y, circ_val, scatter, interpolate))
            profile.points[(field, view)] = reconstructed_points
        for (field, view), i_points in serializable_profile['i_points'].items():
            reconstructed_i_points = []
            for point in i_points:
                x, y, circ_val, scatter_state, interpolate = point
                scatter = self.recreate_scatter_plot(scatter_state)
                reconstructed_i_points.append((x, y, circ_val, scatter, interpolate))
            profile.i_points[(field, view)] = reconstructed_i_points
        return profile

    def populate_combobox(self):
        """Populate the profile selection combobox.

        Clears and repopulates the combobox with the list of profile names for the current sample.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        self.main_window.comboBoxProfileList.clear()
        self.main_window.comboBoxProfileList.addItem('Create New Profile')
        for profile_name in self.profiles[self.main_window.sample_id].keys():
            self.main_window.comboBoxProfileList.addItem(profile_name)

    def load_profiles_from_directory(self, project_dir, sample_id):
        """Load all profiles from a directory for a sample.

        Iterates over .prfl files in the specified directory and loads profiles for the given sample.

        Parameters
        ----------
        project_dir : str
            The directory containing the profiles.
        sample_id : str
            The sample ID whose profiles are to be loaded.

        Returns
        -------
        None
        """
        directory = os.path.join(project_dir, sample_id)
        for file_name in os.listdir(directory):
            if file_name.endswith(".prfl"):
                file_path = os.path.join(directory, file_name)
                with open(file_path, 'rb') as file:
                    profile_name = os.path.basename(file_path).split('.')[0]
                    self.profiles[sample_id][profile_name] = pickle.load(file)

        self.populate_combobox()
        print("All profiles loaded successfully.")

    def on_profile_selected(self, profile_name):
        """Handle profile selection from the combobox.

        Loads existing profile data or creates a new profile based on the user's selection.

        Parameters
        ----------
        profile_name : str
            The name of the selected profile.

        Returns
        -------
        None
        """
        if profile_name == 'Create New Profile':  # create a new profile instance and store instance in self.profiles
            new_profile_name, ok = QInputDialog.getText(self.main_window, 'New Profile', 'Enter new profile name:')
            if ok and new_profile_name:
                if new_profile_name in self.profiles[self.main_window.sample_id]:
                    QMessageBox.warning(self.main_window, 'Error', 'Profile name already exists!')
                else:
                    self.clear_profiles()  # clear profiling plots and  contents
                    # obtain metadata of profiles from UI
                    sort = self.main_window.comboBoxProfileSort.currentText()
                    radius = self.main_window.lineEditPointRadius.text()
                    thresh = self.main_window.lineEditPointRadius.text()
                    int_dist = self.main_window.lineEditIntDist.text()
                    point_error = self.main_window.comboBoxPointType.currentText()

                    # create new profile instance
                    self.profiles[self.main_window.sample_id][new_profile_name] = Profile(new_profile_name, sort, radius, thresh, int_dist, point_error)
                    # add profile name to profile table
                    self.main_window.comboBoxProfileList.addItem(new_profile_name)
                    self.main_window.comboBoxProfileList.setCurrentText(new_profile_name)
                    self.profile_name = new_profile_name
            else:
                self.main_window.comboBoxProfileList.setCurrentIndex(0)  # Reset to 'Create New Profile'
        else:
            # plot existing profile and load profile metadata from dictionary
            self.profile_name = profile_name
            self.plot_existing_profile(self.main_window.plot)
            profile = self.profiles[self.main_window.sample_id][self.profile_name]
            self.main_window.comboBoxProfileSort.setCurrentText(profile.sort)
            self.main_window.lineEditPointRadius.setText(profile.radius)
            self.main_window.lineEditPointRadius.setText(profile.y_axis_thresh)
            self.main_window.lineEditIntDist.setText(profile.int_dist)
            self.main_window.comboBoxPointType.setCurrentText(profile.point_error)
            self.plot_profiles()
            self.update_table_widget()

    def cart_to_dist(self, pixel: int, direction='y') -> float:
        """Convert pixel units to distance units.

        Converts pixel coordinates to physical distance based on the array size and range.

        Parameters
        ----------
        pixel : int
            The pixel value to convert.
        direction : str, optional
            The axis direction ('x' or 'y'), default is 'y'.

        Returns
        -------
        distance : float
            The physical distance corresponding to the pixel value.
        """
        if direction == 'x':
            return pixel * self.data.array_size[1] / self.data.x_range
        else:
            return pixel * self.data.array_size[0] / self.data.y_range

    def dist_to_cart(self, dist: float, direction='y') -> int:
        """Convert distance units to pixel units.

        Converts physical distance to pixel coordinates based on the array size and range.

        Parameters
        ----------
        dist : float
            The physical distance to convert.
        direction : str, optional
            The axis direction ('x' or 'y'), default is 'y'.

        Returns
        -------
        pixel : int
            The pixel value corresponding to the physical distance.
        """
        if direction == 'x':
            return round(dist * self.data.dx)
        else:
            return round(dist * self.data.dy)

    def plot_profile_scatter(self, event, field , view, plot, x, y, x_i, y_i):
        """Plot a scatter point for profile at the clicked position.

        Computes the profile value by averaging concentrations over a specified radius around the clicked point and plots it.

        Parameters
        ----------
        event : object
            The mouse event recorded on the canvas.
        field: 'str'
            Field name of map
        view: 'int'
            : ``self.canvasWindow.currentIndex() ``
        plot : object
            The plot window where the scatter point will be added.
        x : float
            The x-coordinate of the click position.
        y : float
            The y-coordinate of the click position.
        x_i : float
            The index of the x-coordinate in the array.
        y_i : float
            The index of the y-coordinate in the array.

        Returns
        -------
        None
        """
        self.sample_id = self.main_window.sample_id
        self.data = self.main_window.data[self.sample_id]
        self.array_x = self.data.array_size[1]  # no of columns
        self.array_y = self.data.array_size[0]  # no of rows
        interpolate = False

        profile_points = self.profiles[self.sample_id][self.profile_name].points
        scatter_points = self.profiles[self.sample_id][self.profile_name].scatter_points

        radius = int(self.main_window.lineEditPointRadius.text())
        if event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPlotProfile.isChecked():
            # Turn off profiling points
            self.main_window.toolButtonPlotProfile.setChecked(False)
            self.main_window.toolButtonPointMove.setEnabled(True)
            return
        elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPointMove.isChecked():
            # Turn off moving point, reset point_selected
            self.main_window.toolButtonPointMove.setChecked(False)
            self.point_selected = False
            return
        elif event.button() == QtCore.Qt.RightButton or event.button() == QtCore.Qt.MiddleButton:
            return
        elif event.button() == QtCore.Qt.LeftButton and not (self.main_window.toolButtonPlotProfile.isChecked()) and self.main_window.toolButtonPointMove.isChecked():
            # move point
            if self.point_selected:
                # Add the scatter item to all plots and save points in profile
                for (field,view), (_, plot,  array) in self.main_window.lasermaps.items():
                    plot.removeItem(prev_scatter)
                    if self.array_x ==array.shape[1] and self.array_y ==array.shape[0] : #ensure points within boundaries of plot
                        # remove selected point
                        prev_scatter = scatter_points[(field,view)][self.point_index]
                        plot.removeItem(prev_scatter)

                        # Create a scatter plot item at the clicked position
                        scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                        scatter.setZValue(1e9)
                        plot.addItem(scatter)
                        scatter_points[self.point_index] = scatter
                self.compute_profile_points(profile_points, radius, x, y, x_i, y_i, self.point_index)
                self.point_index = -1              # reset index 
                if self.main_window.toolButtonProfileInterpolate.isChecked():  # reset interpolation if selected
                    self.clear_interpolation()
                    self.interpolate_points(interpolation_distance=int(self.main_window.lineEditIntDist.text()), radius=int(self.main_window.lineEditPointRadius.text()))
                # switch to profile tab
                self.main_window.tabWidget.setCurrentIndex(self.main_window.bottom_tab['profile'])
                self.plot_profiles()  # Plot averaged profile value on profiles plots with error bars
                self.update_table_widget()
            else:
                # find nearest profile point
                mindist = 10 ** 12
                for i, (x_p, y_p, _, _, interpolate) in enumerate(profile_points[field, view]):
                    dist = (x_p - x) ** 2 + (y_p - y) ** 2
                    if mindist > dist:
                        mindist = dist
                        self.point_index = i
                if not (round(mindist * self.array_x / self.data.x_range) < 50):
                    self.point_selected = True
        elif event.button() == QtCore.Qt.LeftButton:  # plot profile scatter
            # Add the scatter item to all plots and save points in profile
            for (field,view), (_, plot,  array) in self.main_window.lasermaps.items():
                circ_val = []
                if self.array_x ==array.shape[1] and self.array_y ==array.shape[0] : #ensure points within boundaries of plot
                    # Create a scatter plot item at the clicked position
                    scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                    scatter.setZValue(1e9)
                    plot.addItem(scatter)
                    # add scatter point
                    if (field, view) in scatter_points:
                        scatter_points[(field,view)].append(scatter)
                    else:
                        scatter_points[(field,view)]= [(scatter)]
            self.compute_profile_points(profile_points, radius, x, y, x_i, y_i)
            # switch to profile tab
            self.main_window.tabWidget.setCurrentIndex(self.main_window.bottom_tab['profile'])
            
            self.plot_profiles(fields=[field])  # Plot averaged profile value on profiles plots with error bars
            self.update_table_widget()

    

    def compute_profile_points(self, profile_points, radius, x, y, x_i, y_i, point_index=None):
        """Compute profile points by averaging values within a radius.

        Calculates the mean values within a specified radius around a point and updates the profile points.

        Parameters
        ----------
        profile_points : dict
            Dictionary to store computed profile points.
        radius : int
            The radius around the point to consider for averaging.
        x : float
            The x-coordinate of the point.
        y : float
            The y-coordinate of the point.
        x_i : int
            The index of the x-coordinate in the array.
        y_i : int
            The index of the y-coordinate in the array.
        point_index : int, optional
            The index of the point if updating an existing point.

        Returns
        -------
        None
        """
        # Obtain field data of all fields that will be used for profiling
        fields= self.data.processed_data.match_attribute('data_type','analyte')+ self.data.processed_data.match_attribute('data_type','ratio')
        field_data = self.data.processed_data[fields]
        for field in field_data.columns:
            # If updating an existing point, remove it first
            if point_index is not None and field in profile_points and len(profile_points[field]) > point_index:
                del profile_points[field][point_index]

            array = np.reshape(field_data[field].values, self.data.array_size, order=self.data.order)
            # Find all points within the specified radius
            circ_val = []
            p_radius_y = self.dist_to_cart(radius, 'y')  # Pixel radius in y direction
            p_radius_x = self.dist_to_cart(radius, 'x')  # Pixel radius in x direction

            # Store pixel values within bounds of circle with center (x_i, y_i) and radius `radius`
            for i in range(max(0, y_i - p_radius_y), min(self.array_y, y_i + p_radius_y + 1)):
                for j in range(max(0, x_i - p_radius_x), min(self.array_x, x_i + p_radius_x + 1)):
                    if self.calculate_distance(self.cart_to_dist(y_i - i), self.cart_to_dist(x_i - j)) <= radius:
                        value = array[i, j]
                        circ_val.append(value)

            # Add values within circle of radius in profile
            if field in profile_points:
                if point_index is not None:
                    # Insert at the correct index if updating
                    profile_points[field].insert(point_index, (x, y, circ_val))
                else:
                    profile_points[field].append((x, y, circ_val))  # Append profile point list
            else:
                profile_points[field] = [(x, y, circ_val)]  # Create profile point list

    def plot_existing_profile(self, plot):
        """Plot existing profile points on the plot.

        Clears existing plot and plots all profile points for the selected profile.

        Parameters
        ----------
        plot : object
            The plot window where the profile points will be plotted.

        Returns
        -------
        None
        """
        # clear existing plot
        self.clear_plot()
        if self.profile_name in self.profiles[self.main_window.sample_id]:
            profile_points = self.profiles[self.main_window.sample_id][self.profile_name].points
            for (field, view) in profile_points:
                for x, y, _, _, _ in profile_points[field, view]:
                    # Create a scatter plot item
                    scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                    scatter.setZValue(1e9)
                    plot.addItem(scatter)

    def interpolate_points(self, interpolation_distance, radius):
        """Interpolate points between existing profile points.

        Generates interpolated points between profile points and updates the plot accordingly.

        Parameters
        ----------
        interpolation_distance : int
            The distance between interpolated points.
        radius : int
            The radius to use when computing values for interpolated points.

        Returns
        -------
        None
        """
        profile_points = self.profiles[self.main_window.sample_id][self.profile_name].points
        i_profile_points = self.profiles[self.main_window.sample_id][self.profile_name].i_points

        if self.main_window.toolButtonProfileInterpolate.isChecked():
            interpolate = True
            for (field, view), points in profile_points.items():
                for i in range(len(points) - 1):
                    start_point = points[i]
                    end_point = points[i + 1]
                    if i == 0:
                        i_profile_points[(field, view)] = [start_point]
                    else:
                        i_profile_points[(field, view)].append(start_point)

                    # Calculate the distance between start and end points
                    dist = self.calculate_distance(start_point, end_point)

                    # Determine the number of interpolations based on the distance
                    num_interpolations = max(int(dist / interpolation_distance), 0)

                    # Calculate the unit vector in the direction from start_point to end_point
                    dx = (end_point[0] - start_point[0]) / dist
                    dy = (end_point[1] - start_point[1]) / dist

                    for t in range(0, num_interpolations + 1):
                        x = start_point[0] + t * interpolation_distance * dx
                        y = start_point[1] + t * interpolation_distance * dy

                        x_i = self.dist_to_cart(x, 'x')  # index points
                        y_i = self.dist_to_cart(y, 'y')

                        # Add the scatter item to all other plots and save points in profile
                        _, p, array = self.main_window.lasermaps[(field, view)]
                        if (v == self.main_window.canvasWindow.currentIndex()) and (self.array_x == array.shape[1]) and (self.array_y == array.shape[0]):  # only add scatters to other lasermaps of same sample
                            # Create a scatter plot item at the clicked position
                            scatter = ScatterPlotItem([x], [y], symbol='+', size=5)
                            scatter.setZValue(1e9)
                            p.addItem(scatter)
                            # Find all points within the specified radius
                            circ_val = []

                            p_radius_y = self.dist_to_cart(radius, 'y')  # pixel radius in pixels y direction
                            p_radius_x = self.dist_to_cart(radius, 'x')  # pixel radius in pixels x direction

                            for i in range(max(0, y_i - p_radius_y), min(self.array_y, y_i + p_radius_y + 1)):
                                for j in range(max(0, x_i - p_radius_x), min(self.array_x, x_i + p_radius_x + 1)):
                                    if self.calculate_distance(self.cart_to_dist(y_i - i) ** 2, self.cart_to_dist(x_i - j) ** 2) <= radius:
                                        value = array[i, j]
                                        circ_val.append(value)

                            if (field, view) in i_profile_points:
                                i_profile_points[(field, view)].append((x, y, circ_val, scatter, interpolate))

                    i_profile_points[(field, view)].append(end_point)
            # After interpolation, update the plot and table widget
            self.plot_profiles(interpolate=interpolate)
        else:
            self.clear_interpolation()
            # plot original profile
            self.plot_profiles(interpolate=False)
        # self.update_table_widget(interpolate= True)

    def clear_plot(self):
        """Clear all existing profiles from the plot.

        Removes all profile points and interpolated points from the plot for the current sample.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        if self.main_window.sample_id in self.profiles:
            for profile_name, profile in self.profiles[self.main_window.sample_id].items():
                # Clear points from the plot
                for (field, view), points in profile.points.items():
                    for _, _, _, scatter, _ in points:
                        self.main_window.plot.removeItem(scatter)

                # Clear interpolated points from the plot (if applicable)
                for (field, view), i_points in profile.i_points.items():
                    for _, _, _, scatter, _ in i_points:
                        self.main_window.plot.removeItem(scatter)

    def clear_interpolation(self):
        """Clear all interpolated points from the plot.

        Removes all interpolated profile points from the plot for the current profile.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        i_profile_points = self.profiles[self.main_window.sample_id][self.profile_name].i_points
        # remove interpolation
        if len(i_profile_points) > 0:
            for (field, view), profile in i_profile_points.items():
                for point in profile:
                    scatter_item = point[3]  # Access the scatter plot item
                    interpolate = point[4]
                    if interpolate:
                        _, plot, _ = self.main_window.lasermaps[(field, view)]
                        plot.removeItem(scatter_item)

    def plot_profiles(self, fields=None, num_subplots=None, selected_subplot=None, interpolate=False, sort_axis=None):
        """Plot averaged profile values with error bars.

        Plots the profile values stored in self.profiles with error bars on the specified subplot(s),
        optionally using interpolated points.

        Parameters
        ----------
        fields : list of str, optional
            List of fields to plot. If None, fields are obtained from self.main_window.listViewProfile.
        num_subplots : int, optional
            Number of subplots to create. If None, value is obtained from self.main_window.spinBoxProfileNumSubplots.
        selected_subplot : int, optional
            Index of the selected subplot to plot on (1-based). If None, value is obtained from self.main_window.spinBoxProfileSelectedSubplots.
        interpolate : bool, optional
            Whether to use interpolated points. Default is False.
        sort_axis : str, optional
            Axis to sort the profile points by ('x' or 'y'). If None, obtained from self.main_window.comboBoxProfileSort.

        Returns
        -------
        None
        """
        # Get fields from the list view if not provided
        if fields is None:
            fields = self.get_fields_from_listview()
        else:
            for field in fields:
                self.add_field_to_listview(field,update=False) # add field used to generate points to list view (Field viewer table in Profiles tab)
        # Get num_subplots and selected_subplot from UI if not provided
        if num_subplots is None:
            num_subplots = self.main_window.spinBoxProfileNumSubplots.value()
        if selected_subplot is None:
            selected_subplot = self.main_window.spinBoxProfileSelectedSubplot.value()

        # Get the point type
        point_type_text = self.main_window.comboBoxPointType.currentText()
        if point_type_text == 'median + IQR':
            point_type = 'median'
        else:
            point_type = 'mean'

        # Get sort axis if not provided
        if sort_axis is None:
            sort_axis = self.main_window.comboBoxProfileSort.currentText().lower()

        # Decide whether to use interpolated points
        if interpolate:
            profile_points = self.profiles[self.main_window.sample_id][self.profile_name].i_points
        else:
            profile_points = self.profiles[self.main_window.sample_id][self.profile_name].points

        # Get style and colormap
        style = self.main_window.style
        cmap = style.get_colormap()

        # Clear existing plot
        layout = self.main_window.widgetProfilePlot.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Initialize the figure
        self.fig = Figure()
        self.fig.canvas.mpl_connect('pick_event', self.on_pick)

        # Set up subplots
        self.all_errorbars = []
        num_fields = len(fields)
        if num_subplots < 1:
            num_subplots = 1
        if num_subplots > num_fields:
            num_subplots = num_fields

        # Create subplots
        axes = []
        for i in range(num_subplots):
            ax = self.fig.add_subplot(num_subplots, 1, i + 1)
            axes.append(ax)

        # Map fields to subplots
        fields_per_subplot = {i: [] for i in range(num_subplots)}

        # Plot all fields on the selected subplot
        subplot_idx = selected_subplot - 1  # Convert to 0-based index
        fields_per_subplot = {i: [] for i in range(num_subplots)}
        fields_per_subplot[subplot_idx] = fields

        # Now, plot the fields
        for subplot_idx, ax in enumerate(axes):
            fields_in_subplot = fields_per_subplot[subplot_idx]
            if not fields_in_subplot:
                continue  # No fields to plot in this subplot

            for field_idx, field in enumerate(fields_in_subplot):
                # Get the points for the field
                key = (field, self.main_window.canvasWindow.currentIndex())
                if field not in profile_points:
                    continue  # Skip if no data for this field
                points = profile_points[field]

                # Process points
                distances, medians, lowers, uppers, means, s_errors = self.process_points(points, sort_axis)

                # Decide color
                color = cmap(field_idx / len(fields_in_subplot))

                # Plot data
                if point_type == 'median':
                    # Use medians and IQR
                    errors = [[median - lower for median, lower in zip(medians, lowers)],
                              [upper - median for upper, median in zip(uppers, medians)]]
                    scatter = ax.scatter(distances, medians,
                                         color=color,
                                         s=style.marker_size,
                                         marker=style.marker_dict[style.marker],
                                         edgecolors='none',
                                         picker=5,
                                         gid=field,
                                         label=field)
                    # Plot error bars
                    _, _, barlinecols = ax.errorbar(distances, medians,
                                                    yerr=errors,
                                                    fmt='none',
                                                    color=color,
                                                    ecolor=style.line_color,
                                                    elinewidth=style.line_width,
                                                    capsize=0)
                    self.all_errorbars.append((scatter, barlinecols[0]))
                    self.original_colors[field] = color
                    self.selected_points[field] = [False] * len(medians)
                else:
                    # Use means and standard errors
                    scatter = ax.scatter(distances, means,
                                         color=color,
                                         s=style.marker_size,
                                         marker=style.marker_dict[style.marker],
                                         edgecolors='none',
                                         picker=5,
                                         gid=field,
                                         label=field)
                    # Plot error bars
                    _, _, barlinecols = ax.errorbar(distances, means,
                                                    yerr=s_errors,
                                                    fmt='none',
                                                    color=color,
                                                    ecolor=style.line_color,
                                                    elinewidth=style.line_width,
                                                    capsize=0)
                    self.all_errorbars.append((scatter, barlinecols[0]))
                    self.original_colors[field] = color
                    self.selected_points[field] = [False] * len(means)

            # Set labels and legend
            if subplot_idx == num_subplots - 1:
                ax.set_xlabel('Distance')
            else:
                ax.xaxis.set_visible(False)
            ax.set_ylabel('Value')
            ax.legend()

        # Adjust layout
        self.fig.tight_layout(pad=3, w_pad=0, h_pad=0)
        self.fig.subplots_adjust(wspace=0, hspace=0)

        # Embed the matplotlib plot in a QWidget
        canvas = FigureCanvas(self.fig)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(canvas)
        widget.setLayout(layout)

        # Add the new plot widget to the layout
        self.main_window.widgetProfilePlot.layout().addWidget(widget)
        widget.show()

    def get_fields_from_listview(self):
        """Retrieve the list of fields from the profile list view.

        Extracts the selected fields from the UI's list view widget to determine which fields to plot.

        Parameters
        ----------
        None

        Returns
        -------
        fields : list of str
            List of field names selected in the list view.
        """
        fields = []
        model = self.main_window.listViewProfile.model()
        if not model:
            #set item model if it doesnt exist
            model = QStandardItemModel()
            self.main_window.listViewProfile.setModel(model)
        for index in range(model.rowCount()):
            item = model.item(index)
            fields.append(item.text())
        return fields

    def process_points(self, points, sort_axis):
        """Process profile points to compute statistics and distances.

        Calculates distances and statistical measures (median, mean, quartiles, standard errors) for profile points.

        Parameters
        ----------
        points : list
            List of profile points, each point is a tuple (x, y, values).
        sort_axis : str
            Axis to sort the points by ('x' or 'y').

        Returns
        -------
        distances : list of float
            Cumulative distances along the profile.
        median_values : list of float
            Median values at each point.
        lower_quantiles : list of float
            Lower quartile (25th percentile) at each point.
        upper_quantiles : list of float
            Upper quartile (75th percentile) at each point.
        mean_values : list of float
            Mean values at each point.
        standard_errors : list of float
            Standard errors at each point.
        """
        # Sort the points based on the user-specified axis
        if sort_axis == 'x':
            points.sort(key=lambda p: p[0])  # Sort by x-coordinate
        elif sort_axis == 'y':
            points.sort(key=lambda p: p[1])  # Sort by y-coordinate

        median_values = []
        lower_quantiles = []
        upper_quantiles = []
        mean_values = []
        standard_errors = []
        distances = []

        for i, point in enumerate(points):
            x, y, values = point[0], point[1], point[2]
            # Compute statistics
            median = np.median(values)
            lower = np.quantile(values, 0.25)
            upper = np.quantile(values, 0.75)
            mean = np.mean(values)
            std_err = np.std(values, ddof=1) / np.sqrt(len(values))

            median_values.append(median)
            lower_quantiles.append(lower)
            upper_quantiles.append(upper)
            mean_values.append(mean)
            standard_errors.append(std_err)

            # Compute distances
            if i == 0:
                distances.append(0)
            else:
                prev_point = points[i - 1]
                dist = self.calculate_distance((x, y), (prev_point[0], prev_point[1]))
                distances.append(distances[-1] + dist)

        return distances, median_values, lower_quantiles, upper_quantiles, mean_values, standard_errors
        

    def clear_profiles(self):
        """Clear profile data and plots.

        Removes all profile scatter points from the plots and clears profile data from the table.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        if self.main_window.sample_id in self.profiles:  # if profiles have been initiated for the samples
            if self.profile_name in self.profiles[self.main_window.sample_id]:  # if profiles for that sample exist
                # Clear all scatter plot items from the lasermaps
                for _, (_, plot, _) in self.main_window.lasermaps.items():
                    items_to_remove = [item for item in plot.listDataItems() if isinstance(item, ScatterPlotItem)]
                    for item in items_to_remove:
                        plot.removeItem(item)

                # Clear the profiles data
                # profile.clear()

                # Clear all data from the table
                self.main_window.tableWidgetProfilePoints.clearContents()

                # Remove all rows
                self.main_window.tableWidgetProfilePoints.setRowCount(0)

                # Clear the profile plot widget
                layout = self.main_window.widgetProfilePlot.layout()
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()

    def calculate_distance(self, point1, point2):
        """Calculate the Euclidean distance between two points.

        Computes the Euclidean distance between two 2D points or from the origin if scalar values are given.

        Parameters
        ----------
        point1 : tuple, list, or float
            The first point or coordinate.
        point2 : tuple, list, or float
            The second point or coordinate.

        Returns
        -------
        distance : float
            The Euclidean distance between the two points.
        """
        if isinstance(point1, (tuple, list)) and isinstance(point2, (tuple, list)):
            # Simple Euclidean distance for 2D points
            return np.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)
        else:
            return np.sqrt((point1 ** 2 + point2 ** 2))

    def update_table_widget(self, update=False):
        """Update the profile points table widget.

        Refreshes the table widget to display the current profile points.

        Parameters
        ----------
        update : bool, optional
            Indicates whether to perform an update, default is False.

        Returns
        -------
        None
        """
        if self.main_window.sample_id in self.profiles:
            if self.profile_name in self.profiles[self.main_window.sample_id]:  # if profiles for that sample exist
                profile_points = self.profiles[self.main_window.sample_id][self.profile_name].points
                self.main_window.tableWidgetProfilePoints.setRowCount(0)  # Clear existing rows
                point_number = 0
                first_data_point = list(profile_points.values())[0]
                for data_point in first_data_point:
                    x, y, _ = data_point  # Assuming data_point structure
                    row_position = self.main_window.tableWidgetProfilePoints.rowCount()
                    self.main_window.tableWidgetProfilePoints.insertRow(row_position)

                    # Fill in the data
                    self.main_window.tableWidgetProfilePoints.setItem(row_position, 0, QTableWidgetItem(str(point_number)))
                    self.main_window.tableWidgetProfilePoints.setItem(row_position, 1, QTableWidgetItem(str(round(x))))
                    self.main_window.tableWidgetProfilePoints.setItem(row_position, 2, QTableWidgetItem(str(round(y))))
                    self.main_window.tableWidgetProfilePoints.setRowHeight(row_position, 20)
                    point_number += 1

                # Enable or disable buttons based on the presence of points
                self.toggle_buttons(self.main_window.tableWidgetProfilePoints.rowCount() > 0)

    def toggle_buttons(self, enable):
        """Enable or disable profile point editing buttons.

        Enables or disables buttons based on the presence of profile points.

        Parameters
        ----------
        enable : bool
            Whether to enable or disable the buttons.

        Returns
        -------
        None
        """
        self.main_window.toolButtonPointUp.setEnabled(enable)
        self.main_window.toolButtonPointDown.setEnabled(enable)
        self.main_window.toolButtonPointDelete.setEnabled(enable)

    def on_pick(self, event):
        """Handle pick events on the profile plot.

        Processes user interactions with profile points on the plot when in edit mode.

        Parameters
        ----------
        event : object
            The pick event object.

        Returns
        -------
        None
        """
        style = self.main_window.style

        if self.edit_mode_enabled and isinstance(event.artist, PathCollection):
            # The picked scatter plot
            picked_scatter = event.artist
            # Indices of the picked points, could be multiple if overlapping
            ind = event.ind[0]  # Let's handle the first picked point for simplicity
            profile_key = picked_scatter.get_gid()
            # Determine the color of the picked point
            facecolors = picked_scatter.get_facecolors().copy()
            original_color = colors.to_rgba(self.original_colors[profile_key])  # Assuming you have a way to map indices to original colors

            # Toggle selection state
            self.selected_points[profile_key][ind] = not self.selected_points[profile_key][ind]

            num_points = len(picked_scatter.get_offsets())
            # If initially, there's only one color for all points,
            # we might need to ensure the array is expanded to explicitly cover all points.
            if len(facecolors) == 1 and num_points > 1:
                facecolors = np.tile(facecolors, (num_points, 1))

            if not self.selected_points[profile_key][ind]:
                # If already grey (picked)
                # Set to original color
                facecolors[ind] = colors.to_rgba(original_color)
            else:
                # Set to grey
                facecolors[ind] = (0.75, 0.75, 0.75, 1)

            picked_scatter.set_facecolors(facecolors)
            # Update the scatter plot sizes
            picked_scatter.set_sizes(np.full(num_points, style.marker_size))
            self.fig.canvas.draw_idle()

    def toggle_edit_mode(self):
        """Toggle the profile editing mode.

        Enables or disables profile editing mode based on the state of the edit mode toggle.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        self.edit_mode_enabled = not self.edit_mode_enabled

    def toggle_point_visibility(self):
        """Toggle visibility of selected profile points.

        Hides or shows selected profile points on the plot without removing them from the data.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        for profile_key in self.selected_points.keys():
            # Retrieve the scatter object using its profile key
            scatter, barlinecol = self.get_scatter_errorbar_by_gid(profile_key)
            if scatter is None:
                continue

            facecolors = scatter.get_facecolors().copy()
            num_points = len(scatter.get_offsets())

            # If initially, there's only one color for all points, expand the colors array
            if len(facecolors) == 1 and num_points > 1:
                facecolors = np.tile(facecolors, (num_points, 1))

            # Get the current array of colors (RGBA) for the LineCollection
            line_colors = barlinecol.get_colors().copy()

            # Ensure the color array is not a single color by expanding it if necessary
            if len(line_colors) == 1 and len(barlinecol.get_segments()) > 1:
                line_colors = np.tile(line_colors, (num_points, 1))

            # Iterate through each point to adjust visibility based on selection state
            for idx, selected in enumerate(self.selected_points[profile_key]):
                if selected:
                    if facecolors[idx][-1] > 0:
                        # Toggle visibility by setting alpha to 0 (invisible) or back to its original value
                        new_alpha = 0.0
                    else:
                        new_alpha = 1.0  # Assume original alpha was 1.0
                    line_colors[idx][-1] = new_alpha  # Set alpha to 0 for the line at index idx
                    facecolors[idx][-1] = new_alpha  # Hide/unhide scatter
            barlinecol.set_colors(line_colors)
            scatter.set_facecolors(facecolors)
        self.fig.canvas.draw_idle()

    def get_scatter_errorbar_by_gid(self, gid):
        """Retrieve scatter and errorbar objects by group ID.

        Finds and returns the scatter and errorbar plot items corresponding to a given group ID.

        Parameters
        ----------
        gid : str
            The group ID of the scatter plot.

        Returns
        -------
        tuple
            A tuple containing the scatter and errorbar plot items, or None if not found.
        """
        # return the correct scatter for corresponding key
        for (scatter, errorbars) in self.all_errorbars:
            if scatter.get_gid() == gid:
                return (scatter, errorbars)
        return None

    def add_field_to_listview(self, field=None, update=True):
        """Add selected fields to the profile list view.

        Opens a dialog to select fields from available data fields and adds them to the list view.
        """
        # Get available fields (assuming you have a method to retrieve them)
        if not field:
            field = self.main_window.comboBoxProfileField.currentText()
        if not field:
            QMessageBox.warning(self.main_window, 'No Fields', 'There are no available fields to add.')
            return

        else:
            # Add selected field(s) to the list view
            model = self.main_window.listViewProfile.model()
            if not model:
                model = QStandardItemModel()
                self.main_window.listViewProfile.setModel(model)
            existing_fields = [model.item(i).text() for i in range(model.rowCount())]

            if field not in existing_fields:
                model.appendRow(QStandardItem(field))
                
                if update:# Update the plot
                    self.plot_profiles()
            else:
                return

    def remove_field_from_listview(self):
        """Remove selected fields from the profile list view.

        Removes the selected field(s) from the list view.
        """
        # Get selected indices
        selection_model = self.main_window.listViewProfile.selectionModel()
        indexes = selection_model.selectedIndexes()

        if not indexes:
            QMessageBox.warning(self.main_window, 'No Selection', 'Please select a field to remove.')
            return

        # Remove selected items
        model = self.main_window.listViewProfile.model()
        for index in sorted(indexes, reverse=True):
            model.removeRow(index.row())

        # Update the plot
        self.plot_profiles()