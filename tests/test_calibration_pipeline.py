"""End-to-end pipeline test over a small synthetic raw-data directory (not
the real proprietary data), plus multi-sample-folder discovery/batch tests.

Pure Python -- no PyQt/QApplication needed.
"""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.background import BackgroundWindowOverride
from src.calibration.dating_ratios import DatingRatioSpec
from src.calibration.isotope_apportion import IsotopeShareSpec
from src.calibration.massbias import BiasSpec, natural_abundance_ratio
from src.calibration.pipeline import (
    PipelineError,
    discover_sample_directories,
    run,
    run_batch,
    run_from_parsed,
)
from src.calibration.rawfile import list_line_files, parse_line_file
from src.calibration.pooling import PooledElementSpec, combined_abundance_fraction
from src.calibration.reflib import parse_reference_material

ANALYTES = ["Al27", "Ca43"]


def _write_raw_file(directory: Path, label: str, index: int, acquired_at: datetime,
                     bg_level=(500.0, 300.0), ablation_level=(900000.0, 600000.0),
                     bg_n=10, ablation_n=20, seed=0, analytes=None):
    analytes = analytes or ANALYTES
    rng = random.Random(seed)
    lines = []
    stem = f"{label} - {index}"
    lines.append(rf"S:\Data\Synthetic\SyntheticBatch.b\{stem}.d")
    lines.append("Intensity Vs Time,CPS")
    acquired_str = acquired_at.strftime("%d/%m/%Y %H:%M:%S")
    lines.append(f"Acquired      : {acquired_str} using Batch SyntheticBatch.b")
    lines.append("Time [Sec]," + ",".join(analytes))

    t = 0.30
    dt = 0.30
    for _ in range(bg_n):
        row = [t] + [lvl + rng.uniform(-lvl * 0.05, lvl * 0.05) for lvl in bg_level]
        lines.append(",".join(f"{v:.2f}" if i > 0 else f"{v:.4f}" for i, v in enumerate(row)))
        t += dt
    for _ in range(ablation_n):
        row = [t] + [lvl + rng.uniform(-lvl * 0.02, lvl * 0.02) for lvl in ablation_level]
        lines.append(",".join(f"{v:.2f}" if i > 0 else f"{v:.4f}" for i, v in enumerate(row)))
        t += dt

    lines.append("")
    lines.append("")
    printed = (acquired_at + timedelta(seconds=t)).strftime("%d/%m/%Y %H:%M:%S")
    lines.append(f"          Printed:{printed}")

    content = "\r\n".join(lines) + "\r\n"
    (directory / f"{stem}.csv").write_bytes(content.encode("ascii"))


def _reference_library():
    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {
            "Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"},
            "Ca43": {"element": "Ca", "mass": 43, "value": 300.0, "uncertainty": 3.0, "uncertainty_type": "1SD"},
        },
    })
    return {"NIST610": material}


def _make_sample_dir(directory: Path):
    base = datetime(2026, 3, 1, 10, 0, 0)
    _write_raw_file(directory, "NIST610", 1, base, seed=1)
    _write_raw_file(directory, "SAMPLE", 1, base + timedelta(minutes=15), seed=2)
    _write_raw_file(directory, "SAMPLE", 2, base + timedelta(minutes=30), seed=3)
    _write_raw_file(directory, "NIST610", 2, base + timedelta(minutes=45), seed=4)


def test_run_end_to_end_produces_calibrated_ppm(tmp_path):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0,
    )

    assert set(results.keys()) == {"SAMPLE"}
    result = results["SAMPLE"]
    assert result.sample_label == "SAMPLE"
    assert not result.calibrated_ppm.empty
    assert "Al27" in result.calibrated_ppm.columns
    assert result.calibrated_ppm["Al27"].notna().all()
    assert not result.grid_index.empty
    assert set(result.grid_index["line_number"]) == {0, 1}

    assert result.provenance["sample_label"] == "SAMPLE"
    assert result.provenance["primary_standards"] == ["NIST610"]
    assert result.provenance["drift_order"] == 0
    assert result.provenance["raw_dir"] == str(sample_dir)
    assert "NIST610" in result.standard_results


