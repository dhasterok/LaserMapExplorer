"""Top-level orchestrator: raw directory -> parsed files -> background/drift
corrected, standard-calibrated result.

Also handles the two-level "multi-sample session" layout observed in real
raw-data exports: a parent directory holding several self-contained sample
subfolders, each bracketed by its own standard files (see
``discover_sample_directories`` / ``run_batch``).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

from src.calibration.background import (
    AblationWindow,
    BackgroundResult,
    BackgroundWindow,
    BackgroundWindowOverride,
    compute_background_result,
    fit_session_background_drift,
    select_reference_channels,
    window_from_override,
)
from src.calibration.despike import noise_despike
from src.calibration.drift import DriftFitLike
from src.calibration.geometry import InstrumentSettings, compute_pixel_spacing
from src.calibration.dating_ratios import DatingRatioFit, DatingRatioSpec, corrected_dating_ratio, fit_session_dating_ratios
from src.calibration.isotope_apportion import IsotopeShareSpec, apportion_from_spec
from src.calibration.massbias import BiasFit, BiasSpec, DEFAULT_ISOTOPE_TABLE_PATH, corrected_ratio, fit_session_bias
from src.calibration.pooling import PooledElementSpec, synthesize_pooled_channels
from src.calibration.rawfile import LineFileData, list_line_files, parse_line_file
from src.calibration.reflib import ReferenceMaterial
from src.calibration.standards import (
    MultiStandardCalibrationResult,
    StandardCalibrationResult,
    apply_calibration,
    apply_multi_point_calibration,
    assemble_occurrences,
    calibrate_standard,
    combine_primary_standards,
)


class PipelineError(ValueError):
    """Raised for configuration problems the caller must resolve (e.g. an
    ambiguous primary-standard choice), as opposed to a per-file/per-analyte
    issue that's recorded in provenance and skipped."""


@dataclass
class SampleCalibratedResult:
    sample_label: str
    files: list[LineFileData]
    backgrounds: list[BackgroundResult]
    standard_results: dict[str, StandardCalibrationResult]
    calibrated_ppm: pd.DataFrame
    grid_index: pd.DataFrame
    session_background_drift: dict[str, DriftFitLike]
    instrument_settings: InstrumentSettings
    qc_report: dict
    provenance: dict = field(default_factory=dict)
    multi_standard_calibration: MultiStandardCalibrationResult | None = None  # set when 2+ primary_standards were used
    bias_fits: dict[str, BiasFit] = field(default_factory=dict)  # "Pb206/Pb204" -> session mass-bias fit, see massbias.py
    calibrated_ratios: pd.DataFrame = field(default_factory=pd.DataFrame)  # columns like "Pb206 / Pb204" -- mass-bias-corrected AND cross-element dating ratios share this one frame, per-row
    isotopic_ppm: pd.DataFrame = field(default_factory=pd.DataFrame)  # same analyte-string columns as calibrated_ppm (e.g. "Pb206"), but a SEPARATE frame -- see isotope_apportion.py
    isotopic_ppm_provenance: dict[str, dict] = field(default_factory=dict)  # "Pb" -> {"included_masses":..., "missing_masses":..., "normalizer_mass":...}
    dating_ratio_fits: dict[str, DatingRatioFit] = field(default_factory=dict)  # "Pb206/U238" -> session cross-element dating-ratio fit, see dating_ratios.py


def _group_by_label(files: list[LineFileData]) -> dict[str, list[LineFileData]]:
    groups: dict[str, list[LineFileData]] = {}
    for f in files:
        groups.setdefault(f.meta.label, []).append(f)
    return groups


def _timing_summary(backgrounds: list[BackgroundResult]) -> list[dict]:
    return [
        {
            "file": b.file_meta.path.name,
            "label": b.file_meta.label,
            "index": b.file_meta.index,
            "is_standard": b.file_meta.is_standard,
            "bg_start_time": b.window.start_time.isoformat(),
            "bg_end_time": b.window.end_time.isoformat(),
            "bg_method": b.window.method,
            "ablation_start_time": b.ablation.start_time.isoformat(),
            "ablation_end_time": b.ablation.end_time.isoformat(),
        }
        for b in sorted(backgrounds, key=lambda x: x.file_meta.acquired_at)
    ]


