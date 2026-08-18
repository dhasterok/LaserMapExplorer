"""Cross-element parent/daughter dating-ratio module tests -- hand-computable
synthetic bracketing scenarios, following the same convention as
tests/test_calibration_massbias.py.

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

from src.calibration.dating_ratios import (
    DatingRatioSpec,
    corrected_dating_ratio,
    fit_dating_ratio,
    fit_session_dating_ratios,
    resolve_dating_ratio_truth,
)
from src.calibration.rawfile import LineFileMeta
from src.calibration.reflib import parse_reference_material
from src.calibration.standards import StandardCalibrationResult, StandardOccurrence

BASE_TIME = datetime(2026, 3, 1, 10, 0, 0)

REFERENCE_ZIRCON = parse_reference_material({
    "standard": "ZRNSTD",
    "analytes": {
        "Pb206": {"element": "Pb", "mass": 206, "value": 0.05, "uncertainty": 0.001, "uncertainty_type": "1SD"},
        "U238": {"element": "U", "mass": 238, "value": 400.0, "uncertainty": 4.0, "uncertainty_type": "1SD"},
    },
    "isotope_ratios": {
        "Pb206/U238": {
            "numerator_element": "Pb", "numerator_mass": 206, "denominator_element": "U", "denominator_mass": 238,
            "value": 0.05, "uncertainty": 0.0005, "uncertainty_type": "1SD", "source": "test",
        },
        "Pb208/Th232": {
            "numerator_element": "Pb", "numerator_mass": 208, "denominator_element": "Th", "denominator_mass": 232,
            "value": 0.03, "uncertainty": 0.0003, "uncertainty_type": "1SD", "source": "test",
        },
    },
})

REFERENCE_NO_RATIO = parse_reference_material({
    "standard": "NORATIOSTD",
    "analytes": {"U238": {"element": "U", "mass": 238, "value": 400.0, "uncertainty": 4.0, "uncertainty_type": "1SD"}},
})


def _occurrence(order, acquired_at, mean_signal, sem_signal=None):
    meta = LineFileMeta(
        path=Path(f"ZRNSTD - {order}.csv"), label="ZRNSTD", index=order, is_standard=True,
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
# resolve_dating_ratio_truth
# ---------------------------------------------------------------------------

def test_resolve_dating_ratio_truth_uses_certified_ratio():
    truth = resolve_dating_ratio_truth(REFERENCE_ZIRCON, "Pb", 206, "U", 238)
    assert truth is not None
    assert truth.source == "certified_reference_ratio"
    assert truth.value == pytest.approx(0.05)
    assert truth.uncertainty_1sd == pytest.approx(0.0005)


def test_resolve_dating_ratio_truth_has_no_natural_abundance_fallback():
    # No certified Pb206/U238 in this material -- unlike massbias.resolve_truth_ratio,
    # there is NO fallback for a cross-element pair.
    assert resolve_dating_ratio_truth(REFERENCE_NO_RATIO, "Pb", 206, "U", 238) is None


# ---------------------------------------------------------------------------
# fit_dating_ratio -- hand-computable bracketing scenario
# ---------------------------------------------------------------------------

# Known underlying log-drift curve for Pb206/U238: log(f0(t)) = a + b*t
# (t = seconds since first occurrence).
_A, _B = 0.01, 0.0002


def _synthetic_zircon_occurrences(n=6, step_s=300.0):
    occurrences = []
    for i in range(n):
        t = BASE_TIME + timedelta(seconds=step_s * i)
        seconds = step_s * i
        f0 = np.exp(_A + _B * seconds)
        measured_206_238 = 0.05 * f0  # truth (0.05) * session drift factor
        occurrences.append(_occurrence(i + 1, t, {"Pb206": measured_206_238, "U238": 1.0}))
    return occurrences


def test_fit_dating_ratio_recovers_known_linear_drift():
    occurrences = _synthetic_zircon_occurrences()
    standard_results = {"ZRNSTD": _minimal_result("ZRNSTD", REFERENCE_ZIRCON, occurrences)}
    spec = DatingRatioSpec(numerator_element="Pb", numerator_mass=206, denominator_element="U", denominator_mass=238)

    fit = fit_dating_ratio(standard_results, ["ZRNSTD"], spec, order=1, method="fixed")

    assert fit is not None
    assert fit.n_points == 6
    assert fit.truth.value == pytest.approx(0.05)
    assert fit.log_ratio_fit.coeffs[0] == pytest.approx(_B, abs=1e-9)  # slope
    assert fit.log_ratio_fit.coeffs[1] == pytest.approx(_A, abs=1e-9)  # intercept


def test_corrected_dating_ratio_recovers_sample_truth():
    occurrences = _synthetic_zircon_occurrences()
    standard_results = {"ZRNSTD": _minimal_result("ZRNSTD", REFERENCE_ZIRCON, occurrences)}
    spec = DatingRatioSpec(numerator_element="Pb", numerator_mass=206, denominator_element="U", denominator_mass=238)
    fit = fit_dating_ratio(standard_results, ["ZRNSTD"], spec, order=1, method="fixed")

    probe_time = BASE_TIME + timedelta(seconds=750.0)
    seconds = 750.0
    f0 = np.exp(_A + _B * seconds)
    sample_true_206_238 = 0.08  # arbitrary "true" sample ratio, unrelated to the standard's own ratio
    measured = sample_true_206_238 * f0

    signal = pd.DataFrame({"Pb206": [measured], "U238": [1.0]})
    recovered = corrected_dating_ratio(signal, [probe_time], fit)
    assert recovered[0] == pytest.approx(sample_true_206_238, rel=1e-6)


def test_fit_dating_ratio_applies_numerator_scale_factor_before_fitting():
    # The 207Pb/235U reformulation: 235U is never measured, so the
    # "measured ratio" is k * (Pb207/U238) instead -- confirm the scale
    # factor is applied BEFORE the log-ratio fit (not just at correction
    # time), by checking the fit recovers a truth that only matches when
    # the scale factor is properly baked in.
    k = 137.818
    truth_207_235 = 0.045  # some certified 207Pb/235U-equivalent value
    reference = parse_reference_material({
        "standard": "ZRNSTD2",
        "analytes": {"U238": {"element": "U", "mass": 238, "value": 400.0, "uncertainty": 4.0, "uncertainty_type": "1SD"}},
        "isotope_ratios": {
            "Pb207/U238": {
                "numerator_element": "Pb", "numerator_mass": 207, "denominator_element": "U", "denominator_mass": 238,
                "value": truth_207_235, "uncertainty": 0.0005, "uncertainty_type": "1SD", "source": "test",
            },
        },
    })
    occurrences = []
    for i in range(6):
        t = BASE_TIME + timedelta(seconds=300.0 * i)
        seconds = 300.0 * i
        f0 = np.exp(_A + _B * seconds)
        # Pb207/U238 raw CPS ratio such that k * (Pb207/U238) == truth_207_235 * f0
        raw_207_238 = (truth_207_235 * f0) / k
        occurrences.append(_occurrence(i + 1, t, {"Pb207": raw_207_238, "U238": 1.0}))
    standard_results = {"ZRNSTD2": _minimal_result("ZRNSTD2", reference, occurrences)}
    spec = DatingRatioSpec(
        numerator_element="Pb", numerator_mass=207, denominator_element="U", denominator_mass=238,
        numerator_scale_factor=k,
    )

    fit = fit_dating_ratio(standard_results, ["ZRNSTD2"], spec, order=1, method="fixed")
    assert fit is not None
    assert fit.log_ratio_fit.coeffs[0] == pytest.approx(_B, abs=1e-6)
    assert fit.log_ratio_fit.coeffs[1] == pytest.approx(_A, abs=1e-6)

    probe_time = BASE_TIME + timedelta(seconds=750.0)
    f0_probe = np.exp(_A + _B * 750.0)
    sample_true_ratio = 0.09
    raw_sample = (sample_true_ratio * f0_probe) / k
    signal = pd.DataFrame({"Pb207": [raw_sample], "U238": [1.0]})
    recovered = corrected_dating_ratio(signal, [probe_time], fit)
    assert recovered[0] == pytest.approx(sample_true_ratio, rel=1e-6)


def test_fit_dating_ratio_returns_none_with_too_few_points():
    occurrences = _synthetic_zircon_occurrences(n=1)
    standard_results = {"ZRNSTD": _minimal_result("ZRNSTD", REFERENCE_ZIRCON, occurrences)}
    spec = DatingRatioSpec(numerator_element="Pb", numerator_mass=206, denominator_element="U", denominator_mass=238)
    assert fit_dating_ratio(standard_results, ["ZRNSTD"], spec) is None


def test_fit_dating_ratio_returns_none_when_no_truth_resolvable():
    occurrences = _synthetic_zircon_occurrences()
    standard_results = {"ZRNSTD": _minimal_result("ZRNSTD", REFERENCE_ZIRCON, occurrences)}
    spec = DatingRatioSpec(numerator_element="Xx", numerator_mass=999, denominator_element="Yy", denominator_mass=998)
    assert fit_dating_ratio(standard_results, ["ZRNSTD"], spec) is None


def test_fit_dating_ratio_returns_none_when_channels_missing_from_signal():
    occurrences = [_occurrence(1, BASE_TIME, {"Al27": 100.0})]
    standard_results = {"ZRNSTD": _minimal_result("ZRNSTD", REFERENCE_ZIRCON, occurrences)}
    spec = DatingRatioSpec(numerator_element="Pb", numerator_mass=206, denominator_element="U", denominator_mass=238)
    assert fit_dating_ratio(standard_results, ["ZRNSTD"], spec) is None


def test_fit_dating_ratio_invalid_method_raises():
    occurrences = _synthetic_zircon_occurrences()
    standard_results = {"ZRNSTD": _minimal_result("ZRNSTD", REFERENCE_ZIRCON, occurrences)}
    spec = DatingRatioSpec(numerator_element="Pb", numerator_mass=206, denominator_element="U", denominator_mass=238)
    with pytest.raises(ValueError):
        fit_dating_ratio(standard_results, ["ZRNSTD"], spec, method="auto_poisson_lrt")


# ---------------------------------------------------------------------------
# fit_session_dating_ratios
# ---------------------------------------------------------------------------

def test_fit_session_dating_ratios_returns_fits_keyed_by_pair():
    occurrences = _synthetic_zircon_occurrences()
    standard_results = {"ZRNSTD": _minimal_result("ZRNSTD", REFERENCE_ZIRCON, occurrences)}
    specs = [DatingRatioSpec(numerator_element="Pb", numerator_mass=206, denominator_element="U", denominator_mass=238)]
    fits = fit_session_dating_ratios(standard_results, specs)
    assert "Pb206/U238" in fits
    assert fits["Pb206/U238"].truth.value == pytest.approx(0.05)


def test_fit_session_dating_ratios_skips_specs_with_no_usable_data():
    occurrences = _synthetic_zircon_occurrences()
    standard_results = {"ZRNSTD": _minimal_result("ZRNSTD", REFERENCE_ZIRCON, occurrences)}
    specs = [
        DatingRatioSpec(numerator_element="Pb", numerator_mass=206, denominator_element="U", denominator_mass=238),
        DatingRatioSpec(numerator_element="Xx", numerator_mass=999, denominator_element="Yy", denominator_mass=998),
    ]
    fits = fit_session_dating_ratios(standard_results, specs)
    assert set(fits) == {"Pb206/U238"}


def test_fit_session_dating_ratios_respects_explicit_dating_standards_subset():
    occurrences_a = _synthetic_zircon_occurrences(n=3)
    occurrences_b = [_occurrence(1, BASE_TIME, {"Pb206": 999.0, "U238": 1.0})]  # would badly skew a pooled fit
    standard_results = {
        "ZRNSTD": _minimal_result("ZRNSTD", REFERENCE_ZIRCON, occurrences_a),
        "OTHER": _minimal_result("OTHER", REFERENCE_ZIRCON, occurrences_b),
    }
    specs = [DatingRatioSpec(
        numerator_element="Pb", numerator_mass=206, denominator_element="U", denominator_mass=238,
        dating_standards=["ZRNSTD"],
    )]
    fits = fit_session_dating_ratios(standard_results, specs)
    assert fits["Pb206/U238"].standard_labels == ["ZRNSTD"]
