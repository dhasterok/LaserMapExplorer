"""Map Import dialog construction, outside the full LaME application.

``MapImporter`` reaches into its parent for exactly one thing: a
``.project_manager.add_samples([path])`` call fired after a successful
import (normally supplied by LaME's MainWindow/ProjectManager).
``_StubHost`` below stands in for that.

The automated tests here are construction/wiring smoke checks -- the parsing
logic has its own coverage in tests/test_map_importer_parse_filenames.py,
and the post-import chaining in tests/test_import_chaining.py.

``python tests/test_map_importer.py`` still opens the dialog interactively,
for driving the import by hand against real data; that part can't be
automated, since it waits on a person.
"""
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import sys
from pathlib import Path

import pandas as pd
import pytest
from PyQt6.QtWidgets import QApplication, QCheckBox, QTableWidgetItem, QWidget

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import src.app.config  # noqa: F401 -- runs lame_core.config.setup()
from src.importers.MapImporter import MapImporter, _as_check_state


class _StubProjectManager:
    """Stand-in for ProjectManager, the only thing MapImporter calls on its parent."""

    def __init__(self):
        self.added = []

    def add_samples(self, paths):
        self.added.append(paths)
        return []


class _StubHost(QWidget):
    """A real QWidget (so QDialog parenting works) with a ``.project_manager``."""

    def __init__(self):
        super().__init__()
        self.project_manager = _StubProjectManager()


@pytest.fixture
def importer(qtbot):
    host = _StubHost()
    qtbot.addWidget(host)
    dialog = MapImporter(parent=host)
    qtbot.addWidget(dialog)
    return dialog


def test_dialog_constructs_without_a_main_window(importer):
    assert importer.ok is False
    assert importer.sample_ids in ([], None)


def test_data_type_combo_offers_the_supported_types(importer):
    types = [importer.comboBoxDataType.itemText(i) for i in range(importer.comboBoxDataType.count())]
    assert 'LA-ICP-MS' in types


# Data types the combo offers *and* resources/app_data/standards_list.csv has
# a row for. 'CL' and 'Petrography photo' are deliberately absent: the combo
# offers both, but the CSV has neither ('petrography' there doesn't match the
# combo's 'Petrography photo'), so selecting either raises KeyError out of
# data_type_changed(). That is an app bug, not a test-fixture gap -- covering
# them here would just pin the crash.
WIRED_DATA_TYPES = ['LA-ICP-MS', 'MLA', 'XRF', 'SEM']


@pytest.mark.parametrize("data_type", WIRED_DATA_TYPES)
def test_switching_data_type_repopulates_the_metadata_table(importer, data_type):
    """data_type_changed() drives the table layout; it must not raise, and
    must leave a usable table behind."""
    importer.comboBoxDataType.setCurrentText(data_type)
    assert importer.tableWidgetMetadata.columnCount() > 0


def test_method_combo_swaps_sweep_speed_for_length_width(importer):
    """TOF reports the raster's physical extent directly; quadrupole/SF
    report spot size + sweep + stage speed, from which spacing is derived."""
    importer.comboBoxDataType.setCurrentText('LA-ICP-MS')

    importer.comboBoxMethod.setCurrentText('TOF')
    importer.update_method_columns()
    headers = [importer.tableWidgetMetadata.horizontalHeaderItem(c).text()
               for c in range(importer.tableWidgetMetadata.columnCount())]
    assert any('Length' in h for h in headers)
    assert any('Width' in h for h in headers)

    importer.comboBoxMethod.setCurrentText('quadrupole')
    importer.update_method_columns()
    headers = [importer.tableWidgetMetadata.horizontalHeaderItem(c).text()
               for c in range(importer.tableWidgetMetadata.columnCount())]
    assert any('Sweep' in h for h in headers)
    assert any('Speed' in h for h in headers)




# --- loading a saved metadata ("parameters") CSV -----------------------------
#
# Regression: update_table_row() wrote a QTableWidgetItem into *every* cell it
# didn't recognise as a QComboBox, including the checkbox columns. CustomTable-
# Widget.to_dataframe() reads item(row, col) first and only falls back to the
# cell widget, so that item permanently shadowed the checkbox and the column
# came back as the strings 'True'/'False'. Two consequences:
#   * import_la_icp_ms_data did .loc[<string series>] -- a *label* lookup, not
#     a mask -- and raised KeyError;
#   * bool('False') is True, so Swap XY / Reverse X / Reverse Y all flipped on.


@pytest.fixture
def populated_importer(importer, tmp_path):
    """An importer with a metadata table for two samples."""
    importer.comboBoxDataType.setCurrentText('LA-ICP-MS')
    importer.root_path = str(tmp_path)
    importer.sample_ids = ['S1', 'S2']
    importer.paths = [str(tmp_path / 'S1'), str(tmp_path / 'S2')]
    importer.populate_table()
    return importer


