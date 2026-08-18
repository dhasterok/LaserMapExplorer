"""Mass-bias correction module tests -- hand-computable synthetic bracketing
scenarios, following the same convention as tests/test_calibration_standards.py.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.massbias import (
    BiasSpec,
    bias_correction_factor,
    corrected_ratio,
    fit_bias_curve,
    fit_session_bias,
    most_abundant_mass,
    natural_abundance_ratio,
    resolve_truth_ratio,
)
from src.calibration.rawfile import LineFileMeta
from src.calibration.reflib import parse_reference_material
from src.calibration.standards import StandardCalibrationResult, StandardOccurrence

BASE_TIME = datetime(2026, 3, 1, 10, 0, 0)

REFERENCE_PB = parse_reference_material({
    "standard": "PBSTD",
    "analytes": {"Pb204": {"element": "Pb", "mass": 204, "value": 2.0, "uncertainty": 0.1, "uncertainty_type": "1SD"}},
    "isotope_ratios": {
        "Pb206/Pb204": {
            "numerator_element": "Pb", "numerator_mass": 206, "denominator_element": "Pb", "denominator_mass": 204,
            "value": 17.0, "uncertainty": 0.01, "uncertainty_type": "1SD", "source": "test",
        },
    },
})

REFERENCE_U_NO_RATIO = parse_reference_material({
    "standard": "USTD",
    "analytes": {"U238": {"element": "U", "mass": 238, "value": 400.0, "uncertainty": 4.0, "uncertainty_type": "1SD"}},
})


def _occurrence(order, acquired_at, mean_signal, sem_signal=None):
    meta = LineFileMeta(
        path=Path(f"PBSTD - {order}.csv"), label="PBSTD", index=order, is_standard=True,
        acquired_at=acquired_at, batch="Test.b",
    )
    return StandardOccurrence(
        file_meta=meta, background=None, mean_signal=mean_signal,
        sem_signal=sem_signal or {k: 1.0 for k in mean_signal}, occurrence_order=order,
    )


def _minimal_result(label, reference, occurrences):
    return StandardCalibrationResult(
        standard_label=label, reference=reference, occurrences=occurrences,
        drift_fits={}, calibration_factor={}, accuracy_table=[], holdout_accuracy_table=None,
        split_enabled=False,
    )


# ---------------------------------------------------------------------------
# natural_abundance_ratio / resolve_truth_ratio
# ---------------------------------------------------------------------------

def test_natural_abundance_ratio_known_pair():
    # U238/U235 natural abundance: 0.9927417 / 0.0072041 ~= 137.8
    ratio = natural_abundance_ratio("U", 238, 235)
    assert ratio == pytest.approx(137.8, abs=0.5)


def test_natural_abundance_ratio_missing_pair_returns_none():
    assert natural_abundance_ratio("Xx", 999, 998) is None


def test_most_abundant_mass_picks_dominant_isotope():
    # Pb208 is the most naturally abundant Pb isotope of {204, 206, 207, 208}.
    assert most_abundant_mass("Pb", [204, 206, 207, 208]) == 208


def test_most_abundant_mass_returns_none_for_unresolvable_element():
    assert most_abundant_mass("Xx", [1, 2]) is None


def test_resolve_truth_ratio_prefers_certified_over_natural_abundance():
    truth = resolve_truth_ratio(REFERENCE_PB, "Pb", 206, 204)
    assert truth is not None
    assert truth.source == "certified_reference_ratio"
    assert truth.value == pytest.approx(17.0)
    assert truth.uncertainty_1sd == pytest.approx(0.01)


def test_resolve_truth_ratio_falls_back_to_natural_abundance_when_no_certified_value():
    # REFERENCE_U_NO_RATIO has no isotope_ratios at all -- U238/U235 must
    # fall back to natural abundance (a genuinely invariant pair).
    truth = resolve_truth_ratio(REFERENCE_U_NO_RATIO, "U", 238, 235)
    assert truth is not None
    assert truth.source == "natural_abundance"
    assert truth.value == pytest.approx(137.8, abs=0.5)


def test_resolve_truth_ratio_returns_none_when_neither_available():
    assert resolve_truth_ratio(REFERENCE_PB, "Xx", 999, 998) is None


# ---------------------------------------------------------------------------
# fit_bias_curve -- hand-computable bracketing scenario
# ---------------------------------------------------------------------------

# Known underlying log-bias curve for Pb206/Pb204: log(f0(t)) = a + b*t
# (t = seconds since first occurrence).
_A, _B = 0.02, 0.0005


def _synthetic_pb_occurrences(n=6, step_s=300.0):
    occurrences = []
    for i in range(n):
        t = BASE_TIME + timedelta(seconds=step_s * i)
        seconds = step_s * i
        f0 = np.exp(_A + _B * seconds)
        measured_206_204 = 17.0 * f0  # truth (17.0) * bias factor
        occurrences.append(_occurrence(i + 1, t, {"Pb206": measured_206_204, "Pb204": 1.0}))
    return occurrences


def test_fit_bias_curve_recovers_known_linear_drift():
    occurrences = _synthetic_pb_occurrences()
    standard_results = {"PBSTD": _minimal_result("PBSTD", REFERENCE_PB, occurrences)}

    fit = fit_bias_curve(standard_results, ["PBSTD"], "Pb", 206, 204, order=1, method="fixed")

    assert fit is not None
    assert fit.n_points == 6
    assert fit.truth.value == pytest.approx(17.0)
    assert fit.log_bias_fit.coeffs[0] == pytest.approx(_B, abs=1e-9)  # slope
    assert fit.log_bias_fit.coeffs[1] == pytest.approx(_A, abs=1e-9)  # intercept


def test_bias_correction_factor_recovers_truth_at_fitted_times():
    occurrences = _synthetic_pb_occurrences()
    standard_results = {"PBSTD": _minimal_result("PBSTD", REFERENCE_PB, occurrences)}
    fit = fit_bias_curve(standard_results, ["PBSTD"], "Pb", 206, 204, order=1, method="fixed")

    times = [o.file_meta.acquired_at for o in occurrences]
    measured = np.array([o.mean_signal["Pb206"] / o.mean_signal["Pb204"] for o in occurrences])
    correction = bias_correction_factor(fit, times, 206, 204)
    recovered = measured / correction
    assert recovered == pytest.approx(np.full(len(times), 17.0), rel=1e-6)


def test_bias_correction_factor_generalizes_to_second_pair_of_same_element():
    # Core property test: a SECOND isotope pair of the same element
    # (Pb208/Pb204), synthetically consistent with the SAME underlying
    # f0(t) rescaled by the known mass-ratio exponent beta, must be
    # recoverable using ONLY the first pair's (Pb206/Pb204) fitted curve.
    occurrences = _synthetic_pb_occurrences()
    standard_results = {"PBSTD": _minimal_result("PBSTD", REFERENCE_PB, occurrences)}
    fit = fit_bias_curve(standard_results, ["PBSTD"], "Pb", 206, 204, order=1, method="fixed")
    assert fit is not None

    beta = np.log(208 / 204) / np.log(206 / 204)
    probe_time = BASE_TIME + timedelta(seconds=750.0)  # an UNfitted timepoint, mid-session
    seconds = 750.0
    f0 = np.exp(_A + _B * seconds)
    sample_true_208_204 = 2.164  # arbitrary "true" sample ratio, unrelated to any standard's own ratio
    measured_208_204 = sample_true_208_204 * f0 ** beta

    signal = pd.DataFrame({"Pb208": [measured_208_204], "Pb204": [1.0]})
    recovered = corrected_ratio(signal, [probe_time], fit, numerator_mass=208, denominator_mass=204)
    assert recovered[0] == pytest.approx(sample_true_208_204, rel=1e-6)


def test_corrected_ratio_with_fits_own_pair_matches_bias_correction_factor():
    occurrences = _synthetic_pb_occurrences()
    standard_results = {"PBSTD": _minimal_result("PBSTD", REFERENCE_PB, occurrences)}
    fit = fit_bias_curve(standard_results, ["PBSTD"], "Pb", 206, 204, order=1, method="fixed")

    probe_time = BASE_TIME + timedelta(seconds=750.0)
    seconds = 750.0
    f0 = np.exp(_A + _B * seconds)
    sample_true_206_204 = 16.5
    measured = sample_true_206_204 * f0

    signal = pd.DataFrame({"Pb206": [measured], "Pb204": [1.0]})
    recovered = corrected_ratio(signal, [probe_time], fit, numerator_mass=206, denominator_mass=204)
    assert recovered[0] == pytest.approx(sample_true_206_204, rel=1e-6)


def test_fit_bias_curve_returns_none_with_too_few_points():
    occurrences = _synthetic_pb_occurrences(n=1)
    standard_results = {"PBSTD": _minimal_result("PBSTD", REFERENCE_PB, occurrences)}
    fit = fit_bias_curve(standard_results, ["PBSTD"], "Pb", 206, 204)
    assert fit is None


def test_fit_bias_curve_returns_none_when_no_truth_resolvable():
    occurrences = _synthetic_pb_occurrences()
    standard_results = {"PBSTD": _minimal_result("PBSTD", REFERENCE_PB, occurrences)}
    # No natural abundance and no certified ratio exists for this made-up pair.
    fit = fit_bias_curve(standard_results, ["PBSTD"], "Xx", 999, 998)
    assert fit is None


def test_fit_bias_curve_returns_none_when_channels_missing_from_signal():
    occurrences = [_occurrence(1, BASE_TIME, {"Al27": 100.0})]
    standard_results = {"PBSTD": _minimal_result("PBSTD", REFERENCE_PB, occurrences)}
    fit = fit_bias_curve(standard_results, ["PBSTD"], "Pb", 206, 204)
    assert fit is None


def test_fit_bias_curve_invalid_method_raises():
    occurrences = _synthetic_pb_occurrences()
    standard_results = {"PBSTD": _minimal_result("PBSTD", REFERENCE_PB, occurrences)}
    with pytest.raises(ValueError):
        fit_bias_curve(standard_results, ["PBSTD"], "Pb", 206, 204, method="auto_poisson_lrt")


def test_fit_bias_curve_pools_multiple_standards_with_different_truths():
    # A second standard with a DIFFERENT certified Pb206/Pb204 value,
    # consistent with the SAME underlying f0(t) -- both should contribute
    # points to one shared fit.
    reference_b = parse_reference_material({
        "standard": "PBSTD2",
        "analytes": {"Pb204": {"element": "Pb", "mass": 204, "value": 2.0, "uncertainty": 0.1, "uncertainty_type": "1SD"}},
        "isotope_ratios": {
            "Pb206/Pb204": {
                "numerator_element": "Pb", "numerator_mass": 206, "denominator_element": "Pb", "denominator_mass": 204,
                "value": 20.0, "uncertainty": 0.01, "uncertainty_type": "1SD", "source": "test",
            },
        },
    })
    occ_a = _synthetic_pb_occurrences(n=3)
    occ_b = []
    for i in range(3):
        t = BASE_TIME + timedelta(seconds=300.0 * (i + 10))
        seconds = 300.0 * (i + 10)
        f0 = np.exp(_A + _B * seconds)
        occ_b.append(_occurrence(i + 1, t, {"Pb206": 20.0 * f0, "Pb204": 1.0}))

    standard_results = {
        "PBSTD": _minimal_result("PBSTD", REFERENCE_PB, occ_a),
        "PBSTD2": _minimal_result("PBSTD2", reference_b, occ_b),
    }
    fit = fit_bias_curve(standard_results, ["PBSTD", "PBSTD2"], "Pb", 206, 204, order=1, method="fixed")
    assert fit is not None
    assert fit.n_points == 6
    assert set(fit.standard_labels) == {"PBSTD", "PBSTD2"}
    assert fit.log_bias_fit.coeffs[0] == pytest.approx(_B, abs=1e-6)
    assert fit.log_bias_fit.coeffs[1] == pytest.approx(_A, abs=1e-6)


# ---------------------------------------------------------------------------
# fit_session_bias
# ---------------------------------------------------------------------------

def test_fit_session_bias_returns_fit_keyed_by_pair():
    occurrences = _synthetic_pb_occurrences()
    standard_results = {"PBSTD": _minimal_result("PBSTD", REFERENCE_PB, occurrences)}
    specs = [BiasSpec(element="Pb", numerator_mass=206, denominator_mass=204)]
    fits = fit_session_bias(standard_results, specs)
    assert "Pb206/Pb204" in fits
    assert fits["Pb206/Pb204"].truth.value == pytest.approx(17.0)


def test_fit_session_bias_skips_specs_with_no_usable_data():
    occurrences = _synthetic_pb_occurrences()
    standard_results = {"PBSTD": _minimal_result("PBSTD", REFERENCE_PB, occurrences)}
    specs = [
        BiasSpec(element="Pb", numerator_mass=206, denominator_mass=204),
        BiasSpec(element="Xx", numerator_mass=999, denominator_mass=998),
    ]
    fits = fit_session_bias(standard_results, specs)
    assert set(fits) == {"Pb206/Pb204"}


def test_fit_session_bias_respects_explicit_bias_standards_subset():
    occurrences_a = _synthetic_pb_occurrences(n=3)
    occurrences_b = [_occurrence(1, BASE_TIME, {"Pb206": 999.0, "Pb204": 1.0})]  # would badly skew a pooled fit
    standard_results = {
        "PBSTD": _minimal_result("PBSTD", REFERENCE_PB, occurrences_a),
        "OTHER": _minimal_result("OTHER", REFERENCE_PB, occurrences_b),
    }
    specs = [BiasSpec(element="Pb", numerator_mass=206, denominator_mass=204, bias_standards=["PBSTD"])]
    fits = fit_session_bias(standard_results, specs)
    assert fits["Pb206/Pb204"].standard_labels == ["PBSTD"]
