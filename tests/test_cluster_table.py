"""Cluster table behaviour (``ClusterTab`` in ``src/data/Masking.py``).

Two regressions worth guarding, both found by auditing the cluster-linking
work:

* renaming a cluster used to write the new name *string* into the numeric
  label column, which pandas rejects -- the exception was swallowed and,
  because that write came first, the rename never reached ``cluster_dict``
  at all, so renaming silently did nothing.
* the table never reset its row count when the active method had no labels,
  so switching to a sample that had not been clustered left the previous
  sample's rows behind, with live checkboxes still reporting a selection.

These drive the real ``MainWindow``. Deliberately only **two** tests: this
suite cannot hold more than a couple of live MainWindows in one process (the
same Qt teardown problem that leaves ``test_roi_filtering`` with 8 errors at
baseline), so each test covers one regression end to end rather than being
split into a window apiece.
"""
import numpy as np
import pytest
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem

METHOD = 'k-means'


def cluster_four(window, monkeypatch):
    """Compute four clusters for RM01 and return ``(tab, entries, warnings)``."""
    window.app_data.sample_id = 'RM01'
    window.open_mask_dock('cluster')

    window.app_data.cluster_method = METHOD
    window.app_data.num_clusters = 4
    window.app_data.update_cluster_flag = True
    window.control_dock.clustering.compute_clusters_update_groups()

    tab = window.mask_dock.cluster_tab
    tab.update_table_widget()

    # The duplicate-name path is modal; record it instead of showing it.
    warnings = []
    monkeypatch.setattr(QMessageBox, 'warning',
                        staticmethod(lambda *a, **k: warnings.append(a[1:3])))

    return tab, window.app_data.cluster_dict[METHOD], warnings


def rename(tab, row, text):
    """Rename a cluster the way editing its Name cell does."""
    tab.updating_cluster_table_flag = False
    tab.cluster_table.setItem(row, 1, QTableWidgetItem(text))


def test_renaming_a_cluster_works_and_leaves_the_labels_alone(loaded_window, monkeypatch):
    window, _ = loaded_window
    tab, entries, warnings = cluster_four(window, monkeypatch)
    labels = window.data['RM01'].processed[METHOD].values.copy()

    rename(tab, 1, 'Plagioclase')

    # 1. the name is stored, and reaches the legend
    assert entries[1]['name'] == 'Plagioclase'
    _, legend, _ = window.style_data.get_cluster_colormap(entries)
    assert legend[1] == 'Plagioclase'

    # 2. names live in cluster_dict only -- a string in the label column would
    #    break every np.isin match on it: the cluster mask, cluster_percentages
    #    and cluster-defined regions
    column = window.data['RM01'].processed[METHOD]
    assert column.dtype == np.float64
    np.testing.assert_array_equal(column.values, labels)
    assert sorted(window.data['RM01'].cluster_percentages(METHOD)) == [0, 1, 2, 3]

    # 3. duplicate names are still refused, and the cell reverts so the table
    #    keeps matching the model
    rename(tab, 2, 'Plagioclase')
    assert entries[2]['name'] != 'Plagioclase'
    assert any('Duplicate' in str(w) for w in warnings)
    assert tab.cluster_table.item(2, 1).text() == entries[2]['name']

    # 4. a linked class is labelled by its leader, so renaming the leader is
    #    how the class gets named
    for row in range(tab.cluster_table.rowCount()):
        tab.cluster_table.cellWidget(row, 0).setChecked(row in (0, 1))
    tab.actionClusterLink.trigger()
    rename(tab, 0, 'Feldspar')
    _, legend, _ = window.style_data.get_cluster_colormap(entries)
    assert legend[0] == legend[1] == 'Feldspar'


def test_a_method_with_no_labels_leaves_an_empty_table(loaded_window, monkeypatch):
    """Stale rows would keep live checkboxes reporting a phantom selection."""
    window, _ = loaded_window
    tab, _, _ = cluster_four(window, monkeypatch)
    assert tab.cluster_table.rowCount() == 4

    # a method that has never been computed for this sample
    window.app_data.cluster_method = 'fuzzy c-means'
    tab.update_table_widget()

    assert tab.cluster_table.rowCount() == 0
    assert tab._checked_cluster_ids() == []
    assert not tab.actionClusterLink.isEnabled()
    assert not tab.actionClusterRegion.isEnabled()
