"""Diagnostic figures and QC tables.

Every plotting function takes a pre-built ``matplotlib.axes.Axes`` and draws
into it (no ``plt.figure()``/``plt.show()`` calls), so both a headless script
(``fig.savefig(...)``) and the GUI (``SimpleMplCanvas.axes``) reuse the same
code. No PyQt imports anywhere in this module.
"""
from __future__ import annotations

import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

from src.calibration.background import BackgroundResult, classify_rows
from src.calibration.dating_ratios import DatingRatioFit, resolve_dating_ratio_truth
from src.calibration.drift import DriftFit
from src.calibration.massbias import BiasFit, DEFAULT_ISOTOPE_TABLE_PATH, resolve_truth_ratio
from src.calibration.rawfile import LineFileData
from src.calibration.standards import CalibrationCurve, StandardCalibrationResult

# Fixed role -> color mapping, shared between standard and sample lines (role
# drives color, not line identity) -- see plot_time_series.
# "unclassified" (pre-Run, no BackgroundResult yet) intentionally matches
# "included"'s color -- a pre-Run raw preview should look like ordinary
# "normal" data, not visually distinct/muted, so it's directly viewable
# before a calibration Run completes. "manual" (a user's click/drag point
# exclusion from the Time Series/Standards QC viewers) is kept visually
# distinct from every automatic role -- this is the default ("light_gray")
# display; callers can instead omit it entirely via each function's
# ``mask_display="hidden"`` option (see plot_time_series/
# plot_standard_vs_reference).
ROLE_COLORS = {
    "background": "tab:green",
    "excluded": "tab:red",
    "included": "tab:blue",
    "outlier": "tab:orange",
    "unclassified": "tab:blue",
    "manual": "lightgray",
}


# Per-label color cycle for plot_background_drift -- matplotlib's default
# "tab10" palette, cycled deterministically by sorted label so color
# assignment is stable across redraws (not dependent on rcParams/axes
# state). Distinct from the drift-fit line's own color (black), so the fit
# never visually collides with a same-colored label's points.
_LABEL_COLOR_CYCLE = [
    "tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple",
    "tab:brown", "tab:pink", "tab:gray", "tab:olive", "tab:cyan",
]


def plot_background_drift(
    ax, groups: dict[str, list[BackgroundResult]], drift_fit: DriftFit | None, analyte: str,
    reference_labels: set[str] | None = None,
) -> None:
    """Background level vs time (mean ± SE per file), combined across every
    sample AND reference-standard label in one plot, with the session
    drift fit overlaid.

    ``groups`` is label -> that label's own ``BackgroundResult`` list
    (samples and reference standards mixed together -- e.g. one sample
    label's files plus every standard label's occurrence backgrounds).
    ``reference_labels`` (a subset of ``groups``' keys) marks which labels
    are reference standards, drawn as circles; every other label is a
    sample, drawn as squares. Each label gets its own color (cycled from
    :data:`_LABEL_COLOR_CYCLE`, stable by sorted label order) so different
    samples/standards stay visually distinguishable even when both share a
    marker shape.
    """
    reference_labels = reference_labels or set()
    all_times: list = []
    for i, label in enumerate(sorted(groups)):
        results = groups[label]
        if not results:
            continue
        ordered = sorted(results, key=lambda b: b.file_meta.acquired_at)
        times = [b.window.start_time + (b.window.end_time - b.window.start_time) / 2 for b in ordered]
        means = [b.background_mean.get(analyte, np.nan) for b in ordered]
        ns = [max(b.background_n.get(analyte, 1), 1) for b in ordered]
        stds = [b.background_std.get(analyte, 0.0) for b in ordered]
        sems = [s / np.sqrt(n) for s, n in zip(stds, ns)]

        is_reference = label in reference_labels
        color = _LABEL_COLOR_CYCLE[i % len(_LABEL_COLOR_CYCLE)]
        marker = "o" if is_reference else "s"
        role = "reference" if is_reference else "sample"
        ax.errorbar(
            times, means, yerr=sems, fmt=marker, color=color, markersize=5, capsize=2,
            label=f"{label} ({role})",
        )
        all_times.extend(times)

    if not all_times:
        ax.set_title(f"{analyte}: no data")
        return

    if drift_fit is not None:
        curve_times = pd.date_range(min(all_times), max(all_times), periods=100)
        ax.plot(curve_times, drift_fit.predict(curve_times), "--", color="black",
                 label=f"drift fit (order {drift_fit.order})")
    ax.set_xlabel("Time")
    ax.set_ylabel(f"{analyte} background (CPS)")
    ax.set_title(f"Background drift: {analyte}")
    ax.legend(loc="best", fontsize="small")


