"""Headless, Qt-free verification of `src/project/ProjectModel.py`.

Run directly: `python tests/test_project_model.py`. No QApplication, no
pytest dependency (pytest isn't installed in this project's .venv today --
see the project-migration plan's test-infra caveat) -- plain asserts, same
pattern as this repo's other standalone verification scripts.
"""
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.project.ProjectModel import (
    Project, ProjectSampleEntry, SampleCalibration, SampleProcessingState,
    FilterSpec, MaskSpec, ComputedFieldSpec, ProcessingLogEntry,
    new_project, save_project, load_project,
    compute_source_hash, is_calibration_stale,
    calibration_sidecar_path, save_calibration_sidecar, load_calibration_sidecar,
)


def test_new_project_is_untitled_and_empty():
    p = new_project()
    assert p.name == "Untitled Project"
    assert p.samples == {}
    assert p.dirty is False
    assert p.manifest_path is None
    print("PASS: new_project() is untitled and empty")


def test_round_trip_save_load(tmpdir):
    raw = tmpdir / "RM02.lame.csv"
    raw.write_text("Xc,Yc\n0,0\n", encoding='utf-8')

    project = new_project("RM02 study")
    project.samples['RM02'] = ProjectSampleEntry(
        sample_path=raw,
        calibration=SampleCalibration(
            source_hash=compute_source_hash(raw),
            calibrated_at=datetime(2026, 6, 14, 12, 0, 0),
            method='LA-ICP-MS standards+drift',
            payload={'standards_used': ['NIST610', 'STDGL2b-2']},
        ),
        processing=SampleProcessingState(
            workflow_ref='hpe_correction.json',
            applied_filters=[FilterSpec(True, 'Analyte', 'Fe57', 'none', 0.0, 100.0, '>', True)],
            masks=[MaskSpec('polygon', True, {'n_polygons': 2})],
            computed_fields=[ComputedFieldSpec('Fe_Mn_ratio', 'Fe57 / Mn55')],
            processing_log=[ProcessingLogEntry('2026-06-14T12:00:00', 'filter_applied', {'field': 'Fe57'})],
        ),
    )
    project.workflow_refs = [tmpdir / "workflows" / "hpe_correction.json"]

    manifest = tmpdir / "projects" / "RM02study" / "RM02study.lame_project.json"
    save_project(project, manifest)
    assert project.dirty is False
    assert project.manifest_path == Path(manifest)
    assert manifest.exists()

    reloaded = load_project(manifest)
    assert reloaded.name == "RM02 study"
    assert set(reloaded.samples) == {'RM02'}

    entry = reloaded.samples['RM02']
    assert entry.sample_path == Path(raw).resolve()
    assert entry.calibration.method == 'LA-ICP-MS standards+drift'
    assert entry.calibration.payload['standards_used'] == ['NIST610', 'STDGL2b-2']
    assert entry.processing.workflow_ref == 'hpe_correction.json'
    assert len(entry.processing.applied_filters) == 1
    assert entry.processing.applied_filters[0].field == 'Fe57'
    assert entry.processing.masks[0].kind == 'polygon'
    assert entry.processing.computed_fields[0].formula == 'Fe57 / Mn55'
    assert entry.processing.processing_log[0].action == 'filter_applied'
    assert reloaded.workflow_refs == [Path(tmpdir / "workflows" / "hpe_correction.json").resolve()]
    print("PASS: project round-trips through save_project/load_project")


def test_relative_paths_survive_moving_project_dir(tmpdir):
    raw = tmpdir / "data" / "RM02.lame.csv"
    raw.parent.mkdir()
    raw.write_text("Xc,Yc\n0,0\n", encoding='utf-8')

    project = new_project("Movable")
    project.samples['RM02'] = ProjectSampleEntry(sample_path=raw)

    manifest = tmpdir / "proj_original_location" / "proj.lame_project.json"
    save_project(project, manifest)

    # simulate moving the whole project directory (but not the raw data) elsewhere
    moved_dir = tmpdir / "proj_new_location"
    shutil.move(str(Path(manifest).parent), str(moved_dir))
    moved_manifest = moved_dir / "proj.lame_project.json"

    reloaded = load_project(moved_manifest)
    assert reloaded.samples['RM02'].sample_path == Path(raw).resolve()
    assert reloaded.samples['RM02'].sample_path.exists()
    print("PASS: relative sample paths resolve correctly after moving the project directory")


