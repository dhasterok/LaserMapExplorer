import os
from PyQt5.QtCore import ( Qt, QUrl, QEvent, pyqtSlot, QSize )
from PyQt5.QtWidgets import ( QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy, QDockWidget, QGroupBox, QToolButton, QLabel, QLineEdit )
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtGui import QIcon, QMouseEvent
    
# WebEngineView - Web engine for viewing userguide help pages
# -------------------------------
class WebEngineView(QWebEngineView):
    """Creates a web engine widget to display user guide

    _extended_summary_

    Parameters
    ----------
    QWebEngineView : QWebEngine
        A web engine widget
    """    
    def __init__(self, parent=None, debug=False):
        super().__init__(parent)

        self.parent = parent
        self.debug = debug

        # Connect signals
        self.loadFinished.connect(self.on_load_finished)
        self.loadStarted.connect(self.on_load_started)
        self.loadProgress.connect(self.on_load_progress)
        self.page().profile().setHttpAcceptLanguage("en-US,en;q=0.9")
        self.page().profile().setHttpUserAgent("MyBrowser 1.0")

        # Set up a JavaScript console message handler
        self.page().setWebChannel(None)
        self.page().setFeaturePermission(QUrl(), QWebEnginePage.Notifications, QWebEnginePage.PermissionGrantedByUser)
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
        self.parent.statusBar.showMessage("Loading started...")

    @pyqtSlot(int)
    def on_load_progress(self, progress):
        """Adds a loading progress message to the MainWindow.statusBar 

        Parameters
        ----------
        progress : int
            Loading fraction
        """        
        self.parent.statusBar.showMessage(f"Loading progress: {progress}%")

    def show_error_page(self):
        """Displays 404 error page."""
        html = f"<html><body><img src={os.path.abspath('docs/build/html/404.html')} /></html>"
        self.setHtml(html)

    def handle_console_message(self, level, message, line, source_id):
        pass
        #print(f"JavaScript Console: {message} at line {line} in {source_id}")


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
    debug : bool, optional
        A verbose mode for the browser, by Default ``False``

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
    def __init__(self, parent=None, help_mapping={}, base_path='', debug=False):
        if not isinstance(parent, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")
        super().__init__(parent)

        container = QWidget()

        self.debug = debug
        
        if self.debug:
            print("Initializing browser")

        if parent is None:
            return

        self.parent = parent

        self.help_mapping = help_mapping
        self.base_path = base_path

        self.dock_layout = QVBoxLayout(container)

        toolbar = QGroupBox("")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)  # Adjust margins as needed
        toolbar_layout.setSpacing(5)  # Spacing between buttons
        toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # self.groupBoxBrowserControl = QtWidgets.QGroupBox(self.container)
        # self.groupBoxBrowserControl.setMinimumSize(QtCore.QSize(0, 40))
        # self.groupBoxBrowserControl.setMaximumSize(QtCore.QSize(16777215, 40))
        # self.groupBoxBrowserControl.setTitle("")
        # self.groupBoxBrowserControl.setObjectName("groupBoxBrowserControl")
        
        # Run button
        self.home_button = QToolButton()
        home_icon = QIcon(":resources/icons/icon-home-64.svg")
        if not home_icon.isNull():
            self.home_button.setIcon(home_icon)
        else:
            self.home_button.setText("Home")
        self.home_button.setToolTip("Return to LaME documentation homepage")

        self.back_button = QToolButton()
        back_icon = QIcon(":resources/icons/icon-back-arrow-64.svg")
        if not back_icon.isNull():
            self.back_button.setIcon(back_icon)
        else:
            self.back_button.setText("Back")
        self.back_button.setToolTip("Back")

        self.forward_button = QToolButton()
        forward_icon = QIcon(":resources/icons/icon-forward-arrow-64.svg")
        if not forward_icon.isNull():
            self.forward_button.setIcon(forward_icon)
        else:
            self.forward_button.setText("Forward")
        self.forward_button.setToolTip("Forward")

        self.location_label = QLabel()
        self.browser_location = QLineEdit()
        self.browser_location.setMinimumSize(QSize(200, 20))
        self.browser_location.setMaximumSize(QSize(16777215, 20))
        self.browser_location.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        toolbar_layout.addWidget(self.home_button)
        toolbar_layout.addWidget(self.back_button)
        toolbar_layout.addWidget(self.forward_button)
        toolbar_layout.addWidget(self.location_label)
        toolbar_layout.addWidget(self.browser_location)

        self.dock_layout.addWidget(toolbar)

        self.setWidget(container)

        self.setFloating(True)
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

        self.setWindowTitle("Documentation")

        self.setMinimumSize(QSize(300, 150))
        self.setMaximumSize(QSize(16777215, 16777215))

        # open browser
        self.open_browser()
        #self.parent.browser = WebEngineView(self.parent)

        # connect widget slots
        self.home_button.clicked.connect(self.go_to_home)
        self.browser_location.editingFinished.connect(self.go_to_page)
        self.back_button.clicked.connect(self.engine.back)
        self.forward_button.clicked.connect(self.engine.forward)

        # install event filter for help
        for widget in self.help_mapping.keys():
            widget.installEventFilter(self)

        parent.addDockWidget(Qt.BottomDockWidgetArea, self)

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
        if self.parent.actionHelp.isChecked():
            # Handle hover events
            if event.type() == QEvent.Enter:
                if obj in self.help_mapping:
                    self.parent.setCursor(Qt.WhatsThisCursor)
                else:
                    self.parent.setCursor(Qt.ForbiddenCursor)
                return True
            elif event.type() == QEvent.Leave:
                # Reset cursor when leaving a widget
                self.parent.setCursor(Qt.WhatsThisCursor)
                return True

            # Handle mouse press events
            if event.type() == QEvent.MouseButtonPress:
                self.parent.actionHelp.setChecked(False)
                self.parent.setCursor(Qt.ArrowCursor)

                if obj in self.help_mapping:
                    self.go_to_page(self.help_mapping[obj])
                else:
                    return False

                if self.debug:
                    print(f"Browser.eventFilter: Accessing help page {obj}:{self.help_mapping[obj]}")

                return True

        return super().eventFilter(obj, event)


    def open_browser(self):
        """Creates and opens a browser in the bottom tabWidget

        A browser for the LaME documentation.  It can access some external sites, but the browser is primarily for help data.
        """        
        if self.debug:
            print("open_browser")

        # Open a file dialog to select a local HTML file
        # Create a QWebEngineView widget
        self.engine = WebEngineView(self.parent)
        self.dock_layout.addWidget(self.engine)

        #file_name, _ = QFileDialog.getOpenFileName(self, "Open HTML File", "", "HTML Files (*.html *.htm)")
        self.go_to_home()

    def go_to_home(self):
        """The browser returns to the documentation index.html file"""        
        if self.debug:
            print("go_to_home")

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
        if self.debug:
            print(f"go_to_page, location {location}")

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