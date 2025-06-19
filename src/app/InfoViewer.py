import os, re
import numexpr as ne
from src.app.config import BASEDIR
import numpy as np
import pandas as pd
from src.common.varfunc import partial_match

from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtWidgets import (
        QMainWindow, QTextEdit, QWidget, QVBoxLayout, QMessageBox, QInputDialog, QLabel,
        QToolBar, QComboBox, QToolButton, QDialog, QCheckBox, QDialogButtonBox, QPushButton,
        QGroupBox, QHBoxLayout, QSpacerItem, QSizePolicy, QTableWidgetItem, QTableWidget, QTabWidget,
        QAbstractItemView, QFormLayout, QHeaderView
    )
from PyQt6.QtGui import QIcon, QFont, QPixmap, QAction

from src.common.CustomWidgets import CustomComboBox, CustomDockWidget
from src.app.UIControl import UIFieldLogic

from src.app.UITheme import default_font
from src.common.CustomMplCanvas import MplCanvas

PRECISION = 5

def increase_precision():
    global PRECISION

    if PRECISION == 16:
        return
    PRECISION += 1
    
def decrease_precision():
    global PRECISION

    if PRECISION == 1:
        return
    PRECISION -= 1

def create_checkbox(is_checked, callback, key):
    checkbox = QCheckBox()
    checkbox.setChecked(is_checked)
    checkbox.stateChanged.connect(lambda state: callback(state, key))
    return checkbox

def update_dataframe(dataframe, table_widget):
    global PRECISION

    """Load the DataFrame data into the QTableWidget."""
    # Set the row and column count
    table_widget.setRowCount(len(dataframe))
    table_widget.setColumnCount(len(dataframe.columns))

    # Set the column headers
    table_widget.setHorizontalHeaderLabels(dataframe.columns)

    # Add the data to the table
    for row_idx, row in dataframe.iterrows():
        for col_idx, value in enumerate(row):
            item = QTableWidgetItem(f"{value:.{PRECISION}g}")
            table_widget.setItem(row_idx, col_idx, item)

def update_numpy_array(array, table_widget):
    global PRECISION

    """Load numpy.ndarray data into the QTableWidget."""
    if not isinstance(array, np.ndarray):
        raise TypeError("Input must be a numpy.ndarray")

    # Set the row and column count
    table_widget.setRowCount(array.shape[0])
    table_widget.setColumnCount(array.shape[1])

    # Use row and column indices as headers
    table_widget.setHorizontalHeaderLabels([str(i) for i in range(array.shape[1])])
    table_widget.setVerticalHeaderLabels([str(i) for i in range(array.shape[0])])

    # Add the data to the table
    for row_idx, row in enumerate(array):
        for col_idx, value in enumerate(row):
            item = QTableWidgetItem(f"{value:.{PRECISION}g}")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table_widget.setItem(row_idx, col_idx, item)

