"""Pooled-isotope virtual-channel tests -- hand-computable sums against the
real isotope_info.csv abundance table, following the same convention as
tests/test_calibration_massbias.py.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from datetime import datetime
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.pooling import (
    PooledElementSpec,
    combined_abundance_fraction,
    is_pooled_channel_name,
    pooled_channel_name,
    synthesize_pooled_channels,
)
from src.calibration.rawfile import parse_line_file
from tests.test_calibration_pipeline import _write_raw_file

BASE_TIME = datetime(2026, 3, 1, 10, 0, 0)


def test_pooled_channel_name_and_is_pooled_channel_name_round_trip():
    name = pooled_channel_name("Pb")
    assert name == "Pb total"
    assert is_pooled_channel_name(name) == "Pb"
    assert is_pooled_channel_name("Pb206") is None


def test_combined_abundance_fraction_known_values():
    # 206Pb + 207Pb + 208Pb natural abundance ~= 0.2414 + 0.2208 + 0.5235 (excludes 204Pb).
    fraction = combined_abundance_fraction("Pb", [206, 207, 208])
    assert fraction == pytest.approx(0.241447 + 0.220827 + 0.523481, abs=1e-4)


def test_combined_abundance_fraction_unresolvable_element_returns_none():
    assert combined_abundance_fraction("Xx", [1, 2]) is None


def test_synthesize_pooled_channels_sums_and_scales_by_combined_abundance(tmp_path):
    pb_analytes = ["Pb204", "Pb206", "Pb207", "Pb208"]
    bg, abl = (500.0, 8500.0, 7750.0, 18000.0), (100000.0, 1700000.0, 1550000.0, 3600000.0)
    _write_raw_file(tmp_path, "SAMPLE", 1, BASE_TIME, seed=1, analytes=pb_analytes, bg_level=bg, ablation_level=abl)
    path = tmp_path / "SAMPLE - 1.csv"
    line = parse_line_file(path, standard_names=set())

    spec = PooledElementSpec(element="Pb", masses=[206, 207, 208])
    synthesize_pooled_channels([line], [spec])

    assert "Pb total" in line.analytes
    assert "Pb total" in line.signal.columns
    fraction = combined_abundance_fraction("Pb", [206, 207, 208])
    expected = ((line.signal["Pb206"] + line.signal["Pb207"] + line.signal["Pb208"]) / fraction).to_numpy()
    assert line.signal["Pb total"].to_numpy() == pytest.approx(expected)
    # Pb204 (excluded from this spec) must not affect the pooled sum.
    wrong = ((line.signal["Pb204"] + line.signal["Pb206"] + line.signal["Pb207"] + line.signal["Pb208"]) / fraction).to_numpy()
    assert line.signal["Pb total"].to_numpy() != pytest.approx(wrong)


def test_synthesize_pooled_channels_skips_file_missing_every_requested_mass(tmp_path):
    _write_raw_file(tmp_path, "SAMPLE", 1, BASE_TIME, seed=1)  # default Al27/Ca43 analytes -- no Pb at all
    path = tmp_path / "SAMPLE - 1.csv"
    line = parse_line_file(path, standard_names=set())

    spec = PooledElementSpec(element="Pb", masses=[206, 207, 208])
    synthesize_pooled_channels([line], [spec])

    assert "Pb total" not in line.analytes
    assert "Pb total" not in line.signal.columns


def test_synthesize_pooled_channels_uses_only_masses_actually_present(tmp_path):
    # Only Pb206/Pb208 measured (Pb207 absent) -- the combined fraction and
    # sum must use just the two present channels, not raise or silently
    # include a phantom Pb207 contribution.
    pb_analytes = ["Pb206", "Pb208"]
    _write_raw_file(tmp_path, "SAMPLE", 1, BASE_TIME, seed=1, analytes=pb_analytes, bg_level=(8500.0, 18000.0), ablation_level=(1700000.0, 3600000.0))
    path = tmp_path / "SAMPLE - 1.csv"
    line = parse_line_file(path, standard_names=set())

    spec = PooledElementSpec(element="Pb", masses=[206, 207, 208])
    synthesize_pooled_channels([line], [spec])

    assert "Pb total" in line.signal.columns
    fraction = combined_abundance_fraction("Pb", [206, 208])
    expected = ((line.signal["Pb206"] + line.signal["Pb208"]) / fraction).to_numpy()
    assert line.signal["Pb total"].to_numpy() == pytest.approx(expected)
