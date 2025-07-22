from PyQt6.QtWidgets import ( 
        QWidget, QLineEdit, QTableWidget, QComboBox, QPushButton, QCheckBox, QWidget, QTreeView,
        QMenu, QDockWidget, QHeaderView, QToolButton, QSlider, QVBoxLayout, QHBoxLayout, QLabel,
    )
from PyQt6.QtGui import (
    QStandardItem, QStandardItemModel, QFont, QDoubleValidator, QIcon, QCursor, QPainter,
    QColor, QAction, QIcon
)
from PyQt6.QtCore import Qt, QRect, QPropertyAnimation, pyqtProperty, pyqtSignal, QSize
import src.common.format as fmt
import pandas as pd

from src.common.colorfunc import is_valid_hex_color

class CustomLineEdit(QLineEdit):
    """Custom line edit widget, when the only input should be of type float

    Adds additional functionality to QLineEdit by installing a validator and methods for limiting the
    precision of the displayed value in the UI.  Note that full precision of the value is stored in
    self.value, only a 'pretty' number is displayed.

    Parameters
    ----------
    parent : _type_, optional
        _description_, by default None
    value : float, optional
        _description_, by default 0.0
    precision : int, optional
        _description_, by default 4
    threshold : _type_, optional
        _description_, by default 1e4
    toward : int, optional
        _description_, by default None
    validator : QValidator, optional
        Provide a validator to automatically text inputs for appropriate type and
        ranges, by default QDoubleValidator
    """        
    def __init__(self, parent=None, value=0.0, precision=4, threshold=1e4, toward=None, validator=QDoubleValidator()):
        super().__init__(parent)
        self._value = value
        self._precision = precision
        self._threshold = threshold
        self._toward = toward
        self._lower_bound = None
        self._upper_bound = None
        self.textChanged.connect(self._update_value_from_text)
        self.setValidator(validator)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)

    @property
    def value(self):
        """
        float: The current internal numeric value stored in the widget.
        """
        return self._value

    @value.setter
    def value(self, new_value):
        """
        Set the internal value and update the displayed text accordingly.

        Parameters
        ----------
        new_value : float
            The new value to store and display.
        """
        # ensure value is a float rather than integer
        if self._lower_bound is not None:
            new_value = max(self._lower_bound, new_value)
        if self._upper_bound is not None:
            new_value = min(self._upper_bound, new_value)
        self._value = new_value
        self._update_text_from_value()

    @property
    def precision(self):
        """
        int: The number of significant digits to display in the line edit.
        """
        return self._precision 

    @precision.setter
    def precision(self, new_precision):
        """
        Set the display precision and update the text accordingly.

        Parameters
        ----------
        new_precision : int
            New number of significant digits to display.
        """
        self._precision = new_precision
        self._update_text_from_value
    
    @property
    def threshold(self):
        """
        float: Threshold above which scientific notation is used.
        """
        return self._threshold
    
    @threshold.setter
    def threshold(self, new_threshold):
        """
        Set the threshold for scientific notation and update the text.

        Parameters
        ----------
        new_threshold : float
            Value above which to switch to scientific notation.
        """
        self._threshold = new_threshold
        self._update_text_from_value

    @property
    def toward(self):
        """
        int | float | None: Determines rounding direction in formatting.

        * 0 = round toward zero
        * 1 = round away from zero
        * None = standard rounding
        """
        return self._toward
    
    @toward.setter
    def toward(self, val):
        """
        Set the rounding direction and update the display.

        Parameters
        ----------
        val : int, float, or None
            Rounding mode to apply in formatting.
        """
        self._toward = val
        self._update_text_from_value

    def set_bounds(self, lower=None, upper=None):
        """Set optional lower and upper bounds for the value."""
        self._lower_bound = lower
        self._upper_bound = upper
        # Apply clamping if value already exists
        self.value = self._value

    def _update_text_from_value(self):
        """
        Update the displayed text based on internal value and formatting rules.
        """
        if self._value is None:
            self.setText('')
        elif self._precision is None:
            self.setText(str(self._value))
        else:
            self.setText(fmt.dynamic_format(self._value, threshold=self._threshold, order=self._precision, toward=self._toward))
            #self.setText(f"{self._value:.{self._precision}f}")

    def _update_value_from_text(self):
        """
        Update the internal value from the current text, if valid.
        """
        try:
            new_val = float(self.text())
            # Clamp if bounds are defined
            if self._lower_bound is not None:
                new_val = max(self._lower_bound, new_val)
            if self._upper_bound is not None:
                new_val = min(self._upper_bound, new_val)
            self._value = new_val
        except ValueError:
            # ignore error
            pass

