"""Lu-Hf geochronology: single-pixel date maps, per-cluster isochron
regression with Monte Carlo age uncertainty, isochron reference-line
overlays, and log-space bilateral smoothing of isotope maps.

Ported from a MATLAB workflow (``process_maps.m`` and supporting functions).
The total-least-squares/Deming regression itself reuses
``src.common.RegressionModel.fit_regression`` rather than re-deriving
SVD-based TLS from scratch -- only the Lu-Hf-specific date conversion, the
Monte Carlo age-uncertainty loop, and the isochron reference-line overlay
are new.

Only Lu-Hf has real math implemented here, matching what is actually
implemented (as opposed to stubbed) in the source MATLAB code.
"""
import numpy as np
import cv2

from PyQt6.QtWidgets import QMessageBox

from src.common import RegressionModel as rm
from src.common.Logger import log, auto_log_methods

# 176Lu decay constant and CHUR intercept, Sonderlund et al., EPSL, 2004,
# https://doi.org/10.1016/S0012-821X(04)00012-3
LU_HF = {
    'lambda': 1.867e-5,          # Ma^-1
    'lambda_unc': 0.008e-5,      # Ma^-1
    'Hf176_Hf177_i': 0.2829,     # CHUR intercept for 176Hf/177Hf
    'Hf176_Hf177_i_unc': 0.003,
}

DATING_METHODS = ['Lu-Hf', 'Re-Os', 'Sm-Nd', 'Rb-Sr', 'U-Pb', 'Th-Pb', 'Pb-Pb']
IMPLEMENTED_METHODS = ['Lu-Hf']


# ---------------------------------------------------------------------------
# Pure date/age math (ports of fwd_dates.m / inv_dates.m / fwd_time.m / inv_time.m)
# ---------------------------------------------------------------------------

def fwd_date(hf176_hf177, lu176_hf177, intercept=None, decay_const=None):
    """Per-pixel forward (normal-space) Lu-Hf date. Port of ``fwd_dates.m``.

    ``real(log(x))`` in the MATLAB source is equivalent to ``log(abs(x))``
    for real ``x`` (the real part of the complex log of a negative number),
    used there to tolerate noise-driven negative arguments rather than
    raising -- reproduced here via ``np.abs`` instead of a complex dtype.
    """
    if intercept is None:
        intercept = LU_HF['Hf176_Hf177_i']
    if decay_const is None:
        decay_const = LU_HF['lambda']
    hf176_hf177 = np.asarray(hf176_hf177, dtype=float)
    lu176_hf177 = np.asarray(lu176_hf177, dtype=float)
    with np.errstate(invalid='ignore', divide='ignore'):
        arg = (hf176_hf177 - intercept) / lu176_hf177 + 1
        dates = np.log(np.abs(arg)) / decay_const
    dates = np.where(np.isinf(dates), np.nan, dates)
    return dates


def inv_date(hf177_hf176, lu176_hf176, intercept=None, decay_const=None):
    """Per-pixel inverse-space Lu-Hf date. Port of ``inv_dates.m``."""
    if intercept is None:
        intercept = 1.0 / LU_HF['Hf176_Hf177_i']
    if decay_const is None:
        decay_const = LU_HF['lambda']
    hf177_hf176 = np.asarray(hf177_hf176, dtype=float)
    lu176_hf176 = np.asarray(lu176_hf176, dtype=float)
    with np.errstate(invalid='ignore', divide='ignore'):
        arg = (1 - hf177_hf176 / intercept) / lu176_hf176 + 1
        dates = np.log(np.abs(arg)) / decay_const
    dates = np.where(np.isinf(dates), np.nan, dates)
    return dates