def _build_calibrated_ppm_and_grid(
    pairs: list[tuple[LineFileData, BackgroundResult]],
    standard_result: StandardCalibrationResult | None,
    instrument_settings: InstrumentSettings,
    multi_result: MultiStandardCalibrationResult | None = None,
    standard_results: dict[str, StandardCalibrationResult] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``multi_result``/``standard_results`` (both required together) route
    calibration through :func:`~src.calibration.standards.apply_multi_point_calibration`
    instead of the single-standard ``standard_result``/``apply_calibration``
    path -- used when 2+ primary standards were configured (see ``run()``)."""
    dx, dy = compute_pixel_spacing(instrument_settings)
    ordered = sorted(pairs, key=lambda p: p[0].meta.acquired_at)

    ppm_frames = []
    grid_rows = []
    index_tuples = []
    for line_number, (line_data, bg) in enumerate(ordered):
        abl_time = line_data.absolute_time[bg.ablation.start_idx:bg.ablation.end_idx]
        if multi_result is not None:
            calibrated = apply_multi_point_calibration(bg.background_corrected_signal, abl_time, multi_result, standard_results)
        else:
            calibrated = apply_calibration(bg.background_corrected_signal, abl_time, standard_result)
        calibrated = calibrated.reset_index(drop=True)
        n = len(calibrated)
        for sweep_index in range(n):
            index_tuples.append((line_data.meta.index, sweep_index))
            grid_rows.append({
                "file_index": line_data.meta.index,
                "row_in_ablation": sweep_index,
                "line_number": line_number,
                "sweep_index": sweep_index,
                "x": sweep_index * dx,
                "y": line_number * dy,
                "absolute_time": pd.Timestamp(abl_time[sweep_index]),
            })
        ppm_frames.append(calibrated)

    if not ppm_frames:
        return pd.DataFrame(), pd.DataFrame()

    calibrated_ppm = pd.concat(ppm_frames, ignore_index=True)
    multi_index = pd.MultiIndex.from_tuples(index_tuples, names=["file_index", "row_in_ablation"])
    calibrated_ppm.index = multi_index
    grid_index = pd.DataFrame(grid_rows)
    grid_index.index = multi_index
    return calibrated_ppm, grid_index


def _build_calibrated_ratios(
    pairs: list[tuple[LineFileData, BackgroundResult]], bias_fits: dict[str, BiasFit],
    dating_ratio_fits: dict[str, DatingRatioFit] | None = None,
) -> pd.DataFrame:
    """Sibling to :func:`_build_calibrated_ppm_and_grid`: mass-bias-
    corrected same-element isotope ratios (see ``massbias.corrected_ratio``,
    one column per ``bias_fits`` entry) AND standard-bracketed cross-element
    dating ratios (see ``dating_ratios.corrected_dating_ratio``, one column
    per ``dating_ratio_fits`` entry) in a single shared frame -- both use
    LaME's existing ``"<num> / <den>"`` ratio-field naming convention (see
    ``src/common/geochronology.py``), on the SAME ``(file_index,
    row_in_ablation)`` index ``_build_calibrated_ppm_and_grid`` produces
    for the same ``pairs`` -- both iterate ``pairs`` in the same
    ``acquired_at`` order and use every ablation row of every line (both
    corrections read ``bg.background_corrected_signal`` at its full,
    un-truncated length, same as ``apply_calibration`` does), so the two
    frames stay row-aligned without sharing index-building code.
    """
    dating_ratio_fits = dating_ratio_fits or {}
    if not bias_fits and not dating_ratio_fits:
        return pd.DataFrame()

    ordered = sorted(pairs, key=lambda p: p[0].meta.acquired_at)
    ratio_frames = []
    index_tuples = []
    for line_data, bg in ordered:
        abl_time = line_data.absolute_time[bg.ablation.start_idx:bg.ablation.end_idx]
        signal = bg.background_corrected_signal.reset_index(drop=True)
        n = len(signal)
        row_data = {}
        for key, fit in bias_fits.items():
            numerator, denominator = key.split("/")
            if numerator not in signal.columns or denominator not in signal.columns:
                continue
            row_data[f"{numerator} / {denominator}"] = corrected_ratio(
                signal, abl_time, fit, fit.numerator_mass, fit.denominator_mass,
            )
        for fit in dating_ratio_fits.values():
            numerator = f"{fit.numerator_element}{fit.numerator_mass}"
            denominator = f"{fit.denominator_element}{fit.denominator_mass}"
            if numerator not in signal.columns or denominator not in signal.columns:
                continue
            row_data[f"{numerator} / {denominator}"] = corrected_dating_ratio(signal, abl_time, fit)
        index_tuples.extend((line_data.meta.index, sweep_index) for sweep_index in range(n))
        ratio_frames.append(pd.DataFrame(row_data, index=range(n)))

    if not ratio_frames:
        return pd.DataFrame()

    calibrated_ratios = pd.concat(ratio_frames, ignore_index=True)
    calibrated_ratios.index = pd.MultiIndex.from_tuples(index_tuples, names=["file_index", "row_in_ablation"])
    return calibrated_ratios


def _build_isotopic_ppm(
    calibrated_ppm: pd.DataFrame, calibrated_ratios: pd.DataFrame, isotope_share_specs: list[IsotopeShareSpec],
    isotope_table: pd.DataFrame | str | Path | None = DEFAULT_ISOTOPE_TABLE_PATH,
) -> tuple[pd.DataFrame, dict[str, dict]]:
    """Per-sample isotope apportionment (see ``isotope_apportion.py``) --
    reads the already-built ``calibrated_ppm``/``calibrated_ratios`` frames'
    columns, so this must run after both are built. Specs with no usable
    data for this sample (missing total-ppm column, no resolvable ratio at
    all) are silently omitted, matching how an unresolvable analyte is
    handled elsewhere in this module."""
    if not isotope_share_specs or calibrated_ppm.empty:
        return pd.DataFrame(), {}

    ppm_columns = {col: calibrated_ppm[col].to_numpy() for col in calibrated_ppm.columns}
    ratio_columns = (
        {col: calibrated_ratios[col].to_numpy() for col in calibrated_ratios.columns}
        if not calibrated_ratios.empty else {}
    )

    isotopic_ppm_data: dict[str, "pd.Series | list"] = {}
    isotopic_ppm_provenance: dict[str, dict] = {}
    for spec in isotope_share_specs:
        result = apportion_from_spec(spec, ppm_columns, ratio_columns, isotope_table=isotope_table)
        if result is None:
            continue
        for mass, values in result.ppm.items():
            isotopic_ppm_data[f"{spec.element}{mass}"] = values
        isotopic_ppm_provenance[spec.element] = {
            "normalizer_mass": spec.normalizer_mass,
            "included_masses": result.included_masses,
            "missing_masses": result.missing_masses,
        }

    if not isotopic_ppm_data:
        return pd.DataFrame(), {}

    isotopic_ppm = pd.DataFrame(isotopic_ppm_data, index=calibrated_ppm.index)
    return isotopic_ppm, isotopic_ppm_provenance


def run(
    sample_dir: str | Path,
    standard_names: Iterable[str] | Callable[[str], bool],
    reference_library: dict[str, ReferenceMaterial],
    drift_order: int = 1,
    background_drift_order: int = 1,
    split_odd_even: bool = False,
    accuracy_threshold: float = 2.0,
    primary_standards: list[str] | None = None,
    instrument_settings: InstrumentSettings | None = None,
    background_detection_kwargs: dict | None = None,
    reference_channel_top_n: int = 5,
    drift_method: str = "fixed",
    background_drift_method: str = "fixed",
    max_order: int = 3,
    background_override: BackgroundWindowOverride | None = None,
    per_file_overrides: dict[str, BackgroundWindowOverride] | None = None,
    acquired_time_format: str | None = None,
    excluded_files: set[str] | None = None,
    manual_row_exclusions: dict[str, dict[str, set[int]]] | None = None,
    manual_occurrence_exclusions: dict[str, set[str]] | None = None,
    detrend: bool = False,
    despike_noise: bool = False,
    force_zero_intercept: bool = False,
    bias_specs: list[BiasSpec] | None = None,
    bias_drift_order: int = 1,
    bias_drift_method: str = "fixed",
    bias_max_order: int = 3,
    isotope_table: pd.DataFrame | str | Path | None = None,
    isotope_share_specs: list[IsotopeShareSpec] | None = None,
    pool_specs: list[PooledElementSpec] | None = None,
    dating_ratio_specs: list[DatingRatioSpec] | None = None,
    dating_ratio_drift_order: int = 1,
    dating_ratio_drift_method: str = "fixed",
    dating_ratio_max_order: int = 3,
) -> dict[str, SampleCalibratedResult]:
    """Runs the full background/drift/calibration pipeline over one self-contained
    raw-data folder (one or more sample labels, bracketed by standard files).

    ``drift_method``/``background_drift_method`` select between ``"fixed"``
    (OLS at ``drift_order``/``background_drift_order``, the original
    behavior), ``"auto_aic"``, and ``"auto_poisson_lrt"`` -- see
    ``standards.calibrate_standard``/``background.fit_session_background_drift``.
    ``max_order`` is the ceiling used by both ``"auto_*"`` methods.

    ``background_override`` (applied to every file) and ``per_file_overrides``
    (keyed by filename, taking precedence over the global override for that
    file) replace auto-detection with an explicit background/edge-trim
    window from relative time offsets -- see
    ``background.BackgroundWindowOverride``/``window_from_override``, for
    excluding mounting-epoxy contamination or a standard glass's edge-effect
    ramp. Files with no applicable override still use auto-detection.

    ``acquired_time_format`` overrides auto-detection of each file header's
    ``Acquired : <timestamp>`` line (see ``rawfile._parse_acquired_line``)
    -- only needed when an instrument export uses a timestamp layout none of
    the built-in candidates match (different export versions have already
    been seen to differ on 2- vs 4-digit years).

    ``excluded_files`` (matched by filename, e.g. ``"NIST610 - 3.csv"``)
    drops whole files before they enter background/drift fitting or
    calibration at all -- e.g. a standard line the user has decided is
    unusable. ``manual_row_exclusions``/``manual_occurrence_exclusions``
    are finer-grained, per-analyte manual overrides from the GUI's
    click/drag point masking (Time Series and Standards QC viewers
    respectively) -- see ``background.compute_background_result``/
    ``standards.assemble_occurrences``/``standards.calibrate_standard``'s
    own docstrings for exactly how each is applied; all three are
    additional, user-driven exclusions layered on top of (not replacing)
    the automatic outlier screens already run at each stage.

    ``primary_standards`` chooses which already-computed standard
    calibration(s) get applied to samples -- every standard label with a
    resolvable reference is *always* calibrated independently (``standard_
    results``, for its own QC regardless of primary/secondary status);
    this only picks which one(s) samples are actually calibrated against.
    Omitted/empty auto-infers: exactly one standard found -> use it; zero
    or more than one -> raises (ambiguous, pass this explicitly). With
    exactly one label, behavior is unchanged from the original single-
    standard ``apply_calibration`` path. With two or more, they're
    combined into one shared per-analyte CPS-vs-ppm calibration curve (see
    ``standards.combine_primary_standards``/``apply_multi_point_
    calibration``) -- a genuine multi-point linear fit rather than a
    single ratio.

    ``detrend`` (default off) enables an additional, deliberately simple
    post-hoc linear correction per standard/analyte when residual time
    trend remains in a standard's own accuracy-vs-time after its drift fit
    -- see ``standards.calibrate_standard``'s own docstring.

    ``force_zero_intercept`` (default off) only affects the 2+ primary
    standard (multi-point) case, forcing the shared CPS-vs-ppm calibration
    curve through the origin instead of fitting a free intercept -- see
    ``standards.combine_primary_standards``'s docstring for what this does
    and doesn't guarantee about negative calibrated values. The single-
    primary-standard case is already always a zero-intercept ratio and is
    unaffected by this flag either way.

    ``despike_noise`` (default off, matching this module's convention of
    new processing steps being opt-in) applies :func:`despike.noise_despike`
    to every analyte of every file immediately after parsing, before
    background/ablation windowing or any outlier detection -- a rolling-
    window, Poisson-consistent filter (ported from latools) that replaces
    isolated single-sweep spikes/dropouts with the local rolling mean. Runs
    with its default window/threshold (see that function's docstring); not
    independently tunable from here.

    ``bias_specs`` (default none -- opt in per isotope pair) requests
    mass-bias/radiogenic-isotope-ratio calibration (see ``massbias.py``):
    each ``massbias.BiasSpec`` names one same-element isotope pair (e.g.
    Pb206/Pb204) to correct for instrumental fractionation via standard
    bracketing, distinct from and complementary to the elemental (total-
    concentration) calibration above -- see ``massbias.resolve_truth_ratio``'s
    docstring for why this can't reuse natural-abundance scaling the way
    elemental calibration does. A spec with no usable data (no resolvable
    truth ratio for any bias standard, or too few bracketing points) is
    silently omitted from the result rather than raising, matching how a
    single unresolvable analyte is handled elsewhere in this pipeline, not
    treated as a fatal configuration error. ``bias_drift_order``/``bias_
    drift_method``/``bias_max_order`` mirror ``drift_order``/``drift_
    method``/``max_order`` above, but for the mass-bias log-ratio drift fit
    specifically (``"auto_poisson_lrt"`` is not valid here -- a log-ratio
    of two CPS channels isn't a Poisson count). ``isotope_table`` overrides
    the natural-abundance table read from ``resources/app_data/
    isotope_info.csv`` (a preloaded DataFrame, or an alternate path) --
    None uses the default.

    ``isotope_share_specs`` (default none) requests per-isotope concentration
    apportionment (see ``isotope_apportion.py``): each ``IsotopeShareSpec``
    names one element's normalizer isotope and companion isotopes (e.g. Pb204
    normalizer, 206/207/208 companions) and is resolved against that sample's
    own already-built ``calibrated_ppm`` (Mechanism A total-element ppm) and
    ``calibrated_ratios`` (this sample's own mass-bias-corrected ratios, from
    ``bias_specs`` above -- ``isotope_share_specs`` is meaningless without a
    matching ``bias_specs`` entry for the same pairs). Result is written to
    ``SampleCalibratedResult.isotopic_ppm``, a separate frame from
    ``calibrated_ppm`` (same analyte-string column names, e.g. ``"Pb206"``)
    so elemental-mode and isotopic-mode values for the same analyte can
    coexist without a column collision. A spec with no usable ratio data for
    a given sample is silently omitted from ``isotopic_ppm``, not raised.

    ``pool_specs`` (default none) synthesizes a pooled ``"<element>
    total"`` virtual raw channel per ``pooling.PooledElementSpec``,
    BEFORE background-window detection, from 2+ measured isotopes of the
    same element -- an opt-in precision tool (combining several channels'
    raw counts gives better counting statistics than any single isotope
    alone), not a correctness fix (a single isotope already independently
    estimates the same total-element concentration -- see
    ``reflib.resolve_elemental_value``'s docstring). The pooled channel
    then flows through the exact same background/drift/standard-
    bracketing machinery as any ordinary analyte and appears in
    ``calibrated_ppm`` alongside the individual isotopes -- see
    ``pooling.py``'s module docstring for the natural-abundance-fraction
    rescaling this relies on, and its caveat about NOT being valid for
    radiogenic isotope pairs.

    ``dating_ratio_specs`` (default none) requests cross-element parent/
    daughter isotope-ratio calibration for radiometric dating systems
    (e.g. 206Pb/238U, 208Pb/232Th -- see ``dating_ratios.py``): each
    ``dating_ratios.DatingRatioSpec`` names one ratio, corrected via
    session-level standard bracketing of the raw measured ratio against
    the reference material's own certified value (NOT down-hole
    fractionation curve-fitting, and NOT the same-element mass-bias law
    ``bias_specs`` uses -- a cross-element pair has no valid mass-ratio-
    exponent generalization). Same-element ratios needed for a dating
    system (e.g. Pb-Pb's 206Pb/204Pb, or U-Pb's 207Pb/206Pb) should
    instead go through ``bias_specs`` above -- ``dating_ratio_specs`` is
    only for genuinely cross-element pairs. Written into the SAME
    ``calibrated_ratios`` frame ``bias_specs``' ratios populate (one
    shared ``"<num> / <den>"``-named column set), reported separately in
    ``SampleCalibratedResult.dating_ratio_fits``/``qc_report``/
    ``provenance``. ``dating_ratio_drift_order``/``dating_ratio_drift_
    method``/``dating_ratio_max_order`` mirror ``bias_drift_order``/
    ``bias_drift_method``/``bias_max_order`` above, but for this fit
    specifically.

    Returns a dict keyed by sample label (non-standard files) -- usually one
    entry, but a folder may hold more than one distinct sample label.
    """
    sample_dir = Path(sample_dir)
    instrument_settings = instrument_settings or InstrumentSettings()
    background_detection_kwargs = background_detection_kwargs or {}
    per_file_overrides = per_file_overrides or {}
    excluded_files = excluded_files or set()
    manual_row_exclusions = manual_row_exclusions or {}
    manual_occurrence_exclusions = manual_occurrence_exclusions or {}
    bias_specs = bias_specs or []
    isotope_share_specs = isotope_share_specs or []
    pool_specs = pool_specs or []
    dating_ratio_specs = dating_ratio_specs or []
    isotope_table_resolved = isotope_table if isotope_table is not None else DEFAULT_ISOTOPE_TABLE_PATH

    paths = list_line_files(sample_dir)
    if not paths:
        raise PipelineError(f"No raw line files found in {sample_dir}.")
    paths = [p for p in paths if p.name not in excluded_files]
    if not paths:
        raise PipelineError(f"All raw line files in {sample_dir} were excluded via excluded_files.")

    files = [
        parse_line_file(p, standard_names=standard_names, acquired_time_format=acquired_time_format)
        for p in paths
    ]

    if despike_noise:
        for f in files:
            for analyte in f.analytes:
                f.signal[analyte] = noise_despike(f.signal[analyte].to_numpy())

    if pool_specs:
        synthesize_pooled_channels(files, pool_specs, isotope_table=isotope_table_resolved)

    reference_channels = select_reference_channels(files, top_n=reference_channel_top_n)

    def _override_window(f: LineFileData) -> tuple[BackgroundWindow, AblationWindow] | tuple[None, None]:
        override = per_file_overrides.get(f.meta.path.name) or background_override
        if override is None:
            return None, None
        return window_from_override(f, override)

    # First pass: auto-detect (or apply a manual override) and compute naive
    # per-file backgrounds.
    initial_backgrounds = []
    for f in files:
        window, ablation = _override_window(f)
        initial_backgrounds.append(
            compute_background_result(
                f, window=window, ablation=ablation,
                reference_channels=reference_channels, detection_kwargs=background_detection_kwargs,
                dwell_time_ms=instrument_settings.dwell_time_ms,
                sweeps_per_reading=instrument_settings.sweeps_per_reading,
                manual_row_exclusions=manual_row_exclusions.get(f.meta.path.name),
            )
        )

    # Session-level background drift (standards AND samples both contribute).
    session_background_drift = fit_session_background_drift(
        initial_backgrounds, order=background_drift_order, method=background_drift_method, max_order=max_order,
    )

    # Second pass: recompute with the session drift model, reusing the same
    # detected/overridden windows (no re-running changepoint detection).
    backgrounds = [
        compute_background_result(
            f, window=b.window, ablation=b.ablation, reference_channels=reference_channels,
            session_background_drift=session_background_drift,
            dwell_time_ms=instrument_settings.dwell_time_ms,
            sweeps_per_reading=instrument_settings.sweeps_per_reading,
            manual_row_exclusions=manual_row_exclusions.get(f.meta.path.name),
        )
        for f, b in zip(files, initial_backgrounds)
    ]

    pairs_by_label = _group_by_label(files)
    backgrounds_by_label: dict[str, list[BackgroundResult]] = {}
    for f, b in zip(files, backgrounds):
        backgrounds_by_label.setdefault(f.meta.label, []).append(b)

    standard_labels = [label for label, fs in pairs_by_label.items() if fs[0].meta.is_standard]
    sample_labels = [label for label, fs in pairs_by_label.items() if not fs[0].meta.is_standard]

    standard_results: dict[str, StandardCalibrationResult] = {}
    missing_reference_for: list[str] = []
    for label in standard_labels:
        reference = reference_library.get(label)
        if reference is None:
            missing_reference_for.append(label)
            continue
        occurrences = assemble_occurrences(backgrounds_by_label[label], manual_row_exclusions=manual_row_exclusions)
        standard_results[label] = calibrate_standard(
            occurrences, reference, drift_order=drift_order, split_odd_even=split_odd_even,
            accuracy_threshold=accuracy_threshold, standard_label=label,
            method=drift_method, max_order=max_order,
            manual_occurrence_exclusions=manual_occurrence_exclusions,
            detrend=detrend,
        )

    bias_fits = (
        fit_session_bias(
            standard_results, bias_specs, isotope_table=isotope_table_resolved,
            method=bias_drift_method, order=bias_drift_order, max_order=bias_max_order,
        )
        if bias_specs else {}
    )

    dating_ratio_fits = (
        fit_session_dating_ratios(
            standard_results, dating_ratio_specs,
            method=dating_ratio_drift_method, order=dating_ratio_drift_order, max_order=dating_ratio_max_order,
        )
        if dating_ratio_specs else {}
    )

    provenance_base = {
        "raw_dir": str(sample_dir),
        "standard_labels_found": standard_labels,
        "sample_labels_found": sample_labels,
        "missing_reference_for_standards": missing_reference_for,
        "drift_order": drift_order,
        "background_drift_order": background_drift_order,
        "drift_method": drift_method,
        "background_drift_method": background_drift_method,
        "max_order": max_order,
        "split_odd_even": split_odd_even,
        "accuracy_threshold": accuracy_threshold,
        "reference_channels": reference_channels,
        "instrument_settings": asdict(instrument_settings),
        "background_override": asdict(background_override) if background_override else None,
        "per_file_overrides": {name: asdict(o) for name, o in per_file_overrides.items()},
        "excluded_files": sorted(excluded_files),
        "detrend": detrend,
        "despike_noise": despike_noise,
        "force_zero_intercept": force_zero_intercept,
        "bias_specs": [
            {
                "element": s.element, "numerator_mass": s.numerator_mass, "denominator_mass": s.denominator_mass,
                "bias_standards": s.bias_standards,
            }
            for s in bias_specs
        ],
        "bias_drift_order": bias_drift_order,
        "bias_drift_method": bias_drift_method,
        "isotope_share_specs": [
            {
                "element": s.element, "normalizer_mass": s.normalizer_mass,
                "companion_masses": s.companion_masses, "total_ppm_source_mass": s.total_ppm_source_mass,
            }
            for s in isotope_share_specs
        ],
        "pool_specs": [{"element": s.element, "masses": s.masses} for s in pool_specs],
        "dating_ratio_specs": [
            {
                "numerator_element": s.numerator_element, "numerator_mass": s.numerator_mass,
                "denominator_element": s.denominator_element, "denominator_mass": s.denominator_mass,
                "numerator_scale_factor": s.numerator_scale_factor, "dating_standards": s.dating_standards,
            }
            for s in dating_ratio_specs
        ],
        "dating_ratio_drift_order": dating_ratio_drift_order,
        "dating_ratio_drift_method": dating_ratio_drift_method,
        "generated_at": datetime.now().isoformat(),
    }

    results: dict[str, SampleCalibratedResult] = {}
    if not sample_labels:
        return results

    if primary_standards:
        missing_primary = [p for p in primary_standards if p not in standard_results]
        if missing_primary:
            raise PipelineError(
                f"primary_standards {missing_primary} have no usable calibration "
                f"(available: {sorted(standard_results)})."
            )
        chosen_standards = list(primary_standards)
    elif len(standard_results) == 1:
        chosen_standards = [next(iter(standard_results))]
    elif len(standard_results) == 0:
        raise PipelineError(
            f"No standard could be calibrated in {sample_dir} (found standard labels "
            f"{standard_labels}, missing reference data for {missing_reference_for})."
        )
    else:
        raise PipelineError(
            f"Multiple standards available ({sorted(standard_results)}) -- pass primary_standards= to choose."
        )

    multi_result = (
        combine_primary_standards(standard_results, chosen_standards, force_zero_intercept=force_zero_intercept)
        if len(chosen_standards) > 1 else None
    )

    for label in sample_labels:
        sample_files = pairs_by_label[label]
        sample_backgrounds = backgrounds_by_label[label]
        pairs = list(zip(sample_files, sample_backgrounds))

        if multi_result is not None:
            calibrated_ppm, grid_index = _build_calibrated_ppm_and_grid(
                pairs, None, instrument_settings, multi_result=multi_result, standard_results=standard_results,
            )
        else:
            calibrated_ppm, grid_index = _build_calibrated_ppm_and_grid(
                pairs, standard_results[chosen_standards[0]], instrument_settings,
            )

        calibrated_ratios = _build_calibrated_ratios(pairs, bias_fits, dating_ratio_fits)
        isotopic_ppm, isotopic_ppm_provenance = _build_isotopic_ppm(
            calibrated_ppm, calibrated_ratios, isotope_share_specs, isotope_table=isotope_table_resolved,
        )

        qc_report = {
            "n_files": len(sample_files),
            "timing": _timing_summary(sample_backgrounds),
            "primary_standards": chosen_standards,
            "standards": {
                lbl: {
                    "n_occurrences": len(sr.occurrences),
                    "n_flagged_fit": sum(1 for r in sr.accuracy_table if r.flagged),
                    "n_flagged_holdout": (
                        sum(1 for r in sr.holdout_accuracy_table if r.flagged)
                        if sr.holdout_accuracy_table is not None else None
                    ),
                    "skipped_analytes": sr.skipped_analytes,
                }
                for lbl, sr in standard_results.items()
            },
        }
        if multi_result is not None:
            qc_report["calibration_curves"] = {
                analyte: {
                    "method": curve.method, "slope": curve.slope, "intercept": curve.intercept,
                    "r_squared": curve.r_squared, "n_points": curve.n_points,
                }
                for analyte, curve in multi_result.curves.items()
            }
        if bias_fits:
            qc_report["bias_fits"] = {
                pair: {
                    "n_points": fit.n_points, "truth_source": fit.truth.source,
                    "truth_value": fit.truth.value, "standard_labels": fit.standard_labels,
                }
                for pair, fit in bias_fits.items()
            }
        if isotopic_ppm_provenance:
            qc_report["isotopic_ppm"] = isotopic_ppm_provenance
        if dating_ratio_fits:
            qc_report["dating_ratio_fits"] = {
                pair: {
                    "n_points": fit.n_points, "truth_source": fit.truth.source,
                    "truth_value": fit.truth.value, "standard_labels": fit.standard_labels,
                }
                for pair, fit in dating_ratio_fits.items()
            }

        provenance = dict(provenance_base)
        provenance["sample_label"] = label
        provenance["primary_standards"] = chosen_standards

        results[label] = SampleCalibratedResult(
            sample_label=label, files=sample_files, backgrounds=sample_backgrounds,
            standard_results=standard_results, calibrated_ppm=calibrated_ppm, grid_index=grid_index,
            session_background_drift=session_background_drift, instrument_settings=instrument_settings,
            qc_report=qc_report, provenance=provenance, multi_standard_calibration=multi_result,
            bias_fits=bias_fits, calibrated_ratios=calibrated_ratios,
            isotopic_ppm=isotopic_ppm, isotopic_ppm_provenance=isotopic_ppm_provenance,
            dating_ratio_fits=dating_ratio_fits,
        )

    return results


def discover_sample_directories(parent_dir: str | Path) -> list[Path]:
    """Subfolders of ``parent_dir`` that look like self-contained raw-file sets
    (i.e. contain at least one file matching '<label> - <N>.csv')."""
    parent_dir = Path(parent_dir)
    return [child for child in sorted(p for p in parent_dir.iterdir() if p.is_dir()) if list_line_files(child)]


def run_batch(
    parent_dir: str | Path,
    standard_names: Iterable[str] | Callable[[str], bool],
    reference_library: dict[str, ReferenceMaterial],
    **kwargs,
) -> dict[str, dict[str, SampleCalibratedResult]]:
    """Runs :func:`run` independently over every sample subfolder discovered
    under ``parent_dir``.

    Standards are NOT shared across folders by default -- each subfolder
    brackets and calibrates its own samples, matching what's observed on real
    multi-sample sessions (each sibling folder has its own standard files).
    This assumption is recorded in each result's provenance rather than
    silently baked in.
    """
    results: dict[str, dict[str, SampleCalibratedResult]] = {}
    for sample_dir in discover_sample_directories(parent_dir):
        folder_results = run(sample_dir, standard_names, reference_library, **kwargs)
        for sample_result in folder_results.values():
            sample_result.provenance["standards_shared_across_folders"] = False
            sample_result.provenance["batch_parent_dir"] = str(parent_dir)
        results[sample_dir.name] = folder_results
    return results
