"""ProjectFilesDock: tree contents, live status indicators, and its
Locate.../Remove/double-click actions.

Headless MainWindow integration tests -- shared setup (QApplication, modal
dialog stubbing, sample files) comes from tests/conftest.py.
"""
import shutil
import time
from datetime import datetime

import pytest
from PyQt6.QtCore import QModelIndex
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from src.project.ProjectModel import (
    SampleCalibration,
    compute_source_hash,
    save_calibration_sidecar,
)
from tests.conftest import first_analyte


def _calibrate(path):
    save_calibration_sidecar(path, SampleCalibration(
        source_hash=compute_source_hash(path),
        calibrated_at=datetime(2026, 6, 14, 12, 0, 0),
        method='LA-ICP-MS standards+drift',
        payload={'standards_used': ['NIST610']},
    ))


def _leaf_texts(dock, sample_id='RM01'):
    """The status leaves under one sample's branch."""
    root = dock.treeView.root_node
    branch = next(root.child(i) for i in range(root.rowCount())
                  if root.child(i).data() == sample_id)
    return branch, [branch.child(i).text() for i in range(branch.rowCount())]


@pytest.fixture
def dock_window(lame_window, sample_factory):
    """``(window, dock, sample_path)`` with the dock open and one calibrated
    sample added.

    The sample is added *after* the dock is open so the auto-refresh through
    projectChanged/dirtyChanged is what populates the tree.
    """
    lame_window.open_project_files_dock()
    path = sample_factory('RM01')
    _calibrate(path)
    lame_window.project_manager.add_samples([path])
    return lame_window, lame_window.project_files_dock, path


def test_dock_is_created_and_toggles_visibility(lame_window):
    assert not hasattr(lame_window, 'project_files_dock')

    lame_window.open_project_files_dock()
    dock = lame_window.project_files_dock
    assert dock.isVisible()
    assert lame_window.lame_action.ProjectFiles.isChecked()

    lame_window.open_project_files_dock()      # second call toggles closed
    assert not dock.isVisible()
    assert not lame_window.lame_action.ProjectFiles.isChecked()

    lame_window.open_project_files_dock()
    assert dock.isVisible()


def test_tree_is_empty_with_no_project_open(lame_window):
    lame_window.open_project_files_dock()
    assert lame_window.project_files_dock.treeView.root_node.rowCount() == 0


def test_adding_a_sample_auto_refreshes_the_tree(dock_window):
    _window, dock, _path = dock_window

    assert dock.treeView.root_node.rowCount() == 1, \
        "adding a sample should auto-refresh the dock via projectChanged/dirtyChanged"
    branch, leaves = _leaf_texts(dock)
    assert branch.data() == 'RM01'
    assert '✓ linked' in branch.text(), branch.text()
    assert branch.rowCount() == 3, "expected calibration/processing/notes leaves"
    assert any(t.startswith('calibration: ✓') for t in leaves), leaves
    assert 'processing: none' in leaves, leaves
    assert 'notes: none' in leaves, leaves


def test_processing_status_tracks_the_live_sample_not_the_last_save(dock_window):
    window, dock, _path = dock_window
    window.data['RM01'].add_filter(
        field_type='Analyte', field=first_analyte(window), min_val=0.0, max_val=1e9,
        operator='and', use=True,
    )

    dock.refresh()

    _branch, leaves = _leaf_texts(dock)
    assert any('1 filter' in t for t in leaves), leaves


def test_touched_source_file_surfaces_as_a_stale_calibration(dock_window):
    _window, dock, path = dock_window

    time.sleep(1.1)                            # mtime has 1 s resolution
    path.write_text(path.read_text() + "\n")
    dock.refresh()

    _branch, leaves = _leaf_texts(dock)
    assert any('stale' in t for t in leaves), leaves


def test_missing_sample_is_flagged_and_locate_repairs_it(dock_window, sample_factory, monkeypatch):
    window, dock, _path = dock_window
    missing = sample_factory('RM02')
    window.project_manager.add_samples([missing])
    missing.unlink()

    dock.refresh()
    branch, _leaves = _leaf_texts(dock, 'RM02')
    assert '⚠ missing' in branch.text(), branch.text()

    relocated = sample_factory('RM02_relocated')
    monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                        staticmethod(lambda *a, **k: (str(relocated), '')))
    dock._locate_sample('RM02')

    assert window.project_manager.current_project.samples['RM02'].sample_path == relocated.resolve()
    dock.refresh()
    branch, _leaves = _leaf_texts(dock, 'RM02')
    assert '✓ linked' in branch.text(), branch.text()


def test_double_clicking_a_sample_branch_loads_it(dock_window):
    window, dock, _path = dock_window
    window.app_data.sample_id = ''
    window.data.clear()

    index = dock.treeView.treeModel.indexFromItem(dock.treeView.root_node.child(0))
    dock.on_double_click(index)

    assert window.app_data.sample_id == 'RM01'
    assert 'RM01' in window.data


def test_remove_sample_drops_it_from_the_project_and_refreshes(dock_window, dialogs, sample_factory):
    window, dock, _path = dock_window
    window.project_manager.add_samples([sample_factory('RM02')])
    dock.refresh()
    assert dock.treeView.root_node.rowCount() == 2

    dialogs.question = QMessageBox.StandardButton.Yes   # confirm the removal prompt
    dock._remove_sample('RM02')

    assert 'RM02' not in window.project_manager.current_project.samples
    assert dock.treeView.root_node.rowCount() == 1


def test_remove_sample_is_abandoned_when_the_prompt_is_declined(dock_window, dialogs, sample_factory):
    window, dock, _path = dock_window
    window.project_manager.add_samples([sample_factory('RM02')])

    dialogs.question = QMessageBox.StandardButton.No
    dock._remove_sample('RM02')

    assert 'RM02' in window.project_manager.current_project.samples
