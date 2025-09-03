from src.app.config import BASEDIR
import numpy as np
import pandas as pd
from src.common.varfunc import partial_match
import src.common.format as fmt
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtWidgets import (
        QTextEdit, QWidget, QVBoxLayout, QMessageBox, QLabel,
        QToolBar, QComboBox, QCheckBox, QHBoxLayout, QTableWidgetItem, QTableWidget, QTabWidget,
        QAbstractItemView, QHeaderView, QStyledItemDelegate, QLineEdit, QSpacerItem, QDialog
    )
from PyQt6.QtGui import QDoubleValidator

from src.common.CustomWidgets import CustomComboBox, CustomDockWidget, CustomAction, ColorButton
from src.app.FieldLogic import FieldLogicUI

from src.app.UITheme import default_font
from src.common.CustomMplCanvas import MplCanvas

PRECISION = 5

def increase_precision():
    """
    Increase the global display precision for numeric formatting.

    Increments the global PRECISION variable by 1, 
    up to a maximum of 16 significant figures.
    """
    global PRECISION

    if PRECISION == 16:
        return
    PRECISION += 1
    
def decrease_precision():
    """
    Decrease the global display precision for numeric formatting.

    Decrements the global PRECISION variable by 1,
    but will not go below 1 significant figure.
    """
    global PRECISION

    if PRECISION == 1:
        return
    PRECISION -= 1

def create_checkbox(is_checked, callback, key):
    """
    Create a QCheckBox widget with an initial state and a bound callback.

    Parameters
    ----------
    is_checked : bool
        Whether the checkbox should be initially checked.
    callback : callable
        Function to call when the checkbox state changes. Will receive
        the new state and the key as arguments.
    key : any
        Identifier passed to the callback when the checkbox state changes.

    Returns
    -------
    QCheckBox
        The configured checkbox widget.
    """
    checkbox = QCheckBox()
    checkbox.setChecked(is_checked)
    checkbox.stateChanged.connect(lambda state: callback(state, key))
    return checkbox

def create_color_button(color, callback, key):
    button = ColorButton(initial_color=color)
    button.colorChanged.connect(lambda color: callback(color, key))
    return button

def update_dataframe(dataframe, table_widget):
    global PRECISION
    """
    Populate a QTableWidget with the contents of a pandas DataFrame.

    Parameters
    ----------
    dataframe : pandas.DataFrame
        The data to populate the table with.
    table_widget : QTableWidget
        The widget to display the DataFrame content.

    Notes
    -----
    Each numeric value is formatted using the current global PRECISION.
    """
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
    """
    Populate a QTableWidget with the contents of a NumPy array.

    Parameters
    ----------
    array : np.ndarray
        The array to display in the table. Must be 2D.
    table_widget : QTableWidget
        The widget to populate with the array data.

    Raises
    ------
    TypeError
        If the input is not a NumPy ndarray.

    Notes
    -----
    Data is formatted using the global PRECISION setting.
    Cells are made read-only.
    """
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

