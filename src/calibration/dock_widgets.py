"""Standalone Qt widgets for the LA-ICP-MS calibration GUI.

The only PyQt-importing file in this package besides ``app.py``. Builds an
independent ``QMainWindow`` (not a ``CustomDockWidget`` bound to LaME's
``MainWindow``) so this stays usable without the rest of the app.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import re
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QTabWidget, QToolBar, QToolBox, QVBoxLayout, QWidget, QGridLayout, QStatusBar,
)

from lame_core.CustomWidgets import CustomAction, CustomSlider, ListFilterWidget, SpinComboBox

from src.calibration import diagnostics, io_export, pipeline, reflib, standards
from src.calibration.background import BackgroundWindowOverride
from src.calibration.dating_ratios import DatingRatioSpec
from src.calibration.geometry import InstrumentSettings
from src.calibration.isotope_apportion import IsotopeShareSpec
from src.calibration.massbias import BiasSpec, most_abundant_mass, natural_abundance_ratio
from src.calibration.pipeline import PipelineError, SampleCalibratedResult
from src.calibration.pooling import PooledElementSpec
from src.calibration.rawfile import LineFileData, list_line_files, parse_filename_label, parse_line_file
from src.classification.cosine import classify_batch
from src.classification.presets import DEFAULT_PRESETS_PATH, load_presets, save_preset
from src.classification.reference import (
    MineralReference, ReferenceLibraryError, load_reference_library,
)
from src.deconvolution import diagnostics as deconv_diagnostics
from src.deconvolution import esf
from src.deconvolution.config import DeconvolutionSettings
from src.deconvolution.esf import SinglePulseFit
from src.deconvolution.pipeline import correct_line
from src.plotting.CustomMplCanvas import SimpleMplCanvas, make_compact_nav_toolbar

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_LIBRARY_DIR = PROJECT_ROOT / "resources" / "calibration" / "reference_materials"

# Drift-fit method choices shown in the GUI -> pipeline.run()'s method strings.
DRIFT_METHOD_LABELS = {
    "Fixed order": "fixed",
    "Auto (AIC)": "auto_aic",
    "Auto (Poisson GLM+LRT)": "auto_poisson_lrt",
}


def _populate_table(table_widget: QTableWidget, df: pd.DataFrame) -> None:
    """Renders a DataFrame of mixed dtypes into a QTableWidget (booleans/strings
    included) -- ``InfoViewer.update_dataframe`` assumes all-numeric content,
    which the calibration QC tables don't satisfy."""
    table_widget.setRowCount(len(df))
    table_widget.setColumnCount(len(df.columns))
    table_widget.setHorizontalHeaderLabels([str(c) for c in df.columns])
    for row_idx, (_, row) in enumerate(df.iterrows()):
        for col_idx, value in enumerate(row):
            if isinstance(value, float):
                text = f"{value:.4g}"
            else:
                text = str(value)
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table_widget.setItem(row_idx, col_idx, item)
    table_widget.resizeColumnsToContents()


_ELEMENT_COL_RE = re.compile(r"^([A-Z][a-z]?)(\d+)$")


def _resolve_element_columns(references: list[MineralReference], available_columns) -> dict[str, str]:
    """Map each element symbol any reference needs to a matching isotope-
    style analyte column in ``calibrated_ppm`` (e.g. 'Ca' -> 'Ca43'), by
    prefix match -- same problem/approach as
    ``src.stoichiometry.dock._resolve_ppm_columns``, reimplemented locally
    rather than importing that sibling package's private helper (same
    "duplicate a small private helper" precedent already used for
    ``_mad_outlier_mask``/deconvolution's shift-offset math elsewhere in
    this codebase).
    """
    needed = {el for ref in references for el in ref.composition}
    resolved: dict[str, str] = {}
    for col in available_columns:
        m = _ELEMENT_COL_RE.match(str(col))
        if not m:
            continue
        el = m.group(1)
        if el in needed and el not in resolved:
            resolved[el] = col
    return resolved


class _PipelineWorker(QThread):
    """Runs ``pipeline.run``/``run_batch`` off the UI thread so scanning/parsing
    a full session (potentially 100+ files) doesn't freeze the GUI."""

    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, fn, kwargs, parent=None):
        super().__init__(parent)
        self._fn = fn
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(**self._kwargs)
        except Exception as e:  # noqa: BLE001 -- surfaced to the user via a message box
            self.failed.emit(str(e))
            return
        self.finished_ok.emit(result if isinstance(result, dict) else {})


class ReferenceMaterialEditDialog(QMainWindow):
    """Editor for the reference material library -- browse/switch between
    every material in ``reference_library`` via a combo (moved here from
    the main window's left panel, since this is the only place that
    actually needs it), edit the selected one's analyte values, or create
    a new one, all without reopening the dialog.

    A QMainWindow (not QDialog) only so it can host a QTableWidget without
    extra boilerplate; opened model from the toolbar's Edit/Add
    Standard actions.

    ``reference_library`` is mutated in place (``.clear()``/``.update()``,
    never reassigned) whenever it's reloaded or a material is
    added/edited here, so the caller's own reference to the same dict
    (``CalibrationMainWindow.reference_library``) stays in sync live --
    no explicit sync-back step needed, including while this dialog is
    still open.
    """

    def __init__(
        self, reference_library: dict[str, reflib.ReferenceMaterial], library_dir: Path,
        initial_name: str | None = None, parent=None,
    ):
        super().__init__(parent)
        self.reference_library = reference_library
        self.library_dir = library_dir
        self.material: reflib.ReferenceMaterial | None = None
        self.setWindowTitle("Edit reference standards")
        self.resize(760, 560)

        central = QWidget()
        layout = QVBoxLayout(central)

        picker_row = QHBoxLayout()
        picker_row.addWidget(QLabel("Standard"))
        self.comboStandard = QComboBox()
        self.comboStandard.currentTextChanged.connect(self._load_selected_material)
        picker_row.addWidget(self.comboStandard, stretch=1)
        self.buttonNewStandard = QPushButton("New...")
        self.buttonNewStandard.clicked.connect(self._on_new_standard)
        picker_row.addWidget(self.buttonNewStandard)
        self.buttonReloadStandards = QPushButton("Reload")
        self.buttonReloadStandards.setToolTip("Reload the reference library from disk")
        self.buttonReloadStandards.clicked.connect(self._on_reload)
        picker_row.addWidget(self.buttonReloadStandards)
        layout.addLayout(picker_row)

        layout.addWidget(QLabel("Analytes (elemental concentrations)"))
        self.table = QTableWidget()
        columns = ["analyte", "element", "mass", "value", "uncertainty", "uncertainty_type", "units", "source"]
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        analyte_row_buttons = QHBoxLayout()
        add_analyte_button = QPushButton("Add row")
        add_analyte_button.clicked.connect(self._on_add_analyte_row)
        analyte_row_buttons.addWidget(add_analyte_button)
        delete_analyte_button = QPushButton("Delete selected row")
        delete_analyte_button.clicked.connect(lambda: self._on_delete_selected_row(self.table))
        analyte_row_buttons.addWidget(delete_analyte_button)
        analyte_row_buttons.addStretch(1)
        layout.addLayout(analyte_row_buttons)

        layout.addWidget(QLabel("Isotope ratios (certified, for mass-bias/radiogenic-ratio calibration)"))
        self.tableRatios = QTableWidget()
        ratio_columns = ["numerator", "denominator", "value", "uncertainty", "uncertainty_type", "source"]
        self.tableRatios.setColumnCount(len(ratio_columns))
        self.tableRatios.setHorizontalHeaderLabels(ratio_columns)
        self.tableRatios.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.tableRatios)

        ratio_row_buttons = QHBoxLayout()
        add_ratio_button = QPushButton("Add row")
        add_ratio_button.clicked.connect(self._on_add_ratio_row)
        ratio_row_buttons.addWidget(add_ratio_button)
        delete_ratio_button = QPushButton("Delete selected row")
        delete_ratio_button.clicked.connect(lambda: self._on_delete_selected_row(self.tableRatios))
        ratio_row_buttons.addWidget(delete_ratio_button)
        ratio_row_buttons.addStretch(1)
        layout.addLayout(ratio_row_buttons)

        button_row = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self._on_save)
        button_row.addWidget(save_button)
        layout.addLayout(button_row)

        self.setCentralWidget(central)

        self._populate_combo(select=initial_name)

    def _populate_combo(self, select: str | None = None):
        select = select or self.comboStandard.currentText() or None
        self.comboStandard.blockSignals(True)
        self.comboStandard.clear()
        self.comboStandard.addItems(sorted(self.reference_library))
        self.comboStandard.blockSignals(False)
        idx = self.comboStandard.findText(select) if select else -1
        self.comboStandard.setCurrentIndex(idx if idx >= 0 else 0 if self.comboStandard.count() else -1)
        self._load_selected_material(self.comboStandard.currentText())

    def _load_selected_material(self, name: str):
        self.material = self.reference_library.get(name) if name else None
        self.table.setRowCount(0)
        self.tableRatios.setRowCount(0)
        if self.material is None:
            self.setWindowTitle("Edit reference standards")
            return
        self.setWindowTitle(f"Edit reference standards: {self.material.standard}")
        rows = sorted(self.material.analytes.items())
        self.table.setRowCount(len(rows))
        for i, (analyte_name, a) in enumerate(rows):
            values = [analyte_name, a.element, str(a.mass), "" if a.value is None else str(a.value),
                      "" if a.uncertainty is None else str(a.uncertainty), a.uncertainty_type, a.units, a.source]
            for j, v in enumerate(values):
                item = QTableWidgetItem(v)
                if j in (0, 1, 2):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, j, item)
        self.table.resizeColumnsToContents()

        ratio_rows = sorted(self.material.isotope_ratios.items())
        self.tableRatios.setRowCount(len(ratio_rows))
        for i, (_, r) in enumerate(ratio_rows):
            values = [
                r.numerator, r.denominator, "" if r.value is None else str(r.value),
                "" if r.uncertainty is None else str(r.uncertainty), r.uncertainty_type or "", r.source,
            ]
            for j, v in enumerate(values):
                self.tableRatios.setItem(i, j, QTableWidgetItem(v))
        self.tableRatios.resizeColumnsToContents()

    def _on_add_analyte_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for j in range(self.table.columnCount()):
            self.table.setItem(row, j, QTableWidgetItem(""))

    def _on_add_ratio_row(self):
        row = self.tableRatios.rowCount()
        self.tableRatios.insertRow(row)
        for j in range(self.tableRatios.columnCount()):
            self.tableRatios.setItem(row, j, QTableWidgetItem(""))

    @staticmethod
    def _on_delete_selected_row(table: QTableWidget):
        rows = sorted({idx.row() for idx in table.selectedIndexes()}, reverse=True)
        for row in rows:
            table.removeRow(row)

    def _on_reload(self):
        self.library_dir.mkdir(parents=True, exist_ok=True)
        fresh = reflib.load_reference_library(self.library_dir)
        self.reference_library.clear()
        self.reference_library.update(fresh)
        self._populate_combo()

    def _on_new_standard(self):
        name, ok = QInputDialog.getText(self, "Add standard", "Standard name (matches raw filename label):")
        if not ok or not name.strip():
            return
        name = name.strip()
        template_path = self.library_dir / "_template.yaml"
        template = reflib.load_reference_material(template_path)
        material = reflib.ReferenceMaterial(
            standard=name, description=template.description, source=template.source,
            analytes=template.analytes, isotope_ratios=template.isotope_ratios,
        )
        reflib.save_reference_material(material, self.library_dir / f"{name}.yaml")
        self.reference_library[name] = material
        self._populate_combo(select=name)

    def _on_save(self):
        if self.material is None:
            return
        analytes = {}
        for i in range(self.table.rowCount()):
            name = self.table.item(i, 0).text().strip()
            element = self.table.item(i, 1).text().strip()
            mass_text = self.table.item(i, 2).text().strip()
            value_text = self.table.item(i, 3).text().strip()
            uncertainty_text = self.table.item(i, 4).text().strip()
            uncertainty_type = self.table.item(i, 5).text().strip() or "1SD"
            units = self.table.item(i, 6).text().strip() or "ppm"
            source = self.table.item(i, 7).text().strip()
            try:
                analytes[name] = reflib._parse_analyte(name, {
                    "element": element, "mass": int(mass_text),
                    "value": float(value_text) if value_text else None,
                    "uncertainty": float(uncertainty_text) if uncertainty_text else None,
                    "uncertainty_type": uncertainty_type, "units": units, "source": source,
                })
            except (ValueError, reflib.ReferenceLibraryError) as e:
                QMessageBox.warning(self, "Edit standard", f"Analyte row {i + 1} ({name or '(blank)'}): {e}")
                return

        isotope_ratios = {}
        for i in range(self.tableRatios.rowCount()):
            numerator = self.tableRatios.item(i, 0).text().strip()
            denominator = self.tableRatios.item(i, 1).text().strip()
            value_text = self.tableRatios.item(i, 2).text().strip()
            uncertainty_text = self.tableRatios.item(i, 3).text().strip()
            uncertainty_type = self.tableRatios.item(i, 4).text().strip() or None
            source = self.tableRatios.item(i, 5).text().strip()
            name = f"{numerator}/{denominator}"
            try:
                num_parsed = reflib.parse_analyte_name(numerator)
                den_parsed = reflib.parse_analyte_name(denominator)
                if num_parsed is None or den_parsed is None:
                    raise reflib.ReferenceLibraryError(
                        f"numerator/denominator must look like 'Pb206' -- got {numerator!r}/{denominator!r}."
                    )
                numerator_element, numerator_mass = num_parsed
                denominator_element, denominator_mass = den_parsed
                isotope_ratios[name] = reflib._parse_isotope_ratio(name, {
                    "numerator_element": numerator_element, "numerator_mass": numerator_mass,
                    "denominator_element": denominator_element, "denominator_mass": denominator_mass,
                    "value": float(value_text) if value_text else None,
                    "uncertainty": float(uncertainty_text) if uncertainty_text else None,
                    "uncertainty_type": uncertainty_type, "source": source,
                })
            except (ValueError, reflib.ReferenceLibraryError) as e:
                QMessageBox.warning(self, "Edit standard", f"Ratio row {i + 1} ({name}): {e}")
                return

        material = reflib.ReferenceMaterial(
            standard=self.material.standard, description=self.material.description,
            source=self.material.source, analytes=analytes, isotope_ratios=isotope_ratios,
        )
        save_path = self.library_dir / f"{material.standard}.yaml"
        reflib.save_reference_material(material, save_path)
        self.reference_library[material.standard] = material
        self.material = material
        QMessageBox.information(self, "Edit standard", f"Saved {save_path}.")


