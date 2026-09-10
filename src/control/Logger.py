"""
Created on Tues July 8 13:30 2025

@author: Derrick Hasterok (Adelaide University)

*Logger Module for PyQt6 Applications**

This module provides a flexible logging system for PyQt6 GUI applications, featuring:

- A dockable logger UI (`LoggerDock`)
- Function and class decorators for automatic logging
- Optional logging of function arguments and call chains
- Toggle switches and UI controls for filtering and managing output
- Customizable color-coded prefixes (e.g., 'UI', 'Error', 'Warning')
- Runtime log control through a `LoggerOptionsDialog`

*BASIC USAGE EXAMPLES*

1. *Log Function Calls with Arguments:*

    .. code-block:: python

        from src.common.Logger import log_call

        @log_call("UI")
        def button_clicked():
            print("Button was clicked")

2. *Log All Methods in a Class:*

    .. code-block:: python
        
        from src.common.Logger import auto_log_methods

        @auto_log_methods("Data")
        class MyModel:
            def load_data(self):
                pass

            def save_data(self):
                pass
        
3. *Exclude Specific Methods:*

    .. code-block:: python

        from src.common.Logger import no_log

        class MyClass:
            @no_log
            def helper(self):
                pass

4. *Add LoggerDock in Your QMainWindow:*

    .. code-block:: python

        self.logger_options = {"UI": True, "Data": False}
        self.logger_dock = LoggerDock(parent=self)

5. *Customize Log Colors (optional):*

    .. code-block:: python

        self.log_colors = {"Data": "teal", "CustomTag": "#ffaa00"}

**LOGGER OPTIONS / DOCK USER INTERFACE**

- Pause/resume toggle: Temporarily stop or resume log output.
- Search bar: Filter visible log messages.
- Gear icon: Opens LoggerOptionsDialog to enable/disable log keys and options.
- Save icon: Exports log to file (default "temp.log").
- Clear icon: Clears current log view.

**QUIET BY DEFAULT / VERBOSE MODE**

The application is silent by default: tracing produced by ``@log_call`` and
``@auto_log_methods`` is discarded unless a sink is listening. There are two sinks:

- **Verbose mode** -- start the app with ``python main.py --verbose`` (or ``-v``)
  to stream tracing to the terminal. Restrict it to particular categories with
  ``--verbose Data,Plot``.
- **LoggerDock** -- opening the dock at runtime turns capture on regardless of
  how the app was started, and closing it turns capture back off.

Messages prefixed ``Error`` or ``Warning`` always reach the terminal (via stderr),
even when quiet, so genuine failures are never hidden.

Keeping this gate cheap matters: these decorators wrap every method of ~50 classes,
so ``log_call`` checks ``LoggerConfig.is_active()`` (a single attribute read) before
doing any frame inspection.

**LOGGERCONFIG OPTIONS (GLOBAL FLAGS)**

- `LoggerConfig` stores persistent settings accessible globally across the app.
- `LoggerConfig.set_verbose(True)`: Stream logs to the terminal
- `LoggerConfig.set_category_filter(["Data"])`: Limit logging to given categories
- `LoggerConfig.set_show_args(True)`: Print function arguments
- `LoggerConfig.set_show_call_chain(True)`: Show simplified call stack
- `LoggerConfig.set_paused(True)`: Suppress all logging output

To update all logger keys at runtime::

    LoggerConfig.set_options({"UI": True, "Data": False, "Custom": True})

**EXTENDING LOGGER BEHAVIOR**

To support more complex behaviors (e.g. conditional prefixes, advanced color mapping),
subclass LoggerDock or modify:
- `LoggerDock.detect_color_from_message(msg)`
- `LoggerConfig` to store more global flags
- `auto_log_methods()` to wrap only specific method names

**RECOMMENDED STRUCTURE**

- Attach LoggerDock to your QMainWindow
- Set `self.logger_options` and optionally `self.log_colors`
- Use `@log_call` or `@auto_log_methods` on key components, skipping any functions with `@no_log`
- Enable/disable features at runtime with `LoggerConfig`
- Export or clear logs using the built-in toolbar

*COMMON ERROR: Missing `*args`/`**kwargs`*
- If a decorated function causes a crash like:
    `TypeError: wrapper() takes N positional arguments but M were given`
- Ensure the original function accepts *args and **kwargs::

    @log_call("UI")
    def your_function(*args, **kwargs):
        ...
"""
import sys, functools, inspect, types
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QtMsgType, qInstallMessageHandler
from PyQt6.QtWidgets import (
        QMainWindow, QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
        QToolBar, QSpacerItem, QSizePolicy, QDialog, QCheckBox, QDialogButtonBox, QToolButton, QWidgetAction
    )