def test_ablation_onset_trim_shortens_every_line(tmp_path):
    """Each synthetic line has 20 ablation rows at dt=0.30s -- trimming
    0.9s (3 rows) should drop every line (standards and samples alike,
    the ramp is a physical artifact affecting both) to 17 rows, and the
    calibrated_ppm/grid_index row counts should shrink to match."""
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    baseline = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0,
    )["SAMPLE"]
    trimmed = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0, ablation_onset_trim_s=0.9,
    )["SAMPLE"]

    assert len(baseline.calibrated_ppm) == len(trimmed.calibrated_ppm) + 3 * 2  # 2 sample lines
    for line_number in trimmed.grid_index["line_number"].unique():
        n_baseline = int((baseline.grid_index["line_number"] == line_number).sum())
        n_trimmed = int((trimmed.grid_index["line_number"] == line_number).sum())
        assert n_trimmed == n_baseline - 3
    # sweep_index is re-based to 0 for the trimmed line, not shifted
    assert trimmed.grid_index["sweep_index"].min() == 0


def test_run_from_parsed_matches_run(tmp_path):
    """Regression test for the run()/run_from_parsed() extraction
    (_run_from_files): given the exact files run() would have parsed
    itself, run_from_parsed() must produce identical calibrated_ppm/
    grid_index/qc_report -- proves the refactor changed nothing about
    run()'s own behavior, only added a second entry point."""
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    kwargs = dict(
        standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0,
    )
    run_results = run(sample_dir, **kwargs)

    files = [
        parse_line_file(p, standard_names={"NIST610"})
        for p in list_line_files(sample_dir)
    ]
    parsed_kwargs = dict(kwargs)
    parsed_kwargs.pop("standard_names")
    parsed_results = run_from_parsed(files, sample_dir, **parsed_kwargs)

    assert set(run_results.keys()) == set(parsed_results.keys()) == {"SAMPLE"}
    run_sample, parsed_sample = run_results["SAMPLE"], parsed_results["SAMPLE"]
    pd.testing.assert_frame_equal(run_sample.calibrated_ppm, parsed_sample.calibrated_ppm)
    pd.testing.assert_frame_equal(run_sample.grid_index, parsed_sample.grid_index)
    assert run_sample.qc_report == parsed_sample.qc_report


def test_run_calibrates_sibling_isotope_with_no_reference_key(tmp_path):
    # Reference material only has a "U238" entry (GeoREM's elemental-total
    # convention) -- U235 has no key of its own but must still calibrate,
    # unscaled, via U238's entry (element-based fallback).
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    # Equal levels for both columns (rather than the default mismatched
    # per-column levels) so U235/U238 share the same CPS magnitude in both
    # the standard and the sample, isolating the fallback-lookup behavior
    # under test from unrelated per-column signal-level differences.
    u_analytes = ["U235", "U238"]
    u_bg, u_abl = (500.0, 500.0), (900000.0, 900000.0)
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1, analytes=u_analytes, bg_level=u_bg, ablation_level=u_abl)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=u_analytes, bg_level=u_bg, ablation_level=u_abl)
    _write_raw_file(sample_dir, "NIST610", 2, base + timedelta(minutes=45), seed=4, analytes=u_analytes, bg_level=u_bg, ablation_level=u_abl)

    library = {"NIST610": parse_reference_material({
        "standard": "NIST610",
        "analytes": {"U238": {"element": "U", "mass": 238, "value": 461.5, "uncertainty": 1.0, "uncertainty_type": "1SD"}},
    })}

    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=library,
        drift_order=0, background_drift_order=0,
    )
    result = results["SAMPLE"]

    assert "U235" not in result.standard_results["NIST610"].skipped_analytes
    assert "U235" in result.calibrated_ppm.columns
    assert result.calibrated_ppm["U235"].notna().all()
    # Elemental mode: both isotopes calibrate to the same total-U-equivalent
    # concentration, since sample/standard share the same U235/U238 CPS
    # magnitude (independent per-column synthetic noise -> a loose tolerance).
    assert result.calibrated_ppm["U235"].mean() == pytest.approx(result.calibrated_ppm["U238"].mean(), rel=0.1)


