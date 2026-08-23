"""Kernel estimation from real reference data (design spec Sec 6.1, routes
a and b): single-pulse decay fitting (washout tau, single- vs
double-exponential, AIC/BIC-gated) and edge-spread-function fitting (the
analytic EMG curve, eq. 5), plus a closure check comparing the two.

Route (c), in-situ estimation from unmixed fraction profiles, needs the
classification/unmixing machinery (a later stage of the six-stage scheme)
and isn't implemented here. The spec's bidirectional "scan the same edge
both directions" tau-sign-reversal validation is also not implemented --
secondary QC, deferred until real paired forward/reverse reference scans
are available to validate against.

Fitting engine: ``scipy.optimize.least_squares`` in log10-space for
strictly-positive, orders-of-magnitude parameters (tau, sigma) -- same
approach as ``src.common.diffusion.fit_tt_isothermal``. Model-selection
(single vs. double exponential) AIC/BIC follows
``src.calibration.drift.select_order_by_aic``'s formula
(``AIC = n*ln(RSS/n) + 2k``, ``BIC = n*ln(RSS/n) + k*ln(n)``). Outlier
flagging reimplements ``src.calibration.standards._mad_outlier_mask``'s
MAD/modified-z-score convention locally (that helper is private to
``standards.py``).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.stats import norm


@dataclass
class SinglePulseFit:
    model: str                 # "single" | "double"
    tau_s: float                # dominant (longer/slower) time constant
    amplitude: float             # amplitude paired with tau_s
    baseline: float
    tau2_s: float | None = None  # "double" only: the faster/shorter time constant
    amplitude2: float | None = None
    aic: float = float("nan")
    bic: float = float("nan")
    r_squared: float = float("nan")
    n_points: int = 0
    success: bool = False


@dataclass
class EdgeSpreadFit:
    mu_s: float
    sigma_s: float
    tau_s: float
    level_a: float
    level_b: float
    r_squared: float = float("nan")
    n_points: int = 0
    success: bool = False


@dataclass
class ClosureCheckResult:
    pulse_tau_s: float
    edge_tau_s: float
    relative_difference: float
    within_tolerance: bool
    tolerance: float


def _r_squared(signal: np.ndarray, predicted: np.ndarray) -> float:
    rss = float(np.sum((signal - predicted) ** 2))
    tss = float(np.sum((signal - np.mean(signal)) ** 2))
    if tss <= 0:
        return float("nan")
    return 1.0 - rss / tss


def _aic_bic(n: int, rss: float, k: int) -> tuple[float, float]:
    rss = max(rss, 1e-12)  # guard ln(0) for a near-perfect fit, same convention as drift.py
    aic = n * np.log(rss / n) + 2 * k
    bic = n * np.log(rss / n) + k * np.log(n)
    return float(aic), float(bic)


def _fit_single_exp(time_s: np.ndarray, signal: np.ndarray) -> tuple[SinglePulseFit, np.ndarray]:
    """m(t) = baseline + A*exp(-t/tau). Fits log10(tau) for numerical
    stability across orders-of-magnitude tau (see module docstring)."""
    n = len(time_s)
    baseline0 = float(np.median(signal[-max(1, n // 10):]))
    a0 = max(float(signal[0] - baseline0), 1e-6)
    half = baseline0 + a0 / 2.0
    below = np.where(signal <= half)[0]
    tau0 = float(time_s[below[0]] - time_s[0]) if len(below) else float(time_s[-1] - time_s[0]) / 3.0
    tau0 = max(tau0, 1e-6)

    def residual(x):
        log_tau, a, baseline = x
        tau = 10.0 ** log_tau
        return baseline + a * np.exp(-time_s / tau) - signal

    result = least_squares(
        residual, x0=[np.log10(tau0), a0, baseline0],
        bounds=([-12, 0, -np.inf], [12, np.inf, np.inf]),
    )
    log_tau, a, baseline = result.x
    tau = 10.0 ** log_tau
    predicted = baseline + a * np.exp(-time_s / tau)
    rss = float(np.sum(result.fun ** 2))
    fit = SinglePulseFit(
        model="single", tau_s=float(tau), amplitude=float(a), baseline=float(baseline),
        r_squared=_r_squared(signal, predicted), n_points=n, success=bool(result.success),
    )
    return fit, predicted


def _fit_double_exp(time_s: np.ndarray, signal: np.ndarray) -> tuple[SinglePulseFit, np.ndarray]:
    """m(t) = baseline + A1*exp(-t/tau1) + A2*exp(-t/tau2). tau1/tau2 are
    unordered during optimization (interchangeable) and sorted after, so
    the optimizer isn't fighting an artificial ordering constraint."""
    n = len(time_s)
    baseline0 = float(np.median(signal[-max(1, n // 10):]))
    a0 = max(float(signal[0] - baseline0), 1e-6)
    span = float(time_s[-1] - time_s[0]) or 1.0

    def residual(x):
        log_tau_a, aa, log_tau_b, ab, baseline = x
        tau_a, tau_b = 10.0 ** log_tau_a, 10.0 ** log_tau_b
        return baseline + aa * np.exp(-time_s / tau_a) + ab * np.exp(-time_s / tau_b) - signal

    x0 = [np.log10(span / 10.0), a0 / 2.0, np.log10(span / 2.0), a0 / 2.0, baseline0]
    result = least_squares(
        residual, x0=x0,
        bounds=([-12, 0, -12, 0, -np.inf], [12, np.inf, 12, np.inf, np.inf]),
    )
    log_tau_a, aa, log_tau_b, ab, baseline = result.x
    tau_a, tau_b = 10.0 ** log_tau_a, 10.0 ** log_tau_b
    # Sort so tau_s (reported "dominant") is the longer/slower constant --
    # the one that matters most for washout smearing over a full line.
    if tau_a >= tau_b:
        tau_s, amp, tau2_s, amp2 = tau_a, aa, tau_b, ab
    else:
        tau_s, amp, tau2_s, amp2 = tau_b, ab, tau_a, aa
    predicted = baseline + aa * np.exp(-time_s / tau_a) + ab * np.exp(-time_s / tau_b)
    fit = SinglePulseFit(
        model="double", tau_s=float(tau_s), amplitude=float(amp), baseline=float(baseline),
        tau2_s=float(tau2_s), amplitude2=float(amp2),
        r_squared=_r_squared(signal, predicted), n_points=n, success=bool(result.success),
    )
    return fit, predicted


def fit_single_pulse_decay(time_s, signal, model: str = "auto") -> SinglePulseFit:
    """Fits an isolated pulse's decay (spec Sec 6.1 route a). ``time_s``
    should start at/after the pulse peak (0 at the first decay sample) --
    this function fits the decay tail, not the rise.

    ``model``: ``"single"``/``"double"`` force that model; ``"auto"``
    (default) fits both and accepts the double-exponential model only when
    *both* AIC and BIC prefer it over the single-exponential fit (see
    module docstring) -- otherwise reports the single-exponential fit.
    """
    time_s = np.asarray(time_s, dtype=float)
    signal = np.asarray(signal, dtype=float)
    if len(time_s) != len(signal):
        raise ValueError(f"time_s and signal must be the same length, got {len(time_s)} and {len(signal)}.")
    if len(time_s) < 4:
        raise ValueError("At least 4 points are needed to fit a decay curve.")
    n = len(time_s)

    single_fit, single_pred = _fit_single_exp(time_s, signal)
    if model == "single":
        aic, bic = _aic_bic(n, float(np.sum((signal - single_pred) ** 2)), k=3)
        single_fit.aic, single_fit.bic = aic, bic
        return single_fit

    double_fit, double_pred = _fit_double_exp(time_s, signal)
    aic_s, bic_s = _aic_bic(n, float(np.sum((signal - single_pred) ** 2)), k=3)
    aic_d, bic_d = _aic_bic(n, float(np.sum((signal - double_pred) ** 2)), k=5)
    single_fit.aic, single_fit.bic = aic_s, bic_s
    double_fit.aic, double_fit.bic = aic_d, bic_d

    if model == "double":
        return double_fit

    # "auto": require both criteria to prefer the double-exponential model.
    if aic_d < aic_s and bic_d < bic_s:
        return double_fit
    return single_fit


def fit_single_pulse_decay_per_analyte(
    time_s, signal_df: pd.DataFrame, model: str = "auto",
) -> dict[str, SinglePulseFit]:
    """Per-analyte version of :func:`fit_single_pulse_decay` -- spec Sec 6.1's
    "test whether h is element-dependent... report per-analyte fits and
    flag outliers" (outlier flagging itself is :func:`flag_tau_outliers`,
    run separately over this function's output)."""
    fits = {}
    for analyte in signal_df.columns:
        try:
            fits[analyte] = fit_single_pulse_decay(time_s, signal_df[analyte].to_numpy(), model=model)
        except ValueError:
            continue
    return fits


def flag_tau_outliers(fits: dict[str, SinglePulseFit], threshold: float = 3.5) -> dict[str, bool]:
    """MAD/modified-z-score outlier screen across analytes' fitted
    ``tau_s`` -- flags memory-prone deviants (Hg, B, Au-type elements whose
    washout genuinely differs from the bulk aerosol-transport behavior).
    Same convention/threshold as ``standards._mad_outlier_mask`` (Iglewicz
    & Hoaglin, threshold=3.5); requires at least 4 successful fits to
    attempt rejection, same reasoning as that function.

    Returns ``{analyte: True}`` for an outlier, ``{analyte: False}``
    otherwise -- analytes with a failed fit (``success=False``) are
    included as ``False`` (not flagged as an outlier; a failed fit is a
    different problem, not an element-dependent-tau finding).
    """
    successful = {a: f for a, f in fits.items() if f.success}
    analytes = list(successful)
    if len(analytes) < 4:
        return {a: False for a in fits}

    tau_values = np.array([successful[a].tau_s for a in analytes])
    median = float(np.median(tau_values))
    mad = float(np.median(np.abs(tau_values - median)))
    flags = {a: False for a in fits}
    if mad == 0:
        return flags
    modified_z = 0.6745 * (tau_values - median) / mad
    for analyte, z in zip(analytes, modified_z):
        flags[analyte] = bool(abs(z) > threshold)
    return flags


def _emg_cdf(t: np.ndarray, mu: float, sigma: float, tau: float) -> np.ndarray:
    """Exponentially-modified-Gaussian CDF (closed form, eq. 5's integral) --
    F(t) = Phi(u) - exp(-u*(sigma/tau) + (sigma/tau)^2/2) * Phi(u - sigma/tau),
    u = (t-mu)/sigma. The exponent is clipped to +/-700 (float64's overflow
    boundary) -- for realistic edge-scan spans this is never active at the
    optimum, only guards against a transient overflow while ``least_squares``
    explores an early, far-from-optimal parameter guess.
    """
    u = (t - mu) / sigma
    exponent = np.clip(-(t - mu) / tau + (sigma ** 2) / (2 * tau ** 2), -700, 700)
    return norm.cdf(u) - np.exp(exponent) * norm.cdf(u - sigma / tau)


def fit_edge_spread(time_s, signal) -> EdgeSpreadFit:
    """Fits a sharp material-couple edge scan to the analytic EMG curve
    (spec Sec 6.1 route b, eq. 5's cumulative/edge-response form):
    ``level_a + (level_b - level_a) * EMG_CDF(t; mu, sigma, tau)``.

    Free parameters (mu, sigma, tau, level_a, level_b), fit in the same
    time units as ``time_s`` -- see module docstring on why this stays in
    time (not spatial-pixel) units, and how that makes :func:`check_closure`
    a direct comparison against :func:`fit_single_pulse_decay`'s tau.
    """
    time_s = np.asarray(time_s, dtype=float)
    signal = np.asarray(signal, dtype=float)
    if len(time_s) != len(signal):
        raise ValueError(f"time_s and signal must be the same length, got {len(time_s)} and {len(signal)}.")
    n = len(time_s)
    if n < 6:
        raise ValueError("At least 6 points are needed to fit an edge-spread curve.")

    edge_frac = max(1, n // 10)
    level_a0 = float(np.mean(signal[:edge_frac]))
    level_b0 = float(np.mean(signal[-edge_frac:]))
    half = (level_a0 + level_b0) / 2.0
    crossing = np.where((signal - half) * np.sign(level_b0 - level_a0) >= 0)[0]
    mu0 = float(time_s[crossing[0]]) if len(crossing) else float(np.median(time_s))
    span = float(time_s[-1] - time_s[0]) or 1.0
    sigma0 = span / 10.0
    tau0 = span / 10.0

    def residual(x):
        mu, log_sigma, log_tau, level_a, level_b = x
        sigma, tau = 10.0 ** log_sigma, 10.0 ** log_tau
        model = level_a + (level_b - level_a) * _emg_cdf(time_s, mu, sigma, tau)
        return model - signal

    result = least_squares(
        residual,
        x0=[mu0, np.log10(sigma0), np.log10(tau0), level_a0, level_b0],
        bounds=(
            [time_s[0], -12, -12, -np.inf, -np.inf],
            [time_s[-1], 12, 12, np.inf, np.inf],
        ),
    )
    mu, log_sigma, log_tau, level_a, level_b = result.x
    sigma, tau = 10.0 ** log_sigma, 10.0 ** log_tau
    predicted = level_a + (level_b - level_a) * _emg_cdf(time_s, mu, sigma, tau)

    return EdgeSpreadFit(
        mu_s=float(mu), sigma_s=float(sigma), tau_s=float(tau),
        level_a=float(level_a), level_b=float(level_b),
        r_squared=_r_squared(signal, predicted), n_points=n, success=bool(result.success),
    )


def check_closure(pulse_fit: SinglePulseFit, edge_fit: EdgeSpreadFit, tolerance: float = 0.3) -> ClosureCheckResult:
    """Spec Sec 6.1's mandatory closure check: the edge-spread fit's tau
    (route b) should agree with the single-pulse fit's tau (route a) within
    ``tolerance`` (relative difference) -- both fits work in the same time
    units (see module docstring), so this is a direct comparison, no unit
    conversion needed.
    """
    rel_diff = abs(edge_fit.tau_s - pulse_fit.tau_s) / pulse_fit.tau_s if pulse_fit.tau_s else float("inf")
    return ClosureCheckResult(
        pulse_tau_s=pulse_fit.tau_s, edge_tau_s=edge_fit.tau_s,
        relative_difference=float(rel_diff), within_tolerance=rel_diff <= tolerance, tolerance=tolerance,
    )