class InfoDock(CustomDockWidget, FieldLogicUI):
    """
    Dockable widget providing data insight tools through multiple interactive tabs.

    This widget embeds a tabbed interface within a dockable container, giving users access
    to key information and visualization tools related to the dataset and current plot.
    It includes:

    - **Metadata**: Displays detailed descriptions and stats of dataset fields.
    - **Dataframe**: Shows the full data table in a view-only format.
    - **Field Map**: Displays selected field data spatially (map representation).
    - **Plot Info**: Contains current plot settings, selections, and summaries.

    Parameters
    ----------
    parent : QMainWindow
        The main application window to which this dock is attached.
    title : str, optional
        The title displayed on the dock widget window (default is "Info Tools").

    See Also
    --------
    MetadataTab : Displays metadata for columns in the current dataset.
    DataFrameTab : Shows the entire dataset as a table.
    FieldTab : Provides a map-based visualization for selected fields.
    PlotInfoTab : Displays configuration and summary information for the current plot.
    """
    def __init__(self, parent, title="Info Tools"):
        super().__init__(parent)

        self.ui = parent

        if self.ui.plot_info:
            self.plot_info = self.ui.plot_info
        else:
            self.plot_info = None

        if self.ui.data or self.ui.app_data.sample_id == '':
            self.sample_id = self.ui.app_data.sample_id
            self.data = self.ui.data[self.sample_id]
            self.app_data = self.ui.app_data
        else:
            self.sample_id = ''
            self.data = None

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
        """
        Updates the content of the currently active tab.

        This method is called automatically when the user switches between tabs or
        when the dock's visibility changes. It ensures that the tab contents are
        refreshed with up-to-date data:

        - **Metadata**: Refreshes statistics from `processed_data`.
        - **Data**: Loads the full `processed_data` DataFrame into the table widget.
        - **Field**: Updates the map table for the selected field.
        - **Plot Info**: Refreshes plot configuration and status data.

        Notes
        -----
        Assumes that `self.data.processed` and `self.plot_info` are already populated.
        Fields are not updated if none are selected.
        """
        idx = self.tabWidgetInfo.currentIndex()
        match self.tabWidgetInfo.tabText(idx).lower():
            case "metadata":
                self.metadata_tab.update_metadata(self.data.processed)
            case "data":
                update_dataframe(self.data.processed, self.dataframe_tab.data_table)
            case "field":
                field = self.field_tab.field_combobox.currentText()
                if not (field == ''):
                    update_numpy_array(self.data.get_map_data(field), self.field_tab.field_table)
            case "plot info":
                self.plot_info_tab.update_plot_info_tab(self.ui.plot_info)

