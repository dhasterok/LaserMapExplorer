"""Regression tests for the discrete cluster-/ROI-map colormaps
(``src/plotting/LamePlot.py`` ``plot_cluster_map`` / ``plot_roi_map`` and
``src/style/StyleToolbox.py`` ``get_cluster_colormap`` / ``get_roi_colormap``).

The bug: ``plot_cluster_map`` sized the colour ``norm`` from the number of
cluster labels *still visible* (``np.unique`` of the non-masked pixels).
When the cluster table has a subset selected, ``BoundaryNorm``'s range
collapses and every remaining pixel clips to the first colour -- with one
cluster shown, every pixel gets cluster 0's colour. The norm has to span
*every* group the colormap defines, so raw label ``k`` always lands on
``cmap(k)``. ``plot_roi_map`` already did this (``len(data.roi_stack)``);
these tests pin the shared behaviour for both.

PyQt-free: ``get_cluster_colormap`` / ``get_roi_colormap`` don't touch
``self``, and ``color_norm``'s discrete branch is just a ``BoundaryNorm``
over ``arange(-0.5, N, 1)`` -- reproduced here.
"""
import inspect
import sys
from pathlib import Path

import numpy as np
import pytest
from matplotlib import colors

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.style.StyleToolbox import StyleData
from src.plotting import LamePlot


def discrete_norm(n):
    """Same construction as StyleData.color_norm(N) for cscale='discrete'."""
    return colors.BoundaryNorm(np.arange(-0.5, n, 1), n, clip=True)


# --- the discrete colormap is built straight from the table colours -----------

def test_get_roi_colormap_uses_stack_colours_in_order():
    roi_stack = [
        {'id': 1, 'name': 'A', 'color': '#ff0000'},
        {'id': 2, 'name': 'B', 'color': '#00ff00'},
        {'id': 5, 'name': 'C', 'color': '#0000ff'},   # ids need not be contiguous
    ]
    roi_color, roi_label, cmap = StyleData.get_roi_colormap(None, roi_stack, alpha=100)

    assert roi_label == ['A', 'B', 'C']
    assert cmap.N == 3
    assert cmap(0) == pytest.approx((1.0, 0.0, 0.0, 1.0))
    assert cmap(1) == pytest.approx((0.0, 1.0, 0.0, 1.0))
    assert cmap(2) == pytest.approx((0.0, 0.0, 1.0, 1.0))


def test_get_cluster_colormap_uses_dict_colours_and_alpha():
    cluster_dict = {
        0: {'name': '0', 'color': '#ff0000'},
        1: {'name': '1', 'color': '#00ff00'},
        2: {'name': '2', 'color': '#0000ff'},
        3: {'name': '3', 'color': '#ffff00'},
        'n_clusters': 4,   # ignored -- non-int key
    }
    cluster_color, cluster_label, cmap = StyleData.get_cluster_colormap(None, cluster_dict, alpha=50)

    assert cluster_label == ['0', '1', '2', '3']
    assert cmap.N == 4
    for i, rgb in enumerate([(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0)]):
        assert cmap(i) == pytest.approx(rgb + (0.5,))  # alpha 50 -> 0.5


def test_roi_and_cluster_colormaps_match_for_equivalent_inputs():
    hexcols = ['#112233', '#445566', '#778899']
    roi_stack = [{'id': i + 1, 'name': str(i), 'color': c} for i, c in enumerate(hexcols)]
    cluster_dict = {i: {'name': str(i), 'color': c} for i, c in enumerate(hexcols)}

    rc, _, rcmap = StyleData.get_roi_colormap(None, roi_stack)
    cc, _, ccmap = StyleData.get_cluster_colormap(None, cluster_dict)

    assert rcmap.N == ccmap.N == 3
    assert [rcmap(i) for i in range(3)] == [ccmap(i) for i in range(3)]
    assert rc == cc


# --- the norm has to span every group, not just the visible ones -------------

def test_partial_selection_keeps_each_group_on_its_own_colour():
    """cmap has 4 colours; only group id 3 is visible. Sizing the norm from
    the visible count (1) is the bug; sizing it from the full count (4) is
    the fix.
    """
    cmap = colors.ListedColormap(
        [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1), (1, 1, 0, 1)]
    )

    buggy = discrete_norm(1)                     # len(np.unique(visible)) == 1
    assert cmap(buggy(3.0)) == (1.0, 0.0, 0.0, 1.0)   # clips to colour 0 -- wrong

    fixed = discrete_norm(4)                     # full group count
    assert cmap(fixed(3.0)) == (1.0, 1.0, 0.0, 1.0)   # group 3 -> colour 3
    for k in range(4):
        assert cmap(fixed(float(k))) == cmap(k)


