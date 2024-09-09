import os
from PyQt5.QtCore import ( Qt, QUrl, QEvent, pyqtSlot )
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from lame_helper import BASEDIR
    
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
        if not success:
            self.setUrl(QUrl(os.path.abspath('docs/build/html/404.html')))
            #self.show_error_page()

    @pyqtSlot()
    def on_load_started(self):
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
        html = f"<html><body><img src={os.path.abspath('docs/build/html/404.html')} /></html>"
        self.setHtml(html)

    def handle_console_message(self, level, message, line, source_id):
        pass
        #print(f"JavaScript Console: {message} at line {line} in {source_id}")


class Browser():
    def __init__(self, parent=None):
        
        self.parent = parent

        self.open_browser()
        #self.parent.browser = WebEngineView(self.parent)

        self.parent.toolButtonBrowserHome.clicked.connect(self.browser_home_callback)
        self.parent.lineEditBrowserLocation.editingFinished.connect(self.browser_location_callback)
        self.parent.toolButtonBack.clicked.connect(self.parent.browser.back)
        self.parent.toolButtonForward.clicked.connect(self.parent.browser.forward)

    def eventFilter(self, source, event):
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

            match source:
                case self.parent.centralwidget | self.parent.canvasWindow:
                    self.browser_location_callback('center_pane')
                case self.parent.toolBox | self.parent.dockWidgetLeftToolbox:
                    self.browser_location_callback('left_toolbox')
                case self.parent.toolBoxTreeView | self.parent.dockWidgetRightToolbox:
                    self.browser_location_callback('right_toolbox')
                case self.parent.dockWidgetBottomTabs | self.parent.tabWidget:
                    self.browser_location_callback('lower_tabs')
                case _:
                    return False
            self.parent.tabWidget.setCurrentIndex(self.parent.bottom_tab['help'])

            return True

        return super().eventFilter(source, event)

    def open_browser(self):
        """Creates and opens a browser in the bottom tabWidget

        A browser for the LaME documentation.  It can access some external sites, but the browser is primarily for help data.
        """        
        # Open a file dialog to select a local HTML file
        # Create a QWebEngineView widget
        self.parent.browser = WebEngineView(self.parent)
        self.parent.verticalLayoutBrowser.addWidget(self.parent.browser)

        #file_name, _ = QFileDialog.getOpenFileName(self, "Open HTML File", "", "HTML Files (*.html *.htm)")
        self.browser_home_callback()

    def browser_home_callback(self):
        """The browser returns to the documentation index.html file"""        
        filename = os.path.join(BASEDIR,"docs/build/html/index.html")

        self.parent.lineEditBrowserLocation.setText(filename)

        if filename:
            # Load the selected HTML file into the QWebEngineView
            self.parent.browser.setUrl(QUrl.fromLocalFile(filename))
        
    def browser_location_callback(self, location=None):
        """Tries to load the page given in ``MainWindow.lineEditBrowserLocation``

        Parameters
        ----------
        location : str, optional
            Name of webpage (excluding base directory and .html)
        """
        if not location:
            location = self.parent.lineEditBrowserLocation.text()
        else:
            location = os.path.join(BASEDIR,"docs/build/html/"+location+".html")

        self.parent.lineEditBrowserLocation.setText(location)

        try:
            if location:
                self.parent.browser.setUrl(QUrl.fromLocalFile(location))
        except:
            pass
            #self.browser.setUrl(QUrl(os.path.abspath('docs/build/html/404.html')))



