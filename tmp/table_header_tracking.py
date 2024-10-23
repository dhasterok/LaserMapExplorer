from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QApplication, QWidget, QVBoxLayout
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class MyApp(QWidget):
    def __init__(self):
        super().__init__()

        # Set up the layout and table
        layout = QVBoxLayout(self)
        self.tableWidgetAnalytes = QTableWidget(self)
        layout.addWidget(self.tableWidgetAnalytes)

        self.tableWidgetAnalytes.setRowCount(5)
        self.tableWidgetAnalytes.setColumnCount(5)

        analytes = ['Analyte 1', 'Analyte 2', 'Analyte 3', 'Analyte 4', 'Analyte 5']
        self.tableWidgetAnalytes.setHorizontalHeaderLabels(analytes)
        self.tableWidgetAnalytes.setVerticalHeaderLabels(analytes)

        # Add items to the table
        for i in range(5):
            for j in range(5):
                item = QTableWidgetItem(f"{i},{j}")
                self.tableWidgetAnalytes.setItem(i, j, item)

        # Set the headers to resize based on contents
        self.tableWidgetAnalytes.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidgetAnalytes.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Set initial font for headers to Normal weight
        header_font = self.tableWidgetAnalytes.horizontalHeader().font()
        header_font.setWeight(QFont.Normal)
        self.tableWidgetAnalytes.horizontalHeader().setFont(header_font)
        self.tableWidgetAnalytes.verticalHeader().setFont(header_font)

        # Variables to track previous row/column for font reset
        self.prev_row = None
        self.prev_col = None

        # Enable mouse tracking to capture hover events
        self.tableWidgetAnalytes.setMouseTracking(True)
        self.tableWidgetAnalytes.viewport().setMouseTracking(True)

        # Connect mouse move event to custom handler
        self.tableWidgetAnalytes.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.tableWidgetAnalytes.viewport() and event.type() == event.MouseMove:
            # Get the row and column of the cell under the mouse
            index = self.tableWidgetAnalytes.indexAt(event.pos())
            row = index.row()
            col = index.column()

            # Reset the previous row and column to normal font if they exist
            if self.prev_row is not None:
                self._set_row_font(self.prev_row, QFont.Normal)
            if self.prev_col is not None:
                self._set_col_font(self.prev_col, QFont.Normal)

            # Apply bold font to the current row and column headers
            if row >= 0:
                self._set_row_font(row, QFont.Bold)
                self.prev_row = row
            if col >= 0:
                self._set_col_font(col, QFont.Bold)
                self.prev_col = col

        # Handle resetting when the mouse leaves the widget
        if obj == self.tableWidgetAnalytes.viewport() and event.type() == event.Leave:
            # Reset any bold headers when the mouse leaves the table
            if self.prev_row is not None:
                self._set_row_font(self.prev_row, QFont.Normal)
            if self.prev_col is not None:
                self._set_col_font(self.prev_col, QFont.Normal)
            self.prev_row = None
            self.prev_col = None

        return super().eventFilter(obj, event)

    def _set_row_font(self, row, weight):
        """Set the font weight for the vertical header row."""
        if row is not None and self.tableWidgetAnalytes.verticalHeaderItem(row):
            font = self.tableWidgetAnalytes.verticalHeaderItem(row).font()
            font.setWeight(weight)
            self.tableWidgetAnalytes.verticalHeaderItem(row).setFont(font)

    def _set_col_font(self, col, weight):
        """Set the font weight for the horizontal header column."""
        if col is not None and self.tableWidgetAnalytes.horizontalHeaderItem(col):
            font = self.tableWidgetAnalytes.horizontalHeaderItem(col).font()
            font.setWeight(weight)
            self.tableWidgetAnalytes.horizontalHeaderItem(col).setFont(font)


if __name__ == "__main__":
    app = QApplication([])
    window = MyApp()
    window.show()
    app.exec_()