def _columns(importer):
    table = importer.tableWidgetMetadata
    return {table.horizontalHeaderItem(c).text(): c for c in range(table.columnCount())}


@pytest.mark.parametrize("value, expected", [
    (True, True), (False, False),
    ('True', True), ('False', False),
    ('true', True), ('FALSE', False),
    (1, True), (0, False),
    ('yes', True), ('', False),
    (float('nan'), False),   # bool(nan) is True -- must not mark a blank for import
    (None, False),
])
def test_as_check_state(value, expected):
    assert _as_check_state(value) is expected


def test_get_metadata_returns_bools_for_checkbox_columns(populated_importer):
    data = populated_importer.get_metadata()
    for column in ('Import', 'Swap XY', 'Reverse X', 'Reverse Y'):
        assert data[column].dtype == bool, f"{column} is {data[column].dtype}"


def test_loading_a_metadata_csv_keeps_checkbox_columns_boolean(populated_importer, tmp_path):
    """The reported crash, end to end: configure, save, reload, re-read."""
    table = populated_importer.tableWidgetMetadata
    columns = _columns(populated_importer)
    table.cellWidget(0, columns['Import']).setChecked(True)
    table.cellWidget(1, columns['Import']).setChecked(False)

    saved = populated_importer.get_metadata()
    csv = tmp_path / 'params.csv'
    saved.to_csv(csv, index=False)

    for _, row in pd.read_csv(csv).iterrows():
        populated_importer.update_table_row(
            populated_importer.sample_ids.index(row['Sample ID']), row
        )

    reloaded = populated_importer.get_metadata()
    assert reloaded['Import'].dtype == bool
    assert list(reloaded['Import']) == [True, False]
    # The exact expression from the traceback -- a mask, not a label lookup.
    reloaded.loc[reloaded['Import'], 'Select files'].sum()


def test_loading_a_metadata_csv_does_not_flip_unchecked_boxes(populated_importer, tmp_path):
    """bool('False') is True, so the shadowing item used to turn every
    orientation checkbox on."""
    columns = _columns(populated_importer)
    saved = populated_importer.get_metadata()
    assert not saved['Swap XY'].any()
    csv = tmp_path / 'params.csv'
    saved.to_csv(csv, index=False)

    for _, row in pd.read_csv(csv).iterrows():
        populated_importer.update_table_row(
            populated_importer.sample_ids.index(row['Sample ID']), row
        )

    reloaded = populated_importer.get_metadata()
    assert not reloaded['Swap XY'].any()
    assert not reloaded['Reverse X'].any()
    assert not reloaded['Reverse Y'].any()
    # the live widget, not just the dataframe, must still be unchecked
    assert populated_importer.tableWidgetMetadata.cellWidget(0, columns['Swap XY']).isChecked() is False


def test_update_table_row_restores_widget_state_not_shadowing_items(populated_importer):
    """A checkbox cell must keep its widget as the source of truth -- no item
    written over it."""
    table = populated_importer.tableWidgetMetadata
    columns = _columns(populated_importer)
    # update_table_row matches by position, so build the row in table order.
    row = pd.Series({
        table.horizontalHeaderItem(c).text(): 'True' for c in range(table.columnCount())
    })

    populated_importer.update_table_row(0, row)

    table = populated_importer.tableWidgetMetadata
    assert isinstance(table.cellWidget(0, columns['Import']), QCheckBox)
    assert table.item(0, columns['Import']) is None, \
        "an item here would shadow the checkbox in to_dataframe()"


def test_string_valued_import_column_still_reads_as_a_mask(populated_importer):
    """Defence in depth for a dataframe built before this fix (or by another
    path): get_metadata() coerces, so downstream .loc stays a mask."""
    columns = _columns(populated_importer)
    populated_importer.tableWidgetMetadata.setItem(
        0, columns['Import'], QTableWidgetItem('True')
    )

    data = populated_importer.get_metadata()

    assert data['Import'].dtype == bool
    assert list(data['Import']) == [True, False]


def main():
    """Open the dialog interactively (not a pytest test -- it waits on a person)."""
    app = QApplication(sys.argv)

    host = _StubHost()
    dialog = MapImporter(parent=host)
    dialog.setWindowTitle("Map Import Test Harness")

    result = dialog.exec()

    print(f"[test harness] dialog closed, exec() result={result}, ok={dialog.ok}")
    if dialog.sample_ids:
        print(f"[test harness] root_path={getattr(dialog, 'root_path', None)}")
        print(f"[test harness] sample_ids={dialog.sample_ids}")

    sys.exit(0)


if __name__ == '__main__':
    main()
