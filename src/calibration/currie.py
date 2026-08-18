"""Currie (1968) detection-limit statistics: critical level L_C and detection
limit L_D, in net counts above background. Two distinct thresholds:

- L_C (critical level): the decision threshold -- a net signal above L_C is
  called a detection, controlling the false-positive rate at alpha.
- L_D (detection limit): the smallest TRUE signal detected with probability
  1-beta -- always larger than L_C, since it also has to survive a
  false-negative constraint. Uses the asymptotic Gaussian-derived formula
  throughout its whole range (not the exact-Poisson inversion L_C switches
  to near zero) -- that's what keeps the textbook constant term (2.71 counts
  at alpha=beta=0.05) correct even at mu_b=0 exactly.

Callers scale background rate x sample counting time to get mu_b (expected
background counts in the *sample's* integration window) before calling in
here -- this module is pure statistics, no knowledge of CPS/tau conversion
beyond the final convenience bundle (:func:`compute_currie_limits`).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import chi2, norm, poisson

_GAUSSIAN_REGIME_THRESHOLD = 20.0  # mu_b at/above this: Gaussian approx is adequate for L_C

# Textbook rounded constants (Currie 1968) for the standard alpha=beta=0.05 case --
# used verbatim rather than derived from z-values so results match the
# well-known published numbers exactly, not just asymptotically.
_L_C_COEFF_ALPHA05 = 2.33
_L_D_CONST_ALPHA05_BETA05 = 2.71
_L_D_COEFF_ALPHA05_BETA05 = 4.65


@dataclass
class CurrieLimits:
    mu_b_counts: float
    L_C_counts: float
    L_D_counts: float
    L_C_cps: float
    L_D_cps: float
    tau_s: float


def critical_level(mu_b_counts: float, alpha: float = 0.05) -> float:
    """L_C in net counts: smallest net signal called a detection at false-positive rate alpha.

    Gaussian approximation for mu_b large enough for it to be valid; exact
    Poisson-CDF inversion (smallest n with P(N>=n | mu_b) < alpha) near zero,
    where the Gaussian approximation breaks down.
    """
    if mu_b_counts >= _GAUSSIAN_REGIME_THRESHOLD:
        if alpha == 0.05:
            return float(_L_C_COEFF_ALPHA05 * np.sqrt(mu_b_counts))
        return float(norm.ppf(1 - alpha) * np.sqrt(2 * mu_b_counts))

    n = 0
    while poisson.sf(n - 1, mu_b_counts) >= alpha:
        n += 1
    return float(n)


def detection_limit(mu_b_counts: float, alpha: float = 0.05, beta: float = 0.05) -> float:
    """L_D in net counts (Currie 1968): smallest true signal detected with probability 1-beta.

    Always uses the asymptotic Gaussian-derived form (``2*L_C_gaussian +
    z_beta**2``), even where :func:`critical_level` itself has switched to
    the exact near-zero branch -- see module docstring.
    """
    if alpha == 0.05 and beta == 0.05:
        return float(_L_D_CONST_ALPHA05_BETA05 + _L_D_COEFF_ALPHA05_BETA05 * np.sqrt(mu_b_counts))
    l_c_gaussian = norm.ppf(1 - alpha) * np.sqrt(2 * mu_b_counts)
    z_beta = norm.ppf(1 - beta)
    return float(2 * l_c_gaussian + z_beta ** 2)


def garwood_ci(total_counts: int, total_tau_s: float, alpha: float = 0.05) -> tuple[float, float]:
    """Exact (Garwood 1936) confidence interval for a pooled Poisson rate
    (counts/s), given total observed counts N over total counting time T.

    Never degenerate -- an all-zero observation still gives a nonzero upper
    bound (~3.0/T at alpha=0.05), unlike a Gaussian SE=0 for the same input.
    """
    n, t = total_counts, total_tau_s
    lower = chi2.ppf(alpha / 2, 2 * n) / (2 * t) if n > 0 else 0.0
    upper = chi2.ppf(1 - alpha / 2, 2 * n + 2) / (2 * t)
    return float(lower), float(upper)


def compute_currie_limits(mu_b_counts: float, tau_s: float, alpha: float = 0.05, beta: float = 0.05) -> CurrieLimits:
    """Bundles L_C/L_D in both counts and CPS for one analyte's background."""
    l_c = critical_level(mu_b_counts, alpha=alpha)
    l_d = detection_limit(mu_b_counts, alpha=alpha, beta=beta)
    return CurrieLimits(
        mu_b_counts=mu_b_counts, L_C_counts=l_c, L_D_counts=l_d,
        L_C_cps=l_c / tau_s, L_D_cps=l_d / tau_s, tau_s=tau_s,
    )
