"""Non-parametric session-background drift fits: LOWESS, smoothing spline, kriging.

A single low-order polynomial (``drift.fit_polynomial`` /
``drift.select_order_by_aic``) is the right model for a short analytical
session whose background wanders slowly and monotonically. It is the wrong
model for a long multi-day session, where the gas blank can rise, fall, and
rise again several times (instrument warm-up, cell-gas bottle swaps,
auto-tune events) -- structure a degree-2 or degree-3 polynomial either
cannot follow at all or follows only by swinging wildly between the
observed points.

These three fitters trade the polynomial's global form for a local one:

- ``"lowess"`` -- locally-weighted linear regression (Cleveland 1979). At
  each query time, fit a line to the nearby background points with tricube
  distance weights. Hand-rolled here (statsmodels is not a dependency).
- ``"spline"`` -- a cubic least-squares regression spline
  (:class:`scipy.interpolate.LSQUnivariateSpline`) whose flexibility is set
  by a knot count, so it follows real structure without chasing scatter.
- ``"kriging"`` -- Gaussian-process regression
  (:class:`sklearn.gaussian_process.GaussianProcessRegressor`) with an
  RBF + white-noise kernel, i.e. ordinary kriging with an automatically
  fitted length scale.

All three return a :class:`NonparametricDriftFit`, which is
``predict(times)``-compatible with :class:`~src.calibration.drift.DriftFit`
so ``background.compute_background_result`` and ``diagnostics`` consume it
unchanged. ``background.fit_session_background_drift`` dispatches to
:func:`fit_nonparametric_drift` for these method names.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from src.calibration.drift import DriftFitError, _to_seconds

_MIN_POINTS = 5  # below this, no non-parametric fit is attempted (caller falls back)

# LOWESS is pre-evaluated on this many points across the (standardized)
# session span, then interpolated at predict time -- see fit_lowess. 2000
# points over a multi-day session is roughly one knot per minute, far finer
# than the drift structure any gas blank actually has.
_GRID_POINTS = 2000
# Extra span at each end, as a fraction of the session -- covers ablation
# rows that run past the last gas blank the fit saw. 0.02 of a 36-hour
# session is ~45 minutes, comfortably more than one line takes.
_GRID_MARGIN = 0.02

# Regression-spline flexibility: one interior knot per this many background
# measurements, capped. Chosen by held-out prediction error on a real
# 791-blank, 38-hour session -- see fit_spline's Notes.
_SPLINE_POINTS_PER_KNOT = 20
_SPLINE_MAX_KNOTS = 60


def _standardize(times, values):
    """Common preamble: to standardized time in ``[0, 1]``, sorted, de-duplicated.

    Parameters
    ----------
    times : array_like
        Acquisition datetimes.
    values : array_like
        Values aligned with ``times``.

    Returns
    -------
    tuple
        ``(t0, t_scale, x_std, y)`` where ``x_std`` is strictly increasing
        in ``[0, 1]`` and ``y`` has had co-located points averaged.

    Raises
    ------
    DriftFitError
        If fewer than :data:`_MIN_POINTS` distinct points remain, or the
        session has zero time span.
    """
    times = list(times)
    values = np.asarray(values, dtype=float)
    if len(times) < _MIN_POINTS:
        raise DriftFitError(f"Need at least {_MIN_POINTS} points, got {len(times)}.")

    t0 = pd.Timestamp(min(times)).to_pydatetime()
    secs = _to_seconds(times, t0)
    span = float(np.max(secs) - np.min(secs))
    if span <= 0:
        raise DriftFitError("Zero time span -- cannot fit a drift curve.")
    t_scale = span
    x = secs / t_scale

    order = np.argsort(x, kind="stable")
    x, y = x[order], values[order]

    # A smoothing spline (and, more mildly, the LOWESS/kriging solves) needs
    # strictly increasing x; two lines acquired in the same second collapse
    # to one point at their mean.
    ux, inv = np.unique(x, return_inverse=True)
    if ux.size != x.size:
        uy = np.zeros_like(ux)
        np.add.at(uy, inv, y)
        counts = np.zeros_like(ux)
        np.add.at(counts, inv, 1.0)
        y = uy / counts
        x = ux
    if x.size < _MIN_POINTS:
        raise DriftFitError(f"Need at least {_MIN_POINTS} distinct times, got {x.size}.")
    return t0, t_scale, x, y


def _goodness_of_fit(y, fitted):
    """``(r_squared, residual_std)`` of ``fitted`` against ``y``."""
    resid = y - fitted
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    residual_std = float(np.std(resid, ddof=1)) if y.size > 1 else 0.0
    return r_squared, residual_std


@dataclass
class NonparametricDriftFit:
    """A LOWESS / smoothing-spline / kriging fit of background level vs. time.

    ``predict(times)``-compatible with :class:`~src.calibration.drift.DriftFit`
    (same datetime-in, ndarray-out contract), so every existing background
    consumer works unchanged.

    Attributes
    ----------
    analyte : str
        Analyte fitted. May be empty.
    method : {"lowess", "spline", "kriging"}
        Which fitter produced this.
    t0 : datetime.datetime
        Time origin; the fit's x-axis is ``(t - t0) / t_scale``.
    t_scale : float
        Time span in seconds used to standardize the x-axis to ``[0, 1]``.
    n_points : int
        Number of (de-duplicated) points fitted.
    r_squared : float
        Coefficient of determination on the fitted points.
    residual_std : float
        Sample standard deviation (``ddof=1``) of the residuals.
    model : object
        The backing estimator: a
        :class:`scipy.interpolate.LSQUnivariateSpline` (``"spline"``), a fitted
        :class:`sklearn.gaussian_process.GaussianProcessRegressor`
        (``"kriging"``), or a ``(grid_x, grid_y)`` pair of the LOWESS curve
        pre-evaluated on a dense standardized-time grid (``"lowess"``,
        interpolated at predict time).
    order : int
        Always ``-1`` -- a non-parametric fit has no polynomial order. Kept
        so code that reads ``.order`` off a drift fit (e.g. diagnostic
        labels) does not raise; such code should check ``.method`` first.
    """

    analyte: str
    method: str
    t0: datetime
    t_scale: float
    n_points: int
    r_squared: float
    residual_std: float
    model: object = field(repr=False)
    order: int = -1

    def predict(self, times) -> np.ndarray:
        """Evaluate the fitted drift curve at ``times``.

        Parameters
        ----------
        times : array_like
            Datetimes (or anything :func:`pandas.to_datetime` accepts).

        Returns
        -------
        numpy.ndarray
            Predicted background level, one per element of ``times``.
        """
        s = _to_seconds(times, self.t0) / self.t_scale
        if self.method == "spline":
            return np.asarray(self.model(s), dtype=float)
        if self.method == "kriging":
            return np.asarray(self.model.predict(s.reshape(-1, 1)), dtype=float).ravel()
        if self.method == "lowess":
            # Interpolated off a pre-evaluated dense curve, not re-solved per
            # query point: compute_background_result calls predict() once per
            # file per analyte over that file's whole ablation window, which
            # is hundreds of thousands of query times across a session --
            # a per-point local regression there would dominate the run.
            # Outside the grid (only the tail of the last line's ablation,
            # seconds past the last blank), numpy.interp clamps to the end
            # value, which is steadier than extrapolating a local fit.
            grid_x, grid_y = self.model
            return np.interp(s, grid_x, grid_y)
        raise ValueError(f"Unknown non-parametric drift method {self.method!r}.")


def _lowess_bandwidth_frac(n: int) -> float:
    """Default neighbourhood fraction for :func:`fit_lowess`.

    Sized so the local window holds ``~2 * sqrt(n)`` points (min 6): wide
    enough to average down blank scatter, narrow enough to follow the
    multi-bump drift of a long session that motivated these fitters. The
    classic 2/3 default is deliberately not used -- it is close to a global
    linear fit on the point counts a session produces.
    """
    k = max(6, int(round(2.0 * np.sqrt(n))))
    return min(1.0, k / n)


def _tricube(u: np.ndarray) -> np.ndarray:
    """Tricube kernel ``(1 - |u|^3)^3`` for ``|u| < 1``, else 0."""
    w = np.clip(1.0 - np.abs(u) ** 3, 0.0, None) ** 3
    return w


def _lowess_predict(x_train: np.ndarray, y_train: np.ndarray, x_query: np.ndarray, frac: float) -> np.ndarray:
    """Locally-weighted linear regression of ``y_train`` on ``x_train`` at ``x_query``.

    Parameters
    ----------
    x_train, y_train : numpy.ndarray
        Standardized training times and their values (sorted, de-duplicated).
    x_query : numpy.ndarray
        Standardized times to predict at (any order, may extrapolate).
    frac : float
        Neighbourhood fraction in ``(0, 1]``; the local window is the
        ``ceil(frac * n)`` nearest training points.

    Returns
    -------
    numpy.ndarray
        Predicted values, aligned with ``x_query``.
    """
    n = x_train.size
    k = max(2, int(np.ceil(frac * n)))
    k = min(k, n)
    out = np.empty(x_query.shape, dtype=float)
    for i, x0 in enumerate(np.asarray(x_query, dtype=float).ravel()):
        d = np.abs(x_train - x0)
        # k-th smallest distance = local bandwidth; points beyond it get
        # zero weight from the tricube kernel.
        h = np.partition(d, k - 1)[k - 1]
        if h <= 0:
            # x0 coincides with >= k training points -- plain mean of the
            # exact matches (weights would all be 1, slope undefined).
            out.flat[i] = float(np.mean(y_train[d == 0]))
            continue
        w = _tricube(d / h)
        nz = w > 0
        if np.count_nonzero(nz) < 2:
            out.flat[i] = float(y_train[np.argmin(d)])
            continue
        xw, yw, ww = x_train[nz], y_train[nz], w[nz]
        # Weighted least squares for [intercept, slope] via the 2x2 normal
        # equations -- cheaper and steadier than np.polyfit per query point.
        sw = np.sum(ww)
        sx = np.sum(ww * xw)
        sxx = np.sum(ww * xw * xw)
        sy = np.sum(ww * yw)
        sxy = np.sum(ww * xw * yw)
        det = sw * sxx - sx * sx
        if abs(det) < 1e-12:
            out.flat[i] = sy / sw
            continue
        intercept = (sxx * sy - sx * sxy) / det
        slope = (sw * sxy - sx * sy) / det
        out.flat[i] = intercept + slope * x0
    return out.reshape(x_query.shape)


def fit_lowess(times, values, analyte: str = "", frac: float | None = None) -> NonparametricDriftFit:
    """Fit a LOWESS (locally-weighted linear) drift curve.

    Parameters
    ----------
    times : array_like
        Acquisition datetimes.
    values : array_like
        Background levels aligned with ``times``.
    analyte : str, optional
        Label stored on the fit.
    frac : float or None, optional
        Neighbourhood fraction; ``None`` uses :func:`_lowess_bandwidth_frac`.

    Returns
    -------
    NonparametricDriftFit

    Raises
    ------
    DriftFitError
        If there are too few distinct points (see :data:`_MIN_POINTS`).
    """
    t0, t_scale, x, y = _standardize(times, values)
    if frac is None:
        frac = _lowess_bandwidth_frac(x.size)
    fitted = _lowess_predict(x, y, x, frac)
    r_squared, residual_std = _goodness_of_fit(y, fitted)

    # Pre-evaluate the curve on a dense grid once, so predict() is an
    # O(1)-per-point interpolation rather than an O(n_train) local solve
    # (see NonparametricDriftFit.predict). The margin covers the tail of
    # the last line's ablation window, which runs a few minutes past the
    # last gas blank the fit was built from.
    margin = _GRID_MARGIN
    grid_x = np.linspace(x[0] - margin, x[-1] + margin, _GRID_POINTS)
    grid_y = _lowess_predict(x, y, grid_x, frac)
    return NonparametricDriftFit(
        analyte=analyte, method="lowess", t0=t0, t_scale=t_scale, n_points=int(x.size),
        r_squared=r_squared, residual_std=residual_std, model=(grid_x, grid_y),
    )


def fit_spline(times, values, analyte: str = "") -> NonparametricDriftFit:
    """Fit a cubic least-squares regression spline drift curve.

    Flexibility is set by the *number of knots*
    (``n / _SPLINE_POINTS_PER_KNOT``, placed at quantiles of the observed
    times so each span holds a comparable number of blanks), not by a
    smoothing parameter. On a long session that is one knot every couple of
    hours -- fine enough for real drift structure, far too coarse to chase
    blank-to-blank scatter.

    Notes
    -----
    A :class:`scipy.interpolate.UnivariateSpline` smoothing fit was tried
    first (smoothing target ``s`` derived from a MAD-of-first-differences
    noise estimate, escalated until FITPACK converged) and rejected: on the
    real 791-blank session it was the *worst* of every method tested,
    including a straight line, and on channels whose blank is essentially
    pure noise (Ti47, Sr88, Zr90 there) FITPACK returned wildly divergent
    curves -- held-out prediction errors seven orders of magnitude past the
    data's own spread. The failure mode is inherent: ``s`` is a target
    residual sum, so a bad noise estimate silently buys unlimited
    flexibility. Fixing the knot count instead caps flexibility outright,
    and measured 0.344 median held-out error on that session (normalized
    per analyte) against 0.762 for a cubic polynomial and 1.257 for the
    smoothing spline.

    Parameters
    ----------
    times : array_like
        Acquisition datetimes.
    values : array_like
        Background levels aligned with ``times``.
    analyte : str, optional
        Label stored on the fit.

    Returns
    -------
    NonparametricDriftFit

    Raises
    ------
    DriftFitError
        If there are too few distinct points, or SciPy fails to build even
        the zero-interior-knot (plain cubic) spline.
    """
    from scipy.interpolate import LSQUnivariateSpline

    t0, t_scale, x, y = _standardize(times, values)
    k = min(3, x.size - 1)

    spline = None
    n_knots = int(np.clip(round(x.size / _SPLINE_POINTS_PER_KNOT), 0, _SPLINE_MAX_KNOTS))
    last_exc: Exception | None = None
    # Walk the knot count down until SciPy accepts it. LSQUnivariateSpline
    # enforces the Schoenberg-Whitney condition (every knot span needs its
    # own data), which quantile placement usually satisfies but clustered
    # acquisition times can still violate. The ladder bottoms out at zero
    # interior knots -- an ordinary least-squares cubic, always fittable.
    while n_knots >= 0:
        if n_knots:
            quantiles = np.linspace(0.0, 1.0, n_knots + 2)[1:-1]
            knots = np.unique(np.quantile(x, quantiles))
            knots = knots[(knots > x[0]) & (knots < x[-1])]
        else:
            knots = np.array([])
        try:
            spline = LSQUnivariateSpline(x, y, t=knots, k=k)
            break
        except Exception as exc:  # SciPy raises bare ValueError/dfitpack errors
            last_exc = exc
            n_knots = n_knots // 2 - 1
    if spline is None:
        raise DriftFitError(f"Spline fit failed: {last_exc}")

    fitted = np.asarray(spline(x), dtype=float)
    r_squared, residual_std = _goodness_of_fit(y, fitted)
    return NonparametricDriftFit(
        analyte=analyte, method="spline", t0=t0, t_scale=t_scale, n_points=int(x.size),
        r_squared=r_squared, residual_std=residual_std, model=spline,
    )


def fit_kriging(times, values, analyte: str = "") -> NonparametricDriftFit:
    """Fit an ordinary-kriging (Gaussian-process) drift curve.

    Uses an ``RBF + WhiteKernel`` covariance with bounded hyper-parameters,
    ``normalize_y=True`` (the background level is far from zero-mean), and a
    couple of optimizer restarts for a stable length scale.

    Parameters
    ----------
    times : array_like
        Acquisition datetimes.
    values : array_like
        Background levels aligned with ``times``.
    analyte : str, optional
        Label stored on the fit.

    Returns
    -------
    NonparametricDriftFit

    Raises
    ------
    DriftFitError
        If there are too few distinct points, or the GP fit fails.
    """
    import warnings

    from sklearn.exceptions import ConvergenceWarning
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel

    t0, t_scale, x, y = _standardize(times, values)
    y_span = float(np.max(y) - np.min(y)) or 1.0
    kernel = (
        ConstantKernel(1.0, (1e-3, 1e3))
        * RBF(length_scale=0.2, length_scale_bounds=(1e-2, 1e1))
        + WhiteKernel(noise_level=(0.1 * y_span) ** 2, noise_level_bounds=(1e-12, 1e2))
    )
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, n_restarts_optimizer=2)
    try:
        with warnings.catch_warnings():
            # A near-constant or noiseless analyte drives a hyper-parameter
            # to its bound -- the fit is still fine (a flat line), the
            # warning just adds noise to a session-wide run over many
            # analytes.
            warnings.simplefilter("ignore", ConvergenceWarning)
            gp.fit(x.reshape(-1, 1), y)
    except Exception as exc:
        raise DriftFitError(f"Kriging fit failed: {exc}") from exc
    fitted = np.asarray(gp.predict(x.reshape(-1, 1)), dtype=float).ravel()
    r_squared, residual_std = _goodness_of_fit(y, fitted)
    return NonparametricDriftFit(
        analyte=analyte, method="kriging", t0=t0, t_scale=t_scale, n_points=int(x.size),
        r_squared=r_squared, residual_std=residual_std, model=gp,
    )


_FITTERS = {"lowess": fit_lowess, "spline": fit_spline, "kriging": fit_kriging}

#: The method strings :func:`fit_nonparametric_drift` accepts -- the set
#: ``background.fit_session_background_drift`` treats as "not a polynomial".
NONPARAMETRIC_DRIFT_METHODS = frozenset(_FITTERS)


def fit_nonparametric_drift(times, values, method: str, analyte: str = "") -> NonparametricDriftFit:
    """Dispatch to :func:`fit_lowess` / :func:`fit_spline` / :func:`fit_kriging`.

    Parameters
    ----------
    times : array_like
        Acquisition datetimes.
    values : array_like
        Background levels aligned with ``times``.
    method : {"lowess", "spline", "kriging"}
    analyte : str, optional
        Label stored on the fit.

    Returns
    -------
    NonparametricDriftFit

    Raises
    ------
    ValueError
        If ``method`` is not one of the three (a caller bug).
    DriftFitError
        If the data cannot support the fit (caller should fall back to a
        polynomial).
    """
    try:
        fitter = _FITTERS[method]
    except KeyError:
        raise ValueError(
            f"Unknown non-parametric drift method {method!r}; "
            f"expected one of {sorted(_FITTERS)}."
        ) from None
    return fitter(times, values, analyte=analyte)
