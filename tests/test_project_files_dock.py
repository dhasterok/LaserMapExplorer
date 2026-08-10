"""Headless integration check for step 6: ProjectFilesDock.

Run: .venv/bin/python <this file>
"""
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime
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
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

from src.app.MainWindow import MainWindow
from src.project.ProjectModel import (
    SampleCalibration, compute_source_hash, save_calibration_sidecar,
)

RM01_SOURCE = Path("/Users/dhasterok/maps/processed data/RM01.lame.csv")
assert RM01_SOURCE.exists(), f"missing fixture: {RM01_SOURCE}"

tmp_dir = Path(tempfile.mkdtemp(prefix='lame_project_files_dock_test_'))
RM01 = tmp_dir / "RM01.lame.csv"
shutil.copy(RM01_SOURCE, RM01)
RM02_MISSING = tmp_dir / "RM02.lame.csv"
shutil.copy(RM01_SOURCE, RM02_MISSING)

win = MainWindow(app)
pm = win.project_manager

# ------------------------------------------------------------------
# Dock creation + toggle
# ------------------------------------------------------------------
assert not hasattr(win, 'project_files_dock')
win.open_project_files_dock()
assert hasattr(win, 'project_files_dock')
dock = win.project_files_dock
assert dock.isVisible()
assert win.lame_action.ProjectFiles.isChecked()

win.open_project_files_dock()  # second call toggles closed
assert not dock.isVisible()
assert not win.lame_action.ProjectFiles.isChecked()

win.open_project_files_dock()  # toggle back open for the rest of the test
assert dock.isVisible()
print("PASS: open_project_files_dock() creates the dock and toggles visibility/action-checked state")

# ------------------------------------------------------------------
# Empty project -> empty tree
# ------------------------------------------------------------------
assert dock.treeView.root_node.rowCount() == 0
print("PASS: tree is empty with no project open")

# ------------------------------------------------------------------
# Add a calibrated, linked sample -> refresh() driven by projectChanged/dirtyChanged
# ------------------------------------------------------------------
save_calibration_sidecar(RM01, SampleCalibration(
    source_hash=compute_source_hash(RM01),
    calibrated_at=datetime(2026, 6, 14, 12, 0, 0),
    method='LA-ICP-MS standards+drift',
    payload={'standards_used': ['NIST610']},
))
pm.add_samples([RM01])

root = dock.treeView.root_node
assert root.rowCount() == 1, "adding a sample should auto-refresh the dock via projectChanged/dirtyChanged"
branch = root.child(0)
assert branch.data() == 'RM01'
assert '✓ linked' in branch.text(), branch.text()
assert branch.rowCount() == 3, "expected calibration/processing/notes leaves"
leaf_texts = [branch.child(i).text() for i in range(branch.rowCount())]
assert any(t.startswith('calibration: ✓') for t in leaf_texts), leaf_texts
assert 'processing: none' in leaf_texts, leaf_texts
assert 'notes: none' in leaf_texts, leaf_texts
print("PASS: adding a sample auto-refreshes the tree with linked/calibration/processing/notes status")

# ------------------------------------------------------------------
# Filter a loaded sample -> processing status updates live (from SampleObj,
# not the last-saved snapshot)
# ------------------------------------------------------------------
data = win.data['RM01']
analyte = data.processed.match_attribute('data_type', 'Analyte')[0]
data.add_filter(field_type='Analyte', field=analyte, min_val=0.0, max_val=1e9, operator='and', use=True)
dock.refresh()
branch = dock.treeView.root_node.child(0)
leaf_texts = [branch.child(i).text() for i in range(branch.rowCount())]
assert any('1 filter' in t for t in leaf_texts), leaf_texts
print("PASS: processing status reflects the live SampleObj's current filter state, not just the last save")

# ------------------------------------------------------------------
# Calibration staleness surfaces
# ------------------------------------------------------------------
time.sleep(1.1)
RM01.write_text(RM01.read_text() + "\n")
dock.refresh()
branch = dock.treeView.root_node.child(0)
leaf_texts = [branch.child(i).text() for i in range(branch.rowCount())]
assert any('stale' in t for t in leaf_texts), leaf_texts
print("PASS: a touched source file surfaces as a stale calibration in the tree")

# ------------------------------------------------------------------
# Missing sample surfaces as such, with a working Locate... flow
# ------------------------------------------------------------------
pm.add_samples([RM02_MISSING])
RM02_MISSING.unlink()
dock.refresh()
missing_branch = next(
    dock.treeView.root_node.child(i) for i in range(dock.treeView.root_node.rowCount())
    if dock.treeView.root_node.child(i).data() == 'RM02'
)
assert '⚠ missing' in missing_branch.text(), missing_branch.text()

relocated = tmp_dir / "RM02_relocated.lame.csv"
shutil.copy(RM01_SOURCE, relocated)
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(relocated), ''))
dock._locate_sample('RM02')
assert pm.current_project.samples['RM02'].sample_path == relocated.resolve()
dock.refresh()
relocated_branch = next(
    dock.treeView.root_node.child(i) for i in range(dock.treeView.root_node.rowCount())
    if dock.treeView.root_node.child(i).data() == 'RM02'
)
assert '✓ linked' in relocated_branch.text(), relocated_branch.text()
print("PASS: a missing sample is flagged, and Locate... (mocked dialog) fixes it via ProjectManager")

# ------------------------------------------------------------------
# Double-click a sample branch loads it
# ------------------------------------------------------------------
win.app_data.sample_id = ''
win.data.clear()
from PyQt6.QtCore import QModelIndex
index = dock.treeView.treeModel.indexFromItem(dock.treeView.root_node.child(0))
dock.on_double_click(index)
assert win.app_data.sample_id == 'RM01'
assert 'RM01' in win.data
print("PASS: double-clicking a sample branch loads that sample")

# ------------------------------------------------------------------
# Remove from Project
# ------------------------------------------------------------------
dock._remove_sample('RM02')
assert 'RM02' not in pm.current_project.samples
assert dock.treeView.root_node.rowCount() == 1
print("PASS: _remove_sample() removes the sample from the project and refreshes the tree")

shutil.rmtree(tmp_dir, ignore_errors=True)
print("\nALL ProjectFilesDock INTEGRATION TESTS PASSED")