def test_multiple_but_not_all_selected_still_correct():
    cmap = colors.ListedColormap(
        [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1), (1, 1, 0, 1)]
    )
    # groups 1 and 3 visible (2 of 4). Visible-count norm (2) sends 3 -> colour 1.
    assert cmap(discrete_norm(2)(3.0)) == (0.0, 1.0, 0.0, 1.0)      # wrong
    full = discrete_norm(4)
    assert cmap(full(1.0)) == (0.0, 1.0, 0.0, 1.0)                  # right
    assert cmap(full(3.0)) == (1.0, 1.0, 0.0, 1.0)                  # right


# --- pin the fix in the plotting code itself ---------------------------------

def test_plot_cluster_map_sizes_norm_from_full_cluster_count():
    src = inspect.getsource(LamePlot.plot_cluster_map)
    # the norm count now comes from the cluster_dict's own keys ...
    assert "cluster_dict[method].keys()" in src
    # ... not from whatever labels are left after masking
    assert "np.unique(groups[~np.isnan(groups)])" not in src


def test_plot_roi_map_sizes_norm_from_full_roi_count():
    src = inspect.getsource(LamePlot.plot_roi_map)
    assert "len(data.roi_stack)" in src
    assert "np.unique" not in src


# --- stale cluster entries after reducing the cluster count ------------------
#
# The legend/colormap is sized from cluster_dict's int keys (see
# get_cluster_colormap). AppData.cluster_group_changed is responsible for
# clearing the previous run's per-cluster entries before repopulating; when it
# didn't, reducing the cluster count left the high-numbered entries behind and
# the map kept drawing legend patches for clusters that no longer existed.


def _cluster_dict_after_runs(*cluster_counts):
    """Replay cluster_group_changed's dict bookkeeping for successive runs.

    Mirrors the method's clear-then-repopulate on a plain dict, so the
    behaviour can be pinned without a MainWindow (the method needs a real
    AppData parent, and StyleData for the colours).
    """
    entry = {'n_clusters': 0, 'seed': 23, 'selected_clusters': []}
    for n in cluster_counts:
        entry['selected_clusters'] = []
        # the clear step under test
        for cluster_id in [k for k in entry if isinstance(k, int)]:
            del entry[cluster_id]
        for c in range(n):
            entry[c] = {'name': f'Cluster {c + 1}', 'link': [], 'color': '#ff0000'}
        entry['n_clusters'] = n
    return entry


def test_reducing_the_cluster_count_drops_the_stale_entries():
    entry = _cluster_dict_after_runs(6, 3)

    assert sorted(k for k in entry if isinstance(k, int)) == [0, 1, 2]
    _colors, labels, cmap = StyleData.get_cluster_colormap(None, entry, alpha=100)
    assert labels == ['Cluster 1', 'Cluster 2', 'Cluster 3']
    assert cmap.N == 3


def test_increasing_the_cluster_count_still_works():
    entry = _cluster_dict_after_runs(3, 8)

    _colors, labels, cmap = StyleData.get_cluster_colormap(None, entry, alpha=100)
    assert len(labels) == 8
    assert cmap.N == 8


def test_clearing_cluster_entries_keeps_the_methods_settings():
    """Only cluster ids are int keys -- 'n_clusters', 'seed' and friends are
    str keys and have to survive the clear."""
    entry = _cluster_dict_after_runs(6, 2)

    assert entry['seed'] == 23
    assert entry['n_clusters'] == 2
    assert entry['selected_clusters'] == []


def test_a_stale_mask_group_is_cleared_too():
    """99 is the mask/noise group. It's an int key like any other cluster id,
    so a run that produces no mask must not leave the old one behind."""
    entry = _cluster_dict_after_runs(4)
    entry[99] = {'name': 'Mask', 'link': [], 'color': '#888888'}

    entry = {**entry}
    for cluster_id in [k for k in entry if isinstance(k, int)]:
        del entry[cluster_id]
    for c in range(2):
        entry[c] = {'name': f'Cluster {c + 1}', 'link': [], 'color': '#ff0000'}

    assert 99 not in entry
    _colors, labels, _cmap = StyleData.get_cluster_colormap(None, entry, alpha=100)
    assert labels == ['Cluster 1', 'Cluster 2']


def test_cluster_group_changed_clears_int_keys_not_str_keys():
    """Pin the fix in the source: the clear must key off int-ness. The loop it
    replaced popped str(i) against int keys, so it raised on its first
    iteration and removed nothing at all."""
    from src.app.AppData import AppData

    src = inspect.getsource(AppData.cluster_group_changed)
    assert "isinstance(k, int)" in src
    assert "pop(str(i))" not in src
