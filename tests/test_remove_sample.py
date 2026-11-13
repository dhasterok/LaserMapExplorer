"""Removing the current sample from the project.

A File-menu action -- deliberately not on any toolbar, since it throws away
everything derived from the sample and cannot be undone. It confirms first,
naming the sample, and the confirmation defaults to *No* so a stray click
on the menu does nothing.

Nothing is deleted from disk: the sample's ``.lame.csv`` is the user's file.
"""
import numpy as np
import pytest
from PyQt6.QtWidgets import QMessageBox


@pytest.fixture
def two_samples(loaded_window, dialogs, sample_factory):
    """``(window, manager)`` with RM01 and RM02, RM01 selected and loaded."""
    window, _path = loaded_window
    window.project_manager.add_samples([sample_factory('RM02', subdir='b')])
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    return window, window.project_manager


# ---------------------------------------------------------------------------
# the confirmation
# ---------------------------------------------------------------------------
def test_it_asks_before_removing_and_names_the_sample(two_samples, dialogs):
    window, manager = two_samples
    dialogs.question = QMessageBox.StandardButton.No

    manager.remove_current_sample()

    assert dialogs.question_calls, 'no confirmation was shown'
    title, message = dialogs.question_calls[0][1], dialogs.question_calls[0][2]
    assert title == 'Remove Sample'
    assert "'RM01'" in message


def test_no_is_the_default_button(two_samples, dialogs):
    """The menu item and the dialog's buttons land near each other, so the
    safe answer has to be the one already selected."""
    window, manager = two_samples
    dialogs.question = QMessageBox.StandardButton.No

    manager.remove_current_sample()

    default_button = dialogs.question_calls[0][4]
    assert default_button == QMessageBox.StandardButton.No


def test_answering_no_changes_nothing(two_samples, dialogs):
    window, manager = two_samples
    dialogs.question = QMessageBox.StandardButton.No

    assert manager.remove_current_sample() is False

    assert 'RM01' in manager.current_project.samples
    assert 'RM01' in window.data
    assert window.app_data.sample_id == 'RM01'


def test_with_no_sample_there_is_nothing_to_ask(loaded_window, dialogs):
    window, _path = loaded_window
    window.app_data.sample_id = ''

    assert window.project_manager.remove_current_sample() is False
    assert dialogs.question_calls == []


# ---------------------------------------------------------------------------
# what removal takes with it
# ---------------------------------------------------------------------------
@pytest.fixture
def removed(two_samples, dialogs):
    """RM01 removed after a Yes, with derived state on it beforehand."""
    window, manager = two_samples
    data = window.data['RM01']
    data.add_columns('Calculated', 'derived', np.ones(len(data.processed)))
    data.add_map_annotation({
        'type': 'text', 'text': 'note', 'position': [[10.0, 10.0]],
        'style': {'color': '#000', 'font_size': 11.0},
    })
    window.style_data.plot_type = 'field map'
    window.update_SV()
    window.plot_tree.add_tree_item(window.plot_info)
    assert window.plot_registry.get_plots_for_sample('RM01')

    dialogs.question = QMessageBox.StandardButton.Yes
    assert manager.remove_current_sample() is True
    return window, manager


def test_the_sample_leaves_the_project(removed):
    window, manager = removed
    assert 'RM01' not in manager.current_project.samples
    assert list(manager.current_project.samples) == ['RM02']


def test_the_loaded_data_is_released(removed):
    window, _manager = removed
    assert 'RM01' not in window.data


def test_its_plots_go_with_it(removed):
    window, _manager = removed
    assert window.plot_registry.get_plots_for_sample('RM01') == []


def test_it_leaves_the_plot_tree(removed):
    window, _manager = removed
    branch = window.plot_tree.treeView.branch_exists(
        window.plot_tree.tree['Analyte'], 'RM01')
    assert branch is None


def test_it_leaves_the_sample_list(removed):
    window, _manager = removed
    assert 'RM01' not in window.app_data.sample_list
    assert window.app_data.sample_list == ['RM02']


def test_another_sample_is_selected(removed):
    """The removed one was the selection; something has to take its place."""
    window, _manager = removed
    assert window.app_data.sample_id == 'RM02'


def test_the_project_is_marked_dirty(removed):
    _window, manager = removed
    assert manager.current_project.dirty is True


def test_the_data_file_is_not_deleted(two_samples, dialogs, sample_factory):
    """Removing from the project is not deleting the user's data."""
    window, manager = two_samples
    path = manager.current_project.samples['RM01'].sample_path
    dialogs.question = QMessageBox.StandardButton.Yes

    manager.remove_current_sample()

    assert path.exists()


def test_profiles_and_polygons_for_the_sample_are_dropped(two_samples, dialogs):
    """They are held per sample by their own managers, outside the
    SampleObj, so they need removing separately."""
    window, manager = two_samples
    window.open_mask_dock('polygon')
    polygons = window.mask_dock.polygon_tab.polygon_manager
    polygons.polygons['RM01'] = {1: object()}
    polygons.loaded_samples.add('RM01')

    dialogs.question = QMessageBox.StandardButton.Yes
    manager.remove_current_sample()

    assert 'RM01' not in polygons.polygons
    assert 'RM01' not in polygons.loaded_samples


# ---------------------------------------------------------------------------
# removing the last one
# ---------------------------------------------------------------------------
def test_removing_the_last_sample_empties_the_project(loaded_window, dialogs):
    """`_sync_app_data_from_project` used to return early on an empty
    project, which would have left the removed sample in the selector."""
    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    dialogs.question = QMessageBox.StandardButton.Yes

    assert window.project_manager.remove_current_sample() is True

    assert window.project_manager.current_project.samples == {}
    assert window.app_data.sample_list == []
    assert window.app_data.sample_id == ''
    assert window.data == {}


# ---------------------------------------------------------------------------
# the action itself
# ---------------------------------------------------------------------------
def test_the_action_is_in_the_file_menu_and_nowhere_else(lame_window):
    """One stray click should not be able to reach it."""
    from PyQt6.QtWidgets import QToolBar

    action = lame_window.lame_action.RemoveSample

    assert action in lame_window.menu_bar.menuFile.actions()
    for toolbar in lame_window.findChildren(QToolBar):
        assert action not in toolbar.actions(), f"also on {toolbar.objectName()}"
