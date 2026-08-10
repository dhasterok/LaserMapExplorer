"""Regression fitting engine for scatter/heatmap biplots.

Qt-free computation module: fits a model (linear, polynomial, exponential,
logarithmic) to an (x, y) point cloud using ordinary least squares or
total-least-squares/Deming (errors-in-variables) regression, with optional
per-axis uncertainties. Paired with outlier detection and leverage/influence
diagnostics. See ``src/common/Regression.py`` for the UI that drives this.

The total-least-squares/Deming path follows the same ``scipy.odr`` pattern
already used for isochron-style dating fits in ``src/common/geochronology.py``
(``scatter_date()``), generalized to arbitrary linear-in-parameters models
and to unfixed as well as fixed-parameter fits.
"""
from dataclasses import dataclass
from typing import Callable, Optional
import numpy as np
import scipy.odr as odr

MODELS = ['linear', 'polynomial', 'exponential', 'logarithmic']
METHODS = ['ols', 'tls', 'deming']


@dataclass
class RegressionResult:
    """Result of a single model/method fit.

    ``leverage``/``cooks_distance`` are only computed for OLS (they rely on
    the OLS hat matrix). ``orthogonal_residual`` is the TLS/Deming analog
    used for flagging high-influence points with those methods -- it is a
    perpendicular-distance diagnostic, not a true statistical leverage.
    """
    model: str
    method: str
    params: np.ndarray
    param_errors: np.ndarray
    param_names: list
    r_squared: float
    residuals: np.ndarray
    n: int
    equation_str: str
    predict: Callable[[np.ndarray], np.ndarray]
    leverage: Optional[np.ndarray] = None
    cooks_distance: Optional[np.ndarray] = None
    orthogonal_residual: Optional[np.ndarray] = None


def _design_matrix(model, x, degree):
    """Builds the linear-in-parameters design matrix and target for a model.

    Returns (X, y_target, back_transform, predict_from_beta, param_names),
    where ``back_transform(beta)`` maps fitted linear-space parameters to the
    reported model parameters, and ``predict_from_beta(beta, xnew)`` predicts
    y in the original (non-transformed) space.
    """
    x = np.asarray(x, dtype=float)

    if model in ('linear', 'polynomial'):
        deg = 1 if model == 'linear' else max(1, int(degree))
        X = np.vander(x, deg + 1, increasing=True)
        back_transform = lambda beta: beta
        predict_from_beta = lambda beta, xnew: np.polyval(beta[::-1], xnew)
        names = ['b0 (intercept)'] + [f'b{i}' for i in range(1, deg + 1)]
        return X, None, back_transform, predict_from_beta, names

    if model == 'exponential':
        # y = a * exp(b*x)  =>  ln(y) = ln(a) + b*x
        X = np.vander(x, 2, increasing=True)
        back_transform = lambda beta: np.array([np.exp(beta[0]), beta[1]])
        predict_from_beta = lambda beta, xnew: beta[0] * np.exp(beta[1] * xnew)
        return X, 'log_y', back_transform, predict_from_beta, ['a', 'b']

    if model == 'logarithmic':
        # y = a + b*ln(x)
        X = np.vander(np.log(x), 2, increasing=True)
        back_transform = lambda beta: beta
        predict_from_beta = lambda beta, xnew: beta[0] + beta[1] * np.log(xnew)
        return X, None, back_transform, predict_from_beta, ['a', 'b']

    raise ValueError(f"Unknown model: {model!r}. Expected one of {MODELS}.")


def _target(model, y, target_kind):
    y = np.asarray(y, dtype=float)
    if target_kind == 'log_y':
        return np.log(y)
    return y


def _equation_str(model, params):
    if model in ('linear', 'polynomial'):
        terms = [f"{params[0]:.4g}"]
        for i, b in enumerate(params[1:], start=1):
            power = '' if i == 1 else f'^{i}'
            terms.append(f"{b:+.4g}*x{power}")
        return "y = " + " ".join(terms)
    if model == 'exponential':
        a, b = params
        return f"y = {a:.4g}*exp({b:+.4g}*x)"
    if model == 'logarithmic':
        a, b = params
        return f"y = {a:.4g}{b:+.4g}*ln(x)"
    return ""


def _r_squared(y, y_pred):
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0
    return 1.0 - ss_res / ss_tot


