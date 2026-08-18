"""Gas-blank window auto-detection and per-file background correction.

No in-file marker separates the gas blank from the ablation signal -- the
transition is an abrupt (typically >1000x) step in counts-per-second on
whichever analytes are abundant in the ablated material. Detection works on
a single robust reference channel (built from a session-wide list of
high-abundance analytes, or the sum of every analyte column as a fallback)
via a simple windowed mean-shift statistic in log space.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from src.calibration.counts import cps_to_counts, resolve_tau
from src.calibration.currie import CurrieLimits, compute_currie_limits
from src.calibration.drift import (
    DriftFit,
    DriftFitError,
    DriftFitLike,
    fit_polynomial,
    select_drift_fit,
    select_order_by_aic,
)
from src.calibration.lod import compute_lod
from src.calibration.poisson_drift import PoissonFitError, detect_poisson_file_outliers
from src.calibration.rawfile import LineFileData, LineFileMeta


@dataclass
class BackgroundWindow:
    start_idx: int
    end_idx: int              # exclusive
    start_time: datetime
    end_time: datetime
    method: str                # "changepoint_median_channel" | "fallback_fixed_window" | "manual_override"
    reference_channel: str      # channel(s) used for detection, or fallback reason


@dataclass
class AblationWindow:
    start_idx: int
    end_idx: int               # exclusive
    start_time: datetime
    end_time: datetime
    # Edge-trimmed region used for STATISTICS (standards.assemble_occurrences'
    # mean_signal/sem_signal) -- start_idx/end_idx above (and everything raw/
    # background+drift/calibrated maps display) stay the full span regardless.
    # None (the default at every construction site in this module) means "no
    # trim", normalized to start_idx/end_idx in __post_init__ -- see
    # apply_edge_trim() for how a nonzero trim gets applied.
    included_start_idx: int | None = None
    included_end_idx: int | None = None
    # Per-row keep/reject mask over [included_start_idx, included_end_idx),
    # keyed per analyte -- from a low-order-fit outlier check (see
    # detect_row_outliers) run on *that analyte's own* signal, not a shared
    # reference channel: an ablation-interval anomaly (e.g. hitting a
    # micro-inclusion of a different mineral mid-line) can be
    # compositionally specific to one trace element and invisible in the
    # major elements typically used as reference channels -- same reasoning
    # as the background window's per-analyte screen (see
    # BackgroundResult.background_row_outlier_mask). Unlike
    # included_start_idx/included_end_idx (a single contiguous trim), this
    # can flag any subset of rows (e.g. a short leading ramp on a standard
    # glass, without a manually-specified trim duration). An analyte is
    # omitted only when there weren't enough rows to attempt detection.
    row_outlier_mask: dict[str, np.ndarray] = field(default_factory=dict)

    def __post_init__(self):
        if self.included_start_idx is None:
            self.included_start_idx = self.start_idx
        if self.included_end_idx is None:
            self.included_end_idx = self.end_idx


@dataclass
class BackgroundResult:
    file_meta: LineFileMeta
    window: BackgroundWindow
    ablation: AblationWindow
    background_mean: dict[str, float]
    background_std: dict[str, float]
    background_n: dict[str, int]
    lod: dict[str, float]
    ablation_signal: pd.DataFrame
    background_corrected_signal: pd.DataFrame
    background_correction_method: str  # "naive_per_file_constant" | "session_drift_aware"
    # Poisson-statistics additions (poisson_background_spec.md) -- additive
    # alongside the Gaussian mean/std/lod fields above, which stay computed
    # exactly as before for existing consumers (diagnostics.plot_background_drift,
    # etc.). All four are keyed per analyte, since count recovery is a
    # per-analyte decision (a major element's quantization is invisible, a
    # trace element's usually isn't, even within the same file).
    background_counts: dict[str, float | None] = field(default_factory=dict)   # recovered total integer counts
    background_tau_s: dict[str, float | None] = field(default_factory=dict)     # per-reading counting time (s)
    tau_provenance: dict[str, str] = field(default_factory=dict)                 # "metadata"|"inferred"|"bounded"|"unknown"
    currie: dict[str, CurrieLimits] = field(default_factory=dict)                  # detection limits; key omitted
                                                                                     # per analyte when tau unknown
    # Per-row keep/reject mask over [window.start_idx, window.end_idx),
    # keyed per analyte -- from a median-centered outlier check (see
    # detect_row_outliers, order=0) run on *that analyte's own* signal, not
    # a shared reference channel: a contamination event (a stray mineral
    # inclusion, an instrument glitch) can be compositionally specific to
    # one trace element and invisible in the major elements typically used
    # as reference channels (confirmed against real data -- a lone
    # ablation-level Eu153 spike with no corresponding elevation in the
    # session's reference channels). Catches the spike before it can skew
    # that analyte's background_mean/background_std/background_counts.
    # An analyte is omitted only when there weren't enough rows to attempt
    # detection (see detect_row_outliers's own minimum-points guard).
    background_row_outlier_mask: dict[str, np.ndarray] = field(default_factory=dict)


def _to_datetime(x) -> datetime:
    return pd.Timestamp(x).to_pydatetime()


def _total_signal(signal: pd.DataFrame, channels: list[str] | None) -> np.ndarray:
    cols = [c for c in (channels or []) if c in signal.columns]
    if not cols:
        cols = list(signal.columns)
    return signal[cols].sum(axis=1).to_numpy()


def select_reference_channels(
    files: list[LineFileData], top_n: int = 5, n_rows: int = 5, min_fold_change: float = 500.0
) -> list[str]:
    """Analytes with the largest session-wide ablation signal, used as the
    background-detection reference channel(s), restricted to channels that
    actually respond to the ablation onset.

    Two single-criterion approaches were tried against real instrument data
    and both mis-selected channels that made changepoint detection unreliable:

    - Ranking by raw early-row magnitude alone picks channels that are
      already elevated *during the gas blank itself* (observed on real
      data: Na, from instrument memory/contamination) -- high magnitude,
      but its fold-change onto ablation is small (~a few hundred x, vs
      tens-of-thousands x for a true matrix element), diluting the real
      step in a summed series.
    - Ranking by fold-change alone favors near-zero-background trace
      channels whose "background" is mostly discretization noise around
      zero counts -- a stray nonzero blip produces a spurious, enormous
      fold-change ratio despite the channel being too weak/noisy for a
      clean, sharply-localized step (this measurably made real-data
      changepoint detection worse, not better).

    So: first discard channels whose fold-change (peak / early-row baseline)
    falls below ``min_fold_change`` -- excluding low-responsiveness
    "contamination-like" channels -- then rank the survivors by raw peak
    magnitude, which favors genuinely abundant matrix elements over noisy
    low-abundance trace channels. Verified against a real 124-file LA-ICP-MS
    session: this combination detected a clean step in every file, where
    either single-criterion approach left roughly a third to two-thirds
    falling back to a fixed window.
    """
    baselines: dict[str, list[float]] = {}
    peaks: dict[str, list[float]] = {}
    for f in files:
        head = f.signal.iloc[: min(n_rows, len(f.signal))]
        for col in f.signal.columns:
            baselines.setdefault(col, []).append(max(float(head[col].median()), 1.0))
            peaks.setdefault(col, []).append(float(f.signal[col].max()))

    median_baseline = {c: float(np.median(v)) for c, v in baselines.items()}
    median_peak = {c: float(np.median(v)) for c, v in peaks.items()}
    fold_change = {c: median_peak[c] / median_baseline[c] for c in median_peak}

    candidates = [c for c in median_peak if fold_change[c] >= min_fold_change] or list(median_peak)
    ranked = sorted(candidates, key=lambda c: -median_peak[c])
    return ranked[:top_n]


def _fallback_window(
    line_data: LineFileData, fallback_n_rows: int, reason: str
) -> tuple[BackgroundWindow, AblationWindow]:
    n = line_data.n_rows
    end_idx = min(max(1, fallback_n_rows), max(1, n - 1))
    window = BackgroundWindow(
        start_idx=0, end_idx=end_idx,
        start_time=_to_datetime(line_data.absolute_time[0]),
        end_time=_to_datetime(line_data.absolute_time[end_idx - 1]),
        method="fallback_fixed_window", reference_channel=reason,
    )
    ablation = AblationWindow(
        start_idx=end_idx, end_idx=n,
        start_time=_to_datetime(line_data.absolute_time[min(end_idx, n - 1)]),
        end_time=_to_datetime(line_data.absolute_time[-1]),
    )
    return window, ablation


def detect_background_window(
    line_data: LineFileData,
    reference_channels: list[str] | None = None,
    window: int = 10,
    threshold_ratio: float = 100.0,
    fallback_n_rows: int = 20,
    search_margin: int = 5,
    tail_margin: int = 20,
    eps: float = 1.0,
) -> tuple[BackgroundWindow, AblationWindow]:
    """Locate the gas-blank -> ablation step change in ``line_data``.

    Method: sum the reference channel(s) into one robust series, then scan
    left to right for the *first* index where the trailing-window median
    jumps by at least ``threshold_ratio`` over the leading-window median.

    Deliberately the first qualifying jump, not the single largest one over
    the whole file: an early version of this function picked whichever jump
    maximized the step statistic anywhere in the file, and on real data that
    sometimes locked onto a *later*, larger jump -- a secondary
    material-domain transition partway through the ablation itself -- rather
    than the true (typically smaller) blank-to-ablation transition at the
    start, misclassifying most of the file as "background". Since a gas
    blank always precedes ablation and never recurs mid-file, the first
    sustained jump clearing the threshold is the one that's actually wanted.
    If no candidate clears ``threshold_ratio`` anywhere, this falls back to a
    fixed-width window from the start of the file and marks
    ``method="fallback_fixed_window"`` so downstream QC can flag it rather
    than silently using a wrong window.
    """
    n = line_data.n_rows
    total = _total_signal(line_data.signal, reference_channels)

    w = max(1, window)
    lo = max(search_margin, w)
    hi = n - max(tail_margin, w)
    if hi <= lo:
        return _fallback_window(line_data, fallback_n_rows, "too_short_for_detection")

    chosen_idx = None
    chosen_before_med = None
    for k in range(lo, hi):
        before = total[max(0, k - w):k]
        after = total[k:k + w]
        if len(before) == 0 or len(after) == 0:
            continue
        before_med = float(np.median(before))
        # The low end (20th percentile), not the median, of the *after*
        # window -- a window straddling the true transition (partly
        # background, partly ablation) would already show an inflated
        # median once roughly half its rows are past the step, triggering
        # several rows too early. Requiring most of the window to be
        # elevated only starts triggering once the window has genuinely
        # moved past the transition.
        after_low = float(np.percentile(after, 20))
        if before_med <= 0:
            continue
        if after_low / max(before_med, eps) >= threshold_ratio:
            chosen_idx = k
            chosen_before_med = before_med
            break

    if chosen_idx is None:
        return _fallback_window(line_data, fallback_n_rows, "below_threshold_ratio")

    # The coarse scan above only locates the *window* (of width w) where the
    # transition happens, not the exact row -- it triggers once ~80% of the
    # forward window is elevated, which is often still one or two rows past
    # the true step, since a window can qualify while its first row or two
    # (right at chosen_idx) are still legitimately at background level. That
    # under-counted the tail of the gas blank on real data. Refine forward
    # from chosen_idx to the first row whose own value already clears the
    # threshold -- guaranteed to exist within [chosen_idx, chosen_idx + w),
    # since after_low (a value at/below at least 80% of the window) already
    # cleared it.
    per_row_threshold = threshold_ratio * max(chosen_before_med, eps)
    best_idx = chosen_idx
    for j in range(chosen_idx, min(chosen_idx + w, n)):
        if total[j] >= per_row_threshold:
            best_idx = j
            break

    reference_channel = ",".join(reference_channels) if reference_channels else "all_channels_sum"
    bg_window = BackgroundWindow(
        start_idx=0, end_idx=best_idx,
        start_time=_to_datetime(line_data.absolute_time[0]),
        end_time=_to_datetime(line_data.absolute_time[best_idx - 1]),
        method="changepoint_median_channel", reference_channel=reference_channel,
    )
    ablation = AblationWindow(
        start_idx=best_idx, end_idx=n,
        start_time=_to_datetime(line_data.absolute_time[best_idx]),
        end_time=_to_datetime(line_data.absolute_time[-1]),
    )
    return bg_window, ablation


def _window_midpoint(window: BackgroundWindow) -> datetime:
    return window.start_time + (window.end_time - window.start_time) / 2


def fit_session_background_drift(
    backgrounds: list[BackgroundResult], order: int = 1, method: str = "fixed", max_order: int = 3,
) -> dict[str, DriftFitLike]:
    """Fit a per-analyte polynomial to background level vs time, across every file in the session.

    Background applies to every file (standards and samples both have a gas
    blank), so this should be called on the full session's `BackgroundResult`
    list, not just the standards'. An analyte with no data at all is simply
    omitted, and callers fall back to the naive per-file-constant correction
    for it.

    ``method``:

    - ``"fixed"`` (default): ordinary-least-squares fit at ``order``, falling
      back to a lower order per analyte (down to 0) when there are too few
      background measurements to fit it stably (fewer than ``order + 2``
      points) -- the original behavior of this function.
    - ``"auto_aic"``: :func:`~src.calibration.drift.select_order_by_aic` over
      ``0..max_order`` on the Gaussian background means.
    - ``"auto_poisson_lrt"``: Poisson GLM + likelihood-ratio-test order
      selection (see poisson_background_spec.md) on each file's recovered
      integer background counts, using files where that analyte's
      ``tau_provenance`` isn't ``"unknown"`` (a merely ``"bounded"`` tau
      still contributes -- conservative but valid). Before fitting, whole
      *files* whose recovered count is grossly inconsistent with a single
      common rate shared by the rest of the session are excluded (see
      :func:`~src.calibration.poisson_drift.detect_poisson_file_outliers`)
      -- this is a session-wide, per-file screen, distinct from
      ``compute_background_result``'s per-*row*, per-file screen: a file
      whose entire background window is uniformly elevated (no internal
      row-to-row anomaly for that screen to catch) can otherwise dominate
      the fitted rate on its own when most of the session reads near zero.
      If too few files have usable counts (or the Poisson fit fails
      outright), that analyte falls back to ``"auto_aic"`` on the Gaussian
      means instead -- the returned dict can be `isinstance()`-checked
      (:class:`PoissonDriftFit` vs :class:`DriftFit`) to see which analytes
      actually used the Poisson path.
    """
    if not backgrounds:
        return {}
    analytes = list(backgrounds[0].background_mean.keys())

    fits: dict[str, DriftFitLike] = {}
    for analyte in analytes:
        usable = [b for b in backgrounds if analyte in b.background_mean]
        if not usable:
            continue
        fit_times = [_window_midpoint(b.window) for b in usable]
        values = [b.background_mean[analyte] for b in usable]

        if method == "auto_poisson_lrt":
            poisson_usable = [
                b for b in usable
                if b.tau_provenance.get(analyte, "unknown") != "unknown"
                and b.background_counts.get(analyte) is not None
                and b.background_tau_s.get(analyte) is not None
            ]
            if len(poisson_usable) >= 2:
                p_times_all = [_window_midpoint(b.window) for b in poisson_usable]
                p_counts_all = np.array([b.background_counts[analyte] for b in poisson_usable])
                p_tau_all = np.array([b.background_tau_s[analyte] * b.background_n[analyte] for b in poisson_usable])
                file_outliers = detect_poisson_file_outliers(p_counts_all, p_tau_all)
                keep = ~file_outliers
                p_times = [t for t, k in zip(p_times_all, keep) if k]
                p_counts = p_counts_all[keep]
                p_tau = p_tau_all[keep]
                try:
                    fits[analyte] = select_drift_fit(
                        p_times, None, counts=p_counts, tau_s=p_tau,
                        method="auto_poisson_lrt", max_order=max_order, analyte=analyte,
                    )
                    continue
                except PoissonFitError:
                    pass  # fall through to the Gaussian/AIC fallback below
            try:
                fits[analyte] = select_order_by_aic(fit_times, values, max_order=max_order, analyte=analyte)
            except DriftFitError:
                continue
        elif method == "auto_aic":
            try:
                fits[analyte] = select_order_by_aic(fit_times, values, max_order=max_order, analyte=analyte)
            except DriftFitError:
                continue
        else:  # "fixed"
            eff_order = order
            while eff_order > 0 and len(values) < eff_order + 2:
                eff_order -= 1
            try:
                fits[analyte] = fit_polynomial(fit_times, values, order=eff_order, analyte=analyte)
            except DriftFitError:
                continue
    return fits


def compute_background_result(
    line_data: LineFileData,
    window: BackgroundWindow | None = None,
    ablation: AblationWindow | None = None,
    reference_channels: list[str] | None = None,
    detection_kwargs: dict | None = None,
    session_background_drift: dict[str, DriftFitLike] | None = None,
    dwell_time_ms: float | None = None,
    sweeps_per_reading: int | None = None,
    manual_row_exclusions: dict[str, set[int]] | None = None,
) -> BackgroundResult:
    """Background stats, LOD, and background-corrected ablation signal.

    If ``window``/``ablation`` aren't supplied, they're auto-detected via
    :func:`detect_background_window`. If ``session_background_drift`` (from
    :func:`fit_session_background_drift`) is supplied, each ablation sweep is
    corrected using the session-level drift curve evaluated at that sweep's
    own absolute time, per analyte -- not the single per-file background
    mean -- so a background level that drifts across the session is tracked
    continuously rather than treated as a per-file constant. Analytes with no
    session fit (or when ``session_background_drift`` is omitted entirely)
    fall back to the simple per-file-constant subtraction.

    ``dwell_time_ms``/``sweeps_per_reading`` (from
    ``geometry.InstrumentSettings``, when the user has entered them) give
    every analyte ``tau_provenance="metadata"``; otherwise each analyte's
    counting time is estimated independently from its own background-window
    CPS values (see ``counts.resolve_tau``) -- this drives the additive
    Poisson-statistics fields (``background_counts``, ``background_tau_s``,
    ``tau_provenance``, ``currie``).

    Before any of that, each analyte's own background-window rows are
    screened for outliers (a contamination spike during blank acquisition
    -- a stray particle, an instrument glitch) via :func:`detect_row_outliers`
    (``order=0``, median-centered -- appropriate here since a gas blank is
    expected genuinely flat within one file, unlike an ablation interval).
    This is done **per analyte**, not with one shared mask: a
    contamination event can be compositionally specific to a single trace
    element (e.g. a mineral inclusion rich in one rare-earth element) and
    completely invisible in the major elements typically used as reference
    channels for window detection -- confirmed against real data, where a
    lone Eu153 spike orders of magnitude above its blank level had no
    corresponding elevation in any reference channel. ``background_mean``
    is computed from each analyte's own *clean* rows, and -- since this is
    fundamentally counting-statistics data -- as a Poisson rate (total
    recovered counts / total clean counting time) rather than a plain
    arithmetic CPS average, whenever the counting time is resolvable;
    falling back to the arithmetic mean of the clean rows only when it
    isn't (``tau_provenance == "unknown"``). ``background_std``/
    ``background_n`` are likewise per-analyte, computed from that
    analyte's own clean rows. The exclusion masks are attached
    (``BackgroundResult.background_row_outlier_mask``, keyed per analyte)
    so they're visible in the time-series viewer (see ``classify_rows``),
    not a silent correction.

    ``manual_row_exclusions`` (analyte -> set of absolute row indices into
    ``line_data.signal``, i.e. directly comparable to ``window.start_idx``)
    are user-specified exclusions from the Time Series viewer's click/drag
    masking -- unioned into each analyte's automatic ``row_outlier_mask``
    before computing statistics, so a manually-dropped row is excluded the
    same way an automatically-detected one is. Kept as a separate input
    (not merged into the automatic screen's own logic) so a user's choice
    survives being re-Run without the automatic detector silently
    re-including or second-guessing it.
    """
    if window is None or ablation is None:
        window, ablation = detect_background_window(
            line_data, reference_channels=reference_channels, **(detection_kwargs or {})
        )

    bg_signal = line_data.signal.iloc[window.start_idx:window.end_idx]

    background_mean: dict[str, float] = {}
    background_std: dict[str, float] = {}
    background_n: dict[str, int] = {}
    background_row_outlier_mask: dict[str, np.ndarray] = {}
    background_counts: dict[str, float | None] = {}
    background_tau_s: dict[str, float | None] = {}
    tau_provenance: dict[str, str] = {}
    currie_limits: dict[str, CurrieLimits] = {}
    for analyte in bg_signal.columns:
        analyte_cps_full = bg_signal[analyte].to_numpy()
        row_outlier_mask = detect_row_outliers(analyte_cps_full, order=0)
        clean_cps = analyte_cps_full[~row_outlier_mask]
        if clean_cps.size == 0:
            # Degenerate case (every row flagged) -- don't trust the
            # screen for this analyte, fall back to the full, unfiltered
            # window rather than reporting statistics over zero rows.
            row_outlier_mask = np.zeros(len(analyte_cps_full), dtype=bool)
            clean_cps = analyte_cps_full

        manual = (manual_row_exclusions or {}).get(analyte, ())
        if manual:
            for abs_idx in manual:
                if window.start_idx <= abs_idx < window.end_idx:
                    row_outlier_mask[abs_idx - window.start_idx] = True
            clean_cps = analyte_cps_full[~row_outlier_mask]
        background_row_outlier_mask[analyte] = row_outlier_mask

        n_clean = int(clean_cps.size)
        background_n[analyte] = n_clean
        background_std[analyte] = float(np.std(clean_cps, ddof=1)) if n_clean > 1 else 0.0

        tau_estimate = resolve_tau(clean_cps, dwell_time_ms, sweeps_per_reading)
        tau_provenance[analyte] = tau_estimate.provenance
        background_tau_s[analyte] = tau_estimate.tau_s
        counts_arr = cps_to_counts(clean_cps, tau_estimate)
        total_counts = float(np.sum(counts_arr)) if counts_arr is not None else None
        background_counts[analyte] = total_counts

        if total_counts is not None and n_clean > 0:
            background_mean[analyte] = total_counts / (tau_estimate.tau_s * n_clean)
        else:
            background_mean[analyte] = float(np.mean(clean_cps)) if n_clean > 0 else 0.0

        if tau_estimate.tau_s is not None:
            mu_b_counts = max(background_mean[analyte] * tau_estimate.tau_s, 0.0)
            currie_limits[analyte] = compute_currie_limits(mu_b_counts, tau_estimate.tau_s)

    lod_values = compute_lod(background_mean, background_std)

    ablation_signal = line_data.signal.iloc[ablation.start_idx:ablation.end_idx].reset_index(drop=True)
    ablation_time = line_data.absolute_time[ablation.start_idx:ablation.end_idx]

    if session_background_drift:
        used_drift = False
        corrected_cols = {}
        for analyte in ablation_signal.columns:
            fit = session_background_drift.get(analyte)
            if fit is not None:
                predicted_bg = fit.predict(ablation_time)
                corrected_cols[analyte] = ablation_signal[analyte].to_numpy() - predicted_bg
                used_drift = True
            else:
                corrected_cols[analyte] = ablation_signal[analyte].to_numpy() - background_mean[analyte]
        corrected = pd.DataFrame(corrected_cols, index=ablation_signal.index)
        method_used = "session_drift_aware" if used_drift else "naive_per_file_constant"
    else:
        corrected = (ablation_signal - pd.Series(background_mean)).reset_index(drop=True)
        method_used = "naive_per_file_constant"

    return BackgroundResult(
        file_meta=line_data.meta, window=window, ablation=ablation,
        background_mean=background_mean, background_std=background_std, background_n=background_n,
        lod=lod_values, ablation_signal=ablation_signal, background_corrected_signal=corrected,
        background_correction_method=method_used,
        background_counts=background_counts, background_tau_s=background_tau_s,
        tau_provenance=tau_provenance, currie=currie_limits,
        background_row_outlier_mask=background_row_outlier_mask,
    )


def recompute_from_window(
    line_data: LineFileData,
    start_idx: int,
    end_idx: int,
    reference_channels: list[str] | None = None,
    session_background_drift: dict[str, DriftFitLike] | None = None,
    dwell_time_ms: float | None = None,
    sweeps_per_reading: int | None = None,
) -> BackgroundResult:
    """Recompute a :class:`BackgroundResult` for GUI-overridden window bounds.

    Marks ``window.method = "manual_override"`` so it's visibly distinct from
    an auto-detected window in diagnostics/QC output.
    """
    n = line_data.n_rows
    window = BackgroundWindow(
        start_idx=start_idx, end_idx=end_idx,
        start_time=_to_datetime(line_data.absolute_time[start_idx]),
        end_time=_to_datetime(line_data.absolute_time[end_idx - 1]),
        method="manual_override",
        reference_channel=",".join(reference_channels) if reference_channels else "manual",
    )
    ablation = AblationWindow(
        start_idx=end_idx, end_idx=n,
        start_time=_to_datetime(line_data.absolute_time[min(end_idx, n - 1)]),
        end_time=_to_datetime(line_data.absolute_time[-1]),
    )
    return compute_background_result(
        line_data, window=window, ablation=ablation, session_background_drift=session_background_drift,
        dwell_time_ms=dwell_time_ms, sweeps_per_reading=sweeps_per_reading,
    )


@dataclass
class BackgroundWindowOverride:
    """Manual gas-blank/edge-trim settings, expressed relative to each
    line's own start (not absolute per-file times) -- the gas blank's timing
    is expected to be consistent across a whole session (e.g. to exclude
    mounting-epoxy contamination measured right after the true gas blank),
    so a single override applies uniformly to every file rather than needing
    per-file entries. See ``pipeline.run()``'s ``background_override``
    (global) and ``per_file_overrides`` (per-file escape hatch, keyed by
    filename, taking precedence over the global override for that file).
    """
    start_offset_s: float | None = None    # seconds from line start (Time [Sec]); None -> 0
    end_offset_s: float | None = None       # seconds from line start; None -> same as start (empty background)
    edge_trim_lead_s: float = 0.0            # trims the *statistics* region (see apply_edge_trim), not the display
    edge_trim_trail_s: float = 0.0


def window_from_override(
    line_data: LineFileData, override: BackgroundWindowOverride
) -> tuple[BackgroundWindow, AblationWindow]:
    """Builds explicit background/ablation windows from a manual time-offset
    override instead of running changepoint detection.

    ``start_offset_s``/``end_offset_s`` select the background window as
    seconds from the line's own start (against ``line_data.time_s``, not
    absolute time). If ``edge_trim_lead_s``/``edge_trim_trail_s`` are
    nonzero, the resulting ablation window is additionally edge-trimmed (see
    :func:`apply_edge_trim`) for excluding a standard glass's leading/
    trailing edge-effect ramp from calibration statistics.
    """
    n = line_data.n_rows
    start_idx = (
        int(np.searchsorted(line_data.time_s, override.start_offset_s))
        if override.start_offset_s is not None else 0
    )
    end_idx = (
        int(np.searchsorted(line_data.time_s, override.end_offset_s))
        if override.end_offset_s is not None else start_idx
    )
    start_idx = max(0, min(start_idx, n - 2))
    end_idx = max(start_idx + 1, min(end_idx, n - 1))

    window = BackgroundWindow(
        start_idx=start_idx, end_idx=end_idx,
        start_time=_to_datetime(line_data.absolute_time[start_idx]),
        end_time=_to_datetime(line_data.absolute_time[end_idx - 1]),
        method="manual_override", reference_channel="manual",
    )
    ablation = AblationWindow(
        start_idx=end_idx, end_idx=n,
        start_time=_to_datetime(line_data.absolute_time[end_idx]),
        end_time=_to_datetime(line_data.absolute_time[-1]),
    )
    if override.edge_trim_lead_s or override.edge_trim_trail_s:
        ablation = apply_edge_trim(ablation, line_data, override.edge_trim_lead_s, override.edge_trim_trail_s)
    return window, ablation


def apply_edge_trim(
    ablation: AblationWindow, line_data: LineFileData, lead_s: float, trail_s: float
) -> AblationWindow:
    """Returns a copy of ``ablation`` with ``included_start_idx``/``included_end_idx``
    narrowed to exclude ``lead_s`` seconds from the start and ``trail_s``
    seconds from the end of the ablation window -- e.g. for excluding a
    standard glass's edge-effect ramp (a leading/trailing rise or fall in
    counts, rather than the ordinary flat plateau) from the statistics used
    for calibration (``standards.assemble_occurrences``). ``start_idx``/
    ``end_idx`` (and everything raw/background+drift/calibrated maps
    display) are untouched -- only the *included* (statistics) region shrinks.
    """
    abl_time_s = line_data.time_s[ablation.start_idx:ablation.end_idx]
    if len(abl_time_s) == 0:
        return ablation

    rel_time = abl_time_s - abl_time_s[0]
    total_span = float(abl_time_s[-1] - abl_time_s[0])

    lead_count = int(np.searchsorted(rel_time, lead_s)) if lead_s > 0 else 0
    if trail_s > 0:
        trail_cutoff = total_span - trail_s
        trail_count = len(rel_time) - int(np.searchsorted(rel_time, trail_cutoff))
    else:
        trail_count = 0

    included_start_idx = ablation.start_idx + lead_count
    included_end_idx = ablation.end_idx - trail_count
    # Never let the trim collapse the included region to empty/negative width.
    included_start_idx = min(included_start_idx, ablation.end_idx - 1)
    included_end_idx = max(included_end_idx, included_start_idx + 1)
    included_end_idx = min(included_end_idx, ablation.end_idx)

    return dataclasses.replace(ablation, included_start_idx=included_start_idx, included_end_idx=included_end_idx)


def detect_row_outliers(
    values: np.ndarray, order: int = 1, threshold: float = 5.0, provisional_threshold: float = 2.5,
) -> np.ndarray:
    """Row-level outlier detection: fits a low-order polynomial (default
    order 1, i.e. linear) vs. row index, then flags rows whose residual
    against that fit is a robust (MAD-based) outlier -- catches a short
    edge-effect ramp on a standard glass, or an isolated spike/dropout,
    automatically, without a manually-specified trim duration.

    ``order=0`` is a dedicated, simpler single-pass path: it centers on the
    **median** of the rows, not a mean/polyfit-based fit. The median is
    already robust (50% breakdown point) to however many outliers are in
    the minority, so there's no need for the two-pass provisional/refit
    dance below (built specifically to compensate for a *mean*-based
    center's fragility) -- an outlier can't drag the median toward itself
    the way it could a mean.

    The order=0 path also screens **only the nonzero rows** against each
    other, leaving every exactly-zero row untouched. A near-zero-count
    background window is genuinely zero-inflated Poisson data: zero is the
    single most common value by a wide margin, and a lone real 1- or
    2-count event (one or two quantization steps above zero) is completely
    ordinary Poisson variability, not an anomaly -- but comparing it to a
    median/MAD built from a population that's mostly exact zeros made it
    look like a huge, many-MAD-units outlier (regression, caught on real
    data: a channel reading zero on ~110 of 116 files had its rare genuine
    1-2-count files flagged and stripped, corrupting that channel's
    session-level background rate upward instead of leaving it near zero).
    Restricting the screen to nonzero rows only compares real counts
    against other real counts, where a true contamination event (orders of
    magnitude larger than any other observed count) still stands out, while
    ordinary sparse low counts no longer look anomalous just for not being
    zero. Needs at least 4 nonzero rows to attempt this (mirrors the
    module's general minimum-points convention); with fewer, nothing is
    flagged -- not enough information to distinguish a genuine rare count
    from contamination.

    ``order >= 1`` still needs the polynomial two-pass approach, since a
    median doesn't generalize to a trend line. A first version of the
    order-1 path used ``order=0`` (fit the mean) universally and failed on
    real ablation data with any genuine within-window trend -- a mean fit
    badly underfits real signal drift, so residuals (and the MAD scale
    computed from them) get dominated by that systematic error instead of
    the actual anomaly. ``order=1`` fixes that by tracking the trend
    itself, but introduces a different, well-known problem: a single global
    fit *to all the rows, ramp included* lets the ramp partially drag the
    fitted slope toward itself ("masking"), diluting its own residuals.

    Fixed with a two-pass robust refit:

    1. Fit order ``order`` to every row, compute residuals, and flag rows
       whose residual clears a *loose* ``provisional_threshold`` (2.5) --
       loose on purpose, to catch every plausible outlier candidate even if
       masking has partly hidden it, rather than trying to get the final
       answer in one pass.
    2. Refit **excluding** those provisional rows, so they can no longer
       influence the fit at all, then recompute every row's residual
       (including the provisional ones) against this cleaner fit and apply
       the real (stricter) ``threshold`` (5.0) for the final answer.

    Verified against: a short 3-row ramp on an otherwise flat plateau (all
    3 correctly isolated, nothing else flagged); a realistic standard-
    occurrence-scale decaying curve (order=1 tracks the genuine trend, zero
    false positives) with an injected mid-window dropout cluster (exactly
    those rows isolated); a false-positive-rate Monte Carlo against flat
    synthetic data (zero false positives across 100 trials at
    threshold=5.0, at the 40-row scale typical of one standard occurrence);
    and, for the order=0 median path, a near-zero background-window scale
    (~25-30 rows) with one or two injected contamination spikes (isolated
    exactly, with a false-positive rate under 1% across 100 flat-data trials).

    Returns a boolean array the length of ``values`` (``True`` = outlier).
    Requires at least ``order + 4`` points; with fewer, nothing is flagged.
    """
    n = len(values)
    values = np.asarray(values, dtype=float)
    if n < order + 4:
        return np.zeros(n, dtype=bool)

    if order == 0:
        nonzero_idx = np.flatnonzero(values != 0)
        if nonzero_idx.size < 4:
            return np.zeros(n, dtype=bool)
        nz = values[nonzero_idx]
        med = float(np.median(nz))
        resid = nz - med
        mad = float(np.median(np.abs(resid)))
        if mad == 0:
            # Degenerate but possible when several nonzero rows share the
            # same count level -- MAD is then 0 regardless of how extreme a
            # minority of the *other* nonzero rows are, which would
            # otherwise silently disable outlier detection in exactly the
            # scenario it matters most for. Fall back to the mean absolute
            # deviation from the median: still centered on the robust
            # median, just averaged instead of medianed, so a minority of
            # extreme rows still produces a nonzero scale.
            mad = float(np.mean(np.abs(resid)))
            if mad == 0:
                return np.zeros(n, dtype=bool)
        z = 0.6745 * resid / mad
        out = np.zeros(n, dtype=bool)
        out[nonzero_idx] = np.abs(z) > threshold
        return out

    x = np.arange(n, dtype=float)
    x -= x.mean()

    def _fitted(idx: np.ndarray) -> np.ndarray:
        coeffs = np.polyfit(x[idx], values[idx], order)
        return np.polyval(coeffs, x)

    fitted1 = _fitted(np.arange(n))
    resid1 = values - fitted1
    med1 = float(np.median(resid1))
    mad1 = float(np.median(np.abs(resid1 - med1)))
    if mad1 == 0:
        return np.zeros(n, dtype=bool)
    z1 = 0.6745 * (resid1 - med1) / mad1
    provisional = np.abs(z1) > provisional_threshold

    clean_idx = np.where(~provisional)[0]
    if provisional.all() or len(clean_idx) < order + 2:
        return np.abs(z1) > threshold

    fitted2 = _fitted(clean_idx)
    resid2 = values - fitted2
    med2 = float(np.median(resid2[clean_idx]))
    mad2 = float(np.median(np.abs(resid2[clean_idx] - med2)))
    if mad2 == 0:
        return provisional
    z2 = 0.6745 * (resid2 - med2) / mad2
    return np.abs(z2) > threshold


def classify_rows(
    line_data: LineFileData, background: BackgroundResult | None, analyte: str | None = None,
    is_outlier: bool = False, manual_row_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Per-row role for every sweep in ``line_data``: ``"background"``,
    ``"excluded"``, or ``"included"``.

    ``"excluded"`` covers rows inside the ablation window but outside its
    edge-trimmed included region (``AblationWindow.included_start_idx``/
    ``included_end_idx`` -- see :func:`apply_edge_trim`), plus any
    individual row within the included region flagged by
    :func:`detect_row_outliers` for ``analyte`` specifically
    (``AblationWindow.row_outlier_mask``, keyed per analyte and attached by
    ``standards.assemble_occurrences``), plus any row within the
    *background* window flagged the same way for ``analyte``
    (``BackgroundResult.background_row_outlier_mask``, keyed per analyte
    and attached by ``compute_background_result``) -- both screens are
    per-analyte, not a shared reference channel, since a contamination
    event (blank or mid-ablation) can be compositionally specific to one
    trace element and invisible in the major elements a reference channel
    would be based on; with none of these applied, no rows fall in this
    category. ``analyte`` is needed for both per-analyte lookups -- pass
    ``None`` (the default) to skip them and show every ablation/background
    row using only the coarser included-region/window boundaries.
    Used by the time-series viewer to color points by role, consistently
    between standard and sample lines (see ``diagnostics.plot_time_series``).

    ``is_outlier`` marks the *entire* included region as ``"outlier"``
    instead of ``"included"``/``"excluded"`` -- set this when the whole
    occurrence this line represents was dropped from its analyte's drift
    fit/calibration factor by ``standards._mad_outlier_mask`` (see
    ``StandardCalibrationResult.excluded_outliers``), so statistical outlier
    rejection is visible in the time-series viewer, not just in the
    accuracy-table's outlier count. This takes precedence over
    ``row_outlier_mask`` -- once a whole occurrence is excluded, the
    finer-grained per-row distinction no longer matters.

    ``manual_row_mask`` (a boolean array the length of ``line_data.signal``,
    caller-supplied -- GUI session state from click/drag point masking, not
    stored on ``BackgroundResult``) marks rows as ``"manual"``, taking
    precedence over everything else including ``is_outlier``: a user's
    explicit choice should always be visible as itself, not folded into an
    automatic role. Works even when ``background`` is ``None`` (pre-Run),
    for instant visual feedback on a click before the next pipeline Run
    actually recomputes statistics with the exclusion applied (see
    ``compute_background_result``'s/``assemble_occurrences``'s own
    ``manual_row_exclusions`` parameter for that computational side).

    Returns an array of role strings, one per row of ``line_data.signal``. If
    ``background`` is ``None`` (no pipeline run yet -- a pre-Run raw preview),
    every row is ``"unclassified"`` (before ``manual_row_mask`` is applied).
    """
    n = line_data.n_rows
    if background is None:
        roles = np.full(n, "unclassified", dtype=object)
    else:
        roles = np.full(n, "background", dtype=object)
        window = background.window
        win_lo, win_hi = window.start_idx, window.end_idx
        bg_mask = background.background_row_outlier_mask.get(analyte) if analyte is not None else None
        if bg_mask is not None and len(bg_mask) == win_hi - win_lo:
            background_roles = np.where(np.asarray(bg_mask), "excluded", "background")
            roles[win_lo:win_hi] = background_roles

        ablation = background.ablation
        roles[ablation.start_idx:ablation.end_idx] = "excluded"
        lo, hi = ablation.included_start_idx, ablation.included_end_idx
        ablation_mask = ablation.row_outlier_mask.get(analyte) if analyte is not None else None
        if is_outlier:
            roles[lo:hi] = "outlier"
        elif ablation_mask is not None and len(ablation_mask) == hi - lo:
            included_roles = np.where(np.asarray(ablation_mask), "excluded", "included")
            roles[lo:hi] = included_roles
        else:
            roles[lo:hi] = "included"

    if manual_row_mask is not None and len(manual_row_mask) == n:
        roles[np.asarray(manual_row_mask)] = "manual"
    return roles