# -------------------------------
# Plot Info Tab functions
# -------------------------------
class PlotInfoTab():
    """
    Plot Info Tab UI for displaying plot metadata and managing annotations.

    This tab provides a read-only display of the current plot's metadata and a table for managing
    user-added annotations, including their type, value, and visibility.

    The tab contains:
    - A toolbar with actions to select all annotations, toggle visibility, and delete them.
    - A read-only QTextEdit for displaying plot metadata.
    - A QTableWidget for interacting with annotations.

    Parameters
    ----------
    parent : QTabWidget
        The parent tab widget to which this tab will be added.
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

        # export metadata table
        self.action_export_plot_info = CustomAction(
            text="Export to notes",
            light_icon_unchecked="icon-save-notes-64.svg",
            parent=toolbar,
        )
        self.action_export_plot_info.triggered.connect(self.export_plot_info)
        self.action_export_plot_info.setToolTip("Export plot information to notes")

        self.actionSelectAll = CustomAction(
            text="Select All",
            light_icon_unchecked="icon-select-all-64.svg",
            dark_icon_unchecked="icon-select-all-dark-64.svg",
            parent=toolbar
        )
        self.actionSelectAll.setToolTip("Select all annotations")

        self.actionShowHide = CustomAction(
            text="Show/Hide",
            light_icon_unchecked="icon-show-hide-64.svg",
            light_icon_checked="icon-show-64.svg",
            parent=toolbar,
        )
        self.actionShowHide.setToolTip("Toggle show/hide annotations")

        self.actionRemove = CustomAction(
            text="Remove",
            light_icon_unchecked="icon-delete-64.svg",
            dark_icon_unchecked="icon-delete-dark-64.svg",
            parent=toolbar
        )
        self.actionRemove.setToolTip("Remove selected annotation(s)")

        toolbar.addAction(self.action_export_plot_info)
        toolbar.addSeparator()
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

        plot_info_layout.addWidget(self.plot_info_label)
        plot_info_layout.addWidget(self.plot_info_text_edit)

        tab_widgets_layout.addLayout(plot_info_layout)

        # annotations display
        self.annotations_layout = QVBoxLayout()

        self.annotations_label = QLabel(self.plot_info_tab)
        self.annotations_label.setText("Annotations")

        self.annotations_table = QTableWidget(0, 6, self.plot_info_tab)
        self.annotations_table.setHorizontalHeaderLabels(["Type", "Text", "Size", "Width", "Color", "Visible"])
        self.annotations_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)

        header = self.annotations_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.annotations_layout.addWidget(self.annotations_label)
        self.annotations_layout.addWidget(self.annotations_table)

        tab_widgets_layout.addLayout(self.annotations_layout)

        tab_layout.addLayout(tab_widgets_layout)

        self.parent.tabWidgetInfo.addTab(self.plot_info_tab, "Plot Info")

        if hasattr(self.parent,"plot_info") and self.parent.plot_info:
            self.update_plot_info_tab(self.parent.plot_info)
            self.update_annotation_table()

    def update_plot_info_tab(self, plot_info, write_info=True, level=0):
        """
        Recursively display plot metadata as HTML in the info panel.

        This method traverses the nested `plot_info` dictionary and generates a formatted HTML
        string that is either inserted into the `plot_info_text_edit` display or returned.

        Parameters
        ----------
        plot_info : dict
            Dictionary of plot metadata (can be nested).
        write_info : bool, optional
            If True, the formatted HTML will be displayed directly in the UI.
            If False, the method will return the formatted HTML string instead.
            Default is True.
        level : int, optional
            Current indentation level for recursive formatting. Default is 0.

        Returns
        -------
        str
            A formatted HTML string if `write_info` is False. Otherwise, None.
        """
        if plot_info is None:
            return ''

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
        """
        Populate the annotation table with data from the current plot.

        Reads annotation data from the current `MplCanvas` instance in `plot_info['figure']` and
        populates the QTableWidget. Each row includes:

        - Annotation type (non-editable)
        - Editable annotation value
        - A checkbox for visibility control

        If the figure or its annotations are not available, the method returns silently.
        """
        if not self.parent.plot_info['figure'] or not isinstance(self.parent.plot_info['figure'], MplCanvas):
            return

        annotations = self.parent.plot_info['figure'].annotations

        self.annotations_table.blockSignals(True)
        self.annotations_table.setRowCount(len(annotations))
        for row, ann in enumerate(annotations):
            # Type
            type_item = QTableWidgetItem(ann['Type'])
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.annotations_table.setItem(row, 0, type_item)

            # Text
            read_only = True
            if isinstance(ann["Text"],dict):
                text = ann["Text"]["Text"]
                font_size = ann["Text"]["FontDict"]["size"]
                line_width = ann["Width"]
            else:
                text = ann["Text"]
                read_only = False
                font_size = ann["Size"]
                line_width = None
            text_item = QTableWidgetItem(text)
            if read_only:
                text_item.setFlags(text_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.annotations_table.setItem(row, 1, text_item)

            # Font Size
            font_size_item = QTableWidgetItem(str(font_size))
            font_size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
            self.annotations_table.setItem(row, 2, font_size_item)

            # Line Width
            line_width_item = QTableWidgetItem(str(line_width))
            line_width_item.setTextAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
            self.annotations_table.setItem(row, 3, line_width_item)

            # Color
            button = create_color_button(color=ann["Color"], callback=self.change_annotation_color, key=row)
            self.annotations_table.setCellWidget(row, 4, button)

            # Visibility checkbox
            checkbox = create_checkbox(is_checked=ann["Visible"], callback=self.toggle_annotation, key=row)
            self.annotations_table.setCellWidget(row, 5, checkbox)

        self.annotations_table.blockSignals(False)
        self.annotations_table.itemChanged.connect(self.update_annotation_from_table)

    def toggle_annotation(self, state, index):
        """
        Callback function to toggle annotation visibility.

        Updates both the internal state and visual visibility of the selected annotation.

        Parameters
        ----------
        state : int
            The checkbox state (0 for unchecked, 2 for checked).
        index : int
            The index of the annotation in the annotations list.
        """
        canvas = self.parent.plot_info['figure']
        if index >= len(canvas.annotations):
            return
            
        # Update annotation data
        annotation_data = canvas.annotations[index]
        visible = bool(state)
        annotation_data["Visible"] = visible
        
        # Update matplotlib object visibility
        matplotlib_obj = annotation_data.get('object')
        if matplotlib_obj:
            if isinstance(matplotlib_obj, list):
                # Handle line+text objects
                for obj in matplotlib_obj:
                    obj.set_visible(visible)
            else:
                matplotlib_obj.set_visible(visible)
        
        # Update registry if annotation has registry_id
        if hasattr(canvas, 'sample_obj') and canvas.plot_id and 'registry_id' in annotation_data:
            canvas.sample_obj.update_annotation(canvas.plot_id, annotation_data['registry_id'], {'visible': visible})
        
        canvas.draw()

    def change_annotation_color(self, color, index):
        """Update annotation color both in data and matplotlib object."""
        canvas = self.parent.plot_info['figure']
        if index >= len(canvas.annotations):
            return
            
        # Update annotation data
        annotation_data = canvas.annotations[index]
        annotation_data["Color"] = color
        
        # Update matplotlib object color
        matplotlib_obj = annotation_data.get('object')
        if matplotlib_obj:
            if isinstance(matplotlib_obj, list):
                # Handle line+text objects
                for obj in matplotlib_obj:
                    obj.set_color(color)
            else:
                matplotlib_obj.set_color(color)
        
        # Update registry if annotation has registry_id
        if hasattr(canvas, 'sample_obj') and canvas.plot_id and 'registry_id' in annotation_data:
            updates = {'style': annotation_data.get('style', {})}
            updates['style']['color'] = color
            canvas.sample_obj.update_annotation(canvas.plot_id, annotation_data['registry_id'], updates)
        
        canvas.draw()

    def update_annotation_from_table(self, item):
        """
        Handle edits made directly to the annotation table.

        Specifically updates the "Value" of the annotation in the canvas and triggers
        a redraw of the plot.

        Parameters
        ----------
        item : QTableWidgetItem
            The item in the annotation table that was changed.
        """
        # Update the annotation from the table
        row = item.row()
        canvas = self.parent.plot_info['figure']
        if row >= len(canvas.annotations):
            return  # Safety check
            
        annotation_data = canvas.annotations[row]
        matplotlib_obj = annotation_data.get('object')

        # Update value in annotation data and matplotlib object
        match item.column():
            case 1: # text
                new_text = item.text()
                annotation_data['Text'] = new_text
                if matplotlib_obj and hasattr(matplotlib_obj, 'set_text'):
                    matplotlib_obj.set_text(new_text)
            case 2: # font size
                new_size = float(item.text())
                if annotation_data['Type'].lower() == 'text':
                    annotation_data['Size'] = new_size
                    if matplotlib_obj and hasattr(matplotlib_obj, 'set_fontsize'):
                        matplotlib_obj.set_fontsize(new_size)
                else:
                    # For line annotations with text labels
                    if isinstance(annotation_data.get('Text'), dict):
                        annotation_data['Text']['FontDict']['size'] = new_size
            case 3: # line width
                new_width = float(item.text())
                annotation_data['Width'] = new_width
                if matplotlib_obj and hasattr(matplotlib_obj, 'set_linewidth'):
                    matplotlib_obj.set_linewidth(new_width)
        
        # Update registry if annotation has registry_id
        if hasattr(canvas, 'sample_obj') and canvas.plot_id and 'registry_id' in annotation_data:
            # Update the annotation in registry via sample object
            updates = {}
            if item.column() == 1:
                updates['text'] = new_text
            elif item.column() == 2:
                updates['style'] = annotation_data.get('style', {})
                updates['style']['font_size'] = new_size
            elif item.column() == 3:
                updates['style'] = annotation_data.get('style', {})
                updates['style']['line_width'] = new_width
            
            if updates:
                canvas.sample_obj.update_annotation(canvas.plot_id, annotation_data['registry_id'], updates)
        
        canvas.draw()

    def export_plot_info(self):
        if not hasattr(self.parent.ui,"notes_dock") or not self.parent.ui.plot_info:
            return
        
        notes = self.parent.ui.notes_dock.notes
        notes.print_info(self.parent.ui.plot_info)

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
        field_label.setText("Field")

        self.field_combobox = QComboBox(self.metadata_tab)
        self.field_combobox.setObjectName("field_combobox")

        # select all columns
        self.actionSelectAll_columns = CustomAction(
            text="Select Columns",
            light_icon_unchecked="icon-top-toolbar-hide-64.svg",
            light_icon_checked="icon-top-toolbar-show-64.svg",
            parent=toolbar
        )
        self.actionSelectAll_columns.setCheckable(True)
        self.actionSelectAll_columns.toggled.connect(self.toggle_all_columns)
        self.actionSelectAll_columns.setToolTip("Select/deselect all columns")

        # select all rows
        self.actionSelectAll_rows = CustomAction(
            text="Select Rows",
            light_icon_unchecked="icon-left-toolbar-hide-64.svg",
            light_icon_checked="icon-left-toolbar-show-64.svg",
            parent=toolbar,
        )
        self.actionSelectAll_rows.toggled.connect(self.toggle_all_rows)
        self.actionSelectAll_rows.setToolTip("Select/deselect all rows")

        # set the norm method for all samples
        scaling_label = QLabel(self.metadata_tab)
        scaling_label.setText("Norm")

        #normalising
        self.norm_combobox = QComboBox(self.metadata_tab)
        self.norm_combobox.setEditable(False)
        self.norm_combobox.addItems(['linear', 'log', 'logit', 'symlog', 'mixed'])
        # self.norm_combobox.activated.connect(lambda: self.update_norm(self.norm_combobox.currentText()))
        self.norm_combobox.setToolTip("Set the norm for all analytes")

        # view/hide
        self.actionToggleView = CustomAction(
            text="Show/hide columns and rows",
            light_icon_unchecked="icon-show-hide-64.svg",
            light_icon_checked="icon-show-64.svg",
            parent=toolbar,
        )
        self.actionToggleView.setChecked(True)
        self.actionToggleView.toggled.connect(self.toggle_view)
        self.actionToggleView.setToolTip("Click to toggle visibility of unselected columns/rows")

        # export metadata table
        self.action_export_metadata = CustomAction(
            text="Export to notes",
            light_icon_unchecked="icon-save-notes-64.svg",
            parent=toolbar,
        )
        self.action_export_metadata.triggered.connect(self.export_metadata)
        self.action_export_metadata.setToolTip("Export metadata to notes")

        # adjust precision
        self.action_sigfigs_more = CustomAction(
            text="Increase Significant Figures",
            light_icon_unchecked="icon-sigfigs-add-64.svg",
            dark_icon_unchecked="icon-sigfigs-add-dark-64.svg",
            parent=toolbar,
        )
        self.action_sigfigs_more.triggered.connect(increase_precision)
        self.action_sigfigs_more.triggered.connect(self.update_table)
        self.action_sigfigs_more.setToolTip("Increase the number of displayed digits")

        self.action_sigfigs_less = CustomAction(
            text="Decrease Significant Figures",
            light_icon_unchecked="icon-sigfigs-remove-64.svg",
            dark_icon_unchecked="icon-sigfigs-remove-dark-64.svg",
            parent=toolbar,
        )
        self.action_sigfigs_less.triggered.connect(decrease_precision)
        self.action_sigfigs_less.triggered.connect(self.update_table)
        self.action_sigfigs_less.setToolTip("Reduce the number of displayed digits")
        

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
        toolbar.addAction(self.action_sigfigs_more)
        toolbar.addAction(self.action_sigfigs_less)

        self.metadata_table = QTableWidget(self.metadata_tab)
        self.metadata_table.setObjectName("metadata_table")
        self.metadata_table.setColumnCount(0)
        self.metadata_table.setRowCount(0)

        self.editable_rows = {"label": str, "units": str, "use": bool, "norm": ["linear","log","symlog"], "plot_max": float,"plot_min":float}
        self.metadata_table.itemChanged.connect(self.update_column_attributes_on_cell_change)

        tab_layout.addWidget(self.metadata_table)


        # set metadata 
        self.parent.tabWidgetInfo.addTab(self.metadata_tab, "Metadata")

        # Track selected columns
        self.metadata_selected_columns = []

        self.field_combobox.activated.connect(self.update_table)

        data = self.data.processed
        data.attribute_callback = self.on_attribute_batch_changed

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
        self.field_combobox.addItems(data.column_attributes.keys())

        # self.selected_columns = list(self.parent.data[self.parent.sample_id].processed.column_attributes.keys())
        # self.selected_rows = list(self.parent.data[self.parent.sample_id].processed.column_attributes.keys(1).keys())
        self.selected_columns = set()
        self.selected_rows = set()

        # Initialize the table
        self.update_table()

    def update_table(self):
        global PRECISION
        self.metadata_table.blockSignals(True)

        # clear contents to avoid repeated check box bug
        self.metadata_table.clear()
        self.metadata_table.setRowCount(0)
        self.metadata_table.setColumnCount(0)

        data = self.data.processed.column_attributes

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
            # for col_idx, col_key in enumerate(columns_to_display, start=1):
            #     value = data.get(col_key, {}).get(row_key, "")
            #     item = QTableWidgetItem(str(value))

            #     # Make editable only if the row is in editable_rows
            #     if row_key in self.editable_rows:
            #         item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            #     else:
            #         item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            #     #item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Make it read-only
            #     self.metadata_table.setItem(row_idx, col_idx, item)

            for col_idx, col_key in enumerate(columns_to_display, start=1):
                value = data.get(col_key, {}).get(row_key, "")

                editor = self.editable_rows.get(row_key)

                if not editor: #item is not editable 
                    item = QTableWidgetItem(str(value))
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.metadata_table.setItem(row_idx, col_idx, item)

                elif editor is bool:
                    checkbox = QCheckBox()
                    checkbox.setChecked(bool(value))
                    checkbox.stateChanged.connect(lambda state, rk=row_key, ck=col_key: self.update_column_attributes_on_checkbox_state(state, rk, ck))
                    self.metadata_table.setCellWidget(row_idx, col_idx, checkbox)

                elif isinstance(editor, list):  # enum/choice type (e.g., for 'norm')
                    combobox = QComboBox()
                    combobox.addItems(editor)
                    if value in editor:
                        combobox.setCurrentText(value)
                    combobox.currentTextChanged.connect(lambda text, rk=row_key, ck=col_key: self.update_column_attributes_on_combobox_change(text, rk, ck))
                    self.metadata_table.setCellWidget(row_idx, col_idx, combobox)

                elif editor is float:# Check if value is a float
                    item = QTableWidgetItem(f"{value:.{PRECISION}g}")
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                    self.metadata_table.setItem(row_idx, col_idx, item)
                        
                elif editor is str: #editable string item
                    item = QTableWidgetItem(str(value))
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                    self.metadata_table.setItem(row_idx, col_idx, item)
                
                else: 
                    pass

        # Add a delegate to handle float formatting
        # and ensure edited 'plot_min' and 'plot_max' are within bounds
        delegate = FloatItemDelegate(
            parent=self.metadata_table,
            row_labels=rows_to_display,
            column_keys=columns_to_display,
            processed_data=self.data.processed,
            special_rows={'plot_min', 'plot_max'},
            precision=PRECISION
        )

        self.metadata_table.setItemDelegate(delegate)


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
            self.selected_columns = set(self.parent.data[self.parent.sample_id].processed.column_attributes.keys())
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
                key for column in self.parent.data[self.parent.sample_id].processed.column_attributes.values()
                for key in column.keys()
            )
            self.selected_rows = rows
        else:
            self.selected_rows.clear()

        self.rows_flag = not self.rows_flag
        self.update_table()

    def update_column_attributes_on_checkbox_state(self, state, row_key, col_key):
        value = state == Qt.CheckState.Checked
        if col_key not in self.data.processed.column_attributes:
            self.data.processed.column_attributes[col_key] = {}

        self.data.processed.column_attributes[col_key][row_key] = value

    def update_column_attributes_on_combobox_change(self, value, row_key, col_key):
        if col_key not in self.data.processed.column_attributes:
            self.data.processed.column_attributes[col_key] = {}
        self.data.processed.column_attributes[col_key][row_key] = value


    def update_column_attributes_on_cell_change(self, item):
        row = item.row()
        col = item.column()

        # Ignore header row/column (0)
        if row == 0 or col == 0:
            return

        # Get the row and column keys
        row_key = self.metadata_table.verticalHeaderItem(row).text()
        col_key = self.metadata_table.horizontalHeaderItem(col).text()

        attibute_dtype =  self.editable_rows.get(row_key)
        # Only update editable rows
        if attibute_dtype == bool:
            return  # Skip boolean — handled via checkbox callback

        # Update column_attributes
        if col_key not in self.data.processed.column_attributes:
            self.data.processed.column_attributes[col_key] = {}
        
        # store attribute in specified dtype
        if attibute_dtype == float:
            self.data.processed.column_attributes[col_key][row_key] = fmt.oround(float(item.text()), order=2, toward=0)
        else:
            self.data.processed.column_attributes[col_key][row_key] = item.text()

    def on_attribute_batch_changed(self, columns, attribute, values):
        # Map row keys and column keys to indices
        row_map = {
            self.metadata_table.verticalHeaderItem(i).text(): i
            for i in range(1, self.metadata_table.rowCount())
        }
        col_map = {
            self.metadata_table.horizontalHeaderItem(i).text(): i
            for i in range(1, self.metadata_table.columnCount())
        }

        # Only update if the attribute (row) and column are currently visible
        if attribute not in row_map:
            return

        row_idx = row_map[attribute]
        for col_name, val in zip(columns, values):
            if col_name not in col_map:
                continue
            col_idx = col_map[col_name]

            editor_type = self.editable_rows.get(attribute)

            if editor_type == bool:
                widget = self.metadata_table.cellWidget(row_idx, col_idx)
                if isinstance(widget, QCheckBox):
                    widget.setChecked(bool(val))

            elif isinstance(editor_type, list):  # e.g., norm choices
                widget = self.metadata_table.cellWidget(row_idx, col_idx)
                if isinstance(widget, QComboBox):
                    widget.setCurrentText(str(val))

            else:
                item = self.metadata_table.item(row_idx, col_idx)
                if item:
                    item.setText(str(val))

    def export_metadata(self):
        if not hasattr(self.parent.ui,"notes_dock"):
            return
        
        notes = self.parent.ui.notes_dock
        pass

# -------------------------------
# Data Tab functions
# -------------------------------
class DataFrameTab():
    """Creates the data info tab for plots and annotations.

    Parameters
    ----------
    parent : QTabWidget, optional
        Parent tab widget that will contain this tab.
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

        self.action_sigfigs_more = CustomAction(
            text="Increase Significant Figures",
            light_icon_unchecked="icon-sigfigs-add-64.svg",
            dark_icon_unchecked="icon-sigfigs-add-dark-64.svg",
            parent=toolbar,
        )
        self.action_sigfigs_more.triggered.connect(increase_precision)
        self.action_sigfigs_more.triggered.connect(lambda: update_dataframe(self.data.processed, self.data_table))
        self.action_sigfigs_more.setToolTip("Increase the number of displayed digits")

        self.action_sigfigs_less = CustomAction(
            text="Decrease Significant Figures",
            light_icon_unchecked="icon-sigfigs-remove-64.svg",
            dark_icon_unchecked="icon-sigfigs-remove-dark-64.svg",
            parent=toolbar
        )
        self.action_sigfigs_less.triggered.connect(decrease_precision)
        self.action_sigfigs_less.triggered.connect(lambda: update_dataframe(self.data.processed, self.data_table))
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

        update_dataframe(self.data.processed, self.data_table)


