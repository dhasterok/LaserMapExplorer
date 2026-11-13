"""Re-importing a sample whose file has changed re-reads it.

Re-importing used to do nothing at all. Two gates saw to it:
`ProjectManager.add_samples` skipped any sample id already in the project
("re-adding the same directory is a safe no-op"), and
`LameIO.initialize_sample_object` only reads a file when the sample is
absent from ``ui.data`` -- which it never becomes, since nothing removed it.
There was no reload path anywhere, so restarting the program was the only
way to pick up re-imported data.

Reloading is *clean*: everything derived from the old data is discarded
rather than replayed. A re-import can change the map's dimensions, so a
stored pixel mask or an annotation's coordinates may no longer mean what
they did, and a figure already drawn from the old data is simply wrong.
The user is warned and can decline.

Only a sample whose file has actually changed is touched -- re-adding an
unchanged directory stays the harmless no-op it has always been.
"""
import numpy as np
import pandas as pd
import pytest
from PyQt6.QtWidgets import QMessageBox

from src.project.ProjectModel import compute_source_hash


@pytest.fixture
def loaded(loaded_window, dialogs):
    """``(window, path, entry)`` with RM01 imported and read into memory."""
    window, path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    entry = window.project_manager.current_project.samples['RM01']
    assert 'RM01' in window.data
    return window, path, entry


def rewrite(path, extra_column='Zz99'):
    """Rewrite the sample file with an extra analyte, as a re-import would."""
    frame = pd.read_csv(path)
    frame[extra_column] = np.linspace(1.0, 2.0, len(frame))
    # mtime has one-second resolution in the fingerprint, so make sure the
    # rewrite is distinguishable from the original.
    frame.to_csv(path, index=False)
    import os, time
    stat = os.stat(path)
    os.utime(path, (stat.st_atime + 10, stat.st_mtime + 10))
    return path


# ---------------------------------------------------------------------------
# noticing the change
# ---------------------------------------------------------------------------
def test_the_file_is_fingerprinted_when_it_is_read(loaded):
    _window, path, entry = loaded
    assert entry.source_hash == compute_source_hash(path)


def test_re_adding_an_unchanged_sample_changes_nothing(loaded, dialogs):
    """The no-op that was always intended, and still is."""
    window, path, _entry = loaded
    original = window.data['RM01']

    window.project_manager.add_samples([path])

    assert window.data['RM01'] is original
    assert dialogs.warning_calls == []


def test_a_sample_never_loaded_is_not_a_reload(loaded_window, dialogs, sample_factory):
    """Nothing is cached for it, so there is nothing to warn about -- the
    entry just picks up the new path."""
    window, _path = loaded_window
    second = sample_factory('RM02')
    window.project_manager.add_samples([second])
    entry = window.project_manager.current_project.samples['RM02']
    assert entry.source_hash is None

    rewrite(second)
    window.project_manager.add_samples([second])

    assert dialogs.warning_calls == []
    assert 'RM02' not in window.data


# ---------------------------------------------------------------------------
# reloading
# ---------------------------------------------------------------------------
def test_a_changed_file_is_re_read(loaded, dialogs):
    """The reported bug: this needed a restart."""
    window, path, _entry = loaded
    dialogs.warning = QMessageBox.StandardButton.Yes
    assert 'Zz99' not in window.data['RM01'].processed.columns

    rewrite(path)
    window.project_manager.add_samples([path])

    assert 'Zz99' in window.data['RM01'].processed.columns


def test_the_user_is_warned_first(loaded, dialogs):
    window, path, _entry = loaded
    dialogs.warning = QMessageBox.StandardButton.Yes

    rewrite(path)
    window.project_manager.add_samples([path])

    assert len(dialogs.warning_calls) == 1
    message = dialogs.warning_calls[0][2]
    assert 'RM01' in message
    assert 'discards' in message.lower()


def test_declining_keeps_what_is_loaded(loaded, dialogs):
    window, path, _entry = loaded
    dialogs.warning = QMessageBox.StandardButton.Cancel
    original = window.data['RM01']

    rewrite(path)
    window.project_manager.add_samples([path])

    assert window.data['RM01'] is original
    assert 'Zz99' not in window.data['RM01'].processed.columns


def test_the_reload_is_clean(loaded, dialogs):
    """Derived state describes data that no longer exists."""
    window, path, entry = loaded
    dialogs.warning = QMessageBox.StandardButton.Yes
    data = window.data['RM01']
    data.add_columns('Calculated', 'derived', np.ones(len(data.processed)))
    data.add_map_annotation({
        'type': 'text', 'text': 'note', 'position': [[10.0, 10.0]],
        'style': {'color': '#000', 'font_size': 11.0},
    })
    window.project_manager._pull_processing_state_from_loaded_samples()

    rewrite(path)
    window.project_manager.add_samples([path])

    reloaded = window.data['RM01']
    assert reloaded is not data
    assert 'derived' not in reloaded.processed.columns
    assert reloaded.get_map_annotations() == []
    assert entry.processing.annotations == []


def test_figures_from_the_old_data_are_dropped(loaded, dialogs):
    """They were drawn from values that no longer exist."""
    window, path, _entry = loaded
    dialogs.warning = QMessageBox.StandardButton.Yes
    window.style_data.plot_type = 'field map'
    window.update_SV()
    window.plot_tree.add_tree_item(window.plot_info)
    assert window.plot_registry.get_plots_for_sample('RM01')

    rewrite(path)
    window.project_manager.add_samples([path])

    assert window.plot_registry.get_plots_for_sample('RM01') == []


def test_the_field_list_is_rebuilt(loaded, dialogs):
    """`PlotTree.add_sample` returns early when the sample already has a
    branch, so without removing it first the tree would still list the old
    analytes."""
    window, path, _entry = loaded
    dialogs.warning = QMessageBox.StandardButton.Yes

    rewrite(path)
    window.project_manager.add_samples([path])

    analytes = window.data['RM01'].processed.match_attribute('data_type', 'Analyte')
    assert 'Zz99' in analytes
    branch = window.plot_tree.treeView.branch_exists(
        window.plot_tree.tree['Analyte'], 'RM01')
    assert branch is not None
    leaves = [branch.child(i).text() for i in range(branch.rowCount())]
    assert 'Zz99' in leaves


def test_the_fingerprint_is_refreshed_after_a_reload(loaded, dialogs):
    """Otherwise the same import would warn again every time."""
    window, path, entry = loaded
    dialogs.warning = QMessageBox.StandardButton.Yes
    rewrite(path)
    window.project_manager.add_samples([path])
    assert entry.source_hash == compute_source_hash(path)

    window.project_manager.add_samples([path])

    assert len(dialogs.warning_calls) == 1
