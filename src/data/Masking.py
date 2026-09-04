from __future__ import annotations
import os
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.app.MainWindow import MainWindow
from PyQt6.QtCore import Qt, QSize, QEvent, pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel, QIcon, QFont, QIntValidator, QAction
from PyQt6.QtWidgets import (
        QMessageBox, QToolButton, QWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QGroupBox, QInputDialog,
        QDoubleSpinBox, QComboBox, QCheckBox, QSizePolicy, QListView, QToolBar, QAbstractItemView, QMenu,
        QLabel, QHeaderView, QTableWidget, QScrollArea, QMainWindow, QWidgetAction, QTabWidget, QDockWidget, QGridLayout,
        QSpacerItem,
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
from matplotlib.path import Path
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
        self.setMinimumSize(QSize(855, 367))
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
        self.setWidget(container)

        # Connect tab change signal to update toolbar visibility
        self.tab_widgets.currentChanged.connect(self.update_toolbar_for_tab)
        self.visibilityChanged.connect(self.update_tab_widget)
        
        # Initialize toolbar for the first tab
        self.update_toolbar_for_tab(0)

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
        print(f"DEBUG: MaskDock.apply_theme called with theme: {theme}")
        
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
            print(f"DEBUG: Applying style to QGroupBox: {groupbox.objectName()}")
            groupbox.setStyleSheet(groupbox_style)
            # Force style refresh safely
            if groupbox.style():
                groupbox.style().unpolish(groupbox)
                groupbox.style().polish(groupbox)
            groupbox.update()
        
        # Also apply specifically to filter_tools_groupbox if it exists
        if hasattr(self.filter_tab, 'filter_tools_groupbox'):
            print("DEBUG: Applying style to filter_tools_groupbox")
            self.filter_tab.filter_tools_groupbox.setStyleSheet(groupbox_style)
            # Force style refresh safely
            if self.filter_tab.filter_tools_groupbox.style():
                self.filter_tab.filter_tools_groupbox.style().unpolish(self.filter_tab.filter_tools_groupbox)
                self.filter_tab.filter_tools_groupbox.style().polish(self.filter_tab.filter_tools_groupbox)
            self.filter_tab.filter_tools_groupbox.update()
            print(f"Applied {theme} theme to filter_tools_groupbox")

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
        if active_id is None:
            current_data.filter_df = current_data.filter_df.iloc[0:0]
        else:
            entry = next((r for r in current_data.roi_stack if r['id'] == active_id), None)
            current_data.filter_df = entry['filter_df'].copy() if entry is not None else current_data.filter_df.iloc[0:0]
        self.update_filter_table(reload=True, apply=False)

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
        if active_id is None:
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
        if obj is self.roi_table.viewport() and event.type() == QEvent.Type.MouseButtonRelease:
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

        self.actionPolyMovePoint = CustomAction(
            text="Move Point",
            light_icon_unchecked="icon-move-point-64.svg",
            dark_icon_unchecked="icon-move-point-dark-64.svg",
            parent=self
        )
        self.actionPolyMovePoint.setToolTip("Move a profile point")

        self.actionPolyAddPoint = CustomAction(
            text="Add Point",
            light_icon_unchecked="icon-add-point-64.svg",
            dark_icon_unchecked="icon-add-point-dark-64.svg",
            parent=self
        )
        self.actionPolyAddPoint.setToolTip("Add a profile point")

        self.actionPolyRemovePoint = CustomAction(
            text="Remove Point",
            light_icon_unchecked="icon-remove-point-64.svg",
            dark_icon_unchecked="icon-remove-point-dark-64.svg",
            parent=self
        )
        self.actionPolyRemovePoint.setToolTip("Remove a profile point")

        self.actionPolyLink = CustomAction(
            text="Link Polygons",
            light_icon_unchecked="icon-link-64.svg",
            dark_icon_unchecked="icon-link-dark-64.svg",
            parent=self
        )
        self.actionPolyLink.setToolTip("Create a link between polygons")

        self.actionPolyDelink = CustomAction(
            text="Remove Link",
            light_icon_unchecked="icon-unlink-64.svg",
            dark_icon_unchecked="icon-unlink-dark-64.svg",
            parent=self
        )
        self.actionPolyDelink.setToolTip("Remove link between polygons")

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
        toolbar.addSeparator()
        toolbar.addAction(self.actionPolySave)
        toolbar.addAction(self.actionPolyDelete)
        
        if not getattr(self, '_polygon_signals_connected', False):
            self.actionPolyCreate.triggered.connect(lambda: self.polygon_manager.increment_pid())
            self.actionPolyCreate.triggered.connect(lambda: self.polygon_manager.start_polygon(self.ui.mpl_canvas))
            self.actionPolyDelete.triggered.connect(lambda: self.table_fcn.delete_row(self.tableWidgetPolyPoints))
            self.tableWidgetPolyPoints.selectionModel().selectionChanged.connect(self.view_selected_polygon)
            self._polygon_signals_connected = True

        #self.actionPolyCreate.triggered.connect(self.parent.data.polygon.create_new_polygon)
        #self.actionPolyMovePoint.triggered.connect(lambda: setattr(self.parent.data.polygon,'is_add_point_polygon', True))
        #self.actionPolyAddPoint.triggered.connect(lambda: setattr(self.parent.data.polygon,'is_moving_polygon', True))
        #self.actionPolyRemovePoint.triggered.connect(lambda: setattr(self.parent.data.polygon,'is_moving_polygon', True))

        self.toggle_polygon_actions()


    def polygon_state_changed(self):
        self.ui.polygon_state = self.polygon_toggle.isChecked()
        if self.polygon_toggle.isChecked():
            # self.ui.update_plot_type_combobox()
            if (hasattr(self.ui, "profile_dock")):
                self.ui.profile_dock.profile_toggle.setChecked(False)
                self.ui.profile_dock.profile_state_changed()

        self.toggle_polygon_actions()


        self.ui.schedule_update()
        self.toggle_polygon_actions()

    def toggle_polygon_actions(self):
        """Toggle enabled state of polygon actions based on ``self.polygon_toggle`` checked state."""
        if self.polygon_toggle.isChecked():
            self.actionEdgeDetect.setEnabled(True)
            self.comboBoxEdgeDetectMethod.setEnabled(True)
            self.actionPolyCreate.setEnabled(True)
            self.actionPolyMovePoint.setEnabled(False)
            self.actionPolyMovePoint.setChecked(False)
            self.actionPolyAddPoint.setEnabled(True)
            self.actionPolyAddPoint.setChecked(False)
            self.actionPolyRemovePoint.setEnabled(True)
            self.actionPolyRemovePoint.setChecked(True)
            self.actionPolyLink.setEnabled(True)
            self.actionPolyDelink.setEnabled(False)
            self.actionPolySave.setEnabled(False)
            self.actionPolyDelete.setEnabled(False)
        else:
            self.actionEdgeDetect.setEnabled(False)
            self.comboBoxEdgeDetectMethod.setEnabled(False)
            self.actionPolyCreate.setEnabled(False)
            if self.tableWidgetPolyPoints.rowCount() > 1:
                self.actionPolyLink.setEnabled(True)
                self.actionPolyDelink.setEnabled(True)
            if self.tableWidgetPolyPoints.rowCount() > 0:
                self.actionPolySave.setEnabled(False)
                self.actionPolyDelete.setEnabled(False)

    def update_table_widget(self, *args, **kwargs):
        """Update the polygon table (PyQt6 version)."""
        sample_id = self.ui.app_data.sample_id
        table = self.tableWidgetPolyPoints

        if sample_id in self.polygon_manager.polygons:
            table.clearContents()
            table.setRowCount(0)

            for p_id, _ in self.polygon_manager.polygons[sample_id].items():
                row_position = table.rowCount()
                table.insertRow(row_position)

                table.setItem(row_position, 0, QTableWidgetItem(str(p_id)))
                table.setItem(row_position, 1, QTableWidgetItem(f'Polygon {p_id}'))
                table.setItem(row_position, 2, QTableWidgetItem(''))
                table.setItem(row_position, 3, QTableWidgetItem('In'))

                checkBox = QCheckBox()
                checkBox.setChecked(True)
                # Correct slot signature for PyQt6 (int state)
                def make_cb_callback(p_id_inner):
                    return lambda state: self.apply_polygon_mask(update_plot=True)
                checkBox.stateChanged.connect(make_cb_callback(p_id))
                table.setCellWidget(row_position, 4, checkBox)

        self.apply_polygon_mask(update_plot=True)

    def view_selected_polygon(self, *args):
        """View the selected polygon when a selection is made in the table widget ."""
        sample_id = self.ui.app_data.sample_id

        if sample_id in self.polygon_manager.polygons:
            # Get selected rows (PyQt6 returns QModelIndex objects)
            selected_rows = self.tableWidgetPolyPoints.selectionModel().selectedRows()

            if selected_rows:
                # Assume only one row is selected for simplicity
                selected_row = selected_rows[0]
                polygon_id_item = self.tableWidgetPolyPoints.item(selected_row.row(), 0)

                if polygon_id_item:
                    polygon_id = int(polygon_id_item.text())

                    if polygon_id in self.polygon_manager.polygons[sample_id]:
                        # Clear all current polygons from the plot
                        self.polygon_manager.clear_plot()
                        # Plot the selected polygon on self.ax
                        self.polygon_manager.plot_existing_polygon(self.ui.mpl_canvas, polygon_id)

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

        # create array of all true
        self.ui.data[sample_id].polygon_mask = np.ones_like(self.ui.data[sample_id].mask, dtype=bool)

        # update toolbar actions
        self.ui.lame_action.ClearFilters.setEnabled(True)
        self.ui.lame_action.PolygonMask.setEnabled(True)
        self.ui.lame_action.PolygonMask.setChecked(True)
        self.ui.data[sample_id].polygon_mask_enabled = True

        # apply polygon mask — iterate each row in the polygon table
        for row in range(self.tableWidgetPolyPoints.rowCount()):
            checkBox = self.tableWidgetPolyPoints.cellWidget(row, 4)

            if checkBox.isChecked():
                pid = int(self.tableWidgetPolyPoints.item(row, 0).text())

                polygon_points = self.polygon_manager.polygons[sample_id][pid].verts
                polygon_points = [(x, y) for x, y in polygon_points]

                path = Path(polygon_points)

                # Polygon vertices are in imshow pixel-index space (col, row).
                # The image is produced by np.reshape(values, array_size, order=data.order).
                # For order='F': data[k] → matrix[k % nrows, k // nrows]
                #   → image position (col = k // nrows, row = k % nrows)
                # For order='C': data[k] → matrix[k // ncols, k % ncols]
                #   → image position (col = k % ncols, row = k // ncols)
                # Using this mapping makes containment match what the user drew.
                sample = self.ui.data[sample_id]
                nrows, ncols = sample.array_size
                order = sample.order
                n = len(sample.processed)
                k = np.arange(n, dtype=float)
                if order == 'F':
                    image_col = k // nrows
                    image_row = k % nrows
                else:
                    image_col = k % ncols
                    image_row = k // ncols
                points = np.column_stack([image_col, image_row])
                inside_polygon = path.contains_points(points)
                self.ui.data[sample_id].polygon_mask &= inside_polygon

        # recompute combined mask
        d = self.ui.data[sample_id]
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
            text="Link Polygons",
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
        toolbar.addAction(self.actionGroupMask)

        if not getattr(self, '_cluster_signals_connected', False):
            self.actionClusterColorReset.triggered.connect(lambda: self.reset_cluster_colors())
            self.cluster_table.itemChanged.connect(self.cluster_label_changed)
            self.actionGroupMask.triggered.connect(lambda: self.ui.apply_cluster_mask(inverse=False))
            self._cluster_signals_connected = True

        self.toggle_cluster_actions()
        self.update_table_widget()

    def toggle_cluster_actions(self):
        enabled = bool(self.ui.data)
        self.actionClusterColorReset.setEnabled(enabled)
        self.actionClusterLink.setEnabled(enabled)
        self.actionClusterDelink.setEnabled(enabled)
        self.actionGroupMask.setEnabled(enabled)

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
        app_data.cluster_dict[method][row]['color'] = hexcolor

        # update plot if currently coloring by cluster
        if app_data.c_field_type.lower() == 'cluster':
            self.ui.schedule_update()

    def update_table_widget(self):

        app_data = self.ui.app_data
        data = self.ui.data[app_data.sample_id]

        # # block signals
        self.cluster_table.blockSignals(True)

        # Clear the list widget
        self.cluster_table.clearContents()
        self.cluster_table.setHorizontalHeaderLabels(['', 'Name', 'Link', 'Color', '% Total', '% Filtered'])
        method = app_data.cluster_method
        percentages = data.cluster_percentages(method)
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

                    self.updating_cluster_table_flag = True
                    c = int(c)

                    # checkbox in col 0
                    def make_cb(cluster_id):
                        cb = QCheckBox()
                        cb.setChecked(False)
                        cb.stateChanged.connect(lambda state, cid=cluster_id: self.update_clusters())
                        return cb
                    self.cluster_table.setCellWidget(c, 0, make_cb(c))
                    self.cluster_table.setItem(c, 1, QTableWidgetItem(cluster_name))
                    self.cluster_table.setItem(c, 2, QTableWidgetItem(''))

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
            print(f'(group_changed) Cluster method, ({method}) is not defined')

        #print(app_data.cluster_dict)
        self.cluster_table.blockSignals(False)
        self.updating_cluster_table_flag = False

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

            old_name = app_data.cluster_dict[method][cluster_id]['name']
            for i in range(self.cluster_table.rowCount()):
                if i != row and self.cluster_table.item(i, 1) and self.cluster_table.item(i, 1).text() == new_name:
                    # Duplicate name found, revert to the original name and show a warning
                    item.setText(old_name)
                    QMessageBox.warning(self, "Clusters", "Duplicate name not allowed.")
                    return

            # Update processed data with the new name
            if method in self.ui.data[app_data.sample_id].processed.columns:
                # Find the rows where the value matches cluster_id
                rows_to_update = self.ui.data[app_data.sample_id].processed.loc[:, method] == cluster_id

                # Update these rows with the new name
                self.ui.data[app_data.sample_id].processed.loc[rows_to_update, method] = new_name

            # update current_group to reflect the new cluster name
            app_data.cluster_dict[method][cluster_id]['name'] = new_name

            # update plot with new cluster name
            # trigger update to plot
            self.ui.schedule_update()

    def update_clusters(self, *args):
        """Executed on update to cluster table.

        Updates ``MainWindow.cluster_dict`` and plot when the selected cluster have changed.
        """        
        if not self.updating_cluster_table_flag:
            app_data = self.ui.app_data
            selected_clusters = []
            method = app_data.cluster_method

            # get checked clusters from checkboxes in col 0
            for row in range(self.cluster_table.rowCount()):
                cb = self.cluster_table.cellWidget(row, 0)
                if cb is not None and cb.isChecked():
                    selected_clusters.append(row)
            selected_clusters.sort()

            # update selected cluster list in cluster_dict
            if selected_clusters:
                if np.array_equal(app_data.cluster_dict[method]['selected_clusters'], selected_clusters):
                    return
                app_data.cluster_dict[method]['selected_clusters'] = selected_clusters
            else:
                app_data.cluster_dict[method]['selected_clusters'] = []

            # apply cluster mask and update plot
            self.ui.apply_cluster_mask()

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

        self.cluster_table.blockSignals(True)
        for i, color in enumerate(hexcolor):
            app_data.cluster_dict[method][i]['color'] = color
            button = self.cluster_table.cellWidget(i, 3)
            if button is not None:
                button.blockSignals(True)
                button.color = color
                button.blockSignals(False)
        self.cluster_table.blockSignals(False)

        if app_data.c_field_type.lower() == 'cluster':
            self.ui.schedule_update()