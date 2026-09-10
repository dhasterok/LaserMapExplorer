from pathlib import Path
from PyQt6.QtWidgets import QMainWindow, QWidget
import lame_core.config as lame_core_config

# In a frozen (PyInstaller one-dir) build this resolves to the bundle root, so the
# spec must place `resources/` there for these paths to keep working -- see
# packaging/LaME.spec. `src/calibration/{massbias,dock_widgets}.py` climb `__file__`
# to reach `resources/` the same way and rely on the same invariant.
_basedir = Path(__file__).resolve().parent.parent.parent
_resource_path = _basedir / 'resources'

lame_core_config.setup(
    basedir=_basedir,
    resource_path=_resource_path,
    appdata_path=_resource_path / 'app_data',
    # Anything written at runtime goes here: the installation directory is
    # read-only once the app is frozen and installed.
    userdata_path=lame_core_config.default_user_data_dir('LaME'),
)


def get_top_parent(widget: QWidget):
    """Walks up the parent chain until a QMainWindow or Workflow is found."""
    from src.workflow.Workflow import Workflow

    w = widget
    while w is not None:
        if isinstance(w, QMainWindow):
            return w
        elif isinstance(w, Workflow):
            return w.bridge.lame_blockly
        w = w.parentWidget()
    return None