def test_run_with_bias_specs_produces_mass_bias_corrected_ratio(tmp_path):
    # No injected instrumental fractionation here (both standard and
    # sample columns are written with their own fixed, noise-only CPS
    # ratio) -- this end-to-end test is about the WIRING (bias_specs ->
    # bias_fits -> calibrated_ratios), not re-deriving the mass-bias law
    # itself (already hand-verified in test_calibration_massbias.py). The
    # standard's own measured ratio matches its certified truth (17.0) by
    # construction, so the fitted bias curve should be ~1 (no correction
    # needed), and the SAMPLE's own (different, 15.0) ratio should survive
    # essentially unchanged -- confirming the correction preserves the
    # sample's own ratio rather than snapping it to the standard's.
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    pb_analytes = ["Pb204", "Pb206"]
    std_bg, std_abl = (500.0, 8500.0), (100000.0, 1700000.0)   # ratio 17.0, matches certified truth
    sample_bg, sample_abl = (500.0, 7500.0), (100000.0, 1500000.0)  # ratio 15.0 -- the sample's own true ratio
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1, analytes=pb_analytes, bg_level=std_bg, ablation_level=std_abl)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=pb_analytes, bg_level=sample_bg, ablation_level=sample_abl)
    _write_raw_file(sample_dir, "NIST610", 2, base + timedelta(minutes=45), seed=4, analytes=pb_analytes, bg_level=std_bg, ablation_level=std_abl)

    library = {"NIST610": parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Pb204": {"element": "Pb", "mass": 204, "value": 2.0, "uncertainty": 0.1, "uncertainty_type": "1SD"}},
        "isotope_ratios": {
            "Pb206/Pb204": {
                "numerator_element": "Pb", "numerator_mass": 206, "denominator_element": "Pb", "denominator_mass": 204,
                "value": 17.0, "uncertainty": 0.01, "uncertainty_type": "1SD", "source": "test",
            },
        },
    })}

    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=library,
        drift_order=0, background_drift_order=0,
        bias_specs=[BiasSpec(element="Pb", numerator_mass=206, denominator_mass=204)],
        bias_drift_order=0,
    )
    result = results["SAMPLE"]

    assert "Pb206/Pb204" in result.bias_fits
    assert result.bias_fits["Pb206/Pb204"].truth.source == "certified_reference_ratio"
    assert not result.calibrated_ratios.empty
    assert "Pb206 / Pb204" in result.calibrated_ratios.columns
    mean_ratio = result.calibrated_ratios["Pb206 / Pb204"].mean()
    # Loose tolerance -- synthetic per-column noise (independent ±2%/±5%
    # draws on each of Pb204/Pb206) propagates disproportionately into a
    # ratio of two noisy channels; the numeric details of the mass-bias
    # law itself are already hand-verified in test_calibration_massbias.py.
    # This end-to-end test only needs to show the corrected ratio reflects
    # the SAMPLE's own (15.0) ratio, clearly distinct from the standard's
    # (17.0) -- i.e. the correction didn't just snap to the standard.
    assert abs(mean_ratio - 15.0) < abs(mean_ratio - 17.0)
    assert mean_ratio == pytest.approx(15.0, rel=0.3)
    assert result.qc_report["bias_fits"]["Pb206/Pb204"]["truth_value"] == pytest.approx(17.0)
    assert result.provenance["bias_specs"][0]["element"] == "Pb"


