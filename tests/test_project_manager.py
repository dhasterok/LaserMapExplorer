"""ProjectManager against a real MainWindow.

Covers: the untitled project created on the first add_samples(), gathering
files from two *different* directories into one project (the scenario that
required the initialize_sample_object() path-resolution fix), preserving the
current selection across a resync, the save/load round-trip, and
close_project() clearing ui.data/AppData sample state.

Headless MainWindow integration tests -- shared setup (QApplication, modal
dialog stubbing, sample files) comes from tests/conftest.py.
"""
from pathlib import Path

import pytest


@pytest.fixture
def two_dir_samples(sample_factory):
    """Two samples in two different directories.

    Different parents is the point: ``selected_directory`` only ever holds
    one, so this is what proves ``initialize_sample_object()`` resolves each
    sample's own absolute path rather than indexing one shared directory.
    """
    rm01 = sample_factory('RM01', subdir='dir_a')
    rm02 = sample_factory('RM02', subdir='dir_b')
    assert rm01.parent != rm02.parent
    return rm01, rm02


def test_first_add_samples_creates_an_untitled_project(lame_window, sample_factory):
    pm = lame_window.project_manager
    assert pm.current_project is None

    added = pm.add_samples([sample_factory('RM01')])

    assert added == ['RM01'], added
    assert pm.current_project is not None
    assert pm.current_project.name == "Untitled Project"
    assert pm.current_project.dirty is True


def test_adding_from_a_second_directory_keeps_the_first_sample(lame_window, two_dir_samples):
    pm = lame_window.project_manager
    rm01, rm02 = two_dir_samples

    assert pm.add_samples([rm01]) == ['RM01']
    assert pm.add_samples([rm02]) == ['RM02']

    assert set(pm.current_project.samples) == {'RM01', 'RM02'}
    assert pm.current_project.samples['RM01'].sample_path == rm01.resolve()
    assert pm.current_project.samples['RM02'].sample_path == rm02.resolve()
    assert lame_window.app_data.sample_list == ['RM01', 'RM02']


def test_re_adding_an_existing_sample_returns_no_new_ids(lame_window, sample_factory):
    pm = lame_window.project_manager
    path = sample_factory('RM01')
    pm.add_samples([path])

    assert pm.add_samples([path]) == []


def test_current_selection_survives_a_resync(lame_window, two_dir_samples):
    pm = lame_window.project_manager
    rm01, rm02 = two_dir_samples
    pm.add_samples([rm01, rm02])

    lame_window.app_data.sample_id = 'RM02'
    pm._sync_app_data_from_project()     # what add_samples() does internally

    assert lame_window.app_data.sample_id == 'RM02'


def test_each_sample_loads_from_its_own_directory(lame_window, two_dir_samples):
    """The path-resolution fix: loading must use each sample's own absolute
    path, not ``directory/csv_files[index]``, which only reflects one
    directory."""
    pm = lame_window.project_manager
    rm01, rm02 = two_dir_samples
    pm.add_samples([rm01, rm02])

    for sample_id, path in (('RM01', rm01), ('RM02', rm02)):
        lame_window.app_data.sample_id = sample_id
        lame_window.change_sample()
        assert sample_id in lame_window.data, f"{sample_id} should have loaded"
        assert Path(lame_window.data[sample_id].file_path).resolve() == path.resolve()


def test_save_project_writes_a_manifest_and_clears_dirty(lame_window, sample_factory, tmp_path):
    pm = lame_window.project_manager
    pm.add_samples([sample_factory('RM01')])
    manifest = tmp_path / 'TestProject.lame_project.json'

    pm.save_project(manifest)

    assert manifest.exists()
    assert pm.current_project.dirty is False


def test_open_project_reloads_the_same_samples_and_resyncs_app_data(lame_window, two_dir_samples, tmp_path):
    pm = lame_window.project_manager
    pm.add_samples(list(two_dir_samples))
    manifest = tmp_path / 'TestProject.lame_project.json'
    pm.save_project(manifest)
    original_sample_ids = set(pm.current_project.samples)

    pm.open_project(manifest)

    assert set(pm.current_project.samples) == original_sample_ids
    assert pm.current_project.dirty is False
    assert set(lame_window.app_data.sample_list) == original_sample_ids


def test_close_project_clears_ui_data_in_place(lame_window, sample_factory):
    """``AppData.data`` aliases ``ui.data``, so the dict must be cleared, not
    reassigned."""
    pm = lame_window.project_manager
    pm.add_samples([sample_factory('RM01')])
    lame_window.app_data.sample_id = 'RM01'
    lame_window.change_sample()
    assert lame_window.data
    data_ref_before = lame_window.data

    pm.close_project()

    assert pm.current_project is None
    assert lame_window.data == {}
    assert lame_window.data is data_ref_before
    assert lame_window.app_data.data is lame_window.data
    assert lame_window.app_data.sample_list == []


def test_recent_projects_includes_the_just_saved_manifest(lame_window, sample_factory, tmp_path):
    pm = lame_window.project_manager
    pm.add_samples([sample_factory('RM01')])
    manifest = tmp_path / 'TestProject.lame_project.json'
    pm.save_project(manifest)

    assert Path(manifest) in pm.recent_projects()
