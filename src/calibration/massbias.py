"""Mass-bias / instrumental-fractionation correction for radiogenic
isotope ratios.

Distinct from ``standards.py``'s concentration calibration: that module
corrects a single CPS channel against a reference material's elemental
(total-element) concentration -- natural-abundance-independent, since the
abundance fraction of whichever isotope is used cancels between sample
and standard (see ``reflib.resolve_elemental_value``'s docstring). This
module instead corrects a RATIO of two CPS channels of the SAME element
against a reference material's own truth ratio, because a radiogenic
isotope pair (Pb-206/207/208 relative to Pb-204, Sr-87/Sr-86, etc.) has
no single natural-abundance value at all -- its true ratio is exactly
what varies sample-to-sample from radiogenic ingrowth, which is the whole
point of measuring it.

The mass-bias law and the certified-value-first resolution order below
are modeled on two independently-investigated, credible reference
implementations (this session): KJ.jl's (Vermeesch) ``bias.jl``
(``get_bias_truth``: try a natural-abundance ratio only for pairs known
to be physically invariant, else require a certified reference-material
anchor -- the mass-ratio-exponent rescaling of one fitted bias curve to
every isotope pair of an element) and Iolite's DRS example scripts
(``referenceMaterialData(rm)[...]`` certified-value lookups, an
exponential-law mass-bias correction via standard bracketing).

No PyQt imports -- matches background.py/standards.py/drift.py's headless
convention.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.calibration.drift import DriftFitError, DriftFitLike, fit_polynomial_with_order_fallback, select_order_by_aic
from src.calibration.reflib import ReferenceMaterial
from src.calibration.standards import StandardCalibrationResult

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ISOTOPE_TABLE_PATH = PROJECT_ROOT / "resources" / "app_data" / "isotope_info.csv"

_VALID_METHODS = {"fixed", "auto_aic"}


def load_isotope_table(path: str | Path) -> pd.DataFrame | None:
    """Load the isotope reference CSV.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the isotope table (``symbol``, ``atomic_mass``,
        ``abundance_nominal`` columns).

    Returns
    -------
    pandas.DataFrame or None
        The parsed table, or ``None`` if the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        return None
    return pd.read_csv(path)


def natural_abundance_ratio(
    element: str, numerator_mass: int, denominator_mass: int,
    isotope_table: pd.DataFrame | str | Path | None = DEFAULT_ISOTOPE_TABLE_PATH,
) -> float | None:
    """Natural terrestrial abundance ratio of two isotopes of the same element.

    Parameters
    ----------
    element : str
        Element symbol, e.g. ``"U"``.
    numerator_mass : int
        Isotope mass of the ratio numerator, e.g. ``238``.
    denominator_mass : int
        Isotope mass of the ratio denominator, e.g. ``235``.
    isotope_table : pandas.DataFrame or str or pathlib.Path or None, optional
        A loaded isotope table, or a path to one. Defaults to
        :data:`DEFAULT_ISOTOPE_TABLE_PATH`.

    Returns
    -------
    float or None
        ``abundance_nominal[numerator] / abundance_nominal[denominator]``
        (e.g. ~137.8 for U238/U235). ``None`` if the table is unavailable,
        either isotope is missing, or the denominator abundance is zero.

    Notes
    -----
    Only meaningful for isotope pairs that are physically invariant in
    nature. A radiogenic daughter pair's true ratio is exactly what varies
    sample-to-sample, so this must never be used as a calibration truth for
    one; :func:`resolve_truth_ratio`'s certified-value-first resolution
    order is what enforces that distinction -- this function itself has no
    way to know which pairs are radiogenic.
    """
    if isotope_table is None:
        return None
    table = isotope_table if isinstance(isotope_table, pd.DataFrame) else load_isotope_table(isotope_table)
    if table is None:
        return None
    num_rows = table[(table["symbol"] == element) & (table["atomic_mass"].astype(int) == numerator_mass)]
    den_rows = table[(table["symbol"] == element) & (table["atomic_mass"].astype(int) == denominator_mass)]
    if num_rows.empty or den_rows.empty:
        return None
    num_abundance = float(num_rows.iloc[0]["abundance_nominal"])
    den_abundance = float(den_rows.iloc[0]["abundance_nominal"])
    if den_abundance == 0:
        return None
    return num_abundance / den_abundance