class InfoDock(CustomDockWidget, UIFieldLogic):
    """Creates a dock widget with a various tools to view the data, metadata, and plot information

    Creates a tab widget within a dock widget with tabs for metadata, the full dataframe,
    selected fields (in map form), and plot information.  Each tab and the methods for it are
    contained within their own class.

    Parameters
    ----------
    parent : QMainWindow, optional
        The parent window, by default None
    title : str, optional
        Window title, by default "Info Tools"

    :see also:
        metadata_tab : A tab displaying metadata for each column of the dataframe
        dataframe_tab : A tab that displays the entire dataframe
        field_tab : A tab that displays each field in map form (as displayed in a map plot)
        plot_info_tab : A tab that displays information about the current plot
    """        
    def __init__(self, parent, title="Info Tools"):
        super().__init__(parent)

        self.parent = parent

        if self.parent.plot_info:
            self.plot_info = self.parent.plot_info
        else:
            self.plot_info = None

        if self.parent.data or self.parent.app_data.sample_id == '':
            self.sample_id = self.parent.app_data.sample_id
            self.data = self.parent.data[self.sample_id]
        else:
            self.sample_id = ''
            self.data = None

        self.font = default_font()

        self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.setObjectName("dockWidgetInfoToolbox")
        self.dockWidgetInfo = QWidget()
        self.dockWidgetInfo.setObjectName("dockWidgetInfo")
        dock_layout = QVBoxLayout(self.dockWidgetInfo)

        self.tabWidgetInfo = QTabWidget(self.dockWidgetInfo)
        self.tabWidgetInfo.setObjectName("tabWidgetInfo")

        self.metadata_tab = MetadataTab(self)
        self.dataframe_tab = DataFrameTab(self)
        self.field_tab = FieldTab(self)
        self.plot_info_tab = PlotInfoTab(self)

        dock_layout.addWidget(self.tabWidgetInfo)
        self.setWidget(self.dockWidgetInfo)

        self.setFloating(True)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)

        parent.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self)

        self.visibilityChanged.connect(self.update_tab_widget)
        self.tabWidgetInfo.currentChanged.connect(self.update_tab_widget)

    def update_tab_widget(self):
        idx = self.tabWidgetInfo.currentIndex()
        match self.tabWidgetInfo.tabText(idx).lower():
            case "metadata":
                self.metadata_tab.update_metadata(self.data.processed_data.column_attributes)
            case "data":
                update_dataframe(self.data.processed_data, self.dataframe_tab.data_table)
            case "field":
                field = self.field_tab.field_combobox.currentText()
                if not (field == ''):
                    update_numpy_array(self.data.get_map_data(field), self.field_tab.field_table)
            case "plot info":
                self.plot_info_tab.update_plot_info_tab(self.parent.plot_info)

