"""Unit tests for src/deconvolution/inclusions.py -- design spec Sec 6.7 /
Stage 8's phantom-style acceptance criteria: recovers a planted inclusion's
mass/tau, and correctly separates a one-line spike from a cross-line-coherent
lamella (Sec 8, Stage 8's stated accept criteria).

Pure Python/numpy/scipy -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.deconvolution.inclusions import (
    InclusionEvent,
    detect_events,
    fit_event_tail,
    subtract_event_tails,
    mark_coherent_events,
    merge_events,
    decontaminate_inclusions,
    apply_events_to_line,
)


def _phantom_line(n, dt_s, baseline, peak_idx, peak_height, tau_s, rng, noise_sd=3.0, ramp=(0.3, 0.7, 1.0)):
    """A flat baseline with additive Gaussian noise, an inclusion's rising
    edge (a short ramp, matching the real ramp-then-decay shape reported
    against washout.py's pure single-exponential assumption), and a causal
    exponential decay tail -- the along-line signature Sec 6.7 attributes
    to a sub-spot inclusion (spike plus PSF-shaped tail).
    """
    line = np.full(n, float(baseline)) + rng.normal(0, noise_sd, n)
    for k, frac in enumerate(ramp):
        idx = peak_idx - (len(ramp) - 1 - k)
        line[idx] += frac * peak_height
    tail_idx = np.arange(peak_idx + 1, n)
    t = (tail_idx - peak_idx) * dt_s
    line[tail_idx] += peak_height * np.exp(-t / tau_s)
    return np.clip(line + rng.normal(0, noise_sd, n), 0, None)


def test_detect_events_finds_the_planted_peak():
    rng = np.random.default_rng(0)
    line = _phantom_line(200, 0.5, 100.0, peak_idx=80, peak_height=5000.0, tau_s=3.0, rng=rng)
    events = detect_events(line, threshold=5.0)
    assert len(events) == 1
    assert events[0].peak == 80
    assert events[0].start <= 80 <= events[0].end


def test_detect_events_ignores_flat_noise():
    rng = np.random.default_rng(0)
    line = np.full(100, 100.0) + rng.normal(0, 3.0, 100)
    assert detect_events(line, threshold=5.0) == []


def test_fit_event_tail_recovers_tau_and_amplitude():
    rng = np.random.default_rng(1)
    tau_true, amp_true = 3.0, 5000.0
    line = _phantom_line(200, 0.5, 100.0, peak_idx=80, peak_height=amp_true, tau_s=tau_true, rng=rng)
    events = detect_events(line, threshold=5.0)
    fit_event_tail(line, events[0], dt_s=0.5)

    ev = events[0]
    assert ev.fit_success
    assert ev.tau_s == pytest.approx(tau_true, rel=0.1)
    assert ev.amplitude == pytest.approx(amp_true, rel=0.1)


def test_fit_event_tail_skips_insufficient_tail():
    ev = InclusionEvent(line=0, start=8, peak=10, end=11, peak_value=1000.0, baseline_value=100.0)
    ev.flags.append("insufficient_tail_points")
    line = np.full(20, 100.0)
    fit_event_tail(line, ev, dt_s=0.5)
    assert ev.tau_s is None
    assert not ev.fit_success


def test_subtract_event_tails_restores_baseline_downstream():
    rng = np.random.default_rng(2)
    baseline = 100.0
    line = _phantom_line(200, 0.5, baseline, peak_idx=80, peak_height=5000.0, tau_s=3.0, rng=rng)
    events = detect_events(line, threshold=5.0)
    fit_event_tail(line, events[0], dt_s=0.5)

    corrected, subtracted, negative_count = subtract_event_tails(line, events, dt_s=0.5)

    # Well downstream of the tail, correction should land close to the true
    # baseline -- the original signal there was still contaminated by the
    # tail (elevated well above `baseline`).
    window = slice(90, 140)
    assert abs(np.mean(corrected[window]) - baseline) < abs(np.mean(line[window]) - baseline)
    assert np.mean(corrected[window]) == pytest.approx(baseline, abs=5.0)
    assert np.all(subtracted >= 0)
    # line itself must not be mutated
    assert line[100] != corrected[100] or subtracted[100] == 0


def test_subtract_event_tails_reports_negative_not_clipped():
    # A fitted tail can overshoot the true remaining signal at a pixel --
    # same "report, never silently clip" convention as washout.py.
    ev = InclusionEvent(
        line=0, start=8, peak=10, end=15, peak_value=1000.0, baseline_value=1.0,
        tau_s=5.0, amplitude=1000.0, fit_baseline=1.0, fit_model="single",
        fit_r_squared=0.99, fit_success=True,
    )
    line = np.full(20, 1.0)  # far too little signal for the fitted tail to be subtracted from
    corrected, subtracted, negative_count = subtract_event_tails(line, [ev], dt_s=0.5)
    assert negative_count > 0
    assert np.any(corrected < 0)


def test_subtract_event_tails_conserves_mass_by_redistributing_to_peak():
    """Washout mass is relocated to the source pixel, not deleted -- the
    inclusion itself must not be diminished, only the pixels it smeared
    into."""
    rng = np.random.default_rng(3)
    line = _phantom_line(200, 0.5, 100.0, peak_idx=80, peak_height=5000.0, tau_s=3.0, rng=rng)
    events = detect_events(line, threshold=5.0)
    fit_event_tail(line, events[0], dt_s=0.5)
    ev = events[0]

    corrected, subtracted, _ = subtract_event_tails(line, events, dt_s=0.5, redistribute_to_source=True)
    total_removed = np.sum(subtracted)
    assert corrected[ev.peak] == pytest.approx(line[ev.peak] + total_removed)
    # total signal over the affected window is unchanged (redistribution, not deletion)
    window = slice(ev.peak, ev.end + 1)
    assert np.sum(corrected[window]) == pytest.approx(np.sum(line[window]), rel=1e-9)

    corrected_no_redist, _, _ = subtract_event_tails(line, events, dt_s=0.5, redistribute_to_source=False)
    assert corrected_no_redist[ev.peak] == line[ev.peak]  # peak untouched when redistribution is off
    assert np.sum(corrected_no_redist[window]) < np.sum(line[window])  # mass genuinely removed


def test_fit_event_tail_auto_selects_double_exponential_when_warranted():
    rng = np.random.default_rng(4)
    n, dt_s, peak_idx = 300, 0.5, 100
    baseline = 500.0
    fast_amp, fast_tau = 1.0e7, 0.4
    slow_amp, slow_tau = 2.0e4, 20.0
    line = np.full(n, baseline)
    for k, frac in enumerate([0.3, 0.7, 1.0]):
        line[peak_idx - (2 - k)] += frac * (fast_amp + slow_amp)
    tail_idx = np.arange(peak_idx + 1, n)
    t = (tail_idx - peak_idx) * dt_s
    line[tail_idx] += fast_amp * np.exp(-t / fast_tau) + slow_amp * np.exp(-t / slow_tau)
    line = np.clip(line + rng.normal(0, np.sqrt(np.clip(line, 1, None))), 0, None)

    events = detect_events(line, threshold=5.0, baseline_half_window=120, max_tail_pixels=150, min_prominence=1000.0)
    assert len(events) == 1
    fit_event_tail(line, events[0], dt_s, model="auto")

    ev = events[0]
    assert ev.fit_success
    assert ev.fit_model == "double"
    assert ev.tau_s == pytest.approx(slow_tau, rel=0.3)  # dominant/slower reported as tau_s
    assert ev.tau2_s == pytest.approx(fast_tau, rel=0.3)


def test_coherent_event_is_not_subtracted_by_default():
    ev = InclusionEvent(
        line=0, start=8, peak=10, end=15, peak_value=1000.0, baseline_value=100.0,
        tau_s=3.0, amplitude=500.0, fit_baseline=100.0, fit_model="single",
        fit_r_squared=0.99, fit_success=True, coherent_across_lines=True,
    )
    line = np.full(20, 100.0)
    corrected, subtracted, _ = subtract_event_tails(line, [ev], dt_s=0.5)
    assert np.array_equal(corrected, line)
    assert np.all(subtracted == 0)

    corrected2, subtracted2, _ = subtract_event_tails(line, [ev], dt_s=0.5, decontaminate_coherent=True)
    assert not np.array_equal(corrected2, line)


def test_mark_coherent_events_any_neighbor_not_every_neighbor():
    """The middle-of-a-vein row must match on both sides; the row at the
    vein's edge only matches its one in-vein neighbor and must still be
    called coherent -- "any neighbor", not "every existing neighbor" (see
    module docstring's rationale).
    """
    vein_events = {
        0: [InclusionEvent(line=0, start=48, peak=50, end=55, peak_value=1.0, baseline_value=0.0)],
        1: [InclusionEvent(line=1, start=48, peak=50, end=55, peak_value=1.0, baseline_value=0.0)],
        2: [InclusionEvent(line=2, start=48, peak=50, end=55, peak_value=1.0, baseline_value=0.0)],
        3: [InclusionEvent(line=3, start=118, peak=120, end=125, peak_value=1.0, baseline_value=0.0)],
    }
    mark_coherent_events(vein_events, position_tolerance=3)

    assert vein_events[0][0].coherent_across_lines
    assert vein_events[1][0].coherent_across_lines
    assert vein_events[2][0].coherent_across_lines  # edge-of-vein row
    assert not vein_events[3][0].coherent_across_lines  # isolated inclusion


def test_decontaminate_inclusions_separates_vein_from_inclusion():
    """Stage 8's stated accept criterion: correctly separates a one-line
    spike from a cross-line-coherent lamella.
    """
    dt_s = 0.5
    lines = []
    for i in range(3):
        lines.append(_phantom_line(200, dt_s, 100.0, 50, 3000.0, 2.0, np.random.default_rng(100 + i)))
    lines.append(_phantom_line(200, dt_s, 100.0, 120, 5000.0, 3.0, np.random.default_rng(200)))
    lines.append(np.full(200, 100.0) + np.random.default_rng(300).normal(0, 3.0, 200))

    result = decontaminate_inclusions(lines, dt_s, threshold=5.0)

    vein_flags = [ev.coherent_across_lines for evs in (result.events_by_line[0], result.events_by_line[1], result.events_by_line[2]) for ev in evs]
    assert all(vein_flags)
    assert not any(ev.coherent_across_lines for ev in result.events_by_line[3])

    # vein lines untouched; inclusion line corrected substantially
    assert np.allclose(result.corrected[0], lines[0])
    assert not np.allclose(result.corrected[3], lines[3])


def test_merge_events_collapses_same_pixel_across_trigger_channels():
    """A zircon inclusion trips detection on both Zr90 and Hf178 (say) at
    the same pixel -- merge_events must not require picking one hardcoded
    trigger element and must not double-count the same physical event.
    """
    zr_events = [InclusionEvent(line=0, start=78, peak=80, end=100, peak_value=1e6, baseline_value=0.0)]
    hf_events = [InclusionEvent(line=0, start=79, peak=81, end=95, peak_value=5e4, baseline_value=0.0)]
    # a rutile inclusion elsewhere, only visible on a Ti channel
    ti_events = [InclusionEvent(line=0, start=148, peak=150, end=170, peak_value=2e5, baseline_value=0.0)]

    merged = merge_events(zr_events, hf_events, ti_events, position_tolerance=3)

    assert len(merged) == 2  # the co-located zr/hf pair collapsed to one
    peaks = sorted(ev.peak for ev in merged)
    assert peaks == [80, 150]
    # the higher-peak_value (Zr90) event wins the co-located pair
    assert merged[0].peak_value == pytest.approx(1e6)


def test_merge_events_keeps_events_on_different_lines_separate():
    events_a = [InclusionEvent(line=0, start=8, peak=10, end=20, peak_value=100.0, baseline_value=0.0)]
    events_b = [InclusionEvent(line=1, start=8, peak=10, end=20, peak_value=100.0, baseline_value=0.0)]
    merged = merge_events(events_a, events_b)
    assert {ev.line for ev in merged} == {0, 1}


def test_apply_events_to_line_refits_per_analyte_not_shared_amplitude():
    """Same event window (position) detected on a "trigger" channel, but
    reused on a different analyte with its own, different amplitude/tau --
    the refit must recover *that* analyte's own values, not the trigger's.
    """
    dt_s = 0.5
    rng_trigger = np.random.default_rng(10)
    trigger_line = _phantom_line(200, dt_s, 100.0, 80, 50000.0, 5.0, rng_trigger)
    trigger_events = detect_events(trigger_line, threshold=5.0)
    fit_event_tail(trigger_line, trigger_events[0], dt_s)
    assert trigger_events[0].amplitude == pytest.approx(50000.0, rel=0.15)

    rng_other = np.random.default_rng(11)
    other_amp_true, other_tau_true = 800.0, 2.0
    other_line = _phantom_line(200, dt_s, 20.0, 80, other_amp_true, other_tau_true, rng_other, noise_sd=1.0)

    corrected, subtracted, refit_events, _ = apply_events_to_line(other_line, trigger_events, dt_s)

    assert refit_events[0].amplitude == pytest.approx(other_amp_true, rel=0.2)
    assert refit_events[0].tau_s == pytest.approx(other_tau_true, rel=0.2)
    # the trigger channel's own event must not have been mutated
    assert trigger_events[0].amplitude == pytest.approx(50000.0, rel=0.15)
