"""The ROI-only filtering redesign (``src/data/Masking.py``'s ``FilterTab``)
against a real MainWindow.

Covers: no filtering happens before an ROI exists (auto-create on first
"Add filter"), a second filter added while that region stays selected joins
the same region, "Add ROI" starts a genuinely new/empty region, row
selection drives the filter table directly (replacing the old recall
combobox), 0/2+ selected rows both empty the table and block "Add filter"
with a dialog, the ROI context menu's Add/Duplicate/Delete, drag-reorder
persisting back into the active region, and loading a filter *preset* going
through the same ROI gate instead of a region-less filter table.

Headless MainWindow integration tests -- shared setup (QApplication, modal
dialog stubbing, sample files) comes from tests/conftest.py.
"""
import numpy as np
import pytest
from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QMenu

PRESET_NAME = 'muscovite'


@pytest.fixture
def filter_tab(loaded_window, dialogs):
    """``(window, data, ft)`` with the mask dock open and no ROIs yet."""
    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    data = window.app_data.current_data
    assert data is not None

    window.open_mask_dock()
    ft = window.mask_dock.filter_tab
    # Whatever the field-type combo already resolved to for this sample --
    # update_filter_values() has run, so min/max are loaded and clicking
    # "Add filter" adds a real, valid filter.
    assert ft.combo_field_type_type.currentText() and ft.combo_field.currentText(), \
        "no field available to filter on"
    assert data.roi_stack == []
    return window, data, ft


@pytest.fixture
def menu_chooser(monkeypatch):
    """Makes QMenu.exec() pick an action by text instead of blocking.

    ``exec()`` is modal and would hang headless. The stub also records
    ``_active_roi_id()`` at the moment the menu would pop up, which is how
    the row-preselection side effect of ``show_roi_context_menu`` is
    observed -- the state a real user sees before choosing anything.
    """
    state = {'choice': None, 'active_roi_at_exec': 'unset'}
    holder = {}

    def fake_exec(self, *a, **k):
        state['active_roi_at_exec'] = holder['active_roi_id']()
        for action in self.actions():
            if action.text() == state['choice']:
                return action
        return None

    monkeypatch.setattr(QMenu, 'exec', fake_exec)

    def configure(ft, choice):
        holder['active_roi_id'] = ft._active_roi_id
        state['choice'] = choice
        return state

    return configure


def _row_for(ft, roi_id):
    return next(row for row in range(ft.roi_table.rowCount())
                if ft.roi_table.item(row, 1).data(Qt.ItemDataRole.UserRole) == roi_id)


def _select_rows(ft, roi_ids):
    ft.roi_table.clearSelection()
    selection = ft.roi_table.selectionModel()
    for roi_id in roi_ids:
        selection.select(
            ft.roi_table.model().index(_row_for(ft, roi_id), 0),
            selection.SelectionFlag.Select | selection.SelectionFlag.Rows,
        )


def test_first_add_filter_auto_creates_and_selects_an_roi(filter_tab):
    _window, data, ft = filter_tab

    ft._on_add_filter_clicked()

    assert len(data.roi_stack) == 1, data.roi_stack
    assert ft._active_roi_id() == data.roi_stack[0]['id']
    assert len(data.roi_stack[0]['filter_df']) == 1
    assert ft.filter_table.rowCount() == 1


def test_recompute_mask_no_longer_folds_in_the_live_filter_mask(filter_tab):
    """Filtering only takes effect through a committed ROI, so ``self.mask``
    must not depend on ``filter_mask`` at all any more -- toggling
    filter_mask synthetically must leave mask unchanged."""
    _window, data, ft = filter_tab
    ft._on_add_filter_clicked()
    data.filter_df = data.filter_df.iloc[0:0]
    data.apply_field_filters()
    data.recompute_mask()

    mask_before = data.mask.copy()
    data.filter_mask = np.zeros_like(data.filter_mask)
    data.recompute_mask()

    assert np.array_equal(data.mask, mask_before)


def test_second_filter_joins_the_still_selected_roi(filter_tab):
    _window, data, ft = filter_tab
    ft._on_add_filter_clicked()

    ft._on_add_filter_clicked()

    assert len(data.roi_stack) == 1, "a second 'Add filter' must not create a second ROI"
    assert len(data.roi_stack[0]['filter_df']) == 2
    assert ft.filter_table.rowCount() == 2


