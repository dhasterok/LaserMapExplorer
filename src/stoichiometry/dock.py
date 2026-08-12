"""StoichiometryDock: floating QDockWidget UI for the stoichiometric
mineral formula calculator.

Thin by design -- gathers settings, resolves which analyte/oxide columns
in the current sample correspond to the mineral config's needed elements,
runs ``pipeline.calculate`` per pixel, writes results back via
``SampleObj.add_columns('Stoichiometry', ...)``, and renders tables via the
app's existing ``InfoViewer.update_dataframe`` helper. All actual
stoichiometric math lives in the backend modules (``normalize``, ``redox``,
``sites``, ``endmembers``, ``qc``, ``pipeline``) -- this file is the only
one in the package with PyQt imports.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from PyQt6.QtCore import QRect, QSize, Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QScrollArea, QSizePolicy, QSplitter, QTableWidget, QVBoxLayout, QWidget,
)

from lame_core.CustomWidgets import CustomDockWidget
from src.control.FieldLogic import FieldLogicUI
from src.stoichiometry import pipeline, regionstats
from src.stoichiometry.config import MineralConfig, MineralConfigError, load_mineral_config

_ELEMENT_COL_RE = re.compile(r"^([A-Z][a-z]?)(\d+)$")

DEFAULT_GARNET_CONFIG_PATH = "resources/minerals/garnet.yaml"


def _base_element(species: str) -> str:
    """Redox species like 'Fe2'/'Fe3' -> 'Fe'; anything else unchanged.

    Input columns (analyte or oxide) measure total element content, not a
    specific valence species, so column resolution always looks up the base
    element regardless of which site/redox species reference it.
    """
    if len(species) > 1 and species[-1] in "23" and species[:-1].isalpha():
        return species[:-1]
    return species


def _resolve_ppm_columns(config: MineralConfig, available_columns) -> dict[str, str]:
    """Map each element the config needs to a matching isotope-style analyte
    column (e.g. 'Si' -> 'Si29'), by prefix match against ``available_columns``.
    """
    needed = {
        _base_element(el)
        for el in (config.all_site_elements() | set(config.redox.elements) | set(config.trace_elements.structural))
    }
    resolved = {}
    for col in available_columns:
        m = _ELEMENT_COL_RE.match(str(col))
        if not m:
            continue
        el = m.group(1)
        if el in needed and el not in resolved:
            resolved[el] = col
    return resolved


def _resolve_oxide_columns(config: MineralConfig, available_columns) -> dict[str, str]:
    """Map each standard oxide form the config's elements need to a matching
    column, by exact name match (e.g. an XRF-imported 'SiO2' column).
    """
    from src.stoichiometry.normalize import STANDARD_OXIDES

    needed_elements = {_base_element(el) for el in (config.all_site_elements() | set(config.redox.elements))}
    available = set(str(c) for c in available_columns)
    resolved = {}
    for el in needed_elements:
        oxide = STANDARD_OXIDES.get(el)
        if oxide and oxide in available and oxide not in resolved:
            resolved[oxide] = oxide
    return resolved


class StoichiometryDock(CustomDockWidget, FieldLogicUI):
    """Stoichiometric mineral formula calculator (garnet, Phase 1).

    Opens as a floating panel (following ``GeochronDock``/``DiffusionDock``)
    rather than registering into a ``QMainWindow`` dock area.

    Calculations can be restricted to specific ROIs or cluster groups (e.g.
    a garnet formula only makes sense on garnet-bearing pixels): the "Compute
    scope" selector limits which pixels this run touches, and repeated runs
    over different scopes/minerals write into their own columns (per
    mineral) or their own rows (per scope) without clobbering each other --
    see ``_write_results_to_sample`` and ``SampleObj.add_columns(..., merge=True)``.
    """

    _ALL_PIXELS_LABEL = "(All pixels)"

    def __init__(self, ui=None, config_path: str = DEFAULT_GARNET_CONFIG_PATH):
        self.ui = ui
        self.logger_key = "Stoichiometry"

        if not isinstance(ui, QMainWindow):
            raise TypeError("Parent must be an instance of QMainWindow.")

        super().__init__(ui)

        self._last_results: dict = {}
        self._last_mask = None
        self.config: MineralConfig | None = None
        self._config_path = config_path

        self.setWindowTitle("Stoichiometric Calculator")
        self.setObjectName("StoichiometryDock")

        try:
            self.config = load_mineral_config(config_path)
        except MineralConfigError as e:
            self.config = None
            self._config_error = str(e)
        else:
            self._config_error = None

        self.setupUI()
        self.connect_widgets()
        self._refresh_region_columns()
        self.setGeometry(QRect(0, 0, 700, 600))

    @property
    def app_data(self):
        """Delegate to ui.app_data so FieldLogicUI methods work correctly."""
        return self.ui.app_data

    @property
    def data(self):
        """Access current sample data without caching a reference."""
        if hasattr(self.ui, "app_data"):
            return self.ui.app_data.current_data
        return None

    @data.setter
    def data(self, value):
        """Ignored -- data is always derived from ui.app_data.current_data."""
        pass

    # -------------------------------------
    # UI construction
    # -------------------------------------
    def setupUI(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(6, 6, 6, 6)

        mineral_row = QHBoxLayout()
        mineral_row.addWidget(QLabel("Mineral"))
        self.comboBoxMineral = QComboBox()
        self._minerals = self._available_minerals()
        self.comboBoxMineral.addItems(list(self._minerals.keys()))
        for name, path in self._minerals.items():
            if Path(path).resolve() == Path(self._config_path).resolve():
                self.comboBoxMineral.setCurrentText(name)
                break
        mineral_row.addWidget(self.comboBoxMineral, stretch=1)
        outer.addLayout(mineral_row)

        self.labelMineral = QLabel(f"Mineral: {self.config.mineral if self.config else '(config failed to load)'}")
        outer.addWidget(self.labelMineral)
        self.labelConfigError = QLabel(f"Config error: {self._config_error}" if self._config_error else "")
        self.labelConfigError.setStyleSheet("color: red;")
        self.labelConfigError.setVisible(bool(self._config_error))
        outer.addWidget(self.labelConfigError)

        scope_group = QGroupBox("Compute scope")
        scope_layout = QVBoxLayout(scope_group)
        scope_note = QLabel(
            "Restrict this calculation to specific ROIs/clusters (e.g. skip "
            "pixels that aren't this mineral). Different scopes and minerals "
            "can be run separately without overwriting each other's results."
        )
        scope_note.setWordWrap(True)
        scope_layout.addWidget(scope_note)
        scope_row = QHBoxLayout()
        scope_row.addWidget(QLabel("Restrict to"))
        self.comboBoxScopeColumn = QComboBox()
        self.comboBoxScopeColumn.addItem(self._ALL_PIXELS_LABEL)
        scope_row.addWidget(self.comboBoxScopeColumn, stretch=1)
        scope_layout.addLayout(scope_row)
        self.listScopeRegions = QListWidget()
        self.listScopeRegions.setMaximumHeight(100)
        self.listScopeRegions.setVisible(False)
        scope_layout.addWidget(self.listScopeRegions)
        outer.addWidget(scope_group)

        settings_group = QGroupBox("Settings")
        form = QFormLayout(settings_group)

        self.comboBoxInputMode = QComboBox()
        self.comboBoxInputMode.addItems(["ppm", "wt_percent"])
        form.addRow("Input basis", self.comboBoxInputMode)

        self.comboBoxRedoxMethod = QComboBox()
        if self.config:
            self.comboBoxRedoxMethod.addItems(self.config.redox.methods)
            if self.config.redox.default_method:
                self.comboBoxRedoxMethod.setCurrentText(self.config.redox.default_method)
        form.addRow("Redox method", self.comboBoxRedoxMethod)

        self.checkBoxCompareRedox = QPushButton("Compare all redox methods")
        self.checkBoxCompareRedox.setCheckable(True)
        form.addRow("", self.checkBoxCompareRedox)

        self.comboBoxLodTreatment = QComboBox()
        self.comboBoxLodTreatment.addItems(["zero", "half_lod", "exclude"])
        form.addRow("Below-LOD treatment", self.comboBoxLodTreatment)

        outer.addWidget(settings_group)

        self.labelColumnMapping = QLabel("(load a sample to resolve element columns)")
        self.labelColumnMapping.setWordWrap(True)
        outer.addWidget(self.labelColumnMapping)

        self.pushButtonCalculate = QPushButton("Calculate")
        outer.addWidget(self.pushButtonCalculate)

        splitter = QSplitter(Qt.Orientation.Vertical)

        results_group = QGroupBox("Per-pixel results (sample)")
        results_layout = QVBoxLayout(results_group)
        self.tableResults = QTableWidget()
        results_layout.addWidget(self.tableResults)
        splitter.addWidget(results_group)

        summary_group = QGroupBox("Region summary (ROI / cluster)")
        summary_layout = QVBoxLayout(summary_group)
        region_row = QHBoxLayout()
        region_row.addWidget(QLabel("Region source"))
        self.comboBoxRegionColumn = QComboBox()
        self.comboBoxRegionColumn.addItems(["ROI"])
        region_row.addWidget(self.comboBoxRegionColumn)
        summary_layout.addLayout(region_row)
        self.tableSummary = QTableWidget()
        summary_layout.addWidget(self.tableSummary)
        splitter.addWidget(summary_group)

        outer.addWidget(splitter, stretch=1)

        results_row = QHBoxLayout()
        self.textEditResults = QPlainTextEdit()
        self.textEditResults.setReadOnly(True)
        self.textEditResults.setMaximumHeight(120)
        results_row.addWidget(self.textEditResults)
        outer.addLayout(results_row)

        self.pushButtonCopyToNotes = QPushButton("Copy to Notes")
        outer.addWidget(self.pushButtonCopyToNotes)

        scroll_area.setWidget(container)
        dock_layout = QVBoxLayout()
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.addWidget(scroll_area)
        wrapper = QWidget()
        wrapper.setLayout(dock_layout)
        self.setWidget(wrapper)

    def connect_widgets(self):
        self.pushButtonCalculate.clicked.connect(self.calculate)
        self.comboBoxMineral.currentIndexChanged.connect(self._on_mineral_changed)
        self.comboBoxInputMode.currentIndexChanged.connect(self.calculate)
        self.comboBoxRedoxMethod.currentIndexChanged.connect(self.calculate)
        self.comboBoxLodTreatment.currentIndexChanged.connect(self.calculate)
        self.checkBoxCompareRedox.toggled.connect(self.calculate)
        self.comboBoxScopeColumn.currentIndexChanged.connect(self._on_scope_column_changed)
        # Debounced rather than a direct connection: checking/unchecking a batch of
        # regions fires one itemChanged per click, and calculate() writes with
        # merge=True (never clears stale values) -- an un-debounced recompute on
        # every intermediate click would permanently "leak" whichever regions were
        # transiently checked partway through the user's edit, even after they're
        # unchecked in the final state.
        self._scope_debounce = QTimer(self)
        self._scope_debounce.setSingleShot(True)
        self._scope_debounce.timeout.connect(self.calculate)
        self.listScopeRegions.itemChanged.connect(lambda *_: self._scope_debounce.start(300))
        self.comboBoxRegionColumn.currentIndexChanged.connect(self._on_region_column_changed)
        self.pushButtonCopyToNotes.clicked.connect(
            lambda: self.ui.insert_info_note("stoichiometry results"))

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_region_columns()

    # -------------------------------------
    # Mineral selection
    # -------------------------------------
    def _available_minerals(self) -> dict[str, str]:
        """{display name: yaml path} for every mineral config in resources/minerals/."""
        paths = sorted(Path("resources/minerals").glob("*.yaml"))
        return {p.stem.capitalize(): str(p) for p in paths}

    def _on_mineral_changed(self, *_args):
        name = self.comboBoxMineral.currentText()
        path = self._minerals.get(name)
        if not path:
            return
        self._config_path = path
        try:
            self.config = load_mineral_config(path)
            self._config_error = None
        except MineralConfigError as e:
            self.config = None
            self._config_error = str(e)

        self.labelMineral.setText(f"Mineral: {self.config.mineral if self.config else '(config failed to load)'}")
        self.labelConfigError.setText(f"Config error: {self._config_error}" if self._config_error else "")
        self.labelConfigError.setVisible(bool(self._config_error))

        self.comboBoxRedoxMethod.blockSignals(True)
        self.comboBoxRedoxMethod.clear()
        if self.config:
            self.comboBoxRedoxMethod.addItems(self.config.redox.methods)
            if self.config.redox.default_method:
                self.comboBoxRedoxMethod.setCurrentText(self.config.redox.default_method)
        self.comboBoxRedoxMethod.blockSignals(False)

        self.calculate()

    # -------------------------------------
    # Region scope (restrict computation to specific ROIs/clusters)
    # -------------------------------------
    def _available_region_columns(self, data) -> list[str]:
        if data is None:
            return []
        cols = []
        if "ROI" in data.processed.columns:
            cols.append("ROI")
        try:
            methods = self.app_data.cluster_method_options
        except Exception:
            methods = []
        for method in methods:
            if method in data.processed.columns:
                cols.append(method)
        return cols

    def _refresh_region_columns(self):
        """Repopulate the scope/summary region-column combos from the current sample.

        Preserves each combo's current selection when it's still valid (e.g. a
        settings-change recompute shouldn't silently reset which region column
        the user was scoping/summarizing by).
        """
        available = self._available_region_columns(self.data)

        for combo, extra in ((self.comboBoxScopeColumn, [self._ALL_PIXELS_LABEL]), (self.comboBoxRegionColumn, [])):
            current = combo.currentText()
            items = extra + available
            if [combo.itemText(i) for i in range(combo.count())] == items:
                continue
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(items)
            combo.setCurrentText(current if current in items else (items[0] if items else ""))
            combo.blockSignals(False)

        self._refresh_scope_regions()

    def _refresh_scope_regions(self):
        """Repopulate the checkable region-id list for the current scope column.

        Leaves existing check states alone when the available id set hasn't
        changed (e.g. recompute triggered by an unrelated settings change), so
        the user's scope selection survives routine recomputes. New ids default
        to checked (included); ids that disappear are simply dropped.
        """
        column = self.comboBoxScopeColumn.currentText()
        data = self.data

        if column == self._ALL_PIXELS_LABEL or data is None:
            self.listScopeRegions.setVisible(False)
            self.listScopeRegions.blockSignals(True)
            self.listScopeRegions.clear()
            self.listScopeRegions.blockSignals(False)
            return

        if column == "ROI":
            entries = [(0, "Unassigned")] + [(r["id"], r["name"]) for r in data.roi_stack]
        elif column in data.processed.columns:
            ids = sorted(int(v) for v in data.processed[column].dropna().unique() if v != 99)
            entries = [(i, f"Cluster {i}") for i in ids]
        else:
            entries = []

        current_ids = {rid for rid, _ in entries}
        existing_ids = {
            self.listScopeRegions.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.listScopeRegions.count())
        }
        self.listScopeRegions.setVisible(True)
        if current_ids == existing_ids and self.listScopeRegions.count() > 0:
            return

        previous_checked = {
            self.listScopeRegions.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.listScopeRegions.count())
            if self.listScopeRegions.item(i).checkState() == Qt.CheckState.Checked
        }
        had_items_before = self.listScopeRegions.count() > 0

        self.listScopeRegions.blockSignals(True)
        self.listScopeRegions.clear()
        for region_id, label in entries:
            item = QListWidgetItem(f"{label} (id {region_id})")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            checked = (region_id in previous_checked) if had_items_before else True
            item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, region_id)
            self.listScopeRegions.addItem(item)
        self.listScopeRegions.blockSignals(False)

    def _on_scope_column_changed(self, *_args):
        self._refresh_scope_regions()
        # Debounced, not called directly: a freshly-populated region list
        # defaults every item to checked, so an immediate calculate() here
        # would eagerly compute (and permanently, since writes use
        # merge=True) over every region before the user narrows the
        # selection down to the ones they actually want.
        self._scope_debounce.start(300)

    def _on_region_column_changed(self, *_args):
        if self.data is not None and self._last_mask is not None:
            self._populate_summary_table(self.data, self._last_mask)

    def _current_scope_mask(self, data):
        """Boolean array (True = include), or None for '(All pixels)' (no extra restriction)."""
        column = self.comboBoxScopeColumn.currentText()
        if column == self._ALL_PIXELS_LABEL or column not in data.processed.columns:
            return None
        selected_ids = [
            self.listScopeRegions.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.listScopeRegions.count())
            if self.listScopeRegions.item(i).checkState() == Qt.CheckState.Checked
        ]
        if not selected_ids:
            return np.zeros(data.processed.shape[0], dtype=bool)
        return np.isin(data.processed[column].to_numpy(), selected_ids)

    def _scope_description(self) -> str:
        column = self.comboBoxScopeColumn.currentText()
        if column == self._ALL_PIXELS_LABEL or not self.listScopeRegions.isVisible():
            return "All pixels"
        checked = [
            self.listScopeRegions.item(i).text()
            for i in range(self.listScopeRegions.count())
            if self.listScopeRegions.item(i).checkState() == Qt.CheckState.Checked
        ]
        return f"{column}: " + (", ".join(checked) if checked else "(none selected)")

    # -------------------------------------
    # Computation
    # -------------------------------------
    def _resolve_columns(self, input_mode: str) -> dict[str, str]:
        if self.data is None or self.config is None:
            return {}
        columns = self.data.processed.columns
        if input_mode == "ppm":
            return _resolve_ppm_columns(self.config, columns)
        return _resolve_oxide_columns(self.config, columns)

    def calculate(self, *_args):
        """Recompute over the current scope and write results back.

        Called on any settings change (input mode, redox method, LOD
        treatment, compare-methods toggle, or region-scope selection) -- no
        need to close and reopen the dock, or click a separate button, to see
        an updated result. Scoped runs (e.g. one mineral on one cluster,
        another mineral on a different cluster) coexist: see
        ``_write_results_to_sample``.
        """
        if self.config is None:
            QMessageBox.warning(self.ui, "Stoichiometric Calculator", f"Mineral config failed to load: {self._config_error}")
            return
        data = self.data
        if data is None or self.app_data.sample_id == "":
            return

        self._refresh_region_columns()

        input_mode = self.comboBoxInputMode.currentText()
        column_map = self._resolve_columns(input_mode)
        if not column_map:
            self.labelColumnMapping.setText("No matching element/oxide columns found in this sample.")
            return
        self.labelColumnMapping.setText(
            "Using columns: " + ", ".join(f"{el}→{col}" for el, col in sorted(column_map.items()))
        )

        scope_mask = self._current_scope_mask(data)
        base_mask = np.asarray(data.mask)
        mask = base_mask if scope_mask is None else (base_mask & scope_mask)

        if not np.any(mask):
            self.labelColumnMapping.setText(
                self.labelColumnMapping.text() + "\nNo pixels in the selected region scope."
            )
            self._last_mask = None
            return

        n = data.processed.shape[0]
        rows = data.processed.loc[mask, list(column_map.values())]
        rows.columns = list(column_map.keys())

        redox_methods = self.config.redox.methods if self.checkBoxCompareRedox.isChecked() else [self.comboBoxRedoxMethod.currentText()]
        lod_treatment = self.comboBoxLodTreatment.currentText()

        per_method_results: dict[str, list] = {m: [] for m in redox_methods}
        last_result = None
        for _, row in rows.iterrows():
            analysis = {k: float(v) for k, v in row.items() if pd.notna(v)}
            for method in redox_methods:
                try:
                    result = pipeline.calculate(
                        analysis, self.config, input_mode=input_mode,
                        redox_method=method, lod_treatment=lod_treatment,
                    )
                except Exception:
                    result = None
                per_method_results[method].append(result)
                if method == redox_methods[-1]:
                    last_result = result

        primary_method = self.comboBoxRedoxMethod.currentText()
        self._write_results_to_sample(data, mask, per_method_results.get(primary_method, per_method_results[redox_methods[0]]))
        self._populate_results_table(per_method_results, redox_methods)
        self._populate_summary_table(data, mask)
        self._last_mask = mask
        self._last_results = {
            "mineral": self.config.mineral,
            "scope": self._scope_description(),
            "input_mode": input_mode,
            "redox_method": primary_method,
            "lod_treatment": lod_treatment,
            "n_pixels": int(mask.sum()) if hasattr(mask, "sum") else len(rows),
            "summary_df": getattr(self, "_last_summary_df", None),
        }
        self._update_results_text()
        self.ui.schedule_update()

    def _write_results_to_sample(self, data, mask, results: list):
        """Write per-site apfu totals and end-member % back via ``add_columns``.

        Uses ``merge=True`` so this scoped run only touches rows inside
        ``mask`` -- pixels outside it (e.g. a different ROI/cluster computed
        with this same mineral in an earlier run) keep whatever they already
        had instead of being reset to NaN. That's what lets separate
        scoped/mineral runs coexist rather than each overwriting the whole
        column.
        """
        if self.config is None or not results:
            return

        site_names = list(self.config.site_order)
        member_names = list(self.config.end_members.members)
        column_names = [f"apfu_{s}" for s in site_names] + [f"endmember_{m}" for m in member_names]

        arrays = []
        for r in results:
            if r is None:
                arrays.append([np.nan] * len(column_names))
                continue
            row_vals = [r.site_allocation.sites[s].total for s in site_names]
            row_vals += [r.end_members.get(m, np.nan) for m in member_names]
            arrays.append(row_vals)

        array_2d = np.array(arrays, dtype=float)
        mask_arr = mask.values if hasattr(mask, "values") else np.asarray(mask)
        data.add_columns("Stoichiometry", column_names, array_2d, mask=mask_arr, merge=True)

    def _populate_results_table(self, per_method_results, redox_methods):
        from src.app.InfoViewer import update_dataframe

        primary = per_method_results[redox_methods[0]]
        rows = []
        for i, r in enumerate(primary):
            if r is None:
                continue
            row = {"pixel": i}
            for site_name, s in r.site_allocation.sites.items():
                row[f"{site_name} total"] = round(s.total, 4)
            if r.redox is not None:
                row["Fe3+/ΣFe"] = round(
                    r.redox.species_3plus_apfu / (r.redox.species_2plus_apfu + r.redox.species_3plus_apfu), 3
                ) if (r.redox.species_2plus_apfu + r.redox.species_3plus_apfu) > 0 else 0.0
            for member, pct in r.end_members.items():
                row[member] = round(pct, 2)
            rows.append(row)

        if len(redox_methods) > 1:
            for method in redox_methods[1:]:
                for i, r in enumerate(per_method_results[method]):
                    if r is None or i >= len(rows):
                        continue
                    frac = (
                        r.redox.species_3plus_apfu / (r.redox.species_2plus_apfu + r.redox.species_3plus_apfu)
                        if r.redox and (r.redox.species_2plus_apfu + r.redox.species_3plus_apfu) > 0 else 0.0
                    )
                    rows[i][f"Fe3+/ΣFe ({method})"] = round(frac, 3)

        df = pd.DataFrame(rows)
        if not df.empty:
            update_dataframe(df, self.tableResults)

    def _populate_summary_table(self, data, mask):
        value_columns = [c for c in data.processed.columns if c.startswith("apfu_") or c.startswith("endmember_")]
        if not value_columns:
            self._last_summary_df = None
            return
        region_column = self.comboBoxRegionColumn.currentText()
        if region_column not in data.processed.columns:
            self._last_summary_df = None
            return

        # ROI id 0 ("unassigned" -- pixels not claimed by any named region) is
        # kept in the summary so users can see stats for everything outside
        # their defined ROIs, not just inside them. Cluster's id 99 ("mask"
        # placeholder for unclustered pixels) has no comparable meaning and
        # stays excluded.
        exclude_ids = [] if region_column == "ROI" else [99]
        try:
            summary_df = regionstats.region_stats(data.processed, mask, region_column, value_columns, exclude_ids=exclude_ids)
        except Exception:
            self._last_summary_df = None
            return

        self._last_summary_df = summary_df
        from src.app.InfoViewer import update_dataframe
        if not summary_df.empty:
            update_dataframe(summary_df, self.tableSummary)

    def _update_results_text(self):
        r = self._last_results
        if not r:
            return
        lines = [
            f"Mineral: {r['mineral']}",
            f"Scope: {r.get('scope', 'All pixels')}",
            f"Input basis: {r['input_mode']}, redox method: {r['redox_method']}, LOD: {r['lod_treatment']}",
            f"Pixels calculated: {r['n_pixels']}",
        ]
        self.textEditResults.setPlainText("\n".join(lines))
