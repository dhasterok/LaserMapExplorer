"""Recursive exact inverse for a single-exponential washout response --
spec eq. (6)-(7). This is the Stage 3 "fast path": a closed-form two-tap
FIR inverse, not an iterative solve through ``operator.py``'s
``ForwardOperator`` (that's the Stage 4 Poisson-RL job, a later pass).

Unconstrained by design (spec Sec 6.3): it will produce negative counts
wherever a large-contrast tail is subtracted from a low-abundance phase.
That's expected and reported (``WashoutCorrectionResult.negative_count``/
``flags``), never silently clipped -- per the design spec's explicit
requirement (Sec 10) that this failure mode be surfaced, not hidden.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class WashoutCorrectionResult:
    corrected: np.ndarray
    noise_amplification: float          # eq. (7): Var(u_hat)/Var(m), white-noise approximation
    negative_count: int                  # samples that went negative after inversion
    flags: list[str] = field(default_factory=list)


def invert_washout(signal: np.ndarray, tau_s: float, dt_s: float) -> WashoutCorrectionResult:
    """Exactly inverts a causal single-exponential washout response
    (eq. 6): ``u[n] = (m[n] - a*m[n-1]) / (1-a)``, ``a = exp(-dt_s/tau_s)``.

    Boundary: there is no ``m[-1]`` for the line's first sample, so
    ``u[0]`` is set to ``m[0]`` (steady-state/pre-equilibrated assumption --
    the spec's alternative, an explicit equilibration prefix, requires
    context this per-line array doesn't carry) and flagged
    ``"first_sample_boundary_assumed"`` so callers can mask or discount it
    rather than treating it as an equally-reliable inverted value.

    Direction-agnostic: for a line scanned in the reverse direction, flip
    ``signal`` before calling this and flip the result back -- see
    ``pipeline.py``'s per-line orchestration, which handles the
    ``bidirectional_scan`` flip so this function stays a pure 1D operation.
    """
    if tau_s <= 0 or dt_s <= 0:
        raise ValueError(f"tau_s and dt_s must be positive, got tau_s={tau_s!r}, dt_s={dt_s!r}.")
    signal = np.asarray(signal, dtype=float)
    if signal.ndim != 1:
        raise ValueError(f"signal must be 1D, got shape {signal.shape!r}.")

    a = np.exp(-dt_s / tau_s)
    u = np.empty_like(signal)
    u[0] = signal[0]
    if len(signal) > 1:
        u[1:] = (signal[1:] - a * signal[:-1]) / (1.0 - a)

    noise_amplification = (1.0 + a**2) / (1.0 - a) ** 2
    negative_count = int(np.sum(u < 0))

    flags = ["first_sample_boundary_assumed"]
    if negative_count > 0:
        flags.append("negative_counts")

    return WashoutCorrectionResult(
        corrected=u, noise_amplification=noise_amplification,
        negative_count=negative_count, flags=flags,
    )
