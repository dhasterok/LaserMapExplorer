"""Unit tests for src/deconvolution/washout.py -- most importantly that
eq. (6) exactly inverts a noiseless synthetic AR(1) sequence (design spec
Sec 9.2's reference invariant).

Pure Python/numpy -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.deconvolution.washout import invert_washout


def _forward_ar1(u: np.ndarray, tau_s: float, dt_s: float) -> np.ndarray:
    """Reference forward model: m[n] = a*m[n-1] + (1-a)*u[n], m[0] = u[0]."""
    a = np.exp(-dt_s / tau_s)
    m = np.empty_like(u)
    m[0] = u[0]
    for n in range(1, len(u)):
        m[n] = a * m[n - 1] + (1 - a) * u[n]
    return m


def test_invert_washout_exactly_inverts_noiseless_ar1():
    rng = np.random.default_rng(0)
    tau_s, dt_s = 2.0, 0.5
    u_true = rng.uniform(10, 1000, size=50)
    m = _forward_ar1(u_true, tau_s, dt_s)

    result = invert_washout(m, tau_s, dt_s)

    assert np.allclose(result.corrected, u_true, atol=1e-9)


def test_noise_amplification_matches_eq7():
    tau_s, dt_s = 3.0, 0.5
    a = np.exp(-dt_s / tau_s)
    expected = (1 + a**2) / (1 - a) ** 2
    result = invert_washout(np.full(10, 100.0), tau_s, dt_s)
    assert result.noise_amplification == pytest.approx(expected)


def test_noise_amplification_grows_with_tau():
    dt_s = 0.5
    r_short = invert_washout(np.full(10, 100.0), tau_s=0.1, dt_s=dt_s)
    r_long = invert_washout(np.full(10, 100.0), tau_s=20.0, dt_s=dt_s)
    assert r_long.noise_amplification > r_short.noise_amplification


def test_negative_counts_reported_not_clipped():
    # A sharp drop from a large-contrast tail should produce a negative
    # inverted value that must be visible, not silently zeroed.
    m = np.array([10000.0, 9000.0, 50.0, 45.0, 40.0])
    result = invert_washout(m, tau_s=5.0, dt_s=0.5)
    assert result.negative_count > 0
    assert "negative_counts" in result.flags
    assert np.any(result.corrected < 0)  # not clipped away


def test_first_sample_boundary_flag_always_present():
    result = invert_washout(np.full(5, 100.0), tau_s=1.0, dt_s=0.5)
    assert "first_sample_boundary_assumed" in result.flags
    assert result.corrected[0] == 100.0


def test_invert_washout_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        invert_washout(np.ones(5), tau_s=0.0, dt_s=0.5)
    with pytest.raises(ValueError):
        invert_washout(np.ones(5), tau_s=1.0, dt_s=0.0)
    with pytest.raises(ValueError):
        invert_washout(np.ones((2, 2)), tau_s=1.0, dt_s=0.5)
