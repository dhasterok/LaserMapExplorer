"""Top-level orchestrator: raw directory -> parsed files -> background/drift
corrected, standard-calibrated result.

:func:`run` treats a session folder and its immediate subfolders as one
pooled run (see :func:`gather_session_line_files`) -- the common real-world
layout where standards and samples each sit in their own subdirectory
(``session/N610/``, ``session/GSD/``, ``session/RM01/`` …) but share one
background/drift fit and one set of bracketing standards.

:func:`run_batch` handles the other layout -- a parent directory of several
*independent* self-contained sessions, each calibrated on its own (see
``discover_sample_directories``).
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
from src.deconvolution.config import DeconvolutionSettings
from src.deconvolution.pipeline import correct_line
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
    """Everything the pipeline produces for one sample label.

    Attributes
    ----------
    sample_label : str
        The sample's filename label.
    files : list[LineFileData]
        The sample's parsed raw files.
    backgrounds : list[BackgroundResult]
        Per-file background results for ``files``.
    standard_results : dict[str, StandardCalibrationResult]
        Every calibrated standard label in the session (not just the
        primaries), for QC.
    calibrated_ppm : pandas.DataFrame
        Calibrated elemental ppm, ``(file_index, row_in_ablation)`` index,
        one column per analyte.
    grid_index : pandas.DataFrame
        Per-pixel grid/position columns aligned with ``calibrated_ppm``.
    session_background_drift : dict[str, DriftFitLike]
        Per-analyte session background drift fits.
    instrument_settings : InstrumentSettings
        The geometry/metadata settings used.
    qc_report : dict
        Nested QC summary (timing, per-standard flag counts, curve stats,
        ...).
    provenance : dict
        Full record of the inputs and options this run used.
    multi_standard_calibration : MultiStandardCalibrationResult or None
        Set when 2+ primary standards were combined.
    bias_fits : dict[str, BiasFit]
        ``"Pb206/Pb204"`` -> session mass-bias fit (see ``massbias.py``).
    calibrated_ratios : pandas.DataFrame
        Mass-bias-corrected *and* cross-element dating ratios, one
        ``"<num> / <den>"`` column each, sharing this per-row frame.
    isotopic_ppm : pandas.DataFrame
        Isotope-apportioned concentrations -- same analyte-string columns as
        ``calibrated_ppm`` but a separate frame (see
        ``isotope_apportion.py``).
    isotopic_ppm_provenance : dict[str, dict]
        Per-element ``{"included_masses", "missing_masses",
        "normalizer_mass"}``.
    dating_ratio_fits : dict[str, DatingRatioFit]
        ``"Pb206/U238"`` -> session cross-element dating-ratio fit.
    deconvolution_provenance : dict[int, dict]
        ``line_number`` -> per-analyte deconvolution provenance.
    deconvolution_settings : DeconvolutionSettings or None
        The settings actually used, retained so a "deconvolution
        correction" map stage can recompute the per-pixel delta.
    classification : pandas.DataFrame
        ``label``/``score``/``gap``/``ambiguous`` columns on the
        ``calibrated_ppm`` index; set by the GUI's classify step, empty
        until the user runs it.
    classification_categories : list[str]
        The selected mineral-name subset in stable sorted order, fixing the
        discrete colormap's code->name mapping.
    """

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
    deconvolution_provenance: dict[int, dict] = field(default_factory=dict)  # line_number -> {analyte -> {shift_applied, washout_applied, tau_s, noise_amplification, negative_count, flags}}, see src/deconvolution/pipeline.py
    deconvolution_settings: DeconvolutionSettings | None = None  # the settings actually used -- kept (not just the resulting provenance) so a "deconvolution correction" map stage can recompute the per-pixel delta on demand, same recompute-don't-store convention as the "background+drift correction" map stage (see dock_widgets._stage_series)
    ablation_onset_trim_s: float = 0.0  # leading-row trim applied when building calibrated_ppm -- retained so apply_deconvolution() can re-derive with the same trim
    isotope_share_specs: list[IsotopeShareSpec] = field(default_factory=list)  # the resolved per-isotope apportionment specs -- retained so apply_deconvolution() can rebuild isotopic_ppm from the deconvolved calibrated_ppm
    classification: pd.DataFrame = field(default_factory=pd.DataFrame)  # columns label/score/gap/ambiguous, same (file_index, row_in_ablation) index as calibrated_ppm -- set by dock_widgets._on_classify (Stage 3, src/classification/), not by run() itself; empty until the user runs it
    classification_categories: list[str] = field(default_factory=list)  # the selected mineral-name subset, in stable sorted order -- fixes the discrete colormap's code->name mapping regardless of which minerals actually got assigned


def _group_by_label(files: list[LineFileData]) -> dict[str, list[LineFileData]]:
    """Group parsed files by their filename label.

    Parameters
    ----------
    files : list[LineFileData]
        Parsed raw files.

    Returns
    -------
    dict[str, list[LineFileData]]
        ``label -> files with that label``, preserving input order within
        each group.
    """
    groups: dict[str, list[LineFileData]] = {}
    for f in files:
        groups.setdefault(f.meta.label, []).append(f)
    return groups


def _timing_summary(backgrounds: list[BackgroundResult]) -> list[dict]:
    """Serialize per-file background/ablation timing to JSON-ready dicts.

    Parameters
    ----------
    backgrounds : list[BackgroundResult]
        Background results to summarize; sorted here by ``acquired_at``.

    Returns
    -------
    list[dict]
        One dict per file with ISO-8601 timing strings and window methods.
    """
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
    deconvolution_settings: DeconvolutionSettings | None = None,
    ablation_onset_trim_s: float = 0.0,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, dict]]:
    """Build the calibrated ppm frame and its per-pixel grid index.

    Parameters
    ----------
    pairs : list[tuple[LineFileData, BackgroundResult]]
        One ``(line, background)`` pair per file of a single sample label.
        Sorted here by ``acquired_at``.
    standard_result : StandardCalibrationResult or None
        Single-standard calibration to apply. Ignored when ``multi_result``
        is given.
    instrument_settings : InstrumentSettings
        Supplies pixel spacing for the grid.
    multi_result : MultiStandardCalibrationResult or None, optional
        Multi-standard calibration; when given (together with
        ``standard_results``) routes through
        :func:`~src.calibration.standards.apply_multi_point_calibration`.
    standard_results : dict[str, StandardCalibrationResult] or None, optional
        Per-label results, required with ``multi_result`` for the
        per-analyte drift reference.
    deconvolution_settings : DeconvolutionSettings or None, optional
        When given, applies
        :func:`src.deconvolution.pipeline.correct_line` to each line's
        background-corrected signal immediately before calibration.
    ablation_onset_trim_s : float, optional
        Seconds of leading ablation rows dropped from *every* line before
        deconvolution/calibration, by default ``0.0`` (off).

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame, dict[int, dict]]
        ``(calibrated_ppm, grid_index, deconvolution_provenance)``. The
        first two share a ``(file_index, row_in_ablation)`` MultiIndex; both
        are empty frames when ``pairs`` yields no rows.

    Notes
    -----
    ``deconvolution_settings``, when given, applies
    :func:`src.deconvolution.pipeline.correct_line` to each line's
    background-corrected signal (still pre-calibration counts) immediately
    before calibration -- this is the ordering the design spec requires
    (Sec 7.1: deconvolve before ratioing/calibration). ``None`` (the
    default) skips deconvolution entirely, identical to this function's
    behavior before deconvolution existed.

    ``ablation_onset_trim_s`` (default 0.0, off) drops that many seconds'
    worth of leading rows from *every* line's ablation window -- the
    aerosol-transport ramp-up after the laser starts firing takes a few
    sweeps to reach steady-state, so the first several pixels of a raw
    ablation interval aren't representative of the true sample composition.
    This is deliberately separate from ``BackgroundWindowOverride.
    edge_trim_lead_s`` (see that field's docstring): the edge-trim override
    only narrows the region used for a *standard's own* calibration-factor
    statistics, never touching ``background_corrected_signal`` itself --
    exactly why the ramp still showed up in samples' per-pixel maps and
    classification despite edge_trim_lead_s existing. Applied here, before
    deconvolution and calibration both see the signal, and to standards and
    samples alike (the ramp is a physical aerosol-onset artifact, not
    sample-specific).
    """
    dx, dy = compute_pixel_spacing(instrument_settings)
    ordered = sorted(pairs, key=lambda p: p[0].meta.acquired_at)

    ppm_frames = []
    grid_rows = []
    index_tuples = []
    deconvolution_provenance: dict[int, dict] = {}
    for line_number, (line_data, bg) in enumerate(ordered):
        onset_trim_rows = int(round(ablation_onset_trim_s / line_data.dt_s)) if ablation_onset_trim_s > 0 else 0
        abl_time = line_data.absolute_time[bg.ablation.start_idx + onset_trim_rows:bg.ablation.end_idx]
        signal = bg.background_corrected_signal.iloc[onset_trim_rows:].reset_index(drop=True)
        if deconvolution_settings is not None:
            line_result = correct_line(signal, line_data.analytes, deconvolution_settings, instrument_settings, line_number)
            signal = line_result.corrected
            deconvolution_provenance[line_number] = line_result.provenance
        if multi_result is not None:
            calibrated = apply_multi_point_calibration(signal, abl_time, multi_result, standard_results)
        else:
            calibrated = apply_calibration(signal, abl_time, standard_result)
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
        return pd.DataFrame(), pd.DataFrame(), deconvolution_provenance

    calibrated_ppm = pd.concat(ppm_frames, ignore_index=True)
    multi_index = pd.MultiIndex.from_tuples(index_tuples, names=["file_index", "row_in_ablation"])
    calibrated_ppm.index = multi_index
    grid_index = pd.DataFrame(grid_rows)
    grid_index.index = multi_index
    return calibrated_ppm, grid_index, deconvolution_provenance


def _build_calibrated_ratios(
    pairs: list[tuple[LineFileData, BackgroundResult]], bias_fits: dict[str, BiasFit],
    dating_ratio_fits: dict[str, DatingRatioFit] | None = None,
) -> pd.DataFrame:
    """Build the shared frame of corrected isotope and dating ratios.

    Parameters
    ----------
    pairs : list[tuple[LineFileData, BackgroundResult]]
        One ``(line, background)`` pair per file of a single sample label.
        Sorted here by ``acquired_at``.
    bias_fits : dict[str, BiasFit]
        ``"<num>/<den>"`` -> mass-bias fit; one corrected column per entry
        whose channels are present.
    dating_ratio_fits : dict[str, DatingRatioFit] or None, optional
        ``"<num>/<den>"`` -> cross-element dating-ratio fit; one corrected
        column per entry whose channels are present.

    Returns
    -------
    pandas.DataFrame
        Corrected ratios with a ``(file_index, row_in_ablation)``
        MultiIndex, columns named ``"<num> / <den>"``. Empty when there are
        no fits or no usable columns.

    Notes
    -----
    Row-aligned with :func:`_build_calibrated_ppm_and_grid` without sharing
    index-building code: both iterate ``pairs`` in ``acquired_at`` order and
    use every ablation row of every line (reading
    ``bg.background_corrected_signal`` at full length). Uses LaME's
    ``"<num> / <den>"`` ratio-field naming convention (see
    ``src/common/geochronology.py``).
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
    """Apportion per-isotope concentrations for a sample.

    Parameters
    ----------
    calibrated_ppm : pandas.DataFrame
        The sample's calibrated elemental ppm (already built).
    calibrated_ratios : pandas.DataFrame
        The sample's mass-bias-corrected ratios (already built). May be
        empty.
    isotope_share_specs : list[IsotopeShareSpec]
        One entry per element to apportion.
    isotope_table : pandas.DataFrame or str or pathlib.Path or None, optional
        Isotope table (or path) for ``"natural_abundance"`` mode. Defaults
        to :data:`~src.calibration.massbias.DEFAULT_ISOTOPE_TABLE_PATH`.

    Returns
    -------
    tuple[pandas.DataFrame, dict[str, dict]]
        ``(isotopic_ppm, provenance)`` where ``isotopic_ppm`` has the
        ``calibrated_ppm`` index and ``provenance`` maps each element to its
        ``{"normalizer_mass", "included_masses", "missing_masses"}``. Both
        empty when nothing resolves.

    Notes
    -----
    Must run after both input frames are built. Specs with no usable data
    for this sample (missing total-ppm column, no resolvable ratio) are
    silently omitted.
    """
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
    session_drift_exclude_labels: set[str] | None = None,
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
    deconvolution_settings: DeconvolutionSettings | None = None,
    ablation_onset_trim_s: float = 0.0,
) -> dict[str, SampleCalibratedResult]:
    """Run the full background/drift/calibration pipeline over one session folder.

    Parameters
    ----------
    sample_dir : str or pathlib.Path
        The session folder. Raw line files are gathered from it *and each
        of its immediate subfolders* (see :func:`gather_session_line_files`),
        so a session laid out as ``session/N610/``, ``session/GSD/``,
        ``session/RM01/`` … is pooled into one run: one shared
        background/drift fit and one set of bracketing standards across
        every sample.
    standard_names : Iterable[str] or Callable[[str], bool]
        Which filename labels are reference standards.
    reference_library : dict[str, ReferenceMaterial]
        Certified compositions keyed by standard label.
    drift_order, background_drift_order : int, optional
        Polynomial order for the standard-signal and session-background
        drift fits when the corresponding method is ``"fixed"``. Both
        default to ``1``.
    split_odd_even : bool, optional
        Odd/even holdout split for standard accuracy QC. By default
        ``False``.
    accuracy_threshold : float, optional
        ``z``/``t`` cutoff for flagging accuracy rows, by default ``2.0``.
    primary_standards : list[str] or None, optional
        Which calibrated standard(s) samples are calibrated against.
        ``None``/empty auto-infers (exactly one standard -> use it, else
        raise).
    instrument_settings : InstrumentSettings or None, optional
        Geometry/metadata; a blank :class:`InstrumentSettings` when
        ``None``.
    background_detection_kwargs : dict or None, optional
        Extra keyword arguments for :func:`detect_background_window`.
    reference_channel_top_n : int, optional
        Number of background-detection reference channels, by default ``5``.
    drift_method, background_drift_method : {"fixed", "auto_aic", "auto_poisson_lrt"}, optional
        Order-selection strategy for the standard and background drift fits.
        Both default to ``"fixed"``.
    max_order : int, optional
        Order ceiling for the ``auto_*`` methods, by default ``3``.
    background_override : BackgroundWindowOverride or None, optional
        Global manual background/edge-trim window replacing auto-detection.
    per_file_overrides : dict[str, BackgroundWindowOverride] or None, optional
        Per-filename overrides taking precedence over ``background_override``.
    acquired_time_format : str or None, optional
        :func:`datetime.datetime.strptime` pattern overriding header
        timestamp auto-detection.
    excluded_files : set[str] or None, optional
        Filenames dropped entirely before any fitting.
    session_drift_exclude_labels : set[str] or None, optional
        Filename labels whose gas blanks are left *out of the session
        background-drift fit* (:func:`fit_session_background_drift`). Those
        labels are still parsed, background-corrected (with the model fit
        from the remaining files), and calibrated -- this only removes their
        contribution to the fit, e.g. for a sample whose blank is
        contaminated. Empty/``None`` pools every label.
    manual_row_exclusions : dict[str, dict[str, set[int]]] or None, optional
        ``filename -> analyte -> row indices`` to exclude (Time Series
        viewer).
    manual_occurrence_exclusions : dict[str, set[str]] or None, optional
        ``filename -> analytes`` to drop from that analyte's drift
        fit/calibration factor (Standards QC viewer).
    detrend : bool, optional
        Enable the post-hoc linear detrend per standard/analyte, by default
        ``False``.
    despike_noise : bool, optional
        Apply :func:`~src.calibration.despike.noise_despike` to every
        analyte immediately after parsing, by default ``False``.
    force_zero_intercept : bool, optional
        Force the multi-point calibration curve through the origin (2+
        primary standards only), by default ``False``.
    bias_specs : list[BiasSpec] or None, optional
        Same-element mass-bias/isotope-ratio calibration requests.
    bias_drift_order : int, optional
        Polynomial order for the mass-bias log-ratio drift fit, by default
        ``1``.
    bias_drift_method : {"fixed", "auto_aic"}, optional
        Order-selection strategy for the mass-bias fit, by default
        ``"fixed"``.
    bias_max_order : int, optional
        Order ceiling for the mass-bias ``auto_aic`` path, by default ``3``.
    isotope_table : pandas.DataFrame or str or pathlib.Path or None, optional
        Natural-abundance table override; ``None`` uses the default path.
    isotope_share_specs : list[IsotopeShareSpec] or None, optional
        Per-isotope concentration apportionment requests (needs matching
        ``bias_specs``).
    pool_specs : list[PooledElementSpec] or None, optional
        Pooled ``"<element> total"`` virtual channels to synthesize before
        background detection.
    dating_ratio_specs : list[DatingRatioSpec] or None, optional
        Cross-element parent/daughter dating-ratio calibration requests.
    dating_ratio_drift_order : int, optional
        Polynomial order for the dating-ratio drift fit, by default ``1``.
    dating_ratio_drift_method : {"fixed", "auto_aic"}, optional
        Order-selection strategy for the dating-ratio fit, by default
        ``"fixed"``.
    dating_ratio_max_order : int, optional
        Order ceiling for the dating-ratio ``auto_aic`` path, by default
        ``3``.
    deconvolution_settings : DeconvolutionSettings or None, optional
        Dwell-offset shift / washout-tailing correction applied before
        calibration.
    ablation_onset_trim_s : float, optional
        Seconds of leading ablation rows dropped from every line before
        deconvolution/calibration, by default ``0.0``.

    Returns
    -------
    dict[str, SampleCalibratedResult]
        One entry per non-standard sample label found in ``sample_dir``
        (usually one).

    Raises
    ------
    PipelineError
        If no raw files are found, all are excluded, or the primary
        standard cannot be determined unambiguously.

    Notes
    -----
    ``deconvolution_settings``, when given, applies dwell-offset shift and/or
    washout-tailing correction (``src/deconvolution/``) to each line's
    background-corrected counts before standard calibration -- see
    ``_build_calibrated_ppm_and_grid``'s docstring for the ordering
    rationale. Defaults to ``None`` (no deconvolution), so existing callers
    see unchanged behavior.

    ``ablation_onset_trim_s`` (default 0.0, off) drops that many seconds of
    leading rows from every line's ablation window before deconvolution/
    calibration -- see ``_build_calibrated_ppm_and_grid``'s docstring for
    why this is separate from ``BackgroundWindowOverride.edge_trim_lead_s``
    (that one only affects a standard's own calibration-factor statistics,
    never the per-pixel data itself).

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
    """
    sample_dir = Path(sample_dir)
    instrument_settings = instrument_settings or InstrumentSettings()
    background_detection_kwargs = background_detection_kwargs or {}
    per_file_overrides = per_file_overrides or {}
    excluded_files = excluded_files or set()
    manual_row_exclusions = manual_row_exclusions or {}
    manual_occurrence_exclusions = manual_occurrence_exclusions or {}
    session_drift_exclude_labels = session_drift_exclude_labels or set()
    bias_specs = bias_specs or []
    isotope_share_specs = isotope_share_specs or []
    pool_specs = pool_specs or []
    dating_ratio_specs = dating_ratio_specs or []
    isotope_table_resolved = isotope_table if isotope_table is not None else DEFAULT_ISOTOPE_TABLE_PATH

    paths = gather_session_line_files(sample_dir)
    if not paths:
        raise PipelineError(f"No raw line files found in {sample_dir} or its immediate subfolders.")
    paths = [p for p in paths if p.name not in excluded_files]
    if not paths:
        raise PipelineError(f"All raw line files under {sample_dir} were excluded via excluded_files.")

    files = [
        parse_line_file(p, standard_names=standard_names, acquired_time_format=acquired_time_format)
        for p in paths
    ]

    return _run_from_files(
        files=files, sample_dir=sample_dir, reference_library=reference_library,
        drift_order=drift_order, background_drift_order=background_drift_order,
        split_odd_even=split_odd_even, accuracy_threshold=accuracy_threshold,
        primary_standards=primary_standards, instrument_settings=instrument_settings,
        background_detection_kwargs=background_detection_kwargs,
        reference_channel_top_n=reference_channel_top_n, drift_method=drift_method,
        background_drift_method=background_drift_method, max_order=max_order,
        background_override=background_override, per_file_overrides=per_file_overrides,
        excluded_files=excluded_files, session_drift_exclude_labels=session_drift_exclude_labels,
        manual_row_exclusions=manual_row_exclusions,
        manual_occurrence_exclusions=manual_occurrence_exclusions, detrend=detrend,
        despike_noise=despike_noise, force_zero_intercept=force_zero_intercept,
        bias_specs=bias_specs, bias_drift_order=bias_drift_order, bias_drift_method=bias_drift_method,
        bias_max_order=bias_max_order, isotope_table=isotope_table_resolved,
        isotope_share_specs=isotope_share_specs, pool_specs=pool_specs,
        dating_ratio_specs=dating_ratio_specs, dating_ratio_drift_order=dating_ratio_drift_order,
        dating_ratio_drift_method=dating_ratio_drift_method, dating_ratio_max_order=dating_ratio_max_order,
        deconvolution_settings=deconvolution_settings, ablation_onset_trim_s=ablation_onset_trim_s,
    )


