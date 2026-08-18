"""Background-window auto-detection, LOD, and naive per-file correction.

Uses synthetic in-memory signals (not the real proprietary data) so the
injected step location is known exactly and assertions are hand-checkable.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.background import (
    BackgroundWindowOverride,
    apply_edge_trim,
    classify_rows,
    compute_background_result,
    detect_background_window,
    detect_row_outliers,
    fit_session_background_drift,
    recompute_from_window,
    select_reference_channels,
    window_from_override,
)
from src.calibration.drift import DriftFit
from src.calibration.lod import compute_lod
from src.calibration.poisson_drift import PoissonDriftFit
from src.calibration.rawfile import LineFileData, LineFileMeta


def _make_line_data_with_background(bg_values: dict, ablation_level=900000.0, ablation_n=20, seed=0,
                                     label="SYNSTD", index=1, acquired_at=None):
    """Like `_make_line_data` but lets the caller supply exact per-analyte
    background arrays (all analytes must share the same background length)."""
    acquired_at = acquired_at or datetime(2026, 3, 1, 10, 0, 0)
    bg_n = len(next(iter(bg_values.values())))
    n = bg_n + ablation_n
    dt = 0.2803
    time_s = np.round(np.arange(1, n + 1) * dt, 4)
    absolute_time = np.array([np.datetime64(acquired_at) + np.timedelta64(int(round(t * 1e6)), "us") for t in time_s])
    rng = np.random.default_rng(seed)
    signal_cols = {}
    for analyte, bg in bg_values.items():
        abl = ablation_level + rng.normal(0, max(ablation_level * 0.01, 1.0), ablation_n)
        signal_cols[analyte] = np.concatenate([np.asarray(bg, dtype=float), abl])
    signal = pd.DataFrame(signal_cols)
    meta = LineFileMeta(
        path=Path(f"{label} - {index}.csv"), label=label, index=index, is_standard=True,
        acquired_at=acquired_at, batch="Test.b",
    )
    return LineFileData(
        meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=list(bg_values.keys()),
        signal=signal, dt_s=dt, n_rows=n,
    )


def _make_line_data(bg_n=40, ablation_n=60, bg_level=500.0, ablation_level=900000.0, seed=0, label="SYNSTD", index=1):
    rng = np.random.default_rng(seed)
    n = bg_n + ablation_n
    dt = 0.2803
    time_s = np.round(np.arange(1, n + 1) * dt, 4)
    acquired_at = datetime(2026, 3, 1, 10, 0, 0)
    absolute_time = np.array([np.datetime64(acquired_at) + np.timedelta64(int(round(t * 1e6)), "us") for t in time_s])

    bg = bg_level + rng.normal(0, bg_level * 0.05, bg_n)
    abl = ablation_level + rng.normal(0, ablation_level * 0.02, ablation_n)
    al27 = np.concatenate([bg, abl])
    ca43 = al27 * 0.7

    signal = pd.DataFrame({"Al27": al27, "Ca43": ca43})
    meta = LineFileMeta(
        path=Path(f"{label} - {index}.csv"), label=label, index=index, is_standard=True,
        acquired_at=acquired_at, batch="Test.b",
    )
    return LineFileData(
        meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=["Al27", "Ca43"],
        signal=signal, dt_s=dt, n_rows=n,
    ), bg_n


def test_detect_background_window_locates_injected_step():
    line_data, true_bg_n = _make_line_data(bg_n=40, ablation_n=60)
    window, ablation = detect_background_window(line_data, reference_channels=["Al27"])

    assert window.method == "changepoint_median_channel"
    # A hard step (no ramp) should be located exactly, not just within a
    # tolerance -- see the refinement step in detect_background_window and
    # test_detect_background_window_refines_past_coarse_window_edge below
    # for the case (a gradual ramp) a plain tolerance was masking.
    assert window.end_idx == true_bg_n
    assert ablation.start_idx == window.end_idx
    assert ablation.end_idx == line_data.n_rows


def test_detect_background_window_refines_past_coarse_window_edge():
    """Regression test: a gradual ramp (not an instant step) between blank
    and ablation used to get the coarse scan's window-left-edge as the
    boundary, which could still be one or two genuinely blank-level rows
    -- undercounting the tail of the gas blank on real data. The refinement
    step should walk forward to the row that's actually elevated."""
    acquired_at = datetime(2026, 3, 1, 10, 0, 0)
    rng = np.random.default_rng(0)
    blank = rng.normal(50, 10, 20).clip(min=0)
    ramp = np.linspace(50, 100000, 5)
    plateau = rng.normal(100000, 500, 15)
    total = np.concatenate([blank, ramp, plateau])
    n = len(total)
    dt_s = 0.28
    time_s = np.arange(n) * dt_s
    absolute_time = np.array([
        np.datetime64(acquired_at) + np.timedelta64(int(t * 1e6), "us") for t in time_s
    ])
    signal = pd.DataFrame({"Al27": total})
    meta = LineFileMeta(
        path=Path("RAMP - 1.csv"), label="RAMP", index=1, is_standard=False,
        acquired_at=acquired_at, batch="Test.b",
    )
    line_data = LineFileData(
        meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=["Al27"],
        signal=signal, dt_s=dt_s, n_rows=n,
    )

    window, ablation = detect_background_window(line_data, reference_channels=["Al27"])

    # Rows 19-20 are still blank-level (~44, ~50) even though they fall
    # inside the coarse scan's forward-looking window -- they must land in
    # the background window, not get swept into ablation.
    assert window.end_idx >= 21
    assert ablation.start_idx == window.end_idx
    # And the boundary shouldn't run away past the actual ramp either.
    assert window.end_idx <= 24