def plot_standard_vs_reference(
    ax, standard_result: StandardCalibrationResult, analyte: str, ax_cps=None,
    manually_excluded_override: set[int] | None = None, mask_display: str = "light_gray",
) -> pd.DataFrame:
    """Back-calculated standard ppm vs time (filled markers, left/primary
    axis), against the reference value ± uncertainty band, with the
    session's raw background-corrected CPS overlaid as open markers on a
    secondary axis (``ax_cps`` -- created via ``ax.twinx()`` if not
    supplied; callers reusing the same Axes across redraws should pass
    their own persistent twin, since ``ax.twinx()`` creates a new Axes
    every call).

    A point flagged by the accuracy QC test (``AccuracyRow.flagged`` --
    its measured-vs-reference difference exceeded the accuracy threshold)
    is drawn in red instead of its usual fit/holdout-group color; a point
    excluded via manual click/drag masking (``AccuracyRow.
    manually_excluded``, or ``manually_excluded_override`` -- an
    occurrence_order set forcing this color even before a Run recomputes
    that field, for instant visual feedback right after a click) takes
    precedence over the flagged color. This replaces an earlier version
    that overlaid a red "*" annotation on flagged points instead of
    recoloring them.

    ``mask_display`` controls how a manually-excluded point is drawn:
    ``"light_gray"`` (default) or ``"hidden"`` (dropped from both the ppm
    and its mirrored cps point entirely). Either way, masked points are
    still included in the returned point-index DataFrame with
    ``manually_excluded=True`` -- hiding is purely visual, click/drag
    hit-testing still works at a hidden point's (unchanged) data location
    so it can be un-masked again.

    Returns a DataFrame (columns: ``occurrence_order, analyte, x, y,
    series, group, flagged, manually_excluded``, one row per rendered
    point across both the ppm and cps series) for hit-testing click/drag
    point-masking interactions against -- see ``dock_widgets``'s canvas
    wiring. Empty (but present) when there's no data to plot.
    """
    point_columns = ["occurrence_order", "analyte", "x", "y", "series", "group", "flagged", "manually_excluded"]
    rows = [r for r in standard_result.accuracy_table if r.analyte == analyte]
    if standard_result.holdout_accuracy_table:
        rows += [r for r in standard_result.holdout_accuracy_table if r.analyte == analyte]
    point_rows: list[dict] = []
    if not rows:
        ax.set_title(f"{analyte}: no data")
        return pd.DataFrame(point_rows, columns=point_columns)
    rows = sorted(rows, key=lambda r: r.occurrence_order)
    manually_excluded_override = manually_excluded_override or set()

    if ax_cps is None:
        ax_cps = ax.twinx()

    signal_by_order = {o.occurrence_order: o.mean_signal.get(analyte) for o in standard_result.occurrences}

    def _is_masked(r) -> bool:
        return bool(r.manually_excluded or r.occurrence_order in manually_excluded_override)

    def _point_color(r, default_color: str) -> str:
        if _is_masked(r):
            return "lightgray"
        if r.flagged:
            return "tab:red"
        return default_color

    fit_rows = [r for r in rows if r.group in ("fit", "all")]
    holdout_rows = [r for r in rows if r.group == "holdout"]

    for group_rows, default_color, marker, group_label in (
        (fit_rows, "tab:blue", "o", "fit occurrences"), (holdout_rows, "tab:green", "s", "holdout occurrences"),
    ):
        if not group_rows:
            continue
        drawable = [r for r in group_rows if mask_display != "hidden" or not _is_masked(r)]
        if drawable:
            times = [r.time for r in drawable]
            values = [r.observed_value for r in drawable]
            colors = [_point_color(r, default_color) for r in drawable]
            ax.errorbar(times, values, yerr=[r.observed_se for r in drawable], fmt="none", ecolor=default_color, capsize=3, zorder=2)
            ax.scatter(times, values, c=colors, marker=marker, label=group_label, zorder=3)
        for r in group_rows:
            point_rows.append({
                "occurrence_order": r.occurrence_order, "analyte": analyte, "x": r.time, "y": r.observed_value,
                "series": "ppm", "group": r.group, "flagged": r.flagged, "manually_excluded": _is_masked(r),
            })

        cps_source = [r for r in drawable if signal_by_order.get(r.occurrence_order) is not None]
        cps_times = [r.time for r in cps_source]
        cps_values = [signal_by_order[r.occurrence_order] for r in cps_source]
        if cps_times:
            ax_cps.scatter(cps_times, cps_values, facecolors="none", edgecolors=default_color, marker=marker, zorder=1)
        for r in group_rows:
            cps_val = signal_by_order.get(r.occurrence_order)
            if cps_val is not None:
                point_rows.append({
                    "occurrence_order": r.occurrence_order, "analyte": analyte, "x": r.time, "y": cps_val,
                    "series": "cps", "group": r.group, "flagged": r.flagged, "manually_excluded": False,
                })

    ref_value = rows[0].reference_value
    ref_unc = rows[0].reference_uncertainty
    ax.axhline(ref_value, color="tab:red", linestyle="--", label="reference value")
    if ref_unc:
        ax.axhspan(ref_value - ref_unc, ref_value + ref_unc, color="tab:red", alpha=0.15)

    ax.set_xlabel("Time")
    ax.set_ylabel(f"{analyte} (ppm, filled)")
    ax_cps.set_ylabel(f"{analyte} (CPS, open)")
    ax.set_title(f"Standard vs reference: {analyte} (offset from {ref_value:g})")
    ax.legend(loc="best", fontsize="small")

    return pd.DataFrame(point_rows, columns=point_columns)