# -------------------------------
# Field Tab functions
# -------------------------------
class FieldTab(FieldLogicUI):
    """Creates the field info tab for plots and annotations.

    Parameters
    ----------
    parent : QTabWidget
        Parent tab widget that will contain this tab.
    """
    def __init__(self, parent):
        super().__init__(parent)

        if not parent.data:
            return
        self.data = parent.data
        self.app_data = parent.app_data
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

        self.action_sigfigs_more = CustomAction(
            text="Increase Significant Figures",
            light_icon_unchecked="icon-sigfigs-add-64.svg",
            dark_icon_unchecked="icon-sigfigs-add-dark-64.svg",
            parent=toolbar,
        )
        self.action_sigfigs_more.triggered.connect(increase_precision)
        self.action_sigfigs_more.triggered.connect(self.update_field_table)
        self.action_sigfigs_more.setToolTip("Increase the number of displayed digits")

        self.action_sigfigs_less = CustomAction(
            text="Decrease Significant Figures",
            light_icon_unchecked="icon-sigfigs-remove-64.svg",
            dark_icon_unchecked="icon-sigfigs-remove-dark-64.svg",
            parent=toolbar
        )
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
        self.update_field_type_combobox(self.field_type_combobox)
        
        # when field combobox is updated
        self.field_combobox.activated.connect(self.update_field_table)

        self.update_field_table()

    def update_field_table(self):
        if self.field_combobox.currentText() == '' or self.field_type_combobox.currentText() == '':
            return

        map_df = self.data.get_map_data(self.field_combobox.currentText(), self.field_type_combobox.currentText())
        reshaped_array = np.reshape(map_df['array'].values, self.data.array_size, order=self.data.order)
        update_numpy_array(reshaped_array, self.field_table)



