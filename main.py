import sys, os, darkdetect
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QSplashScreen, QApplication
from PyQt6.QtGui import QPixmap, QIcon
from src.app.config import BASEDIR, ICONPATH, load_stylesheet
from src.app.MainWindow import MainWindow

# -------------------------------
# MAIN FUNCTION!!!
# Sure doesn't look like much
# -------------------------------
app = None

def create_app():
    """
    Initializes and configures the QApplication instance for the application.

    This function creates a global QApplication object, applies a high-DPI scaling setting (default in PyQt6),
    and sets the application's stylesheet based on the current system theme (dark or light mode).  The stylesheet
    is loaded from either 'dark.qss' or 'light.qss' using the `load_stylesheet` function.  If the system is in
    dark mode, it applies the dark stylesheet; otherwise, it applies the light stylesheet.

    The function also sets the global `app` variable to the created QApplication instance.

    This function should be called before creating any GUI elements to ensure that the application is properly initialized.

    Returns
    -------
    QApplication :
        The initialized and configured QApplication instance.
    """

    global app
    app = QApplication(sys.argv)

    # Enable high-DPI scaling (enabled by default in PyQt6)

    if darkdetect.isDark():
        ss = load_stylesheet('dark.qss')
        app.setStyleSheet(ss)
    else:
        ss = load_stylesheet('light.qss')
        app.setStyleSheet(ss)

    return app

def show_splash():
    """
    Displays a splash screen for the application using a QPixmap image.

    The splash screen shows an image for 3 seconds before closing automatically.
    """
    pixmap = QPixmap("lame_splash.png")
    splash = QSplashScreen(pixmap)
    splash.setMask(pixmap.mask())
    splash.show()
    QTimer.singleShot(3000, splash.close)

def main():
    """
    Main entry point for the application.

    This function initializes the application, displays a splash screen,
    and creates the main window of the application.  It sets the
    application icon and starts the event loop.

    It also ensures that the application exits cleanly when the main window is closed.
    """    
    app = create_app()
    show_splash()

    # Uncomment this line to set icon to App
    app.setWindowIcon(QIcon(os.path.join(BASEDIR, os.path.join(ICONPATH,'LaME-64.svg'))))

    # create application data properties with notifiable observers that can be used to
    # update widgets in the UI
    main = MainWindow(app)

    # Set the main window to fullscreen
    #main.showFullScreen()
    main.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()