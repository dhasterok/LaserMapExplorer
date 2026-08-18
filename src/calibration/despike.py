"""Raw-signal despiking filters.

Ported from `latools <https://github.com/oscarbranson/latools>`_ (Branson)
rather than taken on as a runtime dependency -- latools is unmaintained
(last release ~2021, needed dependency workarounds to even import in a
current environment) and its own calibration methodology (internal-standard
ratio normalization) is a different measurement geometry from this module's
direct CPS-to-ppm calibration, so a full adoption isn't a good fit. Its
despiking filters, however, are a self-contained, generically useful
pre-processing step, worth having natively.

Two independent filters, matching latools' own two filters:

- :func:`noise_despike` -- a rolling-window, Poisson-consistent spike
  filter. Catches isolated single-sweep spikes/dropouts that don't fit the
  local rolling mean plus its Poisson-scale noise band. This is the one
  latools itself enables by default.
- :func:`expdecay_despike` -- an exponential-decay washout filter. Catches
  values physically impossible given the laser cell's washout time. This
  one is off by default in latools, and requires an explicit ``exponent``
  here -- latools can auto-fit one from a standard's washout tail
  (``find_expcoef``), but that routine is entangled with latools' own
  signal/background boundary detection (``autorange``) and hasn't been
  ported; supply a known/measured decay exponent (1/s, negative) for this
  instrument/cell instead.

Both operate on a single analyte's raw CPS series (one file, one column)
and return a cleaned copy -- callers decide when/whether to apply them
(see ``pipeline.run``'s ``despike_noise``/``despike_expdecay`` options).
"""
from __future__ import annotations

import numpy as np


def noise_despike(values: np.ndarray, window: int = 3, nlim: float = 12.0, maxiter: int = 4) -> np.ndarray:
    """Replaces rows whose value exceeds a rolling-mean-plus-Poisson-noise
    band with that local rolling mean, iterating until stable (or
    ``maxiter``).

    ``rolling_std = sqrt(rolling_mean)`` -- the Poisson count-statistics
    approximation latools itself uses (treating the CPS values numerically
    as if they were counts, rather than converting via dwell time/tau).
    Combined with a loose ``nlim`` (12 rolling-std by default), this is
    meant to catch only extreme, physically implausible spikes, not to be
    a precise statistical test.

    Edge rows (within ``window // 2`` of either end, where the rolling
    window doesn't fully overlap the data) are never flagged. Requires at
    least ``window`` points; shorter arrays are returned unchanged.

    Returns a cleaned copy -- ``values`` itself is not modified.
    """
    sig = np.array(values, dtype=float, copy=True)
    n = len(sig)
    win = window if window % 2 == 1 else window + 1
    if n < win:
        return sig

    npad = (win - 1) // 2
    kernel = np.ones(win) / win

    over = np.ones(n, dtype=bool)
    over[:npad] = False
    if npad > 0:
        over[-npad:] = False

    loops = 0
    while over.any() and loops < maxiter:
        rmean = np.convolve(sig, kernel, "valid")
        rstd = rmean ** 0.5
        over[npad:n - npad] = sig[npad:n - npad] > rmean + nlim * rstd
        if not over.any():
            break
        sig[npad:n - npad][over[npad:n - npad]] = rmean[over[npad:n - npad]]
        loops += 1
    return sig


def expdecay_despike(values: np.ndarray, tstep: float, exponent: float, maxiter: int = 3) -> np.ndarray:
    """Replaces rows that jump beyond what the laser cell's washout decay
    (``exponent``, 1/s, negative) could physically explain relative to
    their immediate neighbour, with that neighbour's value, iterating
    until stable (or ``maxiter``).

    The initial noise estimate is built from the first up-to-50 points
    (matching latools: start from the first 5, widen to 10/20/30/50 only
    while doing so doesn't inflate the estimate by more than 50% -- avoids
    the estimate itself being contaminated by the ablation onset). Requires
    at least 6 points; shorter arrays are returned unchanged.

    Returns a cleaned copy -- ``values`` itself is not modified.
    """
    sig = np.array(values, dtype=float, copy=True)
    n = len(sig)
    if n < 6:
        return sig

    noise = float(np.std(sig[:5]))
    for i in (10, 20, 30, 50):
        if i >= n:
            break
        inoise = float(np.std(sig[:i]))
        if inoise < 1.5 * noise:
            noise = inoise
    rms_noise3 = 3 * noise

    loops = 0
    changed = True
    while loops < maxiter and changed:
        siglo = np.roll(sig * np.exp(tstep * exponent), 1)
        sighi = np.roll(sig * np.exp(-tstep * exponent), -1)

        loind = (sig < siglo - rms_noise3) & (sig < np.roll(sig, -1) - rms_noise3)
        hiind = (sig > sighi + rms_noise3) & (sig > np.roll(sig, 1) + rms_noise3)

        sig[loind] = sig[np.roll(loind, -1)]
        sig[hiind] = sig[np.roll(hiind, -1)]

        changed = bool(np.any(loind) or np.any(hiind))
        loops += 1
    return sig
