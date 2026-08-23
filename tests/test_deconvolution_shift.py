"""Unit tests for src/deconvolution/shift.py.

Pure Python/numpy -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.deconvolution.shift import correct_shift, sweep_offset_pixels


def test_sweep_offset_pixels_zero_for_first_analyte():
    assert sweep_offset_pixels(0, dwell_time_ms=10.0, sweep_s=0.5) == 0.0


def test_sweep_offset_pixels_scales_with_index_and_dwell():
    dt_s = 0.5
    dwell_ms = 10.0
    off1 = sweep_offset_pixels(1, dwell_ms, dt_s)
    off2 = sweep_offset_pixels(2, dwell_ms, dt_s)
    assert off2 == pytest.approx(2 * off1)
    assert off1 == pytest.approx((dwell_ms / 1000.0) / dt_s)


def test_sweep_offset_pixels_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        sweep_offset_pixels(0, dwell_time_ms=-1.0, sweep_s=0.5)
    with pytest.raises(ValueError):
        sweep_offset_pixels(0, dwell_time_ms=1.0, sweep_s=0.0)


def test_correct_shift_zero_shift_is_identity():
    x = np.array([1.0, 5.0, 2.0, 8.0, 3.0])
    out = correct_shift(x, shift_pixels=0.0)
    assert np.allclose(out, x)


def test_correct_shift_integer_shift_moves_samples():
    x = np.array([0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0])
    # shift_pixels positive -> shifted backward (toward index 0), per the
    # documented "analyte read later -> pulled back toward line start" convention
    out = correct_shift(x, shift_pixels=2.0, order=1)
    assert np.argmax(out) == 1


def test_correct_shift_round_trip_recovers_signal_away_from_edges():
    # Cubic-spline resampling round-trips well on a smooth (band-limited)
    # signal, matching real LA-ICP-MS line profiles -- it is *not* expected
    # to round-trip white noise exactly (the spec's documented "correlates
    # noise" caveat for this quick-look path, see shift.py's docstring),
    # so a smooth test signal is used rather than random noise.
    s = np.arange(60)
    x = 100.0 + 20.0 * np.sin(2 * np.pi * s / 25.0)
    shifted = correct_shift(x, shift_pixels=3.7)
    back = correct_shift(shifted, shift_pixels=-3.7)
    # Interior samples should round-trip closely under cubic-spline resampling;
    # edges are excluded since 'nearest' boundary handling isn't exactly invertible.
    assert np.allclose(back[10:-10], x[10:-10], atol=0.5)
