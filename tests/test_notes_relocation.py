"""Notes relocated to ``<project_dir>/<sample_id>/notes.rst``, plus the
profile/polygon persistence gap that was closed alongside it.

Headless MainWindow integration tests -- shared setup (QApplication, modal
dialog stubbing, sample files) comes from tests/conftest.py.
"""
import pytest

from src.plotting.Profile import Profile


@pytest.fixture
def saved_project(loaded_window, tmp_path):
    """``(window, manifest, project_dir)`` for a project saved once to disk."""
    window, _path = loaded_window
    manifest = tmp_path / 'NotesTest.lame_project.json'
    window.project_manager.save_project(manifest)
    return window, manifest, window.project_manager.project_dir


def test_notes_use_the_scratch_directory_before_the_project_is_saved(loaded_window):
    """An untitled project has no directory of its own, so `project_dir`
    resolves to the session scratch directory -- Notes always has somewhere
    to write, and never falls back to the old ``selected_directory`` path."""
    window, _path = loaded_window
    pm = window.project_manager

    assert pm.project_dir == pm.scratch_dir
    assert pm.notes_path_for_sample('RM01') == pm.scratch_dir / 'RM01' / 'notes.rst'

    window.open_notes()
    assert window.notes_dock.notes.notes_file == pm.scratch_dir / 'RM01' / 'notes.rst'
    assert window.notes_dock.notes.notes_file.exists(), \
        "opening Notes should create the file, not just name it"


def test_scratch_notes_move_under_the_project_on_first_save(loaded_window, tmp_path):
    """Notes taken before the project was saved follow it to its real home."""
    window, _path = loaded_window
    pm = window.project_manager

    window.open_notes()
    scratch_notes = window.notes_dock.notes.notes_file
    window.notes_dock.notes.editor.setPlainText("Notes taken before saving.")

    manifest = tmp_path / 'Migrated.lame_project.json'
    pm.save_project(manifest)

    relocated = pm.project_dir / 'RM01' / 'notes.rst'
    assert relocated.read_text() == "Notes taken before saving."
    assert window.notes_dock.notes.notes_file == relocated, \
        "the live editor should follow the notes to the project directory"
    assert not scratch_notes.exists(), "the scratch directory should be cleaned up"


def test_saving_puts_notes_under_the_project_directory(saved_project):
    window, manifest, project_dir = saved_project
    pm = window.project_manager

    assert project_dir == manifest.parent / 'NotesTest'
    expected = project_dir / 'RM01' / 'notes.rst'
    assert pm.notes_path_for_sample('RM01') == expected
    assert expected.parent.is_dir(), "notes_path_for_sample() should create the parent directory"


def test_notes_do_not_fall_back_to_the_old_location(saved_project, loaded_window):
    window, _manifest, _project_dir = saved_project
    _win, sample_path = loaded_window
    old_style_path = sample_path.parent / 'RM01.rst'
    window.project_manager.notes_path_for_sample('RM01')
    assert not old_style_path.exists()


def test_live_editor_is_pointed_at_the_relocated_path_and_saves_there(saved_project):
    window, _manifest, project_dir = saved_project
    expected = project_dir / 'RM01' / 'notes.rst'

    window.app_data.sample_id = 'RM01'
    window.change_sample()
    window.open_notes()
    assert window.notes_dock.notes.notes_file == expected

    window.notes_dock.notes.editor.setPlainText("Test notes for RM01.")
    window.notes_dock.notes.save_notes_file()

    assert expected.exists()
    assert expected.read_text() == "Test notes for RM01."


def test_project_files_dock_notes_indicator_follows_the_relocation(saved_project):
    """The dock's notes check was originally written against the old
    location -- confirm it was updated to match."""
    window, _manifest, project_dir = saved_project
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    window.open_notes()
    window.notes_dock.notes.editor.setPlainText("Test notes for RM01.")
    window.notes_dock.notes.save_notes_file()

    window.open_project_files_dock()
    window.project_files_dock.refresh()

    branch = window.project_files_dock.treeView.root_node.child(0)
    leaves = [branch.child(i).text() for i in range(branch.rowCount())]
    assert 'notes: present' in leaves, leaves


def test_save_project_persists_profile_sidecars(saved_project):
    """A gap that predated the relocation work: save_project() silently
    didn't write .prfl/.poly sidecars at all."""
    window, manifest, project_dir = saved_project
    window.open_profile()
    window.open_mask_dock()
    window.profile_dock.profiling.profiles.setdefault('RM01', {})['p1'] = Profile(name='p1', radius=5)

    window.project_manager.save_project(manifest)

    assert (project_dir / 'RM01' / 'p1.prfl').exists(), \
        "save_project() should persist profiles via Profiling.save_profiles()"


def test_reselecting_a_sample_reloads_its_profile_from_disk(saved_project):
    window, manifest, _project_dir = saved_project
    window.open_profile()
    window.open_mask_dock()
    window.profile_dock.profiling.profiles.setdefault('RM01', {})['p1'] = Profile(name='p1', radius=5)
    window.project_manager.save_project(manifest)

    # Drop everything the session holds in memory, then re-select.
    window.data.clear()
    window.app_data.sample_id = ''
    window.app_data.sample_list = []
    window.profile_dock.profiling.profiles.clear()

    window.app_data.sample_list = ['RM01']
    window.app_data.sample_id = 'RM01'
    window.change_sample()

    assert 'RM01' in window.data
    assert 'p1' in window.profile_dock.profiling.profiles.get('RM01', {}), \
        "initialize_sample_object() should have reloaded this sample's profile from disk"
