import sys, os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QTextEdit, QDockWidget, QToolButton, QWidget, QHBoxLayout, QVBoxLayout, QGroupBox
from PyQt5.QtGui import QIcon
from src.app.config import BASEDIR

class LoggerDock(QDockWidget):
    """A dock widget that contains a logging display.

    A logging dock widget useful for debugging and recording actions.

    Parameters
    ----------
    parent : QObject
        Calling window.
    """    
    def __init__(self, parent):
        if not isinstance(parent, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        super().__init__("Logger", parent)

        # Create container
        container = QWidget()
        logger_layout = QVBoxLayout()

        # Export button
        toolbar = QGroupBox("")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)  # Adjust margins as needed
        toolbar_layout.setSpacing(5)  # Spacing between buttons

        self.save_button = QToolButton()
        self.save_button.setIcon(QIcon(":resources/icons/icon-save-file-64.svg"))
        self.save_button.setToolTip("Save log")

        self.clear_button = QToolButton()
        self.clear_button.setIcon(QIcon(":resources/icons/icon-delete-64.svg"))
        self.clear_button.setToolTip("Clear log")

        toolbar_layout.addWidget(self.save_button)
        toolbar_layout.addWidget(self.clear_button)

        logger_layout.addWidget(toolbar)

        # Create QTextEdit for logging
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)

        logger_layout.addWidget(self.text_edit)

        # Set layout to the container
        container.setLayout(logger_layout)
        self.setWidget(container)

        self.setFloating(True)
        self.setWindowTitle("LaME Logger")

        # create hide button
        #hide_button = QToolButton()
        #hide_button.setIcon(QIcon(":/icons/icon-reject-64.svg"))
        #hide_button.setToolTip("Hide Dock")
        #hide_button.clicked.connect(self.hide)

        # handle signals
        self.save_button.clicked.connect(self.export_log)
        self.clear_button.clicked.connect(self.text_edit.clear)

        self.hide()

        parent.addDockWidget(Qt.RightDockWidgetArea, self)

        # Example print statements
        self.log_file = os.path.join(BASEDIR,"resources/log/lame.log")

    def closeEvent(self, event):
        """When closed stdout is restored to ``sys.__stdout__``

        Parameters
        ----------
        event : QEvent
            Executed on a close event.
        """        
        # Restore sys.stdout to its original state when the application closes
        sys.stdout = sys.__stdout__
        super().closeEvent(event)

    def write(self, message):
        """Adds message to logger

        Parameters
        ----------
        message : str
            Message to display in logger
        """        
        self.text_edit.append(message)  # Append the message to the QTextEdit

    def flush(self):
        """Flushes the write buffer.

        Currently doesn't do anything.
        """        
        pass  # Required to implement flush for compatibility

    def export_log(self):
        """
        Export the contents of the text edit to lame.log.
        """
        log_contents = self.text_edit.toPlainText()
        if log_contents.strip():
            try:
                with open(self.log_file, "w") as log_file:
                    log_file.write(log_contents)
                print(f"Log exported to: {self.log_file}")
            except Exception as e:
                print(f"Failed to export log: {e}")
        else:
            print("No log contents to export.")