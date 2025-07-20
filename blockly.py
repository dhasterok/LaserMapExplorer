import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import pyqtSlot, QObject, QUrl, QFile, QIODevice
from src.app.config import BASEDIR
from PyQt5.QtWebEngineWidgets import QWebEngineSettings
import os
#export QTWEBENGINE_REMOTE_DEBUGGING=9222  
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

class BlocklyBridge(QObject):
    def __init__(self, output_text_edit):
        super().__init__()
        self.output_text_edit = output_text_edit

    @pyqtSlot(str)
    def runCode(self, code):
        # Display the received code in the QTextEdit
        self.output_text_edit.setPlainText(code)
        # This method will be called with the generated code as a string
        print("Received code:")
        print(code)
        
class Workflow(QMainWindow):
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
        # Enable developer tools
        # self.web_view.settings().setAttribute(QWebEngineSettings.DeveloperExtrasEnabled, True)
        # Enable developer tools in the QWebEngineView
        # self.web_view.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        # self.web_view.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        # self.web_view.settings().setAttribute(QWebEngineSettings.ErrorPageEnabled, True)
        # self.web_view.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)

        # Setup the WebChannel for communication
        self.channel = QWebChannel()
        self.bridge = BlocklyBridge(self.output_text_edit)
        self.channel.registerObject('blocklyBridge', self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        # Load the qwebchannel.js file and inject it into the page
        api_file = QFile(":/qtwebchannel/qwebchannel.js")
        if not api_file.open(QIODevice.ReadOnly):
            print("Couldn't load Qt's QWebChannel API!")
        api_script = str(api_file.readAll(), 'utf-8')
        api_file.close()
        self.web_view.page().runJavaScript(api_script)
        #Load the Blockly HTML page
        self.web_view.setUrl(QUrl.fromLocalFile(BASEDIR + '/blockly/index.html'))

        # Add the web view to the layout
        self.layout.addWidget(self.web_view)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Workflow()
    window.show()
    sys.exit(app.exec())