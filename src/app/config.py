from pathlib import Path
from PyQt6.QtWidgets import QMainWindow, QWidget

# __file__ holds the full path to the current Python file
BASEDIR = Path(__file__).resolve().parent.parent.parent

# Path to the resources directory
RESOURCE_PATH = BASEDIR / 'resources'

# Path to app_data directory
APPDATA_PATH = RESOURCE_PATH / 'app_data'

# Path to the icons directory
ICONPATH = RESOURCE_PATH / 'icons'

# Path to the stylesheet directory
STYLE_PATH = RESOURCE_PATH / 'styles'

def load_stylesheet(filename):
    replacements = {
        '{icon_path}': str(ICONPATH.as_posix()),  # Ensure forward slashes
    }
    with open(STYLE_PATH / filename, "r", encoding="utf-8") as file:
        stylesheet = file.read()
    for key, value in replacements.items():
        stylesheet = stylesheet.replace(key, value)
    return stylesheet

def get_top_parent(widget: QWidget):
    """Walks up the parent chain until a QMainWindow or Workspace is found.
    
    Parameters
    ----------
    widget : QWidget
        Widget that the base parent is needed, either MainWindow or Workflow
    """
    from src.app.Workflow import Workflow

    w = widget
    while w is not None:
        if isinstance(w, (QMainWindow)):
            return w
        elif isinstance(w, (Workflow)):
            return w.bridge.lame_blockly
        w = w.parentWidget()
    return None  # fallback if nothing found