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
    path = Path(path)
    if not path.exists():
        return None
    return pd.read_csv(path)


def natural_abundance_ratio(
    element: str, numerator_mass: int, denominator_mass: int,
    isotope_table: pd.DataFrame | str | Path | None = DEFAULT_ISOTOPE_TABLE_PATH,
) -> float | None:
    """Natural terrestrial abundance ratio of two isotopes of the SAME
    element (e.g. ``natural_abundance_ratio("U", 238, 235)`` -> ~137.8,
    from ``resources/app_data/isotope_info.csv``'s ``abundance_nominal``
    column).

    Only meaningful for isotope pairs that are physically invariant in
    nature -- a radiogenic daughter pair's true ratio is exactly what
    varies sample-to-sample, so this must never be used as a calibration
    truth for one; see :func:`resolve_truth_ratio`'s certified-value-first
    resolution order, which is what actually enforces that distinction
    (this function itself has no way to know which pairs are radiogenic --
    it just does the abundance-ratio arithmetic).
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
    """The most naturally abundant of ``candidate_masses`` for ``element``
    (from ``isotope_table``'s ``abundance_nominal`` column) -- a reasonable
    default isotope-ratio denominator/normalizer when no certified
    reference-material ratio is available to pick one (see the GUI's
    isotope-calibration table: certified-ratio denominators take priority,
    this is only the fallback). Returns ``None`` if the table is
    unavailable or none of ``candidate_masses`` resolve.
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
    value: float
    uncertainty_1sd: float | None
    source: str  # "certified_reference_ratio" | "natural_abundance"


def resolve_truth_ratio(
    reference: ReferenceMaterial, element: str, numerator_mass: int, denominator_mass: int,
    isotope_table: pd.DataFrame | str | Path | None = DEFAULT_ISOTOPE_TABLE_PATH,
) -> BiasTruth | None:
    """The calibration "truth" for isotope pair ``element{numerator_mass}/
    element{denominator_mass}`` in ``reference`` -- a certified reference-
    material ratio first, natural abundance second.

    This is a deliberate INVERSION of KJ.jl's own order (natural-abundance
    first, certified-anchor fallback only for pairs its own curated
    "known invariant" table excludes) -- rather than separately
    maintaining such a table (an auto-detected "is this pair radiogenic"
    classification this project has deliberately chosen not to build), a
    certified ratio's mere presence in a reference material's YAML already
    encodes "this pair needed special handling": it was deliberately added
    for Pb/Sr/Nd/Hf (see ``scripts/build_reference_library_from_georem.py``),
    never added for pairs where natural abundance already suffices (e.g.
    U238/U235). Natural abundance is the fallback only when no certified
    entry exists for that exact standard/pair.

    Returns ``None`` if neither source has data for this pair.
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
    element: str
    numerator_mass: int          # the pair actually fit, e.g. 206 for Pb206/Pb204
    denominator_mass: int        # e.g. 204
    truth: BiasTruth              # representative truth (see fit_bias_curve's tie-break when multiple standards contribute)
    log_bias_fit: DriftFitLike
    standard_labels: list[str]
    n_points: int

    def correction_factor(self, times) -> np.ndarray:
        return np.exp(np.asarray(self.log_bias_fit.predict(times), dtype=float))


def bias_correction_factor(fit: BiasFit, times, numerator_mass: int, denominator_mass: int) -> np.ndarray:
    """Generalizes ONE fitted bias curve to any OTHER isotope pair of the
    SAME element without refitting -- KJ.jl's mass-ratio-exponent
    rescaling (``bias.jl``): fractionation-per-unit-mass-difference is
    assumed constant, so a curve fit on one pair predicts any other pair
    of the same element by rescaling its exponent to that pair's own mass
    ratio. Passing ``fit``'s own ``(numerator_mass, denominator_mass)``
    gives ``beta == 1`` (no rescaling), i.e. the fitted curve itself.
    """
    beta = np.log(numerator_mass / denominator_mass) / np.log(fit.numerator_mass / fit.denominator_mass)
    return fit.correction_factor(times) ** beta


def fit_bias_curve(
    standard_results: dict[str, StandardCalibrationResult], labels: list[str],
    element: str, numerator_mass: int, denominator_mass: int,
    isotope_table: pd.DataFrame | str | Path | None = DEFAULT_ISOTOPE_TABLE_PATH,
    order: int = 1, method: str = "fixed", max_order: int = 3,
) -> BiasFit | None:
    """Fits a single time-varying mass-bias curve for isotope pair
    ``element{numerator_mass}/element{denominator_mass}`` from every
    occurrence of every label in ``labels`` that has both channels and a
    resolvable truth ratio (see :func:`resolve_truth_ratio`).

    Each occurrence's point is ``log(measured_ratio / that label's own
    truth)`` vs. time -- occurrences from different standards (each with
    their own truth) are pooled into one fit this way, matching how a
    session's bracketing standards are pooled elsewhere in this codebase.
    Reuses ``StandardOccurrence.mean_signal`` (already background-
    corrected, already row-outlier-screened -- the exact signal
    ``calibrate_standard`` itself drift-fits) rather than recomputing
    anything from raw per-row data.

    ``method="auto_poisson_lrt"`` is invalid here (raises) -- a log-ratio
    of two CPS channels isn't a Poisson count, unlike the raw signal
    ``standards.py``/``background.py`` fit that method against.

    Returns ``None`` (not a crash) when fewer than 2 usable points exist
    or the underlying fit fails.
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
    """The SAMPLE's own mass-bias-corrected TRUE ratio -- removes
    instrumental fractionation (via ``fit``), does NOT impose the
    standard's ratio on the sample. That's the whole point: it preserves
    whatever radiogenic signal is actually present in the sample.

    ``numerator_mass``/``denominator_mass`` need not match ``fit``'s own
    pair -- any isotope pair of ``fit.element`` can be corrected from one
    fitted curve (see :func:`bias_correction_factor`); the caller is
    responsible for ensuring ``signal`` actually has both requested
    channels for ``fit.element``.
    """
    numerator, denominator = f"{fit.element}{numerator_mass}", f"{fit.element}{denominator_mass}"
    measured = signal[numerator].to_numpy(dtype=float) / signal[denominator].to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return measured / bias_correction_factor(fit, absolute_time, numerator_mass, denominator_mass)


@dataclass
class BiasSpec:
    element: str
    numerator_mass: int
    denominator_mass: int
    bias_standards: list[str] | None = None  # None -> every standard label with usable occurrences + a resolvable truth


def fit_session_bias(
    standard_results: dict[str, StandardCalibrationResult], bias_specs: list[BiasSpec],
    isotope_table: pd.DataFrame | str | Path | None = DEFAULT_ISOTOPE_TABLE_PATH,
    method: str = "fixed", order: int = 1, max_order: int = 3,
) -> dict[str, BiasFit]:
    """One :func:`fit_bias_curve` per ``bias_specs`` entry, keyed
    ``"{element}{numerator_mass}/{element}{denominator_mass}"``. A spec
    that resolves to no usable data (see ``fit_bias_curve``) is simply
    omitted from the result, not an error.
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
