import sys, functools, inspect, types

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
        QMainWindow, QLineEdit, QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
        QToolBar, QSpacerItem, QSizePolicy, QDialog, QCheckBox, QDialogButtonBox, QToolButton, QWidgetAction
    )
from PyQt6.QtGui import QIcon, QAction, QFont, QTextCursor, QTextCharFormat, QColor, QTextDocument

from src.common.CustomWidgets import CustomDockWidget, ToggleSwitch
from src.common.SearchTool import SearchWidget

_global_logger = None

def set_global_logger(logger):
    global _global_logger
    _global_logger = logger

def get_global_logger():
    return _global_logger

def log(msg, prefix=""):
    if LoggerConfig.is_paused():
        return

    logger = get_global_logger()
    if not (prefix == ""):
        prefix = f"{prefix}: "
    if logger and hasattr(logger, 'write'):
        logger.write(f"{prefix}{msg}")
    else:
        print(f"{prefix}{msg}")

def log_call(logger_key=None):
    """Method decorator to log function whenever it is called

    Parameters
    ----------
    logger_key : str, optional
        key into dict logger_options, by default None
    show_args : bool, optional
        If True will print method arguments in the log, by default False
    show_call_chain : bool, optional
        If True will give the supply chain, by default False
    """    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Determine if 'self' exists (bound method)
            self_obj = args[0] if args else None
            if logger_key and LoggerConfig.get_option(logger_key):
                prefix = f"{logger_key.upper()}"

                if self_obj and hasattr(self_obj, 'logger_options'):
                    if not self_obj.logger_options.get(logger_key, False):
                        return func(*args, **kwargs)
            else:
                prefix = ""

            # Build message
            func_name = func.__qualname__
            caller = inspect.stack()[1].function
            parts = [f"{prefix}: [{caller} → {func_name}]"]

            if LoggerConfig.get_show_args():
                arg_list = [describe_arg(arg) for arg in args]
                kwarg_list = [f"{k}={describe_arg(v)}" for k, v in kwargs.items()]
                parts.append("args=[" + ", ".join(arg_list + kwarg_list) + "]")

            if LoggerConfig.get_show_call_chain():
                chain = " → ".join(f.function for f in reversed(inspect.stack()[1:4]))
                parts.append(f"chain:/ {chain}")

            log(" | ".join(parts))
            return func(*args, **kwargs)
        return wrapper
    return decorator

def describe_arg(arg):
    """Return a string description of the argument."""
    try:
        if hasattr(arg, 'objectName') and callable(arg.objectName):
            name = arg.objectName()
            cls = arg.__class__.__name__
            return f"<{cls} name='{name}'>"
        return repr(arg)
    except Exception:
        return "<unprintable>"

def auto_log_methods(logger_key: str=None, **log_options):
    """Decorator that wraps all methods in a class   

    Parameters
    ----------
    logger_key : str, optional
        key into dict logger_options, by default None
    """    
    def decorator(cls):
        print(f"[DEBUG] Wrapping methods for: {cls.__name__}")
        for attr_name in dir(cls):
            if attr_name.startswith("__"):
                continue

            attr = getattr(cls, attr_name)
            if not isinstance(attr, types.FunctionType):
                continue  # Skip non-function attributes

            if getattr(attr, "_no_log", False):
                print(f"  - Skipping method (no_log): {attr_name}")
                continue

            print(f"  - Wrapping method: {attr_name}")
            wrapped = log_call(logger_key=logger_key, **log_options)(attr)
            setattr(cls, attr_name, wrapped)
        return cls
    return decorator

def no_log(func):
    """A decorator to skip logging a function

    Use the decorator @no_log before the function defininition to prevent logging the function.

    Parameters
    ----------
    func : _type_
        Function not to log

    Returns
    -------
    bool
        sets func._no_log flag to True to skip logging
    """
    func._no_log = True
    return func

class LoggerConfig:
    # _options is used to set flags for the logged items (classes/methods)
    _options = {}

    # log arguments/call chain
    _show_args = True
    _show_call_chain = False

    # to pause the logging
    _paused = False

    @classmethod
    def set_options(cls, options_dict):
        cls._options = options_dict

    @classmethod
    def get_option(cls, key):
        return cls._options.get(key, False)

    @classmethod
    def get_all(cls):
        return cls._options

    @classmethod
    def set_show_args(cls, value: bool):
        cls._show_args = value

    @classmethod
    def get_show_args(cls):
        return cls._show_args

    @classmethod
    def set_show_call_chain(cls, value: bool):
        cls._show_call_chain = value

    @classmethod
    def get_show_call_chain(cls):
        return cls._show_call_chain

    @classmethod
    def is_paused(cls):
        return cls._paused

    @classmethod
    def set_paused(cls, value: bool):
        cls._paused = value

