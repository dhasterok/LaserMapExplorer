from pathlib import Path
from PyQt6.QtWidgets import QMainWindow, QWidget
import lame_core.config as lame_core_config

_basedir = Path(__file__).resolve().parent.parent.parent
_resource_path = _basedir / 'resources'

lame_core_config.setup(
    basedir=_basedir,
    resource_path=_resource_path,
    appdata_path=_resource_path / 'app_data',
)


def get_top_parent(widget: QWidget):
    """Walks up the parent chain until a QMainWindow or Workflow is found."""
    from src.app.Workflow import Workflow

    w = widget
    while w is not None:
        if isinstance(w, QMainWindow):
            return w
        elif isinstance(w, Workflow):
            return w.bridge.lame_blockly
        w = w.parentWidget()
    return None
