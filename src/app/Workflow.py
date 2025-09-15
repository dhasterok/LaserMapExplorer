import sys, os, json
from PyQt6.QtWidgets import ( 
    QMainWindow, QVBoxLayout, QWidget, QTextEdit, QSizePolicy, QDockWidget, QToolBar , QStatusBar, QLabel, QFileDialog, QPlainTextEdit
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import QIcon, QAction, QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextFormat, QPainter
from PyQt6.QtCore import pyqtSlot, Qt, QObject, QUrl, QFile, QIODevice, QSize, QRegularExpression, QRect
from src.app.config import BASEDIR
from src.common.CustomWidgets import CustomDockWidget
import numpy as np
from src.app.BlocklyModules import LameBlockly
os.environ["QTWEBENGINE_REMOTE_DEBUGGING"]="9222" #uncomment to debug in chrome  
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

class BlocklyBridge(QObject):
    """Bridge object exposed to JavaScript via QWebChannel.

    Provides slots to receive generated code, execute code, query lists/values,
    and update style/app parameters from the Blockly front-end.

    Parameters
    ----------
    parent : QObject
        The owning Python object that contains UI widgets (e.g., CodeEditor).
    """
    def __init__(self,parent):
        super().__init__()

        self.output_text_edit = parent.output_text_edit # This will be used to display the generated code
        
        # Initiate the LameBlockly instance
        # This is a instance of Lame, which is customised to be run with Blockly
        self.lame_blockly = LameBlockly(parent)
        

    @pyqtSlot(str)
    def runCode(self, code):
        """Display the generated code in the output editor.

        Parameters
        ----------
        code : str
            Python source code emitted by Blockly.
        """
        # Display the received code in the QTextEdit
        self.output_text_edit.set_code(code)
        # This method will be called with the generated code as a string
        #print("Received code:")
        #print(code)


    @pyqtSlot(str)
    def executeCode(self, code):
        """Execute the provided code within the LameBlockly context.

        Parameters
        ----------
        code : str
            Python source code to execute.
        """
        self.lame_blockly.execute_code(self.output_text_edit, code)

    @pyqtSlot(str, result=str)
    def invokeSetStyleWidgets(self, arg_json):
        """Update style/app settings from JSON and return the active style.

        Parameters
        ----------
        arg_json : str
            JSON string with keys like plot_type, c_field, c_field_type, etc.

        Returns
        -------
        str
            JSON string of the current style dict (NumPy types converted).
        """
        """arg_json: JSON string with keys like plot_type, c_field, c_field_type, etc."""
        if arg_json !='':
            args = json.loads(arg_json)
            
            # Update app_data and plot_style based on dictionary
            for key, value in args.items():
                # You can expand this to more robust attribute validation if needed
                if hasattr(self.lame_blockly.app_data, key):
                    setattr(self.lame_blockly.app_data, key, value)
                elif hasattr(self.lame_blockly.style_data, key):
                    setattr(self.lame_blockly.style_data, key, value)
            plot_type = args.get('plot_type', 'field map').replace('_',' ')
            if plot_type in self.lame_blockly.style_data.style_dict.keys():
                self.lame_blockly.style_data.plot_type = plot_type
                self.lame_blockly.style_data.set_style_attributes(
                    data=self.lame_blockly.data[self.lame_blockly.app_data.sample_id],
                    app_data=self.lame_blockly.app_data,
                    plot_type=plot_type
                )
                style = self.lame_blockly.style_data.style_dict[plot_type]
                style_serializable = self.convert_numpy_types(style)
            else:
                style_serializable = {}
        else:
            style_serializable = {}
        return json.dumps(style_serializable)
        
    @pyqtSlot(str,str,str,int, result=float)
    def getHistogramRange(self, fieldType, field, hist_type, n_bins):
        """Compute or retrieve a suggested histogram range.

        Parameters
        ----------
        fieldType : str
            Type of field (e.g., 'Analyte', 'Attribute').
        field : str
            Field/column name.
        hist_type : str
            Histogram type identifier.
        n_bins : int
            Number of histogram bins.

        Returns
        -------
        float
            Suggested histogram range scalar (implementation-specific).
        """
        return self.lame_blockly.histogram_get_range(fieldType, field, hist_type, n_bins)
    
    @pyqtSlot(str, result=list)
    def getFieldList(self, field_type):
        """Return a list of fields of the given type.

        Parameters
        ----------
        field_type : str
            Field type to query.

        Returns
        -------
        list
            List of field names.
        """
        return self.lame_blockly.app_data.get_field_list(field_type)
    
    @pyqtSlot(str,str, result=list)
    def getFieldTypeList(self, ax, plot_type):
        """Return available field types for an axis and plot type.

        Parameters
        ----------
        ax : str
            Axis identifier (e.g., 'x' or 'y').
        plot_type : str
            Plot type key.

        Returns
        -------
        list
            Supported field types for the given axis/plot combination.
        """
        self.lame_blockly.style_data.plot_type = plot_type
        return self.lame_blockly.app_data.get_field_type_list(ax, self.lame_blockly.style_data)

    @pyqtSlot(result=str)
    def getBaseDir(self):
        """Return the application base directory.

        Returns
        -------
        str
            Base directory path.
        """
        return BASEDIR
    
    @pyqtSlot(result=list)
    def getRefValueList(self):
        """Return the list of reference model names.

        Returns
        -------
        list
            Reference names as a list of strings.
        """
        
        return self.lame_blockly.app_data.ref_list.tolist()
    
    @pyqtSlot(result=list)
    def getNDimAnalyteSets(self):
        """Return available N-D analyte set keys.

        Returns
        -------
        list
            Keys such as ['majors', 'full trace', 'REE', 'metals'].
        """
        # Return e.g. ["majors", "full trace", "REE", "metals"]
        return list(self.lame_blockly.app_data.ndim_list_dict.keys())

    @pyqtSlot(result=list)
    def getNDimQuantiles(self):
        """Return available quantile presets as label/value objects.

        Returns
        -------
        list of dict
            Each item has {'label': str, 'value': int}.
        """
        # Return list of {label, value}, kept simple
        q = self.lame_blockly.app_data.ndim_quantiles
        return [{"label": f"{q[k]}", "value": int(k)} for k in sorted(q.keys())]


    @pyqtSlot(str,result=list)
    def getSavedLists(self,type):
        """Get saved analyte lists by type for use in Blockly.

        Parameters
        ----------
        type : str
            Saved list category.

        Returns
        -------
        list
            Saved list names.
        """
        """
        Exposed method to JavaScript to get the list of saved analyte lists.
        """
        saved_lists = self.lame_blockly.get_saved_lists(type)
        return saved_lists
    
    @pyqtSlot(result=str)
    def getSelectedDir(self) -> str:
        """Return the last-selected directory used for saving outputs.

        Returns
        -------
        str
            Absolute or user-resolved path to the save directory. Empty string if unavailable.
        """
        """
        Return the last-selected directory used for saving outputs.

        Returns
        -------
        str
            Absolute or user-resolved path to the save directory. Empty string if unavailable.
        """
        try:
            return str(self.lame_blockly.app_data.selected_directory)
        except Exception:
            return ""
        
    @pyqtSlot(str, result=str)
    def selectDirectory(self, start_dir: str = "") -> str:
        """Open a native directory chooser and return the selected path.

        Parameters
        ----------
        start_dir : str, optional
            Initial directory to open, by default "".

        Returns
        -------
        str
            Absolute selected directory or empty string if cancelled.
        """
        """
        Open a native directory chooser starting at start_dir (or app selected_dir),
        and return the selected path, or '' if the user cancels.
        """
        try:
            base = start_dir or str(getattr(self.lame_blockly.app_data, 'selected_dir', "")) or ""
        except Exception:
            base = ""
        path = QFileDialog.getExistingDirectory(
            parent=None,
            caption="Select Save Directory",
            directory=base
        )
        return path or ""

    @pyqtSlot(result=list)
    def getCurrentDimensions(self):
        """Return current data grid spacing (dx, dy).

        Returns
        -------
        list
            [dx, dy] spacing values, or [0, 0] if unavailable.
        """
        """
        Exposed method to JavaScript to get the current dx and dy dimensions.
        """
        dx =0
        dy = 0
        if self.lame_blockly.app_data.sample_id:
            dx = self.lame_blockly.data[self.lame_blockly.app_data.sample_id].dx
            dy = self.lame_blockly.data[self.lame_blockly.app_data.sample_id].dy
        return [dx, dy]
    
    # -------- Clustering defaults / helpers --------

    @pyqtSlot(result=list)
    def getClusterMethodList(self):
        """
        Return available clustering methods from AppData.

        Returns
        -------
        list
            Method names as stored in AppData.cluster_dict (e.g., ['k-means', 'fuzzy c-means']).
        """
        app = self.lame_blockly.app_data
        try:
            return list(app.cluster_dict.keys())
        except Exception:
            return []


    @pyqtSlot(str, result=str)
    def getClusterDefaults(self, method):
        """
        Return default clustering parameters for a given method as JSON.

        The JSON object includes:
        - method : str
        - max_clusters : int
        - n_clusters : int
        - seed : int or null
        - distance : str or null
        - exponent : float or null
        - selected_clusters : list[int]
        - precondition : bool
        - n_basis : int

        Parameters
        ----------
        method : str
            Clustering method key as in AppData.cluster_dict.

        Returns
        -------
        str
            JSON string of the defaults for the requested method.
        """
        app = self.lame_blockly.app_data
        d = app.cluster_dict.get(method, {})

        # robust fallbacks for names used elsewhere
        num_clusters_fallback = getattr(app, 'num_clusters', None)
        if num_clusters_fallback is None:
            num_clusters_fallback = getattr(app, '_num_clusters', 0)

        seed_fallback = d.get('seed', getattr(app, 'cluster_seed', None))
        distance_fallback = d.get('distance', getattr(app, 'cluster_distance', None))
        exponent_fallback = d.get('exponent', getattr(app, 'cluster_exponent', None))

        out = {
            'method': method,
            'max_clusters': int(getattr(app, 'max_clusters', getattr(app, '_max_clusters', 10))),
            'n_clusters': int(d.get('n_clusters', num_clusters_fallback if num_clusters_fallback is not None else 0)),
            'seed': (int(seed_fallback) if seed_fallback is not None else None),
            'distance': (str(distance_fallback) if distance_fallback is not None else None),
            'exponent': (float(exponent_fallback) if exponent_fallback is not None else None),
            'selected_clusters': list(d.get('selected_clusters', [])),
            'precondition': bool(getattr(app, 'dim_red_precondition', getattr(app, '_dim_red_precondition', False))),
            'n_basis': int(getattr(app, 'num_basis_for_precondition', getattr(app, '_num_basis_for_precondition', 0))),
        }
        return json.dumps(self.convert_numpy_types(out))


    @pyqtSlot(str, result=str)
    def getClusterOptionSpec(self, method):
        """
        Return which options are supported by a clustering method.

        Useful to enable/disable UI controls conditionally.

        Parameters
        ----------
        method : str
            Clustering method key as in AppData.cluster_dict.

        Returns
        -------
        str
            JSON string with boolean flags:
            {
            "supports_exponent": bool,
            "supports_distance": bool,
            "supports_seed": bool
            }
        """
        app = self.lame_blockly.app_data
        d = app.cluster_dict.get(method, {})

        spec = {
            'supports_exponent': ('exponent' in d) or hasattr(app, 'cluster_exponent') or hasattr(app, '_cluster_exponent'),
            'supports_distance': ('distance' in d) or hasattr(app, 'cluster_distance') or hasattr(app, '_cluster_distance'),
            'supports_seed':     ('seed' in d) or hasattr(app, 'cluster_seed') or hasattr(app, '_cluster_seed'),
        }
        return json.dumps(spec)


    @pyqtSlot(result=list)
    def getClusterDistanceOptions(self):
        """
        Return distance metrics available for clustering.

        Returns
        -------
        list
            List of distance names. Falls back to common metrics if not defined in AppData.
        """
        app = self.lame_blockly.app_data
        # If you add a canonical list to AppData (e.g., app.cluster_distance_options), we’ll use it.
        opts = getattr(app, 'cluster_distance_options', None)
        if isinstance(opts, (list, tuple)) and len(opts):
            return list(opts)
        # Fallback to a sensible default set used by your UI
        return ['euclidean', 'manhattan', 'cosine']


    @pyqtSlot(result=int)
    def randomClusterSeed(self) -> int:
        """Generate and return a random cluster seed from AppData.

        Returns
        -------
        int
            Random integer seed (0–1e9).
        """
        self.lame_blockly.app_data.generate_random_seed()
        return self.lame_blockly.app_data.cluster_seed


    # -------- Dimensional reduction defaults (optional helper) --------

    @pyqtSlot(result=str)
    def getDimRedDefaults(self):
        """
        Return default dimensional-reduction settings as JSON.

        Returns
        -------
        str
            JSON string with keys:
            {
            "method": str,
            "pc_x": int,
            "pc_y": int,
            "pc_x_max": int,
            "pc_y_max": int
            }
        """
        app = self.lame_blockly.app_data
        out = {
            'method': str(getattr(app, 'dim_red_method', getattr(app, '_dim_red_method', 'PCA: Principal component analysis (PCA)'))),
            'pc_x': int(getattr(app, 'dim_red_x', getattr(app, '_dim_red_x', 0))),
            'pc_y': int(getattr(app, 'dim_red_y', getattr(app, '_dim_red_y', 0))),
            'pc_x_max': int(getattr(app, 'dim_red_x_max', getattr(app, '_dim_red_x_max', 2))),
            'pc_y_max': int(getattr(app, 'dim_red_y_max', getattr(app, '_dim_red_y_max', 2))),
        }
        return json.dumps(out)


    


    def convert_numpy_types(self, obj):
        """Recursively convert NumPy types to Python native types.

        Parameters
        ----------
        obj : Any
            Input object possibly containing NumPy scalars/arrays.

        Returns
        -------
        Any
            Same structure with NumPy types converted to native Python types.
        """
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
        self.setParent(None)  # Make it a real top-level window
        
        container = QWidget()

        # Create the layout within main_window.tabWorkflow
        dock_layout = QVBoxLayout()   

        self.output_text_edit = CodeEditor(main_window)
        self.output_text_edit.setReadOnly(True)
        dock_layout.addWidget(self.output_text_edit)

        # attach the Python syntax highlighter
        self.highlighter = PythonHighlighter(self.output_text_edit.document())
        
        #### toolbar setup ####
        toolbar = QToolBar("Blockly Toolbar", self)
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
        # Button signals
        self.run_action.triggered.connect(lambda: self.bridge.lame_blockly.execute_code(self.output_text_edit))

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
                # Add a stretch (spacer) so label is at the right, optional
        toolbar.addSeparator()  # Optional: visual separator
        
        # Add status label
        self.statusLabel = QLabel("Ready")
        toolbar.addWidget(self.statusLabel)
        dock_layout.addWidget(toolbar)
        
        #### Blockly Setup ####
        #self.save_action.triggered.connect(self.save_workflow)
        #self.clear_action.triggered.connect(self.clear_workflow)

        # Create a web engine view
        self.web_view = QWebEngineView()
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Setup the WebChannel for communication
        self.channel = QWebChannel()

        # Create an instance of the BlocklyBridge and register it with the channel

        self.bridge = BlocklyBridge(parent=self)
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
        self.web_view.setUrl(QUrl.fromLocalFile(str(BASEDIR / 'blockly/index.html')))
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
        """Forward main window resize to the Blockly page for responsive layout.

        Parameters
        ----------
        event : QResizeEvent
            Qt resize event from the main window.
        """
        self.web_view.page().runJavaScript("resizeBlocklyWorkspace()")
        event.accept()

# --- Syntax Highlighter for Python ---
class PythonHighlighter(QSyntaxHighlighter):
    """Minimal Python syntax highlighter for QPlainTextEdit.

    Highlights Python keywords, strings, and comments.

    Parameters
    ----------
    parent : QAbstractTextDocumentLayout, optional
        Target document, typically `editor.document()`.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # Keywords
        kw_fmt = QTextCharFormat()
        kw_fmt.setForeground(QColor("#0077aa"))
        kw_fmt.setFontWeight(QFont.Weight.Bold)

        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def", "del",
            "elif", "else", "except", "False", "finally", "for", "from", "global",
            "if", "import", "in", "is", "lambda", "None", "nonlocal", "not", "or",
            "pass", "raise", "return", "True", "try", "while", "with", "yield"
        ]
        self.rules = [(QRegularExpression(rf"\b{kw}\b"), kw_fmt) for kw in keywords]

        # Strings
        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor("#aa5500"))
        self.rules.append((QRegularExpression(r"\"[^\"]*\""), str_fmt))
        self.rules.append((QRegularExpression(r"\'[^\']*\'"), str_fmt))

        # Comments
        com_fmt = QTextCharFormat()
        com_fmt.setForeground(QColor("#888888"))
        self.rules.append((QRegularExpression(r"#.*"), com_fmt))

    def highlightBlock(self, text: str):
        """Apply formatting rules to the given text block.

        Parameters
        ----------
        text : str
            The plain text of the current block.
        """
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)


# --- Line number gutter widget ---
class LineNumberArea(QWidget):
    """Narrow widget rendered to the left of the editor to show line numbers.

    Parameters
    ----------
    editor : CodeEditor
        The associated code editor instance that owns and paints this area.
    """
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        """Return preferred gutter size based on editor width."""
        return QSize(self._editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        """Delegate painting to the owning editor."""
        self._editor.lineNumberAreaPaintEvent(event)


# --- Code editor with gutter ---
class CodeEditor(QPlainTextEdit):
    """Plain-text code editor with a line-number gutter and current-line highlight.

    The gutter is painted in a sibling widget to the left of the text viewport.
    This widget is suitable for displaying generated/readonly Python code.

    Parameters
    ----------
    parent : QWidget, optional
        Parent widget, by default None.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)

        # Font & basic look
        self.setFont(QFont("Consolas", 10))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # Signals to keep the gutter in sync
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)
        self.highlightCurrentLine()

    # --- Public API ---
    def set_code(self, code: str):
        """Set the editor contents to the provided code.

        Parameters
        ----------
        code : str
            Text to display in the editor.
        """
        self.setPlainText(code)

    # --- Gutter geometry ---
    def lineNumberAreaWidth(self) -> int:
        """Compute the gutter width from the number of lines.

        Returns
        -------
        int
            Pixel width required for right-aligned line numbers.
        """
        # Width based on number of digits + padding
        digits = max(1, len(str(self.blockCount())))
        space = self.fontMetrics().horizontalAdvance('9') * digits + 14
        return space

    def updateLineNumberAreaWidth(self, _):
        """Update viewport margin to accommodate the gutter."""
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        """Scroll or update the gutter in response to editor updates.

        Parameters
        ----------
        rect : QRect
            Rect that changed in the editor.
        dy : int
            Vertical scroll delta; when non-zero, scroll gutter accordingly.
        """
        if dy != 0:
            self._line_number_area.scroll(0, dy)
        else:
            # Repaint the area that changed
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        """Reposition gutter on editor resize."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    # --- Painting the gutter ---
    def lineNumberAreaPaintEvent(self, event):
        """Paint the line-number gutter.

        Parameters
        ----------
        event : QPaintEvent
            Paint event covering the gutter region to redraw.
        """
        painter = QPainter(self._line_number_area)
        # Background
        painter.fillRect(event.rect(), QColor("#f5f5f5"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        # Draw visible line numbers
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                # Current line emphasis
                is_current = (block_number == self.textCursor().blockNumber())
                color = QColor("#444444") if not is_current else QColor("#0077aa")
                painter.setPen(color)

                # Right-align numbers
                fm = self.fontMetrics()
                x = self._line_number_area.width() - 6 - fm.horizontalAdvance(number)
                y = bottom - fm.descent()
                painter.drawText(x, y, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

        # Optional: separator line
        painter.setPen(QColor("#dddddd"))
        painter.drawLine(self._line_number_area.width() - 1, event.rect().top(),
                         self._line_number_area.width() - 1, event.rect().bottom())

    # --- Highlight current line ---
    def highlightCurrentLine(self):
        """Apply a subtle background to the current cursor line."""
        if self.isReadOnly():
            self.setExtraSelections([])
            return
        sel = QTextEdit.ExtraSelection()
        sel.format.setBackground(QColor(0, 120, 215, 20))  # subtle blue
        sel.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        sel.cursor = self.textCursor()
        sel.cursor.clearSelection()
        self.setExtraSelections([sel])
