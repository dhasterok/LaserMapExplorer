"""Headless integration check for step 9: MapImporter's post-import success
handler chains into ProjectManager.add_samples(), not the old dead
LameIO.open_directory() path.

Rather than driving MapImporter's full raw-instrument-data pipeline (a lot
of unrelated setup -- data_type/method dispatch, standards config, real
LA-ICP-MS files), this drives the real import_data() method with the two
data-reading calls it makes (get_metadata(), import_la_icp_ms_data())
monkeypatched to a no-op that sets exactly what a real successful import
would (self.ok, self.sample_ids, self.root_path) -- the tail logic under
test (evict stale cache -> add_samples() -> reload if selected) then runs
completely unmodified, exactly as shipped.

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
from PyQt6.QtWidgets import QMessageBox
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)

from src.app.MainWindow import MainWindow
from src.importers.MapImporter import MapImporter

RM01_SOURCE = Path("/Users/dhasterok/maps/processed data/RM01.lame.csv")
assert RM01_SOURCE.exists(), f"missing fixture: {RM01_SOURCE}"

tmp_dir = Path(tempfile.mkdtemp(prefix='lame_import_chaining_test_'))
RM01 = tmp_dir / "RM01.lame.csv"
shutil.copy(RM01_SOURCE, RM01)

win = MainWindow(app)
pm = win.project_manager


def make_importer():
    """A real MapImporter, with the two data-reading calls a real successful
    import would make stubbed to simulate "already imported to tmp_dir".
    """
    dlg = MapImporter(parent=win)
    dlg.comboBoxDataType.setCurrentText('LA-ICP-MS')
    dlg.checkBoxSaveToRoot.setChecked(True)
    dlg.root_path = tmp_dir
    dlg.get_metadata = lambda: {}
    dlg.import_la_icp_ms_data = lambda save_path: (
        setattr(dlg, 'ok', True),
        setattr(dlg, 'sample_ids', ['RM01']),
    )
    return dlg


# ------------------------------------------------------------------
# A fresh import adds the sample to the current project via ProjectManager
# ------------------------------------------------------------------
assert pm.current_project is None
dlg = make_importer()
dlg.import_data()
assert pm.current_project is not None
assert 'RM01' in pm.current_project.samples
assert pm.current_project.samples['RM01'].sample_path == RM01.resolve()
print("PASS: a successful import adds the sample via ProjectManager.add_samples(), creating an untitled project")

# ------------------------------------------------------------------
# Reimporting (same sample_ids, unchanged) evicts the stale cached
# SampleObj and reloads the currently-selected sample
# ------------------------------------------------------------------
win.app_data.sample_id = 'RM01'
win.change_sample()
assert 'RM01' in win.data
old_sample_obj = win.data['RM01']

dlg2 = make_importer()
dlg2.import_data()
assert 'RM01' in win.data
assert win.data['RM01'] is not old_sample_obj, "reimport should evict and reconstruct the stale cached SampleObj"
print("PASS: reimporting the currently-selected sample evicts the stale cache and reloads it fresh")

shutil.rmtree(tmp_dir, ignore_errors=True)
print("\nALL import-chaining INTEGRATION TESTS PASSED")
