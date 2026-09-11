"""Project.workflow_refs round-trips through save/close/reopen, mirroring
AppData.active_workflow_file (a list of 0 or 1 entries, not a history).

Headless MainWindow integration tests -- shared setup (QApplication, modal
dialog stubbing, sample files) comes from tests/conftest.py.
"""
import json

import pytest


@pytest.fixture
def saved_window(loaded_window, tmp_path):
    """``(window, manifest)`` for a project saved once, so ``dirty`` starts False."""
    window, _path = loaded_window
    manifest = tmp_path / 'WorkflowRefs.lame_project.json'
    window.project_manager.save_project(manifest)
    assert window.project_manager.current_project.dirty is False
    return window, manifest


def _refs(manifest):
    return json.loads(manifest.read_text())['workflow_refs']


def test_no_active_workflow_saves_as_an_empty_list(saved_window):
    _window, manifest = saved_window
    assert _refs(manifest) == []


def test_linking_a_workflow_marks_the_project_dirty(saved_window, dialogs, tmp_path):
    window, _manifest = saved_window
    workflow_path = tmp_path / 'hpe_correction.json'
    dialogs.save_filename = workflow_path

    window.new_workflow()

    assert window.app_data.active_workflow_file == workflow_path
    assert window.project_manager.current_project.dirty is True


def test_save_captures_the_active_workflow_as_a_relative_path(saved_window, dialogs, tmp_path):
    window, manifest = saved_window
    dialogs.save_filename = tmp_path / 'hpe_correction.json'
    window.new_workflow()

    window.project_manager.save_project(manifest)

    assert _refs(manifest) == ['hpe_correction.json']


def test_reopening_restores_the_workflow_link_without_marking_dirty(saved_window, dialogs, tmp_path):
    window, manifest = saved_window
    pm = window.project_manager
    workflow_path = tmp_path / 'hpe_correction.json'
    dialogs.save_filename = workflow_path
    window.new_workflow()
    pm.save_project(manifest)

    pm.close_project()
    assert window.app_data.active_workflow_file is None

    pm.open_project(manifest)

    # load_project() resolves paths (symlink-correctness, see ProjectModel.py),
    # so compare against the resolved form.
    assert window.app_data.active_workflow_file == workflow_path.resolve()
    assert pm.current_project.workflow_refs == [workflow_path.resolve()]
    assert pm.current_project.dirty is False, \
        "restoring an existing workflow link on open must not mark dirty"


def test_closing_the_workflow_marks_dirty_and_clears_the_refs(saved_window, dialogs, tmp_path):
    window, manifest = saved_window
    pm = window.project_manager
    dialogs.save_filename = tmp_path / 'hpe_correction.json'
    window.new_workflow()
    pm.save_project(manifest)

    window.close_workflow_file()

    assert window.app_data.active_workflow_file is None
    assert pm.current_project.dirty is True

    pm.save_project(manifest)
    assert _refs(manifest) == []


def test_closing_an_inactive_workflow_is_a_no_op(saved_window):
    """No spurious dirty mark when there was nothing to close."""
    window, _manifest = saved_window
    assert window.app_data.active_workflow_file is None

    window.close_workflow_file()

    assert window.project_manager.current_project.dirty is False