def test_run_with_isotope_share_specs_apportions_isotopic_ppm(tmp_path):
    # Extends the Pb206/Pb204 bias-spec fixture above to all three Pb
    # companion masses, then requests isotope_share_specs to check the
    # apportionment reconciles with the elemental (Mechanism A) total --
    # this is a pure algebraic identity of apportion_element_ppm, so it
    # must hold exactly (row by row) regardless of the actual ratio noise.
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    pb_analytes = ["Pb204", "Pb206", "Pb207", "Pb208"]
    # Standard: ratios matching certified truth (206/204=17.0, 207/204=15.5,
    # 208/204=36.0) so the fitted bias curves are ~1 (no correction needed).
    std_bg, std_abl = (500.0, 8500.0, 7750.0, 18000.0), (100000.0, 1700000.0, 1550000.0, 3600000.0)
    # Sample: its own different true ratios (206/204=16.0, 207/204=14.0, 208/204=34.0).
    sample_bg, sample_abl = (500.0, 8000.0, 7000.0, 17000.0), (100000.0, 1600000.0, 1400000.0, 3400000.0)
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1, analytes=pb_analytes, bg_level=std_bg, ablation_level=std_abl)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=pb_analytes, bg_level=sample_bg, ablation_level=sample_abl)
    _write_raw_file(sample_dir, "NIST610", 2, base + timedelta(minutes=45), seed=4, analytes=pb_analytes, bg_level=std_bg, ablation_level=std_abl)

    def _ratio(num_mass, value):
        return {
            "numerator_element": "Pb", "numerator_mass": num_mass, "denominator_element": "Pb", "denominator_mass": 204,
            "value": value, "uncertainty": 0.01, "uncertainty_type": "1SD", "source": "test",
        }

    library = {"NIST610": parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Pb204": {"element": "Pb", "mass": 204, "value": 2.0, "uncertainty": 0.1, "uncertainty_type": "1SD"}},
        "isotope_ratios": {
            "Pb206/Pb204": _ratio(206, 17.0),
            "Pb207/Pb204": _ratio(207, 15.5),
            "Pb208/Pb204": _ratio(208, 36.0),
        },
    })}

    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=library,
        drift_order=0, background_drift_order=0,
        bias_specs=[
            BiasSpec(element="Pb", numerator_mass=206, denominator_mass=204),
            BiasSpec(element="Pb", numerator_mass=207, denominator_mass=204),
            BiasSpec(element="Pb", numerator_mass=208, denominator_mass=204),
        ],
        bias_drift_order=0,
        isotope_share_specs=[IsotopeShareSpec(element="Pb", normalizer_mass=204, companion_masses=[206, 207, 208])],
    )
    result = results["SAMPLE"]

    assert not result.isotopic_ppm.empty
    for col in ["Pb204", "Pb206", "Pb207", "Pb208"]:
        assert col in result.isotopic_ppm.columns

    total_reconstructed = result.isotopic_ppm[["Pb204", "Pb206", "Pb207", "Pb208"]].sum(axis=1)
    pd.testing.assert_series_equal(
        total_reconstructed.reset_index(drop=True), result.calibrated_ppm["Pb204"].reset_index(drop=True),
        check_names=False, rtol=1e-6,
    )

    # The sample's own (16.0 > 14.0) ratio should dominate the split, not
    # the standard's own (17.0/15.5) values.
    assert result.isotopic_ppm["Pb206"].mean() > result.isotopic_ppm["Pb207"].mean()

    assert result.isotopic_ppm_provenance["Pb"] == {
        "normalizer_mass": 204, "included_masses": [206, 207, 208], "missing_masses": [],
    }
    assert result.qc_report["isotopic_ppm"]["Pb"]["included_masses"] == [206, 207, 208]
    assert result.provenance["isotope_share_specs"][0]["element"] == "Pb"


def test_run_with_pool_specs_produces_pooled_element_channel(tmp_path):
    # Pb206/Pb207/Pb208 measured (no Pb204) with equal CPS levels shared
    # between standard and sample (isolating the pooling wiring itself from
    # unrelated per-column magnitude differences, same convention as
    # test_run_calibrates_sibling_isotope_with_no_reference_key). The
    # reference material only carries a "Pb206" elemental entry -- the
    # pooled "Pb total" channel must resolve against it via
    # reflib.resolve_elemental_value's " total" handling.
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    pb_analytes = ["Pb206", "Pb207", "Pb208"]
    pb_bg, pb_abl = (500.0, 500.0, 500.0), (900000.0, 900000.0, 900000.0)
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1, analytes=pb_analytes, bg_level=pb_bg, ablation_level=pb_abl)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=pb_analytes, bg_level=pb_bg, ablation_level=pb_abl)
    _write_raw_file(sample_dir, "NIST610", 2, base + timedelta(minutes=45), seed=4, analytes=pb_analytes, bg_level=pb_bg, ablation_level=pb_abl)

    library = {"NIST610": parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Pb206": {"element": "Pb", "mass": 206, "value": 461.5, "uncertainty": 1.0, "uncertainty_type": "1SD"}},
    })}

    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=library,
        drift_order=0, background_drift_order=0,
        pool_specs=[PooledElementSpec(element="Pb", masses=[206, 207, 208])],
    )
    result = results["SAMPLE"]

    assert "Pb total" not in result.standard_results["NIST610"].skipped_analytes
    assert "Pb total" in result.calibrated_ppm.columns
    assert result.calibrated_ppm["Pb total"].notna().all()
    # Pooling doesn't change the calibrated total-element estimate (ratio
    # cancellation applies to a fixed isotope subset the same way it does
    # to a single isotope) -- just its precision, so it should closely
    # track any single constituent isotope's own elemental estimate.
    assert result.calibrated_ppm["Pb total"].mean() == pytest.approx(result.calibrated_ppm["Pb206"].mean(), rel=0.1)

    assert result.provenance["pool_specs"] == [{"element": "Pb", "masses": [206, 207, 208]}]


