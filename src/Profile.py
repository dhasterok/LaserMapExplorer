import os, pickle
from PyQt5 import QtCore
from PyQt5.QtWidgets import ( QMessageBox, QInputDialog, QWidget, QTableWidgetItem, QVBoxLayout )
from pyqtgraph import ( ScatterPlotItem )
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.colors as colors
from matplotlib.collections import PathCollection
import numpy as np

# Profiles
# -------------------------------
class Profile:
    def __init__(self,name,sort,radius,thresh,int_dist, point_error):
        self.name = name  
        self.points = {}
        self.i_points = {}
        self.sort = sort
        self.radius = radius
        self.y_axis_thresh = thresh
        self.int_dist = int_dist
        self.point_error = point_error


class Profiling:
    def __init__(self,main_window):
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
        #add sample id to dictionary
        for sample_id in self.main_window.sample_ids:
            if sample_id not in self.profiles:
                self.profiles[sample_id] = {}
        

    # def save_profiles(self,project_dir, sample_id):
    #     if sample_id in self.profiles:
    #         for profile_name, profile in self.profiles[sample_id].items():
    #             file_name =  os.path.join(project_dir,sample_id,f'{profile_name}.prfl')
    #             with open(file_name, 'wb') as file:
    #                 pickle.dump(profile, file)
    #         print("Profile saved successfully.")



    def save_profiles(self, project_dir, sample_id):
        if sample_id in self.profiles:
            for profile_name, profile in self.profiles[sample_id].items():
                file_name = os.path.join(project_dir, sample_id, f'{profile_name}.prfl')
                serializable_profile = self.transform_profile_for_pickling(profile)
                with open(file_name, 'wb') as file:
                    pickle.dump(serializable_profile, file)
            print("Profile saved successfully.")

    def load_profiles(self, project_dir, sample_id):
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
        for (k, v), points in profile.points.items():
            serializable_points = []
            for point in points:
                x, y, circ_val, scatter, interpolate = point
                scatter_state = self.extract_scatter_plot_state(scatter)
                serializable_points.append((x, y, circ_val, scatter_state, interpolate))
            serializable_profile['points'][(k, v)] = serializable_points
        for (k, v), i_points in profile.i_points.items():
            serializable_i_points = []
            for point in i_points:
                x, y, circ_val, scatter, interpolate = point
                scatter_state = self.extract_scatter_plot_state(scatter)
                serializable_i_points.append((x, y, circ_val, scatter_state, interpolate))
            serializable_profile['i_points'][(k, v)] = serializable_i_points
        return serializable_profile

    def extract_scatter_plot_state(self, scatter):
        data = scatter.getData()
        symbol = scatter.opts['symbol']
        size = scatter.opts['size']
        z_value = scatter.zValue()
        return {'data': data, 'symbol': symbol, 'size': size, 'z_value': z_value}

    def recreate_scatter_plot(self, state):
        scatter = ScatterPlotItem(state['data'][0], state['data'][1], symbol=state['symbol'], size=state['size'])
        scatter.setZValue(state['z_value'])
        return scatter



    def reconstruct_profile(self, serializable_profile):
        profile = Profile(
            serializable_profile['name'],
            serializable_profile['sort'],
            serializable_profile['radius'],
            serializable_profile['y_axis_thresh'],
            serializable_profile['int_dist'],
            serializable_profile['point_error']
        )
        for (k, v), points in serializable_profile['points'].items():
            reconstructed_points = []
            for point in points:
                x, y, circ_val, scatter_state, interpolate = point
                scatter = self.recreate_scatter_plot(scatter_state)
                reconstructed_points.append((x, y, circ_val, scatter, interpolate))
            profile.points[(k, v)] = reconstructed_points
        for (k, v), i_points in serializable_profile['i_points'].items():
            reconstructed_i_points = []
            for point in i_points:
                x, y, circ_val, scatter_state, interpolate = point
                scatter = self.recreate_scatter_plot(scatter_state)
                reconstructed_i_points.append((x, y, circ_val, scatter, interpolate))
            profile.i_points[(k, v)] = reconstructed_i_points
        return profile
    
    def populate_combobox(self):
        self.main_window.comboBoxProfileList.clear()
        self.main_window.comboBoxProfileList.addItem('Create New Profile')
        for profile_name in self.profiles[self.main_window.sample_id].keys():
            self.main_window.comboBoxProfileList.addItem(profile_name)
        

    def load_profiles_from_directory(self, project_dir, sample_id):
        directory = os.path.join(project_dir,sample_id)
        for file_name in os.listdir(directory):
            if file_name.endswith(".prfl"):
                file_path = os.path.join(directory, file_name)
                with open(file_path, 'rb') as file:
                    profile_name = os.path.basename(file_path).split('.')[0]
                    self.profiles[sample_id][profile_name] = pickle.load(file)

        self.populate_combobox()
        print("All profiles loaded successfully.")

    def on_profile_selected(self, profile_name):
        if profile_name == 'Create New Profile':
            new_profile_name, ok = QInputDialog.getText(self.main_window, 'New Profile', 'Enter new profile name:')
            if ok and new_profile_name:
                if new_profile_name in self.profiles[self.main_window.sample_id]:
                    QMessageBox.warning(self.main_window, 'Error', 'Profile name already exists!')
                else:
                    self.clear_profiles()
                    sort = self.main_window.comboBoxProfileSort.currentText()
                    radius = self.main_window.lineEditPointRadius.text() 
                    thresh = self.main_window.lineEditPointRadius.text()
                    int_dist = self.main_window.lineEditIntDist.text()
                    point_error = self.main_window.comboBoxPointType.currentText()

                    # create new profile instance
                    self.profiles[self.main_window.sample_id][new_profile_name] = Profile(new_profile_name,sort,radius,thresh,int_dist, point_error)
                    # self.i_profiles[self.main_window.sample_id][new_profile_name] = {}
                    self.main_window.comboBoxProfileList.addItem(new_profile_name)
                    self.main_window.comboBoxProfileList.setCurrentText(new_profile_name)
                    self.profile_name = new_profile_name
            else:
                self.main_window.comboBoxProfileList.setCurrentIndex(0)  # Reset to 'Create New Profile'
        else:
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

    def cart_to_dist(self,pixel:int,direction = 'y') -> float:
        if direction == 'x':
            return pixel*self.main_window.data[self.main_window.sample_id].array_size[1]/self.main_window.data[self.main_window.sample_id].x_range
        else:
            return pixel*self.main_window.data[self.main_window.sample_id].array_size[0]/self.main_window.data[self.main_window.sample_id].y_range
    
    def dist_to_cart(self,dist:float, direction = 'y')-> int:
        if direction == 'x':
            return round(dist*self.main_window.data[self.main_window.sample_id].dx)
        else:
            return round(dist*self.main_window.data[self.main_window.sample_id].dy)

    def plot_profile_scatter(self, event, array,k,v, plot, x, y, x_i, y_i):
        #k is key (name of Analyte)
        #create profile dict particular sample if it doesnt exisist
        # if self.main_window.sample_id not in self.profiles:
        #     self.profiles[self.main_window.sample_id] = {}
        #     self.i_profiles[self.main_window.sample_id] = {}
        
        self.array_x = array.shape[1] #no of colmns
        self.array_y = array.shape[0] #no of rows
        interpolate = False
        radius= int(self.main_window.lineEditPointRadius.text())

        profile = self.profiles[self.main_window.sample_id][self.profile_name].points
        
        # turn off profile (need to suppress context menu on right click)
        if event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPlotProfile.isChecked():
            self.main_window.toolButtonPlotProfile.setChecked(False)
            self.main_window.toolButtonPointMove.setEnabled(True)
            return
        elif event.button() == QtCore.Qt.RightButton and self.main_window.toolButtonPointMove.isChecked():
            self.main_window.toolButtonPointMove.setChecked(False)
            self.point_selected = False
            return
        elif event.button() == QtCore.Qt.RightButton or event.button() == QtCore.Qt.MiddleButton:
            return



        elif event.button() == QtCore.Qt.LeftButton and not(self.main_window.toolButtonPlotProfile.isChecked()) and self.main_window.toolButtonPointMove.isChecked():

            # move point
            if self.point_selected:
                #remove selected point
                prev_scatter = profile[k,v][self.point_index][3]
                plot.removeItem(prev_scatter)


                # Create a scatter plot item at the clicked position
                scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                scatter.setZValue(1e9)
                plot.addItem(scatter)
                # Find all points within the specified radius
                circ_val = []
                circ_cord = []

                p_radius_y = self.dist_to_cart(radius, 'y') # pixel radius in pixels y direction
                p_radius_x = self.dist_to_cart(radius, 'x') # pixel radius in pixels x direction
                
                for i in range(max(0, y_i - p_radius_y), min(self.array_y, y_i + p_radius_y + 1)):
                    for j in range(max(0, x_i - p_radius_x), min(self.array_x , x_i + p_radius_x + 1)):
                        if self.calculate_distance(self.cart_to_dist(y_i - i)**2 , self.cart_to_dist(x_i - j)**2) <= radius:
                            value = array[i, j]
                            circ_cord.append([i, j])
                            circ_val.append( value)


                # for i in range(max(0, y_i - radius), min(self.array_y, y_i + radius + 1)):
                #     for j in range(max(0, x_i - radius), min(self.array_x , x_i + radius + 1)):
                #         if np.sqrt((x_i - j)**2 + (y_i - i)**2) <= radius:
                #             value = array[i, j]
                #             circ_cord.append([i, j])
                #             circ_val.append( value)

                #update self.point_index index of self.profiles[self.self.profile_name] with new point data
                if (k,v) in profile:

                    profile[k,v][self.point_index] = (x,y, circ_val,scatter, interpolate)


                if self.main_window.canvasWindow.currentIndex() == self.main_window.canvas_tab['mv']:
                    # Add the scatter item to all other plots and save points in profile
                    for (k,v), (_, p, array) in self.main_window.lasermaps.items():
                        circ_val = []
                        if p != plot and v==1 and self.array_x ==array.shape[1] and self.array_y ==array.shape[0] : #only add scatters to other lasermaps of same sample
                            # Create a scatter plot item at the clicked position
                            scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                            scatter.setZValue(1e9)
                            p.addItem(scatter)
                            for c in circ_cord:
                                value = array[c[0], c[1]]
                                circ_val.append( value)
                            if (k,v) in profile:
                                profile[k,v][self.point_index] = (x,y, circ_val,scatter, interpolate)

                #update plot and table widget
                self.main_window.plot_profiles()
                self.update_table_widget()
                if self.main_window.toolButtonProfileInterpolate.isChecked(): #reset interpolation if selected
                    self.clear_interpolation()
                    self.interpolate_points(interpolation_distance=int(self.main_window.lineEditIntDist.text()), radius= int(self.main_window.lineEditPointRadius.text()))
            else:
                # find nearest profile point
                mindist = 10**12
                for i, (x_p,y_p,_,_,interpolate) in enumerate(profile[k,v]):
                    dist = (x_p - x)**2 + (y_p - y)**2
                    if mindist > dist:
                        mindist = dist
                        self.point_index = i
                if not(round(mindist*self.array_x/self.main_window.data[self.main_window.sample_id].x_range) < 50):
                    self.point_selected = True


        elif event.button() == QtCore.Qt.LeftButton:  #plot profile
            #switch to profile tab
            self.main_window.tabWidget.setCurrentIndex(self.main_window.bottom_tab['profile'])

            # Create a scatter plot item at the clicked position
            scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
            scatter.setZValue(1e9)
            plot.addItem(scatter)
            # Find all points within the specified radius
            circ_val = []
            circ_cord = []
            p_radius_y = self.dist_to_cart(radius, 'y') # pixel radius in pixels y direction
            p_radius_x = self.dist_to_cart(radius, 'x') # pixel radius in pixels x direction
            
            for i in range(max(0, y_i - p_radius_y), min(self.array_y, y_i + p_radius_y + 1)):
                for j in range(max(0, x_i - p_radius_x), min(self.array_x , x_i + p_radius_x + 1)):
                    if self.calculate_distance(self.cart_to_dist(y_i - i) , self.cart_to_dist(x_i - j)) <= radius: # filter values that lies within radius
                        value = array[i, j]
                        circ_cord.append([i, j])
                        circ_val.append( value)

            #add values within circle of radius in profile
            if (k,v) in profile:
                profile[(k,v)].append((x,y,circ_val,scatter, interpolate))
            else:
                profile[(k,v)] = [(x,y, circ_val,scatter, interpolate)]


            if self.main_window.canvasWindow.currentIndex() == self.main_window.canvas_tab['mv']:
                # Add the scatter item to all other plots and save points in profile
                for (k,v), (_, p,  array) in self.main_window.lasermaps.items():
                    circ_val = []
                    if p != plot and v==1 and self.array_x ==array.shape[1] and self.array_y ==array.shape[0] : #only add scatters to other lasermaps of same sample
                        # Create a scatter plot item at the clicked position
                        scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                        scatter.setZValue(1e9)
                        p.addItem(scatter)
                        for c in circ_cord:
                            value = array[c[0], c[1]]
                            circ_val.append( value)
                        if (k,v) in profile:
                            profile[k,v].append((x,y,circ_val, interpolate))
                        else:
                            profile[k,v] = [(x,y, circ_val,scatter, interpolate)]

            self.plot_profiles()
            self.update_table_widget()
    
    def plot_existing_profile(self,plot):
        # clear exisiting plot
        self.clear_plot()
        if self.profile_name in self.profiles[self.main_window.sample_id]:
            profile = self.profiles[self.main_window.sample_id][self.profile_name].points        
            for (k,v) in profile:
                for x,y,_,_,_ in profile[k,v]:
                    # Create a scatter plot items
                    scatter = ScatterPlotItem([x], [y], symbol='+', size=10)
                    scatter.setZValue(1e9)
                    plot.addItem(scatter)

    def interpolate_points(self, interpolation_distance,radius):
        
        """
        Interpolate linear points between each pair of points in the profiles.
        """
        profile = self.profiles[self.main_window.sample_id][self.profile_name].points
        i_profile = self.profiles[self.main_window.sample_id][self.profile_name].i_points

        if self.main_window.toolButtonProfileInterpolate.isChecked():
            interpolate = True
            for (k,v), points in profile.items():
                for i in range(len(points) - 1):
                    start_point = points[i]
                    end_point = points[i + 1]
                    if i == 0:
                        i_profile[(k,v)] = [start_point]
                    else:
                        i_profile[(k,v)].append(start_point)

                    # Calculate the distance between start and end points
                    dist = self.calculate_distance(start_point, end_point)

                    # Determine the number of interpolations based on the distance
                    num_interpolations = max(int(dist / interpolation_distance), 0)

                    # Calculate the unit vector in the direction from start_point to end_point
                    dx = (end_point[0] - start_point[0]) / dist
                    dy = (end_point[1] - start_point[1]) / dist

                    # # Generate linearly spaced points between start_point and end_point
                    # for t in np.linspace(0, 1, num_interpolations + 2)[1:-1]:  # Exclude the endpoints
                    #     x = start_point[0] + t * (end_point[0] - start_point[0])
                    #     y = start_point[1] + t * (end_point[1] - start_point[1])

                    for t in range(0, num_interpolations+1):
                        x = start_point[0] + t * interpolation_distance * dx
                        y = start_point[1] + t * interpolation_distance * dy

                        x_i = self.dist_to_cart(x,'x') #index points
                        y_i = self.dist_to_cart(y,'y')

                        # Add the scatter item to all other plots and save points in profile
                        _, p, array = self.main_window.lasermaps[(k,v)]
                        if (v == self.main_window.canvasWindow.currentIndex()) and (self.array_x == array.shape[1]) and (self.array_y == array.shape[0]) : #only add scatters to other lasermaps of same sample
                            # Create a scatter plot item at the clicked position
                            scatter = ScatterPlotItem([x], [y], symbol='+', size=5)
                            scatter.setZValue(1e9)
                            p.addItem(scatter)
                            # Find all points within the specified radius
                            circ_val = []

                            p_radius_y = self.dist_to_cart(radius, 'y') # pixel radius in pixels y direction
                            p_radius_x = self.dist_to_cart(radius, 'x') # pixel radius in pixels x direction
                            
                            for i in range(max(0, y_i - p_radius_y), min(self.array_y, y_i + p_radius_y + 1)):
                                for j in range(max(0, x_i - p_radius_x), min(self.array_x , x_i + p_radius_x + 1)):
                                    if self.calculate_distance(self.cart_to_dist(y_i - i)**2 , self.cart_to_dist(x_i - j)**2) <= radius:
                                        value = array[i, j]
                                        circ_val.append(value)

                            if (k,v) in i_profile:
                                i_profile[(k,v)].append((x,y,circ_val, scatter, interpolate))

                    i_profile[(k,v)].append(end_point)
            # After interpolation, update the plot and table widget
            self.plot_profiles(interpolate= interpolate)
        else:
            self.clear_interpolation()
            #plot original profile
            self.plot_profiles(interpolate= False)
        # self.update_table_widget(interpolate= True)

    def clear_plot(self):
        """Clear all existing profiles from the plot."""
        if self.main_window.sample_id in self.profiles:
            for profile_name, profile in self.profiles[self.main_window.sample_id].items():
                # Clear points from the plot
                for (k, v), points in profile.points.items():
                    for _, _, _, scatter, _ in points:
                        self.main_window.plot.removeItem(scatter)

                # Clear interpolated points from the plot (if applicable)
                for (k, v), i_points in profile.i_points.items():
                    for _, _, _, scatter, _ in i_points:
                        self.main_window.plot.removeItem(scatter)

    def clear_interpolation(self):
            i_profile = self.profiles[self.main_window.sample_id][self.profile_name].i_points
            # remove interpolation
            if len(i_profile)>0:
                for (k,v), profile in i_profile.items():
                    for point in profile:
                        scatter_item = point[3]  # Access the scatter plot item
                        interpolate =point[4]
                        if interpolate:
                            _, plot, _ = self.main_window.lasermaps[(k,v)]
                            plot.removeItem(scatter_item)

    def plot_profiles(self, interpolate=False, sort_axis=None):
        profile = self.profiles[self.main_window.sample_id][self.profile_name].points
        i_profile = self.profiles[self.main_window.sample_id][self.profile_name].i_points
        def process_points( points, sort_axis):
            # Sort the points based on the user-specified axis
            if sort_axis == 'x':
                points.sort(key=lambda p: p[0])  # Sort by x-coordinate of median point
            elif sort_axis == 'y':
                points.sort(key=lambda p: p[1])  # Sort by y-coordinate of median point

            median_values = []
            lower_quantiles = []
            upper_quantiles = []
            mean_values = []
            standard_errors = []
            distances = [0]

            for i, group in enumerate(points):

                values = [p for p in group[2]] # Extract values
                median_values.append(np.median(values))
                lower_quantiles.append(np.quantile(values, 0.25))
                upper_quantiles.append(np.quantile(values, 0.75))
                mean_values.append(np.mean(values))
                standard_errors.append(np.std(values, ddof=1) / np.sqrt(len(values)))
                if i>0:
                    dist = self.calculate_distance(points[i - 1], points[i])
                    distances.append(distances[-1] + dist)

            return distances, median_values, lower_quantiles, upper_quantiles,mean_values,standard_errors

        def group_profiles_by_range(sort_axis, range_threshold,interpolate,point_type):
            if not interpolate:
                profiles = profile
            else:
                profiles = i_profile
            # Group profiles based on range similarity
            profile_groups = {}
            keys = []
            if self.main_window.canvasWindow.currentIndex() == self.main_window.canvas_tab['mv']: #multiview
                keys= [(k,v) for (k,v) in profiles.keys() if v== 1]



            else: #singleview
                keys = [(k,v) for (k,v) in profiles.keys() if v== 0]

            colors = [cmap(i / len(keys)) for i in range(len(keys))]

            for (k,v) in keys:
                points =  profiles[(k,v)]
                distances, medians, lowers, uppers, mean,s_error  = process_points(points, sort_axis)
                if point_type == 'mean':
                    range_value = np.nanmax(mean) - np.nanmin(mean)

                    similar_group_found = False

                    for group_key, _ in profile_groups.items():
                        if abs(range_value - group_key) <= range_threshold:
                            profile_groups[group_key].append((k, distances, mean, s_error, np.nanmin(mean)))
                            similar_group_found = True
                            break
                    if not similar_group_found:
                        profile_groups[range_value] = [(k, distances, mean, s_error, np.nanmin(mean, np.nanmax(mean)))]
                else:

                    range_value = np.nanmax(medians)- np.nanmin(medians)

                    similar_group_found = False

                    for group_key, _ in profile_groups.items():
                        if abs(range_value - group_key) <= range_threshold:
                            profile_groups[group_key].append((k, distances, medians, lowers, uppers, np.nanmin(medians), np.nanmax(medians)))
                            similar_group_found = True
                            break
                    if not similar_group_found:
                        profile_groups[range_value] = [(k, distances, medians, lowers, uppers, np.nanmin(medians), np.nanmax(medians))]

            return profile_groups, colors


        if not interpolate:
            profiles = profile
        else:
            profiles = i_profile

        style = self.main_window.styles['profile']

        if len(list(profiles.values())[0])>0: #if profile has values
            self.main_window.tabWidget.setCurrentIndex(self.main_window.bottom_tab['profile']) #show profile plot tab
            sort_axis=self.main_window.comboBoxProfileSort.currentText()
            range_threshold=int(self.main_window.lineEditYThresh.text())
            # Clear existing plot
            layout = self.main_window.widgetProfilePlot.layout()
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Get the colormap specified by the user
            cmap = self.main_window.get_colormap()
            # Determine point type from the pushButtonProfileType text
            if self.main_window.comboBoxPointType.currentText() == 'median + IQR':
                point_type = 'median'
            else:
                point_type ='mean'
            # Group profiles and set up the figure
            profile_groups,colors = group_profiles_by_range(sort_axis, range_threshold, interpolate, point_type)
            # Initialize the figure
            self.fig = Figure()
            #Connect the pick_event signal to a handler that will process the picked points.
            self.fig.canvas.mpl_connect('pick_event', self.on_pick)
            num_groups = len(profile_groups)
            num_subplots = (num_groups + 1) // 2  # Two groups per subplot, rounding up
            subplot_idx = 1
            #reset existing error_bar list
            self.all_errorbars = []
            original_range = None
            original_min = None
            twinx_min = None
            original_max = None
            twinx_max = None
            # Adjust subplot spacing
            # fig.subplots_adjust(hspace=0.1)  # Adjust vertical spacing
            ax = self.fig.add_subplot(num_subplots, 1, subplot_idx)

            for idx, (range_value, group_profiles) in enumerate(profile_groups.items()):
                scale_factor = 0
                if idx > 1 and idx % 2 == 0:  # Create a new subplot for every 2 groups after the first two
                    subplot_idx += 1
                    ax = self.fig.add_subplot(num_subplots, 1, subplot_idx)
                    original_range = range_value

                elif idx % 2 == 1:  # Create a new axis for every second group

                    twinx_range = range_value
                    scale_factor = original_range/twinx_range
                    ax2 = ax.twinx()
                    ax.set_zorder(ax2.get_zorder()+1)
                    # ax = ax2
                else:
                    original_range = range_value
                el_labels = []
                # Plot each profile in the group
                if point_type == 'mean':
                    for g_idx,(profile_key, distances, means,s_errors, min_val, max_val) in enumerate(group_profiles):
                        if scale_factor>0: #needs scaling
                            if g_idx == 0: #the min value of the group is stored in first row of each group_profiles
                                twinx_min = min_val
                                twinx_min = max_val
                                # Scale values and errors
                                scaled_values = [(value - twinx_min) * scale_factor + original_min for value in means]
                                scaled_errors = [error * scale_factor for error in s_errors]

                            # Plot markers with ax.scatter
                            scatter = ax.scatter(distances, scaled_values,
                                                  color=colors[idx+g_idx],
                                                  s=style['Markers']['Size'],
                                                  marker=self.main_window.markerdict[style['Markers']['Symbol']],
                                                  edgecolors='none',
                                                  picker=5,
                                                  label=f'{profile_key}',
                                                  zorder=2*g_idx+1)

                            #plot errorbars with no marker
                            _, _, barlinecols = ax.errorbar(distances, scaled_errors,
                                                            yerr=scaled_errors,
                                                            fmt='none',
                                                            color=colors[idx+g_idx],
                                                            ecolor=style['Colors']['Color'],
                                                            elinewidth=style['Lines']['LineWidth'],
                                                            capsize=0,
                                                            zorder=2*g_idx)

                            # Assuming you have the scaling factors and original data range
                            scale_factor = (original_max - original_min) / (twinx_max - twinx_min)

                            # Determine positions for custom ticks on ax2
                            # Choose representative values from the original scale you want as ticks on ax2
                            original_tick_values = [twinx_min, (twinx_max + twinx_min) / 2, twinx_max]

                            # Calculate the scaled positions of these ticks on ax
                            scaled_tick_positions = [(value - twinx_min) * scale_factor + original_min for value in original_tick_values]

                        else:
                            if g_idx == 0:
                                original_min = min_val
                                original_max = max_val
                            # Plot markers with ax.scatter
                            scatter = ax.scatter(distances, means,
                                                color=colors[idx+g_idx],
                                                s=style['Markers']['Size'],
                                                marker=self.main_window.markerdict[style['Markers']['Symbol']],
                                                edgecolors='none',
                                                picker=5,
                                                label=f'{profile_key[:-1]}',
                                                zorder = 2*g_idx+1)

                            #plot errorbars with no marker
                            _, _, barlinecols = ax.errorbar(distances, means,
                                                            yerr=s_errors,
                                                            fmt='none',
                                                            color=colors[idx+g_idx],
                                                            ecolor=style['Colors']['Color'],
                                                            elinewidth=style['Lines']['LineWidth'],
                                                            capsize=0, zorder=2*g_idx)

                        self.all_errorbars.append((scatter,barlinecols[0]))
                        self.original_colors[profile_key] = colors[idx+g_idx]  # Assuming colors is accessible
                        self.selected_points[profile_key] = [False] * len(means)
                        el_labels.append(profile_key.split('_')[-1]) #get element name
                        y_axis_text = ','.join(el_labels)
                        if scale_factor>0:
                            ax2.set_ylabel(f'{y_axis_text}')
                            ax2.set_yticks(scaled_tick_positions)
                            ax2.set_yticklabels([f"{value:.2f}" for value in original_tick_values])
                        else:
                            ax.set_ylabel(f'{y_axis_text}')
                        # Append the new Line2D objects to the list
                        # self.markers.extend(marker)
                else:
                    for g_idx,(profile_key, distances, medians, lowers, uppers, min_val, max_val) in enumerate(group_profiles):
                        #asymmetric error bars
                        errors = [[median - lower for median, lower in zip(medians, lowers)],
                            [upper - median for upper, median in zip(uppers, medians)]]
                        if scale_factor>0: #needs scaling
                            if g_idx == 0: #the min value of the group is stored in first row of each group_profiles
                                twinx_min = min_val
                                twinx_max = max_val


                            # Scale values and errors
                            scaled_values = [(value - twinx_min) * scale_factor + original_min for value in medians]
                            # Assuming errors is structured as [lower_errors, upper_errors]
                            scaled_lower_errors = [error * scale_factor for error in errors[0]]
                            scaled_upper_errors = [error * scale_factor for error in errors[1]]

                            # Now, scaled_errors is ready to be used in plotting functions
                            scaled_errors = [scaled_lower_errors, scaled_upper_errors]
                            # Plot markers with ax.scatter
                            scatter = ax.scatter(distances, scaled_values,
                                                color=colors[idx+g_idx],
                                                s=style['Markers']['Size'],
                                                marker=self.main_window.markerdict[style['Markers']['Symbol']],
                                                edgecolors='none',
                                                picker=5,
                                                gid=profile_key,
                                                label=f'{profile_key}',
                                                zorder=2*g_idx+1)
                            # ax2.scatter(distances, medians, color=colors[idx+g_idx],s=self.scatter_size, picker=5, gid=profile_key, edgecolors = 'none', label=f'{profile_key[:-1]}')
                            #plot errorbars with no marker
                            _, _, barlinecols = ax.errorbar(distances, scaled_values,
                                                            yerr=scaled_errors,
                                                            fmt='none',
                                                            color=colors[idx+g_idx],
                                                            ecolor=style['Colors']['Color'],
                                                            elinewidth=style['Lines']['LineWidth'],
                                                            capsize=0,
                                                            zorder=2*g_idx)


                            # Assuming you have the scaling factors and original data range
                            scale_factor = (original_max - original_min) / (twinx_max - twinx_min)

                            # Determine positions for custom ticks on ax2
                            # Choose representative values from the original scale you want as ticks on ax2
                            original_tick_values = [twinx_min, (twinx_max + twinx_min) / 2, twinx_max]

                            # Calculate the scaled positions of these ticks on ax
                            scaled_tick_positions = [(value - twinx_min) * scale_factor + original_min for value in original_tick_values]
                        else:
                            if g_idx == 0: #the min value of the group is stored in first row of each group_profiles
                                original_min = min_val
                                original_max = max_val

                            # Plot markers with ax.scatter
                            scatter = ax.scatter(distances, medians,
                                                 color=colors[idx+g_idx],
                                                 s=style['Markers']['Size'],
                                                 marker=self.main_window.markerdict[style['Markers']['Symbol']],
                                                 edgecolors='none',
                                                 picker=5,
                                                 gid=profile_key,
                                                 label=f'{profile_key}',
                                                 zorder=2*g_idx+1)

                            #plot errorbars with no marker
                            _, _, barlinecols = ax.errorbar(distances, medians,
                                                            yerr=errors,
                                                            fmt='none',
                                                            color=colors[idx+g_idx],
                                                            ecolor=style['Colors']['Color'],
                                                            elinewidth=style['Lines']['LineWidth'],
                                                            capsize=0,
                                                            zorder=2*g_idx)

                        self.all_errorbars.append((scatter,barlinecols[0]))
                        self.original_colors[profile_key] = colors[idx+g_idx]  # Assuming colors is accessible
                        self.selected_points[profile_key] = [False] * len(medians)
                        el_labels.append(profile_key[:-1].split('_')[-1]) #get element name
                        y_axis_text = ','.join(el_labels)
                        if scale_factor>0:
                            ax2.set_ylabel(f'{y_axis_text}')
                            ax2.set_yticks(scaled_tick_positions)
                            ax2.set_yticklabels([f"{value:.2f}" for value in original_tick_values])
                        else:
                            ax.set_ylabel(f'{y_axis_text}')

            # Set labels only for the bottom subplot
                if subplot_idx == num_subplots:
                    ax.set_xlabel('Distance')
                else:
                    # Remove the x-axis for the first subplot
                    ax.xaxis.set_visible(False)
                # ax.set_ylabel(f'Axis {idx}')
                # Adjust legend position based on the subplot index
                legend_loc = 'upper left' if idx % 2 == 0 else 'upper right'
                # ax.legend(title=f'Axis {idx}', loc=legend_loc, bbox_to_anchor=(1.05, 1))

            # self.fig.tight_layout(pad=3, h_pad=None, w_pad=None, rect=None)
            self.fig.tight_layout(pad=3,w_pad=0, h_pad=0)
            self.fig.subplots_adjust(wspace=0, hspace=0)
            self.fig.legend(loc='outside right upper')

            # Embed the matplotlib plot in a QWidget
            canvas = FigureCanvas(self.fig)
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.addWidget(canvas)
            widget.setLayout(layout)

            # Add the new plot widget to the layout
            self.main_window.widgetProfilePlot.layout().addWidget(widget)
            widget.show()
        else:
            self.clear_profiles()

    def clear_profiles(self):
        if self.main_window.sample_id in self.profiles: #if profiles have been initiated for the samples
            if self.profile_name in self.profiles[self.main_window.sample_id]: #if profiles for that sample if exists
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
        # Simple Euclidean distance
        if isinstance(point1, (tuple, list)) and isinstance(point2, (tuple, list)):
        # Simple Euclidean distance for 2D points
            return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
        else:
            return np.sqrt((point1**2 + point2**2))
        

    def  update_table_widget(self, update = False):
        if self.main_window.sample_id in self.profiles:
            if self.profile_name in self.profiles[self.main_window.sample_id]: #if profiles for that sample if exists
                profile = self.profiles[self.main_window.sample_id][self.profile_name].points
                self.main_window.tableWidgetProfilePoints.setRowCount(0)  # Clear existing rows
                point_number = 0
                first_data_point = list(profile.values())[0]
                for data_point in first_data_point:
                    x, y, _,_,_ = data_point  # Assuming data_point structure
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
        self.main_window.toolButtonPointUp.setEnabled(enable)
        self.main_window.toolButtonPointDown.setEnabled(enable)
        self.main_window.toolButtonPointDelete.setEnabled(enable)

    def on_pick(self, event):

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
            picked_scatter.set_sizes(np.full(num_points, self.main_window.styles['profile']['Markers']['Size']))
            self.fig.canvas.draw_idle()

    def toggle_edit_mode(self):
        """Toggles profile editing mode.

        State determined by toolButtonProfileEditMode checked.
        """
        self.edit_mode_enabled = not self.edit_mode_enabled

    def toggle_point_visibility(self):
        """Toggles visibility of individual profile points

        Toggled points are still retained in the data, but an associated boolean field indicates
        whether they should be displayed or not.
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
                        new_alpha= 1.0  # Assume original alpha was 1.0
                    line_colors[idx][-1] = new_alpha  # Set alpha to 0 for the line at index idx
                    facecolors[idx][-1] = new_alpha #hid/unhide scatter
            barlinecol.set_colors(line_colors)
            scatter.set_facecolors(facecolors)
        self.fig.canvas.draw_idle()

    def get_scatter_errorbar_by_gid(self, gid):
        #return the correct scatter for corresponding key
        for (scatter, errorbars) in self.all_errorbars:
            if scatter.get_gid() == gid:
                return (scatter, errorbars)
        return None
