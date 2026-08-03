import os, pickle
import numpy as np
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import (
    QStandardItem, QStandardItemModel, QIcon, QFont, QIntValidator, QAction
)
from PyQt6.QtWidgets import (
        QMessageBox, QInputDialog, QFileDialog, QWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QGroupBox,
        QToolButton, QComboBox, QSpinBox, QSizePolicy, QFormLayout, QListView, QToolBar,
        QLabel, QHeaderView, QTableWidget, QScrollArea, QMainWindow, QWidgetAction, QAbstractItemView
    )
from lame_core.CustomWidgets import CustomDockWidget, CustomLineEdit, CustomComboBox, ToggleSwitch
from lame_core.config import BASEDIR
from src.app.FieldLogic import FieldLogicUI
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.colors as colors
from matplotlib.collections import PathCollection
from src.common.Logger import LoggerConfig, auto_log_methods

@auto_log_methods(logger_key='Profile')
class ProfileDock(CustomDockWidget, FieldLogicUI):
    def __init__(self, parent=None):
        if not isinstance(parent, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        super().__init__(parent)
        self.logger_key = 'Profile'

        self.main_window = parent

        self.profiling = Profiling(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        container = QWidget()
        container_layout = QVBoxLayout()

        # create toolbar for editing profile plots
        toolbar = QToolBar("Profile Toolbar", self)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out

        # profile toggle
        self.profile_toggle = ToggleSwitch(toolbar, height=18, bg_left_color="#D8ADAB", bg_right_color="#A8B078")
        self.profile_toggle.setChecked(False)
        self.actionProfileToggle = QWidgetAction(toolbar)
        self.actionProfileToggle.setDefaultWidget(self.profile_toggle)
        self.profile_toggle.stateChanged.connect(self.profile_state_changed)

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
        self.actionControlPoints.setShortcut("Ctrl+N")
        self.actionControlPoints.setToolTip("Create new profile and set control points")
        self.actionControlPoints.setCheckable(True)
        self.actionControlPoints.setChecked(False)

        # Interpolate profile -- interpolation runs automatically whenever control
        # points change; this just forces a refresh (e.g. after changing radius/
        # spacing without editing a point), so it's a simple trigger, not a toggle.
        self.actionInterpolate = QAction()
        self.actionInterpolate.setIcon(QIcon(":resources/icons/icon-interpolate-64.svg"))
        self.actionInterpolate.setToolTip("Recompute interpolation with the current radius/spacing")

        # Move control point
        self.actionPointMove = QAction()
        self.actionPointMove.setIcon(QIcon(":resources/icons/icon-move-point-64.svg"))
        self.actionPointMove.setToolTip("Move a control point")
        self.actionPointMove.setCheckable(True)
        self.actionPointMove.setChecked(False)

        # Add control point
        self.actionPointAdd = QAction()
        self.actionPointAdd.setIcon(QIcon(":resources/icons/icon-add-point-64.svg"))
        self.actionPointAdd.setToolTip("Add a control point")
        self.actionPointAdd.setCheckable(True)
        self.actionPointAdd.setChecked(False)

        # Remove control point
        self.actionPointRemove = QAction()
        self.actionPointRemove.setIcon(QIcon(":resources/icons/icon-remove-point-64.svg"))
        self.actionPointRemove.setToolTip("Remove a control point")
        self.actionPointRemove.setCheckable(True)
        self.actionPointRemove.setChecked(False)

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

        # export profile figure button
        self.actionExport = QAction()
        self.actionExport.setIcon(QIcon(":resources/icons/icon-save-file-64.svg"))
        self.actionExport.setToolTip("Save profile to disk")

        toolbar.addAction(self.actionProfileToggle)
        toolbar.addSeparator()
        toolbar.addAction(self.actionOpenProfile)
        toolbar.addWidget(self.profile_label)
        toolbar.addWidget(self.profile_combobox)
        toolbar.addAction(self.actionExport)
        toolbar.addAction(self.actionDeleteProfile)
        toolbar.addSeparator()
        toolbar.addAction(self.actionControlPoints)
        toolbar.addAction(self.actionInterpolate)
        toolbar.addAction(self.actionPointMove)
        toolbar.addAction(self.actionPointAdd)
        toolbar.addAction(self.actionPointRemove)
        toolbar.addSeparator()
        toolbar.addAction(self.actionEdit)
        toolbar.addAction(self.actionTogglePoint)

        container_layout.addWidget(toolbar)

        dock_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        dock_layout.addLayout(left_layout)

        # create widget for placing profile plots
        self.widgetProfilePlot = QWidget()
        self.widgetProfilePlot.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))
        self.widgetProfilePlot.setLayout(QVBoxLayout())
        dock_layout.addWidget(self.widgetProfilePlot)
        # create profile controls

        profile_tools = QGroupBox()
        profile_tools.setTitle("Profile Options")
        profile_tools.setMinimumWidth(180)
        profile_tools.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding))
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


        self.tableWidgetControlPoints = QTableWidget()
        font = QFont()
        font.setPointSize(11)
        font.setStyleStrategy(QFont.StyleStrategy.PreferDefault)
        self.tableWidgetControlPoints.setFont(font)
        #self.tableWidgetControlPoints.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.tableWidgetControlPoints.setObjectName("tableWidgetControlPoints")
        self.tableWidgetControlPoints.setColumnCount(3)
        self.tableWidgetControlPoints.setRowCount(0)
        item = QTableWidgetItem()
        item.setText("Point")
        font = QFont()
        font.setPointSize(11)
        item.setFont(font)
        self.tableWidgetControlPoints.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem()
        item.setText("X")
        font = QFont()
        font.setPointSize(11)
        item.setFont(font)
        self.tableWidgetControlPoints.setHorizontalHeaderItem(1, item)
        item = QTableWidgetItem()
        item.setText("Y")
        font = QFont()
        font.setPointSize(11)
        item.setFont(font)
        self.tableWidgetControlPoints.setHorizontalHeaderItem(2, item)
        self.tableWidgetControlPoints.horizontalHeader().setDefaultSectionSize(80)
        self.tableWidgetControlPoints.horizontalHeader().setStretchLastSection(True)
        self.tableWidgetControlPoints.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        header = self.tableWidgetControlPoints.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        profile_group_layout.addWidget(self.tableWidgetControlPoints)

        left_layout.addWidget(profile_tools)


        # create profile plot controls
        axis_tools = QGroupBox()
        axis_tools.setTitle("Axis Options")
        axis_tools.setMinimumWidth(180)
        axis_tools.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        axis_tools.setContentsMargins(3,3,3,3)
        axis_tools_layout = QVBoxLayout()
        axis_tools_layout.setContentsMargins(3,3,3,3)
        axis_tools.setLayout(axis_tools_layout)

        layoutSubplot = QFormLayout()

        # Create first spin box and label
        self.num_subplots_spinbox = QSpinBox()
        self.num_subplots_spinbox.setRange(1, 6)  # Set range for spin box
        self.num_subplots_spinbox.setValue(1)     # Set default value

        # Create second spin box and label
        self.selected_subplot_spinbox = QSpinBox()
        self.selected_subplot_spinbox.setRange(1, 1)
        self.selected_subplot_spinbox.setValue(1)

        # Add the spin boxes and labels to the form layout
        layoutSubplot.addRow("No. subplots", self.num_subplots_spinbox)
        layoutSubplot.addRow("Selected subplot", self.selected_subplot_spinbox)

        self.comboBoxFieldType = CustomComboBox(popup_callback=lambda: self.update_field_type_combobox(self.comboBoxFieldType))
        self.comboBoxFieldType.setToolTip("Select field type")

        layoutField = QHBoxLayout()

        self.comboBoxField = QComboBox()
        self.comboBoxField.setToolTip("Select field")


        self.add_field_button = QToolButton()
        add_icon = QIcon(":resources/icons/icon-accept-64.svg")
        if not add_icon.isNull():
            self.add_field_button.setIcon(add_icon)
        else:
            self.add_field_button.setText("Select a field to add it to the selected subplot")

        self.buttonRemoveField = QToolButton()
        add_icon = QIcon(":resources/icons/icon-reject-64.svg")
        if not add_icon.isNull():
            self.buttonRemoveField.setIcon(add_icon)
        else:
            self.buttonRemoveField.setText("Select a field in the list below to remove it from the selected subplot")

        layoutField.addWidget(self.comboBoxField)
        layoutField.addWidget(self.add_field_button)
        layoutField.addWidget(self.buttonRemoveField)

        self.listViewProfile = QListView()

        axis_tools_layout.addLayout(layoutSubplot)
        axis_tools_layout.addWidget(self.comboBoxFieldType)
        axis_tools_layout.addLayout(layoutField)
        axis_tools_layout.addWidget(self.listViewProfile)

        left_layout.addWidget(axis_tools)

        container_layout.addLayout(dock_layout)
        container.setLayout(container_layout)
        scroll_area.setWidget(container)

        self.setWidget(scroll_area)

        self.setFloating(True)
        self.setWindowTitle("LaME Profiles")

        parent.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self)


        # connections for point tools
        self.point_sort_combobox.currentIndexChanged.connect(lambda: self.profiling.plot_profile_and_table())
        self.radius_line_edit.setValidator(QIntValidator())
        self.threshold_line_edit.setValidator(QIntValidator())

        # Recompute the interpolated profile (and its plot) whenever the
        # averaging radius or interpolation spacing changes, not just when
        # control points themselves are edited.
        self.radius_line_edit.editingFinished.connect(lambda: self.profiling._refresh_interpolation())
        self.spacing_line_edit.editingFinished.connect(lambda: self.profiling._refresh_interpolation())

        self.actionInterpolate.triggered.connect(
            lambda: self.profiling.interpolate_points(
                interpolation_distance=float(self.spacing_line_edit.value),
                radius=float(self.radius_line_edit.value)
            )
        )
        # update profile plot when point type is changed
        self.point_type_combobox.currentIndexChanged.connect(lambda: self.profiling.plot_profiles())
        # update profile plot when Num subplot is changed
        self.num_subplots_spinbox.valueChanged.connect(lambda: self.profiling.plot_profiles())
        self.num_subplots_spinbox.valueChanged.connect(self.update_profile_spinbox)
        self.selected_subplot_spinbox.valueChanged.connect(lambda: self.profiling.plot_profiles())

        # Connect the add and remove field buttons to methods
        self.comboBoxFieldType.activated.connect(lambda: self.update_field_combobox(self.comboBoxFieldType, self.comboBoxField))
        self.add_field_button.clicked.connect(lambda: self.profiling.add_field_to_listview())
        self.buttonRemoveField.clicked.connect(lambda: self.profiling.remove_field_from_listview())

        # Mutually-exclusive point-editing modes: checking one of these both starts
        # listening for clicks on the live map canvas and unchecks the others.
        self.actionControlPoints.triggered.connect(lambda: self._set_mode(self.actionControlPoints, 'create'))
        self.actionPointMove.triggered.connect(lambda: self._set_mode(self.actionPointMove, 'move'))
        self.actionPointAdd.triggered.connect(lambda: self._set_mode(self.actionPointAdd, 'add'))
        self.actionPointRemove.triggered.connect(lambda: self._set_mode(self.actionPointRemove, 'remove'))

        # Connect toolButtonProfilePointToggle's clicked signal to toggle point visibility
        self.actionEdit.triggered.connect(lambda: self.actionTogglePoint.setEnabled(self.actionEdit.isChecked()))
        self.actionEdit.setChecked(False)
        self.actionEdit.triggered.connect(lambda: self.profiling.toggle_edit_mode())
        self.actionTogglePoint.triggered.connect(lambda: self.profiling.toggle_point_visibility())

        self.profile_combobox.activated.connect(lambda: self.profiling.on_profile_selected(self.profile_combobox.currentText()))
        self.actionDeleteProfile.triggered.connect(lambda: self.profiling.delete_current_profile())
        self.actionExport.triggered.connect(lambda: self.profiling.save_current_profile())
        self.actionOpenProfile.triggered.connect(lambda: self.profiling.load_profiles_dialog())

        # Redraw the active profile's map overlay immediately if the user changes
        # the shared overlay color (Styling toolbox), rather than waiting for the
        # next point edit or replot to pick it up.
        self.main_window.style_data.overlayColorChanged.connect(lambda color: self.profiling.redraw_current_profile())

        self.visibilityChanged.connect(self.update_dock_visibility)

        self.toggle_profile_actions()

    @property
    def app_data(self):
        """Delegate to main_window.app_data so FieldLogicUI methods work correctly."""
        return self.main_window.app_data

    @property
    def data(self):
        """Access current sample data without caching a reference, so this always
        reflects whatever sample is currently selected."""
        if hasattr(self.main_window, 'app_data') and self.main_window.app_data.current_data:
            return self.main_window.app_data.current_data
        return None

    @data.setter
    def data(self, value):
        """Ignored -- data is always derived from main_window.app_data.current_data."""
        pass

    def _set_mode(self, action, mode):
        """Toggle one of the four mutually-exclusive point-editing modes.

        Checking one of ``actionControlPoints``/``actionPointMove``/``actionPointAdd``/
        ``actionPointRemove`` unchecks the others and arms click-handling on the live
        map canvas for that mode; unchecking disarms it.
        """
        checked = action.isChecked()
        for other in (self.actionControlPoints, self.actionPointMove, self.actionPointAdd, self.actionPointRemove):
            if other is not action:
                other.blockSignals(True)
                other.setChecked(False)
                other.blockSignals(False)

        self.main_window.reset_checked_items('profiling')

        canvas = getattr(self.main_window, 'mpl_canvas', None)
        if checked:
            if mode == 'create':
                was_field_map = (self.main_window.style_data.plot_type == 'field map')
                self.main_window.control_dock.comboBoxPlotType.setCurrentText('field map')
                self.profiling.on_profile_selected(self.profile_combobox.currentText())
                if was_field_map:
                    # Already on field map -- no replot was scheduled, canvas is current.
                    self.profiling.set_active_mode(mode, getattr(self.main_window, 'mpl_canvas', None))
                else:
                    # Switching plot types goes through the debounced Scheduler
                    # (~300ms); arm the click handler once the new canvas exists
                    # instead of grabbing a soon-to-be-replaced one.
                    QTimer.singleShot(350, lambda: self.profiling.set_active_mode(
                        mode, getattr(self.main_window, 'mpl_canvas', None)))
            else:
                self.profiling.set_active_mode(mode, canvas)
        else:
            self.profiling.set_active_mode(None, canvas)

    def update_dock_visibility(self, *args, **kwargs):
        if not self.profile_toggle.isChecked():
            return

        self.main_window.profile_state = False
        self.profile_toggle.setChecked(False)

        self.main_window.update_SV()

    def sync_field_combobox_to_map(self):
        """Set the Field Type/Field controls to match whatever is currently
        displayed on the map, so a user adding a field starts from a sensible
        default instead of a blank/first-item combobox state."""
        field_type = self.main_window.app_data.c_field_type
        field = self.main_window.app_data.c_field
        if not field_type or not field:
            return

        # comboBoxFieldType's items are populated lazily (only when its popup is
        # opened), so it must be explicitly populated before setCurrentText can
        # find a match -- otherwise it silently no-ops on the still-empty combobox.
        self.update_field_type_combobox(self.comboBoxFieldType)
        self.comboBoxFieldType.setCurrentText(field_type)
        self.update_field_combobox(self.comboBoxFieldType, self.comboBoxField)
        self.comboBoxField.setCurrentText(field)

    def toggle_profile_actions(self):
        if self.profile_toggle.isChecked():
            self.actionInterpolate.setEnabled(False)
            self.actionControlPoints.setEnabled(False)
            self.actionPointMove.setEnabled(False)
            self.actionPointAdd.setEnabled(False)
            self.actionPointRemove.setEnabled(False)
            self.actionEdit.setEnabled(False)
            self.actionTogglePoint.setEnabled(False)
        else:
            self.actionControlPoints.setEnabled(True)
            if not self.actionControlPoints.isChecked() and self.tableWidgetControlPoints.rowCount() > 1:
                self.actionInterpolate.setEnabled(True)
            else:
                self.actionInterpolate.setEnabled(False)

            if self.tableWidgetControlPoints.rowCount() > 0:
                if self.tableWidgetControlPoints.rowCount() > 1:
                    self.actionInterpolate.setEnabled(True)
                else:
                    self.actionInterpolate.setEnabled(False)
                self.actionPointMove.setEnabled(True)
                self.actionPointAdd.setEnabled(True)
                self.actionPointRemove.setEnabled(True)
                self.actionEdit.setEnabled(True)
                self.actionTogglePoint.setEnabled(True)
            else:
                self.actionInterpolate.setEnabled(False)
                self.actionPointMove.setEnabled(False)
                self.actionPointAdd.setEnabled(False)
                self.actionPointRemove.setEnabled(False)
                self.actionEdit.setEnabled(False)
                self.actionTogglePoint.setEnabled(False)

        # Save/delete apply to the profile as a whole (metadata + whatever
        # points it has so far), so they only depend on a profile being
        # actively viewed -- not on how many control points it has yet.
        has_profile = self.profiling.profile_name is not None
        self.actionExport.setEnabled(has_profile)
        self.actionDeleteProfile.setEnabled(has_profile)


    def update_profile_spinbox(self, *args, **kwargs):
        """Updates the maximum number of subplots that can be selected.

        Updates ``ProfileDock.selected_subplot_spinbox.setMaximum()``
        """
        n = self.num_subplots_spinbox.value()
        self.selected_subplot_spinbox.setMaximum(int(n))

    def profile_state_changed(self, *args, **kwargs):
        self.main_window.profile_state = self.profile_toggle.isChecked()
        if self.profile_toggle.isChecked():
            self.main_window.control_dock.update_plot_type_combobox_options()
            if hasattr(self.main_window, "mask_dock"):
                self.main_window.mask_dock.polygon_tab.polygon_toggle.setChecked(False)
                self.main_window.mask_dock.polygon_tab.toggle_polygon_actions()

        self.toggle_profile_actions()
        self.main_window.update_SV()

