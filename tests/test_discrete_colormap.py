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
