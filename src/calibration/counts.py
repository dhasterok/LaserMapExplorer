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
    """An analyte's effective per-value counting time and how it was obtained.

    Attributes
    ----------
    tau_s : float or None
        Effective counting time per reported value, in seconds. ``None``
        only when ``provenance == "unknown"``.
    provenance : {"metadata", "inferred", "bounded", "unknown"}
        How ``tau_s`` was determined -- see :func:`resolve_tau`.
    quantum_cps : float or None, optional
        Estimated elementary CPS step ``Delta = 1 / tau``, retained for QC
        display. Set only when ``provenance == "inferred"``.
    """

    tau_s: float | None
    provenance: str              # "metadata" | "inferred" | "bounded" | "unknown"
    quantum_cps: float | None = None   # estimated Delta = 1/tau, for QC display


def estimate_quantum(
    cps, dmin: float = 0.1, dmax: float = 200.0, nsteps: int = 20000,
    score_tol: float = 1e-6, max_best_score: float = 0.01,
) -> float | None:
    """Estimate the elementary CPS step ``Delta = 1 / tau`` from quantized data.

    Parameters
    ----------
    cps : array_like
        Reported counts-per-second values for one analyte. Only strictly
        positive values are used.
    dmin : float, optional
        Smallest candidate ``Delta`` in the grid search, by default ``0.1``.
    dmax : float, optional
        Largest candidate ``Delta`` in the grid search, by default
        ``200.0``.
    nsteps : int, optional
        Number of geometrically spaced candidates between ``dmin`` and
        ``dmax``, by default ``20000``.
    score_tol : float, optional
        Absolute width of the "near-minimal" score band used to pick the
        largest compatible candidate, by default ``1e-6``.
    max_best_score : float, optional
        Reject the search (return ``None``) if even the best candidate's
        mean squared fractional deviation exceeds this, by default ``0.01``.

    Returns
    -------
    float or None
        The largest candidate ``Delta`` achieving a near-minimal score, or
        ``None`` if fewer than three positive values are available or the
        data does not look genuinely quantized.

    Notes
    -----
    Grid-searches candidate deltas, scoring each by mean squared fractional
    deviation of ``cps / delta`` from the nearest integer. Multiple deltas
    can score near-zero at once (harmonics: if ``Delta`` fits, so do
    ``Delta/2``, ``Delta/3``, ...) -- the true quantum is the *largest*
    candidate achieving a near-minimal score, since every integer multiple
    of ``Delta`` is also an integer multiple of ``Delta/m``.

    ``score_tol`` is an absolute floor on the near-minimal band, not a
    multiple of the best score: with sparse/small integer counts the true
    quantum's best-achievable score is often itself ~0 to floating-point
    precision, at which point a relative band collapses to nothing and
    excludes the true quantum's own nearest grid point.

    ``max_best_score`` guards against a genuinely smooth (non-quantized)
    channel still returning whichever grid delta scored least badly. A
    random continuous-valued channel's best achievable score is ~``1/12``
    (mean squared distance to the nearest integer for uniformly distributed
    fractional parts) -- ``0.01`` sits comfortably below that while well
    above the near-zero scores genuine quantization produces.
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
    """Determine an analyte's effective per-value counting time and its provenance.

    Parameters
    ----------
    cps : array_like
        Reported counts-per-second values for one analyte.
    dwell_time_ms : float or None, optional
        Per-analyte dwell time from instrument metadata, in milliseconds.
        Must be given together with ``sweeps_per_reading`` to take the
        exact ``"metadata"`` path.
    sweeps_per_reading : int or None, optional
        Number of sweeps averaged into each reported value, from instrument
        metadata.
    max_tau_s : float, optional
        Largest plausible ``tau``; nonzero CPS values below ``1 / max_tau_s``
        are treated as noise and excluded from the ``"bounded"`` lower
        bound. By default ``60.0``.

    Returns
    -------
    TauEstimate
        The resolved counting time and its provenance:

        - ``"metadata"`` -- both ``dwell_time_ms`` and ``sweeps_per_reading``
          supplied; ``tau_s = (dwell_time_ms / 1000) * sweeps_per_reading``.
        - ``"inferred"`` -- no metadata, but the quantization step is
          confidently estimable from the data (see :func:`estimate_quantum`).
        - ``"bounded"`` -- quantization not cleanly estimable, but
          ``tau_s >= 1 / min(cps > 0)`` gives a conservative lower bound.
        - ``"unknown"`` -- no metadata and no usable nonzero values;
          ``tau_s`` is ``None``.

    Notes
    -----
    ``max_tau_s`` guards the ``"bounded"`` branch: exported data sometimes
    carries a stray near-zero (floating-point residue, not a genuine
    sub-quantum count) alongside otherwise-clean zeros. A plain
    ``1 / nonzero.min()`` would let one row with ``cps = 4.7e-6`` imply
    ``tau ~ 212,766 s`` and, fed back through :func:`cps_to_counts`, inflate
    that row's recovered count by 5-6 orders of magnitude. No real
    LA-ICP-MS ``dwell * sweeps`` setting approaches ``60`` seconds, so
    smaller nonzero values are excluded from the bound.
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

    Parameters
    ----------
    cps : array_like
        Reported counts-per-second values for one analyte.
    tau : TauEstimate
        Effective counting time and its provenance, from
        :func:`resolve_tau`.

    Returns
    -------
    numpy.ndarray or None
        Non-negative integer counts, ``round(cps * tau.tau_s)`` clipped at
        zero, with the same shape as ``cps``. ``None`` when
        ``tau.tau_s is None`` (``provenance == "unknown"``).

    Notes
    -----
    Exact when ``tau.provenance`` is ``"metadata"`` or ``"inferred"`` (a
    validated quantum); a rounded approximation for ``"bounded"`` -- still a
    usable Poisson-GLM input per the spec's degraded-mode guidance, just
    with wider effective uncertainty.
    """
    if tau.tau_s is None:
        return None
    n = np.round(np.asarray(cps, dtype=float) * tau.tau_s)
    return np.clip(n, 0, None).astype(int)