def _fit_ols(X, y, fixed_slope=None, fixed_intercept=None):
    """OLS fit of y = X @ beta. Optionally fixes one of a two-parameter
    (intercept, slope) fit, matching the reduced-model approach used for
    isochron-style dating fits.
    """
    n, p = X.shape

    if p == 2 and fixed_intercept is not None:
        # y - c = b*x  ->  solve for slope only
        x = X[:, 1]
        b = np.sum(x * (y - fixed_intercept)) / np.sum(x ** 2)
        beta = np.array([fixed_intercept, b])
        beta_err = np.array([0.0, np.nan])
        y_pred = X @ beta
        return beta, beta_err, y_pred, None, None

    if p == 2 and fixed_slope is not None:
        # y - b*x = c  ->  solve for intercept only (mean of residual)
        x = X[:, 1]
        c = np.mean(y - fixed_slope * x)
        beta = np.array([c, fixed_slope])
        beta_err = np.array([np.nan, 0.0])
        y_pred = X @ beta
        return beta, beta_err, y_pred, None, None

    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    y_pred = X @ beta

    dof = max(n - p, 1)
    mse = np.sum((y - y_pred) ** 2) / dof
    XtX_inv = np.linalg.pinv(X.T @ X)
    cov = mse * XtX_inv
    beta_err = np.sqrt(np.clip(np.diag(cov), 0, None))

    H = X @ XtX_inv @ X.T
    leverage = np.diag(H)
    resid = y - y_pred
    with np.errstate(divide='ignore', invalid='ignore'):
        cooks_d = (resid ** 2 / (p * mse)) * (leverage / (1 - leverage) ** 2)
    cooks_d = np.nan_to_num(cooks_d, nan=0.0, posinf=0.0)

    return beta, beta_err, y_pred, leverage, cooks_d


def _fit_odr(X, y, x_raw, sx, sy, fixed_slope=None, fixed_intercept=None):
    """Total-least-squares/Deming fit via scipy.odr.

    ``X`` supplies the polynomial powers of x_raw (same convention as the OLS
    path) so the same model function works for linear/polynomial fits;
    ``x_raw`` is the (possibly log-transformed) predictor ODR actually
    perturbs.
    """
    degree = X.shape[1] - 1

    if degree == 1 and fixed_intercept is not None:
        def f(beta, x):
            return beta[0] * x + fixed_intercept
        model = odr.Model(f)
        beta0 = [1.0]
    elif degree == 1 and fixed_slope is not None:
        def f(beta, x):
            return fixed_slope * x + beta[0]
        model = odr.Model(f)
        beta0 = [0.0]
    else:
        def f(beta, x):
            return sum(beta[i] * x ** i for i in range(degree + 1))
        model = odr.Model(f)
        beta0 = [0.0] * (degree + 1)

    data = odr.RealData(x_raw, y, sx=sx, sy=sy)
    result = odr.ODR(data, model, beta0=beta0).run()

    if degree == 1 and fixed_intercept is not None:
        beta = np.array([fixed_intercept, result.beta[0]])
        beta_err = np.array([0.0, result.sd_beta[0]])
    elif degree == 1 and fixed_slope is not None:
        beta = np.array([result.beta[0], fixed_slope])
        beta_err = np.array([result.sd_beta[0], 0.0])
    else:
        beta = result.beta
        beta_err = result.sd_beta

    y_pred = sum(beta[i] * x_raw ** i for i in range(degree + 1))

    # Perpendicular distance from each point to the fitted curve, in
    # standardized (x, y) units, as an influence diagnostic analogous to
    # OLS leverage (not a true leverage/hat-matrix value).
    x_std = np.std(x_raw) or 1.0
    y_std = np.std(y) or 1.0
    orth_resid = np.sqrt(((x_raw - x_raw) / x_std) ** 2 + ((y - y_pred) / y_std) ** 2)

    return beta, beta_err, y_pred, orth_resid