# -------------------------------
# Plot Info Tab functions
# -------------------------------
class PlotInfoTab():
    """Creates the plot info tab for plots and annotations.

    Parameters
    ----------
    parent : QTabWidget, optional
        Tab widget to add this tab to.
    """
    def __init__(self, parent):
        self.parent = parent

        self.plot_info_tab = QWidget()
        self.plot_info_tab.setObjectName("Plot Info Tab")
        tab_layout = QVBoxLayout(self.plot_info_tab)
        tab_layout.setContentsMargins(6, 6, 6, 6)
        self.plot_info_tab.setLayout(tab_layout)

        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out
        tab_layout.addWidget(toolbar)

        self.actionSelectAll = QAction(toolbar)
        select_all_icon = QIcon(":resources/icons/icon-select-all-64.svg")
        self.actionSelectAll.setIcon(select_all_icon)
        self.actionSelectAll.setToolTip("Select all annotations")

        self.actionShowHide = QAction(toolbar)
        show_hide_icon = QIcon(":resources/icons/icon-show-hide-64.svg")
        self.actionShowHide.setIcon(show_hide_icon)
        self.actionShowHide.setCheckable(True)
        self.actionShowHide.setToolTip("Toggle show/hide annotations")

        self.actionRemove = QAction(toolbar)
        remove_icon = QIcon(":resources/icons/icon-delete-64.svg")
        self.actionRemove.setIcon(remove_icon)
        self.actionRemove.setToolTip("Remove selected annotation(s)")

        toolbar.addAction(self.actionSelectAll)
        toolbar.addAction(self.actionShowHide)
        toolbar.addAction(self.actionRemove)


        tab_widgets_layout = QHBoxLayout()
        tab_widgets_layout.setObjectName("plot_into_tab_layout")

        # plot info display
        plot_info_layout = QVBoxLayout()

        self.plot_info_label = QLabel(self.plot_info_tab)
        self.plot_info_label.setText("Current plot")

        self.plot_info_text_edit = QTextEdit(self.plot_info_tab)
        self.plot_info_text_edit.setReadOnly(True)
        self.plot_info_text_edit.setFont(self.parent.font)

        plot_info_layout.addWidget(self.plot_info_label)
        plot_info_layout.addWidget(self.plot_info_text_edit)

        tab_widgets_layout.addLayout(plot_info_layout)

        # annotations display
        self.annotations_layout = QVBoxLayout()

        self.annotations_label = QLabel(self.plot_info_tab)
        self.annotations_label.setText("Annotations")

        self.annotations_table = QTableWidget(0, 3, self.plot_info_tab)
        self.annotations_table.setHorizontalHeaderLabels(["Type", "Value", "Visible"])
        self.annotations_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)

        self.annotations_layout.addWidget(self.annotations_label)
        self.annotations_layout.addWidget(self.annotations_table)

        tab_widgets_layout.addLayout(self.annotations_layout)

        tab_layout.addLayout(tab_widgets_layout)

        self.parent.tabWidgetInfo.addTab(self.plot_info_tab, "Plot Info")

        if hasattr(self.parent,"plot_info") and self.parent.plot_info:
            self.update_plot_info_tab(self.parent.plot_info)
            self.update_annotation_table()

    def update_plot_info_tab(self, plot_info, write_info=True, level=0):
        """Prints plot info in the information tab
        
        Prints ``plot_info`` into the bottom information tab ``MainWindow.textEditPlotInfo``.

        Parameters
        ----------
        plot_info : dict
            Plot information dictionary.
        write_info : bool
            Flag to write dictionary contents when ``True``. When calling ``update_plot_info`` is used
            recursively to handle dictionaries within dictionaries, the flag is set to ``False``. By default ``True``
        level : int
            Indent level, by default ``0``

        Returns
        -------
        str
            When called recursively, a string is returned
        """
        if plot_info is None:
            return

        content = ''
        if level > 0:
            indent = '&nbsp;'*(4*level)
        else:
            indent = ''

        for key, value in plot_info.items():
            if isinstance(value,str):
                if value == '':
                    content += f"{indent}<b>{key}:</b> ''<br>"
                else:
                    content += f"{indent}<b>{key}:</b> {value}<br>"
            elif isinstance(value,list) | isinstance(value,int) | isinstance(value,float):
                content += f"{indent}<b>{key}:</b> {value}<br>"
            elif isinstance(value,dict):
                content += f"{indent}<b>{key}:</b><br>"
                content += self.update_plot_info_tab(value, write_info=False, level=level+1)
            elif value is None:
                content += f"{indent}<b>{key}:</b> None<br>"
            else:
                content += f"{indent}<b>{key}:</b> {str(type(value))}<br>"
            
        if write_info:
            self.plot_info_text_edit.clear()
            self.plot_info_text_edit.setText(content)
        else:
            return content

    def update_annotation_table(self):
        if not self.parent.plot_info['figure'] or not isinstance(self.parent.plot_info['figure'], MplCanvas):
            return

        annotations = self.parent.plot_info['figure'].annotations

        # Update the table with the current annotations
        self.annotations_table.setRowCount(len(annotations))
        for row, (annotation, data) in enumerate(annotations.items()):
            # Type
            type_item = QTableWidgetItem(data["type"])
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.annotations_table.setItem(row, 0, type_item)

            # Value
            value_item = QTableWidgetItem(data["value"])
            self.annotations_table.setItem(row, 1, value_item)

            # Visibility checkbox
            checkbox = create_checkbox(is_checked=data["visible"], callback=self.toggle_annotation, key=annotation)
            self.annotations_table.setCellWidget(row, 2, checkbox)

        # Connect cell changes to the update function
        self.annotations_table.itemChanged.connect(self.update_annotation_from_table)

    def toggle_annotation(self, state, annotation):
        # Show or hide the annotation
        self.parent.plot_info['figure'].annotations[annotation]["visible"] = bool(state)
        annotation.set_visible(bool(state))
        self.parent.canvas.draw()

    def update_annotation_from_table(self, item):
        # Update the annotation from the table
        row = item.row()
        canvas = self.parent.plot_info['figure']
        annotation = list(canvas.annotations.keys())[row]

        # Update value
        if item.column() == 1:  # Value column
            new_text = item.text()
            canvas.annotations[annotation]["value"] = new_text
            annotation.set_text(new_text)
            self.parent.canvas.draw()