def plot_standard_qc_series(ax_cps, ax_ppm, standard_result: StandardCalibrationResult, analyte: str) -> None:
    """Raw/background-corrected CPS and corrected ppm across the session, one
    point per standard occurrence -- used when more than one standard
    measurement exists to QC drift over the whole session."""
    occurrences = sorted(standard_result.occurrences, key=lambda o: o.occurrence_order)
    orders = [o.occurrence_order for o in occurrences]
    cps = [o.mean_signal.get(analyte, np.nan) for o in occurrences]
    fit_orders = {o.occurrence_order for o in occurrences if not standard_result.split_enabled or o.occurrence_order % 2 == 1}

    colors = ["tab:blue" if order in fit_orders else "tab:green" for order in orders]
    ax_cps.scatter(orders, cps, c=colors)
    ax_cps.set_xlabel("Standard occurrence")
    ax_cps.set_ylabel(f"{analyte} (CPS, background-corrected)")
    ax_cps.set_title(f"{analyte}: CPS across session")

    rows = sorted(
        [r for r in standard_result.accuracy_table if r.analyte == analyte]
        + ([r for r in standard_result.holdout_accuracy_table if r.analyte == analyte] if standard_result.holdout_accuracy_table else []),
        key=lambda r: r.occurrence_order,
    )
    if rows:
        ppm_colors = ["tab:blue" if r.group in ("fit", "all") else "tab:green" for r in rows]
        ax_ppm.scatter([r.occurrence_order for r in rows], [r.observed_value for r in rows], c=ppm_colors)
        ax_ppm.axhline(rows[0].reference_value, color="tab:red", linestyle="--")
    ax_ppm.set_xlabel("Standard occurrence")
    ax_ppm.set_ylabel(f"{analyte} (ppm, calibrated)")
    ax_ppm.set_title(f"{analyte}: corrected ppm across session")


