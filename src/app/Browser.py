import os
from PyQt5.QtCore import ( Qt, QUrl, QEvent, QObject, pyqtSlot )
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from src.app.config import BASEDIR, DEBUG_BROWSER
    
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
    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent = parent

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


class Browser(QWidget, QObject):
    """A collection of browser related methods.

    Methods
    -------
    eventFilter
    open_browser :
        Opens a web browser for use in LaME
    browser_home_callback :
        Returns to project homepage.
    browser_location_callback :
        Loads location typed into the file line edit field.
    """    
    def __init__(self, parent=None):
        super().__init__(parent)
        QWidget.__init__(self)
        
        if DEBUG_BROWSER:
            print("Initializing browser")

        if parent is None:
            return

        self.parent = parent

        self.help_mapping = {
            parent.centralwidget: 'center_pane',
            parent.canvasWindow: 'center_pane',
            parent.dockWidgetLeftToolbox: 'left_toolbox',
            parent.toolBox: 'left_toolbox',
            parent.dockWidgetRightToolbox: 'right_toolbox',
            parent.toolBoxTreeView: 'right_toolbox',
            parent.dockWidgetBottomTabs: 'lower_tabs',
            parent.tabWidget: 'lower_tabs'
        }

        self.open_browser()
        #self.parent.browser = WebEngineView(self.parent)

        parent.toolButtonBrowserHome.clicked.connect(self.browser_home_callback)
        parent.lineEditBrowserLocation.editingFinished.connect(self.browser_location_callback)
        parent.toolButtonBack.clicked.connect(self.engine.back)
        parent.toolButtonForward.clicked.connect(self.engine.forward)

        for widget in self.help_mapping.keys():
            widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Event filter to capture mouse press events

        If help mode is active, the clicked widget opens the help browser.

        Parameters
        ----------
        source : any
            Calling application or dialog
        event : 
            Mouse click.

        Returns
        -------
        bool
            ``True`` if help is opened, otherwise ``False``
        """        
        if event.type() == QEvent.MouseButtonPress and self.parent.actionHelp.isChecked():
            self.parent.actionHelp.setChecked(False)
            self.setCursor(Qt.ArrowCursor)

            if obj in self.help_mapping:
                self.browser_location_callback(self.help_mapping[obj])
            else:
                return False

            if DEBUG_BROWSER:
                print("Browser.eventFilter: Accessing help page")

            self.parent.tabWidget.setCurrentIndex(self.parent.bottom_tab['help'])

            return True

        return super().eventFilter(obj, event)

    def open_browser(self):
        """Creates and opens a browser in the bottom tabWidget

        A browser for the LaME documentation.  It can access some external sites, but the browser is primarily for help data.
        """        
        if DEBUG_BROWSER:
            print("open_browser")

        # Open a file dialog to select a local HTML file
        # Create a QWebEngineView widget
        self.engine = WebEngineView(self.parent)
        self.parent.verticalLayoutBrowser.addWidget(self.engine)

        #file_name, _ = QFileDialog.getOpenFileName(self, "Open HTML File", "", "HTML Files (*.html *.htm)")
        self.browser_home_callback()

    def browser_home_callback(self):
        """The browser returns to the documentation index.html file"""        
        if DEBUG_BROWSER:
            print("browser_home_callback")

        filename = os.path.join(BASEDIR,"docs/build/html/index.html")

        self.parent.lineEditBrowserLocation.setText(filename)

        if filename:
            # Load the selected HTML file into the QWebEngineView
            self.engine.setUrl(QUrl.fromLocalFile(filename))
        
    def browser_location_callback(self, location=None):
        """Tries to load the page given in ``MainWindow.lineEditBrowserLocation``

        Parameters
        ----------
        location : str, optional
            Name of webpage (excluding base directory and .html)
        """
        if DEBUG_BROWSER:
            print(f"browser_location_callback, location {location}")

        if not location:
            location = self.parent.lineEditBrowserLocation.text()
        else:
            location = os.path.join(BASEDIR,"docs/build/html/"+location+".html")

        self.parent.lineEditBrowserLocation.setText(location)

        try:
            if location:
                self.engine.setUrl(QUrl.fromLocalFile(location))
        except:
            pass
            #self.browser.setUrl(QUrl(os.path.abspath('docs/build/html/404.html')))



