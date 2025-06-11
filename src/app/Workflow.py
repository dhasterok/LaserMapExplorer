import sys, os, json
from PyQt6.QtWidgets import ( 
    QMainWindow, QVBoxLayout, QWidget, QTextEdit, QSizePolicy, QDockWidget, QToolBar , QStatusBar
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import QIcon, QAction, QFont
from PyQt6.QtCore import pyqtSlot, Qt, QObject, QUrl, QFile, QIODevice, QSize
from src.app.config import BASEDIR
from src.common.CustomWidgets import CustomDockWidget

import numpy as np
from src.app.BlocklyModules import LameBlockly
os.environ["QTWEBENGINE_REMOTE_DEBUGGING"]="9222" #uncomment to debug in chrome  
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

class BlocklyBridge(QObject):
    def __init__(self,main_window,blockly_webpage, output_text_edit):
        super().__init__()
        
        self.output_text_edit = output_text_edit # This will be used to display the generated code
        # Initiate the LameBlockly instance
        # This is a instance of Lame, which is customised to be run with Blockly
        self.lame_blockly = LameBlockly(main_window,blockly_webpage)
        

    @pyqtSlot(str)
    def runCode(self, code):
        # Display the received code in the QTextEdit
        self.output_text_edit.setPlainText(code)
        # This method will be called with the generated code as a string
        #print("Received code:")
        #print(code)


    @pyqtSlot(str)
    def executeCode(self, code):
        self.lame_blockly.execute_code(self.output_text_edit, code)

    @pyqtSlot(str, result=str)
    def invokeSetStyleWidgets(self, plot_type):
        # Call the set_style_widgets function
        plot_type = plot_type.replace('_',' ')
        if plot_type in self.lame_blockly.plot_style.style_dict.keys():
            self.lame_blockly.plot_style.set_style_dictionary(plot_type)
            style = self.lame_blockly.plot_style.style_dict[plot_type]
            print('invokeSetStyleWidgets')
            # Convert NumPy types to native Python types (if any)
            style_serializable = self.convert_numpy_types(style)
            
        else:
            style_serializable = {}
        # Return the style dictionary as a JSON string
        return json.dumps(style_serializable)
    
    @pyqtSlot(str,str, result=float)
    def getHistogramRange(self, fieldType, field):
        return self.lame_blockly.histogram_get_range(fieldType, field)
    
    @pyqtSlot(str, result=list)
    def getFieldList(self, field_type):
        print('get_field_list')
        return self.lame_blockly.get_field_list(field_type)
    
    @pyqtSlot(result=str)
    def getBaseDir(self):
        return BASEDIR
    
    @pyqtSlot(result=list)
    def getRefValueList(self):
        
        return self.lame_blockly.ref_list.tolist()

    @pyqtSlot(str,result=list)
    def getSavedLists(self,type):
        """
        Exposed method to JavaScript to get the list of saved analyte lists.
        """
        saved_lists = self.get_saved_lists(type)
        return saved_lists
    

    @pyqtSlot(result=list)
    def getCurrentDimensions(self):
        """
        Exposed method to JavaScript to get the current dx and dy dimensions.
        """
        dx =0
        dy = 0
        if self.lame_blockly.app_data.sample_id:
            dx = self.lame_blockly.data[self.lame_blockly.app_data.sample_id].dx
            dy = self.lame_blockly.data[self.lame_blockly.app_data.sample_id].dy
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
    main_window : QMainWindow, optional
        MainWindow UI, by default None

    Raises
    ------
    TypeError
        main_window must be an instance of QMainWindow.
    """        
    def __init__(self,main_window = None):
        if not isinstance(main_window, QMainWindow):
            raise TypeError("main_window must be an instance of QMainWindow.")

        super().__init__(main_window)
        
        container = QWidget()

        # Create the layout within main_window.tabWorkflow
        dock_layout = QVBoxLayout()   

        # Create a QTextEdit to display the generated code
        self.output_text_edit = QTextEdit(main_window)
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


        #self.save_action.triggered.connect(self.save_workflow)
        #self.clear_action.triggered.connect(self.clear_workflow)

        # Create a web engine view
        self.web_view = QWebEngineView()
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Setup the WebChannel for communication
        self.channel = QWebChannel()

        # Create an instance of the BlocklyBridge and register it with the channel

        self.bridge = BlocklyBridge(main_window ,self.web_view.page(), self.output_text_edit)
        self.channel.registerObject('blocklyBridge', self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        # Button signals
        self.run_action.triggered.connect(lambda: self.bridge.lame_blockly.execute_code(self.output_text_edit))

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
        main_window.resizeEvent = self.handleResizeEvent

        # Set layout to the container
        container.setLayout(dock_layout)
        self.setWidget(container)

        self.setFloating(True)
        self.setWindowTitle("Workflow Method Design")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)

        main_window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self)

        

    def handleResizeEvent(self, event):
        self.web_view.page().runJavaScript("resizeBlocklyWorkspace()")
        event.accept()


    