def plot_multi_point_calibration(ax, curve: CalibrationCurve, analyte: str) -> None:
    """CPS-vs-ppm calibration curve for one analyte across every primary
    standard that contributed to it (see
    ``standards.combine_primary_standards``) -- one point per standard,
    labeled by name, with the fitted line drawn across the observed CPS
    range. Only meaningful for ``method="multi_point_linear"`` (2+ primary
    standards); called with a ``"single_point_ratio"`` curve it still
    draws the single point and the (origin-forced) line through it, just
    without a meaningful R².
    """
    if not curve.points:
        ax.set_title(f"{analyte}: no calibration points")
        return

    labels = [p[0] for p in curve.points]
    cps = np.array([p[1] for p in curve.points], dtype=float)
    ppm = np.array([p[2] for p in curve.points], dtype=float)

    ax.scatter(cps, ppm, color="tab:blue", zorder=3)
    for label, x, y in zip(labels, cps, ppm):
        ax.annotate(f" {label}", (x, y), fontsize=8, va="center", ha="left")

    x_lo = min(0.0, float(np.min(cps)))
    x_hi = float(np.max(cps)) * 1.05 if np.max(cps) > 0 else 1.0
    line_x = np.linspace(x_lo, x_hi, 100)
    line_y = curve.slope * line_x + curve.intercept
    ax.plot(line_x, line_y, "-", color="tab:orange", zorder=2)

    r2_text = f", R²={curve.r_squared:.4f}" if curve.r_squared is not None else ""
    ax.set_xlabel(f"{analyte} (CPS, drift-fit mean)")
    ax.set_ylabel(f"{analyte} (ppm, reference)")
    ax.set_title(
        f"{analyte}: calibration curve ({curve.method}, n={curve.n_points})\n"
        f"slope={curve.slope:.4g}, intercept={curve.intercept:.4g}{r2_text}"
    )


def plot_bias_fit(
    ax, bias_fit: BiasFit, standard_results: dict[str, StandardCalibrationResult],
    isotope_table=DEFAULT_ISOTOPE_TABLE_PATH,
) -> None:
    """Mass-bias QC view (see ``massbias.py``): each bracketing-standard
    occurrence's own measured-ratio-over-truth (a value near 1.0 means no
    bias at that point in the session), colored per label, against the
    fitted bias curve -- the mass-bias counterpart to
    ``plot_standard_vs_reference``.

    Recomputes each occurrence's point the same way
    ``massbias.fit_bias_curve`` did internally (``BiasFit`` itself doesn't
    retain the raw per-occurrence points, only the fitted curve), so
    ``standard_results`` must be the same dict the fit was produced from.
    """
    numerator = f"{bias_fit.element}{bias_fit.numerator_mass}"
    denominator = f"{bias_fit.element}{bias_fit.denominator_mass}"

    times: list = []
    ratios: list[float] = []
    labels: list[str] = []
    for label in bias_fit.standard_labels:
        sr = standard_results.get(label)
        if sr is None:
            continue
        truth = resolve_truth_ratio(sr.reference, bias_fit.element, bias_fit.numerator_mass, bias_fit.denominator_mass, isotope_table)
        if truth is None:
            continue
        for occ in sr.occurrences:
            num_cps = occ.mean_signal.get(numerator)
            den_cps = occ.mean_signal.get(denominator)
            if num_cps is None or den_cps is None or den_cps == 0:
                continue
            times.append(occ.file_meta.acquired_at)
            ratios.append((num_cps / den_cps) / truth.value)
            labels.append(label)

    if not times:
        ax.set_title(f"{numerator}/{denominator}: no bias-fit data")
        return

    for i, label in enumerate(sorted(set(labels))):
        color = _LABEL_COLOR_CYCLE[i % len(_LABEL_COLOR_CYCLE)]
        xs = [t for t, l in zip(times, labels) if l == label]
        ys = [r for r, l in zip(ratios, labels) if l == label]
        ax.scatter(xs, ys, color=color, label=label, zorder=3)

    curve_times = pd.date_range(min(times), max(times), periods=100)
    ax.plot(curve_times, bias_fit.correction_factor(curve_times), "--", color="black", label="fitted bias curve")
    ax.axhline(1.0, color="gray", linestyle=":", linewidth=1)
    ax.set_xlabel("Time")
    ax.set_ylabel(f"{numerator}/{denominator}: measured / truth")
    ax.set_title(f"Mass bias: {numerator}/{denominator} (truth={bias_fit.truth.value:.4g}, {bias_fit.truth.source})")
    ax.legend(loc="best", fontsize="small")


