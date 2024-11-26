import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QPushButton, QSizePolicy
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import pyqtSlot, QObject, QUrl, QFile, QIODevice
from src.app.config import BASEDIR
from PyQt5.QtWebEngineWidgets import QWebEngineSettings
import os
import json
import numpy as np
os.environ["QTWEBENGINE_REMOTE_DEBUGGING"]="9222" #uncomment to debug in chrome  
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

class BlocklyBridge(QObject):
    def __init__(self,parent, output_text_edit):
        super().__init__()
        self.parent = parent  # Store reference to parent
        self.output_text_edit = output_text_edit
    
    @pyqtSlot(str)
    def runCode(self, code):
        # Display the received code in the QTextEdit
        self.output_text_edit.setPlainText(code)
        # This method will be called with the generated code as a string
        #print("Received code:")
        #print(code)


    @pyqtSlot(str)
    def executeCode(self, code):
        self.parent.execute_code(code)

    @pyqtSlot(str, result=str)
    def invokeSetStyleWidgets(self, plot_type):
        # Call the set_style_widgets function
        plot_type = plot_type.replace('_',' ')
        if plot_type in self.parent.parent.style.style_dict.keys():
            ### need to add parent.parent to access main code from this class 
            self.parent.parent.style.set_style_widgets(plot_type)
            style = self.parent.parent.style.style_dict[plot_type]
            print('invokeSetStyleWidgets')
            # Convert NumPy types to native Python types (if any)
            style_serializable = self.convert_numpy_types(style)
            
        else:
            style_serializable = {}
        # Return the style dictionary as a JSON string
        return json.dumps(style_serializable)
    
    @pyqtSlot(str, result=list)
    def getFieldList(self, field_type):
        print('get_field_list')
        return self.parent.parent.get_field_list(field_type)

    @pyqtSlot(str, result=list)
    def getFieldTypeList(self):
        print('get_field_type_list')
        return self.parent.parent.get_field_type_list()
    
    @pyqtSlot(result=str)
    def getBaseDir(self):
        return self.parent.parent.BASEDIR
    
    @pyqtSlot(result=list)
    def getAnalyteList(self):
        directory = os.path.join(self.parent.parent.BASEDIR, 'resources/analytes list')
        # List all .txt files in the directory
        print('analyte_list')
        txt_files = [str(f).replace('.txt','') for f in os.listdir(directory) if f.endswith('.txt')]
        return txt_files

    @pyqtSlot()
    def refreshAnalyteDropdown(self):
        """Fetches the list of analytes and sends it to JavaScript to refresh the dropdown."""
        analyte_list = self.getAnalyteList()
        analyte_list_js_array = json.dumps(analyte_list)  # Convert to JSON for JavaScript
        self.parent.web_view.page().runJavaScript(f"updateAnalyteDropdown({analyte_list_js_array})")

    def convert_numpy_types(self, obj):
        """ Recursively convert NumPy types to Python native types. """
        if isinstance(obj, dict):
            return {key: self.convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_numpy_types(element) for element in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
        
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
        self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Setup the WebChannel for communication
        self.channel = QWebChannel()
        self.bridge = BlocklyBridge(self, self.output_text_edit)
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

        # Connect resize event
        parent.resizeEvent = self.handleResizeEvent

    def handleResizeEvent(self, event):
        self.web_view.page().runJavaScript("resizeBlocklyWorkspace()")
        event.accept()
    
    def store_sample_ids(self):
        """
        Sends sample_ids to JavaScript to update the sample_ids list and refresh dropdowns.
        """
        # Convert the sample_ids list to a format that JavaScript can use (a JSON array)
        sample_ids_js_array = str(self.parent.sample_ids)
        self.web_view.page().runJavaScript(f"updateSampleDropdown({sample_ids_js_array})")

        
    def execute_code(self,code=None):
        if not code:
            # Get the code from the output_text_edit and execute it
            code = self.output_text_edit.toPlainText()
        # try:
        #     print("Execute code:")
        #     print(code)
        #     exec(code)
        # except Exception as e:
        #     print(f"Error executing code: {e}")

        print(code)
        exec(code)