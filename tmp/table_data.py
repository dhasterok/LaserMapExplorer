import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableView, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem

class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("User Role Example")
        self.setGeometry(100, 100, 600, 400)

        # Create a central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create a layout for the central widget
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Create a table view
        self.table_view = QTableView()
        layout.addWidget(self.table_view)

        # Create a model
        self.model = QStandardItemModel(4, 2)
        self.table_view.setModel(self.model)

        # Set data and retrieve it
        self.set_data()
        self.retrieve_data()

    def set_data(self):
        for row in range(self.model.rowCount()):
            for col in range(self.model.columnCount()):
                item = self.model.item(row, col)
                if not item:
                    item = QStandardItem()
                    self.model.setItem(row, col, item)
                item.setData("Data for row {} col {}".format(row, col), Qt.UserRole)

    def retrieve_data(self):
        for row in range(self.model.rowCount()):
            for col in range(self.model.columnCount()):
                item = self.model.item(row, col)
                data = item.data(Qt.UserRole)
                print("Data at row {} col {}: {}".format(row, col, data))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
