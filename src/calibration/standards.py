"""Standard-signal drift fitting, calibration-factor computation, odd/even
holdout validation, and accuracy QC (z/t-test on combined uncertainty).

Operates on the occurrences of a single standard label at a time; multiple
standard types (e.g. a primary + secondary standard) are orchestrated by
``pipeline.py`` calling this module once per label.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from src.calibration.background import BackgroundResult, detect_row_outliers
from src.calibration.counts import TauEstimate, cps_to_counts
from src.calibration.drift import (
    DriftFit,
    DriftFitError,
    DriftFitLike,
    fit_polynomial,
    fit_polynomial_with_order_fallback,
    select_drift_fit,
    select_order_by_aic,
)
from src.calibration.poisson_drift import PoissonFitError
from src.calibration.rawfile import LineFileMeta
from src.calibration.reflib import ReferenceMaterial, resolve_elemental_value


@dataclass
class StandardOccurrence:
    file_meta: LineFileMeta
    background: BackgroundResult
    mean_signal: dict[str, float]
    sem_signal: dict[str, float]
    occurrence_order: int    # 1-based, in true acquisition-time order among this label's files


@dataclass
class AccuracyRow:
    analyte: str
    observed_value: float
    observed_se: float
    reference_value: float
    reference_uncertainty: float
    difference: float
    combined_uncertainty: float
    z_or_t_stat: float
    threshold_multiple: float
    flagged: bool
    group: str    # "fit" | "holdout" | "all"
    occurrence_order: int
    time: datetime    # the occurrence's acquired_at -- lets diagnostics plot reference-vs-time
    manually_excluded: bool = False  # user click/drag exclusion (see calibrate_standard's manual_occurrence_exclusions)


@dataclass
class StandardCalibrationResult:
    standard_label: str
    reference: ReferenceMaterial
    occurrences: list[StandardOccurrence]
    drift_fits: dict[str, DriftFitLike]
    calibration_factor: dict[str, float]        # analyte -> summary ppm-per-CPS multiplier (QC/reporting)
    accuracy_table: list[AccuracyRow]
    holdout_accuracy_table: list[AccuracyRow] | None
    split_enabled: bool
    skipped_analytes: list[str] = field(default_factory=list)  # no reference value or no stable drift fit
    excluded_outliers: dict[str, list[int]] = field(default_factory=dict)  # analyte -> excluded occurrence_order (automatic MAD screen)
    manually_excluded_occurrences: dict[str, list[int]] = field(default_factory=dict)  # analyte -> excluded occurrence_order (user click/drag)
    mean_predicted_signal: dict[str, float] = field(default_factory=dict)  # analyte -> mean(drift_fit.predict(kept_times)) -- multi-point calibration input
    detrend_fits: dict[str, DriftFitLike] = field(default_factory=dict)  # analyte -> linear fit of (observed-reference) vs time, see calibrate_standard's detrend


@dataclass
class CalibrationCurve:
    """One analyte's CPS->ppm calibration curve, fit across every PRIMARY
    standard's own (drift-fit mean predicted CPS, reference ppm) point --
    see :func:`combine_primary_standards`.

    With exactly one primary standard, this degenerates to today's
    single-point behavior: ``slope = reference_value / mean_predicted_cps``,
    ``intercept = 0`` (a line forced through the origin), ``r_squared =
    None`` (not a meaningful statistic for one point). With two or more,
    it's an ordinary-least-squares fit of ppm vs CPS -- with a free
    intercept (``method="multi_point_linear"``) by default, or forced
    through the origin (``method="multi_point_zero_intercept"``,
    ``intercept=0``) when ``force_zero_intercept`` is requested -- see
    :func:`combine_primary_standards`.
    """
    analyte: str
    slope: float
    intercept: float
    r_squared: float | None
    n_points: int
    method: str  # "single_point_ratio" | "multi_point_linear" | "multi_point_zero_intercept"
    points: list[tuple[str, float, float]]  # (standard_label, mean_predicted_cps, reference_ppm)


@dataclass
class MultiStandardCalibrationResult:
    """The combined output of :func:`combine_primary_standards` -- a
    sibling to (not a replacement for) each primary standard's own
    :class:`StandardCalibrationResult`, which every standard (primary or
    secondary) still gets independently for its own QC story (occurrences,
    drift fit, accuracy table). This only exists once 2+ primary standards
    are configured; with exactly one, callers use the existing
    ``calibrate_standard``/``apply_calibration`` path directly instead.
    """
    primary_labels: list[str]
    curves: dict[str, CalibrationCurve]
    drift_reference_by_analyte: dict[str, str]  # analyte -> which primary label's own drift fit time-normalizes samples
    skipped_analytes: list[str] = field(default_factory=list)  # no usable (CPS, ppm) point from any primary standard


def assemble_occurrences(
    backgrounds: list[BackgroundResult], row_outlier_order: int = 1, row_outlier_threshold: float = 5.0,
    manual_row_exclusions: dict[str, dict[str, set[int]]] | None = None,
) -> list[StandardOccurrence]:
    """Builds :class:`StandardOccurrence` entries from a standard label's
    background results, numbered by true acquisition-time order (not by
    filename index, which is only meaningful within one label).

    Statistics use the ablation window's *included* (edge-trimmed) region
    (``AblationWindow.included_start_idx``/``included_end_idx``), not
    necessarily the full ablation span -- see ``background.apply_edge_trim``.
    Untrimmed (the default) this is identical to the full span, so existing
    behavior is unchanged unless edge trim was explicitly applied.

    Within that included region, individual rows are further screened by
    :func:`~src.calibration.background.detect_row_outliers` -- a low-order
    (linear, by default) fit -- run separately **per analyte**, against
    that analyte's own signal, not a shared reference channel: an
    ablation-interval anomaly (e.g. hitting a micro-inclusion of a
    different mineral mid-line) can be compositionally specific to one
    trace element and invisible in the major elements a reference-channel
    mask would be based on (confirmed against real data for the analogous
    background-window case -- see ``compute_background_result``). This
    catches things like a short edge-effect ramp on a standard glass
    automatically, without a manually-tuned trim duration -- unlike the
    coarse, fixed-duration ``apply_edge_trim``, it can flag any subset of
    rows, not just a contiguous lead/trail span, and different analytes can
    have entirely different flagged rows. Only ever applied here (standard
    occurrences), never to sample maps -- a sample's natural signal
    heterogeneity must not be silently filtered. The resulting masks are
    attached to a copy of the occurrence's ``AblationWindow``
    (``row_outlier_mask``, keyed per analyte) so the time-series viewer can
    display them (see ``background.classify_rows``).

    ``manual_row_exclusions`` (filename -> analyte -> set of absolute row
    indices into that file's own signal, i.e. directly comparable to
    ``ablation.included_start_idx``) are user-specified exclusions from the
    Time Series viewer's click/drag masking -- unioned into each analyte's
    automatic ``mask`` before computing ``mean_signal``/``sem_signal``, the
    same way :func:`~src.calibration.background.compute_background_result`
    unions its own ``manual_row_exclusions`` into the background window's
    screen. Kept separate from the automatic screen so a user's choice
    survives being re-Run without silent second-guessing.
    """
    ordered = sorted(backgrounds, key=lambda b: b.file_meta.acquired_at)
    occurrences = []
    for i, b in enumerate(ordered, start=1):
        ablation = b.ablation
        lo = ablation.included_start_idx - ablation.start_idx
        hi = ablation.included_end_idx - ablation.start_idx
        included_signal = b.background_corrected_signal.iloc[lo:hi]
        manual_for_file = (manual_row_exclusions or {}).get(b.file_meta.path.name, {})

        row_outlier_mask: dict[str, np.ndarray] = {}
        clean_cols = {}
        for analyte in included_signal.columns:
            analyte_signal = included_signal[analyte].to_numpy()
            mask = detect_row_outliers(analyte_signal, order=row_outlier_order, threshold=row_outlier_threshold)
            clean = included_signal[analyte].loc[~mask]
            if clean.empty:
                # Degenerate case (every row flagged) -- don't trust the
                # screen for this analyte, fall back to the full,
                # unfiltered region rather than reporting statistics over
                # zero rows.
                mask = np.zeros(len(analyte_signal), dtype=bool)
                clean = included_signal[analyte]

            manual = manual_for_file.get(analyte, ())
            if manual:
                for abs_idx in manual:
                    if ablation.included_start_idx <= abs_idx < ablation.included_end_idx:
                        mask[abs_idx - ablation.included_start_idx] = True
                clean = included_signal[analyte].loc[~mask]

            row_outlier_mask[analyte] = mask
            clean_cols[analyte] = clean

        ablation = dataclasses.replace(ablation, row_outlier_mask=row_outlier_mask)
        b = dataclasses.replace(b, ablation=ablation)

        mean_signal = {analyte: float(s.mean()) if len(s) else float("nan") for analyte, s in clean_cols.items()}
        sem_signal = {analyte: float(s.sem()) if len(s) > 1 else 0.0 for analyte, s in clean_cols.items()}
        occurrences.append(
            StandardOccurrence(
                file_meta=b.file_meta, background=b, mean_signal=mean_signal,
                sem_signal=sem_signal, occurrence_order=i,
            )
        )
    return occurrences


def _mad_outlier_mask(values: list[float], threshold: float = 3.5) -> list[bool]:
    """Robust keep-mask via modified z-score (median absolute deviation).

    A standard occurrence can include a bad measurement (contamination, a
    mis-detected background window, an isolated spike) that would otherwise
    skew both the drift fit and the calibration factor derived from it.
    ``threshold=3.5`` is the conventional cutoff for this statistic (Iglewicz
    & Hoaglin). Requires at least 4 points to attempt rejection -- with
    fewer, there's not enough information to distinguish a real outlier from
    ordinary scatter, so nothing is excluded.
    """
    n = len(values)
    if n < 4:
        return [True] * n
    arr = np.asarray(values, dtype=float)
    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median)))
    if mad == 0:
        return [True] * n
    modified_z = 0.6745 * (arr - median) / mad
    return [bool(abs(z) <= threshold) for z in modified_z]


def _poisson_eligible(o: StandardOccurrence, analyte: str, background_fraction_threshold: float) -> bool:
    """True when this occurrence's background is negligible enough, relative
    to its raw ablation signal, that fitting the *raw* (uncorrected) rate is
    an adequate stand-in for the background-corrected rate this module
    otherwise fits -- see ``calibrate_standard``'s ``method`` docstring."""
    bg = o.background
    if bg.tau_provenance.get(analyte, "unknown") == "unknown":
        return False
    if analyte not in bg.ablation_signal.columns:
        return False
    ablation_level = float(bg.ablation_signal[analyte].mean())
    if ablation_level <= 0:
        return False
    background_level = bg.background_mean.get(analyte, 0.0)
    return background_level < background_fraction_threshold * ablation_level


