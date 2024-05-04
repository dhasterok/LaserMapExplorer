import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView
from PyQt5.QtCore import Qt

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drag and Drop Rows in QTableWidget")
        self.setGeometry(100, 100, 600, 400)

        # Create a central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create a layout for the central widget
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Create a QTableWidget
        self.table_widget = QTableWidget(4, 2)
        layout.addWidget(self.table_widget)

        # Populate the table with some data
        self.populate_table()

        # Enable custom drag and drop
        self.table_widget.setDragEnabled(True)
        self.table_widget.viewport().setAcceptDrops(True)
        self.table_widget.setDropIndicatorShown(True)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)

    def populate_table(self):
        for row in range(self.table_widget.rowCount()):
            for col in range(self.table_widget.columnCount()):
                item = QTableWidgetItem(f"Row {row}, Col {col}")
                self.table_widget.setItem(row, col, item)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def mousePressEvent(self, event):
        print('mousePressEvent')
        if event.buttons() == Qt.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event):
        print('mouseMoveEvent')
        if not event.buttons() & Qt.LeftButton:
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
        item = self.table_widget.itemAt(self.drag_start_position)
        if item is None:
            return
        drag = QDrag(self)
        mime_data = self.table_widget.mimeData(self.table_widget.selectedIndexes())
        drag.setMimeData(mime_data)
        drag.exec_(Qt.MoveAction)

    def dropEvent(self, event):
        print('dropEvent')
        if event.source() == self.table_widget:
            super().dropEvent(event)
        else:
            dropped_index = self.table_widget.indexAt(event.pos())
            if not dropped_index.isValid():
                return
            selected_rows = sorted(set(index.row() for index in self.table_widget.selectedIndexes()))
            if dropped_index.row() > selected_rows[-1]:
                dropped_index = self.table_widget.indexFromItem(self.table_widget.item(dropped_index.row() - len(selected_rows), 0))
            for row in selected_rows:
                self.move_row(row, dropped_index.row())
                if row < dropped_index.row():
                    dropped_index = self.table_widget.indexFromItem(self.table_widget.item(dropped_index.row() + 1, 0))

    def move_row(self, source_row, target_row):
        print('move_row')
        items = []
        for column in range(self.table_widget.columnCount()):
            items.append(self.table_widget.takeItem(source_row, column))
        for column in range(self.table_widget.columnCount()):
            self.table_widget.setItem(target_row, column, items[column])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
