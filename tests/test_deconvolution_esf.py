"""Unit tests for src/deconvolution/esf.py (kernel estimation from real
reference data: single-pulse decay fitting, edge-spread-function fitting,
closure check).

Pure Python/numpy/scipy -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import cumulative_trapezoid
from scipy.special import erfc

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.deconvolution.esf import (
    ClosureCheckResult, EdgeSpreadFit, SinglePulseFit, _emg_cdf,
    check_closure, fit_edge_spread, fit_single_pulse_decay,
    fit_single_pulse_decay_per_analyte, flag_tau_outliers,
)


# ------------------------------------------------------------------
# Single-pulse decay fitting
# ------------------------------------------------------------------

def _single_exp_decay(time_s, tau_s, amplitude=1000.0, baseline=50.0, noise=0.0, seed=0):
    signal = baseline + amplitude * np.exp(-time_s / tau_s)
    if noise:
        rng = np.random.default_rng(seed)
        signal = signal + rng.normal(0, noise, size=len(time_s))
    return signal


def _double_exp_decay(time_s, tau1_s, tau2_s, amp1=700.0, amp2=300.0, baseline=50.0, noise=0.0, seed=0):
    signal = baseline + amp1 * np.exp(-time_s / tau1_s) + amp2 * np.exp(-time_s / tau2_s)
    if noise:
        rng = np.random.default_rng(seed)
        signal = signal + rng.normal(0, noise, size=len(time_s))
    return signal


def test_fit_single_pulse_decay_recovers_known_tau_noiseless():
    t = np.linspace(0, 20, 100)
    signal = _single_exp_decay(t, tau_s=3.0, amplitude=800.0, baseline=40.0)
    fit = fit_single_pulse_decay(t, signal, model="single")
    assert fit.success
    assert fit.tau_s == pytest.approx(3.0, rel=1e-3)
    assert fit.amplitude == pytest.approx(800.0, rel=1e-3)
    assert fit.baseline == pytest.approx(40.0, abs=1e-2)
    assert fit.r_squared > 0.999


def test_fit_single_pulse_decay_recovers_known_tau_with_noise():
    t = np.linspace(0, 20, 200)
    signal = _single_exp_decay(t, tau_s=4.0, amplitude=1000.0, baseline=50.0, noise=5.0, seed=1)
    fit = fit_single_pulse_decay(t, signal, model="single")
    assert fit.success
    assert fit.tau_s == pytest.approx(4.0, rel=0.1)
    assert fit.r_squared > 0.9


def test_auto_model_selection_picks_single_on_single_exponential_data():
    """Guards against overfitting: truly single-exponential data (plus
    modest noise) should not spuriously prefer the double model."""
    t = np.linspace(0, 20, 200)
    signal = _single_exp_decay(t, tau_s=3.5, amplitude=900.0, baseline=45.0, noise=3.0, seed=2)
    fit = fit_single_pulse_decay(t, signal, model="auto")
    assert fit.model == "single"


def test_auto_model_selection_picks_double_on_double_exponential_data():
    t = np.linspace(0, 30, 300)
    signal = _double_exp_decay(t, tau1_s=0.5, tau2_s=8.0, amp1=600.0, amp2=400.0, baseline=30.0, noise=2.0, seed=3)
    fit = fit_single_pulse_decay(t, signal, model="auto")
    assert fit.model == "double"
    # dominant (reported) tau_s is the longer/slower constant
    assert fit.tau_s == pytest.approx(8.0, rel=0.15)
    assert fit.tau2_s == pytest.approx(0.5, rel=0.3)


def test_fit_single_pulse_decay_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        fit_single_pulse_decay(np.arange(10), np.arange(5))


def test_fit_single_pulse_decay_rejects_too_few_points():
    with pytest.raises(ValueError):
        fit_single_pulse_decay(np.arange(3), np.arange(3))


def test_fit_single_pulse_decay_per_analyte():
    t = np.linspace(0, 20, 100)
    import pandas as pd
    df = pd.DataFrame({
        "Si29": _single_exp_decay(t, tau_s=2.0),
        "Ca43": _single_exp_decay(t, tau_s=5.0),
    })
    fits = fit_single_pulse_decay_per_analyte(t, df, model="single")
    assert set(fits) == {"Si29", "Ca43"}
    assert fits["Si29"].tau_s == pytest.approx(2.0, rel=1e-2)
    assert fits["Ca43"].tau_s == pytest.approx(5.0, rel=1e-2)


# ------------------------------------------------------------------
# Outlier flagging
# ------------------------------------------------------------------

def _fake_fit(tau_s):
    return SinglePulseFit(model="single", tau_s=tau_s, amplitude=1.0, baseline=0.0, success=True)


def test_flag_tau_outliers_catches_planted_deviant():
    fits = {
        "Si29": _fake_fit(2.0), "Ca43": _fake_fit(2.1), "Al27": _fake_fit(1.9),
        "Mg24": _fake_fit(2.05), "Hg202": _fake_fit(50.0),  # memory-prone deviant
    }
    flags = flag_tau_outliers(fits)
    assert flags["Hg202"] is True
    assert flags["Si29"] is False
    assert flags["Ca43"] is False


def test_flag_tau_outliers_requires_at_least_four_fits():
    fits = {"Si29": _fake_fit(2.0), "Ca43": _fake_fit(50.0)}
    flags = flag_tau_outliers(fits)
    assert all(v is False for v in flags.values())


def test_flag_tau_outliers_ignores_failed_fits():
    fits = {
        "Si29": _fake_fit(2.0), "Ca43": _fake_fit(2.1), "Al27": _fake_fit(1.9), "Mg24": _fake_fit(2.05),
        "Bad": SinglePulseFit(model="single", tau_s=999.0, amplitude=1.0, baseline=0.0, success=False),
    }
    flags = flag_tau_outliers(fits)
    assert flags["Bad"] is False


# ------------------------------------------------------------------
# Edge-spread-function fitting
# ------------------------------------------------------------------

def _emg_pdf_reference(s, mu, sigma, tau):
    """Direct implementation of spec eq. (5), independent of esf.py's
    closed-form CDF -- used to build ground-truth edge data by numerical
    integration, so the CDF test below is a genuine correctness check, not
    a tautological self-consistency check."""
    term1 = 1.0 / (2.0 * tau)
    term2 = np.exp((sigma ** 2) / (2 * tau ** 2) - (s - mu) / tau)
    term3 = erfc(sigma / (np.sqrt(2) * tau) - (s - mu) / (np.sqrt(2) * sigma))
    return term1 * term2 * term3


def test_emg_cdf_matches_numerical_integral_of_eq5_pdf():
    mu, sigma, tau = 10.0, 1.5, 2.0
    s = np.linspace(-30, 50, 20000)
    pdf = _emg_pdf_reference(s, mu, sigma, tau)
    numerical_cdf = cumulative_trapezoid(pdf, s, initial=0.0)

    check_points = np.array([0.0, 5.0, 10.0, 15.0, 20.0, 30.0])
    closed_form = _emg_cdf(check_points, mu, sigma, tau)
    numerical_at_points = np.interp(check_points, s, numerical_cdf)

    assert np.allclose(closed_form, numerical_at_points, atol=5e-3)


def test_fit_edge_spread_recovers_known_parameters_noiseless():
    mu, sigma, tau = 15.0, 1.0, 2.0
    t = np.linspace(0, 30, 300)
    signal = 100.0 + (900.0 - 100.0) * _emg_cdf(t, mu, sigma, tau)
    fit = fit_edge_spread(t, signal)
    assert fit.success
    assert fit.mu_s == pytest.approx(mu, abs=0.2)
    assert fit.sigma_s == pytest.approx(sigma, rel=0.15)
    assert fit.tau_s == pytest.approx(tau, rel=0.15)
    assert fit.level_a == pytest.approx(100.0, rel=0.05)
    assert fit.level_b == pytest.approx(900.0, rel=0.05)
    assert fit.r_squared > 0.999


def test_fit_edge_spread_recovers_known_parameters_with_noise():
    mu, sigma, tau = 12.0, 1.2, 3.0
    t = np.linspace(0, 30, 400)
    rng = np.random.default_rng(4)
    signal = 50.0 + (800.0 - 50.0) * _emg_cdf(t, mu, sigma, tau) + rng.normal(0, 8.0, size=len(t))
    fit = fit_edge_spread(t, signal)
    assert fit.success
    assert fit.tau_s == pytest.approx(tau, rel=0.2)
    assert fit.r_squared > 0.95


def test_fit_edge_spread_rejects_too_few_points():
    with pytest.raises(ValueError):
        fit_edge_spread(np.arange(4), np.arange(4))


def test_fit_edge_spread_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        fit_edge_spread(np.arange(10), np.arange(5))


# ------------------------------------------------------------------
# Closure check
# ------------------------------------------------------------------

def test_check_closure_passes_on_matching_tau():
    pulse_fit = _fake_fit(3.0)
    edge_fit = EdgeSpreadFit(mu_s=0.0, sigma_s=1.0, tau_s=3.1, level_a=0.0, level_b=1.0, success=True)
    result = check_closure(pulse_fit, edge_fit, tolerance=0.3)
    assert result.within_tolerance is True
    assert result.relative_difference == pytest.approx(0.1 / 3.0, rel=1e-6)


def test_check_closure_fails_on_mismatched_tau():
    pulse_fit = _fake_fit(3.0)
    edge_fit = EdgeSpreadFit(mu_s=0.0, sigma_s=1.0, tau_s=10.0, level_a=0.0, level_b=1.0, success=True)
    result = check_closure(pulse_fit, edge_fit, tolerance=0.3)
    assert result.within_tolerance is False
