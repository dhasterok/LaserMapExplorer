import sys
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (
        QMainWindow, QTextEdit, QDockWidget, QWidget, QVBoxLayout,
        QToolBar, QSpacerItem, QSizePolicy, QAction, QDialog, QCheckBox, QDialogButtonBox
    )
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
        self.parent = parent

        # Create container
        container = QWidget()
        logger_layout = QVBoxLayout()

        # Create toolbar
        toolbar = QToolBar("Notes Toolbar", self)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out

        # Export button
        self.action_save = QAction()
        save_icon = QIcon(":resources/icons/icon-save-file-64.svg")
        if not save_icon.isNull():
            self.action_save.setIcon(save_icon)
        else:
            self.action_save.setText("Save")
        self.action_save.setToolTip("Save log to file")

        # Add spacer
        spacer = QSpacerItem(20, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)

        if hasattr(parent,'logger_options'):
            self.action_settings = QAction()
            settings_icon = QIcon(":resources/icons/icon-gear-64.svg")
            if not settings_icon.isNull():
                self.action_settings.setIcon(settings_icon)
            else:
                self.action_settings.setText("Settings")
            self.action_settings.setToolTip("Logger settings")

        self.action_clear = QAction()
        clear_icon = QIcon(":resources/icons/icon-delete-64.svg")
        if not clear_icon.isNull():
            self.action_clear.setIcon(clear_icon)
        else:
            self.action_clear.setText("Clear")
        self.action_clear.setToolTip("Clear log")

        toolbar.addAction(self.action_save)
        toolbar.addAction(self.action_settings)
        toolbar.addSeparator()
        toolbar.addAction(self.action_clear)

        logger_layout.addWidget(toolbar)

        # Create QTextEdit for logging
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)

        logger_layout.addWidget(self.text_edit)

        # handle actions
        self.action_save.triggered.connect(self.export_log)
        if hasattr(self,'action_settings'):
            self.action_settings.triggered.connect(self.set_logger_options)
        self.action_clear.triggered.connect(self.text_edit.clear)

        # Set layout to the container
        container.setLayout(logger_layout)
        self.setWidget(container)

        self.setFloating(True)
        self.setWindowTitle("LaME Logger")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

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

    def set_logger_options(self):
        """ Opens a dialog to edit logger options."""
        dialog = LoggerOptionsDialog(self.parent.logger_options, self)
        if dialog.exec() == QDialog.Accepted:
            self.parent.logger_options = dialog.get_updated_options()

class LoggerOptionsDialog(QDialog):
    """Allows the user to set logger options.

    The use of these options is determined by the main program, not the logger,
    this is simply a place to view and change them.

    Parameters
    ----------
    options_dict : dict
        A dictionary of options with key values displayed as the labels and values
        are bool indicating a set option for logging.
    parent : LoggerDock, optional
        Parent logger, by default None
    """        
    def __init__(self, options_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Logger Options")
        self.setLayout(QVBoxLayout())

        # Store references to checkboxes and the dictionary
        self.options_dict = options_dict.copy()
        self.checkboxes = {}

        # Create checkboxes based on the dictionary
        for key, value in self.options_dict.items():
            checkbox = QCheckBox(key)  # The label is set directly here
            checkbox.setChecked(value)  # Set initial state from the dictionary
            self.checkboxes[key] = checkbox
            self.layout().addWidget(checkbox)

        # Add OK button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        self.layout().addWidget(button_box)

    def get_updated_options(self):
        """
        Updates the dictionary with the current state of checkboxes and returns it.

        Returns
        -------
        dict
            Returns the dictionary of boolean logger options
        """
        for key, checkbox in self.checkboxes.items():
            self.options_dict[key] = checkbox.isChecked()
        return self.options_dict