def most_abundant_mass(
    element: str, candidate_masses: list[int],
    isotope_table: pd.DataFrame | str | Path | None = DEFAULT_ISOTOPE_TABLE_PATH,
) -> int | None:
    """Pick the most naturally abundant isotope from a candidate list.

    Parameters
    ----------
    element : str
        Element symbol, e.g. ``"Pb"``.
    candidate_masses : list[int]
        Isotope masses of ``element`` to choose among.
    isotope_table : pandas.DataFrame or str or pathlib.Path or None, optional
        A loaded isotope table, or a path to one. Defaults to
        :data:`DEFAULT_ISOTOPE_TABLE_PATH`.

    Returns
    -------
    int or None
        The candidate mass with the largest ``abundance_nominal``, or
        ``None`` if the table is unavailable or none of ``candidate_masses``
        resolve.

    Notes
    -----
    A reasonable default isotope-ratio denominator/normalizer when no
    certified reference-material ratio is available to pick one; certified
    denominators take priority in the GUI's isotope-calibration table, this
    is only the fallback.
    """
    if isotope_table is None:
        return None
    table = isotope_table if isinstance(isotope_table, pd.DataFrame) else load_isotope_table(isotope_table)
    if table is None:
        return None
    rows = table[(table["symbol"] == element) & (table["atomic_mass"].astype(int).isin(candidate_masses))]
    if rows.empty:
        return None
    return int(rows.loc[rows["abundance_nominal"].idxmax(), "atomic_mass"])


@dataclass
class BiasTruth:
    """The truth isotope ratio a mass-bias curve is fit against.

    Attributes
    ----------
    value : float
        The truth ratio.
    uncertainty_1sd : float or None
        One-sigma uncertainty on ``value``; ``None`` for a
        natural-abundance value.
    source : {"certified_reference_ratio", "natural_abundance"}
        Where ``value`` came from.
    """

    value: float
    uncertainty_1sd: float | None
    source: str  # "certified_reference_ratio" | "natural_abundance"


def resolve_truth_ratio(
    reference: ReferenceMaterial, element: str, numerator_mass: int, denominator_mass: int,
    isotope_table: pd.DataFrame | str | Path | None = DEFAULT_ISOTOPE_TABLE_PATH,
) -> BiasTruth | None:
    """Resolve the truth ratio for an isotope pair: certified first, natural second.

    Parameters
    ----------
    reference : ReferenceMaterial
        The reference material carrying certified isotope-ratio values.
    element : str
        Element symbol, e.g. ``"Pb"``.
    numerator_mass : int
        Isotope mass of the ratio numerator.
    denominator_mass : int
        Isotope mass of the ratio denominator.
    isotope_table : pandas.DataFrame or str or pathlib.Path or None, optional
        Isotope table (or path) for the natural-abundance fallback.
        Defaults to :data:`DEFAULT_ISOTOPE_TABLE_PATH`.

    Returns
    -------
    BiasTruth or None
        The certified reference ratio if present, else the natural
        terrestrial abundance ratio, else ``None``.

    Notes
    -----
    This is a deliberate inversion of KJ.jl's order (natural-abundance
    first, certified-anchor fallback only for pairs excluded by its curated
    "known invariant" table). Rather than maintaining such a table, a
    certified ratio's mere presence in a reference material's YAML already
    encodes "this pair needed special handling": it was deliberately added
    for Pb/Sr/Nd/Hf (see
    ``scripts/build_reference_library_from_georem.py``), never for pairs
    where natural abundance already suffices (e.g. U238/U235).
    """
    numerator, denominator = f"{element}{numerator_mass}", f"{element}{denominator_mass}"
    entry = reference.ratio(numerator, denominator)
    if entry is not None and entry.value is not None:
        return BiasTruth(value=entry.value, uncertainty_1sd=entry.uncertainty_1sd(), source="certified_reference_ratio")
    fallback = natural_abundance_ratio(element, numerator_mass, denominator_mass, isotope_table)
    if fallback is not None:
        return BiasTruth(value=fallback, uncertainty_1sd=None, source="natural_abundance")
    return None


