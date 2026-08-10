"""2-D coupled multicomponent diffusion modeling, starting with garnet
Fe-Mg-Mn-Ca interdiffusion.

The module-level functions are a **pure numerical library** -- deliberately
no Qt/UI imports and no ``SampleObj`` access. Every function takes explicit
arrays/scalars and returns plain data (dicts of numpy arrays, floats), so it
is unit-testable without the app running and callable from a future non-GUI
(batch/script) context for free. ``DiffusionDock`` (bottom of this file, co-
located the same way Lu-Hf dating's engine and ``GeochronDock`` share
``geochronology.py``) is the UI layer: it gathers parameters from widgets,
calls the functions above with those plain values, and is itself responsible
for writing the returned results back into a ``SampleObj`` (via
``add_columns``) and onto plots/Notes -- the functions above never do this
themselves.

v1 scope (see the project plan for the full list): solves directly on the
map's native pixel grid with an immersed-boundary mask (no FEM mesh); full
coupled multicomponent diffusion (not independent per-element diffusion),
using the standard "constrained multicomponent diffusion in a fixed lattice"
formulation (Loomis 1990; Chakraborty & Ganguly 1991-style); a fixed (not
composition-updated) diffusivity matrix evaluated once at a reference
composition; Dirichlet boundary pixels (both the true grain rim and the
margins of any internal dissolution void, since both are simply "not part of
the grain mask"); isothermal-duration-only T-t fitting (temperature is a
required input, only duration is fit). ``fit_tt_isothermal``'s reported
duration uncertainty is a regression (least-squares Jacobian/covariance)
uncertainty, not a Monte Carlo propagation of input-composition uncertainty
-- ``fit_isochron_mc`` in ``src.common.geochronology`` is the template for
that as a future iteration.
"""
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import splu
from scipy.ndimage import binary_erosion, generate_binary_structure, distance_transform_edt
from scipy.optimize import least_squares

from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtWidgets import (
        QMessageBox, QWidget, QGroupBox, QVBoxLayout, QScrollArea, QFormLayout,
        QComboBox, QLabel, QGridLayout, QPushButton, QPlainTextEdit, QSpacerItem,
        QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView,
    )

from lame_core.CustomWidgets import CustomDockWidget, CustomLineEdit
from lame_core.config import APPDATA_PATH
from src.control.FieldLogic import FieldLogicUI
from src.control.Logger import auto_log_methods

R_GAS = 8.314462618  # J / (mol K)

GARNET_ELEMENTS = ['Fe', 'Mg', 'Mn']  # independent components
GARNET_DEPENDENT = 'Ca'  # recovered by mass balance: X_Ca = 1 - sum(others)

DIFFUSION_MINERALS = ['Garnet']
IMPLEMENTED_MINERALS = ['Garnet']

_NEIGHBOR_OFFSETS = [(-1, 0, 'y'), (1, 0, 'y'), (0, -1, 'x'), (0, 1, 'x')]


# ---------------------------------------------------------------------------
# Arrhenius diffusivity and the coupled interdiffusion matrix
# ---------------------------------------------------------------------------

def arrhenius_D(T_K, D0, Ea):
    """Arrhenius diffusivity, ``D = D0 * exp(-Ea / (R*T))``.

    Parameters
    ----------
    T_K : float or ndarray
        Temperature, Kelvin.
    D0 : float
        Pre-exponential factor, m^2/s.
    Ea : float
        Activation energy, J/mol.

    Returns
    -------
    float or ndarray
        Diffusivity, m^2/s.
    """
    return D0 * np.exp(-Ea / (R_GAS * T_K))


def build_interdiffusion_matrix(D_self, X_ref, dependent=GARNET_DEPENDENT, order=None):
    """Builds the fixed-lattice constrained multicomponent interdiffusion matrix.

    ``D_ij = delta_ij * D_i - X_i * (D_i - D_dependent)`` for independent
    components ``i, j`` (Loomis 1990; Chakraborty & Ganguly 1991-style
    formulation for diffusion of ``n`` components constrained to a fixed
    number of lattice sites, with one dependent component recovered by mass
    balance). Collapses to ``D_i * I`` (a diagonal matrix, independent
    per-element diffusion) when every component shares the same self-diffusivity.

    Parameters
    ----------
    D_self : dict
        ``{element: diffusivity}`` (m^2/s) -- must include every independent
        element in ``order`` plus ``dependent``.
    X_ref : dict
        ``{element: mole fraction}`` reference composition the matrix is
        evaluated at (held fixed for the whole model run in v1 -- see module
        docstring).
    dependent : str, optional
        The mass-balance-derived component, by default ``GARNET_DEPENDENT`` ('Ca').
    order : list of str, optional
        Independent-component order. Defaults to ``GARNET_ELEMENTS``.

    Returns
    -------
    D_matrix : numpy.ndarray
        Square interdiffusion matrix, shape ``(len(order), len(order))``.
    order : list of str
        The independent-component order used to build ``D_matrix`` (echoed
        back so callers that pass ``order=None`` know the row/column labels).
    """
    if order is None:
        order = list(GARNET_ELEMENTS)

    D_dep = D_self[dependent]
    n = len(order)
    D_matrix = np.zeros((n, n))
    for i, ei in enumerate(order):
        for j in range(n):
            delta = 1.0 if i == j else 0.0
            D_matrix[i, j] = delta * D_self[ei] - X_ref[ei] * (D_self[ei] - D_dep)

    return D_matrix, order


# ---------------------------------------------------------------------------
# Resource loading
# ---------------------------------------------------------------------------