class CalibrationMainWindow(QMainWindow):
    """Standalone calibration GUI: raw-data scanning, background/drift/standard
    settings, reference-library editing, instrument-geometry entry, run
    controls, export, and diagnostic viewer tabs.

    Not registered into LaME's ``MainWindow`` -- deliberately independent per
    the "standalone for now" requirement.
    """

    # Tab indices, matching the add order in _build_results_tabs -- shared
    # between _refresh_active_tab (which plot to redraw) and
    # _update_plot_controls_visibility (which shared controls apply).
    TAB_TIMING = 0
    TAB_TIME_SERIES = 1
    TAB_BACKGROUND = 2
    TAB_STANDARDS = 3
    TAB_CALIBRATION_CURVE = 4
    TAB_ISOTOPE_RATIOS = 5
    TAB_MAPS = 6
    TAB_DATA = 7
    TAB_DECONVOLUTION = 8
    TAB_CLASSIFICATION = 9

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LA-ICP-MS Calibration")
        self.resize(1400, 900)

        self._data_dir: Path | None = None
        self._batch_sample_dirs: list[Path] = []
        # Analytes whose tableWashoutTau cell was last written by
        # _fill_washout_tau_from_fits (Kernel estimation's "Fit" button),
        # not typed by the user -- lets a later Fit click refresh its own
        # earlier output without ever overwriting a hand-typed value (see
        # _on_washout_tau_item_changed, which discards an analyte from this
        # set the moment the user edits that cell).
        self._auto_filled_tau: set[str] = set()
        # tableStandardLabels' Primary/Secondary checkbox and Reference
        # combo cell widgets, keyed by label -- source of truth for
        # _primary_standard_names/_secondary_standard_names/_reference_overrides.
        self._primary_checkboxes: dict[str, QCheckBox] = {}
        self._secondary_checkboxes: dict[str, QCheckBox] = {}
        self._bias_checkboxes: dict[str, QCheckBox] = {}
        self._reference_combos: dict[str, QComboBox] = {}
        # Isotope Calibration table state (see _populate_isotope_calibration_table) --
        # element -> its Mode combobox, element -> its "El total" pooling
        # checkbox, and element -> the sorted list of measured isotope
        # masses backing that row, all keyed the same way so
        # _gather_isotope_specs/_gather_pool_specs can walk them together.
        self._isotope_mode_combos: dict[str, QComboBox] = {}
        self._isotope_pool_checkboxes: dict[str, QCheckBox] = {}
        self._isotope_element_masses: dict[str, list[int]] = {}
        # Radiometric dating ratios table state (see
        # _populate_dating_systems_table) -- system name (e.g. "Pb-Pb",
        # "U-Pb", "Th-Pb") -> its single Enable checkbox, read at Run time
        # by _gather_dating_ratio_specs.
        self._dating_system_checkboxes: dict[str, QCheckBox] = {}
        self.reference_library: dict[str, reflib.ReferenceMaterial] = {}
        # Mineral composition library for Classification (src/classification/,
        # webmineral_compositions.csv) -- distinct from reference_library
        # above (that's calibration standards' certified concentrations, an
        # unrelated concept that happens to share the word "reference").
        try:
            self.mineral_references = load_reference_library()
            self._mineral_library_error = None
        except ReferenceLibraryError as e:
            self.mineral_references = []
            self._mineral_library_error = str(e)
        self.results: dict[str, SampleCalibratedResult] = {}
        self._worker: _PipelineWorker | None = None
        # Eagerly parsed at Scan time (before any pipeline Run) so the Time
        # Series tab can preview raw lines while the user is still deciding
        # what background/edge-trim overrides to set -- keyed by filename.
        self._scanned_files: dict[str, LineFileData] = {}
        # Per-file state backing tableTimeSeriesFiles's View/Use columns --
        # keyed by filename, initialized (View=False, Use=True) the first
        # time a file is seen at Scan time and preserved across focus-combo
        # changes/re-scans of the same directory. View drives which lines
        # plot on the Time Series tab (purely a display filter); Use drives
        # which files are excluded from the next pipeline Run entirely (see
        # pipeline.run's excluded_files).
        self._file_view_state: dict[str, bool] = {}
        self._file_use_state: dict[str, bool] = {}
        # Point-index DataFrames from the last redraw of each canvas (see
        # diagnostics.plot_time_series/plot_standard_vs_reference's return
        # values) -- used by the click/drag point-masking wiring below to
        # hit-test against drawn points without recomputing pixel
        # positions itself.
        self._time_series_point_index: pd.DataFrame | None = None
        self._standards_point_index: pd.DataFrame | None = None
        # Manual click/drag point-exclusion state (see the "Point masking"
        # section below), separate from the automatic outlier screens so a
        # user's choice isn't silently overwritten by re-detection on the
        # next Run -- both keyed by filename, then further keyed per
        # analyte since spikes/anomalies don't correlate across analytes
        # (confirmed earlier this session for the automatic screens; the
        # user explicitly wants manual masking scoped the same way).
        # Time Series: filename -> analyte -> set of absolute row indices
        # (a single measurement). Standards QC: filename -> set of
        # analytes (a whole occurrence, for that analyte only).
        self._manual_row_exclusions: dict[str, dict[str, set[int]]] = {}
        self._manual_occurrence_exclusions: dict[str, set[str]] = {}
        # Drag-vs-click disambiguation state for _on_canvas_press/_motion/
        # _release (pixel-space start point + which canvas/axes is active).
        self._drag_canvas = None
        self._drag_start_px: tuple[float, float] | None = None
        self._drag_start_data: tuple[float, float] | None = None
        self._drag_axes = None
        self._drag_rect_artist = None

        self._reload_reference_library()
        self._setup_ui()
        self._connect_widgets()
        self._refresh_mineral_preview()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _setup_ui(self):
        self.addToolBar(self._build_toolbar())

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMaximumWidth(420)
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(3, 3, 3, 3)

        left_layout.addWidget(self._build_input_data_toolbox())
        left_scroll.setWidget(left_container)
        splitter.addWidget(left_scroll)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        splitter.addWidget(right_container)

        sample_layout = QHBoxLayout()

        # list of samples
        sample_layout.addWidget(QLabel("Viewing"))
        self.comboBoxSampleResult = QComboBox()
        sample_layout.addWidget(self.comboBoxSampleResult, stretch=1)

        # list of analytes
        sample_layout.addWidget(QLabel("Analyte"))
        self.analyte_list = SpinComboBox()
        self.analyte_list.spin_box.setFixedWidth(60)
        self.analyte_list.spin_box.setToolTip("Step through analytes")
        sample_layout.addWidget(self.analyte_list, stretch=1)

        # list of standards
        sample_layout.addWidget(QLabel("Standard"))
        self.comboStandardLabel = QComboBox()
        sample_layout.addWidget(self.comboStandardLabel)

        right_layout.addLayout(sample_layout)
        right_layout.addLayout(self._build_plot_controls_row())

        right_layout.addWidget(self._build_results_tabs())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([420, 980])

        self.setCentralWidget(splitter)

        self.setStatusBar(self._build_status_bar())

    def _build_plot_controls_row(self) -> QHBoxLayout:
        """Shared row of per-plot controls, above the tab widget instead of
        duplicated inside each tab: the Stage combobox (Maps only), Offset
        lines checkbox (Time Series only), and a single Log scale checkbox
        shared by Maps and Time Series. ``_update_plot_controls_visibility``
        shows/hides each control to match the active tab; a fixed-height
        spacer keeps the row's height constant even when every control in
        it is hidden (Timing/Background/Standards/Data tabs), so the tab
        widget below doesn't jump up and down as the user switches tabs.
        """
        row = QHBoxLayout()

        self.labelMapStage = QLabel("Stage")
        row.addWidget(self.labelMapStage)
        self.comboMapStage = QComboBox()
        self.comboMapStage.addItems(["raw", "background+drift correction", "deconvolution correction", "calibrated"])
        self.comboMapStage.setCurrentText("calibrated")
        row.addWidget(self.comboMapStage)

        self.checkOffsetLines = QCheckBox("Offset lines")
        row.addWidget(self.checkOffsetLines)

        self.checkLogScale = QCheckBox("Log scale")
        row.addWidget(self.checkLogScale)

        self.checkEditMode = QCheckBox("Edit mode")
        self.checkEditMode.setToolTip(
            "Arms click/drag point masking on this plot -- single click toggles one point, "
            "click-and-drag toggles every point in the rectangle. Off by default so zooming/"
            "panning never accidentally masks a point."
        )
        row.addWidget(self.checkEditMode)

        self.checkHideMaskedPoints = QCheckBox("Hide masked points")
        self.checkHideMaskedPoints.setToolTip(
            "Masked points are shown in light gray by default; check this to omit them from "
            "the plot entirely instead (they're still masked -- this only changes the display, "
            "and a hidden point can still be clicked at its usual location to un-mask it)."
        )
        row.addWidget(self.checkHideMaskedPoints)

        row.addStretch(1)

        row_height = max(
            self.labelMapStage.sizeHint().height(), self.comboMapStage.sizeHint().height(),
            self.checkOffsetLines.sizeHint().height(), self.checkLogScale.sizeHint().height(),
            self.checkEditMode.sizeHint().height(), self.checkHideMaskedPoints.sizeHint().height(),
        )
        row.addSpacerItem(QSpacerItem(0, row_height, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        return row

    def _update_plot_controls_visibility(self):
        index = self.tabs.currentIndex()
        is_maps = index == self.TAB_MAPS
        is_time_series = index == self.TAB_TIME_SERIES
        is_standards = index == self.TAB_STANDARDS
        is_isotope_ratios = index == self.TAB_ISOTOPE_RATIOS
        is_maskable = is_time_series or is_standards
        self.labelMapStage.setVisible(is_maps)
        self.comboMapStage.setVisible(is_maps)
        self.checkOffsetLines.setVisible(is_time_series)
        self.checkLogScale.setVisible(is_maps or is_time_series or is_isotope_ratios)
        self.checkEditMode.setVisible(is_maskable)
        self.checkHideMaskedPoints.setVisible(is_maskable)

    def _build_status_bar(self) -> QStatusBar:
        statusbar = QStatusBar(self)

        self.labelRunStatus = QLabel("")
        self.labelRunStatus.setWordWrap(True)
        statusbar.addWidget(self.labelRunStatus, stretch=1)

        return statusbar

    def _build_toolbar(self) -> QToolBar:
        toolbar = QToolBar("Calibration", self)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon) 

        self.actionRun = CustomAction(text="Run", light_icon_unchecked="icon-run-64.svg", parent=self)
        self.actionRun.setToolTip("Run pipeline")

        self.actionReprocess = CustomAction(text="Reprocess", light_icon_unchecked="icon-run-64.svg", parent=self)
        self.actionReprocess.setToolTip(
            "Fast re-run from already-scanned files (re-applies deconvolution/calibration "
            "settings without re-parsing raw files from disk). Single-folder mode only."
        )

        self.actionClassify = CustomAction(text="Classify", light_icon_unchecked="icon-run-64.svg", parent=self)
        self.actionClassify.setToolTip("Classify the current sample's calibrated pixels against the selected reference minerals.")

        self.actionExportCsv = CustomAction(text="Save Data", light_icon_unchecked="icon-save-file-64.svg", parent=self)
        self.actionExportCsv.setToolTip("Save calibrated CSV...")

        self.actionExportJson = CustomAction(text="Save QC Report", light_icon_unchecked="icon-save-notes-64.svg", icon_text="Save\nReport", parent=self)
        self.actionExportJson.setToolTip("Save QC report (JSON)...")

        self.actionOpenRefLibrary = CustomAction(text="Standards", light_icon_unchecked="icon-add-list-64.svg", icon_text="Standards", parent=self)
        self.actionOpenRefLibrary.setToolTip("Open the reference library of standards to view, edit or add.")

        toolbar.addAction(self.actionRun)
        toolbar.addAction(self.actionReprocess)
        toolbar.addAction(self.actionClassify)
        toolbar.addSeparator()
        toolbar.addAction(self.actionExportCsv)
        toolbar.addAction(self.actionExportJson)
        toolbar.addSeparator()
        toolbar.addAction(self.actionOpenRefLibrary)

        return toolbar

    def _build_input_data_toolbox(self) -> QToolBox:
        """Groups the left-panel controls onto five QToolBox pages so the user
        scrolls through one at a time instead of stacking every group box:
        "Input Data" (data source / standard configuration / instrument
        settings), "Analyte Settings" (isotope calibration / dating ratios),
        "Calibration Settings" (drift/calibration and background/edge-trim
        overrides), "Deconvolution" (along-line shift/washout correction,
        src/deconvolution/), and "Classification" (cosine-distance mineral
        matching, src/classification/)."""
        toolbox = QToolBox()
        # Matches the spacing set on the app's other two production
        # QToolBoxes (see MainWindow.py's control_dock/mask_dock toolboxes).
        toolbox.layout().setSpacing(2)

        input_page = QWidget()
        input_layout = QVBoxLayout(input_page)
        input_layout.setContentsMargins(3, 3, 3, 3)
        input_layout.addWidget(self._build_data_source_group())
        input_layout.addWidget(self._build_standards_group())
        input_layout.addWidget(self._build_instrument_settings_group())
        input_layout.addStretch(1)
        toolbox.addItem(input_page, "Input Data")

        analyte_page = QWidget()
        analyte_layout = QVBoxLayout(analyte_page)
        analyte_layout.setContentsMargins(3, 3, 3, 3)
        analyte_layout.addWidget(self._build_isotope_calibration_group())
        analyte_layout.addWidget(self._build_radiometric_dating_group())
        analyte_layout.addStretch(1)
        toolbox.addItem(analyte_page, "Analyte Settings")

        calibration_page = QWidget()
        calibration_layout = QVBoxLayout(calibration_page)
        calibration_layout.setContentsMargins(3, 3, 3, 3)
        calibration_layout.addWidget(self._build_drift_calibration_group())
        calibration_layout.addWidget(self._build_background_override_group())
        calibration_layout.addStretch(1)
        toolbox.addItem(calibration_page, "Calibration Settings")

        deconvolution_page = QWidget()
        deconvolution_layout = QVBoxLayout(deconvolution_page)
        deconvolution_layout.setContentsMargins(3, 3, 3, 3)
        deconvolution_layout.addWidget(self._build_deconvolution_group())
        toolbox.addItem(deconvolution_page, "Deconvolution")

        classification_page = QWidget()
        classification_layout = QVBoxLayout(classification_page)
        classification_layout.setContentsMargins(3, 3, 3, 3)
        classification_layout.addWidget(self._build_classification_group())
        toolbox.addItem(classification_page, "Classification")

        return toolbox

    def _build_data_source_group(self) -> QGroupBox:
        group = QGroupBox("Data source")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(3, 3, 3, 3)

        dir_row = QHBoxLayout()
        self.lineEditDataDir = QLineEdit()
        self.lineEditDataDir.setReadOnly(True)
        self.lineEditDataDir.setPlaceholderText("Raw data directory...")
        dir_row.addWidget(self.lineEditDataDir, stretch=1)
        self.buttonBrowseDir = QPushButton("Browse...")
        dir_row.addWidget(self.buttonBrowseDir)
        layout.addLayout(dir_row)

        self.checkBoxBatchMode = QCheckBox("Parent folder")
        layout.addWidget(self.checkBoxBatchMode)

        time_format_row = QHBoxLayout()
        time_format_row.addWidget(QLabel("Acquired time format"))
        self.lineEditTimeFormat = QLineEdit()
        self.lineEditTimeFormat.setPlaceholderText("Auto-detect (or e.g. %d/%m/%y %H:%M:%S)")
        self.lineEditTimeFormat.setToolTip(
            "Leave blank to auto-detect the header's 'Acquired : <timestamp>' line "
            "(handles both 2- and 4-digit years, day-first and month-first). Set this "
            "explicitly only if scanning reports a timestamp parse error -- enter a "
            "Python datetime.strptime pattern matching this instrument export's format."
        )
        time_format_row.addWidget(self.lineEditTimeFormat, stretch=1)
        layout.addLayout(time_format_row)

        self.buttonScan = QPushButton("Scan")
        layout.addWidget(self.buttonScan)

        self.listWidgetSampleFolders = QListWidget()
        self.listWidgetSampleFolders.setMaximumHeight(100)
        self.listWidgetSampleFolders.setVisible(False)
        layout.addWidget(self.listWidgetSampleFolders)

        self.labelScanSummary = QLabel("")
        self.labelScanSummary.setWordWrap(True)
        layout.addWidget(self.labelScanSummary)

        return group

    def _build_standards_group(self) -> QGroupBox:
        group = QGroupBox("Standard configuration")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(3, 3, 3, 3)
        self.tableStandardLabels = QTableWidget(0, 5)
        self.tableStandardLabels.setHorizontalHeaderLabels(["Primary", "Secondary", "Bias", "Label", "Reference"])
        self.tableStandardLabels.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tableStandardLabels)
        # note = QLabel(
        #     "One Primary standard -> single-point calibration. Two or more -> "
        #     "multi-point (linear) calibration across them. Secondary standards "
        #     "are still calibrated/reported for their own QC, just not applied to samples."
        # )
        # note.setWordWrap(True)
        # layout.addWidget(note)
        return group

    def _build_instrument_settings_group(self) -> QGroupBox:
        group = QGroupBox("Instrument settings")
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(3, 3, 3, 3)
        form_layout = QFormLayout()
        group_layout.addLayout(form_layout)

        self.lineEditInstrument = QLineEdit()
        self.lineEditInstrument.setPlaceholderText("(unset)")
        form_layout.addRow("Instrument", self.lineEditInstrument)

        self.spinSpotSize = QDoubleSpinBox()
        self.spinSpotSize.setRange(0, 1e6)
        self.spinSpotSize.setSpecialValueText("(unset)")
        form_layout.addRow("Spot size (µm)", self.spinSpotSize)

        self.spinSweep = QDoubleSpinBox()
        self.spinSweep.setRange(0, 1e6)
        self.spinSweep.setDecimals(4)
        self.spinSweep.setSpecialValueText("(unset)")
        form_layout.addRow("Sweep (s)", self.spinSweep)

        self.spinSpeed = QDoubleSpinBox()
        self.spinSpeed.setRange(0, 1e6)
        self.spinSpeed.setSpecialValueText("(unset)")
        form_layout.addRow("Speed (µm/s)", self.spinSpeed)

        self.spinDwellTime = QDoubleSpinBox()
        self.spinDwellTime.setRange(0, 1e5)
        self.spinDwellTime.setDecimals(3)
        self.spinDwellTime.setSpecialValueText("(unset)")
        self.spinDwellTime.setToolTip(
            "Per-analyte dwell time -- feeds counts.py's Poisson tau recovery and, "
            "combined with each analyte's position in the sweep read-out order, the "
            "Deconvolution page's dwell-offset shift correction (assumes uniform "
            "per-analyte dwell)."
        )
        form_layout.addRow("Dwell time (ms)", self.spinDwellTime)

        self.spinLaserWavelength = QDoubleSpinBox()
        self.spinLaserWavelength.setRange(0, 1e5)
        self.spinLaserWavelength.setSpecialValueText("(unset)")
        form_layout.addRow("Laser wavelength (nm)", self.spinLaserWavelength)

        self.spinFluence = QDoubleSpinBox()
        self.spinFluence.setRange(0, 1e4)
        self.spinFluence.setDecimals(3)
        self.spinFluence.setSpecialValueText("(unset)")
        form_layout.addRow("Fluence (J/cm²)", self.spinFluence)

        self.spinPulseRate = QDoubleSpinBox()
        self.spinPulseRate.setRange(0, 1e6)
        self.spinPulseRate.setSpecialValueText("(unset)")
        form_layout.addRow("Pulse rate (Hz)", self.spinPulseRate)

        xy_layout = QHBoxLayout()
        group_layout.addLayout(xy_layout)

        self.comboScanAxis = QComboBox()
        self.comboScanAxis.addItems(["Xc", "Yc"])
        xy_layout.addWidget(QLabel("Scan axis"))
        xy_layout.addWidget(self.comboScanAxis)
        xy_layout.addWidget(QLabel("Reverse:"))
        self.checkReverseX = QCheckBox("X")
        xy_layout.addWidget(self.checkReverseX)
        self.checkReverseY = QCheckBox("Y")
        xy_layout.addWidget(self.checkReverseY)
        self.checkBidirectionalScan = QCheckBox("Bidirectional scan")
        self.checkBidirectionalScan.setToolTip(
            "Alternate lines scanned in opposite directions -- the Deconvolution "
            "page's washout correction flips the causal tail's direction on odd "
            "lines when this is set, avoiding 'herringbone' artifacts."
        )
        xy_layout.addWidget(self.checkBidirectionalScan)

        notes_layout = QHBoxLayout()
        group_layout.addLayout(notes_layout)

        self.textNotes = QPlainTextEdit()
        self.textNotes.setPlaceholderText(
            "Other logbook fields, one 'key: value' per line "
            "(laser power, gas flow, operator, etc.)" )
        self.textNotes.setMaximumHeight(80)
        notes_layout.addWidget(QLabel("Notes"))
        notes_layout.addWidget(self.textNotes)

        return group

    def _build_drift_calibration_group(self) -> QGroupBox:
        group = QGroupBox("Drift && calibration")
        form_layout = QFormLayout(group)
        form_layout.setContentsMargins(3, 3, 3, 3)

        self.comboDriftMethod = QComboBox()
        self.comboDriftMethod.addItems(list(DRIFT_METHOD_LABELS))
        self.comboDriftMethod.setCurrentText("Auto (Poisson GLM+LRT)")
        form_layout.addRow("Standard drift method", self.comboDriftMethod)

        self.spinDriftOrder = QSpinBox()
        self.spinDriftOrder.setRange(0, 6)
        self.spinDriftOrder.setValue(3)
        form_layout.addRow("Drift: max/fixed order", self.spinDriftOrder)

        self.comboBackgroundDriftMethod = QComboBox()
        self.comboBackgroundDriftMethod.addItems(list(DRIFT_METHOD_LABELS))
        self.comboBackgroundDriftMethod.setCurrentText("Auto (Poisson GLM+LRT)")
        form_layout.addRow("Background drift method", self.comboBackgroundDriftMethod)

        self.checkSplitOddEven = QCheckBox("Std Split QC")
        form_layout.addRow("", self.checkSplitOddEven)

        self.checkDetrend = QCheckBox("Detrend (linear)")
        self.checkDetrend.setToolTip(
            "Post-hoc linear correction per standard/analyte, applied on top of the "
            "existing drift fit, when a standard's own accuracy-vs-time still shows "
            "a residual linear trend after background/drift correction."
        )
        form_layout.addRow("", self.checkDetrend)

        self.checkDespikeNoise = QCheckBox("Despike (noise filter)")
        self.checkDespikeNoise.setToolTip(
            "Rolling-window, Poisson-consistent spike filter (ported from latools), applied "
            "to every analyte of every file right after parsing, before background/ablation "
            "windowing -- replaces isolated single-sweep spikes/dropouts with the local "
            "rolling mean."
        )
        form_layout.addRow("", self.checkDespikeNoise)

        self.checkForceZeroIntercept = QCheckBox("Force zero intercept (multi-point)")
        self.checkForceZeroIntercept.setToolTip(
            "Only affects calibration with 2+ primary standards: fits the shared CPS-vs-ppm "
            "curve through the origin instead of a free intercept, removing extrapolation "
            "below the lowest calibration point as a source of negative values. Doesn't "
            "guarantee non-negative output on its own -- background-subtracted CPS can still "
            "be negative near the detection limit. A single primary standard is always a "
            "zero-intercept ratio regardless of this setting."
        )
        form_layout.addRow("", self.checkForceZeroIntercept)

        self.spinAccuracyThreshold = QDoubleSpinBox()
        self.spinAccuracyThreshold.setRange(0.1, 10.0)
        self.spinAccuracyThreshold.setValue(2.0)
        self.spinAccuracyThreshold.setSingleStep(0.1)
        form_layout.addRow("Accuracy threshold", self.spinAccuracyThreshold)

        return group

    def _build_isotope_calibration_group(self) -> QGroupBox:
        """One row per measured element with 2+ isotopes (populated at Scan
        time, see _populate_isotope_calibration_table), each with a 3-state
        Mode combobox read at Run time by _gather_isotope_specs. Elements
        with only one measured isotope are omitted -- there's nothing to
        apportion, only Mechanism A's elemental calibration (always on,
        unconditionally) applies to them."""
        group = QGroupBox("Isotope calibration")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(3, 3, 3, 3)

        note = QLabel(
            "Every isotope is always calibrated elementally (Mechanism A -- ratio-based "
            "calibration cancels natural abundance, see reflib.resolve_elemental_value). "
            "The Mode below additionally splits an element's total into per-isotope "
            "concentrations -- 'mass-bias corrected' needs a Bias-checked standard with a "
            "certified or natural-abundance ratio for that element (see the table above). "
            "'El total' adds a pooled '<element> total' channel combining every measured "
            "isotope's raw counts for better precision than any single isotope alone -- "
            "independent of Mode, and not valid for radiogenic isotope pairs."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.tableIsotopeCalibration = QTableWidget(0, 4)
        self.tableIsotopeCalibration.setHorizontalHeaderLabels(["Element", "Isotopes", "Mode", "El total"])
        self.tableIsotopeCalibration.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tableIsotopeCalibration)

        return group

    def _build_radiometric_dating_group(self) -> QGroupBox:
        """One row per radiometric dating system whose required isotopes
        are present among the analytes seen at Scan time (see
        _populate_dating_systems_table) -- Stage 1: Pb-Pb, U-Pb, Th-Pb
        only (Rb-Sr/Sm-Nd/Lu-Hf/Re-Os need isobaric-interference stripping
        this pass deliberately doesn't build). Each row is a single Enable
        checkbox, no Mode dropdown -- unlike the per-element table above,
        a cross-element parent/daughter pair has no elemental/natural-
        abundance fallback to choose between."""
        group = QGroupBox("Radiometric dating ratios")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(3, 3, 3, 3)

        note = QLabel(
            "Stage 1: Pb-Pb, U-Pb, Th-Pb (checking both U-Pb and Th-Pb together gives Th-U-Pb). "
            "Rb-Sr, Sm-Nd, Lu-Hf, Re-Os are not yet supported -- they need isobaric-interference "
            "correction not built here. Corrected via session-level standard bracketing against "
            "the checked standard(s)' certified ratio (Reference column above); reuses the same "
            "Bias-checked standards as the Isotope calibration table."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.tableRadiometricSystems = QTableWidget(0, 3)
        self.tableRadiometricSystems.setHorizontalHeaderLabels(["System", "Ratios", "Enable"])
        self.tableRadiometricSystems.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tableRadiometricSystems)

        return group

    def _build_background_override_group(self) -> QGroupBox:
        group = QGroupBox("Timing overrides (optional)")
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(3, 3, 3, 3)
        layout = QGridLayout()
        group_layout.addLayout(layout)

        self.checkBackgroundOverride = QCheckBox("Override gas-blank window")
        layout.addWidget(self.checkBackgroundOverride,0,0,1,4)

        self.spinOverrideStart = QDoubleSpinBox()
        self.spinOverrideStart.setRange(0, 1e4)
        self.spinOverrideStart.setDecimals(2)
        layout.addWidget(QLabel("Start (s)"),1,0)
        layout.addWidget(self.spinOverrideStart,1,1)

        self.spinOverrideEnd = QDoubleSpinBox()
        self.spinOverrideEnd.setRange(0, 1e4)
        self.spinOverrideEnd.setDecimals(2)
        self.spinOverrideEnd.setValue(10.0)
        layout.addWidget(QLabel("End (s)"),1,2)
        layout.addWidget(self.spinOverrideEnd,1,3)

        self.checkEdgeTrim = QCheckBox("Trim ablation edge effect")
        layout.addWidget(self.checkEdgeTrim,2,0,1,4)

        edge_trim_layout = QHBoxLayout()
        self.spinEdgeTrimLead = QDoubleSpinBox()
        self.spinEdgeTrimLead.setRange(0, 1e4)
        self.spinEdgeTrimLead.setDecimals(2)
        layout.addWidget(QLabel("Leading (s)"),3,0)
        layout.addWidget(self.spinEdgeTrimLead,3,1)

        self.spinEdgeTrimTrail = QDoubleSpinBox()
        self.spinEdgeTrimTrail.setRange(0, 1e4)
        self.spinEdgeTrimTrail.setDecimals(2)
        layout.addWidget(QLabel("Trailing (s)"),3,2)
        layout.addWidget(self.spinEdgeTrimTrail,3,3)

        label_onset_trim = QLabel("Ablation onset trim (s)")
        label_onset_trim.setToolTip(
            "Drops this many seconds of leading rows from every line's actual per-pixel data "
            "(background_corrected_signal/calibrated_ppm), before deconvolution and calibration -- "
            "not the same as 'Trim ablation edge effect' above, which only narrows the region used "
            "for a STANDARD's own calibration-factor statistics and never touches the displayed/"
            "exported/classified per-pixel data. Use this one to actually remove the aerosol-onset "
            "ramp (the first few pixels taking time to reach true sample values) from maps."
        )
        layout.addWidget(label_onset_trim, 4, 0, 1, 2)
        self.spinAblationOnsetTrim = QDoubleSpinBox()
        self.spinAblationOnsetTrim.setRange(0, 1e4)
        self.spinAblationOnsetTrim.setDecimals(2)
        self.spinAblationOnsetTrim.setToolTip(label_onset_trim.toolTip())
        layout.addWidget(self.spinAblationOnsetTrim, 4, 2, 1, 2)

        group_layout.addWidget(QLabel("Per-line overrides (optional; blank = use the settings above)"))
        self.tablePerLineOverrides = QTableWidget(0, 5)
        self.tablePerLineOverrides.setHorizontalHeaderLabels(
            ["File", "Bg start (s)", "Bg end (s)", "Edge lead (s)", "Edge trail (s)"]
        )
        self.tablePerLineOverrides.setMaximumHeight(150)
        group_layout.addWidget(self.tablePerLineOverrides)

        return group

    def _build_deconvolution_group(self) -> QGroupBox:
        """Along-line dwell-offset shift and washout-tailing correction
        (src/deconvolution/, Stages 0/1/3 of
        plans/laicpms_map_correction_spec.md). Both flags default off, so
        an existing Run is unaffected unless explicitly enabled here. Tau
        can be entered by hand in the table below, or fitted from real
        reference data via the Kernel estimation section (spec Stage 2,
        src/deconvolution/esf.py) -- an analyte with no tau (manual or
        fitted) simply isn't washout-corrected."""
        group = QGroupBox("Deconvolution")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(3, 3, 3, 3)

        note = QLabel(
            "Corrects along-line spot-mixing/smearing artifacts before standard "
            "calibration. Shift uses each analyte's position in the sweep read-out "
            "order (Instrument settings' Dwell time); washout needs a tau (s) per "
            "analyte below, either typed in or fitted from reference data (Kernel "
            "estimation, below). Both are off by default."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.checkBoxApplyShift = QCheckBox("Apply dwell-offset shift")
        layout.addWidget(self.checkBoxApplyShift)
        self.checkBoxApplyWashout = QCheckBox("Apply washout correction")
        layout.addWidget(self.checkBoxApplyWashout)

        self.tableWashoutTau = QTableWidget(0, 2)
        self.tableWashoutTau.setHorizontalHeaderLabels(["Analyte", "Tau (s)"])
        self.tableWashoutTau.horizontalHeader().setStretchLastSection(True)
        self.tableWashoutTau.setToolTip(
            "Populated with every measured analyte at Scan time. Leave Tau blank to "
            "skip washout correction for that analyte even when the checkbox above is on. "
            "Values in italic-free black were typed by hand or fitted; 'Fit' below only "
            "ever fills a blank cell or refreshes a value it fitted earlier -- it never "
            "overwrites a value you typed yourself."
        )
        self.tableWashoutTau.itemChanged.connect(self._on_washout_tau_item_changed)
        layout.addWidget(self.tableWashoutTau)

        layout.addWidget(self._build_kernel_estimation_group())

        return group

    def _build_kernel_estimation_group(self) -> QGroupBox:
        """Fits washout tau (and a validating edge-spread tau) from real
        reference data already in the scanned session (spec Sec 6.1 routes
        a/b, src/deconvolution/esf.py) -- Pulse rows fit every analyte's
        decay (single- vs double-exponential, AIC/BIC-gated) and feed
        tableWashoutTau; Edge rows fit one representative analyte (the
        highest-signal one in the window) to the analytic EMG curve and,
        when at least one Pulse row was also fitted, cross-check its tau
        against the pulse fit (the "closure check", spec's mandatory
        Sec 6.1 test). Route (c), in-situ estimation, needs the
        classification/unmixing stage (not built yet) and isn't offered
        here.
        """
        group = QGroupBox("Kernel estimation")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(3, 3, 3, 3)

        note = QLabel(
            "Designate a time window in an already-scanned file as either an isolated "
            "single-pulse decay (Pulse) or a sharp material-couple edge (Edge), then Fit. "
            "Pulse rows estimate washout tau per analyte and fill the table above; Edge "
            "rows validate that tau against an independent edge-spread fit."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.tableKernelReferences = QTableWidget(0, 4)
        self.tableKernelReferences.setHorizontalHeaderLabels(["File", "Start (s)", "End (s)", "Kind"])
        self.tableKernelReferences.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.tableKernelReferences)

        row_buttons = QHBoxLayout()
        button_add_reference = QPushButton("Add row")
        button_add_reference.clicked.connect(self._on_add_kernel_reference_row)
        row_buttons.addWidget(button_add_reference)
        button_remove_reference = QPushButton("Delete selected row")
        button_remove_reference.clicked.connect(self._on_delete_selected_kernel_reference_row)
        row_buttons.addWidget(button_remove_reference)
        row_buttons.addStretch(1)
        layout.addLayout(row_buttons)

        self.buttonFitKernels = QPushButton("Fit")
        self.buttonFitKernels.clicked.connect(self._on_fit_kernels)
        layout.addWidget(self.buttonFitKernels)

        self.textKernelFitReport = QPlainTextEdit()
        self.textKernelFitReport.setReadOnly(True)
        self.textKernelFitReport.setMaximumHeight(150)
        layout.addWidget(self.textKernelFitReport)

        return group

    def _on_add_kernel_reference_row(self):
        row = self.tableKernelReferences.rowCount()
        self.tableKernelReferences.insertRow(row)
        file_combo = QComboBox()
        file_combo.addItems(sorted(self._scanned_files))
        self.tableKernelReferences.setCellWidget(row, 0, file_combo)
        self.tableKernelReferences.setItem(row, 1, QTableWidgetItem("0.0"))
        self.tableKernelReferences.setItem(row, 2, QTableWidgetItem("1.0"))
        kind_combo = QComboBox()
        kind_combo.addItems(["Pulse", "Edge"])
        self.tableKernelReferences.setCellWidget(row, 3, kind_combo)

    def _on_delete_selected_kernel_reference_row(self):
        rows = sorted({idx.row() for idx in self.tableKernelReferences.selectedIndexes()}, reverse=True)
        for row in rows:
            self.tableKernelReferences.removeRow(row)

    def _on_washout_tau_item_changed(self, item: QTableWidgetItem):
        """A cell edit (by the user -- programmatic fills below block
        signals first) means that analyte's tau is no longer "just
        something Fit filled in" -- drop it from _auto_filled_tau so a
        later Fit click won't silently overwrite what the user just typed.
        """
        if item.column() != 1:
            return
        analyte_item = self.tableWashoutTau.item(item.row(), 0)
        if analyte_item is not None:
            self._auto_filled_tau.discard(analyte_item.text())

    def _on_fit_kernels(self):
        report_lines = []
        pulse_fits_by_analyte: dict[str, "esf.SinglePulseFit"] = {}
        edge_fits: list["esf.EdgeSpreadFit"] = []

        for row in range(self.tableKernelReferences.rowCount()):
            file_combo = self.tableKernelReferences.cellWidget(row, 0)
            kind_combo = self.tableKernelReferences.cellWidget(row, 3)
            start_item = self.tableKernelReferences.item(row, 1)
            end_item = self.tableKernelReferences.item(row, 2)
            if file_combo is None or kind_combo is None or start_item is None or end_item is None:
                continue
            filename = file_combo.currentText()
            line_data = self._scanned_files.get(filename)
            if line_data is None:
                report_lines.append(f"Row {row + 1}: file {filename!r} not found (re-scan?) -- skipped.")
                continue
            try:
                start_s, end_s = float(start_item.text()), float(end_item.text())
            except ValueError:
                report_lines.append(f"Row {row + 1}: Start/End must be numeric -- skipped.")
                continue
            mask = (line_data.time_s >= start_s) & (line_data.time_s <= end_s)
            if mask.sum() < 6:
                report_lines.append(f"Row {row + 1} ({filename}): fewer than 6 points in [{start_s}, {end_s}]s -- skipped.")
                continue
            window_time = line_data.time_s[mask] - line_data.time_s[mask][0]
            window_signal = line_data.signal.loc[mask]

            if kind_combo.currentText() == "Pulse":
                fits = esf.fit_single_pulse_decay_per_analyte(window_time, window_signal, model="auto")
                pulse_fits_by_analyte.update(fits)
                report_lines.append(f"Row {row + 1} ({filename}, Pulse): fitted {len(fits)} analyte(s).")
            else:
                analyte = window_signal.mean().idxmax()
                try:
                    fit = esf.fit_edge_spread(window_time, window_signal[analyte].to_numpy())
                    edge_fits.append(fit)
                    report_lines.append(
                        f"Row {row + 1} ({filename}, Edge, analyte {analyte}): "
                        f"tau={fit.tau_s:.3g}s sigma={fit.sigma_s:.3g}s R2={fit.r_squared:.3f}"
                    )
                except ValueError as e:
                    report_lines.append(f"Row {row + 1} ({filename}, Edge): {e}")

        if pulse_fits_by_analyte:
            outlier_flags = esf.flag_tau_outliers(pulse_fits_by_analyte)
            report_lines.append("")
            report_lines.append("Per-analyte pulse fits:")
            for analyte, fit in sorted(pulse_fits_by_analyte.items()):
                flag = " [OUTLIER]" if outlier_flags.get(analyte) else ""
                status = "" if fit.success else " [fit did not converge]"
                report_lines.append(
                    f"  {analyte}: model={fit.model} tau={fit.tau_s:.3g}s R2={fit.r_squared:.3f}{flag}{status}"
                )
            self._fill_washout_tau_from_fits(
                {a: f.tau_s for a, f in pulse_fits_by_analyte.items() if f.success and not outlier_flags.get(a)}
            )

        if edge_fits and pulse_fits_by_analyte:
            median_pulse_tau = float(np.median([f.tau_s for f in pulse_fits_by_analyte.values() if f.success]))
            report_lines.append("")
            report_lines.append("Closure check (edge tau vs. median pulse tau):")
            for fit in edge_fits:
                reference = SinglePulseFit(model="single", tau_s=median_pulse_tau, amplitude=0.0, baseline=0.0, success=True)
                closure = esf.check_closure(reference, fit)
                verdict = "PASS" if closure.within_tolerance else "FAIL"
                report_lines.append(
                    f"  edge tau={closure.edge_tau_s:.3g}s vs pulse tau={closure.pulse_tau_s:.3g}s "
                    f"(rel. diff {closure.relative_difference:.1%}) -- {verdict}"
                )

        self.textKernelFitReport.setPlainText("\n".join(report_lines) if report_lines else "No reference rows to fit.")

    def _fill_washout_tau_from_fits(self, tau_by_analyte: dict[str, float]):
        """Only overwrites a tableWashoutTau cell that's blank or was
        previously filled by this same mechanism (_auto_filled_tau) -- a
        value the user typed by hand is never touched (see
        _on_washout_tau_item_changed)."""
        self.tableWashoutTau.blockSignals(True)
        for row in range(self.tableWashoutTau.rowCount()):
            analyte_item = self.tableWashoutTau.item(row, 0)
            tau_item = self.tableWashoutTau.item(row, 1)
            if analyte_item is None or tau_item is None:
                continue
            analyte = analyte_item.text()
            if analyte not in tau_by_analyte:
                continue
            if tau_item.text().strip() and analyte not in self._auto_filled_tau:
                continue
            tau_item.setText(f"{tau_by_analyte[analyte]:.4g}")
            self._auto_filled_tau.add(analyte)
        self.tableWashoutTau.blockSignals(False)

    def _populate_washout_tau_table(self):
        """(Re)builds tableWashoutTau from the analytes seen at Scan time --
        same "populated at Scan time" pattern as
        _populate_isotope_calibration_table, but one row per analyte (no
        element grouping, since washout tau is a per-analyte/per-isotope
        physical property, not something isotopes of one element share).
        Existing Tau entries are preserved across a re-scan (e.g. after
        adding more files under the same labels) rather than wiped.
        """
        existing_tau = {}
        for row in range(self.tableWashoutTau.rowCount()):
            analyte_item = self.tableWashoutTau.item(row, 0)
            tau_item = self.tableWashoutTau.item(row, 1)
            if analyte_item is not None and tau_item is not None and tau_item.text().strip():
                existing_tau[analyte_item.text()] = tau_item.text()

        self.tableWashoutTau.blockSignals(True)
        self.tableWashoutTau.setRowCount(0)
        analytes = sorted(next(iter(self._scanned_files.values())).analytes) if self._scanned_files else []
        for analyte in analytes:
            row = self.tableWashoutTau.rowCount()
            self.tableWashoutTau.insertRow(row)
            analyte_item = QTableWidgetItem(analyte)
            analyte_item.setFlags(analyte_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tableWashoutTau.setItem(row, 0, analyte_item)
            self.tableWashoutTau.setItem(row, 1, QTableWidgetItem(existing_tau.get(analyte, "")))
        self.tableWashoutTau.blockSignals(False)

    def _current_deconvolution_settings(self) -> DeconvolutionSettings:
        washout_tau_s = {}
        for row in range(self.tableWashoutTau.rowCount()):
            analyte_item = self.tableWashoutTau.item(row, 0)
            tau_item = self.tableWashoutTau.item(row, 1)
            if analyte_item is None or tau_item is None:
                continue
            text = tau_item.text().strip()
            if not text:
                continue
            try:
                tau = float(text)
            except ValueError:
                continue
            if tau > 0:
                washout_tau_s[analyte_item.text()] = tau

        return DeconvolutionSettings(
            apply_shift=self.checkBoxApplyShift.isChecked(),
            apply_washout=self.checkBoxApplyWashout.isChecked(),
            washout_tau_s=washout_tau_s,
        )

    def _build_classification_group(self) -> QGroupBox:
        """Mineral classification by cosine-distance matching
        (src/classification/, design spec
        plans/mineral_classification_calibration_spec.md Sec 3) against
        ``calibrated_ppm`` -- unlike Deconvolution (a per-line correction
        threaded into the Run pipeline itself), classification runs
        on-demand, after a Run has already produced calibrated data, via
        its own Classify button -- there's nothing to correct upstream of
        it, and re-classifying with a different threshold/mineral subset
        shouldn't require re-running background/drift/standards from
        scratch.
        """
        group = QGroupBox("Classification")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(3, 3, 3, 3)

        self.labelMineralLibraryStatus = QLabel(
            f"{len(self.mineral_references)} minerals loaded from webmineral_compositions.csv"
            if not self._mineral_library_error else f"Reference library failed to load: {self._mineral_library_error}"
        )
        self.labelMineralLibraryStatus.setWordWrap(True)
        if self._mineral_library_error:
            self.labelMineralLibraryStatus.setStyleSheet("color: red;")
        layout.addWidget(self.labelMineralLibraryStatus)

        note = QLabel(
            "Cosine-similarity match against the selected reference minerals' element "
            "composition, restricted to whichever analytes this sample and a given "
            "reference both report. Pixels below the match threshold are left "
            "unclassified rather than forced to their best (poor) match."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.sliderMatchThreshold = CustomSlider(
            min_value=0.0, max_value=1.0, step=0.01, initial_value=0.95,
            precision=2, fixed_point=True, orientation="horizontal", label_position="low",
        )
        self.sliderMatchThreshold.setToolTip("Minimum cosine similarity (tau_min) for a pixel to be assigned a mineral.")
        layout.addWidget(QLabel("Match threshold"))
        layout.addWidget(self.sliderMatchThreshold)

        self.sliderAmbiguityGap = CustomSlider(
            min_value=0.0, max_value=0.5, step=0.005, initial_value=0.02,
            precision=3, fixed_point=True, orientation="horizontal", label_position="low",
        )
        self.sliderAmbiguityGap.setToolTip(
            "Minimum gap (g_min) between the best cross-group match and the runner-up "
            "for a pixel to be considered confidently, not ambiguously, classified."
        )
        layout.addWidget(QLabel("Ambiguity gap"))
        layout.addWidget(self.sliderAmbiguityGap)

        layout.addWidget(QLabel("Reference minerals"))
        self.comboMineralClassFilter = QComboBox()
        self.comboMineralClassFilter.addItem("All")
        self.comboMineralClassFilter.addItems(
            sorted({r.mineral_class for r in self.mineral_references if r.mineral_class})
        )
        self.comboMineralClassFilter.setToolTip(
            "Filter the list below to one broad mineral class (e.g. Carbonate, Feldspar) -- "
            "combines with the text search below it. Does not affect which minerals are checked."
        )
        layout.addWidget(self.comboMineralClassFilter)
        self.listMinerals = QListWidget()
        self.filterMinerals = ListFilterWidget(self.listMinerals, placeholder="Search minerals...")
        layout.addWidget(self.filterMinerals)
        layout.addWidget(self.listMinerals)
        self._populate_mineral_list()

        select_row = QHBoxLayout()
        self.buttonSelectAllMinerals = QPushButton("Select All")
        self.buttonSelectAllMinerals.clicked.connect(lambda: self._set_all_minerals_checked(True))
        select_row.addWidget(self.buttonSelectAllMinerals)
        self.buttonSelectNoneMinerals = QPushButton("Select None")
        self.buttonSelectNoneMinerals.clicked.connect(lambda: self._set_all_minerals_checked(False))
        select_row.addWidget(self.buttonSelectNoneMinerals)
        select_row.addStretch(1)
        layout.addLayout(select_row)

        preset_row = QHBoxLayout()
        self.buttonSavePreset = QPushButton("Save Preset...")
        self.buttonSavePreset.setToolTip("Save the currently checked minerals as a named, reusable subset.")
        self.buttonSavePreset.clicked.connect(self._on_save_mineral_preset)
        preset_row.addWidget(self.buttonSavePreset)
        self.comboMineralPresets = QComboBox()
        self._populate_mineral_preset_combo()
        preset_row.addWidget(self.comboMineralPresets, stretch=1)
        self.buttonLoadPreset = QPushButton("Load")
        self.buttonLoadPreset.clicked.connect(self._on_load_mineral_preset)
        preset_row.addWidget(self.buttonLoadPreset)
        layout.addLayout(preset_row)

        self.buttonClassify = QPushButton("Classify")
        self.buttonClassify.clicked.connect(self._on_classify)
        layout.addWidget(self.buttonClassify)

        # Connected after the list/combo above are fully populated, so the
        # initial population doesn't spuriously trigger a filter/preview
        # refresh before the rest of the group (e.g. self.tableClassification-
        # Summary, built later in _build_results_tabs) even exists yet.
        self.filterMinerals.filterChanged.connect(self._apply_mineral_filters)
        self.comboMineralClassFilter.currentTextChanged.connect(self._apply_mineral_filters)
        self.listMinerals.itemChanged.connect(self._refresh_mineral_preview)

        return group

    def _populate_mineral_list(self):
        self.listMinerals.clear()
        for ref in sorted(self.mineral_references, key=lambda r: r.mineral_name):
            item = QListWidgetItem(ref.mineral_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.listMinerals.addItem(item)

    def _set_all_minerals_checked(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(self.listMinerals.count()):
            self.listMinerals.item(i).setCheckState(state)

    def _selected_mineral_references(self) -> list[MineralReference]:
        checked_names = {
            self.listMinerals.item(i).text()
            for i in range(self.listMinerals.count())
            if self.listMinerals.item(i).checkState() == Qt.CheckState.Checked
        }
        return [r for r in self.mineral_references if r.mineral_name in checked_names]

    def _apply_mineral_filters(self, *_args):
        """Combines (ANDs) the class-filter combo with the text search --
        neither ListFilterWidget's own text-only hiding nor a class-only
        pass is sufficient alone, so this recomputes visibility for both
        conditions together on every change to either one."""
        query = self.filterMinerals.filter_text().strip().lower()
        selected_class = self.comboMineralClassFilter.currentText()
        class_by_name = {r.mineral_name: r.mineral_class for r in self.mineral_references}
        for i in range(self.listMinerals.count()):
            item = self.listMinerals.item(i)
            name = item.text()
            matches_text = not query or query in name.lower()
            matches_class = selected_class == "All" or class_by_name.get(name) == selected_class
            item.setHidden(not (matches_text and matches_class))
        self._refresh_mineral_preview()

    def _refresh_mineral_preview(self, *_args):
        """Live preview: shows the currently checked mineral names in
        tableClassificationSummary with blank score/gap columns, even
        before Classify has ever been run -- _on_classify overwrites this
        with the real per-pixel stats once it runs."""
        if not hasattr(self, "tableClassificationSummary"):
            return
        selected_refs = self._selected_mineral_references()
        preview = pd.DataFrame({
            "mineral": sorted(r.mineral_name for r in selected_refs),
        })
        preview["pixel_count"] = ""
        preview["mean_score"] = ""
        preview["mean_gap"] = ""
        preview["n_ambiguous"] = ""
        _populate_table(self.tableClassificationSummary, preview)

    def _populate_mineral_preset_combo(self, select: str | None = None):
        self.comboMineralPresets.blockSignals(True)
        self.comboMineralPresets.clear()
        presets = load_presets(DEFAULT_PRESETS_PATH)
        self.comboMineralPresets.addItems(sorted(presets))
        if select is not None:
            idx = self.comboMineralPresets.findText(select)
            if idx >= 0:
                self.comboMineralPresets.setCurrentIndex(idx)
        self.comboMineralPresets.blockSignals(False)

    def _on_save_mineral_preset(self):
        selected_refs = self._selected_mineral_references()
        if not selected_refs:
            QMessageBox.warning(self, "Save Preset", "No reference minerals selected.")
            return
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        save_preset(DEFAULT_PRESETS_PATH, name, sorted(r.mineral_name for r in selected_refs))
        self._populate_mineral_preset_combo(select=name)

    def _on_load_mineral_preset(self):
        name = self.comboMineralPresets.currentText()
        if not name:
            QMessageBox.warning(self, "Load Preset", "No saved presets yet.")
            return
        names = set(load_presets(DEFAULT_PRESETS_PATH).get(name, []))
        if not names:
            QMessageBox.warning(self, "Load Preset", f"Preset '{name}' is empty or no longer exists.")
            return
        for i in range(self.listMinerals.count()):
            item = self.listMinerals.item(i)
            item.setCheckState(Qt.CheckState.Checked if item.text() in names else Qt.CheckState.Unchecked)

    def _on_classify(self):
        result = self._current_result()
        if result is None:
            QMessageBox.warning(self.ui if hasattr(self, "ui") else self, "Classify", "Run the pipeline first.")
            return
        if not self.mineral_references:
            QMessageBox.warning(self, "Classify", f"Reference library failed to load: {self._mineral_library_error}")
            return

        selected_refs = self._selected_mineral_references()
        if not selected_refs:
            QMessageBox.warning(self, "Classify", "No reference minerals selected.")
            return

        element_columns = _resolve_element_columns(selected_refs, result.calibrated_ppm.columns)
        if not element_columns:
            QMessageBox.warning(self, "Classify", "No matching analyte columns found in this sample.")
            return

        tau_min = self.sliderMatchThreshold.value()
        g_min = self.sliderAmbiguityGap.value()
        result.classification = classify_batch(
            result.calibrated_ppm, selected_refs, element_columns, tau_min=tau_min, g_min=g_min,
        )
        result.classification_categories = sorted({r.mineral_name for r in selected_refs})

        self._refresh_classification_tab()

    def _build_results_tabs(self) -> QTabWidget:
        self.tabs = QTabWidget()

        # -- Timing / files --
        self.tableTiming = QTableWidget()
        self.tabs.addTab(self.tableTiming, "Timing / Files")

        
        # -- Time Series --
        time_series_widget = QWidget()
        time_series_layout = QHBoxLayout(time_series_widget)
        ts_left = QVBoxLayout()
        ts_lines_header = QHBoxLayout()
        ts_lines_header.addWidget(QLabel("Lines"))
        ts_lines_header.addStretch(1)
        # Label text is kept in sync with what a click will actually do --
        # see _update_toggle_all_button_labels -- so it always reads "All"
        # when a click would check every currently-listed row, "None" when
        # a click would uncheck them (i.e. every row is already checked).
        self.buttonViewAll = QPushButton("View All")
        self.buttonViewAll.setToolTip("Check/uncheck View for every currently-listed line")
        ts_lines_header.addWidget(self.buttonViewAll)
        self.buttonUseAll = QPushButton("Use All")
        self.buttonUseAll.setToolTip("Check/uncheck Use for every currently-listed line")
        ts_lines_header.addWidget(self.buttonUseAll)
        ts_left.addLayout(ts_lines_header)
        self.tableTimeSeriesFiles = QTableWidget(0, 3)
        self.tableTimeSeriesFiles.setHorizontalHeaderLabels(["View", "Use", "Filename"])
        self.tableTimeSeriesFiles.horizontalHeader().setStretchLastSection(True)
        self.tableTimeSeriesFiles.verticalHeader().setVisible(False)
        ts_left.addWidget(self.tableTimeSeriesFiles)
        ts_left_widget = QWidget()
        ts_left_widget.setLayout(ts_left)
        ts_left_widget.setMaximumWidth(260)
        time_series_layout.addWidget(ts_left_widget)

        ts_right = QVBoxLayout()
        self.canvasTimeSeries = SimpleMplCanvas(width=8, height=5)
        self.toolbarTimeSeries = make_compact_nav_toolbar(self.canvasTimeSeries, time_series_widget)
        ts_right.addWidget(self.toolbarTimeSeries)
        ts_right.addWidget(self.canvasTimeSeries)
        time_series_layout.addLayout(ts_right, stretch=1)
        self.tabs.addTab(time_series_widget, "Time Series")

        # -- Background --
        background_widget = QWidget()
        background_layout = QVBoxLayout(background_widget)
        self.canvasBackground = SimpleMplCanvas(width=8, height=5)
        self.toolbarBackground = make_compact_nav_toolbar(self.canvasBackground, background_widget)
        background_layout.addWidget(self.toolbarBackground)
        background_layout.addWidget(self.canvasBackground)
        self.labelDetectionLimits = QLabel("")
        self.labelDetectionLimits.setWordWrap(True)
        background_layout.addWidget(self.labelDetectionLimits)
        self.tabs.addTab(background_widget, "Background")

        # -- Standards QC --
        standards_widget = QWidget()
        standards_layout = QVBoxLayout(standards_widget)
        self.canvasStandardVsReference = SimpleMplCanvas(width=8, height=4)
        self.toolbarStandardVsReference = make_compact_nav_toolbar(self.canvasStandardVsReference, standards_widget)
        standards_layout.addWidget(self.toolbarStandardVsReference)
        standards_layout.addWidget(self.canvasStandardVsReference)
        self.tableAccuracyFit = QTableWidget()
        standards_layout.addWidget(QLabel("Fit-group accuracy"))
        standards_layout.addWidget(self.tableAccuracyFit)
        self.tableAccuracyHoldout = QTableWidget()
        standards_layout.addWidget(QLabel("Holdout-group accuracy (odd/even split)"))
        standards_layout.addWidget(self.tableAccuracyHoldout)
        self.tabs.addTab(standards_widget, "Standards QC")

        # -- Calibration Curve (multi-point calibration only) --
        curve_widget = QWidget()
        curve_layout = QVBoxLayout(curve_widget)
        self.canvasCalibrationCurve = SimpleMplCanvas(width=8, height=5)
        self.toolbarCalibrationCurve = make_compact_nav_toolbar(self.canvasCalibrationCurve, curve_widget)
        curve_layout.addWidget(self.toolbarCalibrationCurve)
        curve_layout.addWidget(self.canvasCalibrationCurve)
        self.tabs.addTab(curve_widget, "Calibration Curve")

        # -- Isotope Ratios (mass-bias calibration only, see massbias.py) --
        isotope_ratios_widget = QWidget()
        isotope_ratios_layout = QVBoxLayout(isotope_ratios_widget)
        pair_row = QHBoxLayout()
        pair_row.addWidget(QLabel("Isotope pair"))
        self.comboIsotopeRatioPair = QComboBox()
        pair_row.addWidget(self.comboIsotopeRatioPair, stretch=1)
        isotope_ratios_layout.addLayout(pair_row)

        isotope_ratios_splitter = QSplitter(Qt.Orientation.Vertical)

        bias_fit_widget = QWidget()
        bias_fit_layout = QVBoxLayout(bias_fit_widget)
        self.canvasIsotopeBiasFit = SimpleMplCanvas(width=8, height=3)
        self.toolbarIsotopeBiasFit = make_compact_nav_toolbar(self.canvasIsotopeBiasFit, bias_fit_widget)
        bias_fit_layout.addWidget(self.toolbarIsotopeBiasFit)
        bias_fit_layout.addWidget(self.canvasIsotopeBiasFit)
        isotope_ratios_splitter.addWidget(bias_fit_widget)

        ratio_map_widget = QWidget()
        ratio_map_layout = QVBoxLayout(ratio_map_widget)
        self.canvasIsotopeRatioMap = SimpleMplCanvas(width=8, height=3)
        self.toolbarIsotopeRatioMap = make_compact_nav_toolbar(self.canvasIsotopeRatioMap, ratio_map_widget)
        ratio_map_layout.addWidget(self.toolbarIsotopeRatioMap)
        ratio_map_layout.addWidget(self.canvasIsotopeRatioMap)
        isotope_ratios_splitter.addWidget(ratio_map_widget)

        isotope_ratios_layout.addWidget(isotope_ratios_splitter)
        self.tabs.addTab(isotope_ratios_widget, "Isotope Ratios")

        # -- Maps --
        maps_widget = QWidget()
        maps_layout = QVBoxLayout(maps_widget)
        self.canvasMap = SimpleMplCanvas(width=8, height=5)
        self.toolbarMap = make_compact_nav_toolbar(self.canvasMap, maps_widget)
        maps_layout.addWidget(self.toolbarMap)
        maps_layout.addWidget(self.canvasMap)
        self.tabs.addTab(maps_widget, "Maps")

        # -- Data --
        self.tableData = QTableWidget()
        self.labelDataNote = QLabel("")
        data_widget = QWidget()
        data_layout = QVBoxLayout(data_widget)
        data_layout.addWidget(self.labelDataNote)
        data_layout.addWidget(self.tableData)
        self.tabs.addTab(data_widget, "Data")

        # -- Deconvolution QC --
        deconvolution_widget = QWidget()
        deconvolution_qc_layout = QVBoxLayout(deconvolution_widget)
        self.canvasDeconvolution = SimpleMplCanvas(width=8, height=4)
        self.toolbarDeconvolution = make_compact_nav_toolbar(self.canvasDeconvolution, deconvolution_widget)
        deconvolution_qc_layout.addWidget(self.toolbarDeconvolution)
        deconvolution_qc_layout.addWidget(self.canvasDeconvolution)
        self.tableDeconvolutionReport = QTableWidget()
        self.tableDeconvolutionReport.setMaximumHeight(200)
        deconvolution_qc_layout.addWidget(self.tableDeconvolutionReport)
        self.tabs.addTab(deconvolution_widget, "Deconvolution QC")

        # -- Classification --
        classification_widget = QWidget()
        classification_result_layout = QVBoxLayout(classification_widget)
        self.canvasClassification = SimpleMplCanvas(width=8, height=5)
        self.toolbarClassification = make_compact_nav_toolbar(self.canvasClassification, classification_widget)
        classification_result_layout.addWidget(self.toolbarClassification)
        classification_result_layout.addWidget(self.canvasClassification)
        self.tableClassificationSummary = QTableWidget()
        self.tableClassificationSummary.setMaximumHeight(200)
        classification_result_layout.addWidget(self.tableClassificationSummary)
        self.tabs.addTab(classification_widget, "Classification")

        return self.tabs

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------
    def _connect_widgets(self):
        self.buttonBrowseDir.clicked.connect(self._on_browse_dir)
        self.checkBoxBatchMode.toggled.connect(self.listWidgetSampleFolders.setVisible)
        self.buttonScan.clicked.connect(self._on_scan)
        self.actionOpenRefLibrary.triggered.connect(self._on_edit_standard)
        self.actionRun.triggered.connect(self._on_run)
        self.actionReprocess.triggered.connect(self._on_reprocess)
        self.actionClassify.triggered.connect(self._on_classify)
        self.comboBoxSampleResult.currentIndexChanged.connect(self._on_sample_selected)
        # The analyte selector is shared across every results tab, but only
        # the currently-visible tab's plot needs to redraw when it changes
        # -- refreshing all four on every step would be wasted work.
        # Switching tabs re-refreshes too, since the newly-active tab may be
        # stale (last drawn for a different analyte while it was hidden).
        self.analyte_list.currentIndexChanged.connect(self._refresh_active_tab)
        self.tabs.currentChanged.connect(self._refresh_active_tab)
        # The Stage/Offset-lines/Log-scale row is likewise shared, and each
        # tab only shows the controls relevant to it (_update_plot_controls_
        # visibility) -- switching tabs must update which are visible, in
        # addition to (above) triggering that tab's own refresh.
        self.tabs.currentChanged.connect(self._update_plot_controls_visibility)
        self._update_plot_controls_visibility()
        self.comboStandardLabel.currentIndexChanged.connect(self._on_standard_label_changed)
        self.comboIsotopeRatioPair.currentIndexChanged.connect(self._refresh_isotope_ratios_tab)
        self.comboMapStage.currentIndexChanged.connect(self._refresh_active_tab)
        self.checkHideMaskedPoints.toggled.connect(self._refresh_active_tab)
        self.checkOffsetLines.toggled.connect(self._refresh_active_tab)
        self.checkLogScale.toggled.connect(self._refresh_active_tab)
        self.comboBoxSampleResult.currentIndexChanged.connect(self._populate_file_table)
        self.buttonViewAll.clicked.connect(self._on_toggle_view_all)
        self.buttonUseAll.clicked.connect(self._on_toggle_use_all)
        self.actionExportCsv.triggered.connect(self._on_export_csv)
        self.actionExportJson.triggered.connect(self._on_export_json)
        self._connect_canvas_interactions()

    # ------------------------------------------------------------------
    # Data source / scan
    # ------------------------------------------------------------------
    def _on_browse_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select raw data directory")
        if directory:
            self._data_dir = Path(directory)
            self.lineEditDataDir.setText(directory)

    def _on_scan(self):
        if self._data_dir is None:
            QMessageBox.warning(self, "Scan", "Choose a raw data directory first.")
            return

        if self.checkBoxBatchMode.isChecked():
            self._batch_sample_dirs = pipeline.discover_sample_directories(self._data_dir)
            self.listWidgetSampleFolders.clear()
            for d in self._batch_sample_dirs:
                item = QListWidgetItem(d.name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                item.setData(Qt.ItemDataRole.UserRole, str(d))
                self.listWidgetSampleFolders.addItem(item)
            scan_dirs = self._batch_sample_dirs
        else:
            self._batch_sample_dirs = []
            scan_dirs = [self._data_dir]

        time_format = self.lineEditTimeFormat.text().strip() or None

        labels: set[str] = set()
        self._scanned_files = {}
        n_files = 0
        failures: list[str] = []
        for d in scan_dirs:
            for path in list_line_files(d):
                n_files += 1
                try:
                    label, _ = parse_filename_label(path)
                    labels.add(label)
                except Exception:
                    continue
                # Parsed eagerly (not just the filename label) so the Time
                # Series tab can preview raw lines before any pipeline Run.
                try:
                    self._scanned_files[path.name] = parse_line_file(
                        path, standard_names=labels, validate_isotopes=False, acquired_time_format=time_format,
                    )
                except Exception as e:
                    failures.append(f"{path.name}: {e}")

        summary = f"{len(scan_dirs)} folder(s), {n_files} file(s), labels: {sorted(labels)}"
        if failures:
            summary += f"\n{len(failures)} file(s) failed to parse:\n" + "\n".join(failures[:10])
            if len(failures) > 10:
                summary += f"\n... and {len(failures) - 10} more."
            summary += (
                "\nIf these are timestamp errors, set 'Acquired time format' above to an explicit "
                "datetime.strptime pattern matching this instrument export and scan again."
            )
        self.labelScanSummary.setText(summary)
        self._populate_standard_labels(labels)
        self._populate_focus_combo(labels)
        self._populate_file_table()
        self._populate_per_line_override_table()
        self._populate_isotope_calibration_table()
        self._populate_dating_systems_table()
        self._populate_washout_tau_table()

    def _populate_focus_combo(self, labels: set[str]):
        """Populates comboBoxSampleResult with every label found at Scan
        time (both samples and standards) plus "(all)", so the Time Series
        file table can be focused to one label pre-Run -- not just the
        per-run calibrated-result keys _on_run_finished adds post-Run (see
        that method, which unions those in rather than replacing this)."""
        current = self.comboBoxSampleResult.currentText()
        self.comboBoxSampleResult.blockSignals(True)
        self.comboBoxSampleResult.clear()
        self.comboBoxSampleResult.addItem("(all)")
        self.comboBoxSampleResult.addItems(sorted(labels))
        idx = self.comboBoxSampleResult.findText(current)
        self.comboBoxSampleResult.setCurrentIndex(idx if idx >= 0 else 0)
        self.comboBoxSampleResult.blockSignals(False)

    def _populate_standard_labels(self, labels: set[str]):
        self.tableStandardLabels.setRowCount(0)
        self._primary_checkboxes = {}
        self._secondary_checkboxes = {}
        self._bias_checkboxes = {}
        self._reference_combos = {}
        for label in sorted(labels):
            row = self.tableStandardLabels.rowCount()
            self.tableStandardLabels.insertRow(row)

            # Case-insensitive auto-guess against the loaded reference
            # library -- a matched label defaults to Primary-checked (same
            # zero-friction default the old single "is standard" checkbox
            # gave a single recognized standard, extended naturally to
            # multiple: every recognized standard defaults to contributing
            # to calibration, which for 2+ means multi-point by default).
            match = next((k for k in self.reference_library if k.lower() == label.lower()), None)

            primary_cb = QCheckBox()
            primary_cb.setChecked(match is not None)
            primary_cb.toggled.connect(lambda checked, lbl=label: self._on_primary_toggled(lbl, checked))
            self.tableStandardLabels.setCellWidget(row, 0, primary_cb)
            self._primary_checkboxes[label] = primary_cb

            secondary_cb = QCheckBox()
            secondary_cb.toggled.connect(lambda checked, lbl=label: self._on_secondary_toggled(lbl, checked))
            self.tableStandardLabels.setCellWidget(row, 1, secondary_cb)
            self._secondary_checkboxes[label] = secondary_cb

            bias_cb = QCheckBox()
            bias_cb.setToolTip(
                "Contributes to mass-bias/radiogenic-isotope-ratio calibration (see the Isotope "
                "calibration table above) -- independent of Primary/Secondary, which only control "
                "elemental (total-concentration) calibration."
            )
            self.tableStandardLabels.setCellWidget(row, 2, bias_cb)
            self._bias_checkboxes[label] = bias_cb

            label_item = QTableWidgetItem(label)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tableStandardLabels.setItem(row, 3, label_item)

            combo = QComboBox()
            combo.addItem("—")
            combo.addItems(sorted(self.reference_library))
            combo.setCurrentText(match or "—")
            self.tableStandardLabels.setCellWidget(row, 4, combo)
            self._reference_combos[label] = combo

    def _on_primary_toggled(self, label: str, checked: bool):
        if checked:
            self._secondary_checkboxes[label].setChecked(False)

    def _on_secondary_toggled(self, label: str, checked: bool):
        if checked:
            self._primary_checkboxes[label].setChecked(False)

    def _primary_standard_names(self) -> list[str]:
        return sorted(label for label, cb in self._primary_checkboxes.items() if cb.isChecked())

    def _secondary_standard_names(self) -> list[str]:
        return sorted(label for label, cb in self._secondary_checkboxes.items() if cb.isChecked())

    def _bias_standard_names(self) -> list[str]:
        return sorted(label for label, cb in self._bias_checkboxes.items() if cb.isChecked())

    def _checked_standard_names(self) -> set[str]:
        """Every label treated as a standard file by the pipeline --
        Primary/Secondary (elemental calibration) union Bias (mass-bias/
        isotope-ratio calibration only) -- a label checked Bias but neither
        Primary nor Secondary still needs to be scanned as a standard file
        (not a sample) and have its reference material resolved."""
        return set(self._primary_standard_names()) | set(self._secondary_standard_names()) | set(self._bias_standard_names())

    def _reference_overrides(self) -> dict[str, str]:
        """label -> chosen reference-material name (tableStandardLabels'
        Reference column), omitting rows left at the "—" placeholder."""
        return {
            label: combo.currentText()
            for label, combo in self._reference_combos.items()
            if combo.currentText() != "—"
        }

    # ------------------------------------------------------------------
    # Isotope calibration (Mechanism B -- mass-bias/isotope-ratio
    # apportionment on top of the always-on Mechanism A elemental
    # calibration; see isotope_apportion.py/massbias.py)
    # ------------------------------------------------------------------
    ISOTOPE_MODE_ELEMENTAL = "Elemental"
    ISOTOPE_MODE_MASS_BIAS = "Isotopic (mass-bias corrected)"
    ISOTOPE_MODE_NATURAL_ABUNDANCE = "Isotopic (natural abundance)"

    def _populate_isotope_calibration_table(self):
        """(Re)builds tableIsotopeCalibration from the analytes seen at Scan
        time, one row per element with 2+ measured isotopes -- an element
        with only one measured isotope has nothing to apportion (Mechanism
        A's elemental calibration already covers it unconditionally)."""
        self.tableIsotopeCalibration.setRowCount(0)
        self._isotope_mode_combos = {}
        self._isotope_pool_checkboxes = {}
        self._isotope_element_masses = {}

        analytes = sorted(next(iter(self._scanned_files.values())).analytes) if self._scanned_files else []
        by_element: dict[str, list[int]] = {}
        for analyte in analytes:
            parsed = reflib.parse_analyte_name(analyte)
            if parsed is None:
                continue
            element, mass = parsed
            by_element.setdefault(element, []).append(mass)

        for element in sorted(by_element):
            masses = sorted(set(by_element[element]))
            if len(masses) < 2:
                continue
            self._isotope_element_masses[element] = masses

            row = self.tableIsotopeCalibration.rowCount()
            self.tableIsotopeCalibration.insertRow(row)

            elem_item = QTableWidgetItem(element)
            elem_item.setFlags(elem_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tableIsotopeCalibration.setItem(row, 0, elem_item)

            isotopes_item = QTableWidgetItem(", ".join(f"{element}{m}" for m in masses))
            isotopes_item.setFlags(isotopes_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tableIsotopeCalibration.setItem(row, 1, isotopes_item)

            combo = QComboBox()
            combo.addItems([self.ISOTOPE_MODE_ELEMENTAL, self.ISOTOPE_MODE_MASS_BIAS, self.ISOTOPE_MODE_NATURAL_ABUNDANCE])
            combo.setToolTip(
                "Elemental (default): unaffected by this table -- every isotope already "
                "independently estimates the same total-element concentration. Isotopic (mass-bias "
                "corrected): splits that total across isotopes using this sample's own mass-bias-"
                "corrected ratios -- the scientifically valid choice for radiogenic daughter isotopes "
                "(Pb-206/207/208, Sr-87, Nd-143, Hf-176, Os-187, ...); needs a Bias-checked standard "
                "with a certified or natural-abundance ratio for this element. Isotopic (natural "
                "abundance): splits using a fixed terrestrial-abundance ratio instead -- invalid for "
                "radiogenic pairs (their whole point is that the true ratio varies sample-to-sample), "
                "offered for non-radiogenic isotope pairs a user still wants split out by mass."
            )
            self.tableIsotopeCalibration.setCellWidget(row, 2, combo)
            self._isotope_mode_combos[element] = combo

            pool_cb = QCheckBox()
            pool_cb.setToolTip(
                f"Adds a pooled '{element} total' channel: sums this element's measured isotopes' "
                "raw counts (rescaled by their combined natural-abundance fraction) before "
                "calibration, for better counting-statistics precision than any single isotope "
                "alone -- see pooling.py. Independent of Mode above; not valid for elements whose "
                "isotopic composition is itself the signal of interest (radiogenic pairs)."
            )
            self.tableIsotopeCalibration.setCellWidget(row, 3, pool_cb)
            self._isotope_pool_checkboxes[element] = pool_cb

    def _resolve_isotope_normalizer_mass(
        self, element: str, masses: list[int], remapped_library: dict[str, reflib.ReferenceMaterial],
    ) -> int | None:
        """Which of ``masses`` acts as the ratio denominator/normalizer for
        ``element`` -- a certified reference-material ratio's own
        denominator, when the currently-checked standards' reference
        materials carry one for this element (the first one found, sorted
        by standard label then isotope-ratio key, matching this project's
        "certified-first" resolution order elsewhere -- see
        massbias.resolve_truth_ratio's docstring); otherwise the most
        naturally abundant of the measured isotopes (see
        massbias.most_abundant_mass), a reasonable default when there's no
        certified pair to anchor on.
        """
        for label in sorted(self._checked_standard_names()):
            material = remapped_library.get(label)
            if material is None:
                continue
            for key in sorted(material.isotope_ratios):
                ratio = material.isotope_ratios[key]
                if ratio.numerator_element == element and ratio.denominator_mass in masses:
                    return ratio.denominator_mass
                if ratio.denominator_element == element and ratio.numerator_mass in masses:
                    return ratio.numerator_mass
        return most_abundant_mass(element, masses)

    def _gather_isotope_specs(
        self, remapped_library: dict[str, reflib.ReferenceMaterial],
    ) -> tuple[list[BiasSpec], list[IsotopeShareSpec]]:
        """Reads tableIsotopeCalibration's per-element Mode selection into
        the ``bias_specs``/``isotope_share_specs`` pipeline.run() expects --
        called from _on_run, after remapped_library (this run's resolved
        label -> reference material mapping) is built, since normalizer-mass
        resolution needs it."""
        bias_specs: list[BiasSpec] = []
        isotope_share_specs: list[IsotopeShareSpec] = []
        bias_standards = self._bias_standard_names() or None  # None -> pipeline uses every usable standard

        for element, combo in self._isotope_mode_combos.items():
            mode_text = combo.currentText()
            if mode_text == self.ISOTOPE_MODE_ELEMENTAL:
                continue
            masses = self._isotope_element_masses.get(element, [])
            if len(masses) < 2:
                continue
            normalizer_mass = self._resolve_isotope_normalizer_mass(element, masses, remapped_library)
            if normalizer_mass is None:
                continue
            companion_masses = [m for m in masses if m != normalizer_mass]

            if mode_text == self.ISOTOPE_MODE_MASS_BIAS:
                for mass in companion_masses:
                    bias_specs.append(BiasSpec(
                        element=element, numerator_mass=mass, denominator_mass=normalizer_mass,
                        bias_standards=bias_standards,
                    ))
                isotope_share_specs.append(IsotopeShareSpec(
                    element=element, normalizer_mass=normalizer_mass, companion_masses=companion_masses,
                    mode="mass_bias",
                ))
            elif mode_text == self.ISOTOPE_MODE_NATURAL_ABUNDANCE:
                isotope_share_specs.append(IsotopeShareSpec(
                    element=element, normalizer_mass=normalizer_mass, companion_masses=companion_masses,
                    mode="natural_abundance",
                ))

        return bias_specs, isotope_share_specs

    def _gather_pool_specs(self) -> list[PooledElementSpec]:
        """Reads tableIsotopeCalibration's "El total" checkbox column into
        ``pipeline.run()``'s ``pool_specs`` -- independent of each row's
        Mode selection (pooling and per-isotope apportionment are separate,
        opt-in-together-or-separately features)."""
        return [
            PooledElementSpec(element=element, masses=self._isotope_element_masses.get(element, []))
            for element, cb in self._isotope_pool_checkboxes.items()
            if cb.isChecked() and len(self._isotope_element_masses.get(element, [])) >= 2
        ]

    # ------------------------------------------------------------------
    # Radiometric dating ratios (Stage 1: Pb-Pb, U-Pb, Th-Pb -- see
    # dating_ratios.py for the cross-element pairs, massbias.py reused
    # directly for Pb-Pb's same-element pairs)
    # ------------------------------------------------------------------
    def _populate_dating_systems_table(self):
        """(Re)builds tableRadiometricSystems from the analytes seen at
        Scan time, one row per dating system whose required isotopes are
        all present -- Pb-Pb (2+ of Pb204/206/207/208), U-Pb (U238 +
        Pb206, optionally Pb207 for the 207Pb/235U reformulation and
        Pb207/Pb206), Th-Pb (Th232 + Pb208)."""
        self.tableRadiometricSystems.setRowCount(0)
        self._dating_system_checkboxes = {}

        analytes = set(next(iter(self._scanned_files.values())).analytes) if self._scanned_files else set()

        def has(name: str) -> bool:
            return name in analytes

        systems: list[tuple[str, str]] = []
        pb_masses = [m for m in (204, 206, 207, 208) if has(f"Pb{m}")]
        if len(pb_masses) >= 2:
            # Heavier isotope as numerator (e.g. "Pb206/Pb204", not "Pb204/Pb206")
            # -- matches conventional isotope-ratio naming, and _gather_dating_ratio_specs's own pairing.
            pairs = ", ".join(f"Pb{num}/Pb{den}" for i, den in enumerate(pb_masses) for num in pb_masses[i + 1:])
            systems.append(("Pb-Pb", pairs))
        if has("U238") and has("Pb206"):
            ratios = ["Pb206/U238"]
            if has("Pb207"):
                ratios += ["Pb207/U238 (as 207Pb/235U)", "Pb207/Pb206"]
            systems.append(("U-Pb", ", ".join(ratios)))
        if has("Th232") and has("Pb208"):
            systems.append(("Th-Pb", "Pb208/Th232"))

        for name, detail in systems:
            row = self.tableRadiometricSystems.rowCount()
            self.tableRadiometricSystems.insertRow(row)

            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tableRadiometricSystems.setItem(row, 0, name_item)

            detail_item = QTableWidgetItem(detail)
            detail_item.setFlags(detail_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tableRadiometricSystems.setItem(row, 1, detail_item)

            cb = QCheckBox()
            self.tableRadiometricSystems.setCellWidget(row, 2, cb)
            self._dating_system_checkboxes[name] = cb

    def _gather_dating_ratio_specs(self) -> tuple[list[BiasSpec], list[DatingRatioSpec]]:
        """Reads tableRadiometricSystems' per-system Enable checkbox into
        the ``bias_specs`` (same-element pairs, e.g. Pb-Pb's 206Pb/204Pb --
        reuses ``massbias.py`` directly, the exact same mechanism the
        per-element Isotope calibration table's "Isotopic (mass-bias
        corrected)" Mode uses) / ``dating_ratio_specs`` (cross-element
        pairs, see ``dating_ratios.py``) ``pipeline.run()`` expects --
        called from ``_on_run``; the returned ``bias_specs`` still need
        merging/deduping against the per-element Mode table's own
        ``bias_specs`` by the caller, since the same pair (e.g. Pb207/
        Pb206) can legitimately be requested by both tables.

        Reuses the *same* "Bias" checkbox column on ``tableStandardLabels``
        as the standards-selection source these fits bracket against
        (``self._bias_standard_names()``) -- one shared "which standards
        anchor isotope-ratio work" concept, no separate checkbox column
        for dating systems.
        """
        bias_specs: dict[tuple[str, int, int], BiasSpec] = {}
        dating_specs: list[DatingRatioSpec] = []
        dating_standards = self._bias_standard_names() or None

        analytes = set(next(iter(self._scanned_files.values())).analytes) if self._scanned_files else set()

        def has(name: str) -> bool:
            return name in analytes

        pb_pb_cb = self._dating_system_checkboxes.get("Pb-Pb")
        if pb_pb_cb is not None and pb_pb_cb.isChecked():
            pb_masses = [m for m in (204, 206, 207, 208) if has(f"Pb{m}")]
            # Heavier isotope as numerator (matches _populate_dating_systems_table's own pairing).
            for i, den in enumerate(pb_masses):
                for num in pb_masses[i + 1:]:
                    bias_specs[("Pb", num, den)] = BiasSpec(
                        element="Pb", numerator_mass=num, denominator_mass=den, bias_standards=dating_standards,
                    )

        u_pb_cb = self._dating_system_checkboxes.get("U-Pb")
        if u_pb_cb is not None and u_pb_cb.isChecked():
            dating_specs.append(DatingRatioSpec(
                numerator_element="Pb", numerator_mass=206, denominator_element="U", denominator_mass=238,
                dating_standards=dating_standards,
            ))
            if has("Pb207"):
                k = natural_abundance_ratio("U", 238, 235)
                if k is not None:
                    dating_specs.append(DatingRatioSpec(
                        numerator_element="Pb", numerator_mass=207, denominator_element="U", denominator_mass=238,
                        numerator_scale_factor=k, dating_standards=dating_standards,
                    ))
                bias_specs[("Pb", 207, 206)] = BiasSpec(
                    element="Pb", numerator_mass=207, denominator_mass=206, bias_standards=dating_standards,
                )

        th_pb_cb = self._dating_system_checkboxes.get("Th-Pb")
        if th_pb_cb is not None and th_pb_cb.isChecked():
            dating_specs.append(DatingRatioSpec(
                numerator_element="Pb", numerator_mass=208, denominator_element="Th", denominator_mass=232,
                dating_standards=dating_standards,
            ))

        return list(bias_specs.values()), dating_specs

    # ------------------------------------------------------------------
    # Time series (works pre-Run on scanned files, and post-Run with
    # role-colored points once a BackgroundResult is available)
    # ------------------------------------------------------------------
    def _populate_file_table(self):
        """(Re)builds tableTimeSeriesFiles, filtered to the label currently
        selected in comboBoxSampleResult (every file if "(all)"/blank).
        View/Use state (self._file_view_state/_file_use_state) is
        initialized once per filename the first time it's seen and
        persists across focus changes and re-population -- so switching
        the focus combo doesn't lose View/Use choices made while a
        different label was in focus."""
        for name in self._scanned_files:
            self._file_view_state.setdefault(name, False)
            self._file_use_state.setdefault(name, True)

        focus = self.comboBoxSampleResult.currentText()
        # Batch mode keys comboBoxSampleResult's sample-result entries as
        # "folder / label" (see _on_run_finished), but a raw filename only
        # ever carries its own bare label -- compare against the trailing
        # segment so focusing a batch-mode result still filters correctly.
        focus_label = focus.rsplit(" / ", 1)[-1] if focus else focus

        def _matches_focus(name: str) -> bool:
            if not focus or focus == "(all)":
                return True
            try:
                label, _ = parse_filename_label(Path(name))
            except Exception:
                return False
            return label == focus_label

        names = sorted(n for n in self._scanned_files if _matches_focus(n))

        self.tableTimeSeriesFiles.blockSignals(True)
        self.tableTimeSeriesFiles.setRowCount(0)
        for name in names:
            row = self.tableTimeSeriesFiles.rowCount()
            self.tableTimeSeriesFiles.insertRow(row)

            view_check = QCheckBox()
            view_check.setChecked(self._file_view_state[name])
            view_check.toggled.connect(lambda checked, n=name: self._on_file_view_toggled(n, checked))
            self.tableTimeSeriesFiles.setCellWidget(row, 0, view_check)

            use_check = QCheckBox()
            use_check.setChecked(self._file_use_state[name])
            use_check.toggled.connect(lambda checked, n=name: self._on_file_use_toggled(n, checked))
            self.tableTimeSeriesFiles.setCellWidget(row, 1, use_check)

            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tableTimeSeriesFiles.setItem(row, 2, name_item)
        self.tableTimeSeriesFiles.blockSignals(False)
        self._update_toggle_all_button_labels()

        analytes = sorted(next(iter(self._scanned_files.values())).analytes) if self._scanned_files else []
        self.analyte_list.blockSignals(True)
        self.analyte_list.setItems(analytes)
        self.analyte_list.blockSignals(False)

    def _on_file_view_toggled(self, name: str, checked: bool):
        self._file_view_state[name] = checked
        self._update_toggle_all_button_labels()
        self._refresh_time_series_tab()

    def _on_file_use_toggled(self, name: str, checked: bool):
        self._file_use_state[name] = checked
        self._update_toggle_all_button_labels()

    def _visible_file_table_names(self) -> list[str]:
        return [
            self.tableTimeSeriesFiles.item(row, 2).text() for row in range(self.tableTimeSeriesFiles.rowCount())
        ]

    def _update_toggle_all_button_labels(self):
        """buttonViewAll/buttonUseAll's label always names the action a
        click will actually perform: "All" when at least one currently-
        listed row is unchecked (so a click would check every row), "None"
        when every currently-listed row is already checked (so a click
        would uncheck them all) -- matches _on_toggle_view_all/_on_toggle_
        use_all's own all-or-nothing toggle logic."""
        names = self._visible_file_table_names()
        view_all_checked = bool(names) and all(self._file_view_state.get(n, False) for n in names)
        use_all_checked = bool(names) and all(self._file_use_state.get(n, True) for n in names)
        self.buttonViewAll.setText("View None" if view_all_checked else "View All")
        self.buttonUseAll.setText("Use None" if use_all_checked else "Use All")

    def _on_toggle_view_all(self):
        names = self._visible_file_table_names()
        if not names:
            return
        new_state = not all(self._file_view_state.get(n, False) for n in names)
        for n in names:
            self._file_view_state[n] = new_state
        self._populate_file_table()
        self._refresh_time_series_tab()

    def _on_toggle_use_all(self):
        names = self._visible_file_table_names()
        if not names:
            return
        new_state = not all(self._file_use_state.get(n, True) for n in names)
        for n in names:
            self._file_use_state[n] = new_state
        self._populate_file_table()

    def _refresh_time_series_tab(self):
        analyte = self.analyte_list.currentText()
        if not analyte:
            self.canvasTimeSeries.axes.clear()
            self._draw(self.canvasTimeSeries)
            return

        checked_names = {name for name, viewed in self._file_view_state.items() if viewed}

        file_by_name = dict(self._scanned_files)
        background_by_name: dict[str, object] = {}
        outlier_names: set[str] = set()
        result = self._current_result()
        if result is not None:
            for f, b in zip(result.files, result.backgrounds):
                file_by_name[f.meta.path.name] = f
                background_by_name[f.meta.path.name] = b
            for standard_result in result.standard_results.values():
                outlier_orders = set(standard_result.excluded_outliers.get(analyte, []))
                for occ in standard_result.occurrences:
                    background_by_name[occ.file_meta.path.name] = occ.background
                    if occ.occurrence_order in outlier_orders:
                        outlier_names.add(occ.file_meta.path.name)

        lines = [
            (file_by_name[name], background_by_name.get(name))
            for name in sorted(checked_names) if name in file_by_name
        ]

        self.canvasTimeSeries.axes.clear()
        self._time_series_point_index = diagnostics.plot_time_series(
            self.canvasTimeSeries.axes, lines, analyte,
            offset=self.checkOffsetLines.isChecked(),
            log_scale=self.checkLogScale.isChecked(),
            outlier_names=outlier_names,
            manual_row_masks=self._manual_row_masks_for_analyte(analyte),
            mask_display=self._mask_display_mode(),
        )
        self._draw(self.canvasTimeSeries)

    def _mask_display_mode(self) -> str:
        """``"hidden"`` or ``"light_gray"`` for ``plot_time_series``/
        ``plot_standard_vs_reference``'s ``mask_display`` param, from the
        shared "Hide masked points" checkbox above the tab widget."""
        return "hidden" if self.checkHideMaskedPoints.isChecked() else "light_gray"

    def _manual_row_masks_for_analyte(self, analyte: str) -> dict[str, np.ndarray]:
        """Builds the per-filename boolean mask ``plot_time_series``'s
        ``manual_row_masks`` expects, from ``self._manual_row_exclusions``
        (filename -> analyte -> set of absolute row indices) for one
        analyte -- used for instant visual feedback on a click/drag
        exclusion, before the next Run actually recomputes statistics with
        it applied (see ``pipeline.run``'s own ``manual_row_exclusions``)."""
        masks: dict[str, np.ndarray] = {}
        for filename, per_analyte in self._manual_row_exclusions.items():
            row_indices = per_analyte.get(analyte)
            if not row_indices:
                continue
            file_data = self._scanned_files.get(filename)
            n = file_data.n_rows if file_data is not None else (max(row_indices) + 1)
            mask = np.zeros(n, dtype=bool)
            for idx in row_indices:
                if idx < n:
                    mask[idx] = True
            masks[filename] = mask
        return masks

    # ------------------------------------------------------------------
    # Per-line background/edge-trim override table
    # ------------------------------------------------------------------
    def _populate_per_line_override_table(self):
        self.tablePerLineOverrides.setRowCount(0)
        for name in sorted(self._scanned_files):
            row = self.tablePerLineOverrides.rowCount()
            self.tablePerLineOverrides.insertRow(row)
            item = QTableWidgetItem(name)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tablePerLineOverrides.setItem(row, 0, item)
            for col in range(1, 5):
                self.tablePerLineOverrides.setItem(row, col, QTableWidgetItem(""))

    def _gather_per_file_overrides(self) -> dict[str, BackgroundWindowOverride]:
        """Reads the per-line override table into overrides, one per row with
        at least one non-blank cell -- blank cells fall back to the global
        override/edge-trim settings (or auto-detection, if the global
        override itself isn't enabled)."""
        overrides: dict[str, BackgroundWindowOverride] = {}
        global_override = self._current_background_override()

        def _cell_float(row: int, col: int, default: float | None) -> float | None:
            text = self.tablePerLineOverrides.item(row, col).text().strip()
            return float(text) if text else default

        for row in range(self.tablePerLineOverrides.rowCount()):
            name = self.tablePerLineOverrides.item(row, 0).text()
            any_set = any(self.tablePerLineOverrides.item(row, col).text().strip() for col in range(1, 5))
            if not any_set:
                continue
            default_start = global_override.start_offset_s if global_override else None
            default_end = global_override.end_offset_s if global_override else None
            default_lead = global_override.edge_trim_lead_s if global_override else 0.0
            default_trail = global_override.edge_trim_trail_s if global_override else 0.0
            overrides[name] = BackgroundWindowOverride(
                start_offset_s=_cell_float(row, 1, default_start),
                end_offset_s=_cell_float(row, 2, default_end),
                edge_trim_lead_s=_cell_float(row, 3, default_lead) or 0.0,
                edge_trim_trail_s=_cell_float(row, 4, default_trail) or 0.0,
            )
        return overrides

    def _current_background_override(self) -> BackgroundWindowOverride | None:
        if not self.checkBackgroundOverride.isChecked() and not self.checkEdgeTrim.isChecked():
            return None
        return BackgroundWindowOverride(
            start_offset_s=self.spinOverrideStart.value() if self.checkBackgroundOverride.isChecked() else None,
            end_offset_s=self.spinOverrideEnd.value() if self.checkBackgroundOverride.isChecked() else None,
            edge_trim_lead_s=self.spinEdgeTrimLead.value() if self.checkEdgeTrim.isChecked() else 0.0,
            edge_trim_trail_s=self.spinEdgeTrimTrail.value() if self.checkEdgeTrim.isChecked() else 0.0,
        )

    # ------------------------------------------------------------------
    # Reference library
    # ------------------------------------------------------------------
    def _reload_reference_library(self):
        """Mutates ``self.reference_library`` in place (never reassigns) --
        an open ReferenceMaterialEditDialog holds the same dict object, so
        this keeps it in sync live rather than needing an explicit
        sync-back step when the dialog closes."""
        REFERENCE_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        fresh = reflib.load_reference_library(REFERENCE_LIBRARY_DIR)
        self.reference_library.clear()
        self.reference_library.update(fresh)

    def _open_reference_dialog(self, initial_name: str | None = None) -> ReferenceMaterialEditDialog:
        dialog = ReferenceMaterialEditDialog(
            self.reference_library, REFERENCE_LIBRARY_DIR, initial_name=initial_name, parent=self,
        )
        dialog.destroyed.connect(self._reload_reference_library)
        dialog.show()
        self._active_dialog = dialog  # keep a reference so it isn't garbage-collected
        return dialog

    def _on_edit_standard(self):
        initial = sorted(self.reference_library)[0] if self.reference_library else None
        self._open_reference_dialog(initial_name=initial)

    def _on_add_standard(self):
        # Opens the same dialog used for editing, then immediately triggers
        # its own "New..." flow (name prompt, template-based creation) --
        # reuses that logic rather than duplicating it here.
        dialog = self._open_reference_dialog()
        dialog._on_new_standard()

    # ------------------------------------------------------------------
    # Instrument settings
    # ------------------------------------------------------------------
    def _current_instrument_settings(self) -> InstrumentSettings:
        notes = {}
        for line in self.textNotes.toPlainText().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                notes[key.strip()] = value.strip()

        def _or_none(spin: QDoubleSpinBox):
            return None if spin.value() == 0 else spin.value()

        return InstrumentSettings.from_manual_entry(
            instrument=self.lineEditInstrument.text().strip() or None,
            spot_size_um=_or_none(self.spinSpotSize),
            sweep_s=_or_none(self.spinSweep),
            speed_um_s=_or_none(self.spinSpeed),
            dwell_time_ms=_or_none(self.spinDwellTime),
            scan_axis=self.comboScanAxis.currentText(),
            reverse_x=self.checkReverseX.isChecked(),
            reverse_y=self.checkReverseY.isChecked(),
            bidirectional_scan=self.checkBidirectionalScan.isChecked(),
            laser_wavelength_nm=_or_none(self.spinLaserWavelength),
            fluence_j_cm2=_or_none(self.spinFluence),
            pulse_rate_hz=_or_none(self.spinPulseRate),
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    def _on_run(self):
        if self._data_dir is None:
            QMessageBox.warning(self, "Run", "Choose and scan a raw data directory first.")
            return
        standard_names = self._checked_standard_names()
        if not standard_names:
            QMessageBox.warning(self, "Run", "Mark at least one label as a standard.")
            return

        primary_standards = self._primary_standard_names()
        # Per-label reference-material overrides (tableStandardLabels'
        # Reference column) are resolved here into an exact-name-keyed
        # library, since pipeline.run's label->reference matching is still
        # simple exact-name lookup (reference_library.get(label)) -- this
        # is the only place that needs to know about the override UI.
        overrides = self._reference_overrides()
        remapped_library = {
            label: self.reference_library[overrides[label]]
            for label in self._checked_standard_names()
            if overrides.get(label) in self.reference_library
        }

        bias_specs, isotope_share_specs = self._gather_isotope_specs(remapped_library)
        pool_specs = self._gather_pool_specs()
        dating_bias_specs, dating_ratio_specs = self._gather_dating_ratio_specs()
        # Dedupe against the per-element Mode table's own bias_specs by pair
        # key -- the same pair (e.g. Pb207/Pb206) can legitimately be
        # requested by both the Isotope calibration table and the
        # Radiometric dating ratios table; both sources resolve to an
        # identical BiasSpec (same "Bias" checkbox column), so this is a
        # safe merge, not a conflict to reconcile.
        bias_spec_by_key = {(s.element, s.numerator_mass, s.denominator_mass): s for s in bias_specs}
        for s in dating_bias_specs:
            bias_spec_by_key.setdefault((s.element, s.numerator_mass, s.denominator_mass), s)
        bias_specs = list(bias_spec_by_key.values())

        common_kwargs = dict(
            standard_names=standard_names,
            reference_library=remapped_library,
            drift_order=self.spinDriftOrder.value(),
            background_drift_order=self.spinDriftOrder.value(),
            drift_method=DRIFT_METHOD_LABELS[self.comboDriftMethod.currentText()],
            background_drift_method=DRIFT_METHOD_LABELS[self.comboBackgroundDriftMethod.currentText()],
            max_order=self.spinDriftOrder.value(),
            split_odd_even=self.checkSplitOddEven.isChecked(),
            accuracy_threshold=self.spinAccuracyThreshold.value(),
            primary_standards=primary_standards,
            instrument_settings=self._current_instrument_settings(),
            background_override=self._current_background_override(),
            per_file_overrides=self._gather_per_file_overrides(),
            acquired_time_format=self.lineEditTimeFormat.text().strip() or None,
            excluded_files={name for name, used in self._file_use_state.items() if not used},
            manual_row_exclusions=self._manual_row_exclusions,
            manual_occurrence_exclusions=self._manual_occurrence_exclusions,
            detrend=self.checkDetrend.isChecked(),
            despike_noise=self.checkDespikeNoise.isChecked(),
            force_zero_intercept=self.checkForceZeroIntercept.isChecked(),
            bias_specs=bias_specs,
            isotope_share_specs=isotope_share_specs,
            pool_specs=pool_specs,
            dating_ratio_specs=dating_ratio_specs,
            deconvolution_settings=self._current_deconvolution_settings(),
            ablation_onset_trim_s=self.spinAblationOnsetTrim.value(),
        )

        if self.checkBoxBatchMode.isChecked():
            fn = pipeline.run_batch
            kwargs = dict(parent_dir=self._data_dir, **common_kwargs)
        else:
            fn = pipeline.run
            kwargs = dict(sample_dir=self._data_dir, **common_kwargs)

        self.actionRun.setEnabled(False)
        self.actionReprocess.setEnabled(False)
        self.labelRunStatus.setText("Running...")
        self._worker = _PipelineWorker(fn, kwargs, parent=self)
        self._worker.finished_ok.connect(self._on_run_finished)
        self._worker.failed.connect(self._on_run_failed)
        self._worker.start()

    def _on_reprocess(self):
        """Fast reprocess-only re-run: reuses files already parsed by the
        last Scan (self._scanned_files) instead of re-reading every raw
        file from disk -- for quickly re-applying changed deconvolution/
        calibration settings. Batch mode isn't supported here (unlike
        _on_run/run_batch) since self._scanned_files doesn't track which
        subdirectory each file came from -- see run_from_parsed's
        docstring; use the main Run button for batch mode instead.
        """
        if self.checkBoxBatchMode.isChecked():
            QMessageBox.information(
                self, "Reprocess",
                "Reprocess (fast re-run) isn't available in batch mode -- use Run instead.",
            )
            return
        if not self._scanned_files:
            QMessageBox.warning(self, "Reprocess", "Scan a raw data directory first.")
            return
        standard_names = self._checked_standard_names()
        if not standard_names:
            QMessageBox.warning(self, "Reprocess", "Mark at least one label as a standard.")
            return

        # self._scanned_files was parsed at Scan time with every label
        # treated as a standard (see _on_scan's docstring) -- correct
        # is_standard here to reflect what's actually checked now, since
        # run_from_parsed never re-parses and so never re-derives this.
        files = [
            dataclasses.replace(f, meta=dataclasses.replace(f.meta, is_standard=f.meta.label in standard_names))
            for f in self._scanned_files.values()
        ]

        primary_standards = self._primary_standard_names()
        overrides = self._reference_overrides()
        remapped_library = {
            label: self.reference_library[overrides[label]]
            for label in standard_names
            if overrides.get(label) in self.reference_library
        }

        bias_specs, isotope_share_specs = self._gather_isotope_specs(remapped_library)
        pool_specs = self._gather_pool_specs()
        dating_bias_specs, dating_ratio_specs = self._gather_dating_ratio_specs()
        bias_spec_by_key = {(s.element, s.numerator_mass, s.denominator_mass): s for s in bias_specs}
        for s in dating_bias_specs:
            bias_spec_by_key.setdefault((s.element, s.numerator_mass, s.denominator_mass), s)
        bias_specs = list(bias_spec_by_key.values())

        kwargs = dict(
            files=files,
            sample_dir=self._data_dir,
            reference_library=remapped_library,
            drift_order=self.spinDriftOrder.value(),
            background_drift_order=self.spinDriftOrder.value(),
            drift_method=DRIFT_METHOD_LABELS[self.comboDriftMethod.currentText()],
            background_drift_method=DRIFT_METHOD_LABELS[self.comboBackgroundDriftMethod.currentText()],
            max_order=self.spinDriftOrder.value(),
            split_odd_even=self.checkSplitOddEven.isChecked(),
            accuracy_threshold=self.spinAccuracyThreshold.value(),
            primary_standards=primary_standards,
            instrument_settings=self._current_instrument_settings(),
            background_override=self._current_background_override(),
            per_file_overrides=self._gather_per_file_overrides(),
            excluded_files={name for name, used in self._file_use_state.items() if not used},
            manual_row_exclusions=self._manual_row_exclusions,
            manual_occurrence_exclusions=self._manual_occurrence_exclusions,
            detrend=self.checkDetrend.isChecked(),
            despike_noise=self.checkDespikeNoise.isChecked(),
            force_zero_intercept=self.checkForceZeroIntercept.isChecked(),
            bias_specs=bias_specs,
            isotope_share_specs=isotope_share_specs,
            pool_specs=pool_specs,
            dating_ratio_specs=dating_ratio_specs,
            deconvolution_settings=self._current_deconvolution_settings(),
            ablation_onset_trim_s=self.spinAblationOnsetTrim.value(),
        )

        self.actionRun.setEnabled(False)
        self.actionReprocess.setEnabled(False)
        self.labelRunStatus.setText("Reprocessing...")
        self._worker = _PipelineWorker(pipeline.run_from_parsed, kwargs, parent=self)
        self._worker.finished_ok.connect(self._on_run_finished)
        self._worker.failed.connect(self._on_run_failed)
        self._worker.start()

    def _on_run_failed(self, message: str):
        self.actionRun.setEnabled(True)
        self.actionReprocess.setEnabled(True)
        self.labelRunStatus.setText(f"Failed: {message}")
        QMessageBox.critical(self, "Run pipeline", message)

    def _on_run_finished(self, raw_results: dict):
        self.actionRun.setEnabled(True)
        self.actionReprocess.setEnabled(True)
        self.results = {}
        if self.checkBoxBatchMode.isChecked():
            for folder_name, folder_results in raw_results.items():
                for label, result in folder_results.items():
                    self.results[f"{folder_name} / {label}"] = result
        else:
            self.results = dict(raw_results)

        self.labelRunStatus.setText(f"Done: {len(self.results)} sample result(s).")
        # Union in every standard label used across all results (not just
        # sample-result keys) so a standard-only label (never itself a
        # sample folder) stays selectable to focus the file table on --
        # _current_result() gracefully returns None for those, which every
        # other tab refresher already handles.
        standard_labels = {lbl for r in self.results.values() for lbl in r.standard_results}
        current = self.comboBoxSampleResult.currentText()
        self.comboBoxSampleResult.blockSignals(True)
        self.comboBoxSampleResult.clear()
        self.comboBoxSampleResult.addItem("(all)")
        self.comboBoxSampleResult.addItems(sorted(set(self.results) | standard_labels))
        # "(all)" is never a meaningful prior selection to restore post-Run
        # -- treat it the same as "nothing selected yet" so the preference
        # for landing on a real sample result (below) actually applies.
        idx = self.comboBoxSampleResult.findText(current) if current != "(all)" else -1
        if idx < 0:
            # Prefer landing on an actual sample result (so tabs populate
            # immediately) over the "(all)" placeholder, when one exists.
            idx = self.comboBoxSampleResult.findText(sorted(self.results)[0]) if self.results else 0
        self.comboBoxSampleResult.setCurrentIndex(max(idx, 0))
        self.comboBoxSampleResult.blockSignals(False)
        self._on_sample_selected()
        self._populate_file_table()
        self._refresh_time_series_tab()

    # ------------------------------------------------------------------
    # Results viewer
    # ------------------------------------------------------------------
    def _current_result(self) -> SampleCalibratedResult | None:
        key = self.comboBoxSampleResult.currentText()
        return self.results.get(key)

    @staticmethod
    def _draw(canvas):
        """``canvas.draw()`` alone schedules a Qt repaint for the next
        event-loop iteration but doesn't force one -- on some platforms
        that iteration doesn't happen promptly, leaving a tab's plot
        visually stale (still showing the previous analyte/state) even
        though its data already updated, until something else (e.g.
        switching tabs) triggers a repaint. ``flush_events()`` forces the
        pending repaint through immediately instead of waiting for it."""
        canvas.draw()
        canvas.flush_events()

    def _refresh_active_tab(self):
        """Refreshes whichever results tab is currently visible -- the
        counterpart to the shared analyte selector and the shared plot
        controls (offset/log-scale/stage), all of which are wired to this
        instead of to each analyte-dependent tab directly. Timing/Files and
        Data don't depend on the selected analyte, so they're omitted."""
        refreshers = {
            self.TAB_BACKGROUND: self._refresh_background_tab,
            self.TAB_TIME_SERIES: self._refresh_time_series_tab,
            self.TAB_STANDARDS: self._refresh_standards_tab,
            self.TAB_CALIBRATION_CURVE: self._refresh_calibration_curve_tab,
            self.TAB_ISOTOPE_RATIOS: self._refresh_isotope_ratios_tab,
            self.TAB_MAPS: self._refresh_map_tab,
        }
        refresh = refreshers.get(self.tabs.currentIndex())
        if refresh is not None:
            refresh()

    def _on_sample_selected(self):
        result = self._current_result()
        if result is None:
            return

        analytes = sorted(result.calibrated_ppm.columns) if not result.calibrated_ppm.empty else []

        self.analyte_list.blockSignals(True)
        self.analyte_list.setItems(analytes)
        self.analyte_list.blockSignals(False)

        self.comboStandardLabel.blockSignals(True)
        self.comboStandardLabel.clear()
        self.comboStandardLabel.addItems(sorted(result.standard_results))
        self.comboStandardLabel.blockSignals(False)

        self.comboIsotopeRatioPair.blockSignals(True)
        self.comboIsotopeRatioPair.clear()
        self.comboIsotopeRatioPair.addItems(sorted(set(result.bias_fits) | set(result.dating_ratio_fits)))
        self.comboIsotopeRatioPair.blockSignals(False)

        self._refresh_timing_tab()
        self._refresh_background_tab()
        self._refresh_standards_tab()
        self._refresh_calibration_curve_tab()
        self._refresh_isotope_ratios_tab()
        self._refresh_map_tab()
        self._refresh_data_tab()
        self._refresh_deconvolution_tab()
        self._refresh_classification_tab()

    def _refresh_timing_tab(self):
        result = self._current_result()
        if result is None:
            return
        df = diagnostics.build_timing_report_df(result.files, result.backgrounds)
        _populate_table(self.tableTiming, df)

    def _refresh_background_tab(self):
        result = self._current_result()
        analyte = self.analyte_list.currentText()
        if result is None or not analyte:
            return
        self.canvasBackground.axes.clear()
        drift_fit = result.session_background_drift.get(analyte)
        groups = {result.sample_label: result.backgrounds}
        groups.update({label: [occ.background for occ in sr.occurrences] for label, sr in result.standard_results.items()})
        diagnostics.plot_background_drift(
            self.canvasBackground.axes, groups, drift_fit, analyte,
            reference_labels=set(result.standard_results),
        )
        self._draw(self.canvasBackground)

        provenance_counts: dict[str, int] = {}
        l_c_values, l_d_values = [], []
        for b in result.backgrounds:
            provenance = b.tau_provenance.get(analyte, "unknown")
            provenance_counts[provenance] = provenance_counts.get(provenance, 0) + 1
            limits = b.currie.get(analyte)
            if limits is not None:
                l_c_values.append(limits.L_C_cps)
                l_d_values.append(limits.L_D_cps)

        provenance_text = ", ".join(f"{k}: {v}" for k, v in sorted(provenance_counts.items()))
        if l_d_values:
            self.labelDetectionLimits.setText(
                f"Detection limits (Currie): L_C ≈ {np.median(l_c_values):.3g} CPS (median), "
                f"L_D ≈ {np.median(l_d_values):.3g} CPS (median) across {len(l_d_values)} file(s). "
                f"Counting-time provenance: {provenance_text}."
            )
        else:
            self.labelDetectionLimits.setText(
                f"Detection limits unavailable for {analyte} (counting time unresolved in every file). "
                f"Counting-time provenance: {provenance_text}."
            )

    def _on_standard_label_changed(self):
        self._refresh_standards_tab()

    def _refresh_standards_tab(self):
        result = self._current_result()
        label = self.comboStandardLabel.currentText()
        analyte = self.analyte_list.currentText()
        if result is None or not label or not analyte or label not in result.standard_results:
            return
        standard_result = result.standard_results[label]

        # plot_standard_vs_reference adds a twinx() secondary axis for the
        # CPS overlay -- axes.clear() alone wouldn't remove it (same
        # pitfall as the Maps tab's colorbar axis), so clear the whole
        # figure and rebuild the primary subplot fresh each time.
        self.canvasStandardVsReference.fig.clear()
        self.canvasStandardVsReference.axes = self.canvasStandardVsReference.fig.add_subplot(111)
        manual_override = {
            o.occurrence_order for o in standard_result.occurrences
            if analyte in self._manual_occurrence_exclusions.get(o.file_meta.path.name, set())
        }
        self._standards_point_index = diagnostics.plot_standard_vs_reference(
            self.canvasStandardVsReference.axes, standard_result, analyte,
            manually_excluded_override=manual_override, mask_display=self._mask_display_mode(),
        )
        self._draw(self.canvasStandardVsReference)
        self.toolbarStandardVsReference.update()

        fit_df = diagnostics.build_accuracy_table_df(standard_result.accuracy_table, standard_result.excluded_outliers)
        _populate_table(self.tableAccuracyFit, fit_df)
        if standard_result.holdout_accuracy_table is not None:
            holdout_df = diagnostics.build_accuracy_table_df(standard_result.holdout_accuracy_table, standard_result.excluded_outliers)
        else:
            holdout_df = pd.DataFrame()
        _populate_table(self.tableAccuracyHoldout, holdout_df)

    def _refresh_calibration_curve_tab(self):
        self.canvasCalibrationCurve.axes.clear()
        result = self._current_result()
        analyte = self.analyte_list.currentText()
        if result is None or not analyte or result.multi_standard_calibration is None:
            self.canvasCalibrationCurve.axes.set_title(
                "No multi-point calibration -- select 2+ Primary standards to enable this tab."
            )
            self._draw(self.canvasCalibrationCurve)
            return
        curve = result.multi_standard_calibration.curves.get(analyte)
        if curve is None:
            self.canvasCalibrationCurve.axes.set_title(f"{analyte}: no calibration curve")
            self._draw(self.canvasCalibrationCurve)
            return
        diagnostics.plot_multi_point_calibration(self.canvasCalibrationCurve.axes, curve, analyte)
        self._draw(self.canvasCalibrationCurve)

    def _refresh_isotope_ratios_tab(self):
        result = self._current_result()
        pair = self.comboIsotopeRatioPair.currentText()

        self.canvasIsotopeBiasFit.axes.clear()
        # Full figure clear (not just axes.clear()) -- plot_index_map adds a
        # colorbar as its own Axes, same pitfall as the Maps tab.
        self.canvasIsotopeRatioMap.fig.clear()
        self.canvasIsotopeRatioMap.axes = self.canvasIsotopeRatioMap.fig.add_subplot(111)

        if result is None or not pair or (pair not in result.bias_fits and pair not in result.dating_ratio_fits):
            self.canvasIsotopeBiasFit.axes.set_title(
                "No fit available -- select 'Isotopic (mass-bias corrected)' for an element in the "
                "Isotope calibration table, or a system in Radiometric dating ratios, check a Bias "
                "standard, then Run."
            )
            self._draw(self.canvasIsotopeBiasFit)
            self._draw(self.canvasIsotopeRatioMap)
            self.toolbarIsotopeRatioMap.update()
            return

        if pair in result.bias_fits:
            diagnostics.plot_bias_fit(self.canvasIsotopeBiasFit.axes, result.bias_fits[pair], result.standard_results)
            map_title = f"{pair}: mass-bias-corrected ratio"
        else:
            diagnostics.plot_dating_ratio_fit(self.canvasIsotopeBiasFit.axes, result.dating_ratio_fits[pair], result.standard_results)
            map_title = f"{pair}: dating ratio"
        self._draw(self.canvasIsotopeBiasFit)
        self.toolbarIsotopeBiasFit.update()

        # calibrated_ratios columns use LaME's "<num> / <den>" convention
        # (spaces around the slash) -- bias_fits/dating_ratio_fits keys
        # don't (see massbias.fit_session_bias/dating_ratios.
        # fit_session_dating_ratios/pipeline._build_calibrated_ratios).
        ratio_col = pair.replace("/", " / ")
        series = result.calibrated_ratios[ratio_col] if ratio_col in result.calibrated_ratios.columns else pd.Series(dtype=float)
        diagnostics.plot_index_map(
            self.canvasIsotopeRatioMap.axes, series, result.grid_index,
            title=map_title, cbar_label="ratio",
            log_scale=self.checkLogScale.isChecked(),
        )
        self._draw(self.canvasIsotopeRatioMap)
        self.toolbarIsotopeRatioMap.update()

    # ------------------------------------------------------------------
    # Point masking (click to toggle one point, click-and-drag a rectangle
    # to toggle a group) on the Time Series and Standards QC canvases.
    # Hit-testing is done against the point-index DataFrames
    # plot_time_series/plot_standard_vs_reference return (stashed as
    # self._time_series_point_index/_standards_point_index by their
    # respective refresh methods) -- diagnostics.py stays pure/PyQt-free,
    # all mpl_connect wiring lives here. Toggling only updates
    # self._manual_row_exclusions/_manual_occurrence_exclusions and
    # immediately re-renders for visual feedback; it does NOT recompute
    # background/drift/calibration statistics -- that only happens on the
    # next Run (see pipeline.run's own manual_row_exclusions/
    # manual_occurrence_exclusions parameters).
    # ------------------------------------------------------------------
    _DRAG_THRESHOLD_PX = 5.0
    _CLICK_TOLERANCE_PX = 8.0

    def _connect_canvas_interactions(self):
        # source -> toolbar, so click/drag point-masking can defer to the
        # toolbar's own zoom/pan rubber-band interaction instead of running
        # alongside it -- two independent rectangle-overlay draws (the
        # toolbar's native rubber-band paint and our own Rectangle artist +
        # draw_idle()) racing on the same Qt canvas during the same drag
        # caused a real, reproducible segfault (EXC_BAD_ACCESS) when zooming
        # on Time Series.
        self._canvas_toolbars = {
            "time_series": self.toolbarTimeSeries, "standards": self.toolbarStandardVsReference,
        }
        for canvas, source in (
            (self.canvasTimeSeries, "time_series"), (self.canvasStandardVsReference, "standards"),
        ):
            canvas.mpl_connect("button_press_event", lambda e, s=source: self._on_canvas_press(e, s))
            canvas.mpl_connect("motion_notify_event", lambda e, s=source: self._on_canvas_motion(e, s))
            canvas.mpl_connect("button_release_event", lambda e, s=source: self._on_canvas_release(e, s))

    def _on_canvas_press(self, event, source: str):
        if not self.checkEditMode.isChecked():
            return  # point masking only responds to clicks in Edit mode
        toolbar = self._canvas_toolbars.get(source)
        if toolbar is not None and toolbar.mode:
            return  # zoom/pan tool is active -- let the toolbar handle this drag alone
        if event.inaxes is None or event.xdata is None:
            return
        self._drag_canvas = source
        self._drag_start_px = (event.x, event.y)
        self._drag_start_data = (event.xdata, event.ydata)
        self._drag_axes = event.inaxes

    def _on_canvas_motion(self, event, source: str):
        if self._drag_canvas != source or self._drag_start_px is None or event.xdata is None:
            return
        dx = event.x - self._drag_start_px[0]
        dy = event.y - self._drag_start_px[1]
        if (dx * dx + dy * dy) ** 0.5 < self._DRAG_THRESHOLD_PX:
            return
        x0, y0 = self._drag_start_data
        x1, y1 = event.xdata, event.ydata
        if self._drag_rect_artist is not None:
            self._drag_rect_artist.remove()
        self._drag_rect_artist = Rectangle(
            (min(x0, x1), min(y0, y1)), abs(x1 - x0), abs(y1 - y0),
            fill=False, edgecolor="black", linestyle="--", linewidth=1,
        )
        self._drag_axes.add_patch(self._drag_rect_artist)
        self._drag_axes.figure.canvas.draw_idle()

    def _on_canvas_release(self, event, source: str):
        if self._drag_canvas != source or self._drag_start_px is None:
            return
        start_px, start_data, axes = self._drag_start_px, self._drag_start_data, self._drag_axes
        rect_artist = self._drag_rect_artist
        self._drag_canvas = None
        self._drag_start_px = None
        self._drag_start_data = None
        self._drag_axes = None
        self._drag_rect_artist = None
        if rect_artist is not None:
            rect_artist.remove()
            axes.figure.canvas.draw_idle()

        if event.xdata is None or event.inaxes is None:
            return
        dx = event.x - start_px[0]
        dy = event.y - start_px[1]
        is_drag = (dx * dx + dy * dy) ** 0.5 >= self._DRAG_THRESHOLD_PX

        if source == "time_series":
            df = self._time_series_point_index
        else:
            df = self._standards_point_index
            if df is not None and not df.empty:
                df = df[df["series"] == "ppm"]  # CPS overlay points are read-only

        if is_drag:
            selected = self._points_in_rect(df, start_data[0], start_data[1], event.xdata, event.ydata)
        else:
            idx = self._nearest_point(df, axes, event.x, event.y, self._CLICK_TOLERANCE_PX)
            selected = df.loc[[idx]] if idx is not None else df.iloc[0:0]

        if selected.empty:
            return
        if source == "time_series":
            self._toggle_time_series_points(selected)
        else:
            self._toggle_standards_points(selected)

    @staticmethod
    def _to_numeric_x(series: pd.Series) -> np.ndarray:
        if pd.api.types.is_datetime64_any_dtype(series):
            import matplotlib.dates as mdates
            return mdates.date2num(series)
        return series.to_numpy(dtype=float)

    def _nearest_point(self, df: pd.DataFrame | None, ax, px_x: float, px_y: float, tolerance_px: float):
        if df is None or df.empty:
            return None
        x_num = self._to_numeric_x(df["x"])
        xy_data = np.column_stack([x_num, df["y"].to_numpy(dtype=float)])
        xy_px = ax.transData.transform(xy_data)
        d = np.hypot(xy_px[:, 0] - px_x, xy_px[:, 1] - px_y)
        i = int(np.argmin(d))
        return df.index[i] if d[i] <= tolerance_px else None

    def _points_in_rect(self, df: pd.DataFrame | None, x0: float, y0: float, x1: float, y1: float) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame() if df is None else df.iloc[0:0]
        x_num = self._to_numeric_x(df["x"])
        lo_x, hi_x = min(x0, x1), max(x0, x1)
        lo_y, hi_y = min(y0, y1), max(y0, y1)
        y_num = df["y"].to_numpy(dtype=float)
        mask = (x_num >= lo_x) & (x_num <= hi_x) & (y_num >= lo_y) & (y_num <= hi_y)
        return df[mask]

    def _toggle_time_series_points(self, selected: pd.DataFrame):
        # Consistency rule (matches the Use-all/View-all toggle buttons):
        # if any selected point is already manually excluded, un-exclude
        # the whole group; otherwise exclude the whole group. A single
        # click is just a group of one, so this also covers plain toggling.
        currently_excluded = [
            row.row_index in self._manual_row_exclusions.get(row.filename, {}).get(row.analyte, set())
            for row in selected.itertuples()
        ]
        target_excluded = not all(currently_excluded)
        for row in selected.itertuples():
            s = self._manual_row_exclusions.setdefault(row.filename, {}).setdefault(row.analyte, set())
            if target_excluded:
                s.add(row.row_index)
            else:
                s.discard(row.row_index)
        self.labelRunStatus.setText("Manual point exclusions changed -- click Run to apply.")
        self._refresh_time_series_tab()

    def _toggle_standards_points(self, selected: pd.DataFrame):
        result = self._current_result()
        label = self.comboStandardLabel.currentText()
        if result is None or label not in result.standard_results:
            return
        occ_by_order = {o.occurrence_order: o for o in result.standard_results[label].occurrences}
        currently_excluded = []
        targets = []
        for row in selected.itertuples():
            occ = occ_by_order.get(row.occurrence_order)
            if occ is None:
                continue
            filename = occ.file_meta.path.name
            targets.append((filename, row.analyte))
            currently_excluded.append(row.analyte in self._manual_occurrence_exclusions.get(filename, set()))
        if not targets:
            return
        target_excluded = not all(currently_excluded)
        for filename, analyte in targets:
            s = self._manual_occurrence_exclusions.setdefault(filename, set())
            if target_excluded:
                s.add(analyte)
            else:
                s.discard(analyte)
        self.labelRunStatus.setText("Manual point exclusions changed -- click Run to apply.")
        self._refresh_standards_tab()

    def _stage_series(self, result: SampleCalibratedResult, stage: str, analyte: str) -> pd.Series:
        """Reconstructs one correction stage's per-row values, aligned with
        ``result.grid_index``'s (file_index, row_in_ablation) index, so
        ``diagnostics.plot_index_map`` can position them identically to the
        calibrated stage.

        "background+drift correction" combines both corrections into a
        single map stage and displays the *change* they made (corrected
        minus raw), not the corrected value itself. The drift-normalized
        signal alone (background-corrected divided by the standard's drift
        curve) is in standard-relative units, not CPS -- showing it directly
        would look almost identical to raw, just rescaled, and wouldn't
        highlight what the correction actually did. Instead the
        background-corrected signal is rescaled by the drift curve's own
        value at its time origin (``drift_fit.t0``) over its value at the
        sample's time -- a ratio near 1 that keeps the combined correction
        in the same CPS-like units as raw -- so "corrected minus raw"
        isolates the correction's spatial/temporal pattern (background level
        plus the standard-drift adjustment) instead of being swamped by the
        sample signal's own huge dynamic range.

        "deconvolution correction" follows the same "show the change, not
        the corrected value" convention, recomputing src/deconvolution/'s
        shift+washout correction from ``result.deconvolution_settings`` (the
        settings actually used for this run -- falls back to an all-off
        ``DeconvolutionSettings()`` if the run predates that field or
        deconvolution wasn't configured, in which case the map is all
        zeros rather than raising).
        """
        if stage == "calibrated":
            return result.calibrated_ppm[analyte] if analyte in result.calibrated_ppm.columns else pd.Series(dtype=float)

        if result.multi_standard_calibration is not None:
            primary_standard = result.multi_standard_calibration.drift_reference_by_analyte.get(analyte)
        else:
            primary_standards = result.provenance.get("primary_standards") or []
            primary_standard = primary_standards[0] if primary_standards else None
        standard_result = result.standard_results.get(primary_standard) if primary_standard else None
        drift_fit = standard_result.drift_fits.get(analyte) if standard_result else None
        drift_reference_value = float(drift_fit.predict([drift_fit.t0])[0]) if drift_fit is not None else None

        ordered = sorted(zip(result.files, result.backgrounds), key=lambda p: p[0].meta.acquired_at)
        deconvolution_settings = result.deconvolution_settings or DeconvolutionSettings()
        values = []
        index_tuples = []
        for line_number, (line_data, bg) in enumerate(ordered):
            if analyte not in bg.background_corrected_signal.columns:
                continue
            n = len(bg.background_corrected_signal)
            raw = line_data.signal.iloc[bg.ablation.start_idx:bg.ablation.end_idx][analyte].to_numpy()
            if stage == "raw":
                series = raw
            elif stage == "background+drift correction":
                bg_corrected = bg.background_corrected_signal[analyte].to_numpy()
                if drift_fit is not None and drift_reference_value is not None:
                    abl_time = line_data.absolute_time[bg.ablation.start_idx:bg.ablation.end_idx]
                    predicted = drift_fit.predict(abl_time)
                    with np.errstate(divide="ignore", invalid="ignore"):
                        combined = bg_corrected * (drift_reference_value / predicted)
                else:
                    combined = bg_corrected
                series = combined - raw
            elif stage == "deconvolution correction":
                # Recomputed on demand from the stored settings (same
                # "recompute, don't store every intermediate stage"
                # convention as "background+drift correction" above) --
                # shows what shift/washout changed, not the corrected value
                # itself, since the correction is usually small relative to
                # the signal's own dynamic range.
                bg_corrected = bg.background_corrected_signal[analyte].to_numpy()
                line_result = correct_line(
                    bg.background_corrected_signal, line_data.analytes, deconvolution_settings,
                    result.instrument_settings, line_number,
                )
                series = line_result.corrected[analyte].to_numpy() - bg_corrected
            else:
                series = np.full(n, np.nan)
            values.extend(series.tolist())
            index_tuples.extend((line_data.meta.index, i) for i in range(n))

        if not values:
            return pd.Series(dtype=float)
        return pd.Series(values, index=pd.MultiIndex.from_tuples(index_tuples, names=["file_index", "row_in_ablation"]))

    def _refresh_map_tab(self):
        result = self._current_result()
        analyte = self.analyte_list.currentText()
        stage = self.comboMapStage.currentText()
        if result is None or not analyte:
            return
        series = self._stage_series(result, stage, analyte)
        # Full figure clear (not just axes.clear()) -- plot_index_map adds a
        # colorbar as its own Axes, which axes.clear() wouldn't remove,
        # causing colorbars to pile up on repeated redraws.
        self.canvasMap.fig.clear()
        self.canvasMap.axes = self.canvasMap.fig.add_subplot(111)
        diagnostics.plot_index_map(
            self.canvasMap.axes, series, result.grid_index, title=f"{analyte}: {stage}",
            cbar_label=diagnostics.cbar_label_for_stage(stage),
            log_scale=self.checkLogScale.isChecked(),
        )
        self._draw(self.canvasMap)
        # The fig.clear() above destroys the Axes the nav toolbar's home/
        # back/forward stack was tracking -- reset it so Home doesn't
        # reference a since-destroyed Axes after this refresh.
        self.toolbarMap.update()

    def _refresh_data_tab(self):
        result = self._current_result()
        if result is None:
            return
        df = result.calibrated_ppm
        max_rows = 1000
        if len(df) > max_rows:
            self.labelDataNote.setText(f"Showing first {max_rows} of {len(df)} rows.")
            df = df.iloc[:max_rows]
        else:
            self.labelDataNote.setText(f"{len(df)} rows.")
        display_df = df.reset_index()
        _populate_table(self.tableData, display_df)

    def _refresh_deconvolution_tab(self):
        """Not analyte-dependent (summarizes every analyte at once, same as
        _refresh_data_tab) -- called once per sample-result selection, not
        wired into _refresh_active_tab's per-analyte-change dict."""
        result = self._current_result()
        if result is None:
            return
        df = deconv_diagnostics.build_deconvolution_report_df(result.deconvolution_provenance)
        self.canvasDeconvolution.axes.clear()
        if df.empty:
            self.canvasDeconvolution.axes.set_title("No deconvolution applied for this run")
        else:
            deconv_diagnostics.plot_noise_amplification_summary(self.canvasDeconvolution.axes, df)
        self._draw(self.canvasDeconvolution)
        _populate_table(self.tableDeconvolutionReport, df)

    def _refresh_classification_tab(self):
        """Not analyte-dependent (classification's own map is a single
        categorical field, not one-per-analyte) -- called once per sample-
        result selection, not wired into _refresh_active_tab's per-analyte-
        change dict. classification is populated by the Classify button
        (_on_classify), not by a pipeline Run, so this is commonly empty
        immediately after a fresh Run -- that's expected, not an error.
        """
        result = self._current_result()
        self.canvasClassification.axes.clear()
        if result is None or result.classification.empty:
            self.canvasClassification.axes.set_title("No classification run yet for this sample")
            self._draw(self.canvasClassification)
            self.tableClassificationSummary.clear()
            self.tableClassificationSummary.setRowCount(0)
            return

        diagnostics.plot_categorical_map(
            self.canvasClassification.axes, result.classification["label"], result.grid_index,
            result.classification_categories, title=f"{result.sample_label}: mineral classification",
        )
        self._draw(self.canvasClassification)

        classified = result.classification[result.classification["label"].notna()]
        if classified.empty:
            self.tableClassificationSummary.clear()
            self.tableClassificationSummary.setRowCount(0)
            return
        summary = classified.groupby("label").agg(
            pixel_count=("label", "size"), mean_score=("score", "mean"),
            mean_gap=("gap", "mean"), n_ambiguous=("ambiguous", "sum"),
        ).reset_index().rename(columns={"label": "mineral"})
        summary["mean_score"] = summary["mean_score"].round(4)
        summary["mean_gap"] = summary["mean_gap"].round(4)
        summary = summary.sort_values("pixel_count", ascending=False)
        _populate_table(self.tableClassificationSummary, summary)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def _on_export_csv(self):
        result = self._current_result()
        if result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save calibrated CSV", f"{result.sample_label}_calibrated.csv", "CSV (*.csv)")
        if path:
            io_export.export_calibrated_csv(result, path)

    def _on_export_json(self):
        result = self._current_result()
        if result is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save QC report", f"{result.sample_label}_qc_report.json", "JSON (*.json)")
        if path:
            io_export.export_qc_report_json(result, path)