# Profiles
# -------------------------------
# The following class defines the metadata of a profile and its control points.
class Profile:
    """Holds data for one profile.

    Attributes
    ----------
    name : str
        Name given by the user for the profile.
    radius : float
        Radius used for averaging around each control point.
    sort : str
        Axis to sort points by ('no', 'x', 'y').
    y_axis_thresh : float
        Threshold used to clip the y-axis of the profile plot.
    int_dist : float
        Target spacing between interpolated points.
    point_type : str
        Statistic used to summarize points ('median + IQR', 'mean + stdev', 'mean + stderr').
    points : dict
        ``{'x': [...], 'y': [...], field_name: [[values within radius], ...]}`` -- each
        list is parallel/indexed the same as every other entry (one element per control point).
    i_points : dict
        Same shape as ``points``, but for the interpolated path.
    marker_artists, line_artist : matplotlib artist references
        Transient references to what's currently drawn on the live map canvas; never
        persisted (rebuilt fresh by ``Profiling._draw_profile`` whenever needed).
    """
    def __init__(self, name, radius=5.0, sort='no', y_axis_thresh=500.0, int_dist=50.0, point_type='median + IQR'):
        self.name = name
        self.radius = radius
        self.sort = sort
        self.y_axis_thresh = y_axis_thresh
        self.int_dist = int_dist
        self.point_type = point_type

        self.points = {}
        self.i_points = {}

        self.marker_artists = []
        self.line_artist = None