def _run_from_files(
    files: list[LineFileData],
    sample_dir,
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
    excluded_files: set[str] | None = None,
    session_drift_exclude_labels: set[str] | None = None,
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
    deconvolution_settings: DeconvolutionSettings | None = None,
    ablation_onset_trim_s: float = 0.0,
) -> dict[str, SampleCalibratedResult]:
    """Shared implementation behind :func:`run` and :func:`run_from_parsed`.

    Parameters
    ----------
    files : list[LineFileData]
        Already-parsed raw files. ``meta.is_standard`` must already be
        correct for the current selection.
    sample_dir : str or pathlib.Path
        Used only as a provenance/error-message label here, not for file
        I/O.
    reference_library : dict[str, ReferenceMaterial]
        Certified compositions keyed by standard label.
    **kwargs
        Every other option; see :func:`run` for the full description of
        each (the names and defaults are identical).

    Returns
    -------
    dict[str, SampleCalibratedResult]
        One entry per non-standard sample label.

    Raises
    ------
    PipelineError
        If the primary standard cannot be determined unambiguously.

    Notes
    -----
    Everything from despike/pooling through per-sample grid building is
    identical whether ``files`` were parsed fresh (:func:`run`) or reused
    from a prior Scan (:func:`run_from_parsed`).
    """
    instrument_settings = instrument_settings or InstrumentSettings()
    background_detection_kwargs = background_detection_kwargs or {}
    per_file_overrides = per_file_overrides or {}
    excluded_files = excluded_files or set()
    session_drift_exclude_labels = session_drift_exclude_labels or set()
    manual_row_exclusions = manual_row_exclusions or {}
    manual_occurrence_exclusions = manual_occurrence_exclusions or {}
    bias_specs = bias_specs or []
    isotope_share_specs = isotope_share_specs or []
    pool_specs = pool_specs or []
    dating_ratio_specs = dating_ratio_specs or []
    isotope_table_resolved = isotope_table if isotope_table is not None else DEFAULT_ISOTOPE_TABLE_PATH

    if despike_noise:
        for f in files:
            for analyte in f.analytes:
                f.signal[analyte] = noise_despike(f.signal[analyte].to_numpy())

    if pool_specs:
        synthesize_pooled_channels(files, pool_specs, isotope_table=isotope_table_resolved)

    reference_channels = select_reference_channels(files, top_n=reference_channel_top_n)

    def _override_window(f: LineFileData) -> tuple[BackgroundWindow, AblationWindow] | tuple[None, None]:
        """Resolve the manual background window for one file, if any.

        Parameters
        ----------
        f : LineFileData
            The file to window.

        Returns
        -------
        tuple[BackgroundWindow, AblationWindow] or tuple[None, None]
            Explicit windows from the per-file or global override, or
            ``(None, None)`` when neither applies (auto-detect).
        """
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

    # Session-level background drift: standards AND samples both contribute,
    # minus any labels the caller explicitly held out of the fit (their
    # blanks are still corrected below using the model fit from the rest).
    drift_fit_backgrounds = [
        b for b in initial_backgrounds if b.file_meta.label not in session_drift_exclude_labels
    ]
    session_background_drift = fit_session_background_drift(
        drift_fit_backgrounds or initial_backgrounds,
        order=background_drift_order, method=background_drift_method, max_order=max_order,
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
        "session_drift_exclude_labels": sorted(session_drift_exclude_labels),
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
            calibrated_ppm, grid_index, deconvolution_provenance = _build_calibrated_ppm_and_grid(
                pairs, None, instrument_settings, multi_result=multi_result, standard_results=standard_results,
                deconvolution_settings=deconvolution_settings, ablation_onset_trim_s=ablation_onset_trim_s,
            )
        else:
            calibrated_ppm, grid_index, deconvolution_provenance = _build_calibrated_ppm_and_grid(
                pairs, standard_results[chosen_standards[0]], instrument_settings,
                deconvolution_settings=deconvolution_settings, ablation_onset_trim_s=ablation_onset_trim_s,
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
            deconvolution_provenance=deconvolution_provenance,
            deconvolution_settings=deconvolution_settings,
            ablation_onset_trim_s=ablation_onset_trim_s,
            isotope_share_specs=list(isotope_share_specs),
        )

    return results


def apply_deconvolution(
    results: dict[str, SampleCalibratedResult],
    deconvolution_settings: DeconvolutionSettings,
    *,
    isotope_table: pd.DataFrame | str | Path | None = None,
) -> dict[str, SampleCalibratedResult]:
    """Re-derive each sample's calibrated ppm with deconvolution applied.

    The standalone "deconvolution" workflow stage: :func:`run` produces a
    calibration from the plain background-corrected signal (no
    deconvolution), the user QCs it, then this recomputes ``calibrated_ppm``
    / ``grid_index`` / ``isotopic_ppm`` for every sample with
    :func:`src.deconvolution.pipeline.correct_line` applied first, reusing
    the already-fitted background, drift, standard, and bias state on each
    result unchanged.

    Parameters
    ----------
    results : dict[str, SampleCalibratedResult]
        Output of :func:`run` / :func:`run_from_parsed`. Mutated in place
        and also returned.
    deconvolution_settings : DeconvolutionSettings
        Shift / washout configuration to apply. Both flags off makes this a
        no-op that restores the Stage-1 values.
    isotope_table : pandas.DataFrame or str or pathlib.Path or None, optional
        Natural-abundance table for isotope apportionment. Defaults to
        :data:`DEFAULT_ISOTOPE_TABLE_PATH`.

    Returns
    -------
    dict[str, SampleCalibratedResult]
        The same ``results`` dict, with each entry's ``calibrated_ppm``,
        ``grid_index``, ``deconvolution_provenance``,
        ``deconvolution_settings``, ``isotopic_ppm``,
        ``isotopic_ppm_provenance``, and the ``deconvolution`` entries of
        ``qc_report`` refreshed. ``calibration``/``classification_categories``
        are cleared (the ppm they were computed from has changed).

    Notes
    -----
    Always recomputes from ``result.backgrounds``' untouched
    ``background_corrected_signal``, so it is idempotent and safe to re-run
    after changing the settings. Isotope *ratios* (``calibrated_ratios``)
    are unaffected -- they are computed directly from the
    background-corrected signal, not the deconvolved one, at every stage.
    """
    isotope_table_resolved = isotope_table if isotope_table is not None else DEFAULT_ISOTOPE_TABLE_PATH

    for result in results.values():
        pairs = list(zip(result.files, result.backgrounds))
        multi_result = result.multi_standard_calibration
        if multi_result is not None:
            standard_result = None
        else:
            primary = (result.provenance.get("primary_standards") or [None])[0]
            standard_result = result.standard_results.get(primary)
            if standard_result is None:
                continue

        calibrated_ppm, grid_index, deconvolution_provenance = _build_calibrated_ppm_and_grid(
            pairs, standard_result, result.instrument_settings,
            multi_result=multi_result, standard_results=result.standard_results,
            deconvolution_settings=deconvolution_settings,
            ablation_onset_trim_s=result.ablation_onset_trim_s,
        )
        isotopic_ppm, isotopic_ppm_provenance = _build_isotopic_ppm(
            calibrated_ppm, result.calibrated_ratios, result.isotope_share_specs,
            isotope_table=isotope_table_resolved,
        )

        result.calibrated_ppm = calibrated_ppm
        result.grid_index = grid_index
        result.deconvolution_provenance = deconvolution_provenance
        result.deconvolution_settings = deconvolution_settings
        result.isotopic_ppm = isotopic_ppm
        result.isotopic_ppm_provenance = isotopic_ppm_provenance
        result.qc_report["deconvolution"] = {
            "apply_shift": deconvolution_settings.apply_shift,
            "apply_washout": deconvolution_settings.apply_washout,
            "n_lines": len(deconvolution_provenance),
        }
        if isotopic_ppm_provenance:
            result.qc_report["isotopic_ppm"] = isotopic_ppm_provenance
        result.provenance["deconvolution_settings"] = asdict(deconvolution_settings)
        # The calibrated ppm these were computed from has changed.
        result.classification = pd.DataFrame()
        result.classification_categories = []

    return results


def run_from_parsed(
    files: list[LineFileData],
    sample_dir: str | Path,
    reference_library: dict[str, ReferenceMaterial],
    excluded_files: set[str] | None = None,
    **kwargs,
) -> dict[str, SampleCalibratedResult]:
    """Run the pipeline from already-parsed files instead of reading from disk.

    Parameters
    ----------
    files : list[LineFileData]
        Already-parsed raw files (e.g. ``dock_widgets.py``'s
        ``self._scanned_files``). Each ``meta.is_standard`` must already be
        correct for the current UI selection -- this function never calls
        ``parse_line_file`` and so cannot re-apply a ``standard_names``
        criterion.
    sample_dir : str or pathlib.Path
        Provenance/error-message label only; no file I/O.
    reference_library : dict[str, ReferenceMaterial]
        Certified compositions keyed by standard label.
    excluded_files : set[str] or None, optional
        Filenames (matched by ``f.meta.path.name``) dropped before
        processing.
    **kwargs
        Every other :func:`run`/:func:`_run_from_files` parameter; see
        :func:`run` for descriptions.

    Returns
    -------
    dict[str, SampleCalibratedResult]
        One entry per non-standard sample label.

    Raises
    ------
    PipelineError
        If all provided files were excluded, or the primary standard is
        ambiguous.

    Notes
    -----
    Every ``LineFileData.meta.is_standard`` must already correctly reflect
    which labels are standards under the *current* UI selection -- unlike
    ``run()``, this function never calls ``parse_line_file`` itself, so it
    has no ``standard_names`` criterion to (re)apply. A cache populated by
    ``dock_widgets.py:_on_scan`` does NOT already satisfy this (see that
    method's docstring) and must be corrected by the caller first (see
    ``dock_widgets.py:_on_reprocess``).

    ``excluded_files`` is applied here (matched by ``f.meta.path.name``),
    same semantics as ``run()``'s pre-parse filtering. ``**kwargs`` accepts
    every other ``run()``/``_run_from_files`` parameter (drift_order,
    instrument_settings, deconvolution_settings, ablation_onset_trim_s,
    etc.) -- not re-listed here to avoid the two signatures drifting out of
    sync; see ``run()``'s docstring for what each one does.
    """
    excluded_files = excluded_files or set()
    files = [f for f in files if f.meta.path.name not in excluded_files]
    if not files:
        raise PipelineError("All provided files were excluded via excluded_files.")
    return _run_from_files(
        files=files, sample_dir=sample_dir, reference_library=reference_library,
        excluded_files=excluded_files, **kwargs,
    )

def gather_session_line_files(session_dir: str | Path) -> list[Path]:
    """Collect raw line files from a session folder and its immediate subfolders.

    Parameters
    ----------
    session_dir : str or pathlib.Path
        The session directory.

    Returns
    -------
    list[pathlib.Path]
        Every ``"<label> - <N>.csv"`` file directly in ``session_dir`` plus
        those one level down in each subfolder, de-duplicated by resolved
        path and sorted by name. Non-matching files and deeper nesting are
        ignored.

    Notes
    -----
    This is what lets :func:`run` treat a session laid out as
    ``session/N610/``, ``session/GSD/``, ``session/RM01/`` … (standards and
    samples each in their own subfolder) as one pooled run. A flat session
    folder with every file loose still works -- the subfolder scan simply
    adds nothing.
    """
    session_dir = Path(session_dir)
    seen: set[Path] = set()
    ordered: list[Path] = []
    dirs = [session_dir]
    if session_dir.is_dir():
        dirs += [p for p in sorted(session_dir.iterdir()) if p.is_dir()]
    for d in dirs:
        for p in list_line_files(d):
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                ordered.append(p)
    return sorted(ordered, key=lambda p: p.name)


def discover_sample_directories(parent_dir: str | Path) -> list[Path]:
    """Find sample subfolders under a parent directory.

    Parameters
    ----------
    parent_dir : str or pathlib.Path
        Directory whose immediate subfolders are inspected.

    Returns
    -------
    list[pathlib.Path]
        Subfolders (sorted) containing at least one file matching the raw
        ``"<label> - <N>.csv"`` pattern.
    """
    parent_dir = Path(parent_dir)
    return [child for child in sorted(p for p in parent_dir.iterdir() if p.is_dir()) if list_line_files(child)]


def run_batch(
    parent_dir: str | Path,
    standard_names: Iterable[str] | Callable[[str], bool],
    reference_library: dict[str, ReferenceMaterial],
    **kwargs,
) -> dict[str, dict[str, SampleCalibratedResult]]:
    """Run :func:`run` independently over every discovered sample subfolder.

    Parameters
    ----------
    parent_dir : str or pathlib.Path
        Directory holding one sample subfolder per session (see
        :func:`discover_sample_directories`).
    standard_names : Iterable[str] or Callable[[str], bool]
        Which filename labels are reference standards.
    reference_library : dict[str, ReferenceMaterial]
        Certified compositions keyed by standard label.
    **kwargs
        Forwarded to each :func:`run` call.

    Returns
    -------
    dict[str, dict[str, SampleCalibratedResult]]
        ``subfolder name -> {sample label -> result}``. Each result's
        provenance records ``standards_shared_across_folders=False`` and the
        batch parent directory.

    Notes
    -----
    Standards are not shared across folders -- each subfolder brackets and
    calibrates its own samples, matching real multi-sample sessions.
    """
    results: dict[str, dict[str, SampleCalibratedResult]] = {}
    for sample_dir in discover_sample_directories(parent_dir):
        folder_results = run(sample_dir, standard_names, reference_library, **kwargs)
        for sample_result in folder_results.values():
            sample_result.provenance["standards_shared_across_folders"] = False
            sample_result.provenance["batch_parent_dir"] = str(parent_dir)
        results[sample_dir.name] = folder_results
    return results
