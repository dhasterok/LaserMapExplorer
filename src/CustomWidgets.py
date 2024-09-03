from PyQt5.QtWidgets import QLineEdit, QTableWidget, QComboBox, QCheckBox, QWidget, QAbstractItemView, QTableWidgetItem
import src.format as fmt
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