def plot_dating_ratio_fit(
    ax, fit: DatingRatioFit, standard_results: dict[str, StandardCalibrationResult],
) -> None:
    """Cross-element dating-ratio QC view (see ``dating_ratios.py``): each
    bracketing-standard occurrence's own measured-ratio-over-truth (a
    value near 1.0 means no session drift at that point), colored per
    label, against the fitted correction curve -- the dating-ratio
    counterpart to :func:`plot_bias_fit`.

    Recomputes each occurrence's point the same way
    ``dating_ratios.fit_dating_ratio`` did internally (``DatingRatioFit``
    itself doesn't retain the raw per-occurrence points, only the fitted
    curve), so ``standard_results`` must be the same dict the fit was
    produced from.
    """
    numerator = f"{fit.numerator_element}{fit.numerator_mass}"
    denominator = f"{fit.denominator_element}{fit.denominator_mass}"

    times: list = []
    ratios: list[float] = []
    labels: list[str] = []
    for label in fit.standard_labels:
        sr = standard_results.get(label)
        if sr is None:
            continue
        truth = resolve_dating_ratio_truth(sr.reference, fit.numerator_element, fit.numerator_mass, fit.denominator_element, fit.denominator_mass)
        if truth is None:
            continue
        for occ in sr.occurrences:
            num_cps = occ.mean_signal.get(numerator)
            den_cps = occ.mean_signal.get(denominator)
            if num_cps is None or den_cps is None or den_cps == 0:
                continue
            measured = fit.numerator_scale_factor * num_cps / den_cps
            times.append(occ.file_meta.acquired_at)
            ratios.append(measured / truth.value)
            labels.append(label)

    if not times:
        ax.set_title(f"{numerator}/{denominator}: no dating-ratio-fit data")
        return

    for i, label in enumerate(sorted(set(labels))):
        color = _LABEL_COLOR_CYCLE[i % len(_LABEL_COLOR_CYCLE)]
        xs = [t for t, l in zip(times, labels) if l == label]
        ys = [r for r, l in zip(ratios, labels) if l == label]
        ax.scatter(xs, ys, color=color, label=label, zorder=3)

    curve_times = pd.date_range(min(times), max(times), periods=100)
    ax.plot(curve_times, fit.correction_factor(curve_times), "--", color="black", label="fitted correction curve")
    ax.axhline(1.0, color="gray", linestyle=":", linewidth=1)
    ax.set_xlabel("Time")
    ax.set_ylabel(f"{numerator}/{denominator}: measured / truth")
    ax.set_title(f"Dating ratio: {numerator}/{denominator} (truth={fit.truth.value:.4g}, {fit.truth.source})")
    ax.legend(loc="best", fontsize="small")


def plot_index_map(
    ax, values: pd.Series, grid_index: pd.DataFrame, title: str = "", cbar_label: str = "",
    log_scale: bool = False,
) -> None:
    """Index-based 2D map: line/file order x sweep-index-within-ablation-window.

    ``grid_index`` must carry ``line_number``/``sweep_index`` columns aligned
    with ``values``' index (see ``pipeline._build_calibrated_ppm_and_grid``).
    ``cbar_label`` names the colorbar's units (e.g. ``"CPS"`` for raw/
    background+drift stages, ``"ppm"`` for calibrated).

    ``log_scale`` switches the color mapping to :class:`~matplotlib.colors.LogNorm`
    (values <= 0, e.g. from a background-corrected stage, are masked out --
    undefined on a log scale -- rather than raising).
    """
    if values.empty or grid_index.empty:
        ax.set_title(f"{title}: no data")
        return
    n_lines = int(grid_index["line_number"].max()) + 1
    n_sweeps = int(grid_index["sweep_index"].max()) + 1
    array = np.full((n_lines, n_sweeps), np.nan)
    for (line_number, sweep_index), value in zip(
        zip(grid_index["line_number"], grid_index["sweep_index"]), values.to_numpy()
    ):
        array[int(line_number), int(sweep_index)] = value

    norm = None
    if log_scale:
        array = np.where(array > 0, array, np.nan)
        positive = array[np.isfinite(array)]
        if positive.size:
            norm = mcolors.LogNorm(vmin=positive.min(), vmax=positive.max())

    im = ax.imshow(array, aspect="auto", origin="lower", cmap="viridis", norm=norm)
    ax.set_xlabel("Sweep index (within line)")
    ax.set_ylabel("Line number")
    ax.set_title(title)
    ax.figure.colorbar(im, ax=ax, label=cbar_label)
    return im


