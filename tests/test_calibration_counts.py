"""Integer-count recovery from quantized CPS -- hand-derivable cases.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.counts import TauEstimate, cps_to_counts, estimate_quantum, resolve_tau


def test_estimate_quantum_recovers_known_step():
    # tau=0.2s -> quantum Delta=5 CPS. Integer counts [0,0,1,0,2,1,0] -> cps = counts/0.2.
    counts = np.array([0, 0, 1, 0, 2, 1, 0])
    cps = counts / 0.2
    assert estimate_quantum(cps) == pytest.approx(5.0, rel=0.01)


def test_estimate_quantum_returns_none_with_too_few_nonzero_values():
    assert estimate_quantum([0.0, 0.0, 5.0]) is None
    assert estimate_quantum([]) is None


def test_estimate_quantum_returns_none_for_smooth_continuous_data():
    # Real-valued, non-quantized background (e.g. a major element's already-
    # continuous CPS) must not silently claim a confident quantum -- without
    # a fit-quality floor, the grid search would still return *some* delta
    # (whichever scored least-badly), falsely implying visible quantization.
    rng = np.random.default_rng(9)
    cps = rng.normal(5000.0, 200.0, size=50)
    assert estimate_quantum(cps) is None


def test_estimate_quantum_robust_to_float32_rounding():
    tau = 0.31
    rng = np.random.default_rng(3)
    counts = rng.poisson(0.4, size=200)
    cps = (counts / tau).astype(np.float32).astype(np.float64)
    quantum = estimate_quantum(cps)
    assert quantum == pytest.approx(1.0 / tau, rel=0.01)


def test_resolve_tau_metadata_provenance():
    tau = resolve_tau([0.0, 5.0, 10.0], dwell_time_ms=310.0, sweeps_per_reading=1)
    assert tau.provenance == "metadata"
    assert tau.tau_s == pytest.approx(0.31)


def test_resolve_tau_inferred_provenance():
    counts = np.array([0, 1, 0, 2, 1, 0, 0, 1, 2, 0])
    cps = counts / 0.2
    tau = resolve_tau(cps)
    assert tau.provenance == "inferred"
    assert tau.tau_s == pytest.approx(0.2, rel=0.02)
    assert tau.quantum_cps == pytest.approx(5.0, rel=0.02)


def test_resolve_tau_bounded_provenance():
    # Only one nonzero value -- too few for estimate_quantum (needs >=3) --
    # falls back to a conservative lower bound: tau >= 1/min(cps>0).
    tau = resolve_tau([0.0, 0.0, 0.0, 7.3, 0.0])
    assert tau.provenance == "bounded"
    assert tau.tau_s == pytest.approx(1.0 / 7.3)


def test_resolve_tau_bounded_ignores_spurious_near_zero_value():
    """Regression test: a real exported file can carry a stray near-zero-
    but-not-exactly-zero value (floating-point residue from upstream
    processing, not a genuine sub-quantum count) alongside a real
    single-count event. A naive 1/min(nonzero) bound would treat that
    residue as the smallest genuine count, inferring an absurd tau (here
    ~212,766s) that then inflates the real event's own recovered count by
    5-6 orders of magnitude when fed through cps_to_counts. The bound must
    ignore implausibly tiny values instead."""
    true_tau = 0.28
    cps = [0.0] * 20
    cps[3] = 1 / true_tau      # one real single-count event
    cps[15] = 4.7e-6            # floating-point residue, not a real count

    tau = resolve_tau(cps)
    assert tau.provenance == "bounded"
    assert tau.tau_s == pytest.approx(true_tau, rel=0.01)

    recovered = cps_to_counts(cps, tau)
    assert recovered.sum() == 1


def test_resolve_tau_bounded_returns_unknown_when_only_spurious_values_present():
    # Every nonzero value is far too small to be a plausible real count --
    # nothing left to bound from, so this must fall through to "unknown"
    # rather than trusting noise.
    tau = resolve_tau([0.0, 0.0, 4.7e-6, 0.0, 1.2e-7])
    assert tau.provenance == "unknown"
    assert tau.tau_s is None


def test_resolve_tau_unknown_provenance():
    tau = resolve_tau([0.0, 0.0, 0.0, 0.0])
    assert tau.provenance == "unknown"
    assert tau.tau_s is None


def test_cps_to_counts_exact_with_known_tau():
    tau = TauEstimate(tau_s=0.2, provenance="inferred", quantum_cps=5.0)
    counts = cps_to_counts([0.0, 5.0, 10.0, 15.0], tau)
    assert counts.tolist() == [0, 1, 2, 3]


def test_cps_to_counts_none_when_tau_unknown():
    tau = TauEstimate(tau_s=None, provenance="unknown")
    assert cps_to_counts([0.0, 5.0], tau) is None
