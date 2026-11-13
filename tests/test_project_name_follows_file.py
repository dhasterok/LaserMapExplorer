"""A project is named after its file.

Nothing else ever set ``Project.name``: `new_project` assigns the untitled
placeholder, and `save_project` set ``dirty`` and ``manifest_path`` but not
the name. So saving an untitled project as "MyGarnets" cleared the
unsaved-changes marker from the window title while leaving the title itself
reading "LaME - Untitled Project" -- and, because the stale name was
written into the manifest, it came back wrong when the project was
reopened.

``Path.stem`` is not enough to derive it: the suffix is a double extension,
so the stem of ``Foo.lame_project.json`` is ``Foo.lame_project``.
"""
import json

import pytest

from src.project.ProjectModel import (
    PROJECT_FILE_SUFFIX,
    UNTITLED_PROJECT_NAME,
    load_project,
    new_project,
    project_name_for,
    save_project,
)


@pytest.fixture
def manifest(tmp_path):
    return tmp_path / f'MyGarnets{PROJECT_FILE_SUFFIX}'


# --- the name helper --------------------------------------------------
@pytest.mark.parametrize("filename,expected", [
    (f'MyGarnets{PROJECT_FILE_SUFFIX}', 'MyGarnets'),
    ('MyGarnets.lame_project.json', 'MyGarnets'),
    ('a.b.c.lame_project.json', 'a.b.c'),
    ('Odd.json', 'Odd'),
    ('no_suffix', 'no_suffix'),
])
def test_project_name_for(filename, expected):
    assert project_name_for(f'/somewhere/{filename}') == expected


# --- saving -----------------------------------------------------------
def test_saving_an_untitled_project_names_it_after_the_file(manifest):
    project = new_project()
    assert project.name == UNTITLED_PROJECT_NAME

    save_project(project, manifest)

    assert project.name == 'MyGarnets'


def test_the_name_is_written_into_the_manifest(manifest):
    """Set before the payload is built, or the file records the old name
    and a reload brings it back."""
    save_project(new_project(), manifest)

    assert json.loads(manifest.read_text())['name'] == 'MyGarnets'


def test_saving_again_somewhere_else_renames_it(tmp_path, manifest):
    project = new_project()
    save_project(project, manifest)

    save_project(project, tmp_path / f'Renamed{PROJECT_FILE_SUFFIX}')

    assert project.name == 'Renamed'


def test_an_autosave_copy_does_not_rename_the_project(tmp_path):
    """`ProjectManager.autosave` writes an untitled project into a scratch
    manifest with ``update_project_state=False``; that copy must not make
    it look saved, name included."""
    project = new_project()

    save_project(project, tmp_path / f'scratch{PROJECT_FILE_SUFFIX}',
                 update_project_state=False)

    assert project.name == UNTITLED_PROJECT_NAME
    assert project.manifest_path is None
    assert project.dirty is False   # unchanged from its initial state


# --- loading ----------------------------------------------------------
def test_loading_uses_the_file_name(manifest):
    save_project(new_project(), manifest)

    assert load_project(manifest).name == 'MyGarnets'


def test_a_project_renamed_on_disk_opens_under_its_new_name(tmp_path, manifest):
    """The file is the authority, not the payload -- renaming the manifest
    in Finder should rename the project."""
    save_project(new_project(), manifest)
    renamed = tmp_path / f'Pyrite{PROJECT_FILE_SUFFIX}'
    manifest.rename(renamed)

    assert load_project(renamed).name == 'Pyrite'


# --- the window title, which is what the user sees --------------------
def test_the_window_title_follows_a_save(lame_window, tmp_path, monkeypatch):
    manager = lame_window.project_manager
    manager.new_project()
    manager.mark_dirty('something changed')
    assert lame_window.windowTitle() == f'LaME - {UNTITLED_PROJECT_NAME} *'

    target = tmp_path / f'MyGarnets{PROJECT_FILE_SUFFIX}'
    manager.save_project(target)

    assert lame_window.windowTitle() == 'LaME - MyGarnets'