# -------------------------------
# Metadata Info Tab functions
# -------------------------------
class MetadataTab():
    """Creates the metadata tab for plots and annotations.

    Parameters
    ----------
    parent : QTabWidget, optional
        Tab widget to add this tab to.
    """
    def __init__(self, parent):
        self.parent = parent

        self.data = self.parent.data

        self.rows_flag = True
        self.columns_flag = True

        self.metadata_tab = QWidget()
        self.metadata_tab.setObjectName("Metadata Tab")
        tab_layout = QVBoxLayout(self.metadata_tab)
        tab_layout.setContentsMargins(6, 6, 6, 6)

        # Create toolbar for actions
        toolbar = QToolBar(self.metadata_tab)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out
        tab_layout.addWidget(toolbar)

        # Add toolbar actions
        # select field
        field_label = QLabel(self.metadata_tab)
        field_label.setFont(self.parent.font)
        field_label.setText("Field")

        self.field_combobox = QComboBox(self.metadata_tab)
        self.field_combobox.setFont(self.parent.font)
        self.field_combobox.setObjectName("field_combobox")

        # select all columns
        self.actionSelectAll_columns = QAction("Select All Columns", toolbar)
        select_columns_icon = QIcon(":resources/icons/icon-top_toolbar_show-64.svg")
        self.actionSelectAll_columns.setIcon(select_columns_icon)
        self.actionSelectAll_columns.setCheckable(True)
        self.actionSelectAll_columns.toggled.connect(self.toggle_all_columns)
        self.actionSelectAll_columns.setToolTip("Select/deselect all columns")

        # select all rows
        self.actionSelectAll_rows = QAction("Select All Rows", toolbar)
        select_rows_icon = QIcon(":resources/icons/icon-left_toolbar_show-64.svg")
        self.actionSelectAll_rows.setIcon(select_rows_icon)
        self.actionSelectAll_rows.setCheckable(True)
        self.actionSelectAll_rows.toggled.connect(self.toggle_all_rows)
        self.actionSelectAll_rows.setToolTip("Select/deselect all rows")

        # set the norm method for all samples
        scaling_label = QLabel(self.metadata_tab)
        scaling_label.setFont(self.parent.font)
        scaling_label.setText("Norm")

        #normalising
        self.norm_combobox = QComboBox(self.metadata_tab)
        self.norm_combobox.setMaximumSize(QSize(16777215, 16777215))
        self.norm_combobox.setFont(self.parent.font)
        self.norm_combobox.setEditable(False)
        self.norm_combobox.addItems(['linear', 'log', 'logit', 'mixed'])
        # self.norm_combobox.activated.connect(lambda: self.update_norm(self.norm_combobox.currentText()))
        self.norm_combobox.setToolTip("Set the norm for all analytes")

        # view/hide
        self.actionToggleView = QAction("Show/hide columns and rows", toolbar)
        self.actionToggleView.setCheckable(True)
        self.actionToggleView.setChecked(True)
        self.actionToggleView.toggled.connect(self.toggle_view)
        self.toggle_view_icon = QIcon()
        self.toggle_view_icon.addPixmap(QPixmap(":resources/icons/icon-show-hide-64.svg"), QIcon.Mode.Normal, QIcon.State.Off)
        self.toggle_view_icon.addPixmap(QPixmap(":resources/icons/icon-show-64.svg"), QIcon.Mode.Normal, QIcon.State.On)
        self.actionToggleView.setIcon(self.toggle_view_icon)
        self.actionToggleView.setToolTip("Click to toggle visibility of unselected columns/rows")

        # export metadata table
        self.action_export_metadata = QAction("Export Metadata", toolbar)
        self.action_export_metadata.triggered.connect(self.export_metadata)
        export_notes_icon = QIcon(":resources/icons/icon-save-notes-64.svg")
        self.action_export_metadata.setIcon(export_notes_icon)
        self.action_export_metadata.setToolTip("Export metadata to notes")

        # add actions and widgets to toolbar
        toolbar.addWidget(field_label)
        toolbar.addWidget(self.field_combobox)
        toolbar.addAction(self.actionSelectAll_columns)
        toolbar.addAction(self.actionSelectAll_rows)
        toolbar.addAction(self.actionToggleView)
        toolbar.addSeparator()
        toolbar.addWidget(scaling_label)
        toolbar.addWidget(self.norm_combobox)
        toolbar.addSeparator()
        toolbar.addAction(self.action_export_metadata)

        self.metadata_table = QTableWidget(self.metadata_tab)
        self.metadata_table.setObjectName("metadata_table")
        self.metadata_table.setColumnCount(0)
        self.metadata_table.setRowCount(0)

        self.editable_rows = {"label", "units", "use", "norm"}
        self.metadata_table.itemChanged.connect(self.update_column_attributes_on_cell_change)
        
        tab_layout.addWidget(self.metadata_table)


        # set metadata 
        self.parent.tabWidgetInfo.addTab(self.metadata_tab, "Metadata")

        # Track selected columns
        self.metadata_selected_columns = []

        self.field_combobox.currentIndexChanged.connect(self.update_table)

        data = self.data.processed_data.column_attributes
        self.update_metadata(data)

    def toggle_view(self):
        pass

    def update_metadata(self, data):
        """Update the info dock with metadata
        """
        if not hasattr(self.parent,"sample_id") or self.parent.sample_id == '':
            return

        # ComboBox for column selection
        self.field_combobox.addItem("All")
        self.field_combobox.addItem("Selected")
        self.field_combobox.addItems(data.keys())

        # self.selected_columns = list(self.parent.data[self.parent.sample_id].processed_data.column_attributes.keys())
        # self.selected_rows = list(self.parent.data[self.parent.sample_id].processed_data.column_attributes.keys(1).keys())
        self.selected_columns = set()
        self.selected_rows = set()

        # Initialize the table
        self.update_table()

    def update_table(self):
        self.metadata_table.blockSignals(True)

        data = self.data.processed_data.column_attributes

        # Determine the selected display option
        selected_option = self.field_combobox.currentText()

        # Get rows and columns to display
        rows = sorted(set([key for column in data.values() for key in column.keys()]))
        columns = list(data.keys())

        rows_to_display = [
            row for row in rows if selected_option != "Selected" or row in self.selected_rows
        ]
        # Get the columns to display
        if selected_option == "All":
            columns_to_display = list(data.keys())
        elif selected_option == "Selected":
            columns_to_display = list(self.selected_columns)
            # columns_to_display = (
            #     [col for col in columns if not show_selected_only or col in self.selected_columns]
            # )
        else:
            columns_to_display = [selected_option]

        # Set the row and column count
        self.metadata_table.setRowCount(len(rows_to_display) + 1)  # +1 for header row checkboxes
        self.metadata_table.setColumnCount(len(columns_to_display) + 1)  # +1 for column selection checkboxes

        # Set horizontal headers
        self.metadata_table.setHorizontalHeaderLabels(["Select Row"] + columns_to_display)

        self.metadata_table.setVerticalHeaderLabels(["Select Column"] + rows_to_display)


        # Populate the header row with checkboxes
        for col_idx, col_key in enumerate(columns_to_display, start=1):
            checkbox = create_checkbox(is_checked=col_key in columns_to_display, callback=self.toggle_column_selection, key=col_key)
            self.metadata_table.setCellWidget(0, col_idx, checkbox)

        # Populate the first column and the rest of the metadata table
        for row_idx, row_key in enumerate(sorted(rows_to_display), start=1):
            # Add a checkbox for row selection in the first column
            checkbox = create_checkbox(is_checked=row_key in rows_to_display, callback=self.toggle_row_selection, key=row_key)
            self.metadata_table.setCellWidget(row_idx, 0, checkbox)

            # Populate the rest of the cells
            for col_idx, col_key in enumerate(columns_to_display, start=1):
                value = data.get(col_key, {}).get(row_key, "")
                item = QTableWidgetItem(str(value))

                # Make editable only if the row is in editable_rows
                if row_key in self.editable_rows:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                #item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make it read-only
                self.metadata_table.setItem(row_idx, col_idx, item)

        # Adjust metadata table appearance
        self.metadata_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.metadata_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        self.metadata_table.blockSignals(False)

    def toggle_row_selection(self, state, row):
        """Toggle selection of rows based on checkbox state."""
        if state == Qt.CheckState.Checked:
            self.selected_rows.add(row)
        else:
            self.selected_rows.discard(row)
        if self.field_combobox.currentText() == "Selected":
            self.update_table()

    def toggle_column_selection(self, state, column):
        """Toggle selection of columns based on checkbox state."""
        if state == Qt.CheckState.Checked:
            self.selected_columns.add(column)
        else:
            self.selected_columns.discard(column)
        if self.field_combobox.currentText() == "Selected":
            self.update_table()

    def toggle_all_columns(self):
        """Toggle all columns based on toolbar action."""
        if not self.columns_flag:
            self.selected_columns = set(self.parent.data[self.parent.sample_id].processed_data.column_attributes.keys())
        else:
            self.selected_columns.clear()

        self.columns_flag = not self.columns_flag
        if self.columns_flag:
            self.field_combobox.setCurrentText("All")
        else:
            self.field_combobox.setCurrentText("Selected")
        self.update_table()

    def toggle_all_rows(self):
        """Toggle all rows based on toolbar action."""
        if not self.rows_flag:
            rows = set(
                key for column in self.parent.data[self.parent.sample_id].processed_data.column_attributes.values()
                for key in column.keys()
            )
            self.selected_rows = rows
        else:
            self.selected_rows.clear()

        self.rows_flag = not self.rows_flag
        self.update_table()

    def update_column_attributes_on_cell_change(self, item):
        row = item.row()
        col = item.column()

        # Ignore header row/column (0)
        if row == 0 or col == 0:
            return

        # Get the row and column keys
        row_key = self.metadata_table.verticalHeaderItem(row).text()
        col_key = self.metadata_table.horizontalHeaderItem(col).text()

        # Only update editable rows
        if row_key not in self.editable_rows:
            return

        # Update column_attributes
        if col_key not in self.data.processed_data.column_attributes:
            self.data.processed_data.column_attributes[col_key] = {}

        self.data.processed_data.column_attributes[col_key][row_key] = item.text()

    def export_metadata(self):
        pass