def test_detect_background_window_falls_back_when_no_step_present():
    # Flat noise throughout -- no ablation step at all.
    line_data, _ = _make_line_data(bg_n=50, ablation_n=0, ablation_level=0.0)
    # Force a flat, no-step series by using only background-level noise for the whole file.
    rng = np.random.default_rng(1)
    flat = 500.0 + rng.normal(0, 25, line_data.n_rows)
    line_data.signal["Al27"] = flat
    line_data.signal["Ca43"] = flat * 0.7

    window, ablation = detect_background_window(line_data, reference_channels=["Al27"], fallback_n_rows=15)
    assert window.method == "fallback_fixed_window"
    assert window.end_idx == 15
    assert ablation.start_idx == 15


def test_select_reference_channels_excludes_low_fold_change_channel():
    # Ca43 mimics a real-data quirk (instrument memory/contamination, e.g.
    # Na): a high, roughly-constant level in the gas blank itself, so its
    # early-row magnitude towers over Al27's -- but it barely responds to
    # ablation (~3x), while Al27's background jumps ~1800x once ablation
    # starts. A channel below the fold-change floor must never be selected,
    # regardless of its raw magnitude -- it doesn't distinguish blank from
    # ablation, which is exactly what select_reference_channels is for.
    line_data, _ = _make_line_data(bg_n=10, ablation_n=10, bg_level=500.0, ablation_level=900000.0, seed=2)
    rng = np.random.default_rng(4)
    line_data.signal["Ca43"] = np.concatenate([
        5000.0 + rng.normal(0, 50, 10),
        15000.0 + rng.normal(0, 100, 10),
    ])

    channels = select_reference_channels([line_data], top_n=2)
    assert channels == ["Al27"]  # Ca43 fails the fold-change floor, so it's dropped even with room for 2


def test_select_reference_channels_ranks_qualified_candidates_by_peak_magnitude():
    # Both channels clear the fold-change floor (Al27 ~1800x, Mg24 ~50000x --
    # Mg24's fold-change is actually larger), but Al27 has the bigger raw
    # peak (900000 vs 50000). Ranking survivors by peak magnitude (not by
    # fold-change) must put Al27 first -- this is the real-data-motivated
    # behavior: prefer genuinely abundant matrix elements over lower-
    # abundance channels just because their fold-change ratio is larger.
    line_data, _ = _make_line_data(bg_n=10, ablation_n=10, bg_level=500.0, ablation_level=900000.0, seed=2)
    rng = np.random.default_rng(6)
    line_data.signal["Ca43"] = np.concatenate([
        1.0 + rng.normal(0, 0.1, 10),
        50000.0 + rng.normal(0, 100, 10),
    ]).clip(min=0)

    channels = select_reference_channels([line_data], top_n=2)
    assert channels == ["Al27", "Ca43"]


def test_compute_lod_is_mean_plus_3sd():
    bg_mean = {"Al27": 500.0, "Ca43": 350.0}
    bg_std = {"Al27": 10.0, "Ca43": 5.0}
    lod = compute_lod(bg_mean, bg_std)
    assert lod["Al27"] == pytest.approx(530.0)
    assert lod["Ca43"] == pytest.approx(365.0)


def test_compute_background_result_naive_correction():
    line_data, true_bg_n = _make_line_data(bg_n=40, ablation_n=60, bg_level=500.0, ablation_level=900000.0, seed=5)
    result = compute_background_result(line_data, reference_channels=["Al27"])

    assert result.background_n["Al27"] == pytest.approx(true_bg_n, abs=2)
    assert result.background_correction_method == "naive_per_file_constant"
    # Corrected ablation signal should equal raw ablation minus the scalar background mean.
    expected = result.ablation_signal["Al27"] - result.background_mean["Al27"]
    assert np.allclose(result.background_corrected_signal["Al27"].to_numpy(), expected.to_numpy())
    assert result.lod["Al27"] == pytest.approx(result.background_mean["Al27"] + 3 * result.background_std["Al27"])


