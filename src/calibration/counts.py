"""Recovering integer counts from reported CPS, for the Poisson-statistics
background treatment (see ``poisson_drift.py``, ``currie.py``).

Many trace-element channels report CPS = n/tau for small integer n (one, two,
three ion-counting events per reading) -- individual Poisson events, not
continuous Gaussian noise. When tau (the effective counting time per
reported value) isn't known from instrument metadata, it can often be
recovered from the data itself: every reported value is an integer multiple
of the elementary step Delta = 1/tau, visible as quantization in low-count
channels.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

VALID_PROVENANCE = {"metadata", "inferred", "bounded", "unknown"}


@dataclass
class TauEstimate:
    tau_s: float | None
    provenance: str              # "metadata" | "inferred" | "bounded" | "unknown"
    quantum_cps: float | None = None   # estimated Delta = 1/tau, for QC display


def estimate_quantum(
    cps, dmin: float = 0.1, dmax: float = 200.0, nsteps: int = 20000,
    score_tol: float = 1e-6, max_best_score: float = 0.01,
) -> float | None:
    """Estimates the elementary CPS step Delta = 1/tau from quantized data.

    Grid-searches candidate deltas, scoring each by mean squared fractional
    deviation of ``cps / delta`` from the nearest integer. Multiple deltas
    can score near-zero at once (harmonics: if Delta fits, so do Delta/2,
    Delta/3, ...) -- the true quantum is the *largest* candidate achieving a
    near-minimal score, since a sub-harmonic is always spuriously
    "compatible" too (every integer multiple of Delta is also an integer
    multiple of Delta/m).

    ``score_tol`` is an absolute floor on the "near-minimal" band, not a
    multiple of the best score: with sparse/small integer counts the true
    quantum's best-achievable score is often itself ~0 to floating-point
    precision, at which point a relative band collapses to nothing and
    excludes the true quantum's own nearest grid point (whose score is only
    a very small nonzero value away from a coincidentally-perfect but wrong
    tiny candidate). An absolute floor avoids that failure mode.

    ``max_best_score`` rejects the search entirely (returns ``None``) when
    even the *best* candidate doesn't fit well -- without this, a channel
    with genuinely smooth/continuous (non-quantized) values would still get
    *some* grid delta returned (whichever happened to score least-badly),
    silently claiming a confident "inferred" quantum where none really
    exists. A random continuous-valued channel's best achievable score is
    ~1/12 (mean squared distance to the nearest integer for uniformly
    distributed fractional parts) -- 0.01 sits comfortably below that while
    still well above the near-zero scores genuine quantization produces.

    Returns ``None`` if there are too few nonzero values to estimate from,
    or if quantization doesn't look genuinely present in the data (only
    meaningful when it's actually visible -- i.e. the low-count regime this
    whole module exists for).
    """
    v = np.asarray(cps, dtype=float)
    v = v[v > 0]
    if len(v) < 3:
        return None

    deltas = np.geomspace(dmin, dmax, nsteps)
    r = v[:, None] / deltas[None, :]
    frac = r - np.round(r)
    scores = np.mean(frac ** 2, axis=0)

    best = float(scores.min())
    if best > max_best_score:
        return None

    good = scores <= best + score_tol
    return float(deltas[good].max())


def resolve_tau(
    cps, dwell_time_ms: float | None = None, sweeps_per_reading: int | None = None, max_tau_s: float = 60.0,
) -> TauEstimate:
    """Determines an analyte's effective per-value counting time and its provenance.

    - ``"metadata"``: both ``dwell_time_ms`` and ``sweeps_per_reading`` supplied
      (see ``geometry.InstrumentSettings``) -- exact, no estimation needed.
    - ``"inferred"``: no metadata, but the quantization step is confidently
      estimable from this analyte's own data (see :func:`estimate_quantum`).
    - ``"bounded"``: quantization isn't cleanly estimable, but the smallest
      nonzero CPS value gives a conservative lower bound on tau (the true
      quantum can't be larger than the smallest observed nonzero value, so
      ``tau >= 1 / min(cps > 0)``).
    - ``"unknown"``: no metadata, no nonzero values to infer or bound from.

    ``max_tau_s`` guards the ``"bounded"`` branch specifically: real exported
    data sometimes carries a stray near-zero-but-not-exactly-zero value
    (floating-point residue from upstream processing, not a genuine
    sub-quantum count) alongside otherwise-clean zeros. Unlike
    :func:`estimate_quantum`'s grid search -- whose fractional-deviation
    scoring is naturally insensitive to a single such value, since dividing
    it by any candidate delta rounds to ~0 with near-zero deviation
    regardless of delta, so it doesn't preferentially favor a wrong one --
    a plain ``1 / nonzero.min()`` has no such protection: one row with
    ``cps=4.7e-6`` implies ``tau ~ 212,766s`` and, fed back through
    :func:`cps_to_counts`, inflates that single row's *own* recovered count
    by 5-6 orders of magnitude (confirmed: a lone real single-count event
    that should recover as 1 count instead recovered as ~760,000). No real
    LA-ICP-MS dwell*sweeps setting is anywhere near that -- ``60`` seconds
    is already far more generous than any plausible instrument
    configuration, so any nonzero value smaller than ``1/max_tau_s`` is
    excluded from the bound (treated as noise, not signal) rather than
    trusted as the smallest genuine count.
    """
    if dwell_time_ms is not None and sweeps_per_reading is not None:
        tau_s = (dwell_time_ms / 1000.0) * sweeps_per_reading
        return TauEstimate(tau_s=tau_s, provenance="metadata")

    quantum = estimate_quantum(cps)
    if quantum is not None and quantum > 0:
        return TauEstimate(tau_s=1.0 / quantum, provenance="inferred", quantum_cps=quantum)

    v = np.asarray(cps, dtype=float)
    min_plausible_cps = 1.0 / max_tau_s
    nonzero = v[v >= min_plausible_cps]
    if len(nonzero) > 0:
        return TauEstimate(tau_s=1.0 / float(nonzero.min()), provenance="bounded")

    return TauEstimate(tau_s=None, provenance="unknown")


def cps_to_counts(cps, tau: TauEstimate) -> np.ndarray | None:
    """Best-effort integer-count recovery given a :class:`TauEstimate`.

    Exact when ``tau.provenance`` is ``"metadata"``/``"inferred"`` (a
    validated quantum); a rounded approximation for ``"bounded"`` (still a
    usable Poisson-GLM input per the spec's degraded-mode guidance, just
    with wider effective uncertainty). Returns ``None`` only when ``tau``
    itself is unavailable (``"unknown"``).
    """
    if tau.tau_s is None:
        return None
    n = np.round(np.asarray(cps, dtype=float) * tau.tau_s)
    return np.clip(n, 0, None).astype(int)