# -------------------------------
# Data Tab functions
# -------------------------------
class DataFrameTab():
    """Creates the data info tab for plots and annotations.

    Parameters
    ----------
    parent : QTabWidget, optional
        Tab widget to add this tab to.
    """
    def __init__(self, parent):
        self.parent = parent

        self.data = self.parent.data

        self.data_tab = QWidget()
        self.data_tab.setObjectName("Data Tab")
        layout = QVBoxLayout(self.data_tab)
        layout.setContentsMargins(6, 6, 6, 6)

        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out

        layout.addWidget(toolbar)

        self.action_sigfigs_more = QAction("Increase Significant Figures", toolbar)
        sigfigs_more_icon = QIcon(":resources/icons/icon-sigfigs-add-64.svg")
        self.action_sigfigs_more.setIcon(sigfigs_more_icon)
        self.action_sigfigs_more.triggered.connect(increase_precision)
        self.action_sigfigs_more.triggered.connect(lambda: update_dataframe(self.data.processed_data, self.data_table))
        self.action_sigfigs_more.setToolTip("Increase the number of displayed digits")

        self.action_sigfigs_less = QAction("Decrease Significant Figures", toolbar)
        sigfigs_less_icon = QIcon(":resources/icons/icon-sigfigs-remove-64.svg")
        self.action_sigfigs_less.setIcon(sigfigs_less_icon)
        self.action_sigfigs_less.triggered.connect(decrease_precision)
        self.action_sigfigs_less.triggered.connect(lambda: update_dataframe(self.data.processed_data, self.data_table))
        self.action_sigfigs_less.setToolTip("Reduce the number of displayed digits")

        toolbar.addAction(self.action_sigfigs_more)
        toolbar.addAction(self.action_sigfigs_less)

        self.data_table = QTableWidget(self.data_tab)
        self.data_table.setObjectName("data_table")
        self.data_table.setColumnCount(0)
        self.data_table.setRowCount(0)
        self.data_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.data_table)

        self.parent.tabWidgetInfo.addTab(self.data_tab, "Data")

        if not self.parent.data:
            return

        update_dataframe(self.data.processed_data, self.data_table)


