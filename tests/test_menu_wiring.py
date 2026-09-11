"""File menu / toolbar restructuring: the project actions exist, sit in
menuFile, and are wired to the matching ProjectManager calls.

Headless MainWindow integration tests -- shared setup (QApplication, modal
dialog stubbing, sample files) comes from tests/conftest.py.
"""
import pytest
from PyQt6.QtWidgets import QFileDialog, QMessageBox

#: LameAction attribute -> the objectName the menu/toolbar looks it up by.
PROJECT_ACTIONS = {
    'NewProject': 'actionNewProject',
    'OpenProject': 'actionOpenProject',
    'AddSampleFiles': 'actionAddSampleFiles',
    'AddSampleDirectory': 'actionAddSampleDirectory',
    'SaveProject': 'actionSaveProject',
    'SaveProjectAs': 'actionSaveProjectAs',
    'CloseProject': 'actionCloseProject',
}


@pytest.fixture
def sample_dir(tmp_path, sample_factory):
    """A directory holding exactly one sample, for the add-directory action."""
    directory = tmp_path / 'samples'
    directory.mkdir()
    path = sample_factory('RM01')
    path.rename(directory / path.name)
    return directory


@pytest.mark.parametrize("attr, object_name", sorted(PROJECT_ACTIONS.items()))
def test_project_actions_exist_with_expected_object_names(lame_window, attr, object_name):
    action = getattr(lame_window.lame_action, attr)
    assert action.objectName() == object_name


@pytest.mark.parametrize("old_name, new_name", [
    ('OpenSample', 'AddSampleFiles'),
    ('OpenDirectory', 'AddSampleDirectory'),
])
def test_renamed_actions_no_longer_exist_under_their_old_names(lame_window, old_name, new_name):
    assert not hasattr(lame_window.lame_action, old_name), \
        f"{old_name} should have been renamed to {new_name}"


def test_menu_file_contains_every_project_action(lame_window):
    file_menu_actions = {a.objectName() for a in lame_window.menu_bar.menuFile.actions() if a.objectName()}
    missing = set(PROJECT_ACTIONS.values()) - file_menu_actions
    assert not missing, f"missing from menuFile: {sorted(missing)}"


def test_recent_projects_submenu_exists(lame_window):
    assert hasattr(lame_window.menu_bar, 'menuRecentProjects')


def test_new_project_action_creates_an_untitled_project(lame_window):
    pm = lame_window.project_manager
    assert pm.current_project is None

    lame_window.lame_action.NewProject.trigger()

    assert pm.current_project is not None
    assert pm.current_project.name == "Untitled Project"


def test_add_sample_files_action_adds_the_chosen_sample(lame_window, sample_factory, monkeypatch):
    pm = lame_window.project_manager
    lame_window.lame_action.NewProject.trigger()
    path = sample_factory('RM01')
    monkeypatch.setattr(QFileDialog, 'getOpenFileNames',
                        staticmethod(lambda *a, **k: ([str(path)], '')))

    lame_window.lame_action.AddSampleFiles.trigger()

    assert 'RM01' in pm.current_project.samples


def test_add_sample_directory_action_is_idempotent(lame_window, sample_dir, monkeypatch):
    """Re-adding a directory already in the project is a safe no-op, not a
    duplicate entry or an error."""
    pm = lame_window.project_manager
    lame_window.lame_action.NewProject.trigger()
    monkeypatch.setattr(QFileDialog, 'getExistingDirectory',
                        staticmethod(lambda *a, **k: str(sample_dir)))

    lame_window.lame_action.AddSampleDirectory.trigger()
    lame_window.lame_action.AddSampleDirectory.trigger()

    assert list(pm.current_project.samples.keys()) == ['RM01']


def test_switching_sample_does_not_prompt_to_save(loaded_window, monkeypatch):
    """Dirty tracking is project-scoped now, so changing sample must not pop
    a save prompt (and must not raise on a same-sample no-op switch)."""
    window, _path = loaded_window

    def fail_on_warning(*a, **k):
        raise AssertionError(f"QMessageBox.warning should not be called here: args={a}")

    monkeypatch.setattr(QMessageBox, 'warning', staticmethod(fail_on_warning))

    window.app_data.sample_id = 'RM01'
    window.change_sample()
    window.toolbar.comboBoxSampleId.setCurrentText('RM01')
    window.toolbar.update_sample_id()


def test_recent_projects_menu_lists_a_saved_project(loaded_window, tmp_path):
    window, _path = loaded_window
    manifest = tmp_path / 'MenuWiringTest.lame_project.json'
    window.project_manager.save_project(manifest)

    window.menu_bar._refresh_recent_projects_menu(window)

    labels = [a.text() for a in window.menu_bar.menuRecentProjects.actions()]
    assert manifest.stem in labels, labels


def test_triggering_a_recent_project_entry_reopens_it(loaded_window, dialogs, tmp_path):
    window, _path = loaded_window
    pm = window.project_manager
    manifest = tmp_path / 'MenuWiringTest.lame_project.json'
    pm.save_project(manifest)
    window.menu_bar._refresh_recent_projects_menu(window)

    pm.close_project()
    assert pm.current_project is None

    entry = next(a for a in window.menu_bar.menuRecentProjects.actions() if a.text() == manifest.stem)
    entry.trigger()

    assert pm.current_project is not None
    assert 'RM01' in pm.current_project.samples