def load_diffusivity_params(mineral='Garnet'):
    """Loads diffusivity parameters for a mineral from the app's resource CSV.

    Parameters
    ----------
    mineral : str, optional
        Mineral name to filter on (case-insensitive), by default ``'Garnet'``.

    Returns
    -------
    pandas.DataFrame
        Rows for ``mineral`` from ``resources/app_data/diffusion_constants.csv``
        (columns: ``mineral, element, D0_m2_s, D0_uncertainty, Ea_kJ_mol,
        Ea_uncertainty, T_min_K, T_max_K, P_reference_GPa, orientation,
        reference, notes``), index reset.
    """
    path = APPDATA_PATH / 'diffusion_constants.csv'
    df = pd.read_csv(path)
    return df[df['mineral'].str.lower() == mineral.lower()].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Domain / boundary handling on the native pixel grid (immersed-boundary style)
# ---------------------------------------------------------------------------

def erode_interior_mask(mask_2d):
    """Splits a grain pixel-mask into interior (solved) and boundary (fixed) pixels.

    ``interior`` = mask pixels whose 4 neighbors are all also in the mask.
    ``boundary`` = the remaining mask pixels -- this uniformly covers both the
    true exterior grain rim and the margins of any internal dissolution void,
    since both are simply "adjacent to a non-mask pixel." No special-casing
    of voids vs. rim is needed or performed.

    Parameters
    ----------
    mask_2d : numpy.ndarray of bool
        2-D grain pixel mask.

    Returns
    -------
    interior_2d, boundary_2d : numpy.ndarray of bool
        Same shape as ``mask_2d``.
    """
    structure = generate_binary_structure(2, 1)  # 4-connectivity
    interior_2d = binary_erosion(mask_2d, structure=structure, border_value=0)
    boundary_2d = mask_2d & ~interior_2d
    return interior_2d, boundary_2d


def initial_core_composition(observed_2d, mask_2d, core_fraction=0.1):
    """Estimates a homogeneous pre-diffusion core composition from observed data.

    Uses a distance transform to find the pixels furthest from the mask edge
    (the "most interior" pixels, most likely to be least affected by rim
    diffusion) and takes their median observed value.

    Parameters
    ----------
    observed_2d : numpy.ndarray
        Observed composition map, same shape as ``mask_2d``.
    mask_2d : numpy.ndarray of bool
        Grain pixel mask.
    core_fraction : float, optional
        Fraction of in-mask pixels (by distance-transform depth) to treat as
        "core", by default 0.1 (the deepest 10%).

    Returns
    -------
    float
    """
    dist = distance_transform_edt(mask_2d)
    depths = dist[mask_2d]
    threshold = np.quantile(depths, 1 - core_fraction)
    core_mask = mask_2d & (dist >= threshold)
    return float(np.median(observed_2d[core_mask]))


def build_laplacian_operator(interior_2d, boundary_2d, dx, dy):
    """Builds the 5-point finite-difference Laplacian restricted to interior pixels.

    Boundary-pixel contributions are split out into a separate coupling
    matrix rather than folded into ``L`` itself, so a caller can combine them
    with fixed (Dirichlet) boundary values on the right-hand side of a
    time-stepping scheme without needing ghost cells outside the domain.

    Parameters
    ----------
    interior_2d, boundary_2d : numpy.ndarray of bool
        From :func:`erode_interior_mask`.
    dx, dy : float
        Pixel spacing (consistent units, e.g. meters).

    Returns
    -------
    L : scipy.sparse.csr_matrix
        Interior-only Laplacian, shape ``(n_interior, n_interior)``.
    boundary_coupling : scipy.sparse.csr_matrix
        Maps a boundary-pixel value vector to its contribution to each
        interior row, shape ``(n_interior, n_boundary)``.
    interior_index_map : dict
        ``{(row, col): interior_index}``.
    boundary_index_map : dict
        ``{(row, col): boundary_index}``.
    """
    interior_coords = [tuple(rc) for rc in np.argwhere(interior_2d)]
    boundary_coords = [tuple(rc) for rc in np.argwhere(boundary_2d)]
    interior_index_map = {rc: k for k, rc in enumerate(interior_coords)}
    boundary_index_map = {rc: k for k, rc in enumerate(boundary_coords)}

    n_interior = len(interior_coords)
    n_boundary = len(boundary_coords)

    inv_dx2 = 1.0 / dx**2
    inv_dy2 = 1.0 / dy**2
    diag_coeff = -2.0 * (inv_dx2 + inv_dy2)
    axis_coeff = {'x': inv_dx2, 'y': inv_dy2}

    rows, cols, vals = [], [], []
    bc_rows, bc_cols, bc_vals = [], [], []

    for (r, c), k in interior_index_map.items():
        rows.append(k)
        cols.append(k)
        vals.append(diag_coeff)

        for dr, dc, axis in _NEIGHBOR_OFFSETS:
            neighbor = (r + dr, c + dc)
            coeff = axis_coeff[axis]
            if neighbor in interior_index_map:
                rows.append(k)
                cols.append(interior_index_map[neighbor])
                vals.append(coeff)
            elif neighbor in boundary_index_map:
                bc_rows.append(k)
                bc_cols.append(boundary_index_map[neighbor])
                bc_vals.append(coeff)
            # else: neighbor outside the mask entirely -- cannot happen for a
            # true interior pixel (erosion already guarantees all 4 neighbors
            # are in the mask), guarded here rather than asserted so a
            # malformed mask degrades gracefully (no flux through the gap).

    L = sparse.csr_matrix((vals, (rows, cols)), shape=(n_interior, n_interior))
    boundary_coupling = sparse.csr_matrix((bc_vals, (bc_rows, bc_cols)), shape=(n_interior, n_boundary))

    return L, boundary_coupling, interior_index_map, boundary_index_map


# ---------------------------------------------------------------------------
# Crank-Nicolson time-stepping for the coupled system
# ---------------------------------------------------------------------------