def plot_categorical_map(
    ax, labels: pd.Series, grid_index: pd.DataFrame, category_names: list[str], title: str = "",
) -> None:
    """Index-based 2D map of a categorical field (mineral classification --
    ``src/classification/``) -- same line/sweep-index grid as
    :func:`plot_index_map`, but a discrete swatch-per-category legend
    instead of a continuous colorbar, since a category code has no
    meaningful magnitude ordering. Mirrors the generic-discrete-field path
    ``src/plotting/LamePlot.py``'s ``plot_map_mpl`` already uses for
    ``SampleObj``-backed maps (e.g. the stoichiometry dock's
    ``{abbrev}_dominant``); this app's own maps aren't ``SampleObj``-backed
    (see ``pipeline.SampleCalibratedResult``), so that generic path isn't
    reachable here and this is a standalone reimplementation of the same
    idea against this app's own ``grid_index`` grid.

    ``labels`` : per-pixel category string (or NaN/None for unclassified),
    aligned with ``grid_index``'s index. ``category_names`` fixes the
    code->color assignment (same list every redraw, e.g. the full selected
    mineral subset) so a category's color doesn't shift between redraws
    just because a different subset happened to be present in the frame.
    """
    if labels.empty or grid_index.empty or not category_names:
        ax.set_title(f"{title}: no data")
        return

    n_lines = int(grid_index["line_number"].max()) + 1
    n_sweeps = int(grid_index["sweep_index"].max()) + 1
    name_to_code = {name: i for i, name in enumerate(category_names)}
    codes = labels.map(name_to_code)  # NaN for unclassified or a name outside category_names

    array = np.full((n_lines, n_sweeps), np.nan)
    for (line_number, sweep_index), code in zip(
        zip(grid_index["line_number"], grid_index["sweep_index"]), codes.to_numpy()
    ):
        array[int(line_number), int(sweep_index)] = code

    colors = _qualitative_colors_for_diagnostics(len(category_names))
    cmap = mcolors.ListedColormap(colors).with_extremes(bad="white")  # white = unclassified pixels
    norm = mcolors.BoundaryNorm(np.arange(-0.5, len(category_names) + 0.5, 1.0), cmap.N)

    ax.imshow(np.ma.masked_invalid(array), aspect="auto", origin="lower", cmap=cmap, norm=norm)
    ax.set_xlabel("Sweep index (within line)")
    ax.set_ylabel("Line number")
    ax.set_title(title)

    from matplotlib.patches import Patch
    handles = [Patch(facecolor=colors[i], label=name) for i, name in enumerate(category_names)]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize="small", borderaxespad=0.0)


def _qualitative_colors_for_diagnostics(n: int) -> list[str]:
    """Same qualitative-colormap convention as
    ``src.stoichiometry.dock._qualitative_colors``/
    ``src.calibration.dock_widgets._qualitative_colors`` (categories have
    no natural ordering, so a perceptually-sequential colormap would
    mislead) -- reimplemented locally since this module has no PyQt/dock
    dependency to import it from.
    """
    import matplotlib.pyplot as plt

    cmap_name = "tab10" if n <= 10 else "tab20"
    cmap = plt.get_cmap(cmap_name, n)
    return [mcolors.to_hex(cmap(i)) for i in range(n)]


def cbar_label_for_stage(stage: str) -> str:
    """Colorbar unit label for a map correction stage: ppm for calibrated,
    CPS for anything still in instrument-counts-like units."""
    return "ppm" if stage == "calibrated" else "CPS"


