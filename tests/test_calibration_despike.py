"""Unit tests for src/calibration/despike.py (ported from latools).

Pure Python/numpy -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import numpy as np

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.despike import expdecay_despike, noise_despike


def test_noise_despike_leaves_flat_data_unchanged():
    rng = np.random.default_rng(0)
    sig = 1000.0 + rng.normal(0, 5, size=50)  # small noise, far below nlim=12 * sqrt(1000)~=380
    out = noise_despike(sig)
    assert np.allclose(out, sig)


def test_noise_despike_removes_isolated_spike():
    sig = np.full(30, 1000.0)
    sig[15] = 50_000.0  # a realistic contamination-scale spike (50x baseline)
    out = noise_despike(sig)
    assert out[15] < 2000.0
    # every other row untouched
    untouched = np.delete(np.arange(30), 15)
    assert np.allclose(out[untouched], sig[untouched])


def test_noise_despike_does_not_mutate_input():
    sig = np.full(30, 1000.0)
    sig[10] = 5_000_000.0
    original = sig.copy()
    noise_despike(sig)
    assert np.array_equal(sig, original)


def test_noise_despike_short_array_returned_unchanged():
    sig = np.array([1.0, 2.0])
    out = noise_despike(sig, window=3)
    assert np.array_equal(out, sig)


def test_noise_despike_never_flags_edge_rows():
    sig = np.full(10, 1000.0)
    sig[0] = 1_000_000.0
    sig[-1] = 1_000_000.0
    out = noise_despike(sig, window=3)
    assert out[0] == sig[0]
    assert out[-1] == sig[-1]


def test_expdecay_despike_leaves_smooth_decay_unchanged():
    t = np.arange(60, dtype=float)
    tstep = 1.0
    exponent = -0.2
    sig = 10_000.0 * np.exp(exponent * t) + 50.0
    out = expdecay_despike(sig, tstep=tstep, exponent=exponent)
    # allow the physically-expected decay through with only small (noise-scale) change
    assert np.max(np.abs(out - sig)) < 1.0


def test_expdecay_despike_removes_physically_impossible_jump():
    t = np.arange(60, dtype=float)
    tstep = 1.0
    exponent = -0.2
    sig = 10_000.0 * np.exp(exponent * t) + 50.0
    sig[30] = 500_000.0  # far above what the washout decay could produce from neighbours
    out = expdecay_despike(sig, tstep=tstep, exponent=exponent)
    assert out[30] < 50_000.0


def test_expdecay_despike_does_not_mutate_input():
    sig = np.full(20, 1000.0)
    sig[10] = 5_000_000.0
    original = sig.copy()
    expdecay_despike(sig, tstep=1.0, exponent=-0.2)
    assert np.array_equal(sig, original)


def test_expdecay_despike_short_array_returned_unchanged():
    sig = np.array([1.0, 2.0, 3.0])
    out = expdecay_despike(sig, tstep=1.0, exponent=-0.2)
    assert np.array_equal(out, sig)
