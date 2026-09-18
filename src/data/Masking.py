from __future__ import annotations
import os
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.app.MainWindow import MainWindow
from PyQt6.QtCore import Qt, QSize, QEvent, pyqtSignal
from PyQt6.QtGui import (
    QStandardItem, QStandardItemModel, QIcon, QFont, QIntValidator, QAction
)
from PyQt6.QtWidgets import (
        QMessageBox, QToolButton, QWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QGroupBox, QInputDialog,
        QDoubleSpinBox, QComboBox, QCheckBox, QSizePolicy, QListView, QToolBar, QAbstractItemView, QMenu,
        QLabel, QHeaderView, QTableWidget, QScrollArea, QMainWindow, QWidgetAction, QTabWidget, QDockWidget, QGridLayout,
        QSpacerItem, QFrame,
    )
from lame_core.CustomWidgets import (
    CustomDockWidget, CustomTableWidget, CustomLineEdit, CustomComboBox, ToggleSwitch, CustomToolButton, CustomAction
)
from blueberry.ColorButton import ColorButton
from src.control.FieldLogic import FieldLogicUI
# from pyqtgraph import ( ScatterPlotItem )
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.colors as colors
from matplotlib.collections import PathCollection
import numpy as np
import pandas as pd
from scipy.stats import percentileofscore

from lame_core.UITheme import default_font
from lame_core.config import BASEDIR, ICONPATH
# Removed deprecated imports: get_hex_color, get_rgb_color - now using ColorManager
from lame_core.ColorManager import convert_color

from src.common.TableFunctions import TableFcn as TableFcn
from src.app.CustomTableWidget import ReorderableTableWidget, compute_row_reorder
import lame_core.format as fmt
from src.data.Polygon import PolygonManager
from src.data.polygon_mask import polygon_mask
from src.data.cluster_groups import (
    cluster_groups, expand_to_groups, group_index, group_of,
    link_clusters, unlink_clusters,
)
from src.control.Logger import LoggerConfig, auto_log_methods, log

# Mask object
# -------------------------------
class MaskObj:
    def __init__(self, initial_value=None):
        self._value = initial_value
        self._callbacks = []

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        old_value = self._value
        self._value = new_value 
        self._notify_observers(old_value, new_value)

    def _notify_observers(self, old_value, new_value):
        for callback in self._callbacks:
            callback(old_value, new_value)
    
    def register_callback(self, callback):
        self._callbacks.append(callback)


# remove lines from approx 1980 to 2609 in MainWindow.py (Masking Toolbox dockWidgetMaskToolbox) when complete
@auto_log_methods(logger_key='Mask')
class MaskDock(CustomDockWidget, FieldLogicUI):
    def __init__(self, ui: MainWindow | None = None, title: str = "Masking Toolbox"):
        self.logger_key = 'Mask'

        if not isinstance(ui, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        super().__init__(ui)
        self.ui: MainWindow | None = ui

        self.setObjectName("Mask Dock")
        self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.setFloating(False)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)

        if self.ui is not None:
            self.ui.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self)

        #self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        # Keep the minimum small: the central CanvasWidget sits directly above
        # this dock, so their minimum heights add up. A tall minimum here forced
        # QMainWindow to grow (and then refuse to shrink), or squished the canvas
        # toolbar when the window was already screen-height. The contents scroll
        # (see the QScrollArea below) instead of imposing their own minimum.
        self.setMinimumSize(QSize(400, 150))
        self.setMaximumSize(QSize(524287, 524287))
        self.setFloating(False)
        # Closable in addition to floatable -- the status bar's 'BottomDock'
        # toggle button (see MainWindow.open_mask_dock) already hides/shows
        # this dock, but a native title-bar close button is a more
        # discoverable way to do the same thing. Both stay in sync via
        # visibilityChanged (see open_mask_dock), since either one can
        # trigger a hide.
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetClosable)

        # create a container to hold the dock contents
        container = QWidget()
        container.setObjectName("Mask Dock Container")
        dock_layout = QVBoxLayout(container)

        # create common toolbar
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setMovable(False)
        dock_layout.addWidget(self.toolbar)

        # create a tab widget
        self.tab_widgets = QTabWidget(container)
        self.tab_widgets.setObjectName("Mask Tab Widget")

        self.filter_tab = FilterTab(self)
        self.polygon_tab = PolygonTab(self)
        self.cluster_tab = ClusterTab(self)

        dock_layout.addWidget(self.tab_widgets)

        # scroll rather than enforce the contents' minimum height on the dock
        scroll_area = QScrollArea()
        scroll_area.setObjectName("Mask Dock Scroll Area")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(container)
        self.setWidget(scroll_area)
        self._scroll_area = scroll_area
        self._container = container

        # Connect tab change signal to update toolbar visibility
        self.tab_widgets.currentChanged.connect(self.update_toolbar_for_tab)
        self.visibilityChanged.connect(self.update_tab_widget)
        
        # Initialize toolbar for the first tab
        self.update_toolbar_for_tab(0)

    def fit_to_contents(self, max_fraction: float = 0.6):
        """Grow the dock so its contents fit without scrolling, if there is room.

        The dock keeps a small minimum height (the contents scroll) so that the
        central canvas can always shrink, but that also means the dock opens at
        a height smaller than the tabs need. This resizes it once to the
        contents' preferred height, leaving the rest of the window to the
        canvas.

        Parameters
        ----------
        max_fraction : float, optional
            Largest share of the canvas+dock vertical space the dock may
            take, by default 0.6.
        """
        if self.ui is None or not self.isVisible() or self.isFloating():
            return

        # scroll area chrome (frame + horizontal scrollbar, if any)
        chrome = self._scroll_area.height() - self._scroll_area.viewport().height()
        wanted = self._container.sizeHint().height() + chrome
        wanted += self.height() - self._scroll_area.height()  # dock title bar

        # only the canvas and this dock share the vertical space
        canvas = getattr(self.ui, 'canvas_widget', None)
        available = (canvas.height() + self.height()) if canvas is not None else self.ui.height()
        limit = int(available * max_fraction)
        target = max(self.minimumSizeHint().height(), min(wanted, limit))
        if target > self.height():
            self.ui.resizeDocks([self], [target], Qt.Orientation.Vertical)


    @property
    def app_data(self):
        """Delegate to ui.app_data so FieldLogicUI methods work correctly"""
        return self.ui.app_data

    @property
    def data(self):
        """Access current data without storing reference to avoid circular dependency"""
        if hasattr(self.ui, 'app_data') and self.ui.app_data.current_data:
            return self.ui.app_data.current_data
        return None

    @data.setter
    def data(self, value):
        """Ignored — data is always derived from self.ui.app_data.current_data"""
        pass

    def update_toolbar_for_tab(self, index):
        """Update toolbar to show only actions relevant to the current tab"""
        # Clear toolbar
        self.toolbar.clear()
        
        # Add actions based on the current tab
        if index == 0:  # Filter tab
            self.filter_tab.setup_toolbar_actions(self.toolbar)
        elif index == 1:  # Polygon tab
            self.polygon_tab.setup_toolbar_actions(self.toolbar)
        elif index == 2:  # Cluster tab
            self.cluster_tab.setup_toolbar_actions(self.toolbar)

    def update_tab_widget(self, *args, **kwargs):
        if not self.isVisible():
            return

        self.filter_tab.update_filter_values()

    def apply_theme(self, theme):
        """Apply theme to MaskDock and all its components"""
        log(f"MaskDock.apply_theme called with theme: {theme}", prefix="Style")
        
        # Define theme-specific styles for QGroupBox
        if theme == "dark":
            groupbox_style = """
            QGroupBox {
                border: none;
                border-radius: 3px;
                background-color: #282828;
                font: 10px;
                margin-top: 15px;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left; 
                padding: 0 3px;
                color: #ffffff;
            }
            """
        else:  # light theme
            groupbox_style = """
            QGroupBox {
                border: none;
                border-radius: 3px;
                background-color: #e0e0e0;
                font: 10px;
                margin-top: 15px;
                color: #000000;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left; 
                padding: 0 3px;
                color: #000000;
            }
            """
        
        # Apply to all QGroupBox widgets in this dock
        for groupbox in self.findChildren(QGroupBox):
            log(f"Applying style to QGroupBox: {groupbox.objectName()}", prefix="Style")
            groupbox.setStyleSheet(groupbox_style)
            # Force style refresh safely
            if groupbox.style():
                groupbox.style().unpolish(groupbox)
                groupbox.style().polish(groupbox)
            groupbox.update()
        
        # Also apply specifically to filter_tools_groupbox if it exists
        if hasattr(self.filter_tab, 'filter_tools_groupbox'):
            log("Applying style to filter_tools_groupbox", prefix="Style")
            self.filter_tab.filter_tools_groupbox.setStyleSheet(groupbox_style)
            # Force style refresh safely
            if self.filter_tab.filter_tools_groupbox.style():
                self.filter_tab.filter_tools_groupbox.style().unpolish(self.filter_tab.filter_tools_groupbox)
                self.filter_tab.filter_tools_groupbox.style().polish(self.filter_tab.filter_tools_groupbox)
            self.filter_tab.filter_tools_groupbox.update()
            log(f"Applied {theme} theme to filter_tools_groupbox", prefix="Style")

