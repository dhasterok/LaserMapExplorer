from PyQt5.QtWidgets import QLineEdit, QTableWidget, QComboBox, QPushButton, QCheckBox, QWidget, QTreeView
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QFont
import src.common.format as fmt
import pandas as pd

class CustomLineEdit(QLineEdit):
    def __init__(self, parent=None, value=0.0, precision=4, threshold=1e4, toward=None):
        super().__init__(parent)
        self._value = value
        self._precision = precision
        self._threshold = threshold
        self._toward = toward
        self.textChanged.connect(self._update_value_from_text)

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
        return self._toward
    
    @toward.setter
    def toward(self, new_toward):
        self._toward = new_toward
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