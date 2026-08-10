"""Standalone test harness for the Map Import dialog.

Runs ``MapImporter`` outside of the full LaME application so the import
workflow and its GUI can be exercised in isolation, without needing to
launch the main window first.

``MapImporter`` reaches into its parent for exactly one thing: a
``.project_manager.add_samples([path])`` call fired after a successful
import (normally supplied by LaME's ``MainWindow``/``ProjectManager``).
``_StubHost`` below stands in for that, printing what would have happened
instead of loading the result back into LaME.

Usage:
    python tests/test_map_importer.py
"""
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QWidget

# Add the project root (parent of tests/) to sys.path so `src.*` resolves
# regardless of the working directory this script is launched from.
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import src.app.config  # noqa: F401 -- runs lame_core.config.setup()
from src.importers.MapImporter import MapImporter


class _StubProjectManager:
    """Stand-in for ProjectManager, the only thing MapImporter calls on its parent."""

    def add_samples(self, paths):
        print(f"[test harness] import finished successfully, would add_samples: {paths}")
        return []


class _StubHost(QWidget):
    """Stand-in for the LaME MainWindow: a real QWidget (so QDialog parenting works) with a `.project_manager`."""

    def __init__(self):
        super().__init__()
        self.project_manager = _StubProjectManager()


def main():
    app = QApplication(sys.argv)

    host = _StubHost()
    dialog = MapImporter(parent=host)
    dialog.setWindowTitle("Map Import Test Harness")

    result = dialog.exec()

    print(f"[test harness] dialog closed, exec() result={result}, ok={dialog.ok}")
    if dialog.sample_ids:
        print(f"[test harness] root_path={getattr(dialog, 'root_path', None)}")
        print(f"[test harness] sample_ids={dialog.sample_ids}")

    sys.exit(0)


if __name__ == '__main__':
    main()