def plot_all_stage_maps(
    fig, raw: pd.Series, background_drift_corrected: pd.Series,
    calibrated: pd.Series, grid_index: pd.DataFrame, analyte: str,
    log_scale: bool = False,
) -> None:
    """1x3 row of :func:`plot_index_map` calls, one per correction stage
    (raw / combined background+drift correction / calibrated)."""
    axes = fig.subplots(1, 3)
    stages = [
        (axes[0], raw, f"{analyte}: raw", "raw"),
        (axes[1], background_drift_corrected, f"{analyte}: background+drift correction", "background+drift correction"),
        (axes[2], calibrated, f"{analyte}: calibrated (ppm)", "calibrated"),
    ]
    for ax, values, title, stage in stages:
        plot_index_map(
            ax, values, grid_index, title=title, cbar_label=cbar_label_for_stage(stage), log_scale=log_scale,
        )
    fig.tight_layout()


def build_accuracy_table_df(accuracy_rows, excluded_outliers: dict[str, list[int]] | None = None) -> pd.DataFrame:
    """Flattens a list of :class:`~src.calibration.standards.AccuracyRow` into
    a display-ready table, with a boolean (True/False) flag column.

    ``excluded_outliers`` (``StandardCalibrationResult.excluded_outliers``),
    if given, adds an ``outliers_excluded`` column: the total number of
    fit-group occurrences dropped from that analyte's drift fit/calibration
    factor by outlier rejection (see ``standards._mad_outlier_mask``). An
    excluded occurrence still gets its own row here -- outlier rejection
    only affects the drift fit/calibration factor, not this QC table -- so
    this column is a same-value-per-analyte summary, not a per-row flag.
    """
    rows = []
    for r in accuracy_rows:
        n_outliers = len((excluded_outliers or {}).get(r.analyte, []))
        rows.append({
            "analyte": r.analyte,
            "observed": r.observed_value,
            "observed_se": r.observed_se,
            "reference": r.reference_value,
            "reference_uncertainty": r.reference_uncertainty,
            "difference": r.difference,
            "combined_uncertainty": r.combined_uncertainty,
            "stat": r.z_or_t_stat,
            "threshold": r.threshold_multiple,
            "group": r.group,
            "flag": r.flagged,
            "outliers_excluded": n_outliers,
        })
    return pd.DataFrame(rows)


def build_timing_report_df(files: list[LineFileData], backgrounds: list[BackgroundResult]) -> pd.DataFrame:
    """One row per file: acquired time, background start/end, ablation start/end."""
    by_path = {b.file_meta.path: b for b in backgrounds}
    rows = []
    for f in sorted(files, key=lambda x: x.meta.acquired_at):
        b = by_path.get(f.meta.path)
        if b is None:
            continue
        rows.append({
            "file": f.meta.path.name,
            "label": f.meta.label,
            "index": f.meta.index,
            "is_standard": f.meta.is_standard,
            "acquired_at": f.meta.acquired_at,
            "bg_start_time": b.window.start_time,
            "bg_end_time": b.window.end_time,
            "bg_method": b.window.method,
            "ablation_start_time": b.ablation.start_time,
            "ablation_end_time": b.ablation.end_time,
        })
    return pd.DataFrame(rows)


