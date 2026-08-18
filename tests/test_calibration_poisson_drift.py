"""Poisson GLM (IRLS) drift fitting + incremental LRT order selection.

Statistical test cases use reduced repetition counts (relative to the design
spec's suggested 200/100) to keep runtime fast while still meaningfully
validating the selection behavior -- pass-rate thresholds are scaled
proportionally.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.poisson_drift import (
    PoissonFitError,
    _cv_deviance_for_order,
    _predicted_rate_is_stable,
    detect_poisson_file_outliers,
    fit_poisson_glm,
    select_poisson_order_lrt,
)


def _times(n, step_s=60.0, start=None):
    start = start or datetime(2026, 3, 1, 10, 0, 0)
    return [start + timedelta(seconds=step_s * i) for i in range(n)]


def test_order0_closed_form_matches_pooled_rate():
    times = _times(8)
    counts = np.array([0, 1, 0, 2, 1, 0, 0, 1])
    tau = np.ones(8)
    fit = fit_poisson_glm(times, counts, tau, order=0)
    assert fit is not None
    assert fit.model == "constant"
    rate_hat = np.exp(fit.coeffs[0])
    assert rate_hat == pytest.approx(5.0 / 8.0, rel=1e-9)
    # predict() is constant everywhere, at the pooled rate.
    predicted = fit.predict(_times(3, step_s=3600.0))
    assert np.allclose(predicted, 5.0 / 8.0)


def test_detect_poisson_file_outliers_catches_whole_file_contamination():
    """Regression test: a whole-file background contamination event (every
    row in that one file's window uniformly elevated, so there's no
    internal row-to-row anomaly for the per-row screen in background.py to
    catch) must be flagged at the session level, since left unscreened it
    can single-handedly dominate the fitted session rate even though the
    rest of the session sits near zero."""
    rng = np.random.default_rng(5)
    n_files = 116
    true_tau = 0.2803
    tau_s = np.full(n_files, true_tau * 30)
    counts = np.zeros(n_files)
    low_idx = rng.choice(n_files, size=5, replace=False)
    for i, idx in enumerate(low_idx):
        counts[idx] = [2, 2, 3, 5, 8][i]
    contam_idx = 80
    counts[contam_idx] = 420  # whole file uniformly elevated -- not a single spurious row

    mask = detect_poisson_file_outliers(counts, tau_s)
    assert mask[contam_idx]
    assert mask.sum() == 1
    assert not mask[low_idx].any()


def test_detect_poisson_file_outliers_no_false_positives_on_genuine_sparse_counts():
    """The 5 genuine low-count files above (no contamination) must never be
    flagged just for being nonzero among a mostly-zero session -- same
    zero-inflation lesson as background.detect_row_outliers's order=0 path."""
    rng = np.random.default_rng(5)
    n_files = 116
    true_tau = 0.2803
    tau_s = np.full(n_files, true_tau * 30)
    counts = np.zeros(n_files)
    low_idx = rng.choice(n_files, size=5, replace=False)
    for i, idx in enumerate(low_idx):
        counts[idx] = [2, 2, 3, 5, 8][i]

    mask = detect_poisson_file_outliers(counts, tau_s)
    assert not mask.any()


def test_detect_poisson_file_outliers_too_few_nonzero_flags_nothing():
    counts = np.array([0, 0, 0, 1, 0, 0])
    tau_s = np.ones(6)
    mask = detect_poisson_file_outliers(counts, tau_s)
    assert not mask.any()


def test_detect_poisson_file_outliers_catches_sparse_trace_element_contamination():
    """Regression test: a very sparse trace element (e.g. Lu175/Eu153 on
    real data -- only 2-3 nonzero-count files in the whole session) must
    still have a severe contamination event caught. The earlier Huber-IRLS
    design required >=4 nonzero files to attempt any screening at all and
    silently let this sail through -- exactly what real data showed."""
    n_files = 116
    tau_s = np.full(n_files, 0.2803 * 30)
    counts = np.zeros(n_files)
    counts[10] = 1
    counts[20] = 2
    counts[50] = 300  # severe whole-file contamination
    mask = detect_poisson_file_outliers(counts, tau_s)
    assert mask[50]
    assert mask.sum() == 1
    assert not mask[10] and not mask[20]


