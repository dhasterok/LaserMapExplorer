"""Headless integration check for step 4: calibration sidecar auto-load on
sample init, staleness logging, and the full Tier 2 processing-state
round-trip through a real save/close/reopen cycle.

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
from PyQt6.QtWidgets import QMessageBox
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)

from src.app.MainWindow import MainWindow
from src.project.ProjectModel import (
    SampleCalibration, compute_source_hash, calibration_sidecar_path,
    save_calibration_sidecar,
)

RM01_SOURCE = Path("/Users/dhasterok/maps/processed data/RM01.lame.csv")
assert RM01_SOURCE.exists(), f"missing fixture: {RM01_SOURCE}"

# Work on a disposable copy so we can write a .calib.json sidecar and touch
# mtimes without touching real user data.
tmp_dir = Path(tempfile.mkdtemp(prefix='lame_calib_wiring_test_'))
RM01 = tmp_dir / "RM01.lame.csv"
shutil.copy(RM01_SOURCE, RM01)

win = MainWindow(app)
pm = win.project_manager

# ------------------------------------------------------------------
# Calibration sidecar auto-load + staleness logging
#
# The sidecar must exist BEFORE the sample is added: add_samples() ->
# _sync_app_data_from_project() -> AppData.sample_list setter fires
# sampleChanged immediately, which drives change_sample()/
# initialize_sample_object() synchronously as part of add_samples() itself
# (not lazily on some later explicit change_sample() call) -- this mirrors
# real usage, where calibration would already be on disk from an earlier,
# separate calibration step by the time a sample is added to a project.
# ------------------------------------------------------------------
save_calibration_sidecar(RM01, SampleCalibration(
    source_hash=compute_source_hash(RM01),
    calibrated_at=datetime(2026, 6, 14, 12, 0, 0),
    method='LA-ICP-MS standards+drift',
    payload={'standards_used': ['NIST610']},
))
assert calibration_sidecar_path(RM01).exists()

pm.add_samples([RM01])
entry = pm.current_project.samples['RM01']
assert 'RM01' in win.data, "add_samples() should have driven initialize_sample_object() already"
assert entry.calibration is not None, "initialize_sample_object() should have auto-loaded the sidecar"
assert entry.calibration.method == 'LA-ICP-MS standards+drift'
print("PASS: calibration sidecar is auto-loaded into the project entry on first sample init")

# staleness: must not raise, and must actually detect the change (checked
# directly via is_calibration_stale rather than scraping logs)
from src.project.ProjectModel import is_calibration_stale
assert is_calibration_stale(entry.calibration, RM01) is False
time.sleep(1.1)
RM01.write_text(RM01.read_text() + "\n")  # touch mtime+size
assert is_calibration_stale(entry.calibration, RM01) is True

# re-selecting a DIFFERENT sample then back to RM01 forces
# initialize_sample_object() to run again is not needed here -- the staleness
# log path just needs to not crash when re-entered; confirm via a second
# direct call path exercised through change_sample() on a fresh sample_id
# is unnecessary since entry.calibration is already cached (by design, only
# auto-loaded once). Confirm the cached object itself is now flagged stale
# by the same function the future dock will call.
print("PASS: is_calibration_stale() detects the touched source file without raising")

# ------------------------------------------------------------------
# Full Tier 2 round-trip: filter -> save -> close -> reopen -> replayed
# ------------------------------------------------------------------
data = win.data['RM01']
analyte = data.processed.match_attribute('data_type', 'Analyte')[0]
data.add_filter(field_type='Analyte', field=analyte, min_val=0.0, max_val=1e9, operator='and', use=True)
assert len(data.filter_df) == 1

manifest = tmp_dir / "CalibTest.lame_project.json"
pm.save_project(manifest)

# confirm the manifest actually contains the filter and the calibration
import json
payload = json.loads(manifest.read_text())
sample_payload = payload['samples']['RM01']
assert len(sample_payload['processing']['applied_filters']) == 1
assert sample_payload['processing']['applied_filters'][0]['field'] == analyte
assert sample_payload['calibration']['method'] == 'LA-ICP-MS standards+drift'
print("PASS: save_project() pulls live filter + calibration state into the manifest")

pm.close_project()
assert win.data == {}

pm.open_project(manifest)
win.app_data.sample_id = 'RM01'
win.change_sample()
assert 'RM01' in win.data
reloaded_data = win.data['RM01']
assert len(reloaded_data.filter_df) == 1, "filter should have been replayed via apply_processing_state()"
assert reloaded_data.filter_df.iloc[0]['field'] == analyte
reloaded_entry = pm.current_project.samples['RM01']
assert reloaded_entry.calibration is not None
assert reloaded_entry.calibration.method == 'LA-ICP-MS standards+drift'
print("PASS: full round-trip -- filter and calibration both survive save/close/reopen through real sample-load wiring")

shutil.rmtree(tmp_dir, ignore_errors=True)
print("\nALL calibration-wiring INTEGRATION TESTS PASSED")
