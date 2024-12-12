import os, pickle
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QIcon, QFont, QIntValidator
from PyQt5.QtWidgets import ( 
        QMessageBox, QInputDialog, QWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QGroupBox,
        QToolButton, QComboBox, QSpinBox, QSpacerItem, QSizePolicy, QFormLayout, QListView, QToolBar,
        QAction, QLabel, QHeaderView, QTableWidget, QScrollArea
    )
from src.common.CustomWidgets import CustomDockWidget, CustomLineEdit, CustomComboBox
from src.app.UIControl import UIFieldLogic
from pyqtgraph import ( ScatterPlotItem )
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.colors as colors
from matplotlib.collections import PathCollection
import numpy as np

class ProfileDock(CustomDockWidget, UIFieldLogic):
    def __init__(self, parent=None):

        super().__init__(parent)
        self.profiling = Profiling(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        container = QWidget()
        container_layout = QVBoxLayout()

        # create toolbar for editing profile plots
        toolbar = QToolBar("Profile Toolbar", self)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out

        # open profiles
        self.actionOpenProfile = QAction()
        self.actionOpenProfile.setIcon(QIcon(":resources/icons/icon-open-file-64.svg"))
        self.actionOpenProfile.setToolTip("Open profiles")

        # profile list
        self.profile_label = QLabel()
        self.profile_label.setText("Profile:")
        self.profile_combobox = QComboBox()
        self.profile_combobox.setMinimumWidth(200)
        self.profile_combobox.setToolTip("Select a profile to view/edit")
        self.profile_combobox.setPlaceholderText("Add or load a profile...")

        # delete profiles
        self.actionDeleteProfile = QAction()
        self.actionDeleteProfile.setIcon(QIcon(":resources/icons/icon-delete-64.svg"))
        self.actionDeleteProfile.setToolTip("Delete profile")

        # create new profile and set control points
        self.actionControlPoints = QAction()
        self.actionControlPoints.setIcon(QIcon(":resources/icons/icon-profile-64.svg"))
        self.actionControlPoints.setToolTip("Create new profile and set control points")
        self.actionControlPoints.setCheckable(True)
        self.actionControlPoints.setChecked(False)

        # Interpolate profile
        self.actionInterpolate = QAction()
        self.actionInterpolate.setIcon(QIcon(":resources/icons/icon-interpolate-64.svg"))
        self.actionInterpolate.setToolTip("Interpolate between control points")
        self.actionInterpolate.setCheckable(True)
        self.actionInterpolate.setChecked(False)
        self.actionInterpolate.setEnabled(False)

        # Move control point
        self.actionMovePoint = QAction()
        self.actionMovePoint.setIcon(QIcon(":resources/icons/icon-move-point-64.svg"))
        self.actionMovePoint.setToolTip("Move a control point")
        self.actionMovePoint.setCheckable(True)
        self.actionMovePoint.setChecked(False)
        self.actionMovePoint.setEnabled(False)

        # Add control point
        self.actionAddPoint = QAction()
        self.actionAddPoint.setIcon(QIcon(":resources/icons/icon-add-point-64.svg"))
        self.actionAddPoint.setToolTip("Add a control point")
        self.actionAddPoint.setCheckable(True)
        self.actionAddPoint.setChecked(False)
        self.actionAddPoint.setEnabled(False)

        # Remove control point
        self.actionRemovePoint = QAction()
        self.actionRemovePoint.setIcon(QIcon(":resources/icons/icon-remove-point-64.svg"))
        self.actionRemovePoint.setToolTip("Remove a control point")
        self.actionRemovePoint.setCheckable(True)
        self.actionRemovePoint.setChecked(False)
        self.actionRemovePoint.setEnabled(False)

        # edit profile button
        self.actionEdit = QAction()
        self.actionEdit.setIcon(QIcon(":resources/icons/icon-edit-64.svg"))
        self.actionEdit.setToolTip("Toggle profile editing mode")
        self.actionEdit.setCheckable(True)
        self.actionEdit.setChecked(False)

        # point toggle button
        self.actionTogglePoint = QAction()
        self.actionTogglePoint.setIcon(QIcon(":resources/icons/icon-show-hide-64.svg"))
        self.actionTogglePoint.setToolTip("Toggle point visibility")
        self.actionTogglePoint.setCheckable(True)
        self.actionTogglePoint.setChecked(False)
        self.actionTogglePoint.setEnabled(False)

        # export profile figure button
        self.actionExport = QAction()
        self.actionExport.setIcon(QIcon(":resources/icons/icon-save-file-64.svg"))
        self.actionExport.setToolTip("Export profile image or data")

        toolbar.addAction(self.actionOpenProfile)
        toolbar.addWidget(self.profile_label)
        toolbar.addWidget(self.profile_combobox)
        toolbar.addAction(self.actionDeleteProfile)
        toolbar.addSeparator()
        toolbar.addAction(self.actionControlPoints)
        toolbar.addAction(self.actionInterpolate)
        toolbar.addAction(self.actionMovePoint)
        toolbar.addAction(self.actionAddPoint)
        toolbar.addAction(self.actionRemovePoint)
        toolbar.addSeparator()
        toolbar.addAction(self.actionEdit)
        toolbar.addAction(self.actionTogglePoint)
        toolbar.addAction(self.actionExport)

        container_layout.addWidget(toolbar)

        dock_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        dock_layout.addLayout(left_layout)

        # create widget for placing profile plots
        self.widgetProfilePlot = QWidget()
        self.widgetProfilePlot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        dock_layout.addWidget(self.widgetProfilePlot)
        # create profile controls

        profile_tools = QGroupBox()
        profile_tools.setTitle("Profile Options")
        profile_tools.setMinimumWidth(180)
        profile_tools.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        profile_tools.setContentsMargins(3,3,3,3)
        profile_tools_layout = QFormLayout()
        profile_group_layout = QVBoxLayout()
        profile_group_layout.addLayout(profile_tools_layout)
        profile_group_layout.setContentsMargins(3,3,3,3)
        profile_tools.setLayout(profile_group_layout)

        self.point_sort_combobox = QComboBox()
        self.point_sort_combobox.addItems(['no','x','y'])
        self.point_sort_combobox.setToolTip("Sort the control points")
        self.radius_line_edit = CustomLineEdit()
        self.radius_line_edit.value = 5
        self.radius_line_edit.setToolTip("Set radius for averaging points")
        self.threshold_line_edit = CustomLineEdit()
        self.threshold_line_edit.value = 500
        self.threshold_line_edit.setToolTip("")
        self.spacing_line_edit = CustomLineEdit()
        self.spacing_line_edit.value = 50
        self.spacing_line_edit.setToolTip("Distance between interpolated points")
        self.point_type_combobox = QComboBox()
        self.point_type_combobox.addItems(['median + IQR', 'mean + stdev', 'mean + stderr'])
        self.point_type_combobox.setToolTip("Statistic for estimating point value")

        profile_tools_layout.addRow("Point sort",self.point_sort_combobox)
        profile_tools_layout.addRow("Point radius",self.radius_line_edit)
        profile_tools_layout.addRow("Y-Axis threshold",self.threshold_line_edit)
        profile_tools_layout.addRow("Interp. distance",self.spacing_line_edit)
        profile_tools_layout.addRow("Point type",self.point_type_combobox)


        self.control_points_table = QTableWidget()
        font = QFont()
        font.setPointSize(11)
        font.setStyleStrategy(QFont.PreferDefault)
        self.control_points_table.setFont(font)
        #self.control_points_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.control_points_table.setObjectName("control_points_table")
        self.control_points_table.setColumnCount(3)
        self.control_points_table.setRowCount(0)
        item = QTableWidgetItem()
        item.setText("Point")
        font = QFont()
        font.setPointSize(11)
        item.setFont(font)
        self.control_points_table.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem()
        item.setText("X")
        font = QFont()
        font.setPointSize(11)
        item.setFont(font)
        self.control_points_table.setHorizontalHeaderItem(1, item)
        item = QTableWidgetItem()
        item.setText("Y")
        font = QFont()
        font.setPointSize(11)
        item.setFont(font)
        self.control_points_table.setHorizontalHeaderItem(2, item)
        self.control_points_table.horizontalHeader().setDefaultSectionSize(80)
        self.control_points_table.horizontalHeader().setStretchLastSection(True)
        self.control_points_table.setSelectionBehavior(QTableWidget.SelectRows)

        header = self.control_points_table.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.Stretch)
        header.setSectionResizeMode(1,QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2,QHeaderView.ResizeToContents)

        profile_group_layout.addWidget(self.control_points_table)

        left_layout.addWidget(profile_tools)

        
        # create profile plot controls
        axis_tools = QGroupBox()
        axis_tools.setTitle("Axis Options")
        axis_tools.setMinimumWidth(180)
        axis_tools.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        axis_tools.setContentsMargins(3,3,3,3)
        axis_tools_layout = QVBoxLayout()
        axis_tools_layout.setContentsMargins(3,3,3,3)
        axis_tools.setLayout(axis_tools_layout)

        subplot_layout = QFormLayout()

        # Create first spin box and label
        self.num_subplots_spinbox = QSpinBox()
        self.num_subplots_spinbox.setRange(1, 6)  # Set range for spin box
        self.num_subplots_spinbox.setValue(1)     # Set default value

        # Create second spin box and label
        self.selected_subplot_spinbox = QSpinBox()
        self.selected_subplot_spinbox.setRange(1, 1)
        self.selected_subplot_spinbox.setValue(1)

        # Add the spin boxes and labels to the form layout
        subplot_layout.addRow("No. subplots", self.num_subplots_spinbox)
        subplot_layout.addRow("Selected subplot", self.selected_subplot_spinbox)

        self.field_type_combobox = CustomComboBox(update_callback=lambda: self.update_field_type_combobox(self.field_type_combobox))
        self.field_type_combobox.setToolTip("Select field type")

        field_layout = QHBoxLayout()

        self.field_combobox = QComboBox()
        self.field_combobox.setToolTip("Select field")


        self.add_field_button = QToolButton()
        add_icon = QIcon(":resources/icons/icon-accept-64.svg")
        if not add_icon.isNull():
            self.add_field_button.setIcon(add_icon)
        else:
            self.add_field_button.setText("Select a field to add it to the selected subplot")

        self.remove_field_button = QToolButton()
        add_icon = QIcon(":resources/icons/icon-reject-64.svg")
        if not add_icon.isNull():
            self.remove_field_button.setIcon(add_icon)
        else:
            self.remove_field_button.setText("Select a field in the list below to remove it from the selected subplot")

        field_layout.addWidget(self.field_combobox)
        field_layout.addWidget(self.add_field_button)
        field_layout.addWidget(self.remove_field_button)

        self.listViewProfile = QListView()

        self.remove_field_button = QToolButton()


        axis_tools_layout.addLayout(subplot_layout)
        axis_tools_layout.addWidget(self.field_type_combobox)
        axis_tools_layout.addLayout(field_layout)
        axis_tools_layout.addWidget(self.listViewProfile)

        left_layout.addWidget(axis_tools)

        container_layout.addLayout(dock_layout)
        container.setLayout(container_layout)
        scroll_area.setWidget(container)

        self.setWidget(scroll_area)

        self.setFloating(True)
        self.setWindowTitle("LaME Profiles")

        parent.addDockWidget(Qt.BottomDockWidgetArea, self)


        # connections for point tools
        self.point_sort_combobox.currentIndexChanged.connect(self.profiling.plot_profile_and_table)
        self.radius_line_edit.setValidator(QIntValidator())
        self.threshold_line_edit.setValidator(QIntValidator())
        self.actionControlPoints.triggered.connect(lambda: self.parent.comboBoxPlotType.setCurrentText("analyte map"))
        self.actionControlPoints.triggered.connect(lambda: self.profiling.on_profile_selected(self.profile_combobox.currentText()))
        # not implemented
        #self.toolButtonPointUp.clicked.connect(lambda: self.table_fcn.move_row_up(self.tableWidgetProfilePoints))
        #self.toolButtonPointDown.clicked.connect(lambda: self.table_fcn.move_row_down(self.tableWidgetProfilePoints))
        #self.toolButtonPointDelete.clicked.connect(lambda: self.table_fcn.delete_row(self.tableWidgetProfilePoints))
        #self.comboBoxProfileSort.currentIndexChanged.connect(self.profiling.plot_profile_and_table)
        #self.toolButtonPointSelectAll.clicked.connect(self.tableWidgetProfilePoints.selectAll)

        self.actionInterpolate.triggered.connect(lambda: self.profiling.interpolate_points(interpolation_distance=int(self.spacing_line_edit.text()), radius= int(self.radius_line_edit.text())))
        # update profile plot when point type is changed
        self.point_type_combobox.currentIndexChanged.connect(lambda: self.profiling.plot_profiles())
        # update profile plot when selected subplot is changed
        self.num_subplots_spinbox.valueChanged.connect(lambda: self.profiling.plot_profiles())
        # update profile plot when Num subplot is changed
        self.num_subplots_spinbox.valueChanged.connect(lambda: self.profiling.plot_profiles())
        self.num_subplots_spinbox.valueChanged.connect(self.update_profile_spinbox)
        # update profile plot when field in subplot table is changed
        
        # Connect the add and remove field buttons to methods
        self.field_type_combobox.activated.connect(lambda: self.update_field_combobox(self.field_type_combobox, self.field_combobox))
        self.add_field_button.clicked.connect(self.profiling.add_field_to_listview)
        self.add_field_button.clicked.connect(lambda: self.profiling.plot_profiles())
        self.remove_field_button.clicked.connect(self.profiling.remove_field_from_listview)
        self.remove_field_button.clicked.connect(lambda: self.profiling.plot_profiles())
        self.field_type_combobox.activated.connect(lambda: self.update_field_combobox(self.comboBoxProfileFieldType, self.comboBoxProfileField))

        # below line is commented because plot_profiles is automatically triggered when user clicks on map once they are in profiling tab
        # self.toolButtonPlotProfile.clicked.connect(lambda:self.profiling.plot_profiles())
        # Connect toolButtonProfileEditToggle's clicked signal to toggle edit mode
        self.actionControlPoints.triggered.connect(self.profiling.toggle_edit_mode)

        # Connect toolButtonProfilePointToggle's clicked signal to toggle point visibility
        self.actionEdit.checkedStateChanged.connect(lambda: self.actionTogglePoint.setEnabled(self.actionEdit.isChecked()))
        self.actionEdit.setChecked(False)
        self.actionTogglePoint.triggered.connect(self.profiling.toggle_point_visibility)
        
        self.actionControlPoints.triggered.connect(lambda: self.parent.reset_checked_items('profiling'))
        self.actionMovePoint.triggered.connect(lambda: self.parent.reset_checked_items('profiling'))
        

