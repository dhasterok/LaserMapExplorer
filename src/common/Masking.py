import os
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QStandardItem, QStandardItemModel, QIcon, QFont, QIntValidator, QAction
from PyQt6.QtWidgets import ( 
        QMessageBox, QToolButton, QWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QGroupBox, QInputDialog,
        QDoubleSpinBox, QComboBox, QCheckBox, QSizePolicy, QListView, QToolBar, QAbstractItemView,
        QLabel, QHeaderView, QTableWidget, QScrollArea, QMainWindow, QWidgetAction, QTabWidget, QDockWidget, QGridLayout,
        QSpacerItem,
    )
from src.common.CustomWidgets import (
    CustomDockWidget, CustomTableWidget, CustomLineEdit, CustomComboBox, ToggleSwitch
)
from src.app.FieldLogic import FieldLogicUI
# from pyqtgraph import ( ScatterPlotItem )
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.colors as colors
from matplotlib.collections import PathCollection
import numpy as np
import pandas as pd
from scipy.stats import percentileofscore

from src.app.UITheme import default_font
from src.app.config import BASEDIR
# Removed deprecated imports: get_hex_color, get_rgb_color - now using ColorManager
from src.common.ColorManager import convert_color

from src.common.TableFunctions import TableFcn as TableFcn
import src.common.format as fmt
from src.common.PolygonMatplotlib import PolygonManager
from src.common.Logger import LoggerConfig, auto_log_methods

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
    def __init__(self, ui=None, title="Masking Toolbox"):
        self.logger_key = 'Mask'

        if not isinstance(ui, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        super().__init__(ui)
        self.ui = ui
        # Note: Do not store self.data as property to avoid circular reference
        # Use self.ui.app_data.current_data in methods that need it
        
        # Initialize FieldLogicUI properly - use property to access current data
        FieldLogicUI.__init__(self, data=None)

        self.setObjectName("Mask Dock")
        self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.setFloating(False)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)

        ui.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self)

        #self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QSize(855, 367))
        self.setMaximumSize(QSize(524287, 524287))
        self.setFloating(False)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable)

        ui.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self)

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
    def data(self):
        """Access current data without storing reference to avoid circular dependency"""
        if hasattr(self.ui, 'app_data') and self.ui.app_data.current_data:
            return self.ui.app_data.current_data
        return None

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
    def __init__(self, dock):
        super().__init__(dock)
        self.setObjectName("Filter Tab")

        self.dock = dock
        self.ui = dock.ui

        self.logger_key = 'Mask'

        #init table_fcn
        self.table_fcn = TableFcn(self)

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

        filter_layout = QGridLayout(self.filter_tools_groupbox)
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

        filter_layout.addWidget(QLabel("Preset"), 0, 0, 1, 1, Qt.AlignmentFlag.AlignRight)
        filter_layout.addWidget(self.combo_filter_presets, 0, 1, 1, 5)

        filter_layout.addWidget(QLabel("Field type"), 1, 0, 1, 1, Qt.AlignmentFlag.AlignRight)
        filter_layout.addWidget(self.combo_field_type_type, 1, 1, 1, 2)
        filter_layout.addWidget(QLabel("Field"), 1, 3, 1, 1, Qt.AlignmentFlag.AlignRight)
        filter_layout.addWidget(self.combo_field, 1, 4, 1, 2)

        filter_layout.addWidget(QLabel("Min"), 2, 0, 1, 1, Qt.AlignmentFlag.AlignRight)
        filter_layout.addWidget(self.edit_filter_min, 2, 1, 1, 1)
        filter_layout.addWidget(self.spin_filter_min, 2, 2, 1, 1)
        filter_layout.addWidget(QLabel("Max"), 2, 3, 1, 1, Qt.AlignmentFlag.AlignRight)
        filter_layout.addWidget(self.edit_filter_max, 2, 4, 1, 1)
        filter_layout.addWidget(self.spin_filter_max, 2, 5, 1, 1)

        filter_layout.addWidget(QLabel("Operator"), 3, 0, 1, 1, Qt.AlignmentFlag.AlignRight)
        filter_layout.addWidget(self.combo_operator, 3, 1, 1, 1)

        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        group_layout.addItem(spacer)

        # Filter Table
        self.filter_table = CustomTableWidget(self)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.filter_table.sizePolicy().hasHeightForWidth())
        self.filter_table.setSizePolicy(sizePolicy)
        self.filter_table.setMinimumSize(QSize(400, 0))
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
            header.setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(5,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(6,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(7,QHeaderView.ResizeMode.ResizeToContents)

        self.filter_table.setHorizontalHeaderLabels(["Use", "Field Type", "Field", "Scale", "Min", "Max", "Operator", "Persistent"])

        horizontal_layout.addWidget(self.filter_tools_groupbox)
        horizontal_layout.addWidget(self.filter_table)

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
        self.action_add_filter = QAction("Add filter")
        icon_add_filter = QIcon(":/resources/icons/icon-filter-64.svg")
        self.action_add_filter.setIcon(icon_add_filter)
        self.action_add_filter.setToolTip("Add a filter using the properties set below")

        self.action_move_up = QAction("Move up")
        icon_up = QIcon(":/resources/icons/icon-up-arrow-64.svg")
        self.action_move_up.setIcon(icon_up)
        self.action_move_up.setToolTip("Move the selected filter line up")

        self.action_move_down = QAction("Move down")
        icon_down = QIcon(":/resources/icons/icon-down-arrow-64.svg")
        self.action_move_down.setIcon(icon_down)
        self.action_move_down.setToolTip("Move the selected filter line down")

        self.action_remove_filter = QAction("Delete filter")
        icon_delete = QIcon(":/resources/icons/icon-delete-64.svg")
        self.action_remove_filter.setIcon(icon_delete)
        self.action_remove_filter.setToolTip("Delete selected filters")

        self.action_select_all_filters = QAction("Select all")
        icon_select_all = QIcon(":/resources/icons/icon-select-all-64.svg")
        self.action_select_all_filters.setIcon(icon_select_all)
        self.action_select_all_filters.setToolTip("Select all filter lines")

        self.action_save_filters = QAction("Save filter")
        icon_save = QIcon(":/resources/icons/icon-save-file-64.svg")
        self.action_save_filters.setIcon(icon_save)
        self.action_save_filters.setToolTip("Save current filter table")

    def setup_toolbar_actions(self, toolbar):
        """Add filter tab actions to the common toolbar"""
        toolbar.addAction(self.action_add_filter)
        toolbar.addSeparator()
        toolbar.addAction(self.action_save_filters)
        toolbar.addSeparator()
        toolbar.addAction(self.action_select_all_filters)
        toolbar.addAction(self.action_move_up)
        toolbar.addAction(self.action_move_down)
        toolbar.addAction(self.action_remove_filter)

    def connect_widgets(self):
        # filter tab toolbar connections
        self.action_add_filter.triggered.connect(self.update_filter_table)
        self.action_add_filter.triggered.connect(lambda: self.apply_field_filters_update_plot())
        self.action_move_up.triggered.connect(lambda: self.table_fcn.move_row_up(self.filter_table))
        self.action_move_up.triggered.connect(lambda: self.apply_field_filters_update_plot())
        self.action_move_down.triggered.connect(lambda: self.table_fcn.move_row_down(self.filter_table))
        self.action_move_down.triggered.connect(lambda: self.apply_field_filters_update_plot())
        self.action_remove_filter.triggered.connect(self.remove_selected_rows)
        self.action_remove_filter.triggered.connect(lambda: self.table_fcn.delete_row(self.filter_table))
        self.action_remove_filter.triggered.connect(lambda: self.apply_field_filters_update_plot())
        self.action_save_filters.triggered.connect(self.save_filter_table)
        self.action_select_all_filters.triggered.connect(self.filter_table.selectAll)

        # filter widget connections
        self.combo_filter_presets.activated.connect(self.read_filter_table)
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
            self.ui.schedule_update()

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

    def update_filter_table(self, reload = False):
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
            """Update the 'use' value in the filter_df for the given row"""
            if current_data and row < len(current_data.filter_df):
                current_data.filter_df.at[row, 'use'] = state == Qt.CheckState.Checked

        # If reload is True, clear the table and repopulate it from filter_df
        if reload:
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
        current_data.apply_field_filters()

    def remove_selected_rows(self):
        """Remove selected rows from filter table.

        Removes selected rows from filter table and updates DataHandling filter_df.
        """
        current_data = self.ui.app_data.current_data
        if not current_data:
            return

        print(self.filter_table.selectedIndexes())

        # Collect indices to remove (from filter_df)
        indices_to_remove = []
        
        # We loop in reverse to avoid issues when removing rows
        for row in range(self.filter_table.rowCount()-1, -1, -1):
            chkBoxItem = self.filter_table.item(row, 7)
            if chkBoxItem and chkBoxItem.checkState() == Qt.CheckState.Checked:
                # Store the filter_df index (stored in row 0 as hidden data)
                filter_index = row  # In our case, table row corresponds to filter_df index
                indices_to_remove.append(filter_index)
                # Remove from table
                self.filter_table.removeRow(row)

        # Remove from DataHandling filter_df using new method
        for index in indices_to_remove:
            current_data.remove_filter(index)

        # Apply filters and update plot
        self.apply_field_filters_update_plot()

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
            
            # put filter_info into data and table
            current_data.filter_df = filter_info

            self.update_filter_table()
        except FileNotFoundError:
            QMessageBox.warning(self.ui, 'Error', f'Filter file {filter_file} not found.')
        except Exception as e:
            QMessageBox.warning(self.ui, 'Error', f'Error loading filter: {str(e)}')

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

        self.actionEdgeDetect = QAction("Toggle edge detection")
        icon_edge_detection = QIcon(":/resources/icons/icon-spotlight-64.svg")
        self.actionEdgeDetect.setCheckable(True)
        self.actionEdgeDetect.setChecked(False)
        self.actionEdgeDetect.setIcon(icon_edge_detection)
        self.actionEdgeDetect.setToolTip("Toggle edge detection")
        self.actionEdgeDetect.triggered.connect(self.toggle_edge_detection)

        self.comboBoxEdgeDetectMethod = QComboBox()
        self.comboBoxEdgeDetectMethod.addItems(["Sobel","Canny","Zero cross"])
        self.comboBoxEdgeDetectMethod.activated.connect(self.ui.control_dock.noise_reduction.add_edge_detection)

        self.actionPolyLoad = QAction("Load Polygon")
        icon_load_file = QIcon(":/resources/icons/icon-open-file-64.svg")
        self.actionPolyLoad.setIcon(icon_load_file)
        self.actionPolyLoad.setToolTip("Load polygons")

        self.actionPolyCreate = QAction("Create Polygon")
        icon_create_polygon = QIcon(":/resources/icons/icon-polygon-new-64.svg")
        self.actionPolyCreate.setIcon(icon_create_polygon)
        self.actionPolyCreate.setToolTip("Create a new polygon")

        self.actionPolyMovePoint = QAction("Move Point")
        icon_move_point = QIcon(":/resources/icons/icon-move-point-64.svg")
        self.actionPolyMovePoint.setIcon(icon_move_point)
        self.actionPolyMovePoint.setToolTip("Move a profile point")

        self.actionPolyAddPoint = QAction("Add Point")
        icon_add_point = QIcon(":/resources/icons/icon-add-point-64.svg")
        self.actionPolyAddPoint.setIcon(icon_add_point)
        self.actionPolyAddPoint.setToolTip("Add a profile point")

        self.actionPolyRemovePoint = QAction("Remove Point")
        icon_remove_point = QIcon(":/resources/icons/icon-remove-point-64.svg")
        self.actionPolyRemovePoint.setIcon(icon_remove_point)
        self.actionPolyRemovePoint.setToolTip("Remove a profile point")

        self.actionPolyLink = QAction("Link Polygons")
        icon_link = QIcon(":/resources/icons/icon-link-64.svg")
        self.actionPolyLink.setIcon(icon_link)
        self.actionPolyLink.setToolTip("Create a link between polygons")

        self.actionPolyDelink = QAction("Remove Link")
        icon_delink = QIcon(":/resources/icons/icon-unlink-64.svg")
        self.actionPolyDelink.setIcon(icon_delink)
        self.actionPolyDelink.setToolTip("Remove link between polygons")

        self.actionPolySave = QAction("Save Polygons")
        icon_save = QIcon(":/resources/icons/icon-save-file-64.svg")
        self.actionPolySave.setIcon(icon_save)
        self.actionPolySave.setToolTip("Save polygons to a file")

        self.actionPolyDelete = QAction("Delete Polygon")
        icon_delete = QIcon(":/resources/icons/icon-delete-64.svg")
        self.actionPolyDelete.setIcon(icon_delete)
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
        
        # initialise polygon dictionary for a given sample id in self.parent.data
        self.polygon_manager = PolygonManager(parent = self, main_window=self.ui)
        #self.ui.data.polygon = self.polygon_manger.polygons
        self.actionPolyCreate.triggered.connect(lambda: self.polygon_manager.increment_pid())
        self.actionPolyCreate.triggered.connect(lambda: self.polygon_manager.start_polygon(self.ui.mpl_canvas))
        self.actionPolyDelete.triggered.connect(lambda: self.table_fcn.delete_row(self.tableWidgetPolyPoints))
        self.tableWidgetPolyPoints.selectionModel().selectionChanged.connect(lambda: self.view_selected_polygon)

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
                    return lambda state: self.apply_polygon_mask(update_plot=True, p_id=p_id_inner)
                checkBox.stateChanged.connect(make_cb_callback(p_id))
                table.setCellWidget(row_position, 4, checkBox)

        self.apply_polygon_mask(update_plot=False)

    def view_selected_polygon(self):
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
                        self.polygon_manager.plot_existing_polygon(polygon_id)

    # Polygon mask functions
    # -------------------------------
    def apply_polygon_mask(self, update_plot=True):
        """Creates the polygon mask for masking data

        Updates ``MainWindow.data[sample_id].polygon_mask`` and if ``update_plot==True``, updates ``MainWindow.data[sample_id].mask``.

        Parameters
        ----------
        update_plot : bool, optional
            If true, calls ``MainWindow.apply_filters`` which also calls ``MainWindow.update_SV``, by default True
        """        
        sample_id = self.app_data.sample_id

        # create array of all true
        self.data[sample_id].polygon_mask = np.ones_like(self.data[sample_id].mask, dtype=bool)

        # remove all masks
        self.actionClearFilters.setEnabled(True)
        self.actionPolygonMask.setEnabled(True)
        self.actionPolygonMask.setChecked(True)

        # apply polygon mask
        # Iterate through each polygon in self.polygons[self.ui.sample_id]
        for row in range(self.tableWidgetPolyPoints.rowCount()):
            #check if checkbox is checked
            checkBox = self.tableWidgetPolyPoints.cellWidget(row, 4)

            if checkBox.isChecked():
                pid = int(self.tableWidgetPolyPoints.item(row,0).text())

                polygon_points = self.polygon.polygons[sample_id][pid].points
                polygon_points = [(x,y) for x,y,_ in polygon_points]

                # Convert the list of (x, y) tuples to a list of points acceptable by Path
                path = Path(polygon_points)

                # Create a grid of points covering the entire array
                # x, y = np.meshgrid(np.arange(self.array.shape[1]), np.arange(self.array.shape[0]))

                points = pd.concat([self.data[sample_id].processed['X'], self.data[sample_id].processed['Y']] , axis=1).values
                # Use the path to determine which points are inside the polygon
                inside_polygon = path.contains_points(points)

                # Reshape the result back to the shape of self.array
                inside_polygon_mask = np.array(inside_polygon).reshape(self.data[self.app_data.sample_id].array_size, order =  'C')
                inside_polygon = inside_polygon_mask.flatten('F')
                # Update the polygon mask - include points that are inside this polygon
                self.data[sample_id].polygon_mask &= inside_polygon

                #clear existing polygon lines
                #self.polygon.clear_lines()

        if update_plot:
            self.apply_filters(fullmap=False)

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

        self.tableWidgetViewGroups = CustomTableWidget()
        self.tableWidgetViewGroups.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.tableWidgetViewGroups.setObjectName("tableWidgetViewGroups")
        self.tableWidgetViewGroups.setColumnCount(3)
        self.tableWidgetViewGroups.setRowCount(0)
        
        header = self.tableWidgetViewGroups.horizontalHeader()
        if header:
            header.setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
        self.tableWidgetViewGroups.setHorizontalHeaderLabels(["Name", "Link", "Color"])

        tab_layout.addWidget(self.tableWidgetViewGroups)

        cluster_icon = QIcon(":/resources/icons/icon-cluster-64.svg")
        self.dock.tab_widgets.addTab(self, cluster_icon, "Clusters")

    def create_actions(self):
        """Create toolbar actions for the cluster tab"""
        self.labelClusterGroup = QLabel("Cluster")

        self.spinBoxClusterGroup = QDoubleSpinBox()

        self.toolButtonClusterColor = QToolButton()
        self.toolButtonClusterColor.setMaximumSize(QSize(18, 18))
        self.toolButtonClusterColor.setText("")

        self.actionClusterColorReset = QAction("Cluster Color Reset")
        icon_reset = QIcon(":/resources/icons/icon-reset-64.svg")
        self.actionClusterColorReset.setIcon(icon_reset)
        self.actionClusterColorReset.setToolTip("Reset cluster colors")

        self.actionClusterLink = QAction("Link Polygons")
        icon_link = QIcon(":/resources/icons/icon-link-64.svg")
        self.actionClusterLink.setIcon(icon_link)
        self.actionClusterLink.setToolTip("Create a link between clusters")

        self.actionClusterDelink = QAction("Remove Link")
        icon_delink = QIcon(":/resources/icons/icon-unlink-64.svg")
        self.actionClusterDelink.setIcon(icon_delink)
        self.actionClusterDelink.setToolTip("Remove link between clusters")

        self.actionGroupMask = QAction("Create Cluster Mask")
        icon_dark = QIcon(":/resources/icons/icon-mask-dark-64.svg")
        self.actionGroupMask.setIcon(icon_dark)
        self.actionGroupMask.setToolTip("Create a mask based on the currently selected clusters")

        self.actionGroupMaskInverse = QAction("Create Cluster Mask Inverse")
        icon_light = QIcon(":/resources/icons/icon-mask-light-64.svg")
        self.actionGroupMaskInverse.setIcon(icon_light)
        self.actionGroupMaskInverse.setToolTip("Create a mask based on the inverse of currently selected clusters")

    def setup_toolbar_actions(self, toolbar):
        """Add cluster tab actions to the common toolbar"""
        toolbar.addWidget(self.labelClusterGroup)
        toolbar.addWidget(self.spinBoxClusterGroup)
        toolbar.addWidget(self.toolButtonClusterColor)
        toolbar.addAction(self.actionClusterColorReset)
        toolbar.addSeparator()
        toolbar.addAction(self.actionClusterLink)
        toolbar.addAction(self.actionClusterDelink)
        toolbar.addSeparator()
        toolbar.addAction(self.actionGroupMask)
        toolbar.addAction(self.actionGroupMaskInverse)

        self.spinBoxClusterGroup.valueChanged.connect(self.select_cluster_group_callback)
        self.toolButtonClusterColor.clicked.connect(self.cluster_color_callback)
        self.actionClusterColorReset.triggered.connect(self.ui.style_data.set_default_cluster_colors)
        self.tableWidgetViewGroups.itemChanged.connect(self.cluster_label_changed)
        self.tableWidgetViewGroups.selectionModel().selectionChanged.connect(self.update_clusters)
        self.actionGroupMask.triggered.connect(lambda: self.ui.apply_cluster_mask(inverse=False))
        self.actionGroupMaskInverse.triggered.connect(lambda: self.ui.apply_cluster_mask(inverse=True))

        self.toggle_cluster_actions()
        self.update_table_widget()

    def toggle_cluster_actions(self):
        if self.ui.data:
            self.spinBoxClusterGroup.setEnabled(True)
            self.toolButtonClusterColor.setEnabled(True)
            self.actionClusterColorReset.setEnabled(True)
            self.actionClusterLink.setEnabled(True)
            self.actionClusterDelink.setEnabled(True)
            self.actionGroupMask.setEnabled(True)
            self.actionGroupMaskInverse.setEnabled(True)
        else:
            self.spinBoxClusterGroup.setEnabled(False)
            self.toolButtonClusterColor.setEnabled(False)
            self.actionClusterColorReset.setEnabled(False)
            self.actionClusterLink.setEnabled(False)
            self.actionClusterDelink.setEnabled(False)
            self.actionGroupMask.setEnabled(False)
            self.actionGroupMaskInverse.setEnabled(False)

    def cluster_color_callback(self):
        """Updates color of a cluster

        Uses ``QColorDialog`` to select new cluster color and then updates plot on change of
        backround ``self.toolButtonClusterColor`` color.  Also updates ``self.tableWidgetViewGroups``
        color associated with selected cluster.  The selected cluster is determined by ``self.spinBoxClusterGroup.value()``
        """
        #print('cluster_color_callback')
        if self.tableWidgetViewGroups.rowCount() == 0:
            return

        selected_cluster = int(self.spinBoxClusterGroup.value()-1)

        # change color
        self.ui.button_color_select(self.toolButtonClusterColor)
        color = convert_color(self.toolButtonClusterColor.palette().button().color(), 'qcolor', 'hex')
        color = color if color is not None else '#000000'
        self.ui.cluster_dict[self.ui.cluster_dict['active method']][selected_cluster]['color'] = color
        if self.tableWidgetViewGroups.item(selected_cluster,2).text() == color:
            return

        # update_table
        self.tableWidgetViewGroups.setItem(selected_cluster,2,QTableWidgetItem(color))

        # update plot
        if self.ui.comboBoxColorByField.currentText() == 'cluster':
            self.ui.schedule_update()

    def select_cluster_group_callback(self):
        """Set cluster color button background after change of selected cluster group

        Sets ``MainWindow.toolButtonClusterColor`` background on change of ``MainWindow.spinBoxClusterGroup``
        """
        if self.tableWidgetViewGroups.rowCount() == 0:
            return
        self.toolButtonClusterColor.setStyleSheet("background-color: %s;" % self.tableWidgetViewGroups.item(int(self.spinBoxClusterGroup.value()-1),2).text())

    def update_table_widget(self):
        
        app_data = self.ui.app_data
        data = self.ui.data[app_data.sample_id]
        
        # # block signals
        self.tableWidgetViewGroups.blockSignals(True)
        self.spinBoxClusterGroup.blockSignals(True)

        # Clear the list widget
        self.tableWidgetViewGroups.clearContents()
        self.tableWidgetViewGroups.setHorizontalHeaderLabels(['Name','Link','Color'])
        method = app_data.cluster_method
        if method in data.processed.columns:
            if not data.processed[method].empty:
                clusters = data.processed[method].dropna().unique()
                clusters.sort()
                # set number of rows in tableWidgetViewGroups
                # set default colors for clusters and update associated widgets
                self.spinBoxClusterGroup.setMinimum(1)
                if 99 in clusters:
                    self.tableWidgetViewGroups.setRowCount(len(clusters)-1)
                    self.spinBoxClusterGroup.setMaximum(len(clusters)-1)

                else:
                    self.tableWidgetViewGroups.setRowCount(len(clusters))
                    self.spinBoxClusterGroup.setMaximum(len(clusters))

                for c in clusters:
                    if c == 99:
                        break
                    cluster_name =  app_data.cluster_dict[method][c]['name']
                    hexcolor = app_data.cluster_dict[method][c]['color']
                    
                    
                    # Initialize the flag
                    self.updating_cluster_table_flag = True
                    c = int(c)
                    self.tableWidgetViewGroups.setItem(c, 0, QTableWidgetItem(cluster_name))
                    self.tableWidgetViewGroups.setItem(c, 1, QTableWidgetItem(''))
                    self.tableWidgetViewGroups.setItem(c, 2,QTableWidgetItem(hexcolor))
                    # colors in table are set by style_data.set_default_cluster_colors()
                    self.tableWidgetViewGroups.selectRow(c)
                    

        else:
            print(f'(group_changed) Cluster method, ({method}) is not defined')

        #print(app_data.cluster_dict)
        self.tableWidgetViewGroups.blockSignals(False)
        self.spinBoxClusterGroup.blockSignals(False)
        self.updating_cluster_table_flag = False

    def cluster_label_changed(self, item):
        # Initialize the flag
        if not self.updating_cluster_table_flag: #change name only when cluster renamed
            # Get the new name and the row of the changed item
            new_name = item.text()

            row = item.row()
            if item.column() > 0:
                return
            
            app_data = self.ui.app_data
            method = app_data.cluster_method
            # Extract the cluster id (assuming it's stored in the table)
            cluster_id = row

            old_name = app_data.cluster_dict[method][cluster_id]['name']
            # Check for duplicate names
            for i in range(self.tableWidgetViewGroups.rowCount()):
                if i != row and self.tableWidgetViewGroups.item(i, 0).text() == new_name:
                    # Duplicate name found, revert to the original name and show a warning
                    item.setText(old_name)
                    QMessageBox.warning(self, "Clusters", "Duplicate name not allowed.")
                    return

            # Update self.parent.data.processed with the new name
            if method in self.parent.data[app_data.sample_id].processed.columns:
                # Find the rows where the value matches cluster_id
                rows_to_update = self.parent.data[app_data.sample_id].processed.loc[:,method] == cluster_id

                # Update these rows with the new name
                self.parent.data[app_data.sample_id].processed.loc[rows_to_update, method] = new_name

            # update current_group to reflect the new cluster name
            app_data.cluster_dict[method][cluster_id]['name'] = new_name

            # update plot with new cluster name
            # trigger update to plot
            self.ui.schedule_update()

    def update_clusters(self):
        """Executed on update to cluster table.

        Updates ``MainWindow.cluster_dict`` and plot when the selected cluster have changed.
        """        
        if not self.updating_cluster_table_flag:
            app_data = self.ui.app_data
            selected_clusters = []
            method = app_data.cluster_method

            # get the selected clusters
            for idx in self.tableWidgetViewGroups.selectionModel().selectedRows():
                selected_clusters.append(idx.row())
            selected_clusters.sort()

            # update selected cluster list in cluster_dict
            if selected_clusters:
                if np.array_equal(app_data.cluster_dict[method]['selected_clusters'], selected_clusters):
                    return
                app_data.cluster_dict[method]['selected_clusters'] = selected_clusters
            else:
                app_data.cluster_dict[method]['selected_clusters'] = []

            # update plot
            if (self.ui.style_data.plot_type not in ['cluster', 'cluster score']) and (app_data.c_field_type == 'cluster'):
                # trigger update to plot
                self.ui.schedule_update()

    
        # cluster styles
    # -------------------------------------

    def set_default_cluster_colors(self,style_data,cluster_tab, mask=False):
        """Sets cluster group to default colormap

        Sets the colors in ``self.tableWidgetViewGroups`` to the default colormap in
        ``self.styles['cluster']['Colormap'].  Change the default colormap
        by changing ``self.comboBoxColormap``, when ``self.comboBoxFieldTypeC.currentText()`` is ``Cluster``.

        Returns
        -------
            str : hexcolor
        """

        #print('set_default_cluster_colors')
        # cluster_tab = self.parent.mask_dock.cluster_tab

        # cluster colormap
        cmap = style_data.get_colormap(N=self.tableWidgetViewGroups.rowCount())

        # set color for each cluster and place color in table
        colors = [cmap(i) for i in range(cmap.N)]

        hexcolor = []
        for i in range(self.tableWidgetViewGroups.rowCount()):
            hex_color = convert_color(colors[i], 'rgb', 'hex', norm_in=True)
            hexcolor.append(hex_color if hex_color is not None else '#000000')
            self.tableWidgetViewGroups.blockSignals(True)
            self.tableWidgetViewGroups.setItem(i,2,QTableWidgetItem(hexcolor[i]))
            self.tableWidgetViewGroups.blockSignals(False)

        if mask:
            hexcolor.append(style_data.style_dict['cluster']['OverlayColor'])

        self.toolButtonClusterColor.setStyleSheet("background-color: %s;" % self.tableWidgetViewGroups.item(self.spinBoxClusterGroup.value()-1,2).text())

        return hexcolor