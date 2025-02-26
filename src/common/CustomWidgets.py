from PyQt6.QtWidgets import ( 
        QWidget, QLineEdit, QTableWidget, QComboBox, QPushButton, QCheckBox, QWidget, QTreeView,
        QMenu, QDockWidget, QHeaderView, QToolButton
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
    def __init__(self, parent=None, value=0.0, precision=4, threshold=1e4, toward=None, validator=QDoubleValidator()):
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
        super().__init__(parent)
        self._value = value
        self._precision = precision
        self._threshold = threshold
        self._toward = toward
        self.textChanged.connect(self._update_value_from_text)
        self.setValidator(validator)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        # ensure value is a float rather than integer
        self._value = new_value
        self._update_text_from_value()

    @property
    def precision(self):
        return self._precision 

    @precision.setter
    def precision(self, new_precision):
        self._precision = new_precision
        self._update_text_from_value
    
    @property
    def threshold(self):
        return self._threshold
    
    @threshold.setter
    def threshold(self, new_threshold):
        self._threshold = new_threshold
        self._update_text_from_value

    @property
    def toward(self):
        """int | float: sets whether to round towards 0, 1, or nearest integer"""
        return self._toward
    
    @toward.setter
    def toward(self, val):
        self._toward = val
        self._update_text_from_value

    def _update_text_from_value(self):
        if self._value is None:
            self.setText('')
        elif self._precision is None:
            self.setText(str(self._value))
        else:
            self.setText(fmt.dynamic_format(self._value, threshold=self._threshold, order=self._precision, toward=self._toward))
            #self.setText(f"{self._value:.{self._precision}f}")

    def _update_value_from_text(self):
        try:
            self._value = float(self.text())
        except ValueError:
            pass

class CustomTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def extract_widget_data(self, widget: QWidget):
        """Extracts relevant information from a widget for placing in a DataFrame

        _extended_summary_

        Parameters
        ----------
        widget : QWidget
            A widget stored in ``ImportTool.tableWidgetMetadata``

        Returns
        -------
        str or bool
            Returns key value of widget item to be added to a DataFrame
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
        """Converts the table data to a pandas DataFrame.

        Returns
        -------
        pd.DataFrame
            Data frame with data from the CustomTableWidget.
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
        """Extract data from a column of a CustomTableWidget into a list.

        Parameters
        ----------
        column : int, str
            Column index or column name.

        Returns
        -------
        list
            Data from ``column`` is placed into a list.

        Raises
        ------
        ValueError
            Column was not found.
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
    """Rotates the column header of a table by 90 degrees

    Parameters
    ----------
    parent : obj, optional
        Parent table object
    """    
    def __init__(self, parent=None):
        super(RotatedHeaderView, self).__init__(Qt.Orientation.Horizontal, parent)
        self.setMinimumSectionSize(20)

    def paintSection(self, painter, rect, logicalIndex ):
        painter.save()
        # translate the painter to the appropriate position
        painter.translate(rect.x(), rect.y() + rect.height())
        painter.rotate(-90)  # rotate by -90 degrees
        # and have parent code paint at this location
        newrect = QRect(0,0,rect.height(),rect.width())
        super(RotatedHeaderView, self).paintSection(painter, newrect, logicalIndex)
        painter.restore()

    def minimumSizeHint(self):
        size = super(RotatedHeaderView, self).minimumSizeHint()
        size.transpose()
        return size

    def sectionSizeFromContents(self, logicalIndex):
        size = super(RotatedHeaderView, self).sectionSizeFromContents(logicalIndex)
        size.transpose()
        return size
    
class StandardItem(QStandardItem):
    def __init__(self, txt='', font_size=10, set_bold=False, data=None):
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.treeModel = QStandardItemModel()
        self.root_node = self.treeModel.invisibleRootItem()
        self.setModel(self.treeModel)
    
    def branch_exists(self, parent_item, branch_name):
        """Check if a branch exists under the given parent."""
        for row in range(parent_item.rowCount()):
            item = parent_item.child(row)
            if item.text() == branch_name:
                return item  # Return the branch if found
        return None  # Branch not found
    
    def add_branch(self, parent_item, branch_name, data=None):
        """Add a branch to the tree under the given parent item."""
        branch_item = StandardItem(branch_name, 10, True, data)
        parent_item.appendRow(branch_item)
        return branch_item
    
    def add_leaf(self, branch_item, leaf_name, data=None):
        """Add a leaf to the tree under the given parent branch."""
        leaf_item = StandardItem(leaf_name, 10, False, data)
        branch_item.appendRow(leaf_item)
        return leaf_item

    def get_item_path(self, item):
        """Return the path of the given item as (tree, branch, leaf)."""
        path = []
        while item is not None:
            path.insert(0, item.text())
            item = item.parent()
        return path
    
    def get_leaf_data(self, parent_item, branch_name, leaf_name):
        """Get the data associated with a leaf."""
        return leaf_item.data()
    
    def find_leaf(self, branch_item, leaf_name):
        """Find a leaf by name under a branch."""
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
        """Handle double-click events in the tree view."""
        item = self.treeModel.itemFromIndex(index)
        item_path = self.get_item_path(item)
        leaf_data = self.get_leaf_data(item)
        print(f"Double-clicked on: {item_path}, Data: {leaf_data}")

    def clear_tree(self):
        try:
            self.treeModel.clear()
        except Exception as e:
            print(f"Error while clearing model: {e}")

class CustomActionMenu(QAction):
    """A QAction with an attached menu that displays on click.

    Parameters
    ----------
    icon : str
        Path to icon
    text : str
        Action text
    menu_items : list of tuple
        List of tuples where each tuple is (displayed text, callback function) or (displayed text, submenu items).
    parent : QObject, optional
        Parent widget.
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
            self.menu.exec_(QCursor.pos())

        # Connect the action to the show_menu function
        self.triggered.connect(show_menu)

    def _add_menu_items(self, menu, items):
        """Recursively add items and submenus to a menu."""
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

    def update_submenu(self, submenu_name, new_items):
        """Update a submenu with new items."""
        submenu = self.submenu_references.get(submenu_name)
        if submenu:
            submenu.clear()  # Remove all current actions
            self._add_menu_items(submenu, new_items)

class CustomComboBox(QComboBox):
    def __init__(self, update_callback=None, *args, **kwargs):
        """Initialize the CustomComboBox with an option update callback that executes at popup before the items are displayed.
        
        Parameters
        ----------
        update_callback : callback, optional
            Executes on showPopup(), by default None
        """
        super().__init__(*args, **kwargs)
        self.update_callback = update_callback

        setattr(self, "allItems", lambda: [self.itemText(i) for i in range(self.count())])

    def showPopup(self):
        """Update combobox items using callback before displaying items."""

        if self.update_callback:
            self.update_callback()
        super().showPopup()

class CustomDockWidget(QDockWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.show()

        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)

    def closeEvent(self, event):
        """Override the close event to hide the dock widget instead of closing it."""
        self.hide()
        event.ignore()  # Ignore the close event to prevent the widget from being removed.

class ToggleSwitch(QWidget):
    stateChanged = pyqtSignal(bool)  # Signal emitted when the state changes

    def __init__(self, parent=None, height=24, duration=100, fg_color=None, bg_left_color=None, bg_right_color=None):
        super().__init__(parent)
        self.height = height
        self.width = height * 2
        self.setFixedSize(self.width, self.height)
        self._checked = False
        self._thumb_pos = 2  # Initial position
        self.animation = QPropertyAnimation(self, b"thumb_pos")
        self.animation.setDuration(duration)  # Smooth animation

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
        self.animation.setStartValue(self._thumb_pos)
        self.animation.setEndValue(self.width - self.height + 2 if self._checked else 2)
        self.animation.start()

        self.stateChanged.emit(self._checked)  # Emit signal

    def setChecked(self, state):
        if not isinstance(state, bool):
            TypeError("ToggleSwitch requires state argument to be a bool")

        if state == self._checked:
            return

        self.toggle()


    def isChecked(self):
        """Return the current state of the toggle switch"""
        return self._checked

    def mousePressEvent(self, event):
        """Toggle switch on click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()

    def paintEvent(self, event):
        """Draw switch"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        bg_color = QColor(self.bg_right_color) if self._checked else QColor(self.bg_left_color)
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, self.width, self.height, self.height // 2, self.height // 2)

        # Draw sliding thumb
        thumb_size = self.height - 4
        painter.setBrush(QColor(self.fg_color))
        painter.drawEllipse(QRect(self._thumb_pos, 2, thumb_size, thumb_size))

    def get_thumb_pos(self):
        return self._thumb_pos

    def set_thumb_pos(self, pos):
        self._thumb_pos = pos
        self.update()  # Redraw switch

    thumb_pos = property(get_thumb_pos, set_thumb_pos)

class CustomCheckButton(QToolButton):
    """A button that changes icons when checked
    
    Properties
    ----------
    """
    def __init__(self, icon_unchecked: QIcon, icon_checked: QIcon, parent=None):
        super().__init__()

        # icons for checked and unchecked states
        self.icon_checked = icon_checked
        self.icon_unchecked = icon_checked

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