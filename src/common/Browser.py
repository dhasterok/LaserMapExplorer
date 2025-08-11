import os
from PyQt6.QtCore import ( Qt, QUrl, QEvent, pyqtSlot, QSize )
from PyQt6.QtWidgets import ( 
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy, QDockWidget, QGroupBox,
    QLabel, QLineEdit, QToolBar
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtGui import QIcon, QMouseEvent
from src.common.CustomWidgets import CustomAction, CustomToolButton
from src.common.Logger import LoggerConfig, auto_log_methods
    
# WebEngineView - Web engine for viewing userguide help pages
# -------------------------------
@auto_log_methods(logger_key='Browser')
class WebEngineView(QWebEngineView):
    """Creates a web engine widget to display user guide

    _extended_summary_

    Parameters
    ----------
    QWebEngineView : QWebEngine
        A web engine widget
    """    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger_key = 'Browser'
        self.parent = parent

        # Connect signals
        self.loadFinished.connect(self.on_load_finished)
        self.loadStarted.connect(self.on_load_started)
        self.loadProgress.connect(self.on_load_progress)
        self.page().profile().setHttpAcceptLanguage("en-US,en;q=0.9")
        self.page().profile().setHttpUserAgent("LaME Browser 1.0")

        # Set up a JavaScript console message handler
        self.page().setWebChannel(None)
        self.page().setFeaturePermission(
            QUrl(),
            QWebEnginePage.Feature.Notifications,
            QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )
        self.page().javaScriptConsoleMessage = self.handle_console_message

    @pyqtSlot(bool)
    def on_load_finished(self, success):
        """Executes after page loading is complete

        Parameters
        ----------
        success : bool
            Runs upon load
        """        
        if not success:
            self.show_error_page()
            #self.show_error_page()

    @pyqtSlot()
    def on_load_started(self):
        """Executes when page starts to load."""
        self.parent.statusBar().showMessage("Loading started...")

    @pyqtSlot(int)
    def on_load_progress(self, progress):
        """Adds a loading progress message to the MainWindow.statusBar 

        Parameters
        ----------
        progress : int
            Loading fraction
        """        
        self.parent.statusBar().showMessage(f"Loading progress: {progress}%")

    def show_error_page(self):
        """Displays 404 error page."""
        html = f"<html><body><img src={os.path.abspath('docs/build/html/404.html')} /></html>"
        self.setHtml(html)

    def handle_console_message(self, level, message, line, source_id):
        pass
        #print(f"JavaScript Console: {message} at line {line} in {source_id}")


@auto_log_methods(logger_key='Browser')
class Browser(QDockWidget):
    """A collection of browser related methods.

    Parameters
    ----------
    parent : QMainWindow
        Calling UI
    help_mapping : dict
        Dictionary with objects as keys and page (excluding html) for navigation
    base_path : str
        Base directory to docs/build/html.

    Methods
    -------
    eventFilter : 
        event filter used to select help page.
    open_browser :
        Opens a web browser for use in LaME
    go_to_home :
        Returns to project homepage.
    go_to_page :
        Loads location typed into the file line edit field.

    Raises
    ------
    TypeError :
        Parent must be an instance of QMainWindow
    """    
    def __init__(self, parent=None, help_mapping={}, base_path=''):
        if not isinstance(parent, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")
        super().__init__(parent)

        self.logger_key = 'Browser'

        container = QWidget()

        if parent is None:
            return

        self.parent = parent

        self.help_mapping = help_mapping
        self.base_path = base_path

        self.dock_layout = QVBoxLayout(container)

        toolbar = QToolBar("Browser Toolbar", self)
        toolbar.setIconSize(QSize(32, 32))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out

        # self.groupBoxBrowserControl = QtWidgets.QGroupBox(self.container)
        # self.groupBoxBrowserControl.setMinimumSize(QtCore.QSize(0, 40))
        # self.groupBoxBrowserControl.setMaximumSize(QtCore.QSize(16777215, 40))
        # self.groupBoxBrowserControl.setTitle("")
        # self.groupBoxBrowserControl.setObjectName("groupBoxBrowserControl")
        
        # Run button
        self.home_action = CustomAction(
            text="Home",
            light_icon_unchecked="icon-home-64.svg",
            dark_icon_unchecked="icon-home-dark-64.svg",
            parent=toolbar,
        )
        self.home_action.setToolTip("Return to LaME documentation homepage")

        self.back_action = CustomAction(
            text="Back",
            light_icon_unchecked="icon-back-arrow-64.svg",
            dark_icon_unchecked="icon-back-arrow-dark-64.svg",
            parent=toolbar,
        )
        self.back_action.setToolTip("Return to the previous page")

        self.forward_action = CustomAction(
            text="Forward",
            light_icon_unchecked="icon-forward-arrow-64.svg",
            dark_icon_unchecked="icon-forward-arrow-dark-64.svg",
            parent=toolbar,
        )
        self.forward_action.setToolTip("Return to the next page")

        self.location_label = QLabel()
        self.browser_location = QLineEdit()
        self.browser_location.setMinimumSize(QSize(200, 20))
        self.browser_location.setMaximumSize(QSize(16777215, 20))
        self.browser_location.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        toolbar.addAction(self.home_action)
        toolbar.addAction(self.back_action)
        toolbar.addAction(self.forward_action)
        toolbar.addWidget(self.location_label)
        toolbar.addWidget(self.browser_location)

        self.dock_layout.addWidget(toolbar)

        self.setWidget(container)

        self.setFloating(True)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)

        self.setWindowTitle("Documentation")

        self.setMinimumSize(QSize(800, 500))
        self.setMaximumSize(QSize(16777215, 16777215))

        # open browser
        self.open_browser()

        # connect widget slots
        self.home_action.triggered.connect(self.go_to_home)
        self.browser_location.editingFinished.connect(self.go_to_page)
        self.back_action.triggered.connect(self.engine.back)
        self.forward_action.triggered.connect(self.engine.forward)

        # install event filter for help
        for widget in self.help_mapping.keys():
            widget.installEventFilter(self)

        parent.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self)

        self.show()

    def eventFilter(self, obj, event):
        """Event filter to capture mouse press and hover events

        If help mode is active, handles mouse clicks to open help or changes cursor on hover.

        Parameters
        ----------
        obj : QObject
            The widget the event occurred on.
        event : QEvent
            The event being filtered.

        Returns
        -------
        bool
            ``True`` if the event was handled, otherwise ``False``.
        """        
        if self.parent.lame_action.Help.isChecked():
            # Handle hover events
            if event.type() == QEvent.Type.Enter:
                if obj in self.help_mapping:
                    self.parent.setCursor(Qt.CursorShape.WhatsThisCursor)
                else:
                    self.parent.setCursor(Qt.CursorShape.ForbiddenCursor)
                return True
            elif event.type() == QEvent.Type.Leave:
                # Reset cursor when leaving a widget
                self.parent.setCursor(Qt.CursorShape.WhatsThisCursor)
                return True

            # Handle mouse press events
            if event.type() == QEvent.Type.MouseButtonPress:
                self.parent.lame_action.Help.setChecked(False)
                self.parent.setCursor(Qt.CursorShape.ArrowCursor)

                if obj in self.help_mapping:
                    self.go_to_page(self.help_mapping[obj])
                else:
                    return False

                return True

        return super().eventFilter(obj, event)


    def open_browser(self):
        """Creates and opens a browser in the bottom tabWidget

        A browser for the LaME documentation.  It can access some external sites, but the browser is primarily for help data.
        """        
        # Open a file dialog to select a local HTML file
        # Create a QWebEngineView widget
        self.engine = WebEngineView(self.parent)
        self.dock_layout.addWidget(self.engine)

        #file_name, _ = QFileDialog.getOpenFileName(self, "Open HTML File", "", "HTML Files (*.html *.htm)")
        self.go_to_home()

    def go_to_home(self):
        """The browser returns to the documentation index.html file"""        
        filename = os.path.join(self.base_path,"docs/build/html/index.html")

        self.browser_location.setText(filename)

        if filename:
            # Load the selected HTML file into the QWebEngineView
            self.engine.setUrl(QUrl.fromLocalFile(filename))
        
    def go_to_page(self, location=None):
        """Tries to load the page given in ``MainWindow.browser_location``

        Parameters
        ----------
        location : str, optional
            Name of webpage (excluding base directory and .html)
        """
        if not location:
            location = self.browser_location.text()
        else:
            location = os.path.join(self.base_path,"docs/build/html/"+location+".html")

        self.browser_location.setText(location)

        try:
            if location:
                self.engine.setUrl(QUrl.fromLocalFile(location))
        except:
            pass
            #self.browser.setUrl(QUrl(os.path.abspath('docs/build/html/404.html')))