def plot_time_series(
    ax, lines: list[tuple[LineFileData, BackgroundResult | None]], analyte: str,
    offset: bool = False, offset_step: float | None = None, log_scale: bool = False,
    outlier_names: set[str] | None = None, manual_row_masks: dict[str, np.ndarray] | None = None,
    mask_display: str = "light_gray",
) -> pd.DataFrame:
    """Discrete-point (scatter, never connected) time-series view of one
    analyte across one or more lines.

    Points are colored by role -- background / excluded (edge-trim or
    manual-override exclusion) / included / outlier -- using the same colors
    (:data:`ROLE_COLORS`) whether the line is a standard or a sample, so
    color always means "role", not "which line". A sample line only ever
    shows background/included (it has no edge-trim or outlier-rejection
    concept applied to it by default), reusing the standard's own
    background/included colors. If a line has no
    :class:`~src.calibration.background.BackgroundResult` (a pre-pipeline-run
    raw preview), its points use a single neutral color instead of the
    role-based scheme (see ``background.classify_rows``).

    ``outlier_names``, if given, is the set of filenames (``path.name``)
    whose occurrence was dropped from this analyte's drift fit/calibration
    factor by statistical outlier rejection (see
    ``StandardCalibrationResult.excluded_outliers``) -- those lines' included
    region is colored ``"outlier"`` instead of ``"included"``, making outlier
    rejection visible here rather than only as a count in the accuracy table.

    When ``offset`` is True, each line's y-values are shifted by
    ``i * offset_step`` (its position in ``lines``) so multiple lines don't
    overlap, and a text label (filename) is placed at the right end of each
    line's (offset) series -- omitted when ``offset`` is False, since
    overlapping unlabeled series have no single meaningful label position.
    ``offset_step`` defaults to half the overall value range across ``lines``.

    ``log_scale`` switches the y-axis to a log scale (points at zero/negative
    counts simply don't render, per matplotlib's usual log-axis behavior).

    ``manual_row_masks`` (filename -> boolean array the length of that
    line's own signal, i.e. ``background.classify_rows``'s own
    ``manual_row_mask`` param, per line) renders a click/drag-masked row
    with the ``"manual"`` role/color, taking precedence over every
    automatic role -- works even pre-Run (see ``classify_rows``).

    ``mask_display`` controls how ``"manual"``-role (masked) points are
    drawn: ``"light_gray"`` (default, :data:`ROLE_COLORS`'s own color for
    that role) or ``"hidden"`` (not drawn at all). Either way, masked rows
    are still included in the returned point-index DataFrame with
    ``role="manual"`` -- hiding is purely visual, click/drag hit-testing
    still works at a hidden point's (unchanged) data location so it can be
    un-masked again.

    Returns a DataFrame (columns: ``filename, row_index, analyte, x, y,
    role``, one row per plotted point -- ``row_index`` is the absolute
    index into that line's own ``signal``/``absolute_time`` arrays) for
    hit-testing click/drag point-masking interactions against -- see
    ``dock_widgets``'s canvas wiring. Empty (but present) when there's no
    data to plot.
    """
    point_columns = ["filename", "row_index", "analyte", "x", "y", "role"]
    if not lines:
        ax.set_title(f"{analyte}: no data")
        return pd.DataFrame(columns=point_columns)

    outlier_names = outlier_names or set()
    manual_row_masks = manual_row_masks or {}

    if offset and offset_step is None:
        all_vals = np.concatenate([
            ld.signal[analyte].to_numpy() for ld, _ in lines if analyte in ld.signal.columns
        ])
        span = float(np.nanmax(all_vals) - np.nanmin(all_vals)) if len(all_vals) else 0.0
        offset_step = span * 0.5 if span > 0 else 1.0
    offset_step = offset_step or 0.0

    point_rows: list[dict] = []
    seen_roles: set[str] = set()
    for i, (line_data, background) in enumerate(lines):
        if analyte not in line_data.signal.columns:
            continue
        name = line_data.meta.path.name
        t = line_data.time_s
        values = line_data.signal[analyte].to_numpy().astype(float)
        is_outlier = name in outlier_names
        roles = classify_rows(
            line_data, background, analyte=analyte, is_outlier=is_outlier,
            manual_row_mask=manual_row_masks.get(name),
        )
        y = values + (i * offset_step if offset else 0.0)

        for role, color in ROLE_COLORS.items():
            mask = roles == role
            if not mask.any():
                continue
            if role == "manual" and mask_display == "hidden":
                continue  # still recorded in point_rows below, just not drawn
            ax.scatter(t[mask], y[mask], c=color, s=8, label=role if role not in seen_roles else None)
            seen_roles.add(role)

        for row_index in range(len(t)):
            point_rows.append({
                "filename": name, "row_index": row_index, "analyte": analyte,
                "x": t[row_index], "y": y[row_index], "role": roles[row_index],
            })

        if offset:
            ax.text(t[-1], y[-1], f" {line_data.meta.path.name}", va="center", ha="left", fontsize=8)

    ax.set_xlabel("Time (s, from line start)")
    ax.set_ylabel(f"{analyte} (CPS)" + (" + offset" if offset else ""))
    ax.set_title(f"{analyte}: time series ({len(lines)} line(s))")
    if log_scale:
        ax.set_yscale("log")
    if seen_roles:
        ax.legend(loc="best", fontsize="small")

    return pd.DataFrame(point_rows, columns=point_columns)