from PyQt6.QtGui import QFont, QColor

from lame_core.CustomWidgets import CustomDockWidget, CustomAction, ToggleSwitch
from lame_core.SearchTool import SearchWidget
from lame_core.applog import set_log_handler

_global_logger = None

def set_global_logger(logger):
    """
    Set the global logger instance.

    Parameters
    ----------
    logger : object
        An object with a `write(str)` method used to handle log output.
        Typically, this could be a file-like object or a custom logger.
    """
    global _global_logger
    _global_logger = logger

def get_global_logger():
    """
    Retrieve the global logger instance.

    Returns
    -------
    object
        The global logger previously set by `set_global_logger()`.
    """
    return _global_logger

# Prefixes that always reach the user, even when logging is quiet or paused.
# These indicate something actually went wrong rather than routine tracing.
_ALWAYS_SHOW = ('error', 'warning')


def _emit(text, error=False):
    """Send an already-formatted message to the active log sink.

    The LoggerDock takes precedence while it is visible; otherwise the message
    goes to the terminal.
    """
    logger = get_global_logger()
    if logger is not None and LoggerConfig.sink_active() and hasattr(logger, 'write'):
        logger.write(text)
        return
    print(text, file=sys.stderr if error else sys.stdout)


def log(msg, prefix=""):
    """
    Write a log message using the global logger, respecting pause state and formatting.

    Parameters
    ----------
    msg : str
        The message to be logged.

    prefix : str, optional
        A label to prepend to the message, typically representing a module or category.
        If provided, it is formatted as 'PREFIX: '.

    Notes
    -----
    Messages prefixed 'Error' or 'Warning' are always emitted (to stderr), even when
    logging is paused or quiet -- they report real failures rather than tracing.

    All other messages are suppressed unless a sink is active: either verbose mode
    (``--verbose`` on the command line) or a visible LoggerDock. This keeps the
    terminal clean by default.
    """
    prefix_key = prefix.strip().rstrip(':').lower()
    text = f"{prefix}: {msg}" if prefix else f"{msg}"

    if prefix_key in _ALWAYS_SHOW:
        _emit(text, error=True)
        return

    if LoggerConfig.is_paused() or not LoggerConfig.is_active():
        return

    # Honour the category toggles (settings dialog / --verbose Data,Plot) when the
    # prefix names a known category. Unknown prefixes are always allowed through.
    if prefix:
        options = LoggerConfig.get_all()
        for key in options:
            if key.strip().lower() == prefix_key and not options[key]:
                return

    _emit(text, error=False)


# lame_core and the sibling widget libraries sit below the app in the dependency
# graph and cannot import this module, so they log through lame_core.applog.
# Registering here routes their messages through the same gate.
set_log_handler(log)


