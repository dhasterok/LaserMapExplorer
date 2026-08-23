"""Unit tests for src/deconvolution/kernels.py.

Pure Python/numpy -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.deconvolution.kernels import boxcar_kernel, gaussian_kernel, washout_kernel


def test_boxcar_kernel_sums_to_one():
    for width in (1.0, 2.3, 5.0, 0.5, 10.7):
        k = boxcar_kernel(width)
        assert k.sum() == pytest.approx(1.0)


def test_boxcar_kernel_integer_width_is_uniform():
    k = boxcar_kernel(4.0)
    assert len(k) == 4
    assert np.allclose(k, 0.25)


def test_boxcar_kernel_fractional_width_partial_tap():
    k = boxcar_kernel(2.5)
    assert len(k) == 3
    # pre-normalization weights are [1, 1, 0.5] (sum 2.5) -- ratio preserved after renorm
    assert k[0] == pytest.approx(1.0 / 2.5)
    assert k[-1] == pytest.approx(0.5 / 2.5)
    assert k[0] == k[1]
    assert k[0] > k[-1]


def test_boxcar_kernel_rejects_nonpositive():
    with pytest.raises(ValueError):
        boxcar_kernel(0.0)
    with pytest.raises(ValueError):
        boxcar_kernel(-1.0)


def test_washout_kernel_sums_to_one_to_machine_precision():
    for tau_s in (0.1, 1.0, 5.0, 20.0):
        h = washout_kernel(tau_s, dt_s=0.5)
        assert h.sum() == pytest.approx(1.0, abs=1e-12)


def test_washout_kernel_is_causal_and_decaying():
    h = washout_kernel(tau_s=2.0, dt_s=0.5)
    assert np.all(h > 0)
    assert np.all(np.diff(h) < 0)  # strictly decaying (causal exponential)


def test_washout_kernel_longer_tau_has_more_taps():
    h_short = washout_kernel(tau_s=0.5, dt_s=0.5)
    h_long = washout_kernel(tau_s=20.0, dt_s=0.5)
    assert len(h_long) > len(h_short)


def test_washout_kernel_rejects_nonpositive():
    with pytest.raises(ValueError):
        washout_kernel(0.0, dt_s=1.0)
    with pytest.raises(ValueError):
        washout_kernel(1.0, dt_s=0.0)


def test_gaussian_kernel_sums_to_one_and_is_symmetric():
    k = gaussian_kernel(sigma_pixels=2.0)
    assert k.sum() == pytest.approx(1.0, abs=1e-12)
    assert np.allclose(k, k[::-1])


def test_gaussian_kernel_rejects_nonpositive():
    with pytest.raises(ValueError):
        gaussian_kernel(0.0)