def test_add_roi_creates_a_new_empty_region_and_selects_it(filter_tab):
    _window, data, ft = filter_tab
    ft._on_add_filter_clicked()

    ft.add_roi()

    assert len(data.roi_stack) == 2, data.roi_stack
    assert ft._active_roi_id() == data.roi_stack[1]['id']
    assert len(data.roi_stack[1]['filter_df']) == 0
    assert ft.filter_table.rowCount() == 0


def test_filters_added_after_add_roi_go_to_the_new_region(filter_tab):
    _window, data, ft = filter_tab
    ft._on_add_filter_clicked()
    ft._on_add_filter_clicked()
    ft.add_roi()

    ft._on_add_filter_clicked()

    assert len(data.roi_stack[1]['filter_df']) == 1
    assert len(data.roi_stack[0]['filter_df']) == 2, "ROI 1 must be unaffected"


def test_selecting_a_row_swaps_the_filter_table_to_that_region(filter_tab):
    _window, data, ft = filter_tab
    ft._on_add_filter_clicked()
    ft._on_add_filter_clicked()
    roi1_id = data.roi_stack[0]['id']
    ft.add_roi()
    roi2_id = data.roi_stack[1]['id']
    ft._on_add_filter_clicked()

    ft._select_roi_row(roi1_id)
    assert ft.filter_table.rowCount() == 2

    ft._select_roi_row(roi2_id)
    assert ft.filter_table.rowCount() == 1


def test_multi_selection_empties_the_table_and_blocks_add_filter(filter_tab, dialogs):
    _window, data, ft = filter_tab
    ft._on_add_filter_clicked()
    ft.add_roi()
    _select_rows(ft, [r['id'] for r in data.roi_stack])

    assert len(ft._selected_roi_ids()) == 2
    assert ft._active_roi_id() is None
    assert ft.filter_table.rowCount() == 0

    dialogs.information_calls.clear()
    ft._on_add_filter_clicked()

    assert len(dialogs.information_calls) == 1, "should show the guidance dialog"
    assert len(data.roi_stack) == 2, "nothing should have been added"


def test_zero_selection_also_blocks_add_filter(filter_tab, dialogs):
    _window, data, ft = filter_tab
    ft._on_add_filter_clicked()
    ft.add_roi()
    ft.roi_table.clearSelection()

    assert ft._active_roi_id() is None
    assert ft.filter_table.rowCount() == 0

    dialogs.information_calls.clear()
    ft._on_add_filter_clicked()

    assert len(dialogs.information_calls) == 1
    assert len(data.roi_stack) == 2


def test_right_click_selects_the_row_then_duplicates_it(filter_tab, menu_chooser, monkeypatch):
    _window, data, ft = filter_tab
    ft._on_add_filter_clicked()
    ft._on_add_filter_clicked()
    roi1_id = data.roi_stack[0]['id']
    ft.roi_table.clearSelection()
    assert ft._active_roi_id() is None

    # rowAt is decoupled from real pixel geometry in an offscreen window.
    monkeypatch.setattr(ft.roi_table, 'rowAt', lambda y: _row_for(ft, roi1_id))
    state = menu_chooser(ft, "Duplicate ROI")
    ft.show_roi_context_menu(QPoint(5, 5))

    assert state['active_roi_at_exec'] == roi1_id, \
        "right-clicking an unselected row should select it before the menu shows"
    assert len(data.roi_stack) == 2
    duplicate = next(r for r in data.roi_stack if r['id'] != roi1_id)
    assert duplicate['name'] == f"{data.roi_stack[0]['name']} copy"
    assert len(duplicate['filter_df']) == 2
    assert ft._active_roi_id() == duplicate['id'], "the new duplicate should end up selected"


def test_context_menu_deletes_every_selected_region(filter_tab, menu_chooser, monkeypatch):
    _window, data, ft = filter_tab
    ft._on_add_filter_clicked()
    roi1_id = data.roi_stack[0]['id']
    ft.add_roi()
    roi2_id = data.roi_stack[1]['id']
    ft.add_roi()
    roi3_id = data.roi_stack[2]['id']

    _select_rows(ft, [roi2_id, roi3_id])
    assert set(ft._selected_roi_ids()) == {roi2_id, roi3_id}

    monkeypatch.setattr(ft.roi_table, 'rowAt', lambda y: _row_for(ft, roi2_id))
    menu_chooser(ft, "Delete 2 ROIs")
    ft.show_roi_context_menu(QPoint(5, 5))

    assert [r['id'] for r in data.roi_stack] == [roi1_id]


