"""Isotope-apportionment tests -- hand-computable Pb-style toy cases,
following the same convention as tests/test_calibration_standards.py.

Pure Python -- no PyQt/QApplication needed.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.isotope_apportion import (
    IsotopeShareSpec,
    apportion_element_ppm,
    apportion_from_spec,
)
from src.calibration.massbias import natural_abundance_ratio


def test_apportion_element_ppm_full_ratio_set_sums_to_total():
    # total Pb = 100 ppm; R206=0.9, R207=0.8, R208=2.0 (all relative to Pb204).
    total = np.array([100.0])
    corrected_ratios = {206: np.array([0.9]), 207: np.array([0.8]), 208: np.array([2.0])}
    result = apportion_element_ppm(total, corrected_ratios, normalizer_mass=204)

    assert result is not None
    assert result.included_masses == [206, 207, 208]
    assert result.missing_masses == []

    denom = 1 + 0.9 + 0.8 + 2.0
    assert result.ppm[204][0] == pytest.approx(100.0 / denom)
    assert result.ppm[206][0] == pytest.approx(100.0 * 0.9 / denom)
    assert result.ppm[207][0] == pytest.approx(100.0 * 0.8 / denom)
    assert result.ppm[208][0] == pytest.approx(100.0 * 2.0 / denom)

    total_recovered = sum(result.ppm[m][0] for m in (204, 206, 207, 208))
    assert total_recovered == pytest.approx(100.0)


def test_apportion_element_ppm_partial_ratio_set_still_self_consistent():
    # Pb207 ratio unavailable -- shares should be computed from the
    # isotopes that DO have a ratio, self-consistently (sum to total among
    # those included), not silently backfilled from natural abundance.
    total = np.array([100.0])
    corrected_ratios = {206: np.array([0.9]), 208: np.array([2.0])}
    result = apportion_element_ppm(total, corrected_ratios, normalizer_mass=204)

    assert result is not None
    assert result.included_masses == [206, 208]

    denom = 1 + 0.9 + 2.0
    assert result.ppm[204][0] == pytest.approx(100.0 / denom)
    assert result.ppm[206][0] == pytest.approx(100.0 * 0.9 / denom)
    assert result.ppm[208][0] == pytest.approx(100.0 * 2.0 / denom)
    assert 207 not in result.ppm

    total_recovered = sum(result.ppm[m][0] for m in (204, 206, 208))
    assert total_recovered == pytest.approx(100.0)


def test_apportion_element_ppm_vectorized_over_multiple_rows():
    total = np.array([100.0, 200.0])
    corrected_ratios = {206: np.array([1.0, 1.0])}  # constant ratio, varying total
    result = apportion_element_ppm(total, corrected_ratios, normalizer_mass=204)
    assert result is not None
    assert result.ppm[204] == pytest.approx([50.0, 100.0])
    assert result.ppm[206] == pytest.approx([50.0, 100.0])


def test_apportion_element_ppm_no_usable_ratios_returns_none():
    total = np.array([100.0])
    assert apportion_element_ppm(total, {}, normalizer_mass=204) is None
    assert apportion_element_ppm(total, {206: None}, normalizer_mass=204) is None


def test_apportion_from_spec_resolves_columns_and_reports_missing():
    spec = IsotopeShareSpec(element="Pb", normalizer_mass=204, companion_masses=[206, 207, 208])
    calibrated_ppm_columns = {"Pb204": np.array([100.0])}  # total-element column, auto-picked (normalizer present)
    calibrated_ratio_columns = {
        "Pb206 / Pb204": np.array([0.9]),
        "Pb208 / Pb204": np.array([2.0]),
        # "Pb207 / Pb204" intentionally absent
    }
    result = apportion_from_spec(spec, calibrated_ppm_columns, calibrated_ratio_columns)

    assert result is not None
    assert result.included_masses == [206, 208]
    assert result.missing_masses == [207]
    denom = 1 + 0.9 + 2.0
    assert result.ppm[204][0] == pytest.approx(100.0 / denom)


def test_apportion_from_spec_returns_none_when_total_ppm_column_absent():
    spec = IsotopeShareSpec(element="Pb", normalizer_mass=204, companion_masses=[206])
    result = apportion_from_spec(spec, {}, {"Pb206 / Pb204": np.array([0.9])})
    assert result is None


def test_apportion_from_spec_natural_abundance_mode_ignores_ratio_columns():
    # The Fe56/Fe57 case discussed with the user: Fe57 is measured, Fe56
    # dominates natural abundance -- natural_abundance mode splits total Fe
    # using the real terrestrial abundance ratio, independent of whatever
    # (irrelevant, possibly stale) columns happen to be in calibrated_ratio_columns.
    spec = IsotopeShareSpec(element="Fe", normalizer_mass=56, companion_masses=[57], mode="natural_abundance")
    calibrated_ppm_columns = {"Fe56": np.array([100.0])}
    result = apportion_from_spec(spec, calibrated_ppm_columns, {"Fe57 / Fe56": np.array([999.0])})

    assert result is not None
    assert result.included_masses == [57]
    assert result.missing_masses == []

    expected_ratio = natural_abundance_ratio("Fe", 57, 56)
    denom = 1 + expected_ratio
    assert result.ppm[56][0] == pytest.approx(100.0 / denom)
    assert result.ppm[57][0] == pytest.approx(100.0 * expected_ratio / denom)


def test_apportion_from_spec_natural_abundance_mode_reports_missing_when_isotope_unresolvable():
    spec = IsotopeShareSpec(element="Xx", normalizer_mass=1, companion_masses=[2], mode="natural_abundance")
    result = apportion_from_spec(spec, {"Xx1": np.array([100.0])}, {})
    assert result is None  # no usable ratios at all -- apportion_element_ppm itself returns None


def test_apportion_from_spec_rejects_unknown_mode():
    spec = IsotopeShareSpec(element="Pb", normalizer_mass=204, companion_masses=[206], mode="bogus")
    with pytest.raises(ValueError):
        apportion_from_spec(spec, {"Pb204": np.array([100.0])}, {})


def test_apportion_from_spec_uses_explicit_total_ppm_source_mass():
    # total_ppm_source_mass explicitly points at Pb206's own calibrated
    # column instead of the (also-present) normalizer's.
    spec = IsotopeShareSpec(element="Pb", normalizer_mass=204, companion_masses=[206], total_ppm_source_mass=206)
    calibrated_ppm_columns = {"Pb204": np.array([999.0]), "Pb206": np.array([100.0])}
    calibrated_ratio_columns = {"Pb206 / Pb204": np.array([0.9])}
    result = apportion_from_spec(spec, calibrated_ppm_columns, calibrated_ratio_columns)
    assert result is not None
    denom = 1 + 0.9
    assert result.ppm[204][0] == pytest.approx(100.0 / denom)
