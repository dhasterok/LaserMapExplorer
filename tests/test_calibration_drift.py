"""Generic polynomial-vs-time drift fitting, tested against synthetic data
with a known injected trend so the recovered coefficients are hand-checkable.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.drift import (
    DriftFit,
    DriftFitError,
    _cv_rss_for_order,
    _predicted_values_are_stable,
    evaluate,
    fit_polynomial,
    fit_polynomial_with_order_fallback,
    select_drift_fit,
    select_order_by_aic,
)
from src.calibration.poisson_drift import PoissonDriftFit


def _times(n, step_s=60.0, start=None):
    start = start or datetime(2026, 3, 1, 10, 0, 0)
    return [start + timedelta(seconds=step_s * i) for i in range(n)]


def test_fit_polynomial_order1_recovers_known_slope_intercept():
    times = _times(10)
    # value = 100 + 0.01 * seconds_since_t0, no noise.
    seconds = np.array([(t - times[0]).total_seconds() for t in times])
    values = 100.0 + 0.01 * seconds

    fit = fit_polynomial(times, values, order=1, analyte="Al27")

    assert fit.order == 1
    assert fit.n_points == 10
    assert fit.coeffs[0] == pytest.approx(0.01, abs=1e-9)   # slope
    assert fit.coeffs[1] == pytest.approx(100.0, abs=1e-6)  # intercept
    assert fit.r_squared == pytest.approx(1.0, abs=1e-9)
    assert fit.residual_std == pytest.approx(0.0, abs=1e-9)


def test_fit_polynomial_order0_degenerates_to_mean():
    times = _times(5)
    values = np.array([10.0, 12.0, 8.0, 11.0, 9.0])
    fit = fit_polynomial(times, values, order=0)
    assert fit.coeffs[0] == pytest.approx(np.mean(values))


def test_predict_and_evaluate_agree():
    times = _times(6)
    seconds = np.array([(t - times[0]).total_seconds() for t in times])
    values = 5.0 + 2.0 * seconds
    fit = fit_polynomial(times, values, order=1)

    query_times = _times(3, step_s=30.0)
    predicted_method = fit.predict(query_times)
    predicted_func = evaluate(fit, query_times)
    assert np.allclose(predicted_method, predicted_func)


def test_fit_polynomial_raises_when_too_few_points():
    times = _times(2)
    values = np.array([1.0, 2.0])
    with pytest.raises(DriftFitError):
        fit_polynomial(times, values, order=2)


def test_fit_polynomial_with_order_fallback_uses_requested_order_when_enough_points():
    times = _times(10)
    seconds = np.array([(t - times[0]).total_seconds() for t in times])
    values = 100.0 + 0.01 * seconds
    fit = fit_polynomial_with_order_fallback(times, values, order=1, analyte="Al27")
    assert fit is not None
    assert fit.order == 1
    assert fit.coeffs[0] == pytest.approx(0.01, abs=1e-9)


def test_fit_polynomial_with_order_fallback_reduces_order_when_too_few_points():
    # The fallback loop requires order+2 points (not just fit_polynomial's
    # own order+1 minimum) -- 3 points can't support order=2 (needs 4) but
    # can support order=1 (needs exactly 3).
    times = _times(3)
    values = np.array([1.0, 3.0, 2.0])
    fit = fit_polynomial_with_order_fallback(times, values, order=2, analyte="Al27")
    assert fit is not None
    assert fit.order == 1


def test_fit_polynomial_with_order_fallback_returns_none_with_no_data():
    fit = fit_polynomial_with_order_fallback([], [], order=1)
    assert fit is None


def test_select_order_by_aic_picks_flat_model_for_flat_data():
    # AIC is a statistical selection procedure -- a single seed can go either
    # way on genuinely flat data (a tiny spurious slope sometimes clears the
    # 2-parameter penalty by chance), so test the majority behavior over
    # repeated trials rather than asserting one fixed seed's outcome.
    times = _times(20)
    rng = np.random.default_rng(1)
    n_reps = 50
    selected_order0 = 0
    for _ in range(n_reps):
        values = 10.0 + rng.normal(0, 0.01, 20)
        fit = select_order_by_aic(times, values, max_order=3)
        if fit.order == 0:
            selected_order0 += 1
    assert selected_order0 >= 35  # majority, allowing statistical slack


def test_select_order_by_aic_picks_linear_model_for_linear_data():
    times = _times(20)
    seconds = np.array([(t - times[0]).total_seconds() for t in times])
    rng = np.random.default_rng(2)
    values = 10.0 + 0.05 * seconds + rng.normal(0, 0.01, 20)
    fit = select_order_by_aic(times, values, max_order=3)
    assert fit.order == 1
    assert fit.coeffs[0] == pytest.approx(0.05, rel=0.05)


def test_select_drift_fit_fixed_matches_fit_polynomial():
    times = _times(10)
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    fit = select_drift_fit(times, values, method="fixed", order=1)
    direct = fit_polynomial(times, values, order=1)
    assert isinstance(fit, DriftFit)
    assert np.allclose(fit.coeffs, direct.coeffs)


def test_select_drift_fit_auto_aic_returns_drift_fit():
    times = _times(20)
    rng = np.random.default_rng(4)
    values = 5.0 + rng.normal(0, 0.01, 20)
    fit = select_drift_fit(times, values, method="auto_aic", max_order=3)
    assert isinstance(fit, DriftFit)
    assert fit.order == 0


def test_select_drift_fit_auto_poisson_lrt_returns_poisson_drift_fit():
    times = _times(50)
    tau = np.ones(50)
    rng = np.random.default_rng(5)
    counts = rng.poisson(0.3, size=50)
    fit = select_drift_fit(times, counts, counts=counts, tau_s=tau, method="auto_poisson_lrt", max_order=3)
    assert isinstance(fit, PoissonDriftFit)


def test_select_drift_fit_auto_poisson_lrt_requires_counts_and_tau():
    times = _times(5)
    with pytest.raises(ValueError):
        select_drift_fit(times, [1, 2, 3, 4, 5], method="auto_poisson_lrt")


def test_select_drift_fit_unknown_method_raises():
    times = _times(5)
    with pytest.raises(ValueError):
        select_drift_fit(times, [1, 2, 3, 4, 5], method="bogus")


def test_select_order_by_aic_stays_flat_on_gapped_sparse_clusters():
    """Regression test mirroring poisson_drift's cross-validation guard:
    three widely-gapped clusters of near-constant, noisy values (separate
    analytical sessions within one dataset). Plain AIC can pick a higher
    order that reduces in-sample residuals at the sparse clustered points
    while swinging unrealistically between them; the CV requirement must
    catch that and stay at order 0."""
    t0 = datetime(2026, 3, 18, 17, 10)
    times = []
    for block_start_min, n_files in [(0, 40), (130, 40), (250, 40)]:
        for i in range(n_files):
            times.append(t0 + timedelta(minutes=block_start_min + i * 2))
    rng = np.random.default_rng(11)
    values = 5.0 + rng.normal(0, 3.0, len(times))

    fit = select_order_by_aic(times, values, max_order=3)

    assert fit.order == 0
    probe = [t0 + timedelta(minutes=m) for m in range(0, 291, 2)]
    predicted = fit.predict(probe)
    span = float(np.max(values) - np.min(values))
    assert np.max(np.abs(predicted - np.median(values))) <= 10 * span


def test_cv_rss_for_order_returns_none_with_too_few_points():
    times = _times(3)
    assert _cv_rss_for_order(times, [1.0, 2.0, 1.0], order=2) is None


def test_predicted_values_are_stable_flags_wild_extrapolation():
    t0 = datetime(2026, 1, 1)
    times = [t0 + timedelta(minutes=m) for m in [0, 10, 20, 200, 210, 220, 400, 410, 420]]
    observed_values = [500.0] * len(times)

    unstable_fit = DriftFit(
        analyte="X", order=3, coeffs=np.array([4e-7, 0.0, 0.0, 500.0]),
        t0=t0, r_squared=1.0, n_points=len(times), residual_std=0.0,
    )
    assert _predicted_values_are_stable(unstable_fit, times, observed_values) is False

    flat_fit = DriftFit(
        analyte="X", order=0, coeffs=np.array([500.0]),
        t0=t0, r_squared=1.0, n_points=len(times), residual_std=0.0,
    )
    assert _predicted_values_are_stable(flat_fit, times, observed_values) is True
