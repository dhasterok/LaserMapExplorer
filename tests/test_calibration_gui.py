"""Headless GUI smoke tests for the standalone calibration window.

Uses pytest-qt (qtbot) and QT_QPA_PLATFORM=offscreen, following the same
headless convention as tests/test_calibration_wiring.py. Lower priority than
the backend tests -- mainly "constructs and wires up without error" plus a
couple of light interaction checks, since the module is deliberately thin on
the GUI side.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import src.calibration.dock_widgets as dw
from src.calibration.app import create_app
from src.calibration.dock_widgets import CalibrationMainWindow
from src.calibration import reflib
from src.calibration.reflib import parse_reference_material
from tests.test_calibration_pipeline import _make_sample_dir, _write_raw_file


@pytest.fixture(scope="module")
def app():
    return create_app()


@pytest.fixture
def main_window(qtbot, app):
    window = CalibrationMainWindow()
    qtbot.addWidget(window)
    window.show()
    return window


def test_main_window_constructs_without_error(main_window):
    assert main_window.windowTitle() == "LA-ICP-MS Calibration"
    assert main_window.tableStandardLabels.columnCount() == 5
    assert main_window.tableStandardLabels.rowCount() == 0


def test_drift_order_spinbox_default_and_editable(main_window):
    assert main_window.spinDriftOrder.value() == 3
    main_window.spinDriftOrder.setValue(2)
    assert main_window.spinDriftOrder.value() == 2


def test_batch_mode_toggle_shows_folder_list(main_window):
    assert main_window.listWidgetSampleFolders.isVisible() is False
    main_window.checkBoxBatchMode.setChecked(True)
    assert main_window.listWidgetSampleFolders.isVisible() is True


def test_scan_populates_standard_label_table(tmp_path, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    assert main_window.tableStandardLabels.rowCount() == 2
    labels = {
        main_window.tableStandardLabels.item(i, 3).text()
        for i in range(main_window.tableStandardLabels.rowCount())
    }
    assert labels == {"NIST610", "SAMPLE"}
    # NIST610 is already a key in the seeded reference library (placeholder
    # values), so its Primary checkbox should default to checked (auto-
    # guessed Reference combo match); SAMPLE should not be checked at all.
    assert main_window._primary_checkboxes["NIST610"].isChecked() is True
    assert main_window._secondary_checkboxes["NIST610"].isChecked() is False
    assert main_window._bias_checkboxes["NIST610"].isChecked() is False
    assert main_window._primary_checkboxes["SAMPLE"].isChecked() is False
    assert main_window._secondary_checkboxes["SAMPLE"].isChecked() is False
    assert main_window._bias_checkboxes["SAMPLE"].isChecked() is False
    assert main_window._reference_combos["NIST610"].currentText() == "NIST610"
    assert main_window._reference_combos["SAMPLE"].currentText() == "—"


def test_run_pipeline_end_to_end_via_gui(tmp_path, qtbot, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {
            "Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"},
            "Ca43": {"element": "Ca", "mass": 43, "value": 300.0, "uncertainty": 3.0, "uncertainty_type": "1SD"},
        },
    })
    main_window.reference_library["NIST610"] = material
    main_window.spinDriftOrder.setValue(0)

    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    # "(all)" + every standard/sample label used across results.
    assert main_window.comboBoxSampleResult.count() == 3
    assert main_window.comboBoxSampleResult.currentText() == "SAMPLE"
    result = main_window._current_result()
    assert result is not None
    assert not result.calibrated_ppm.empty
    assert main_window.tableTiming.rowCount() == len(result.files)
    assert main_window.tableAccuracyFit.rowCount() > 0


def test_scan_populates_time_series_lines_and_override_table(tmp_path, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    assert main_window.tableTimeSeriesFiles.rowCount() == 4  # 2 NIST610 + 2 SAMPLE files, "(all)" focus by default
    assert main_window.tablePerLineOverrides.rowCount() == 4
    assert main_window.analyte_list.combo_box.count() == 2  # Al27, Ca43
    assert len(main_window._scanned_files) == 4
    # Every scanned file gets default View=False, Use=True state.
    assert all(main_window._file_view_state[n] is False for n in main_window._scanned_files)
    assert all(main_window._file_use_state[n] is True for n in main_window._scanned_files)


def test_drift_method_combo_defaults_to_auto_poisson(main_window):
    assert main_window.comboDriftMethod.currentText() == "Auto (Poisson GLM+LRT)"
    assert main_window.comboBackgroundDriftMethod.currentText() == "Auto (Poisson GLM+LRT)"
    assert dw.DRIFT_METHOD_LABELS[main_window.comboDriftMethod.currentText()] == "auto_poisson_lrt"


def test_background_override_group_disabled_by_default(main_window):
    assert main_window.checkBackgroundOverride.isChecked() is False
    assert main_window._current_background_override() is None
    main_window.checkBackgroundOverride.setChecked(True)
    main_window.spinOverrideStart.setValue(0.0)
    main_window.spinOverrideEnd.setValue(5.0)
    override = main_window._current_background_override()
    assert override is not None
    assert override.start_offset_s == 0.0
    assert override.end_offset_s == 5.0


def test_detrend_checkbox_default_unchecked_and_reaches_run(tmp_path, qtbot, main_window):
    assert main_window.checkDetrend.isChecked() is False

    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)
    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    })
    main_window.reference_library["NIST610"] = material
    main_window._reference_combos["NIST610"].addItem("NIST610")
    main_window._reference_combos["NIST610"].setCurrentText("NIST610")
    main_window._primary_checkboxes["NIST610"].setChecked(True)
    main_window.spinDriftOrder.setValue(0)
    main_window.checkDetrend.setChecked(True)

    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    result = main_window._current_result()
    assert result is not None
    assert result.provenance["detrend"] is True


def test_despike_noise_checkbox_default_unchecked_and_reaches_run(tmp_path, qtbot, main_window):
    assert main_window.checkDespikeNoise.isChecked() is False

    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)
    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    })
    main_window.reference_library["NIST610"] = material
    main_window._reference_combos["NIST610"].addItem("NIST610")
    main_window._reference_combos["NIST610"].setCurrentText("NIST610")
    main_window._primary_checkboxes["NIST610"].setChecked(True)
    main_window.spinDriftOrder.setValue(0)
    main_window.checkDespikeNoise.setChecked(True)

    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    result = main_window._current_result()
    assert result is not None
    assert result.provenance["despike_noise"] is True


def test_force_zero_intercept_checkbox_default_unchecked_and_reaches_run(tmp_path, qtbot, main_window):
    assert main_window.checkForceZeroIntercept.isChecked() is False

    sample_dir = tmp_path / "multi_std"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1)
    _write_raw_file(sample_dir, "NIST612", 1, base + timedelta(minutes=5), seed=2)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=10), seed=3)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    material_610 = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    })
    material_612 = parse_reference_material({
        "standard": "NIST612",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 40.0, "uncertainty": 1.0, "uncertainty_type": "1SD"}},
    })
    main_window.reference_library["NIST610"] = material_610
    main_window.reference_library["NIST612"] = material_612
    main_window._reference_combos["NIST610"].addItem("NIST610")
    main_window._reference_combos["NIST610"].setCurrentText("NIST610")
    main_window._reference_combos["NIST612"].addItem("NIST612")
    main_window._reference_combos["NIST612"].setCurrentText("NIST612")
    main_window._primary_checkboxes["NIST610"].setChecked(True)
    main_window._primary_checkboxes["NIST612"].setChecked(True)
    main_window.spinDriftOrder.setValue(0)
    main_window.checkForceZeroIntercept.setChecked(True)

    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    result = main_window._current_result()
    assert result is not None
    assert result.provenance["force_zero_intercept"] is True
    assert result.multi_standard_calibration.curves["Al27"].method == "multi_point_zero_intercept"


def test_run_with_background_override_via_gui(tmp_path, qtbot, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    })
    main_window.reference_library["NIST610"] = material
    main_window.comboDriftMethod.setCurrentText("Fixed order")
    main_window.comboBackgroundDriftMethod.setCurrentText("Fixed order")
    main_window.spinDriftOrder.setValue(0)
    main_window.checkBackgroundOverride.setChecked(True)
    main_window.spinOverrideStart.setValue(0.0)
    main_window.spinOverrideEnd.setValue(2.0)

    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    result = main_window._current_result()
    assert all(b.window.method == "manual_override" for b in result.backgrounds)


def test_time_series_tab_plots_checked_lines(tmp_path, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    name = sorted(main_window._scanned_files)[0]
    main_window._file_view_state[name] = True
    main_window._refresh_time_series_tab()

    assert len(main_window.canvasTimeSeries.axes.collections) > 0


def test_map_log_scale_checkbox_toggles_without_error(tmp_path, qtbot, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    })
    main_window.reference_library["NIST610"] = material
    main_window.spinDriftOrder.setValue(0)

    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    assert main_window.checkLogScale.isChecked() is False
    main_window.checkLogScale.setChecked(True)
    assert len(main_window.canvasMap.fig.axes) >= 1


def test_time_series_log_scale_checkbox_toggles_without_error(tmp_path, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    name = sorted(main_window._scanned_files)[0]
    main_window._file_view_state[name] = True
    main_window.checkLogScale.setChecked(True)
    main_window._refresh_time_series_tab()

    assert main_window.canvasTimeSeries.axes.get_yscale() == "log"


def test_plot_controls_row_visibility_matches_active_tab(main_window):
    """Stage/Offset-lines/Log-scale/Edit-mode/Hide-masked are a single
    shared row above the tab widget, not duplicated per tab -- only the
    controls relevant to the active tab should be visible. Log scale is
    shared by Maps and Time Series; Edit mode/Hide masked are shared by
    Time Series and Standards (the only two tabs with point masking)."""
    expected = {
        dw.CalibrationMainWindow.TAB_TIMING: (False, False, False, False),
        dw.CalibrationMainWindow.TAB_BACKGROUND: (False, False, False, False),
        dw.CalibrationMainWindow.TAB_TIME_SERIES: (False, True, True, True),
        dw.CalibrationMainWindow.TAB_STANDARDS: (False, False, False, True),
        dw.CalibrationMainWindow.TAB_CALIBRATION_CURVE: (False, False, False, False),
        dw.CalibrationMainWindow.TAB_MAPS: (True, False, True, False),
        dw.CalibrationMainWindow.TAB_DATA: (False, False, False, False),
    }
    for index, (stage, offset, log_scale, maskable) in expected.items():
        main_window.tabs.setCurrentIndex(index)
        assert main_window.comboMapStage.isVisible() is stage, main_window.tabs.tabText(index)
        assert main_window.checkOffsetLines.isVisible() is offset, main_window.tabs.tabText(index)
        assert main_window.checkLogScale.isVisible() is log_scale, main_window.tabs.tabText(index)
        assert main_window.checkEditMode.isVisible() is maskable, main_window.tabs.tabText(index)
        assert main_window.checkHideMaskedPoints.isVisible() is maskable, main_window.tabs.tabText(index)


def test_tab_constants_match_actual_tab_order(main_window):
    """Regression test: the TAB_* class constants must match the real
    addTab() order in _build_results_tabs, or _refresh_active_tab/
    _update_plot_controls_visibility silently act on the wrong tab.
    Confirmed in the field: TAB_BACKGROUND/TAB_TIME_SERIES were swapped
    (1 and 2 reversed), so changing analyte while genuinely viewing one
    redrew the other's (hidden) canvas instead -- each tab only appeared
    to update after round-tripping through the other, since that's what
    incidentally redrew its own (by-then-hidden) canvas. Checks against
    each tab's actual displayed text, independent of the constants
    themselves, so a self-consistent-but-wrong renumbering can't hide
    from this the way it hid from a test using the same constants for
    both the tab switch and the expected result."""
    expected_labels = {
        dw.CalibrationMainWindow.TAB_TIMING: "Timing / Files",
        dw.CalibrationMainWindow.TAB_TIME_SERIES: "Time Series",
        dw.CalibrationMainWindow.TAB_BACKGROUND: "Background",
        dw.CalibrationMainWindow.TAB_STANDARDS: "Standards QC",
        dw.CalibrationMainWindow.TAB_CALIBRATION_CURVE: "Calibration Curve",
        dw.CalibrationMainWindow.TAB_ISOTOPE_RATIOS: "Isotope Ratios",
        dw.CalibrationMainWindow.TAB_MAPS: "Maps",
        dw.CalibrationMainWindow.TAB_DATA: "Data",
    }
    for index, label in expected_labels.items():
        assert main_window.tabs.tabText(index) == label, f"index {index} expected {label!r}"


def test_tab_refresh_forces_immediate_repaint_not_just_scheduled(tmp_path, qtbot, main_window, mocker):
    """Regression test: canvas.draw() alone schedules a Qt repaint for the
    next event-loop iteration but doesn't force one -- reported in the
    field as the Background/Time Series plots not visually updating when
    the analyte changes, only catching up after switching tabs away and
    back (which happens to trigger its own repaint). Every tab refresh
    must go through _draw(), which calls flush_events() to force the
    pending repaint through immediately instead of leaving it scheduled."""
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)
    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    })
    main_window.reference_library["NIST610"] = material
    main_window._reference_combos["NIST610"].addItem("NIST610")
    main_window._reference_combos["NIST610"].setCurrentText("NIST610")
    main_window._primary_checkboxes["NIST610"].setChecked(True)
    main_window.spinDriftOrder.setValue(0)
    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    for canvas_name, tab_index in [
        ("canvasBackground", dw.CalibrationMainWindow.TAB_BACKGROUND),
        ("canvasTimeSeries", dw.CalibrationMainWindow.TAB_TIME_SERIES),
        ("canvasStandardVsReference", dw.CalibrationMainWindow.TAB_STANDARDS),
    ]:
        canvas = getattr(main_window, canvas_name)
        spy = mocker.spy(canvas, "flush_events")
        main_window.tabs.setCurrentIndex(tab_index)
        main_window.analyte_list.combo_box.setCurrentIndex(
            (main_window.analyte_list.combo_box.currentIndex() + 1) % main_window.analyte_list.combo_box.count()
        )
        assert spy.call_count >= 1, f"{canvas_name} did not force a repaint on analyte change"


def test_view_all_button_toggles_based_on_current_state(tmp_path, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    names = main_window._visible_file_table_names()
    assert names  # sanity: files were actually scanned

    # Default View state is all-unchecked -> label names the "check all"
    # action, and clicking should check every one.
    assert main_window.buttonViewAll.text() == "View All"
    main_window.buttonViewAll.click()
    assert all(main_window._file_view_state[n] for n in names)

    # Now all checked -> label flips to name the "uncheck all" action, and
    # clicking should uncheck every one (not leave a mix).
    assert main_window.buttonViewAll.text() == "View None"
    main_window.buttonViewAll.click()
    assert not any(main_window._file_view_state[n] for n in names)
    assert main_window.buttonViewAll.text() == "View All"


def test_use_all_button_toggles_based_on_current_state(tmp_path, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    names = main_window._visible_file_table_names()
    # Default Use state is all-checked -> label names the "uncheck all"
    # action, and clicking should uncheck every one.
    assert main_window.buttonUseAll.text() == "Use None"
    main_window.buttonUseAll.click()
    assert not any(main_window._file_use_state[n] for n in names)
    assert main_window.buttonUseAll.text() == "Use All"

    main_window.buttonUseAll.click()
    assert all(main_window._file_use_state[n] for n in names)
    assert main_window.buttonUseAll.text() == "Use None"


def test_use_column_feeds_excluded_files_into_run(tmp_path, qtbot, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    main_window._file_use_state["NIST610 - 2.csv"] = False
    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    })
    main_window.reference_library["NIST610"] = material
    main_window.spinDriftOrder.setValue(0)

    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    result = main_window._current_result()
    assert result.provenance["excluded_files"] == ["NIST610 - 2.csv"]


def test_toggle_all_button_labels_say_all_when_state_is_mixed(tmp_path, main_window):
    """A partial check (some rows checked, some not) must still show the
    "All" label -- only a uniformly-checked set of rows shows "None"."""
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    names = main_window._visible_file_table_names()
    assert len(names) >= 2
    main_window._file_view_state[names[0]] = True  # only one of several -> still mixed
    main_window._populate_file_table()
    assert main_window.buttonViewAll.text() == "View All"

    main_window._file_use_state[names[0]] = False  # one unchecked out of all-checked -> mixed
    main_window._populate_file_table()
    assert main_window.buttonUseAll.text() == "Use All"


def test_focus_combo_filters_file_table_rows(tmp_path, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    assert len(main_window._visible_file_table_names()) == 4  # "(all)" focus by default

    main_window.comboBoxSampleResult.setCurrentText("NIST610")
    names = main_window._visible_file_table_names()
    assert len(names) == 2
    assert all(n.startswith("NIST610") for n in names)


def test_time_series_shows_outlier_color_for_excluded_occurrence(tmp_path, qtbot, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    })
    main_window.reference_library["NIST610"] = material
    main_window.spinDriftOrder.setValue(0)
    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    result = main_window._current_result()
    standard_result = result.standard_results["NIST610"]
    forced_order = standard_result.occurrences[0].occurrence_order
    standard_result.excluded_outliers["Al27"] = [forced_order]

    main_window.analyte_list.combo_box.setCurrentText("Al27")
    target_name = standard_result.occurrences[0].file_meta.path.name
    main_window._file_view_state[target_name] = True
    main_window._refresh_time_series_tab()

    labels = {coll.get_label() for coll in main_window.canvasTimeSeries.axes.collections}
    assert "outlier" in labels


def _fake_event(px, py, xdata, ydata, ax, canvas):
    """A minimal stand-in for a matplotlib MouseEvent, carrying just the
    attributes _on_canvas_press/_motion/_release read (pixel x/y, data
    xdata/ydata, the Axes it landed in, and the originating canvas)."""
    return SimpleNamespace(x=px, y=py, xdata=xdata, ydata=ydata, inaxes=ax, canvas=canvas)


def test_click_on_time_series_point_toggles_manual_exclusion(tmp_path, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    name = sorted(main_window._scanned_files)[0]
    main_window._file_view_state[name] = True
    main_window._refresh_time_series_tab()

    point_index = main_window._time_series_point_index
    assert point_index is not None and not point_index.empty
    target = point_index.iloc[0]
    ax = main_window.canvasTimeSeries.axes
    px, py = ax.transData.transform((target["x"], target["y"]))
    event = _fake_event(px, py, target["x"], target["y"], ax, main_window.canvasTimeSeries)

    main_window.checkEditMode.setChecked(True)
    main_window._on_canvas_press(event, "time_series")
    main_window._on_canvas_release(event, "time_series")

    excluded = main_window._manual_row_exclusions.get(target["filename"], {}).get(target["analyte"], set())
    assert int(target["row_index"]) in excluded


def test_canvas_press_is_inert_while_edit_mode_is_off(tmp_path, main_window):
    """Point masking is opt-in: a plain click does nothing unless Edit mode
    is armed, even with the toolbar idle -- avoids accidentally masking a
    point while just examining the plot."""
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    name = sorted(main_window._scanned_files)[0]
    main_window._file_view_state[name] = True
    main_window._refresh_time_series_tab()

    point_index = main_window._time_series_point_index
    assert point_index is not None and not point_index.empty
    target = point_index.iloc[0]
    ax = main_window.canvasTimeSeries.axes
    px, py = ax.transData.transform((target["x"], target["y"]))
    event = _fake_event(px, py, target["x"], target["y"], ax, main_window.canvasTimeSeries)

    assert main_window.checkEditMode.isChecked() is False  # default
    main_window._on_canvas_press(event, "time_series")
    assert main_window._drag_canvas is None
    main_window._on_canvas_release(event, "time_series")

    excluded = main_window._manual_row_exclusions.get(target["filename"], {}).get(target["analyte"], set())
    assert int(target["row_index"]) not in excluded


def test_canvas_press_is_inert_while_toolbar_zoom_mode_is_active(tmp_path, main_window):
    """Regression test: point-masking's own press/motion/release handlers
    must defer entirely to the toolbar's zoom/pan tool while it's armed --
    running both on the same drag (the toolbar's native rubber-band paint
    and our own Rectangle-artist + draw_idle()) caused a real, reproducible
    segfault when zooming on the Time Series canvas."""
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    name = sorted(main_window._scanned_files)[0]
    main_window._file_view_state[name] = True
    main_window._refresh_time_series_tab()

    point_index = main_window._time_series_point_index
    assert point_index is not None and not point_index.empty
    target = point_index.iloc[0]
    ax = main_window.canvasTimeSeries.axes
    px, py = ax.transData.transform((target["x"], target["y"]))
    event = _fake_event(px, py, target["x"], target["y"], ax, main_window.canvasTimeSeries)

    main_window.checkEditMode.setChecked(True)  # edit mode armed -- toolbar.mode is the gate under test here
    main_window.toolbarTimeSeries.zoom()  # arms zoom mode, matching a real toolbar click
    assert main_window.toolbarTimeSeries.mode

    main_window._on_canvas_press(event, "time_series")
    assert main_window._drag_canvas is None  # press was ignored, no drag state armed
    main_window._on_canvas_release(event, "time_series")

    excluded = main_window._manual_row_exclusions.get(target["filename"], {}).get(target["analyte"], set())
    assert int(target["row_index"]) not in excluded

    # Clicking the same spot again toggles it back off.
    main_window._on_canvas_press(event, "time_series")
    main_window._on_canvas_release(event, "time_series")
    excluded = main_window._manual_row_exclusions.get(target["filename"], {}).get(target["analyte"], set())
    assert int(target["row_index"]) not in excluded


def test_drag_rectangle_toggles_multiple_points(tmp_path, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    name = sorted(main_window._scanned_files)[0]
    main_window._file_view_state[name] = True
    main_window._refresh_time_series_tab()

    point_index = main_window._time_series_point_index
    subset = point_index[point_index["filename"] == name]
    assert len(subset) >= 2
    ax = main_window.canvasTimeSeries.axes

    x0, x1 = float(subset["x"].min()), float(subset["x"].max())
    y0, y1 = float(subset["y"].min()), float(subset["y"].max())
    pad_x = max((x1 - x0) * 0.05, 1e-6)
    pad_y = max((y1 - y0) * 0.05, 1e-6)
    press_data = (x0 - pad_x, y0 - pad_y)
    release_data = (x1 + pad_x, y1 + pad_y)
    press_px = ax.transData.transform(press_data)
    release_px = ax.transData.transform(release_data)

    press_event = _fake_event(press_px[0], press_px[1], press_data[0], press_data[1], ax, main_window.canvasTimeSeries)
    release_event = _fake_event(release_px[0], release_px[1], release_data[0], release_data[1], ax, main_window.canvasTimeSeries)

    main_window.checkEditMode.setChecked(True)
    main_window._on_canvas_press(press_event, "time_series")
    main_window._on_canvas_release(release_event, "time_series")

    analyte = main_window.analyte_list.currentText()
    excluded = main_window._manual_row_exclusions.get(name, {}).get(analyte, set())
    assert set(int(r) for r in subset["row_index"]) <= excluded


def test_manual_row_exclusion_from_click_feeds_into_run(tmp_path, qtbot, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    _make_sample_dir(sample_dir)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    name = sorted(main_window._scanned_files)[0]
    main_window._file_view_state[name] = True
    main_window._refresh_time_series_tab()

    point_index = main_window._time_series_point_index
    target = point_index.iloc[0]
    ax = main_window.canvasTimeSeries.axes
    px, py = ax.transData.transform((target["x"], target["y"]))
    event = _fake_event(px, py, target["x"], target["y"], ax, main_window.canvasTimeSeries)
    main_window.checkEditMode.setChecked(True)
    main_window._on_canvas_press(event, "time_series")
    main_window._on_canvas_release(event, "time_series")
    assert main_window._manual_row_exclusions  # something got recorded

    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    })
    main_window.reference_library["NIST610"] = material
    main_window.spinDriftOrder.setValue(0)
    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    result = main_window._current_result()
    assert result is not None
    assert not result.calibrated_ppm.empty


def test_reference_combo_auto_guesses_case_insensitive_match(tmp_path, main_window):
    sample_dir = tmp_path / "case_mismatch"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    _write_raw_file(sample_dir, "nist610", 1, base, seed=1)  # lowercase filename label
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=10), seed=2)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    # Library has "NIST610" (uppercase); scanned label is "nist610" -- must
    # still auto-guess the match case-insensitively.
    assert main_window._reference_combos["nist610"].currentText() == "NIST610"
    assert main_window._primary_checkboxes["nist610"].isChecked() is True


def test_two_primary_standards_via_gui_produces_multi_point_calibration(tmp_path, qtbot, main_window):
    sample_dir = tmp_path / "multi_std"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1)
    _write_raw_file(sample_dir, "NIST612", 1, base + timedelta(minutes=5), seed=2)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=10), seed=3)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    material_610 = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 500.0, "uncertainty": 5.0, "uncertainty_type": "1SD"}},
    })
    material_612 = parse_reference_material({
        "standard": "NIST612",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 40.0, "uncertainty": 1.0, "uncertainty_type": "1SD"}},
    })
    main_window.reference_library["NIST610"] = material_610
    main_window.reference_library["NIST612"] = material_612
    # Re-populate so the Reference combos pick up the newly-added materials
    # (they were built from whatever was loaded at Scan time).
    main_window._reference_combos["NIST610"].addItem("NIST610")
    main_window._reference_combos["NIST610"].setCurrentText("NIST610")
    main_window._reference_combos["NIST612"].addItem("NIST612")
    main_window._reference_combos["NIST612"].setCurrentText("NIST612")
    main_window._primary_checkboxes["NIST610"].setChecked(True)
    main_window._primary_checkboxes["NIST612"].setChecked(True)
    main_window.spinDriftOrder.setValue(0)

    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    result = main_window._current_result()
    assert result is not None
    assert result.multi_standard_calibration is not None
    assert result.provenance["primary_standards"] == ["NIST610", "NIST612"]

    main_window.analyte_list.combo_box.setCurrentText("Al27")
    main_window._refresh_calibration_curve_tab()
    assert len(main_window.canvasCalibrationCurve.axes.collections) > 0


def test_scan_populates_isotope_calibration_table_only_for_multi_isotope_elements(tmp_path, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    pb_analytes = ["Al27", "Pb204", "Pb206", "Pb207", "Pb208"]  # Al27 is single-isotope -- no row expected
    bg = (300.0, 500.0, 8500.0, 7750.0, 18000.0)
    abl = (600000.0, 100000.0, 1700000.0, 1550000.0, 3600000.0)
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1, analytes=pb_analytes, bg_level=bg, ablation_level=abl)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=pb_analytes, bg_level=bg, ablation_level=abl)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    assert main_window.tableIsotopeCalibration.rowCount() == 1
    assert main_window.tableIsotopeCalibration.item(0, 0).text() == "Pb"
    assert main_window.tableIsotopeCalibration.item(0, 1).text() == "Pb204, Pb206, Pb207, Pb208"
    assert main_window._isotope_mode_combos["Pb"].currentText() == "Elemental"
    assert main_window._isotope_element_masses["Pb"] == [204, 206, 207, 208]


def test_isotope_calibration_mass_bias_mode_reaches_run_and_produces_bias_fit(tmp_path, qtbot, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    pb_analytes = ["Pb204", "Pb206", "Pb207", "Pb208"]
    std_bg, std_abl = (500.0, 8500.0, 7750.0, 18000.0), (100000.0, 1700000.0, 1550000.0, 3600000.0)
    sample_bg, sample_abl = (500.0, 8000.0, 7000.0, 17000.0), (100000.0, 1600000.0, 1400000.0, 3400000.0)
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1, analytes=pb_analytes, bg_level=std_bg, ablation_level=std_abl)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=pb_analytes, bg_level=sample_bg, ablation_level=sample_abl)
    _write_raw_file(sample_dir, "NIST610", 2, base + timedelta(minutes=45), seed=4, analytes=pb_analytes, bg_level=std_bg, ablation_level=std_abl)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    def _ratio(num_mass, value):
        return {
            "numerator_element": "Pb", "numerator_mass": num_mass, "denominator_element": "Pb", "denominator_mass": 204,
            "value": value, "uncertainty": 0.01, "uncertainty_type": "1SD", "source": "test",
        }

    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Pb204": {"element": "Pb", "mass": 204, "value": 2.0, "uncertainty": 0.1, "uncertainty_type": "1SD"}},
        "isotope_ratios": {"Pb206/Pb204": _ratio(206, 17.0), "Pb207/Pb204": _ratio(207, 15.5), "Pb208/Pb204": _ratio(208, 36.0)},
    })
    main_window.reference_library["NIST610"] = material
    main_window._reference_combos["NIST610"].addItem("NIST610")
    main_window._reference_combos["NIST610"].setCurrentText("NIST610")
    main_window._primary_checkboxes["NIST610"].setChecked(True)
    main_window._bias_checkboxes["NIST610"].setChecked(True)
    main_window.spinDriftOrder.setValue(0)

    assert main_window.tableIsotopeCalibration.rowCount() == 1
    main_window._isotope_mode_combos["Pb"].setCurrentText(dw.CalibrationMainWindow.ISOTOPE_MODE_MASS_BIAS)

    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    result = main_window._current_result()
    assert result is not None
    assert set(result.bias_fits) == {"Pb206/Pb204", "Pb207/Pb204", "Pb208/Pb204"}
    assert not result.isotopic_ppm.empty
    assert result.isotopic_ppm_provenance["Pb"]["normalizer_mass"] == 204

    # Isotope Ratios tab combo/refresh, driven by the same result.
    assert set(main_window.comboIsotopeRatioPair.itemText(i) for i in range(main_window.comboIsotopeRatioPair.count())) == set(result.bias_fits)
    main_window.comboIsotopeRatioPair.setCurrentText("Pb206/Pb204")
    main_window._refresh_isotope_ratios_tab()
    assert "Pb206/Pb204" in main_window.canvasIsotopeBiasFit.axes.get_title()


def test_isotope_calibration_natural_abundance_mode_reaches_run(tmp_path, qtbot, main_window):
    # No isotope_ratios in the reference material and no Bias-checked
    # standard at all -- natural_abundance mode must still work, using
    # most_abundant_mass as its normalizer fallback (see
    # _resolve_isotope_normalizer_mass).
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    fe_analytes = ["Fe56", "Fe57"]
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1, analytes=fe_analytes, bg_level=(500.0, 500.0), ablation_level=(900000.0, 900000.0))
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=fe_analytes, bg_level=(500.0, 500.0), ablation_level=(900000.0, 900000.0))
    _write_raw_file(sample_dir, "NIST610", 2, base + timedelta(minutes=45), seed=4, analytes=fe_analytes, bg_level=(500.0, 500.0), ablation_level=(900000.0, 900000.0))

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Fe56": {"element": "Fe", "mass": 56, "value": 461.5, "uncertainty": 1.0, "uncertainty_type": "1SD"}},
    })
    main_window.reference_library["NIST610"] = material
    main_window._reference_combos["NIST610"].addItem("NIST610")
    main_window._reference_combos["NIST610"].setCurrentText("NIST610")
    main_window._primary_checkboxes["NIST610"].setChecked(True)
    main_window.spinDriftOrder.setValue(0)

    assert main_window.tableIsotopeCalibration.rowCount() == 1
    assert main_window.tableIsotopeCalibration.item(0, 0).text() == "Fe"
    main_window._isotope_mode_combos["Fe"].setCurrentText(dw.CalibrationMainWindow.ISOTOPE_MODE_NATURAL_ABUNDANCE)

    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    result = main_window._current_result()
    assert result is not None
    assert result.bias_fits == {}  # natural_abundance mode never requests a bias_spec
    assert not result.isotopic_ppm.empty
    assert result.isotopic_ppm_provenance["Fe"]["normalizer_mass"] == 56  # Fe56 is most naturally abundant


def test_isotope_calibration_el_total_checkbox_reaches_run_and_produces_pooled_channel(tmp_path, qtbot, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    pb_analytes = ["Pb206", "Pb207", "Pb208"]
    pb_bg, pb_abl = (500.0, 500.0, 500.0), (900000.0, 900000.0, 900000.0)
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1, analytes=pb_analytes, bg_level=pb_bg, ablation_level=pb_abl)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=pb_analytes, bg_level=pb_bg, ablation_level=pb_abl)
    _write_raw_file(sample_dir, "NIST610", 2, base + timedelta(minutes=45), seed=4, analytes=pb_analytes, bg_level=pb_bg, ablation_level=pb_abl)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Pb206": {"element": "Pb", "mass": 206, "value": 461.5, "uncertainty": 1.0, "uncertainty_type": "1SD"}},
    })
    main_window.reference_library["NIST610"] = material
    main_window._reference_combos["NIST610"].addItem("NIST610")
    main_window._reference_combos["NIST610"].setCurrentText("NIST610")
    main_window._primary_checkboxes["NIST610"].setChecked(True)
    main_window.spinDriftOrder.setValue(0)

    assert main_window.tableIsotopeCalibration.rowCount() == 1
    assert main_window._isotope_pool_checkboxes["Pb"].isChecked() is False  # opt-in, unchecked by default
    main_window._isotope_pool_checkboxes["Pb"].setChecked(True)
    # Mode stays Elemental -- El total is independent of the Mode column.
    assert main_window._isotope_mode_combos["Pb"].currentText() == dw.CalibrationMainWindow.ISOTOPE_MODE_ELEMENTAL

    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    result = main_window._current_result()
    assert result is not None
    assert "Pb total" in result.calibrated_ppm.columns
    assert result.calibrated_ppm["Pb total"].notna().all()
    assert result.provenance["pool_specs"] == [{"element": "Pb", "masses": [206, 207, 208]}]


def test_scan_populates_dating_systems_table(tmp_path, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    analytes = ["U238", "Pb204", "Pb206", "Pb207", "Th232", "Pb208"]
    bg = (500.0,) * 6
    abl = (900000.0, 5000.0, 90000.0, 6000.0, 900000.0, 45000.0)
    _write_raw_file(sample_dir, "ZRNSTD", 1, base, seed=1, analytes=analytes, bg_level=bg, ablation_level=abl, bg_n=15, ablation_n=30)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=analytes, bg_level=bg, ablation_level=abl, bg_n=15, ablation_n=30)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    rows = {
        main_window.tableRadiometricSystems.item(i, 0).text(): main_window.tableRadiometricSystems.item(i, 1).text()
        for i in range(main_window.tableRadiometricSystems.rowCount())
    }
    assert set(rows) == {"Pb-Pb", "U-Pb", "Th-Pb"}
    assert "Pb206/Pb204" in rows["Pb-Pb"]
    assert "Pb208/Pb207" in rows["Pb-Pb"]
    assert "Pb206/U238" in rows["U-Pb"]
    assert "207Pb/235U" in rows["U-Pb"]
    assert rows["Th-Pb"] == "Pb208/Th232"
    for cb in main_window._dating_system_checkboxes.values():
        assert cb.isChecked() is False  # opt-in, unchecked by default


def test_scan_omits_dating_systems_missing_required_isotopes(tmp_path, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    # Only U238 + Pb206 -- no Th232/Pb208, no second Pb isotope for Pb-Pb.
    analytes = ["U238", "Pb206"]
    _write_raw_file(sample_dir, "ZRNSTD", 1, base, seed=1, analytes=analytes, bg_level=(500.0, 500.0), ablation_level=(900000.0, 90000.0), bg_n=15, ablation_n=30)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    names = {main_window.tableRadiometricSystems.item(i, 0).text() for i in range(main_window.tableRadiometricSystems.rowCount())}
    assert names == {"U-Pb"}


def test_dating_ratios_u_pb_th_pb_checkboxes_reach_run_and_produce_ratios(tmp_path, qtbot, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    analytes = ["U238", "Pb206", "Pb207", "Th232", "Pb208"]

    std_bg = (500.0,) * 5
    std_abl = (900000.0, 90000.0, 6000.0, 900000.0, 45000.0)  # Pb206/U238=0.1, Pb207/U238=0.006667, Pb208/Th232=0.05
    sample_bg = (500.0,) * 5
    sample_abl = (900000.0, 126000.0, 5400.0, 900000.0, 63000.0)

    _write_raw_file(sample_dir, "ZRNSTD", 1, base, seed=1, analytes=analytes, bg_level=std_bg, ablation_level=std_abl, bg_n=15, ablation_n=30)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=analytes, bg_level=sample_bg, ablation_level=sample_abl, bg_n=15, ablation_n=30)
    _write_raw_file(sample_dir, "ZRNSTD", 2, base + timedelta(minutes=45), seed=4, analytes=analytes, bg_level=std_bg, ablation_level=std_abl, bg_n=15, ablation_n=30)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    def _ratio(num_el, num_mass, den_el, den_mass, value):
        return {
            "numerator_element": num_el, "numerator_mass": num_mass,
            "denominator_element": den_el, "denominator_mass": den_mass,
            "value": value, "uncertainty": 0.001, "uncertainty_type": "1SD", "source": "test",
        }

    k = dw.natural_abundance_ratio("U", 238, 235)
    material = parse_reference_material({
        "standard": "ZRNSTD",
        "analytes": {"Pb206": {"element": "Pb", "mass": 206, "value": 0.05, "uncertainty": 0.0005, "uncertainty_type": "1SD"}},
        "isotope_ratios": {
            "Pb206/U238": _ratio("Pb", 206, "U", 238, 90000.0 / 900000.0),
            "Pb207/U238": _ratio("Pb", 207, "U", 238, k * (6000.0 / 900000.0)),
            "Pb208/Th232": _ratio("Pb", 208, "Th", 232, 45000.0 / 900000.0),
            "Pb207/Pb206": _ratio("Pb", 207, "Pb", 206, 6000.0 / 90000.0),
        },
    })
    main_window.reference_library["ZRNSTD"] = material
    main_window._reference_combos["ZRNSTD"].addItem("ZRNSTD")
    main_window._reference_combos["ZRNSTD"].setCurrentText("ZRNSTD")
    main_window._primary_checkboxes["ZRNSTD"].setChecked(True)
    main_window._bias_checkboxes["ZRNSTD"].setChecked(True)
    main_window.spinDriftOrder.setValue(0)

    main_window._dating_system_checkboxes["U-Pb"].setChecked(True)
    main_window._dating_system_checkboxes["Th-Pb"].setChecked(True)

    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    result = main_window._current_result()
    assert result is not None
    assert set(result.dating_ratio_fits) == {"Pb206/U238", "Pb207/U238", "Pb208/Th232"}
    assert "Pb207/Pb206" in result.bias_fits
    for col in ["Pb206 / U238", "Pb207 / U238", "Pb208 / Th232", "Pb207 / Pb206"]:
        assert col in result.calibrated_ratios.columns
    assert result.provenance["dating_ratio_specs"][0]["numerator_element"] == "Pb"

    # Isotope Ratios tab combo/refresh, driven by the same result.
    combo_items = {main_window.comboIsotopeRatioPair.itemText(i) for i in range(main_window.comboIsotopeRatioPair.count())}
    assert combo_items == set(result.bias_fits) | set(result.dating_ratio_fits)
    main_window.comboIsotopeRatioPair.setCurrentText("Pb206/U238")
    main_window._refresh_isotope_ratios_tab()
    assert "Pb206/U238" in main_window.canvasIsotopeBiasFit.axes.get_title()


def test_dating_ratios_pb_pb_checkbox_generates_all_pairwise_bias_specs(tmp_path, qtbot, main_window):
    sample_dir = tmp_path / "25B-1"
    sample_dir.mkdir()
    base = datetime(2026, 3, 1, 10, 0, 0)
    pb_analytes = ["Pb204", "Pb206", "Pb207", "Pb208"]
    bg = (500.0, 500.0, 500.0, 500.0)
    abl = (100000.0, 1700000.0, 1550000.0, 3600000.0)
    _write_raw_file(sample_dir, "NIST610", 1, base, seed=1, analytes=pb_analytes, bg_level=bg, ablation_level=abl, bg_n=15, ablation_n=30)
    _write_raw_file(sample_dir, "SAMPLE", 1, base + timedelta(minutes=15), seed=2, analytes=pb_analytes, bg_level=bg, ablation_level=abl, bg_n=15, ablation_n=30)
    _write_raw_file(sample_dir, "NIST610", 2, base + timedelta(minutes=45), seed=4, analytes=pb_analytes, bg_level=bg, ablation_level=abl, bg_n=15, ablation_n=30)

    main_window._data_dir = sample_dir
    main_window.lineEditDataDir.setText(str(sample_dir))
    main_window._on_scan()

    def _ratio(num_mass, den_mass, value):
        return {
            "numerator_element": "Pb", "numerator_mass": num_mass, "denominator_element": "Pb", "denominator_mass": den_mass,
            "value": value, "uncertainty": 0.01, "uncertainty_type": "1SD", "source": "test",
        }

    material = parse_reference_material({
        "standard": "NIST610",
        "analytes": {"Pb204": {"element": "Pb", "mass": 204, "value": 2.0, "uncertainty": 0.1, "uncertainty_type": "1SD"}},
        "isotope_ratios": {
            "Pb206/Pb204": _ratio(206, 204, 17.0), "Pb207/Pb204": _ratio(207, 204, 15.5),
            "Pb208/Pb204": _ratio(208, 204, 36.0), "Pb207/Pb206": _ratio(207, 206, 0.911),
            "Pb208/Pb206": _ratio(208, 206, 2.117), "Pb208/Pb207": _ratio(208, 207, 2.323),
        },
    })
    main_window.reference_library["NIST610"] = material
    main_window._reference_combos["NIST610"].addItem("NIST610")
    main_window._reference_combos["NIST610"].setCurrentText("NIST610")
    main_window._primary_checkboxes["NIST610"].setChecked(True)
    main_window._bias_checkboxes["NIST610"].setChecked(True)
    main_window.spinDriftOrder.setValue(0)

    main_window._dating_system_checkboxes["Pb-Pb"].setChecked(True)

    main_window._on_run()
    qtbot.waitUntil(lambda: len(main_window.results) > 0, timeout=10000)

    result = main_window._current_result()
    assert result is not None
    assert set(result.bias_fits) == {
        "Pb206/Pb204", "Pb207/Pb204", "Pb208/Pb204", "Pb207/Pb206", "Pb208/Pb206", "Pb208/Pb207",
    }


def test_add_standard_writes_new_yaml_and_reloads(tmp_path, qtbot, main_window, monkeypatch, mocker):
    fake_dir = tmp_path / "reference_materials"
    fake_dir.mkdir()
    shutil.copy(dw.REFERENCE_LIBRARY_DIR / "_template.yaml", fake_dir / "_template.yaml")
    monkeypatch.setattr(dw, "REFERENCE_LIBRARY_DIR", fake_dir)

    mocker.patch.object(dw.QInputDialog, "getText", return_value=("GUITESTSTD", True))
    main_window._on_add_standard()

    assert (fake_dir / "GUITESTSTD.yaml").exists()
    assert "GUITESTSTD" in main_window.reference_library


def test_edit_standard_opens_dialog_defaulting_to_first_material(main_window):
    analytes = {"Al27": {"element": "Al", "mass": 27, "value": 1.0, "uncertainty": 0.1, "uncertainty_type": "1SD"}}
    main_window.reference_library = {
        "ZZZSTD": parse_reference_material({"standard": "ZZZSTD", "analytes": analytes}),
        "AAASTD": parse_reference_material({"standard": "AAASTD", "analytes": analytes}),
    }
    main_window._on_edit_standard()

    dialog = main_window._active_dialog
    assert dialog.comboStandard.currentText() == "AAASTD"  # sorted first, not insertion order
    assert dialog.material.standard == "AAASTD"
    dialog.close()


def test_reference_dialog_switching_material_loads_its_table(main_window):
    library = {
        "STDA": parse_reference_material({
            "standard": "STDA",
            "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 100.0, "uncertainty": 1.0, "uncertainty_type": "1SD"}},
        }),
        "STDB": parse_reference_material({
            "standard": "STDB",
            "analytes": {"Ca43": {"element": "Ca", "mass": 43, "value": 200.0, "uncertainty": 2.0, "uncertainty_type": "1SD"}},
        }),
    }
    dialog = dw.ReferenceMaterialEditDialog(library, dw.REFERENCE_LIBRARY_DIR, initial_name="STDA")
    assert dialog.table.item(0, 0).text() == "Al27"

    dialog.comboStandard.setCurrentText("STDB")
    assert dialog.material.standard == "STDB"
    assert dialog.table.item(0, 0).text() == "Ca43"
    dialog.close()


def test_reference_dialog_loads_isotope_ratios_into_ratio_table():
    library = {
        "ZRNSTD": parse_reference_material({
            "standard": "ZRNSTD",
            "analytes": {"Pb206": {"element": "Pb", "mass": 206, "value": 0.05, "uncertainty": 0.001, "uncertainty_type": "1SD"}},
            "isotope_ratios": {
                "Pb206/U238": {
                    "numerator_element": "Pb", "numerator_mass": 206, "denominator_element": "U", "denominator_mass": 238,
                    "value": 0.05, "uncertainty": 0.0005, "uncertainty_type": "1SD", "source": "test",
                },
            },
        }),
    }
    dialog = dw.ReferenceMaterialEditDialog(library, dw.REFERENCE_LIBRARY_DIR, initial_name="ZRNSTD")
    assert dialog.tableRatios.rowCount() == 1
    assert dialog.tableRatios.item(0, 0).text() == "Pb206"
    assert dialog.tableRatios.item(0, 1).text() == "U238"
    assert dialog.tableRatios.item(0, 2).text() == "0.05"
    dialog.close()


def test_reference_dialog_save_preserves_isotope_ratios(tmp_path, mocker):
    # Regression test: _on_save used to rebuild ReferenceMaterial(...)
    # without passing isotope_ratios=, silently dropping any existing
    # certified ratios on every Save.
    mocker.patch.object(dw.QMessageBox, "information")
    fake_dir = tmp_path / "reference_materials"
    fake_dir.mkdir()
    material = parse_reference_material({
        "standard": "ZRNSTD",
        "analytes": {"Pb206": {"element": "Pb", "mass": 206, "value": 0.05, "uncertainty": 0.001, "uncertainty_type": "1SD"}},
        "isotope_ratios": {
            "Pb206/U238": {
                "numerator_element": "Pb", "numerator_mass": 206, "denominator_element": "U", "denominator_mass": 238,
                "value": 0.05, "uncertainty": 0.0005, "uncertainty_type": "1SD", "source": "test",
            },
        },
    })
    reflib.save_reference_material(material, fake_dir / "ZRNSTD.yaml")
    library = {"ZRNSTD": material}
    dialog = dw.ReferenceMaterialEditDialog(library, fake_dir, initial_name="ZRNSTD")

    dialog._on_save()

    reloaded = reflib.load_reference_material(fake_dir / "ZRNSTD.yaml")
    assert "Pb206/U238" in reloaded.isotope_ratios
    assert reloaded.isotope_ratios["Pb206/U238"].value == pytest.approx(0.05)
    assert library["ZRNSTD"].isotope_ratios["Pb206/U238"].value == pytest.approx(0.05)
    dialog.close()


def test_reference_dialog_add_and_delete_analyte_row(tmp_path, mocker):
    mocker.patch.object(dw.QMessageBox, "information")
    fake_dir = tmp_path / "reference_materials"
    fake_dir.mkdir()
    library = {"STDA": parse_reference_material({
        "standard": "STDA",
        "analytes": {"Al27": {"element": "Al", "mass": 27, "value": 100.0, "uncertainty": 1.0, "uncertainty_type": "1SD"}},
    })}
    dialog = dw.ReferenceMaterialEditDialog(library, fake_dir, initial_name="STDA")
    assert dialog.table.rowCount() == 1

    dialog._on_add_analyte_row()
    assert dialog.table.rowCount() == 2
    for j, v in enumerate(["Pb206", "Pb", "206", "0.05", "0.001", "1SD", "ppm", "test"]):
        dialog.table.setItem(1, j, dw.QTableWidgetItem(v))

    dialog._on_save()
    assert "Pb206" in dialog.material.analytes
    assert dialog.material.analytes["Pb206"].value == pytest.approx(0.05)

    dialog.table.selectRow(1)
    dialog._on_delete_selected_row(dialog.table)
    assert dialog.table.rowCount() == 1
    dialog.close()


def test_reference_dialog_add_and_delete_ratio_row(tmp_path, mocker):
    mocker.patch.object(dw.QMessageBox, "information")
    fake_dir = tmp_path / "reference_materials"
    fake_dir.mkdir()
    library = {"ZRNSTD": parse_reference_material({
        "standard": "ZRNSTD",
        "analytes": {"Pb206": {"element": "Pb", "mass": 206, "value": 0.05, "uncertainty": 0.001, "uncertainty_type": "1SD"}},
    })}
    dialog = dw.ReferenceMaterialEditDialog(library, fake_dir, initial_name="ZRNSTD")
    assert dialog.tableRatios.rowCount() == 0

    dialog._on_add_ratio_row()
    assert dialog.tableRatios.rowCount() == 1
    for j, v in enumerate(["Pb206", "U238", "0.05", "0.0005", "1SD", "test"]):
        dialog.tableRatios.setItem(0, j, dw.QTableWidgetItem(v))

    dialog._on_save()
    assert "Pb206/U238" in dialog.material.isotope_ratios
    assert dialog.material.isotope_ratios["Pb206/U238"].value == pytest.approx(0.05)

    dialog.tableRatios.selectRow(0)
    dialog._on_delete_selected_row(dialog.tableRatios)
    assert dialog.tableRatios.rowCount() == 0
    dialog.close()


def test_reference_dialog_new_standard_can_add_ratio_and_save(tmp_path, monkeypatch, mocker):
    mocker.patch.object(dw.QMessageBox, "information")
    fake_dir = tmp_path / "reference_materials"
    fake_dir.mkdir()
    shutil.copy(dw.REFERENCE_LIBRARY_DIR / "_template.yaml", fake_dir / "_template.yaml")

    library = {}
    dialog = dw.ReferenceMaterialEditDialog(library, fake_dir)
    mocker.patch.object(dw.QInputDialog, "getText", return_value=("NEWZRN", True))
    dialog._on_new_standard()
    assert dialog.material.standard == "NEWZRN"
    assert dialog.tableRatios.rowCount() == 0

    dialog._on_add_ratio_row()
    for j, v in enumerate(["Pb208", "Th232", "0.03", "0.0003", "1SD", "test"]):
        dialog.tableRatios.setItem(0, j, dw.QTableWidgetItem(v))
    dialog._on_save()

    reloaded = reflib.load_reference_material(fake_dir / "NEWZRN.yaml")
    assert "Pb208/Th232" in reloaded.isotope_ratios
    assert reloaded.isotope_ratios["Pb208/Th232"].value == pytest.approx(0.03)
    dialog.close()


def test_reference_dialog_shares_library_dict_with_main_window(main_window):
    """The dialog mutates the SAME dict object passed in (never reassigns
    it) so edits/reloads made in the dialog are visible on the main window
    immediately, without an explicit sync-back step."""
    main_window._on_edit_standard()
    dialog = main_window._active_dialog
    assert dialog.reference_library is main_window.reference_library
    dialog.close()


def test_reference_dialog_reload_picks_up_disk_changes(tmp_path, monkeypatch, mocker):
    fake_dir = tmp_path / "reference_materials"
    fake_dir.mkdir()
    shutil.copy(dw.REFERENCE_LIBRARY_DIR / "_template.yaml", fake_dir / "_template.yaml")
    monkeypatch.setattr(dw, "REFERENCE_LIBRARY_DIR", fake_dir)

    library = {}
    dialog = dw.ReferenceMaterialEditDialog(library, fake_dir)
    assert dialog.comboStandard.count() == 0

    mocker.patch.object(dw.QInputDialog, "getText", return_value=("NEWSTD", True))
    dialog._on_new_standard()  # writes NEWSTD.yaml directly, bypassing reload

    # Simulate a change made outside this dialog (e.g. hand-edited on disk).
    other_library = {}
    other_dialog = dw.ReferenceMaterialEditDialog(other_library, fake_dir)
    assert "NEWSTD" not in other_library  # not loaded yet

    other_dialog._on_reload()
    assert "NEWSTD" in other_library
    assert other_dialog.comboStandard.findText("NEWSTD") >= 0
    dialog.close()
    other_dialog.close()
