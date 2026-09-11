"""Calibration sidecar auto-load on sample init, staleness detection, and the
full processing-state round-trip through a real save/close/reopen cycle.

Headless MainWindow integration tests -- shared setup (QApplication, modal
dialog stubbing, sample files) comes from tests/conftest.py.
"""
import json
import time
from datetime import datetime

import pytest

from src.project.ProjectModel import (
    SampleCalibration,
    calibration_sidecar_path,
    compute_source_hash,
    is_calibration_stale,
    save_calibration_sidecar,
)
from tests.conftest import first_analyte

CALIBRATION_METHOD = 'LA-ICP-MS standards+drift'


def _write_sidecar(path):
    save_calibration_sidecar(path, SampleCalibration(
        source_hash=compute_source_hash(path),
        calibrated_at=datetime(2026, 6, 14, 12, 0, 0),
        method=CALIBRATION_METHOD,
        payload={'standards_used': ['NIST610']},
    ))
    assert calibration_sidecar_path(path).exists()


@pytest.fixture
def calibrated_window(lame_window, sample_factory):
    """A window with one sample whose calibration sidecar existed *before* it
    was added.

    The ordering matters and is what the auto-load path depends on:
    ``add_samples()`` -> ``_sync_app_data_from_project()`` -> the
    ``AppData.sample_list`` setter fires ``sampleChanged`` immediately, which
    drives ``change_sample()``/``initialize_sample_object()`` synchronously
    as part of ``add_samples()`` itself -- not lazily on some later explicit
    ``change_sample()``. That mirrors real usage, where calibration is
    already on disk from a separate earlier calibration step by the time a
    sample joins a project.
    """
    path = sample_factory('RM01')
    _write_sidecar(path)
    lame_window.project_manager.add_samples([path])
    return lame_window, path


def test_sidecar_is_auto_loaded_on_first_sample_init(calibrated_window):
    window, _path = calibrated_window
    entry = window.project_manager.current_project.samples['RM01']

    assert 'RM01' in window.data, "add_samples() should have driven initialize_sample_object() already"
    assert entry.calibration is not None, "initialize_sample_object() should have auto-loaded the sidecar"
    assert entry.calibration.method == CALIBRATION_METHOD


def test_calibration_is_not_stale_for_an_untouched_source(calibrated_window):
    window, path = calibrated_window
    entry = window.project_manager.current_project.samples['RM01']
    assert is_calibration_stale(entry.calibration, path) is False


def test_calibration_goes_stale_when_the_source_file_changes(calibrated_window):
    """Checked directly through is_calibration_stale -- the function the dock
    calls -- rather than by scraping log output."""
    window, path = calibrated_window
    entry = window.project_manager.current_project.samples['RM01']

    time.sleep(1.1)                              # mtime has 1 s resolution
    path.write_text(path.read_text() + "\n")     # changes mtime and size

    assert is_calibration_stale(entry.calibration, path) is True


def test_save_project_captures_live_filter_and_calibration(calibrated_window, tmp_path):
    window, _path = calibrated_window
    data = window.data['RM01']
    analyte = first_analyte(window)
    data.add_filter(field_type='Analyte', field=analyte, min_val=0.0, max_val=1e9,
                    operator='and', use=True)
    assert len(data.filter_df) == 1

    manifest = tmp_path / 'CalibTest.lame_project.json'
    window.project_manager.save_project(manifest)

    payload = json.loads(manifest.read_text())['samples']['RM01']
    assert len(payload['processing']['applied_filters']) == 1
    assert payload['processing']['applied_filters'][0]['field'] == analyte
    assert payload['calibration']['method'] == CALIBRATION_METHOD


def test_filter_and_calibration_survive_save_close_reopen(calibrated_window, tmp_path):
    """The whole point of the sidecar + processing-state wiring: state set up
    in one session comes back through real sample-load wiring in the next."""
    window, _path = calibrated_window
    pm = window.project_manager
    analyte = first_analyte(window)
    window.data['RM01'].add_filter(field_type='Analyte', field=analyte, min_val=0.0,
                                    max_val=1e9, operator='and', use=True)

    manifest = tmp_path / 'CalibTest.lame_project.json'
    pm.save_project(manifest)

    pm.close_project()
    assert window.data == {}

    pm.open_project(manifest)
    window.app_data.sample_id = 'RM01'
    window.change_sample()

    assert 'RM01' in window.data
    reloaded = window.data['RM01']
    assert len(reloaded.filter_df) == 1, "filter should have been replayed via apply_processing_state()"
    assert reloaded.filter_df.iloc[0]['field'] == analyte

    entry = pm.current_project.samples['RM01']
    assert entry.calibration is not None
    assert entry.calibration.method == CALIBRATION_METHOD