def test_compute_background_result_manual_row_exclusions_union_with_automatic_mask():
    """A manually-excluded row (Time Series click/drag masking) must be
    dropped from background_mean/background_n exactly like an
    automatically-detected outlier, and show up in
    background_row_outlier_mask so classify_rows can render it -- while a
    different analyte in the same file, given no manual exclusion, is
    unaffected."""
    line_data, true_bg_n = _make_line_data(bg_n=40, ablation_n=60, bg_level=500.0, ablation_level=900000.0, seed=5)
    manual_idx = 5
    result_plain = compute_background_result(line_data, reference_channels=["Al27"])
    result_manual = compute_background_result(
        line_data, reference_channels=["Al27"], manual_row_exclusions={"Al27": {manual_idx}},
    )

    assert result_manual.background_row_outlier_mask["Al27"][manual_idx]
    assert result_manual.background_n["Al27"] == result_plain.background_n["Al27"] - 1
    # Ca43 got no manual exclusion -- unaffected.
    assert not result_manual.background_row_outlier_mask["Ca43"][manual_idx]
    assert result_manual.background_n["Ca43"] == result_plain.background_n["Ca43"]


def test_compute_background_result_excludes_contamination_spike():
    """Regression test: a single contaminated row within the gas-blank
    window (a stray particle, an instrument glitch) must not skew
    background_mean -- it should be screened out before background_mean/
    background_std/background_counts are computed, and visible as
    "excluded" via classify_rows rather than silently absorbed."""
    true_tau = 0.2803
    rng = np.random.default_rng(9)
    counts_true = rng.poisson(0.3 * true_tau, 30)
    bg = counts_true / true_tau
    spike_idx = 12
    bg[spike_idx] = 50_000.0  # contamination event, nothing like the true background level

    line_data = _make_line_data_with_background({"Al27": bg}, ablation_level=900_000.0, ablation_n=20, seed=10)
    # Explicit window spanning the full 30-row background: the changepoint
    # detector's default margins can't test a candidate boundary exactly at
    # the true transition for this file's length, falling back to a
    # truncated fixed window -- irrelevant to what this test is checking
    # (outlier screening, not window detection), so bypass it directly.
    from src.calibration.background import BackgroundWindow, AblationWindow, _to_datetime
    window = BackgroundWindow(
        start_idx=0, end_idx=30, start_time=_to_datetime(line_data.absolute_time[0]),
        end_time=_to_datetime(line_data.absolute_time[29]), method="manual_override", reference_channel="manual",
    )
    ablation = AblationWindow(
        start_idx=30, end_idx=line_data.n_rows, start_time=_to_datetime(line_data.absolute_time[30]),
        end_time=_to_datetime(line_data.absolute_time[-1]),
    )
    result = compute_background_result(line_data, window=window, ablation=ablation, reference_channels=["Al27"])

    assert "Al27" in result.background_row_outlier_mask
    assert result.background_row_outlier_mask["Al27"][spike_idx]
    assert result.background_row_outlier_mask["Al27"].sum() == 1

    # background_mean must land near the true ~0.3 cps level, not be
    # dragged toward the spike's ~50,000 cps.
    assert result.background_mean["Al27"] < 5.0

    roles = classify_rows(line_data, result, analyte="Al27")
    assert roles[spike_idx] == "excluded"
    assert roles[0] == "background"


def test_compute_background_result_clean_data_poisson_mean_close_to_arithmetic_mean():
    """Sanity check: with no contamination, the new Poisson-rate
    background_mean shouldn't diverge meaningfully from a plain arithmetic
    mean of the same (moderate-count) data."""
    true_tau = 0.2803
    rng = np.random.default_rng(11)
    counts_true = rng.poisson(5.0 * true_tau, 40)
    bg = counts_true / true_tau

    line_data = _make_line_data_with_background({"Al27": bg}, ablation_level=900_000.0, ablation_n=20, seed=12)
    result = compute_background_result(line_data, reference_channels=["Al27"])

    assert "Al27" in result.background_row_outlier_mask
    assert not result.background_row_outlier_mask["Al27"].any()
    assert result.background_mean["Al27"] == pytest.approx(float(np.mean(bg)), rel=0.15)


def test_compute_background_result_unresolvable_tau_falls_back_to_arithmetic_mean():
    # All-zero background -- no nonzero values anywhere to infer/bound tau
    # from, so this must fall back to the (zero) arithmetic mean rather
    # than raising or dividing by an unresolved tau.
    bg = np.zeros(25)
    line_data = _make_line_data_with_background({"Al27": bg}, ablation_level=900_000.0, ablation_n=20, seed=13)
    result = compute_background_result(line_data, reference_channels=["Al27"])

    assert result.tau_provenance["Al27"] == "unknown"
    assert result.background_mean["Al27"] == 0.0