def install_qt_message_handler():
    """
    Route Qt's own C++-level messages through the logger.

    Qt writes warnings such as "QLayout: Attempting to add QLayout ..." straight to
    stderr, bypassing Python entirely. This handler folds them into the same quiet
    -by-default policy: Qt warnings and info are shown only in verbose mode, while
    critical and fatal messages always surface.

    Call once at startup, before the QApplication is created.
    """
    def handler(mode, context, message):
        if mode in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            log(message, prefix="Error")
        elif mode == QtMsgType.QtWarningMsg:
            # Qt warnings are mostly harmless layout/platform chatter, so they are
            # treated as tracing rather than as the always-shown 'Warning' category.
            log(message, prefix="Qt")
        else:
            log(message, prefix="Qt")

    qInstallMessageHandler(handler)

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

    Examples
    --------

    .. code-block:: python

        from src.common.Logger import log_call

        @log_call("UI")
        def button_clicked():
            print("Button was clicked")

    """    
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Fast path: when no sink is active (the default -- quiet terminal, no
            # visible LoggerDock) do nothing but call through. This must stay ahead
            # of any frame inspection: these wrappers sit on every method of ~50
            # classes, so anything expensive here is paid on every call in the app.
            if not LoggerConfig.is_active():
                return func(*args, **kwargs)

            # Category is disabled -> nothing to report for this call.
            if logger_key and not LoggerConfig.get_option(logger_key):
                return func(*args, **kwargs)

            # Per-instance override, if the owning object carries its own toggles.
            self_obj = args[0] if args else None
            if logger_key and self_obj is not None and hasattr(self_obj, 'logger_options'):
                if not self_obj.logger_options.get(logger_key, False):
                    return func(*args, **kwargs)

            # Walk the stack directly rather than via inspect.stack(), which
            # materialises the *entire* stack and reads source files for context
            # lines. Every call passes through a signature-preserving shim first
            # (see _make_signature_preserving_shim), so skip those frames to find
            # the real caller.
            try:
                frame = sys._getframe(1)
            except ValueError:
                frame = None
            while frame is not None and frame.f_code.co_name == '__log_call_shim__':
                frame = frame.f_back

            # Skip logging if the caller is another wrapper (nested decorated call).
            if frame is not None and frame.f_code.co_name == 'wrapper':
                return func(*args, **kwargs)

            prefix = logger_key.upper() if logger_key else ""
            func_name = func.__qualname__
            caller = frame.f_code.co_name if frame is not None else ""
            parts = [f"{prefix}: [{caller} → {func_name}]"]

            if LoggerConfig.get_show_args():
                arg_list = [describe_arg(arg) for arg in args]
                kwarg_list = [f"{k}={describe_arg(v)}" for k, v in kwargs.items()]
                parts.append("args=[" + ", ".join(arg_list + kwarg_list) + "]")

            if LoggerConfig.get_show_call_chain():
                names = []
                f = frame
                while f is not None and len(names) < 4:
                    if f.f_code.co_name != '__log_call_shim__':
                        names.append(f.f_code.co_name)
                    f = f.f_back
                parts.append("chain:/ " + " → ".join(reversed(names)))

            log(" | ".join(parts))
            return func(*args, **kwargs)
        return _make_signature_preserving_shim(func, wrapper)
    return decorator


def _make_signature_preserving_shim(func, impl):
    """Build a wrapper that calls ``impl(*args, **kwargs)`` but exposes the exact
    same call signature as ``func``.

    Qt's signal/slot connection mechanism decides how much of a signal's payload
    to hand to a slot by inspecting the callable's *raw* argument count -- it does
    not use ``inspect.signature`` and does not follow ``functools.wraps``'s
    ``__wrapped__`` chain. A generic ``(*args, **kwargs)`` wrapper therefore always
    looks like "accepts anything", so Qt passes the signal's full payload straight
    through -- which then blows up inside a slot that doesn't actually take those
    extra arguments (e.g. connecting a checkable QAction's ``triggered(bool)``
    directly to a no-argument method). Regenerating a real function with ``func``'s
    exact parameter list restores Qt's normal arg-trimming behavior, without
    requiring every call site to remember to wrap decorated slots in a lambda.
    """
    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        # No inspectable signature (e.g. some builtins) -- fall back to a plain
        # pass-through wrapper; direct-connect trimming won't work for these,
        # but they're not the case this exists to fix.
        return functools.wraps(func)(lambda *args, **kwargs: impl(*args, **kwargs))

    def_parts = []
    call_parts = []
    namespace = {'__impl__': impl}
    for i, p in enumerate(sig.parameters.values()):
        default_name = f'__default_{i}__'
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD):
            def_parts.append(p.name if p.default is p.empty else f'{p.name}={default_name}')
            call_parts.append(p.name)
        elif p.kind is p.VAR_POSITIONAL:
            def_parts.append(f'*{p.name}')
            call_parts.append(f'*{p.name}')
        elif p.kind is p.KEYWORD_ONLY:
            def_parts.append(p.name if p.default is p.empty else f'{p.name}={default_name}')
            call_parts.append(f'{p.name}={p.name}')
        elif p.kind is p.VAR_KEYWORD:
            def_parts.append(f'**{p.name}')
            call_parts.append(f'**{p.name}')

        if p.default is not p.empty:
            namespace[default_name] = p.default

    src = f"def __log_call_shim__({', '.join(def_parts)}):\n    return __impl__({', '.join(call_parts)})\n"
    exec(src, namespace)
    shim = namespace['__log_call_shim__']
    return functools.wraps(func)(shim)

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

def auto_log_methods(logger_key: str, **log_options):
    """Decorator that wraps all methods in a class   

    Parameters
    ----------
    logger_key : str, optional
        key into dict logger_options, by default None

    Examples
    --------

    .. code-block:: python
        
        from src.common.Logger import auto_log_methods

        @auto_log_methods("Data")
        class MyModel:
            def load_data(self):
                pass

            def save_data(self):
                pass
        
    """    
    def decorator(cls):
        for attr_name in dir(cls):
            if attr_name.startswith("__"):
                continue

            attr = getattr(cls, attr_name)
            if not isinstance(attr, types.FunctionType):
                continue  # Skip non-function attributes

            if getattr(attr, "_no_log", False):
                continue

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

    Examples
    --------

    .. code-block:: python

        from src.common.Logger import no_log

        class MyClass:
            @no_log
            def helper(self):
                pass        
    """
    func._no_log = True
    return func