def test_calibration_staleness(tmpdir):
    raw = tmpdir / "RM01.lame.csv"
    raw.write_text("Xc,Yc\n0,0\n", encoding='utf-8')

    calibration = SampleCalibration(
        source_hash=compute_source_hash(raw),
        calibrated_at=datetime.now(),
        method='XRF (pre-processed externally)',
        payload={'source_software': 'Bruker M4'},
    )
    assert is_calibration_stale(calibration, raw) is False
    assert is_calibration_stale(None, raw) is False  # "no calibration" is not "stale"

    # touch the file so mtime changes; sleep briefly since compute_source_hash
    # truncates mtime to whole seconds
    time.sleep(1.1)
    raw.write_text("Xc,Yc\n0,0\n1,1\n", encoding='utf-8')
    assert is_calibration_stale(calibration, raw) is True
    print("PASS: calibration staleness detects a changed source file, not a false positive on an unchanged one")


def test_calibration_sidecar_round_trip(tmpdir):
    raw = tmpdir / "RM03.lame.csv"
    raw.write_text("Xc,Yc\n0,0\n", encoding='utf-8')

    assert load_calibration_sidecar(raw) is None  # tolerant: no sidecar yet -> None, not an error

    calibration = SampleCalibration(
        source_hash=compute_source_hash(raw),
        calibrated_at=datetime(2026, 1, 1),
        method='LA-ICP-MS standards+drift',
        payload={'standards_used': ['NIST610']},
    )
    save_calibration_sidecar(raw, calibration)

    sidecar = calibration_sidecar_path(raw)
    assert sidecar.name == "RM03.calib.json"
    assert sidecar.exists()

    reloaded = load_calibration_sidecar(raw)
    assert reloaded.method == 'LA-ICP-MS standards+drift'
    assert reloaded.payload['standards_used'] == ['NIST610']
    print("PASS: calibration sidecar round-trips and is tolerant of being absent")


def test_calibration_schema_open_for_different_data_types(tmpdir):
    """A confirmatory test for the schema-open design: two very different
    calibration payload shapes (LA-ICP-MS vs. externally-pre-processed XRF)
    both round-trip without any schema change.
    """
    raw = tmpdir / "XRF01.lame.csv"
    raw.write_text("Xc,Yc\n0,0\n", encoding='utf-8')

    xrf_calibration = SampleCalibration(
        source_hash=compute_source_hash(raw),
        calibrated_at=datetime.now(),
        method='XRF (pre-processed externally)',
        payload={'source_software': 'Bruker M4', 'export_format': 'per-element TIFF'},
    )
    save_calibration_sidecar(raw, xrf_calibration)
    reloaded = load_calibration_sidecar(raw)
    assert reloaded.payload == {'source_software': 'Bruker M4', 'export_format': 'per-element TIFF'}
    assert 'standards_used' not in reloaded.payload
    print("PASS: SampleCalibration.payload accommodates a non-LA-ICP-MS schema without changes")


if __name__ == '__main__':
    test_new_project_is_untitled_and_empty()

    tmp = Path(tempfile.mkdtemp(prefix='lame_project_model_test_'))
    try:
        for sub in ('round_trip', 'moving_test', 'staleness_test', 'sidecar_test', 'schema_test'):
            (tmp / sub).mkdir()

        test_round_trip_save_load(tmp / 'round_trip')
        test_relative_paths_survive_moving_project_dir(tmp / 'moving_test')
        test_calibration_staleness(tmp / 'staleness_test')
        test_calibration_sidecar_round_trip(tmp / 'sidecar_test')
        test_calibration_schema_open_for_different_data_types(tmp / 'schema_test')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nALL ProjectModel TESTS PASSED")
