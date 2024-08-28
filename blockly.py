import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import pyqtSlot, QObject, QUrl
from lame_helper import BASEDIR
from PyQt5.QtWebEngineWidgets import QWebEngineSettings


class BlocklyBridge(QObject):
    def __init__(self, output_text_edit):
        super().__init__()
        self.output_text_edit = output_text_edit

    @pyqtSlot(str)
    def runCode(self, code):
        # Display the received code in the QTextEdit
        self.output_text_edit.setPlainText(code)

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

        # Create a QTextEdit to display the generated code
        self.output_text_edit = QTextEdit(self)
        self.output_text_edit.setReadOnly(True)
        self.layout.addWidget(self.output_text_edit)

        # Create a web engine view
        self.web_view = QWebEngineView()

        # Enable developer tools in the QWebEngineView
        self.web_view.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self.web_view.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        self.web_view.settings().setAttribute(QWebEngineSettings.ErrorPageEnabled, True)
        self.web_view.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)

        # Setup the WebChannel for communication
        self.channel = QWebChannel()
        self.bridge = BlocklyBridge(self.output_text_edit)
        self.channel.registerObject('blocklyBridge', self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        # Load the Blockly HTML page
        self.web_view.setUrl(QUrl.fromLocalFile(BASEDIR + '/blockly/blockly.html'))

        # Add the web view to the layout
        self.layout.addWidget(self.web_view)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ScratchLikeApp()
    window.show()
    sys.exit(app.exec_())