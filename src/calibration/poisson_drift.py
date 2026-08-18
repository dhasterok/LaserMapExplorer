"""Poisson GLM drift fitting via IRLS, with incremental likelihood-ratio-test
order selection. Hand-rolled (no statsmodels dependency, unavailable in this
project) per poisson_background_spec.md Section 4.

Model per analyte: n_i ~ Poisson(mu_i), log(mu_i) = log(tau_i) + X_i . beta,
where n_i is recovered integer counts in window i, tau_i its counting time.
Note beta itself parameterizes log(rate in CPS) directly (mu_i/tau_i =
exp(X_i . beta), independent of any one window's tau) -- so `.predict()`
returns a rate in CPS with no tau needed at prediction time, exactly like
``drift.DriftFit.predict()``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.stats import chi2


class PoissonFitError(ValueError):
    """Raised when there isn't enough data to attempt any Poisson GLM fit
    (not even the order-0 constant model)."""


def _to_seconds(times, t0: datetime) -> np.ndarray:
    ts = pd.to_datetime(list(times))
    t0_ts = pd.Timestamp(t0)
    return (ts - t0_ts).total_seconds().to_numpy(dtype=float)


def _poisson_deviance(n: np.ndarray, mu: np.ndarray) -> float:
    """2*sum(n*log(n/mu) - (n-mu)), with the n*log(n/mu) term defined as 0 when n=0.

    Computed only over n>0 entries (rather than `np.where` over the whole
    array) so 0*log(0) never gets evaluated -- `np.where` evaluates both
    branches eagerly and would raise spurious divide-by-zero/invalid-value
    runtime warnings even though the masked-out result is correct.
    """
    mu_safe = np.maximum(mu, 1e-300)
    term = np.zeros_like(n, dtype=float)
    positive = n > 0
    term[positive] = n[positive] * np.log(n[positive] / mu_safe[positive])
    return float(2.0 * np.sum(term - (n - mu)))


@dataclass
class PoissonDriftFit:
    analyte: str
    order: int                     # 0 = constant
    model: str                      # "constant" | "poly(k)"
    coeffs: np.ndarray              # length order+1, np.vander(..., increasing=True)-compatible
    t0: datetime
    t_scale: float                    # seconds; standardized time = (t - t0) / t_scale
    deviance: float
    n_points: int
    drift_pvalue: float | None        # LRT p-value vs. the previous (order-1) model; None for order 0
    tau_total_s: float
    converged: bool

    def predict(self, times) -> np.ndarray:
        """Predicted background rate in CPS at the given times."""
        s = _to_seconds(times, self.t0) / self.t_scale
        x = np.vander(s, len(self.coeffs), increasing=True)
        eta = np.clip(x @ self.coeffs, -700.0, 30.0)
        return np.exp(eta)


def detect_poisson_file_outliers(counts, tau_s, ratio_threshold: float = 15.0, min_other_nonzero: int = 2) -> np.ndarray:
    """Robust, session-wide file-level outlier screen for Poisson background
    counts: flags a whole *file* whose recovered rate is grossly
    inconsistent with the rest of the session's nonzero-count files.

    This is a different failure mode than ``background.detect_row_outliers``
    catches: that screen only compares *rows within one file's own window*
    against each other, so a file whose entire background window is
    uniformly elevated (a whole-file contamination event, or any other
    session-level anomaly) has no internal row-to-row contrast to flag it by
    and sails through untouched. Left unfiltered, a single such file can
    dominate the session's fitted background rate even though the vast
    majority of files sit near zero -- confirmed against real data: one
    such file pulled a session's fitted order-0 rate above where 94% of the
    session's own files actually sat.

    Method: **leave-one-out median-ratio test**, restricted to nonzero-count
    files exactly as ``background.detect_row_outliers``'s ``order=0`` path
    restricts its own screen to nonzero rows (a zero-count file can never be
    the thing inflating a rate estimate, so it's never a candidate and never
    part of any reference). For each nonzero-count file i, with rate
    ``r_i = n_i / tau_i``, compare it to the *median* of every other
    nonzero-count file's rate (excluding i itself) -- flagged as an outlier
    when ``r_i`` is at least ``ratio_threshold`` times that reference.
    Needs at least ``min_other_nonzero`` *other* nonzero-count files to
    judge any one file by; below that, nothing is flagged for it (not
    enough information, mirrors this project's other minimum-points
    guards).

    An earlier version of this fit a single robust (Huber-reweighted) rate
    to the whole session and flagged files whose residual against it was
    extreme. Two failure modes on real data killed that approach: (1) very
    sparse trace elements with only 2-3 nonzero-count files in the whole
    session never had enough points to estimate a robust scale at all, so a
    severe contamination event went completely unscreened; (2) when *two or
    more* files were anomalously elevated, they were no longer a strict
    minority of the (already tiny) nonzero-count subset, so the robust fit
    partially converged *toward* them instead of rejecting them (classic
    M-estimator masking). The leave-one-out design here sidesteps both:
    judging file i against the median of the *other* nonzero files works
    with as few as 2 other files (no scale-estimation minimum beyond that),
    and stays correct with multiple simultaneous outliers since a median
    isn't dragged by any one (or, with 3+ others, any minority of) excluded
    file the way an iteratively-refit rate could be -- verified against
    both scenarios directly: a lone severe contamination event among just 2
    other genuine low-count files, and two simultaneous severely-elevated
    files among a handful of genuine ones, are both now correctly isolated
    (neither was, under the earlier approach).

    ``ratio_threshold=15`` is deliberately high: a session can legitimately
    have a small handful of nonzero-count files spanning a real few-fold
    range (e.g. counts of 2, 2, 3, 5, 8 across five files, nothing to do
    with each other -- confirmed against real data) without any of them
    being contamination, and this is a session-wide, one-shot decision
    affecting every row of a whole file, so it's biased toward requiring a
    much starker, orders-of-magnitude departure before excluding one.

    Returns a boolean array the length of ``counts`` (``True`` = outlier).
    """
    n_arr = np.asarray(counts, dtype=float)
    tau_arr = np.asarray(tau_s, dtype=float)
    n = len(n_arr)
    nonzero_idx = np.flatnonzero(n_arr > 0)
    outlier = np.zeros(n, dtype=bool)
    if len(nonzero_idx) < min_other_nonzero + 1:
        return outlier

    rates = np.full(n, np.nan)
    rates[nonzero_idx] = n_arr[nonzero_idx] / np.maximum(tau_arr[nonzero_idx], 1e-300)
    for i in nonzero_idx:
        others = nonzero_idx[nonzero_idx != i]
        if len(others) < min_other_nonzero:
            continue
        ref = float(np.median(rates[others]))
        if ref > 0 and rates[i] / ref >= ratio_threshold:
            outlier[i] = True
    return outlier


def fit_poisson_glm(
    times, counts, tau_s, order: int, analyte: str = "",
    max_iter: int = 50, tol: float = 1e-8, eta_clip: float = 30.0,
) -> PoissonDriftFit | None:
    """Fits one Poisson GLM (log link) of the given polynomial order via IRLS.

    Returns ``None`` (never raises) when the fit can't be trusted: too few
    points for the requested order, non-convergence, or an ill-conditioned
    design matrix -- callers (esp. :func:`select_poisson_order_lrt`) use this
    to fall back to a lower order rather than propagate a bad fit.

    Expects file-level outliers already excluded by the caller (see
    :func:`detect_poisson_file_outliers`) -- this function itself performs
    an ordinary (non-robust) fit, deliberately: robustness belongs in a
    one-time pre-filtering decision, not folded into the polynomial search
    itself (see :func:`detect_poisson_file_outliers`'s docstring for why
    that combination was tried and rejected).
    """
    n_arr = np.asarray(counts, dtype=float)
    tau_arr = np.asarray(tau_s, dtype=float)
    n_points = len(n_arr)
    if n_points == 0 or n_points != len(tau_arr):
        return None
    if order > 0 and n_points < order + 2:
        return None

    times = list(times)
    t0 = pd.Timestamp(min(times)).to_pydatetime()
    t_seconds = _to_seconds(times, t0)
    max_abs_t = float(np.max(np.abs(t_seconds)))
    t_scale = max_abs_t if max_abs_t > 0 else 1.0
    s = t_seconds / t_scale

    offset = np.log(np.maximum(tau_arr, 1e-300))
    total_tau = float(np.sum(tau_arr))

    if order == 0:
        total_n = float(np.sum(n_arr))
        if total_tau <= 0:
            return None
        rate_hat = total_n / total_tau
        beta0 = np.log(rate_hat) if rate_hat > 0 else -700.0
        mu_pred = tau_arr * rate_hat
        deviance = _poisson_deviance(n_arr, mu_pred)
        return PoissonDriftFit(
            analyte=analyte, order=0, model="constant", coeffs=np.array([beta0]),
            t0=t0, t_scale=t_scale, deviance=deviance, n_points=n_points,
            drift_pvalue=None, tau_total_s=total_tau, converged=True,
        )

    X = np.vander(s, order + 1, increasing=True)
    mu = n_arr + 0.5
    eta = np.log(mu)
    prev_deviance = _poisson_deviance(n_arr, mu)
    converged = False
    beta = None

    for _ in range(max_iter):
        z = eta - offset + (n_arr - mu) / mu
        w = mu
        sw = np.sqrt(w)
        try:
            beta, *_ = np.linalg.lstsq(sw[:, None] * X, sw * z, rcond=None)
        except np.linalg.LinAlgError:
            return None

        eta = np.clip(offset + X @ beta, -eta_clip, eta_clip)
        mu = np.exp(eta)
        deviance = _poisson_deviance(n_arr, mu)

        if abs(deviance - prev_deviance) < tol * (prev_deviance + 1e-8):
            prev_deviance = deviance
            converged = True
            break
        prev_deviance = deviance

    if beta is None or not np.all(np.isfinite(beta)) or not np.isfinite(prev_deviance):
        return None

    WX = w[:, None] * X
    XtWX = X.T @ WX
    try:
        cond = np.linalg.cond(XtWX)
    except np.linalg.LinAlgError:
        return None
    if not np.isfinite(cond) or cond > 1e10:
        return None

    return PoissonDriftFit(
        analyte=analyte, order=order, model=f"poly({order})", coeffs=beta,
        t0=t0, t_scale=t_scale, deviance=prev_deviance, n_points=n_points,
        drift_pvalue=None, tau_total_s=total_tau, converged=converged,
    )


def _cv_deviance_for_order(times, counts, tau_s, order: int, analyte: str = "") -> float | None:
    """Leave-one-out cross-validated Poisson deviance for a candidate order.

    Refits the model with each observation held out in turn, then scores
    that fit's predicted rate against the held-out observation's actual
    count -- unlike in-sample deviance (what the LRT step below compares),
    this measures genuine *predictive* accuracy. A higher order that only
    reduces in-sample deviance by wiggling unconstrained through the gaps
    between sparse clusters of files (separate analytical sessions within
    one dataset) will predict a held-out point from that same cluster
    poorly once it's not in the training data -- so CV deviance does not
    improve even though in-sample deviance did, and :func:`select_poisson_order_lrt`
    uses that disagreement to reject the order.

    Returns ``None`` if there aren't enough points, or any fold fails to
    fit/converge -- an order that can't even be evaluated robustly across
    folds isn't a safe choice either.
    """
    times_list = list(times)
    n = len(times_list)
    if n < order + 3:
        return None
    counts_arr = np.asarray(counts, dtype=float)
    tau_arr = np.asarray(tau_s, dtype=float)
    total = 0.0
    for i in range(n):
        idx = [j for j in range(n) if j != i]
        train_times = [times_list[j] for j in idx]
        fold_fit = fit_poisson_glm(train_times, counts_arr[idx], tau_arr[idx], order=order, analyte=analyte)
        if fold_fit is None or not fold_fit.converged:
            return None
        rate_i = fold_fit.predict([times_list[i]])[0]
        mu_i = max(rate_i * tau_arr[i], 1e-300)
        n_i = counts_arr[i]
        term = (n_i * np.log(n_i / mu_i) - (n_i - mu_i)) if n_i > 0 else -(n_i - mu_i)
        total += 2.0 * term
    return total


def _predicted_rate_is_stable(
    fit: PoissonDriftFit, times, observed_max_rate: float, max_ratio: float = 10.0
) -> bool:
    """Final safety net alongside the cross-validation check above: the log
    link means ``predict()`` returns ``exp(eta)``, so even a modest wobble
    in the fitted polynomial between or beyond the actual observation times
    gets *exponentiated* into a wildly unrealistic predicted rate. Densely
    samples the fit across the full observed time span and rejects the
    order if its predicted rate anywhere exceeds ``max_ratio`` times the
    largest rate actually observed in the input data.
    """
    ts = pd.Timestamp(min(times))
    te = pd.Timestamp(max(times))
    if te <= ts:
        return True
    probe_times = pd.date_range(ts, te, periods=200)
    predicted = fit.predict(probe_times)
    if not np.all(np.isfinite(predicted)):
        return False
    cap = max_ratio * max(observed_max_rate, 1e-12)
    return bool(np.max(predicted) <= cap)


def select_poisson_order_lrt(
    times, counts, tau_s, analyte: str = "", max_order: int = 3, alpha: float = 0.05,
) -> PoissonDriftFit:
    """Incrementally tests order 0 -> 1 -> 2 -> ... -> max_order (not 0-vs-max),
    accepting each next order only when *all three* hold: its likelihood-
    ratio test against the previous order is significant at ``alpha``, its
    leave-one-out cross-validated deviance also improves on the previous
    order's (see :func:`_cv_deviance_for_order`), and its predicted rate
    stays plausible across the whole session (see
    :func:`_predicted_rate_is_stable`) -- stops at the first order failing
    any of the three and returns the last accepted fit.

    The LRT alone is not sufficient: it only ever compares deviance *at the
    observed times*, so on sparse, gapped data (e.g. separate analytical
    sessions within one dataset) a higher order can pass it by slightly
    improving the fit at those specific clustered points while extrapolating
    wildly in between -- exactly what cross-validation catches, since a
    fit doing that predicts a held-out point from its own cluster poorly.
    Verified: an order that would have passed the LRT alone on such data
    now correctly fails the CV check and this stays at a lower, stable
    order; genuine injected drift is still detected essentially every time
    (the CV/stability requirements cost negligible sensitivity against a
    real signal, only against overfitting sparse noise).

    Expects file-level outliers already excluded by the caller (see
    :func:`detect_poisson_file_outliers`) -- this function performs no
    robustness of its own; see that function's docstring for why file-level
    robustness is handled as a one-time pre-filter rather than folded into
    this search.
    """
    fit_prev = fit_poisson_glm(times, counts, tau_s, order=0, analyte=analyte)
    if fit_prev is None:
        raise PoissonFitError("Could not fit even a constant Poisson model -- check input data.")

    n_arr = np.asarray(counts, dtype=float)
    tau_arr = np.asarray(tau_s, dtype=float)
    observed_max_rate = float(np.max(n_arr / np.maximum(tau_arr, 1e-300))) if len(n_arr) else 0.0

    best = fit_prev
    cv_prev = _cv_deviance_for_order(times, counts, tau_s, 0, analyte=analyte)
    n_points = len(list(times))
    for k in range(1, max_order + 1):
        if n_points < k + 3:
            break
        fit_k = fit_poisson_glm(times, counts, tau_s, order=k, analyte=analyte)
        if fit_k is None or not fit_k.converged:
            break
        lrt_stat = max(fit_prev.deviance - fit_k.deviance, 0.0)
        fit_k.drift_pvalue = float(chi2.sf(lrt_stat, df=1))
        cv_k = _cv_deviance_for_order(times, counts, tau_s, k, analyte=analyte)
        if cv_k is None:
            break
        improves_cv = cv_prev is None or cv_k < cv_prev
        is_significant = fit_k.drift_pvalue < alpha
        is_stable = _predicted_rate_is_stable(fit_k, times, observed_max_rate)
        if is_significant and improves_cv and is_stable:
            best, fit_prev, cv_prev = fit_k, fit_k, cv_k
        else:
            break
    return best