class LoggerDock(CustomDockWidget):
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

        super().__init__(parent)
        self.parent = parent

        self.log_colors = {
            "Error": "red",
            "Warning": "orange",
            "UI": "blue",
            "Data": "green",
        }

        self.match_cursors = []
        self.current_match_index = -1

        #self.logger = LogCounter()
        set_global_logger(self)

        # Create container
        container = QWidget()
        logger_layout = QVBoxLayout()

        # Create toolbar
        toolbar = QToolBar("Notes Toolbar", self)
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)  # Optional: Prevent toolbar from being dragged out

        # log toggle
        self.log_toggle = ToggleSwitch(toolbar, height=18, bg_left_color="#D8ADAB", bg_right_color="#A8B078")
        self.log_toggle.setChecked(True)
        self.log_toggle.setToolTip("Pause/resume logging")
        self.actionLogToggle = QWidgetAction(toolbar)
        self.actionLogToggle.setDefaultWidget(self.log_toggle)
        self.log_toggle.stateChanged.connect(lambda: LoggerConfig.set_paused(not self.log_toggle.isChecked()))

        # Export button
        self.action_save = QAction()
        save_icon = QIcon(":resources/icons/icon-save-file-64.svg")
        if not save_icon.isNull():
            self.action_save.setIcon(save_icon)
        else:
            self.action_save.setText("Save")
        self.action_save.setToolTip("Save log to file")

        # Add spacer
        spacer = QSpacerItem(20, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

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

        # Create QTextEdit for logging
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Monaco",10))

        # Create search bar
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Monaco",10))
        self.search_widget = SearchWidget(self.text_edit, self, enable_replace=False, realtime=False)

        toolbar.addAction(self.actionLogToggle)
        toolbar.addSeparator()
        toolbar.addWidget(self.search_widget)
        toolbar.addSeparator()
        toolbar.addAction(self.action_settings)
        toolbar.addAction(self.action_save)
        toolbar.addSeparator()
        toolbar.addAction(self.action_clear)

        logger_layout.addWidget(toolbar)
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
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)

        parent.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self)

        self.visibilityChanged.connect(self.logger_visibility_change)
        self.logger_visibility_change()

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
        sys.stderr = sys.__stderr__
        super().closeEvent(event)

    def write(self, message):
        """Adds message to logger

        Parameters
        ----------
        message : str
            Message to display in logger
        """        
        # check and change text color if necessary
        color = self.detect_color_from_message(message)
        self.text_edit.setTextColor(QColor(color))

        # add message to to text_edit
        self.text_edit.append(message)

        # reset default color
        self.text_edit.setTextColor(QColor("black"))

    def detect_color_from_message(self, message):
        prefix = message.split(" ", 1)[0].rstrip(":")  # Extract prefix like "UI", "DATA", etc.
        for key, color in self.log_colors.items():
            if prefix.lower() == key.lower():
                return color
        return self.default_color()

    def default_color(self):
        palette = self.text_edit.palette()
        bg = palette.color(self.text_edit.backgroundRole()).lightness()
        return "lightgray" if bg < 128 else "black"

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
        dialog = LoggerOptionsDialog(LoggerConfig._options, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            LoggerConfig.set_options(dialog.get_updated_options())


    def logger_visibility_change(self):
        """Redirect stdout based on the visibility of the logger dock."""
        if self.isVisible():
            sys.stdout = self   # Redirect stdout to logger
            sys.stderr = self   # Redirect stderr to logger
        else:
            sys.stdout = sys.__stdout__  # Restore to default stdout    
            sys.stderr = sys.__stderr__  # Restore to default stderr    
    

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

        
        self.setWindowTitle("Customize Logger")
        self.setLayout(QVBoxLayout())

        # Store references to checkboxes and the dictionary
        self.options_dict = options_dict.copy()
        self.checkboxes = {}

        # Create checkboxes based on the dictionary
        self.logger_item_box = QGroupBox()
        self.logger_item_box.setLayout(QGridLayout())
        self.logger_item_box.setContentsMargins(0,0,0,0)
        self.logger_item_box.layout().setContentsMargins(3,3,3,3)
        self.logger_item_box.setTitle("Toggle items")

        self.layout().addWidget(self.logger_item_box)

        num_options = len(self.options_dict)
        nrow = int((num_options * 4) ** 0.5)
        ncol = max(1, (num_options + nrow - 1) // nrow)

        if nrow > 6 * ncol:
            ncol += 1
            nrow = (num_options + ncol - 1) // ncol

        r = 0
        c = 0
        for key, value in self.options_dict.items():
            checkbox = QCheckBox(key)  # The label is set directly here
            checkbox.setChecked(value)  # Set initial state from the dictionary
            self.checkboxes[key] = checkbox
            self.logger_item_box.layout().addWidget(checkbox, r, c)
            r += 1
            if r >= nrow:
                r = 0;
                c = c + 1;

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0,0,0,0)
        self.button_select_all = QToolButton()
        self.button_select_all.setText("✓ All")
        self.button_select_all.setToolTip("Select all options")
        button_layout.addWidget(self.button_select_all)

        self.button_select_none = QToolButton()
        self.button_select_none.setText("✗ None")
        self.button_select_none.setToolTip("Deselect all options")
        button_layout.addWidget(self.button_select_none)

        self.layout().addLayout(button_layout)
        self.button_select_all.clicked.connect(self.select_all_options)
        self.button_select_none.clicked.connect(self.select_none_options)

        self.layout().addSpacing(20)
        self.option_box = QGroupBox()
        self.option_box.setLayout(QGridLayout())
        self.option_box.setContentsMargins(0,0,0,0)
        self.option_box.layout().setContentsMargins(3,3,3,3)
        self.option_box.setTitle("Toggle options")

        self.layout().addWidget(self.option_box)

        self.show_args_checkbox = QCheckBox("Show arguments")
        self.show_args_checkbox.setChecked(LoggerConfig.get_show_args())
        self.show_args_checkbox.toggled.connect(LoggerConfig.set_show_args)
        self.option_box.layout().addWidget(self.show_args_checkbox)

        self.show_chain_checkbox = QCheckBox("Show call chain")
        self.show_chain_checkbox.setChecked(LoggerConfig.get_show_call_chain())
        self.show_chain_checkbox.toggled.connect(LoggerConfig.set_show_call_chain)
        self.option_box.layout().addWidget(self.show_chain_checkbox)

        # Add OK button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        self.layout().addWidget(button_box)
    
    def select_all_options(self):
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)

    def select_none_options(self):
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)


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