def forward_solve(u0, boundary_values, D_matrix, L, boundary_coupling, dt, n_steps):
    """Implicit (Crank-Nicolson) time-stepping of the coupled diffusion system.

    Solves ``du/dt = (D_matrix (x) L) u + (D_matrix (x) boundary_coupling) b``
    (``b`` = ``boundary_values``, held fixed for the whole run -- v1's
    Dirichlet-boundary assumption). The system matrix is factorized once
    (:func:`scipy.sparse.linalg.splu`) and the factorization is reused for
    every timestep -- Crank-Nicolson is unconditionally stable, so ``dt`` only
    needs to be chosen for resolution, not stability.

    Parameters
    ----------
    u0 : numpy.ndarray
        Initial interior state, shape ``(n_components, n_interior)``.
    boundary_values : numpy.ndarray
        Fixed (Dirichlet) boundary values, shape ``(n_components, n_boundary)``.
    D_matrix : numpy.ndarray
        Interdiffusion matrix, shape ``(n_components, n_components)``.
    L : scipy.sparse.spmatrix
        Interior Laplacian, shape ``(n_interior, n_interior)``.
    boundary_coupling : scipy.sparse.spmatrix
        Shape ``(n_interior, n_boundary)``.
    dt : float
        Timestep.
    n_steps : int
        Number of timesteps.

    Returns
    -------
    numpy.ndarray
        Final interior state, shape ``(n_components, n_interior)``.
    """
    n_comp, n_interior = u0.shape
    n_boundary = boundary_values.shape[1]

    A = sparse.kron(D_matrix, L, format='csc')
    BC = sparse.kron(D_matrix, boundary_coupling, format='csc')

    identity = sparse.identity(n_comp * n_interior, format='csc')
    lhs = (identity - 0.5 * dt * A).tocsc()
    rhs_op = (identity + 0.5 * dt * A).tocsc()

    b_flat = boundary_values.reshape(-1) if n_boundary else np.zeros(0)
    source = dt * (BC @ b_flat) if n_boundary else np.zeros(n_comp * n_interior)

    solver = splu(lhs)

    u = u0.reshape(-1).astype(float).copy()
    for _ in range(n_steps):
        rhs = rhs_op @ u + source
        u = solver.solve(rhs)

    return u.reshape(n_comp, n_interior)


def _default_n_steps(duration_s, D_self=None, dx=None, dy=None, default=50):
    """Default Crank-Nicolson step count.

    Crank-Nicolson is unconditionally stable, so the step count is an
    *accuracy* choice, not a *stability* requirement -- unlike an explicit
    scheme, it does not need a CFL-style ``dt ~ dx^2/D`` condition tied to
    pixel size. An earlier version of this heuristic used exactly that kind
    of pixel-resolution-based ``dt``, which is wrong for an implicit method
    and produced upwards of a million steps for realistic geological
    diffusivities/durations. A modest, fixed step count resolves the
    transient well regardless of grid spacing or duration (confirmed
    empirically: 10 vs. 100 steps produce near-identical modeled fields for
    this solver, and the flat-field/steady-state unit tests pass at any step
    count). ``D_self``/``dx``/``dy`` are accepted (and ignored) only to keep
    this a drop-in replacement at existing call sites; pass an explicit
    ``n_steps`` to :func:`garnet_forward_model`/:func:`fit_tt_isothermal`
    directly if a specific run ever needs more resolution.
    """
    return default


# ---------------------------------------------------------------------------
# Forward model and T-t inversion
# ---------------------------------------------------------------------------

def garnet_forward_model(duration_s, T_K, D0_dict, Ea_dict, mask_2d, dx, dy,
                          initial_X, boundary_X, X_ref=None, n_steps=None):
    """Runs the coupled 2-D garnet Fe-Mg-Mn diffusion forward model.

    Parameters
    ----------
    duration_s : float
        Model duration, seconds.
    T_K : float
        Fixed temperature, Kelvin (v1: isothermal only).
    D0_dict, Ea_dict : dict
        ``{element: value}`` for ``GARNET_ELEMENTS + [GARNET_DEPENDENT]``, SI
        units (D0 in m^2/s, Ea in J/mol).
    mask_2d : numpy.ndarray of bool
        Grain pixel mask.
    dx, dy : float
        Pixel spacing, meters.
    initial_X : dict
        ``{element: float}`` homogeneous initial (pre-diffusion) core
        composition for ``GARNET_ELEMENTS`` (``GARNET_DEPENDENT`` is derived
        by mass balance).
    boundary_X : dict
        ``{element: 2-D ndarray}`` observed composition maps (same shape as
        ``mask_2d``) -- boundary-pixel values are read off these as the fixed
        Dirichlet condition.
    X_ref : dict, optional
        Reference composition for the (fixed) interdiffusion matrix. Defaults
        to ``initial_X`` plus its mass-balance-derived dependent component.
    n_steps : int, optional
        Number of Crank-Nicolson steps. Defaults to a resolution-based
        heuristic (see :func:`_default_n_steps`).

    Returns
    -------
    dict
        ``{element: 2-D ndarray}`` modeled composition maps for
        ``GARNET_ELEMENTS`` (interior pixels solved, boundary pixels equal
        their observed value, pixels outside the mask are NaN).
    """
    elements = GARNET_ELEMENTS
    dependent = GARNET_DEPENDENT

    D_self = {e: arrhenius_D(T_K, D0_dict[e], Ea_dict[e]) for e in elements + [dependent]}

    if X_ref is None:
        X_ref = dict(initial_X)
        X_ref[dependent] = 1.0 - sum(initial_X[e] for e in elements)

    D_matrix, order = build_interdiffusion_matrix(D_self, X_ref, dependent=dependent)

    interior_2d, boundary_2d = erode_interior_mask(mask_2d)
    L, boundary_coupling, interior_index_map, boundary_index_map = build_laplacian_operator(
        interior_2d, boundary_2d, dx, dy)

    interior_coords = sorted(interior_index_map, key=interior_index_map.get)
    boundary_coords = sorted(boundary_index_map, key=boundary_index_map.get)
    n_interior = len(interior_coords)
    n_boundary = len(boundary_coords)
    n_comp = len(order)

    u0 = np.empty((n_comp, n_interior))
    for i, e in enumerate(order):
        u0[i, :] = initial_X[e]

    b = np.empty((n_comp, n_boundary))
    for i, e in enumerate(order):
        b[i, :] = [boundary_X[e][rc] for rc in boundary_coords]

    if n_steps is None:
        n_steps = _default_n_steps(duration_s, D_self, dx, dy)
    dt = duration_s / n_steps

    u_final = forward_solve(u0, b, D_matrix, L, boundary_coupling, dt, n_steps)

    result = {}
    for i, e in enumerate(order):
        arr = np.full(mask_2d.shape, np.nan)
        for k, rc in enumerate(interior_coords):
            arr[rc] = u_final[i, k]
        for rc in boundary_coords:
            arr[rc] = boundary_X[e][rc]
        result[e] = arr

    return result


