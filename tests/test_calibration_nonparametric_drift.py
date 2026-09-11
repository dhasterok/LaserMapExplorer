"""Unit tests for src/calibration/nonparametric_drift.py.

Pure Python/numpy/scipy/sklearn -- no PyQt/QApplication needed.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.drift import DriftFitError, fit_polynomial
from src.calibration.nonparametric_drift import (
    NONPARAMETRIC_DRIFT_METHODS,
    NonparametricDriftFit,
    fit_kriging,
    fit_lowess,
    fit_nonparametric_drift,
    fit_spline,
)

BASE = datetime(2026, 3, 1, 10, 0, 0)


def _session(fn, n=120, step_min=18, noise=4.0, seed=0):
    """(times, values) for a synthetic session; ``fn(i)`` is the noise-free level."""
    rng = np.random.default_rng(seed)
    times = [BASE + timedelta(minutes=step_min * i) for i in range(n)]
    clean = np.array([fn(i) for i in range(n)], dtype=float)
    return times, clean + rng.normal(0.0, noise, n), clean


@pytest.mark.parametrize("method", ["lowess", "spline", "kriging"])
def test_fitters_recover_a_nonmonotonic_curve(method):
    times, values, clean = _session(lambda i: 500.0 + 40.0 * np.sin(i / 12.0) + 0.3 * i)
    fit = fit_nonparametric_drift(times, values, method, analyte="Al27")

    assert isinstance(fit, NonparametricDriftFit)
    assert fit.method == method
    assert fit.analyte == "Al27"
    assert fit.order == -1
    assert fit.n_points == len(times)

    pred = fit.predict(times)
    assert pred.shape == (len(times),)
    # Tracks the noise-free curve to within ~the noise level, and far better
    # than a straight line through the same points.
    np_rmse = np.sqrt(np.mean((pred - clean) ** 2))
    lin = fit_polynomial(times, values, order=1)
    lin_rmse = np.sqrt(np.mean((lin.predict(times) - clean) ** 2))
    assert np_rmse < 8.0
    assert np_rmse < 0.5 * lin_rmse
    assert fit.r_squared > 0.9


@pytest.mark.parametrize("fitter", [fit_lowess, fit_spline, fit_kriging])
def test_predict_off_grid_and_scalar_like(fitter):
    times, values, _ = _session(lambda i: 300.0 + 5.0 * np.cos(i / 8.0))
    fit = fitter(times, values)

    # midpoints between acquisitions -- interpolation, not just at knots
    mids = [BASE + timedelta(minutes=18 * i + 9) for i in range(len(times) - 1)]
    pred_mid = fit.predict(mids)
    assert pred_mid.shape == (len(mids),)
    assert np.all(np.isfinite(pred_mid))

    one = fit.predict([times[10]])
    assert one.shape == (1,)


@pytest.mark.parametrize("method", ["lowess", "spline", "kriging"])
def test_too_few_points_raises_drift_fit_error(method):
    times = [BASE + timedelta(minutes=10 * i) for i in range(3)]
    with pytest.raises(DriftFitError):
        fit_nonparametric_drift(times, [1.0, 2.0, 3.0], method)


@pytest.mark.parametrize("method", ["lowess", "spline", "kriging"])
def test_zero_time_span_raises(method):
    times = [BASE] * 8
    with pytest.raises(DriftFitError):
        fit_nonparametric_drift(times, np.arange(8.0), method)


def test_unknown_method_raises_value_error():
    times, values, _ = _session(lambda i: 100.0 + i)
    with pytest.raises(ValueError, match="Unknown non-parametric drift method"):
        fit_nonparametric_drift(times, values, "polynomial")


def test_duplicate_timestamps_are_averaged_not_fatal():
    # Two lines per acquisition second (co-located x) -- the spline path in
    # particular needs strictly increasing x, so these must collapse to
    # their mean rather than raise.
    times, values = [], []
    for i in range(30):
        t = BASE + timedelta(minutes=20 * i)
        times += [t, t]
        values += [500.0 + i, 500.0 + i + 10.0]
    fit = fit_spline(times, values)
    assert fit.n_points == 30
    mid = fit.predict([BASE + timedelta(minutes=20 * 5)])
    assert np.isfinite(mid[0])
    # averaged target at i=5 is 505 + 5 = 510
    assert mid[0] == pytest.approx(510.0, abs=15.0)


def test_lowess_frac_controls_smoothness():
    times, values, clean = _session(lambda i: 400.0 + 30.0 * np.sin(i / 6.0), noise=2.0)
    wide = fit_lowess(times, values, frac=1.0)     # ~global linear -> misses the wiggle
    narrow = fit_lowess(times, values, frac=0.1)   # local -> follows it
    wide_rmse = np.sqrt(np.mean((wide.predict(times) - clean) ** 2))
    narrow_rmse = np.sqrt(np.mean((narrow.predict(times) - clean) ** 2))
    assert narrow_rmse < wide_rmse


def test_lowess_predict_is_grid_interpolated_not_per_point_resolved():
    """Regression guard: compute_background_result calls predict() over every
    ablation row of every file, so LOWESS prediction must be an
    interpolation off a pre-computed curve, not an O(n_train) local solve
    per query point."""
    import time

    times, values, _ = _session(lambda i: 500.0 + 20.0 * np.sin(i / 9.0), n=150)
    fit = fit_lowess(times, values)
    grid_x, grid_y = fit.model
    assert grid_x.ndim == 1 and grid_x.size > 1000
    assert grid_y.shape == grid_x.shape

    many = [BASE + timedelta(seconds=30 * i) for i in range(200_000)]
    t0 = time.perf_counter()
    pred = fit.predict(many)
    elapsed = time.perf_counter() - t0
    assert pred.shape == (len(many),)
    assert np.all(np.isfinite(pred))
    assert elapsed < 5.0  # generous; a per-point solve here takes minutes


def test_lowess_predict_clamps_beyond_the_grid():
    times, values, _ = _session(lambda i: 100.0 + i, n=30)
    fit = fit_lowess(times, values)
    far_past = fit.predict([BASE - timedelta(days=30)])[0]
    far_future = fit.predict([BASE + timedelta(days=90)])[0]
    grid_y = fit.model[1]
    assert far_past == pytest.approx(grid_y[0])
    assert far_future == pytest.approx(grid_y[-1])


@pytest.mark.parametrize("method", ["lowess", "spline", "kriging"])
def test_pure_noise_background_stays_within_the_observed_range(method):
    """Regression pin: several real channels' blanks are essentially pure
    noise with no drift at all. An earlier UnivariateSpline-based spline fit
    returned wildly divergent curves on exactly those channels (held-out
    errors ~1e7 x the data's own spread). Every fitter must stay bounded by
    the data it saw."""
    rng = np.random.default_rng(3)
    times = [BASE + timedelta(minutes=3 * i) for i in range(400)]
    values = np.abs(rng.normal(50.0, 30.0, 400))
    fit = fit_nonparametric_drift(times, values, method)

    dense = [BASE + timedelta(seconds=45 * i) for i in range(1600)]
    pred = fit.predict(dense)
    assert np.all(np.isfinite(pred))
    span = values.max() - values.min()
    assert pred.min() > values.min() - span
    assert pred.max() < values.max() + span


def test_spline_flexibility_is_knot_controlled():
    times, values, _ = _session(lambda i: 500.0 + 10.0 * np.sin(i / 7.0), n=400)
    fit = fit_spline(times, values)
    # ~n/20 interior knots -> a cubic B-spline with n/20 + 4 coefficients,
    # not one coefficient per data point.
    assert len(fit.model.get_coeffs()) < 40
    assert len(fit.model.get_knots()) < 30


def test_constant_background_is_handled():
    times = [BASE + timedelta(minutes=15 * i) for i in range(20)]
    values = np.full(20, 250.0)
    for method in NONPARAMETRIC_DRIFT_METHODS:
        fit = fit_nonparametric_drift(times, values, method)
        pred = fit.predict(times)
        assert np.allclose(pred, 250.0, atol=1.0)


def test_module_method_set_matches_dispatch():
    assert NONPARAMETRIC_DRIFT_METHODS == frozenset({"lowess", "spline", "kriging"})
