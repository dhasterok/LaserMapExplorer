import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import ( QMainWindow, QTextEdit, QDockWidget, QToolButton, QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QSpacerItem, QSizePolicy )
from PyQt5.QtGui import QIcon

class LoggerDock(QDockWidget):
    """A dock widget that contains a logging display.

    A logging dock widget useful for debugging and recording actions.

    Parameters
    ----------
    parent : QObject
        Calling window.
    """    
    def __init__(self, file='temp.log', parent=None):
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
        save_icon = QIcon(":resources/icons/icon-save-file-64.svg")
        if not save_icon.isNull():
            self.save_button.setIcon(save_icon)
        else:
            self.save_button.setText("Save")
        self.save_button.setToolTip("Save log to file")

        # Add spacer
        spacer = QSpacerItem(20, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.clear_button = QToolButton()
        clear_icon = QIcon(":resources/icons/icon-delete-64.svg")
        if not clear_icon.isNull():
            self.clear_button.setIcon(clear_icon)
        else:
            self.clear_button.setText("Clear")
        self.clear_button.setToolTip("Clear log")

        toolbar_layout.addWidget(self.save_button)
        toolbar_layout.addItem(spacer)
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
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

        # create hide button
        #hide_button = QToolButton()
        #hide_button.setIcon(QIcon(":/icons/icon-reject-64.svg"))
        #hide_button.setToolTip("Hide Dock")
        #hide_button.clicked.connect(self.hide)

        # handle signals
        self.save_button.clicked.connect(self.export_log)
        self.clear_button.clicked.connect(self.text_edit.clear)

        parent.addDockWidget(Qt.RightDockWidgetArea, self)

        # Example print statements
        self.log_file = file 

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