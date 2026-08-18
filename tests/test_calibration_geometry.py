"""Manual-entry instrument-settings / pixel-spacing tests.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.geometry import InstrumentSettings, compute_pixel_spacing


def test_blank_settings_yields_unitless_index_spacing():
    settings = InstrumentSettings()
    assert settings.is_blank() is True
    assert compute_pixel_spacing(settings) == (1.0, 1.0)


def test_spot_size_only_falls_back_to_square_pixels():
    settings = InstrumentSettings.from_manual_entry(spot_size_um=10.0)
    assert settings.is_blank() is False
    assert compute_pixel_spacing(settings) == (10.0, 10.0)


def test_spot_size_with_sweep_and_speed_gives_rectangular_pixels():
    settings = InstrumentSettings.from_manual_entry(spot_size_um=10.0, sweep_s=0.28, speed_um_s=5.0)
    dx, dy = compute_pixel_spacing(settings)
    assert dx == pytest.approx(10.0)
    assert dy == pytest.approx(1.4)


def test_raster_length_width_takes_precedence_over_spot_size():
    settings = InstrumentSettings.from_manual_entry(
        spot_size_um=10.0, raster_length_um=200.0, raster_width_um=150.0
    )
    assert compute_pixel_spacing(settings) == (200.0, 150.0)


def test_scan_axis_yc_swaps_fast_and_slow_axis():
    settings = InstrumentSettings.from_manual_entry(spot_size_um=10.0, sweep_s=0.28, speed_um_s=5.0, scan_axis="Yc")
    dx, dy = compute_pixel_spacing(settings)
    assert dx == pytest.approx(1.4)
    assert dy == pytest.approx(10.0)


def test_notes_dict_is_free_form_and_preserved():
    settings = InstrumentSettings.from_manual_entry(notes={"laser_power_mJ": 3.5, "operator": "SM"})
    assert settings.notes["laser_power_mJ"] == 3.5
    assert settings.notes["operator"] == "SM"
