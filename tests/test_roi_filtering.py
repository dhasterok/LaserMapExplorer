"""Headless integration check for the ROI-only filtering redesign
(``src/data/Masking.py``'s ``FilterTab``) against a real ``MainWindow``.

Run: .venv/bin/python <this file>

Exercises: no filtering happens before an ROI exists (auto-create on first
"Add filter"), a second filter added while that region stays selected joins
the same region, "Add ROI" starts a genuinely new/empty region, row
selection drives the filter table directly (replacing the old recall
combobox), 0/2+ selected rows both empty the table and block "Add filter"
with a dialog, the ROI context menu's Add/Duplicate/Delete, drag-reorder
persisting back into the active region, and loading a filter *preset*
going through the same ROI gate (auto-create a region with no ROIs,
block on no single selection) instead of a region-less filter table.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

project_root = Path("/Users/dhasterok/Documents/GitHub/LaserMapExplorer")
assert (project_root / 'src' / 'app' / 'MainWindow.py').exists()
sys.path.insert(0, str(project_root))

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

app = QApplication(sys.argv)

import src.app.config  # noqa: F401 -- runs lame_core.config.setup()
from PyQt6.QtWidgets import QMessageBox
_info_calls = []
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)


def _record_information(*args, **kwargs):
    _info_calls.append(args)
    return QMessageBox.StandardButton.Ok


QMessageBox.information = staticmethod(_record_information)

from src.app.MainWindow import MainWindow

RM01 = Path("/Users/dhasterok/maps/processed data/RM01.lame.csv")
assert RM01.exists(), f"missing fixture: {RM01}"

win = MainWindow(app)
pm = win.project_manager
added = pm.add_samples([RM01])
assert added == ['RM01'], added
win.app_data.sample_id = 'RM01'
win.change_sample()
current_data = win.app_data.current_data
assert current_data is not None

win.open_mask_dock()
ft = win.mask_dock.filter_tab

# Pick a real field to filter on -- whatever the field-type combo already
# resolved to for this sample.
field_type = ft.combo_field_type_type.currentText()
field = ft.combo_field.currentText()
assert field_type and field, f"no field available to filter on (field_type={field_type!r}, field={field!r})"
print(f"PASS: using field_type={field_type!r} field={field!r} for this run")


def add_one_filter():
    """Mirrors clicking 'Add filter' with whatever min/max are currently
    loaded in the tool group (update_filter_values already ran for the
    field above)."""
    ft._on_add_filter_clicked()


# --- no ROI exists yet: first "Add filter" auto-creates one ---
assert current_data.roi_stack == []
add_one_filter()
assert len(current_data.roi_stack) == 1, current_data.roi_stack
roi1_id = current_data.roi_stack[0]['id']
assert ft._active_roi_id() == roi1_id
assert len(current_data.roi_stack[0]['filter_df']) == 1
assert ft.filter_table.rowCount() == 1
print("PASS: 'Add filter' with zero ROIs auto-creates one, selects it, and adds the filter to it")

# --- no filtering happens outside a committed ROI: with roi_mask_enabled
#     and the region selected (so its own filter narrows roi_selection_mask),
#     the combined mask should differ from an all-True crop-only baseline
#     unless the filter bounds happen to already cover the full range. To
#     directly check "filter_component is gone", confirm recompute_mask
#     no longer references filter_mask by construction: an empty filter_df
#     (no ROI at all) must never narrow self.mask on its own.
current_data.filter_df = current_data.filter_df.iloc[0:0]
current_data.apply_field_filters()
current_data.recompute_mask()
assert bool(current_data.filter_mask.all()) is False or True  # filter_mask itself may or may not be all-True; not the point
# The real assertion: mask does NOT depend on filter_mask any more -- toggle
# filter_mask synthetically and confirm mask is unaffected.
import numpy as np
mask_before = current_data.mask.copy()
current_data.filter_mask = np.zeros_like(current_data.filter_mask)
current_data.recompute_mask()
assert np.array_equal(current_data.mask, mask_before), "self.mask must not depend on filter_mask any more"
print("PASS: recompute_mask no longer folds the live filter_mask into self.mask")

# restore filter_df/mask state for the rest of the script
ft._on_roi_selection_changed()  # no-op reload since roi1 is still selected... but selection may have changed above
ft._select_roi_row(roi1_id)

# --- adding a second filter while ROI 1 stays selected joins the same region ---
add_one_filter()
assert len(current_data.roi_stack) == 1, "a second 'Add filter' with ROI 1 still selected must not create ROI 2"
assert len(current_data.roi_stack[0]['filter_df']) == 2, current_data.roi_stack[0]['filter_df']
assert ft.filter_table.rowCount() == 2
print("PASS: a second filter added while the same ROI is selected joins that ROI's definition")

# --- "Add ROI" starts a new, empty region and selects it ---
ft.add_roi()
assert len(current_data.roi_stack) == 2, current_data.roi_stack
roi2_id = current_data.roi_stack[1]['id']
assert ft._active_roi_id() == roi2_id
assert len(current_data.roi_stack[1]['filter_df']) == 0
assert ft.filter_table.rowCount() == 0
print("PASS: 'Add ROI' creates a new empty region and selects it")

add_one_filter()
assert len(current_data.roi_stack[1]['filter_df']) == 1
assert len(current_data.roi_stack[0]['filter_df']) == 2, "ROI 1 must be unaffected by filters added to ROI 2"
print("PASS: a filter added after 'Add ROI' goes into the new region, not the old one")

# --- row selection drives the filter table directly ---
ft._select_roi_row(roi1_id)
assert ft.filter_table.rowCount() == 2, "selecting ROI 1's row should reload its 2 filters"
ft._select_roi_row(roi2_id)
assert ft.filter_table.rowCount() == 1, "selecting ROI 2's row should reload its 1 filter"
print("PASS: selecting a different ROI row swaps the filter table to that region's filters")

# --- multi-select empties the table and blocks 'Add filter' ---
ft.roi_table.selectRow(0)
sel_model = ft.roi_table.selectionModel()
sel_model.select(ft.roi_table.model().index(1, 0), sel_model.SelectionFlag.Select | sel_model.SelectionFlag.Rows)
assert len(ft._selected_roi_ids()) == 2
assert ft._active_roi_id() is None
assert ft.filter_table.rowCount() == 0, "multi-selection should leave the filter table empty"
_info_calls.clear()
add_one_filter()
assert len(_info_calls) == 1, "'Add filter' with multiple ROIs selected should show the guidance dialog"
assert len(current_data.roi_stack) == 2, "nothing should have been added while multiple ROIs are selected"
print("PASS: multi-selecting ROIs empties the filter table and blocks 'Add filter' with a dialog")

# --- zero-selection also blocks 'Add filter' ---
ft.roi_table.clearSelection()
assert ft._active_roi_id() is None
assert ft.filter_table.rowCount() == 0
_info_calls.clear()
add_one_filter()
assert len(_info_calls) == 1
assert len(current_data.roi_stack) == 2
print("PASS: zero ROIs selected also blocks 'Add filter' with the same dialog")

# --- context menu (show_roi_context_menu itself, not just the backend
#     methods it calls) -- QMenu.exec() is modal and would hang headless,
#     so it's monkeypatched to immediately "choose" whichever action text
#     matches; roi_table.rowAt is monkeypatched too, to decouple from real
#     pixel geometry in an offscreen window.
from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QMenu as _QMenu

_chosen_text = {'value': None}
_active_id_at_exec = {'value': 'unset'}
_orig_menu_exec = _QMenu.exec


def _fake_menu_exec(self, *a, **k):
    # Captures the row-preselection side effect show_roi_context_menu
    # performs *before* building/showing the menu -- i.e. the state a real
    # user would see the moment the menu pops up, before choosing anything.
    _active_id_at_exec['value'] = ft._active_roi_id()
    for action in self.actions():
        if action.text() == _chosen_text['value']:
            return action
    return None


_QMenu.exec = _fake_menu_exec

# right-click ROI 1's row (currently not selected -- selection is still
# ROI 2 from the zero-selection test above having been cleared, then never
# reselected) should select it as a side effect, then Duplicate it.
ft.roi_table.clearSelection()
assert ft._active_roi_id() is None
_row_for_roi1 = next(row for row in range(ft.roi_table.rowCount())
                      if ft.roi_table.item(row, 1).data(Qt.ItemDataRole.UserRole) == roi1_id)
ft.roi_table.rowAt = lambda y: _row_for_roi1
_chosen_text['value'] = "Duplicate ROI"
ft.show_roi_context_menu(QPoint(5, 5))
assert _active_id_at_exec['value'] == roi1_id, "right-clicking an unselected row should select it before the menu shows"
assert len(current_data.roi_stack) == 3
dup_id = next(r['id'] for r in current_data.roi_stack if r['id'] not in (roi1_id, roi2_id))
dup_entry = next(r for r in current_data.roi_stack if r['id'] == dup_id)
assert dup_entry['name'] == f"{current_data.roi_stack[0]['name']} copy"
assert len(dup_entry['filter_df']) == 2
assert ft._active_roi_id() == dup_id, "the new duplicate should end up selected"
print("PASS: right-click selects the row under the cursor, then Duplicate ROI works end-to-end")

# multi-select ROI 2 + the duplicate, right-click, Delete -> both removed
ft.roi_table.clearSelection()
sel_model = ft.roi_table.selectionModel()
for rid in (roi2_id, dup_id):
    row = next(r for r in range(ft.roi_table.rowCount())
               if ft.roi_table.item(r, 1).data(Qt.ItemDataRole.UserRole) == rid)
    sel_model.select(ft.roi_table.model().index(row, 0), sel_model.SelectionFlag.Select | sel_model.SelectionFlag.Rows)
assert set(ft._selected_roi_ids()) == {roi2_id, dup_id}
_chosen_text['value'] = "Delete 2 ROIs"
ft.show_roi_context_menu(QPoint(5, 5))
assert [r['id'] for r in current_data.roi_stack] == [roi1_id]
print("PASS: right-click on a multi-selection deletes every selected region via the context menu")

# empty space: only "Add ROI" is meaningful
ft.roi_table.rowAt = lambda y: -1
_chosen_text['value'] = "Add ROI"
ft.show_roi_context_menu(QPoint(5, 200))
assert len(current_data.roi_stack) == 2, current_data.roi_stack
print("PASS: right-clicking empty space still offers (and runs) 'Add ROI'")

# --- Ctrl+click (the eventFilter path, not a direct show_roi_context_menu
#     call) also opens the menu -- dispatched through the real Qt event
#     pipeline (QApplication.sendEvent) so the installed eventFilter on
#     roi_table.viewport() actually has to fire, not just be called
#     directly, to catch a wrong-widget-installed-on regression.
from PyQt6.QtCore import QEvent, QPointF
from PyQt6.QtGui import QMouseEvent

_row_for_roi1 = next(row for row in range(ft.roi_table.rowCount())
                      if ft.roi_table.item(row, 1).data(Qt.ItemDataRole.UserRole) == roi1_id)
ft.roi_table.rowAt = lambda y: _row_for_roi1
ft.roi_table.clearSelection()
assert ft._active_roi_id() is None
_chosen_text['value'] = "Duplicate ROI"
ctrl_click_event = QMouseEvent(
    QEvent.Type.MouseButtonRelease, QPointF(5, 5),
    Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier,
)
handled = app.sendEvent(ft.roi_table.viewport(), ctrl_click_event)
assert handled, "eventFilter should report the Ctrl+click as handled"
assert len(current_data.roi_stack) == 3, "Ctrl+click should have opened the menu and run Duplicate ROI"
print("PASS: Ctrl+click on roi_table's viewport also opens the context menu (eventFilter path)")

_QMenu.exec = _orig_menu_exec
del ft.roi_table.rowAt  # restore the real bound method

# --- drag-reorder within filter_table persists back into the active ROI ---
# Both of ROI 1's filters were added on the same field/bounds (add_one_filter
# doesn't vary them) -- give them distinguishable 'min' values directly so
# the reorder is actually observable, then reorder and confirm the stored
# ROI definition (not just the live filter_df) reflects the new order.
ft._select_roi_row(roi1_id)
assert ft.filter_table.rowCount() == 2
current_data.filter_df.at[0, 'min'] = 1.0
current_data.filter_df.at[1, 'min'] = 2.0
ft._sync_active_roi_and_refresh()
before_order = list(current_data.filter_df['min'])
assert before_order == [1.0, 2.0]
ft._on_filter_rows_moved([1], 0)  # move the 2nd filter row to the front
after_order_live = list(current_data.filter_df['min'])
after_order_stored = list(current_data.roi_stack[0]['filter_df']['min'])
assert after_order_live == [2.0, 1.0], after_order_live
assert after_order_stored == after_order_live, (
    "reorder must be written back to the active ROI's stored definition", after_order_stored, after_order_live
)
print("PASS: drag-reordering filter_table persists the new order into the active ROI's stored definition")

# --- loading a filter *preset* follows the same ROI gate as "Add filter" ---
# Regression: a preset chosen with no ROI defined used to dump its rows
# straight into a region-less filter table instead of creating a region.
_preset_file = project_root / 'resources' / 'filters' / 'muscovite.fltr'
assert _preset_file.exists(), f"missing preset fixture: {_preset_file}"
_preset_name = _preset_file.stem


def load_preset(name=_preset_name):
    idx = ft.combo_filter_presets.findText(name)
    assert idx != -1, (
        name, [ft.combo_filter_presets.itemText(i) for i in range(ft.combo_filter_presets.count())],
    )
    ft.combo_filter_presets.setCurrentIndex(idx)
    ft.read_filter_table()


# wipe every region so we're back to "no ROI defined yet"
for _rid in [r['id'] for r in current_data.roi_stack]:
    current_data.remove_roi(_rid)
current_data.filter_df = current_data.filter_df.iloc[0:0]
ft.update_roi_table_widget()
ft.roi_table.clearSelection()
assert current_data.roi_stack == []

load_preset()
assert len(current_data.roi_stack) == 1, "loading a preset with zero ROIs must auto-create a region"
preset_roi_id = current_data.roi_stack[0]['id']
assert ft._active_roi_id() == preset_roi_id
assert len(current_data.roi_stack[0]['filter_df']) == 1, current_data.roi_stack[0]['filter_df']
assert ft.filter_table.rowCount() == 1
print("PASS: loading a filter preset with zero ROIs auto-creates a region and loads the preset into it")

load_preset()
assert len(current_data.roi_stack) == 1, "a second preset load with the region still selected must not create a new ROI"
assert len(current_data.roi_stack[0]['filter_df']) == 2, current_data.roi_stack[0]['filter_df']
print("PASS: loading a preset while a single ROI is selected appends it to that region's definition")

ft.roi_table.clearSelection()
assert ft._active_roi_id() is None
_info_calls.clear()
load_preset()
assert len(_info_calls) == 1, "loading a preset with no single ROI selected should show the guidance dialog"
assert len(current_data.roi_stack[0]['filter_df']) == 2, "nothing should be appended when no single ROI is selected"
print("PASS: loading a preset with no single ROI selected is blocked with the same dialog")

print("\nALL ROI-FILTERING TESTS PASSED")
