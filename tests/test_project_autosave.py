"""Scratch directory for untitled projects, project autosave, and the
per-sample import-settings sidecar.

An untitled project has no directory of its own, which used to leave Notes
(and every other sidecar) with nowhere to write until the user saved. It now
gets a scratch directory under the system temp dir, autosaves into it, and
migrates everything to the real project directory on the first save.

Headless MainWindow integration tests -- shared setup (QApplication, modal
dialog stubbing, sample files) comes from tests/conftest.py.
"""
import json

import pytest

from src.project.ProjectManager import (
    AUTOSAVE_INTERVAL_KEY,
    DEFAULT_AUTOSAVE_MINUTES,
    MAX_AUTOSAVE_MINUTES,
    MIN_AUTOSAVE_MINUTES,
    PROJECT_FILE_SUFFIX,
)


@pytest.fixture
def stored_interval(monkeypatch):
    """Reads/writes of the autosave interval kept out of the real QSettings."""
    store = {}

    class FakeSettings:
        def __init__(self, *args, **kwargs):
            pass

        def value(self, key, default=None):
            return store.get(key, default)

        def setValue(self, key, value):
            store[key] = value

    monkeypatch.setattr('src.project.ProjectManager.QSettings', FakeSettings)
    return store


# ---------------------------------------------------------------------------
# Scratch directory
# ---------------------------------------------------------------------------

def test_untitled_project_gets_a_scratch_project_dir(loaded_window):
    pm = loaded_window[0].project_manager

    assert pm.current_project.manifest_path is None
    assert pm.project_dir == pm.scratch_dir
    assert pm.scratch_dir.is_dir()


def test_no_project_means_no_scratch_dir(lame_window):
    pm = lame_window.project_manager
    assert pm.current_project is None
    assert pm.project_dir is None
    assert pm.scratch_dir is None


def test_scratch_sidecars_migrate_on_save(loaded_window, tmp_path):
    """Anything written under the scratch directory follows the project to
    its real directory -- not just notes."""
    window, _path = loaded_window
    pm = window.project_manager

    (pm.project_dir / 'RM01').mkdir(parents=True, exist_ok=True)
    (pm.project_dir / 'RM01' / 'p1.prfl').write_text('scratch profile')
    scratch = pm.scratch_dir

    pm.save_project(tmp_path / 'Migrate.lame_project.json')

    assert (pm.project_dir / 'RM01' / 'p1.prfl').read_text() == 'scratch profile'
    assert not scratch.exists()
    assert pm.scratch_dir is None or pm.scratch_dir != scratch


def test_closing_the_project_removes_the_scratch_dir(loaded_window):
    window, _path = loaded_window
    pm = window.project_manager
    scratch = pm.scratch_dir

    assert pm.close_project(prompt_if_dirty=False) is True
    assert not scratch.exists()


# ---------------------------------------------------------------------------
# Autosave
# ---------------------------------------------------------------------------

def test_autosave_writes_an_untitled_project_into_scratch(loaded_window):
    window, _path = loaded_window
    pm = window.project_manager
    assert pm.current_project.dirty is True

    written = pm.autosave()

    assert written == pm.scratch_manifest_path
    assert written.exists()
    assert written.name.endswith(PROJECT_FILE_SUFFIX)
    assert json.loads(written.read_text())['samples'].keys() == {'RM01'}
    # Still untitled and still unsaved -- an autosave is not a save.
    assert pm.current_project.manifest_path is None
    assert pm.current_project.dirty is True


def test_autosave_writes_a_saved_project_back_to_its_manifest(loaded_window, tmp_path):
    window, _path = loaded_window
    pm = window.project_manager
    manifest = tmp_path / 'Auto.lame_project.json'
    pm.save_project(manifest)

    pm.mark_dirty('test')
    assert pm.autosave() == manifest
    assert pm.current_project.dirty is False


def test_autosave_is_a_no_op_when_nothing_changed(loaded_window, tmp_path):
    window, _path = loaded_window
    pm = window.project_manager
    pm.save_project(tmp_path / 'Clean.lame_project.json')

    assert pm.autosave() is None


def test_autosave_interval_is_clamped_and_persisted(loaded_window, stored_interval):
    pm = loaded_window[0].project_manager

    assert pm.autosave_interval_minutes == DEFAULT_AUTOSAVE_MINUTES

    pm.autosave_interval_minutes = 1
    assert stored_interval[AUTOSAVE_INTERVAL_KEY] == MIN_AUTOSAVE_MINUTES
    assert pm.autosave_interval_minutes == MIN_AUTOSAVE_MINUTES

    pm.autosave_interval_minutes = 120
    assert pm.autosave_interval_minutes == MAX_AUTOSAVE_MINUTES

    pm.autosave_interval_minutes = 15
    assert pm.autosave_interval_minutes == 15
    assert pm.autosave_timer.interval() == 15 * 60 * 1000


def test_autosave_interval_falls_back_on_a_junk_setting(loaded_window, stored_interval):
    pm = loaded_window[0].project_manager
    stored_interval[AUTOSAVE_INTERVAL_KEY] = 'not a number'

    assert pm.autosave_interval_minutes == DEFAULT_AUTOSAVE_MINUTES


# ---------------------------------------------------------------------------
# Import settings sidecar
# ---------------------------------------------------------------------------

def test_import_settings_are_written_beside_the_sample(loaded_window):
    window, _path = loaded_window
    pm = window.project_manager

    path = pm.save_import_settings('RM01', {'data_type': 'LA-ICP-MS', 'method': 'quadrupole'})

    assert path == pm.project_dir / 'RM01' / 'import_settings.json'
    payload = json.loads(path.read_text())
    assert payload['data_type'] == 'LA-ICP-MS'
    assert 'saved' in payload, "a timestamp should be stamped in automatically"


def test_import_settings_survive_the_first_save(loaded_window, tmp_path):
    window, _path = loaded_window
    pm = window.project_manager
    pm.save_import_settings('RM01', {'method': 'TOF'})

    pm.save_project(tmp_path / 'Imported.lame_project.json')

    relocated = pm.project_dir / 'RM01' / 'import_settings.json'
    assert json.loads(relocated.read_text())['method'] == 'TOF'


def test_import_settings_need_a_project(lame_window):
    assert lame_window.project_manager.save_import_settings('RM01', {'method': 'TOF'}) is None