def test_detect_poisson_file_outliers_catches_multiple_simultaneous_outliers():
    """Regression test: two independently-contaminated files among a
    handful of genuine low counts must both be caught, even though together
    they're no longer a small minority of the (already tiny) nonzero-count
    subset. The earlier Huber-IRLS design masked this case -- the robust
    fit partially converged toward both instead of rejecting either."""
    n_files = 116
    tau_s = np.full(n_files, 0.2803 * 30)
    counts = np.zeros(n_files)
    counts[10] = 1
    counts[20] = 2
    counts[50] = 300
    counts[70] = 250
    mask = detect_poisson_file_outliers(counts, tau_s)
    assert mask[50] and mask[70]
    assert mask.sum() == 2
    assert not mask[10] and not mask[20]


def test_select_poisson_order_lrt_excluding_file_outlier_matches_clean_session():
    """End-to-end: fitting with the contaminated file pre-excluded (as
    fit_session_background_drift now does) should land close to fitting the
    same session with no contamination injected at all -- confirms the
    screen neutralizes the outlier's influence on the regression, not just
    on its own detection."""
    rng = np.random.default_rng(5)
    n_files = 116
    true_tau = 0.2803
    tau_s = np.full(n_files, true_tau * 30)
    t0 = datetime(2026, 3, 1, 10, 0, 0)
    times = _times(n_files, step_s=120.0, start=t0)

    counts_clean = np.zeros(n_files)
    low_idx = rng.choice(n_files, size=5, replace=False)
    for i, idx in enumerate(low_idx):
        counts_clean[idx] = [2, 2, 3, 5, 8][i]

    counts_contaminated = counts_clean.copy()
    contam_idx = 80
    counts_contaminated[contam_idx] = 420

    fit_clean = select_poisson_order_lrt(times, counts_clean, tau_s, analyte="Gd157", max_order=3)
    mask = detect_poisson_file_outliers(counts_contaminated, tau_s)
    keep = ~mask
    fit_screened = select_poisson_order_lrt(
        [t for t, k in zip(times, keep) if k], counts_contaminated[keep], tau_s[keep],
        analyte="Gd157", max_order=3,
    )
    assert fit_screened.predict([t0])[0] == pytest.approx(fit_clean.predict([t0])[0], rel=0.05)

    # Without screening, the contaminated fit must land far higher than the clean one.
    fit_unscreened = select_poisson_order_lrt(times, counts_contaminated, tau_s, analyte="Gd157", max_order=3)
    assert fit_unscreened.predict([t0])[0] > 3 * fit_clean.predict([t0])[0]


def test_fit_poisson_glm_returns_none_with_too_few_points_for_order():
    times = _times(3)
    fit = fit_poisson_glm(times, [1, 2, 1], [1, 1, 1], order=2)
    assert fit is None


def test_fit_poisson_glm_returns_none_for_ill_conditioned_design():
    # 5 points but 4 share an identical time -> effectively 2 distinct time
    # points feeding an order-3 (4-coefficient) fit -> rank-deficient design.
    base = datetime(2026, 3, 1, 10, 0, 0)
    times = [base, base + timedelta(seconds=10), base + timedelta(seconds=10),
             base + timedelta(seconds=10), base + timedelta(seconds=10)]
    counts = [0, 1, 2, 1, 0]
    tau = [1.0] * 5
    fit = fit_poisson_glm(times, counts, tau, order=3)
    assert fit is None


def test_lrt_rejects_drift_on_flat_low_count_data():
    rng = np.random.default_rng(42)
    n_reps = 100
    n_windows = 100
    times = _times(n_windows, step_s=60.0)
    tau = np.ones(n_windows)
    selected_order0 = 0
    for rep in range(n_reps):
        counts = rng.poisson(0.2, size=n_windows)
        fit = select_poisson_order_lrt(times, counts, tau, max_order=3)
        if fit.order == 0:
            selected_order0 += 1
    assert selected_order0 >= 90  # expect ~95%, allow some statistical slack


def test_lrt_detects_injected_linear_drift():
    rng = np.random.default_rng(7)
    n_reps = 50
    n_windows = 100
    times = _times(n_windows, step_s=60.0)
    tau = np.ones(n_windows)
    t_seconds = np.array([(t - times[0]).total_seconds() for t in times])
    t_scale = t_seconds.max()

    a, b = 50.0, 30.0  # rate goes from 50 to 80 counts/s-equivalent (lambda*tau) over the session
    detected = 0
    for rep in range(n_reps):
        rate = a + b * (t_seconds / t_scale)
        counts = rng.poisson(rate * tau)
        fit = select_poisson_order_lrt(times, counts, tau, max_order=3)
        if fit.order >= 1:
            detected += 1
    assert detected >= 45  # expect ~95%, allow some statistical slack


