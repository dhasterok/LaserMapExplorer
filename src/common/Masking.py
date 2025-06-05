import os
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QStandardItem, QStandardItemModel, QIcon, QFont, QIntValidator, QAction
from PyQt6.QtWidgets import ( 
        QMessageBox, QToolButton, QWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QGroupBox, QInputDialog,
        QDoubleSpinBox, QComboBox, QCheckBox, QSizePolicy, QFormLayout, QListView, QToolBar, QAbstractItemView,
        QLabel, QHeaderView, QTableWidget, QScrollArea, QMainWindow, QWidgetAction, QTabWidget, QDockWidget
    )
from src.common.CustomWidgets import (
    CustomDockWidget, CustomTableWidget, CustomLineEdit, CustomComboBox, ToggleSwitch
)
from src.app.UIControl import UIFieldLogic
from pyqtgraph import ( ScatterPlotItem )
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.colors as colors
from matplotlib.collections import PathCollection
import numpy as np
import pandas as pd
from scipy.stats import percentileofscore

from src.app.UITheme import default_font
from src.app.config import BASEDIR
from src.common.Polygon import PolygonManager
from src.common.colorfunc import get_hex_color, get_rgb_color

from src.common.TableFunctions import TableFcn as TableFcn
import src.common.format as fmt
from src.common.PolygonMatplotlib import PolygonManager
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

class MaskDock(CustomDockWidget, UIFieldLogic):
    def __init__(self, parent=None, title="Masking Toolbox", debug=False):
        if not isinstance(parent, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        super().__init__(parent)
        self.main_window = parent
        self.debug = debug
        self.data ={}
        if self.main_window.data and self.main_window.app_data.sample_id != '':
            self.data = self.main_window.data[self.main_window.app_data.sample_id]

        self.setObjectName("Mask Dock")
        self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.setWindowTitle(title)
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

        parent.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self)

        # create a container to hold the dock contents
        container = QWidget()
        container.setObjectName("Mask Dock Container")
        dock_layout = QVBoxLayout(container)

        # create a tab widget
        self.tabWidgetMask = QTabWidget(container)
        self.tabWidgetMask.setObjectName("Mask Tab Widget")

        self.filter_tab = FilterTab(self, debug=debug)
        self.polygon_tab = PolygonTab(self, debug=debug)
        self.cluster_tab = ClusterTab(self, debug=debug)

        dock_layout.addWidget(self.tabWidgetMask)
        self.setWidget(container)


        self.visibilityChanged.connect(self.update_tab_widget)
        #self.tabWidgetMask.currentChanged.connect(self.update_tab_widget)

    def update_tab_widget(self):
        if not self.isVisible():
            return

        self.filter_tab.update_filter_values()