def _poisson_inputs_for_analyte(
    occurrences: list[StandardOccurrence], analyte: str
) -> tuple[list[datetime], list[float], list[float]]:
    """(times, total_counts, total_tau_s) per occurrence, recovered from raw
    (pre-background-subtraction) ablation CPS -- the Poisson non-negative-
    integer-count assumption doesn't hold for the net/background-corrected
    signal, which can be negative."""
    times: list[datetime] = []
    counts_list: list[float] = []
    tau_list: list[float] = []
    for o in occurrences:
        bg = o.background
        tau_s = bg.background_tau_s.get(analyte)
        if tau_s is None:
            continue
        raw = bg.ablation_signal[analyte].to_numpy()
        tau_estimate = TauEstimate(tau_s=tau_s, provenance=bg.tau_provenance.get(analyte, "unknown"))
        counts_arr = cps_to_counts(raw, tau_estimate)
        if counts_arr is None:
            continue
        times.append(o.file_meta.acquired_at)
        counts_list.append(float(np.sum(counts_arr)))
        tau_list.append(tau_s * len(raw))
    return times, counts_list, tau_list


def calibrate_standard(
    occurrences: list[StandardOccurrence],
    reference: ReferenceMaterial,
    drift_order: int = 1,
    split_odd_even: bool = False,
    accuracy_threshold: float = 2.0,
    standard_label: str = "",
    method: str = "fixed",
    max_order: int = 3,
    poisson_background_fraction_threshold: float = 0.05,
    manual_occurrence_exclusions: dict[str, set[str]] | None = None,
    detrend: bool = False,
) -> StandardCalibrationResult:
    """Fits per-analyte drift, computes calibration factors, and builds the
    accuracy QC table(s).

    If ``split_odd_even``, odd ``occurrence_order`` entries are the fit group
    (drift fit + calibration factor derived from them) and even entries are
    held out and back-calculated through that fit for independent QC
    (``holdout_accuracy_table``). Otherwise every occurrence is in the fit
    group and ``holdout_accuracy_table`` is ``None``.

    Before fitting, each analyte's fit-group values are screened for
    outliers (see ``_mad_outlier_mask``) -- excluded occurrences are dropped
    from both the drift fit and the calibration-factor average for that
    analyte (see ``StandardCalibrationResult.excluded_outliers``), but still
    appear in ``accuracy_table`` so a badly-behaved occurrence remains
    visible in QC rather than silently vanishing.

    ``manual_occurrence_exclusions`` (filename -> set of analytes) drops a
    whole occurrence from one specific analyte's drift fit/calibration
    factor -- a user's click on the Standards QC viewer -- kept as a
    **separate** field (``StandardCalibrationResult.manually_excluded_occurrences``)
    from the automatic MAD screen's ``excluded_outliers``, so a manual
    choice is distinguishable and isn't silently re-included or
    second-guessed by the automatic screen on the next Run. Like automatic
    exclusions, manually-excluded occurrences still appear in
    ``accuracy_table``/``holdout_accuracy_table`` (``AccuracyRow.manually_excluded``),
    not silently dropped.

    ``method`` mirrors ``background.fit_session_background_drift``'s three
    options (``"fixed"`` / ``"auto_aic"`` / ``"auto_poisson_lrt"``), applied
    per analyte to this standard's own signal-drift fit:

    - ``"fixed"`` (default): the original behavior -- OLS at ``drift_order``,
      with automatic order reduction when there aren't enough points.
    - ``"auto_aic"``: :func:`~src.calibration.drift.select_order_by_aic` on
      the background-corrected ``mean_signal``.
    - ``"auto_poisson_lrt"``: fits a Poisson GLM on **raw** (pre-background-
      subtraction) ablation counts recovered via ``counts.cps_to_counts`` --
      feeding the net-of-background signal (which can be negative/fractional)
      into a Poisson GLM would violate its non-negative-integer-count
      assumption. Only used for an analyte when every kept fit-group
      occurrence has a negligible background relative to its raw ablation
      signal (``background_mean < poisson_background_fraction_threshold *
      ablation_mean``, default 5%) -- close enough that the raw rate's own
      drift trend is an adequate stand-in for the background-corrected
      rate's trend (the same order of approximation already accepted by
      calling the background "negligible" in the first place). Analytes
      failing that check, with unresolvable tau, or where the Poisson fit
      itself fails, fall back to ``"auto_aic"`` instead.

    ``detrend`` (default off): when a standard's own accuracy-vs-time still
    shows a residual linear trend after the drift fit above (a real,
    if less common, session-sensitivity-drift residual that a low-order
    drift fit didn't fully absorb), fits one additional simple linear model
    per analyte -- ``fit_polynomial(order=1)`` on ``(occurrence time,
    observed_value - reference_value)`` from the fit-group accuracy rows --
    and stores it (``StandardCalibrationResult.detrend_fits``) for
    ``apply_calibration``/``apply_multi_point_calibration`` to subtract
    from a sample's calibrated ppm at that sample's own time. Intentionally
    linear-only (not order-selected) -- a simple, deliberately limited
    post-hoc correction, not a second full drift-fitting pass. Needs at
    least 3 fit-group points for an analyte to attempt it; skipped
    (no entry in ``detrend_fits``) otherwise.
    """
    if not occurrences:
        raise ValueError("At least one standard occurrence is required to calibrate.")

    if split_odd_even:
        fit_group = [o for o in occurrences if o.occurrence_order % 2 == 1]
        holdout_group = [o for o in occurrences if o.occurrence_order % 2 == 0]
    else:
        fit_group = list(occurrences)
        holdout_group = []

    analytes = sorted({a for o in occurrences for a in o.mean_signal})
    fit_times = [o.file_meta.acquired_at for o in fit_group]

    # Outlier rejection happens once per analyte and is reused for both the
    # drift fit and the calibration-factor average below, so an excluded
    # occurrence is consistently absent from both statistics rather than
    # contaminating one but not the other.
    drift_fits: dict[str, DriftFitLike] = {}
    inlier_masks: dict[str, list[bool]] = {}
    excluded_outliers: dict[str, list[int]] = {}
    manually_excluded_occurrences: dict[str, list[int]] = {}
    for analyte in analytes:
        values = [o.mean_signal[analyte] for o in fit_group]
        keep_mask = _mad_outlier_mask(values)
        inlier_masks[analyte] = keep_mask
        excluded = [o.occurrence_order for o, keep in zip(fit_group, keep_mask) if not keep]
        if excluded:
            excluded_outliers[analyte] = excluded

        manual_excluded_orders = [
            o.occurrence_order for o in fit_group
            if analyte in (manual_occurrence_exclusions or {}).get(o.file_meta.path.name, set())
        ]
        if manual_excluded_orders:
            manually_excluded_occurrences[analyte] = manual_excluded_orders
            keep_mask = [
                keep and o.occurrence_order not in manual_excluded_orders
                for o, keep in zip(fit_group, keep_mask)
            ]
            inlier_masks[analyte] = keep_mask

        kept_occurrences = [o for o, keep in zip(fit_group, keep_mask) if keep]
        kept_times = [o.file_meta.acquired_at for o in kept_occurrences]
        kept_values = [o.mean_signal[analyte] for o in kept_occurrences]

        fit: DriftFitLike | None = None
        if method == "auto_poisson_lrt" and kept_occurrences and all(
            _poisson_eligible(o, analyte, poisson_background_fraction_threshold) for o in kept_occurrences
        ):
            p_times, p_counts, p_tau = _poisson_inputs_for_analyte(kept_occurrences, analyte)
            if len(p_times) >= 2:
                try:
                    fit = select_drift_fit(
                        p_times, None, counts=p_counts, tau_s=p_tau,
                        method="auto_poisson_lrt", max_order=max_order, analyte=analyte,
                    )
                except PoissonFitError:
                    fit = None

        if fit is None:
            if method in ("auto_poisson_lrt", "auto_aic"):
                try:
                    fit = select_order_by_aic(kept_times, kept_values, max_order=max_order, analyte=analyte)
                except DriftFitError:
                    fit = None
            else:  # "fixed"
                fit = fit_polynomial_with_order_fallback(kept_times, kept_values, drift_order, analyte)

        if fit is not None:
            drift_fits[analyte] = fit

    calibration_factor: dict[str, float] = {}
    mean_predicted_signal: dict[str, float] = {}
    skipped_analytes: list[str] = []
    for analyte in analytes:
        ref_entry = resolve_elemental_value(reference, analyte)
        ref_value = ref_entry.value if ref_entry else None
        fit = drift_fits.get(analyte)
        if ref_value is None or fit is None:
            skipped_analytes.append(analyte)
            continue
        keep_mask = inlier_masks.get(analyte, [True] * len(fit_group))
        kept_times = [t for t, keep in zip(fit_times, keep_mask) if keep]
        predicted = fit.predict(kept_times)
        mean_predicted = float(np.mean(predicted))
        if mean_predicted == 0:
            skipped_analytes.append(analyte)
            continue
        calibration_factor[analyte] = ref_value / mean_predicted
        mean_predicted_signal[analyte] = mean_predicted

    def _accuracy_rows(group_occurrences: list[StandardOccurrence], group_label: str) -> list[AccuracyRow]:
        rows = []
        for o in group_occurrences:
            for analyte in analytes:
                ref_entry = resolve_elemental_value(reference, analyte)
                ref_value = ref_entry.value if ref_entry else None
                fit = drift_fits.get(analyte)
                if ref_value is None or fit is None:
                    continue
                predicted_at_t = float(fit.predict([o.file_meta.acquired_at])[0])
                if predicted_at_t == 0:
                    continue
                scale = ref_value / predicted_at_t
                observed_value = o.mean_signal[analyte] * scale
                observed_se = o.sem_signal.get(analyte, 0.0) * abs(scale)
                ref_uncertainty = (ref_entry.uncertainty_1sd() or 0.0) if ref_entry else 0.0
                combined_unc = float(np.sqrt(observed_se ** 2 + ref_uncertainty ** 2))
                difference = observed_value - ref_value
                stat = difference / combined_unc if combined_unc > 0 else float("inf")
                manually_excluded = analyte in (manual_occurrence_exclusions or {}).get(o.file_meta.path.name, set())
                rows.append(AccuracyRow(
                    analyte=analyte, observed_value=observed_value, observed_se=observed_se,
                    reference_value=ref_value, reference_uncertainty=ref_uncertainty,
                    difference=difference, combined_uncertainty=combined_unc, z_or_t_stat=stat,
                    manually_excluded=manually_excluded,
                    threshold_multiple=accuracy_threshold, flagged=abs(stat) > accuracy_threshold,
                    group=group_label, occurrence_order=o.occurrence_order, time=o.file_meta.acquired_at,
                ))
        return rows

    accuracy_table = _accuracy_rows(fit_group, "fit" if split_odd_even else "all")
    holdout_accuracy_table = _accuracy_rows(holdout_group, "holdout") if split_odd_even else None

    detrend_fits: dict[str, DriftFitLike] = {}
    if detrend:
        for analyte in analytes:
            rows = [r for r in accuracy_table if r.analyte == analyte and not r.manually_excluded]
            if len(rows) < 3:
                continue
            try:
                detrend_fits[analyte] = fit_polynomial(
                    [r.time for r in rows], [r.difference for r in rows], order=1, analyte=analyte,
                )
            except DriftFitError:
                continue

    return StandardCalibrationResult(
        standard_label=standard_label, reference=reference, occurrences=occurrences,
        drift_fits=drift_fits, calibration_factor=calibration_factor,
        accuracy_table=accuracy_table, holdout_accuracy_table=holdout_accuracy_table,
        split_enabled=split_odd_even, skipped_analytes=skipped_analytes,
        excluded_outliers=excluded_outliers,
        manually_excluded_occurrences=manually_excluded_occurrences,
        mean_predicted_signal=mean_predicted_signal,
        detrend_fits=detrend_fits,
    )