def test_recompute_from_window_manual_override():
    line_data, _ = _make_line_data(bg_n=40, ablation_n=60, seed=7)
    result = recompute_from_window(line_data, start_idx=0, end_idx=35)
    assert result.window.method == "manual_override"
    assert result.window.end_idx == 35
    assert result.ablation.start_idx == 35


def _make_line_data_with_bg_level(acquired_at, bg_level, bg_n=20, ablation_n=20, ablation_level=900000.0, seed=0, label="SYNSTD", index=1):
    rng = np.random.default_rng(seed)
    n = bg_n + ablation_n
    dt = 0.28
    time_s = np.round(np.arange(1, n + 1) * dt, 4)
    absolute_time = np.array([np.datetime64(acquired_at) + np.timedelta64(int(round(t * 1e6)), "us") for t in time_s])
    bg = bg_level + rng.normal(0, 5, bg_n)
    abl = ablation_level + rng.normal(0, ablation_level * 0.01, ablation_n)
    al27 = np.concatenate([bg, abl])
    signal = pd.DataFrame({"Al27": al27})
    meta = LineFileMeta(
        path=Path(f"{label} - {index}.csv"), label=label, index=index, is_standard=True,
        acquired_at=acquired_at, batch="Test.b",
    )
    return LineFileData(
        meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=["Al27"],
        signal=signal, dt_s=dt, n_rows=n,
    )


def test_fit_session_background_drift_recovers_linear_trend_and_applies_to_correction():
    base_time = datetime(2026, 3, 1, 10, 0, 0)
    # Background level increases by 5 CPS every 10 minutes across the session.
    files = [
        _make_line_data_with_bg_level(base_time + timedelta(minutes=10 * i), bg_level=500.0 + 5.0 * i, seed=i)
        for i in range(6)
    ]
    backgrounds = [compute_background_result(f, reference_channels=["Al27"]) for f in files]
    for b in backgrounds:
        assert b.background_correction_method == "naive_per_file_constant"

    session_fit = fit_session_background_drift(backgrounds, order=1)
    assert "Al27" in session_fit
    # slope ~ 5 CPS per 10 minutes = 5/600 CPS/s
    assert session_fit["Al27"].coeffs[0] == pytest.approx(5.0 / 600.0, rel=0.25)

    result = compute_background_result(files[3], reference_channels=["Al27"], session_background_drift=session_fit)
    assert result.background_correction_method == "session_drift_aware"


def test_fit_session_background_drift_falls_back_to_lower_order_with_few_points():
    base_time = datetime(2026, 3, 1, 10, 0, 0)
    line_data = _make_line_data_with_bg_level(base_time, bg_level=500.0, seed=0)
    backgrounds = [compute_background_result(line_data, reference_channels=["Al27"])]
    session_fit = fit_session_background_drift(backgrounds, order=2)
    assert session_fit["Al27"].order == 0


def test_fit_session_background_drift_empty_list_returns_empty_dict():
    assert fit_session_background_drift([]) == {}


# ---------------------------------------------------------------------------
# Poisson-statistics additions (poisson_background_spec.md)
# ---------------------------------------------------------------------------

def test_compute_background_result_all_zero_channel_has_unknown_provenance_and_no_currie():
    rng = np.random.default_rng(1)
    bg_values = {
        "Al27": 500.0 + rng.normal(0, 20, 30),   # normal background, used for step detection
        "Yb172": np.zeros(30),                     # all-zero background -- no info to estimate tau from
    }
    line_data = _make_line_data_with_background(bg_values, ablation_level=900000.0, ablation_n=20, seed=2)
    result = compute_background_result(line_data, reference_channels=["Al27"])

    assert result.tau_provenance["Yb172"] == "unknown"
    assert result.background_counts["Yb172"] is None
    assert result.background_tau_s["Yb172"] is None
    assert "Yb172" not in result.currie
    assert np.isfinite(result.background_corrected_signal["Yb172"]).all()  # no exception/NaN propagation

    # The normal-background channel has plenty of nonzero values, so it must
    # get at least a conservative ("bounded") tau, not "unknown".
    assert result.tau_provenance["Al27"] != "unknown"