def fit_regression(x, y, sx=None, sy=None, model='linear', method='ols',
                    degree=2, fixed_slope=None, fixed_intercept=None, delta=1.0):
    """Fits a model to (x, y) data.

    Parameters
    ----------
    x, y : array-like
        Point coordinates.
    sx, sy : array-like, optional
        Per-point uncertainties for ``x``/``y``. Only used by ``'tls'``/
        ``'deming'``; ignored by ``'ols'``. If ``None``, TLS/Deming falls
        back to an equal-weight (unweighted) orthogonal-distance fit.
    model : {'linear', 'polynomial', 'exponential', 'logarithmic'}
    method : {'ols', 'tls', 'deming'}
        ``'tls'`` always uses equal weights (``sx=sy=None``) even if
        uncertainties were supplied, i.e. classic total least squares.
        ``'deming'`` uses supplied ``sx``/``sy`` if available, otherwise a
        scalar variance-ratio ``delta = sy^2/sx^2`` (default 1, equivalent
        to unweighted TLS).
    degree : int
        Polynomial degree, only used when ``model='polynomial'``.
    fixed_slope, fixed_intercept : float, optional
        Fix one of the two parameters of a 2-parameter (degree-1 linear,
        exponential, or logarithmic) fit and solve only for the other.
        Mutually exclusive; ignored for polynomial degree > 1.
    delta : float
        Assumed sigma_y^2/sigma_x^2 ratio for Deming regression when no
        per-point uncertainties are available.

    Returns
    -------
    RegressionResult
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if fixed_slope is not None and fixed_intercept is not None:
        raise ValueError("fixed_slope and fixed_intercept are mutually exclusive.")

    X, target_kind, back_transform, predict_from_beta, param_names = _design_matrix(model, x, degree)
    y_target = _target(model, y, target_kind)
    x_pred = X[:, 1] if model == 'logarithmic' else x

    if method == 'ols':
        beta, beta_err, y_pred_t, leverage, cooks_d = _fit_ols(
            X, y_target, fixed_slope=fixed_slope, fixed_intercept=fixed_intercept)
        orth_resid = None
    elif method in ('tls', 'deming'):
        if method == 'tls':
            use_sx, use_sy = None, None
        else:
            use_sx, use_sy = sx, sy
            if use_sx is None and use_sy is None and delta != 1.0:
                use_sx, use_sy = 1.0, float(np.sqrt(delta))
        beta, beta_err, y_pred_t, orth_resid = _fit_odr(
            X, y_target, x_pred, use_sx, use_sy,
            fixed_slope=fixed_slope, fixed_intercept=fixed_intercept)
        leverage, cooks_d = None, None
    else:
        raise ValueError(f"Unknown method: {method!r}. Expected one of {METHODS}.")

    params = back_transform(beta)
    # param errors propagate 1:1 in linear space; exponential's 'a' error
    # is only approximate (delta method) since a = exp(b0).
    if model == 'exponential':
        param_errors = np.array([params[0] * beta_err[0], beta_err[1]])
    else:
        param_errors = beta_err

    residuals = y_target - y_pred_t
    r_squared = _r_squared(y_target, y_pred_t)
    equation_str = _equation_str(model, params)

    def predict(xnew):
        return predict_from_beta(params, np.asarray(xnew, dtype=float))

    return RegressionResult(
        model=model, method=method, params=params, param_errors=param_errors,
        param_names=param_names, r_squared=r_squared, residuals=residuals,
        n=len(x), equation_str=equation_str, predict=predict,
        leverage=leverage, cooks_distance=cooks_d, orthogonal_residual=orth_resid,
    )


def detect_outliers(values, method='zscore', threshold=2.0):
    """Flags outliers in a 1-D array of diagnostic values.

    Parameters
    ----------
    values : array-like
        Residuals (for ``'zscore'``/``'iqr'``) or Cook's distances (for
        ``'cooks_distance'``, where ``threshold`` is typically ``4/n``).
    method : {'zscore', 'iqr', 'cooks_distance'}
    threshold : float

    Returns
    -------
    numpy.ndarray of bool
        ``True`` where the point is flagged as an outlier.
    """
    values = np.asarray(values, dtype=float)

    if method == 'zscore':
        std = np.std(values)
        if std == 0:
            return np.zeros_like(values, dtype=bool)
        z = (values - np.mean(values)) / std
        return np.abs(z) > threshold

    if method == 'iqr':
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        lo, hi = q1 - threshold * iqr, q3 + threshold * iqr
        return (values < lo) | (values > hi)

    if method == 'cooks_distance':
        return values > threshold

    raise ValueError(f"Unknown outlier method: {method!r}.")


def get_uncertainty_vector(data, field):
    """Looks up a per-point uncertainty array for ``field``, if one exists.

    Uncertainty is stored as a separate column tagged with the ``'analyte'``
    attribute (linking it back to ``field``) and an ``'uncertainty'``
    attribute (``'sd'``/``'se'``), the convention used by ``SpotImporter``
    for spot-imported data. Returns ``None`` (equal weights) if no such
    column exists, which is the common case for raster map data today.
    """
    df = data.processed
    for col in df.match_attribute('analyte', field):
        if df.is_attribute(col, 'uncertainty'):
            return df[col][data.mask].values
    return None