def apply_calibration(signal: pd.DataFrame, absolute_time, result: StandardCalibrationResult) -> pd.DataFrame:
    """Applies ``result``'s drift-normalized calibration curve to arbitrary
    background-corrected signal (typically a sample's ablation signal):
    ``calibrated_ppm(t) = signal(t) / drift_fit.predict(t) * reference_value``,
    per analyte. Reduces to a constant multiplicative scale when the drift
    fit is order 0. Analytes with no drift fit / reference value (see
    ``StandardCalibrationResult.skipped_analytes``) are omitted from the output.
    """
    out = {}
    for analyte in signal.columns:
        fit = result.drift_fits.get(analyte)
        ref_entry = resolve_elemental_value(result.reference, analyte)
        ref_value = ref_entry.value if ref_entry else None
        if fit is None or ref_value is None:
            continue
        predicted = fit.predict(absolute_time)
        with np.errstate(divide="ignore", invalid="ignore"):
            calibrated = signal[analyte].to_numpy() / predicted * ref_value
        detrend_fit = result.detrend_fits.get(analyte)
        if detrend_fit is not None:
            calibrated = calibrated - detrend_fit.predict(absolute_time)
        out[analyte] = calibrated
    return pd.DataFrame(out, index=signal.index)


def combine_primary_standards(
    standard_results: dict[str, StandardCalibrationResult], primary_labels: list[str],
    force_zero_intercept: bool = False,
) -> MultiStandardCalibrationResult:
    """Combines two or more primary standards' own (already-computed, per-
    label) drift fits into one shared CPS-vs-ppm calibration curve per
    analyte.

    For each analyte, gathers one ``(standard_label, mean_predicted_cps,
    reference_ppm)`` point per primary standard that has both a resolvable
    drift fit (``mean_predicted_signal``, populated by
    :func:`calibrate_standard`) and a reference value for that analyte.
    With exactly one usable point, the resulting :class:`CalibrationCurve`
    is the same ratio-through-the-origin ``calibration_factor`` a single
    standard already computes (``method="single_point_ratio"``) -- calling
    this with one primary standard is a no-op vs. that existing behavior,
    it's just not the path callers should use for that case (see
    ``pipeline.run``, which only calls this for 2+ primary standards).
    With two or more, fits an ordinary-least-squares line via
    ``np.polyfit`` (free slope + intercept, ``method="multi_point_linear"``)
    by default. Pass ``force_zero_intercept=True`` to instead fit a line
    forced through the origin (least squares with the intercept term
    dropped: ``slope = sum(cps*ppm) / sum(cps**2)``, ``method=
    "multi_point_zero_intercept"``) -- this can't fully guarantee every
    calibrated value comes out non-negative (background-subtracted CPS
    itself can legitimately go negative near the detection limit, and that
    carries straight through a zero-intercept scaling), but it does remove
    the other common source: a free-intercept fit extrapolating to a
    negative value below the lowest calibration point. ``r_squared`` for
    the forced-origin fit uses the uncentered total sum of squares
    (``sum(ppm**2)``) rather than the usual mean-centered one, since
    forcing the intercept to zero makes the standard (mean-centered)
    definition behave poorly (not bounded to [0, 1], not comparable across
    fits) -- the standard convention for regression through the origin.

    Also picks, per analyte, which one of the contributing primary
    standards' own drift fits should time-normalize a sample's signal
    before the shared curve is applied (``drift_reference_by_analyte`` --
    see :func:`apply_multi_point_calibration`) -- the standard with the
    most kept (non-excluded, automatic or manual) occurrences for that
    analyte, ties broken alphabetically by label. Background/blank drift
    and this per-standard sensitivity-drift correction are deliberately
    kept as two separate steps (background.py's session-wide fit runs
    first and is already applied to every occurrence's signal before it
    ever reaches this module) -- this matches standard LA-ICP-MS data
    reduction practice (e.g. Iolite's baseline-subtraction-then-drift-
    correction sequence, Longerich et al. 1996's internal-standard drift
    correction being distinct from blank subtraction), not an artifact to
    collapse into one step.

    An analyte with no usable point from any primary standard is omitted
    (``skipped_analytes``).
    """
    analytes = sorted({
        a for label in primary_labels if label in standard_results
        for a in standard_results[label].mean_predicted_signal
    })
    curves: dict[str, CalibrationCurve] = {}
    drift_reference_by_analyte: dict[str, str] = {}
    skipped: list[str] = []

    for analyte in analytes:
        points: list[tuple[str, float, float]] = []
        for label in primary_labels:
            sr = standard_results.get(label)
            if sr is None:
                continue
            cps = sr.mean_predicted_signal.get(analyte)
            ref_entry = resolve_elemental_value(sr.reference, analyte)
            ref_value = ref_entry.value if ref_entry else None
            if cps is None or ref_value is None:
                continue
            points.append((label, cps, ref_value))

        if not points:
            skipped.append(analyte)
            continue

        if len(points) == 1:
            label, cps, ref_value = points[0]
            if cps == 0:
                skipped.append(analyte)
                continue
            curves[analyte] = CalibrationCurve(
                analyte=analyte, slope=ref_value / cps, intercept=0.0, r_squared=None,
                n_points=1, method="single_point_ratio", points=points,
            )
        else:
            cps_arr = np.array([p[1] for p in points], dtype=float)
            ppm_arr = np.array([p[2] for p in points], dtype=float)
            method = "multi_point_zero_intercept" if force_zero_intercept else "multi_point_linear"
            if float(np.ptp(cps_arr)) == 0.0:
                # Degenerate: every primary standard reports the same CPS
                # level for this analyte -- a line has no well-defined
                # slope through a single x value. Fall back to the ratio
                # through the mean (still uses every point's ppm value,
                # just can't distinguish a slope from an intercept) --
                # already a zero-intercept fit either way.
                mean_cps = float(np.mean(cps_arr))
                if mean_cps == 0:
                    skipped.append(analyte)
                    continue
                slope, intercept = float(np.mean(ppm_arr)) / mean_cps, 0.0
                r_squared = None
            elif force_zero_intercept:
                slope = float(np.sum(cps_arr * ppm_arr) / np.sum(cps_arr ** 2))
                intercept = 0.0
                predicted = slope * cps_arr
                ss_res = float(np.sum((ppm_arr - predicted) ** 2))
                ss_tot = float(np.sum(ppm_arr ** 2))  # uncentered -- see docstring
                r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
            else:
                slope, intercept = (float(c) for c in np.polyfit(cps_arr, ppm_arr, 1))
                predicted = slope * cps_arr + intercept
                ss_res = float(np.sum((ppm_arr - predicted) ** 2))
                ss_tot = float(np.sum((ppm_arr - np.mean(ppm_arr)) ** 2))
                r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
            curves[analyte] = CalibrationCurve(
                analyte=analyte, slope=slope, intercept=intercept, r_squared=r_squared,
                n_points=len(points), method=method, points=points,
            )

        def _kept_count(label: str) -> int:
            sr = standard_results[label]
            excluded = set(sr.excluded_outliers.get(analyte, [])) | set(sr.manually_excluded_occurrences.get(analyte, []))
            return sum(1 for o in sr.occurrences if o.occurrence_order not in excluded)

        candidate_labels = sorted({label for label, _, _ in points})
        drift_reference_by_analyte[analyte] = max(candidate_labels, key=_kept_count)

    return MultiStandardCalibrationResult(
        primary_labels=list(primary_labels), curves=curves,
        drift_reference_by_analyte=drift_reference_by_analyte, skipped_analytes=skipped,
    )