class LoggerConfig:
    """
    Central configuration manager for logging behavior within the application.

    This class provides global settings for controlling what gets logged and how logging is displayed.
    It includes toggles for enabling or disabling logging for specific keys (e.g., class or method names),
    as well as global flags for displaying method arguments, call chains, and for pausing logging entirely.

    Class Attributes
    ----------------
    _options : dict
        A dictionary mapping logger keys (typically strings identifying classes or methods)
        to booleans indicating whether logging is enabled for that key.
    _show_args : bool
        Flag indicating whether function arguments should be printed in logs.
    _show_call_chain : bool
        Flag indicating whether to include the call chain (stack trace) in log messages.
    _paused : bool
        If True, logging is globally paused.

    Methods
    -------
    set_options(options_dict: dict)
        Set the entire logging options dictionary.
    
    get_option(key: str) -> bool
        Retrieve whether logging is enabled for the given key.
    
    get_all() -> dict
        Return the entire logging options dictionary.
    
    set_show_args(value: bool)
        Enable or disable logging of function arguments.
    
    get_show_args() -> bool
        Return whether function arguments will be logged.
    
    set_show_call_chain(value: bool)
        Enable or disable logging of call chains.
    
    get_show_call_chain() -> bool
        Return whether call chains will be logged.
    
    set_paused(value: bool)
        Pause or resume all logging globally.
    
    is_paused() -> bool
        Return whether logging is currently paused.
    """
    # _options is used to set flags for the logged items (classes/methods)
    _options = {}

    # log arguments/call chain
    _show_args = True
    _show_call_chain = False

    # to pause the logging
    _paused = False

    # verbose mode: emit tracing to the terminal (enabled with --verbose)
    _verbose = False

    # True while a LoggerDock is visible and capturing output
    _sink_active = False

    # Cached result of "is anything listening?" -- read on every decorated call,
    # so it is kept as a plain attribute rather than recomputed each time.
    _active = False

    # Restricts which categories are enabled, e.g. --verbose=Data,Plot.
    # None means no restriction.
    _category_filter = None

    @classmethod
    def _recompute_active(cls):
        cls._active = (not cls._paused) and (cls._verbose or cls._sink_active)

    @classmethod
    def is_active(cls):
        """Return True if any sink (verbose terminal or visible dock) wants log output."""
        return cls._active

    @classmethod
    def set_verbose(cls, value: bool):
        """Enable or disable tracing output to the terminal."""
        cls._verbose = bool(value)
        cls._recompute_active()

    @classmethod
    def is_verbose(cls):
        return cls._verbose

    @classmethod
    def set_sink_active(cls, value: bool):
        """Record whether a LoggerDock is currently visible and capturing output."""
        cls._sink_active = bool(value)
        cls._recompute_active()

    @classmethod
    def sink_active(cls):
        return cls._sink_active

    @classmethod
    def set_category_filter(cls, categories):
        """Restrict logging to the named categories.

        Parameters
        ----------
        categories : iterable of str or None
            Category names to keep enabled. None removes the restriction.
            'Error' and 'Warning' are always retained.
        """
        if categories:
            cls._category_filter = {str(c).strip().lower() for c in categories}
            cls._category_filter.update(_ALWAYS_SHOW)
        else:
            cls._category_filter = None
        cls._apply_category_filter()

    @classmethod
    def _apply_category_filter(cls):
        if cls._category_filter is None:
            return
        for key in cls._options:
            cls._options[key] = key.strip().lower() in cls._category_filter

    @classmethod
    def set_options(cls, options_dict):
        cls._options = dict(options_dict)
        cls._apply_category_filter()

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
        cls._recompute_active()

