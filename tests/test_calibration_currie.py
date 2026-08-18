"""Currie detection-limit statistics -- hand-derivable cases.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.stats import chi2

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.currie import (
    compute_currie_limits,
    critical_level,
    detection_limit,
    garwood_ci,
)


def test_critical_level_gaussian_regime():
    assert critical_level(mu_b_counts=100, alpha=0.05) == pytest.approx(2.33 * np.sqrt(100), rel=1e-6)


def test_detection_limit_gaussian_regime():
    assert detection_limit(mu_b_counts=25, alpha=0.05, beta=0.05) == pytest.approx(2.71 + 4.65 * np.sqrt(25), rel=1e-6)


def test_detection_limit_constant_term_at_zero_background():
    # The constant term matters even at mu_b=0 exactly (spec's key point):
    # L_D = 2.71 counts, not zero, since a nonzero signal still has to clear
    # a real false-negative margin even with a perfectly known background.
    l_d = detection_limit(mu_b_counts=0.0, alpha=0.05, beta=0.05)
    assert l_d == pytest.approx(2.71, rel=1e-6)
    assert np.isfinite(l_d)


def test_critical_level_near_zero_uses_exact_poisson_inversion():
    # Near mu_b=0, critical_level must stay finite and use the exact branch
    # (not the Gaussian formula, which would give ~0 and false-positive constantly).
    l_c = critical_level(mu_b_counts=0.0, alpha=0.05)
    assert np.isfinite(l_c)
    assert l_c >= 0


def test_garwood_ci_all_zero_observation_is_not_degenerate():
    # Exact two-sided (1-alpha) Garwood interval: upper tail uses alpha/2, so
    # at alpha=0.05 this is chi2.ppf(0.975, 2), not the "rule of three"
    # one-sided ~3.0/T heuristic (that uses chi2.ppf(0.95, 2) instead).
    lower, upper = garwood_ci(total_counts=0, total_tau_s=10.0, alpha=0.05)
    assert lower == 0.0
    assert upper == pytest.approx(chi2.ppf(0.975, 2) / (2 * 10.0), rel=1e-6)
    assert upper > 0  # never degenerate, unlike a Gaussian SE=0 for the same input


def test_garwood_ci_positive_counts():
    lower, upper = garwood_ci(total_counts=20, total_tau_s=10.0, alpha=0.05)
    assert lower == pytest.approx(chi2.ppf(0.025, 40) / 20.0, rel=1e-6)
    assert upper == pytest.approx(chi2.ppf(0.975, 42) / 20.0, rel=1e-6)
    assert lower < 2.0 < upper  # true rate (20/10=2.0) should fall inside its own CI


def test_compute_currie_limits_bundles_counts_and_cps():
    limits = compute_currie_limits(mu_b_counts=25.0, tau_s=2.0, alpha=0.05, beta=0.05)
    assert limits.L_D_counts == pytest.approx(2.71 + 4.65 * 5.0, rel=1e-6)
    assert limits.L_D_cps == pytest.approx(limits.L_D_counts / 2.0, rel=1e-9)
    assert limits.L_C_cps == pytest.approx(limits.L_C_counts / 2.0, rel=1e-9)
    assert limits.tau_s == 2.0