@dataclass
class BiasFit:
    """A fitted session-level mass-bias curve for one isotope pair.

    Attributes
    ----------
    element : str
        Element symbol, e.g. ``"Pb"``.
    numerator_mass : int
        Numerator isotope mass of the pair actually fit, e.g. ``206``.
    denominator_mass : int
        Denominator isotope mass of the pair actually fit, e.g. ``204``.
    truth : BiasTruth
        Representative truth for reporting; the contributing standard with
        the most kept points, ties broken alphabetically.
    log_bias_fit : DriftFitLike
        Polynomial fit of ``log(measured_ratio / truth)`` versus time.
    standard_labels : list[str]
        Standard labels that contributed points, sorted.
    n_points : int
        Total number of standard-occurrence points in the fit.
    """

    element: str
    numerator_mass: int          # the pair actually fit, e.g. 206 for Pb206/Pb204
    denominator_mass: int        # e.g. 204
    truth: BiasTruth              # representative truth (see fit_bias_curve's tie-break when multiple standards contribute)
    log_bias_fit: DriftFitLike
    standard_labels: list[str]
    n_points: int

    def correction_factor(self, times) -> np.ndarray:
        """Multiplicative bias-correction factor for the fitted pair.

        Parameters
        ----------
        times : array_like
            Acquisition times at which to evaluate the fitted curve.

        Returns
        -------
        numpy.ndarray
            ``exp(log_bias_fit.predict(times))``. Divide a measured ratio
            of the fitted pair by this to remove instrumental
            fractionation.
        """
        return np.exp(np.asarray(self.log_bias_fit.predict(times), dtype=float))


def bias_correction_factor(fit: BiasFit, times, numerator_mass: int, denominator_mass: int) -> np.ndarray:
    """Rescale one fitted bias curve to another isotope pair of the same element.

    Parameters
    ----------
    fit : BiasFit
        A bias curve fitted on one pair of ``fit.element``.
    times : array_like
        Acquisition times at which to evaluate the correction.
    numerator_mass : int
        Numerator isotope mass of the target pair.
    denominator_mass : int
        Denominator isotope mass of the target pair.

    Returns
    -------
    numpy.ndarray
        ``fit.correction_factor(times) ** beta``, where ``beta`` rescales
        the exponent to the target pair's mass ratio. Passing ``fit``'s own
        pair gives ``beta == 1`` (the fitted curve itself).

    Notes
    -----
    KJ.jl's mass-ratio-exponent rescaling (``bias.jl``):
    fractionation-per-unit-mass-difference is assumed constant, so a curve
    fit on one pair predicts any other pair of the same element without
    refitting.
    """
    beta = np.log(numerator_mass / denominator_mass) / np.log(fit.numerator_mass / fit.denominator_mass)
    return fit.correction_factor(times) ** beta


