"""Headless integration check for step 8: Notes relocated to
<project_dir>/<sample_id>/notes.rst, and the profile/polygon persistence
gap closed alongside it.

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
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)

from src.app.MainWindow import MainWindow

RM01_SOURCE = Path("/Users/dhasterok/maps/processed data/RM01.lame.csv")
assert RM01_SOURCE.exists(), f"missing fixture: {RM01_SOURCE}"

tmp_dir = Path(tempfile.mkdtemp(prefix='lame_notes_relocation_test_'))
RM01 = tmp_dir / "RM01.lame.csv"
shutil.copy(RM01_SOURCE, RM01)

win = MainWindow(app)
pm = win.project_manager

# ------------------------------------------------------------------
# Before the project has ever been saved: no project_dir yet, so Notes
# has nowhere to write -- notes_file is None, not the old
# selected_directory-based path.
# ------------------------------------------------------------------
pm.add_samples([RM01])
assert pm.project_dir is None
assert pm.notes_path_for_sample('RM01') is None
win.open_notes()
assert win.notes_dock.notes.notes_file is None
print("PASS: before the project is ever saved, Notes has no file (project_dir doesn't exist yet)")

# ------------------------------------------------------------------
# After saving, project_dir exists and Notes gets a real path under it,
# not the old <selected_directory>/<sample_id>.rst location.
# ------------------------------------------------------------------
manifest = tmp_dir / "NotesTest.lame_project.json"
pm.save_project(manifest)
assert pm.project_dir == manifest.parent / "NotesTest"

expected_notes_path = pm.project_dir / "RM01" / "notes.rst"
assert pm.notes_path_for_sample('RM01') == expected_notes_path
assert expected_notes_path.parent.is_dir(), "notes_path_for_sample() should create the parent directory"

old_style_path = RM01.parent / "RM01.rst"
assert not old_style_path.exists(), "must not fall back to the old selected_directory-based location"
print(f"PASS: after saving, notes_path_for_sample() resolves under project_dir ({expected_notes_path})")

# ------------------------------------------------------------------
# Selecting the sample points the live Notes editor at that path and it
# actually round-trips content to disk.
# ------------------------------------------------------------------
win.app_data.sample_id = 'RM01'
win.change_sample()
assert win.notes_dock.notes.notes_file == expected_notes_path

win.notes_dock.notes.editor.setPlainText("Test notes for RM01.")
win.notes_dock.notes.save_notes_file()
assert expected_notes_path.exists()
assert expected_notes_path.read_text() == "Test notes for RM01."
print("PASS: the live Notes editor is pointed at the relocated path and autosave writes there")

# ------------------------------------------------------------------
# ProjectFilesDock's notes indicator picks up the relocated file (its
# check was written against the OLD location in step 6 -- confirm it was
# updated to match).
# ------------------------------------------------------------------
win.open_project_files_dock()
win.project_files_dock.refresh()
branch = win.project_files_dock.treeView.root_node.child(0)
leaf_texts = [branch.child(i).text() for i in range(branch.rowCount())]
assert 'notes: present' in leaf_texts, leaf_texts
print("PASS: ProjectFilesDock's notes indicator reflects the relocated file")

# ------------------------------------------------------------------
# The profile/polygon persistence gap closed alongside Notes: save_project()
# now actually writes .prfl/.poly sidecars (it silently didn't before).
# ------------------------------------------------------------------
from src.plotting.Profile import Profile as _Profile
win.open_profile()
win.open_mask_dock()
real_profile = _Profile(name='p1', radius=5)
win.profile_dock.profiling.profiles.setdefault('RM01', {})['p1'] = real_profile

pm.save_project(manifest)
prfl_path = pm.project_dir / "RM01" / "p1.prfl"
assert prfl_path.exists(), "save_project() should now persist profiles via Profiling.save_profiles()"
print("PASS: save_project() persists profile sidecars (a gap that predated this step)")

# ------------------------------------------------------------------
# Reloading a sample within an ongoing session picks the profile back up
# from disk via the new initialize_sample_object() load hook.
# ------------------------------------------------------------------
win.data.clear()
win.app_data.sample_id = ''
win.app_data.sample_list = []
win.profile_dock.profiling.profiles.clear()

win.app_data.sample_list = ['RM01']
win.app_data.sample_id = 'RM01'
win.change_sample()
assert 'RM01' in win.data
assert 'p1' in win.profile_dock.profiling.profiles.get('RM01', {}), \
    "initialize_sample_object() should have reloaded this sample's profile from disk"
print("PASS: re-selecting a sample reloads its profile from disk via the new load hook")

shutil.rmtree(tmp_dir, ignore_errors=True)
print("\nALL Notes-relocation INTEGRATION TESTS PASSED")