def test_high_count_regime_matches_ols_within_tolerance():
    # lambda*tau ~ 1000 per window with mild linear drift -- Poisson GLM
    # should reproduce the OLS fit closely (large-mu Gaussian limit).
    rng = np.random.default_rng(11)
    n_windows = 20
    times = _times(n_windows, step_s=600.0)
    tau = np.ones(n_windows)
    t_seconds = np.array([(t - times[0]).total_seconds() for t in times])
    t_scale = t_seconds.max()
    true_rate = 1000.0 + 200.0 * (t_seconds / t_scale)
    counts = rng.poisson(true_rate)

    poisson_fit = fit_poisson_glm(times, counts, tau, order=1)
    assert poisson_fit is not None
    assert poisson_fit.converged

    ols_coeffs = np.polyfit(t_seconds / t_scale, counts, 1)  # highest power first
    ols_predicted = np.polyval(ols_coeffs, t_seconds / t_scale)
    poisson_predicted = poisson_fit.predict(times)

    assert poisson_predicted == pytest.approx(ols_predicted, rel=0.05)


def test_select_poisson_order_lrt_raises_when_no_data():
    with pytest.raises(PoissonFitError):
        select_poisson_order_lrt([], [], [])


def test_select_poisson_order_lrt_stays_flat_on_gapped_sparse_clusters():
    """Regression test for the real-data failure this cross-validation
    requirement exists to catch: three widely-gapped clusters of files
    (separate analytical sessions within one dataset) with near-zero
    background counts. A plain LRT can pass a higher order by slightly
    improving the in-sample fit at the sparse clustered points while the
    fitted curve swings unconstrained in the gaps between them (which,
    through the Poisson GLM's log link, turns into an unrealistic CPS
    value). Cross-validated deviance must catch that the higher order
    doesn't actually generalize, and stay at order 0."""
    rng = np.random.default_rng(11)
    t0 = datetime(2026, 3, 18, 17, 10)
    times = []
    for block_start_min, n_files in [(0, 40), (130, 40), (250, 40)]:
        for i in range(n_files):
            times.append(t0 + timedelta(minutes=block_start_min + i * 2))
    tau_s = np.full(len(times), 0.3)
    counts = rng.poisson(0.3, len(times)).astype(float)

    fit = select_poisson_order_lrt(times, counts, tau_s, analyte="Ho165", max_order=3)

    assert fit.order == 0
    probe = [t0 + timedelta(minutes=m) for m in range(0, 291, 2)]
    predicted = fit.predict(probe)
    observed_max_rate = float(np.max(counts / tau_s))
    assert np.max(predicted) <= 10 * observed_max_rate


def test_cv_deviance_for_order_returns_none_with_too_few_points():
    times = _times(3)
    assert _cv_deviance_for_order(times, [1, 2, 1], [1, 1, 1], order=2) is None


def test_predicted_rate_is_stable_flags_wild_extrapolation():
    from src.calibration.poisson_drift import PoissonDriftFit

    t0 = datetime(2026, 1, 1)
    times = [t0 + timedelta(minutes=m) for m in [0, 10, 20, 200, 210, 220, 400, 410, 420]]
    t_scale = 420 * 60.0

    unstable_fit = PoissonDriftFit(
        analyte="X", order=3, model="poly(3)", coeffs=np.array([0.0, 0.0, 0.0, 40.0]),
        t0=t0, t_scale=t_scale, deviance=0.0, n_points=len(times),
        drift_pvalue=None, tau_total_s=1.0, converged=True,
    )
    assert _predicted_rate_is_stable(unstable_fit, times, observed_max_rate=1.0) is False

    flat_fit = PoissonDriftFit(
        analyte="X", order=0, model="constant", coeffs=np.array([0.0]),
        t0=t0, t_scale=t_scale, deviance=0.0, n_points=len(times),
        drift_pvalue=None, tau_total_s=1.0, converged=True,
    )
    assert _predicted_rate_is_stable(flat_fit, times, observed_max_rate=1.0) is True