@auto_log_methods(logger_key='Mask')
class FilterTab(QWidget):
    filtersApplied = pyqtSignal(object)  # copy of the active filter_df

    def __init__(self, dock):
        super().__init__(dock)
        self.setObjectName("Filter Tab")

        self.dock = dock
        self.ui = dock.ui

        self.logger_key = 'Mask'

        self.setup_ui()

        self.connect_widgets()

        self.update_filter_values()
        self.load_filter_tables()

    def setup_ui(self):
        tab_layout = QVBoxLayout()
        tab_layout.setContentsMargins(6, 6, 6, 6)
        self.setLayout(tab_layout)

        # Create actions for toolbar (will be added to common toolbar)
        self.create_actions()

        horizontal_layout = QHBoxLayout()
        horizontal_layout.setContentsMargins(0,0,0,0)

        tab_layout.addLayout(horizontal_layout)

        # create groupbox for filter tools
        self.filter_tools_groupbox = QGroupBox(self)
        self.filter_tools_groupbox.setTitle("Filter Settings")
        group_layout = QVBoxLayout(self.filter_tools_groupbox)
        group_layout.setContentsMargins(3, 3, 3, 3)
        self.filter_tools_groupbox.setLayout(group_layout)

        filter_layout = QGridLayout()
        filter_layout.setContentsMargins(3, 3, 3, 3)
        group_layout.addLayout(filter_layout)

        # preset combobox - use to create presets to include or exclude individual minerals etc.
        self.combo_filter_presets = QComboBox(self.filter_tools_groupbox)

        # field type and field comboboxes
        self.combo_field_type_type = CustomComboBox(self.filter_tools_groupbox)
        self.combo_field_type_type.popup_callback = lambda: self.dock.update_field_type_combobox(self.combo_field_type_type, addNone=False)

        self.combo_field = CustomComboBox(self.filter_tools_groupbox)
        self.combo_field.popup_callback = lambda: self.dock.update_field_combobox(self.combo_field_type_type, self.combo_field)


        # minimum value for filter
        self.edit_filter_min = CustomLineEdit(self.filter_tools_groupbox)
        self.edit_filter_min.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.edit_filter_min.precision = 8
        self.edit_filter_min.toward = 0


        # minimum quantile value for filter
        self.spin_filter_min = QDoubleSpinBox(self.filter_tools_groupbox)
        self.spin_filter_min.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.spin_filter_min.setKeyboardTracking(False)
        self.spin_filter_min.setMinimum(0.0)
        self.spin_filter_min.setMaximum(100.0)

        # maximum value for filter
        self.edit_filter_max = CustomLineEdit(self.filter_tools_groupbox)
        self.edit_filter_max.setMinimumSize(QSize(0, 0))
        self.edit_filter_max.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.edit_filter_max.precision = 8
        self.edit_filter_max.toward = 1
        
        # maximum quantile value for filter
        self.spin_filter_max = QDoubleSpinBox(self.filter_tools_groupbox)
        self.spin_filter_max.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.spin_filter_max.setKeyboardTracking(False)
        self.spin_filter_max.setMinimum(0.0)
        self.spin_filter_max.setMaximum(100.0)

        # filter operator
        self.combo_operator = QComboBox(self.filter_tools_groupbox)
        self.combo_operator.clear()
        self.combo_operator.addItems(["and","or","not"])

        self.button_load_preset = CustomToolButton(
            text="Add",
            light_icon_unchecked="icon-forward-arrow-64.svg",
            dark_icon_unchecked="icon-forward-arrow-dark-64.svg",
            parent=self.filter_tools_groupbox)
        self.button_load_preset.setFixedSize(QSize(18, 18))
        self.button_load_preset.setToolTip("Add selected preset into filter table")

        filter_layout.addWidget(QLabel("Preset"), 0, 0, 1, 1, Qt.AlignmentFlag.AlignRight)
        filter_layout.addWidget(self.combo_filter_presets, 0, 1, 1, 2)
        filter_layout.addWidget(self.button_load_preset, 0, 3, 1, 1)

        filter_layout.addWidget(QLabel("Field type"), 1, 0, 1, 1, Qt.AlignmentFlag.AlignRight)
        filter_layout.addWidget(self.combo_field_type_type, 1, 1, 1, 2)
        filter_layout.addWidget(QLabel("Field"), 2, 0, 1, 1, Qt.AlignmentFlag.AlignRight)
        filter_layout.addWidget(self.combo_field, 2, 1, 1, 2)

        filter_layout.addWidget(QLabel("Min"), 3, 0, 1, 1, Qt.AlignmentFlag.AlignRight)
        filter_layout.addWidget(self.edit_filter_min, 3, 1, 1, 1)
        filter_layout.addWidget(self.spin_filter_min, 3, 2, 1, 1)
        filter_layout.addWidget(QLabel("Max"), 4, 0, 1, 1, Qt.AlignmentFlag.AlignRight)
        filter_layout.addWidget(self.edit_filter_max, 4, 1, 1, 1)
        filter_layout.addWidget(self.spin_filter_max, 4, 2, 1, 1)

        filter_layout.addWidget(QLabel("Operator"), 5, 0, 1, 1, Qt.AlignmentFlag.AlignRight)
        filter_layout.addWidget(self.combo_operator, 5, 1, 1, 1)

        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        group_layout.addItem(spacer)

        # Filter Table
        self.filter_table = ReorderableTableWidget(self)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.filter_table.sizePolicy().hasHeightForWidth())
        self.filter_table.setSizePolicy(sizePolicy)
        self.filter_table.setMinimumSize(QSize(500, 0))
        self.filter_table.setMaximumSize(QSize(524287, 524287))
        self.filter_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.filter_table.setObjectName("filter_table")
        self.filter_table.setColumnCount(8)
        self.filter_table.setRowCount(0)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.filter_table.setHorizontalHeaderItem(0, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.filter_table.setHorizontalHeaderItem(1, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.filter_table.setHorizontalHeaderItem(2, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.filter_table.setHorizontalHeaderItem(3, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.filter_table.setHorizontalHeaderItem(4, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.filter_table.setHorizontalHeaderItem(5, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.filter_table.setHorizontalHeaderItem(6, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.filter_table.setHorizontalHeaderItem(7, item)

        self.filter_table.horizontalHeader().setDefaultSectionSize(80)
        header = self.filter_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1,QHeaderView.ResizeMode.Interactive)
            header.resizeSection(1, 90)
            header.setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(5,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(6,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(7,QHeaderView.ResizeMode.ResizeToContents)

        self.filter_table.setHorizontalHeaderLabels(["Use", "Field Type", "Field", "Scale", "Min", "Max", "Operator", "Persistent"])
        self.filter_table.setColumnHidden(3, True)  # Hide "Scale" — always "linear", saves horizontal space

        horizontal_layout.addWidget(self.filter_tools_groupbox)
        horizontal_layout.addWidget(self.filter_table)

        # Regions of interest -- a stack of named, colored, filter-defined
        # groups (see SampleObj.add_roi). Housed here rather than a separate
        # tab: an ROI's definition IS a filter definition, live-edited via
        # filter_table above whenever its row here is the sole selection
        # (see _on_roi_selection_changed) -- no separate recall step, so a
        # separate tab would just duplicate this same filter UI. Docked,
        # this makes the tab tall; floating the dock gives it room to breathe.
        self.roi_table = ReorderableTableWidget(self)
        self.roi_table.setObjectName("roi_table")
        self.roi_table.setColumnCount(5)
        self.roi_table.setRowCount(0)
        self.roi_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        header = self.roi_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.roi_table.setHorizontalHeaderLabels(["", "Name", "Color", "% Total", "% Filtered"])
        self.roi_table.setMaximumHeight(160)
        # Right-click (and Ctrl+click, the traditional single-button-mouse
        # convention -- see the eventFilter override below) opens Add/
        # Duplicate/Delete -- see show_roi_context_menu.
        self.roi_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.roi_table.viewport().installEventFilter(self)
        tab_layout.addWidget(self.roi_table)

        filter_icon = QIcon(":/resources/icons/icon-filter-64.svg")
        self.dock.tab_widgets.addTab(self, filter_icon, "Filters")

        # Initialize combo boxes with current field data
        self.initialize_combo_boxes()

    def initialize_combo_boxes(self):
        """Initialize field type and field combo boxes with current data"""
        # Only initialize if we have data loaded
        if hasattr(self.ui, 'app_data') and self.ui.app_data.sample_id:
            # Initialize field type combo box
            self.dock.update_field_type_combobox(self.combo_field_type_type, addNone=False)
            # Initialize field combo box  
            self.dock.update_field_combobox(self.combo_field_type_type, self.combo_field)

    def refresh_field_data(self):
        """Refresh field combo boxes when data changes"""
        self.initialize_combo_boxes()

    def create_actions(self):
        """Create toolbar actions for the filter tab"""
        self.action_add_filter = CustomAction(
            text="Add filter",
            light_icon_unchecked="icon-filter-add-64.svg",
            dark_icon_unchecked="icon-filter-add-dark-64.svg",
            parent=self )
        self.action_add_filter.setToolTip(
            "Add a filter using the properties set below, into the selected region of interest "
            "(a new region is created automatically if none exist yet)"
        )

        self.action_remove_filter = CustomAction(
            text="Delete filter",
            light_icon_unchecked="icon-filter-remove-64.svg",
            dark_icon_unchecked="icon-filter-remove-dark-64.svg",
            parent=self )
        self.action_remove_filter.setToolTip("Delete selected filters")

        self.action_select_all_filters = CustomAction(
            text="Select all",
            light_icon_unchecked="icon-select-all-64.svg",
            dark_icon_unchecked="icon-select-all-dark-64.svg",
            parent=self )
        self.action_select_all_filters.setToolTip("Select all filter lines")

        self.action_save_filters = CustomAction(
            text="Save filter",
            light_icon_unchecked="icon-save-file-64.svg",
            parent=self )
        self.action_save_filters.setToolTip("Save current filter table")

        self.action_add_to_workflow = CustomAction(
            text="Add to workflow",
            light_icon_unchecked="icon-camera-64.svg",
            parent=self )
        self.action_add_to_workflow.setToolTip("Add current filter settings to the Workflow")

        self.action_add_roi = CustomAction(
            text="Add ROI",
            light_icon_unchecked="icon-roi-add-64.svg",
            parent=self )
        self.action_add_roi.setToolTip("Start a new, empty region of interest and select it")

        self.action_delete_roi = CustomAction(
            text="Delete ROI",
            light_icon_unchecked="icon-roi-remove-64.svg",
            parent=self )
        self.action_delete_roi.setToolTip("Delete the selected region(s) of interest")

    def setup_toolbar_actions(self, toolbar):
        """Add filter tab actions to the common toolbar"""
        toolbar.addAction(self.action_add_filter)
        toolbar.addSeparator()
        toolbar.addAction(self.action_save_filters)
        toolbar.addAction(self.action_add_to_workflow)
        toolbar.addSeparator()
        toolbar.addAction(self.action_select_all_filters)
        toolbar.addAction(self.action_remove_filter)
        toolbar.addSeparator()
        toolbar.addAction(self.action_add_roi)
        toolbar.addAction(self.action_delete_roi)

        self.update_roi_table_widget()

    def connect_widgets(self):
        # filter tab toolbar connections
        self.action_add_filter.triggered.connect(self._on_add_filter_clicked)
        self.filter_table.rowsMoved.connect(self._on_filter_rows_moved)
        self.action_remove_filter.triggered.connect(lambda: self.remove_selected_rows())
        self.action_save_filters.triggered.connect(self.save_filter_table)
        self.action_select_all_filters.triggered.connect(self.filter_table.selectAll)
        self.action_add_to_workflow.triggered.connect(self.add_to_workflow)

        # region-of-interest connections
        self.action_add_roi.triggered.connect(self.add_roi)
        self.action_delete_roi.triggered.connect(self.delete_selected_roi)
        self.roi_table.rowsMoved.connect(self._on_roi_rows_moved)
        self.roi_table.itemChanged.connect(self.roi_label_changed)
        self.roi_table.itemSelectionChanged.connect(self._on_roi_selection_changed)
        self.roi_table.customContextMenuRequested.connect(self.show_roi_context_menu)

        # filter widget connections
        self.button_load_preset.clicked.connect(lambda: self.read_filter_table())
        self.combo_field.currentTextChanged.connect(self.update_filter_values)
        self.edit_filter_min.editingFinished.connect(self.callback_edit_filter_min)
        self.spin_filter_min.valueChanged.connect(self.callback_spin_filter_min)
        self.edit_filter_max.editingFinished.connect(self.callback_edit_filter_max)
        self.spin_filter_max.valueChanged.connect(self.callback_spin_filter_max)

    def apply_field_filters_update_plot(self):
        """Updates filters in current data and schedules plot update

        Updates the plot once filter values have been update
        """
        current_data = self.ui.app_data.current_data
        if current_data:
            current_data.apply_field_filters()
            self.filtersApplied.emit(current_data.filter_df.copy())
            log(f"apply_field_filters_update_plot: plot_flag={self.ui.plot_flag}, calling schedule_update", prefix='Mask')
            self.ui.schedule_update()

    def _on_filter_rows_moved(self, source_rows, target_row):
        """Reorders ``filter_df`` to match a drag-and-drop move in ``filter_table``."""
        current_data = self.ui.app_data.current_data
        if not current_data:
            return

        new_order = compute_row_reorder(len(current_data.filter_df), source_rows, target_row)
        current_data.reorder_filters(new_order)
        self.update_filter_table(reload=True, apply=False)
        self.apply_field_filters_update_plot()
        self._sync_active_roi_and_refresh()

    def add_to_workflow(self):
        """Force-record the current filter settings for the Workflow report.

        Filters have no corresponding Blockly block yet (see
        `ActionRecorder.build_block_state`), so this doesn't insert a block into
        an open Workflow workspace - it records the current `filter_df` so it's
        available to the live `.rst` report writer the next time a workflow runs.
        """
        current_data = self.ui.app_data.current_data
        if not current_data:
            return
        self.ui.action_recorder.record(
            'filter',
            f"Filter settings for sample '{self.ui.app_data.sample_id}'",
            {'filter_df': current_data.filter_df.copy(), 'sample_id': self.ui.app_data.sample_id},
            force=True,
        )
        self.ui.statusbar.showMessage('Filter settings added to workflow record', 4000)

    def update_filter_values(self, *args, **kwargs):
        """Updates widgets that display the filter bounds for a selected field.

        Updates ``self.edit_filter_min`` and ``self.edit_filter_max`` values for display when the
        field in ``self.combo_field`` is changed.
        """
        current_data = self.ui.app_data.current_data
        if not current_data or self.ui.app_data.sample_id == '':
            return

        # Check if field is selected
        if not (field := self.combo_field.currentText()): 
            return

        # Get field data using the proper data access pattern
        try:
            field_data = current_data.get_map_data(field, self.combo_field_type_type.currentText())
            if field_data is not None and 'array' in field_data:
                array = field_data['array'].dropna()
                self.edit_filter_min.value = array.min()
                self.callback_edit_filter_min()
                self.edit_filter_max.value = array.max()
                self.callback_edit_filter_max()
        except Exception:
            # If field data cannot be retrieved, skip update
            return

    def callback_edit_filter_min(self):
        """Updates ``self.spin_filter_min.value`` when ``self.edit_filter_min.value`` is changed"""        
        current_data = self.ui.app_data.current_data
        if not current_data or self.ui.app_data.sample_id == '':
            return

        if (self.combo_field.currentText() == '') or (self.combo_field_type_type.currentText() == ''):
            return

        try:
            field_data = current_data.get_map_data(self.combo_field.currentText(), self.combo_field_type_type.currentText())
            if field_data is not None and 'array' in field_data:
                array = field_data['array'].dropna()
                self.spin_filter_min.blockSignals(True)
                self.spin_filter_min.setValue(percentileofscore(array, self.edit_filter_min.value))
                self.spin_filter_min.blockSignals(False)
        except Exception:
            return

    def callback_edit_filter_max(self):
        """Updates ``self.spin_filter_max.value`` when ``self.edit_filter_max.value`` is changed"""        
        current_data = self.ui.app_data.current_data
        if not current_data or self.ui.app_data.sample_id == '':
            return

        if (self.combo_field.currentText() == '') or (self.combo_field_type_type.currentText() == ''):
            return

        try:
            field_data = current_data.get_map_data(self.combo_field.currentText(), self.combo_field_type_type.currentText())
            if field_data is not None and 'array' in field_data:
                array = field_data['array'].dropna()
                self.spin_filter_max.blockSignals(True)
                self.spin_filter_max.setValue(percentileofscore(array, self.edit_filter_max.value))
                self.spin_filter_max.blockSignals(False)
        except Exception:
            return

    def callback_spin_filter_min(self):
        """Updates ``self.edit_filter_min.value`` when ``self.spin_filter_min.value`` is changed"""        
        current_data = self.ui.app_data.current_data
        if not current_data:
            return
            
        try:
            field_data = current_data.get_map_data(self.combo_field.currentText(), self.combo_field_type_type.currentText())
            if field_data is not None and 'array' in field_data:
                array = field_data['array'].dropna()
                self.edit_filter_min.value = np.percentile(array, self.spin_filter_min.value())
        except Exception:
            return

    def callback_spin_filter_max(self):
        """Updates ``self.edit_filter_max.value`` when ``self.spin_filter_max.value`` is changed"""        
        current_data = self.ui.app_data.current_data
        if not current_data:
            return
            
        try:
            field_data = current_data.get_map_data(self.combo_field.currentText(), self.combo_field_type_type.currentText())
            if field_data is not None and 'array' in field_data:
                array = field_data['array'].dropna()
                self.edit_filter_max.value = np.percentile(array, self.spin_filter_max.value())
        except Exception:
            return

    def update_filter_table(self, reload = False, apply = True):
        """Update data for analysis when filter table is updated.

        Parameters
        ----------
        reload : bool, optional
            Reload ``True`` updates the filter table, by default False
        """
        current_data = self.ui.app_data.current_data
        if not current_data:
            return

        def on_use_checkbox_state_changed(row, state):
            """Update the 'use' value in the filter_df for the given row and refresh the plot"""
            if current_data and row < len(current_data.filter_df):
                current_data.filter_df.at[row, 'use'] = bool(state)
                self.apply_field_filters_update_plot()
                self._sync_active_roi_and_refresh()

        # If reload is True, clear the table and repopulate it from filter_df
        if reload:
            # Disconnect stateChanged signals before clearing to prevent spurious apply calls
            for r in range(self.filter_table.rowCount()):
                widget = self.filter_table.cellWidget(r, 0)
                if widget:
                    widget.blockSignals(True)
            # Clear the table
            self.filter_table.setRowCount(0)

            # Repopulate the table from filter_df
            for index, row in current_data.filter_df.iterrows():
                current_row = self.filter_table.rowCount()
                self.filter_table.insertRow(current_row)

                # Create and set the checkbox for 'use'
                chkBoxItem_use = QCheckBox()
                chkBoxItem_use.setCheckState(Qt.CheckState.Checked if row['use'] else Qt.CheckState.Unchecked)
                chkBoxItem_use.stateChanged.connect(lambda state, row=current_row: on_use_checkbox_state_changed(row, state))
                self.filter_table.setCellWidget(current_row, 0, chkBoxItem_use)

                # Add other items from the row
                self.filter_table.setItem(current_row, 1, QTableWidgetItem(row['field_type']))
                self.filter_table.setItem(current_row, 2, QTableWidgetItem(row['field']))
                self.filter_table.setItem(current_row, 3, QTableWidgetItem(row['norm']))  # Use 'norm' instead of 'scale'
                self.filter_table.setItem(current_row, 4, QTableWidgetItem(fmt.dynamic_format(row['min'])))
                self.filter_table.setItem(current_row, 5, QTableWidgetItem(fmt.dynamic_format(row['max'])))
                self.filter_table.setItem(current_row, 6, QTableWidgetItem(row['operator']))

                # Create and set the checkbox for persistent
                chkBoxItem_persistent = QCheckBox()
                chkBoxItem_persistent.setCheckState(Qt.CheckState.Checked if row.get('persistent', True) else Qt.CheckState.Unchecked)
                self.filter_table.setCellWidget(current_row, 7, chkBoxItem_persistent)

        else:
            # Add new filter using DataHandling methods
            field_type = self.combo_field_type_type.currentText()
            field = self.combo_field.currentText()
            f_min = self.edit_filter_min.value
            f_max = self.edit_filter_max.value
            operator = self.combo_operator.currentText()
            
            # Use the DataHandling method to add the filter
            filter_index = current_data.add_filter(
                field_type=field_type,
                field=field,
                min_val=f_min,
                max_val=f_max,
                operator=operator,
                use=True,
                persistent=True
            )

            # Add a new row to the table
            row = self.filter_table.rowCount()
            self.filter_table.insertRow(row)

            # Create a QCheckBox for the 'use' column
            chkBoxItem_use = QCheckBox()
            chkBoxItem_use.setCheckState(Qt.CheckState.Checked)
            chkBoxItem_use.stateChanged.connect(lambda state, row=row: on_use_checkbox_state_changed(row, state))

            # Create checkbox for persistent
            chkBoxItem_persistent = QCheckBox()
            chkBoxItem_persistent.setCheckState(Qt.CheckState.Checked)

            # Get the norm/scale from the filter_df
            filter_row = current_data.filter_df.iloc[filter_index]
            
            self.filter_table.setCellWidget(row, 0, chkBoxItem_use)
            self.filter_table.setItem(row, 1, QTableWidgetItem(field_type))
            self.filter_table.setItem(row, 2, QTableWidgetItem(field))
            self.filter_table.setItem(row, 3, QTableWidgetItem(filter_row['norm']))
            self.filter_table.setItem(row, 4, QTableWidgetItem(fmt.dynamic_format(f_min)))
            self.filter_table.setItem(row, 5, QTableWidgetItem(fmt.dynamic_format(f_max)))
            self.filter_table.setItem(row, 6, QTableWidgetItem(operator))
            self.filter_table.setCellWidget(row, 7, chkBoxItem_persistent)

        # Apply the filters after updating
        if apply:
            current_data.apply_field_filters()

    def remove_selected_rows(self):
        """Remove selected rows from filter table.

        Removes selected rows from filter table and updates DataHandling filter_df.
        """
        current_data = self.ui.app_data.current_data
        if not current_data:
            return

        # Collect selected row indices in reverse order to avoid shifting issues
        selected_rows = sorted(
            {idx.row() for idx in self.filter_table.selectionModel().selectedRows()},
            reverse=True
        )

        indices_to_remove = []
        for row in selected_rows:
            indices_to_remove.append(row)
            self.filter_table.removeRow(row)

        # Remove from DataHandling filter_df using new method
        for index in indices_to_remove:
            current_data.remove_filter(index)

        # Apply filters and update plot
        self.apply_field_filters_update_plot()
        self._sync_active_roi_and_refresh()

    def save_filter_table(self):
        """Opens a dialog to save filter table

        Executes on ``MainWindow.toolButtonFilterSave`` is clicked.  The filter is added to
        ``MainWindow.filter_table`` and save into a dictionary to a file with a ``.fltr`` extension.
        """
        current_data = self.ui.app_data.current_data
        if not current_data:
            QMessageBox.warning(self.ui, 'Error', 'No data loaded.')
            return

        name, ok = QInputDialog.getText(self.ui, 'Save filter table', 'Enter filter table name:')
        if ok:
            # file name for saving
            filter_file = os.path.join(BASEDIR,f'resources/filters/{name}.fltr')

            # save dictionary to file
            current_data.filter_df.to_csv(filter_file, index=False)

            # update comboBox
            self.combo_filter_presets.addItem(name)
            self.combo_filter_presets.setCurrentText(name)

            self.ui.statusBar.showMessage(f'Filters successfully saved as {filter_file}')
        else:
            # throw a warning that name is not saved
            QMessageBox.warning(self.ui,'Error','could not save filter table.')

            return

    def load_filter_tables(self):
        """Loads filter names and adds them to the filter presets comboBox
        
        Looks for saved filter tables (*.fltr) in ``resources/filters/`` directory and adds them to
        ``self.combo_filter_presets``.
        """
        # read filenames with *.sty
        file_list = os.listdir(os.path.join(BASEDIR,'resources/filters/'))
        filter_list = [file.replace('.fltr','') for file in file_list if file.endswith('.fltr')]

        # add default to list
        filter_list.insert(0,'')

        # update theme comboBox
        self.combo_filter_presets.clear()
        self.combo_filter_presets.addItems(filter_list)
        self.combo_filter_presets.setCurrentIndex(0)

    def read_filter_table(self):
        current_data = self.ui.app_data.current_data
        if not current_data:
            QMessageBox.warning(self.ui, 'Error', 'No data loaded.')
            return
            
        filter_name = self.combo_filter_presets.currentText()

        # If no filter_name is chosen, return
        if filter_name == '':
            return

        # open filter with name filter_name
        filter_file = os.path.join(BASEDIR,f'resources/filters/{filter_name}.fltr')
        try:
            filter_info = pd.read_csv(filter_file)

            # Normalize bool columns that CSV reads as strings
            for col in ('use', 'persistent'):
                if col in filter_info.columns:
                    filter_info[col] = filter_info[col].astype(str).str.strip().str.lower() == 'true'

            # A preset is just a bundle of filter definitions, and filter
            # definitions only live inside a region of interest -- so gate
            # the load exactly like "Add filter" does (see
            # ``_on_add_filter_clicked``):
            #   - no regions yet   -> auto-create one to hold the preset
            #   - regions present, none (or several) selected -> ask the
            #     user to pick a single target; don't drop the preset into
            #     a region-less filter table
            if not current_data.roi_stack:
                color = self.ui.style_data.set_default_cluster_colors(1)[-1]
                new_id = current_data.add_roi(color=color)
                self.update_roi_table_widget()
                self._select_roi_row(new_id)
            elif self._active_roi_id() is None:
                QMessageBox.information(
                    self, "Select a Region of Interest",
                    "Select a single region of interest in the table below before loading a filter preset.",
                )
                return

            # append preset filters to existing filters
            current_data.filter_df = pd.concat([current_data.filter_df, filter_info], ignore_index=True)

            self.update_filter_table(reload=True, apply=False)
            self.apply_field_filters_update_plot()
            self._sync_active_roi_and_refresh()
        except FileNotFoundError:
            QMessageBox.warning(self.ui, 'Error', f'Filter file {filter_file} not found.')
        except Exception as e:
            QMessageBox.warning(self.ui, 'Error', f'Error loading filter: {str(e)}')

    # -------------------------------------
    # Regions of interest (ROI)
    # -------------------------------------
    def add_roi(self):
        """Start a new, empty region of interest and select it -- filters
        added afterward (via "Add filter") go directly into this region
        until a different one is selected. A deliberate "start fresh"
        action, independent of the auto-create that happens the first time
        a filter is added with no region defined yet (see
        ``_on_add_filter_clicked``).
        """
        current_data = self.ui.app_data.current_data
        if not current_data:
            return

        current_data.filter_df = current_data.filter_df.iloc[0:0]
        n = len(current_data.roi_stack) + 1
        color = self.ui.style_data.set_default_cluster_colors(n)[-1]
        new_id = current_data.add_roi(color=color)

        self.update_filter_table(reload=True, apply=False)
        self.update_roi_table_widget()
        self._select_roi_row(new_id)
        self.ui.schedule_update()

    def _active_roi_id(self):
        """The id of the ROI currently selected for editing in
        ``roi_table`` -- None unless *exactly one* row is selected (zero or
        several rows are both "no single target"; see
        ``_on_add_filter_clicked``/``_on_roi_selection_changed``).
        """
        selection_model = self.roi_table.selectionModel()
        if selection_model is None:
            return None
        rows = selection_model.selectedRows()
        if len(rows) != 1:
            return None
        item = self.roi_table.item(rows[0].row(), 1)
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _selected_roi_ids(self):
        """Ids of every row currently selected in ``roi_table`` (any
        count) -- for operations that act on a whole multi-selection, like
        deleting several regions at once. See ``_active_roi_id`` for the
        single-target ("editing") case.
        """
        selection_model = self.roi_table.selectionModel()
        if selection_model is None:
            return []
        ids = []
        for idx in selection_model.selectedRows():
            item = self.roi_table.item(idx.row(), 1)
            if item is not None:
                rid = item.data(Qt.ItemDataRole.UserRole)
                if rid is not None:
                    ids.append(rid)
        return ids

    def _select_roi_row(self, roi_id):
        """Row-select the table row for ``roi_id`` (rows are displayed in
        reverse stack order -- see ``update_roi_table_widget``).
        """
        for row in range(self.roi_table.rowCount()):
            item = self.roi_table.item(row, 1)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == roi_id:
                self.roi_table.selectRow(row)
                return

    def _on_roi_selection_changed(self):
        """Loads whichever ROI is now the sole selection into
        ``filter_table`` for live editing -- replaces the old
        ``combo_roi_select``-driven recall. Zero or several rows selected
        both clear the table (nothing single to show/edit).
        """
        current_data = self.ui.app_data.current_data
        if not current_data:
            return

        active_id = self._active_roi_id()
        entry = None
        if active_id is not None:
            entry = next((r for r in current_data.roi_stack if r['id'] == active_id), None)

        # A region defined by polygons (SampleObj.add_polygon_roi) or clusters
        # (add_cluster_roi) has no filter definition to show -- it was built in
        # the Polygons or Clusters tab.
        if entry is None or entry.get('filter_df') is None:
            current_data.filter_df = current_data.filter_df.iloc[0:0]
        else:
            current_data.filter_df = entry['filter_df'].copy()
        self.update_filter_table(reload=True, apply=False)

    def _derived_roi_kind(self, roi_id):
        """``'polygons'``, ``'clusters'`` or None for the region `roi_id`.

        A *derived* region carries its own definition from another tab instead
        of a filter, so the filter table must neither show nor overwrite it.
        """
        current_data = self.ui.app_data.current_data
        if not current_data or roi_id is None:
            return None
        entry = next((r for r in current_data.roi_stack if r['id'] == roi_id), None)
        if not entry:
            return None
        if entry.get('polygons'):
            return 'polygons'
        if entry.get('clusters'):
            return 'clusters'
        return None

    def _is_derived_roi(self, roi_id):
        """True when `roi_id` names a region defined outside the Filters tab."""
        return self._derived_roi_kind(roi_id) is not None

    def _is_polygon_roi(self, roi_id):
        """True when `roi_id` names a region defined by polygon geometry."""
        return self._derived_roi_kind(roi_id) == 'polygons'

    def _sync_active_roi_and_refresh(self):
        """Writes the live ``filter_df`` back into whichever ROI is
        currently the sole selection (see ``_active_roi_id``), then
        refreshes ``roi_table`` (its "% Filtered" column depends on the
        just-updated definition). A no-op when no single region is
        selected -- the live filter table is empty in that case anyway
        (see ``_on_roi_selection_changed``/``_on_add_filter_clicked``), so
        there's nothing to write back.
        """
        current_data = self.ui.app_data.current_data
        if not current_data:
            return
        active_id = self._active_roi_id()
        if active_id is None or self._is_derived_roi(active_id):
            return
        current_data.update_roi_filter(active_id, current_data.filter_df)
        self.update_roi_table_widget()

    def _on_add_filter_clicked(self):
        """Gate for "Add filter": no filtering happens outside a region of
        interest, so this makes sure exactly one is unambiguously being
        edited before appending anything.

        - No regions exist yet -> auto-create a blank one and select it
          (the new filter becomes its first entry).
        - Regions exist but none (or more than one) is selected -> ask the
          user to select a single region first; nothing is added.
        - The selected region is defined by polygons or clusters -> it has no
          filter definition to add to; say so rather than silently replacing
          the definition it does have.
        - Exactly one region selected -> append the filter as before, then
          sync it into that region's stored definition.
        """
        current_data = self.ui.app_data.current_data
        if not current_data:
            return

        if not current_data.roi_stack:
            color = self.ui.style_data.set_default_cluster_colors(1)[-1]
            new_id = current_data.add_roi(color=color)
            self.update_roi_table_widget()
            self._select_roi_row(new_id)
        elif self._active_roi_id() is None:
            QMessageBox.information(
                self, "Select a Region of Interest",
                "Select a single region of interest in the table below before adding a filter.",
            )
            return
        elif self._is_derived_roi(self._active_roi_id()):
            kind = self._derived_roi_kind(self._active_roi_id())
            source_tab = 'Polygons' if kind == 'polygons' else 'Clusters'
            QMessageBox.information(
                self, f"Region Defined by {source_tab}",
                f"This region is defined by {kind}, not filters. Edit it in the "
                f"{source_tab} tab, or select a different region to add a filter to.",
            )
            return

        self.update_filter_table()
        self.apply_field_filters_update_plot()
        self._sync_active_roi_and_refresh()

    def delete_selected_roi(self):
        """Deletes every currently-selected region (the toolbar's "Delete
        ROI" action and the context menu's Delete both go through this).
        """
        current_data = self.ui.app_data.current_data
        roi_ids = self._selected_roi_ids()
        if not current_data or not roi_ids:
            return
        for roi_id in roi_ids:
            current_data.remove_roi(roi_id)
        self.update_roi_table_widget()
        self.ui.schedule_update()

    def show_roi_context_menu(self, pos):
        """Right-click (and Ctrl+click, see ``eventFilter``) menu on
        ``roi_table``: Add ROI (always available), Duplicate ROI (only for
        a single target), and Delete ROI / Delete N ROIs (for one or more).

        Right-clicking a row not already part of the current selection
        replaces the selection with just that row first (standard table
        convention); right-clicking within an existing multi-selection
        acts on the whole selection. Right-clicking empty space (no row
        under the cursor) still opens the menu, just with only "Add ROI"
        available.
        """
        row = self.roi_table.rowAt(pos.y())
        if row >= 0:
            selection_model = self.roi_table.selectionModel()
            selected_rows = {idx.row() for idx in selection_model.selectedRows()} if selection_model else set()
            if row not in selected_rows:
                self.roi_table.clearSelection()
                self.roi_table.selectRow(row)

        roi_ids = self._selected_roi_ids()

        menu = QMenu(self.roi_table)
        action_add = menu.addAction("Add ROI")
        action_duplicate = menu.addAction("Duplicate ROI") if len(roi_ids) == 1 else None
        action_delete = None
        if roi_ids:
            label = "Delete ROI" if len(roi_ids) == 1 else f"Delete {len(roi_ids)} ROIs"
            action_delete = menu.addAction(label)
        chosen = menu.exec(self.roi_table.viewport().mapToGlobal(pos))

        current_data = self.ui.app_data.current_data
        if not current_data or chosen is None:
            return
        if chosen is action_add:
            self.add_roi()
        elif action_duplicate is not None and chosen is action_duplicate:
            new_id = current_data.duplicate_roi(roi_ids[0])
            self.update_roi_table_widget()
            if new_id is not None:
                self._select_roi_row(new_id)
            self.ui.schedule_update()
        elif action_delete is not None and chosen is action_delete:
            for roi_id in roi_ids:
                current_data.remove_roi(roi_id)
            self.update_roi_table_widget()
            self.ui.schedule_update()

    def eventFilter(self, obj, event):
        """Ctrl+click on ``roi_table`` also opens the context menu -- the
        traditional single-button-mouse convention for a right-click, kept
        alongside real right-click (handled natively via
        ``customContextMenuRequested``). Mouse events for item views are
        delivered to the viewport, not the outer table widget, hence
        filtering ``roi_table.viewport()`` rather than ``roi_table``
        itself. Filtered on release (not press) so Qt's own click-to-
        select/extend-selection handling for the press has already run --
        the menu then acts on whatever selection that produced, same as a
        real right-click would.
        """
        # Same teardown guard as PolygonTab.eventFilter: the filter outlives
        # the tab, so this must not assume its widgets are still there.
        table = getattr(self, 'roi_table', None)
        if table is not None and obj is table.viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
                self.show_roi_context_menu(pos)
                return True
        return super().eventFilter(obj, event)

    def _on_roi_rows_moved(self, source_rows, target_row):
        """Reorders ``roi_stack`` priority to match a drag-and-drop move in ``roi_table``.

        ``roi_table`` displays rows top-to-bottom in *reverse* stack order
        (top row = highest priority = last in ``roi_stack``, see
        ``update_roi_table_widget``), so the visual row positions have to be
        converted to stack-order space before reordering.
        """
        current_data = self.ui.app_data.current_data
        if not current_data:
            return

        stack_ids = [r['id'] for r in current_data.roi_stack]  # ascending priority
        display_ids = list(reversed(stack_ids))  # top-to-bottom, matches table rows

        new_order = compute_row_reorder(len(display_ids), source_rows, target_row)
        new_display_ids = [display_ids[i] for i in new_order]
        new_stack_ids = list(reversed(new_display_ids))

        current_data.reorder_roi_stack(new_stack_ids)
        self.update_roi_table_widget()
        self.ui.schedule_update()

    def _roi_row_color_changed(self, roi_id, hexcolor):
        """Updates an ROI's color when its own row's ColorButton (in
        ``roi_table``'s Color column) is changed, writing it back into
        ``SampleObj.roi_stack`` and refreshing the map if it's currently
        coloured by ROI.
        """
        current_data = self.ui.app_data.current_data
        if not current_data:
            return
        for entry in current_data.roi_stack:
            if entry['id'] == roi_id:
                entry['color'] = hexcolor
                break

        if self.ui.app_data.c_field_type.lower() == 'roi':
            self.ui.schedule_update()

    def roi_label_changed(self, item):
        if item.column() != 1:
            return
        current_data = self.ui.app_data.current_data
        roi_id = item.data(Qt.ItemDataRole.UserRole)
        if not current_data or roi_id is None:
            return

        new_name = item.text()
        for entry in current_data.roi_stack:
            if entry['id'] == roi_id:
                entry['name'] = new_name
                break

        self.update_roi_table_widget()
        if self.ui.app_data.c_field_type.lower() == 'roi':
            self.ui.schedule_update()

    def update_selected_rois(self):
        """Executed on toggling a checkbox in ``roi_table``'s selection column.

        Updates ``SampleObj.selected_rois`` (which regions are currently
        shown -- combined into the mask via ``roi_selection_mask``) and
        recomputes.
        """
        current_data = self.ui.app_data.current_data
        if not current_data:
            return

        selected = []
        for row in range(self.roi_table.rowCount()):
            cb = self.roi_table.cellWidget(row, 0)
            item = self.roi_table.item(row, 1)
            if cb is not None and cb.isChecked() and item is not None:
                rid = item.data(Qt.ItemDataRole.UserRole)
                if rid is not None:
                    selected.append(rid)

        current_data.selected_rois = selected
        current_data.recompute_roi_assignments()
        self.ui.schedule_update()

    def update_roi_table_widget(self):
        """Rebuild ``roi_table`` from ``SampleObj.roi_stack``.

        Displayed top-to-bottom in *reverse* stack order, so the top row is
        the highest-priority region (the one that wins overlapping pixels)
        -- matching the usual "top of the layer stack" convention.

        Re-selects whichever region was the sole active selection before
        the rebuild (rows are recreated from scratch, so the row-selection
        model doesn't survive on its own) -- callers throughout this class
        rely on the active-editing-target selection surviving a table
        refresh (e.g. ``_sync_active_roi_and_refresh`` calls this after
        every filter edit).
        """
        current_data = self.ui.app_data.current_data
        if not current_data:
            return

        active_id_before = self._active_roi_id()
        stack = current_data.roi_stack
        percentages = current_data.roi_percentages()

        self.roi_table.blockSignals(True)
        self.roi_table.clearContents()
        self.roi_table.setRowCount(len(stack))
        self.roi_table.setHorizontalHeaderLabels(["", "Name", "Color", "% Total", "% Filtered"])

        for row, entry in enumerate(reversed(stack)):
            cb = QCheckBox()
            cb.setChecked(entry['id'] in current_data.selected_rois)
            cb.stateChanged.connect(lambda _state: self.update_selected_rois())
            self.roi_table.setCellWidget(row, 0, cb)

            name_item = QTableWidgetItem(entry['name'])
            name_item.setData(Qt.ItemDataRole.UserRole, entry['id'])
            self.roi_table.setItem(row, 1, name_item)

            # ColorButton shows the hex code as its own text (see
            # blueberry.ColorButton) and opens a color picker on click --
            # the per-row Color cell is the way to recolor a region (its
            # colour drives the discrete ROI-map colormap, see
            # StyleToolbox.get_roi_colormap).
            color_button = ColorButton(initial_color=entry['color'], ui=self.ui)
            color_button.colorChanged.connect(lambda hexcolor, roi_id=entry['id']: self._roi_row_color_changed(roi_id, hexcolor))
            self.roi_table.setCellWidget(row, 2, color_button)

            pct = percentages.get(entry['id'], {'pct_total': 0.0, 'pct_filtered': 0.0})
            pct_total_item = QTableWidgetItem(f"{pct['pct_total']:.1f}")
            pct_total_item.setFlags(pct_total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.roi_table.setItem(row, 3, pct_total_item)

            pct_filtered_item = QTableWidgetItem(f"{pct['pct_filtered']:.1f}")
            pct_filtered_item.setFlags(pct_filtered_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.roi_table.setItem(row, 4, pct_filtered_item)

        if active_id_before is not None and any(r['id'] == active_id_before for r in stack):
            for row in range(self.roi_table.rowCount()):
                item = self.roi_table.item(row, 1)
                if item is not None and item.data(Qt.ItemDataRole.UserRole) == active_id_before:
                    self.roi_table.selectRow(row)
                    break

        self.roi_table.blockSignals(False)

@auto_log_methods(logger_key='Mask')
class PolygonTab(QWidget):
    def __init__(self, dock):
        super().__init__(dock)
        self.setObjectName("Polygon Tab")

        self.dock = dock
        self.ui = dock.ui
        
        #init table_fcn
        self.table_fcn = TableFcn(self)
    
        self.setup_ui()

    def setup_ui(self):
        tab_layout = QVBoxLayout()
        tab_layout.setContentsMargins(6, 6, 6, 6)
        self.setLayout(tab_layout)

        # Create actions for toolbar (will be added to common toolbar)
        self.create_actions()
        
        self.tableWidgetPolyPoints = CustomTableWidget()
        self.tableWidgetPolyPoints.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidgetPolyPoints.setColumnCount(5)

        header = self.tableWidgetPolyPoints.horizontalHeader()
        if header:
            header.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4,QHeaderView.ResizeMode.ResizeToContents)

        self.tableWidgetPolyPoints.setHorizontalHeaderLabels(["PolyID", "Name", "Link", "In/out", "Analysis"])

        # Right-click a row to delete it (mirrors the ROI table), and let the
        # Delete key work while the table itself has focus -- the canvas
        # shortcut only fires when the map has focus.
        self.tableWidgetPolyPoints.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tableWidgetPolyPoints.customContextMenuRequested.connect(self.show_polygon_context_menu)

        # An event filter rather than a QShortcut: a shortcut only fires when
        # the widget's window is active, which makes it both flakier and
        # untestable headlessly.
        self.tableWidgetPolyPoints.installEventFilter(self)


        tab_layout.addWidget(self.tableWidgetPolyPoints)

        self.polygon_manager = PolygonManager(parent=self, main_window=self.ui)

        polygon_icon = QIcon(":/resources/icons/icon-polygon-new-64.svg")
        self.dock.tab_widgets.addTab(self, polygon_icon, "Polygons")

    def create_actions(self):
        """Create toolbar actions for the polygon tab"""
        # polygon toggle
        self.polygon_toggle = ToggleSwitch(height=18, bg_left_color="#D8ADAB", bg_right_color="#A8B078")
        self.polygon_toggle.setChecked(False)
        self.actionPolyToggle = QWidgetAction(None)
        self.actionPolyToggle.setDefaultWidget(self.polygon_toggle)
        self.polygon_toggle.stateChanged.connect(lambda: self.polygon_state_changed())

        self.actionEdgeDetect = CustomAction(
            text="Toggle edge detection",
            light_icon_unchecked="icon-spotlight-64.svg",
            dark_icon_unchecked="icon-spotlight-dark-64.svg",
            parent=self
        )
        self.actionEdgeDetect.setCheckable(True)
        self.actionEdgeDetect.setChecked(False)
        self.actionEdgeDetect.setToolTip("Toggle edge detection")
        self.actionEdgeDetect.triggered.connect(self.toggle_edge_detection)

        self.comboBoxEdgeDetectMethod = QComboBox()
        self.comboBoxEdgeDetectMethod.addItems(["Sobel","Canny","Zero cross"])
        self.comboBoxEdgeDetectMethod.activated.connect(self.ui.control_dock.noise_reduction.add_edge_detection)

        self.actionPolyLoad = CustomAction(
            text="Load Polygon",
            light_icon_unchecked="icon-open-file-64.svg",
            dark_icon_unchecked="icon-open-file-dark-64.svg",
            parent=self
        )
        self.actionPolyLoad.setToolTip("Load polygons")

        self.actionPolyCreate = CustomAction(
            text="Create Polygon",
            light_icon_unchecked="icon-polygon-new-64.svg",
            dark_icon_unchecked="icon-polygon-new-dark-64.svg",
            parent=self
        )
        self.actionPolyCreate.setToolTip("Create a new polygon")

        # The three vertex-editing modes are mutually exclusive toggles (see
        # `_set_edit_mode`). CustomAction is only checkable when given a
        # checked icon, so say so explicitly -- as the profile dock does.
        self.actionPolyMovePoint = CustomAction(
            text="Move Point",
            light_icon_unchecked="icon-move-point-64.svg",
            dark_icon_unchecked="icon-move-point-dark-64.svg",
            parent=self
        )
        self.actionPolyMovePoint.setCheckable(True)
        self.actionPolyMovePoint.setToolTip(
            "Move a vertex of the selected polygon by dragging it "
            "(drag inside the polygon to move the whole polygon)"
        )

        self.actionPolyAddPoint = CustomAction(
            text="Add Point",
            light_icon_unchecked="icon-add-point-64.svg",
            dark_icon_unchecked="icon-add-point-dark-64.svg",
            parent=self
        )
        self.actionPolyAddPoint.setCheckable(True)
        self.actionPolyAddPoint.setToolTip("Add a vertex to the selected polygon: click on one of its edges")

        self.actionPolyRemovePoint = CustomAction(
            text="Remove Point",
            light_icon_unchecked="icon-remove-point-64.svg",
            dark_icon_unchecked="icon-remove-point-dark-64.svg",
            parent=self
        )
        self.actionPolyRemovePoint.setCheckable(True)
        self.actionPolyRemovePoint.setToolTip("Remove a vertex from the selected polygon: click on it")

        self.actionPolyLink = CustomAction(
            text="Link Polygons",
            light_icon_unchecked="icon-link-64.svg",
            dark_icon_unchecked="icon-link-dark-64.svg",
            parent=self
        )
        self.actionPolyLink.setToolTip(
            "Link the selected polygons so they form a single region"
        )

        self.actionPolyDelink = CustomAction(
            text="Remove Link",
            light_icon_unchecked="icon-unlink-64.svg",
            dark_icon_unchecked="icon-unlink-dark-64.svg",
            parent=self
        )
        self.actionPolyDelink.setToolTip(
            "Unlink the selected polygons so each is its own region"
        )

        # Same icon as the ROI tab's "Add ROI" -- this creates one of the same
        # regions, just defined by geometry instead of filters. No dark variant
        # ships for it, matching action_add_roi.
        self.actionPolyRegion = CustomAction(
            text="Create Region",
            light_icon_unchecked="icon-roi-add-64.svg",
            parent=self
        )
        self.actionPolyRegion.setToolTip(
            "Create a region of interest from the selected polygons "
            "(one per linked group) for per-region statistics"
        )

        self.actionPolySave = CustomAction(
            text="Save Polygons",
            light_icon_unchecked="icon-save-file-64.svg",
            parent=self
        )
        self.actionPolySave.setToolTip("Save polygons to a file")

        self.actionPolyDelete = CustomAction(
            text="Delete Polygon",
            light_icon_unchecked="icon-delete-64.svg",
            dark_icon_unchecked="icon-delete-dark-64.svg",
            parent=self
        )
        self.actionPolyDelete.setToolTip("Delete selected polygons")

    def setup_toolbar_actions(self, toolbar):
        """Add polygon tab actions to the common toolbar"""
        toolbar.addAction(self.actionPolyToggle)
        toolbar.addAction(self.actionPolyLoad)
        toolbar.addSeparator()
        toolbar.addAction(self.actionEdgeDetect)
        toolbar.addWidget(self.comboBoxEdgeDetectMethod)
        toolbar.addSeparator()
        toolbar.addAction(self.actionPolyCreate)
        toolbar.addAction(self.actionPolyMovePoint)
        toolbar.addAction(self.actionPolyAddPoint)
        toolbar.addAction(self.actionPolyRemovePoint)
        toolbar.addSeparator()
        toolbar.addAction(self.actionPolyLink)
        toolbar.addAction(self.actionPolyDelink)
        toolbar.addAction(self.actionPolyRegion)
        toolbar.addSeparator()
        toolbar.addAction(self.actionPolySave)
        toolbar.addAction(self.actionPolyDelete)
        
        if not getattr(self, '_polygon_signals_connected', False):
            self.actionPolyCreate.triggered.connect(lambda: self.polygon_manager.increment_pid())
            self.actionPolyCreate.triggered.connect(lambda: self.polygon_manager.start_polygon(self.ui.mpl_canvas))
            # Deleting has to remove the polygon itself, not just the row --
            # TableFcn.delete_row matches on accessibleName (never set here)
            # and its polygon branch still speaks the old pyqtgraph API.
            self.actionPolyDelete.triggered.connect(self.delete_selected_polygons)
            self.actionPolyLink.triggered.connect(self.link_selected_polygons)
            self.actionPolyDelink.triggered.connect(self.unlink_selected_polygons)
            self.actionPolyRegion.triggered.connect(self.create_regions_from_polygons)
            self.actionPolyMovePoint.triggered.connect(
                lambda: self._set_edit_mode(self.actionPolyMovePoint, 'move'))
            self.actionPolyAddPoint.triggered.connect(
                lambda: self._set_edit_mode(self.actionPolyAddPoint, 'add'))
            self.actionPolyRemovePoint.triggered.connect(
                lambda: self._set_edit_mode(self.actionPolyRemovePoint, 'remove'))
            self.tableWidgetPolyPoints.selectionModel().selectionChanged.connect(self.view_selected_polygon)
            self.tableWidgetPolyPoints.selectionModel().selectionChanged.connect(self.update_action_states)
            self._polygon_signals_connected = True

        self.toggle_polygon_actions()

    # Polygon vertex editing
    # -------------------------------
    @property
    def _edit_actions(self):
        return (self.actionPolyMovePoint, self.actionPolyAddPoint, self.actionPolyRemovePoint)

    def _set_edit_mode(self, action, mode):
        """Toggle one of the three mutually-exclusive vertex-editing modes.

        Checking Move/Add/Remove Point unchecks the other two and arms the
        polygon manager's click handling on the live map canvas for that
        mode; unchecking it disarms editing (click-to-select stays). Mirrors
        ``ProfileDock._set_mode``.
        """
        checked = action.isChecked()
        for other in self._edit_actions:
            if other is not action:
                other.blockSignals(True)
                other.setChecked(False)
                other.blockSignals(False)

        if not checked:
            self.polygon_manager.set_edit_mode(None, self.ui.mpl_canvas)
            return

        # crop / profile point tools would fight over the same clicks
        self.ui.reset_checked_items('polygon')

        # An edit needs a target: fall back to the first polygon when none
        # is selected on the map or in the table.
        if self.polygon_manager.selected_poly is None:
            p_ids = self._selected_polygon_ids()
            polygons = self.polygon_manager.polygons.get(self.ui.app_data.sample_id, {})
            p_id = p_ids[0] if p_ids else next(iter(polygons), None)
            if p_id is not None:
                self.select_polygon_row(p_id)
                if self.ui.mpl_canvas is not None:
                    self.polygon_manager.draw_polygons(self.ui.mpl_canvas, p_id=p_id)

        self.polygon_manager.set_edit_mode(mode, self.ui.mpl_canvas)

    def exit_edit_mode(self):
        """Leave whichever edit mode is active (Esc / right-click on the map,
        or the polygon toggle going off)."""
        for action in self._edit_actions:
            action.blockSignals(True)
            action.setChecked(False)
            action.blockSignals(False)
        self.polygon_manager.set_edit_mode(None)

    def select_polygon_row(self, p_id):
        """Select `p_id`'s row in the table without triggering a redraw.

        Called by the manager when a polygon is picked on the map, so the
        table follows the canvas. The selection signals are blocked because
        `view_selected_polygon` would otherwise rebuild every artist.
        """
        table = self.tableWidgetPolyPoints
        selection = table.selectionModel()
        if selection is None:
            return
        selection.blockSignals(True)
        try:
            table.clearSelection()
            for row in range(table.rowCount()):
                item = table.item(row, 0)
                if item is not None and int(item.text()) == p_id:
                    table.selectRow(row)
                    break
        finally:
            selection.blockSignals(False)
        self.update_action_states()

    def _update_edit_action_states(self):
        """Move/Add/Remove Point need polygon mode on and a polygon to edit."""
        available = self.polygon_toggle.isChecked() and self.tableWidgetPolyPoints.rowCount() > 0
        for action in self._edit_actions:
            action.setEnabled(available)
        if not available and self.polygon_manager.edit_mode is not None:
            self.exit_edit_mode()


    def polygon_state_changed(self):
        self.ui.polygon_state = self.polygon_toggle.isChecked()
        if self.polygon_toggle.isChecked():
            # self.ui.update_plot_type_combobox()
            if (hasattr(self.ui, "profile_dock")):
                self.ui.profile_dock.profile_toggle.setChecked(False)
                self.ui.profile_dock.profile_state_changed()
        else:
            # polygons are no longer drawn, so stop listening to the map
            self.exit_edit_mode()
            self.polygon_manager.disconnect()

        self.toggle_polygon_actions()


        self.ui.schedule_update()
        self.toggle_polygon_actions()

    def toggle_polygon_actions(self):
        """Toggle enabled state of polygon actions based on ``self.polygon_toggle`` checked state."""
        if self.polygon_toggle.isChecked():
            self.actionEdgeDetect.setEnabled(True)
            self.comboBoxEdgeDetectMethod.setEnabled(True)
            self.actionPolyCreate.setEnabled(True)
            self.actionPolySave.setEnabled(False)
        else:
            self.actionEdgeDetect.setEnabled(False)
            self.comboBoxEdgeDetectMethod.setEnabled(False)
            self.actionPolyCreate.setEnabled(False)
            if self.tableWidgetPolyPoints.rowCount() > 0:
                self.actionPolySave.setEnabled(False)

        self._update_edit_action_states()

        # Delete/Link/Unlink/Create Region follow the *selection*, not the
        # polygon-mode toggle: existing polygons can be grouped, turned into
        # regions or removed whether or not drawing is on.
        self.update_action_states()

    def _selected_polygon_ids(self):
        """Ids of the polygons the user is acting on.

        The table's selected rows, or -- when nothing is selected there -- the
        polygon currently selected on the map, so clicking a region and hitting
        Delete works without touching the table.
        """
        polygons = self.polygon_manager.polygons.get(self.ui.app_data.sample_id, {})

        selection = self.tableWidgetPolyPoints.selectionModel()
        ids = []
        if selection is not None:
            for idx in selection.selectedRows():
                item = self.tableWidgetPolyPoints.item(idx.row(), 0)
                if item is not None:
                    ids.append(int(item.text()))

        if not ids:
            selected = self.polygon_manager.selected_poly
            if selected is not None:
                ids = [selected.p_id]

        return [p_id for p_id in ids if p_id in polygons]

    def delete_selected_polygons(self):
        """Delete every selected polygon (toolbar action and context menu).

        The canvas Delete key goes through ``PolygonManager.onkey`` to the same
        ``remove_polygons``.
        """
        p_ids = self._selected_polygon_ids()
        if not p_ids:
            return

        self.polygon_manager.remove_polygons(p_ids)
        self.refresh_polygons()
        if self.ui.mpl_canvas is not None:
            self.polygon_manager.draw_polygons(self.ui.mpl_canvas)

    def eventFilter(self, obj, event):
        """Delete/Backspace on the polygon table deletes the selected rows.

        The canvas has its own Delete handler (`PolygonManager.onkey`); this
        covers the case where the table, not the map, has focus.
        """
        # An event filter stays installed on the watched widget after this tab
        # has been torn down, and Qt keeps delivering to it -- reading the
        # attribute directly then raises AttributeError out of the event loop,
        # which surfaces as an unrelated failure in whatever runs next.
        table = getattr(self, 'tableWidgetPolyPoints', None)
        if table is not None and obj is table and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                self.delete_selected_polygons()
                return True

        return super().eventFilter(obj, event)

    def show_polygon_context_menu(self, pos):
        """Right-click menu on the polygon table: delete the selection.

        Right-clicking a row outside the current selection replaces the
        selection with that row first (standard table convention).
        """
        table = self.tableWidgetPolyPoints
        row = table.rowAt(pos.y())
        if row >= 0:
            selection = table.selectionModel()
            selected_rows = {idx.row() for idx in selection.selectedRows()} if selection else set()
            if row not in selected_rows:
                table.clearSelection()
                table.selectRow(row)

        p_ids = self._selected_polygon_ids()
        if not p_ids:
            return

        menu = QMenu(table)
        label = "Delete Polygon" if len(p_ids) == 1 else f"Delete {len(p_ids)} Polygons"
        action_delete = menu.addAction(label)
        viewport = table.viewport()
        chosen = menu.exec(viewport.mapToGlobal(pos) if viewport else table.mapToGlobal(pos))

        if chosen is action_delete:
            self.delete_selected_polygons()

    def update_action_states(self, *args, **kwargs):
        """Enable the selection-driven actions only when they'd do something."""
        p_ids = self._selected_polygon_ids()
        self.actionPolyDelete.setEnabled(bool(p_ids))
        self.actionPolyRegion.setEnabled(bool(p_ids))

        polygons = self.polygon_manager.polygons.get(self.ui.app_data.sample_id, {})
        selected = [polygons[p_id] for p_id in p_ids if p_id in polygons]
        groups = {p.group for p in selected}

        # Linking needs two or more polygons that aren't already one group;
        # unlinking needs a selected polygon that is in a group.
        already_one_group = len(groups) == 1 and None not in groups
        self.actionPolyLink.setEnabled(len(selected) > 1 and not already_one_group)
        self.actionPolyDelink.setEnabled(any(p.group is not None for p in selected))

    def link_selected_polygons(self):
        """Link the selected polygons into one region."""
        group = self.polygon_manager.link_polygons(self._selected_polygon_ids())
        if group is None:
            return
        self.refresh_polygons()
        self._redraw_polygons()

    def unlink_selected_polygons(self):
        """Split the selected polygons back into separate regions."""
        if not self.polygon_manager.unlink_polygons(self._selected_polygon_ids()):
            return
        self.refresh_polygons()
        self._redraw_polygons()

    def _redraw_polygons(self):
        """Redraw on the current canvas, if there is one."""
        if self.ui.mpl_canvas is not None:
            self.polygon_manager.draw_polygons(self.ui.mpl_canvas)

    def create_regions_from_polygons(self):
        """Turn the selected polygons into regions of interest.

        One region per linked group; an unlinked polygon is a region of its
        own ("analyzed as separate regions or linked for combined analysis").
        Re-running updates the regions already created from the same polygons
        rather than piling up duplicates.

        The region is a snapshot of the geometry -- editing the polygons
        afterwards doesn't move it until this is run again. From here on it is
        an ordinary ROI: it shows up in the ROI table, the ROI map, and the
        per-region statistics in the Stoichiometry dock.
        """
        data = self.ui.app_data.current_data
        if data is None:
            return

        p_ids = self._selected_polygon_ids()
        if not p_ids:
            return

        created = updated = 0
        for key, members in self.polygon_manager.groups(p_ids=p_ids):
            geometry = [
                {'verts': [(float(x), float(y)) for x, y in p.verts], 'in_out': p.in_out}
                for p in members if p.enabled
            ]
            if not geometry:
                continue  # every member excluded from analysis

            kind, ident = key
            source = f'{kind}:{ident}'
            existing = data.polygon_roi_for_source(source)
            if existing is not None:
                data.update_polygon_roi(existing, geometry)
                updated += 1
                continue

            name = f'Polygon group {ident}' if kind == 'group' else f'Polygon {ident}'
            color = self.ui.style_data.set_default_cluster_colors(len(data.roi_stack) + 1)[-1]
            data.add_polygon_roi(geometry, name=name, color=color, source=source)
            created += 1

        if not (created or updated):
            return

        # the ROI table lives on the filter tab
        self.dock.filter_tab.update_roi_table_widget()
        self.ui.schedule_update()
        log(f"polygon regions created={created} updated={updated}", prefix="Mask")

    def refresh_polygons(self):
        """Resync the table and the mask after the polygon set changed.

        The single entry point for *model* changes (drawn, deleted, loaded).
        Redrawing on its own must not come through here -- see
        ``PolygonManager.clear_polygons``.
        """
        self.update_table_widget()
        self.apply_polygon_mask(update_plot=True)
        # the edit buttons come alive with the first polygon and go with the last
        self._update_edit_action_states()
        self.update_action_states()

    def update_table_widget(self, *args, **kwargs):
        """Rebuild the polygon table from the polygon model."""
        sample_id = self.ui.app_data.sample_id
        table = self.tableWidgetPolyPoints

        # Always clear, even for a sample with no polygons: leaving the
        # previous sample's rows behind made the mask look up polygon ids that
        # don't exist for this sample (a KeyError part-way through
        # MainWindow.change_sample).
        # The selection model is its own QObject, so it needs blocking too --
        # otherwise clearing rows fires selectionChanged and redraws the canvas
        # part-way through the rebuild.
        table.blockSignals(True)
        selection = table.selectionModel()
        if selection is not None:
            selection.blockSignals(True)
        table.clearContents()
        table.setRowCount(0)

        polygons = self.polygon_manager.polygons.setdefault(sample_id, {})

        for row, (p_id, polygon) in enumerate(polygons.items()):
            table.insertRow(row)

            table.setItem(row, 0, QTableWidgetItem(str(p_id)))
            table.setItem(row, 1, QTableWidgetItem(polygon.display_name))
            # Link column: which group this polygon is linked into, if any
            table.setItem(row, 2, QTableWidgetItem(
                f'Group {polygon.group}' if polygon.group is not None else ''
            ))

            in_out = QComboBox()
            in_out.addItems(['In', 'Out'])
            in_out.setCurrentText('Out' if polygon.is_out else 'In')
            in_out.currentTextChanged.connect(self._make_in_out_callback(p_id))
            table.setCellWidget(row, 3, in_out)

            checkBox = QCheckBox()
            checkBox.setChecked(bool(polygon.enabled))
            checkBox.stateChanged.connect(self._make_enabled_callback(p_id))
            table.setCellWidget(row, 4, checkBox)

        if selection is not None:
            selection.blockSignals(False)
        table.blockSignals(False)

    def _make_in_out_callback(self, p_id):
        """Write the In/Out choice back to the polygon, then remask."""
        def callback(text):
            polygon = self.polygon_manager.polygons.get(self.ui.app_data.sample_id, {}).get(p_id)
            if polygon is None:
                return
            polygon.in_out = text.lower()
            self.apply_polygon_mask(update_plot=True)
        return callback

    def _make_enabled_callback(self, p_id):
        """Write the 'Analysis' checkbox back to the polygon, then remask."""
        def callback(state):
            polygon = self.polygon_manager.polygons.get(self.ui.app_data.sample_id, {}).get(p_id)
            if polygon is None:
                return
            polygon.enabled = state == Qt.CheckState.Checked.value
            self.apply_polygon_mask(update_plot=True)
        return callback

    def view_selected_polygon(self, *args):
        """Highlight the polygon selected in the table widget."""
        sample_id = self.ui.app_data.sample_id
        polygons = self.polygon_manager.polygons.get(sample_id, {})
        if not polygons:
            return

        selected_rows = self.tableWidgetPolyPoints.selectionModel().selectedRows()
        if not selected_rows:
            return

        polygon_id_item = self.tableWidgetPolyPoints.item(selected_rows[0].row(), 0)
        if not polygon_id_item:
            return

        polygon_id = int(polygon_id_item.text())
        if polygon_id in polygons and self.ui.mpl_canvas is not None:
            self.polygon_manager.draw_polygons(self.ui.mpl_canvas, p_id=polygon_id)

    # Polygon mask functions
    # -------------------------------
    def apply_polygon_mask(self, update_plot=True):
        """Creates the polygon mask for masking data

        Updates ``MainWindow.data[sample_id].polygon_mask`` and if ``update_plot==True``, updates ``MainWindow.data[sample_id].mask``.

        Parameters
        ----------
        update_plot : bool, optional
            If true, triggers a plot update via ``MainWindow.schedule_update``, by default True
        """
        sample_id = self.ui.app_data.sample_id
        if not sample_id or sample_id not in self.ui.data:
            return

        d = self.ui.data[sample_id]

        # Read the polygons themselves rather than the table's rows -- the
        # table is a view of this, and the two used to drift apart (e.g. a
        # polygon deleted on the canvas left its row behind).
        polygons = self.polygon_manager.polygons.get(sample_id, {})
        # Groups are passed through so an 'out' polygon linked into a group
        # holes that group only -- see polygon_mask's notes.
        enabled = [(p.verts, p.in_out, p.group) for p in polygons.values() if p.enabled]

        d.polygon_mask = polygon_mask(enabled, d.array_size, d.order, len(d.processed))

        # Update toolbar actions. Whether the mask is *applied* belongs to the
        # PolygonMask toggle (MainWindow.toggle_polygon_mask), so it is left
        # alone here -- forcing it on meant the user could never switch it off.
        has_polygons = bool(polygons)
        self.ui.lame_action.PolygonMask.setEnabled(has_polygons)
        if has_polygons:
            self.ui.lame_action.ClearFilters.setEnabled(True)

        # recompute combined mask
        d.recompute_mask()

        if update_plot:
            self.ui.schedule_update()

    def toggle_edge_detection(self):
        """Toggles edge detection to the current laser map plot.

        Executes on change of ``self.comboBoxEdgeDetectMethod`` when ``self.toolButtonEdgeDetect`` is checked.
        """
        if self.actionEdgeDetect.isChecked() == Qt.CheckState.Checked:
            self.ui.app_data.edge_detection_method = self.comboBoxEdgeDetectMethod.currentText()
            self.ui.noise_reduction.add_edge_detection()
        else:
            self.ui.noise_reduction.remove_edge_detection()


@auto_log_methods(logger_key='Mask')
class ClusterTab(QWidget):
    def __init__(self, dock):
        super().__init__(dock)
        self.setObjectName("Cluster Tab")

        self.logger_key = 'Mask'

        self.dock = dock

        self.ui = self.dock.ui
        #init table_fcn
        self.table_fcn = TableFcn(self)

        # Read by _cluster_row_color_changed/update_table_widget/update_clusters
        # as a reentrancy guard. It was never initialised here -- only AppData
        # has its own copy -- so recoloring a row before the first table build
        # raised AttributeError.
        self.updating_cluster_table_flag = False

        self.setup_ui()

    def setup_ui(self):
        tab_layout = QVBoxLayout()
        tab_layout.setContentsMargins(6, 6, 6, 6)
        self.setLayout(tab_layout)

        # Create actions for toolbar (will be added to common toolbar)
        self.create_actions()

        self.cluster_table = CustomTableWidget()
        self.cluster_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.cluster_table.setObjectName("cluster_table")
        self.cluster_table.setColumnCount(6)
        self.cluster_table.setRowCount(0)

        header = self.cluster_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.cluster_table.setHorizontalHeaderLabels(["", "Name", "Link", "Color", "% Total", "% Filtered"])

        tab_layout.addWidget(self.cluster_table)

        cluster_icon = QIcon(":/resources/icons/icon-cluster-64.svg")
        self.dock.tab_widgets.addTab(self, cluster_icon, "Clusters")

    def create_actions(self):
        """Create toolbar actions for the cluster tab"""
        self.actionClusterColorReset = CustomAction(
            text="",
            light_icon_unchecked="icon-reset-64.svg",
            dark_icon_unchecked="icon-reset-dark-64.svg",
            parent=self )
        self.actionClusterColorReset.setToolTip("Reset cluster colors")

        self.actionClusterLink = CustomAction(
            text="Link Clusters",
            light_icon_unchecked="icon-link-64.svg",
            dark_icon_unchecked="icon-link-dark-64.svg",
            parent=self )
        self.actionClusterLink.setToolTip("Create a link between clusters")

        self.actionClusterDelink = CustomAction(
            text="Remove Link",
            light_icon_unchecked="icon-unlink-64.svg",
            dark_icon_unchecked="icon-unlink-dark-64.svg",
            parent=self )
        self.actionClusterDelink.setToolTip("Remove link between clusters")

        # Reuses the ROI-add icon (and, like FilterTab.action_add_roi, has no
        # dark variant) -- this is the cluster counterpart of
        # PolygonTab.actionPolyRegion, and both produce ordinary ROIs.
        self.actionClusterRegion = CustomAction(
            text="Create Region",
            light_icon_unchecked="icon-roi-add-64.svg",
            parent=self )
        self.actionClusterRegion.setToolTip("Create a region of interest from the checked clusters")

        self.actionGroupMask = CustomAction(
            text="Create Cluster Mask",
            light_icon_unchecked="icon-mask-light-64.svg",
            dark_icon_unchecked="icon-mask-dark-64.svg",
            parent=self )
        self.actionGroupMask.setToolTip("Create a mask based on the currently selected clusters")

    def setup_toolbar_actions(self, toolbar):
        """Add cluster tab actions to the common toolbar"""
        toolbar.addAction(self.actionClusterColorReset)
        toolbar.addSeparator()
        toolbar.addAction(self.actionClusterLink)
        toolbar.addAction(self.actionClusterDelink)
        toolbar.addSeparator()
        toolbar.addAction(self.actionClusterRegion)
        toolbar.addSeparator()
        toolbar.addAction(self.actionGroupMask)

        if not getattr(self, '_cluster_signals_connected', False):
            self.actionClusterColorReset.triggered.connect(lambda: self.reset_cluster_colors())
            self.cluster_table.itemChanged.connect(self.cluster_label_changed)
            self.actionClusterLink.triggered.connect(lambda: self.link_checked_clusters())
            self.actionClusterDelink.triggered.connect(lambda: self.unlink_checked_clusters())
            self.actionClusterRegion.triggered.connect(lambda: self.create_regions_from_clusters())
            self.actionGroupMask.triggered.connect(lambda: self.ui.apply_cluster_mask(inverse=False))
            self._cluster_signals_connected = True

        self.toggle_cluster_actions()
        self.update_table_widget()

    def toggle_cluster_actions(self):
        enabled = bool(self.ui.data)
        self.actionClusterColorReset.setEnabled(enabled)
        self.actionGroupMask.setEnabled(enabled)
        # Link/Unlink/Create Region follow what is checked, not merely whether
        # data is loaded -- same rule as PolygonTab.update_action_states.
        self.update_action_states()

    def _cluster_entries(self):
        """The per-cluster entries of the active method, or ``{}``.

        ``cluster_dict[method]`` mixes int cluster ids with str settings keys;
        `src/data/cluster_groups.py` ignores the latter, so this just hands the
        method's dict over once the method has actually been run.
        """
        app_data = self.ui.app_data
        return app_data.cluster_dict.get(app_data.cluster_method, {})

    def _checked_cluster_ids(self):
        """Cluster ids whose row checkbox (column 0) is ticked.

        Row index is the cluster id -- `update_table_widget` builds the table
        that way. The table is ``NoSelection``, so checking *is* selecting
        here, which is the meaning `selected_clusters` and the docs already
        use.
        """
        ids = []
        for row in range(self.cluster_table.rowCount()):
            cb = self.cluster_table.cellWidget(row, 0)
            if cb is not None and cb.isChecked():
                ids.append(row)
        return ids

    def update_action_states(self):
        """Enable Link/Unlink/Create Region from what is currently checked."""
        entries = self._cluster_entries()
        checked = self._checked_cluster_ids()

        # Linking a set that is already exactly one group would do nothing.
        members = expand_to_groups(entries, checked)
        already_one_group = (
            len(members) > 1
            and len({group_of(entries, c) for c in members}) == 1
            and group_of(entries, members[0]) is not None
        )
        self.actionClusterLink.setEnabled(len(members) > 1 and not already_one_group)
        self.actionClusterDelink.setEnabled(any(group_of(entries, c) is not None for c in checked))
        self.actionClusterRegion.setEnabled(bool(checked) and self.ui.app_data.current_data is not None)

    def link_checked_clusters(self):
        """Link the checked clusters into one class.

        A clustering run often splits one mineral across several clusters;
        linking merges them for display and analysis. It never touches the
        labels in ``processed[method]``, so the clustering is unchanged and
        unlinking restores the original classes.
        """
        entries = self._cluster_entries()
        leader = link_clusters(entries, self._checked_cluster_ids())
        if leader is None:
            return
        self._after_group_change()
        log(f"clusters linked into group led by {leader}", prefix="Mask")

    def unlink_checked_clusters(self):
        """Split the checked clusters out of their groups."""
        entries = self._cluster_entries()
        if not unlink_clusters(entries, self._checked_cluster_ids()):
            return
        self._after_group_change()
        log("clusters unlinked", prefix="Mask")

    def _after_group_change(self):
        """Resync the table, the mask and the plot after linking/unlinking.

        Rebuilding the table re-ticks whole groups (see `update_clusters`), so
        the cluster mask has to be reapplied from the expanded selection.
        """
        self.update_table_widget()
        self.update_clusters()
        self.update_action_states()
        self.ui.schedule_update()

    def create_regions_from_clusters(self):
        """Turn the checked clusters into regions of interest.

        One region per linked group; an unlinked cluster is a region of its
        own -- the same rule as `PolygonTab.create_regions_from_polygons`.
        Re-running updates the regions already created from the same clusters
        rather than piling up duplicates.

        The region is a snapshot of which cluster ids belong to it, so
        re-linking afterwards doesn't move it until this is run again. From
        here on it is an ordinary ROI: it shows up in the ROI table, the ROI
        map, the region percentages and the per-region statistics in the
        Stoichiometry dock -- which is how a merged class gets reported as a
        single unit.
        """
        data = self.ui.app_data.current_data
        if data is None:
            return

        entries = self._cluster_entries()
        checked = set(expand_to_groups(entries, self._checked_cluster_ids()))
        if not checked:
            return

        method = self.ui.app_data.cluster_method
        created = updated = 0
        for leader, members in cluster_groups(entries):
            if not checked.intersection(members):
                continue

            source = f'cluster:{method}:{leader}'
            existing = data.roi_for_source(source)
            if existing is not None:
                data.update_cluster_roi(existing, method, members)
                updated += 1
                continue

            # Name and color come from the group leader, so the region matches
            # what the cluster map already shows for that class.
            entry = entries.get(leader, {})
            name = entry.get('name') or f'Cluster {leader + 1}'
            color = entry.get('color') or self.ui.style_data.set_default_cluster_colors(len(data.roi_stack) + 1)[-1]
            data.add_cluster_roi(method, members, name=name, color=color, source=source)
            created += 1

        if not (created or updated):
            return

        # the ROI table lives on the filter tab
        self.dock.filter_tab.update_roi_table_widget()
        self.ui.schedule_update()
        log(f"cluster regions created={created} updated={updated}", prefix="Mask")

    def _cluster_row_color_changed(self, row, hexcolor):
        """Updates a cluster's color when its own row's ColorButton (in
        ``cluster_table``'s Color column) is changed, writing it back into
        ``app_data.cluster_dict`` and refreshing the map if it's currently
        coloured by cluster.
        """
        if self.updating_cluster_table_flag or self.cluster_table.rowCount() == 0:
            return

        app_data = self.ui.app_data
        method = app_data.cluster_method
        entries = app_data.cluster_dict[method]

        # Linked clusters are one class and must stay one color, so recoloring
        # any member recolors the group. Rebuild the table so the other rows'
        # ColorButtons follow.
        members = expand_to_groups(entries, [row])
        for cluster_id in (members or [row]):
            entries[cluster_id]['color'] = hexcolor
        if len(members) > 1:
            self.update_table_widget()

        # update plot if currently coloring by cluster
        if app_data.c_field_type.lower() == 'cluster':
            self.ui.schedule_update()

    def update_table_widget(self):

        app_data = self.ui.app_data
        data = self.ui.data[app_data.sample_id]

        # # block signals
        self.cluster_table.blockSignals(True)
        # The per-row QCheckBoxes are separate widgets, so the table's own
        # blockSignals doesn't cover them -- this flag is what keeps
        # update_clusters out while the rows are being built.
        self.updating_cluster_table_flag = True

        # Clear the list widget.
        #
        # clearContents() drops the *items* but leaves the cell widgets (the
        # checkboxes and colour buttons) alive, so without the row reset a
        # sample that has not been clustered kept the previous sample's rows:
        # blank name/Link/% cells, but live checkboxes still reporting a
        # selection. The populating branch below sets the real count; every
        # path that finds no clusters now leaves the table genuinely empty,
        # which matters because update_action_states reads these rows.
        self.cluster_table.clearContents()
        self.cluster_table.setRowCount(0)
        self.cluster_table.setHorizontalHeaderLabels(['', 'Name', 'Link', 'Color', '% Total', '% Filtered'])
        method = app_data.cluster_method
        percentages = data.cluster_percentages(method)
        # Rebuilding must not silently drop the selection: linking rebuilds the
        # table, and the checkboxes are what `selected_clusters` (and so the
        # cluster mask) is read from.
        # `selected_clusters` is sometimes a numpy array (AppData seeds it from
        # the label array), so test it explicitly rather than for truthiness.
        selected = app_data.cluster_dict.get(method, {}).get('selected_clusters')
        checked = set() if selected is None else {int(c) for c in selected}
        if method in data.processed.columns:
            if not data.processed[method].empty:
                clusters = data.processed[method].dropna().unique()
                clusters.sort()
                if 99 in clusters:
                    self.cluster_table.setRowCount(len(clusters)-1)
                else:
                    self.cluster_table.setRowCount(len(clusters))

                for c in clusters:
                    if c == 99:
                        break
                    cluster_name = app_data.cluster_dict[method][c]['name']
                    hexcolor = app_data.cluster_dict[method][c]['color']

                    c = int(c)

                    # checkbox in col 0
                    def make_cb(cluster_id):
                        cb = QCheckBox()
                        cb.setChecked(cluster_id in checked)
                        cb.stateChanged.connect(lambda state, cid=cluster_id: self.update_clusters())
                        return cb
                    self.cluster_table.setCellWidget(c, 0, make_cb(c))
                    self.cluster_table.setItem(c, 1, QTableWidgetItem(cluster_name))

                    # Link column: which linked class this cluster belongs to,
                    # blank when it stands alone (see cluster_groups).
                    n_group = group_index(app_data.cluster_dict[method], c)
                    link_item = QTableWidgetItem(f'Group {n_group}' if n_group else '')
                    link_item.setFlags(link_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.cluster_table.setItem(c, 2, link_item)

                    # ColorButton shows the hex code as its own text (see
                    # blueberry.ColorButton) and opens a color picker on click --
                    # the per-row Color cell is the way to recolor a cluster (its
                    # colour drives the discrete cluster-map colormap, see
                    # StyleToolbox.get_cluster_colormap).
                    color_button = ColorButton(initial_color=hexcolor, ui=self.ui)
                    color_button.colorChanged.connect(lambda hexcolor, row=c: self._cluster_row_color_changed(row, hexcolor))
                    self.cluster_table.setCellWidget(c, 3, color_button)

                    pct = percentages.get(c, {'pct_total': 0.0, 'pct_filtered': 0.0})
                    pct_total_item = QTableWidgetItem(f"{pct['pct_total']:.1f}")
                    pct_total_item.setFlags(pct_total_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.cluster_table.setItem(c, 4, pct_total_item)

                    pct_filtered_item = QTableWidgetItem(f"{pct['pct_filtered']:.1f}")
                    pct_filtered_item.setFlags(pct_filtered_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.cluster_table.setItem(c, 5, pct_filtered_item)

        else:
            log(f"(group_changed) Cluster method, ({method}) is not defined", prefix="Error")

        #print(app_data.cluster_dict)
        self.cluster_table.blockSignals(False)
        self.updating_cluster_table_flag = False

        # The rows the actions are enabled from only exist now -- without this,
        # Link/Unlink/Create Region keep the state they had when the table was
        # empty until the user happens to toggle a checkbox.
        self.update_action_states()

    def cluster_label_changed(self, item):
        # Initialize the flag
        if not self.updating_cluster_table_flag: #change name only when cluster renamed
            # Get the new name and the row of the changed item
            new_name = item.text()

            row = item.row()
            if item.column() != 1:  # name is now col 1
                return

            app_data = self.ui.app_data
            method = app_data.cluster_method
            cluster_id = row

            entry = app_data.cluster_dict.get(method, {}).get(cluster_id)
            if entry is None:
                # The row doesn't name a cluster of the active method (a table
                # left over from another sample, say) -- nothing to rename.
                return

            old_name = entry['name']
            for i in range(self.cluster_table.rowCount()):
                if i != row and self.cluster_table.item(i, 1) and self.cluster_table.item(i, 1).text() == new_name:
                    # Duplicate name found, revert to the original name and show a warning
                    item.setText(old_name)
                    QMessageBox.warning(self, "Clusters", "Duplicate name not allowed.")
                    return

            # The name lives only in cluster_dict. This used to also write
            # new_name into processed[method], which is the numeric label
            # column -- pandas rejects a str there ("Invalid value for dtype
            # float64"), the exception was swallowed, and because that write
            # came first the rename never reached cluster_dict at all, so
            # renaming a cluster silently did nothing. The write was pointless
            # even when it worked: every consumer (get_cluster_colormap, the
            # stoichiometry dock's region list, this table) reads names from
            # cluster_dict, while strings in the label column would break
            # np.isin -- the cluster mask, cluster_percentages and
            # cluster-defined regions all match on integer ids.
            entry['name'] = new_name

            # A linked class is labelled by its leader, so renaming the leader
            # renames the class -- redraw the plot to pick it up.
            self.ui.schedule_update()

    def update_clusters(self, *args):
        """Executed on update to cluster table.

        Updates ``MainWindow.cluster_dict`` and plot when the selected cluster have changed.
        """        
        if not self.updating_cluster_table_flag:
            app_data = self.ui.app_data
            method = app_data.cluster_method
            entries = app_data.cluster_dict[method]

            # Checking one member of a linked class selects the whole class --
            # that is what makes the cluster mask group-aware, without
            # apply_cluster_mask needing to know about grouping at all.
            selected_clusters = expand_to_groups(entries, self._checked_cluster_ids())
            self._sync_checkboxes(selected_clusters)
            self.update_action_states()

            # update selected cluster list in cluster_dict
            if selected_clusters:
                if np.array_equal(app_data.cluster_dict[method]['selected_clusters'], selected_clusters):
                    return
                app_data.cluster_dict[method]['selected_clusters'] = selected_clusters
            else:
                app_data.cluster_dict[method]['selected_clusters'] = []

            # apply cluster mask and update plot
            self.ui.apply_cluster_mask()

    def _sync_checkboxes(self, checked_ids):
        """Tick exactly ``checked_ids``, without re-entering `update_clusters`."""
        checked = set(checked_ids)
        self.updating_cluster_table_flag = True
        try:
            for row in range(self.cluster_table.rowCount()):
                cb = self.cluster_table.cellWidget(row, 0)
                if cb is not None and cb.isChecked() != (row in checked):
                    cb.setChecked(row in checked)
        finally:
            self.updating_cluster_table_flag = False

    def reset_cluster_colors(self):
        """Resets all cluster colors to the default colormap.

        Updates ``app_data.cluster_dict`` and the Color column in
        ``self.cluster_table``, then updates the plot if currently
        coloring by cluster.
        """
        n = self.cluster_table.rowCount()
        if n == 0:
            return

        hexcolor = self.ui.style_data.set_default_cluster_colors(n)

        app_data = self.ui.app_data
        method = app_data.cluster_method

        entries = app_data.cluster_dict[method]
        for i, color in enumerate(hexcolor):
            entries[i]['color'] = color

        # Re-flatten each linked class onto its leader's color -- the default
        # colormap gives every cluster its own, which would split a merged
        # class back into several colors on the map.
        for leader, members in cluster_groups(entries):
            for cluster_id in members:
                entries[cluster_id]['color'] = entries[leader]['color']

        self.cluster_table.blockSignals(True)
        for i in range(n):
            button = self.cluster_table.cellWidget(i, 3)
            if button is not None:
                button.blockSignals(True)
                button.color = entries[i]['color']
                button.blockSignals(False)
        self.cluster_table.blockSignals(False)

        if app_data.c_field_type.lower() == 'cluster':
            self.ui.schedule_update()