def test_compute_background_result_allows_negative_net_counts():
    # Manual window (bypassing auto-detection) so a below-background ablation
    # row is guaranteed to land inside the ablation region regardless of its
    # own value -- the point being tested is that background subtraction
    # doesn't clip that row at zero.
    bg = 500.0 + np.random.default_rng(3).normal(0, 5, 30)
    ablation = np.concatenate([[100.0], 900000.0 + np.random.default_rng(4).normal(0, 100, 19)])
    signal = pd.DataFrame({"Al27": np.concatenate([bg, ablation])})
    n = len(signal)
    dt = 0.2803
    time_s = np.round(np.arange(1, n + 1) * dt, 4)
    acquired_at = datetime(2026, 3, 1, 10, 0, 0)
    absolute_time = np.array([np.datetime64(acquired_at) + np.timedelta64(int(round(t * 1e6)), "us") for t in time_s])
    meta = LineFileMeta(path=Path("SYNSTD - 1.csv"), label="SYNSTD", index=1, is_standard=True, acquired_at=acquired_at, batch="Test.b")
    line_data = LineFileData(meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=["Al27"], signal=signal, dt_s=dt, n_rows=n)

    result = recompute_from_window(line_data, start_idx=0, end_idx=30)
    assert result.background_corrected_signal["Al27"].iloc[0] < 0


def test_compute_background_result_per_analyte_tau_provenance_can_differ():
    rng = np.random.default_rng(5)
    tau_true = 0.2
    quantized_counts = rng.poisson(0.3, size=30)
    bg_values = {
        "Yb172": quantized_counts / tau_true,        # genuinely quantized low-count channel
        "Al27": 500.0 + rng.normal(0, 20, 30),         # smooth continuous "major element" background
    }
    line_data = _make_line_data_with_background(bg_values, ablation_level=900000.0, ablation_n=20, seed=6)
    result = compute_background_result(line_data, reference_channels=["Al27"])

    assert result.tau_provenance["Yb172"] == "inferred"
    assert result.tau_provenance["Al27"] != "inferred"  # smooth data shouldn't claim a confident quantum
    assert result.tau_provenance["Yb172"] != result.tau_provenance["Al27"]


def _make_quantized_session(n_files=6, tau_true=0.2, rate_cps=0.3, drift_slope=0.0, seed=0):
    """Builds several BackgroundResults for one quantized low-count analyte
    ("Yb172") across a session, with a known (possibly drifting) true rate."""
    rng = np.random.default_rng(seed)
    base_time = datetime(2026, 3, 1, 10, 0, 0)
    backgrounds = []
    for i in range(n_files):
        rate = max(rate_cps + drift_slope * i, 0.01)
        bg_values = {
            "Al27": 500.0 + rng.normal(0, 20, 40),
            "Yb172": rng.poisson(rate, size=40) / tau_true,   # 40 background rows per file
        }
        line_data = _make_line_data_with_background(
            bg_values, ablation_level=900000.0, ablation_n=15, seed=int(rng.integers(0, 1_000_000)),
            index=i + 1, acquired_at=base_time + timedelta(minutes=10 * i),
        )
        backgrounds.append(compute_background_result(line_data, reference_channels=["Al27"]))
    return backgrounds


def test_fit_session_background_drift_auto_poisson_lrt_uses_poisson_path():
    backgrounds = _make_quantized_session(n_files=8, seed=10)
    fits = fit_session_background_drift(backgrounds, method="auto_poisson_lrt", max_order=3)
    assert "Yb172" in fits
    assert isinstance(fits["Yb172"], PoissonDriftFit)


def test_fit_session_background_drift_auto_poisson_lrt_falls_back_when_unknown_tau():
    # All-zero background for every file -- tau stays "unknown" everywhere,
    # so the Poisson path must fall back to the Gaussian/AIC path instead of
    # raising or silently producing an empty result.
    base_time = datetime(2026, 3, 1, 10, 0, 0)
    backgrounds = []
    for i in range(6):
        bg_values = {"Al27": 500.0 + np.random.default_rng(i).normal(0, 20, 30), "Yb172": np.zeros(30)}
        line_data = _make_line_data_with_background(
            bg_values, ablation_level=900000.0, ablation_n=15, seed=i,
            index=i + 1, acquired_at=base_time + timedelta(minutes=10 * i),
        )
        backgrounds.append(compute_background_result(line_data, reference_channels=["Al27"]))

    fits = fit_session_background_drift(backgrounds, method="auto_poisson_lrt", max_order=3)
    assert "Yb172" in fits
    assert isinstance(fits["Yb172"], DriftFit)  # fell back, not a PoissonDriftFit


def test_fit_session_background_drift_fixed_method_still_returns_drift_fit():
    # Backward-compatible default: method="fixed" behaves like the original
    # (pre-Poisson) implementation.
    backgrounds = _make_quantized_session(n_files=6, seed=20)
    fits = fit_session_background_drift(backgrounds, order=1)
    assert isinstance(fits["Yb172"], DriftFit)
    assert not isinstance(fits["Yb172"], PoissonDriftFit)


# ---------------------------------------------------------------------------
# Manual background-window override + ablation edge-trim
# ---------------------------------------------------------------------------

