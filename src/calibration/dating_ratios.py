"""Cross-element parent/daughter isotope-ratio calibration for radiometric
dating systems (Pb-Pb's ratios are same-element and already handled by
``massbias.py`` directly; this module is for genuinely cross-element
pairs -- U-Pb (206Pb/238U, 207Pb/235U) and Th-Pb (208Pb/232Th) this pass.
Rb-Sr, Sm-Nd, Lu-Hf, Re-Os are deferred to a follow-up: they need
isobaric-interference stripping this pass deliberately doesn't build).

Distinct from ``massbias.py``'s same-element exponential mass-bias law (an
exponential function of ISOTOPE MASS RATIO, physically generalizable to
any other pair of the SAME element via ``bias_correction_factor``'s
mass-ratio-exponent rescaling): a parent/daughter ratio across two
DIFFERENT elements has no such generalization -- instrumental
fractionation between different elements depends on each element's own
ionization/transmission behavior, not just isotope mass. So there is no
valid "rescale one fitted curve to a different pair" trick here, and this
module is deliberately NOT a generalization of ``massbias.py``'s
``BiasSpec``/``BiasFit`` (avoiding regression risk to that already-tested
code, and avoiding a class shape that could invite a physically invalid
cross-element rescaling call). Each named cross-element ratio is instead
corrected independently via plain SESSION-LEVEL STANDARD BRACKETING of its
own raw measured ratio (reusing ``drift.py``'s fitting infrastructure the
same way ``massbias.py`` does) -- NOT down-hole fractionation curve-fitting
(how e.g. Iolite's U-Pb DRS script does it); down-hole fractionation for
ratios is an explicit non-goal of this project, consistent with every
other correction here operating at the session level, not per-ablation.

``DatingRatioSpec.numerator_scale_factor`` (default 1.0) supports the one
genuine "mass shift" case in this pass: 235U is never measured -- 207Pb/
235U is instead computed as ``k * (207Pb/238U)`` where ``k`` is the fixed,
natural 238U/235U abundance ratio (~137.818, from
``massbias.natural_abundance_ratio`` -- reused directly, not
reimplemented), avoiding ever needing a synthetic "U235" channel. This
mirrors the U-Pb DRS convention (Hiess et al. 2012 / IUPAC k=137.818)
exactly.

No PyQt imports -- matches background.py/standards.py/massbias.py's
headless convention.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.calibration.drift import DriftFitError, DriftFitLike, fit_polynomial_with_order_fallback, select_order_by_aic
from src.calibration.reflib import ReferenceMaterial
from src.calibration.standards import StandardCalibrationResult

_VALID_METHODS = {"fixed", "auto_aic"}


@dataclass
class DatingRatioTruth:
    """The certified truth value for one cross-element dating ratio.

    Attributes
    ----------
    value : float
        Certified parent/daughter (or daughter/daughter) ratio.
    uncertainty_1sd : float or None
        One-sigma uncertainty on ``value``, or ``None`` if the reference
        material does not report one.
    source : str
        Provenance tag. Always ``"certified_reference_ratio"`` -- there is
        no natural-abundance fallback for cross-element ratios.
    """

    value: float
    uncertainty_1sd: float | None
    source: str = "certified_reference_ratio"


def resolve_dating_ratio_truth(
    reference: ReferenceMaterial, numerator_element: str, numerator_mass: int,
    denominator_element: str, denominator_mass: int,
) -> DatingRatioTruth | None:
    """Look up the certified truth ratio for a cross-element dating pair.

    Parameters
    ----------
    reference : ReferenceMaterial
        The reference material carrying certified isotope-ratio values.
    numerator_element : str
        Element symbol of the ratio numerator, e.g. ``"Pb"``.
    numerator_mass : int
        Isotope mass of the ratio numerator, e.g. ``206``.
    denominator_element : str
        Element symbol of the ratio denominator, e.g. ``"U"``.
    denominator_mass : int
        Isotope mass of the ratio denominator, e.g. ``238``.

    Returns
    -------
    DatingRatioTruth or None
        The certified value and its uncertainty, or ``None`` if the
        reference material has no certified value for this exact pair.

    Notes
    -----
    Unlike ``massbias.resolve_truth_ratio`` there is no natural-abundance
    fallback: no fixed natural ratio relates two different elements'
    concentrations.
    """
    entry = reference.ratio(f"{numerator_element}{numerator_mass}", f"{denominator_element}{denominator_mass}")
    if entry is None or entry.value is None:
        return None
    return DatingRatioTruth(value=entry.value, uncertainty_1sd=entry.uncertainty_1sd())


@dataclass
class DatingRatioFit:
    """A fitted session-level drift curve for one cross-element dating ratio.

    Attributes
    ----------
    numerator_element, denominator_element : str
        Element symbols of the ratio numerator and denominator.
    numerator_mass, denominator_mass : int
        Isotope masses of the ratio numerator and denominator.
    numerator_scale_factor : float
        Fixed multiplier applied to the measured numerator (e.g. the
        238U/235U abundance ratio when 235U is never measured).
    truth : DatingRatioTruth
        Representative certified truth for reporting; the contributing
        standard with the most kept points, ties broken alphabetically.
    log_ratio_fit : DriftFitLike
        Polynomial fit of ``log(measured_ratio / truth)`` versus time.
    standard_labels : list[str]
        Standard labels that contributed points, sorted.
    n_points : int
        Total number of standard-occurrence points in the fit.
    """

    numerator_element: str
    numerator_mass: int
    denominator_element: str
    denominator_mass: int
    numerator_scale_factor: float
    truth: DatingRatioTruth
    log_ratio_fit: DriftFitLike
    standard_labels: list[str]
    n_points: int

    def correction_factor(self, times) -> np.ndarray:
        """Multiplicative drift correction factor at the given times.

        Parameters
        ----------
        times : array_like
            Acquisition times (datetimes or numeric) at which to evaluate
            the fitted curve.

        Returns
        -------
        numpy.ndarray
            ``exp(log_ratio_fit.predict(times))`` -- divide a measured
            ratio by this to remove session drift.
        """
        return np.exp(np.asarray(self.log_ratio_fit.predict(times), dtype=float))


@dataclass
class DatingRatioSpec:
    """Request to calibrate one named cross-element dating ratio.

    Attributes
    ----------
    numerator_element, denominator_element : str
        Element symbols of the ratio numerator and denominator.
    numerator_mass, denominator_mass : int
        Isotope masses of the ratio numerator and denominator.
    numerator_scale_factor : float, optional
        Fixed multiplier for the measured numerator, by default ``1.0``.
        Used for the "mass shift" case where 235U is computed as
        ``k * (207Pb/238U)`` with ``k`` the natural 238U/235U ratio.
    dating_standards : list[str] or None, optional
        Standard labels to fit from. ``None`` (default) uses every standard
        label with usable occurrences and a resolvable truth.
    """

    numerator_element: str
    numerator_mass: int
    denominator_element: str
    denominator_mass: int
    numerator_scale_factor: float = 1.0
    dating_standards: list[str] | None = None  # None -> every standard label with usable occurrences + a resolvable truth


def fit_dating_ratio(
    standard_results: dict[str, StandardCalibrationResult], labels: list[str], spec: DatingRatioSpec,
    order: int = 1, method: str = "fixed", max_order: int = 3,
) -> DatingRatioFit | None:
    """Fit one time-varying calibration curve for a cross-element dating ratio.

    Parameters
    ----------
    standard_results : dict[str, StandardCalibrationResult]
        Per-standard calibration results, keyed by standard label.
    labels : list[str]
        Standard labels to draw occurrences from.
    spec : DatingRatioSpec
        Which ratio to fit and its numerator scale factor.
    order : int, optional
        Polynomial order for ``method="fixed"``, by default ``1``.
    method : {"fixed", "auto_aic"}, optional
        ``"fixed"`` uses ``order`` (with order fallback); ``"auto_aic"``
        selects the order by AIC up to ``max_order``. By default
        ``"fixed"``.
    max_order : int, optional
        Highest polynomial order considered when ``method="auto_aic"``, by
        default ``3``.

    Returns
    -------
    DatingRatioFit or None
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
    truth)`` versus time, with ``measured_ratio = spec.numerator_scale_factor
    * mean_signal[numerator] / mean_signal[denominator]``. Occurrences from
    different standards (each with their own truth) are pooled into one fit,
    matching ``massbias.fit_bias_curve``'s pooling convention, and
    ``StandardOccurrence.mean_signal`` (already background-corrected and
    row-outlier-screened) is reused rather than recomputing from raw rows.
    """
    if method not in _VALID_METHODS:
        raise ValueError(f"dating-ratio fitting only supports {sorted(_VALID_METHODS)}, got {method!r}.")

    numerator = f"{spec.numerator_element}{spec.numerator_mass}"
    denominator = f"{spec.denominator_element}{spec.denominator_mass}"
    analyte_label = f"{numerator}/{denominator}_dating"

    times: list = []
    log_ratios: list[float] = []
    truth_by_label: dict[str, DatingRatioTruth] = {}
    points_by_label: dict[str, int] = {}
    for label in labels:
        sr = standard_results.get(label)
        if sr is None:
            continue
        truth = resolve_dating_ratio_truth(
            sr.reference, spec.numerator_element, spec.numerator_mass, spec.denominator_element, spec.denominator_mass,
        )
        if truth is None:
            continue
        for occ in sr.occurrences:
            num_cps = occ.mean_signal.get(numerator)
            den_cps = occ.mean_signal.get(denominator)
            if num_cps is None or den_cps is None or den_cps == 0:
                continue
            measured = spec.numerator_scale_factor * num_cps / den_cps
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
    # massbias.fit_bias_curve's own tie-break.
    contributing = sorted(points_by_label)
    best_label = max(contributing, key=lambda l: (points_by_label[l], l))
    return DatingRatioFit(
        numerator_element=spec.numerator_element, numerator_mass=spec.numerator_mass,
        denominator_element=spec.denominator_element, denominator_mass=spec.denominator_mass,
        numerator_scale_factor=spec.numerator_scale_factor,
        truth=truth_by_label[best_label], log_ratio_fit=fit,
        standard_labels=contributing, n_points=len(times),
    )


def corrected_dating_ratio(signal: pd.DataFrame, absolute_time, fit: DatingRatioFit) -> np.ndarray:
    """Apply a fitted drift curve to a sample's own measured dating ratio.

    Parameters
    ----------
    signal : pandas.DataFrame
        The sample's signal, containing the numerator and denominator
        analyte columns named by ``fit``.
    absolute_time : array_like
        Per-row acquisition times aligned with ``signal``.
    fit : DatingRatioFit
        The session-level drift curve for this ratio.

    Returns
    -------
    numpy.ndarray
        The sample's drift-corrected parent/daughter (or daughter/daughter)
        ratio, one value per row. The standard's ratio is not imposed on the
        sample -- whatever radiogenic signal is present is preserved, the
        same guarantee ``massbias.corrected_ratio`` makes for same-element
        pairs.
    """
    numerator = f"{fit.numerator_element}{fit.numerator_mass}"
    denominator = f"{fit.denominator_element}{fit.denominator_mass}"
    measured = fit.numerator_scale_factor * signal[numerator].to_numpy(dtype=float) / signal[denominator].to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return measured / fit.correction_factor(absolute_time)


def fit_session_dating_ratios(
    standard_results: dict[str, StandardCalibrationResult], specs: list[DatingRatioSpec],
    method: str = "fixed", order: int = 1, max_order: int = 3,
) -> dict[str, DatingRatioFit]:
    """Fit every requested cross-element dating ratio for a session.

    Parameters
    ----------
    standard_results : dict[str, StandardCalibrationResult]
        Per-standard calibration results, keyed by standard label.
    specs : list[DatingRatioSpec]
        One entry per dating ratio to fit.
    method : {"fixed", "auto_aic"}, optional
        Order-selection method passed to :func:`fit_dating_ratio`, by
        default ``"fixed"``.
    order : int, optional
        Polynomial order for ``method="fixed"``, by default ``1``.
    max_order : int, optional
        Highest order considered for ``method="auto_aic"``, by default
        ``3``.

    Returns
    -------
    dict[str, DatingRatioFit]
        One fit per spec that resolved to usable data, keyed
        ``"{numerator_element}{numerator_mass}/{denominator_element}{denominator_mass}"``.
        Specs with no usable data are omitted rather than raising.
    """
    fits: dict[str, DatingRatioFit] = {}
    for spec in specs:
        labels = spec.dating_standards if spec.dating_standards is not None else sorted(standard_results)
        fit = fit_dating_ratio(standard_results, labels, spec, order=order, method=method, max_order=max_order)
        if fit is not None:
            key = f"{spec.numerator_element}{spec.numerator_mass}/{spec.denominator_element}{spec.denominator_mass}"
            fits[key] = fit
    return fits
