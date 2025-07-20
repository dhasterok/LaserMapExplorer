from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.browser = QWebEngineView()
        # Convert file path string to QUrl and load it
        url = QUrl.fromLocalFile("/Users/shavinkalu/Adelaide Uni/Derrick/Work/LaserMapExplorer/blockly/index.html")
        self.browser.setUrl(url)
        self.setCentralWidget(self.browser)

app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())