def test_window_from_override_converts_offsets_to_indices():
    line_data, _ = _make_line_data(bg_n=40, ablation_n=60, seed=30)
    # time_s starts at ~0.28 and steps by ~0.2803s -- offsets chosen to land
    # cleanly within the background region regardless of auto-detection.
    override = BackgroundWindowOverride(start_offset_s=0.0, end_offset_s=5.0)
    window, ablation = window_from_override(line_data, override)

    expected_end_idx = int(np.searchsorted(line_data.time_s, 5.0))
    assert window.start_idx == 0
    assert window.end_idx == expected_end_idx
    assert window.method == "manual_override"
    assert ablation.start_idx == expected_end_idx
    assert ablation.end_idx == line_data.n_rows
    # No edge trim requested -- included region equals the full ablation span.
    assert ablation.included_start_idx == ablation.start_idx
    assert ablation.included_end_idx == ablation.end_idx


def test_window_from_override_with_edge_trim_narrows_included_region_only():
    line_data, _ = _make_line_data(bg_n=40, ablation_n=60, seed=31)
    override = BackgroundWindowOverride(start_offset_s=0.0, end_offset_s=5.0, edge_trim_lead_s=2.0, edge_trim_trail_s=1.0)
    window, ablation = window_from_override(line_data, override)

    # The displayed/raw span is untouched by edge trim.
    full_start, full_end = ablation.start_idx, ablation.end_idx
    assert ablation.included_start_idx > full_start
    assert ablation.included_end_idx < full_end
    assert ablation.start_idx == full_start
    assert ablation.end_idx == full_end


def test_apply_edge_trim_never_collapses_included_region():
    line_data, true_bg_n = _make_line_data(bg_n=40, ablation_n=10, seed=32)  # short ablation window
    window, ablation = detect_background_window(line_data, reference_channels=["Al27"])
    # Absurdly large trim requests on both ends -- must still leave >=1 row.
    trimmed = apply_edge_trim(ablation, line_data, lead_s=1000.0, trail_s=1000.0)
    assert trimmed.included_end_idx > trimmed.included_start_idx
    assert trimmed.included_end_idx <= trimmed.end_idx
    assert trimmed.included_start_idx >= trimmed.start_idx


def test_assemble_occurrences_uses_included_region_for_statistics():
    from src.calibration.standards import assemble_occurrences

    # Ablation signal with a clear leading ramp (edge effect) that would bias
    # the mean if included -- trimming it out should change mean_signal.
    bg = 500.0 + np.random.default_rng(33).normal(0, 5, 30)
    ramp = np.linspace(2_000_000, 900_000, 5)  # decaying edge-effect ramp
    plateau = 900_000 + np.random.default_rng(34).normal(0, 100, 25)
    ablation_vals = np.concatenate([ramp, plateau])
    signal = pd.DataFrame({"Al27": np.concatenate([bg, ablation_vals])})
    n = len(signal)
    dt = 0.2803
    time_s = np.round(np.arange(1, n + 1) * dt, 4)
    acquired_at = datetime(2026, 3, 1, 10, 0, 0)
    absolute_time = np.array([np.datetime64(acquired_at) + np.timedelta64(int(round(t * 1e6)), "us") for t in time_s])
    meta = LineFileMeta(path=Path("SYNSTD - 1.csv"), label="SYNSTD", index=1, is_standard=True, acquired_at=acquired_at, batch="Test.b")
    line_data = LineFileData(meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=["Al27"], signal=signal, dt_s=dt, n_rows=n)

    from src.calibration.background import BackgroundWindow, AblationWindow, _to_datetime
    window = BackgroundWindow(
        start_idx=0, end_idx=30, start_time=_to_datetime(absolute_time[0]), end_time=_to_datetime(absolute_time[29]),
        method="manual_override", reference_channel="manual",
    )
    ablation_full = AblationWindow(
        start_idx=30, end_idx=n, start_time=_to_datetime(absolute_time[30]), end_time=_to_datetime(absolute_time[-1]),
    )
    trimmed_ablation = apply_edge_trim(ablation_full, line_data, lead_s=5 * dt + 0.01, trail_s=0.0)

    result_untrimmed = compute_background_result(line_data, window=window, ablation=ablation_full)
    result_trimmed = compute_background_result(line_data, window=window, ablation=trimmed_ablation)

    occ_untrimmed = assemble_occurrences([result_untrimmed])[0]
    occ_trimmed = assemble_occurrences([result_trimmed])[0]

    # Trimming out the high-valued ramp should lower the mean toward the plateau.
    assert occ_trimmed.mean_signal["Al27"] < occ_untrimmed.mean_signal["Al27"]
    assert occ_trimmed.mean_signal["Al27"] == pytest.approx(900_000, rel=0.01)


