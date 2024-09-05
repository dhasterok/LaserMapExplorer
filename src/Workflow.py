import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QPushButton
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import pyqtSlot, QObject, QUrl, QFile, QIODevice
from lame_helper import BASEDIR
from PyQt5.QtWebEngineWidgets import QWebEngineSettings
import os
# export QTWEBENGINE_REMOTE_DEBUGGING=9222  
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

class BlocklyBridge(QObject):
    def __init__(self, output_text_edit):
        super().__init__()
        self.output_text_edit = output_text_edit

    @pyqtSlot(result=list)
    def getSampleIds(self):
        # Assume self.parent.sample_ids is a list of sample IDs
        return self.parent.sample_ids
    
    @pyqtSlot(str)
    def runCode(self, code):
        # Display the received code in the QTextEdit
        self.output_text_edit.setPlainText(code)
        # This method will be called with the generated code as a string
        print("Received code:")
        print(code)

    # @pyqtSlot()
    # def updateSampleDropdown(self):
    #     # Notify JavaScript to update the dropdown after directory is loaded
    #     sample_ids = self.parent.sample_ids  # Assume this is a list of sample IDs
    #     self.parent.web_view.page().runJavaScript(f"window.blocklyBridge.updateSampleDropdown({sample_ids})")
        
class Workflow():
    def __init__(self,parent = None):
        self.parent = parent

        # Create the layout within parent.tabWorkflow
        self.layout = QVBoxLayout(parent.tabWorkflow)   

        # Create a QTextEdit to display the generated code
        self.output_text_edit = QTextEdit(self.parent)
        self.output_text_edit.setReadOnly(True)
        self.layout.addWidget(self.output_text_edit)
        
        
        # Create a button to execute the code
        self.run_button = QPushButton("Run Code", parent)
        self.run_button.clicked.connect(self.execute_code)
        self.layout.addWidget(self.run_button)

        # Create a web engine view
        self.web_view = QWebEngineView()

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
        self.web_view.setUrl(QUrl.fromLocalFile(BASEDIR + '/blockly/blockly.html'))

        # Add the web view to the layout
        self.layout.addWidget(self.web_view)
    
    def updateSampleDropdown(self):
        self.web_view.page().runJavaScript(f"updateSampleDropdown({self.parent.sample_ids})")
        
    def execute_code(self):
        # Get the code from the output_text_edit and execute it
        code = self.output_text_edit.toPlainText()
        try:
            exec(code)
        except Exception as e:
            print(f"Error executing code: {e}")
