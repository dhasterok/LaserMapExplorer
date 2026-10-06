"""Field maps of categorical fields, and of fields with no spread at all.

Three bugs, all on the same path -- selecting a non-analyte field as a field
map's colour field (which `PlotAxisSettings`' 'field map' `cfield_type` allows
for Cluster, ROI, Special and Stoichiometry):

* ``plot_small_histogram`` divided the value range by the bin count, so a
  *constant* field gave a 0 bin width and ``np.arange(lo, lo, 0)`` raised
  "arange: cannot compute length", aborting the plot update. A uniform
  categorical classification is ordinary data, not an edge case -- a garnet
  that is almandine everywhere gives a constant ``<abbrev>_dominant`` column.
* cluster columns were never marked categorical, so a Cluster field map drew a
  continuous colorbar over what are only group codes.
* the plot tree had no branch for these field types, so ``add_tree_item``
  raised ``KeyError`` *after* the canvas was drawn -- the map appeared but
  never entered the tree, and so could not be recalled.

Headless MainWindow integration tests -- shared setup comes from
tests/conftest.py.
"""
import numpy as np
import pytest

from src.plotting.LamePlot import plot_map_mpl
from tests.conftest import first_analyte


@pytest.fixture
def clustered_window(loaded_window):
    """``(window, data, method)`` with k-means already computed."""
    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    window.app_data.cluster_method = 'k-means'
    window.app_data.num_clusters = 4
    window.app_data.update_cluster_flag = True
    window.control_dock.clustering.compute_clusters_update_groups()
    return window, window.app_data.current_data, window.app_data.cluster_method


def _draw_field_map(window, data, field_type, field):
    window.style_data.plot_type = 'field map'
    window.app_data.c_field_type = field_type
    window.app_data.c_field = field
    canvas, _info, _ = plot_map_mpl(window, data, window.app_data, window.style_data,
                                     field_type, field)
    return canvas


# --- cluster fields are categorical -----------------------------------------

def test_cluster_column_is_marked_categorical(clustered_window):
    _window, data, method = clustered_window

    assert data.processed.get_attribute(method, 'discrete') is True
    codes = sorted(int(c) for c in set(data.processed[method].dropna()))
    assert data.processed.get_attribute(method, 'category_values') == codes
    assert len(data.processed.get_attribute(method, 'category_labels')) == len(codes)
    assert len(data.processed.get_attribute(method, 'category_colors')) == len(codes)


def test_cluster_field_map_uses_a_discrete_colormap(clustered_window):
    window, data, method = clustered_window
    n_clusters = len(data.processed.get_attribute(method, 'category_values'))

    canvas = _draw_field_map(window, data, 'Cluster', method)

    image = canvas.axes.get_images()[0]
    assert image.get_cmap().N == n_clusters, "one colour per cluster, not a continuous ramp"
    legend = canvas.axes.get_legend()
    assert legend is not None, "a categorical field gets a swatch legend, not a colorbar"
    assert len(legend.get_texts()) == n_clusters


def test_cluster_codes_map_one_to_one_onto_colours(clustered_window):
    """Cluster ids are 0-based, so the 1-based shift the discrete path applies
    by default would fold clusters 0 and 1 onto one colour. 'category_values'
    is what keeps them distinct."""
    window, data, method = clustered_window
    codes = data.processed.get_attribute(method, 'category_values')

    canvas = _draw_field_map(window, data, 'Cluster', method)

    drawn = np.asarray(canvas.axes.get_images()[0].get_array(), dtype=float).ravel()
    drawn = sorted(set(drawn[~np.isnan(drawn)].tolist()))
    assert drawn == [float(i) for i in range(len(codes))]


def test_reducing_the_cluster_count_updates_the_categories(clustered_window):
    """The attributes are rewritten on every recompute, so they can't go stale
    the way cluster_dict's own entries once did."""
    window, data, method = clustered_window
    assert len(data.processed.get_attribute(method, 'category_values')) == 4

    window.app_data.num_clusters = 2
    window.app_data.update_cluster_flag = True
    window.control_dock.clustering.compute_clusters_update_groups()

    assert len(data.processed.get_attribute(method, 'category_values')) == 2
    assert len(data.processed.get_attribute(method, 'category_labels')) == 2


# --- a field with no spread --------------------------------------------------

def test_field_map_of_a_constant_field_does_not_raise(loaded_window):
    """The reported symptom: ``np.arange(lo, lo, 0)`` in plot_small_histogram
    aborted the update, so the map never appeared."""
    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    data = window.app_data.current_data

    data.processed['FlatField'] = 2.0
    data.processed.set_attribute('FlatField', 'data_type', 'Special')
    data.processed.set_attribute('FlatField', 'units', None)

    canvas = _draw_field_map(window, data, 'Special', 'FlatField')
    assert canvas.axes.get_images()


def test_small_histogram_handles_a_constant_field(loaded_window):
    """Drive plot_small_histogram directly -- it is where the arange raised."""
    from src.plotting.LamePlot import plot_small_histogram

    window, _path = loaded_window
    window.app_data.sample_id = 'RM01'
    window.change_sample()
    data = window.app_data.current_data
    analyte = first_analyte(window)

    df = data.get_map_data(analyte, 'Analyte').copy()
    df['array'] = 2.0                      # no spread at all

    window.app_data.c_field_type = 'Analyte'
    window.app_data.c_field = analyte
    plot_small_histogram(window, data, window.app_data, window.style_data, df)


@pytest.mark.parametrize("value", [0.0, 2.0, -5.0, 1e9])
def test_constant_field_bin_edges_are_usable(value):
    """The guard's own arithmetic: a constant field must still yield a valid,
    strictly increasing pair of edges, whatever the value."""
    lo = hi = value
    span = hi - lo
    assert span <= 0
    half = max(abs(lo) * 1e-6, 0.5)
    edges = np.array([lo - half, lo + half])
    assert edges[1] > edges[0]
    assert np.all(np.isfinite(edges))
    np.histogram([value] * 10, bins=edges)      # must not raise


# --- the plot tree accepts these field types ---------------------------------

def test_cluster_field_map_through_the_ui_path_does_not_raise(clustered_window):
    """update_SV() is what the app actually calls. It files field maps under
    the 'Analyte' branch whatever the field type, so this does not assert a
    'Cluster' branch appears -- only that the whole path completes."""
    window, data, method = clustered_window
    window.app_data.c_field_type = 'Cluster'
    window.app_data.c_field = method
    window.style_data.plot_type = 'field map'

    window.update_SV()


def test_get_tree_items_creates_a_missing_branch(loaded_window):
    window, _path = loaded_window
    assert 'Stoichiometry' not in window.plot_tree.tree

    branch = window.plot_tree.get_tree_items('Stoichiometry')

    assert branch is not None
    assert window.plot_tree.tree['Stoichiometry'] is branch
    # idempotent -- a second call reuses it rather than duplicating
    assert window.plot_tree.get_tree_items('Stoichiometry') is branch


def test_prebuilt_branches_are_untouched(loaded_window):
    window, _path = loaded_window
    for name in ('Analyte', 'Ratio', 'Histogram', 'Correlation', 'Calculated'):
        assert name in window.plot_tree.tree