def test_detect_row_outliers_flags_no_rows_on_flat_data():
    rng = np.random.default_rng(50)
    flat = 900_000 + rng.normal(0, 500, 30)
    mask = detect_row_outliers(flat)
    assert not mask.any()


def test_detect_row_outliers_flags_injected_leading_ramp():
    rng = np.random.default_rng(51)
    ramp = np.array([2_000_000.0, 1_600_000.0, 1_200_000.0])
    plateau = 900_000 + rng.normal(0, 500, 27)
    values = np.concatenate([ramp, plateau])
    mask = detect_row_outliers(values)
    assert mask[:3].all()
    assert not mask[3:].any()


def test_detect_row_outliers_too_few_points_flags_nothing():
    mask = detect_row_outliers(np.array([1.0, 2.0, 3.0]))
    assert not mask.any()
    assert len(mask) == 3


def test_detect_row_outliers_order0_is_median_centered():
    """order=0 must use the median, not the mean, as its center -- a mean
    fit is itself dragged by the very outliers it's supposed to detect,
    while the median (50% breakdown point) isn't. At background-window
    scale (~25-30 rows), a couple of contamination spikes should be
    isolated exactly, with no false positives on well-behaved data."""
    rng = np.random.default_rng(1)
    bg = rng.normal(5, 3, 25)
    bg[10] = 5000.0
    mask = detect_row_outliers(bg, order=0)
    assert np.where(mask)[0].tolist() == [10]

    bg2 = rng.normal(5, 3, 25)
    bg2[5] = 5000.0
    bg2[6] = 4800.0
    mask2 = detect_row_outliers(bg2, order=0)
    assert set(np.where(mask2)[0]) == {5, 6}


def test_detect_row_outliers_order0_low_false_positive_rate():
    n_trials = 100
    any_flagged = 0
    for seed in range(n_trials):
        rng = np.random.default_rng(seed)
        flat = 5.0 + rng.normal(0, 3, 30)
        if detect_row_outliers(flat, order=0).any():
            any_flagged += 1
    assert any_flagged <= 3  # expect ~0/100 at threshold=5.0, allow slack


def test_detect_row_outliers_order0_zero_inflated_background_no_false_positives():
    """Regression test for real-data behavior on a near-all-zero trace-
    element background window (e.g. Gd157): occasional genuine single/
    double/triple-count events among mostly-exact-zero rows must not be
    flagged just for being nonzero -- only screen nonzero rows against each
    other, never against the sea of zeros."""
    true_tau = 0.2803
    rng = np.random.default_rng(3)
    counts_true = rng.poisson(0.15 * true_tau, 40)  # mostly 0, a rare 1-3 count
    bg = counts_true / true_tau
    assert np.count_nonzero(bg) >= 1  # sanity: the scenario actually has a genuine nonzero row
    mask = detect_row_outliers(bg, order=0)
    assert not mask.any()

    # A true contamination spike among the same mostly-zero background,
    # alongside a few genuine low counts, must still be caught.
    rng = np.random.default_rng(9)
    counts_true = rng.poisson(0.3 * true_tau, 30)
    bg2 = counts_true / true_tau
    bg2[12] = 50_000.0
    mask2 = detect_row_outliers(bg2, order=0)
    assert mask2[12]
    assert mask2.sum() == 1


def test_detect_row_outliers_tracks_real_decay_without_false_positives():
    """A genuine within-window trend (not a flat plateau) must not itself
    get flagged -- order=1 exists specifically so this decaying signal is
    absorbed into the fit, not mistaken for an outlier."""
    n = 40
    t = np.arange(n)
    curve = 2.0e6 * np.exp(-t / 25.0) + 900_000
    rng = np.random.default_rng(3)
    values = curve + rng.normal(0, 3e4, n)
    mask = detect_row_outliers(values)
    assert not mask.any()


def test_detect_row_outliers_isolates_dropout_within_a_decay_curve():
    """Regression test for the failure mode order=0 had on real data: a
    genuine within-window trend must be tracked (not mistaken for an
    outlier itself -- see test above), while a real localized anomaly on
    top of it still gets caught."""
    n = 40
    t = np.arange(n)
    curve = 2.0e6 * np.exp(-t / 25.0) + 900_000
    rng = np.random.default_rng(3)
    values = curve + rng.normal(0, 3e4, n)
    dropout_idx = [15, 16, 17]
    values[dropout_idx] = [400_000.0, 350_000.0, 420_000.0]

    mask = detect_row_outliers(values)
    assert set(np.where(mask)[0]) == set(dropout_idx)


