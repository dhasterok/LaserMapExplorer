"""Generic polynomial-vs-time drift fitting.

Reused both for session-level background drift (background.py) and standard
signal drift (standards.py) -- fitting a low-order polynomial to a set of
(time, value) points and evaluating it elsewhere is the same operation in
both cases.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from src.calibration.poisson_drift import PoissonDriftFit, select_poisson_order_lrt


class DriftFitError(ValueError):
    """Raised when there is not enough data to fit the requested polynomial order."""


def _to_seconds(times, t0: datetime) -> np.ndarray:
    """Convert an iterable of datetimes to seconds since ``t0``.

    Parameters
    ----------
    times : array_like
        Datetimes, or anything :func:`pandas.to_datetime` accepts.
    t0 : datetime.datetime
        Time origin.

    Returns
    -------
    numpy.ndarray
        ``(times - t0)`` in seconds, as ``float``.
    """
    ts = pd.to_datetime(list(times))
    t0_ts = pd.Timestamp(t0)
    return (ts - t0_ts).total_seconds().to_numpy(dtype=float)


@dataclass
class DriftFit:
    """A polynomial fit of a value versus time, with goodness-of-fit stats.

    Attributes
    ----------
    analyte : str
        Name of the analyte (or synthetic channel) fitted. May be empty.
    order : int
        Polynomial degree actually used.
    coeffs : numpy.ndarray
        :func:`numpy.polyfit` coefficients, highest power first.
    t0 : datetime.datetime
        Time origin; the fit's x-axis is seconds since ``t0``.
    r_squared : float
        Coefficient of determination on the training points (``1.0`` when
        the values have zero variance).
    n_points : int
        Number of points fitted.
    residual_std : float
        Sample standard deviation (``ddof=1``) of the residuals; ``0.0``
        for a single point.
    """

    analyte: str
    order: int
    coeffs: np.ndarray        # np.polyfit coefficients, highest power first
    t0: datetime                # time origin; fit's x-axis is seconds-since-t0
    r_squared: float
    n_points: int
    residual_std: float

    def predict(self, times) -> np.ndarray:
        """Evaluate the fitted polynomial at the given times.

        Parameters
        ----------
        times : array_like
            Datetimes (or anything :func:`pandas.to_datetime` accepts)
            at which to evaluate the curve.

        Returns
        -------
        numpy.ndarray
            Predicted values, one per element of ``times``.
        """
        x = _to_seconds(times, self.t0)
        return np.polyval(self.coeffs, x)


def fit_polynomial(times, values, order: int, analyte: str = "") -> DriftFit:
    """Fit a degree-``order`` polynomial to ``values`` versus ``times``.

    Parameters
    ----------
    times : array_like
        Acquisition datetimes. The earliest becomes the fit's ``t0``.
    values : array_like
        Values to fit, aligned with ``times``.
    order : int
        Polynomial degree. ``order=0`` degenerates to the sample mean.
    analyte : str, optional
        Label stored on the returned fit, by default ``""``.

    Returns
    -------
    DriftFit
        The fitted polynomial and its goodness-of-fit statistics.

    Raises
    ------
    DriftFitError
        If ``times`` is empty, or has fewer than ``order + 1`` points.

    Notes
    -----
    Callers that want automatic order reduction (e.g. ``standards.py`` when
    too few standard occurrences are available) implement that policy
    themselves rather than this function silently picking a different order.
    """
    times = list(times)
    values = np.asarray(values, dtype=float)
    n = len(times)
    if n == 0:
        raise DriftFitError("No data points to fit.")
    if n <= order:
        raise DriftFitError(f"Need at least {order + 1} points to fit order {order}, got {n}.")

    t0 = pd.Timestamp(min(times)).to_pydatetime()
    x = _to_seconds(times, t0)
    coeffs = np.polyfit(x, values, order)

    predicted = np.polyval(coeffs, x)
    residuals = values - predicted
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((values - np.mean(values)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    residual_std = float(np.std(residuals, ddof=1)) if n > 1 else 0.0

    return DriftFit(
        analyte=analyte, order=order, coeffs=coeffs, t0=t0,
        r_squared=r_squared, n_points=n, residual_std=residual_std,
    )


def evaluate(fit: DriftFit, times) -> np.ndarray:
    """Evaluate ``fit`` at ``times`` (thin wrapper over ``fit.predict``).

    Parameters
    ----------
    fit : DriftFit
        A fitted drift polynomial.
    times : array_like
        Datetimes at which to evaluate the curve.

    Returns
    -------
    numpy.ndarray
        Predicted values, one per element of ``times``.
    """
    return fit.predict(times)


def fit_polynomial_with_order_fallback(times, values, order: int, analyte: str = "") -> DriftFit | None:
    """:func:`fit_polynomial` with automatic order reduction instead of raising.

    Parameters
    ----------
    times : array_like
        Acquisition datetimes.
    values : array_like
        Values to fit, aligned with ``times``.
    order : int
        Requested polynomial degree. Reduced (down to 0) while
        ``len(values) < order + 2``.
    analyte : str, optional
        Label stored on the returned fit, by default ``""``.

    Returns
    -------
    DriftFit or None
        The fit at the highest supportable order, or ``None`` if even
        order 0 has no data.

    Notes
    -----
    Shared by ``standards.py`` (per-standard signal drift) and
    ``massbias.py`` (mass-bias log-ratio drift) -- both need "fit at this
    order if there is enough data, otherwise the highest order that fits"
    rather than a hard failure on a sparsely sampled session.
    """
    eff_order = order
    while eff_order > 0 and len(values) < eff_order + 2:
        eff_order -= 1
    try:
        return fit_polynomial(times, values, order=eff_order, analyte=analyte)
    except DriftFitError:
        return None


DriftFitLike = DriftFit | PoissonDriftFit


def _cv_rss_for_order(times, values, order: int) -> float | None:
    """Leave-one-out cross-validated residual sum of squares for a candidate order.

    Parameters
    ----------
    times : array_like
        Acquisition datetimes.
    values : array_like
        Values to fit, aligned with ``times``.
    order : int
        Candidate polynomial degree.

    Returns
    -------
    float or None
        Summed squared held-out prediction errors across all folds, or
        ``None`` if there are fewer than ``order + 3`` points or any fold
        fails to fit.

    Notes
    -----
    The Gaussian/OLS analog of
    ``poisson_drift._cv_deviance_for_order`` (see its docstring for the
    full rationale). AIC alone compares fits only at the observed times, so
    on sparse, gapped data a higher order can lower AIC by wiggling
    unconstrained through the gaps between clusters of points; CV RSS
    catches this, because that same fit predicts a held-out point from its
    own cluster poorly once it is not in the training data.
    """
    times_list = list(times)
    n = len(times_list)
    if n < order + 3:
        return None
    values_arr = np.asarray(values, dtype=float)
    total = 0.0
    for i in range(n):
        idx = [j for j in range(n) if j != i]
        train_times = [times_list[j] for j in idx]
        try:
            fold_fit = fit_polynomial(train_times, values_arr[idx], order=order)
        except DriftFitError:
            return None
        pred_i = fold_fit.predict([times_list[i]])[0]
        total += (values_arr[i] - pred_i) ** 2
    return total


def _predicted_values_are_stable(fit: DriftFit, times, observed_values, max_ratio: float = 10.0) -> bool:
    """Whether a fit stays within a sane range across the whole time span.

    Parameters
    ----------
    fit : DriftFit
        The candidate fit to probe.
    times : array_like
        Observed acquisition datetimes; their min and max bound the probe
        interval.
    observed_values : array_like
        The values that were fitted, used to derive the plausible range.
    max_ratio : float, optional
        Allowed excursion of the predicted curve from the observed median,
        as a multiple of the observed spread. By default ``10.0``.

    Returns
    -------
    bool
        ``True`` if every prediction on a 200-point grid across
        ``[min(times), max(times)]`` is finite and within
        ``max_ratio * span`` of the observed median; ``True`` trivially
        when the time span is degenerate.

    Notes
    -----
    Final safety net alongside the cross-validation check: AIC is computed
    only from residuals at the observed times, so even with the CV
    requirement in place this is cheap extra insurance against a fit that
    swings unrealistically far from the observed data's own range anywhere
    across the full time span (including beyond the last observed time).
    """
    ts = pd.Timestamp(min(times))
    te = pd.Timestamp(max(times))
    if te <= ts:
        return True
    probe_times = pd.date_range(ts, te, periods=200)
    predicted = fit.predict(probe_times)
    if not np.all(np.isfinite(predicted)):
        return False
    obs = np.asarray(observed_values, dtype=float)
    span = float(np.max(obs) - np.min(obs))
    center = float(np.median(obs))
    if span <= 0:
        span = max(abs(center), 1.0)
    cap = max_ratio * span
    return bool(np.max(np.abs(predicted - center)) <= cap)


def select_order_by_aic(times, values, max_order: int = 3, analyte: str = "") -> DriftFit:
    """Select a polynomial drift order by AIC, guarded by cross-validation.

    Parameters
    ----------
    times : array_like
        Acquisition datetimes.
    values : array_like
        Values to fit, aligned with ``times``.
    max_order : int, optional
        Highest polynomial order considered, by default ``3``.
    analyte : str, optional
        Label stored on the returned fit, by default ``""``.

    Returns
    -------
    DriftFit
        The last accepted fit.

    Raises
    ------
    DriftFitError
        If ``times`` is empty.

    Notes
    -----
    Incrementally tests order 0 -> 1 -> ... -> ``max_order``, accepting each
    next order only when all three hold: it lowers
    ``AIC = n * ln(RSS / n) + 2 * (order + 1)`` relative to the current
    best, its leave-one-out cross-validated RSS also improves (see
    :func:`_cv_rss_for_order`), and its predicted curve stays plausible
    across the whole time span (see :func:`_predicted_values_are_stable`).
    Stops at the first order failing any of the three.

    AIC alone is not sufficient on sparse, gapped data (e.g. separate
    analytical sessions within one dataset). A simpler alternative to
    :func:`~src.calibration.poisson_drift.select_poisson_order_lrt` for
    values the Poisson non-negative-integer-count assumption does not apply
    to (e.g. a background-corrected net signal, which can be negative).
    """
    times = list(times)
    values = np.asarray(values, dtype=float)
    n = len(times)
    if n == 0:
        raise DriftFitError("No data points to fit.")

    def _aic(order: int) -> tuple[DriftFit, float]:
        """Fit at ``order`` and return ``(fit, AIC)``.

        Parameters
        ----------
        order : int
            Polynomial order to fit.

        Returns
        -------
        tuple[DriftFit, float]
            The fit and ``n * ln(RSS / n) + 2 * (order + 1)``, with RSS
            floored at ``1e-12`` so a perfect fit does not give ``-inf``.
        """
        fit = fit_polynomial(times, values, order=order, analyte=analyte)
        predicted = fit.predict(times)
        # A perfect fit (RSS=0, e.g. order == n-1) makes ln(RSS/n) -> -inf;
        # floor RSS so AIC stays finite and comparable instead of an
        # overfit order spuriously "winning" via an undefined -inf.
        rss = max(float(np.sum((values - predicted) ** 2)), 1e-12)
        return fit, n * np.log(rss / n) + 2 * (order + 1)

    best_fit, best_aic = _aic(0)
    best_cv = _cv_rss_for_order(times, values, 0)
    for order in range(1, max_order + 1):
        if n < order + 3:
            break
        fit_k, aic_k = _aic(order)
        cv_k = _cv_rss_for_order(times, values, order)
        if cv_k is None:
            break
        improves_cv = best_cv is None or cv_k < best_cv
        is_stable = _predicted_values_are_stable(fit_k, times, values)
        if aic_k < best_aic and improves_cv and is_stable:
            best_fit, best_aic, best_cv = fit_k, aic_k, cv_k
        else:
            break

    return best_fit


def select_drift_fit(
    times, values, counts=None, tau_s=None, method: str = "fixed",
    order: int = 1, max_order: int = 3, analyte: str = "",
) -> DriftFitLike:
    """Dispatch to one of the three user-facing drift-fit methods.

    Parameters
    ----------
    times : array_like
        Acquisition datetimes.
    values : array_like
        Values to fit (``"fixed"`` and ``"auto_aic"``), aligned with
        ``times``.
    counts : array_like or None, optional
        Recovered integer counts, required for ``"auto_poisson_lrt"``.
    tau_s : float or None, optional
        Effective counting time in seconds, required for
        ``"auto_poisson_lrt"``.
    method : {"fixed", "auto_aic", "auto_poisson_lrt"}, optional
        - ``"fixed"`` -- OLS :func:`fit_polynomial` at ``order``.
        - ``"auto_aic"`` -- :func:`select_order_by_aic` over
          ``0..max_order`` (Gaussian/OLS).
        - ``"auto_poisson_lrt"`` --
          :func:`~src.calibration.poisson_drift.select_poisson_order_lrt`
          over ``0..max_order`` on recovered integer counts.

        By default ``"fixed"``.
    order : int, optional
        Polynomial order for ``"fixed"``, by default ``1``.
    max_order : int, optional
        Highest order for the ``auto_*`` methods, by default ``3``.
    analyte : str, optional
        Label stored on the returned fit, by default ``""``.

    Returns
    -------
    DriftFit or PoissonDriftFit
        A :class:`DriftFit` for ``"fixed"``/``"auto_aic"``, a
        :class:`~src.calibration.poisson_drift.PoissonDriftFit` for
        ``"auto_poisson_lrt"``.

    Raises
    ------
    ValueError
        If ``method`` is unknown, or ``method="auto_poisson_lrt"`` without
        both ``counts`` and ``tau_s`` (a caller bug, not a degraded-data
        condition, so it raises rather than falling back).
    """
    if method == "fixed":
        return fit_polynomial(times, values, order=order, analyte=analyte)
    if method == "auto_aic":
        return select_order_by_aic(times, values, max_order=max_order, analyte=analyte)
    if method == "auto_poisson_lrt":
        if counts is None or tau_s is None:
            raise ValueError("method='auto_poisson_lrt' requires both counts and tau_s.")
        return select_poisson_order_lrt(times, counts, tau_s, analyte=analyte, max_order=max_order)
    raise ValueError(f"Unknown drift method {method!r}; expected 'fixed', 'auto_aic', or 'auto_poisson_lrt'.")