def test_right_clicking_empty_space_still_offers_add_roi(filter_tab, menu_chooser, monkeypatch):
    _window, data, ft = filter_tab
    ft._on_add_filter_clicked()

    monkeypatch.setattr(ft.roi_table, 'rowAt', lambda y: -1)
    menu_chooser(ft, "Add ROI")
    ft.show_roi_context_menu(QPoint(5, 200))

    assert len(data.roi_stack) == 2, data.roi_stack


def test_ctrl_click_opens_the_context_menu_via_the_event_filter(filter_tab, menu_chooser,
                                                                 monkeypatch, lame_app):
    """Dispatched through the real Qt pipeline (``QApplication.sendEvent``) so
    the eventFilter installed on ``roi_table.viewport()`` actually has to
    fire -- catching a wrong-widget-installed-on regression that calling
    show_roi_context_menu directly would miss."""
    _window, data, ft = filter_tab
    ft._on_add_filter_clicked()
    roi1_id = data.roi_stack[0]['id']
    ft.roi_table.clearSelection()
    assert ft._active_roi_id() is None

    monkeypatch.setattr(ft.roi_table, 'rowAt', lambda y: _row_for(ft, roi1_id))
    menu_chooser(ft, "Duplicate ROI")
    event = QMouseEvent(
        QEvent.Type.MouseButtonRelease, QPointF(5, 5),
        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier,
    )
    handled = lame_app.sendEvent(ft.roi_table.viewport(), event)

    assert handled, "eventFilter should report the Ctrl+click as handled"
    assert len(data.roi_stack) == 2, "Ctrl+click should have opened the menu and run Duplicate ROI"


def test_drag_reorder_persists_into_the_active_rois_definition(filter_tab):
    """Both filters are added on the same field/bounds, so give them
    distinguishable 'min' values first -- otherwise the reorder isn't
    observable."""
    _window, data, ft = filter_tab
    ft._on_add_filter_clicked()
    ft._on_add_filter_clicked()
    ft._select_roi_row(data.roi_stack[0]['id'])
    assert ft.filter_table.rowCount() == 2

    data.filter_df.at[0, 'min'] = 1.0
    data.filter_df.at[1, 'min'] = 2.0
    ft._sync_active_roi_and_refresh()
    assert list(data.filter_df['min']) == [1.0, 2.0]

    ft._on_filter_rows_moved([1], 0)     # move the 2nd filter row to the front

    assert list(data.filter_df['min']) == [2.0, 1.0]
    assert list(data.roi_stack[0]['filter_df']['min']) == [2.0, 1.0], \
        "reorder must be written back to the active ROI's stored definition"


def _load_preset(ft, name=PRESET_NAME):
    index = ft.combo_filter_presets.findText(name)
    assert index != -1, [ft.combo_filter_presets.itemText(i)
                          for i in range(ft.combo_filter_presets.count())]
    ft.combo_filter_presets.setCurrentIndex(index)
    ft.read_filter_table()


def test_preset_with_zero_rois_auto_creates_a_region(filter_tab):
    """Regression: a preset chosen with no ROI defined used to dump its rows
    straight into a region-less filter table."""
    _window, data, ft = filter_tab

    _load_preset(ft)

    assert len(data.roi_stack) == 1, "loading a preset with zero ROIs must auto-create a region"
    assert ft._active_roi_id() == data.roi_stack[0]['id']
    assert len(data.roi_stack[0]['filter_df']) == 1, data.roi_stack[0]['filter_df']
    assert ft.filter_table.rowCount() == 1


def test_preset_appends_to_the_selected_region(filter_tab):
    _window, data, ft = filter_tab
    _load_preset(ft)

    _load_preset(ft)

    assert len(data.roi_stack) == 1, "a second preset load must not create a new ROI"
    assert len(data.roi_stack[0]['filter_df']) == 2, data.roi_stack[0]['filter_df']


def test_preset_is_blocked_without_a_single_selected_roi(filter_tab, dialogs):
    _window, data, ft = filter_tab
    _load_preset(ft)
    ft.roi_table.clearSelection()
    assert ft._active_roi_id() is None

    dialogs.information_calls.clear()
    _load_preset(ft)

    assert len(dialogs.information_calls) == 1, "should show the guidance dialog"
    assert len(data.roi_stack[0]['filter_df']) == 1, "nothing should be appended"
