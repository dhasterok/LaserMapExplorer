"""Headless integration check for step 7: dirty-check prompt + full
close_project() teardown + MainWindow.closeEvent().

Run: .venv/bin/python <this file>
"""
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
from PyQt6.QtGui import QCloseEvent

RM01_SOURCE = Path("/Users/dhasterok/maps/processed data/RM01.lame.csv")
assert RM01_SOURCE.exists(), f"missing fixture: {RM01_SOURCE}"

tmp_dir = Path(tempfile.mkdtemp(prefix='lame_close_project_test_'))


def make_sample_copy(name):
    p = tmp_dir / f"{name}.lame.csv"
    shutil.copy(RM01_SOURCE, p)
    return p


from src.app.MainWindow import MainWindow

win = MainWindow(app)
pm = win.project_manager

RM01 = make_sample_copy('RM01')

# ------------------------------------------------------------------
# Cancel aborts: nothing is touched
# ------------------------------------------------------------------
pm.add_samples([RM01])
assert pm.current_project.dirty is True

# Open the docks close_project() needs to tear down, so the real branches
# run below -- these assume a sample is already loaded (a pre-existing,
# unrelated requirement of ProfileDock's init), hence opened after add_samples().
win.open_mask_dock()
win.open_profile()
win.open_notes()
data_ref = win.data

QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel)
result = pm.close_project()
assert result is False
assert pm.current_project is not None
assert 'RM01' in win.data
assert win.data is data_ref
print("PASS: Cancel on the dirty-changes prompt aborts close_project() and touches nothing")

# ------------------------------------------------------------------
# Discard proceeds and fully tears down
# ------------------------------------------------------------------
win.app_data.sample_id = 'RM01'
win.change_sample()
data = win.data['RM01']
analyte = data.processed.match_attribute('data_type', 'Analyte')[0]
data.add_filter(field_type='Analyte', field=analyte, min_val=0.0, max_val=1e9, operator='and', use=True)

win.profile_dock.profiling.profiles['RM01'] = {'fake_profile': object()}
win.mask_dock.polygon_tab.polygon_manager.polygons['RM01'] = {1: object()}
win.notes_dock.notes.notes_file = tmp_dir / "RM01.rst"

QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)
result = pm.close_project()
assert result is True
assert pm.current_project is None
assert win.data == {}
assert win.data is data_ref, "ui.data must be cleared in place (AppData.data aliases it)"
assert win.app_data.data is win.data
assert win.app_data.sample_list == []
assert win.profile_dock.profiling.profiles == {}, "add_samples()-only dicts must not leak stale samples"
assert win.profile_dock.profiling.project_dir is None
assert win.mask_dock.polygon_tab.polygon_manager.polygons == {}
assert win.notes_dock.notes.notes_file is None
assert win.lame_action.SelectAnalytes.isEnabled() is False, "toggle_actions(False) should have run"
assert win.windowTitle() == "LaME"
print("PASS: Discard tears down ui.data, profiles, polygons, notes_file, action state, and window title")

# ------------------------------------------------------------------
# Save proceeds: saves first, then tears down
# ------------------------------------------------------------------
RM02 = make_sample_copy('RM02')
pm.add_samples([RM02])
assert pm.current_project.dirty is True
assert "*" in win.windowTitle(), win.windowTitle()  # dirty marker present in the title

manifest = tmp_dir / "SaveOnClose.lame_project.json"
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(manifest), ''))
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Save)
result = pm.close_project()
assert result is True
assert manifest.exists()
assert pm.current_project is None
assert win.data == {}
print("PASS: Save-and-close writes the manifest before tearing down")

# ------------------------------------------------------------------
# new_project()/open_project() respect the dirty check too
# ------------------------------------------------------------------
RM03 = make_sample_copy('RM03')
pm.add_samples([RM03])
original_project = pm.current_project
assert original_project.dirty is True

QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel)
pm.new_project()
assert pm.current_project is original_project, "Cancel on the dirty prompt should abort new_project()"
print("PASS: new_project() aborts on a cancelled dirty-changes prompt, leaving the current project untouched")

QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)
pm.new_project()
assert pm.current_project is not original_project
assert pm.current_project.name == "Untitled Project"
print("PASS: new_project() proceeds once the dirty prompt is answered Discard")

# ------------------------------------------------------------------
# In-session project switching leaves no leakage (open A, close, open B)
# ------------------------------------------------------------------
RM04 = make_sample_copy('RM04')
pm.add_samples([RM04])
# A placeholder profile entry -- close_project()'s teardown (not
# save_profiles(), which expects real Profile objects) is what's under test
# here: does the in-memory dict get cleared on project switch.
win.profile_dock.profiling.profiles.setdefault('RM04', {})['p1'] = object()
assert pm.current_project.dirty is True

QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)
RM05 = make_sample_copy('RM05')
pm.new_project()  # dirty -- prompts, mocked to Discard
pm.add_samples([RM05])
assert 'RM04' not in win.profile_dock.profiling.profiles, "Project A's profile state leaked into Project B"
assert set(pm.current_project.samples) == {'RM05'}
print("PASS: switching projects in one session (A -> close -> B) leaves no leaked per-sample dock state")

# ------------------------------------------------------------------
# closeEvent(): Cancel ignores the close, Discard accepts it
# ------------------------------------------------------------------
RM06 = make_sample_copy('RM06')
pm.add_samples([RM06])
assert pm.current_project.dirty is True

QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel)
event = QCloseEvent()
win.closeEvent(event)
assert not event.isAccepted()
assert pm.current_project is not None
print("PASS: closeEvent() ignores the close when the user cancels the dirty prompt")

QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)
event = QCloseEvent()
win.closeEvent(event)
assert event.isAccepted()
assert pm.current_project is None
print("PASS: closeEvent() accepts the close once the dirty prompt is answered")

shutil.rmtree(tmp_dir, ignore_errors=True)
print("\nALL close_project()/closeEvent() INTEGRATION TESTS PASSED")
