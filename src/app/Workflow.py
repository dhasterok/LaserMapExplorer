import sys, os, json
from PyQt6.QtWidgets import ( 
    QMainWindow, QVBoxLayout, QWidget, QTextEdit, QSizePolicy, QDockWidget, QToolBar 
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import pyqtSlot, Qt, QObject, QUrl, QFile, QIODevice, QSize
from src.app.config import BASEDIR
from src.common.CustomWidgets import CustomDockWidget

import numpy as np
from src.app.Modules import Main
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
        if plot_type in self.parent.main.plot_style.style_dict.keys():
            self.parent.main.plot_style.set_style_dictionary(plot_type)
            style = self.parent.main.plot_style.style_dict[plot_type]
            print('invokeSetStyleWidgets')
            # Convert NumPy types to native Python types (if any)
            style_serializable = self.convert_numpy_types(style)
            
        else:
            style_serializable = {}
        # Return the style dictionary as a JSON string
        return json.dumps(style_serializable)
    
    @pyqtSlot(str,str, result=float)
    def getHistogramRange(self, fieldType, field):
        return self.parent.main.histogram_get_range(fieldType, field)
    
    @pyqtSlot(str, result=list)
    def getFieldList(self, field_type):
        print('get_field_list')
        return self.parent.main.get_field_list(field_type)
    
    @pyqtSlot(result=str)
    def getBaseDir(self):
        return BASEDIR
    
    @pyqtSlot(result=list)
    def getRefValueList(self):
        
        return self.parent.main.ref_list.tolist()

    @pyqtSlot(str,result=list)
    def getSavedLists(self,type):
        """
        Exposed method to JavaScript to get the list of saved analyte lists.
        """
        saved_lists = self.parent.get_saved_lists(type)
        return saved_lists
    



    @pyqtSlot(result=list)
    def getCurrentDimensions(self):
        """
        Exposed method to JavaScript to get the current dx and dy dimensions.
        """
        dx =0
        dy = 0
        if self.parent.main.sample_id:
            dx = self.parent.main.data[self.parent.main.sample_id].dx
            dy = self.parent.main.data[self.parent.main.sample_id].dy
        return [dx, dy]

    


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
        
class Workflow(CustomDockWidget):
    """Creates the workflow method design dock.

    Use this tool to create workflows using a customized version of Google's Blockly.
    This tool allows the user to create a workflow by dragging and dropping code blocks 
    onto the workspace.  The user can run each of the blocks singlely with a
    double-click, or the entire block by pressing the run button.  Blocks can be 
    recorded (to be completed) from LaME and then modified here, or be created from 
    scratch.

    Parameters
    ----------
    parent : QMainWindow, optional
        MainWindow UI, by default None

    Raises
    ------
    TypeError
        parent must be an instance of QMainWindow.
    """        
    def __init__(self,parent = None):
        if not isinstance(parent, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        super().__init__(parent)
        self.parent = parent

        container = QWidget()

        # Create the layout within parent.tabWorkflow
        dock_layout = QVBoxLayout()   

        # Create a QTextEdit to display the generated code
        self.output_text_edit = QTextEdit(self.parent)
        self.output_text_edit.setReadOnly(True)
        dock_layout.addWidget(self.output_text_edit)
        
        toolbar = QToolBar("Notes Toolbar", self)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out

        # Run button
        self.run_action = QAction()
        run_icon = QIcon(":resources/icons/icon-run-64.svg")
        if not run_icon.isNull():
            self.run_action.setIcon(run_icon)
        else:
            self.run_action.setText("Run")
        self.run_action.setToolTip("Execute workflow")

        # Export button
        self.save_action = QAction()
        save_icon = QIcon(":resources/icons/icon-save-file-64.svg")
        if not save_icon.isNull():
            self.save_action.setIcon(save_icon)
        else:
            self.save_action.setText("Save")
        self.save_action.setToolTip("Save log to file")
        self.save_action.setEnabled(False)

        # Clear button
        self.clear_action = QAction()
        clear_icon = QIcon(":resources/icons/icon-delete-64.svg")
        if not clear_icon.isNull():
            self.clear_action.setIcon(clear_icon)
        else:
            self.clear_action.setText("Clear")
        self.clear_action.setToolTip("Clear log")
        self.clear_action.setEnabled(False)

        toolbar.addAction(self.run_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.clear_action)

        dock_layout.addWidget(toolbar)

        # Button signals
        self.run_action.triggered.connect(self.execute_code)
        #self.save_action.triggered.connect(self.save_workflow)
        #self.clear_action.triggered.connect(self.clear_workflow)

        # Create a web engine view
        self.web_view = QWebEngineView()
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Setup the WebChannel for communication
        self.channel = QWebChannel()
        self.bridge = BlocklyBridge(self, self.output_text_edit)
        self.channel.registerObject('blocklyBridge', self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        # Load the qwebchannel.js file and inject it into the page
        api_file = QFile(":/qtwebchannel/qwebchannel.js")
        if not api_file.open(QIODevice.OpenModeFlag.ReadOnly):
            print("Couldn't load Qt's QWebChannel API!")
        api_script = str(api_file.readAll(), 'utf-8')
        api_file.close()
        self.web_view.page().runJavaScript(api_script)
        #Load the Blockly HTML page
        self.web_view.setUrl(QUrl.fromLocalFile(BASEDIR + '/blockly/index.html'))
        # Add the web view to the layout
        dock_layout.addWidget(self.web_view)

        # Connect resize event
        parent.resizeEvent = self.handleResizeEvent

        # Set layout to the container
        container.setLayout(dock_layout)
        self.setWidget(container)

        self.setFloating(True)
        self.setWindowTitle("Workflow Method Design")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)

        parent.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self)

        # Initiate Main class from Modules.py
        # self.main will hold instance of Main code without any UI interactions
        self.main = Main()

    def handleResizeEvent(self, event):
        self.web_view.page().runJavaScript("resizeBlocklyWorkspace()")
        event.accept()

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
    
    def store_sample_ids(self):
        """
        Sends sample_ids to JavaScript to update the sample_ids list and refresh dropdowns.
        """
        # Convert the sample_ids list to a format that JavaScript can use (a JSON array)
        sample_ids_js_array = str(self.main.sample_ids)
        self.web_view.page().runJavaScript(f"updateSampleDropdown({sample_ids_js_array})")

    def update_field_type_list(self, field_type_list):
        # Convert the field type list to JSON
        field_type_list_json = json.dumps(field_type_list)
        # Send the field type list to JavaScript
        self.web_view.page().runJavaScript(f"updateFieldTypeList({field_type_list_json})")
    
    def get_saved_lists(self,type):
        """
        Retrieves the names of saved analyte lists from the resources/analytes list directory.

        Returns
        -------
        list
            List of saved analyte list names.
        """
        path =''
        if type =='Analyte':
            path = 'resources/analytes_list'
        elif type =='field':
             path = 'resources/fields_list'
        directory = os.path.join(self.parent.BASEDIR, path)
        list_names = [str(f).replace('.txt', '') for f in os.listdir(directory) if f.endswith('.txt')]
        return list_names

    def refresh_saved_lists_dropdown(self, type):
            """
            Calls the JavaScript function to refresh the analyteSavedListsDropdown in Blockly.
            """
            self.web_view.page().runJavaScript("refreshListsDropdown({type});")