def test_run_with_dating_ratio_specs_produces_cross_element_dating_ratios(tmp_path):
    # U238+Pb206+Pb207+Th232+Pb208 zircon-style fixture. Standard's own raw
    # CPS ratios are set to EXACTLY match the reference material's
    # certified values, so with drift_order=0 the fitted correction factor
    # is ~1 and each dating ratio's calibrated output should closely track
    # the SAMPLE's own (deliberately different) raw ratio -- same
    # "recovers the sample, not the standard" convention as
    # test_run_with_bias_specs_produces_mass_bias_corrected_ratio. Also
    # requests a same-element Pb207/Pb206 BiasSpec alongside the
    # cross-element DatingRatioSpecs, confirming both mechanisms coexist
    # in one shared calibrated_ratios frame without collision.
    #
    # bg_n/ablation_n are explicitly widened past _write_raw_file's default
    # (10/20 -- only 30 rows total) -- detect_background_window's changepoint
    # scan needs more than ~30 rows to run at all (its tail_margin=20/
    # search_margin=5 defaults leave no room to scan in a 30-row file), and
    # silently falls back to a fixed half-and-half window on files this
    # short, corrupting background subtraction (confirmed while debugging
    # this fixture). Every other test in this file uses small default
    # levels where that fallback's error happens to be small; this test's
    # widely different per-column magnitudes (U238 ~900000 vs Pb207 ~6000)
    # made the fallback's error large enough to break the ratio checks below.
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    analytes = ["U238", "Pb206", "Pb207", "Th232", "Pb208"]

    std_bg = (500.0, 500.0, 500.0, 500.0, 500.0)
    std_abl = (900000.0, 90000.0, 6000.0, 900000.0, 45000.0)  # Pb206/U238=0.1, Pb207/U238=0.006667, Pb208/Th232=0.05
    sample_bg = (500.0, 500.0, 500.0, 500.0, 500.0)
    sample_abl = (900000.0, 126000.0, 5400.0, 900000.0, 63000.0)  # Pb206/U238=0.14, Pb207/U238=0.006, Pb208/Th232=0.07

    _write_raw_file(sample_dir, "ZRNSTD", 1, base, seed=1, analytes=analytes, bg_level=std_bg, ablation_level=std_abl, bg_n=15, ablation_n=30)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=analytes, bg_level=sample_bg, ablation_level=sample_abl, bg_n=15, ablation_n=30)
    _write_raw_file(sample_dir, "ZRNSTD", 2, base + timedelta(minutes=45), seed=4, analytes=analytes, bg_level=std_bg, ablation_level=std_abl, bg_n=15, ablation_n=30)

    k = natural_abundance_ratio("U", 238, 235)
    truth_207_235 = k * (6000.0 / 900000.0)

    def _ratio(num_el, num_mass, den_el, den_mass, value):
        return {
            "numerator_element": num_el, "numerator_mass": num_mass,
            "denominator_element": den_el, "denominator_mass": den_mass,
            "value": value, "uncertainty": 0.001, "uncertainty_type": "1SD", "source": "test",
        }

    library = {"ZRNSTD": parse_reference_material({
        "standard": "ZRNSTD",
        "analytes": {"Pb206": {"element": "Pb", "mass": 206, "value": 0.05, "uncertainty": 0.0005, "uncertainty_type": "1SD"}},
        "isotope_ratios": {
            "Pb206/U238": _ratio("Pb", 206, "U", 238, 90000.0 / 900000.0),
            "Pb207/U238": _ratio("Pb", 207, "U", 238, truth_207_235),
            "Pb208/Th232": _ratio("Pb", 208, "Th", 232, 45000.0 / 900000.0),
            "Pb207/Pb206": _ratio("Pb", 207, "Pb", 206, 6000.0 / 90000.0),
        },
    })}

    results = run(
        sample_dir, standard_names={"ZRNSTD"}, reference_library=library,
        drift_order=0, background_drift_order=0,
        bias_specs=[BiasSpec(element="Pb", numerator_mass=207, denominator_mass=206)],
        bias_drift_order=0,
        dating_ratio_specs=[
            DatingRatioSpec(numerator_element="Pb", numerator_mass=206, denominator_element="U", denominator_mass=238),
            DatingRatioSpec(numerator_element="Pb", numerator_mass=207, denominator_element="U", denominator_mass=238, numerator_scale_factor=k),
            DatingRatioSpec(numerator_element="Pb", numerator_mass=208, denominator_element="Th", denominator_mass=232),
        ],
        dating_ratio_drift_order=0,
    )
    result = results["SAMPLE"]

    assert set(result.dating_ratio_fits) == {"Pb206/U238", "Pb207/U238", "Pb208/Th232"}
    assert "Pb207/Pb206" in result.bias_fits

    for col in ["Pb206 / U238", "Pb207 / U238", "Pb208 / Th232", "Pb207 / Pb206"]:
        assert col in result.calibrated_ratios.columns

    # Loose tolerance + directional checks, not tight equality -- independent
    # per-column synthetic noise (only 2 standard occurrences here) propagates
    # disproportionately into a ratio of two noisy channels, same reasoning
    # as test_run_with_bias_specs_produces_mass_bias_corrected_ratio. Each
    # assertion instead confirms the corrected ratio reflects the SAMPLE's
    # own ratio, clearly closer to it than to the standard's.
    def _closer_to_sample_than_standard(observed, sample_true, std_true):
        assert abs(observed - sample_true) < abs(observed - std_true)
        assert observed == pytest.approx(sample_true, rel=0.3)

    _closer_to_sample_than_standard(result.calibrated_ratios["Pb206 / U238"].mean(), 0.14, 0.1)
    _closer_to_sample_than_standard(result.calibrated_ratios["Pb207 / U238"].mean(), k * 0.006, k * (6000.0 / 900000.0))
    _closer_to_sample_than_standard(result.calibrated_ratios["Pb208 / Th232"].mean(), 0.07, 0.05)
    _closer_to_sample_than_standard(result.calibrated_ratios["Pb207 / Pb206"].mean(), 5400.0 / 126000.0, 6000.0 / 90000.0)

    assert result.qc_report["dating_ratio_fits"]["Pb206/U238"]["truth_value"] == pytest.approx(0.1)
    assert result.provenance["dating_ratio_specs"][0]["numerator_element"] == "Pb"