def misfit_map(observed, modeled, mask=None):
    """Observed-minus-modeled residual map (v1's stand-in for a full Monte
    Carlo uncertainty map -- see module docstring).

    Parameters
    ----------
    observed, modeled : numpy.ndarray
        Same shape.
    mask : numpy.ndarray of bool, optional
        If given, pixels outside the mask are set to NaN.

    Returns
    -------
    numpy.ndarray
    """
    residual = observed - modeled
    if mask is not None:
        residual = np.where(mask, residual, np.nan)
    return residual


def tt_residual(duration_s, T_K, D0_dict, Ea_dict, mask_2d, dx, dy, initial_X,
                 boundary_X, observed_X, X_ref=None, n_steps=None):
    """``scipy.optimize.least_squares``-compatible residual function for
    fitting duration at a fixed temperature.

    Styled after ``erf_forward``/``erf_jac`` in
    ``global_geochemistry.modelling.inversion.models`` -- this codebase
    family's existing "forward model wrapped for scipy.optimize" convention.

    Parameters
    ----------
    duration_s : float or length-1 array-like
        Trial duration (``least_squares`` passes the parameter vector).
    T_K, D0_dict, Ea_dict, mask_2d, dx, dy, initial_X, boundary_X, X_ref
        See :func:`garnet_forward_model`.
    observed_X : dict
        ``{element: 2-D ndarray}`` observed composition maps.
    n_steps : int, optional
        Fixed Crank-Nicolson step count to use at every trial duration.
        **Important**: during an optimization loop, this should be fixed
        (not left ``None``) rather than recomputed per-trial -- letting
        :func:`garnet_forward_model`'s resolution heuristic pick a fresh
        *integer* step count for every trial duration makes the objective
        function's derivative discontinuous at each integer step-count change,
        which was found (empirically) to occasionally stall
        ``scipy.optimize.least_squares`` at a spurious "converged" point.
        :func:`fit_tt_isothermal` fixes this once per fit call.

    Returns
    -------
    numpy.ndarray
        Flattened observed-minus-modeled residuals over interior pixels, all
        elements concatenated.
    """
    duration_s = float(np.atleast_1d(duration_s)[0])
    duration_s = max(duration_s, 1e-6)

    modeled = garnet_forward_model(duration_s, T_K, D0_dict, Ea_dict, mask_2d, dx, dy,
                                    initial_X, boundary_X, X_ref=X_ref, n_steps=n_steps)
    interior_2d, _ = erode_interior_mask(mask_2d)

    residuals = [observed_X[e][interior_2d] - modeled[e][interior_2d] for e in GARNET_ELEMENTS]
    return np.concatenate(residuals)


def fit_tt_isothermal(observed_X, mask_2d, dx, dy, T_K, D0_dict, Ea_dict, initial_X,
                       boundary_X, duration0_s, bounds=(1e3, 1e17), X_ref=None):
    """Fits diffusion duration (fixed temperature) to observed 2-D zoning.

    v1 T-t parameterization: isothermal duration at a *given* temperature --
    one free parameter. A 2-parameter cooling path (peak T, cooling rate) is
    classically ill-posed from a single 2-D snapshot without independent
    constraints, so it's deliberately deferred (see module/plan docs).

    The reported ``duration_std_s`` is a regression uncertainty from the
    least-squares Jacobian/covariance -- **not** a Monte Carlo propagation of
    input-composition uncertainty (that is a deferred iteration; the
    vectorized MC pattern in ``src.common.geochronology.fit_isochron_mc`` is
    the template for it).

    Parameters
    ----------
    observed_X : dict
        ``{element: 2-D ndarray}`` observed composition maps to fit against.
    mask_2d, dx, dy, T_K, D0_dict, Ea_dict, initial_X, boundary_X, X_ref
        See :func:`garnet_forward_model`.
    duration0_s : float
        Initial guess for duration, seconds. Should be a physically reasonable
        estimate: once a trial duration is long enough to fully equilibrate the
        grain with its boundary composition, the forward model becomes
        insensitive to further increases (a genuine "closure" plateau, not a
        numerical artifact -- see ``tt_residual``), and the fit cannot recover
        from a starting guess inside that plateau.
    bounds : tuple of float, optional
        ``(min, max)`` duration bounds, seconds.

    Returns
    -------
    dict
        ``duration_s``, ``duration_std_s``, ``rms_misfit``, ``modeled``
        (``{element: 2-D ndarray}``), ``residual`` (``{element: 2-D ndarray}``,
        via :func:`misfit_map`), ``success`` (bool), ``message`` (str).

        Interpretive caveat, not enforced programmatically: boundary pixels
        are Dirichlet-fixed to their own observed value by construction, so
        their residual is always ~0 -- not diagnostic of fit quality.

    Notes
    -----
    Fits internally in log10(duration) space and converts back -- duration is
    a strictly-positive parameter that can span many orders of magnitude, and
    unscaled least-squares in raw-seconds space was found (empirically) to
    converge unreliably (the finite-difference Jacobian step becomes
    numerically insignificant relative to a ~1e10-scale parameter). The
    reported ``duration_std_s`` is converted from the log10-space covariance
    to linear duration via the delta method (``d(duration)/d(log10 duration)
    = duration * ln(10)``).

    Also fixes the Crank-Nicolson step count once (from ``duration0_s``,
    rather than letting it float per trial via :func:`garnet_forward_model`'s
    resolution heuristic) -- see the ``n_steps`` note on :func:`tt_residual`.
    """
    D_self = {e: arrhenius_D(T_K, D0_dict[e], Ea_dict[e]) for e in GARNET_ELEMENTS + [GARNET_DEPENDENT]}
    n_steps = max(20, _default_n_steps(duration0_s, D_self, dx, dy))

    def _log_residual(log10_duration, *args):
        duration_s = 10.0 ** float(np.atleast_1d(log10_duration)[0])
        return tt_residual(duration_s, *args)

    log_bounds = ([np.log10(bounds[0])], [np.log10(bounds[1])])
    result = least_squares(
        _log_residual,
        x0=[np.log10(duration0_s)],
        bounds=log_bounds,
        args=(T_K, D0_dict, Ea_dict, mask_2d, dx, dy, initial_X, boundary_X, observed_X, X_ref, n_steps),
    )

    duration_s = 10.0 ** float(result.x[0])

    try:
        dof = max(len(result.fun) - 1, 1)
        residual_variance = np.sum(result.fun**2) / dof
        JTJ = result.jac.T @ result.jac
        cov_log10 = residual_variance * np.linalg.inv(JTJ)
        std_log10 = float(np.sqrt(cov_log10[0, 0]))
        duration_std_s = duration_s * np.log(10.0) * std_log10
    except np.linalg.LinAlgError:
        duration_std_s = float('nan')

    modeled = garnet_forward_model(duration_s, T_K, D0_dict, Ea_dict, mask_2d, dx, dy,
                                    initial_X, boundary_X, X_ref=X_ref, n_steps=n_steps)
    residual_maps = {e: misfit_map(observed_X[e], modeled[e], mask_2d) for e in GARNET_ELEMENTS}
    rms_misfit = float(np.sqrt(np.mean(result.fun**2)))

    return {
        'duration_s': duration_s,
        'duration_std_s': duration_std_s,
        'rms_misfit': rms_misfit,
        'modeled': modeled,
        'residual': residual_maps,
        'success': bool(result.success),
        'message': result.message,
    }


