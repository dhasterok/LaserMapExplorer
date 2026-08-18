"""Export (CSV / JSON QC report / figure batch) tests against synthetic
pipeline output.

Pure Python -- no PyQt/QApplication needed.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import pandas as pd
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.io_export import export_calibrated_csv, export_figures, export_qc_report_json
from src.calibration.pipeline import run
from tests.test_calibration_pipeline import _make_sample_dir, _reference_library


@pytest.fixture
def sample_result(tmp_path):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)
    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0,
    )
    return results["SAMPLE"]


def test_export_calibrated_csv_round_trips(sample_result, tmp_path):
    out_path = tmp_path / "calibrated.csv"
    written = export_calibrated_csv(sample_result, out_path)
    assert written == out_path
    assert out_path.exists()

    reloaded = pd.read_csv(out_path)
    assert "Al27" in reloaded.columns
    assert "line_number" in reloaded.columns
    assert "sweep_index" in reloaded.columns
    assert len(reloaded) == len(sample_result.calibrated_ppm)


def test_export_qc_report_json_has_expected_structure(sample_result, tmp_path):
    out_path = tmp_path / "qc_report.json"
    export_qc_report_json(sample_result, out_path)
    assert out_path.exists()

    report = json.loads(out_path.read_text())
    assert report["sample_label"] == "SAMPLE"
    assert "provenance" in report
    assert "timing" in report and len(report["timing"]) == len(sample_result.files)
    assert "NIST610" in report["standards"]
    standard_entry = report["standards"]["NIST610"]
    assert "accuracy_table" in standard_entry
    assert all(isinstance(row["time"], str) for row in standard_entry["accuracy_table"])


def test_export_figures_writes_png_files(sample_result, tmp_path):
    out_dir = tmp_path / "figures"
    written = export_figures(sample_result, out_dir, analytes=["Al27"])
    assert len(written) > 0
    for path in written:
        assert path.exists()
        assert path.suffix == ".png"
