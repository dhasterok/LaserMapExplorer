"""Standard calibration-factor, odd/even holdout split, and z/t-test QC.

Hand-computable toy cases (documented inline), following the same convention
as ``tests/test_stoichiometry_backend.py``.

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

from src.calibration.background import compute_background_result
from src.calibration.drift import DriftFit
from src.calibration.poisson_drift import PoissonDriftFit
from src.calibration.rawfile import LineFileData, LineFileMeta
from src.calibration.reflib import parse_reference_material
from src.calibration.standards import (
    StandardOccurrence,
    _mad_outlier_mask,
    apply_calibration,
    apply_multi_point_calibration,
    assemble_occurrences,
    calibrate_standard,
    combine_primary_standards,
)

REFERENCE = parse_reference_material({
    "standard": "TESTSTD",
    "analytes": {
        "Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 3.0, "uncertainty_type": "1SD"},
    },
})

REFERENCE_B = parse_reference_material({
    "standard": "STDB",
    "analytes": {
        "Al27": {"element": "Al", "mass": 27, "value": 1000.0, "uncertainty": 5.0, "uncertainty_type": "1SD"},
    },
})

REFERENCE_C = parse_reference_material({
    "standard": "STDC",
    "analytes": {
        "Al27": {"element": "Al", "mass": 27, "value": 900.0, "uncertainty": 5.0, "uncertainty_type": "1SD"},
    },
})

BASE_TIME = datetime(2026, 3, 1, 10, 0, 0)


def _occurrence(order, mean, sem=1.0, analyte="Al27", minutes_offset=None):
    offset = minutes_offset if minutes_offset is not None else order * 10
    meta = LineFileMeta(
        path=Path(f"SYNSTD - {order}.csv"), label="SYNSTD", index=order, is_standard=True,
        acquired_at=BASE_TIME + timedelta(minutes=offset), batch="Test.b",
    )
    return StandardOccurrence(
        file_meta=meta, background=None, mean_signal={analyte: mean}, sem_signal={analyte: sem},
        occurrence_order=order,
    )


def test_calibration_factor_order0_is_reference_over_mean_observed():
    # Fit group (no split): mean_signal = [98, 100, 102, 100] -> mean = 100.
    occurrences = [_occurrence(1, 98.0), _occurrence(2, 100.0), _occurrence(3, 102.0), _occurrence(4, 100.0)]
    result = calibrate_standard(occurrences, REFERENCE, drift_order=0, standard_label="TESTSTD")

    assert result.drift_fits["Al27"].coeffs[0] == pytest.approx(100.0)
    assert result.calibration_factor["Al27"] == pytest.approx(500.0 / 100.0)  # = 5.0
    assert result.split_enabled is False
    assert result.holdout_accuracy_table is None
    assert {row.group for row in result.accuracy_table} == {"all"}


def test_accuracy_row_hand_derived_zscore():
    # Fit group: mean_signal = [99, 101] -> order-0 fit predicts 100 everywhere.
    # scale = reference / predicted = 500 / 100 = 5.
    # For the occurrence with mean_signal=101, sem=1:
    #   observed = 101 * 5 = 505, observed_se = 1 * 5 = 5
    #   combined_uncertainty = sqrt(5**2 + 3**2) = sqrt(34) = 5.830951895...
    #   stat = (505 - 500) / sqrt(34) = 0.857492926...  (not flagged at threshold=2)
    occurrences = [_occurrence(1, 99.0, sem=1.0), _occurrence(2, 101.0, sem=1.0)]
    result = calibrate_standard(occurrences, REFERENCE, drift_order=0, standard_label="TESTSTD")

    row = next(r for r in result.accuracy_table if r.observed_value == pytest.approx(505.0))
    assert row.observed_se == pytest.approx(5.0)
    assert row.combined_uncertainty == pytest.approx(np.sqrt(34), rel=1e-9)
    assert row.z_or_t_stat == pytest.approx(5.0 / np.sqrt(34), rel=1e-9)
    assert row.flagged is False

    other_row = next(r for r in result.accuracy_table if r.observed_value == pytest.approx(495.0))
    assert other_row.difference == pytest.approx(-5.0)
    assert other_row.flagged is False


def test_accuracy_row_flags_large_deviation():
    occurrences = [_occurrence(1, 99.0, sem=0.1), _occurrence(2, 200.0, sem=0.1)]
    result = calibrate_standard(occurrences, REFERENCE, drift_order=0, standard_label="TESTSTD")
    flagged_rows = [r for r in result.accuracy_table if r.flagged]
    assert len(flagged_rows) >= 1


def test_odd_even_split_partitions_and_holdout_uses_fit_group_calibration():
    # occurrence_order 1,3 (odd) -> fit group, mean_signal [99, 101] -> order-0 predicts 100, scale=5.
    # occurrence_order 2,4 (even) -> holdout, back-calculated through the SAME fit-group scale.
    occurrences = [
        _occurrence(1, 99.0), _occurrence(2, 101.0), _occurrence(3, 101.0), _occurrence(4, 99.0),
    ]
    result = calibrate_standard(occurrences, REFERENCE, drift_order=0, split_odd_even=True, standard_label="TESTSTD")

    assert result.split_enabled is True
    assert {row.group for row in result.accuracy_table} == {"fit"}
    assert len(result.accuracy_table) == 2   # orders 1 and 3
    assert result.holdout_accuracy_table is not None
    assert {row.group for row in result.holdout_accuracy_table} == {"holdout"}
    assert len(result.holdout_accuracy_table) == 2   # orders 2 and 4

    holdout_observed = sorted(r.observed_value for r in result.holdout_accuracy_table)
    # order 2 (mean=101) -> 101*5=505; order 4 (mean=99) -> 99*5=495.
    assert holdout_observed == pytest.approx([495.0, 505.0])


def test_calibrate_standard_skips_analyte_with_no_reference_value():
    reference = parse_reference_material({
        "standard": "TESTSTD2",
        "analytes": {
            "Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 3.0, "uncertainty_type": "1SD"},
            "Ca43": {"element": "Ca", "mass": 43, "value": None},
        },
    })
    occurrences = [_occurrence(1, 98.0, analyte="Al27"), _occurrence(2, 100.0, analyte="Al27")]
    for o in occurrences:
        o.mean_signal["Ca43"] = 50.0
        o.sem_signal["Ca43"] = 1.0
    result = calibrate_standard(occurrences, reference, drift_order=0)
    assert "Ca43" in result.skipped_analytes
    assert "Ca43" not in result.calibration_factor
    assert all(row.analyte != "Ca43" for row in result.accuracy_table)


def test_calibrate_standard_extends_coverage_to_sibling_isotope_with_no_key():
    # Reference material only has a "U238" entry (GeoREM's elemental-total
    # convention) -- U235 has no key of its own but should now calibrate
    # using U238's (unscaled) elemental value, matching U238's own factor.
    reference = parse_reference_material({
        "standard": "TESTSTD3",
        "analytes": {"U238": {"element": "U", "mass": 238, "value": 400.0, "uncertainty": 4.0, "uncertainty_type": "1SD"}},
    })
    occurrences = [_occurrence(1, 98.0, analyte="U238"), _occurrence(2, 102.0, analyte="U238")]
    for o in occurrences:
        o.mean_signal["U235"] = o.mean_signal["U238"]
        o.sem_signal["U235"] = o.sem_signal["U238"]
    result = calibrate_standard(occurrences, reference, drift_order=0)

    assert "U235" not in result.skipped_analytes
    assert result.calibration_factor["U235"] == pytest.approx(result.calibration_factor["U238"])
    assert result.calibration_factor["U238"] == pytest.approx(400.0 / 100.0)  # unscaled, mean CPS=100


def test_calibrate_standard_raises_on_empty_occurrences():
    with pytest.raises(ValueError):
        calibrate_standard([], REFERENCE)


def test_apply_calibration_reduces_to_constant_scale_for_order0():
    occurrences = [_occurrence(1, 98.0), _occurrence(2, 102.0)]  # mean = 100
    result = calibrate_standard(occurrences, REFERENCE, drift_order=0)

    sample_signal = pd.DataFrame({"Al27": [100.0, 200.0, 50.0]})
    sample_times = [BASE_TIME, BASE_TIME + timedelta(minutes=5), BASE_TIME + timedelta(minutes=15)]
    calibrated = apply_calibration(sample_signal, sample_times, result)

    # scale = 500 / 100 = 5, constant regardless of time for an order-0 fit.
    assert np.allclose(calibrated["Al27"].to_numpy(), [500.0, 1000.0, 250.0])


def test_calibrate_standard_excludes_outlier_from_drift_fit_and_calibration_factor():
    # 5 occurrences, mean_signal = [100, 102, 98, 101, 5000] -- the last is a
    # clear outlier. Modified z-score (median=101, MAD=1) gives it |z|~3305,
    # far past the threshold=3.5 cutoff, so it must be excluded from both the
    # drift fit and the calibration-factor average; the kept-4 mean is 100.25.
    occurrences = [
        _occurrence(1, 100.0), _occurrence(2, 102.0), _occurrence(3, 98.0),
        _occurrence(4, 101.0), _occurrence(5, 5000.0),
    ]
    result = calibrate_standard(occurrences, REFERENCE, drift_order=0, standard_label="TESTSTD")

    assert result.excluded_outliers.get("Al27") == [5]
    assert result.drift_fits["Al27"].coeffs[0] == pytest.approx(100.25)
    assert result.calibration_factor["Al27"] == pytest.approx(500.0 / 100.25)

    # The outlier still appears in the accuracy table (visible, not silently
    # dropped from QC) and its huge deviation is flagged.
    outlier_rows = [r for r in result.accuracy_table if r.occurrence_order == 5]
    assert len(outlier_rows) == 1
    assert outlier_rows[0].flagged is True


def test_calibrate_standard_manual_occurrence_exclusion():
    """A manually-excluded occurrence (Standards QC click) must be dropped
    from the drift fit/calibration factor exactly like an automatically
    detected outlier, tracked SEPARATELY from excluded_outliers (since
    none of these 5 values look anomalous to the MAD screen), and marked
    on its accuracy_table row."""
    occurrences = [
        _occurrence(1, 100.0), _occurrence(2, 102.0), _occurrence(3, 98.0),
        _occurrence(4, 101.0), _occurrence(5, 99.0),
    ]
    result = calibrate_standard(
        occurrences, REFERENCE, drift_order=0, standard_label="TESTSTD",
        manual_occurrence_exclusions={"SYNSTD - 5.csv": {"Al27"}},
    )

    assert result.manually_excluded_occurrences.get("Al27") == [5]
    assert "Al27" not in result.excluded_outliers  # not an automatic MAD exclusion
    # Kept 4 values [100, 102, 98, 101] -> mean 100.25 (occurrence 5 dropped).
    assert result.drift_fits["Al27"].coeffs[0] == pytest.approx(100.25)
    assert result.calibration_factor["Al27"] == pytest.approx(500.0 / 100.25)

    manual_row = next(r for r in result.accuracy_table if r.occurrence_order == 5)
    assert manual_row.manually_excluded is True
    other_row = next(r for r in result.accuracy_table if r.occurrence_order == 1)
    assert other_row.manually_excluded is False


def test_assemble_occurrences_manual_row_exclusion():
    """A manually-excluded row within a standard occurrence's ablation
    window must be dropped from mean_signal/sem_signal, tracked in
    row_outlier_mask alongside the automatic screen."""
    dt = 0.2803
    n = 30

    def make_line_data(index, seed):
        rng = np.random.default_rng(seed)
        time_s = np.round(np.arange(1, n + 1) * dt, 4)
        absolute_time = np.array(
            [np.datetime64(BASE_TIME) + np.timedelta64(int(round(t * 1e6)), "us") for t in time_s]
        )
        bg = 500.0 + rng.normal(0, 5, 10)
        abl = 900000.0 + rng.normal(0, 500, n - 10)
        signal = pd.DataFrame({"Al27": np.concatenate([bg, abl])})
        meta = LineFileMeta(
            path=Path(f"SYNSTD - {index}.csv"), label="SYNSTD", index=index, is_standard=True,
            acquired_at=BASE_TIME, batch="Test.b",
        )
        return LineFileData(
            meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=["Al27"],
            signal=signal, dt_s=dt, n_rows=n,
        )

    line_data = make_line_data(1, seed=7)
    background = compute_background_result(line_data, reference_channels=["Al27"])
    manual_idx = background.ablation.included_start_idx + 2  # an absolute row well inside the ablation window

    occ_plain = assemble_occurrences([background])[0]
    occ_manual = assemble_occurrences(
        [background], manual_row_exclusions={"SYNSTD - 1.csv": {"Al27": {manual_idx}}},
    )[0]

    rel_idx = manual_idx - background.ablation.included_start_idx
    assert occ_manual.background.ablation.row_outlier_mask["Al27"][rel_idx]
    assert not occ_plain.background.ablation.row_outlier_mask["Al27"][rel_idx]
    assert occ_manual.mean_signal["Al27"] != pytest.approx(occ_plain.mean_signal["Al27"])


def test_combine_primary_standards_two_points_recovers_linear_fit():
    # STDA: mean CPS 100 -> ref 500. STDB: mean CPS 200 -> ref 1000. Exactly
    # proportional -- polyfit through 2 points recovers this line exactly.
    occ_a = [_occurrence(1, 100.0), _occurrence(2, 100.0), _occurrence(3, 100.0)]
    result_a = calibrate_standard(occ_a, REFERENCE, drift_order=0, standard_label="STDA")
    occ_b = [_occurrence(1, 200.0)]
    result_b = calibrate_standard(occ_b, REFERENCE_B, drift_order=0, standard_label="STDB")

    multi = combine_primary_standards({"STDA": result_a, "STDB": result_b}, ["STDA", "STDB"])

    curve = multi.curves["Al27"]
    assert curve.method == "multi_point_linear"
    assert curve.n_points == 2
    assert curve.slope == pytest.approx(5.0)
    assert curve.intercept == pytest.approx(0.0, abs=1e-6)
    assert curve.r_squared == pytest.approx(1.0)
    # STDA has 3 kept occurrences vs STDB's 1 -> STDA is the drift reference.
    assert multi.drift_reference_by_analyte["Al27"] == "STDA"


def test_combine_primary_standards_single_primary_matches_existing_ratio():
    occ_a = [_occurrence(1, 100.0), _occurrence(2, 102.0), _occurrence(3, 98.0), _occurrence(4, 100.0)]
    result_a = calibrate_standard(occ_a, REFERENCE, drift_order=0, standard_label="STDA")
    multi = combine_primary_standards({"STDA": result_a}, ["STDA"])

    curve = multi.curves["Al27"]
    assert curve.method == "single_point_ratio"
    assert curve.n_points == 1
    assert curve.slope == pytest.approx(result_a.calibration_factor["Al27"])
    assert curve.intercept == 0.0
    assert curve.r_squared is None


def test_combine_primary_standards_degenerate_cps_falls_back_to_ratio_through_mean():
    # Both primary standards report the identical mean CPS (100) for Al27
    # -- a line has no defined slope through a single x value.
    occ_a = [_occurrence(1, 100.0)]
    result_a = calibrate_standard(occ_a, REFERENCE, drift_order=0, standard_label="STDA")
    occ_b = [_occurrence(1, 100.0)]
    result_b = calibrate_standard(occ_b, REFERENCE_B, drift_order=0, standard_label="STDB")

    multi = combine_primary_standards({"STDA": result_a, "STDB": result_b}, ["STDA", "STDB"])
    curve = multi.curves["Al27"]
    assert curve.n_points == 2
    assert curve.slope == pytest.approx(7.5)  # mean ppm (500+1000)/2=750 / mean cps 100
    assert curve.intercept == pytest.approx(0.0)


def test_combine_primary_standards_force_zero_intercept_uses_least_squares_through_origin():
    # STDA: mean CPS 100 -> ref 500. STDC: mean CPS 200 -> ref 900 -- NOT
    # proportional to STDA's ratio (900/200=4.5 vs 500/100=5), so a free
    # intercept fits both points exactly (any 2 points always do), but a
    # forced-origin fit (only one free parameter) can't -- exactly what
    # distinguishes the two methods.
    occ_a = [_occurrence(1, 100.0)]
    result_a = calibrate_standard(occ_a, REFERENCE, drift_order=0, standard_label="STDA")
    occ_c = [_occurrence(1, 200.0)]
    result_c = calibrate_standard(occ_c, REFERENCE_C, drift_order=0, standard_label="STDC")

    multi = combine_primary_standards(
        {"STDA": result_a, "STDC": result_c}, ["STDA", "STDC"], force_zero_intercept=True,
    )
    curve = multi.curves["Al27"]
    assert curve.method == "multi_point_zero_intercept"
    assert curve.intercept == 0.0
    # slope = sum(cps*ppm) / sum(cps**2) = (100*500 + 200*900) / (100**2 + 200**2) = 4.6
    assert curve.slope == pytest.approx(4.6)
    # r_squared uses the uncentered total sum of squares (see docstring) --
    # not 1.0 here, unlike the free-intercept case, since one slope
    # parameter can't satisfy two non-proportional points exactly.
    predicted = 4.6 * np.array([100.0, 200.0])
    ss_res = float(np.sum((np.array([500.0, 900.0]) - predicted) ** 2))
    ss_tot = float(np.sum(np.array([500.0, 900.0]) ** 2))
    assert curve.r_squared == pytest.approx(1.0 - ss_res / ss_tot)


def test_combine_primary_standards_force_zero_intercept_degenerate_falls_back_to_ratio_through_mean():
    occ_a = [_occurrence(1, 100.0)]
    result_a = calibrate_standard(occ_a, REFERENCE, drift_order=0, standard_label="STDA")
    occ_b = [_occurrence(1, 100.0)]
    result_b = calibrate_standard(occ_b, REFERENCE_B, drift_order=0, standard_label="STDB")

    multi = combine_primary_standards(
        {"STDA": result_a, "STDB": result_b}, ["STDA", "STDB"], force_zero_intercept=True,
    )
    curve = multi.curves["Al27"]
    assert curve.method == "multi_point_zero_intercept"
    assert curve.slope == pytest.approx(7.5)
    assert curve.intercept == pytest.approx(0.0)


def test_apply_multi_point_calibration_matches_apply_calibration_for_single_standard():
    """Regression/equivalence lock: with exactly one primary standard, the
    multi-point path must produce numerically identical output to the
    existing single-point apply_calibration."""
    occ_a = [_occurrence(1, 98.0), _occurrence(2, 102.0)]
    result_a = calibrate_standard(occ_a, REFERENCE, drift_order=0, standard_label="STDA")
    multi = combine_primary_standards({"STDA": result_a}, ["STDA"])

    sample_signal = pd.DataFrame({"Al27": [100.0, 200.0, 50.0]})
    sample_times = [BASE_TIME, BASE_TIME + timedelta(minutes=5), BASE_TIME + timedelta(minutes=15)]

    expected = apply_calibration(sample_signal, sample_times, result_a)
    actual = apply_multi_point_calibration(sample_signal, sample_times, multi, {"STDA": result_a})

    assert np.allclose(actual["Al27"].to_numpy(), expected["Al27"].to_numpy())


def test_calibrate_standard_detrend_recovers_linear_residual_trend():
    # mean_signal increases linearly [90,95,100,105,110] at orders 1-5;
    # order-0 drift fit gives mean=100 (constant across time), scale=
    # 500/100=5 -- so observed_value = mean_signal*5 = [450,475,500,525,550],
    # a perfect linear trend in (observed-reference) vs time.
    occurrences = [_occurrence(i, 90.0 + 5 * (i - 1)) for i in range(1, 6)]
    result = calibrate_standard(occurrences, REFERENCE, drift_order=0, standard_label="TESTSTD", detrend=True)

    assert "Al27" in result.detrend_fits
    detrend_fit = result.detrend_fits["Al27"]
    for r in result.accuracy_table:
        predicted = detrend_fit.predict([r.time])[0]
        assert predicted == pytest.approx(r.difference, abs=1e-6)

    # Without detrend=True (the default), no detrend_fits are computed.
    result_no_detrend = calibrate_standard(occurrences, REFERENCE, drift_order=0, standard_label="TESTSTD")
    assert result_no_detrend.detrend_fits == {}


def test_apply_calibration_subtracts_detrend_correction():
    occurrences = [_occurrence(i, 90.0 + 5 * (i - 1)) for i in range(1, 6)]
    result = calibrate_standard(occurrences, REFERENCE, drift_order=0, standard_label="TESTSTD", detrend=True)

    # At occurrence 3's own time (difference=0 there), detrending is a no-op.
    sample_signal = pd.DataFrame({"Al27": [100.0]})
    sample_time = [occurrences[2].file_meta.acquired_at]
    calibrated = apply_calibration(sample_signal, sample_time, result)
    assert calibrated["Al27"].iloc[0] == pytest.approx(500.0, abs=1e-6)

    # At occurrence 5's own time (difference=+50), detrending pulls the
    # calibrated value down by exactly that amount relative to no detrend.
    sample_time2 = [occurrences[4].file_meta.acquired_at]
    result_no_detrend = calibrate_standard(occurrences, REFERENCE, drift_order=0, standard_label="TESTSTD")
    calibrated_no_detrend = apply_calibration(sample_signal, sample_time2, result_no_detrend)
    calibrated_with_detrend = apply_calibration(sample_signal, sample_time2, result)
    assert calibrated_with_detrend["Al27"].iloc[0] == pytest.approx(
        calibrated_no_detrend["Al27"].iloc[0] - 50.0, abs=1e-6
    )


def test_apply_multi_point_calibration_two_standards():
    occ_a = [_occurrence(1, 100.0), _occurrence(2, 100.0), _occurrence(3, 100.0)]
    result_a = calibrate_standard(occ_a, REFERENCE, drift_order=0, standard_label="STDA")
    occ_b = [_occurrence(1, 200.0)]
    result_b = calibrate_standard(occ_b, REFERENCE_B, drift_order=0, standard_label="STDB")
    standard_results = {"STDA": result_a, "STDB": result_b}
    multi = combine_primary_standards(standard_results, ["STDA", "STDB"])

    # slope=5, intercept=0 (see test_combine_primary_standards_two_points_...),
    # drift reference is STDA (mean_predicted_signal=100, order-0 constant fit).
    sample_signal = pd.DataFrame({"Al27": [100.0, 50.0]})
    sample_times = [BASE_TIME, BASE_TIME + timedelta(minutes=5)]
    calibrated = apply_multi_point_calibration(sample_signal, sample_times, multi, standard_results)

    # normalized_cps = signal/100(constant fit)*100 = signal itself here -> *slope(5)+0.
    assert np.allclose(calibrated["Al27"].to_numpy(), [500.0, 250.0])


def test_mad_outlier_mask_skips_rejection_with_fewer_than_4_points():
    # Only 3 points -- not enough to distinguish a real outlier from
    # ordinary scatter, so nothing is excluded even though 1000 looks extreme.
    assert _mad_outlier_mask([1.0, 2.0, 1000.0]) == [True, True, True]


def test_mad_outlier_mask_handles_identical_values():
    assert _mad_outlier_mask([5.0, 5.0, 5.0, 5.0]) == [True, True, True, True]


def test_assemble_occurrences_orders_by_true_acquisition_time_not_filename_index():
    dt = 0.2803
    n = 30

    def make_line_data(index, acquired_at, seed):
        rng = np.random.default_rng(seed)
        time_s = np.round(np.arange(1, n + 1) * dt, 4)
        absolute_time = np.array([np.datetime64(acquired_at) + np.timedelta64(int(round(t * 1e6)), "us") for t in time_s])
        bg = 500.0 + rng.normal(0, 5, 10)
        abl = 900000.0 + rng.normal(0, 500, n - 10)
        signal = pd.DataFrame({"Al27": np.concatenate([bg, abl])})
        meta = LineFileMeta(
            path=Path(f"SYNSTD - {index}.csv"), label="SYNSTD", index=index, is_standard=True,
            acquired_at=acquired_at, batch="Test.b",
        )
        return LineFileData(meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=["Al27"], signal=signal, dt_s=dt, n_rows=n)

    # Filename index 2 was acquired BEFORE filename index 1 -- true time order must win.
    line_2 = make_line_data(2, BASE_TIME, seed=1)
    line_1 = make_line_data(1, BASE_TIME + timedelta(minutes=10), seed=2)

    backgrounds = [compute_background_result(line_2, reference_channels=["Al27"]), compute_background_result(line_1, reference_channels=["Al27"])]
    occurrences = assemble_occurrences(backgrounds)

    assert [o.file_meta.index for o in occurrences] == [2, 1]
    assert [o.occurrence_order for o in occurrences] == [1, 2]


# ---------------------------------------------------------------------------
# Poisson-statistics drift method (poisson_background_spec.md)
# ---------------------------------------------------------------------------

def _make_standard_line_data(bg_values: dict, ablation_level: float, ablation_n=15, seed=0, index=1, acquired_at=None):
    acquired_at = acquired_at or BASE_TIME
    bg_n = len(next(iter(bg_values.values())))
    n = bg_n + ablation_n
    dt = 0.2803
    time_s = np.round(np.arange(1, n + 1) * dt, 4)
    absolute_time = np.array([np.datetime64(acquired_at) + np.timedelta64(int(round(t * 1e6)), "us") for t in time_s])
    rng = np.random.default_rng(seed)
    signal_cols = {}
    for analyte, bg in bg_values.items():
        abl = ablation_level + rng.normal(0, max(ablation_level * 0.01, 1.0), ablation_n)
        signal_cols[analyte] = np.concatenate([np.asarray(bg, dtype=float), abl])
    signal = pd.DataFrame(signal_cols)
    meta = LineFileMeta(
        path=Path(f"SYNSTD - {index}.csv"), label="SYNSTD", index=index, is_standard=True,
        acquired_at=acquired_at, batch="Test.b",
    )
    return LineFileData(
        meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=list(bg_values.keys()),
        signal=signal, dt_s=dt, n_rows=n,
    )


def _build_occurrences(n_files, bg_rate_cps, ablation_level, tau_true=0.2, seed=0):
    rng = np.random.default_rng(seed)
    backgrounds = []
    for i in range(n_files):
        bg_values = {
            "Al27": 500.0 + rng.normal(0, 20, 30),   # used for step detection
            "Yb172": rng.poisson(bg_rate_cps * tau_true, size=30) / tau_true,
        }
        line_data = _make_standard_line_data(
            bg_values, ablation_level=ablation_level, ablation_n=15,
            seed=int(rng.integers(0, 1_000_000)), index=i + 1,
            acquired_at=BASE_TIME + timedelta(minutes=10 * i),
        )
        backgrounds.append(compute_background_result(line_data, reference_channels=["Al27"]))
    return assemble_occurrences(backgrounds)


def test_calibrate_standard_auto_poisson_lrt_uses_poisson_path_when_background_negligible():
    # Yb172 background rate ~3 CPS vs. ablation ~500 CPS (~0.6%) -- well under
    # the default 5% negligibility threshold. bg_rate_cps is high enough
    # (expected ~18 counts per 30-row background window) that no file's
    # background window is likely to land on all-zero counts by chance,
    # which would otherwise give that file "unknown" tau provenance and
    # (correctly) break eligibility for the whole analyte.
    occurrences = _build_occurrences(n_files=8, bg_rate_cps=3.0, ablation_level=500.0, seed=1)
    reference = parse_reference_material({
        "standard": "TESTSTD_YB",
        "analytes": {"Yb172": {"element": "Yb", "mass": 172, "value": 50.0, "uncertainty": 1.0, "uncertainty_type": "1SD"}},
    })
    result = calibrate_standard(occurrences, reference, method="auto_poisson_lrt", max_order=3, standard_label="TESTSTD_YB")
    assert isinstance(result.drift_fits["Yb172"], PoissonDriftFit)
    assert "Yb172" in result.calibration_factor


def test_calibrate_standard_auto_poisson_lrt_falls_back_when_background_not_negligible():
    # Yb172 background rate ~50 CPS vs. ablation ~150 CPS (~33%) -- well over
    # the 5% threshold, so this analyte must fall back to auto_aic (a plain
    # DriftFit), not use the raw-counts Poisson path.
    occurrences = _build_occurrences(n_files=8, bg_rate_cps=10.0, ablation_level=150.0, seed=2)
    reference = parse_reference_material({
        "standard": "TESTSTD_YB2",
        "analytes": {"Yb172": {"element": "Yb", "mass": 172, "value": 50.0, "uncertainty": 1.0, "uncertainty_type": "1SD"}},
    })
    result = calibrate_standard(occurrences, reference, method="auto_poisson_lrt", max_order=3, standard_label="TESTSTD_YB2")
    assert isinstance(result.drift_fits["Yb172"], DriftFit)
    assert not isinstance(result.drift_fits["Yb172"], PoissonDriftFit)


def test_calibrate_standard_method_fixed_is_backward_compatible():
    # The pre-existing test helper's StandardOccurrence stubs (background=None)
    # must still work when method="fixed" (the default) -- the Poisson
    # eligibility check must never be reached in that path.
    occurrences = [_occurrence(1, 98.0), _occurrence(2, 100.0), _occurrence(3, 102.0), _occurrence(4, 100.0)]
    result = calibrate_standard(occurrences, REFERENCE, drift_order=0, standard_label="TESTSTD")
    assert isinstance(result.drift_fits["Al27"], DriftFit)
    assert not isinstance(result.drift_fits["Al27"], PoissonDriftFit)