# ---------------------------------------------------------------------------
# UI layer -- the only part of this module that touches Qt/SampleObj
# ---------------------------------------------------------------------------

_SECONDS_PER_YEAR = 365.25 * 24 * 3600


@auto_log_methods(logger_key='Diffusion')
class DiffusionDock(CustomDockWidget, FieldLogicUI):
    """2-D garnet diffusion modeling controls.

    Gathers parameters from its widgets, calls the plain functions above
    (``garnet_forward_model``/``fit_tt_isothermal``), and is itself
    responsible for writing the returned results back into the sample (via
    ``SampleObj.add_columns``) -- the functions above never touch
    ``SampleObj`` or Qt themselves. New columns are picked up automatically
    by the existing map-plotting code (``get_map_data``'s generic fallback
    for any non-Analyte/Ratio ``data_type``); no plot-tree entry is created
    until the user actually plots one, matching the Cluster/PCA score pattern.

    Opens as a floating panel (following ``GeochronDock``, the closest
    sibling analysis tool) rather than registering into a ``QMainWindow``
    dock area -- toggled from Tools > Diffusion.
    """
    def __init__(self, ui=None):
        self.ui = ui
        self.logger_key = 'Diffusion'

        super().__init__(ui)

        if ui is None:
            return

        self._region_masks = []
        self._last_results = {}

        self.setWindowTitle("Diffusion Modeling")
        self.setObjectName("DiffusionDock")

        self.setupUI()
        self.connect_widgets()

        self.setGeometry(QRect(0, 0, 300, 700))

    @property
    def app_data(self):
        """Delegate to ui.app_data so FieldLogicUI methods work correctly."""
        return self.ui.app_data

    @property
    def data(self):
        """Access current sample data without caching a reference."""
        if hasattr(self.ui, 'app_data'):
            return self.ui.app_data.current_data
        return None

    @data.setter
    def data(self, value):
        """Ignored -- data is always derived from ui.app_data.current_data."""
        pass

    def setupUI(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        container = QWidget()
        container.setGeometry(QRect(0, 0, 280, 303))

        scroll_area_layout = QVBoxLayout(container)
        scroll_area_layout.setContentsMargins(6, 6, 6, 6)
        scroll_area_layout.setObjectName("verticalLayoutDiffusion")

        # -- dimensionality / mineral / region --
        form_layout = QFormLayout()
        form_layout.setObjectName("formLayoutDiffusionSetup")

        self.comboBoxDimensionality = QComboBox(container)
        self.comboBoxDimensionality.setObjectName("comboBoxDimensionality")
        self.comboBoxDimensionality.addItems(["2D", "1D (not yet implemented)"])
        form_layout.addRow("Dimensionality", self.comboBoxDimensionality)

        self.comboBoxDiffusionMethod = QComboBox(container)
        self.comboBoxDiffusionMethod.setObjectName("comboBoxDiffusionMethod")
        for mineral in DIFFUSION_MINERALS:
            self.comboBoxDiffusionMethod.addItem(mineral)
            if mineral not in IMPLEMENTED_MINERALS:
                idx = self.comboBoxDiffusionMethod.count() - 1
                self.comboBoxDiffusionMethod.setItemText(idx, f"{mineral} (not yet implemented)")
        form_layout.addRow("Mineral", self.comboBoxDiffusionMethod)

        self.comboBoxRegion = QComboBox(container)
        self.comboBoxRegion.setObjectName("comboBoxRegion")
        self.comboBoxRegion.setToolTip(
            "Connected regions of the current filter/cluster/polygon selection "
            "(Mask dock) -- click Refresh to rebuild this list.")
        form_layout.addRow("Region", self.comboBoxRegion)

        self.pushButtonRefreshRegions = QPushButton("Refresh regions from current selection", container)
        self.pushButtonRefreshRegions.setObjectName("pushButtonRefreshRegions")

        self.comboBoxDiffusionProfile = QComboBox(container)
        self.comboBoxDiffusionProfile.setObjectName("comboBoxDiffusionProfile")
        self.comboBoxDiffusionProfile.setToolTip(
            "Existing profiles (Profile dock) available to draw across the modeled "
            "region once results are computed -- for reference only, this dock "
            "does not create or edit profiles itself.")
        form_layout.addRow("Profile", self.comboBoxDiffusionProfile)

        scroll_area_layout.addLayout(form_layout)
        scroll_area_layout.addWidget(self.pushButtonRefreshRegions)

        # -- element field pickers (independent components only -- Ca is the
        # mass-balance-derived dependent component, not a per-pixel input) --
        self.gridLayoutDiffusionFields = QGridLayout()
        self.gridLayoutDiffusionFields.setObjectName("gridLayoutDiffusionFields")

        self.labelElement = []
        self.comboBoxElementFieldType = []
        self.comboBoxElementField = []
        for i, element in enumerate(GARNET_ELEMENTS):
            label = QLabel(f"{element} (mole fraction)", container)
            label.setObjectName(f"labelElement{element}")
            self.gridLayoutDiffusionFields.addWidget(label, i, 0, 1, 1)
            self.labelElement.append(label)

            type_box = QComboBox(container)
            type_box.setMaximumSize(QSize(125, 16777215))
            type_box.setObjectName(f"comboBoxElementFieldType{element}")
            self.gridLayoutDiffusionFields.addWidget(type_box, i, 1, 1, 1)
            self.comboBoxElementFieldType.append(type_box)

            field_box = QComboBox(container)
            field_box.setObjectName(f"comboBoxElementField{element}")
            self.gridLayoutDiffusionFields.addWidget(field_box, i, 2, 1, 1)
            self.comboBoxElementField.append(field_box)

        scroll_area_layout.addLayout(self.gridLayoutDiffusionFields)

        # -- diffusivity constants (pre-filled from resources/app_data/diffusion_constants.csv) --
        constants_group = QGroupBox("Diffusivity Constants", container)
        constants_layout = QVBoxLayout(constants_group)

        self.tableWidgetDiffusionConstants = QTableWidget(constants_group)
        self.tableWidgetDiffusionConstants.setObjectName("tableWidgetDiffusionConstants")
        self.tableWidgetDiffusionConstants.setColumnCount(3)
        self.tableWidgetDiffusionConstants.setHorizontalHeaderLabels(["Element", "D0 (m²/s)", "Ea (kJ/mol)"])
        self.tableWidgetDiffusionConstants.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tableWidgetDiffusionConstants.setToolTip(
            "PLACEHOLDER values shipped with the app -- verify against primary "
            "garnet-diffusion literature before quantitative use. Editable.")
        constants_layout.addWidget(self.tableWidgetDiffusionConstants)

        scroll_area_layout.addWidget(constants_group)

        # -- run parameters --
        run_group = QGroupBox("Run", container)
        run_layout = QFormLayout(run_group)

        self.lineEditDiffusionTemperature = CustomLineEdit(precision=1, parent=run_group)
        self.lineEditDiffusionTemperature.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lineEditDiffusionTemperature.setObjectName("lineEditDiffusionTemperature")
        run_layout.addRow("Temperature (°C)", self.lineEditDiffusionTemperature)

        self.lineEditDiffusionDuration = CustomLineEdit(precision=4, parent=run_group)
        self.lineEditDiffusionDuration.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lineEditDiffusionDuration.setObjectName("lineEditDiffusionDuration")
        self.lineEditDiffusionDuration.setToolTip(
            "Duration (Run forward model) or initial guess (Fit duration), in thousands of years (ka).")
        run_layout.addRow("Duration (ka)", self.lineEditDiffusionDuration)

        self.pushButtonRunForwardModel = QPushButton("Run forward model", run_group)
        self.pushButtonRunForwardModel.setObjectName("pushButtonRunForwardModel")
        self.pushButtonRunForwardModel.setToolTip(
            "Run the forward model once at the given duration and temperature.")
        run_layout.addRow(self.pushButtonRunForwardModel)

        self.pushButtonFitDuration = QPushButton("Fit duration", run_group)
        self.pushButtonFitDuration.setObjectName("pushButtonFitDuration")
        self.pushButtonFitDuration.setToolTip(
            "Fit duration (at the given, fixed temperature) to the observed zoning, "
            "starting from the Duration field as the initial guess.")
        run_layout.addRow(self.pushButtonFitDuration)

        scroll_area_layout.addWidget(run_group)

        # -- results --
        results_group = QGroupBox("Results", container)
        results_layout = QVBoxLayout(results_group)

        self.textEditDiffusionResults = QPlainTextEdit(container)
        self.textEditDiffusionResults.setObjectName("textEditDiffusionResults")
        self.textEditDiffusionResults.setReadOnly(True)
        self.textEditDiffusionResults.setMaximumHeight(160)
        results_layout.addWidget(self.textEditDiffusionResults)

        self.pushButtonCopyToNotes = QPushButton("Copy to Notes", container)
        self.pushButtonCopyToNotes.setObjectName("pushButtonCopyToNotes")
        results_layout.addWidget(self.pushButtonCopyToNotes)

        scroll_area_layout.addWidget(results_group)

        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        scroll_area_layout.addItem(spacer)

        scroll_area.setWidget(container)
        self.setWidget(scroll_area)

        self._populate_diffusivity_table('Garnet')

    def connect_widgets(self):
        self.comboBoxDimensionality.activated.connect(self._guard_1d)
        self.comboBoxDiffusionMethod.activated.connect(self.callback_diffusion_method)
        self.pushButtonRefreshRegions.clicked.connect(self.refresh_regions)
        for type_box, field_box in zip(self.comboBoxElementFieldType, self.comboBoxElementField):
            type_box.activated.connect(lambda _, t=type_box, f=field_box: self.update_field_combobox(t, f))
        self.pushButtonRunForwardModel.clicked.connect(self.run_forward_model)
        self.pushButtonFitDuration.clicked.connect(self.fit_tt)
        self.pushButtonCopyToNotes.clicked.connect(
            lambda: self.ui.insert_info_note('diffusion results'))

    def _guard_1d(self, index):
        if index != 0:
            QMessageBox.information(self.ui, 'Not implemented', '1D diffusion modeling is not yet implemented.')
            self.comboBoxDimensionality.setCurrentIndex(0)

    def callback_diffusion_method(self):
        """Guards non-Garnet minerals and refreshes the diffusivity constants table."""
        method = self.comboBoxDiffusionMethod.currentText()
        if not method.startswith('Garnet'):
            QMessageBox.information(self.ui, 'Not implemented',
                f"{method} is not yet implemented; only Garnet is currently supported.")
            self.comboBoxDiffusionMethod.setCurrentText('Garnet')
            return
        self._populate_diffusivity_table('Garnet')

    def _populate_diffusivity_table(self, mineral):
        df = load_diffusivity_params(mineral)
        self.tableWidgetDiffusionConstants.setRowCount(len(df))
        for row, rec in df.iterrows():
            element_item = QTableWidgetItem(str(rec['element']))
            element_item.setFlags(element_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tableWidgetDiffusionConstants.setItem(row, 0, element_item)
            self.tableWidgetDiffusionConstants.setItem(row, 1, QTableWidgetItem(str(rec['D0_m2_s'])))
            self.tableWidgetDiffusionConstants.setItem(row, 2, QTableWidgetItem(str(rec['Ea_kJ_mol'])))

    def _read_diffusivity_table(self):
        """Reads the (possibly user-edited) constants table into ``{element: value}`` dicts.

        Returns
        -------
        D0_dict : dict
            ``{element: D0}``, m^2/s.
        Ea_dict : dict
            ``{element: Ea}``, J/mol (converted from the table's kJ/mol).
        """
        D0_dict, Ea_dict = {}, {}
        for row in range(self.tableWidgetDiffusionConstants.rowCount()):
            element = self.tableWidgetDiffusionConstants.item(row, 0).text()
            D0_dict[element] = float(self.tableWidgetDiffusionConstants.item(row, 1).text())
            Ea_dict[element] = float(self.tableWidgetDiffusionConstants.item(row, 2).text()) * 1000.0
        return D0_dict, Ea_dict

    def refresh_regions(self):
        """Rebuilds ``comboBoxRegion`` from the current mask's connected blobs."""
        data = self.data
        if data is None:
            QMessageBox.warning(self.ui, 'Warning', 'No sample loaded.')
            return

        regions = data.grain_regions()
        self._region_masks = []
        self.comboBoxRegion.clear()
        for blob_id in sorted(regions):
            info = regions[blob_id]
            self._region_masks.append(info['mask'])
            self.comboBoxRegion.addItem(f"Grain {blob_id} ({info['size']} px, {info['pct_of_map']:.1f}% of map)")

        if hasattr(self.ui, 'profile_dock'):
            self.comboBoxDiffusionProfile.clear()
            profiles = self.ui.profile_dock.profiling.profiles.get(self.app_data.sample_id, {})
            self.comboBoxDiffusionProfile.addItems(list(profiles))

    def _gather_common_inputs(self):
        """Reads widget values into the plain arguments ``diffusion``'s functions need.

        Returns
        -------
        dict or None
            ``None`` (after showing a warning) if anything required is
            missing/invalid.
        """
        data = self.data
        if data is None:
            QMessageBox.warning(self.ui, 'Warning', 'No sample loaded.')
            return None

        region_idx = self.comboBoxRegion.currentIndex()
        if region_idx < 0 or region_idx >= len(self._region_masks):
            QMessageBox.warning(self.ui, 'Warning', 'No region selected -- click "Refresh regions" first.')
            return None
        blob_mask = self._region_masks[region_idx]

        method = self.comboBoxDiffusionMethod.currentText()
        if not method.startswith('Garnet'):
            QMessageBox.information(self.ui, 'Not implemented',
                f"{method} is not yet implemented; only Garnet is currently supported.")
            return None

        observed_X = {}
        for element, field_box, type_box in zip(GARNET_ELEMENTS, self.comboBoxElementField, self.comboBoxElementFieldType):
            field = field_box.currentText()
            field_type = type_box.currentText()
            if not field:
                QMessageBox.warning(self.ui, 'Warning', f'{element} field is not selected.')
                return None
            arr = data.get_map_data(field, field_type)['array'].values
            observed_X[element] = arr.reshape(data.array_size, order=data.order)

        mask_2d = blob_mask.reshape(data.array_size, order=data.order)

        D0_dict, Ea_dict = self._read_diffusivity_table()
        missing = [e for e in GARNET_ELEMENTS + [GARNET_DEPENDENT] if e not in D0_dict or e not in Ea_dict]
        if missing:
            QMessageBox.warning(self.ui, 'Warning', f"Diffusivity constants missing for: {', '.join(missing)}.")
            return None

        temperature_C = self.lineEditDiffusionTemperature.value
        if temperature_C is None:
            QMessageBox.warning(self.ui, 'Warning', 'Enter a temperature.')
            return None
        T_K = temperature_C + 273.15

        # pixel spacing is stored in micrometers throughout the app -- convert to meters
        dx = data.dx * 1e-6
        dy = data.dy * 1e-6

        initial_X = {e: initial_core_composition(observed_X[e], mask_2d) for e in GARNET_ELEMENTS}

        return {
            'data': data, 'blob_mask': blob_mask, 'mask_2d': mask_2d, 'dx': dx, 'dy': dy,
            'T_K': T_K, 'D0_dict': D0_dict, 'Ea_dict': Ea_dict, 'initial_X': initial_X,
            'boundary_X': observed_X, 'observed_X': observed_X,
            'region_label': self.comboBoxRegion.currentText(),
        }

    def _write_results_to_sample(self, data, blob_mask, modeled, residual_maps):
        """Writes modeled/residual maps back as ``'Diffusion model'`` columns.

        One (modeled, residual) column pair per element, following the same
        multi-column ``add_columns`` call used for PCA scores
        (``DataAnalysis.py``) -- masked-out pixels are filled with NaN.
        """
        order = data.order
        column_names = []
        arrays = []
        for e in GARNET_ELEMENTS:
            column_names.append(f'{e} (diffusion model)')
            arrays.append(modeled[e].reshape(-1, order=order)[blob_mask])
            column_names.append(f'{e} (diffusion residual)')
            arrays.append(residual_maps[e].reshape(-1, order=order)[blob_mask])
        array_2d = np.column_stack(arrays)
        data.add_columns('Diffusion model', column_names, array_2d, mask=blob_mask)

    def run_forward_model(self):
        """Runs the forward model once at the given duration and temperature."""
        inputs = self._gather_common_inputs()
        if inputs is None:
            return

        duration_ka = self.lineEditDiffusionDuration.value
        if duration_ka is None:
            QMessageBox.warning(self.ui, 'Warning', 'Enter a duration.')
            return
        duration_s = duration_ka * 1000.0 * _SECONDS_PER_YEAR

        modeled = garnet_forward_model(
            duration_s=duration_s, T_K=inputs['T_K'], D0_dict=inputs['D0_dict'], Ea_dict=inputs['Ea_dict'],
            mask_2d=inputs['mask_2d'], dx=inputs['dx'], dy=inputs['dy'],
            initial_X=inputs['initial_X'], boundary_X=inputs['boundary_X'],
        )
        residual_maps = {e: misfit_map(inputs['observed_X'][e], modeled[e], inputs['mask_2d']) for e in GARNET_ELEMENTS}
        self._write_results_to_sample(inputs['data'], inputs['blob_mask'], modeled, residual_maps)

        rms_misfit = float(np.sqrt(np.nanmean(np.concatenate(
            [residual_maps[e][inputs['mask_2d']]**2 for e in GARNET_ELEMENTS]))))

        self._last_results = {
            'mineral': 'Garnet',
            'region_label': inputs['region_label'],
            'n_pixels': int(inputs['blob_mask'].sum()),
            'pct_of_map': 100 * inputs['blob_mask'].sum() / len(inputs['blob_mask']),
            'T_K': inputs['T_K'],
            'duration_s': duration_s,
            'duration_std_s': None,
            'rms_misfit': rms_misfit,
            'D0_dict': inputs['D0_dict'],
            'Ea_dict': inputs['Ea_dict'],
        }
        self._update_results_text()

    def fit_tt(self):
        """Fits duration (fixed temperature) to the observed zoning."""
        inputs = self._gather_common_inputs()
        if inputs is None:
            return

        duration0_ka = self.lineEditDiffusionDuration.value
        if duration0_ka is None:
            QMessageBox.warning(self.ui, 'Warning', 'Enter an initial duration guess.')
            return
        duration0_s = duration0_ka * 1000.0 * _SECONDS_PER_YEAR

        fit_result = fit_tt_isothermal(
            observed_X=inputs['observed_X'], mask_2d=inputs['mask_2d'], dx=inputs['dx'], dy=inputs['dy'],
            T_K=inputs['T_K'], D0_dict=inputs['D0_dict'], Ea_dict=inputs['Ea_dict'],
            initial_X=inputs['initial_X'], boundary_X=inputs['boundary_X'], duration0_s=duration0_s,
        )
        self._write_results_to_sample(inputs['data'], inputs['blob_mask'], fit_result['modeled'], fit_result['residual'])

        self._last_results = {
            'mineral': 'Garnet',
            'region_label': inputs['region_label'],
            'n_pixels': int(inputs['blob_mask'].sum()),
            'pct_of_map': 100 * inputs['blob_mask'].sum() / len(inputs['blob_mask']),
            'T_K': inputs['T_K'],
            'duration_s': fit_result['duration_s'],
            'duration_std_s': fit_result['duration_std_s'],
            'rms_misfit': fit_result['rms_misfit'],
            'D0_dict': inputs['D0_dict'],
            'Ea_dict': inputs['Ea_dict'],
        }
        if not fit_result['success']:
            self._last_results['fit_message'] = fit_result['message']
        self._update_results_text()

    def _update_results_text(self):
        r = self._last_results
        if not r:
            return

        duration_ka = r['duration_s'] / (1000.0 * _SECONDS_PER_YEAR)
        duration_line = f"Duration: {duration_ka:.4g} ka"
        if r.get('duration_std_s'):
            duration_line += f" ± {r['duration_std_s'] / (1000.0 * _SECONDS_PER_YEAR):.4g} ka"

        lines = [
            f"Mineral: {r['mineral']}",
            f"Region: {r['region_label']} ({r['n_pixels']} px, {r['pct_of_map']:.1f}% of map)",
            f"Temperature: {r['T_K'] - 273.15:.0f} °C",
            duration_line,
            f"RMS misfit: {r['rms_misfit']:.4g}",
            "",
            "Note: boundary pixels are fixed to their observed value and always "
            "show ~0 residual -- this is expected, not a diagnostic of fit quality.",
        ]
        if r.get('fit_message'):
            lines.insert(0, f"Fit did not fully converge: {r['fit_message']}")

        self.textEditDiffusionResults.setPlainText('\n'.join(lines))