def test_run_excludes_files_via_excluded_files_param(tmp_path):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0, excluded_files={"NIST610 - 2.csv"},
    )

    result = results["SAMPLE"]
    assert result.provenance["excluded_files"] == ["NIST610 - 2.csv"]
    # Only the one remaining NIST610 file's occurrence should have been used.
    assert len(result.standard_results["NIST610"].occurrences) == 1


def test_run_raises_when_all_files_excluded(tmp_path):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)
    excluded = {p.name for p in sample_dir.glob("*.csv")}

    with pytest.raises(PipelineError):
        run(
            sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
            drift_order=0, background_drift_order=0, excluded_files=excluded,
        )


def test_run_applies_manual_occurrence_exclusion(tmp_path):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0,
        manual_occurrence_exclusions={"NIST610 - 2.csv": {"Al27"}},
    )

    standard_result = results["SAMPLE"].standard_results["NIST610"]
    assert standard_result.manually_excluded_occurrences.get("Al27") == [2]
    assert "Al27" not in standard_result.excluded_outliers


def test_run_applies_manual_row_exclusion_without_error(tmp_path):
    """Smoke test: manual_row_exclusions threads through both background
    passes and assemble_occurrences without raising -- detailed behavior
    (row actually dropped from statistics) is covered at the
    background.py/standards.py unit level."""
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0,
        manual_row_exclusions={"NIST610 - 1.csv": {"Al27": {2}}},
    )
    assert not results["SAMPLE"].calibrated_ppm.empty