def apply_multi_point_calibration(
    signal: pd.DataFrame, absolute_time, multi_result: MultiStandardCalibrationResult,
    standard_results: dict[str, StandardCalibrationResult],
) -> pd.DataFrame:
    """Applies a :class:`MultiStandardCalibrationResult`'s per-analyte
    calibration curve to arbitrary background-corrected signal, the
    multi-point analog of :func:`apply_calibration`:
    ``calibrated_ppm(t) = (signal(t) / drift_fit.predict(t) * mean_predicted_cps)
    * slope + intercept``, where ``drift_fit``/``mean_predicted_cps`` come
    from whichever primary standard ``drift_reference_by_analyte`` picked
    for that analyte. The inner ``signal/drift_fit.predict(t) *
    mean_predicted_cps`` term is the same time-normalization
    ``apply_calibration`` performs, just expressed as a normalized CPS
    level rather than jumping straight to ppm -- for a single-point curve
    (``slope = ref_value/mean_predicted_cps``, ``intercept = 0``) this is
    algebraically identical to ``apply_calibration``'s output.
    """
    out = {}
    for analyte in signal.columns:
        curve = multi_result.curves.get(analyte)
        if curve is None:
            continue
        drift_label = multi_result.drift_reference_by_analyte.get(analyte)
        drift_result = standard_results.get(drift_label) if drift_label else None
        drift_fit = drift_result.drift_fits.get(analyte) if drift_result else None
        mean_predicted = drift_result.mean_predicted_signal.get(analyte) if drift_result else None
        if drift_fit is None or not mean_predicted:
            continue
        predicted = drift_fit.predict(absolute_time)
        with np.errstate(divide="ignore", invalid="ignore"):
            normalized_cps = signal[analyte].to_numpy() / predicted * mean_predicted
        calibrated = normalized_cps * curve.slope + curve.intercept
        detrend_fit = drift_result.detrend_fits.get(analyte)
        if detrend_fit is not None:
            calibrated = calibrated - detrend_fit.predict(absolute_time)
        out[analyte] = calibrated
    return pd.DataFrame(out, index=signal.index)
