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
    """_summary_

    _extended_summary_

    Returns
    -------
    _type_
        _description_
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
    """Creates splash screen while LaME loads"""    
    pixmap = QPixmap("lame_splash.png")
    splash = QSplashScreen(pixmap)
    splash.setMask(pixmap.mask())
    splash.show()
    QTimer.singleShot(3000, splash.close)

def main():
    """Main function for LaME"""    
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