def fit_bias_curve(
    standard_results: dict[str, StandardCalibrationResult], labels: list[str],
    element: str, numerator_mass: int, denominator_mass: int,
    isotope_table: pd.DataFrame | str | Path | None = DEFAULT_ISOTOPE_TABLE_PATH,
    order: int = 1, method: str = "fixed", max_order: int = 3,
) -> BiasFit | None:
    """Fit one time-varying mass-bias curve for an isotope pair.

    Parameters
    ----------
    standard_results : dict[str, StandardCalibrationResult]
        Per-standard calibration results, keyed by standard label.
    labels : list[str]
        Standard labels to draw occurrences from.
    element : str
        Element symbol, e.g. ``"Pb"``.
    numerator_mass : int
        Numerator isotope mass of the pair to fit.
    denominator_mass : int
        Denominator isotope mass of the pair to fit.
    isotope_table : pandas.DataFrame or str or pathlib.Path or None, optional
        Isotope table (or path) for the natural-abundance truth fallback.
        Defaults to :data:`DEFAULT_ISOTOPE_TABLE_PATH`.
    order : int, optional
        Polynomial order for ``method="fixed"``, by default ``1``.
    method : {"fixed", "auto_aic"}, optional
        Order-selection strategy, by default ``"fixed"``.
    max_order : int, optional
        Highest order considered when ``method="auto_aic"``, by default
        ``3``.

    Returns
    -------
    BiasFit or None
        The fitted curve, or ``None`` when fewer than 2 usable points exist
        or the underlying fit fails.

    Raises
    ------
    ValueError
        If ``method`` is not ``"fixed"`` or ``"auto_aic"`` (a log-ratio of
        two CPS channels is not a Poisson count, so ``"auto_poisson_lrt"``
        is invalid here).

    Notes
    -----
    Each occurrence's point is ``log(measured_ratio / that label's own
    truth)`` versus time. Occurrences from different standards (each with
    their own truth) are pooled into one fit, matching how a session's
    bracketing standards are pooled elsewhere. ``StandardOccurrence.mean_signal``
    (already background-corrected and row-outlier-screened -- the exact
    signal ``calibrate_standard`` drift-fits) is reused rather than
    recomputing from raw rows.
    """
    if method not in _VALID_METHODS:
        raise ValueError(f"massbias fitting only supports {sorted(_VALID_METHODS)}, got {method!r}.")

    numerator, denominator = f"{element}{numerator_mass}", f"{element}{denominator_mass}"
    analyte_label = f"{numerator}/{denominator}_bias"

    times: list = []
    log_ratios: list[float] = []
    truth_by_label: dict[str, BiasTruth] = {}
    points_by_label: dict[str, int] = {}
    for label in labels:
        sr = standard_results.get(label)
        if sr is None:
            continue
        truth = resolve_truth_ratio(sr.reference, element, numerator_mass, denominator_mass, isotope_table)
        if truth is None:
            continue
        for occ in sr.occurrences:
            num_cps = occ.mean_signal.get(numerator)
            den_cps = occ.mean_signal.get(denominator)
            if num_cps is None or den_cps is None or den_cps == 0:
                continue
            measured = num_cps / den_cps
            if measured <= 0:
                continue
            times.append(occ.file_meta.acquired_at)
            log_ratios.append(float(np.log(measured / truth.value)))
            truth_by_label[label] = truth
            points_by_label[label] = points_by_label.get(label, 0) + 1

    if len(times) < 2:
        return None

    if method == "fixed":
        fit = fit_polynomial_with_order_fallback(times, log_ratios, order=order, analyte=analyte_label)
    else:  # "auto_aic"
        try:
            fit = select_order_by_aic(times, log_ratios, max_order=max_order, analyte=analyte_label)
        except DriftFitError:
            fit = None
    if fit is None:
        return None

    # Representative truth for reporting, when multiple standards
    # contributed (each with its own truth value) -- the label with the
    # most kept points wins, ties broken alphabetically, matching
    # standards.combine_primary_standards's own drift-reference tie-break.
    contributing = sorted(points_by_label)
    best_label = max(contributing, key=lambda l: (points_by_label[l], l))
    return BiasFit(
        element=element, numerator_mass=numerator_mass, denominator_mass=denominator_mass,
        truth=truth_by_label[best_label], log_bias_fit=fit,
        standard_labels=contributing, n_points=len(times),
    )