class CustomTableWidget(QTableWidget):
    """
    A QTableWidget subclass with extended utility functions for data extraction and conversion.

    This widget supports conversion of table contents (including embedded widgets such as 
    QLineEdit, QComboBox, QCheckBox, etc.) to a pandas DataFrame, and provides convenience 
    methods for column-based data access. It is designed for integration with tools that 
    dynamically populate cells with interactive widgets.

    Examples
    --------
    >>> widget = CustomTableWidget()
    >>> widget.to_dataframe()
    >>> widget.column_to_list(0)
    >>> widget.column_to_list("Sample Name")

    Notes
    -----
    - Embedded widgets are interpreted based on their type (e.g., `QLineEdit.text()`, 
      `QCheckBox.isChecked()`).
    - Additional widget types can be handled by extending `extract_widget_data()`.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def extract_widget_data(self, widget: QWidget):
        """
        Extracts relevant data from a widget embedded in the table.

        This method is used to obtain the appropriate value representation of a widget 
        for export (e.g., into a DataFrame).

        Parameters
        ----------
        widget : QWidget
            A widget stored in a table cell.

        Returns
        -------
        str or bool or float or None
            The value extracted from the widget, depending on its type.
        """   
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        elif isinstance(widget, QPushButton):
            return widget.text()
        elif isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, CustomLineEdit):
            return widget.value
        # Add more widget types as needed
        else:
            return None

    def to_dataframe(self) -> pd.DataFrame:
        """
        Converts the table content (including widgets) to a pandas DataFrame.

        Returns
        -------
        pd.DataFrame
            A DataFrame with rows and columns matching the table content.
        """
        # Get the number of rows and columns in the QTableWidget
        row_count = self.rowCount()
        column_count = self.columnCount()

        
        # Create a dictionary to store the data with column headers
        column_headers = [self.horizontalHeaderItem(col).text() if self.horizontalHeaderItem(col) is not None else f'Column {col+1}' 
                          for col in range(column_count)]
        
        table_data = {
            column_headers[col]: [
                self.item(row, col).text() if self.item(row, col) is not None else self.extract_widget_data(self.cellWidget(row, col)) 
                for row in range(row_count)
            ] for col in range(column_count)
        }

        # table_data = {self.horizontalHeaderItem(col).text(): [] for col in range(column_count)}
        
        # # Iterate over all rows and columns to retrieve the data
        # for row in range(row_count):
        #     for col in range(column_count):
        #         item = self.item(row, col)
        #         if item is not None:
        #             table_data[self.horizontalHeaderItem(col).text()].append(item.text())
        #         else:
        #             # Check for a widget in the cell
        #             widget = self.cellWidget(row, col)
        #             if widget is not None:
        #                 table_data[self.horizontalHeaderItem(col).text()].append(self.extract_widget_data(widget))
        #             else:
        #                 table_data[self.horizontalHeaderItem(col).text()].append(None)
        
        # Convert the dictionary to a pandas DataFrame
        df = pd.DataFrame(table_data)
        
        return df

    def column_to_list(self, column):
        """
        Extracts data from a specified column into a list.

        Parameters
        ----------
        column : int or str
            Column index (int) or column header name (str).

        Returns
        -------
        list
            A list of cell values from the specified column.

        Raises
        ------
        ValueError
            If the specified column name or index is not found.
        """
        column_index = None
        if isinstance(column, int):
            column_index = column
        elif isinstance(column, str) :
            for col in range(self.columnCount()):
                header_text = self.horizontalHeaderItem(col).text()
                if header_text == column:
                    column_index = col
                    break

        if column_index is None:
            raise ValueError(f"Column '{column}' not found")

        # Loop through each row in the column
        column_data = []
        for row in range(self.rowCount()):
            item = self.item(row, column_index)  # Get QTableWidgetItem at (row, column_index)
            
            # Check if item exists (not None) and add its text to the list
            if item:
                column_data.append(item.text())
            else:
                column_data.append('')  # Handle empty cells if needed
        
        return column_data


class RotatedHeaderView(QHeaderView):
    """
    A custom QHeaderView that displays horizontal headers rotated by 90 degrees.

    This header view is useful for tables with many columns where horizontal space
    is constrained. It transposes the size hint and rotates the header text during
    painting to display the headers vertically.

    Parameters
    ----------
    parent : QWidget, optional
        The parent widget (typically a QTableView).

    Attributes
    ----------
    orientation : Qt.Orientation
        The orientation of the header view. Fixed to Qt.Horizontal.
    minimumSectionSize : int
        The minimum size of each header section, set to 20 pixels.

    Methods
    -------
    paintSection(painter, rect, logicalIndex)
        Paints a rotated header section by -90 degrees.
    minimumSizeHint()
        Returns the transposed minimum size hint for the rotated layout.
    sectionSizeFromContents(logicalIndex)
        Returns the transposed section size to accommodate vertical text.
    """
    def __init__(self, parent=None):
        super(RotatedHeaderView, self).__init__(Qt.Orientation.Horizontal, parent)
        self.setMinimumSectionSize(20)

    def paintSection(self, painter, rect, logicalIndex ):
        """
        Paint a single section of the header, rotating the text by -90 degrees.

        Parameters
        ----------
        painter : QPainter
            The painter used to draw the section.
        rect : QRect
            The bounding rectangle of the section.
        logicalIndex : int
            The index of the section being painted.
        """
        if painter:
            painter.save()
            # translate the painter to the appropriate position
            painter.translate(rect.x(), rect.y() + rect.height())
            painter.rotate(-90)  # rotate by -90 degrees
            # and have parent code paint at this location
            newrect = QRect(0,0,rect.height(),rect.width())
            super(RotatedHeaderView, self).paintSection(painter, newrect, logicalIndex)
            painter.restore()

    def minimumSizeHint(self):
        """
        Return the minimum size hint for the header.

        Returns
        -------
        QSize
            The minimum size hint, transposed due to rotation.
        """
        size = super(RotatedHeaderView, self).minimumSizeHint()
        size.transpose()
        return size

    def sectionSizeFromContents(self, logicalIndex):
        """
        Return the size of a section, adjusted for rotated text.

        Parameters
        ----------
        logicalIndex : int
            The index of the section.

        Returns
        -------
        QSize
            The size of the section, transposed for vertical layout.
        """
        size = super(RotatedHeaderView, self).sectionSizeFromContents(logicalIndex)
        size.transpose()
        return size
    
class StandardItem(QStandardItem):
    """Extends properties of QStandardItem for QTreeView and QList items.

    Parameters
    ----------
    txt : str, optional
        Text displayed in tree or list, by default ``''``
    font_size : int, optional
        fontsize, by default ``10``
    set_bold : bool, optional
        Bold tree font when ``True``, by default ``False``
    """    
    def __init__(self, txt='', font_size=10, set_bold=False, data=None):
        super().__init__()

        # Set item font
        fnt = QFont()
        fnt.setPointSize(font_size)
        fnt.setBold(set_bold)

        self.setEditable(False)
        self.setText(txt)
        self.setFont(fnt)
        if data is not None:
            self.setData(data)

class CustomTreeView(QTreeView):
    """
    A customized QTreeView widget for managing a hierarchical tree structure.

    Provides functionality to create branches and leaves in a QStandardItemModel-based tree,
    search for items, retrieve paths and associated data, sort branches, and handle UI events.
    
    Attributes
    ----------
    treeModel : QStandardItemModel
        The data model used for the tree.
    root_node : QStandardItem
        The invisible root node of the tree model.

    Parameters
    ----------
    parent : QWidget, optional
        The parent widget, by default None.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.treeModel = QStandardItemModel()
        self.root_node = self.treeModel.invisibleRootItem()
        self.setModel(self.treeModel)
    
    def branch_exists(self, parent_item, branch_name):
        """
        Check if a branch with a given name exists under the specified parent item.

        Parameters
        ----------
        parent_item : QStandardItem
            The item to search under.
        branch_name : str
            The name of the branch to look for.

        Returns
        -------
        QStandardItem or None
            The branch item if found, otherwise None.
        """
        for row in range(parent_item.rowCount()):
            item = parent_item.child(row)
            if item.text() == branch_name:
                return item  # Return the branch if found
        return None  # Branch not found
    
    def add_branch(self, parent_item, branch_name, data=None):
        """
        Add a new branch to the tree under the specified parent.

        Parameters
        ----------
        parent_item : QStandardItem
            The parent item to add the branch to.
        branch_name : str
            The name of the new branch.
        data : any, optional
            Optional data to associate with the branch.

        Returns
        -------
        QStandardItem
            The created branch item.
        """
        branch_item = StandardItem(branch_name, 10, True, data)
        parent_item.appendRow(branch_item)
        return branch_item
    
    def add_leaf(self, branch_item, leaf_name, data=None):
        """
        Add a new leaf to a branch.

        Parameters
        ----------
        branch_item : QStandardItem
            The branch item to which the leaf will be added.
        leaf_name : str
            The name of the new leaf.
        data : any, optional
            Optional data to associate with the leaf.

        Returns
        -------
        QStandardItem
            The created leaf item.
        """
        leaf_item = StandardItem(leaf_name, 10, False, data)
        branch_item.appendRow(leaf_item)
        return leaf_item

    def get_item_path(self, item):
        """
        Return the full path of an item as a list from root to the given item.

        Parameters
        ----------
        item : QStandardItem
            The item whose path is to be retrieved.

        Returns
        -------
        list of str
            A list representing the hierarchy from root to the item.
        """
        path = []
        while item is not None:
            path.insert(0, item.text())
            item = item.parent()
        return path
    
    def get_leaf_data(self, leaf_item):
        """
        Return the full path of an item as a list from root to the given item.

        Parameters
        ----------
        item : QStandardItem
            The item whose path is to be retrieved.

        Returns
        -------
        list of str
            A list representing the hierarchy from root to the item.
        """
        return leaf_item.data()
    
    def find_leaf(self, branch_item, leaf_name):
        """
        Find a leaf under a branch by its name.

        Parameters
        ----------
        branch_item : QStandardItem
            The branch item to search within.
        leaf_name : str
            The name of the leaf to find.

        Returns
        -------
        QStandardItem or None
            The leaf item if found, otherwise None.
        """
        for row in range(branch_item.rowCount()):
            leaf = branch_item.child(row)
            if leaf.text() == leaf_name:
                return leaf
        return None

    def sort_branch(self, branch, order_list):
        """
        Sorts a branch in the treeView given an ordered list.

        Parameters
        ----------
        branch : QStandardItem
            Branch to sort leaf items.
        order_list : list
            The desired order for the leaf items.
        """        
        # Collect all children (leaves) under the branch into a list
        leaf_items = []
        for i in range(branch.rowCount()):
            leaf_items.append(branch.takeChild(i))
        
        # Sort the leaves based on the provided order list
        # Items not in order_list will be placed at the end
        leaf_items.sort(key=lambda x: order_list.index(x.text()) if x.text() in order_list else len(order_list))

        # Remove the items within the branch first and then replace it with the sorted ones
        branch.removeRows(0, branch.rowCount())
        
        # Add sorted items back to the branch
        for i, leaf in enumerate(leaf_items):
            branch.insertRow(i, leaf)

    def on_double_click(self, index):
        """
        Handle a double-click event on an item in the tree.

        Parameters
        ----------
        index : QModelIndex
            Index of the clicked item.
        """
        item = self.treeModel.itemFromIndex(index)
        item_path = self.get_item_path(item)
        leaf_data = self.get_leaf_data(item)
        print(f"Double-clicked on: {item_path}, Data: {leaf_data}")

    def clear_tree(self):
        """
        Clears all items from the tree model.
        """
        try:
            self.treeModel.clear()
        except Exception as e:
            print(f"Error while clearing model: {e}")

