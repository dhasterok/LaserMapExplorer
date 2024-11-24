import sys
from PyQt5.QtWidgets import QMainWindow, QTextEdit, QDockWidget
from PyQt5.QtCore import Qt

class LoggerDock:
    def __init__(self, parent):
        if not isinstance(parent, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        # Create QTextEdit for logging
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)

        # Create a QDockWidget
        self.dockLogger = QDockWidget("Logger", parent)
        self.dockLogger.setWidget(self.text_edit)
        self.dockLogger.setFloating(True)  # Start as a floating widget
        parent.addDockWidget(Qt.RightDockWidgetArea, self.dockLogger)

        # Example print statements
        print("This message will appear in the floating QDockWidget!")
        print("Logger is active.")

    def closeEvent(self, event):
        # Restore sys.stdout to its original state when the application closes
        sys.stdout = sys.__stdout__
        super().closeEvent(event)

    def write(self, message):
        self.text_edit.append(message)  # Append the message to the QTextEdit

    def flush(self):
        pass  # Required to implement flush for compatibility