"""Sub-spot inclusion / point-source decontamination (design spec Sec 6.7,
Stage 8): localize a spike-plus-causal-tail event along a line, fit *that
event's own* decay, and subtract the fitted tail from the pixels downstream
of it -- so a single sub-spot inclusion (e.g. a zircon crossed mid-traverse)
doesn't leave every following pixel elevated by washout tailing it never
actually contained.

Why ``washout.py``'s recursive inverse (eq. 6) is not enough for this case:
eq. (6) assumes the *whole line* is one AR(1) process with one fixed tau and
applies the identical two-tap correction everywhere. An inclusion's rising
edge is not itself washout -- the "ramp up" the spec's eq. (4) attributes to
``K`` (the spot/aperture footprint sweeping across a finite-size object,
plus the boxcar dwell ``Pi``), a non-causal blur a causal single-pole filter
cannot undo. Worse, eq. (6) amplifies noise hardest exactly at the huge
contrast step an inclusion produces (``noise_amplification``, eq. 7), while
still underfitting the actual decay once the excursion is large enough that
a single global tau no longer describes it well. This module instead
follows Sec 6.7 directly:

1. **Matched filter** (:func:`detect_events`) localizes each excursion
   against a robust rolling baseline -- a stand-in for correlating against
   the PSF template, using contiguous-exceedance + peak-search since the
   PSF shape itself is only known approximately (Sec 6.1's kernels).
2. **Fit the decay** (:func:`fit_event_tail`) per event -- with Poisson
   (shot-noise) weights, not the unweighted least squares
   :func:`src.deconvolution.esf.fit_single_pulse_decay` uses (see that
   function's docstring for why: an unweighted fit is dominated by just
   the first sample or two of a drop spanning orders of magnitude) --
   rather than assuming one tau for the whole line.
3. **Subtract the fitted tail** (:func:`subtract_event_tails`) from the
   pixels downstream of the peak, and add that same amount back onto the
   peak pixel by default -- relocating the washed-out mass to its source
   rather than deleting it (the inclusion itself, ``[start, peak]``, is
   never touched). Matching ``washout.py``'s convention, this is never
   silently clipped: a downstream pixel that goes negative is reported
   (``negative_count``), not floored.
4. **Interline discrimination** (:func:`mark_coherent_events`) -- an event
   whose position recurs in the neighboring line(s) is a crack/vein/lamella
   (coherent across lines), not a sub-spot inclusion, and is left alone by
   default.

Operates on one analyte's CPS at a time. A genuine inclusion produces a
co-located event in every analyte it contains (Zr90 revealing a zircon that
also elevates Hf176/Hf178, say), but each analyte's own amplitude/tau
differ -- detect on whichever analyte shows the clearest signal (a
"trigger" channel), then reuse that event's *window* on the others via
:func:`apply_events_to_line`, re-fitting the decay locally rather than
assuming a shared amplitude/tau.

There is deliberately no single hardcoded trigger element: which channel
reveals an inclusion depends on the mineral -- Zr90 for zircon, Ti47 for
rutile, and so on -- and one sample can contain more than one inclusion
type. Run :func:`detect_events` independently on each candidate trigger
channel that might be present, then :func:`merge_events` the results
before calling :func:`apply_events_to_line` on whichever analytes each
inclusion type is expected to contaminate. When no single channel is a
reliable trigger (or the affected analyte's own signal is already clear
enough on its own, as Hf176/Hf178 often are for zircon), skip the trigger
step entirely and run :func:`decontaminate_inclusions` independently per
analyte instead -- both are first-class, equally supported workflows.

Known v1 limitation: a contiguous exceedance run is treated as exactly one
event (peak = its global maximum). A rare multi-peak run (two inclusions a
few pixels apart on the same line, without the signal dropping back to
baseline between them) is therefore folded into a single event rather than
split -- acceptable for the common single-inclusion case this targets, but
worth revisiting if closely-spaced inclusion trains turn out to be common.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import median_filter
from scipy.optimize import least_squares


# Same modified-z-score convention as src.calibration.standards._mad_outlier_mask
# / src.deconvolution.esf.flag_tau_outliers (Iglewicz & Hoaglin).
_MAD_SCALE = 0.6745


@dataclass
class InclusionEvent:
    """One detected along-line excursion (candidate sub-spot inclusion).

    Attributes
    ----------
    line : int
        Index into whatever sequence of lines the caller passed in.
    start, peak, end : int
        Sample indices (inclusive) into that line's array: ``start`` is the
        first sample that exceeded the detection threshold, ``peak`` the
        index of the maximum value, ``end`` the last sample still counted as
        part of the decay tail.
    peak_value : float
        Raw signal value at ``peak``.
    baseline_value : float
        Rolling-median baseline at ``peak`` (detection-time reference, used
        for the exceedance test -- distinct from ``fit_baseline``, the tail
        fit's own baseline estimate that subtraction is computed relative
        to).
    tau_s, amplitude, fit_baseline : float or None
        :func:`fit_event_tail`'s fitted (dominant, slower) decay constant,
        its amplitude, and the tail's baseline, for the ``[peak+1, end]``
        window. ``None`` until :func:`fit_event_tail` runs (or if it
        fails).
    tau2_s, amplitude2 : float or None
        The second, faster/shorter time constant and its amplitude, when
        :func:`fit_event_tail` selected the double-exponential model
        (``fit_model == "double"``) -- ``None`` for a single-exponential
        fit or before fitting.
    fit_model : str or None
        ``"single"`` or ``"double"`` -- which model
        :func:`fit_event_tail` selected, ``None`` before fitting.
    fit_r_squared : float
        Tail-fit goodness of fit; ``nan`` before fitting.
    fit_success : bool
        Whether the tail fit converged with enough points to trust.
    coherent_across_lines : bool
        Set by :func:`mark_coherent_events`: ``True`` means this event's
        position recurs in the neighboring line(s) -- a crack/vein/lamella,
        not a sub-spot inclusion (spec Sec 6.7 item 3). Excluded from
        subtraction unless the caller explicitly opts in.
    flags : list[str]
        Human-readable notes (e.g. ``"insufficient_tail_points"``,
        ``"coherent_across_lines"``, ``"clipped_by_next_event"``).
    """

    line: int
    start: int
    peak: int
    end: int
    peak_value: float
    baseline_value: float
    tau_s: float | None = None
    amplitude: float | None = None
    tau2_s: float | None = None      # "double" fit only: the faster/shorter time constant
    amplitude2: float | None = None
    fit_baseline: float | None = None
    fit_model: str | None = None
    fit_r_squared: float = float("nan")
    fit_success: bool = False
    coherent_across_lines: bool = False
    flags: list[str] = field(default_factory=list)


def _rolling_median_baseline(line: np.ndarray, half_window: int) -> np.ndarray:
    """Robust local baseline: a median filter wide enough that a single
    inclusion's spike-plus-tail (assumed shorter than ``half_window``
    samples) cannot pull the median toward it -- median is robust to up to
    ~50% contamination in-window, and a real inclusion should occupy well
    under half of a window this wide. ``mode="reflect"`` avoids a spurious
    edge-of-line baseline drop/rise from zero-padding.
    """
    size = 2 * half_window + 1
    if size > len(line):
        size = len(line) if len(line) % 2 == 1 else len(line) - 1
        size = max(size, 1)
    return median_filter(line, size=size, mode="reflect")


def detect_events(
    line: np.ndarray,
    *,
    line_number: int = 0,
    threshold: float = 5.0,
    tail_threshold_fraction: float = 0.2,
    baseline_half_window: int = 40,
    max_tail_pixels: int = 60,
    min_tail_points: int = 4,
    min_prominence: float = 0.0,
) -> list[InclusionEvent]:
    """Localizes candidate inclusion events in one line via a robust
    rolling baseline + modified-z-score exceedance (spec Sec 6.7 item 1's
    "matched filter", approximated here since the exact PSF template is
    only known within the uncertainty of Sec 6.1's kernel estimates).

    Parameters
    ----------
    line : numpy.ndarray
        One analyte's CPS series for one line, 1D.
    line_number : int, optional
        Recorded on each returned event (which line it came from), by
        default 0 -- callers iterating multiple lines should pass the
        actual index.
    threshold : float, optional
        Modified-z-score cutoff (same convention as
        ``standards._mad_outlier_mask``) above which a sample counts as
        part of an event's core, by default 5.0 -- deliberately higher than
        that function's 3.5 (used to reject a single bad calibration point)
        since this is meant to catch only genuine large excursions, not
        flag routine analytical noise as an "inclusion."
    tail_threshold_fraction : float, optional
        The event's tail is extended, sample by sample past ``peak``, while
        the modified z-score stays above ``threshold * tail_threshold_fraction``
        -- a softer bar than the core detection threshold, since a decaying
        tail is by definition heading back toward baseline and would never
        satisfy the full ``threshold`` for more than a pixel or two. By
        default 0.2.
    baseline_half_window : int, optional
        Half-width (samples) of the rolling-median baseline, by default 40
        -- see :func:`_rolling_median_baseline`.
    max_tail_pixels : int, optional
        Hard cap on how far past ``peak`` the tail window can extend, by
        default 60.
    min_tail_points : int, optional
        An event whose tail (``end - peak``) has fewer than this many
        samples is still returned (so its ``start``/``peak`` are visible)
        but flagged ``"insufficient_tail_points"`` and left unfit -- see
        :func:`fit_event_tail`. By default 4 (matches
        ``esf.fit_single_pulse_decay``'s own minimum).
    min_prominence : float, optional
        Absolute floor (same units as ``line``, e.g. CPS) on
        ``peak_value - baseline_value``; events below it are discarded, by
        default 0.0 (off). Needed because the modified z-score alone is
        not reliable where the local baseline is near-zero: a handful of
        counts of ordinary Poisson shot noise on a near-zero baseline
        produces a tiny MAD, so even a few-count fluctuation can score
        past ``threshold``. That is exactly the regime a trace analyte
        away from its own inclusion sits in (baseline near the detection
        limit), so real data should set this to a level a few times the
        instrument's blank/background CPS -- the phantom-generated data
        this module's own tests use has a well-scaled, non-zero baseline
        and does not need it.

    Returns
    -------
    list[InclusionEvent]
        In line order, one per contiguous exceedance run. Empty if the
        line is too short/flat to compute a baseline (fewer than 3 points)
        or has zero MAD (a perfectly flat line -- no fittable structure).
    """
    line = np.asarray(line, dtype=float)
    n = len(line)
    if n < 3:
        return []

    baseline = _rolling_median_baseline(line, baseline_half_window)
    resid = line - baseline
    med = float(np.median(resid))
    mad = float(np.median(np.abs(resid - med)))
    if mad == 0.0:
        return []
    z = _MAD_SCALE * (resid - med) / mad

    events: list[InclusionEvent] = []
    i = 0
    while i < n:
        if z[i] <= threshold:
            i += 1
            continue
        run_start = i
        while i < n and z[i] > threshold:
            i += 1
        run_end = i - 1  # inclusive

        peak = run_start + int(np.argmax(line[run_start:run_end + 1]))

        if (line[peak] - baseline[peak]) < min_prominence:
            continue

        tail_thresh = threshold * tail_threshold_fraction
        end = peak
        j = peak + 1
        while j < n and (j - peak) <= max_tail_pixels and z[j] > tail_thresh:
            end = j
            j += 1

        events.append(InclusionEvent(
            line=line_number, start=run_start, peak=peak, end=end,
            peak_value=float(line[peak]), baseline_value=float(baseline[peak]),
        ))
        i = max(i, end + 1)

    # Clip each event's tail so it never overlaps the next event's core --
    # mirrors desmear.m's handling of closely-spaced peaks.
    for k in range(len(events) - 1):
        next_start = events[k + 1].start
        if events[k].end >= next_start:
            events[k].end = next_start - 1
            events[k].flags.append("clipped_by_next_event")

    for ev in events:
        if (ev.end - ev.peak) < min_tail_points:
            ev.flags.append("insufficient_tail_points")

    return events


def _aic_bic(n: int, rss: float, k: int) -> tuple[float, float]:
    """Same formula/convention as ``src.calibration.drift.select_order_by_aic``
    and ``src.deconvolution.esf._aic_bic`` -- ``rss`` here is the *weighted*
    residual sum of squares (see :func:`fit_event_tail`), the proper
    generalization when the weights represent inverse-variance.
    """
    rss = max(rss, 1e-12)
    aic = n * np.log(rss / n) + 2 * k
    bic = n * np.log(rss / n) + k * np.log(n)
    return float(aic), float(bic)


def _fit_single_weighted(t: np.ndarray, y: np.ndarray, weight: np.ndarray) -> tuple[float, float, float, np.ndarray, bool]:
    """Weighted single-exponential fit: ``baseline + amplitude*exp(-t/tau)``.
    Returns ``(tau, amplitude, baseline, predicted, success)``.
    """
    n_baseline = max(1, len(y) // 4)
    baseline0 = float(np.median(y[-n_baseline:]))
    amplitude0 = max(float(y[0] - baseline0), 1e-6)
    half = baseline0 + amplitude0 / 2.0
    below = np.where(y <= half)[0]
    tau0 = float(t[below[0]]) if len(below) else float(t[-1]) / 3.0
    tau0 = max(tau0, 1e-6)

    def residual(x):
        log_tau, amplitude, baseline = x
        tau = 10.0 ** log_tau
        return weight * (baseline + amplitude * np.exp(-t / tau) - y)

    result = least_squares(
        residual, x0=[np.log10(tau0), amplitude0, baseline0],
        bounds=([-9, 0, 0], [9, np.inf, np.inf]),
    )
    log_tau, amplitude, baseline = result.x
    tau = 10.0 ** log_tau
    predicted = baseline + amplitude * np.exp(-t / tau)
    return float(tau), float(amplitude), float(baseline), predicted, bool(result.success)


def _fit_double_weighted(
    t: np.ndarray, y: np.ndarray, weight: np.ndarray,
) -> tuple[float, float, float, float, float, np.ndarray, bool]:
    """Weighted double-exponential fit:
    ``baseline + A1*exp(-t/tau1) + A2*exp(-t/tau2)``. ``tau_a``/``tau_b``
    are unordered during optimization (interchangeable) and sorted after,
    same convention as ``esf._fit_double_exp``. Returns
    ``(tau_s, amplitude, tau2_s, amplitude2, baseline, predicted, success)``
    with ``tau_s`` the longer/slower (dominant) constant.

    Seeded sequentially rather than from a single blind guess spanning the
    window, because a joint 5-parameter fit with two time constants that
    can differ by orders of magnitude is easy to land in a bad local
    minimum (both components collapsing onto the same tau, say) starting
    cold: first fit a single exponential (:func:`_fit_single_weighted`,
    which the Poisson weighting naturally locks onto the *fast* component,
    since that is where most of the shot-noise-weighted signal lives),
    then fit a second single exponential to what is left over at late
    times (where the fast component has decayed away) to estimate the
    slow component. Those two estimates seed the joint optimization.
    """
    n_baseline = max(1, len(y) // 4)
    baseline0 = float(np.median(y[-n_baseline:]))

    tau_fast0, amp_fast0, base0, predicted_fast0, _ = _fit_single_weighted(t, y, weight)
    residual_late = y - (base0 + amp_fast0 * np.exp(-t / tau_fast0))
    late = t > 2 * tau_fast0
    if np.sum(late) >= 3 and np.any(residual_late[late] > 0):
        tau_slow0, amp_slow0, _, _, _ = _fit_single_weighted(
            t[late], np.clip(residual_late[late], 0, None), weight[late],
        )
        amp_slow0 = max(amp_slow0, 1e-6)
    else:
        tau_slow0 = max(float(t[-1] - t[0]), tau_fast0 * 10.0)
        amp_slow0 = 1e-6

    def residual(x):
        log_tau_a, aa, log_tau_b, ab, baseline = x
        tau_a, tau_b = 10.0 ** log_tau_a, 10.0 ** log_tau_b
        model = baseline + aa * np.exp(-t / tau_a) + ab * np.exp(-t / tau_b)
        return weight * (model - y)

    x0 = [np.log10(tau_fast0), amp_fast0, np.log10(tau_slow0), amp_slow0, base0]
    result = least_squares(
        residual, x0=x0,
        bounds=([-9, 0, -9, 0, 0], [9, np.inf, 9, np.inf, np.inf]),
    )
    log_tau_a, aa, log_tau_b, ab, baseline = result.x
    tau_a, tau_b = 10.0 ** log_tau_a, 10.0 ** log_tau_b
    if tau_a >= tau_b:
        tau_s, amp, tau2_s, amp2 = tau_a, aa, tau_b, ab
    else:
        tau_s, amp, tau2_s, amp2 = tau_b, ab, tau_a, aa
    predicted = baseline + aa * np.exp(-t / tau_a) + ab * np.exp(-t / tau_b)
    return float(tau_s), float(amp), float(tau2_s), float(amp2), float(baseline), predicted, bool(result.success)


def fit_event_tail(line: np.ndarray, event: InclusionEvent, dt_s: float, model: str = "auto") -> InclusionEvent:
    """Fits ``event``'s decay tail (``[peak+1, end]``), filling in
    ``tau_s``/``amplitude``/``fit_baseline``/``fit_model``/``fit_r_squared``/
    ``fit_success`` in place. A no-op (leaves the fit fields at their
    ``None``/``nan`` defaults) when the tail is too short -- see
    ``detect_events``'s ``min_tail_points``/``"insufficient_tail_points"``.

    Fits with **Poisson (shot-noise) weights**, not
    :func:`src.deconvolution.esf.fit_single_pulse_decay`'s unweighted
    linear-residual least squares -- deliberately, for a reason specific
    to this use case: an inclusion's peak-to-background contrast routinely
    spans several orders of magnitude (the whole reason it is worth
    decontaminating), and an *unweighted* fit is dominated by the handful
    of largest-absolute-value points -- in practice, just the first sample
    or two of the drop. Verified empirically against real inclusion tails
    (AH5C_1 Hf176/Hf178): an unweighted fit converges to a ``tau`` of about
    one sample interval, describing only the initial plunge and leaving
    the long, low-amplitude remainder of the tail -- the part that
    actually contaminates dozens of downstream pixels -- completely
    uncorrected.

    A first attempt fit this in log-signal space instead (a single
    exponential is a straight line there, so ordinary linear regression
    would do -- the same idea, independently arrived at, behind
    ``desmear.m``, the MATLAB prototype this module supersedes). That
    turned out to trade one bias for another: ``log(y)`` of noisy data is
    itself a biased estimator of ``log(E[y])`` once the noise is a
    non-negligible fraction of the signal (exactly the regime deep in the
    tail, near baseline), and discarding non-positive residuals before
    taking the log survivorship-biases what is left. Weighting each point
    of the *linear-space* fit by ``1/sqrt(max(y, 1))`` -- shot noise, the
    same Poisson-down-weighting rationale as the design spec's eq. (8) --
    fixes the original bias (low-count points can no longer dominate the
    fit) without introducing the log-domain one; verified against
    synthetic data spanning both a modest (~50x) and an extreme (~10^4x)
    peak/baseline contrast.

    A real inclusion's washout tail is not always a clean single
    exponential either -- AH5C_1's own zircon-in-garnet tails show a fast
    initial component plus a slower, low-amplitude remainder extending far
    longer. ``model="double"`` fits both components at once (same
    weighting, same two-pole idea as ``esf._fit_double_exp``);
    ``model="auto"`` (the default) fits both and accepts the double model
    only when it improves *both* AIC and BIC over the single fit -- same
    gating convention as ``esf.fit_single_pulse_decay`` -- so the extra
    two parameters have to earn their keep, not just reduce the residual
    by construction.

    Parameters
    ----------
    model : str, optional
        ``"single"``/``"double"`` force that model; ``"auto"`` (default)
        picks between them via the AIC/BIC gate described above.

    Returns
    -------
    InclusionEvent
        ``event`` itself (mutated and returned for convenient chaining).
    """
    if model not in ("single", "double", "auto"):
        raise ValueError(f"model must be 'single', 'double', or 'auto', got {model!r}.")
    if "insufficient_tail_points" in event.flags:
        return event

    tail_idx = np.arange(event.peak + 1, event.end + 1)
    t = (tail_idx - event.peak) * dt_s
    y = np.asarray(line, dtype=float)[tail_idx]
    weight = 1.0 / np.sqrt(np.clip(y, 1.0, None))
    n = len(y)

    tau, amplitude, baseline, predicted_single, success_single = _fit_single_weighted(t, y, weight)
    rss_single = float(np.sum((weight * (predicted_single - y)) ** 2))

    use_double = model == "double"
    tau_d = amp_d = tau2_d = amp2_d = base_d = predicted_double = success_double = None
    if model in ("double", "auto"):
        tau_d, amp_d, tau2_d, amp2_d, base_d, predicted_double, success_double = _fit_double_weighted(t, y, weight)
        if model == "auto" and success_double:
            rss_double = float(np.sum((weight * (predicted_double - y)) ** 2))
            aic_s, bic_s = _aic_bic(n, rss_single, k=3)
            aic_d, bic_d = _aic_bic(n, rss_double, k=5)
            use_double = aic_d < aic_s and bic_d < bic_s

    if use_double:
        event.tau_s, event.amplitude = tau_d, amp_d
        event.tau2_s, event.amplitude2 = tau2_d, amp2_d
        event.fit_baseline = base_d
        event.fit_model = "double"
        event.fit_success = bool(success_double)
        predicted = predicted_double
    else:
        event.tau_s, event.amplitude = tau, amplitude
        event.fit_baseline = baseline
        event.fit_model = "single"
        event.fit_success = success_single
        predicted = predicted_single

    rss = float(np.sum((y - predicted) ** 2))
    tss = float(np.sum((y - np.mean(y)) ** 2))
    event.fit_r_squared = 1.0 - rss / tss if tss > 0 else float("nan")
    if not event.fit_success:
        event.flags.append("tail_fit_did_not_converge")
    return event


def mark_coherent_events(
    events_by_line: dict[int, list[InclusionEvent]],
    position_tolerance: int = 3,
) -> None:
    """Flags each event ``coherent_across_lines`` when a same-position event
    is present in *every* neighboring line that exists (spec Sec 6.7 item
    3): a feature confined to one line, absent in both neighbors, bounds
    its cross-line extent below the line spacing and is a sub-spot
    inclusion; one that recurs in *at least one* neighboring line is a
    crack/vein/lamella and belongs in the smooth background, not the sparse
    point-source layer. Mutates ``events_by_line``'s events in place.

    Deliberately "any neighbor", not "every neighbor that exists": the row
    of a multi-line vein nearest to where the vein ends only matches on the
    side still inside the vein, not the side past its edge -- requiring
    both would misclassify that boundary row as an isolated inclusion. An
    edge line of the sample (no line on one side at all) naturally only has
    one neighbor to check, which this handles the same way -- a match
    there alone is already enough.

    Parameters
    ----------
    events_by_line : dict[int, list[InclusionEvent]]
        Keyed by line number (as recorded on each event by
        :func:`detect_events`'s ``line_number``), typically one entry per
        line actually scanned -- a line with no detected events need not
        have a key.
    position_tolerance : int, optional
        Two events "match" when their ``peak`` indices differ by no more
        than this many samples, by default 3 (a couple of pixels: dwell
        offsets between analytes and the finite spot footprint both shift
        the apparent peak slightly line to line for what is physically the
        same feature).
    """
    lines_present = set(events_by_line)
    for line_number, events in events_by_line.items():
        neighbors = [ln for ln in (line_number - 1, line_number + 1) if ln in lines_present]
        if not neighbors:
            continue
        for ev in events:
            matches_any_neighbor = any(
                abs(other.peak - ev.peak) <= position_tolerance
                for ln in neighbors
                for other in events_by_line[ln]
            )
            if matches_any_neighbor:
                ev.coherent_across_lines = True
                if "coherent_across_lines" not in ev.flags:
                    ev.flags.append("coherent_across_lines")


def merge_events(*event_lists: list[InclusionEvent], position_tolerance: int = 3) -> list[InclusionEvent]:
    """Combines events detected on several candidate trigger channels into
    one position-deduplicated list per line -- see the module docstring's
    "no single hardcoded trigger element" note: a mixed sample can contain
    more than one inclusion type (zircon revealed by Zr90, rutile by Ti47,
    say), each best localized on its own channel, without picking one
    element to detect every inclusion type on.

    Two events on *different* channels that land on (approximately) the
    same pixel are assumed to be the same physical inclusion seen through
    two trigger channels at once, and are collapsed to one -- keeping
    whichever has the larger ``peak_value`` (an arbitrary but consistent
    tie-break: the channel with the clearer signal is taken to have the
    more reliable window). Events on different lines, or far enough apart
    on the same line, are all kept.

    Parameters
    ----------
    *event_lists : list[InclusionEvent]
        One list per trigger channel, e.g. ``detect_events(zr90_line)``
        and ``detect_events(ti47_line)`` for the *same* line -- or, for
        multiple lines at once, each channel's flat concatenation of
        every line's events (grouping is by each event's own ``line``
        attribute, not by which positional list it came from).
    position_tolerance : int, optional
        Same meaning as :func:`mark_coherent_events`'s -- two events with
        ``peak`` indices within this many samples of each other, on the
        same line, are treated as one, by default 3.

    Returns
    -------
    list[InclusionEvent]
        Merged events, grouped by line then sorted by ``peak`` within each
        line.
    """
    by_line: dict[int, list[InclusionEvent]] = {}
    for events in event_lists:
        for ev in events:
            by_line.setdefault(ev.line, []).append(ev)

    merged: list[InclusionEvent] = []
    for line_number in sorted(by_line):
        candidates = sorted(by_line[line_number], key=lambda ev: ev.peak_value, reverse=True)
        kept: list[InclusionEvent] = []
        for ev in candidates:
            if any(abs(ev.peak - k.peak) <= position_tolerance for k in kept):
                continue
            kept.append(ev)
        merged.extend(sorted(kept, key=lambda ev: ev.peak))

    return merged


def subtract_event_tails(
    line: np.ndarray,
    events: list[InclusionEvent],
    dt_s: float,
    *,
    decontaminate_coherent: bool = False,
    redistribute_to_source: bool = True,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Subtracts each fitted event's tail (the excess above
    ``fit_baseline`` -- ``amplitude * exp(-t/tau)``, plus the second
    component when ``fit_model == "double"``) from ``line`` at its
    ``[peak+1, end]`` window.

    This decontaminates the *downstream* pixels a sub-spot inclusion's
    washout smeared into -- it does not touch ``[start, peak]`` at all, so
    the inclusion's own signal (what the laser actually recorded while on
    it) is never removed. By default (``redistribute_to_source=True``) the
    total amount subtracted from the tail is added back onto ``line`` at
    ``ev.peak`` -- the single best-estimate pixel for where the inclusion
    actually is -- so this is a *relocation* of washed-out mass back to
    its source, not a deletion: ``sum(corrected[peak:end+1]) ==
    sum(line[peak:end+1])`` for every successfully-fit, non-coherent event
    (up to the events-skip conditions below). This does not also attempt
    to undo the *rising* edge's smearing (spec eq. (4)'s ``K``/``Pi``
    terms -- a 2D spot-footprint deconvolution problem, not a per-line
    causal-tail one); the peak pixel is the best available single-pixel
    estimate of the source location, not a perfect one.

    Still unconstrained in the sense ``washout.py``'s ``invert_washout``
    is: a downstream pixel can go negative when the fitted tail overshoots
    the true remaining signal there, and this is reported via the
    returned negative count rather than silently clipped away.

    Parameters
    ----------
    line : numpy.ndarray
        The analyte's CPS series to correct, 1D.
    events : list[InclusionEvent]
        Typically :func:`detect_events`'s output after
        :func:`fit_event_tail` (and, if running across multiple lines,
        :func:`mark_coherent_events`) -- events without a successful fit
        (``fit_success`` False, or unfit entirely) are skipped.
    dt_s : float
        Sweep interval (seconds), the same value passed to
        :func:`fit_event_tail` -- ``tau_s``/``amplitude`` were fit against
        a ``t = (index - peak) * dt_s`` axis, so subtraction must rebuild
        that identical axis to stay in the units the fit was made in.
    decontaminate_coherent : bool, optional
        When ``False`` (default), events flagged
        ``coherent_across_lines`` are left uncorrected (spec Sec 6.7 item
        3 -- treat as background, not a point source). Set ``True`` to
        subtract them anyway (e.g. a caller that has already separately
        confirmed the coherent feature is still washout-contaminated, not
        real zoning).
    redistribute_to_source : bool, optional
        When ``True`` (default), each event's total subtracted mass is
        added back onto ``corrected[ev.peak]`` rather than discarded --
        see above. Set ``False`` to just remove the tail (e.g. for a
        diagnostic "how much washout was here" map, where re-adding it
        elsewhere would be misleading).

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray, int]
        ``(corrected, subtracted, negative_count)`` -- ``corrected`` is a
        new array (``line`` is not mutated), ``subtracted`` is the
        non-negative per-pixel amount removed from the tail (same shape,
        zero where nothing was subtracted -- *not* reduced by whatever was
        added back at the source), and ``negative_count`` is how many
        corrected samples went below zero.
    """
    line = np.asarray(line, dtype=float)
    corrected = line.copy()
    subtracted = np.zeros_like(line)

    for ev in events:
        if not ev.fit_success or ev.tau_s is None or ev.amplitude is None:
            continue
        if ev.coherent_across_lines and not decontaminate_coherent:
            continue

        tail_idx = np.arange(ev.peak + 1, ev.end + 1)
        if len(tail_idx) == 0:
            continue
        t = (tail_idx - ev.peak) * dt_s
        tail_model = ev.amplitude * np.exp(-t / ev.tau_s)
        if ev.fit_model == "double" and ev.tau2_s is not None and ev.amplitude2 is not None:
            tail_model = tail_model + ev.amplitude2 * np.exp(-t / ev.tau2_s)

        corrected[tail_idx] -= tail_model
        subtracted[tail_idx] += tail_model
        if redistribute_to_source:
            corrected[ev.peak] += float(np.sum(tail_model))

    return corrected, subtracted, int(np.sum(corrected < 0))


@dataclass
class InclusionDecontaminationResult:
    """Result of running the full detect -> fit -> discriminate -> subtract
    pipeline (:func:`decontaminate_inclusions`) over one analyte's set of
    line scans.

    Attributes
    ----------
    corrected : list[numpy.ndarray]
        One corrected array per input line, same order/shapes as the input.
    subtracted : list[numpy.ndarray]
        Per-line, non-negative amount removed (same shapes as ``corrected``).
    events_by_line : dict[int, list[InclusionEvent]]
        Every detected event (including ones left uncorrected, e.g.
        ``coherent_across_lines`` or an unfit tail), keyed by line number --
        the full audit trail, not just what got subtracted.
    negative_count : int
        Total corrected samples that went below zero, summed over all
        lines.
    """

    corrected: list[np.ndarray]
    subtracted: list[np.ndarray]
    events_by_line: dict[int, list["InclusionEvent"]]
    negative_count: int


def decontaminate_inclusions(
    lines: list[np.ndarray],
    dt_s: float,
    *,
    threshold: float = 5.0,
    tail_threshold_fraction: float = 0.2,
    baseline_half_window: int = 40,
    max_tail_pixels: int = 60,
    min_tail_points: int = 4,
    min_prominence: float = 0.0,
    position_tolerance: int = 3,
    decontaminate_coherent: bool = False,
    redistribute_to_source: bool = True,
    model: str = "auto",
) -> InclusionDecontaminationResult:
    """Runs the full Sec 6.7 pipeline for one analyte's complete set of
    line scans: detect events on every line, fit each event's decay tail,
    flag events that recur in a neighboring line as coherent (crack/vein,
    not a sub-spot inclusion), then subtract the rest.

    Parameters
    ----------
    lines : list[numpy.ndarray]
        One 1D CPS array per line, in scan order (``lines[i]`` is the line
        at index ``i`` -- interline discrimination compares each line only
        against ``i-1``/``i+1``, so the order must be the actual scan
        order, not e.g. sorted by something else).
    dt_s : float
        Sweep interval (seconds), shared by every line (this module does
        not support a per-line ``dt_s``; resample first if that ever
        differs within one sample).
    threshold, tail_threshold_fraction, baseline_half_window,
    max_tail_pixels, min_tail_points, min_prominence : see :func:`detect_events`.
    position_tolerance : see :func:`mark_coherent_events`.
    decontaminate_coherent, redistribute_to_source, model : see
        :func:`subtract_event_tails` / :func:`fit_event_tail`.

    Returns
    -------
    InclusionDecontaminationResult
    """
    events_by_line: dict[int, list[InclusionEvent]] = {}
    for line_number, line in enumerate(lines):
        events = detect_events(
            line, line_number=line_number, threshold=threshold,
            tail_threshold_fraction=tail_threshold_fraction,
            baseline_half_window=baseline_half_window,
            max_tail_pixels=max_tail_pixels, min_tail_points=min_tail_points,
            min_prominence=min_prominence,
        )
        for ev in events:
            fit_event_tail(line, ev, dt_s, model=model)
        if events:
            events_by_line[line_number] = events

    mark_coherent_events(events_by_line, position_tolerance=position_tolerance)

    corrected: list[np.ndarray] = []
    subtracted: list[np.ndarray] = []
    negative_count = 0
    for line_number, line in enumerate(lines):
        events = events_by_line.get(line_number, [])
        c, s, neg = subtract_event_tails(
            line, events, dt_s, decontaminate_coherent=decontaminate_coherent,
            redistribute_to_source=redistribute_to_source,
        )
        corrected.append(c)
        subtracted.append(s)
        negative_count += neg

    return InclusionDecontaminationResult(
        corrected=corrected, subtracted=subtracted,
        events_by_line=events_by_line, negative_count=negative_count,
    )


def apply_events_to_line(
    line: np.ndarray,
    events: list[InclusionEvent],
    dt_s: float,
    *,
    model: str = "auto",
    decontaminate_coherent: bool = False,
    redistribute_to_source: bool = True,
) -> tuple[np.ndarray, np.ndarray, list[InclusionEvent], int]:
    """Reuses event *windows* detected on another analyte (a "trigger"
    channel -- e.g. Zr90 localizing a zircon inclusion) to decontaminate
    ``line`` (a different analyte, e.g. Hf176/Hf178, elevated by washout
    from that same inclusion): re-fits each event's decay against
    ``line``'s own data in the same ``[peak+1, end]`` window (amplitude and
    tau are analyte-specific and must not be copied across channels), then
    subtracts.

    Does not mutate the events passed in -- returns fresh copies (so the
    same trigger-channel events can be reused across several analytes
    without one channel's fit results leaking into another's).

    Parameters
    ----------
    line : numpy.ndarray
        The analyte's CPS series to correct, 1D -- same line/length the
        trigger channel's ``events`` were detected on.
    events : list[InclusionEvent]
        Typically one line's worth of events from another analyte's
        :func:`detect_events` (with :func:`mark_coherent_events` already
        applied, if wanted -- ``coherent_across_lines`` carries over as-is
        since it's a spatial, not per-analyte, property).
    dt_s, model, decontaminate_coherent, redistribute_to_source : see
        :func:`fit_event_tail` / :func:`subtract_event_tails`.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray, list[InclusionEvent], int]
        ``(corrected, subtracted, refit_events, negative_count)``.
    """
    refit_events = [copy.deepcopy(ev) for ev in events]
    for ev in refit_events:
        ev.tau_s = ev.amplitude = ev.tau2_s = ev.amplitude2 = ev.fit_baseline = ev.fit_model = None
        ev.fit_r_squared = float("nan")
        ev.fit_success = False
        fit_event_tail(line, ev, dt_s, model=model)

    corrected, subtracted, negative_count = subtract_event_tails(
        line, refit_events, dt_s, decontaminate_coherent=decontaminate_coherent,
        redistribute_to_source=redistribute_to_source,
    )
    return corrected, subtracted, refit_events, negative_count