class LoggerDock(CustomDockWidget):
    """
    A dockable widget that displays logging messages for debugging and runtime diagnostics.

    This dock is designed to be embedded in a `QMainWindow` and provides:
      - A read-only, color-coded log display
      - A toolbar with controls for search, pause/resume, export, and clear actions
      - Integration with the `LoggerConfig` system for customizable output
      - Optional settings dialog to toggle which keys/categories are logged

    It expects the parent QMainWindow to provide:
      - `logger_options` (dict[str, bool]): Key-based toggles for logging categories.
      - Optionally `log_colors` (dict[str, str]): Hex or named color values for message prefixes.

    Parameters
    ----------
    file : str
        The filename to which the log is saved when exported (default: 'temp.log').
    parent : QMainWindow
        The main window instance that this logger is attached to. Must be a `QMainWindow`.

    Examples
    --------

    .. code-block:: python

        self.logger_options = {"UI": True, "Data": False}
        self.logger_dock = LoggerDock(file="session.log", parent=self)
        self.logger_dock.log_colors = {"Data": "teal", "CustomTag": "#ffaa00"}

    :see also: SearchTool : Adds text search widget to the dock
    ```
    """  
    def __init__(self, file: Path | str='temp.log', parent=None):
        if not isinstance(parent, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        super().__init__(parent)
        self.ui = parent
        self.file = Path(file).resolve()

        self.log_colors = {
            "Error": "red",
            "Warning": "orange",
            "UI": "blue",
            "Data": "green",
        }
        if hasattr(self.ui, 'log_colors'):
            self.log_colors.update(self.ui.log_colors)

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
        self.action_save = CustomAction(
            text="Save",
            light_icon_unchecked="icon-save-file-64.svg",
            parent=toolbar,
        )
        self.action_save.setToolTip("Save log to file")

        # Add spacer
        spacer = QSpacerItem(20, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        if hasattr(self.ui,'logger_options'):
            self.action_settings = CustomAction(
                text="Settings",
                light_icon_unchecked="icon-gear-64.svg",
                dark_icon_unchecked="icons-gear-dark-64.svg",
                parent=toolbar,
            )
            self.action_settings.setToolTip("Logger settings")

        self.action_clear = CustomAction(
            text="Clear",
            light_icon_unchecked="icon-delete-64.svg",
            dark_icon_unchecked="icon-delete-dark-64.svg",
            parent=toolbar,
        )
        self.action_clear.setToolTip("Clear log")

        # Create QTextEdit for logging
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Monaco",10))

        # Create search bar
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

        self.ui.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self)

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
        LoggerConfig.set_sink_active(False)
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
        """Determines the color for the message text

        Determines the message color from the prefix.

        Parameters
        ----------
        message : str
            Log message with prefix.

        Returns
        -------
        str
            Returns a hex string with the color
        """
        prefix = message.split(" ", 1)[0].rstrip(":")  # Extract prefix like "UI", "DATA", etc.
        for key, color in self.log_colors.items():
            if prefix.lower() == key.lower():
                return color
        return self.default_color()

    def default_color(self):
        """Sets default color for text in the LoggerDock"""
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
                log(f"Log exported to: {self.log_file}", prefix="Warning")
            except Exception as e:
                log(f"Failed to export log: {e}", prefix="Error")
        else:
            log("No log contents to export.", prefix="Warning")

    def set_logger_options(self):
        """ Opens a dialog to edit logger options."""
        dialog = LoggerOptionsDialog(LoggerConfig._options, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            LoggerConfig.set_options(dialog.get_updated_options())


    def logger_visibility_change(self):
        """Redirect stdout and enable log capture based on the dock's visibility.

        While the dock is visible it becomes the active log sink, so tracing is
        collected here even when the app was not started with ``--verbose``.
        """
        visible = self.isVisible()
        LoggerConfig.set_sink_active(visible)
        if visible:
            sys.stdout = self   # Redirect stdout to logger
            sys.stderr = self   # Redirect stderr to logger
        else:
            sys.stdout = sys.__stdout__  # Restore to default stdout
            sys.stderr = sys.__stderr__  # Restore to default stderr
    

class LoggerOptionsDialog(QDialog):
    """
    A dialog that allows users to enable or disable individual logging keys
    and adjust logging behavior options.

    This dialog supports:
    - Displaying checkboxes for all logger keys passed via `options_dict`
    - Selecting or deselecting all options with tool buttons
    - Toggles for global logger behaviors:
        * Show method/function arguments in logs
        * Show call chain (stack trace context)

    Typically invoked from the logger toolbar via the gear/settings icon.

    Parameters
    ----------
    options_dict : dict[str, bool]
        Dictionary of logger keys and their current enabled/disabled state.
    parent : QWidget or LoggerDock, optional
        MainWindow for the dialog.

    Examples
    --------

    .. code-block:: python
    
        dialog = LoggerOptionsDialog(LoggerConfig.get_all(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            LoggerConfig.set_options(dialog.get_updated_options())

    See Also
    --------
    LoggerConfig : Stores and retrieves global logging configuration.
    LoggerDock : The main dockable UI that displays logs.
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
        """Select all checkboxes for logger options"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)

    def select_none_options(self):
        """Deselect all checkboxes for logger options"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)


    def get_updated_options(self):
        """Updates the dictionary with the current state of checkboxes and returns it.

        Returns
        -------
        dict
            Returns the dictionary of boolean logger options
        """
        for key, checkbox in self.checkboxes.items():
            self.options_dict[key] = checkbox.isChecked()
        return self.options_dict