class FloatItemDelegate(QStyledItemDelegate):
    """Custom item delegate for handling float input in QTableWidget.       
    This delegate allows for editing of float values in the table, with validation
    to ensure that the input is within a specified range and has a defined precision.       
    It is particularly useful for fields like 'plot_min' and 'plot_max' where the values
    need to be constrained to the actual data range.
    Parameters
    ----------
    metadata_table : QTableWidget
        The table where the delegate will be applied.
    row_labels : list
        List of row labels corresponding to the table rows (e.g., ['min', 'max', 'plot_min', 'plot_max', ...]).
    column_keys : list
        List of column keys corresponding to the table columns (e.g., ['Vp', 'Resistivity']).
    data : dict
        The full dataset containing processed data for each sample.
    sample_id : str
        The ID of the sample currently being viewed or edited.
    special_rows : set, optional
        A set of special row labels that require specific validation (e.g., 'plot_min',
        'plot_max'). Defaults to None, which means no special rows.
    precision : int, optional
        The number of decimal places to which float values should be rounded. Defaults to 3.
    """
    def __init__(self, parent, row_labels, column_keys, processed_data, special_rows=None, precision=3):
        super().__init__(parent)
        self.row_labels = row_labels        # e.g., ['min', 'max', 'plot_min', 'plot_max', ...]
        self.column_keys = column_keys      # Mapping col_idx to key (e.g., ['Vp', 'Resistivity'])
        self.processed = processed_data
        self.special_rows = special_rows or set()
        self.precision = precision

    def createEditor(self, parent, option, index):
        row = index.row() - 1   # -1 because header row is at index 0
        col = index.column() - 1

        editor = QLineEdit(parent)
        validator = QDoubleValidator(parent)

        if row >= 0 and col >= 0:
            row_label = self.row_labels[row]
            col_key = self.column_keys[col]

            # If it's a plot_min or plot_max row, restrict range to actual data
            if row_label in self.special_rows:
                col_data = self.processed[col_key]
                amin, amax = np.min(col_data), np.max(col_data)
                validator.setRange(amin, amax)

                validator.setDecimals(self.precision)
                editor.setValidator(validator)

        return editor
