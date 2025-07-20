import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QVBoxLayout, QLineEdit, QPushButton, QWidget
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QDesktopServices

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Search Help Widget")
        self.setGeometry(100, 100, 600, 400)

        self.create_menu()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout()
        self.central_widget.setLayout(layout)

        self.search_input = QLineEdit()
        layout.addWidget(self.search_input)

        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_help)
        layout.addWidget(search_button)

    def create_menu(self):
        help_menu = self.menuBar().addMenu("Help")

        search_action = QAction(QIcon(), "Search Help", self)
        search_action.triggered.connect(self.show_search_help)
        help_menu.addAction(search_action)

    def search_help(self):
        query = self.search_input.text()
        if query:
            url = QUrl("https://www.example.com/documentation?q={}".format(query))
            QDesktopServices.openUrl(url)

    def show_search_help(self):
        search_dialog = SearchHelpDialog()
        search_dialog.exec()

class SearchHelpDialog(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Search Help")
        self.setGeometry(200, 200, 400, 200)

        layout = QVBoxLayout()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setLayout(layout)

        self.search_input = QLineEdit()
        layout.addWidget(self.search_input)

        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_help)
        layout.addWidget(search_button)

    def search_help(self):
        query = self.search_input.text()
        if query:
            url = QUrl("https://www.example.com/documentation?q={}".format(query))
            QDesktopServices.openUrl(url)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