def test_run_with_detrend_option_produces_calibrated_ppm(tmp_path):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0, detrend=True,
    )
    result = results["SAMPLE"]
    assert not result.calibrated_ppm.empty
    assert result.provenance["detrend"] is True


def test_run_with_despike_noise_option_produces_calibrated_ppm(tmp_path):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0, despike_noise=True,
    )
    result = results["SAMPLE"]
    assert not result.calibrated_ppm.empty
    assert result.provenance["despike_noise"] is True


def test_run_despike_noise_applied_before_windowing(tmp_path, monkeypatch):
    """Verifies despike_noise=True actually runs noise_despike over every
    analyte of every parsed file, before background/ablation windowing --
    the filter's own correctness (spike removal, edge handling, etc.) is
    covered at the despike.py unit level; the pipeline's automatic
    row-level outlier screens are robust enough on their own that an
    injected ablation spike doesn't reliably survive to calibrated_ppm
    either way, so end-to-end numeric comparison isn't a reliable signal
    of whether despiking actually ran -- call-count is."""
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    calls = []
    import src.calibration.pipeline as pipeline_module
    original = pipeline_module.noise_despike

    def _spy(values):
        calls.append(values)
        return original(values)

    monkeypatch.setattr(pipeline_module, "noise_despike", _spy)

    run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0, despike_noise=False,
    )
    assert len(calls) == 0

    run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0, despike_noise=True,
    )
    # 4 files (2 standard + 2 sample occurrences) x 2 analytes (Al27, Ca43)
    assert len(calls) == 8


def test_run_raises_when_multiple_standards_and_no_primary_chosen(tmp_path):
    sample_dir = tmp_path / "multi_std"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1)
    _write_raw_file(sample_dir, "NIST612", 1, base + timedelta(minutes=5), seed=2)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=10), seed=3)

    library = _reference_library()
    library["NIST612"] = parse_reference_material({
        "standard": "NIST612",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 40.0, "uncertainty": 1.0, "uncertainty_type": "1SD"}},
    })

    with pytest.raises(PipelineError):
        run(sample_dir, standard_names={"NIST610", "NIST612"}, reference_library=library, drift_order=0, background_drift_order=0)

    # Explicit primary_standards resolves the ambiguity.
    results = run(
        sample_dir, standard_names={"NIST610", "NIST612"}, reference_library=library,
        drift_order=0, background_drift_order=0, primary_standards=["NIST610"],
    )
    assert results["SAMPLE"].provenance["primary_standards"] == ["NIST610"]


def test_run_with_two_primary_standards_produces_multi_point_calibration(tmp_path):
    sample_dir = tmp_path / "multi_std"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1)
    _write_raw_file(sample_dir, "NIST612", 1, base + timedelta(minutes=5), seed=2)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=10), seed=3)

    library = _reference_library()
    library["NIST612"] = parse_reference_material({
        "standard": "NIST612",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 40.0, "uncertainty": 1.0, "uncertainty_type": "1SD"}},
    })

    results = run(
        sample_dir, standard_names={"NIST610", "NIST612"}, reference_library=library,
        drift_order=0, background_drift_order=0, primary_standards=["NIST610", "NIST612"],
    )
    result = results["SAMPLE"]
    assert result.provenance["primary_standards"] == ["NIST610", "NIST612"]
    assert result.multi_standard_calibration is not None
    assert "Al27" in result.multi_standard_calibration.curves
    curve = result.multi_standard_calibration.curves["Al27"]
    assert curve.method == "multi_point_linear"
    assert curve.n_points == 2
    assert "Al27" in result.qc_report["calibration_curves"]
    assert not result.calibrated_ppm.empty
    # Both standards are still independently calibrated for their own QC,
    # regardless of which are chosen as primary.
    assert set(result.standard_results) == {"NIST610", "NIST612"}


