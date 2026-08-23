"""Diagnostic figure/table smoke tests -- exercised against synthetic pipeline
output. Not strict pixel/value assertions (see build-plan phasing notes):
mainly "doesn't raise" plus a few structural checks on the tables.

Pure Python -- no PyQt/QApplication needed (matplotlib uses the Agg backend).
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.collections as mcollections
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.calibration.diagnostics import (
    build_accuracy_table_df,
    build_timing_report_df,
    cbar_label_for_stage,
    plot_all_stage_maps,
    plot_background_drift,
    plot_bias_fit,
    plot_categorical_map,
    plot_dating_ratio_fit,
    plot_index_map,
    plot_multi_point_calibration,
    plot_standard_qc_series,
    plot_standard_vs_reference,
    plot_time_series,
)
from src.calibration.massbias import BiasSpec
from src.calibration.pipeline import run
from src.calibration.reflib import parse_reference_material
from tests.test_calibration_pipeline import _make_sample_dir, _reference_library, _write_raw_file


@pytest.fixture
def sample_result(tmp_path):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)
    results = run(
        sample_dir, standard_names={"NIST610"}, reference_library=_reference_library(),
        drift_order=0, background_drift_order=0,
    )
    return results["SAMPLE"]


def test_plot_background_drift_draws_without_error(sample_result):
    fig, ax = plt.subplots()
    drift_fit = sample_result.session_background_drift.get("Al27")
    groups = {sample_result.sample_label: sample_result.backgrounds}
    groups.update({
        label: [occ.background for occ in sr.occurrences] for label, sr in sample_result.standard_results.items()
    })
    plot_background_drift(ax, groups, drift_fit, "Al27", reference_labels=set(sample_result.standard_results))
    assert ax.get_title() != ""
    plt.close(fig)


def test_plot_background_drift_uses_circles_for_reference_squares_for_sample(sample_result):
    """Regression test: sample and reference-standard background points
    are combined into one plot, distinguished by marker shape (circle for
    reference, square for sample) and a legend entry per label."""
    groups = {
        sample_result.sample_label: sample_result.backgrounds,
        "NIST610": [occ.background for occ in sample_result.standard_results["NIST610"].occurrences],
    }
    fig, ax = plt.subplots()
    plot_background_drift(ax, groups, None, "Al27", reference_labels={"NIST610"})

    legend_labels = {t.get_text() for t in ax.get_legend().get_texts()}
    assert f"{sample_result.sample_label} (sample)" in legend_labels
    assert "NIST610 (reference)" in legend_labels

    markers_by_label = {c.get_label(): c.lines[0].get_marker() for c in ax.containers}
    assert markers_by_label[f"{sample_result.sample_label} (sample)"] == "s"
    assert markers_by_label["NIST610 (reference)"] == "o"
    plt.close(fig)


def test_plot_standard_vs_reference_draws_without_error(sample_result):
    standard_result = sample_result.standard_results["NIST610"]
    fig, ax = plt.subplots()
    plot_standard_vs_reference(ax, standard_result, "Al27")
    assert ax.get_title() != ""
    plt.close(fig)


def test_plot_standard_vs_reference_returns_point_index_with_cps_and_ppm_series(sample_result):
    standard_result = sample_result.standard_results["NIST610"]
    fig, ax = plt.subplots()
    point_index = plot_standard_vs_reference(ax, standard_result, "Al27")
    assert set(point_index["series"]) == {"ppm", "cps"}
    assert len(point_index) > 0
    plt.close(fig)


def test_plot_standard_vs_reference_shows_cps_as_open_circles_on_second_axis(sample_result):
    standard_result = sample_result.standard_results["NIST610"]
    fig, ax = plt.subplots()
    plot_standard_vs_reference(ax, standard_result, "Al27")

    # A second (twinx) axes was created for the CPS overlay.
    assert len(fig.axes) == 2
    ax_cps = [a for a in fig.axes if a is not ax][0]
    assert ax_cps.collections  # the open-circle CPS scatter was drawn there
    for coll in ax_cps.collections:
        # Open markers: no fill color (facecolor alpha == 0, or explicitly "none").
        facecolors = coll.get_facecolors()
        assert len(facecolors) == 0 or all(rgba[3] == 0 for rgba in facecolors)
    plt.close(fig)


def test_plot_standard_vs_reference_flagged_point_colored_red_not_asterisk(sample_result):
    """Regression test: a flagged accuracy row must be recolored red on
    the point itself, not marked with a separate '*' text annotation."""
    standard_result = sample_result.standard_results["NIST610"]
    rows = [r for r in standard_result.accuracy_table if r.analyte == "Al27"]
    assert rows
    rows[0].flagged = True

    fig, ax = plt.subplots()
    point_index = plot_standard_vs_reference(ax, standard_result, "Al27")

    assert not any(t.get_text() == "*" for t in ax.texts)

    flagged_row = point_index[
        (point_index["occurrence_order"] == rows[0].occurrence_order) & (point_index["series"] == "ppm")
    ]
    assert not flagged_row.empty
    assert bool(flagged_row.iloc[0]["flagged"]) is True
    assert bool(flagged_row.iloc[0]["manually_excluded"]) is False
    plt.close(fig)


def test_plot_standard_vs_reference_manually_excluded_point_default_display_is_light_gray(sample_result):
    standard_result = sample_result.standard_results["NIST610"]
    rows = [r for r in standard_result.accuracy_table if r.analyte == "Al27"]
    assert rows
    rows[0].manually_excluded = True

    fig, ax = plt.subplots()
    point_index = plot_standard_vs_reference(ax, standard_result, "Al27")

    manual_row = point_index[
        (point_index["occurrence_order"] == rows[0].occurrence_order) & (point_index["series"] == "ppm")
    ]
    assert not manual_row.empty
    assert bool(manual_row.iloc[0]["manually_excluded"]) is True

    light_gray = mcolors.to_rgba("lightgray")
    facecolors = np.concatenate([
        coll.get_facecolors() for coll in ax.collections
        if isinstance(coll, mcollections.PathCollection) and len(coll.get_facecolors())
    ])
    assert any(np.allclose(fc, light_gray) for fc in facecolors)
    plt.close(fig)


def test_plot_standard_vs_reference_hidden_mask_display_omits_masked_point(sample_result):
    """A masked point stays in the returned point-index (for hit-testing/
    un-masking) even when mask_display="hidden" drops it from the plot."""
    standard_result = sample_result.standard_results["NIST610"]
    rows = [r for r in standard_result.accuracy_table if r.analyte == "Al27"]
    assert len(rows) >= 2
    rows[0].manually_excluded = True

    def _n_scatter_points(ax) -> int:
        return sum(
            len(coll.get_offsets()) for coll in ax.collections
            if isinstance(coll, mcollections.PathCollection)
        )

    fig1, ax1 = plt.subplots()
    plot_standard_vs_reference(ax1, standard_result, "Al27", mask_display="light_gray")
    n_shown = _n_scatter_points(ax1)
    plt.close(fig1)

    fig2, ax2 = plt.subplots()
    point_index = plot_standard_vs_reference(ax2, standard_result, "Al27", mask_display="hidden")
    n_hidden = _n_scatter_points(ax2)
    plt.close(fig2)

    assert n_hidden < n_shown

    manual_row = point_index[
        (point_index["occurrence_order"] == rows[0].occurrence_order) & (point_index["series"] == "ppm")
    ]
    assert not manual_row.empty
    assert bool(manual_row.iloc[0]["manually_excluded"]) is True


def test_plot_standard_qc_series_draws_without_error(sample_result):
    standard_result = sample_result.standard_results["NIST610"]
    fig, (ax1, ax2) = plt.subplots(1, 2)
    plot_standard_qc_series(ax1, ax2, standard_result, "Al27")
    assert ax1.get_title() != ""
    assert ax2.get_ylabel() != ""
    plt.close(fig)


def test_plot_multi_point_calibration_draws_without_error(tmp_path):
    from datetime import datetime, timedelta

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
    curve = results["SAMPLE"].multi_standard_calibration.curves["Al27"]

    fig, ax = plt.subplots()
    plot_multi_point_calibration(ax, curve, "Al27")
    assert ax.get_title() != ""
    assert len(ax.collections) > 0
    assert len(ax.lines) > 0
    plt.close(fig)


def test_plot_multi_point_calibration_no_points_sets_title():
    from src.calibration.standards import CalibrationCurve
    curve = CalibrationCurve(analyte="Al27", slope=0.0, intercept=0.0, r_squared=None, n_points=0, method="multi_point_linear", points=[])
    fig, ax = plt.subplots()
    plot_multi_point_calibration(ax, curve, "Al27")
    assert "no calibration points" in ax.get_title()
    plt.close(fig)


@pytest.fixture
def pb_bias_result(tmp_path):
    from datetime import datetime, timedelta

    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    pb_analytes = ["Pb204", "Pb206"]
    std_bg, std_abl = (500.0, 8500.0), (100000.0, 1700000.0)   # ratio 17.0, matches certified truth
    sample_bg, sample_abl = (500.0, 7500.0), (100000.0, 1500000.0)
    _write_raw_file(tmp_path / "25B-1", "NIST610", 1, base, seed=1, analytes=pb_analytes, bg_level=std_bg, ablation_level=std_abl)
    _write_raw_file(tmp_path / "25B-1", "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=pb_analytes, bg_level=sample_bg, ablation_level=sample_abl)
    _write_raw_file(tmp_path / "25B-1", "NIST610", 2, base + timedelta(minutes=45), seed=4, analytes=pb_analytes, bg_level=std_bg, ablation_level=std_abl)

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
    return results["SAMPLE"]


def test_plot_bias_fit_draws_without_error(pb_bias_result):
    bias_fit = pb_bias_result.bias_fits["Pb206/Pb204"]
    fig, ax = plt.subplots()
    plot_bias_fit(ax, bias_fit, pb_bias_result.standard_results)
    assert "Pb206/Pb204" in ax.get_title()
    assert len(ax.collections) > 0  # per-label scatter points
    assert len(ax.lines) > 0  # fitted bias curve
    plt.close(fig)


def test_plot_bias_fit_no_data_sets_title():
    from src.calibration.massbias import BiasFit, BiasTruth

    truth = BiasTruth(value=17.0, uncertainty_1sd=0.01, source="certified_reference_ratio")
    bias_fit = BiasFit(
        element="Pb", numerator_mass=206, denominator_mass=204, truth=truth,
        log_bias_fit=None, standard_labels=["MISSING_LABEL"], n_points=0,
    )
    fig, ax = plt.subplots()
    plot_bias_fit(ax, bias_fit, {})  # empty standard_results -> no resolvable data
    assert "no bias-fit data" in ax.get_title()
    plt.close(fig)


@pytest.fixture
def zircon_dating_result(tmp_path):
    from datetime import datetime, timedelta

    from src.calibration.dating_ratios import DatingRatioSpec

    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    analytes = ["U238", "Pb206"]
    std_bg, std_abl = (500.0, 500.0), (900000.0, 90000.0)  # Pb206/U238 = 0.1, matches certified truth
    sample_bg, sample_abl = (500.0, 500.0), (900000.0, 126000.0)
    _write_raw_file(sample_dir, "ZRNSTD", 1, base, seed=1, analytes=analytes, bg_level=std_bg, ablation_level=std_abl, bg_n=15, ablation_n=30)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=analytes, bg_level=sample_bg, ablation_level=sample_abl, bg_n=15, ablation_n=30)
    _write_raw_file(sample_dir, "ZRNSTD", 2, base + timedelta(minutes=45), seed=4, analytes=analytes, bg_level=std_bg, ablation_level=std_abl, bg_n=15, ablation_n=30)

    library = {"ZRNSTD": parse_reference_material({
        "standard": "ZRNSTD",
        "analytes": {"Pb206": {"element": "Pb", "mass": 206, "value": 0.05, "uncertainty": 0.0005, "uncertainty_type": "1SD"}},
        "isotope_ratios": {
            "Pb206/U238": {
                "numerator_element": "Pb", "numerator_mass": 206, "denominator_element": "U", "denominator_mass": 238,
                "value": 0.1, "uncertainty": 0.001, "uncertainty_type": "1SD", "source": "test",
            },
        },
    })}
    results = run(
        sample_dir, standard_names={"ZRNSTD"}, reference_library=library,
        drift_order=0, background_drift_order=0,
        dating_ratio_specs=[DatingRatioSpec(numerator_element="Pb", numerator_mass=206, denominator_element="U", denominator_mass=238)],
        dating_ratio_drift_order=0,
    )
    return results["SAMPLE"]


def test_plot_dating_ratio_fit_draws_without_error(zircon_dating_result):
    fit = zircon_dating_result.dating_ratio_fits["Pb206/U238"]
    fig, ax = plt.subplots()
    plot_dating_ratio_fit(ax, fit, zircon_dating_result.standard_results)
    assert "Pb206/U238" in ax.get_title()
    assert len(ax.collections) > 0  # per-label scatter points
    assert len(ax.lines) > 0  # fitted correction curve
    plt.close(fig)


def test_plot_dating_ratio_fit_no_data_sets_title():
    from src.calibration.dating_ratios import DatingRatioFit, DatingRatioTruth

    truth = DatingRatioTruth(value=0.1, uncertainty_1sd=0.001)
    fit = DatingRatioFit(
        numerator_element="Pb", numerator_mass=206, denominator_element="U", denominator_mass=238,
        numerator_scale_factor=1.0, truth=truth, log_ratio_fit=None, standard_labels=["MISSING_LABEL"], n_points=0,
    )
    fig, ax = plt.subplots()
    plot_dating_ratio_fit(ax, fit, {})  # empty standard_results -> no resolvable data
    assert "no dating-ratio-fit data" in ax.get_title()
    plt.close(fig)


def test_plot_index_map_draws_without_error(sample_result):
    fig, ax = plt.subplots()
    plot_index_map(ax, sample_result.calibrated_ppm["Al27"], sample_result.grid_index, title="Al27 test map", cbar_label="ppm")
    assert ax.get_title() == "Al27 test map"
    # A colorbar is added as its own Axes alongside the map's Axes.
    assert len(fig.axes) == 2
    assert fig.axes[1].get_ylabel() == "ppm"
    plt.close(fig)


def test_plot_index_map_log_scale_uses_lognorm(sample_result):
    import matplotlib.colors as mcolors
    fig, ax = plt.subplots()
    im = plot_index_map(
        ax, sample_result.calibrated_ppm["Al27"], sample_result.grid_index,
        title="Al27 log test", cbar_label="ppm", log_scale=True,
    )
    assert isinstance(im.norm, mcolors.LogNorm)
    plt.close(fig)


def test_plot_index_map_log_scale_masks_nonpositive_without_error():
    import pandas as pd
    fig, ax = plt.subplots()
    values = pd.Series([-1.0, 0.0, 2.0, 5.0])
    grid_index = pd.DataFrame({"line_number": [0, 0, 1, 1], "sweep_index": [0, 1, 0, 1]})
    plot_index_map(ax, values, grid_index, title="mixed sign", log_scale=True)
    plt.close(fig)


def test_cbar_label_for_stage():
    assert cbar_label_for_stage("calibrated") == "ppm"
    assert cbar_label_for_stage("raw") == "CPS"
    assert cbar_label_for_stage("background+drift correction") == "CPS"


def test_plot_index_map_handles_empty_data():
    import pandas as pd
    fig, ax = plt.subplots()
    plot_index_map(ax, pd.Series(dtype=float), pd.DataFrame(), title="empty")
    assert "no data" in ax.get_title()
    plt.close(fig)


def test_plot_categorical_map_handles_empty_data():
    import pandas as pd
    fig, ax = plt.subplots()
    plot_categorical_map(ax, pd.Series(dtype=object), pd.DataFrame(), [], title="empty")
    assert "no data" in ax.get_title()
    plt.close(fig)


def test_plot_categorical_map_draws_swatch_legend_for_real_labels(sample_result):
    import numpy as np
    import pandas as pd

    n = len(sample_result.grid_index)
    rng = np.random.default_rng(0)
    categories = ["Anorthite", "Albite", "Quartz"]
    labels = pd.Series(rng.choice(categories + [None], size=n), index=sample_result.grid_index.index)

    fig, ax = plt.subplots()
    plot_categorical_map(ax, labels, sample_result.grid_index, categories, title="mineral map")
    assert ax.get_title() == "mineral map"
    legend = ax.get_legend()
    assert legend is not None
    assert {t.get_text() for t in legend.get_texts()} == set(categories)
    plt.close(fig)


def test_plot_all_stage_maps_draws_1x3_row(sample_result):
    fig = plt.figure()
    s = sample_result.calibrated_ppm["Al27"]
    plot_all_stage_maps(fig, s, s, s, sample_result.grid_index, "Al27")
    # 3 map Axes + 3 colorbar Axes.
    assert len(fig.axes) == 6
    plt.close(fig)


def test_build_accuracy_table_df_has_flag_column(sample_result):
    standard_result = sample_result.standard_results["NIST610"]
    df = build_accuracy_table_df(standard_result.accuracy_table)
    assert "flag" in df.columns
    assert set(df["analyte"]) <= {"Al27", "Ca43"}
    assert set(df["flag"]) <= {True, False}


def test_build_timing_report_df_has_one_row_per_file(sample_result):
    df = build_timing_report_df(sample_result.files, sample_result.backgrounds)
    assert len(df) == len(sample_result.files)
    assert {"file", "bg_start_time", "bg_end_time", "ablation_start_time", "ablation_end_time"} <= set(df.columns)


def test_plot_time_series_draws_discrete_points_with_role_colors(sample_result):
    lines = list(zip(sample_result.files, sample_result.backgrounds))
    fig, ax = plt.subplots()
    plot_time_series(ax, lines, "Al27", offset=False)
    # scatter() creates PathCollections, not Line2D -- confirms discrete
    # points, not connected lines.
    assert len(ax.collections) > 0
    assert len(ax.lines) == 0
    plt.close(fig)


def test_plot_time_series_labels_lines_only_when_offset_enabled(sample_result):
    lines = list(zip(sample_result.files, sample_result.backgrounds))

    fig, ax = plt.subplots()
    plot_time_series(ax, lines, "Al27", offset=False)
    assert len(ax.texts) == 0
    plt.close(fig)

    fig, ax = plt.subplots()
    plot_time_series(ax, lines, "Al27", offset=True)
    assert len(ax.texts) == len(lines)
    plt.close(fig)


def test_plot_time_series_outlier_names_colors_included_region_as_outlier(sample_result):
    lines = list(zip(sample_result.files, sample_result.backgrounds))
    outlier_file = lines[0][0].meta.path.name

    fig, ax = plt.subplots()
    plot_time_series(ax, lines, "Al27", outlier_names={outlier_file})
    legend_labels = {t.get_text() for t in ax.get_legend().get_texts()}
    assert "outlier" in legend_labels
    plt.close(fig)

    fig, ax = plt.subplots()
    plot_time_series(ax, lines, "Al27", outlier_names=None)
    legend_labels = {t.get_text() for t in ax.get_legend().get_texts()}
    assert "outlier" not in legend_labels
    plt.close(fig)


def test_plot_time_series_unclassified_when_no_background():
    import numpy as np
    from datetime import datetime
    from pathlib import Path
    import pandas as pd
    from src.calibration.rawfile import LineFileData, LineFileMeta

    acquired_at = datetime(2026, 3, 1, 10, 0, 0)
    time_s = np.arange(1, 11) * 0.28
    absolute_time = np.array([np.datetime64(acquired_at) + np.timedelta64(int(t * 1e6), "us") for t in time_s])
    signal = pd.DataFrame({"Al27": np.linspace(500, 900000, 10)})
    meta = LineFileMeta(path=Path("RAW - 1.csv"), label="RAW", index=1, is_standard=False, acquired_at=acquired_at, batch="Test.b")
    line_data = LineFileData(meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=["Al27"], signal=signal, dt_s=0.28, n_rows=10)

    fig, ax = plt.subplots()
    plot_time_series(ax, [(line_data, None)], "Al27", offset=False)
    legend = ax.get_legend()
    assert legend is not None
    assert [t.get_text() for t in legend.get_texts()] == ["unclassified"]
    plt.close(fig)


def test_plot_time_series_no_data_sets_title():
    fig, ax = plt.subplots()
    plot_time_series(ax, [], "Al27")
    assert "no data" in ax.get_title()
    plt.close(fig)


def test_plot_time_series_returns_point_index_covering_every_row(sample_result):
    lines = list(zip(sample_result.files, sample_result.backgrounds))
    fig, ax = plt.subplots()
    point_index = plot_time_series(ax, lines, "Al27")
    total_rows = sum(ld.n_rows for ld, _ in lines)
    assert len(point_index) == total_rows
    assert set(point_index.columns) == {"filename", "row_index", "analyte", "x", "y", "role"}
    plt.close(fig)


def test_plot_time_series_manual_row_mask_overrides_role():
    import numpy as np
    from datetime import datetime
    from pathlib import Path
    import pandas as pd
    from src.calibration.rawfile import LineFileData, LineFileMeta

    acquired_at = datetime(2026, 3, 1, 10, 0, 0)
    time_s = np.arange(1, 11) * 0.28
    absolute_time = np.array([np.datetime64(acquired_at) + np.timedelta64(int(t * 1e6), "us") for t in time_s])
    signal = pd.DataFrame({"Al27": np.linspace(500, 900000, 10)})
    meta = LineFileMeta(path=Path("RAW - 1.csv"), label="RAW", index=1, is_standard=False, acquired_at=acquired_at, batch="Test.b")
    line_data = LineFileData(meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=["Al27"], signal=signal, dt_s=0.28, n_rows=10)

    manual_mask = np.zeros(10, dtype=bool)
    manual_mask[3] = True
    fig, ax = plt.subplots()
    point_index = plot_time_series(ax, [(line_data, None)], "Al27", manual_row_masks={"RAW - 1.csv": manual_mask})
    plt.close(fig)

    row = point_index[point_index["row_index"] == 3].iloc[0]
    assert row["role"] == "manual"
    other = point_index[point_index["row_index"] == 0].iloc[0]
    assert other["role"] == "unclassified"


def _single_line_with_manual_mask(masked_row_index=3, n_rows=10):
    from datetime import datetime
    from pathlib import Path
    import pandas as pd
    from src.calibration.rawfile import LineFileData, LineFileMeta

    acquired_at = datetime(2026, 3, 1, 10, 0, 0)
    time_s = np.arange(1, n_rows + 1) * 0.28
    absolute_time = np.array([np.datetime64(acquired_at) + np.timedelta64(int(t * 1e6), "us") for t in time_s])
    signal = pd.DataFrame({"Al27": np.linspace(500, 900000, n_rows)})
    meta = LineFileMeta(path=Path("RAW - 1.csv"), label="RAW", index=1, is_standard=False, acquired_at=acquired_at, batch="Test.b")
    line_data = LineFileData(meta=meta, time_s=time_s, absolute_time=absolute_time, analytes=["Al27"], signal=signal, dt_s=0.28, n_rows=n_rows)
    manual_mask = np.zeros(n_rows, dtype=bool)
    manual_mask[masked_row_index] = True
    return line_data, manual_mask


def test_plot_time_series_manual_row_default_display_is_light_gray():
    line_data, manual_mask = _single_line_with_manual_mask()
    fig, ax = plt.subplots()
    plot_time_series(ax, [(line_data, None)], "Al27", manual_row_masks={"RAW - 1.csv": manual_mask})

    light_gray = mcolors.to_rgba("lightgray")
    manual_colls = [coll for coll in ax.collections if coll.get_label() == "manual"]
    assert manual_colls
    facecolors = manual_colls[0].get_facecolors()
    assert len(facecolors) == 1
    assert np.allclose(facecolors[0], light_gray)
    plt.close(fig)


def test_plot_time_series_hidden_mask_display_omits_masked_point():
    line_data, manual_mask = _single_line_with_manual_mask()

    fig1, ax1 = plt.subplots()
    plot_time_series(ax1, [(line_data, None)], "Al27", manual_row_masks={"RAW - 1.csv": manual_mask}, mask_display="light_gray")
    assert any(coll.get_label() == "manual" for coll in ax1.collections)
    plt.close(fig1)

    fig2, ax2 = plt.subplots()
    point_index = plot_time_series(
        ax2, [(line_data, None)], "Al27", manual_row_masks={"RAW - 1.csv": manual_mask}, mask_display="hidden",
    )
    assert not any(coll.get_label() == "manual" for coll in ax2.collections)
    plt.close(fig2)

    # Still reported in the point index (for hit-testing/un-masking).
    row = point_index[point_index["row_index"] == 3].iloc[0]
    assert row["role"] == "manual"


def test_plot_time_series_log_scale_sets_yscale(sample_result):
    lines = list(zip(sample_result.files, sample_result.backgrounds))
    fig, ax = plt.subplots()
    plot_time_series(ax, lines, "Al27", log_scale=True)
    assert ax.get_yscale() == "log"
    plt.close(fig)

    fig, ax = plt.subplots()
    plot_time_series(ax, lines, "Al27", log_scale=False)
    assert ax.get_yscale() == "linear"
    plt.close(fig)
