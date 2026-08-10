"""Headless integration check for step 5: File menu/toolbar restructuring.

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

QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

def _fail_on_warning(*a, **k):
    raise AssertionError(f"QMessageBox.warning should not be called here: args={a}")

from src.app.MainWindow import MainWindow

RM01_SOURCE = Path("/Users/dhasterok/maps/processed data/RM01.lame.csv")
assert RM01_SOURCE.exists(), f"missing fixture: {RM01_SOURCE}"

tmp_dir = Path(tempfile.mkdtemp(prefix='lame_menu_wiring_test_'))
sample_dir = tmp_dir / "samples"
sample_dir.mkdir()
RM01 = sample_dir / "RM01.lame.csv"
shutil.copy(RM01_SOURCE, RM01)

win = MainWindow(app)
pm = win.project_manager

# ------------------------------------------------------------------
# Actions exist with expected object names
# ------------------------------------------------------------------
expected = {
    'NewProject': 'actionNewProject',
    'OpenProject': 'actionOpenProject',
    'AddSampleFiles': 'actionAddSampleFiles',
    'AddSampleDirectory': 'actionAddSampleDirectory',
    'SaveProject': 'actionSaveProject',
    'SaveProjectAs': 'actionSaveProjectAs',
    'CloseProject': 'actionCloseProject',
}
for attr, object_name in expected.items():
    action = getattr(win.lame_action, attr)
    assert action.objectName() == object_name, f"{attr}.objectName() == {action.objectName()!r}"
assert not hasattr(win.lame_action, 'OpenSample'), "OpenSample should have been renamed to AddSampleFiles"
assert not hasattr(win.lame_action, 'OpenDirectory'), "OpenDirectory should have been renamed to AddSampleDirectory"
print("PASS: all new/renamed project actions exist with expected object names, old names are gone")

# ------------------------------------------------------------------
# menuFile contains the new actions; Recent Projects submenu exists
# ------------------------------------------------------------------
file_menu_actions = {a.objectName() for a in win.menu_bar.menuFile.actions() if a.objectName()}
for object_name in expected.values():
    assert object_name in file_menu_actions, f"{object_name} missing from menuFile"
assert hasattr(win.menu_bar, 'menuRecentProjects')
print("PASS: menuFile contains all project actions and a Recent Projects submenu")

# ------------------------------------------------------------------
# NewProject action -> ProjectManager.new_project()
# ------------------------------------------------------------------
assert pm.current_project is None
win.lame_action.NewProject.trigger()
assert pm.current_project is not None
assert pm.current_project.name == "Untitled Project"
print("PASS: triggering the NewProject action creates an untitled project via ProjectManager")

# ------------------------------------------------------------------
# AddSampleFiles action -> file dialog -> add_samples()
# ------------------------------------------------------------------
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([str(RM01)], ''))
win.lame_action.AddSampleFiles.trigger()
assert 'RM01' in pm.current_project.samples
print("PASS: triggering AddSampleFiles (with a mocked file dialog) adds the sample via ProjectManager")

# ------------------------------------------------------------------
# AddSampleDirectory action -> directory dialog -> add_samples()
# (re-adding the same directory should be a safe no-op, not a duplicate/error)
# ------------------------------------------------------------------
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: str(sample_dir))
win.lame_action.AddSampleDirectory.trigger()
assert list(pm.current_project.samples.keys()) == ['RM01']
print("PASS: triggering AddSampleDirectory (with a mocked directory dialog) works and re-adding is a no-op")

# ------------------------------------------------------------------
# Sample-switch no longer prompts to save (dirty-tracking is project-scoped)
# ------------------------------------------------------------------
QMessageBox.warning = staticmethod(_fail_on_warning)
win.app_data.sample_id = 'RM01'
win.change_sample()
win.toolbar.comboBoxSampleId.setCurrentText('RM01')
win.toolbar.update_sample_id()  # same sample -- should just no-op, must not raise
print("PASS: update_sample_id() no longer pops a save prompt")

# ------------------------------------------------------------------
# Recent Projects submenu populates from ProjectManager.recent_projects()
# ------------------------------------------------------------------
manifest = tmp_dir / "MenuWiringTest.lame_project.json"
pm.save_project(manifest)
win.menu_bar._refresh_recent_projects_menu(win)
recent_actions = win.menu_bar.menuRecentProjects.actions()
assert any(a.text() == manifest.stem for a in recent_actions), [a.text() for a in recent_actions]
print("PASS: Recent Projects submenu populates with the just-saved project")

# triggering the recent-project entry reopens it
pm.close_project()
assert pm.current_project is None
target_action = next(a for a in win.menu_bar.menuRecentProjects.actions() if a.text() == manifest.stem)
target_action.trigger()
assert pm.current_project is not None
assert 'RM01' in pm.current_project.samples
print("PASS: triggering a Recent Projects entry reopens that project")

shutil.rmtree(tmp_dir, ignore_errors=True)
print("\nALL menu-wiring INTEGRATION TESTS PASSED")