# Profiles
# -------------------------------
# The following class defines the metadata of profiles created along with information regarding each point
class Profile:
    def __init__(self,name,sort,radius,thresh,int_dist, point_error):
        self.name = name  # name given by user for the profile
        # points, i_points stores profile point information in format: 
        # {
        #     'x': [list of x coordinates],
        #     'y': [list of y coordinates],
        #     'field1': [list of circ_val lists at each coordinate],
        #     'field2': [...],
        #     ... other fields ...
        # }

        self.points = {}  
        self.i_points = {}
        # scatter_points holds scatter plots points information in format:
        #         {
        #     (field, view): [scatter1, scatter2, ...],
        # }
        # each scatter point is a pg.ScatterPlotItem
        self.scatter_points = {} 
        
        # initialise profile point properties
        self.sort = sort
        self.radius = radius
        self.y_axis_thresh = thresh
        self.int_dist = int_dist
        self.point_error = point_error
        
        

class Profiling:
    def __init__(self, parent):
        """Initialize the Profiling class.

        Sets up the profiling functionality, initializing necessary attributes and states.

        Parameters
        ----------
        parent : object
            The main window object that the profiling class interacts with.
        """
        self.parent = parent
        # Initialize other necessary attributes
        # Initialize variables and states as needed
        self.profiles = {} # holds profile information in format:  {sample_id: {profile_name:Profile instance}} 
        self.point_selected = False  # move point button selected
        self.point_index = -1              # index for move point
        self.all_errorbars = []       #stores points of profiles
        self.selected_points = {}  # Track selected points, e.g., {point_index: selected_state}
        self.edit_mode_enabled = False  # Track if edit mode is enabled
        self.original_colors = {}
        self.profile_name = None
        self.fields_per_subplot = {}  # Holds fields for each subplot, key: subplot index, value: list of fields
        self.new_plot = False #checks if new profile is being plotted
    
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
        for sample_id in self.parent.sample_ids:
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
                #serializable_profile = self.transform_profile_for_pickling(profile)
                with open(file_name, 'wb') as file:
                    pickle.dump(profile, file)
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
                    profile = pickle.load(file)
                    #profile = self.reconstruct_profile(serializable_profile)
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
        profile.points = serializable_profile['points']
        profile.i_points = serializable_profile['i_points']
        profile.scatter_points = {}

        # Reconstruct scatter_points
        for key, serialized_scatter_list in serializable_profile.get('scatter_points', {}).items():
            scatter_list = []
            for scatter_state in serialized_scatter_list:
                scatter = self.recreate_scatter_plot(scatter_state)
                scatter_list.append(scatter)
            profile.scatter_points[key] = scatter_list

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
        self.parent.comboBoxProfileList.clear()
        self.parent.comboBoxProfileList.addItem('Create New Profile')
        for profile_name in self.profiles[self.parent.sample_id].keys():
            self.parent.comboBoxProfileList.addItem(profile_name)

        self.new_plot = True #resets new plot flag

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
        self.new_plot= True #reset new plot flag
        if profile_name == 'Create New Profile':  # create a new profile instance and store instance in self.profiles
            new_profile_name, ok = QInputDialog.getText(self.parent, 'New Profile', 'Enter new profile name:')
            if ok and new_profile_name:
                if new_profile_name in self.profiles[self.parent.sample_id]:
                    QMessageBox.warning(self.parent, 'Error', 'Profile name already exists!')
                else:
                    self.clear_profiles()  # clear profiling plots and  contents
                    # obtain metadata of profiles from UI
                    sort = self.parent.comboBoxProfileSort.currentText()
                    radius = self.parent.lineEditPointRadius.text()
                    thresh = self.parent.lineEditPointRadius.text()
                    int_dist = self.parent.lineEditIntDist.text()
                    point_error = self.parent.comboBoxPointType.currentText()

                    # create new profile instance
                    self.profiles[self.parent.sample_id][new_profile_name] = Profile(new_profile_name, sort, radius, thresh, int_dist, point_error)
                    # add profile name to profile table
                    self.parent.comboBoxProfileList.addItem(new_profile_name)
                    self.parent.comboBoxProfileList.setCurrentText(new_profile_name)
                    self.profile_name = new_profile_name
            else:
                self.parent.comboBoxProfileList.setCurrentIndex(0)  # Reset to 'Create New Profile'
        else:
            if profile_name != self.profile_name: #if new profile is selected
                self.clear_profiles()  # clear profiling plots and  contents
                # plot existing profile and load profile metadata from dictionary
                self.profile_name = profile_name
                self.plot_existing_profile(self.parent.plot)
                profile = self.profiles[self.parent.sample_id][self.profile_name]
                self.parent.comboBoxProfileSort.setCurrentText(profile.sort)
                self.parent.lineEditPointRadius.setText(profile.radius)
                self.parent.lineEditPointRadius.setText(profile.y_axis_thresh)
                self.parent.lineEditIntDist.setText(profile.int_dist)
                self.parent.comboBoxPointType.setCurrentText(profile.point_error)
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
        """Plot/move a scatter point for profile at the clicked position.

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
        self.sample_id = self.parent.sample_id
        self.data = self.parent.data[self.sample_id]
        self.array_x = self.data.array_size[1]  # no of columns
        self.array_y = self.data.array_size[0]  # no of rows
        interpolate = False

        profile_points = self.profiles[self.sample_id][self.profile_name].points
        scatter_points = self.profiles[self.sample_id][self.profile_name].scatter_points

        radius = int(self.parent.lineEditPointRadius.text())
        if event.button() == Qt.RightButton and self.parent.toolButtonPlotProfile.isChecked():
            # Turn off profiling points
            self.parent.toolButtonPlotProfile.setChecked(False)
            self.parent.toolButtonPointMove.setEnabled(True)
            return
        elif event.button() == Qt.RightButton and self.parent.toolButtonPointMove.isChecked():
            # Turn off moving point, reset point_selected
            self.parent.toolButtonPointMove.setChecked(False)
            self.point_selected = False
            return
        elif event.button() == Qt.RightButton or event.button() == Qt.MiddleButton:
            return
        elif event.button() == Qt.LeftButton and not (self.parent.toolButtonPlotProfile.isChecked()) and self.parent.toolButtonPointMove.isChecked():
            # move point
            if self.point_selected:
                self.plot_scatter_points(scatter_points, x, y,point_index=self.point_index)
                self.compute_profile_points(profile_points, radius, x, y, x_i, y_i, self.point_index)
                self.point_index = -1              # reset index 
                if self.parent.toolButtonProfileInterpolate.isChecked():  # reset interpolation if selected
                    self.clear_interpolation()
                    self.interpolate_points(interpolation_distance=int(self.parent.lineEditIntDist.text()), radius=int(self.parent.lineEditPointRadius.text()))
                # switch to profile tab
                self.parent.tabWidget.setCurrentIndex(self.parent.bottom_tab['profile'])
                self.plot_profiles()  # Plot averaged profile value on profiles plots with error bars
                self.update_table_widget()
            else:
                # find nearest profile point
                mindist = 10 ** 12
                for i, (x_p, y_p) in enumerate(list(zip(profile_points['x'],profile_points['y']))):
                    dist = (x_p - x) ** 2 + (y_p - y) ** 2
                    if mindist > dist:
                        mindist = dist
                        self.point_index = i
                if not (round(mindist * self.array_x / self.data.x_range) < 50):
                    self.point_selected = True
        elif event.button() == Qt.LeftButton:  # plot profile scatter
            # Add the scatter item to all plots
            self.plot_scatter_points(scatter_points, x, y)
            # compute profile value for all fields 
            self.compute_profile_points(profile_points, radius, x, y, x_i, y_i)
            # switch to profile tab
            self.parent.tabWidget.setCurrentIndex(self.parent.bottom_tab['profile'])
            if self.new_plot: #add field name to profile list view if its a new plot
                self.add_field_to_listview(field)
                self.new_plot = False
            self.plot_profiles()  # Plot averaged profile value on profiles plots with error bars
            self.update_table_widget()

    def plot_scatter_points(self,scatter_points, x, y,point_index = None, symbol='+', size=10):
        """Plots scatter point in all plots in canvas (Single view/ Multi view)

        Determines iterates through all plot items in self.lasermaps and add scatter points to the plots in the current view

        Parameters
        ----------
        scatter_points : dict
            Dictionary to store scatter points.
        x : float
            The x-coordinate of the point.
        y : float
            The y-coordinate of the point.
        point_index : int, optional
            The index of the point if updating an existing point.

        Returns
        -------
        None
        """
        for (field,view), (_, plot,  array) in self.parent.lasermaps.items():
            canvas_view  =self.parent.canvasWindow.currentIndex() #check if plot on single view or multi view
            if view == canvas_view and self.array_x ==array.shape[1] and self.array_y ==array.shape[0] : #ensure points within boundaries of plot
                # Create a scatter plot item at the clicked position
                scatter = ScatterPlotItem([x], [y], symbol=symbol, size=size)
                scatter.setZValue(1e9)
                plot.addItem(scatter)
                if point_index is not None: # remove selected point from list (point is being moved) before adding new point
                    prev_scatter = scatter_points[(field,view)][self.point_index]
                    plot.removeItem(prev_scatter)
                    scatter_points[(field,view)][self.point_index] = scatter #add new scatter point to list
                else:
                    # add scatter point to scatter_points dictionary
                    if (field, view) in scatter_points:
                        scatter_points[(field,view)].append(scatter)
                    else:
                        scatter_points[(field,view)]= [scatter]

    # def compute_profile_points(self, profile_points, radius, x, y, x_i, y_i, point_index=None):
    #     """Compute profile points by averaging values within a radius.

    #     Calculates the mean values within a specified radius around a point and updates the profile points.

    #     Parameters
    #     ----------
    #     profile_points : dict
    #         Dictionary to store computed profile points. in format {x: [], y:[], field: (circ_values)}
    #     radius : int
    #         The radius around the point to consider for averaging.
    #     x : float
    #         The x-coordinate of the point.
    #     y : float
    #         The y-coordinate of the point.
    #     x_i : int
    #         The index of the x-coordinate in the array.
    #     y_i : int
    #         The index of the y-coordinate in the array.
    #     point_index : int, optional
    #         The index of the point if updating an existing point.

    #     Returns
    #     -------
    #     None
    #     """
    #     # Obtain field data of all fields that will be used for profiling
    #     fields = self.data.processed_data.match_attribute('data_type', 'analyte') + self.data.processed_data.match_attribute('data_type', 'ratio')
    #     field_data = self.data.processed_data[fields]

    #     # If updating an existing point, remove it first
    #     if point_index is not None:
    #         for key in profile_points.keys():
    #             del profile_points[key][point_index]

    #     # Collect circ_values for each field
    #     circ_values_dict = {}
    #     p_radius_y = self.dist_to_cart(radius, 'y')  # Pixel radius in y direction
    #     p_radius_x = self.dist_to_cart(radius, 'x')  # Pixel radius in x direction

    #     for field in field_data.columns:
    #         array = np.reshape(field_data[field].values, self.data.array_size, order=self.data.order)
    #         circ_values = []

    #         # Store pixel values within bounds of circle with center (x_i, y_i) and radius `radius`
    #         for i in range(max(0, y_i - p_radius_y), min(self.array_y, y_i + p_radius_y + 1)):
    #             for j in range(max(0, x_i - p_radius_x), min(self.array_x, x_i + p_radius_x + 1)):
    #                 if self.calculate_distance(self.cart_to_dist(y_i - i), self.cart_to_dist(x_i - j)) <= radius:
    #                     value = array[i, j]
    #                     circ_values.append(value)

    #         circ_values_dict[field] = circ_values

    #     # Update profile_points with new data
    #     if 'x' in profile_points:
    #         if point_index is not None:
    #             profile_points['x'].insert(point_index, x)
    #             profile_points['y'].insert(point_index, y)
    #         else:
    #             profile_points['x'].append(x)
    #             profile_points['y'].append(y)
    #     else:
    #         profile_points['x'] = [x]
    #         profile_points['y'] = [y]

    #     for field, circ_values in circ_values_dict.items():
    #         if field in profile_points:
    #             if point_index is not None:
    #                 profile_points[field].insert(point_index, circ_values)
    #             else:
    #                 profile_points[field].append(circ_values)
    #         else:
    #             profile_points[field] = [circ_values]
    def compute_profile_points(self, profile_points, radius, x, y, x_i, y_i, point_index=None):
        """Compute profile points by averaging values within a radius.

        Calculates the mean values within a specified radius around a point and updates the profile points.

        Parameters
        ----------
        profile_points : dict
            Dictionary to store computed profile points. in format {x: [], y:[], field: [circ_values]}
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
        fields = (
            self.data.processed_data.match_attribute('data_type', 'analyte') +
            self.data.processed_data.match_attribute('data_type', 'ratio')
        )
        field_data = self.data.processed_data[fields]

        # If updating an existing point, remove it first
        if point_index is not None:
            for key in profile_points.keys():
                del profile_points[key][point_index]

        # Physical size per pixel in x and y directions
        dx = self.data.dx
        dy = self.data.dy

        # Precompute pixel radius in x and y directions
        p_radius_y = self.dist_to_cart(radius, 'y')  # Pixel radius in y direction
        p_radius_x = self.dist_to_cart(radius, 'x')  # Pixel radius in x direction

        # Get the ranges of indices in i and j directions
        i_min = max(0, y_i - p_radius_y)
        i_max = min(self.array_y, y_i + p_radius_y + 1)
        j_min = max(0, x_i - p_radius_x)
        j_max = min(self.array_x, x_i + p_radius_x + 1)

        i_range = np.arange(i_min, i_max)  # Shape: (n_i,)
        j_range = np.arange(j_min, j_max)  # Shape: (n_j,)

        # Create grids for indices
        I_grid, J_grid = np.meshgrid(i_range, j_range, indexing='ij')  # Both shapes: (n_i, n_j)

        # Compute physical distances
        di_phys = (I_grid - y_i) * dy  # Shape: (n_i, n_j)
        dj_phys = (J_grid - x_i) * dx  # Shape: (n_i, n_j)

        dists_squared = di_phys**2 + dj_phys**2  # Shape: (n_i, n_j)

        # Create mask for points within the specified radius
        mask = dists_squared <= radius**2  # Shape: (n_i, n_j)

        # Get the indices of valid points
        i_indices = I_grid[mask]
        j_indices = J_grid[mask]

        # For each field, extract the values at these indices
        for field in field_data.columns:
            array = np.reshape(field_data[field].values, self.data.array_size, order=self.data.order)
            values = array[i_indices, j_indices]
            circ_values = values.tolist()

            if field in profile_points:
                if point_index is not None:
                    profile_points[field].insert(point_index, circ_values)
                else:
                    profile_points[field].append(circ_values)
            else:
                profile_points[field] = [circ_values]

        # Update profile_points with new data
        if 'x' in profile_points:
            if point_index is not None:
                profile_points['x'].insert(point_index, x)
                profile_points['y'].insert(point_index, y)
            else:
                profile_points['x'].append(x)
                profile_points['y'].append(y)
        else:
            profile_points['x'] = [x]
            profile_points['y'] = [y]



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
        # Clear existing plots
        self.clear_plot()
        sample_id = self.parent.sample_id
        profile_name = self.profile_name

        if profile_name in self.profiles[sample_id]:
            profile_points = self.profiles[sample_id][profile_name].points
            scatter_points = self.profiles[sample_id][profile_name].scatter_points
            x_coords = profile_points.get('x', [])
            y_coords = profile_points.get('y', [])

            # Ensure scatter_points is initialized
            if not scatter_points:
                scatter_points = {}

            # Plot the points
            for idx, (x, y) in enumerate(zip(x_coords, y_coords)):
                self.plot_scatter_points(scatter_points, x, y)

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
        # Corrected: Use self.parent.sample_id consistently
        sample_id = self.sample_id
        profile_name = self.profile_name

        profile_points = self.profiles[sample_id][profile_name].points
        i_profile_points = self.profiles[sample_id][profile_name].i_points
        scatter_points = self.profiles[sample_id][profile_name].scatter_points

        # Ensure 'x' and 'y' are in profile_points
        if 'x' not in profile_points or 'y' not in profile_points:
            print("Profile points must contain 'x' and 'y' coordinates.")
            return

        # Corrected: Convert zip object to list for indexing
        point_coordinates = list(zip(profile_points['x'], profile_points['y']))

        # Corrected: Use string literals 'x' and 'y' in the set
        fields = [field for field in profile_points.keys() if field not in {'x', 'y'}]

        if self.parent.toolButtonProfileInterpolate.isChecked():
            interpolate = True
            # Initialize i_profile_points dictionaries
            i_profile_points.clear()
            i_profile_points['x'] = []
            i_profile_points['y'] = []
            for field in fields:
                i_profile_points[field] = []

            for i in range(len(point_coordinates) - 1):
                # Define start and end points
                start_point = point_coordinates[i]
                end_point = point_coordinates[i + 1]

                # Add the start_point coordinates to i_profile_points
                i_profile_points['x'].append(start_point[0])
                i_profile_points['y'].append(start_point[1])

                # Add the circ_val list of start_point for each field to i_profile_points
                for field in fields:
                    i_profile_points[field].append(profile_points[field][i])

                # Calculate the distance between start and end points
                dist = self.calculate_distance(start_point, end_point)

                # Handle division by zero if dist is zero
                if dist == 0:
                    continue  # Skip interpolation if two points are the same

                # Determine the number of interpolations based on the distance
                num_interpolations = max(int(dist / interpolation_distance), 0)

                # Calculate the unit vector in the direction from start_point to end_point
                dx = (end_point[0] - start_point[0]) / dist
                dy = (end_point[1] - start_point[1]) / dist

                for t in range(1, num_interpolations + 1):
                    # Find coordinates of interpolated point
                    x = start_point[0] + t * interpolation_distance * dx
                    y = start_point[1] + t * interpolation_distance * dy

                    x_i = self.dist_to_cart(x, 'x')  # index points
                    y_i = self.dist_to_cart(y, 'y')

                    # Add the scatter item to all plots
                    self.plot_scatter_points(scatter_points, x, y)

                    # Compute profile values for all fields at the interpolated point
                    self.compute_profile_points(i_profile_points, radius, x, y, x_i, y_i)

            # Add the end_point coordinates to i_profile_points
            end_point = point_coordinates[-1]
            i_profile_points['x'].append(end_point[0])
            i_profile_points['y'].append(end_point[1])

            # Add the circ_val list of end_point for each field to i_profile_points
            for field in fields:
                i_profile_points[field].append(profile_points[field][-1])

            # After interpolation, update the plot and table widget
            self.plot_profiles(interpolate=interpolate)
        else:
            self.clear_interpolation()
            # Plot original profile
            self.plot_profiles(interpolate=False)


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
        if self.parent.sample_id in self.profiles:
            for profile_name, profile in self.profiles[self.parent.sample_id].items():
                scatter_points = profile.scatter_points
                # Clear scatter points from the plots
                for (field, view), scatter_list in scatter_points.items():
                    for scatter_item in scatter_list:
                        plot = self.parent.lasermaps[(field, view)][1]
                        plot.removeItem(scatter_item)
                # Clear the scatter_points dictionary
                scatter_points.clear()

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
        i_profile_points = self.profiles[self.parent.sample_id][self.profile_name].i_points
        scatter_points = self.profiles[self.parent.sample_id][self.profile_name].scatter_points
        # Remove interpolated scatter points
        for (field, view), scatter_list in scatter_points.items():
            for scatter_item in scatter_list:
                plot = self.parent.lasermaps[(field, view)][1]
                plot.removeItem(scatter_item)
        # Clear the interpolated profile points and scatter_points
        i_profile_points.clear()
        scatter_points.clear()


    def plot_profiles(self, fields=None, num_subplots=None, selected_subplot=None, interpolate=None, sort_axis=None):
        """Plot averaged profile values with error bars.

        Plots the profile values stored in self.profiles with error bars on the specified subplot(s),
        using fields assigned to each subplot stored in self.fields_per_subplot.

        Parameters
        ----------
        fields : list of str, optional
            List of fields to plot. If None, fields are obtained from self.fields_per_subplot.
        num_subplots : int, optional
            Number of subplots to create. If None, value is obtained from self.parent.spinBoxProfileNumSubplots.
        selected_subplot : int, optional
            Index of the selected subplot to plot on (1-based). If None, value is obtained from self.parent.spinBoxProfileSelectedSubplot.
        interpolate : bool, optional
            Whether to use interpolated points. Default is None, which checks the UI state.
        sort_axis : str, optional
            Axis to sort the profile points by ('x' or 'y'). If None, obtained from self.parent.comboBoxProfileSort.

        Returns
        -------
        None
        """
        if interpolate is None:
            interpolate = self.parent.toolButtonProfileInterpolate.isChecked()

        # Get num_subplots and selected_subplot from UI if not provided
        if num_subplots is None:
            num_subplots = self.parent.spinBoxProfileNumSubplots.value()
        if selected_subplot is None:
            selected_subplot = self.parent.spinBoxProfileSelectedSubplot.value()

        # Ensure fields_per_subplot has entries for all subplots
        for i in range(num_subplots):
            if i not in self.fields_per_subplot:
                self.fields_per_subplot[i] = []

        # Get the point type
        point_type_text = self.parent.comboBoxPointType.currentText()
        point_type = 'median' if point_type_text == 'median + IQR' else 'mean'

        # Get sort axis if not provided
        if sort_axis is None:
            sort_axis = self.parent.comboBoxProfileSort.currentText().lower()

        # Decide whether to use interpolated points
        if interpolate:
            profile_points = self.profiles[self.parent.sample_id][self.profile_name].i_points
        else:
            profile_points = self.profiles[self.parent.sample_id][self.profile_name].points

        # Get style and colormap
        style = self.parent.style
        cmap = style.get_colormap()

        # Clear existing plot
        layout = self.parent.widgetProfilePlot.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Initialize the figure
        self.fig = Figure()
        self.fig.canvas.mpl_connect('pick_event', self.on_pick)

        # Set up subplots
        self.all_errorbars = []
        if num_subplots < 1:
            num_subplots = 1

        # Create subplots
        axes = []
        for i in range(num_subplots):
            ax = self.fig.add_subplot(num_subplots, 1, i + 1)
            axes.append(ax)

        # Now, plot the fields
        for subplot_idx, ax in enumerate(axes):
            fields_in_subplot = self.fields_per_subplot.get(subplot_idx, [])
            # Update the list view if this is the selected subplot
            if subplot_idx == selected_subplot - 1:
                self.update_listview_with_fields(fields_in_subplot)
            if not fields_in_subplot:
                continue  # No fields to plot in this subplot



            for field_idx, field in enumerate(fields_in_subplot):
                # Get the points for the field
                if field not in profile_points:
                    continue  # Skip if no data for this field
                circ_val = profile_points[field]
                x = profile_points['x']
                y = profile_points['y']
                # Process points
                distances, medians, lowers, uppers, means, s_errors = self.process_points(x, y, circ_val, sort_axis)

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
        self.parent.widgetProfilePlot.layout().addWidget(widget)
        widget.show()


    def process_points(self, x, y, circ_values, sort_axis):
        """Process profile points to compute statistics and distances.

        Calculates distances and statistical measures (median, mean, quartiles, standard errors) for profile points.

        Parameters
        ----------
        x : list of float
            List of x-coordinates.
        y : list of float
            List of y-coordinates.
        circ_values : list of lists
            List where each element is a list of values within the radius around the corresponding point.
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
        # Combine x, y, and circ_values into a list of tuples
        combined = list(zip(x, y, circ_values))

        # Sort the combined list based on the user-specified axis
        if sort_axis == 'x':
            combined.sort(key=lambda p: p[0])  # Sort by x-coordinate
        elif sort_axis == 'y':
            combined.sort(key=lambda p: p[1])  # Sort by y-coordinate

        # Unzip the sorted list back into x_sorted, y_sorted, and circ_values_sorted
        x_sorted, y_sorted, circ_values_sorted = zip(*combined)

        median_values = []
        lower_quantiles = []
        upper_quantiles = []
        mean_values = []
        standard_errors = []
        distances = []

        for i, values in enumerate(circ_values_sorted):
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
                dist = self.calculate_distance(
                    (x_sorted[i], y_sorted[i]),
                    (x_sorted[i - 1], y_sorted[i - 1])
                )
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
        if self.parent.sample_id in self.profiles:  # if profiles have been initiated for the samples
            if self.profile_name in self.profiles[self.parent.sample_id]:  # if profiles for that sample exist
                # Clear all scatter plot items from the lasermaps
                for _, (_, plot, _) in self.parent.lasermaps.items():
                    items_to_remove = [item for item in plot.listDataItems() if isinstance(item, ScatterPlotItem)]
                    for item in items_to_remove:
                        plot.removeItem(item)

                # Clear the profiles data
                # profile.clear()

                # Clear all data from the table
                self.parent.control_points_table.clearContents()

                # Remove all rows
                self.parent.control_points_table.setRowCount(0)

                # Clear the profile plot widget
                layout = self.parent.widgetProfilePlot.layout()
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                
                # reset listviewprfile
                model = self.parent.listViewProfile.model()
                if model: 
                    model.clear()

                # reset flags and variables
                self.point_selected = False  # move point button selected
                self.point_index = -1              # index for move point
                self.all_errorbars = []       #stores points of profiles
                self.selected_points = {}  # Track selected points, e.g., {point_index: selected_state}
                self.edit_mode_enabled = False  # Track if edit mode is enabled
                self.original_colors = {}
                self.profile_name = None
                self.fields_per_subplot = {}  # Holds fields for each subplot, key: subplot index, value: list of fields
                self.new_plot = False #checks if new profile is being plotted

                #reset UI widgets
                self.parent.toolButtonPlotProfile.setChecked(False)
                self.parent.toolButtonPointMove.setEnabled(False)
                self.parent.toolButtonProfileInterpolate.setChecked(False)
                # Block signals
                self.parent.spinBoxProfileSelectedSubplot.blockSignals(True)
                self.parent.spinBoxProfileNumSubplots.blockSignals(True)
                # Change the value programmatically
                self.parent.spinBoxProfileSelectedSubplot.setValue(1)
                self.parent.spinBoxProfileNumSubplots.setValue(1)
                # Unblock signals
                self.parent.spinBoxProfileSelectedSubplot.blockSignals(False)
                self.parent.spinBoxProfileNumSubplots.blockSignals(False)
                self.parent.comboBoxProfileFieldType.setCurrentIndex(0)
                self.parent.comboBoxProfileFieldType.setCurrentIndex(0)

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
        if self.parent.sample_id in self.profiles:
            if self.profile_name in self.profiles[self.parent.sample_id]:
                profile_points = self.profiles[self.parent.sample_id][self.profile_name].points
                x_coords = profile_points.get('x', [])
                y_coords = profile_points.get('y', [])

                self.parent.control_points_table.setRowCount(0)
                for idx, (x, y) in enumerate(zip(x_coords, y_coords)):
                    row_position = self.parent.control_points_table.rowCount()
                    self.parent.control_points_table.insertRow(row_position)

                    # Fill in the data
                    self.parent.control_points_table.setItem(row_position, 0, QTableWidgetItem(str(idx)))
                    self.parent.control_points_table.setItem(row_position, 1, QTableWidgetItem(str(round(x))))
                    self.parent.control_points_table.setItem(row_position, 2, QTableWidgetItem(str(round(y))))
                    self.parent.control_points_table.setRowHeight(row_position, 20)

                # Enable or disable buttons based on the presence of points
                self.toggle_buttons(self.parent.control_points_table.rowCount() > 0)


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
        self.parent.toolButtonPointUp.setEnabled(enable)
        self.parent.toolButtonPointDown.setEnabled(enable)
        self.parent.toolButtonPointDelete.setEnabled(enable)

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
        style = self.parent.style

        if self.edit_mode_enabled and isinstance(event.artist, PathCollection):
            # The picked scatter plot
            picked_scatter = event.artist
            # Indices of the picked points, could be multiple if overlapping
            ind = event.ind[0]  # Let's handle the first picked point for simplicity
            field = picked_scatter.get_gid()  # Assuming GID corresponds to field name
            # Determine the color of the picked point
            facecolors = picked_scatter.get_facecolors().copy()
            original_color = colors.to_rgba(self.original_colors[field])  # Map field to original colors

            # Toggle selection state
            self.selected_points[field][ind] = not self.selected_points[field][ind]

            num_points = len(picked_scatter.get_offsets())
            # If initially, there's only one color for all points,
            # we might need to ensure the array is expanded to explicitly cover all points.
            if len(facecolors) == 1 and num_points > 1:
                facecolors = np.tile(facecolors, (num_points, 1))

            if not self.selected_points[field][ind]:
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

        for field in self.selected_points.keys():
            # Retrieve the scatter object using its field name
            scatter, barlinecol = self.get_scatter_errorbar_by_gid(field)
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
            for idx, selected in enumerate(self.selected_points[field]):
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
        for field in self.selected_points.keys():
            # Retrieve the scatter object using its field name
            scatter, barlinecol = self.get_scatter_errorbar_by_gid(field)
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
            for idx, selected in enumerate(self.selected_points[field]):
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
        """Add selected fields to the profile list view and update the fields per subplot."""
        # Get the currently selected subplot index
        selected_subplot = self.parent.spinBoxProfileSelectedSubplot.value() - 1  # 0-based index

        # Get available fields (assuming you have a method to retrieve them)
        if not field:
            field = self.parent.comboBoxProfileField.currentText()
        if not field:
            QMessageBox.warning(self.parent, 'No Fields', 'There are no available fields to add.')
            return

        # Add selected field to the fields_per_subplot
        if selected_subplot not in self.fields_per_subplot:
            self.fields_per_subplot[selected_subplot] = []

        if field not in self.fields_per_subplot[selected_subplot]:
            self.fields_per_subplot[selected_subplot].append(field)
            # Update the list view
            self.update_listview_with_fields(self.fields_per_subplot[selected_subplot])
            if update:
                # Update the plot
                self.plot_profiles()
        else:
            QMessageBox.information(self.parent, 'Field Exists', f'The field "{field}" is already in the list.')

    def remove_field_from_listview(self):
        """Remove selected fields from the profile list view and update the fields per subplot."""
        # Get the currently selected subplot index
        selected_subplot = self.parent.spinBoxProfileSelectedSubplot.value() - 1  # 0-based index

        # Get selected indices
        selection_model = self.parent.listViewProfile.selectionModel()
        indexes = selection_model.selectedIndexes()

        if not indexes:
            QMessageBox.warning(self.parent, 'No Selection', 'Please select a field to remove.')
            return

        # Remove selected items from the fields_per_subplot and list view
        model = self.parent.listViewProfile.model()
        fields_removed = []
        for index in sorted(indexes, reverse=True):
            field = model.item(index.row()).text()
            fields_removed.append(field)
            model.removeRow(index.row())

        # Update fields_per_subplot
        for field in fields_removed:
            if field in self.fields_per_subplot.get(selected_subplot, []):
                self.fields_per_subplot[selected_subplot].remove(field)

        # Update the plot
        self.plot_profiles()

    def update_num_subplots(self):
        num_subplots = self.parent.spinBoxProfileNumSubplots.value()
        # Adjust fields_per_subplot
        existing_subplots = list(self.fields_per_subplot.keys())
        if num_subplots < len(existing_subplots):
            # Remove extra subplots
            for idx in existing_subplots:
                if idx >= num_subplots:
                    del self.fields_per_subplot[idx]
        elif num_subplots > len(existing_subplots):
            # Add new subplots with empty fields
            for idx in range(len(existing_subplots), num_subplots):
                self.fields_per_subplot[idx] = []

        # Ensure selected subplot is within the new range
        selected_subplot = self.parent.spinBoxProfileSelectedSubplot.value()
        if selected_subplot > num_subplots:
            self.parent.spinBoxProfileSelectedSubplot.setValue(num_subplots)

        # Update the plot
        self.plot_profiles()

    def update_listview_with_fields(self, fields):
        """Update the list view with the given list of fields.

        Parameters
        ----------
        fields : list of str
            The list of field names to display in the list view.

        Returns
        -------
        None
        """
        model = self.parent.listViewProfile.model()
        if not model:
            model = QStandardItemModel()
            self.parent.listViewProfile.setModel(model)
        else:
            model.clear()  # Clear existing items

        for field in fields:
            item = QStandardItem(field)
            model.appendRow(item)
            
    def plot_profile_and_table(self):
        self.plot_profiles()
        self.update_table_widget()
    

    
