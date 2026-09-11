"""Dirty-check prompt, close_project() teardown, and MainWindow.closeEvent().

Headless MainWindow integration tests -- shared setup (QApplication, modal
dialog stubbing, sample files) comes from tests/conftest.py. Each test gets
its own window, so a teardown assertion can't be satisfied by whatever an
earlier scenario happened to leave behind.
"""
import pytest
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QMessageBox

from tests.conftest import first_analyte


@pytest.fixture
def window_with_docks(loaded_window):
    """A loaded window with the docks close_project() tears down opened.

    They're opened *after* the sample is added: ProfileDock's init assumes a
    loaded sample (a pre-existing, unrelated requirement).
    """
    window, _path = loaded_window
    window.open_mask_dock()
    window.open_profile()
    window.open_notes()
    return window


def test_cancel_aborts_close_and_touches_nothing(window_with_docks, dialogs):
    window = window_with_docks
    pm = window.project_manager
    assert pm.current_project.dirty is True
    data_ref = window.data

    dialogs.question = QMessageBox.StandardButton.Cancel
    assert pm.close_project() is False

    assert pm.current_project is not None
    assert 'RM01' in window.data
    assert window.data is data_ref


def test_discard_tears_down_every_piece_of_session_state(window_with_docks, dialogs, tmp_path):
    window = window_with_docks
    pm = window.project_manager
    data_ref = window.data

    window.app_data.sample_id = 'RM01'
    window.change_sample()
    window.data['RM01'].add_filter(
        field_type='Analyte', field=first_analyte(window), min_val=0.0, max_val=1e9,
        operator='and', use=True,
    )
    # Placeholder per-sample dock state. close_project()'s teardown is what's
    # under test, not save_profiles(), which would want real Profile objects.
    window.profile_dock.profiling.profiles['RM01'] = {'fake_profile': object()}
    window.mask_dock.polygon_tab.polygon_manager.polygons['RM01'] = {1: object()}
    window.notes_dock.notes.notes_file = tmp_path / 'RM01.rst'

    dialogs.question = QMessageBox.StandardButton.Discard
    assert pm.close_project() is True

    assert pm.current_project is None
    assert window.data == {}
    assert window.data is data_ref, "ui.data must be cleared in place (AppData.data aliases it)"
    assert window.app_data.data is window.data
    assert window.app_data.sample_list == []
    assert window.profile_dock.profiling.profiles == {}, "add_samples()-only dicts must not leak stale samples"
    assert window.profile_dock.profiling.project_dir is None
    assert window.mask_dock.polygon_tab.polygon_manager.polygons == {}
    assert window.notes_dock.notes.notes_file is None
    assert window.lame_action.SelectAnalytes.isEnabled() is False, "toggle_actions(False) should have run"
    assert window.windowTitle() == "LaME"


def test_dirty_marker_appears_in_the_window_title(loaded_window):
    window, _path = loaded_window
    assert window.project_manager.current_project.dirty is True
    assert "*" in window.windowTitle(), window.windowTitle()


def test_save_and_close_writes_the_manifest_before_tearing_down(loaded_window, dialogs, tmp_path):
    window, _path = loaded_window
    pm = window.project_manager
    manifest = tmp_path / 'SaveOnClose.lame_project.json'

    dialogs.save_filename = manifest
    dialogs.question = QMessageBox.StandardButton.Save
    assert pm.close_project() is True

    assert manifest.exists()
    assert pm.current_project is None
    assert window.data == {}


def test_new_project_aborts_on_a_cancelled_dirty_prompt(loaded_window, dialogs):
    window, _path = loaded_window
    pm = window.project_manager
    original_project = pm.current_project
    assert original_project.dirty is True

    dialogs.question = QMessageBox.StandardButton.Cancel
    pm.new_project()

    assert pm.current_project is original_project


def test_new_project_proceeds_once_the_dirty_prompt_is_discarded(loaded_window, dialogs):
    window, _path = loaded_window
    pm = window.project_manager
    original_project = pm.current_project

    dialogs.question = QMessageBox.StandardButton.Discard
    pm.new_project()

    assert pm.current_project is not original_project
    assert pm.current_project.name == "Untitled Project"


def test_switching_projects_in_one_session_leaks_no_dock_state(loaded_window, dialogs, sample_factory):
    """Open A, close it, open B: A's per-sample dock state must not survive."""
    window, _path = loaded_window
    pm = window.project_manager
    window.open_profile()   # creates window.profile_dock
    window.profile_dock.profiling.profiles.setdefault('RM01', {})['p1'] = object()
    assert pm.current_project.dirty is True

    dialogs.question = QMessageBox.StandardButton.Discard
    pm.new_project()                       # dirty -> prompts, answered Discard
    pm.add_samples([sample_factory('RM05')])

    assert 'RM01' not in window.profile_dock.profiling.profiles, \
        "Project A's profile state leaked into Project B"
    assert set(pm.current_project.samples) == {'RM05'}


def test_close_event_is_ignored_when_the_user_cancels(loaded_window, dialogs):
    window, _path = loaded_window
    assert window.project_manager.current_project.dirty is True

    dialogs.question = QMessageBox.StandardButton.Cancel
    event = QCloseEvent()
    window.closeEvent(event)

    assert not event.isAccepted()
    assert window.project_manager.current_project is not None


def test_close_event_is_accepted_once_the_prompt_is_answered(loaded_window, dialogs):
    window, _path = loaded_window

    dialogs.question = QMessageBox.StandardButton.Discard
    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted()
    assert window.project_manager.current_project is None
