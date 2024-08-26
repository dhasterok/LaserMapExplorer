import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QUrl
from PyQt5.QtCore import pyqtSlot, QObject
from lame_helper import BASEDIR, ICONPATH, SSPATH, load_stylesheet
class BlocklyBridge(QObject):
    @pyqtSlot(str)
    def runCode(self, code):
        print("Code received from Blockly:")
        print(code)
        # Here, you could run the code using exec() or another method

class ScratchLikeApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Scratch-like Environment")
        self.setGeometry(100, 100, 1200, 800)

        # Create a central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Create a layout
        self.layout = QVBoxLayout(self.central_widget)

        # Create a web engine view
        self.web_view = QWebEngineView()

        # Setup the WebChannel for communication
        self.channel = QWebChannel()
        self.bridge = BlocklyBridge()
        self.channel.registerObject('blocklyBridge', self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        # Load the Blockly HTML page
        self.web_view.setUrl(QUrl.fromLocalFile(BASEDIR + 'blockly/blockly.html'))

        # Add the web view to the layout
        self.layout.addWidget(self.web_view)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ScratchLikeApp()
    window.show()
    sys.exit(app.exec_())