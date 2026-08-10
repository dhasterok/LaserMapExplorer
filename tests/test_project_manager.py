"""Headless integration check for ProjectManager against a real MainWindow.

Run: .venv/bin/python <this file>

Exercises: new/untitled project on first add_samples(), add_samples() pulling
files from TWO different directories into one project (the scenario that
required the initialize_sample_object() path-resolution fix), previous-
selection preservation, save/load round-trip, and close_project() clearing
ui.data/AppData sample state.
"""
import os
import sys
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
from PyQt6.QtWidgets import QMessageBox
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

from src.app.MainWindow import MainWindow

RM01 = Path("/Users/dhasterok/maps/processed data/RM01.lame.csv")
RM02 = project_root / "maps" / "Alex_garnet_maps" / "processed data" / "RM02.lame.csv"

assert RM01.exists(), f"missing fixture: {RM01}"
assert RM02.exists(), f"missing fixture: {RM02}"
assert RM01.parent != RM02.parent, "fixtures must come from different directories for this test to be meaningful"

win = MainWindow(app)
pm = win.project_manager

# --- untitled project created on first add_samples() ---
assert pm.current_project is None
added = pm.add_samples([RM01])
assert added == ['RM01'], added
assert pm.current_project is not None
assert pm.current_project.name == "Untitled Project"
assert pm.current_project.dirty is True
print("PASS: add_samples() with no project open silently creates an untitled project")

# --- adding from a second, different directory ---
added2 = pm.add_samples([RM02])
assert added2 == ['RM02'], added2
assert set(pm.current_project.samples) == {'RM01', 'RM02'}
assert pm.current_project.samples['RM01'].sample_path == RM01.resolve()
assert pm.current_project.samples['RM02'].sample_path == RM02.resolve()
assert win.app_data.sample_list == ['RM01', 'RM02']
print("PASS: add_samples() from a second directory adds without losing the first sample's entry")

# --- re-adding an already-present sample is a safe no-op ---
added_again = pm.add_samples([RM01])
assert added_again == [], added_again
print("PASS: re-adding an already-present sample returns no new IDs")

# --- selecting RM02, then adding more shouldn't jump selection back to RM01 ---
win.app_data.sample_id = 'RM02'
assert win.app_data.sample_id == 'RM02'
pm._sync_app_data_from_project()  # simulate what add_samples() does internally
assert win.app_data.sample_id == 'RM02', "current selection should be preserved across a resync"
print("PASS: current sample selection is preserved when AppData is resynced from the project")

# --- initialize_sample_object() resolves each sample's own absolute path,
#     not directory/csv_files[index] (which only reflects ONE directory) ---
win.app_data.sample_id = 'RM01'
win.change_sample()
assert 'RM01' in win.data, "RM01 should have loaded via initialize_sample_object()"
assert Path(win.data['RM01'].file_path).resolve() == RM01.resolve()

win.app_data.sample_id = 'RM02'
win.change_sample()
assert 'RM02' in win.data, "RM02 should have loaded via initialize_sample_object()"
assert Path(win.data['RM02'].file_path).resolve() == RM02.resolve()
print("PASS: both samples loaded from their own directories despite selected_directory only holding one")

# --- save / load round-trip ---
import tempfile
tmp_dir = Path(tempfile.mkdtemp(prefix='lame_project_manager_test_'))
manifest = tmp_dir / "TestProject.lame_project.json"
pm.save_project(manifest)
assert pm.current_project.dirty is False
assert manifest.exists()
print("PASS: save_project() writes a manifest and clears dirty")

original_sample_ids = set(pm.current_project.samples)
pm.open_project(manifest)
assert set(pm.current_project.samples) == original_sample_ids
assert pm.current_project.dirty is False
assert win.app_data.sample_list and set(win.app_data.sample_list) == original_sample_ids
print("PASS: open_project() reloads the same sample set and resyncs AppData")

# --- close_project() clears ui.data and AppData sample state in place (aliasing) ---
win.app_data.sample_id = 'RM01'
win.change_sample()
assert win.data  # something loaded
data_ref_before = win.data
pm.close_project()
assert pm.current_project is None
assert win.data == {}
assert win.data is data_ref_before, "ui.data must be cleared in place, not reassigned (AppData.data aliases it)"
assert win.app_data.data is win.data, "AppData.data must still be the same object as ui.data after close"
assert win.app_data.sample_list == []
print("PASS: close_project() clears ui.data in place (preserving the AppData alias) and resets sample_list")

# --- recent projects ---
recents = pm.recent_projects()
assert Path(manifest) in recents, recents
print("PASS: recent_projects() includes the just-saved manifest")

print("\nALL ProjectManager INTEGRATION TESTS PASSED")