def corrected_ratio(signal: pd.DataFrame, absolute_time, fit: BiasFit, numerator_mass: int, denominator_mass: int) -> np.ndarray:
    """Apply a fitted mass-bias curve to a sample's own measured ratio.

    Parameters
    ----------
    signal : pandas.DataFrame
        The sample's signal, containing ``f"{fit.element}{numerator_mass}"``
        and ``f"{fit.element}{denominator_mass}"`` columns.
    absolute_time : array_like
        Per-row acquisition times aligned with ``signal``.
    fit : BiasFit
        The session-level mass-bias curve.
    numerator_mass : int
        Numerator isotope mass of the pair to correct. Need not match
        ``fit``'s own pair.
    denominator_mass : int
        Denominator isotope mass of the pair to correct.

    Returns
    -------
    numpy.ndarray
        The sample's mass-bias-corrected ratio, one value per row.
        Instrumental fractionation is removed but the standard's ratio is
        not imposed -- whatever radiogenic signal is present is preserved.

    Notes
    -----
    Any isotope pair of ``fit.element`` can be corrected from one fitted
    curve (see :func:`bias_correction_factor`); the caller must ensure
    ``signal`` actually has both requested channels.
    """
    numerator, denominator = f"{fit.element}{numerator_mass}", f"{fit.element}{denominator_mass}"
    measured = signal[numerator].to_numpy(dtype=float) / signal[denominator].to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return measured / bias_correction_factor(fit, absolute_time, numerator_mass, denominator_mass)


@dataclass
class BiasSpec:
    """Request to fit one named mass-bias curve.

    Attributes
    ----------
    element : str
        Element symbol, e.g. ``"Pb"``.
    numerator_mass : int
        Numerator isotope mass of the pair to fit.
    denominator_mass : int
        Denominator isotope mass of the pair to fit.
    bias_standards : list[str] or None, optional
        Standard labels to fit from. ``None`` (default) uses every standard
        label with usable occurrences and a resolvable truth.
    """

    element: str
    numerator_mass: int
    denominator_mass: int
    bias_standards: list[str] | None = None  # None -> every standard label with usable occurrences + a resolvable truth


def fit_session_bias(
    standard_results: dict[str, StandardCalibrationResult], bias_specs: list[BiasSpec],
    isotope_table: pd.DataFrame | str | Path | None = DEFAULT_ISOTOPE_TABLE_PATH,
    method: str = "fixed", order: int = 1, max_order: int = 3,
) -> dict[str, BiasFit]:
    """Fit every requested mass-bias curve for a session.

    Parameters
    ----------
    standard_results : dict[str, StandardCalibrationResult]
        Per-standard calibration results, keyed by standard label.
    bias_specs : list[BiasSpec]
        One entry per mass-bias curve to fit.
    isotope_table : pandas.DataFrame or str or pathlib.Path or None, optional
        Isotope table (or path) for natural-abundance truth fallbacks.
        Defaults to :data:`DEFAULT_ISOTOPE_TABLE_PATH`.
    method : {"fixed", "auto_aic"}, optional
        Order-selection strategy passed to :func:`fit_bias_curve`, by
        default ``"fixed"``.
    order : int, optional
        Polynomial order for ``method="fixed"``, by default ``1``.
    max_order : int, optional
        Highest order considered for ``method="auto_aic"``, by default
        ``3``.

    Returns
    -------
    dict[str, BiasFit]
        One fit per spec that resolved to usable data, keyed
        ``"{element}{numerator_mass}/{element}{denominator_mass}"``. Specs
        with no usable data are omitted rather than raising.
    """
    fits: dict[str, BiasFit] = {}
    for spec in bias_specs:
        labels = spec.bias_standards if spec.bias_standards is not None else sorted(standard_results)
        fit = fit_bias_curve(
            standard_results, labels, spec.element, spec.numerator_mass, spec.denominator_mass,
            isotope_table=isotope_table, order=order, method=method, max_order=max_order,
        )
        if fit is not None:
            key = f"{spec.element}{spec.numerator_mass}/{spec.element}{spec.denominator_mass}"
            fits[key] = fit
    return fits
