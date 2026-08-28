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
    """Replace rolling-mean outliers in a raw CPS series with the local mean.

    Parameters
    ----------
    values : numpy.ndarray
        One analyte's raw CPS series (one file, one column).
    window : int, optional
        Rolling-window width in samples, by default ``3``. Forced to the
        next odd number if given even.
    nlim : float, optional
        Number of rolling standard deviations above the rolling mean beyond
        which a row is flagged as a spike, by default ``12.0``.
    maxiter : int, optional
        Maximum number of flag-and-replace passes, by default ``4``.

    Returns
    -------
    numpy.ndarray
        A cleaned copy; flagged rows are set to the local rolling mean.
        ``values`` itself is not modified. Arrays shorter than ``window``
        are returned unchanged.

    Notes
    -----
    ``rolling_std = sqrt(rolling_mean)`` -- the Poisson count-statistics
    approximation latools itself uses (treating the CPS values numerically
    as if they were counts, rather than converting via dwell time/tau).
    Combined with a loose ``nlim``, this is meant to catch only extreme,
    physically implausible spikes, not to be a precise statistical test.
    Edge rows (within ``window // 2`` of either end) are never flagged.
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
    """Replace rows that decay faster than the cell washout physically allows.

    Parameters
    ----------
    values : numpy.ndarray
        One analyte's raw CPS series (one file, one column).
    tstep : float
        Time between successive samples, in seconds.
    exponent : float
        Laser-cell washout decay exponent, in 1/s (negative). A
        known/measured value for this instrument and cell; not auto-fit
        here.
    maxiter : int, optional
        Maximum number of flag-and-replace passes, by default ``3``.

    Returns
    -------
    numpy.ndarray
        A cleaned copy; a row that jumps beyond what ``exponent`` could
        explain relative to its immediate neighbour is set to that
        neighbour's value. ``values`` itself is not modified. Arrays with
        fewer than 6 points are returned unchanged.

    Notes
    -----
    The initial noise estimate is built from the first up-to-50 points
    (matching latools: start from the first 5, widen to 10/20/30/50 only
    while doing so does not inflate the estimate by more than 50%, which
    avoids the estimate being contaminated by the ablation onset).
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
