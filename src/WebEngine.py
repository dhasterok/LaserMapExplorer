import os
from PyQt5.QtCore import (
    QUrl, pyqtSlot
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage

class WebEngineView(QWebEngineView):
    """Creates a web engine widget to display user guide

    Creates and opens a browser in the bottom tabWidget.  A browser for the LaME documentation.  It can access
    some external sites, but the browser is primarily for help data.
    
    Parameters
    ----------
    QWebEngineView : QWebEngine
        A web engine widget
    """    
    def __init__(self, parent=None):
        super().__init__(parent)

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

        self.browser = WebEngineView(parent=self)
        self.verticalLayoutBrowser.addWidget(self.browser)

        #file_name, _ = QFileDialog.getOpenFileName(self, "Open HTML File", "", "HTML Files (*.html *.htm)")
        self.browser_home_callback()

    @pyqtSlot(bool)
    def on_load_finished(self, success):
        if not success:
            self.setUrl(QUrl(os.path.abspath('docs/build/html/404.html')))
            #self.show_error_page()

    @pyqtSlot()
    def on_load_started(self):
        self.statusBar.showMessage("Loading started...")

    @pyqtSlot(int)
    def on_load_progress(self, progress):
        """Adds a loading progress message to the MainWindow.statusBar 

        Parameters
        ----------
        progress : int
            Loading fraction
        """        
        self.statusBar.showMessage(f"Loading progress: {progress}%")

    def show_error_page(self):
        html = f"<html><body><img src={os.path.abspath('docs/build/html/404.html')} /></html>"
        self.setHtml(html)

    def handle_console_message(self, level, message, line, source_id):
        pass
        #print(f"JavaScript Console: {message} at line {line} in {source_id}")

    def browser_home_callback(self):
        """The browser returns to the documentation index.html file"""        
        filename = os.path.join(basedir,"docs/build/html/index.html")

        self.lineEditBrowserLocation.setText(filename)

        if filename:
            # Load the selected HTML file into the QWebEngineView
            self.browser.setUrl(QUrl.fromLocalFile(filename))
        
    def browser_location_callback(self, location=None):
        """Tries to load the page given in ``MainWindow.lineEditBrowserLocation``

        Parameters
        ----------
        location : str, optional
            Name of webpage (excluding base directory and .html)
        """
        if not location:
            location = self.lineEditBrowserLocation.text()
        else:
            location = os.path.join(basedir,"docs/build/html/"+location+".html")

        self.lineEditBrowserLocation.setText(location)

        try:
            if location:
                self.browser.setUrl(QUrl.fromLocalFile(location))
        except:
            pass
            #self.browser.setUrl(QUrl(os.path.abspath('docs/build/html/404.html')))