class CustomActionMenu(QAction):
    """
    A custom QMenu that allows dynamic addition and removal of menu actions.

    Attributes
    ----------
    items : dict[str, QAction]
        A dictionary mapping action names (as strings) to their corresponding QAction objects.

    Methods
    -------
    add_menu_item(name: str, callback: Callable, shortcut: Optional[str] = None, tooltip: Optional[str] = None) -> None
        Add a single menu item with an optional shortcut and tooltip.

    remove_menu_item(name: str) -> None
        Remove a menu item by name if it exists.

    _add_menu_items(items: list[tuple[str, Callable, Optional[str], Optional[str]]]) -> None
        Add multiple menu items in one batch operation.

    clear_menu() -> None
        Remove all existing menu actions from the menu and clear the internal items dictionary.

    update_menu(items: list[tuple[str, Callable, Optional[str], Optional[str]]]) -> None
        Clear and rebuild the menu using the provided list of items.

    get_menu_item(name: str) -> Optional[QAction]
        Return the QAction associated with the given name, or None if not found.

    get_menu_structure() -> nested list
        Return current menu structure as a nested list.

    has_submenu(name: str) -> bool
        Check if a submenu by a specific name exists.

    Parameters
    ----------
    icon : str
        Path to the icon displayed in the action.
    text : str
        Text label for the action.
    menu_items : list
        Initial list of menu items and submenus to add.
    parent : QWidget, optional
        Parent widget for the action and menu.
    """
    def __init__(self, icon, text, menu_items, parent=None):
        super().__init__(QIcon(icon), text, parent)
        
        # Create the main menu
        self.menu = QMenu(parent)

        # Dictionary to hold references to dynamically updatable submenus
        self.submenu_references = {}

        # Populate the menu
        self._add_menu_items(self.menu, menu_items)

        # Function to display the menu
        def show_menu():
            self.menu.exec(QCursor.pos())

        # Connect the action to the show_menu function
        self.triggered.connect(show_menu)

    def _add_menu_items(self, menu, items):
        """
        Recursively adds menu items to the given QMenu.

        Parameters
        ----------
        menu : QMenu
            The parent menu to which items will be added.
        items : list of tuples
            A list where each tuple represents a menu item.

            Each tuple must be of the form:
                (str, Callable | list | None)

            - If the second element is a callable, it will be connected to the triggered signal of a QAction.
            - If it's a list, a submenu will be created with that list as its content (recursively).
            - If it's None, a disabled/non-interactive menu item will be added (useful as a label or placeholder).

        Example
        -------

        .. code-block:: python

            items = [
                ("Export", export_callback),
                ("Import", [
                    ("From CSV", import_csv_callback),
                    ("From JSON", import_json_callback)
                ]),
                ("Disabled Item", None)
            ]

        """
        for item_text, callback_or_submenu in items:
            if isinstance(callback_or_submenu, list):
                # Create a submenu
                submenu = QMenu(item_text, menu)
                self.submenu_references[item_text] = submenu  # Store a reference
                self._add_menu_items(submenu, callback_or_submenu)
                menu.addMenu(submenu)
            else:
                # Add a regular action
                menu.addAction(item_text, callback_or_submenu)

    def update_menu(self, new_items):
        """Replace the entire menu with a new structure.


        Parameters
        ----------
        new_items : list of tuples
            A list where each tuple represents a menu item.

            Each tuple must be of the form:
                (str, Callable | list | None)

        :see also: _add_menu_items
        """
        self.clear_menu()
        self._add_menu_items(self.menu, new_items)

    def update_submenu(self, submenu_name, new_items):
        """
        Update a submenu with new items.
        
        Parameters
        ----------
        submenu_name : str
            Name of submenu
        new_items : items
            A list where each tuple represents a menu item.

            Each tuple must be of the form:
                (str, Callable | list | None)

        :see also: _add_menu_items
        """
        submenu = self.submenu_references.get(submenu_name)
        if submenu:
            submenu.clear()  # Remove all current actions
            self._add_menu_items(submenu, new_items)

    def clear_menu(self):
        """Clear all actions and submenus from the menu."""
        self.menu.clear()
        self.submenu_references.clear()

    def add_menu_item(self, text, callback_or_submenu):
        """
        Adds a single menu item to the specified QMenu.

        Parameters:
            menu (QMenu): The menu to which the item will be added.
            label (str): The text label for the menu item.
            action (Callable | None): The function to be called when the menu item is triggered.
                If None, the menu item will be added as a non-interactive (disabled) item.

        Returns:
            QAction: The QAction object that was added to the menu.

        Example
        -------

        .. code-block:: python

            self.add_menu_item(file_menu, "Open", self.open_file)
            self.add_menu_item(help_menu, "About", None)  # Adds a non-clickable item
        """
        self._add_menu_items(self.menu, [(text, callback_or_submenu)])


    def remove_menu_item(self, menu_path):
        """
        Remove a menu item or submenu by its path.

        Parameters
        ----------
        menu_path : list of str
            A list representing the hierarchical path to the item.
            For example, ['Top Level', 'Submenu', 'Item Text'] will remove
            the action or submenu named 'Item Text' inside 'Submenu' which is
            under 'Top Level'.

        Returns
        -------
        bool
            True if the item was found and removed, False otherwise.

        Examples
        --------
        
        To remove 'Export' from the 'File' top level,

        .. code-block:: python

            action.remove_menu_item(['File', 'Export'])

        """
        if not menu_path:
            return False

        menu = self.menu
        for part in menu_path[:-1]:
            found = None
            for action in menu.actions():
                if action.menu() and action.text() == part:
                    found = action.menu()
                    break
            if not found:
                return False
            menu = found

        for action in menu.actions():
            if action.text() == menu_path[-1]:
                menu.removeAction(action)
                return True

        return False

    def get_menu_structure(self):
        """
        Return current menu structure as a nested list.
         
        This method is useful for debugging or serialization.

        Returns
        -------
        nested list
            Current menu structure.
        """
        def recurse(menu):
            items = []
            for action in menu.actions():
                if action.menu():
                    items.append((action.text(), recurse(action.menu())))
                else:
                    items.append((action.text(), None))
            return items
        return recurse(self.menu)
    
    def has_submenu(self, name):
        """Check if a submenu by a specific name exists.
        
        Parameters
        ----------
        name : str
            Submenu text to test

        Returns
        -------
        bool
            True if `name` is a submenu
        """
        return name in self.submenu_references

