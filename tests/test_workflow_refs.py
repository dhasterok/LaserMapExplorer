"""Headless integration check for step 10: Project.workflow_refs round-trips
through save/close/reopen, mirroring AppData.active_workflow_file (a list of
0 or 1 entries, not a history).

Run: .venv/bin/python <this file>
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

project_root = Path("/Users/dhasterok/Documents/GitHub/LaserMapExplorer")
assert (project_root / 'src' / 'app' / 'MainWindow.py').exists()
sys.path.insert(0, str(project_root))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

app = QApplication(sys.argv)

import src.app.config  # noqa: F401 -- runs lame_core.config.setup()
from PyQt6.QtWidgets import QMessageBox, QFileDialog
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)

from src.app.MainWindow import MainWindow

RM01_SOURCE = Path("/Users/dhasterok/maps/processed data/RM01.lame.csv")
assert RM01_SOURCE.exists(), f"missing fixture: {RM01_SOURCE}"

tmp_dir = Path(tempfile.mkdtemp(prefix='lame_workflow_refs_test_'))
RM01 = tmp_dir / "RM01.lame.csv"
shutil.copy(RM01_SOURCE, RM01)

win = MainWindow(app)
pm = win.project_manager

# ------------------------------------------------------------------
# No active workflow -> workflow_refs saves as an empty list
# ------------------------------------------------------------------
pm.add_samples([RM01])
manifest = tmp_dir / "NoWorkflow.lame_project.json"
pm.save_project(manifest)
payload = json.loads(manifest.read_text())
assert payload['workflow_refs'] == []
print("PASS: with no active workflow file, workflow_refs saves as an empty list")

# ------------------------------------------------------------------
# Linking a workflow file marks the project dirty and gets captured on save
# ------------------------------------------------------------------
workflow_path = tmp_dir / "hpe_correction.json"
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(workflow_path), ''))
pm.save_project(manifest)  # clear dirty from add_samples() first
assert pm.current_project.dirty is False

win.new_workflow()
assert win.app_data.active_workflow_file == workflow_path
assert pm.current_project.dirty is True, "linking a new workflow file should mark the project dirty"
print("PASS: linking a new workflow file (new_workflow()) marks the project dirty")

pm.save_project(manifest)
payload = json.loads(manifest.read_text())
assert payload['workflow_refs'] == ['hpe_correction.json'], payload['workflow_refs']
print("PASS: save_project() captures the active workflow file into workflow_refs (relative path)")

# ------------------------------------------------------------------
# Close and reopen: the workflow link is restored, and doing so does NOT
# itself mark the freshly-reopened project dirty
# ------------------------------------------------------------------
pm.close_project()
assert win.app_data.active_workflow_file is None

pm.open_project(manifest)
# load_project() resolves paths (symlink-correctness, see ProjectModel.py) --
# compare against the resolved form, matching this project's established
# path-comparison convention in other tests.
assert win.app_data.active_workflow_file == workflow_path.resolve()
assert pm.current_project.workflow_refs == [workflow_path.resolve()]
assert pm.current_project.dirty is False, "restoring an existing workflow link on open must not mark dirty"
print("PASS: reopening the project restores the workflow link without marking it dirty")

# ------------------------------------------------------------------
# Closing the workflow file (without closing the project) marks dirty and
# is reflected as an empty list on the next save
# ------------------------------------------------------------------
win.close_workflow_file()
assert win.app_data.active_workflow_file is None
assert pm.current_project.dirty is True, "detaching the workflow file should mark the project dirty"

pm.save_project(manifest)
payload = json.loads(manifest.read_text())
assert payload['workflow_refs'] == []
print("PASS: closing the workflow file marks dirty, and the next save records an empty workflow_refs")

# ------------------------------------------------------------------
# Sanity: calling close_workflow_file() with nothing active is a no-op,
# not a spurious dirty mark
# ------------------------------------------------------------------
pm.save_project(manifest)
assert pm.current_project.dirty is False
win.close_workflow_file()
assert pm.current_project.dirty is False, "closing an already-inactive workflow must not mark dirty"
print("PASS: close_workflow_file() is a no-op (no dirty mark) when nothing was active")

shutil.rmtree(tmp_dir, ignore_errors=True)
print("\nALL workflow_refs INTEGRATION TESTS PASSED")