@auto_log_methods(logger_key='Profile')
class Profiling:
    """Manages multiple profiles for multiple samples.

    Control points are created/moved/added/removed by clicking directly on the live
    map canvas (``MainWindow.mpl_canvas``); since that canvas is a brand-new object on
    every replot, this class never assumes an artist survives a replot -- state lives
    in ``self.profiles`` and is redrawn on demand by ``plot_existing_profile``, mirroring
    ``src/common/Polygon.py``'s ``PolygonManager``.
    """
    def __init__(self, parent):
        self.profile_dock = parent
        self.main_window = parent.main_window

        self.profiles = {}  # {sample_id: {profile_name: Profile}}
        self.profile_name = None
        # Directory profiles were last saved to/loaded from (set by save/load,
        # including via LameIO's whole-project save/open) -- used to know
        # whether/where a profile has a corresponding *.prfl file on disk.
        self.project_dir = None

        # click-mode state
        self.active_mode = None  # 'create' | 'move' | 'add' | 'remove' | None
        self.canvas = None
        self.ax = None
        self.cid_click = None
        self.selected_point_idx = -1

        # profile line-chart state
        self.fig = None
        self.all_errorbars = []
        self.selected_points = {}
        self.edit_mode_enabled = False
        self.original_colors = {}
        self.fields_per_subplot = {}
        self.new_plot = False

    def add_samples(self):
        """Ensure every currently-loaded sample has an (initially empty) profile dict."""
        for sample_id in self.main_window.app_data.sample_list:
            if sample_id not in self.profiles:
                self.profiles[sample_id] = {}

    # -------------------------------------------------------------------------
    # Click-driven control point creation / editing (mirrors PolygonManager)
    # -------------------------------------------------------------------------
    def set_active_mode(self, mode, canvas):
        """Arm or disarm click-handling on ``canvas`` for the given mode.

        Parameters
        ----------
        mode : {'create', 'move', 'add', 'remove', None}
        canvas : MplCanvas or None
            The live map canvas. A new one is created on every replot, so this must
            be re-supplied by the caller each time a mode is (re)armed.
        """
        self.disconnect()
        self.selected_point_idx = -1
        self.active_mode = mode

        if mode is None or canvas is None:
            return

        self.canvas = canvas
        self.ax = canvas.axes
        if hasattr(canvas, 'disable_distance_mode'):
            canvas.disable_distance_mode()
        self.cid_click = canvas.mpl_connect('button_press_event', self.on_map_click)

    def disconnect(self):
        if self.canvas is not None and self.cid_click is not None:
            try:
                self.canvas.mpl_disconnect(self.cid_click)
            except Exception:
                pass
        self.cid_click = None

    def on_map_click(self, event):
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            return
        sample_id = self.main_window.app_data.sample_id
        if sample_id == '' or self.profile_name not in self.profiles.get(sample_id, {}):
            return

        if event.button != 1:
            return

        match self.active_mode:
            case 'create' | 'add':
                self._add_point(event.xdata, event.ydata)
            case 'move':
                self._handle_move_click(event)
            case 'remove':
                self._remove_nearest_point(event.xdata, event.ydata)

    def _current_profile(self):
        sample_id = self.main_window.app_data.sample_id
        if sample_id == '' or self.profile_name not in self.profiles.get(sample_id, {}):
            return None
        return self.profiles[sample_id][self.profile_name]

    def _add_point(self, x, y):
        profile = self._current_profile()
        if profile is None:
            return

        radius = float(self.profile_dock.radius_line_edit.value)
        x_i, y_i = int(round(x)), int(round(y))

        self.compute_profile_points(profile.points, radius, x, y, x_i, y_i)
        self._draw_profile(self.canvas, profile)
        self._refresh_interpolation()
        self.update_table_widget()
        self.profile_dock.toggle_profile_actions()

    def _remove_nearest_point(self, x, y):
        profile = self._current_profile()
        if profile is None:
            return

        idx = self._find_nearest_point_index(profile, x, y)
        if idx is None:
            return

        for key in list(profile.points.keys()):
            del profile.points[key][idx]

        self._draw_profile(self.canvas, profile)
        self._refresh_interpolation()
        self.update_table_widget()
        self.profile_dock.toggle_profile_actions()

    def _handle_move_click(self, event):
        profile = self._current_profile()
        if profile is None:
            return

        if self.selected_point_idx < 0:
            idx = self._find_nearest_point_index(profile, event.xdata, event.ydata, max_dist=10)
            if idx is not None:
                self.selected_point_idx = idx
            return

        idx = self.selected_point_idx
        self.selected_point_idx = -1

        radius = float(self.profile_dock.radius_line_edit.value)
        x_i, y_i = int(round(event.xdata)), int(round(event.ydata))
        self.compute_profile_points(profile.points, radius, event.xdata, event.ydata, x_i, y_i, point_index=idx)

        self._draw_profile(self.canvas, profile)
        self._refresh_interpolation()
        self.update_table_widget()

    def _find_nearest_point_index(self, profile, x, y, max_dist=None):
        xs = profile.points.get('x', [])
        ys = profile.points.get('y', [])
        if not xs:
            return None

        dist_sq = (np.array(xs) - x)**2 + (np.array(ys) - y)**2
        idx = int(np.argmin(dist_sq))
        if max_dist is not None and dist_sq[idx] > max_dist**2:
            return None
        return idx

    def _draw_profile(self, canvas, profile):
        """(Re)draw ``profile``'s control points and connecting line on ``canvas``."""
        if canvas is None:
            return
        ax = canvas.axes

        for artist in profile.marker_artists:
            try:
                artist.remove()
            except Exception:
                pass
        profile.marker_artists = []
        if profile.line_artist is not None:
            try:
                profile.line_artist.remove()
            except Exception:
                pass
            profile.line_artist = None

        overlay_color = self.main_window.style_data.overlay_color

        xs = profile.points.get('x', [])
        ys = profile.points.get('y', [])
        if xs:
            marker = ax.scatter(xs, ys, c=overlay_color, s=40, zorder=5)
            profile.marker_artists.append(marker)
        if len(xs) > 1:
            line, = ax.plot(xs, ys, color=overlay_color, linestyle='--', zorder=4)
            profile.line_artist = line

        canvas.draw_idle()

    def plot_existing_profile(self, canvas):
        """Redraw the active profile's points/line onto ``canvas`` -- called after a
        replot (new sample, new plot type, etc.) since matplotlib artists never
        survive a replot."""
        if canvas is None:
            return
        profile = self._current_profile()
        if profile is None:
            return
        self.canvas = canvas
        self.ax = canvas.axes
        self._draw_profile(canvas, profile)

    def redraw_current_profile(self):
        """Redraw the active profile on whatever canvas it's currently attached
        to, without changing any data -- used to pick up style changes (e.g. a
        new overlay color) immediately."""
        profile = self._current_profile()
        if profile is None or self.canvas is None:
            return
        self._draw_profile(self.canvas, profile)

    def clear_plot(self):
        """Remove all drawn profile artists for the current sample from the canvas."""
        sample_id = self.main_window.app_data.sample_id
        for profile in self.profiles.get(sample_id, {}).values():
            for artist in profile.marker_artists:
                try:
                    artist.remove()
                except Exception:
                    pass
            profile.marker_artists = []
            if profile.line_artist is not None:
                try:
                    profile.line_artist.remove()
                except Exception:
                    pass
                profile.line_artist = None
        if self.canvas is not None:
            self.canvas.draw_idle()

    # -------------------------------------------------------------------------
    # Radius-based averaging
    # -------------------------------------------------------------------------
    def compute_profile_points(self, profile_points, radius, x, y, x_i, y_i, point_index=None):
        """Compute profile points by averaging values within a radius.

        Calculates the mean values within a specified radius around a point and updates the profile points.

        Parameters
        ----------
        profile_points : dict
            Dictionary to store computed profile points, in format {'x': [], 'y':[], field: [circ_values]}
        radius : float
            The (physical) radius around the point to consider for averaging.
        x, y : float
            Coordinates of the point, stored as-is in ``profile_points`` (pixel-index
            space, matching the map canvas' coordinate system).
        x_i, y_i : int
            Pixel-index coordinates of the point, used to index the field arrays.
        point_index : int, optional
            The index of the point if updating an existing point (insert-at-index
            rather than append).

        Returns
        -------
        None
        """
        data = self.main_window.app_data.current_data
        if data is None:
            return

        array_y, array_x = data.array_size

        # Obtain field data of all fields that will be used for profiling
        fields = (
            data.processed.match_attribute('data_type', 'Analyte') +
            data.processed.match_attribute('data_type', 'Ratio')
        )
        field_data = data.processed[fields]

        # If updating an existing point, remove it first
        if point_index is not None:
            for key in profile_points.keys():
                del profile_points[key][point_index]

        # Physical size per pixel in x and y directions, used to convert the
        # physical radius entered by the user into a pixel radius.
        dx = data.dx
        dy = data.dy
        p_radius_y = int(round(radius / dy)) if dy else int(round(radius))
        p_radius_x = int(round(radius / dx)) if dx else int(round(radius))

        # Get the ranges of indices in i and j directions
        i_min = max(0, y_i - p_radius_y)
        i_max = min(array_y, y_i + p_radius_y + 1)
        j_min = max(0, x_i - p_radius_x)
        j_max = min(array_x, x_i + p_radius_x + 1)

        i_range = np.arange(i_min, i_max)
        j_range = np.arange(j_min, j_max)

        I_grid, J_grid = np.meshgrid(i_range, j_range, indexing='ij')

        di_phys = (I_grid - y_i) * dy
        dj_phys = (J_grid - x_i) * dx
        dists_squared = di_phys**2 + dj_phys**2

        mask = dists_squared <= radius**2

        i_indices = I_grid[mask]
        j_indices = J_grid[mask]

        for field in field_data.columns:
            array = np.reshape(field_data[field].values, data.array_size, order=data.order)
            values = array[i_indices, j_indices]
            circ_values = values.tolist()

            if field in profile_points:
                if point_index is not None:
                    profile_points[field].insert(point_index, circ_values)
                else:
                    profile_points[field].append(circ_values)
            else:
                profile_points[field] = [circ_values]

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

    # -------------------------------------------------------------------------
    # Profile management
    # -------------------------------------------------------------------------
    def populate_combobox(self):
        """Populate the profile selection combobox."""
        sample_id = self.main_window.app_data.sample_id
        self.profiles.setdefault(sample_id, {})

        self.profile_dock.profile_combobox.clear()
        self.profile_dock.profile_combobox.addItem('Create New Profile')
        for profile_name in self.profiles[sample_id].keys():
            self.profile_dock.profile_combobox.addItem(profile_name)

        self.new_plot = True

    def on_profile_selected(self, profile_name):
        """Handle profile selection from the combobox: load an existing profile or
        prompt for a name and start a new one."""
        sample_id = self.main_window.app_data.sample_id
        if sample_id == '':
            return
        self.profiles.setdefault(sample_id, {})
        self.new_plot = True

        if profile_name == 'Create New Profile' or not profile_name:
            new_profile_name, ok = QInputDialog.getText(self.profile_dock, 'New Profile', 'Enter new profile name:')
            if ok and new_profile_name:
                if new_profile_name in self.profiles[sample_id]:
                    QMessageBox.warning(self.profile_dock, 'Error', 'Profile name already exists!')
                    return

                self.clear_profiles()
                sort = self.profile_dock.point_sort_combobox.currentText()
                radius = float(self.profile_dock.radius_line_edit.value)
                thresh = float(self.profile_dock.threshold_line_edit.value)
                int_dist = float(self.profile_dock.spacing_line_edit.value)
                point_type = self.profile_dock.point_type_combobox.currentText()

                self.profiles[sample_id][new_profile_name] = Profile(new_profile_name, radius, sort, thresh, int_dist, point_type)
                if self.profile_dock.profile_combobox.findText(new_profile_name) < 0:
                    self.profile_dock.profile_combobox.addItem(new_profile_name)
                self.profile_dock.profile_combobox.setCurrentText(new_profile_name)
                self.profile_name = new_profile_name

                # Seed subplot 1 with whatever field is currently displayed on the
                # map, so the user isn't required to re-pick it right after
                # creating a profile -- more fields can still be added/removed
                # via the Field Type/Field controls afterward.
                current_field = self.main_window.app_data.c_field
                if current_field:
                    self.add_field_to_listview(current_field, update=False)
            else:
                self.profile_dock.profile_combobox.setCurrentIndex(0)
        else:
            if profile_name != self.profile_name:
                self.clear_profiles()
                self.profile_name = profile_name
                profile = self.profiles[sample_id][profile_name]
                self.profile_dock.point_sort_combobox.setCurrentText(profile.sort)
                self.profile_dock.radius_line_edit.value = profile.radius
                self.profile_dock.threshold_line_edit.value = profile.y_axis_thresh
                self.profile_dock.spacing_line_edit.value = profile.int_dist
                self.profile_dock.point_type_combobox.setCurrentText(profile.point_type)

                canvas = getattr(self.main_window, 'mpl_canvas', None)
                self.plot_existing_profile(canvas)
                self.plot_profiles()
                self.update_table_widget()
        self.profile_dock.toggle_profile_actions()

    def delete_current_profile(self):
        """Delete the currently-viewed profile, after confirmation.

        Removes the profile's ``*.prfl`` file too, if it was ever saved to
        disk (``self.project_dir`` is known and the file exists there);
        otherwise the profile only ever existed in memory and is just cleared.
        """
        sample_id = self.main_window.app_data.sample_id
        profile_name = self.profile_name
        if sample_id == '' or profile_name not in self.profiles.get(sample_id, {}):
            return

        response = QMessageBox.question(
            self.profile_dock,
            'Delete Profile',
            f"Delete profile '{profile_name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        if response != QMessageBox.StandardButton.Yes:
            return

        if self.project_dir is not None:
            file_path = os.path.join(self.project_dir, sample_id, f'{profile_name}.prfl')
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError as e:
                    QMessageBox.warning(self.profile_dock, 'Error', f"Could not remove saved profile file: {e}")

        # clear_profiles() resets self.profile_name -- read/delete from the
        # dict using the name captured above, not self.profile_name.
        self.clear_profiles()
        del self.profiles[sample_id][profile_name]
        idx = self.profile_dock.profile_combobox.findText(profile_name)
        if idx >= 0:
            self.profile_dock.profile_combobox.removeItem(idx)
        self.profile_dock.profile_combobox.setCurrentIndex(0)
        self.profile_dock.toggle_profile_actions()

    def clear_profiles(self):
        """Clear profile plots/table/listview for the active profile (data in
        ``self.profiles`` is untouched -- this only clears what's displayed)."""
        sample_id = self.main_window.app_data.sample_id
        if sample_id == '':
            return

        self.clear_plot()
        self.set_active_mode(None, self.canvas)

        self.profile_dock.tableWidgetControlPoints.clearContents()
        self.profile_dock.tableWidgetControlPoints.setRowCount(0)

        layout = self.profile_dock.widgetProfilePlot.layout()
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        model = self.profile_dock.listViewProfile.model()
        if model:
            model.clear()

        self.selected_point_idx = -1
        self.all_errorbars = []
        self.selected_points = {}
        self.edit_mode_enabled = False
        self.original_colors = {}
        self.profile_name = None
        self.fields_per_subplot = {}
        self.new_plot = False

        self.profile_dock.actionControlPoints.setChecked(False)
        self.profile_dock.actionPointMove.setChecked(False)
        self.profile_dock.actionPointAdd.setChecked(False)
        self.profile_dock.actionPointRemove.setChecked(False)

        self.profile_dock.num_subplots_spinbox.blockSignals(True)
        self.profile_dock.selected_subplot_spinbox.blockSignals(True)
        self.profile_dock.num_subplots_spinbox.setValue(1)
        self.profile_dock.selected_subplot_spinbox.setValue(1)
        self.profile_dock.num_subplots_spinbox.blockSignals(False)
        self.profile_dock.selected_subplot_spinbox.blockSignals(False)

        self.profile_dock.toggle_profile_actions()

    # -------------------------------------------------------------------------
    # Interpolation
    # -------------------------------------------------------------------------
    def _refresh_interpolation(self):
        """Recompute the interpolated path for the active profile using the
        current radius/spacing options. Called automatically whenever control
        points are added, moved, or removed, so the displayed profile always
        reflects the current point geometry -- ``actionInterpolate`` remains
        available to force a refresh after only the radius/spacing values change."""
        radius = float(self.profile_dock.radius_line_edit.value)
        spacing = float(self.profile_dock.spacing_line_edit.value)
        self.interpolate_points(interpolation_distance=spacing, radius=radius)

    def interpolate_points(self, interpolation_distance, radius):
        """(Re)compute the interpolated path between the active profile's
        control points, sampling every ``interpolation_distance`` units with
        ``radius``-based averaging. This is the data ``plot_profiles`` displays."""
        profile = self._current_profile()
        if profile is None:
            return

        profile_points = profile.points
        x_coords = profile_points.get('x', [])

        if len(x_coords) < 2 or interpolation_distance <= 0:
            profile.i_points = {}
            self.plot_profiles()
            return

        point_coordinates = list(zip(x_coords, profile_points['y']))
        fields = [field for field in profile_points.keys() if field not in {'x', 'y'}]

        i_profile_points = {'x': [], 'y': []}
        for field in fields:
            i_profile_points[field] = []

        for i in range(len(point_coordinates) - 1):
            start_point = point_coordinates[i]
            end_point = point_coordinates[i + 1]

            i_profile_points['x'].append(start_point[0])
            i_profile_points['y'].append(start_point[1])
            for field in fields:
                i_profile_points[field].append(profile_points[field][i])

            dist = self.calculate_distance(start_point, end_point)
            if dist == 0:
                continue

            num_interpolations = max(int(dist / interpolation_distance), 0)

            dx = (end_point[0] - start_point[0]) / dist
            dy = (end_point[1] - start_point[1]) / dist

            for t in range(1, num_interpolations + 1):
                x = start_point[0] + t * interpolation_distance * dx
                y = start_point[1] + t * interpolation_distance * dy
                x_i, y_i = int(round(x)), int(round(y))

                self.compute_profile_points(i_profile_points, radius, x, y, x_i, y_i)

        end_point = point_coordinates[-1]
        i_profile_points['x'].append(end_point[0])
        i_profile_points['y'].append(end_point[1])
        for field in fields:
            i_profile_points[field].append(profile_points[field][-1])

        profile.i_points = i_profile_points
        self.plot_profiles()

    def calculate_distance(self, point1, point2):
        """Euclidean distance between two (x, y) points."""
        return np.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)

    # -------------------------------------------------------------------------
    # Profile line-chart plotting
    # -------------------------------------------------------------------------
    def plot_profiles(self, fields=None, num_subplots=None, selected_subplot=None, interpolate=None, sort_axis=None, *args, **kwargs):
        """Plot averaged profile values with error bars.

        Plots the profile values stored in the active profile with error bars on the
        specified subplot(s), using fields assigned to each subplot stored in
        ``self.fields_per_subplot``. Uses the interpolated path (``profile.i_points``)
        whenever it's available (kept fresh automatically as control points change),
        falling back to the raw control points otherwise.
        """
        profile = self._current_profile()
        if profile is None:
            return

        if interpolate is None:
            interpolate = bool(profile.i_points.get('x'))
        if num_subplots is None:
            num_subplots = self.profile_dock.num_subplots_spinbox.value()
        if selected_subplot is None:
            selected_subplot = self.profile_dock.selected_subplot_spinbox.value()

        for i in range(num_subplots):
            if i not in self.fields_per_subplot:
                self.fields_per_subplot[i] = []

        point_type_text = self.profile_dock.point_type_combobox.currentText()
        # 'median + IQR' -> median point, IQR error bars
        # 'mean + stdev'  -> mean point, standard-deviation error bars
        # 'mean + stderr' -> mean point, standard-error error bars
        point_type = {'median + IQR': 'median', 'mean + stdev': 'stdev', 'mean + stderr': 'stderr'}.get(point_type_text, 'stderr')

        if sort_axis is None:
            sort_axis = self.profile_dock.point_sort_combobox.currentText().lower()

        profile_points = profile.i_points if interpolate else profile.points
        if not profile_points.get('x'):
            return

        style = self.main_window.style_data
        cmap = style.get_colormap()

        layout = self.profile_dock.widgetProfilePlot.layout()
        if layout is not None:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        self.fig = Figure()
        self.fig.canvas.mpl_connect('pick_event', self.on_pick)

        self.all_errorbars = []
        if num_subplots < 1:
            num_subplots = 1

        axes = []
        for i in range(num_subplots):
            ax = self.fig.add_subplot(num_subplots, 1, i + 1)
            axes.append(ax)

        for subplot_idx, ax in enumerate(axes):
            fields_in_subplot = self.fields_per_subplot.get(subplot_idx, [])
            if subplot_idx == selected_subplot - 1:
                self.update_listview_with_fields(fields_in_subplot)
            if not fields_in_subplot:
                continue

            for field_idx, field in enumerate(fields_in_subplot):
                if field not in profile_points:
                    continue
                circ_val = profile_points[field]
                x = profile_points['x']
                y = profile_points['y']
                distances, medians, lowers, uppers, means, stds, s_errors = self.process_points(x, y, circ_val, sort_axis)

                color = cmap(field_idx / max(len(fields_in_subplot), 1))

                if point_type == 'median':
                    points = medians
                    errors = [[median - lower for median, lower in zip(medians, lowers)],
                            [upper - median for upper, median in zip(uppers, medians)]]
                elif point_type == 'stdev':
                    points = means
                    errors = stds
                else:  # 'stderr'
                    points = means
                    errors = s_errors

                scatter = ax.scatter(distances, points,
                                    color=color,
                                    s=style.marker_size,
                                    marker=style.marker_dict[style.marker],
                                    edgecolors='none',
                                    picker=5,
                                    gid=field,
                                    label=field)
                _, _, barlinecols = ax.errorbar(distances, points,
                                                yerr=errors,
                                                fmt='none',
                                                color=color,
                                                ecolor=style.line_color,
                                                elinewidth=style.line_width,
                                                capsize=0)
                self.all_errorbars.append((scatter, barlinecols[0]))
                self.original_colors[field] = color
                self.selected_points[field] = [False] * len(points)

            if subplot_idx == num_subplots - 1:
                ax.set_xlabel('Distance')
            else:
                ax.xaxis.set_visible(False)
            ax.set_ylabel('Value')
            ax.legend()

        self.fig.tight_layout(pad=3, w_pad=0, h_pad=0)
        self.fig.subplots_adjust(wspace=0, hspace=0)

        canvas = FigureCanvas(self.fig)
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(canvas)
        widget.setLayout(layout)

        self.profile_dock.widgetProfilePlot.layout().addWidget(widget)
        widget.show()

    def process_points(self, x, y, circ_values, sort_axis):
        """Process profile points to compute statistics and distances.

        Parameters
        ----------
        x, y : list of float
            Coordinates of the control points.
        circ_values : list of lists
            One list of values within the radius per control point.
        sort_axis : str
            Axis to sort the points by ('x' or 'y').

        Returns
        -------
        distances, median_values, lower_quantiles, upper_quantiles, mean_values, std_values, standard_errors
        """
        combined = list(zip(x, y, circ_values))

        if sort_axis == 'x':
            combined.sort(key=lambda p: p[0])
        elif sort_axis == 'y':
            combined.sort(key=lambda p: p[1])

        x_sorted, y_sorted, circ_values_sorted = zip(*combined)

        median_values = []
        lower_quantiles = []
        upper_quantiles = []
        mean_values = []
        std_values = []
        standard_errors = []
        distances = []

        for i, values in enumerate(circ_values_sorted):
            if len(values) == 0:
                median = lower = upper = mean = std = std_err = np.nan
            else:
                median = np.median(values)
                lower = np.quantile(values, 0.25)
                upper = np.quantile(values, 0.75)
                mean = np.mean(values)
                std = np.std(values, ddof=1) if len(values) > 1 else 0.0
                std_err = std / np.sqrt(len(values)) if len(values) > 1 else 0.0

            median_values.append(median)
            lower_quantiles.append(lower)
            upper_quantiles.append(upper)
            mean_values.append(mean)
            std_values.append(std)
            standard_errors.append(std_err)

            if i == 0:
                distances.append(0)
            else:
                dist = self.calculate_distance(
                    (x_sorted[i], y_sorted[i]),
                    (x_sorted[i - 1], y_sorted[i - 1])
                )
                distances.append(distances[-1] + dist)

        return distances, median_values, lower_quantiles, upper_quantiles, mean_values, std_values, standard_errors

    # -------------------------------------------------------------------------
    # Save / Load (.prfl)
    # -------------------------------------------------------------------------
    def save_profiles(self, project_dir, sample_id):
        """Save profiles for a sample to ``*.prfl`` files (pickled plain data --
        matplotlib artists are transient and never serialized)."""
        if sample_id not in self.profiles:
            return
        os.makedirs(os.path.join(project_dir, sample_id), exist_ok=True)
        for profile_name, profile in self.profiles[sample_id].items():
            file_name = os.path.join(project_dir, sample_id, f'{profile_name}.prfl')
            data = {
                'name': profile.name,
                'radius': profile.radius,
                'sort': profile.sort,
                'y_axis_thresh': profile.y_axis_thresh,
                'int_dist': profile.int_dist,
                'point_type': profile.point_type,
                'points': profile.points,
                'i_points': profile.i_points,
            }
            with open(file_name, 'wb') as file:
                pickle.dump(data, file)
        print("Profile saved successfully.")

    def load_profiles(self, project_dir, sample_id):
        """Load saved profiles from ``*.prfl`` files."""
        directory = os.path.join(project_dir, sample_id)
        if not os.path.isdir(directory):
            return
        self.profiles.setdefault(sample_id, {})
        for file_name in os.listdir(directory):
            if file_name.endswith(".prfl"):
                file_path = os.path.join(directory, file_name)
                with open(file_path, 'rb') as file:
                    data = pickle.load(file)
                profile = Profile(
                    data['name'], data['radius'], data['sort'],
                    data['y_axis_thresh'], data['int_dist'], data['point_type']
                )
                profile.points = data['points']
                profile.i_points = data.get('i_points', {})
                self.profiles[sample_id][data['name']] = profile
        self.populate_combobox()
        print("All profiles loaded successfully.")

    def save_current_profile(self):
        """UI-facing save: writes all of the current sample's profiles to
        ``self.project_dir`` (prompting for a directory the first time)."""
        sample_id = self.main_window.app_data.sample_id
        if sample_id == '' or self.profile_name is None:
            return

        if self.project_dir is None:
            projects_dir = BASEDIR / "projects"
            projects_dir.mkdir(parents=True, exist_ok=True)
            selected = QFileDialog.getExistingDirectory(
                self.profile_dock, "Save Profile To", str(projects_dir)
            )
            if not selected:
                return
            self.project_dir = selected

        self.save_profiles(self.project_dir, sample_id)
        self.main_window.io.status_manager.show_message(f"Profile '{self.profile_name}' saved.")

    def load_profiles_dialog(self):
        """UI-facing load: prompts for a project directory and loads profiles
        for the current sample from it."""
        sample_id = self.main_window.app_data.sample_id
        if sample_id == '':
            return

        projects_dir = BASEDIR / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)
        selected = QFileDialog.getExistingDirectory(
            self.profile_dock, "Load Profiles From", str(projects_dir)
        )
        if not selected:
            return

        self.project_dir = selected
        self.add_samples()
        self.load_profiles(self.project_dir, sample_id)
        self.profile_dock.toggle_profile_actions()

    # -------------------------------------------------------------------------
    # Point selection / visibility (operates on artists created by plot_profiles)
    # -------------------------------------------------------------------------
    def on_pick(self, event):
        """Handle pick events on the profile plot, toggling point selection."""
        style = self.main_window.style_data

        if self.edit_mode_enabled and isinstance(event.artist, PathCollection):
            picked_scatter = event.artist
            ind = event.ind[0]
            field = picked_scatter.get_gid()
            facecolors = picked_scatter.get_facecolors().copy()
            original_color = colors.to_rgba(self.original_colors[field])

            self.selected_points[field][ind] = not self.selected_points[field][ind]

            num_points = len(picked_scatter.get_offsets())
            if len(facecolors) == 1 and num_points > 1:
                facecolors = np.tile(facecolors, (num_points, 1))

            if not self.selected_points[field][ind]:
                facecolors[ind] = colors.to_rgba(original_color)
            else:
                facecolors[ind] = (0.75, 0.75, 0.75, 1)

            picked_scatter.set_facecolors(facecolors)
            picked_scatter.set_sizes(np.full(num_points, style.marker_size))
            self.fig.canvas.draw_idle()

    def toggle_edit_mode(self):
        """Toggle the profile editing mode (used to select/hide points on the chart)."""
        self.edit_mode_enabled = not self.edit_mode_enabled

        for field in self.selected_points.keys():
            scatter, barlinecol = self.get_scatter_errorbar_by_gid(field)
            if scatter is None:
                continue

            facecolors = scatter.get_facecolors().copy()
            num_points = len(scatter.get_offsets())
            if len(facecolors) == 1 and num_points > 1:
                facecolors = np.tile(facecolors, (num_points, 1))

            line_colors = barlinecol.get_colors().copy()
            if len(line_colors) == 1 and len(barlinecol.get_segments()) > 1:
                line_colors = np.tile(line_colors, (num_points, 1))

            for idx, selected in enumerate(self.selected_points[field]):
                if selected:
                    new_alpha = 0.0 if facecolors[idx][-1] > 0 else 1.0
                    line_colors[idx][-1] = new_alpha
                    facecolors[idx][-1] = new_alpha
            barlinecol.set_colors(line_colors)
            scatter.set_facecolors(facecolors)
        if self.fig is not None:
            self.fig.canvas.draw_idle()

    def toggle_point_visibility(self):
        """Hide or show selected profile points on the plot without removing them."""
        for field in self.selected_points.keys():
            scatter, barlinecol = self.get_scatter_errorbar_by_gid(field)
            if scatter is None:
                continue

            facecolors = scatter.get_facecolors().copy()
            num_points = len(scatter.get_offsets())
            if len(facecolors) == 1 and num_points > 1:
                facecolors = np.tile(facecolors, (num_points, 1))

            line_colors = barlinecol.get_colors().copy()
            if len(line_colors) == 1 and len(barlinecol.get_segments()) > 1:
                line_colors = np.tile(line_colors, (num_points, 1))

            for idx, selected in enumerate(self.selected_points[field]):
                if selected:
                    new_alpha = 0.0 if facecolors[idx][-1] > 0 else 1.0
                    line_colors[idx][-1] = new_alpha
                    facecolors[idx][-1] = new_alpha
            barlinecol.set_colors(line_colors)
            scatter.set_facecolors(facecolors)
        if self.fig is not None:
            self.fig.canvas.draw_idle()

    def get_scatter_errorbar_by_gid(self, gid):
        """Retrieve the (scatter, errorbar) pair for a given field (group id)."""
        for (scatter, errorbars) in self.all_errorbars:
            if scatter.get_gid() == gid:
                return (scatter, errorbars)
        return None, None

    # -------------------------------------------------------------------------
    # Field <-> subplot assignment
    # -------------------------------------------------------------------------
    def add_field_to_listview(self, field=None, update=True, *args, **kwargs):
        """Add selected fields to the profile list view and update the fields per subplot."""
        selected_subplot = self.profile_dock.selected_subplot_spinbox.value() - 1

        if not field:
            field = self.profile_dock.comboBoxField.currentText()
        if not field:
            QMessageBox.warning(self.profile_dock, 'No Fields', 'There are no available fields to add.')
            return

        if selected_subplot not in self.fields_per_subplot:
            self.fields_per_subplot[selected_subplot] = []

        if field not in self.fields_per_subplot[selected_subplot]:
            self.fields_per_subplot[selected_subplot].append(field)
            self.update_listview_with_fields(self.fields_per_subplot[selected_subplot])
            if update:
                self.plot_profiles()
        else:
            QMessageBox.information(self.profile_dock, 'Field Exists', f'The field "{field}" is already in the list.')

    def remove_field_from_listview(self):
        """Remove selected fields from the profile list view and update the fields per subplot."""
        selected_subplot = self.profile_dock.selected_subplot_spinbox.value() - 1

        selection_model = self.profile_dock.listViewProfile.selectionModel()
        indexes = selection_model.selectedIndexes()

        if not indexes:
            QMessageBox.warning(self.profile_dock, 'No Selection', 'Please select a field to remove.')
            return

        model = self.profile_dock.listViewProfile.model()
        fields_removed = []
        for index in sorted(indexes, reverse=True):
            field = model.item(index.row()).text()
            fields_removed.append(field)
            model.removeRow(index.row())

        for field in fields_removed:
            if field in self.fields_per_subplot.get(selected_subplot, []):
                self.fields_per_subplot[selected_subplot].remove(field)

        self.plot_profiles()

    def update_num_subplots(self):
        num_subplots = self.profile_dock.num_subplots_spinbox.value()
        existing_subplots = list(self.fields_per_subplot.keys())
        if num_subplots < len(existing_subplots):
            for idx in existing_subplots:
                if idx >= num_subplots:
                    del self.fields_per_subplot[idx]
        elif num_subplots > len(existing_subplots):
            for idx in range(len(existing_subplots), num_subplots):
                self.fields_per_subplot[idx] = []

        selected_subplot = self.profile_dock.selected_subplot_spinbox.value()
        if selected_subplot > num_subplots:
            self.profile_dock.selected_subplot_spinbox.setValue(num_subplots)

        self.plot_profiles()

    def update_listview_with_fields(self, fields):
        """Update the list view with the given list of fields."""
        model = self.profile_dock.listViewProfile.model()
        if not model:
            model = QStandardItemModel()
            self.profile_dock.listViewProfile.setModel(model)
        else:
            model.clear()

        for field in fields:
            item = QStandardItem(field)
            model.appendRow(item)

    def plot_profile_and_table(self):
        self.plot_profiles()
        self.update_table_widget()

    def update_table_widget(self, update=False):
        """Refresh the control-points table to match the active profile's points."""
        profile = self._current_profile()
        table = self.profile_dock.tableWidgetControlPoints
        table.setRowCount(0)
        if profile is None:
            return

        x_coords = profile.points.get('x', [])
        y_coords = profile.points.get('y', [])

        for idx, (x, y) in enumerate(zip(x_coords, y_coords)):
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(str(idx)))
            table.setItem(row, 1, QTableWidgetItem(str(round(x))))
            table.setItem(row, 2, QTableWidgetItem(str(round(y))))
            table.setRowHeight(row, 20)