class CustomComboBox(QComboBox):
    """
    A QComboBox subclass with support for dynamic item updates before showing the popup.

    This custom combo box allows you to define a callback function that is executed
    each time the combo box is about to display its dropdown list. This is useful for
    updating the list of items dynamically based on application state.

    Attributes
    ----------
    popup_callback : callable or None
        A function to be executed immediately before the popup is shown. Typically used
        to refresh or modify the items in the combo box.

    Methods
    -------
    allItems() -> list[str]
        Returns a list of all item texts currently in the combo box.
    showPopup()
        Overrides the base class method to invoke the callback (if set) before showing the popup.

    Parameters
    ----------
    popup_callback : callable, optional
        A function that updates the combo box items before display. Default is None.
    *args, **kwargs : 
        Additional arguments passed to the QComboBox constructor.

    Examples
    --------

    .. code-block:: python
        def refresh_items():
            combo.clear()
            combo.addItems(["A", "B", "C"])

        combo = CustomComboBox(popup_callback=refresh_items)
        combo.show()  # Each time the dropdown is opened, items are refreshed
    """
    def __init__(self, popup_callback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.popup_callback = popup_callback

    def allItems(self):
        """Return a list of all item texts in the combobox."""
        return [self.itemText(i) for i in range(self.count())]

    def showPopup(self):
        """
        Executes the popup callback (if any) before showing the dropdown list.

        Overrides the QComboBox method to inject behavior that updates the
        combobox contents just before it is shown to the user.
        """
        if self.popup_callback:
            self.popup_callback()
        super().showPopup()

class CustomDockWidget(QDockWidget):
    """
    A custom QDockWidget that hides instead of closing when the user clicks the close button.

    This subclass of QDockWidget overrides the standard close behavior so that the widget
    is simply hidden rather than destroyed. This allows the widget to be shown again later
    without needing to be re-instantiated.

    Parameters
    ----------
    parent : QWidget, optional
        The parent widget, typically a QMainWindow. Default is None.

    Methods
    -------
    closeEvent(event: QEvent)
        Hides the dock instead of closing it when the user clicks the close button.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.show()

        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)

    def closeEvent(self, event):
        """
        Override the default close event to hide the dock widget instead of closing it.

        This prevents the widget from being destroyed and allows it to be shown again later
        via `widget.show()`.

        Parameters
        ----------
        event : QEvent
            The close event triggered by the user action.
        """
        self.hide()
        if event:
            event.ignore()  # Ignore the close event to prevent the widget from being removed.

class ToggleSwitch(QWidget):
    """
    A custom toggle switch widget with animated transitions and customizable colors.

    This widget mimics a modern on/off switch, commonly used in mobile and web UIs. It supports 
    smooth animated transitions between the "on" and "off" states, emits a signal when toggled, 
    and provides optional customization for height, animation duration, and colors.

    Parameters
    ----------
    parent : QWidget, optional
        The parent widget, by default None.
    height : int, optional
        Height of the toggle switch. The width is automatically set to twice the height. Default is 24.
    duration : int, optional
        Duration of the toggle animation in milliseconds. Default is 100.
    fg_color : str, optional
        Foreground color (thumb/slider) in hex format. Default is "#f0f0f0".
    bg_left_color : str, optional
        Background color when the switch is in the "off" position. Default is "#ffffff".
    bg_right_color : str, optional
        Background color when the switch is in the "on" position. Default is "#478ae4".

    Signals
    -------
    stateChanged : bool
        Emitted when the switch state changes.

    Attributes
    ----------
    thumb_pos : float
        Position of the thumb (used for animation).
    
    Methods
    -------
    toggle()
        Toggles the switch state and emits the `stateChanged` signal.
    setChecked(checked)
        Sets the checked state and animates the thumb.
    isChecked() -> bool
        Returns the current checked state.
    """
    stateChanged = pyqtSignal(bool)  # Signal emitted when the state changes

    def __init__(self, parent=None, height=24, duration=100, fg_color="#f0f0f0", bg_left_color="#ffffff", bg_right_color="#478ae4"):
        super().__init__(parent)
        self._height = height
        self._width = height * 2
        self.setFixedSize(self._width, self._height)

        self._checked = False

        self._thumb_pos = 2  # Initial position
        self.duration = duration

        self._animation = QPropertyAnimation(self, b"thumb_pos")
        self._animation.setDuration(duration)  # Smooth animation

        if is_valid_hex_color(fg_color):
            self.fg_color = fg_color
        else:
            self.fg_color = "#f0f0f0"

        # background colors
        if is_valid_hex_color(bg_left_color):
            self.bg_left_color = bg_left_color
        else:
            self.bg_left_color = "#ffffff"
        if is_valid_hex_color(bg_right_color):
            self.bg_right_color = bg_right_color
        else:
            self.bg_right_color="#478ae4"

    def toggle(self):
        """Toggle switch state and emit signal"""
        self._checked = not self._checked
        self._animation.setStartValue(self._thumb_pos)
        self._animation.setEndValue(self._width - self._height + 2 if self._checked else 2)
        self._animation.start()

        self.stateChanged.emit(self._checked)  # Emit signal

    def setChecked(self, checked: bool):
        """Sets the checked state of the toggle switch and triggers the animation

        Parameters
        ----------
        checked : bool
            New check state of the toggle switch.
        """
        if self._checked != checked:
            self._checked = checked
            start = self._thumb_pos
            end = self._width - self._height + 2 if self._checked else 2
            self._animation.stop()
            self._animation.setStartValue(start)
            self._animation.setEndValue(end)
            self._animation.start()
            self.stateChanged.emit(self._checked)


    def isChecked(self) -> bool:
        """Return the current state of the toggle switch.
        
        Returns
        -------
        bool
            Returns checked state of the toggle switch
        """
        return self._checked

    def mousePressEvent(self, event):
        """
        Handles mouse press events to toggle the switch state when clicked.

        If the left mouse button is pressed, this method toggles the checked state of the switch.

        Parameters
        ----------
        event : QMouseEvent
            The mouse event triggered by the user interaction.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)

    def sizeHint(self):
        """Returns the size of the toggle switch.
        
        Returns
        -------
        size : QSize
            Returns the size of the toggle switch.
        """
        return self.size()

    def paintEvent(self, event):
        """Draw the toggle switch.

        Draws the toggle switch.

        Parameters
        ----------
        event : QEvent
        """
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Draw background
            bg_color = QColor(self.bg_right_color if self._checked else self.bg_left_color)
            painter.setBrush(bg_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(0, 0, self._width, self._height, self._height // 2, self._height // 2)


            # Draw the thumb (slider)
            thumb_diameter = self._height - 4
            painter.setBrush(QColor(self.fg_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QRect(int(self._thumb_pos), 2, thumb_diameter, thumb_diameter))
        finally:
            painter.end()

    def get_thumb_pos(self):
        """Returns the thumb position."""
        return self._thumb_pos

    def set_thumb_pos(self, pos):
        """Sets the thumb position.
        
        Paramters
        ---------
        pos : int
            Thumb position"""
        self._thumb_pos = pos
        self.update()  # Redraw switch

    thumb_pos = pyqtProperty(float, get_thumb_pos, set_thumb_pos)


class CustomCheckButton(QToolButton):
    """A button that changes icons when checked

    Parameters
    ----------
    icon_unchecked : QIcon
        Unchecked icon.
    icon_checked : QIcon
        Checked icon.
    parent : QToolButton
        Tool button to set icons.

    Methods
    -------
    update_icon()
        Update the icon based on the button's checked state.
    """
    def __init__(self, icon_unchecked: QIcon, icon_checked: QIcon, parent=None):
        super().__init__(parent)

        # icons for checked and unchecked states
        self.icon_checked = icon_checked
        self.icon_unchecked = icon_unchecked

        # button properties
        self.setFixedSize(24, 24)
        self.setIconSize(QSize(18, 18))

        # initialize checked state and icon
        self.setCheckable(True)
        self.setChecked(False)
        self.update_icon()
    
    def update_icon(self):
        """Update the icon based on the button's checked state."""
        if self.isChecked():
            self.setIcon(self.icon_checked)
        else:
            self.setIcon(self.icon_unchecked)

class CustomSlider(QWidget):
    """
    A custom slider widget that combines a horizontal QSlider and a QLabel.

    This widget displays the current slider value in a label and emits custom signals
    for common slider events. It supports setting initial value, range, and step size.

    Parameters
    ----------
    min_value : float, optional
        Minimum value of the slider range (default is 0).
    max_value : float, optional
        Maximum value of the slider range (default is 100).
    step : float, optional
        Increment between values (default is 1).
    initial_value : float, optional
        Initial slider value (default is 50).
    parent : QWidget, optional
        Parent widget (default is None).

    Signals
    -------
    valueChanged(int)
        Emitted when the slider's value changes.
    sliderMoved(int)
        Emitted while the slider is being dragged.
    sliderReleased(int)
        Emitted when the slider handle is released.
    sliderPressed(int)
        Emitted when the slider handle is pressed.
    """
    valueChanged = pyqtSignal(int)
    sliderMoved = pyqtSignal(int)
    sliderReleased = pyqtSignal(int)
    sliderPressed = pyqtSignal(int)

    def __init__(self, min_value=0, max_value=100, step=1, initial_value=50, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout()
        
        # Create label to display slider value
        self.label = QLabel(f"Value: {initial_value}")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(min_value)
        self.slider.setMaximum(max_value)
        self.slider.setSingleStep(step)
        self.slider.setValue(initial_value)
        
        # Connect slider movement to label update
        self.slider.valueChanged.connect(self.update_label)
        self.slider.valueChanged.connect(self.valueChanged.emit)  # Emit custom signal
        self.slider.sliderMoved.connect(self.update_label)
        self.slider.sliderMoved.connect(self.sliderMoved.emit)
        self.slider.sliderReleased.connect(self.update_label)
        self.slider.sliderReleased.connect(self.sliderReleased.emit)
        self.slider.sliderPressed.connect(self.sliderPressed.emit)
        
        # Add widgets to layout
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.slider)
        
        self.setLayout(self.layout)
    
    def update_label(self, value):
        """
        Updates the label text to display the current slider value.

        Parameters
        ----------
        value : int
            Current value of the slider.
        """
        self.label.setText(f"{value}")
    
    def setMinimum(self, value):
        """
        Sets the minimum value of the slider.

        Parameters
        ----------
        value : int
            Minimum value.
        """
        self.slider.setMinimum(value)
    
    def setMaximum(self, value):
        """
        Sets the maximum value of the slider.

        Parameters
        ----------
        value : int
            Maximum value.
        """
        self.slider.setMaximum(value)
    
    def setStep(self, value):
        """
        Sets the step size of the slider.

        Parameters
        ----------
        value : int
            Step size.
        """
        self.slider.setSingleStep(value)
    
    def setValue(self, value):
        """
        Sets the slider value.

        Parameters
        ----------
        value : int
            Desired slider value.
        """
        self.slider.setValue(value)
    
    def value(self):
        """
        Returns the current value of the slider.

        Returns
        -------
        int
            Current slider value.
        """
        return self.slider.value()


class DoubleSlider(QWidget):
    """
    A dual-slider widget with editable input fields for setting a value range.

    This widget features two horizontal QSliders for setting a minimum and maximum value,
    along with associated QLineEdits to allow manual text input. It emits combined signals
    when either slider changes, is moved, or released.

    Parameters
    ----------
    min_value : int, optional
        Minimum allowed slider value (default is 0).
    max_value : int, optional
        Maximum allowed slider value (default is 100).
    step : int, optional
        Step size between values (default is 1).
    initial_left : int, optional
        Initial value for the left (lower) slider (default is 25).
    initial_right : int, optional
        Initial value for the right (upper) slider (default is 75).
    parent : QWidget, optional
        Parent widget (default is None).

    Signals
    -------
    valueChanged(int, int)
        Emitted when either slider value changes.
    sliderMoved(int, int)
        Emitted while either slider is being dragged.
    sliderReleased(int, int)
        Emitted when either slider handle is released.
    sliderPressed(int, int)
        Emitted when either slider handle is pressed.
    """
    valueChanged = pyqtSignal(int, int)  # Signal emitting both slider values
    sliderMoved = pyqtSignal(int, int)  # Signal emitting both slider values
    sliderReleased = pyqtSignal(int, int)  # Signal emitting both slider values
    sliderPressed = pyqtSignal(int, int)  # Signal emitting both slider values

    def __init__(self, min_value=0, max_value=100, step=1, initial_left=25, initial_right=75, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout()
        
        # Create horizontal layout for sliders
        self.slider_layout = QHBoxLayout()
        
        # Create left slider
        self.left_slider = QSlider(Qt.Orientation.Horizontal)
        self.left_slider.setMinimum(min_value)
        self.left_slider.setMaximum(max_value)
        self.left_slider.setSingleStep(step)
        self.left_slider.setValue(initial_left)
        
        # Create right slider
        self.right_slider = QSlider(Qt.Orientation.Horizontal)
        self.right_slider.setMinimum(min_value)
        self.right_slider.setMaximum(max_value)
        self.right_slider.setSingleStep(step)
        self.right_slider.setValue(initial_right)
        
        # Connect slider changes
        self.left_slider.valueChanged.connect(self.update_values)
        self.right_slider.valueChanged.connect(self.update_values)
        self.left_slider.valueChanged.connect(self.valueChanged.emit)
        self.right_slider.valueChanged.connect(self.valueChanged.emit)

        self.left_slider.sliderMoved.connect(self.update_values)
        self.right_slider.sliderMoved.connect(self.update_values)
        self.left_slider.sliderMoved.connect(self.sliderMoved.emit)
        self.right_slider.sliderMoved.connect(self.sliderMoved.emit)

        self.left_slider.sliderReleased.connect(self.update_values)
        self.right_slider.sliderReleased.connect(self.update_values)
        self.left_slider.sliderReleased.connect(self.sliderReleased.emit)
        self.right_slider.sliderReleased.connect(self.sliderReleased.emit)

        self.left_slider.sliderPressed.connect(self.sliderPressed.emit)
        self.right_slider.sliderPressed.connect(self.sliderPressed.emit)
        
        self.slider_layout.addWidget(self.left_slider)
        self.slider_layout.addWidget(self.right_slider)
        
        # Create horizontal layout for line edits
        self.input_layout = QHBoxLayout()
        
        self.left_input = QLineEdit(str(initial_left))
        self.right_input = QLineEdit(str(initial_right))
        
        self.left_input.setFixedWidth(50)
        self.right_input.setFixedWidth(50)
        
        self.left_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.left_input.editingFinished.connect(self.update_sliders)
        self.right_input.editingFinished.connect(self.update_sliders)
        
        self.input_layout.addWidget(self.left_input)
        self.input_layout.addStretch()
        self.input_layout.addWidget(self.right_input)
        
        self.layout.addLayout(self.slider_layout)
        self.layout.addLayout(self.input_layout)
        
        self.setLayout(self.layout)
    
    def update_values(self):
        """
        Updates the line edits to reflect the slider values and emits the `valueChanged` signal.
        """
        left_value = self.left_slider.value()
        right_value = self.right_slider.value()
        
        self.left_input.setText(str(left_value))
        self.right_input.setText(str(right_value))
        
        self.valueChanged.emit(left_value, right_value)
    
    def update_sliders(self):
        """
        Updates slider values based on text input in the line edits. Invalid input is ignored.
        """
        try:
            left_value = int(self.left_input.text())
            right_value = int(self.right_input.text())
            self.left_slider.setValue(left_value)
            self.right_slider.setValue(right_value)
        except ValueError:
            pass
    
    def setMinimum(self, value):
        """
        Sets the minimum value for both sliders.

        Parameters
        ----------
        value : int
            Minimum value.
        """
        self.left_slider.setMinimum(value)
        self.right_slider.setMinimum(value)
    
    def setMaximum(self, value):
        """
        Sets the maximum value for both sliders.

        Parameters
        ----------
        value : int
            Maximum value.
        """
        self.left_slider.setMaximum(value)
        self.right_slider.setMaximum(value)
    
    def setStep(self, value):
        """
        Sets the step size for both sliders.

        Parameters
        ----------
        value : int
            Step size.
        """
        self.left_slider.setSingleStep(value)
        self.right_slider.setSingleStep(value)

    def setLeftValue(self, value):
        """
        Sets the value of the left slider.

        Parameters
        ----------
        value : int
            Desired value for the left slider.
        """
        self.left_slider.setValue(value)

    def setRightValue(self, value):
        """
        Sets the value of the right slider.

        Parameters
        ----------
        value : int
            Desired value for the right slider.
        """
        self.right_slider.setValue(value)

    def setValues(self, values):
        """
        Sets values for both sliders.

        Parameters
        ----------
        values : tuple of int
            Tuple containing (left_value, right_value).
        """
        self.left_slider.setValue(values[0])
        self.right_slider.setValue(values[1])
    
    def values(self):
        """
        Returns the current values of both sliders.

        Returns
        -------
        tuple of int
            (left_value, right_value)
        """
        return self.left_slider.value(), self.right_slider.value()