def fwd_time_mc(slope_samples, decay_const=None, decay_const_unc=None, alpha=0.95):
    """Date distribution from Monte Carlo slope draws (forward/normal space).

    Port of ``fwd_time.m``. Only the decay constant is perturbed for the
    forward-space conversion -- the MATLAB source also perturbs an
    intercept sample that turns out to be unused in ``t``'s formula.
    """
    if decay_const is None:
        decay_const = LU_HF['lambda']
    if decay_const_unc is None:
        decay_const_unc = LU_HF['lambda_unc']
    slope_samples = np.asarray(slope_samples, dtype=float)
    n = len(slope_samples)
    lam = decay_const
    if n > 1:
        lam = decay_const + decay_const_unc * np.random.standard_normal(n)
    with np.errstate(invalid='ignore', divide='ignore'):
        t = np.log(slope_samples + 1) / lam
    p = (1 - alpha) / 2
    valid = t[np.isfinite(t)]
    if valid.size == 0:
        return t, np.nan, np.nan, (np.nan, np.nan)
    return t, float(np.mean(valid)), float(np.std(valid)), tuple(np.quantile(valid, [p, 1 - p]))


def inv_time_mc(slope_samples, intercept_samples, decay_const=None, decay_const_unc=None,
                 intercept_unc=None, alpha=0.95):
    """Date distribution from Monte Carlo slope/intercept draws (inverse space).

    Port of ``inv_time.m``. ``intercept_unc`` should be the *inverse-space*
    intercept uncertainty (``Hf176_Hf177_i_unc / Hf176_Hf177_i**2``, i.e.
    linear error propagation of ``1/x``), matching the MATLAB source.
    """
    if decay_const is None:
        decay_const = LU_HF['lambda']
    if decay_const_unc is None:
        decay_const_unc = LU_HF['lambda_unc']
    if intercept_unc is None:
        intercept_unc = LU_HF['Hf176_Hf177_i_unc'] / LU_HF['Hf176_Hf177_i'] ** 2

    slope_samples = np.asarray(slope_samples, dtype=float)
    intercept_samples = np.asarray(intercept_samples, dtype=float)
    n = len(slope_samples)
    lam = np.full(n, decay_const)
    intercept = intercept_samples.copy()
    if n > 1:
        lam = decay_const + decay_const_unc * np.random.standard_normal(n)
        intercept = intercept_samples + intercept_unc * np.random.standard_normal(n)

    with np.errstate(invalid='ignore', divide='ignore'):
        r = slope_samples / intercept
    ind = np.isfinite(r) & (r < 1)

    t = np.full(n, np.nan)
    with np.errstate(invalid='ignore', divide='ignore'):
        t[ind] = np.log(1 - r[ind]) / lam[ind]

    valid = t[ind]
    valid = valid[np.isfinite(valid)]
    p = (1 - alpha) / 2
    if valid.size == 0:
        return t, np.nan, np.nan, (np.nan, np.nan)
    return t, float(np.mean(valid)), float(np.std(valid)), tuple(np.quantile(valid, [p, 1 - p]))


# ---------------------------------------------------------------------------
# Multi-pixel (per-cluster) isochron regression with Monte Carlo age
# ---------------------------------------------------------------------------