class FilterTab():
    def __init__(self, parent, debug=False):
        self.parent = parent
        self.main_window = parent.main_window
        self.debug = debug

        

        #init table_fcn
        self.table_fcn = TableFcn(self)

        self.filter_tab = QWidget()
        self.filter_tab.setObjectName("Filter Tab")

        tab_layout = QVBoxLayout()
        tab_layout.setContentsMargins(6, 6, 6, 6)
        self.filter_tab.setLayout(tab_layout)

        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out

        self.actionFilterAdd = QAction("Add filter", toolbar)
        icon_add_filter = QIcon(":/resources/icons/icon-filter-64.svg")
        self.actionFilterAdd.setIcon(icon_add_filter)
        self.actionFilterAdd.setToolTip("Add a filter using the properties set below")

        self.actionFilterUp = QAction("Move up", toolbar)
        icon_up = QIcon(":/resources/icons/icon-up-arrow-64.svg")
        self.actionFilterUp.setIcon(icon_up)
        self.actionFilterUp.setToolTip("Move the selected filter line up")

        self.actionFilterDown = QAction("Move down", toolbar)
        icon_down = QIcon(":/resources/icons/icon-down-arrow-64.svg")
        self.actionFilterDown.setIcon(icon_down)
        self.actionFilterDown.setToolTip("Move the selected filter line down")

        # # There is currently a special function for removing rows, convert to table_fcn.delete_row
        self.actionFilterRemove = QAction("Delete filter", toolbar)
        icon_delete = QIcon(":/resources/icons/icon-delete-64.svg")
        self.actionFilterRemove.setIcon(icon_delete)
        self.actionFilterRemove.setToolTip("Add a filter using the properties set below")

        self.actionFilterSelectAll = QAction("Select all", toolbar)
        icon_select_all = QIcon(":/resources/icons/icon-select-all-64.svg")
        self.actionFilterSelectAll.setIcon(icon_select_all)
        self.actionFilterSelectAll.setToolTip("Select all filter lines")

        self.actionFilterSave = QAction("Save filter", toolbar)
        icon_save = QIcon(":/resources/icons/icon-save-file-64.svg")
        self.actionFilterSave.setIcon(icon_save)
        self.actionFilterSave.setToolTip("Add a filter using the properties set below")

        toolbar.addAction(self.actionFilterAdd)
        toolbar.addSeparator()
        toolbar.addAction(self.actionFilterSave)
        toolbar.addSeparator()
        toolbar.addAction(self.actionFilterSelectAll)
        toolbar.addAction(self.actionFilterUp)
        toolbar.addAction(self.actionFilterDown)
        toolbar.addAction(self.actionFilterRemove)


        tab_layout.addWidget(toolbar)

        horizontal_layout = QHBoxLayout()
        horizontal_layout.setContentsMargins(0,0,0,0)

        tab_layout.addLayout(horizontal_layout)

        # create groupbox for filter tools
        filter_tools_groupbox = QGroupBox()
        filter_tools_layout = QFormLayout(filter_tools_groupbox)
        filter_tools_layout.setContentsMargins(3, 0, 3, 0)
        filter_tools_groupbox.setLayout(filter_tools_layout)

        # preset combobox - use to create presets to include or exclude individual minerals etc.
        labelFilterPresets = QLabel("Preset", filter_tools_groupbox)
        self.comboBoxFilterPresets = QComboBox(filter_tools_groupbox)
        filter_tools_layout.addRow(labelFilterPresets, self.comboBoxFilterPresets)

        # field type and field comboboxes
        self.comboBoxFilterFieldType = CustomComboBox(filter_tools_groupbox)
        self.comboBoxFilterFieldType.popup_callback = lambda: self.main_window.update_field_type_combobox_options(self.comboBoxFilterFieldType, self.comboBoxFilterField, global_list=True)

        self.comboBoxFilterField = CustomComboBox(filter_tools_groupbox)
        self.comboBoxFilterField.popup_callback = lambda: self.main_window.update_field_combobox_options(self.comboBoxFilterField, self.comboBoxFilterFieldType, add_none=False)
        filter_tools_layout.addRow(self.comboBoxFilterFieldType, self.comboBoxFilterField)

        # minimum value for filter
        labelFMinVal = QLabel("Min value", filter_tools_groupbox)
        self.lineEditFMin = CustomLineEdit(filter_tools_groupbox)
        self.lineEditFMin.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditFMin.precision = 8
        self.lineEditFMin.toward = 0
        filter_tools_layout.addRow(labelFMinVal, self.lineEditFMin)

        # minimum quantile value for filter
        labelFMinQ = QLabel("Min quantile", filter_tools_groupbox)
        self.doubleSpinBoxFMinQ = QDoubleSpinBox(filter_tools_groupbox)
        self.doubleSpinBoxFMinQ.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.doubleSpinBoxFMinQ.setKeyboardTracking(False)
        self.doubleSpinBoxFMinQ.setMinimum(0.0)
        self.doubleSpinBoxFMinQ.setMaximum(100.0)
        filter_tools_layout.addRow(labelFMinQ, self.doubleSpinBoxFMinQ)

        # maximum value for filter
        labelFMaxVal = QLabel("Max value", filter_tools_groupbox)
        self.lineEditFMax = CustomLineEdit(filter_tools_groupbox)
        self.lineEditFMax.setMinimumSize(QSize(0, 0))
        self.lineEditFMax.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.lineEditFMax.precision = 8
        self.lineEditFMax.toward = 1
        filter_tools_layout.addRow(labelFMaxVal, self.lineEditFMax)
        
        # maximum quantile value for filter
        labelFMaxQ = QLabel("Max quantile", filter_tools_groupbox)
        self.doubleSpinBoxFMaxQ = QDoubleSpinBox(filter_tools_groupbox)
        self.doubleSpinBoxFMaxQ.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
        self.doubleSpinBoxFMaxQ.setKeyboardTracking(False)
        self.doubleSpinBoxFMaxQ.setMinimum(0.0)
        self.doubleSpinBoxFMaxQ.setMaximum(100.0)
        filter_tools_layout.addRow(labelFMaxQ, self.doubleSpinBoxFMaxQ)


        # filter operator
        labelFilterOperator = QLabel("Operator", filter_tools_groupbox)
        self.comboBoxFilterOperator = QComboBox(filter_tools_groupbox)
        self.comboBoxFilterOperator.clear()
        self.comboBoxFilterOperator.addItems(["and","or","not"])
        filter_tools_layout.addRow(labelFilterOperator, self.comboBoxFilterOperator)

        # Filter Table
        self.tableWidgetFilters = CustomTableWidget(self.filter_tab)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableWidgetFilters.sizePolicy().hasHeightForWidth())
        self.tableWidgetFilters.setSizePolicy(sizePolicy)
        self.tableWidgetFilters.setMinimumSize(QSize(400, 0))
        self.tableWidgetFilters.setMaximumSize(QSize(524287, 524287))
        self.tableWidgetFilters.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidgetFilters.setObjectName("tableWidgetFilters")
        self.tableWidgetFilters.setColumnCount(8)
        self.tableWidgetFilters.setRowCount(0)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.tableWidgetFilters.setHorizontalHeaderItem(0, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.tableWidgetFilters.setHorizontalHeaderItem(1, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.tableWidgetFilters.setHorizontalHeaderItem(2, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.tableWidgetFilters.setHorizontalHeaderItem(3, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.tableWidgetFilters.setHorizontalHeaderItem(4, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.tableWidgetFilters.setHorizontalHeaderItem(5, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.tableWidgetFilters.setHorizontalHeaderItem(6, item)

        item = QTableWidgetItem()
        item.setFont(default_font())
        self.tableWidgetFilters.setHorizontalHeaderItem(7, item)

        self.tableWidgetFilters.horizontalHeader().setDefaultSectionSize(80)
        header = self.tableWidgetFilters.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7,QHeaderView.ResizeMode.ResizeToContents)

        self.tableWidgetFilters.setHorizontalHeaderLabels(["Use", "Field Type", "Field", "Scale", "Min", "Max", "Operator", "Persistent"])

        horizontal_layout.addWidget(filter_tools_groupbox)
        horizontal_layout.addWidget(self.tableWidgetFilters)

        filter_icon = QIcon(":/resources/icons/icon-filter-64.svg")
        self.parent.tabWidgetMask.addTab(self.filter_tab, filter_icon, "Filters")

        # filter tab toolbar connections
        self.actionFilterAdd.triggered.connect(self.update_filter_table)
        self.actionFilterAdd.triggered.connect(lambda: self.apply_field_filters_update_plot())
        self.actionFilterUp.triggered.connect(lambda: self.table_fcn.move_row_up(self.tableWidgetFilters))
        self.actionFilterUp.triggered.connect(lambda: self.apply_field_filters_update_plot())
        self.actionFilterDown.triggered.connect(lambda: self.table_fcn.move_row_down(self.tableWidgetFilters))
        self.actionFilterDown.triggered.connect(lambda: self.apply_field_filters_update_plot())
        self.actionFilterRemove.triggered.connect(self.remove_selected_rows)
        self.actionFilterRemove.triggered.connect(lambda: self.table_fcn.delete_row(self.tableWidgetFilters))
        self.actionFilterRemove.triggered.connect(lambda: self.apply_field_filters_update_plot())
        self.actionFilterSave.triggered.connect(self.save_filter_table)
        self.actionFilterSelectAll.triggered.connect(self.tableWidgetFilters.selectAll)

        # filter widget connections
        self.comboBoxFilterPresets.activated.connect(self.read_filter_table)
        self.comboBoxFilterField.currentTextChanged.connect(self.update_filter_values)
        self.lineEditFMin.editingFinished.connect(self.callback_lineEditFMin)
        self.doubleSpinBoxFMinQ.valueChanged.connect(self.callback_doubleSpinBoxFMinQ)
        self.lineEditFMax.editingFinished.connect(self.callback_lineEditFMax)
        self.doubleSpinBoxFMaxQ.valueChanged.connect(self.callback_doubleSpinBoxFMaxQ)

        self.update_filter_values()
        self.load_filter_tables()

    def apply_field_filters_update_plot(self):
        """Updates filters in ``self.parent.data`` for given sample_id

        Updates the plot once filter values have been update
        """
        self.parent.data.apply_field_filters()
        self.main_window.plot_style.schedule_update()

    def update_filter_values(self):
        """Updates widgets that display the filter bounds for a selected field.

        Updates ``self.lineEditFMin`` and ``self.lineEditFMax`` values for display when the
        field in ``self.comboBoxFilterField`` is changed.
        """
        if self.parent.main_window.app_data.sample_id == '':
            return

        
        # field = self.comboBoxFilterField.currentText()
        # if not field:
        #     return
        if not (field := self.comboBoxFilterField.currentText()): return

        data = self.parent.data

        self.lineEditFMin.value = data[field].min()
        self.callback_lineEditFMin()
        self.lineEditFMax.value = data[field].max()
        self.callback_lineEditFMax()

    def callback_lineEditFMin(self):
        """Updates ``self.doubleSpinBoxFMinQ.value`` when ``self.lineEditFMin.value`` is changed"""        
        if self.parent.main_window.app_data.sample_id == '':
            return

        if (self.comboBoxFilterField.currentText() == '') or (self.comboBoxFilterFieldType.currentText() == ''):
            return

        data = self.parent.data

        try:
            array = data.get_map_data(self.comboBoxFilterField.currentText(), self.comboBoxFilterFieldType.currentText())['array'].dropna()
        except:
            return

        self.doubleSpinBoxFMinQ.blockSignals(True)
        self.doubleSpinBoxFMinQ.setValue(percentileofscore(array, self.lineEditFMin.value))
        self.doubleSpinBoxFMinQ.blockSignals(False)

    def callback_lineEditFMax(self):
        """Updates ``MainWindow.doubleSpinBoxFMaxQ.value`` when ``MainWindow.lineEditFMax.value`` is changed"""        
        if self.parent.main_window.app_data.sample_id == '':
            return

        if (self.comboBoxFilterField.currentText() == '') or (self.comboBoxFilterFieldType.currentText() == ''):
            return

        data = self.parent.data

        try:
            array = data.get_map_data(self.comboBoxFilterField.currentText(), self.comboBoxFilterFieldType.currentText())['array'].dropna()
        except:
            return

        self.doubleSpinBoxFMaxQ.blockSignals(True)
        self.doubleSpinBoxFMaxQ.setValue(percentileofscore(array, self.lineEditFMax.value))
        self.doubleSpinBoxFMaxQ.blockSignals(False)

    def callback_doubleSpinBoxFMinQ(self):
        """Updates ``MainWindow.lineEditFMin.value`` when ``MainWindow.doubleSpinBoxFMinQ.value`` is changed"""        
        array = self.parent.main_window.data[self.parent.main_window.sample_id].get_map_data(self.comboBoxFilterField.currentText(), self.comboBoxFilterFieldType.currentText())['array'].dropna()

        self.lineEditFMin.value = np.percentile(array, self.doubleSpinBoxFMinQ.value())

    def callback_doubleSpinBoxFMaxQ(self):
        """Updates ``MainWindow.lineEditFMax.value`` when ``MainWindow.doubleSpinBoxFMaxQ.value`` is changed"""        
        array = self.parent.main_window.data[self.parent.main_window.sample_id].get_map_data(self.comboBoxFilterField.currentText(), self.comboBoxFilterFieldType.currentText())['array'].dropna()

        self.lineEditFMax.value = np.percentile(array, self.doubleSpinBoxFMaxQ.value())

    def update_filter_table(self, reload = False):
        """Update data for analysis when fiter table is updated.

        Parameters
        ----------
        reload : bool, optional
            Reload ``True`` updates the filter table, by default False
        """
        # If reload is True, clear the table and repopulate it from 'filter_info'
        if reload:
            # Clear the table
            self.tableWidgetFilters.setRowCount(0)

            # Repopulate the table from 'filter_info'
            for index, row in self.parent.main_window.data[self.parent.main_window.sample_id].filter_df.iterrows():
                current_row = self.tableWidgetFilters.rowCount()
                self.tableWidgetFilters.insertRow(current_row)

                # Create and set the checkbox for 'use'
                chkBoxItem_use = QCheckBox()
                chkBoxItem_use.setCheckState(Qt.CheckState.Checked if row['use'] else Qt.CheckState.Unchecked)
                chkBoxItem_use.stateChanged.connect(lambda state, row=current_row: on_use_checkbox_state_changed(row, state))
                self.tableWidgetFilters.setCellWidget(current_row, 0, chkBoxItem_use)

                # Add other items from the row
                self.tableWidgetFilters.setItem(current_row, 1, QTableWidgetItem(row['field_type']))
                self.tableWidgetFilters.setItem(current_row, 2, QTableWidgetItem(row['field']))
                self.tableWidgetFilters.setItem(current_row, 3, QTableWidgetItem(row['scale']))
                self.tableWidgetFilters.setItem(current_row, 4, QTableWidgetItem(fmt.dynamic_format(row['min'])))
                self.tableWidgetFilters.setItem(current_row, 5, QTableWidgetItem(fmt.dynamic_format(row['max'])))
                self.tableWidgetFilters.setItem(current_row, 6, QTableWidgetItem(row['operator']))

                # Create and set the checkbox for selection (assuming this is a checkbox similar to 'use')
                chkBoxItem_select = QCheckBox()
                chkBoxItem_select.setCheckState(Qt.CheckState.Checked if row.get('select', False) else Qt.CheckState.Unchecked)
                self.tableWidgetFilters.setCellWidget(current_row, 7, chkBoxItem_select)

        else:
            # open tabFilterList
            self.parent.main_window.tabWidgetMask.setCurrentIndex(self.parent.main_window.mask_tab['filter'])

            def on_use_checkbox_state_changed(row, state):
                # Update the 'use' value in the filter_df for the given row
                self.parent.main_window.data[self.parent.main_window.sample_id].filter_df.at[row, 'use'] = state == Qt.CheckState.Checked

            field_type = self.comboBoxFilterFieldType.currentText()
            field = self.comboBoxFilterField.currentText()
            f_min = self.lineEditFMin.value
            f_max = self.lineEditFMax.value
            operator = self.comboBoxFilterOperator.currentText()
            # Add a new row at the end of the table
            row = self.tableWidgetFilters.rowCount()
            self.tableWidgetFilters.insertRow(row)

            # Create a QCheckBox for the 'use' column
            chkBoxItem_use = QCheckBox()
            chkBoxItem_use.setCheckState(Qt.CheckState.Checked)
            chkBoxItem_use.stateChanged.connect(lambda state, row=row: on_use_checkbox_state_changed(row, state))

            chkBoxItem_select = QTableWidgetItem()
            chkBoxItem_select.setFlags(Qt.ItemFlag.ItemIsUserCheckable |
                                Qt.ItemFlag.ItemIsEnabled)

            if 'Analyte' in field_type:
                chkBoxItem_select.setCheckState(Qt.CheckState.Unchecked)
                analyte_1 = field
                analyte_2 = None
                scale = self.parent.main_window.data[self.parent.main_window.sample_id].processed_data.get_attribute(field,'norm')
            elif 'Ratio' in field_type:
                chkBoxItem_select.setCheckState(Qt.CheckState.Unchecked)
                analyte_1, analyte_2 = field.split(' / ')
                scale = self.parent.main_window.data[self.parent.main_window.sample_id].processed_data.get_attribute(field,'norm')
            else:
                scale = 'linear'

            self.tableWidgetFilters.setCellWidget(row, 0, chkBoxItem_use)
            self.tableWidgetFilters.setItem(row, 1, QTableWidgetItem(field_type))
            self.tableWidgetFilters.setItem(row, 2, QTableWidgetItem(field))
            self.tableWidgetFilters.setItem(row, 3, QTableWidgetItem(scale))
            self.tableWidgetFilters.setItem(row, 4, QTableWidgetItem(fmt.dynamic_format(f_min)))
            self.tableWidgetFilters.setItem(row, 5, QTableWidgetItem(fmt.dynamic_format(f_max)))
            self.tableWidgetFilters.setItem(row, 6, QTableWidgetItem(operator))
            self.tableWidgetFilters.setItem(row, 7, chkBoxItem_select)

            filter_info = {'use':True, 'field_type': field_type, 'field': field, 'norm':scale ,'min': f_min,'max':f_max, 'operator':operator, 'persistent':True}
            self.parent.main_window.data[self.parent.main_window.sample_id].filter_df.loc[len(self.parent.main_window.data[self.parent.main_window.sample_id].filter_df)] = filter_info

        self.parent.data.apply_field_filters()

    def remove_selected_rows(self):
        """Remove selected rows from filter table.

        Removes selected rows from ``MainWindow.tableWidgetFilter``.
        """
        sample_id = self.parent.main_window.sample_id

        print(self.tableWidgetFilters.selectedIndexes())

        # We loop in reverse to avoid issues when removing rows
        for row in range(self.tableWidgetFilters.rowCount()-1, -1, -1):
            chkBoxItem = self.tableWidgetFilters.item(row, 7)
            field_type = self.tableWidgetFilters.item(row, 1).text()
            field = self.tableWidgetFilters.item(row, 2).text()
            if chkBoxItem.checkState() == Qt.CheckState.Checked:
                self.tableWidgetFilters.removeRow(row)
                self.parent.main_window.data[sample_id].filter_df.drop(self.parent.main_window.data[sample_id].filter_df[(self.parent.main_window.data[sample_id].filter_df['field'] == field)].index, inplace=True)

        self.parent.data.apply_field_filters()

    def save_filter_table(self):
        """Opens a dialog to save filter table

        Executes on ``MainWindow.toolButtonFilterSave`` is clicked.  The filter is added to
        ``MainWindow.tableWidgetFilters`` and save into a dictionary to a file with a ``.fltr`` extension.
        """
        name, ok = QInputDialog.getText(self.parent.main_window, 'Save filter table', 'Enter filter table name:')
        if ok:
            # file name for saving
            filter_file = os.path.join(BASEDIR,f'resources/filters/{name}.fltr')

            # save dictionary to file
            self.parent.main_window.data[self.parent.main_window.sample_id].filter_df.to_csv(filter_file, index=False)

            # update comboBox
            self.comboBoxFilterPresets.addItem(name)
            self.comboBoxFilterPresets.setCurrentText(name)

            self.parent.main_window.statusBar.showMessage(f'Filters successfully saved as {filter_file}')
        else:
            # throw a warning that name is not saved
            QMessageBox.warning(self.parent.main_window,'Error','could not save filter table.')

            return

    def load_filter_tables(self):
        """Loads filter names and adds them to the filter presets comboBox
        
        Looks for saved filter tables (*.fltr) in ``resources/filters/`` directory and adds them to
        ``self.comboBoxFilterPresets``.
        """
        # read filenames with *.sty
        file_list = os.listdir(os.path.join(BASEDIR,'resources/filters/'))
        filter_list = [file.replace('.fltr','') for file in file_list if file.endswith('.fltr')]

        # add default to list
        filter_list.insert(0,'')

        # update theme comboBox
        self.comboBoxFilterPresets.clear()
        self.comboBoxFilterPresets.addItems(filter_list)
        self.comboBoxFilterPresets.setCurrentIndex(0)

    def read_filter_table(self):
        filter_name = self.comboBoxFilterPresets.currentText()

        # If no filter_name is chosen, return
        if filter_name == '':
            return

        # open filter with name filter_name
        filter_file = os.path.join(BASEDIR,f'resources/filters/{filter_name}.fltr')
        filter_info = pd.read_csv(filter_file)

        # put filter_info into data and table
        self.main_window.data[self.main_window.app_data.sample_id].filter_df = filter_info

        self.update_filter_table()

class PolygonTab():
    def __init__(self, parent, debug=False):
        self.parent = parent
        
        self.debug = debug

        #init table_fcn
        self.table_fcn = TableFcn(self)

        self.polygon_tab = QWidget()
        self.polygon_tab.setObjectName("Polygon Tab")

        tab_layout = QVBoxLayout()
        tab_layout.setContentsMargins(6, 6, 6, 6)
        self.polygon_tab.setLayout(tab_layout)

        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out
        # profile toggle
        self.polygon_toggle = ToggleSwitch(toolbar, height=18, bg_left_color="#D8ADAB", bg_right_color="#A8B078")
        self.polygon_toggle.setChecked(False)
        self.actionPolyToggle = QWidgetAction(toolbar)
        self.actionPolyToggle.setDefaultWidget(self.polygon_toggle)
        self.polygon_toggle.stateChanged.connect(self.polygon_state_changed)

        self.actionEdgeDetect = QAction("Toggle edge detection", toolbar)
        icon_edge_detection = QIcon(":/resources/icons/icon-spotlight-64.svg")
        self.actionEdgeDetect.setIcon(icon_edge_detection)
        self.actionEdgeDetect.setToolTip("Add a filter using the properties set below")
        self.actionEdgeDetect.triggered.connect(self.parent.main_window.noise_reduction.add_edge_detection)

        self.comboBoxEdgeDetectMethod = QComboBox(toolbar)
        self.comboBoxEdgeDetectMethod.addItems(["Sobel","Canny","Zero cross"])

        self.actionPolyLoad = QAction("Load Polygon", toolbar)
        icon_load_file = QIcon(":/resources/icons/icon-open-file-64.svg")
        self.actionPolyLoad.setIcon(icon_load_file)
        self.actionPolyLoad.setToolTip("Load polygons")

        self.actionPolyCreate = QAction("Create Polygon", toolbar)
        icon_create_polygon = QIcon(":/resources/icons/icon-polygon-new-64.svg")
        self.actionPolyCreate.setIcon(icon_create_polygon)
        self.actionPolyCreate.setToolTip("Create a new polygon")

        self.actionPolyMovePoint = QAction("Move Point", toolbar)
        icon_move_point = QIcon(":/resources/icons/icon-move-point-64.svg")
        self.actionPolyMovePoint.setIcon(icon_move_point)
        self.actionPolyMovePoint.setToolTip("Move a profile point")

        self.actionPolyAddPoint = QAction("Add Point", toolbar)
        icon_add_point = QIcon(":/resources/icons/icon-add-point-64.svg")
        self.actionPolyAddPoint.setIcon(icon_add_point)
        self.actionPolyAddPoint.setToolTip("Add a profile point")

        self.actionPolyRemovePoint = QAction("Remove Point", toolbar)
        icon_remove_point = QIcon(":/resources/icons/icon-remove-point-64.svg")
        self.actionPolyRemovePoint.setIcon(icon_remove_point)
        self.actionPolyRemovePoint.setToolTip("Remove a profile point")

        self.actionPolyLink = QAction("Link Polygons", toolbar)
        icon_link = QIcon(":/resources/icons/icon-link-64.svg")
        self.actionPolyLink.setIcon(icon_link)
        self.actionPolyLink.setToolTip("Create a link between polygons")

        self.actionPolyDelink = QAction("Remove Link", toolbar)
        icon_delink = QIcon(":/resources/icons/icon-unlink-64.svg")
        self.actionPolyDelink.setIcon(icon_delink)
        self.actionPolyDelink.setToolTip("Remove link between polygons")

        self.actionPolySave = QAction("Save Polygons", toolbar)
        icon_save = QIcon(":/resources/icons/icon-save-file-64.svg")
        self.actionPolySave.setIcon(icon_save)
        self.actionPolySave.setToolTip("Save polygons to a file")

        self.actionPolyDelete = QAction("Delete Polygon", toolbar)
        icon_delete = QIcon(":/resources/icons/icon-delete-64.svg")
        self.actionPolyDelete.setIcon(icon_delete)
        self.actionPolyDelete.setToolTip("Delete selected polygons")

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

        tab_layout.addWidget(toolbar)
        
        self.tableWidgetPolyPoints = CustomTableWidget()
        self.tableWidgetPolyPoints.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableWidgetPolyPoints.setColumnCount(5)

        header = self.tableWidgetPolyPoints.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4,QHeaderView.ResizeMode.ResizeToContents)

        self.tableWidgetPolyPoints.setHorizontalHeaderLabels(["PolyID", "Name", "Link", "In/out", "Analysis"])
        

        tab_layout.addWidget(self.tableWidgetPolyPoints)

        polygon_icon = QIcon(":/resources/icons/icon-polygon-new-64.svg")
        self.parent.tabWidgetMask.addTab(self.polygon_tab, polygon_icon, "Polygons")
        
        # initialise polygon dictionary for a given sample id in self.parent.data
        self.polygon_manager = PolygonManager(parent = self, main_window = self.parent.main_window, debug=self.parent.main_window.logger_options['Polygon'])
        #self.parent.main_window.data.polygon = self.polygon_manger.polygons
        self.actionPolyCreate.triggered.connect(self.polygon_manager.increment_pid)
        self.actionPolyCreate.triggered.connect(lambda: self.polygon_manager.start_polygon(self.parent.main_window.mpl_canvas))
        self.actionPolyDelete.triggered.connect(lambda: self.table_fcn.delete_row(self.tableWidgetPolyPoints))
        self.tableWidgetPolyPoints.selectionModel().selectionChanged.connect(lambda: self.view_selected_polygon)

        self.actionPolyCreate.triggered.connect(lambda: self.parent.main_window.reset_checked_items('polygon'))
        self.actionPolyMovePoint.triggered.connect(lambda: self.parent.main_window.reset_checked_items('polygon'))
        self.actionPolyAddPoint.triggered.connect(lambda: self.parent.main_window.reset_checked_items('polygon'))
        self.actionPolyRemovePoint.triggered.connect(lambda: self.parent.main_window.reset_checked_items('polygon'))

        self.toggle_polygon_actions()


    def polygon_state_changed(self):
        self.parent.main_window.polygon_state = self.polygon_toggle.isChecked()
        if self.polygon_toggle.isChecked():
            # self.parent.main_window.update_plot_type_combobox()
            if (hasattr(self.parent.main_window, "profile_dock")):
                self.parent.main_window.profile_dock.profile_toggle.setChecked(False)
                self.parent.main_window.profile_dock.profile_state_changed()

        self.toggle_polygon_actions()


        self.parent.main_window.plot_style.schedule_update()

    def toggle_polygon_actions(self):
        """Toggle enabled state of polygon actions based on ``self.polygon_toggle`` checked state."""
        if self.polygon_toggle.isChecked():
            self.actionEdgeDetect.setEnabled(True)
            self.comboBoxEdgeDetectMethod.setEnabled(True)
            self.actionPolyCreate.setEnabled(True)
            self.actionPolyMovePoint.setEnabled(False)
            self.actionPolyMovePoint.setChecked(False)
            self.actionPolyAddPoint.setEnabled(False)
            self.actionPolyAddPoint.setChecked(False)
            self.actionPolyRemovePoint.setEnabled(False)
            self.actionPolyRemovePoint.setChecked(False)
            self.actionPolyLink.setEnabled(False)
            self.actionPolyDelink.setEnabled(False)
            self.actionPolySave.setEnabled(False)
            self.actionPolyDelete.setEnabled(False)
        else:
            self.actionEdgeDetect.setEnabled(False)
            self.comboBoxEdgeDetectMethod.setEnabled(False)
            self.actionPolyCreate.setEnabled(False)
            if self.tableWidgetPolyPoints.rowCount() > 1:
                self.actionPolyLink.setEnabled(False)
                self.actionPolyDelink.setEnabled(False)
            if self.tableWidgetPolyPoints.rowCount() > 0:
                self.actionPolySave.setEnabled(False)
                self.actionPolyDelete.setEnabled(False)

    def update_table_widget(self):
        """Update the polygon table (PyQt6 version)."""
        sample_id = self.parent.main_window.app_data.sample_id
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
        sample_id = self.parent.main_window.app_data.sample_id

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
        # Iterate through each polygon in self.polygons[self.main_window.sample_id]
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

                points = pd.concat([self.data[sample_id].processed_data['X'], self.data[sample_id].processed_data['Y']] , axis=1).values
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



class ClusterTab():
    def __init__(self, parent, debug=False):
        self.parent = parent

        self.main_window = self.parent.main_window
        #init table_fcn
        self.table_fcn = TableFcn(self)

        self.cluster_tab = QWidget()
        self.cluster_tab.setObjectName("Cluster Tab")

        tab_layout = QVBoxLayout()
        tab_layout.setContentsMargins(6, 6, 6, 6)
        self.cluster_tab.setLayout(tab_layout)

        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out

        tab_layout.addWidget(toolbar)

        labelClusterGroup = QLabel("Cluster", toolbar)

        self.spinBoxClusterGroup = QDoubleSpinBox(toolbar)

        self.toolButtonClusterColor = QToolButton(toolbar)
        self.toolButtonClusterColor.setMaximumSize(QSize(18, 18))
        self.toolButtonClusterColor.setText("")

        self.actionClusterColorReset = QAction("Cluster Color Reset", toolbar)
        icon_reset = QIcon(":/resources/icons/icon-reset-64.svg")
        self.actionClusterColorReset.setIcon(icon_reset)
        self.actionClusterColorReset.setToolTip("Reset cluster colors")

        self.actionClusterLink = QAction("Link Polygons", toolbar)
        icon_link = QIcon(":/resources/icons/icon-link-64.svg")
        self.actionClusterLink.setIcon(icon_link)
        self.actionClusterLink.setToolTip("Create a link between clusters")

        self.actionClusterDelink = QAction("Remove Link", toolbar)
        icon_delink = QIcon(":/resources/icons/icon-unlink-64.svg")
        self.actionClusterDelink.setIcon(icon_delink)
        self.actionClusterDelink.setToolTip("Remove link between clusters")

        self.actionGroupMask = QAction("Create Cluster Mask", toolbar)
        icon_dark = QIcon(":/resources/icons/icon-mask-dark-64.svg")
        self.actionGroupMask.setIcon(icon_dark)
        self.actionGroupMask.setToolTip("Create a mask based on the currently selected clusters")

        self.actionGroupMaskInverse = QAction("Create Cluster Mask Inverse", toolbar)
        icon_light = QIcon(":/resources/icons/icon-mask-light-64.svg")
        self.actionGroupMaskInverse.setIcon(icon_light)
        self.actionGroupMaskInverse.setToolTip("Create a mask based on the inverese of currently seletected clusters")

        toolbar.addWidget(labelClusterGroup)
        toolbar.addWidget(self.spinBoxClusterGroup)
        toolbar.addWidget(self.toolButtonClusterColor)
        toolbar.addAction(self.actionClusterColorReset)
        toolbar.addSeparator()
        toolbar.addAction(self.actionClusterLink)
        toolbar.addAction(self.actionClusterDelink)
        toolbar.addSeparator()
        toolbar.addAction(self.actionGroupMask)
        toolbar.addAction(self.actionGroupMaskInverse)

        self.tableWidgetViewGroups = CustomTableWidget()
        self.tableWidgetViewGroups.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.tableWidgetViewGroups.setObjectName("tableWidgetViewGroups")
        self.tableWidgetViewGroups.setColumnCount(3)
        self.tableWidgetViewGroups.setRowCount(0)
        
        header = self.tableWidgetViewGroups.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
        self.tableWidgetViewGroups.setHorizontalHeaderLabels(["Name", "Link", "Color"])

        tab_layout.addWidget(self.tableWidgetViewGroups)

        cluster_icon = QIcon(":/resources/icons/icon-cluster-64.svg")
        self.parent.tabWidgetMask.addTab(self.cluster_tab, cluster_icon, "Clusters")

        self.spinBoxClusterGroup.valueChanged.connect(self.select_cluster_group_callback)
        self.toolButtonClusterColor.clicked.connect(self.cluster_color_callback)
        self.actionClusterColorReset.triggered.connect(self.main_window.plot_style.set_default_cluster_colors)
        self.tableWidgetViewGroups.itemChanged.connect(self.cluster_label_changed)
        self.tableWidgetViewGroups.selectionModel().selectionChanged.connect(self.update_clusters)
        self.actionGroupMask.triggered.connect(lambda: self.main_window.apply_cluster_mask(inverse=False))
        self.actionGroupMaskInverse.triggered.connect(lambda: self.main_window.apply_cluster_mask(inverse=True))

        self.toggle_cluster_actions()
        self.update_table_widget()

    def toggle_cluster_actions(self):
        if self.parent.data:
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
        if self.debug:
            print("cluster_color_callback")

        #print('cluster_color_callback')
        if self.tableWidgetViewGroups.rowCount() == 0:
            return

        selected_cluster = int(self.spinBoxClusterGroup.value()-1)

        # change color
        self.parent.main_window.button_color_select(self.toolButtonClusterColor)
        color = get_hex_color(self.toolButtonClusterColor.palette().button().color())
        self.parent.main_window.cluster_dict[self.parent.main_window.cluster_dict['active method']][selected_cluster]['color'] = color
        if self.tableWidgetViewGroups.item(selected_cluster,2).text() == color:
            return

        # update_table
        self.tableWidgetViewGroups.setItem(selected_cluster,2,QTableWidgetItem(color))

        # update plot
        if self.parent.main_window.comboBoxColorByField.currentText() == 'cluster':
            self.parent.main_window.plot_style.schedule_update()

    def select_cluster_group_callback(self):
        """Set cluster color button background after change of selected cluster group

        Sets ``MainWindow.toolButtonClusterColor`` background on change of ``MainWindow.spinBoxClusterGroup``
        """
        if self.debug:
            print("select_cluster_group_callback")

        if self.tableWidgetViewGroups.rowCount() == 0:
            return
        self.toolButtonClusterColor.setStyleSheet("background-color: %s;" % self.tableWidgetViewGroups.item(int(self.spinBoxClusterGroup.value()-1),2).text())

    def update_table_widget(self):
        
        app_data = self.main_window.app_data
        data = self.main_window.data[app_data.sample_id]
        
        # # block signals
        self.tableWidgetViewGroups.blockSignals(True)
        self.spinBoxClusterGroup.blockSignals(True)

        # Clear the list widget
        self.tableWidgetViewGroups.clearContents()
        self.tableWidgetViewGroups.setHorizontalHeaderLabels(['Name','Link','Color'])
        method = app_data.cluster_method
        if method in data.processed_data.columns:
            if not data.processed_data[method].empty:
                clusters = data.processed_data[method].dropna().unique()
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
                    # colors in table are set by plot_style.set_default_cluster_colors()
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
            
            app_data = self.parent.main_window.app_data
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

            # Update self.parent.data.processed_data with the new name
            if method in self.parent.data[app_data.sample_id].processed_data.columns:
                # Find the rows where the value matches cluster_id
                rows_to_update = self.parent.data[app_data.sample_id].processed_data.loc[:,method] == cluster_id

                # Update these rows with the new name
                self.parent.data[app_data.sample_id].processed_data.loc[rows_to_update, method] = new_name

            # update current_group to reflect the new cluster name
            app_data.cluster_dict[method][cluster_id]['name'] = new_name

            # update plot with new cluster name
            # trigger update to plot
            self.parent.main_window.plot_style.schedule_update()

    def update_clusters(self):
        """Executed on update to cluster table.

        Updates ``MainWindow.cluster_dict`` and plot when the selected cluster have changed.
        """        
        if not self.updating_cluster_table_flag:
            app_data = self.parent.main_window.app_data
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
            if (self.parent.main_window.plot_style.plot_type not in ['cluster', 'cluster score']) and (app_data.c_field_type == 'cluster'):
                # trigger update to plot
                self.parent.main_window.plot_style.schedule_update()

    
        # cluster styles
    # -------------------------------------

    def set_default_cluster_colors(self,plot_style,cluster_tab, mask=False):
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
        cmap = plot_style.get_colormap(N=self.tableWidgetViewGroups.rowCount())

        # set color for each cluster and place color in table
        colors = [cmap(i) for i in range(cmap.N)]

        hexcolor = []
        for i in range(self.tableWidgetViewGroups.rowCount()):
            hexcolor.append(get_hex_color(colors[i]))
            self.tableWidgetViewGroups.blockSignals(True)
            self.tableWidgetViewGroups.setItem(i,2,QTableWidgetItem(hexcolor[i]))
            self.tableWidgetViewGroups.blockSignals(False)

        if mask:
            hexcolor.append(plot_style.style_dict['cluster']['OverlayColor'])

        self.toolButtonClusterColor.setStyleSheet("background-color: %s;" % self.tableWidgetViewGroups.item(self.spinBoxClusterGroup.value()-1,2).text())

        return hexcolor