"""Drag-and-drop of sample files, sample folders and project manifests onto
the main window (and onto widgets that accept drops for their own purposes).

Headless MainWindow integration tests -- shared setup (QApplication, modal
dialog stubbing, sample files) comes from tests/conftest.py.
"""
import pytest
from PyQt6.QtCore import Qt, QMimeData, QUrl, QPointF, QEvent
from PyQt6.QtGui import QDropEvent, QDragEnterEvent

from src.app.FileDrop import (
    classify_dropped_paths, mime_has_droppable_files, urls_to_local_paths,
)
from src.project.ProjectManager import PROJECT_FILE_SUFFIX


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def _mime_for(*paths):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    return mime


def _drop(lame_app, widget, *paths):
    """Dispatch a synthetic drop of `paths` onto `widget` and flush the
    deferred handler."""
    # Qt events hold a bare pointer to the mime data, so keep it alive here
    # for the event's whole lifetime.
    mime = _mime_for(*paths)
    # Qt only delivers a Drop to a widget that accepted a DragEnter for the
    # same drag session, exactly as a real drag does.
    enter = QDragEnterEvent(QPointF(5, 5).toPoint(), Qt.DropAction.CopyAction, mime,
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    lame_app.sendEvent(widget, enter)
    event = QDropEvent(QPointF(5, 5), Qt.DropAction.CopyAction, mime,
                       Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    handled = lame_app.sendEvent(widget, event)
    accepted = event.isAccepted()
    lame_app.processEvents()
    lame_app.processEvents()
    del event, enter
    return handled and accepted


def _drag_enter(lame_app, widget, *paths):
    mime = _mime_for(*paths)
    event = QDragEnterEvent(QPointF(5, 5).toPoint(), Qt.DropAction.CopyAction, mime,
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    lame_app.sendEvent(widget, event)
    accepted = event.isAccepted()
    del event
    return accepted


@pytest.fixture
def sample_dir(tmp_path, sample_factory):
    directory = tmp_path / 'samples'
    directory.mkdir()
    path = sample_factory('RM01')
    path.rename(directory / path.name)
    return directory


# ----------------------------------------------------------------------
# Qt-free classification
# ----------------------------------------------------------------------

def test_classify_sorts_projects_samples_and_rejects(tmp_path):
    sample = tmp_path / 'RM01.lame.csv'; sample.write_text('x')
    plain_csv = tmp_path / 'other.csv'; plain_csv.write_text('x')
    manifest = tmp_path / f'proj{PROJECT_FILE_SUFFIX}'; manifest.write_text('{}')
    folder = tmp_path / 'folder'; folder.mkdir()
    junk = tmp_path / 'notes.txt'; junk.write_text('x')
    missing = tmp_path / 'gone.lame.csv'

    plan = classify_dropped_paths([sample, plain_csv, manifest, folder, junk, missing])

    assert plan.projects == [manifest]
    assert plan.samples == [sample, plain_csv, folder]
    assert plan.rejected == [junk, missing]
    assert not plan.is_empty


def test_classify_only_rejects_is_empty(tmp_path):
    junk = tmp_path / 'notes.txt'; junk.write_text('x')
    plan = classify_dropped_paths([junk])
    assert plan.is_empty


def test_urls_to_local_paths_ignores_non_file_urls(tmp_path, lame_app):
    mime = QMimeData()
    mime.setUrls([QUrl('https://example.org/x.csv'), QUrl.fromLocalFile(str(tmp_path))])
    assert urls_to_local_paths(mime) == [tmp_path]


def test_mime_without_urls_is_not_droppable(lame_app):
    mime = QMimeData()
    mime.setText('RM01.lame.csv')
    assert not mime_has_droppable_files(mime)


def test_mime_with_only_junk_is_not_droppable(tmp_path, lame_app):
    junk = tmp_path / 'notes.txt'; junk.write_text('x')
    assert not mime_has_droppable_files(_mime_for(junk))


# ----------------------------------------------------------------------
# MainWindow integration
# ----------------------------------------------------------------------

def test_main_window_accepts_drops(lame_window):
    assert lame_window.acceptDrops()


def test_drag_enter_rejects_unsupported_files(lame_app, lame_window, tmp_path):
    junk = tmp_path / 'notes.txt'; junk.write_text('x')
    assert not _drag_enter(lame_app, lame_window, junk)


def test_drag_enter_accepts_sample_file(lame_app, lame_window, sample_factory):
    assert _drag_enter(lame_app, lame_window, sample_factory('RM01'))


def test_dropping_a_sample_file_adds_it(lame_app, lame_window, sample_factory):
    pm = lame_window.project_manager
    path = sample_factory('RM01')

    assert _drop(lame_app, lame_window, path)

    assert pm.current_project is not None
    assert 'RM01' in pm.current_project.samples
    assert pm.current_project.samples['RM01'].sample_path == path.resolve()


def test_dropping_a_directory_is_idempotent(lame_app, lame_window, sample_dir):
    pm = lame_window.project_manager

    _drop(lame_app, lame_window, sample_dir)
    _drop(lame_app, lame_window, sample_dir)

    assert list(pm.current_project.samples.keys()) == ['RM01']


def test_dropping_an_empty_directory_reports_and_adds_nothing(lame_app, lame_window, tmp_path):
    empty = tmp_path / 'raw'; empty.mkdir()
    pm = lame_window.project_manager

    _drop(lame_app, lame_window, empty)

    assert pm.current_project is None or not pm.current_project.samples
    assert 'No valid *.lame.csv' in lame_window.statusBar().currentMessage()


def test_dropping_junk_only_shows_a_status_message(lame_app, lame_window, tmp_path):
    junk = tmp_path / 'notes.txt'; junk.write_text('x')
    pm = lame_window.project_manager

    handled = lame_window.handle_dropped_paths([junk])

    assert handled is False
    assert pm.current_project is None
    assert 'notes.txt' in lame_window.statusBar().currentMessage()


def test_dropping_a_manifest_opens_the_project(lame_app, loaded_window, tmp_path):
    window, _path = loaded_window
    pm = window.project_manager
    manifest = tmp_path / f'DropTest{PROJECT_FILE_SUFFIX}'
    pm.save_project(manifest)
    pm.close_project()
    assert pm.current_project is None

    assert _drop(lame_app, window, manifest)

    assert pm.current_project is not None
    assert 'RM01' in pm.current_project.samples
    assert pm.current_project.manifest_path == manifest


def test_dropping_a_manifest_and_samples_opens_then_adds(lame_app, loaded_window, sample_factory, tmp_path):
    window, _path = loaded_window
    pm = window.project_manager
    manifest = tmp_path / f'DropTest{PROJECT_FILE_SUFFIX}'
    pm.save_project(manifest)
    pm.close_project()
    extra = sample_factory('RM02')

    _drop(lame_app, window, manifest, extra)

    assert sorted(pm.current_project.samples) == ['RM01', 'RM02']


def test_cancelled_dirty_prompt_does_not_add_samples(lame_app, loaded_window, sample_factory, tmp_path, monkeypatch):
    """If the user cancels the Save/Discard/Cancel prompt while a manifest is
    dropped, nothing else from the drop is applied either."""
    from PyQt6.QtWidgets import QMessageBox
    window, _path = loaded_window
    pm = window.project_manager
    manifest = tmp_path / f'DropTest{PROJECT_FILE_SUFFIX}'
    pm.save_project(manifest)
    pm.mark_dirty('test')
    extra = sample_factory('RM02')
    monkeypatch.setattr(QMessageBox, 'question',
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel))

    # A second, different manifest so open_project() must go through the prompt.
    other = tmp_path / f'Other{PROJECT_FILE_SUFFIX}'
    other.write_text(manifest.read_text())

    _drop(lame_app, window, other, extra)

    assert pm.current_project.manifest_path == manifest
    assert 'RM02' not in pm.current_project.samples


# ----------------------------------------------------------------------
# Widgets that accept drops for their own purposes must forward file drops
# ----------------------------------------------------------------------

def test_drop_on_multi_view_tab_is_forwarded(lame_app, lame_window, sample_factory):
    pm = lame_window.project_manager
    tab = lame_window.findChild(object, 'multiViewTab')
    assert tab is not None and tab.acceptDrops()

    assert _drop(lame_app, tab, sample_factory('RM01'))

    assert 'RM01' in pm.current_project.samples


def test_multi_view_tab_still_ignores_junk_files(lame_app, lame_window, tmp_path):
    tab = lame_window.findChild(object, 'multiViewTab')
    junk = tmp_path / 'notes.txt'; junk.write_text('x')
    assert not _drag_enter(lame_app, tab, junk)


def test_drop_on_reorderable_table_is_forwarded(lame_app, lame_window, sample_factory):
    from src.app.CustomTableWidget import ReorderableTableWidget
    pm = lame_window.project_manager
    table = ReorderableTableWidget(parent=lame_window.canvas_widget)
    try:
        assert _drop(lame_app, table, sample_factory('RM01'))
        assert 'RM01' in pm.current_project.samples
    finally:
        table.deleteLater()


def test_drop_on_floating_dock_is_forwarded(lame_app, lame_window, sample_factory):
    pm = lame_window.project_manager
    dock = lame_window.control_dock
    dock.setFloating(True)
    try:
        assert dock.acceptDrops()
        assert _drop(lame_app, dock, sample_factory('RM01'))
        assert 'RM01' in pm.current_project.samples
    finally:
        dock.setFloating(False)