# -------------------------------
# Field Tab functions
# -------------------------------
class FieldTab(UIFieldLogic):
    """Creates the field info tab for plots and annotations.

    Parameters
    ----------
    parent : QTabWidget
        Tab widget to add this tab to.
    """
    def __init__(self, parent):
        super().__init__(parent)

        if not parent.data:
            return
        self.data = parent.data

        self.field_tab = QWidget()
        self.field_tab.setObjectName("Field Tab")
        tab_layout = QVBoxLayout(self.field_tab)
        tab_layout.setContentsMargins(6, 6, 6, 6)

        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out

        tab_layout.addWidget(toolbar)

        field_type_label = QLabel(self.field_tab)
        field_type_label.setText("Field type")

        self.field_type_combobox = CustomComboBox(popup_callback=lambda: self.update_field_type_combobox(self.field_type_combobox))
        self.field_type_combobox.setObjectName("field_type_combobox")

        field_label = QLabel(self.field_tab)
        field_label.setText("Field")

        self.field_combobox = QComboBox(self.field_tab)
        self.field_combobox.setObjectName("field_combobox")

        self.action_sigfigs_more = QAction("Increase Significant Figures", toolbar)
        sigfigs_more_icon = QIcon(":resources/icons/icon-sigfigs-add-64.svg")
        self.action_sigfigs_more.setIcon(sigfigs_more_icon)
        self.action_sigfigs_more.triggered.connect(increase_precision)
        self.action_sigfigs_more.triggered.connect(self.update_field_table)
        self.action_sigfigs_more.setToolTip("Increase the number of displayed digits")

        self.action_sigfigs_less = QAction("Decrease Significant Figures", toolbar)
        sigfigs_less_icon = QIcon(":resources/icons/icon-sigfigs-remove-64.svg")
        self.action_sigfigs_less.setIcon(sigfigs_less_icon)
        self.action_sigfigs_less.triggered.connect(decrease_precision)
        self.action_sigfigs_less.triggered.connect(self.update_field_table)
        self.action_sigfigs_less.setToolTip("Reduce the number of displayed digits")

        toolbar.addWidget(field_type_label)
        toolbar.addWidget(self.field_type_combobox)
        toolbar.addWidget(field_label)
        toolbar.addWidget(self.field_combobox)
        toolbar.addAction(self.action_sigfigs_more)
        toolbar.addAction(self.action_sigfigs_less)

        self.field_table = QTableWidget(self.field_tab)
        self.field_table.setObjectName("field_table")
        self.field_table.setColumnCount(0)
        self.field_table.setRowCount(0)
        self.field_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        tab_layout.addWidget(self.field_table)

        parent.tabWidgetInfo.addTab(self.field_tab, "Field")

        # when field type combobox is updated
        self.field_type_combobox.activated.connect(lambda: self.update_field_combobox(self.field_type_combobox, self.field_combobox))
        self.field_type_combobox.activated.connect(self.update_field_table)

        self.update_field_combobox(self.field_type_combobox, self.field_combobox)

        # when field combobox is updated
        self.field_combobox.activated.connect(self.update_field_table)

        self.update_field_table()

    def update_field_table(self):
        if self.field_combobox.currentText() == '' or self.field_type_combobox.currentText() == '':
            return

        map_df = self.data.get_map_data(self.field_combobox.currentText(), self.field_type_combobox.currentText())
        reshaped_array = np.reshape(map_df['array'].values, self.data.array_size, order=self.data.order)
        update_numpy_array(reshaped_array, self.field_table)