def test_assemble_occurrences_auto_excludes_ramp_without_manual_edge_trim():
    """Regression test: a leading ramp should be caught by the low-order-fit
    row-outlier check automatically -- no apply_edge_trim call, no
    manually-specified trim duration -- and reflected as "excluded" rows in
    classify_rows, not silently folded into the mean."""
    from src.calibration.standards import assemble_occurrences

    bg = 500.0 + np.random.default_rng(52).normal(0, 5, 30)
    ramp = np.array([2_000_000.0, 1_600_000.0, 1_200_000.0])
    plateau = 900_000 + np.random.default_rng(53).normal(0, 500, 27)
    ablation_vals = np.concatenate([ramp, plateau])
    signal = pd.DataFrame({"Al27": np.concatenate([bg, ablation_vals])})
    n = len(signal)
    dt = 0.2803
    time_s = np.round(np.arange(1, n + 1) * dt, 4)
    acquired_at = datetime(2026, 3, 1, 10, 0, 0)
    absolute_time = np.array([np.datetime64(acquired_at) + np.timedelta64(int(round(t * 1e6)), "us") for t in time_s])
    meta = LineFileMeta(path=Path("SYNSTD - 1.csv"), label="SYNSTD", index=1, is_standard=True, acquired_at=acquired_at, batch="Test.b")
    line_data = LineFileData(meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=["Al27"], signal=signal, dt_s=dt, n_rows=n)

    result = compute_background_result(line_data, reference_channels=["Al27"])
    occ = assemble_occurrences([result])[0]

    # The ramp should have been excluded automatically -- mean lands near
    # the plateau, not pulled up by the ramp's elevated leading rows.
    assert occ.mean_signal["Al27"] == pytest.approx(900_000, rel=0.02)

    # Some leading rows got excluded (the ramp, at minimum), and the
    # plateau itself (last row of the included region -- unambiguously
    # past both the ramp and the auto-detected blank/ablation boundary's
    # own imprecision) is not.
    roles = classify_rows(line_data, occ.background, analyte="Al27")
    lo, hi = occ.background.ablation.included_start_idx, occ.background.ablation.included_end_idx
    assert roles[lo] == "excluded"
    assert roles[hi - 1] == "included"


def test_classify_rows_matches_window_boundaries():
    line_data, true_bg_n = _make_line_data(bg_n=40, ablation_n=60, seed=40)
    result = compute_background_result(line_data, reference_channels=["Al27"])
    roles = classify_rows(line_data, result)

    assert len(roles) == line_data.n_rows
    assert set(roles[result.window.start_idx:result.window.end_idx]) == {"background"}
    assert set(roles[result.ablation.included_start_idx:result.ablation.included_end_idx]) == {"included"}


def test_classify_rows_marks_edge_trimmed_rows_as_excluded():
    line_data, _ = _make_line_data(bg_n=40, ablation_n=60, seed=41)
    window, ablation = detect_background_window(line_data, reference_channels=["Al27"])
    trimmed_ablation = apply_edge_trim(ablation, line_data, lead_s=3.0, trail_s=0.0)
    result = compute_background_result(line_data, window=window, ablation=trimmed_ablation)
    roles = classify_rows(line_data, result)

    excluded_span = roles[ablation.start_idx:trimmed_ablation.included_start_idx]
    assert len(excluded_span) > 0
    assert set(excluded_span) == {"excluded"}


def test_classify_rows_returns_unclassified_when_no_background():
    line_data, _ = _make_line_data(bg_n=40, ablation_n=60, seed=42)
    roles = classify_rows(line_data, None)
    assert len(roles) == line_data.n_rows
    assert set(roles) == {"unclassified"}


def test_classify_rows_manual_mask_takes_precedence_and_works_pre_run():
    """A manual click/drag exclusion must render as "manual" even without
    a completed pipeline Run (instant visual feedback -- see
    dock_widgets's click/drag wiring), and must override every other role,
    including is_outlier."""
    line_data, _ = _make_line_data(bg_n=40, ablation_n=60, seed=43)
    n = line_data.n_rows
    manual_mask = np.zeros(n, dtype=bool)
    manual_mask[[0, 50]] = True  # one background-window row, one ablation-window row

    # Pre-Run: no BackgroundResult yet, manual mask still applies.
    roles_pre_run = classify_rows(line_data, None, manual_row_mask=manual_mask)
    assert roles_pre_run[0] == "manual"
    assert roles_pre_run[50] == "manual"
    assert set(roles_pre_run) - {"manual"} == {"unclassified"}

    # Post-Run, even with is_outlier=True (would otherwise mark the whole
    # included region "outlier"), the manually-masked rows still show "manual".
    result = compute_background_result(line_data, reference_channels=["Al27"])
    roles_post_run = classify_rows(line_data, result, analyte="Al27", is_outlier=True, manual_row_mask=manual_mask)
    assert roles_post_run[0] == "manual"
    assert roles_post_run[50] == "manual"