def fit_isochron_mc(x, y, method='normal', fixed_intercept=None, decay_const=None,
                     decay_const_unc=None, intercept_unc=None, regression_method='deming',
                     num_sim=1000, outlier_method='none', outlier_threshold=0.0):
    """Fits an isochron to (x, y) pixel data with Monte Carlo age uncertainty.

    Builds on ``RegressionModel.fit_regression`` (total-least-squares/Deming,
    with an optional fixed intercept) for the point estimate, then
    Monte-Carlo-resamples the fit around its own residual scatter (rather
    than MATLAB's decomposed sigma_x/sigma_y from the orthogonal residual
    projection -- a reasonable simplification, noted as a possible follow-up
    if it proves insufficiently faithful) to propagate slope uncertainty,
    the decay constant uncertainty, and (for inverse-space fits) the
    intercept uncertainty into an age distribution.

    Parameters
    ----------
    x, y : array-like
        Pixel ratio pairs -- (176Lu/177Hf, 176Hf/177Hf) for ``method='normal'``,
        or (176Lu/176Hf, 177Hf/176Hf) for ``method='inverse'``.
    method : {'normal', 'inverse'}
        Selects ``fwd_time_mc``/``inv_time_mc`` for the date conversion.
    fixed_intercept : float, optional
        Fixed y-intercept (CHUR value or its inverse); fit intercept if ``None``.
    regression_method : {'tls', 'deming'}
        Passed through to ``RegressionModel.fit_regression``.
    num_sim : int
        Number of Monte Carlo simulations for age uncertainty.
    outlier_method : {'none', 'zscore', 'iqr'}
        Passed through to ``RegressionModel.detect_outliers``; flagged points
        are excluded and the fit is redone once.

    Returns
    -------
    dict
        ``n``, ``n_outliers``, ``outlier_mask``, ``x``, ``y`` (post-outlier-removal),
        ``slope``, ``intercept``, ``r_squared``, ``slope_ci``, ``t`` (age samples),
        ``age_mean``, ``age_std``, ``age_ci``. On failure (fewer than 3 valid
        pixels), returns ``{'n': ..., 'error': ...}``.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]

    result = {'n': len(x), 'method': method}
    if len(x) < 3:
        result['error'] = 'not enough valid pixels to fit (need >= 3)'
        return result

    def _fit(xx, yy):
        return rm.fit_regression(xx, yy, model='linear', method=regression_method,
                                  fixed_intercept=fixed_intercept)

    fit = _fit(x, y)

    outlier_mask = np.zeros(len(x), dtype=bool)
    if outlier_method != 'none':
        outlier_mask = rm.detect_outliers(fit.residuals, method=outlier_method,
                                           threshold=outlier_threshold or 2.0)
        if outlier_mask.any():
            x, y = x[~outlier_mask], y[~outlier_mask]
            fit = _fit(x, y)

    result['outlier_mask'] = outlier_mask
    result['n_outliers'] = int(outlier_mask.sum())
    result['x'] = x
    result['y'] = y
    result['slope'] = float(fit.params[1])
    result['intercept'] = float(fit.params[0])
    result['r_squared'] = float(fit.r_squared)

    # Monte Carlo: resample around the fit's own residual scatter and refit,
    # vectorized over all simulations at once (a per-simulation Python loop
    # calling the full TLS/Deming solver -- scipy.odr's iterative optimizer --
    # thousands of times is far too slow for interactive use on map-sized
    # pixel clusters). This closed-form linear refit matches what the source
    # MATLAB code's simulation loop actually does (a simple per-simulation
    # SVD/least-squares solve, not a full re-optimization each time).
    resid_std = float(np.std(fit.residuals)) if len(fit.residuals) else 0.0
    if resid_std > 0:
        y_noisy = y[None, :] + resid_std * np.random.standard_normal((num_sim, len(y)))
        if fixed_intercept is not None:
            slope_samples = np.sum(x[None, :] * (y_noisy - fixed_intercept), axis=1) / np.sum(x ** 2)
            intercept_samples = np.full(num_sim, fixed_intercept)
        else:
            x_mean = np.mean(x)
            x_centered = x - x_mean
            denom = np.sum(x_centered ** 2)
            slope_samples = np.sum(x_centered[None, :] * (y_noisy - np.mean(y_noisy, axis=1, keepdims=True)), axis=1) / denom
            intercept_samples = np.mean(y_noisy, axis=1) - slope_samples * x_mean
    else:
        slope_samples = np.full(num_sim, fit.params[1])
        intercept_samples = np.full(num_sim, fit.params[0])

    ok = np.isfinite(slope_samples) & np.isfinite(intercept_samples)
    slope_samples = slope_samples[ok]
    intercept_samples = intercept_samples[ok]

    if method == 'normal':
        t, t_mean, t_std, t_ci = fwd_time_mc(slope_samples, decay_const=decay_const,
                                              decay_const_unc=decay_const_unc)
    else:
        t, t_mean, t_std, t_ci = inv_time_mc(slope_samples, intercept_samples,
                                              decay_const=decay_const, decay_const_unc=decay_const_unc,
                                              intercept_unc=intercept_unc)

    result['t'] = t
    result['age_mean'] = t_mean
    result['age_std'] = t_std
    result['age_ci'] = t_ci
    if len(slope_samples):
        result['slope_ci'] = tuple(np.quantile(slope_samples, [0.025, 0.975]))
    else:
        result['slope_ci'] = (np.nan, np.nan)

    return result


def plot_isochron_lines(ax, method, intercept=None, decay_const=None):
    """Overlays Lu-Hf reference isochron lines on a scatter axes.

    Draws a reference line every 250 Ma from 0-4000 Ma (labeled every
    1000 Ma), in either normal-ratio space (``method='normal'``:
    ``y = intercept + x*(exp(lambda*t) - 1)``) or inverse-ratio space
    (``method='inverse'``: the line connecting ``(0, 1/intercept)`` to
    ``(1/(exp(lambda*t) - 1), 0)``). Port of ``plot_isochrons.m``, simplified
    to text-labeled reference lines instead of MATLAB's manual secondary-axis
    tick labeling (which relies on axes-positioning tricks that don't
    translate cleanly to matplotlib).
    """
    if decay_const is None:
        decay_const = LU_HF['lambda']
    if intercept is None:
        intercept = LU_HF['Hf176_Hf177_i']

    xl = ax.get_xlim()
    yl = ax.get_ylim()
    line_color = (0.5, 0.5, 0.5)

    if method == 'inverse':
        inv_intercept = 1.0 / intercept
        for t in np.arange(250, 4001, 250):
            x_end = 1.0 / (np.exp(decay_const * t) - 1)
            major = (t % 1000 == 0)
            ax.plot([0, x_end], [inv_intercept, 0], '-' if major else ':',
                     color=line_color, linewidth=1.5, zorder=1)
            if major and xl[0] <= x_end <= xl[1]:
                ax.annotate(f'{int(t)}', (x_end, 0), textcoords='offset points',
                            xytext=(0, 6), fontsize=7, color=line_color, ha='center')
    else:
        for t in np.arange(0, 4001, 250):
            y0 = intercept + xl[0] * (np.exp(decay_const * t) - 1)
            y1 = intercept + xl[1] * (np.exp(decay_const * t) - 1)
            major = (t % 1000 == 0)
            ax.plot(list(xl), [y0, y1], '-' if major else ':',
                     color=line_color, linewidth=1.5, zorder=1)
            if major and yl[0] <= y1 <= yl[1]:
                ax.annotate(f'{int(t)}', (xl[1], y1), textcoords='offset points',
                            xytext=(4, 0), fontsize=7, color=line_color, va='center')

    ax.set_xlim(xl)
    ax.set_ylim(yl)


# ---------------------------------------------------------------------------
# Isotope map smoothing (port of smooth_map2.m, minus the grid-regridding
# step -- LaME maps are already on a regular grid)
# ---------------------------------------------------------------------------

def smooth_isotope_field(array, array_size, order, sigma_spatial, sigma_intensity, cluster=None):
    """Log-space bilateral filter of a per-pixel field, preserving cluster means.

    Port of ``smooth_map2.m``: log-transforms the field, bilateral-filters
    spatially (edge-preserving), exponentiates back, then rescales per
    cluster (or globally, if ``cluster`` is ``None``) so the smoothed field's
    mean matches the original's -- bilateral filtering pulls outlier pixels
    toward their neighborhood, which otherwise biases cluster means.

    Parameters
    ----------
    array : numpy.ndarray
        Full-length 1D per-pixel field (as returned by ``get_map_data``).
    array_size : tuple
        ``(nrows, ncols)`` map shape, as ``SampleObj.array_size``.
    order : str
        Reshape order, as ``SampleObj.order`` (``'C'`` or ``'F'``).
    sigma_spatial : float
        Spatial extent (pixel diameter) of the bilateral filter.
    sigma_intensity : float
        Intensity-difference sigma of the bilateral filter (in log-space units).
    cluster : numpy.ndarray, optional
        Full-length 1D per-pixel cluster label array; if given, the
        mean-preservation rescale is computed per cluster instead of globally.

    Returns
    -------
    numpy.ndarray
        Smoothed, full-length 1D per-pixel field (positive values only,
        NaNs preserved where the input was NaN or non-positive).
    """
    array = np.asarray(array, dtype=float)
    valid = np.isfinite(array) & (array > 0)

    log_map = np.full(array.shape, np.nan)
    log_map[valid] = np.log(array[valid])

    grid = np.reshape(log_map, array_size, order=order)
    # cv2.bilateralFilter can't handle NaN -- fill with the map's own mean
    # for the filter pass, then restore NaN afterward.
    fill_value = np.nanmean(grid) if np.isfinite(grid).any() else 0.0
    grid_filled = np.nan_to_num(grid, nan=fill_value).astype(np.float32)

    filtered = cv2.bilateralFilter(grid_filled, int(round(sigma_spatial)) * 2 + 1,
                                    float(sigma_intensity), float(sigma_spatial))

    smoothed_log = np.reshape(filtered, array.shape, order=order)
    smoothed_log = np.where(valid, smoothed_log, np.nan)

    smoothed = np.full(array.shape, np.nan)
    smoothed[valid] = np.exp(smoothed_log[valid])

    # rescale to preserve the mean (globally or per cluster)
    if cluster is not None:
        cluster = np.asarray(cluster)
        for c in np.unique(cluster[valid]):
            if not np.isfinite(c):
                continue
            ind = valid & (cluster == c)
            if not ind.any():
                continue
            mu_raw = np.mean(array[ind])
            mu_smooth = np.mean(smoothed[ind])
            if mu_smooth > 0:
                smoothed[ind] *= mu_raw / mu_smooth
    else:
        mu_raw = np.mean(array[valid])
        mu_smooth = np.mean(smoothed[valid])
        if mu_smooth > 0:
            smoothed[valid] *= mu_raw / mu_smooth

    return smoothed


@auto_log_methods(logger_key="Geochron")
class Geochronology():
    """Lu-Hf geochronology engine, driving the Dating tab in ``SpecialTools.py``.

    Single-pixel date maps are written directly as new 'Calculated' fields
    (viewable via the existing Field Map/Histogram plot types); the
    multi-pixel isochron fit renders on the new ``'isochron'`` plot type.
    """
    DATING_METHODS = DATING_METHODS
    IMPLEMENTED_METHODS = IMPLEMENTED_METHODS

    def __init__(self, ui=None):
        self.ui = ui
        self._last_results = {}

    @property
    def dating_tab(self):
        """The DatingTab widget, if the Special Tools page is currently open."""
        control_dock = getattr(self.ui, 'control_dock', None)
        special_tools = getattr(control_dock, 'special_tools', None)
        return getattr(special_tools, 'dating', None)

    def _set_isotope_default(self, dt, index, field_type, field, available):
        """Populates isotope combobox pair ``index`` and selects ``field`` if present."""
        type_box = dt.comboBoxIsotopeAgeFieldType[index]
        field_box = dt.comboBoxIsotopeAgeField[index]

        dt.parent.update_field_type_combobox(type_box)
        items = [type_box.itemText(i) for i in range(type_box.count())]
        if field_type in items:
            type_box.setCurrentText(field_type)

        dt.parent.update_field_combobox(type_box, field_box)
        if field in available:
            field_box.setCurrentText(field)

    def callback_dating_method(self):
        """Updates isotope field defaults and decay constants for the selected dating method."""
        dt = self.dating_tab
        if dt is None or self.ui.app_data.current_data is None:
            return

        method = dt.comboBoxDatingMethod.currentText()
        if not method.startswith('Lu-Hf'):
            QMessageBox.information(self.ui, 'Not implemented',
                f"{method} is not yet implemented; only Lu-Hf dating is currently supported.")
            return

        data = self.ui.app_data.current_data.processed
        ratio_list = list(data.match_attribute('data_type', 'Ratio'))

        # LaME's ratio-field naming convention is "<num> / <den>" (confirmed
        # via ExtendedDF/DataHandling.py's ' / '.split() usage throughout).
        defaults = ['Hf176 / Hf177', 'Lu176 / Hf177', 'Hf177 / Hf176', 'Lu176 / Hf176']
        for i, field in enumerate(defaults):
            self._set_isotope_default(dt, i, 'Ratio', field, ratio_list)

        dt.lineEditDecayConstant.value = LU_HF['lambda']
        dt.lineEditDecayConstantUncertainty.value = LU_HF['lambda_unc']

    def _selected_ratio_arrays(self, dt, data):
        """Reads the 4 selected isotope ratio fields as full-length numpy arrays."""
        arrays = []
        for type_box, field_box in zip(dt.comboBoxIsotopeAgeFieldType, dt.comboBoxIsotopeAgeField):
            field = field_box.currentText()
            field_type = type_box.currentText()
            if not field:
                raise ValueError('one or more isotope ratio fields is not selected')
            arrays.append(data.get_map_data(field, field_type)['array'].values)
        return arrays  # [Hf176_Hf177, Lu176_Hf177, Hf177_Hf176, Lu176_Hf176]

    def compute_date_map(self):
        """Computes single-pixel forward and inverse Lu-Hf dates for every pixel.

        Writes the results as new 'Calculated' fields ('Lu-Hf date (fwd)' and
        'Lu-Hf date (inv)'), viewable immediately via the ordinary Field Map
        and Histogram plot types -- no new plotting code needed for this path.
        """
        dt = self.dating_tab
        if dt is None:
            return
        data = self.ui.app_data.current_data
        if data is None:
            QMessageBox.warning(self.ui, 'Warning', 'No sample loaded.')
            return

        method = dt.comboBoxDatingMethod.currentText()
        if not method.startswith('Lu-Hf'):
            QMessageBox.information(self.ui, 'Not implemented',
                f"{method} is not yet implemented; only Lu-Hf dating is currently supported.")
            return

        decay_const = dt.lineEditDecayConstant.value
        try:
            hf176_hf177, lu176_hf177, hf177_hf176, lu176_hf176 = self._selected_ratio_arrays(dt, data)
        except Exception as exc:
            QMessageBox.warning(self.ui, 'Warning', f'Could not read ratio fields.\n{exc}')
            return

        date_fwd = fwd_date(hf176_hf177, lu176_hf177, decay_const=decay_const)
        date_inv = inv_date(hf177_hf176, lu176_hf176, decay_const=decay_const)

        data.add_columns('Calculated', ['Lu-Hf date (fwd)', 'Lu-Hf date (inv)'],
                          np.column_stack([date_fwd, date_inv]))

        log("Computed single-pixel Lu-Hf date maps ('Lu-Hf date (fwd)', 'Lu-Hf date (inv)')", prefix="Geochron")

        if hasattr(self.ui, 'plot_tree'):
            self.ui.plot_tree.add_calculated_leaf('Lu-Hf date (fwd)')
            self.ui.plot_tree.add_calculated_leaf('Lu-Hf date (inv)')

    def compute_multipixel_isochron(self):
        """Fits an isochron to each selected cluster and shows it as a new 'isochron' plot.

        Reads the selected clusters from the Cluster Filtering tab
        (``app_data.cluster_dict[method]['selected_clusters']``); if none are
        selected, fits all clusters present. Results are cached on
        ``self._last_results`` for ``copy_results_to_notes``.
        """
        dt = self.dating_tab
        if dt is None:
            return
        app_data = self.ui.app_data
        data = app_data.current_data
        if data is None:
            QMessageBox.warning(self.ui, 'Warning', 'No sample loaded.')
            return

        method = dt.comboBoxDatingMethod.currentText()
        if not method.startswith('Lu-Hf'):
            QMessageBox.information(self.ui, 'Not implemented',
                f"{method} is not yet implemented; only Lu-Hf dating is currently supported.")
            return

        # cluster_method is the globally active clustering algorithm (set on
        # the Clustering tab), independent of whatever plot type/C-field is
        # currently displayed -- using app_data.c_field/c_field_type here
        # instead would require the user to first switch to a plot type with
        # C-field set to Cluster before this button would do anything, which
        # is backwards (this button is what switches to the isochron plot).
        cluster_method = app_data.cluster_method
        if not cluster_method or cluster_method not in app_data.cluster_dict \
                or cluster_method not in data.processed.columns:
            QMessageBox.information(self.ui, 'Dating',
                'Compute clusters first (Clustering tab) to fit a multi-pixel isochron.')
            return

        try:
            hf176_hf177, lu176_hf177, hf177_hf176, lu176_hf176 = self._selected_ratio_arrays(dt, data)
        except Exception as exc:
            QMessageBox.warning(self.ui, 'Warning', f'Could not read ratio fields.\n{exc}')
            return

        cluster_labels = data.processed[cluster_method].values
        selected = app_data.cluster_dict[cluster_method].get('selected_clusters') or []
        if not selected:
            selected = sorted({int(c) for c in cluster_labels if np.isfinite(c)})

        decay_const = dt.lineEditDecayConstant.value
        decay_const_unc = dt.lineEditDecayConstantUncertainty.value

        results = {}
        for c in selected:
            ind = cluster_labels == c
            res_fwd = fit_isochron_mc(lu176_hf177[ind], hf176_hf177[ind], method='normal',
                                       fixed_intercept=LU_HF['Hf176_Hf177_i'], decay_const=decay_const,
                                       decay_const_unc=decay_const_unc)
            res_inv = fit_isochron_mc(lu176_hf176[ind], hf177_hf176[ind], method='inverse',
                                       fixed_intercept=1.0 / LU_HF['Hf176_Hf177_i'], decay_const=decay_const,
                                       decay_const_unc=decay_const_unc)
            results[int(c)] = {'normal': res_fwd, 'inverse': res_inv}

        self._last_results = {
            'sample_id': app_data.sample_id,
            'cluster_method': cluster_method,
            'clusters': results,
        }
        self._update_results_text(dt)

        # switch to the isochron plot type and trigger a redraw
        style_data = self.ui.style_data
        if style_data.plot_type != 'isochron':
            style_data.plot_type = 'isochron'
        if hasattr(self.ui, 'schedule_update'):
            self.ui.schedule_update()

    def _update_results_text(self, dt):
        lines = []
        for c, r in self._last_results.get('clusters', {}).items():
            lines.append(f"Cluster {c}:")
            for label, res in (('  forward', r['normal']), ('  inverse', r['inverse'])):
                if 'error' in res:
                    lines.append(f"{label}: {res['error']}")
                    continue
                lines.append(
                    f"{label}: n={res['n']} ({res['n_outliers']} outliers), "
                    f"age={res['age_mean']:.1f} +/- {res['age_std']:.1f} Ma "
                    f"(95% CI [{res['age_ci'][0]:.1f}, {res['age_ci'][1]:.1f}]), "
                    f"slope={res['slope']:.4g}, R2={res['r_squared']:.4f}"
                )
        dt.textEditDatingResults.setPlainText("\n".join(lines))

    def copy_results_to_notes(self):
        """Appends the last multi-pixel isochron results to the sample's Notes."""
        if not self._last_results.get('clusters'):
            QMessageBox.information(self.ui, 'Dating', 'No isochron results to copy yet.')
            return
        if not hasattr(self.ui, 'notes_dock'):
            QMessageBox.information(self.ui, 'Dating',
                'Open the Notes dock first (View > Notes) before copying results.')
            return

        dt = self.dating_tab
        text = dt.textEditDatingResults.toPlainText() if dt is not None else ''
        header = f"Lu-Hf isochron results ({self._last_results.get('sample_id', '')})"
        self.ui.notes_dock.notes.print_info(f"{header}\n{text}\n")

    def smooth_isotope_fields(self):
        """Bilateral-smooths the 4 selected ratio fields and saves them as new Calculated fields."""
        dt = self.dating_tab
        if dt is None:
            return
        app_data = self.ui.app_data
        data = app_data.current_data
        if data is None:
            QMessageBox.warning(self.ui, 'Warning', 'No sample loaded.')
            return

        try:
            sigma_spatial = dt.lineEditSigmaSpatial.value
            sigma_intensity = dt.lineEditSigmaIntensity.value
        except Exception:
            QMessageBox.warning(self.ui, 'Warning', 'Invalid spatial/intensity sigma value.')
            return

        cluster_method = app_data.cluster_method
        cluster = None
        if cluster_method and cluster_method in data.processed.columns:
            cluster = data.processed[cluster_method].values

        new_fields = []
        for type_box, field_box in zip(dt.comboBoxIsotopeAgeFieldType, dt.comboBoxIsotopeAgeField):
            field = field_box.currentText()
            field_type = type_box.currentText()
            if not field:
                continue
            array = data.get_map_data(field, field_type)['array'].values
            smoothed = smooth_isotope_field(array, data.array_size, data.order,
                                             sigma_spatial, sigma_intensity, cluster=cluster)
            new_name = f'{field} (smoothed)'
            data.add_columns('Calculated', new_name, smoothed)
            new_fields.append(new_name)

        if new_fields and hasattr(self.ui, 'plot_tree'):
            for name in new_fields:
                self.ui.plot_tree.add_calculated_leaf(name)

        log(f"Smoothed isotope fields: {new_fields}", prefix="Geochron")

    def add_ree(self, sample_df):
        """Adds predefined sums of rare earth elements to calculated fields.

        Computes four separate sums, LREE, MREE, HREE, and REE. Elements not
        analyzed are ignored by the sum.

        * ``lree = ['la', 'ce', 'pr', 'nd', 'sm', 'eu', 'gd']``
        * ``mree = ['sm', 'eu', 'gd']``
        * ``hree = ['tb', 'dy', 'ho', 'er', 'tm', 'yb', 'lu']``

        Parameters
        ----------
        sample_df : pandas.DataFrame
            Sample data

        Returns
        -------
        pandas.DataFrame
            REE dataframe
        """
        import pandas as pd

        lree = ['la', 'ce', 'pr', 'nd', 'sm', 'eu', 'gd']
        mree = ['sm', 'eu', 'gd']
        hree = ['tb', 'dy', 'ho', 'er', 'tm', 'yb', 'lu']

        lree_cols = [col for col in sample_df.columns if any(col.lower().startswith(iso) for iso in lree)]
        hree_cols = [col for col in sample_df.columns if any(col.lower().startswith(iso) for iso in hree)]
        mree_cols = [col for col in sample_df.columns if any(col.lower().startswith(iso) for iso in mree)]
        ree_cols = lree_cols + hree_cols

        ree_df = pd.DataFrame(index=sample_df.index)
        ree_df['LREE'] = sample_df[lree_cols].sum(axis=1)
        ree_df['HREE'] = sample_df[hree_cols].sum(axis=1)
        ree_df['MREE'] = sample_df[mree_cols].sum(axis=1)
        ree_df['REE'] = sample_df[ree_cols].sum(axis=1)

        return ree_df