def test_run_with_force_zero_intercept_uses_forced_origin_calibration_curve(tmp_path):
    sample_dir = tmp_path / "multi_std"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1)
    _write_raw_file(sample_dir, "NIST612", 1, base + timedelta(minutes=5), seed=2)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=10), seed=3)

    library = _reference_library()
    library["NIST612"] = parse_reference_material({
        "standard": "NIST612",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 40.0, "uncertainty": 1.0, "uncertainty_type": "1SD"}},
    })

    results = run(
        sample_dir, standard_names={"NIST610", "NIST612"}, reference_library=library,
        drift_order=0, background_drift_order=0, primary_standards=["NIST610", "NIST612"],
        force_zero_intercept=True,
    )
    result = results["SAMPLE"]
    assert result.provenance["force_zero_intercept"] is True
    curve = result.multi_standard_calibration.curves["Al27"]
    assert curve.method == "multi_point_zero_intercept"
    assert curve.intercept == 0.0
    assert not result.calibrated_ppm.empty


def test_run_single_primary_standards_list_matches_legacy_single_standard_output(tmp_path):
    """Equivalence lock: passing primary_standards=["NIST610"] (a 1-element
    list) must produce byte-identical calibrated_ppm to today's implicit
    single-standard auto-inference path."""
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    auto_results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0,
    )
    explicit_results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0, primary_standards=["NIST610"],
    )

    assert explicit_results["SAMPLE"].multi_standard_calibration is None
    pd.testing.assert_frame_equal(
        auto_results["SAMPLE"].calibrated_ppm, explicit_results["SAMPLE"].calibrated_ppm,
    )


def test_run_raises_when_no_reference_available_for_any_standard(tmp_path):
    sample_dir = tmp_path / "no_ref"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    _write_raw_file(sample_dir, "UNKNOWNSTD", 1, base, seed=1)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=5), seed=2)

    with pytest.raises(PipelineError):
        run(sample_dir, standard_names={"UNKNOWNSTD"}, reference_library=_reference_library(), drift_order=0, background_drift_order=0)


def test_run_with_global_background_override_applies_to_every_file(tmp_path):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    override = BackgroundWindowOverride(start_offset_s=0.0, end_offset_s=2.0)
    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0, background_override=override,
    )
    result = results["SAMPLE"]
    assert all(b.window.method == "manual_override" for b in result.backgrounds)
    assert result.provenance["background_override"] == {
        "start_offset_s": 0.0, "end_offset_s": 2.0, "edge_trim_lead_s": 0.0, "edge_trim_trail_s": 0.0,
    }


def test_run_with_per_file_override_takes_precedence_over_global(tmp_path):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    global_override = BackgroundWindowOverride(start_offset_s=0.0, end_offset_s=2.0)
    per_file_override = BackgroundWindowOverride(start_offset_s=0.0, end_offset_s=1.0)
    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0, background_override=global_override,
        per_file_overrides={"SAMPLE - 1.csv": per_file_override},
    )
    result = results["SAMPLE"]
    by_index = {b.file_meta.index: b for b in result.backgrounds}
    # The per-file override (end_offset_s=1.0) should give a narrower window
    # than the global override (end_offset_s=2.0) applied to the other file.
    assert by_index[1].window.end_time < by_index[2].window.end_time


def test_run_with_auto_aic_drift_method_produces_calibrated_ppm(tmp_path):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_method="auto_aic", background_drift_method="auto_aic", max_order=2,
    )
    result = results["SAMPLE"]
    assert not result.calibrated_ppm.empty
    assert result.provenance["drift_method"] == "auto_aic"
    assert result.provenance["background_drift_method"] == "auto_aic"
    assert result.provenance["max_order"] == 2


def test_discover_sample_directories_and_run_batch(tmp_path):
    parent = tmp_path / "raw data"
    parent.mkdir()
    for name in ["25B-1", "25B-2"]:
        d = parent / name
        d.mkdir()
        _make_sample_dir(d)
    (parent / "not_a_sample_folder").mkdir()   # no matching csv files -- must be excluded
    (parent / "some_file.txt").write_text("x")  # not a directory

    dirs = discover_sample_directories(parent)
    assert [d.name for d in dirs] == ["25B-1", "25B-2"]

    batch_results = run_batch(
        parent, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0,
    )
    assert set(batch_results.keys()) == {"25B-1", "25B-2"}
    for folder_results in batch_results.values():
        assert set(folder_results.keys()) == {"SAMPLE"}
        result = folder_results["SAMPLE"]
        assert result.provenance["standards_shared_across_folders"] is False
        assert not result.calibrated_ppm.empty
